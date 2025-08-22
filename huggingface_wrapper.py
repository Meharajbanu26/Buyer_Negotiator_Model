# huggingface_wrapper.py
import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get Hugging Face API key from .env
HF_API_KEY = os.getenv("HF_API_KEY")

# Check if key exists
if not HF_API_KEY:
    raise ValueError("❌ Hugging Face API Key not found! Please add it to your .env file as HF_API_KEY='your_key_here'")

# Choose the model you want to use (you can change this to any Hugging Face hosted model)
MODEL_ID = "meta-llama/Llama-2-7b-chat-hf"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_ID}"

# Set headers for API request
HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}


def query_huggingface(prompt: str) -> str:
    """
    Sends a prompt to the Hugging Face Inference API and returns the model's response.
    """
    payload = {"inputs": prompt}

    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)

        if response.status_code != 200:
            raise Exception(f"❌ Hugging Face API Error {response.status_code}: {response.text}")

        result = response.json()

        # Hugging Face returns list of dicts for text models
        if isinstance(result, list) and "generated_text" in result[0]:
            return result[0]["generated_text"].strip()
        else:
            return str(result)

    except Exception as e:
        return f"⚠️ Error querying Hugging Face: {e}"
