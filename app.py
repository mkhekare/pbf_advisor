import streamlit as st
from dotenv import load_dotenv
import os
import pandas as pd
import plotly.express as px
import google.generativeai as genai
from datetime import datetime
import time
from streamlit_authenticator import Authenticate
import yaml
from yaml.loader import SafeLoader

# --- App Configuration ---
st.set_page_config(
    page_title="WealthWise AI",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Load API Key ---
load_dotenv()  # Load .env if exists (for local dev)
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY"))

if not GOOGLE_API_KEY:
    st.error("🚫 Google API key not found. Please set it in .env or Streamlit secrets.")
    st.stop()

# Configure Gemini API
genai.configure(api_key=GOOGLE_API_KEY)

# --- Authentication ---
with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
    config['preauthorized']
)

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
        }
    }

# --- Helper Functions ---
def get_finance_response(text_input):
    try:
        model = genai.GenerativeModel("gemini-1.5-pro")
        prompt = '''You are WealthWise AI, an advanced financial advisor. Provide detailed, personalized advice on:
- Budgeting strategies and optimization
- Saving techniques and emergency funds
- Investment options (FDs, SIPs, Mutual Funds, Stocks, ETFs)
- Retirement planning (NPS, PPF, Pension plans)
- Tax planning and optimization
- Debt management and credit scores
- Financial goal planning (short-term and long-term)
- Insurance planning (term, health, life)

Format responses with clear headings, bullet points, and actionable steps. Use markdown for better readability.

If the question is outside personal finance, politely respond:
"I specialize in personal finance. How about we discuss budgeting, investing, or financial planning instead?"

For stock tips:
"I can provide general market education but cannot give specific recommendations. For personalized advice, consult a SEBI-registered advisor."

Current date: ''' + datetime.now().strftime("%Y-%m-%d") + "\n\nQuestion: " + text_input
        
        with st.spinner("🧠 Analyzing your financial query..."):
            response = model.generate_content(prompt)
            return response.text
    except Exception as e:
        return f"❌ Error processing your request: {str(e)}"

def calculate_savings_metrics(income, expenses):
    savings = income - expenses
    savings_rate = (savings / income) * 100 if income > 0 else 0
    return savings, savings_rate

def create_budget_chart(budget_data):
    df = pd.DataFrame.from_dict(budget_data, orient='index', columns=['Amount'])
    df = df.reset_index().rename(columns={'index': 'Category'})
    df = df[df['Amount'] > 0]
    
    if not df.empty:
        fig = px.pie(df, values='Amount', names='Category', 
                    title='Budget Allocation', hole=0.3,
                    color_discrete_sequence=px.colors.sequential.Agsunset)
        fig.update_traces(textposition='inside', textinfo='percent+label')
        return fig
    return None

# --- UI Components ---
def main_app():
    # --- Main Header ---
    col1, col2 = st.columns([1, 3])
    with col1:
        st.image("https://via.placeholder.com/150x150?text=WealthWise", width=150)
    with col2:
        st.title("WealthWise AI")
        st.subheader("Your Intelligent Personal Finance Assistant", divider="rainbow")
    
    # --- Navigation ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "💬 AI Advisor", 
        "📊 Budget Planner", 
        "🎯 Savings Goals", 
        "📈 Investments", 
        "📚 Learning Center"
    ])
    
    # --- AI Chatbot Tab ---
    with tab1:
        st.header("Ask WealthWise AI")
        st.write("Get personalized advice on budgeting, investing, retirement planning, and more.")
        
        chat_container = st.container(height=400)
        
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        for message in st.session_state.messages:
            with chat_container.chat_message(message["role"]):
                st.markdown(message["content"])
        
        if prompt := st.chat_input("Ask your financial question..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_container.chat_message("user"):
                st.markdown(prompt)
            
            with chat_container.chat_message("assistant"):
                response = get_finance_response(prompt)
                st.markdown(response)
            
            st.session_state.messages.append({"role": "assistant", "content": response})
    
    # --- Budget Planner Tab ---
    with tab2:
        st.header("Personal Budget Planner")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Income & Expenses")
            with st.form("income_form"):
                income = st.number_input("Monthly Income (₹)", min_value=0.0, value=st.session_state.financial_data['income'])
                expenses = st.number_input("Monthly Expenses (₹)", min_value=0.0, value=st.session_state.financial_data['expenses'])
                
                if st.form_submit_button("Update Budget"):
                    st.session_state.financial_data['income'] = income
                    st.session_state.financial_data['expenses'] = expenses
                    savings, savings_rate = calculate_savings_metrics(income, expenses)
                    st.session_state.financial_data['savings'] = savings
                    st.success("Budget updated successfully!")
                    time.sleep(1)
                    st.rerun()
            
            savings, savings_rate = calculate_savings_metrics(
                st.session_state.financial_data['income'],
                st.session_state.financial_data['expenses']
            )
            
            st.metric("Monthly Savings", f"₹{savings:,.2f}")
            st.metric("Savings Rate", f"{savings_rate:.2f}%")
            
            rule_503020 = {
                "Needs (50%)": st.session_state.financial_data['income'] * 0.5,
                "Wants (30%)": st.session_state.financial_data['income'] * 0.3,
                "Savings (20%)": st.session_state.financial_data['income'] * 0.2
            }
            
            st.subheader("50/30/20 Rule Allocation")
            st.dataframe(pd.DataFrame.from_dict(rule_503020, orient='index', columns=['Amount']).style.format('₹{:,}'))
        
        with col2:
            st.subheader("Budget Categories")
            with st.expander("Customize Budget Categories"):
                for category in st.session_state.financial_data['budget_categories']:
                    st.session_state.financial_data['budget_categories'][category] = st.number_input(
                        f"{category} (₹)",
                        min_value=0.0,
                        value=st.session_state.financial_data['budget_categories'][category],
                        key=f"budget_{category}"
                    )
            
            st.subheader("Budget Visualization")
            budget_chart = create_budget_chart(st.session_state.financial_data['budget_categories'])
            if budget_chart:
                st.plotly_chart(budget_chart, use_container_width=True)
            else:
                st.warning("No budget data to display. Please add budget amounts.")
    
    # --- Savings Goals Tab ---
    with tab3:
        st.header("Savings Goals Tracker")
        
        col1, col2 = st.columns(2)
        
        with col1:
            with st.form("goal_form"):
                st.subheader("Add New Goal")
                goal_name = st.text_input("Goal Name")
                goal_amount = st.number_input("Target Amount (₹)", min_value=0.0)
                goal_deadline = st.date_input("Target Date")
                
                if st.form_submit_button("Add Goal"):
                    if goal_name and goal_amount > 0:
                        new_goal = {
                            "name": goal_name,
                            "target": goal_amount,
                            "deadline": goal_deadline.strftime("%Y-%m-%d"),
                            "saved": 0,
                            "created": datetime.now().strftime("%Y-%m-%d")
                        }
                        st.session_state.financial_data['goals'].append(new_goal)
                        st.success("Goal added successfully!")
                        time.sleep(1)
                        st.rerun()
        
        with col2:
            st.subheader("Your Goals")
            if not st.session_state.financial_data['goals']:
                st.info("No savings goals yet. Add your first goal above!")
            else:
                for i, goal in enumerate(st.session_state.financial_data['goals']):
                    with st.expander(f"{goal['name']} - ₹{goal['target']:,.2f}"):
                        progress = goal['saved'] / goal['target'] if goal['target'] > 0 else 0
                        st.progress(min(progress, 1.0))
                        st.write(f"Saved: ₹{goal['saved']:,.2f} of ₹{goal['target']:,.2f}")
                        st.write(f"Target Date: {goal['deadline']}")
                        
                        deposit = st.number_input(f"Add to {goal['name']} (₹)", min_value=0.0, key=f"deposit_{i}")
                        if st.button("Add to Goal", key=f"add_{i}"):
                            if deposit > 0:
                                st.session_state.financial_data['goals'][i]['saved'] += deposit
                                st.success(f"Added ₹{deposit:,.2f} to {goal['name']}")
                                time.sleep(1)
                                st.rerun()
    
    # --- Investments Tab ---
    with tab4:
        st.header("Investment Portfolio")
        
        tab_invest, tab_learn = st.tabs(["Your Portfolio", "Investment Guide"])
        
        with tab_invest:
            st.subheader("Track Your Investments")
            
            with st.form("investment_form"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    inv_type = st.selectbox("Investment Type", [
                        "Fixed Deposit",
                        "Mutual Fund",
                        "Stocks",
                        "ETF",
                        "PPF",
                        "NPS",
                        "Gold",
                        "Real Estate",
                        "Other"
                    ])
                    inv_name = st.text_input("Investment Name")
                
                with col2:
                    inv_amount = st.number_input("Amount Invested (₹)", min_value=0.0)
                    inv_date = st.date_input("Investment Date")
                
                with col3:
                    inv_return = st.number_input("Current Value (₹)", min_value=0.0, value=inv_amount)
                    inv_notes = st.text_area("Notes")
                
                if st.form_submit_button("Add Investment"):
                    new_investment = {
                        "type": inv_type,
                        "name": inv_name,
                        "amount": inv_amount,
                        "date": inv_date.strftime("%Y-%m-%d"),
                        "current_value": inv_return,
                        "notes": inv_notes
                    }
                    if "investments" not in st.session_state.financial_data:
                        st.session_state.financial_data['investments'] = []
                    st.session_state.financial_data['investments'].append(new_investment)
                    st.success("Investment added to portfolio!")
                    time.sleep(1)
                    st.rerun()
            
            if "investments" in st.session_state.financial_data and st.session_state.financial_data['investments']:
                st.subheader("Your Investments")
                inv_df = pd.DataFrame(st.session_state.financial_data['investments'])
                st.dataframe(inv_df.style.format({
                    'amount': '₹{:,}',
                    'current_value': '₹{:,}'
                }), use_container_width=True)
                
                # Calculate overall performance
                total_invested = sum(inv['amount'] for inv in st.session_state.financial_data['investments'])
                total_current = sum(inv['current_value'] for inv in st.session_state.financial_data['investments'])
                overall_return = ((total_current - total_invested) / total_invested * 100) if total_invested > 0 else 0
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Invested", f"₹{total_invested:,.2f}")
                col2.metric("Current Value", f"₹{total_current:,.2f}")
                col3.metric("Overall Return", f"{overall_return:.2f}%")
            else:
                st.info("No investments tracked yet. Add your first investment above!")
        
        with tab_learn:
            st.subheader("Investment Education")
            st.write("Learn about different investment options:")
            
            invest_options = {
                "Fixed Deposits": {
                    "description": "Low-risk, fixed returns with guaranteed principal",
                    "risk": "Low",
                    "returns": "4-7% p.a.",
                    "liquidity": "Low (lock-in period)",
                    "tax": "Taxable as per income slab"
                },
                "Mutual Funds": {
                    "description": "Professional managed funds investing in stocks/bonds",
                    "risk": "Low to High",
                    "returns": "8-15% p.a.",
                    "liquidity": "High (except ELSS)",
                    "tax": "STCG: 15%, LTCG: 10% over ₹1L"
                },
                "Stocks": {
                    "description": "Direct ownership in companies",
                    "risk": "High",
                    "returns": "Variable",
                    "liquidity": "High",
                    "tax": "STCG: 15%, LTCG: 10% over ₹1L"
                },
                "PPF": {
                    "description": "Government-backed long-term savings",
                    "risk": "Low",
                    "returns": "7-8% p.a.",
                    "liquidity": "Low (15-year lock-in)",
                    "tax": "Tax-free"
                }
            }
            
            selected_investment = st.selectbox("Learn about:", list(invest_options.keys()))
            
            st.subheader(selected_investment)
            st.table(pd.DataFrame.from_dict(invest_options[selected_investment], orient='index'))
    
    # --- Learning Center Tab ---
    with tab5:
        st.header("Financial Learning Center")
        
        st.subheader("Educational Resources")
        
        with st.expander("📖 Budgeting Basics"):
            st.markdown("""
            ### The 50/30/20 Budget Rule
            - **50% Needs**: Essential expenses you must pay
                - Rent/Mortgage
                - Groceries
                - Utilities
                - Transportation
                - Minimum debt payments
            
            - **30% Wants**: Non-essential spending
                - Dining out
                - Entertainment
                - Hobbies
                - Vacations
            
            - **20% Savings**: Financial goals
                - Emergency fund
                - Retirement
                - Investments
                - Debt repayment beyond minimums
            """)
        
        with st.expander("📈 Investment Strategies"):
            st.markdown("""
            ### Smart Investment Principles
            1. **Start Early**: Benefit from compounding
            2. **Diversify**: Spread across asset classes
            3. **Risk Assessment**: Match investments to your risk tolerance
            4. **Regular Investing**: SIP approach beats timing the market
            5. **Long-Term Focus**: Avoid reactionary decisions
            
            ### Suggested Allocation by Age
            | Age | Equity | Debt | Gold | Cash |
            |-----|--------|------|------|------|
            | 20s | 70-80% | 10-20% | 5-10% | 5% |
            | 30s | 60-70% | 20-30% | 5-10% | 5% |
            | 40s | 50-60% | 30-40% | 5-10% | 5% |
            | 50+ | 40-50% | 40-50% | 5-10% | 5-10% |
            """)
        
        with st.expander("🛡️ Emergency Fund Guide"):
            st.markdown("""
            ### Building Your Financial Safety Net
            - **How Much?** 3-6 months of living expenses
            - **Where to Keep?** Liquid, low-risk options:
                - Savings account
                - Liquid mutual funds
                - Short-term FDs with easy withdrawal
            
            ### Emergency Fund Calculator
            """)
            
            months_expenses = st.number_input("Your monthly essential expenses (₹):", min_value=0)
            if months_expenses > 0:
                recommended = months_expenses * 6
                st.metric("Recommended Emergency Fund", f"₹{recommended:,.2f}")
        
        st.subheader("Financial Calculators")
        
        col1, col2 = st.columns(2)
        
        with col1:
            with st.expander("💸 SIP Calculator"):
                monthly_inv = st.number_input("Monthly Investment (₹):", min_value=0, value=5000)
                years = st.slider("Investment Period (years):", 1, 30, 10)
                rate = st.slider("Expected Return (% p.a.):", 1, 20, 12)
                
                if st.button("Calculate SIP Growth"):
                    months = years * 12
                    monthly_rate = rate / 12 / 100
                    future_value = monthly_inv * (((1 + monthly_rate)**months - 1) / monthly_rate) * (1 + monthly_rate)
                    st.metric("Estimated Future Value", f"₹{future_value:,.2f}")
        
        with col2:
            with st.expander("🔄 Debt Payoff Calculator"):
                debt_amount = st.number_input("Total Debt (₹):", min_value=0, value=100000)
                interest_rate = st.slider("Interest Rate (% p.a.):", 1, 30, 12)
                monthly_payment = st.number_input("Monthly Payment (₹):", min_value=0, value=5000)
                
                if st.button("Calculate Payoff Plan"):
                    monthly_rate = interest_rate / 12 / 100
                    if monthly_payment <= debt_amount * monthly_rate:
                        st.error("Payment too low! You'll never pay off at this rate.")
                    else:
                        months = 0
                        remaining = debt_amount
                        while remaining > 0:
                            interest = remaining * monthly_rate
                            principal = monthly_payment - interest
                            remaining -= principal
                            months += 1
                        
                        st.metric("Time to Payoff", f"{months//12} years {months%12} months")
                        st.metric("Total Interest Paid", f"₹{(monthly_payment * months - debt_amount):,.2f}")

# --- Login Page ---
def login_page():
    st.title("WealthWise AI")
    st.subheader("Your Intelligent Personal Finance Assistant")
    
    name, authentication_status, username = authenticator.login('Login', 'main')
    
    if authentication_status:
        authenticator.logout('Logout', 'main')
        st.success(f'Welcome *{name}*')
        main_app()
    elif authentication_status is False:
        st.error('Username/password is incorrect')
    elif authentication_status is None:
        st.warning('Please enter your username and password')

# --- App Entry Point ---
if __name__ == "__main__":
    login_page()

# --- Footer ---
st.markdown("---")
st.markdown("""
**Disclaimer**: This application provides general financial information and should not be considered professional advice. 
Consult a certified financial advisor before making investment decisions. Past performance is not indicative of future results.
""")
