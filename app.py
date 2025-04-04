import streamlit as st
from dotenv import load_dotenv
import google.generativeai as genai
import os
import pandas as pd

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE-API-KEY"))

# Streamlit UI
st.header("💰 Personal Finance :blue[Advisor] 📊", divider="green")
user_input = st.text_input("Hi! I'm your Personal Finance Assistant 🧠. Ask me anything related to budgeting, saving, investing, or personal finance.")

submit = st.button("Submit")

# Sidebar - Monthly Budget Planner
st.sidebar.subheader("📆 Monthly Budget Planner")
income = st.sidebar.text_input("Monthly Income (₹): ", value="0")
expenses = st.sidebar.text_input("Monthly Expenses (₹): ", value="0")

try:
    income = float(income)
    expenses = float(expenses)
    savings = income - expenses
    st.sidebar.write(f"💵 Estimated Savings: ₹{savings:,.2f}")

    if income > 0:
        savings_ratio = (savings / income) * 100
        st.sidebar.write(f"📈 Savings Rate: {savings_ratio:.2f}%")
except:
    st.sidebar.write("Please enter valid numbers.")

# Finance Categories Info
finance_tips = """
**Suggested Allocation (50/30/20 Rule):**
- **50% Needs:** Rent, groceries, utilities
- **30% Wants:** Dining out, entertainment
- **20% Savings & Investments:** FD, SIPs, stocks

🧾 Track your expenses and stick to a plan!
"""
st.sidebar.markdown(finance_tips)

# AI Chat Response
def get_finance_response(text_input):
    model = genai.GenerativeModel("gemini-1.5-pro")
    if text_input != "":
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
        response = model.generate_content(prompt + text_input)
        return response.text
    else:
        return "Please enter a question!"

if submit:
    response = get_finance_response(user_input)
    st.subheader("The :orange[Response] is:")
    st.write(response)

# Disclaimer
st.subheader("Disclaimer", divider=True)
st.markdown("""
1. This AI tool provides general financial guidance and is not a substitute for professional advice.
2. Please consult a certified financial planner for investment or legal decisions.
""")
