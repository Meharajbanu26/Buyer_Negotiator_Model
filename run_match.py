"""run_match.py
Simple simulation harness that uses BuyerAgent and a MockSeller to run negotiation tests.
Use this to evaluate performance locally.
"""
from dataclasses import dataclass
from typing import Tuple, Optional
import json, os
from buyer_agent import BuyerAgent, Product, NegotiationResponse, DealStatus, HuggingFaceModelWrapper

@dataclass
class MockSeller:
    min_price: int  # seller's true minimum (hidden from buyer)
    personality: str = "standard"

    def get_opening_price(self, product: Product) -> Tuple[int, str]:
        price = int(product.base_market_price * 1.5)
        return price, f"These are premium {product.quality_grade} grade {product.name}. I'm asking ₹{price}."

    def respond_to_buyer(self, buyer_offer: Optional[int], round_num: int) -> Tuple[int, str, bool]:
        # If buyer_offer exceeds a profitable margin, accept.
        if buyer_offer is not None and buyer_offer >= int(self.min_price * 1.1):
            return buyer_offer, f"You have a deal at ₹{buyer_offer}!", True
        # If late rounds, soften aggressively
        if round_num >= 8:
            counter = max(self.min_price, int(buyer_offer * 1.05) if buyer_offer else self.min_price)
            return counter, f"Final offer: ₹{counter}. Take it or leave it.", False
        # Normal behavior: come down to ~15% above buyer_offer
        counter = max(self.min_price, int((buyer_offer or self.min_price) * 1.15))
        return counter, f"I can come down to ₹{counter}.", False

def run_single_simulation(agent: BuyerAgent, product: Product, buyer_budget: int, seller_min: int) -> dict:
    seller = MockSeller(min_price=seller_min)
    # Seller opens
    seller_price, seller_msg = seller.get_opening_price(product)
    conversation = [{"role":"seller","message":seller_msg}]

    deal_made = False
    final_price = None
    buyer_offer = None

    for round_num in range(1, 11):  # 1..10
        # Buyer responds
        response = agent.negotiate(product, buyer_budget, seller_msg, round_num)
        conversation.append({"role":"buyer","message":response.message, "price": response.price})
        if response.status == DealStatus.ACCEPTED:
            deal_made = True
            final_price = response.price
            break
        buyer_offer = response.price
        # Seller responds
        seller_price, seller_msg, seller_accepts = seller.respond_to_buyer(buyer_offer, round_num)
        conversation.append({"role":"seller","message":seller_msg, "price": seller_price})
        if seller_accepts:
            deal_made = True
            final_price = buyer_offer
            break

    result = {
        "deal_made": deal_made,
        "final_price": final_price,
        "rounds": round_num,
        "savings": (buyer_budget - final_price) if deal_made and final_price else 0,
        "conversation": conversation
    }
    return result

def main():
    # Load product examples
    products = [
        Product(name="Alphonso Mangoes", category="Mangoes", quantity=100, quality_grade="A", origin="Ratnagiri", base_market_price=180000, attributes={"export_grade": True}),
        Product(name="Kesar Mangoes", category="Mangoes", quantity=150, quality_grade="B", origin="Gujarat", base_market_price=150000, attributes={"export_grade": False})
    ]

    # Initialize agent with Hugging Face wrapper if HF_API_KEY provided; else model=None
    hf_key = os.getenv("HF_API_KEY")
    model = None
    if hf_key:
        try:
            model = HuggingFaceModelWrapper()
        except Exception as e:
            print("Warning: Hugging Face wrapper init failed:", e)
            model = None

    agent = BuyerAgent(personality_path="personality_config.json", model=model)

    scenarios = ["easy","medium","hard"]
    for product in products:
        for scenario in scenarios:
            if scenario == "easy":
                buyer_budget = int(product.base_market_price * 1.2)
                seller_min = int(product.base_market_price * 0.8)
            elif scenario == "medium":
                buyer_budget = int(product.base_market_price * 1.0)
                seller_min = int(product.base_market_price * 0.85)
            else:
                buyer_budget = int(product.base_market_price * 0.9)
                seller_min = int(product.base_market_price * 0.82)

            print(f"\nTest: {product.name} - {scenario} scenario\nBudget: ₹{buyer_budget:,} | Market: ₹{product.base_market_price:,}")
            result = run_single_simulation(agent, product, buyer_budget, seller_min)
            if result["deal_made"]:
                print(f"✅ DEAL at ₹{result['final_price']:,} in {result['rounds']} rounds | Savings: ₹{result['savings']:,}")
            else:
                print(f"❌ NO DEAL after {result['rounds']} rounds")        
if __name__ == '__main__':
    main()
