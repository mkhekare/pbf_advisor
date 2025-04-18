import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from langchain.llms import GooglePalm 
from datetime import datetime, timedelta
import time
import os
import html.parser
import yfinance as yf
import numpy as np
import requests
from bs4 import BeautifulSoup
import random
import json
from streamlit_lottie import st_lottie
import feedparser

# --- App Configuration ---
st.set_page_config(
    page_title="WealthWise AI",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)
import os
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    st.error("API key not found. Please set GOOGLE_API_KEY environment variable")
    st.stop()
    
# --- Load API Key ---
#GOOGLE_API_KEY = secrets["GOOGLE_API_KEY"]
#except (ImportError, KeyError, FileNotFoundError):
    # Fallback to environment variable if secrets not found
 #   GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
  #  if not GOOGLE_API_KEY:
   #     st.error("""
    #        🚫 Google API key not found. Please either:
     #       1. Create a .streamlit/secrets.toml file with your key, or
      #      2. Set it as an environment variable
        #    """)
       # st.stop()

# Configure Gemini API
genai.configure(api_key=GOOGLE_API_KEY)

# Add to app.py
def get_stock_data(ticker):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    return requests.get(url).json()['chart']['result'][0]

# --- Animation Setup ---
def load_lottieurl(url: str):
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return None
        return r.json()
    except:
        return None

lottie_animation = load_lottieurl("https://assets9.lottiefiles.com/packages/lf20_6e0QCr.json")

# --- Enhanced Financial News API ---
def fetch_latest_financial_news():
    """Fetch real-time financial news from multiple sources"""
    news_items = []
    
    # News API sources (using free tier endpoints)
    sources = [
        {"name": "Reuters Business", "url": "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best"},
        {"name": "Bloomberg", "url": "https://news.google.com/rss/search?q=Bloomberg+finance&hl=en-IN&gl=IN&ceid=IN:en"},
        {"name": "Economic Times", "url": "https://economictimes.indiatimes.com/rssfeedstopstories.cms"},
        {"name": "Moneycontrol", "url": "https://www.moneycontrol.com/rss/latestnews.xml"},
        {"name": "Business Standard", "url": "https://www.business-standard.com/rss/latest.rss"},
        {"name": "CNBC", "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html"},
        {"name": "Financial Times", "url": "https://www.ft.com/?format=rss"},
        {"name": "Mint", "url": "https://www.livemint.com/rss/news"},
        {"name": "NDTV Profit", "url": "https://feeds.feedburner.com/ndtvprofit-latest"}
    ]
    
    # Fetch news from each source
    for source in sources:
        try:
            feed = feedparser.parse(source["url"])
            for entry in feed.entries[:10]:  # Get top 10 from each source
                if any(term in entry.title.lower() for term in ["finance", "stock", "market", "economy", "investment"]):
                    news_items.append(f"{source['name']}: {entry.title}")
        except Exception as e:
            st.warning(f"Could not fetch news from {source['name']}: {str(e)}")
            continue
    
    # Add some curated recent headlines if RSS fails (as fallback)
    if len(news_items) < 30:
        recent_headlines = [
            "RBI keeps repo rate unchanged at 6.5% in latest policy meeting",
            "Sensex crosses 75,000 mark for first time, Nifty above 22,700",
            "Gold prices hit record high of ₹74,000 per 10 grams in India",
            "India's GDP growth forecast revised to 7.5% for FY25 by IMF",
            "Rupee strengthens to 82.45 against US dollar",
            "SEBI tightens norms for algo trading to protect retail investors",
            "FPIs invest ₹20,000 crore in Indian equities in April",
            "India's forex reserves rise to $645 billion, near all-time high",
            "Tata Motors reports 18% growth in Q4 EV sales",
            "Reliance Jio announces 5G rollout in 100 more cities",
            "Adani Group stocks recover after Hindenburg report resolution",
            "India's manufacturing PMI rises to 59.1 in April, highest in 3 years",
            "Bitcoin surges past $70,000 amid ETF inflows and halving event",
            "US Fed signals possible rate cuts later this year",
            "Oil prices rise as Middle East tensions escalate",
            "China's economy grows 5.3% in Q1, beats expectations",
            "Nvidia stock hits record high on AI chip demand",
            "Tesla announces new affordable EV models coming in 2025",
            "Apple invests $1 billion in India manufacturing expansion",
            "Microsoft's AI push drives record quarterly revenue",
            "Amazon Web Services announces $10 billion India investment",
            "Google parent Alphabet announces first-ever dividend",
            "Meta reports strong Q1 earnings with 27% revenue growth",
            "India's retail inflation eases to 4.85% in March",
            "GST collections hit record ₹2.1 lakh crore in April",
            "India's unemployment rate falls to 6.7% in Q1 2024",
            "LIC reports 15% growth in premium income for FY24",
            "SBI raises FD interest rates by 50 basis points",
            "HDFC Bank reports 20% growth in net profit for Q4",
            "ICICI Bank announces 1:1 bonus share issue"
        ]
        news_items.extend(recent_headlines)
    
    return random.sample(news_items, min(30, len(news_items)))

# --- News Ticker Display Function ---
def display_news_ticker():
    """Display the scrolling news ticker"""
    st.markdown("""
    <style>
    .news-ticker {
        background: #2c3e50;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        margin-bottom: 1rem;
        overflow: hidden;
        white-space: nowrap;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .news-container {
        display: inline-block;
        padding-left: 100%;
        animation: ticker 30s linear infinite;
    }
    
    .news-item {
        display: inline-block;
        padding-right: 2rem;
        font-size: 0.9rem;
    }
    
    @keyframes ticker {
        0% { transform: translateX(0); }
        100% { transform: translateX(-100%); }
    }
    
    .news-ticker:hover .news-container {
        animation-play-state: paused;
    }
    </style>
    """, unsafe_allow_html=True)

    if 'news_ticker' not in st.session_state:
        st.session_state.news_ticker = fetch_latest_financial_news()

    ticker_html = """
    <div class="news-ticker">
        <div class="news-container">
            {news_items}
        </div>
    </div>
    """.format(
        news_items=''.join([f'<span class="news-item">• {html.escape(news)}</span>' 
                          for news in st.session_state.news_ticker])
    )
    
    st.markdown(ticker_html, unsafe_allow_html=True)

    if st.button("🔄 Refresh News", key="refresh_news"):
        st.session_state.news_ticker = fetch_latest_financial_news()
        st.rerun()

# --- Initialize Session State ---
def initialize_session_state():
    if 'financial_data' not in st.session_state:
        st.session_state.financial_data = {
            'income': 0.0,
            'expenses': 0.0,
            'savings': 0.0,
            'goals': [],
            'transactions': [],
            'budget_categories': {
                'Housing': 0.0,
                'Food': 0.0,
                'Transportation': 0.0,
                'Utilities': 0.0,
                'Healthcare': 0.0,
                'Entertainment': 0.0,
                'Education': 0.0,
                'Savings': 0.0,
                'Investments': 0.0,
                'Debt Repayment': 0.0,
                'Other': 0.0
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

    if 'news_ticker' not in st.session_state:
        st.session_state.news_ticker = fetch_latest_financial_news()

    if 'messages' not in st.session_state:
        st.session_state.messages = []

# --- Helper Functions ---
@st.cache_data(ttl=3600)
def get_market_data(ticker):
    try:
        return yf.Ticker(ticker).history(period="1mo")
    except Exception as e:
        st.warning(f"Error fetching market data: {str(e)}")
        return pd.DataFrame()

def get_finance_response(text_input):
    try:
        model = genai.GenerativeModel("gemini-pro")
        prompt = f'''You are WealthWise AI, an advanced financial advisor. Provide detailed, personalized advice including:
- Contextual chat history: {st.session_state.chat_context[-3:] if st.session_state.chat_context else 'No context'}
- Current financial data: {st.session_state.financial_data}
- Question: {text_input}'''
        
        with st.spinner("🧠 Analyzing your financial query..."):
            response = model.generate_content(prompt)
            if st.session_state.chat_context is not None:
                st.session_state.chat_context.append(response.text)
            return response.text
    except Exception as e:
        return f"❌ Error processing your request: {str(e)}"

def calculate_savings_metrics(income, expenses):
    try:
        savings = float(income) - float(expenses)
        savings_rate = (savings / float(income)) * 100 if income > 0 else 0.0
        return savings, savings_rate
    except Exception as e:
        st.error(f"Error calculating savings metrics: {str(e)}")
        return 0.0, 0.0

def create_cashflow_diagram():
    try:
        income = st.session_state.financial_data['income']
        categories = st.session_state.financial_data['budget_categories']
        
        if income == 0:
            return None
        
        labels = ["Income"] + list(categories.keys())
        source = [0] * len(categories)
        target = list(range(1, len(categories)+1))
        value = [income * (categories[cat]/100) for cat in categories]
        
        fig = go.Figure(go.Sankey(
            node=dict(label=labels, pad=15, thickness=20),
            link=dict(source=source, target=target, value=value),
            orientation="h",
            valueformat=".0f",
            valuesuffix="₹"
        ))
        
        fig.update_layout(
            title_text="Monthly Cash Flow Visualization",
            font=dict(size=12, color="white"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=50, l=0, r=0, b=0),
            height=500
        )
        
        return fig
    except Exception as e:
        st.error(f"Error creating cashflow diagram: {str(e)}")
        return None

def create_savings_gauge(savings_rate):
    """Create a gauge chart for savings rate using plotly.graph_objects"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=savings_rate,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Savings Rate Progress"},
        gauge={
            'axis': {'range': [0, 50]},
            'steps': [
                {'range': [0, 10], 'color': "red"},
                {'range': [10, 20], 'color': "orange"},
                {'range': [20, 50], 'color': "green"}
            ],
            'threshold': {
                'line': {'color': "white", 'width': 4},
                'thickness': 0.75,
                'value': savings_rate
            }
        }
    ))
    
    fig.update_layout(
        margin=dict(t=50, b=10),
        height=300
    )
    
    return fig

def calculate_goal_forecast(target, current, deadline):
    try:
        deadline_date = datetime.strptime(deadline, "%Y-%m-%d")
        months_left = max((deadline_date - datetime.now()).days // 30, 1)
        required_monthly = (target - current) / months_left
        completion_prob = min((current/target)*100 + (100 - (current/target)*100)/months_left, 100)
        return {
            "required_monthly": required_monthly,
            "completion_probability": completion_prob
        }
    except Exception as e:
        st.error(f"Error calculating goal forecast: {str(e)}")
        return {"required_monthly": 0, "completion_probability": 0}

def update_investment_values():
    try:
        for inv in st.session_state.financial_data['investments']:
            if inv['type'] in ["Stocks", "ETF"] and 'ticker' in inv and inv['ticker']:
                data = get_market_data(inv['ticker'])
                if not data.empty and 'Close' in data:
                    inv['current_value'] = data['Close'].iloc[-1] * inv.get('shares', 1)
    except Exception as e:
        st.error(f"Error updating investment values: {str(e)}")

def format_currency(value):
    try:
        return f"₹{value:,.2f}" if isinstance(value, (int, float)) else value
    except Exception as e:
        st.error(f"Error formatting currency: {str(e)}")
        return str(value)

# --- Custom CSS ---
def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except:
        st.markdown('''
        <style>
        /* Main Styles */
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #333;
            background-color: #f5f5f5;
        }
        
        /* Header Styles */
        .header {
            padding: 1rem 0;
            border-bottom: 1px solid #e0e0e0;
            margin-bottom: 1.5rem;
        }
        
        /* Metric Cards */
        .dashboard-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 2rem;
            gap: 1rem;
        }
        
        .metric-card {
            background: white;
            border-radius: 10px;
            padding: 1rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            flex: 1;
            text-align: center;
        }
        
        .metric-card h3 {
            font-size: 1rem;
            color: #666;
            margin: 0 0 0.5rem 0;
        }
        
        .metric-card p {
            font-size: 1.5rem;
            font-weight: bold;
            margin: 0;
            color: #2c3e50;
        }
        
        /* News Ticker */
        .news-ticker {
            background: #2c3e50;
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 5px;
            margin-bottom: 1rem;
            overflow: hidden;
            white-space: nowrap;
        }
        
        .news-container {
            display: inline-block;
            padding-left: 100%;
            animation: ticker 30s linear infinite;
        }
        
        .news-item {
            display: inline-block;
            padding-right: 2rem;
        }
        
        @keyframes ticker {
            0% { transform: translateX(0); }
            100% { transform: translateX(-100%); }
        }
        
        /* Info Box */
        .info-box {
            background: #e3f2fd;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
            border-left: 4px solid #2196f3;
        }
        
        /* Footer */
        .footer {
            margin-top: 2rem;
            padding: 1rem 0;
            text-align: center;
            color: #666;
            font-size: 0.9rem;
        }
        
        /* Responsive Adjustments */
        @media (max-width: 768px) {
            .dashboard-header {
                flex-direction: column;
            }
            
            .news-item {
                font-size: 0.8rem;
            }
        }
        </style>
        ''', unsafe_allow_html=True)

# --- Main App ---
def main():
    initialize_session_state()
    local_css("style.css")
    
    # --- Enhanced News Ticker ---
    display_news_ticker()
    
    # --- Header Section ---
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("""
        <div class="header">
            <h1 style="color:#2c3e50;">WealthWise AI</h1>
            <p class="subtitle" style="color:#666;">Your Intelligent Personal Finance Ecosystem</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        if lottie_animation:
            st_lottie(lottie_animation, height=100, key="header-animation")
    
    # Calculate metrics
    update_investment_values()
    total_investments = sum(inv.get('current_value', inv.get('amount', 0)) 
                         for inv in st.session_state.financial_data['investments'])
    
    savings, savings_rate = calculate_savings_metrics(
        st.session_state.financial_data['income'],
        st.session_state.financial_data['expenses']
    )
    
    # Calculate investment growth percentage
    investment_growth = 0.0
    total_invested = sum(inv.get('amount', 0) for inv in st.session_state.financial_data['investments'])
    if total_invested > 0:
        investment_growth = ((total_investments - total_invested) / total_invested) * 100

    # --- Dashboard Metrics ---
    st.markdown(f"""
    <div class="dashboard-header">
        <div class="metric-card">
            <h3>Net Worth</h3>
            <p>{format_currency(total_investments + st.session_state.financial_data['savings'])}</p>
        </div>
        <div class="metric-card">
            <h3>Savings Rate</h3>
            <p>{savings_rate:.1f}%</p>
        </div>
        <div class="metric-card">
            <h3>Investment Growth</h3>
            <p>{investment_growth:.1f}%</p>
        </div>
        <div class="metric-card">
            <h3>Monthly Cashflow</h3>
            <p>{format_currency(savings)}</p>
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
        st.header("🤖 AI Financial Advisor")
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown("""
            <div class="info-box">
                <strong>Pro Tip:</strong> Ask about budgeting strategies, investment options, or retirement planning. 
                Try "How should I allocate my salary?" or "Best SIP plans for 2024"
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            if st.button("🔄 Refresh News", help="Update financial news ticker"):
                st.session_state.news_ticker = fetch_latest_financial_news()
                st.rerun()
        
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
        
        col1, col2 = st.columns([1, 1], gap="large")
        
        with col1:
            with st.container(border=True):
                st.subheader("💰 Income & Expenses")
                
                income = st.number_input("Monthly Income (₹)", 
                    min_value=0.0,
                    value=float(st.session_state.financial_data['income']),
                    step=1000.0,
                    format="%.2f",
                    key="income_input"
                )
                
                expenses = st.number_input("Monthly Expenses (₹)", 
                    min_value=0.0,
                    value=float(st.session_state.financial_data['expenses']),
                    step=1000.0,
                    format="%.2f",
                    key="expenses_input"
                )
                
                if st.button("Update Budget", type="primary", use_container_width=True):
                    st.session_state.financial_data.update({
                        'income': income,
                        'expenses': expenses,
                        'savings': income - expenses
                    })
                    st.toast("Budget updated successfully!", icon="✅")
                    st.session_state.achievements['budget_set'] = True
            
            with st.container(border=True):
                st.subheader("📈 Savings Overview")
                savings, savings_rate = calculate_savings_metrics(
                    st.session_state.financial_data['income'],
                    st.session_state.financial_data['expenses']
                )
                
                cols = st.columns(2)
                cols[0].metric("Monthly Savings", format_currency(savings))
                cols[1].metric("Savings Rate", f"{savings_rate:.1f}%")
                
                # Visual gauge for savings rate
                gauge = create_savings_gauge(savings_rate)
                st.plotly_chart(gauge, use_container_width=True)

        with col2:
            with st.container(border=True):
                st.subheader("🗂 Budget Allocation")
                
                categories = st.session_state.financial_data['budget_categories']
                total_percent = 0
                
                cols = st.columns(3)
                for i, category in enumerate(categories):
                    with cols[i % 3]:
                        percent = st.slider(
                            f"{category} (%)",
                            min_value=0,
                            max_value=100,
                            value=int(categories[category]/st.session_state.financial_data['income']*100 
                                   if st.session_state.financial_data['income'] > 0 else 0),
                            key=f"budget_{category}"
                        )
                        categories[category] = percent
                        total_percent += percent
                
                if total_percent > 100:
                    st.error(f"Total allocation exceeds 100% (currently {total_percent}%)")
                else:
                    st.session_state.financial_data['budget_categories'] = {
                        k: v/100*st.session_state.financial_data['income'] 
                        for k, v in categories.items()
                    }
                    st.success(f"Allocation: {total_percent}%")
            
            # Cash Flow Visualization
            cashflow_chart = create_cashflow_diagram()
            if cashflow_chart:
                st.plotly_chart(cashflow_chart, use_container_width=True)
            else:
                st.warning("Enter your income to see cash flow visualization")

    # --- Savings Goals Tab ---
    with tabs[2]:
        st.header("🎯 Smart Savings Goals")
        
        col1, col2 = st.columns([1, 1], gap="large")
        
        with col1:
            with st.container(border=True):
                st.subheader("➕ New Goal")
                goal_name = st.text_input("Goal Name", key="goal_name")
                goal_amount = st.number_input("Target Amount (₹)", 
                    min_value=0.0, 
                    value=10000.0,
                    format="%.2f",
                    key="goal_amount"
                )
                goal_deadline = st.date_input("Target Date", 
                    min_value=datetime.now().date(),
                    value=datetime.now().date() + timedelta(days=180),
                    key="goal_deadline"
                )
                
                if st.button("Add Goal", use_container_width=True):
                    if goal_name and goal_amount > 0:
                        new_goal = {
                            "name": goal_name,
                            "target": goal_amount,
                            "deadline": goal_deadline.strftime("%Y-%m-%d"),
                            "saved": 0.0,
                            "created": datetime.now().strftime("%Y-%m-%d")
                        }
                        st.session_state.financial_data['goals'].append(new_goal)
                        st.session_state.achievements['savings_goal'] = True
                        st.toast(f"Goal '{goal_name}' added successfully!", icon="✅")
                        st.rerun()
        
        with col2:
            st.subheader("🏆 Your Goals")
            if not st.session_state.financial_data['goals']:
                st.info("No savings goals yet. Add your first goal!")
            else:
                for i, goal in enumerate(st.session_state.financial_data['goals']):
                    with st.container(border=True):
                        forecast = calculate_goal_forecast(
                            goal['target'],
                            goal['saved'],
                            goal['deadline']
                        )
                        
                        cols = st.columns([3, 1])
                        with cols[0]:
                            st.markdown(f"### {goal['name']}")
                            st.caption(f"Target: {format_currency(goal['target'])} by {goal['deadline']}")
                            
                            progress = goal['saved'] / goal['target'] if goal['target'] > 0 else 0
                            st.progress(
                                min(progress, 1.0), 
                                text=f"{progress*100:.1f}% completed"
                            )
                        
                        with cols[1]:
                            deposit = st.number_input(
                                "Add amount", 
                                min_value=0.0,
                                value=0.0,
                                step=100.0,
                                format="%.2f",
                                key=f"deposit_{i}",
                                label_visibility="collapsed"
                            )
                            if st.button("Add", key=f"add_{i}", use_container_width=True):
                                if deposit > 0:
                                    st.session_state.financial_data['goals'][i]['saved'] += deposit
                                    st.toast(f"Added {format_currency(deposit)} to {goal['name']}", icon="✅")
                                    st.rerun()
                        
                        cols = st.columns(2)
                        cols[0].metric(
                            "Monthly Needed", 
                            format_currency(forecast['required_monthly'])
                        )
                        cols[1].metric(
                            "Success Probability", 
                            f"{forecast['completion_probability']:.1f}%"
                        )

    # --- Investments Tab ---
    with tabs[3]:
        st.header("📈 Intelligent Investments")
        
        tab_invest, tab_research = st.tabs(["Your Portfolio", "Market Research"])
        
        with tab_invest:
            st.subheader("💼 Investment Portfolio")
            
            with st.form("investment_form", clear_on_submit=True):
                cols = st.columns([2, 1, 1])
                
                with cols[0]:
                    inv_type = st.selectbox("Type", [
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
                    inv_name = st.text_input("Name/Description")
                
                with cols[1]:
                    inv_amount = st.number_input("Amount (₹)", 
                        min_value=0.0,
                        value=10000.0,
                        format="%.2f"
                    )
                    inv_date = st.date_input("Date", 
                        value=datetime.now().date()
                    )
                
                with cols[2]:
                    if inv_type in ["Stocks", "ETF"]:
                        inv_ticker = st.text_input("Ticker Symbol (e.g., RELIANCE.NS)")
                    else:
                        inv_ticker = ""
                    
                    inv_notes = st.text_area("Notes")
                
                if st.form_submit_button("Add Investment", type="primary"):
                    new_investment = {
                        "type": inv_type,
                        "name": inv_name,
                        "amount": inv_amount,
                        "date": inv_date.strftime("%Y-%m-%d"),
                        "current_value": inv_amount,
                        "ticker": inv_ticker if inv_type in ["Stocks", "ETF"] else "",
                        "notes": inv_notes
                    }
                    st.session_state.financial_data['investments'].append(new_investment)
                    st.session_state.achievements['first_investment'] = True
                    st.toast("Investment added to portfolio!", icon="✅")
                    st.rerun()
            
            if st.session_state.financial_data['investments']:
                st.subheader("📊 Portfolio Performance")
                
                # Calculate metrics
                total_invested = sum(inv.get('amount', 0) for inv in st.session_state.financial_data['investments'])
                total_current = sum(inv.get('current_value', inv.get('amount', 0)) 
                                 for inv in st.session_state.financial_data['investments'])
                overall_return = ((total_current - total_invested) / total_invested * 100) if total_invested > 0 else 0

                # Display metrics
                cols = st.columns(3)
                cols[0].metric("Total Invested", format_currency(total_invested))
                cols[1].metric("Current Value", format_currency(total_current))
                cols[2].metric("Overall Return", f"{overall_return:.2f}%")
                
                # Display investments in a nice dataframe
                inv_df = pd.DataFrame(st.session_state.financial_data['investments'])
                inv_df['Return'] = (inv_df['current_value'] - inv_df['amount']) / inv_df['amount'] * 100
                
                st.dataframe(
                    inv_df.style.format({
                        'amount': '{:,.2f}',
                        'current_value': '{:,.2f}',
                        'Return': '{:.2f}%'
                    }),
                    column_order=["type", "name", "amount", "current_value", "Return", "date"],
                    column_config={
                        "type": "Type",
                        "name": "Name",
                        "amount": st.column_config.NumberColumn("Invested (₹)", format="%.2f"),
                        "current_value": st.column_config.NumberColumn("Current (₹)", format="%.2f"),
                        "Return": st.column_config.NumberColumn("Return %", format="%.2f"),
                        "date": "Date"
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No investments tracked yet. Add your first investment above!")
        
        with tab_research:
            st.subheader("🔍 Market Research")
            
            research_option = st.radio("Research Type", 
                ["Stock Analysis", "Mutual Funds", "Fixed Deposits", "Gold/Silver"],
                horizontal=True
            )
            
            if research_option == "Stock Analysis":
                ticker = st.text_input("Enter Stock/ETF Symbol (e.g., TCS.NS, ^NSEI)", "RELIANCE.NS")
                
                if ticker:
                    try:
                        data = get_market_data(ticker)
                        if not data.empty:
                            st.subheader(f"{ticker} Performance")
                            
                            cols = st.columns([3, 1])
                            with cols[0]:
                                st.line_chart(data['Close'])
                            
                            with cols[1]:
                                current_price = data['Close'].iloc[-1]
                                prev_close = data['Close'].iloc[-2] if len(data) > 1 else current_price
                                change = (current_price - prev_close) / prev_close * 100
                                
                                st.metric("Current Price", 
                                    f"₹{current_price:,.2f}", 
                                    f"{change:.2f}%"
                                )
                                
                                st.metric("52 Week Range", 
                                    f"₹{data['Close'].min():,.2f} - ₹{data['Close'].max():,.2f}"
                                )
                                
                                st.metric("Volume", 
                                    f"{data['Volume'].iloc[-1]:,.0f}"
                                )
                        else:
                            st.warning("No data found for this ticker")
                    except Exception as e:
                        st.error(f"Error fetching data: {str(e)}")

    # --- Learning Center Tab ---
    with tabs[4]:
        st.header("📚 Financial Learning Hub")
        
        with st.expander("💰 Financial Calculators", expanded=True):
            calc_type = st.selectbox("Select Calculator", 
                ["SIP Calculator", "EMI Calculator", "Retirement Planner", "Education Fund Planner"]
            )
            
            if calc_type == "SIP Calculator":
                years = st.slider("Investment Period (years)", 1, 40, 10)
                monthly = st.number_input("Monthly Investment (₹)", 1000, 1000000, 5000)
                rate = st.slider("Expected Annual Return (%)", 1, 30, 12)
                
                future_value = monthly * (((1 + rate/100/12)**(years*12) - 1) / (rate/100/12)) * (1 + rate/100/12)
                st.metric("Estimated Future Value", format_currency(future_value))
                
                # Visualization
                growth_data = pd.DataFrame({
                    'Year': range(1, years+1),
                    'Value': [monthly * (((1 + rate/100/12)**(y*12) - 1) / (rate/100/12)) * (1 + rate/100/12) for y in range(1, years+1)]
                })
                st.line_chart(growth_data.set_index('Year'))
            
            elif calc_type == "EMI Calculator":
                principal = st.number_input("Loan Amount (₹)", 1000, 10000000, 1000000)
                interest = st.slider("Interest Rate (% p.a.)", 1, 30, 10)
                tenure = st.slider("Loan Tenure (years)", 1, 30, 10)
                
                monthly_rate = interest / 12 / 100
                months = tenure * 12
                emi = principal * monthly_rate * ((1 + monthly_rate)**months) / (((1 + monthly_rate)**months) - 1)
                
                cols = st.columns(3)
                cols[0].metric("Monthly EMI", format_currency(emi))
                cols[1].metric("Total Interest", format_currency(emi * months - principal))
                cols[2].metric("Total Payment", format_currency(emi * months))
                
                # Amortization schedule
                schedule = []
                balance = principal
                for month in range(1, months + 1):
                    interest_payment = balance * monthly_rate
                    principal_payment = emi - interest_payment
                    balance -= principal_payment
                    schedule.append({
                        'Month': month,
                        'EMI': emi,
                        'Principal': principal_payment,
                        'Interest': interest_payment,
                        'Balance': max(balance, 0)
                    })
                
                st.line_chart(pd.DataFrame(schedule).set_index('Month')[['Principal', 'Interest']])
        
        with st.expander("🎓 Financial Education", expanded=False):
            topic = st.selectbox("Learn About", [
                "Budgeting Basics",
                "Investing 101",
                "Tax Planning",
                "Retirement Strategies",
                "Debt Management"
            ])
            
            if topic == "Budgeting Basics":
                st.markdown("""
                ### The 50/30/20 Rule
                - **50% Needs**: Essential expenses
                    - Housing (rent/mortgage)
                    - Groceries
                    - Utilities
                    - Transportation
                    - Minimum debt payments
                
                - **30% Wants**: Lifestyle choices
                    - Dining out
                    - Entertainment
                    - Travel
                    - Hobbies
                
                - **20% Savings**: Financial goals
                    - Emergency fund
                    - Retirement
                    - Investments
                    - Extra debt payments
                """)
            
            elif topic == "Investing 101":
                st.markdown("""
                ### Investment Options in India
                **1. Fixed Income:**
                - Fixed Deposits (5-7% returns)
                - PPF (7.1% interest)
                - Senior Citizen Savings Scheme (8.2%)
                
                **2. Market-Linked:**
                - Mutual Funds (Equity: 12-15%, Debt: 7-9%)
                - Direct Stocks (High risk, high reward)
                - ETFs (Nifty 50, Sectoral)
                
                **3. Alternative:**
                - Gold (Sovereign Gold Bonds)
                - Real Estate
                - REITs
                """)

# --- Run the App ---
if __name__ == "__main__":
    try:
        main()
        
        # --- Footer ---
        st.markdown("---")
        st.markdown(f"""
        <div class="footer">
            <p>💰 WealthWise AI • Real-time Financial Insights • Personalized Recommendations</p>
            <p>Data updates every 15 minutes • Last refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        </div>
        """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.stop()
