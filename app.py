import streamlit as st
from dotenv import load_dotenv
import os
import pandas as pd
import google.generativeai as genai

# --- Load API Key ---
load_dotenv()  # Load .env if exists (for local dev)

# Prefer Streamlit secret if running on Cloud
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", os.getenv("GOOGLE-API-KEY"))

# Exit gracefully if API key is missing
if not GOOGLE_API_KEY:
    st.error("🚫 Google API key not found. Please set it in .env or Streamlit secrets.")
    st.stop()

# Configure Gemini API
genai.configure(api_key=GOOGLE_API_KEY)

# --- Page Layout ---
st.header("💰 Personal Finance Advisor 📊", divider="green")

user_input = st.text_input("Hi! I'm your Personal Finance Assistant 🧠. Ask me anything related to budgeting, saving, investing, or personal finance.")
submit = st.button("Submit")

# --- Sidebar Budget Calculator ---
st.sidebar.subheader("📆 Monthly Budget Planner")
income = st.sidebar.text_input("Monthly Income (₹):", value="0")
expenses = st.sidebar.text_input("Monthly Expenses (₹):", value="0")

try:
    income = float(income)
    expenses = float(expenses)
    savings = income - expenses
    st.sidebar.write(f"💵 Estimated Savings: ₹{savings:,.2f}")
    if income > 0:
        savings_ratio = (savings / income) * 100
        st.sidebar.write(f"📈 Savings Rate: {savings_ratio:.2f}%")
except:
    st.sidebar.write("⚠️ Please enter valid numbers.")

st.sidebar.markdown("""
**Suggested Allocation (50/30/20 Rule):**
- **50% Needs:** Rent, groceries, utilities  
- **30% Wants:** Dining out, entertainment  
- **20% Savings & Investments:** FD, SIPs, stocks  

🧾 Track your expenses and stick to a plan!
""")

# --- Gemini API Call ---
def get_finance_response(text_input):
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        prompt = '''I want you to act as a Financial Advisor and only respond to topics on:
- Budgeting
- Saving and Investments
- Retirement Planning
- Emergency Funds
- Mutual Funds, SIPs, FDs
- Personal Finance strategies

If the user asks anything outside personal finance, just reply:
"I am a Personal Finance Chatbot. I can help only with saving, investing, and financial planning-related questions."

If the user asks for stock tips, say:
"I'm not authorized to give stock recommendations. Please consult a SEBI-registered advisor."

So here's the user's question: 
'''
        with st.spinner("💬 Generating your personalized advice..."):
            response = model.generate_content(prompt + text_input)
        return response.text
    except Exception as e:
        return f"❌ Error: {str(e)}"

# --- Handle Submission ---
if submit and user_input.strip() != "":
    response = get_finance_response(user_input)
    st.subheader("🧠 The :orange[Response] is:")
    st.write(response)

# --- Disclaimer ---
st.subheader("Disclaimer", divider=True)
st.markdown("""
1. This AI tool provides general financial guidance and is not a substitute for professional advice.  
2. Please consult a certified financial planner for investment or legal decisions.
""")
