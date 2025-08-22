<<<<<<< HEAD
# Buyer_Negotiator_Model
# Negotiation Agent Project

A buyer agent built using **DeepMind’s Concordia framework** to simulate negotiation scenarios.  
This project defines agent personalities, strategies, and behaviors for interactive negotiation tasks.  
Includes all required dependencies for easy setup and reproducibility.

## Files in this Repo
- `buyer_agent.py` → Concordia-based implementation of the buyer agent  
- `personality_config.json` → Personality configuration for the agent  
- `strategy.md` → One-page explanation of the negotiation strategy  
- `requirements.txt` → Required dependencies for the project  

## Setup
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Mac/Linux
.venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt
=======
# Negotiation Agent Project (Hugging Face)

This project implements an **Aggressive Negotiator** buyer agent with a configurable personality.
The agent uses deterministic decision rules for offers and can optionally use a Hugging Face model
for phrasing messages (not for price decisions).

## Files
- `buyer_agent.py` : Buyer agent implementation (loadable by harness)
- `personality_config.json` : Configurable personality and strategy params
- `strategy.md` : 1-page strategy explanation
- `run_match.py` : Simple simulation harness to test agent vs MockSeller
- `requirements.txt` : Python dependencies
- `.env.example` : Example environment variables

## Setup
1. Create and activate a virtual environment.
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # or .venv\Scripts\activate on Windows
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file (copy `.env.example`) and set your Hugging Face token:
   ```
   HF_API_KEY=hf_YOUR_TOKEN_HERE
   ```
4. Run simulations:
   ```bash
   python run_match.py
   ```

## Hugging Face integration
The project includes `HuggingFaceModelWrapper` in `buyer_agent.py` that uses the Inference API.
The wrapper expects `HF_API_KEY` in the environment. If the key is missing, the agent falls back to deterministic phrasing.

## Tuning
Edit `personality_config.json` to tweak strategy parameters (opening_pct, mid_pct, late_pct, final_round, etc.).

## Notes
- The agent ensures it never exceeds its budget.
- The LLM is only used for natural language phrasing — all price decisions are rule-based to ensure reproducibility.
>>>>>>> cc21a83 (Initial commit with .gitignore)
