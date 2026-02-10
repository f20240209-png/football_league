import os
from google import genai
from dotenv import load_dotenv

# Load your API Key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: API Key not found. Make sure .env file is correct.")
else:
    print(f"✅ API Key found: {api_key[:5]}*******")
    
    try:
        client = genai.Client(api_key=api_key)
        print("\n🔍 Checking available models for your account...")
        
        # List all models
        models = client.models.list()
        
        print("\n--- ✅ AVAILABLE MODELS ---")
        found_any = False
        for m in models:
            # We only care about models that can generate content
            if "generateContent" in m.supported_actions:
                print(f"• {m.name}")
                found_any = True
        
        if not found_any:
            print("❌ No models found. You might need to enable the Free Tier in Google AI Studio.")
            
    except Exception as e:
        print(f"\n❌ ERROR CONNECTING TO GOOGLE: {e}")