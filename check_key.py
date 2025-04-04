from dotenv import load_dotenv
import os

# Load the .env file from the current directory (symlinked to env repo)
load_dotenv()

api_key = os.getenv("GOOGLE-API-KEY")

if api_key:
    print("✅ GOOGLE-API-KEY found:", api_key[:8] + "..." + api_key[-4:])
else:
    print("🚫 GOOGLE-API-KEY not found.")
