# interactive_match.py
"""
Interactive CLI negotiation:
- You act as the SELLER (human).
- BuyerAgent responds (with optional HF phrasing if HF_API_KEY is set).
- Up to 10 rounds, or stops when either side accepts.

Run:
  python interactive_match.py
"""

import os
from buyer_agent import BuyerAgent, Product, HuggingFaceModelWrapper
from dotenv import load_dotenv

def maybe_load_hf_model():
    load_dotenv()
    api = os.getenv("HF_API_KEY")
    if not api:
        print("⚠️  HF_API_KEY not set. Running WITHOUT Hugging Face phrasing (logic still works).")
        return None
    try:
        print("✅ Using Hugging Face model for phrasing.")
        return HuggingFaceModelWrapper()  # default model id inside wrapper
    except Exception as e:
        print("⚠️  Could not init Hugging Face model. Falling back to no-LLM. Reason:", e)
        return None

def pick_product() -> Product:
    # You can change or prompt for these values as needed
    print("\nSelect a product to negotiate:")
    print("1) Alphonso Mangoes (A grade, export)")
    print("2) Kesar Mangoes (B grade)")
    choice = input("Enter 1 or 2: ").strip()
    if choice == "1":
        return Product(
            name="Alphonso Mangoes",
            category="Mangoes",
            quantity=100,
            quality_grade="A",
            origin="Ratnagiri",
            base_market_price=180000,
            attributes={"export_grade": True},
        )
    else:
        return Product(
            name="Kesar Mangoes",
            category="Mangoes",
            quantity=150,
            quality_grade="B",
            origin="Gujarat",
            base_market_price=150000,
            attributes={"export_grade": False},
        )

def main():
    model = maybe_load_hf_model()
    agent = BuyerAgent(personality_path="personality_config.json", model=model)

    product = pick_product()
    print(f"\n📦 Product: {product.name} | Market: ₹{product.base_market_price:,}")

    # Ask buyer budget
    while True:
        try:
            budget = int(input("Enter BUYER budget (₹): ").replace(",", "").strip())
            break
        except Exception:
            print("Please enter a valid integer (e.g., 180000).")

    print("\nYou are the SELLER. Enter a numeric offer each round (or 'q' to quit).")
    print("The buyer will respond with an aggressive strategy and optional LLM phrasing.\n")

    seller_msg = f"Opening price ₹{int(product.base_market_price * 1.5)}"
    print(f"Seller (opening): {seller_msg}")

    for round_num in range(1, 11):
        # Buyer responds to the seller message (string) so the logic sees context, not only price
        response = agent.negotiate(product, budget, seller_msg, round_num)
        print(f"Buyer (R{round_num}): {response.message}")
        if response.status.name == "ACCEPTED":
            print(f"✅ Deal closed at ₹{response.price:,} on round {round_num}")
            return

        # Get next seller price
        seller_in = input("Your next SELLER offer (₹ number), or 'q' to quit: ").strip()
        if seller_in.lower() in {"q", "quit", "exit"}:
            print("👋 Exiting without a deal.")
            return
        try:
            seller_offer = int(seller_in.replace(",", ""))
        except Exception:
            print("Please enter a valid integer price.")
            seller_offer = None

        # Build seller message from the offer to keep parsing consistent
        seller_msg = f"I can sell for ₹{seller_offer}" if seller_offer else "Give me your best price."

    print("⏳ Reached 10 rounds without agreement. No deal.")

if __name__ == "__main__":
    main()
