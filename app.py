import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
from datetime import datetime
import time
import os
import yfinance as yf
import plaid  # Remove if not using Plaid integration

# --- App Configuration ---
st.set_page_config(
    page_title="WealthWise AI",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Load API Key ---
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY"))

if not GOOGLE_API_KEY:
    st.error("🚫 Google API key not found. Please set it in secrets.toml or environment variables.")
    st.stop()

# Configure Gemini API
genai.configure(api_key=GOOGLE_API_KEY)

# --- Session State ---
if 'financial_data' not in st.session_state:
    st.session_state.financial_data = {
        'income': 0,
        'expenses': 0,
        'savings': 0,
        'goals': [],
        'transactions': [],
        'budget_categories': {
            'Housing': 0,
            'Food': 0,
            'Transportation': 0,
            'Utilities': 0,
            'Healthcare': 0,
            'Entertainment': 0,
            'Education': 0,
            'Savings': 0,
            'Investments': 0,
            'Debt Repayment': 0,
            'Other': 0
        },
        'investments': []
    }

if 'chat_context' not in st.session_state:
    st.session_state.chat_context = []

if 'achievements' not in st.session_state:
    st.session_state.achievements = {
        'budget_set': False,
        'first_investment': False,
        'savings_goal': False
    }

# --- Helper Functions ---
@st.cache_data(ttl=3600)
def get_market_data(ticker):
    return yf.Ticker(ticker).history(period="1mo")

def get_finance_response(text_input):
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        prompt = f'''You are WealthWise AI, an advanced financial advisor. Provide detailed, personalized advice including:
- Contextual chat history: {st.session_state.chat_context[-3:]}
- Current financial data: {st.session_state.financial_data}
- Question: {text_input}'''
        
        with st.spinner("🧠 Analyzing your financial query..."):
            response = model.generate_content(prompt)
            st.session_state.chat_context.append(response.text)
            return response.text
    except Exception as e:
        return f"❌ Error processing your request: {str(e)}"

def calculate_savings_metrics(income, expenses):
    savings = float(income) - float(expenses)
    savings_rate = (savings / float(income)) * 100 if income > 0 else 0.0
    return savings, savings_rate

def create_cashflow_diagram():
    income = st.session_state.financial_data['income']
    categories = st.session_state.financial_data['budget_categories']
    
    fig = px.sankey(
        node=dict(label=["Income"] + list(categories.keys())),
        link=dict(
            source=[0]*len(categories),
            target=list(range(1, len(categories)+1)),
            value=[income] + list(categories.values())
        )
    )
    fig.update_layout(title_text="Cash Flow Analysis", font_size=12)
    return fig

def calculate_goal_forecast(target, current, deadline):
    months_left = (datetime.strptime(deadline, "%Y-%m-%d") - datetime.now()).days // 30
    required_monthly = (target - current) / months_left if months_left > 0 else 0
    return {
        "required_monthly": required_monthly,
        "completion_probability": min(current/target*100 + (100 - current/target*100)/months_left, 100)
    }

def update_investment_values():
    for inv in st.session_state.financial_data['investments']:
        if inv['type'] in ["Stocks", "ETF"] and 'ticker' in inv:
            try:
                data = get_market_data(inv['ticker'])
                inv['current_value'] = data['Close'].iloc[-1] * inv.get('shares', 1)
            except:
                pass

# --- Custom CSS ---
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("style.css")

# --- Main App ---
def main():
    # --- Header Section ---
    st.markdown("""
    <div class="header">
        <h1>WealthWise AI</h1>
        <p class="subtitle">Your Intelligent Personal Finance Assistant</p>
        <div class="dashboard-header">
            <div class="metric-card">
                <h3>Net Worth</h3>
                <p>₹{(sum(inv['current_value'] for inv in st.session_state.financial_data['investments']) + st.session_state.financial_data['savings']):,.2f}</p>
            </div>
            <div class="metric-card">
                <h3>Savings Rate</h3>
                <p>{calculate_savings_metrics(st.session_state.financial_data['income'], st.session_state.financial_data['expenses'])[1]:.1f}%</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # --- Navigation Tabs ---
    tabs = st.tabs([
        "💬 AI Advisor", 
        "📊 Budget Planner", 
        "🎯 Savings Goals", 
        "📈 Investments", 
        "📚 Learning Center"
    ])
    
    # --- AI Chatbot Tab ---
    with tabs[0]:
        st.header("Ask WealthWise AI")
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown("""
            <div class="info-box">
                Get personalized advice on budgeting, investing, retirement planning, and more.
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            if st.button("🎤 Voice Input", help="Use microphone for voice input"):
                st.experimental_rerun()  # Placeholder for voice input implementation
        
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        if prompt := st.chat_input("Ask your financial question..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                response = get_finance_response(prompt)
                st.markdown(response)
            
            st.session_state.messages.append({"role": "assistant", "content": response})

    # --- Budget Planner Tab ---
    with tabs[1]:
        st.header("📊 Smart Budget Planner")
        update_investment_values()
        
        col1, col2 = st.columns([1, 1], gap="large")
        
        with col1:
            with st.container(border=True):
                st.subheader("💰 Real-Time Tracking")
                if st.button("🔗 Connect Bank Account", help="Secure connection using Plaid API"):
                    st.info("Bank connection feature coming soon!")
                
                income = st.number_input("Monthly Income (₹)", 
                    value=st.session_state.financial_data['income'],
                    format="%.2f")
                expenses = st.number_input("Monthly Expenses (₹)", 
                    value=st.session_state.financial_data['expenses'],
                    format="%.2f")
                
                if st.button("Update Budget", type="primary"):
                    st.session_state.financial_data.update({
                        'income': income,
                        'expenses': expenses,
                        'savings': income - expenses
                    })
                    st.toast("Budget updated!", icon="✅")

            with st.container(border=True):
                st.plotly_chart(create_cashflow_diagram(), use_container_width=True)

        with col2:
            with st.container(border=True):
                st.subheader("🗂 Category Breakdown")
                categories = st.session_state.financial_data['budget_categories']
                for cat in categories:
                    categories[cat] = st.slider(f"{cat} (%)", 
                        value=int(categories[cat]/income*100 if income >0 else 0),
                        max_value=100)
                st.session_state.financial_data['budget_categories'] = {
                    k: v/100*income for k,v in categories.items()
                }

    # --- Savings Goals Tab ---
    with tabs[2]:
        st.header("🎯 Smart Savings Goals")
        col1, col2 = st.columns(2)
        
        with col1:
            with st.container(border=True):
                st.subheader("New Goal Setup")
                goal_name = st.text_input("Goal Name")
                goal_target = st.number_input("Target Amount (₹)", min_value=0)
                goal_date = st.date_input("Target Date")
                
                if st.button("➕ Add Goal"):
                    new_goal = {
                        "name": goal_name,
                        "target": goal_target,
                        "saved": 0,
                        "deadline": goal_date.strftime("%Y-%m-%d")
                    }
                    st.session_state.financial_data['goals'].append(new_goal)
        
        with col2:
            for goal in st.session_state.financial_data['goals']:
                with st.container(border=True):
                    forecast = calculate_goal_forecast(goal['target'], goal['saved'], goal['deadline'])
                    st.markdown(f"**{goal['name']}**")
                    cols = st.columns(2)
                    cols[0].metric("Target", f"₹{goal['target']:,.2f}")
                    cols[1].metric("Monthly Needed", f"₹{forecast['required_monthly']:,.2f}")
                    st.progress(forecast['completion_probability']/100)

    # --- Investments Tab ---
    with tabs[3]:
        st.header("📈 Intelligent Investments")
        update_investment_values()
        
        tab1, tab2 = st.tabs(["Portfolio", "Research"])
        
        with tab1:
            st.subheader("Live Portfolio Tracking")
            for inv in st.session_state.financial_data['investments']:
                with st.container(border=True):
                    cols = st.columns([2,1,1,1])
                    cols[0].write(f"**{inv['name']}** ({inv['type']})")
                    cols[1].metric("Invested", f"₹{inv['amount']:,.2f}")
                    cols[2].metric("Current", f"₹{inv['current_value']:,.2f}")
                    cols[3].metric("Return", 
                        f"{(inv['current_value']/inv['amount']-1)*100:.1f}%")
            
            total = sum(inv['current_value'] for inv in st.session_state.financial_data['investments'])
            st.metric("Total Portfolio Value", f"₹{total:,.2f}")

        with tab2:
            st.subheader("Market Research")
            ticker = st.text_input("Enter Stock/ETF Symbol:")
            if ticker:
                data = get_market_data(ticker)
                st.line_chart(data['Close'])

    # --- Learning Center Tab ---
    with tabs[4]:
        st.header("📚 Interactive Learning Hub")
        
        with st.expander("💰 Financial Simulators", expanded=True):
            tab1, tab2 = st.tabs(["Compound Growth", "Debt Payoff"])
            
            with tab1:
                years = st.slider("Investment Horizon (years)", 1, 40, 10)
                monthly = st.number_input("Monthly Contribution (₹)", 1000, 100000, 5000)
                rate = st.slider("Expected Return (%)", 1, 20, 10)
                future_value = monthly * (((1 + rate/100/12)**(years*12) - 1) / (rate/100/12)
                st.metric("Future Value", f"₹{future_value:,.2f}")
            
            with tab2:
                debt = st.number_input("Debt Amount (₹)", 1000, 10000000, 100000)
                interest = st.slider("Interest Rate (%)", 1, 30, 15)
                payment = st.number_input("Monthly Payment (₹)", 1000, 100000, 5000)
                months = -np.log(1 - debt*(interest/100/12)/payment) / np.log(1 + interest/100/12)
                st.metric("Payoff Period", f"{months//12:.0f} years {months%12:.0f} months")

# --- Run the App ---
if __name__ == "__main__":
    main()
    st.markdown("---")
    st.markdown("""
    <div class="footer">
        <p>💰 Wealth management powered by AI | Real-time market data | Predictive analytics</p>
    </div>
    """, unsafe_allow_html=True)
