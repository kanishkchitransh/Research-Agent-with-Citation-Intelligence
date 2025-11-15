"""Quick test to debug Perplexity API."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("PERPLEXITY_API_KEY")
print(f"API Key: {api_key[:20]}..." if api_key else "No API key found")

# Test Perplexity API
url = "https://api.perplexity.ai/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}

payload = {
    "model": "sonar",
    "messages": [
        {
            "role": "system",
            "content": "You are a research assistant.",
        },
        {
            "role": "user",
            "content": "Find the paper: Tucker et al. 2021 academic paper",
        },
    ],
    "temperature": 0.2,
    "max_tokens": 500,
}

print("\nTesting Perplexity API...")
try:
    response = requests.post(url, json=payload, headers=headers, timeout=30)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text[:500]}")

    if response.status_code == 200:
        data = response.json()
        print("\n[SUCCESS]")
        print(f"Content: {data.get('choices', [{}])[0].get('message', {}).get('content', '')[:200]}")
    else:
        print(f"\n[ERROR] Status: {response.status_code}")
        print(f"Details: {response.text}")

except Exception as e:
    print(f"\n[ERROR] Exception: {e}")
