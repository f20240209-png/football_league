import os
from dotenv import load_dotenv
import google.generativeai as genai

# 1. Load the key
load_dotenv()
api_key = os.getenv("AIzaSyCFmGUeikxzy6pvFrlTmn-c6fP0kV6DMtU")

print("------------------------------------------------")
if not api_key:
    print("❌ ERROR: No API Key found. The variable is empty.")
    print("   Fix: Check that your .env file exists and has text inside.")
else:
    print(f"✅ Key Found: {api_key[:5]}... (Rest hidden)")

# 2. Try to connect
print("🤖 Attempting to contact Gemini...")
try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content("Say 'Hello' if you can hear me!")
    print(f"✅ SUCCESS! The AI said: {response.text}")
except Exception as e:
    print("\n❌ CRITICAL ERROR:")
    print(e)
print("------------------------------------------------")