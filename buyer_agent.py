# buyer_agent.py
from __future__ import annotations

import os
import json
import re
import requests
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from dotenv import load_dotenv

# ==============================
# Hugging Face model wrapper
# ==============================
class HuggingFaceModelWrapper:
    """Minimal wrapper around Hugging Face Inference API (text generation).
    If HF_API_KEY is unavailable, raise at init so caller can fall back gracefully.
    """

    def __init__(self, model_id: str = "meta-llama/Meta-Llama-3-8B-Instruct") -> None:
        load_dotenv()  # read .env if present
        self.model_id = model_id

        # Primary expected var
        self.api_key = os.getenv("HF_API_KEY")
        # (Optional) If you DO NOT want to change run_match.py but it checks a weird env var name,
        # you can ALSO set that name in your .env to the same key so run_match decides to enable model.
        # Example: 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=<your key>

        if not self.api_key:
            raise RuntimeError(
                "HF_API_KEY not found in environment. "
                "Set HF_API_KEY in your .env (or shell) to enable Hugging Face."
            )

        self.endpoint = f"https://api-inference.huggingface.co/models/{self.model_id}"
        self.headers = {"Authorization": f"Bearer {self.api_key}"}

    def generate(self, prompt: str, max_tokens: int = 160, temperature: float = 0.7) -> str:
        """Basic text generation call."""
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                # Keep defaults simple/robust for HF hosted inference
                "return_full_text": False,
            },
        }
        r = requests.post(self.endpoint, headers=self.headers, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()

        # HF responses can be list[{"generated_text": "..."}] or another shape.
        if isinstance(data, list) and data and isinstance(data[0], dict) and "generated_text" in data[0]:
            return str(data[0]["generated_text"]).strip()
        if isinstance(data, dict) and "generated_text" in data:
            return str(data["generated_text"]).strip()

        # Fallback stringify
        return str(data)


# ==============================
# Negotiation structures
# ==============================
class DealStatus(Enum):
    ONGOING = "ongoing"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


@dataclass
class NegotiationResponse:
    status: DealStatus
    price: Optional[int]
    message: str


@dataclass
class Product:
    name: str
    category: str
    quantity: int
    quality_grade: str
    origin: str
    base_market_price: int
    attributes: Dict[str, Any]


# ==============================
# Concordia-style components
# ==============================
class MemoryComponent:
    """Keeps short serialized history (round, role, msg, price)."""

    def __init__(self, max_len: int = 200) -> None:
        self.max_len = max_len
        self.history: List[Dict[str, Any]] = []

    def add(self, round_num: int, role: str, message: str, price: Optional[int]) -> None:
        self.history.append(
            {"round": int(round_num), "role": role, "message": message, "price": price}
        )
        if len(self.history) > self.max_len:
            self.history.pop(0)

    def summary(self, last_n: int = 8) -> str:
        recent = self.history[-last_n:]
        return "\n".join(
            f"R{h['round']} {h['role']}: {h['message']} (₹{h['price']})" for h in recent
        )

    def get_state(self) -> Dict[str, Any]:
        return {"history": self.history}

    def set_state(self, state: Dict[str, Any]) -> None:
        self.history = state.get("history", [])


class PersonalityComponent:
    """Loads buyer persona JSON (traits, style, catchphrases, strategy_params)."""

    def __init__(self, config_path: str = "personality_config.json") -> None:
        with open(config_path, "r", encoding="utf-8") as fh:
            self.persona: Dict[str, Any] = json.load(fh)

    def make_prompt(self) -> str:
        p = self.persona
        traits = ", ".join(p.get("traits", []))
        style = p.get("negotiation_style", p.get("style", "direct"))
        phrases = ", ".join(p.get("catchphrases", []))
        return f"Persona: {p.get('name', 'Buyer')} | Style: {style} | Traits: {traits} | Catchphrases: {phrases}"

    def strategy_params(self) -> Dict[str, Any]:
        return self.persona.get("strategy_params", {})

    def get_state(self) -> Dict[str, Any]:
        return {"persona": self.persona}

    def set_state(self, state: Dict[str, Any]) -> None:
        if state.get("persona"):
            self.persona = state["persona"]


class ObservationComponent:
    """Extract seller price, finality, urgency and concession hints from a message."""

    PRICE_RE = re.compile(r"(?:₹|INR|Rs\.?)\s*([\d,]+)|\b(\d{4,})\b", re.I)

    def parse(self, seller_message: str) -> Dict[str, Any]:
        seller_price = None
        m = self.PRICE_RE.search(seller_message)
        if m:
            num = m.group(1) or m.group(2)
            try:
                seller_price = int(num.replace(",", ""))
            except Exception:
                seller_price = None

        is_final = bool(re.search(r"\b(final|take it or leave it|last)\b", seller_message, re.I))
        urgency = 0.9 if is_final or re.search(r"\b(urgent|today|immediately)\b", seller_message, re.I) else 0.3
        concession = bool(re.search(r"\b(come down|reduce|lower)\b", seller_message, re.I))

        return {
            "seller_price": seller_price,
            "is_final": is_final,
            "urgency": float(urgency),
            "concession": concession,
            "raw": seller_message,
        }


class DecisionComponent:
    """Aggressive strategy: low anchor (60–70%), pressure, larger jumps near deadline."""

    def __init__(self, personality: PersonalityComponent, memory: MemoryComponent, cfg: Optional[Dict[str, Any]] = None) -> None:
        self.personality = personality
        self.memory = memory
        cfg = cfg or personality.strategy_params()

        # Tunables (with safe defaults)
        self.opening_pct = float(cfg.get("opening_pct", 0.65))
        self.mid_pct = float(cfg.get("mid_pct", 0.80))
        self.late_pct = float(cfg.get("late_pct", 0.95))
        self.final_round = int(cfg.get("final_round", 9))
        self.walkaway_threshold_pct = float(cfg.get("walkaway_threshold_pct", 0.98))
        self.max_rounds = int(cfg.get("max_rounds", 10))

    def _fair_price(self, product: Product, urgency: float, budget: int) -> int:
        base = product.base_market_price
        factor = 1.0
        # simple quality/origin tweaks
        q = (product.quality_grade or "").lower()
        if q.startswith("a"):
            factor *= 1.05
        elif q.startswith("b"):
            factor *= 0.98
        if product.attributes.get("export_grade"):
            factor *= 1.05
        factor *= (1 + 0.10 * urgency)
        fair = int(base * factor)
        return min(fair, budget)

    def _opening(self, product: Product, budget: int) -> int:
        return min(int(product.base_market_price * self.opening_pct), budget)

    def _concession(self, product: Product, budget: int, round_num: int) -> int:
        if round_num <= 3:
            pct = self.opening_pct
        elif round_num <= 7:
            pct = self.mid_pct
        else:
            pct = self.late_pct
        return min(int(product.base_market_price * pct), budget)

    def decide(self, product: Product, budget: int, observation: Dict[str, Any], round_num: int) -> Tuple[DealStatus, Optional[int], str]:
        seller_price = observation.get("seller_price")
        is_final = bool(observation.get("is_final", False))
        urgency = float(observation.get("urgency", 0.3))
        concession = bool(observation.get("concession", False))

        fair = self._fair_price(product, urgency, budget)

        # No clear number yet → open or ask
        if seller_price is None:
            if round_num == 1:
                opening = self._opening(product, budget)
                return DealStatus.ONGOING, opening, f"My anchor is ₹{opening}. Put a solid number on the table."
            return DealStatus.ONGOING, None, "Quote a numeric price and we can move."

        # Accept if seller at/below our fair bound
        if seller_price <= fair:
            return DealStatus.ACCEPTED, seller_price, f"Done at ₹{seller_price}. Seal it."

        # If seller claims final and it fits within a near-walkaway budget, accept
        if is_final and seller_price <= budget and seller_price <= int(budget * self.walkaway_threshold_pct):
            return DealStatus.ACCEPTED, seller_price, f"Fine—final at ₹{seller_price}. Close now."

        # Near deadline: last sharp move
        if round_num >= self.final_round:
            counter = min(int((seller_price + budget) / 2), budget)
            if counter >= seller_price:
                return DealStatus.ACCEPTED, seller_price, f"Alright, I’ll take ₹{seller_price}."
            return DealStatus.ONGOING, counter, f"Last call: ₹{counter}. Take it or leave it."

        # Normal concession path
        counter = self._concession(product, budget, round_num)
        if concession:
            counter = min(int(counter * 1.08), budget)

        if counter >= seller_price:
            return DealStatus.ACCEPTED, seller_price, f"Okay, I’ll match ₹{seller_price}."

        persona = self.personality.make_prompt()
        pressure = " If you can’t move, I walk—plenty of options." if (round_num >= 4 and not concession) else ""
        return DealStatus.ONGOING, counter, f"{persona} I can do ₹{counter}.{pressure}"


# ==============================
# High-level BuyerAgent
# ==============================
class BuyerAgent:
    """Combines the components + optional HF model to phrase messages.
    Public API is stable for your run_match.py.
    """

    def __init__(self, personality_path: str, model: Optional[HuggingFaceModelWrapper] = None) -> None:
        self.memory = MemoryComponent()
        self.personality = PersonalityComponent(personality_path)
        self.observer = ObservationComponent()
        self.decision = DecisionComponent(self.personality, self.memory)
        self.model = model  # optional phrasing

    def _phrase(self, raw_text: str) -> str:
        if not self.model:
            return raw_text
        try:
            # Light prompt to keep style but preserve intent
            prompt = (
                f"Rewrite as a concise, confident buyer line, same meaning, keep numbers intact:\n"
                f"---\n{raw_text}\n---"
            )
            out = self.model.generate(prompt, max_tokens=80, temperature=0.4)
            return (out or raw_text).strip()[:500]
        except Exception:
            return raw_text

    def negotiate(self, product: Product, budget: int, seller_message: str, round_num: int) -> NegotiationResponse:
        """Main method used by run_match.py."""
        obs = self.observer.parse(seller_message)
        status, price, message = self.decision.decide(product, budget, obs, round_num)

        # hard safety: never exceed budget
        if price is not None and price > budget:
            price = budget

        phrased = self._phrase(message)

        # memory logging
        self.memory.add(round_num, "Seller", seller_message, obs.get("seller_price"))
        self.memory.add(round_num, "Buyer", phrased, price)

        return NegotiationResponse(status=status, price=price, message=phrased)

    # Helper used by interactive CLI (keeps run_match.py untouched)
    def respond_to_offer(self, product: Product, budget: int, seller_offer: int, round_num: int) -> tuple[int, bool, str]:
        """Take a numeric seller offer and return (buyer_counter_or_accept_price, did_accept, message)."""
        seller_msg = f"I can sell for ₹{seller_offer}"
        response = self.negotiate(product, budget, seller_msg, round_num)
        if response.status == DealStatus.ACCEPTED:
            return int(response.price or seller_offer), True, response.message
        return int(response.price or 0), False, response.message

