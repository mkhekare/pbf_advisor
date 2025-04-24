# app.py
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf
import requests
import feedparser
from bs4 import BeautifulSoup
import html
import streamlit as st
from streamlit_chat import message as st_message
import google.generativeai as genai

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Constants ---
DEFAULT_INCOME = 100000.0
DEFAULT_EXPENSES = 70000.0
DEFAULT_SAVINGS = 30000.0
DEFAULT_ASSETS = {
    'savings_account': 200000.0,
    'investments': 300000.0,
    'property': 5000000.0,
    'vehicles': 500000.0
}
DEFAULT_LIABILITIES = {
    'education_loan': 2500000.0,
    'car_loan': 300000.0,
    'credit_cards': 50000.0
}

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    API_ENABLED = True
else:
    API_ENABLED = False
    logger.warning("Gemini API key not found - running in limited mode")

# Financial Biases
FINANCIAL_BIASES = """
When providing financial advice, consider these cognitive biases:
1. Overconfidence Bias: Investors overestimate their knowledge.
2. Anchoring Bias: Initial information anchors decisions.
3. Herding Behavior: Following the crowd.
4. Loss Aversion: Fear of losses leads to conservative decisions.
5. Confirmation Bias: Seeking confirming information.
6. Recency Bias: Overweighting recent events.
7. Framing Effect: Decisions influenced by presentation.
8. Mental Accounting: Treating money differently.
9. Status Quo Bias: Preference for current situation.
10. Disposition Effect: Selling winners, holding losers.
"""

# Behavioral Finance Info
BEHAVIORAL_FINANCE_INFO = """
### Why Personal & Behavioral Finance Matters

1. **Mind Over Money**  
   Your psychology affects every financial decision more than market knowledge.

2. **The 50-30-20 Rule**  
   - 50% Needs (rent, groceries)  
   - 30% Wants (entertainment)  
   - 20% Savings/Investments

3. **Common Pitfalls**  
   - Emotional spending  
   - Procrastinating savings  
   - Chasing past performance  
   - Overconfidence in stock picking

4. **Better Habits**  
   - Automate savings  
   - Set specific goals  
   - Review finances weekly  
   - Diversify investments
"""

class GeminiClient:
    def generate(self, prompt: str) -> str:
        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 1000,
                    "top_p": 0.9
                },
                safety_settings={
                    'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                    'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                    'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                    'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE'
                }
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return f"⚠️ Gemini Error: {str(e)}"

    def generate_with_web_search(self, prompt: str) -> str:
        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 1000,
                    "top_p": 0.9
                },
                safety_settings={
                    'HARM_CATEGORY_HARASSMENT': 'BLOCK_NONE',
                    'HARM_CATEGORY_HATE_SPEECH': 'BLOCK_NONE',
                    'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'BLOCK_NONE',
                    'HARM_CATEGORY_DANGEROUS_CONTENT': 'BLOCK_NONE'
                },
                tools=[{
                    "web_search": {
                        "enable": True,
                        "search_query": prompt[:100]  # Use first 100 chars as search query
                    }
                }]
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API with web search error: {str(e)}")
            return self.generate(prompt)  # Fallback to regular generation

# Initialize client
gemini = GeminiClient() if API_ENABLED else None

# --- Session State ---
class SessionState:
    def __init__(self):
        self._initialize_default_data()
        self.chat_history = []
        self.news_cache = None
        self.news_cache_time = 0
        self.market_data_cache = {}
        
    def _initialize_default_data(self):
        """Initialize with default financial data"""
        now = datetime.now()
        self.financial_data = {
            'income': DEFAULT_INCOME,
            'expenses': DEFAULT_EXPENSES,
            'savings': DEFAULT_SAVINGS,
            'assets': DEFAULT_ASSETS.copy(),
            'liabilities': DEFAULT_LIABILITIES.copy(),
            'goals': [
                {
                    "name": "Emergency Fund",
                    "target": 500000.0,
                    "deadline": (now + timedelta(days=365)).strftime("%Y-%m-%d"),
                    "saved": 100000.0,
                    "created": now.strftime("%Y-%m-%d")
                },
                {
                    "name": "Vacation Fund",
                    "target": 200000.0,
                    "deadline": (now + timedelta(days=180)).strftime("%Y-%m-%d"),
                    "saved": 50000.0,
                    "created": now.strftime("%Y-%m-%d")
                }
            ],
            'budget_categories': {
                'Housing': 30.0,
                'Food': 15.0,
                'Transportation': 10.0,
                'Utilities': 5.0,
                'Healthcare': 5.0,
                'Entertainment': 10.0,
                'Education': 5.0,
                'Savings': 10.0,
                'Investments': 5.0,
                'Debt Repayment': 5.0,
                'Other': 0.0
            },
            'investments': [
                {
                    "type": "Mutual Fund",
                    "name": "Index Fund",
                    "amount": 100000.0,
                    "date": (now - timedelta(days=90)).strftime("%Y-%m-%d"),
                    "current_value": 105000.0,
                    "ticker": "",
                    "notes": "Nifty 50 Index Fund"
                },
                {
                    "type": "Fixed Deposit",
                    "name": "Bank FD",
                    "amount": 50000.0,
                    "date": (now - timedelta(days=60)).strftime("%Y-%m-%d"),
                    "current_value": 51000.0,
                    "ticker": "",
                    "notes": "1 Year FD @ 7.5%"
                }
            ]
        }
    
    def get_news(self) -> List[Dict[str, str]]:
        """Get financial news with caching"""
        if self.news_cache and (time.time() - self.news_cache_time) < 300:  # 5 min cache
            return self.news_cache
            
        try:
            self.news_cache = self._fetch_financial_news()
            if not self.news_cache or len(self.news_cache) < 5:  # Fallback if few results
                self.news_cache = self._get_sample_news()
        except Exception as e:
            logger.error(f"News fetch error: {str(e)}")
            self.news_cache = self._get_sample_news()
            
        self.news_cache_time = time.time()
        return self.news_cache
    
    def _fetch_financial_news(self) -> List[Dict[str, str]]:
        """Fetch real-time financial news from multiple sources"""
        sources = [
            {
                "name": "Economic Times",
                "url": "https://economictimes.indiatimes.com/rssfeedstopstories.cms",
                "timeout": 5
            },
            {
                "name": "Moneycontrol",
                "url": "https://www.moneycontrol.com/rss/latestnews.xml",
                "timeout": 5
            },
            {
                "name": "Business Standard",
                "url": "https://www.business-standard.com/rss/latest.rss",
                "timeout": 5
            },
            {
                "name": "Reuters Business",
                "url": "https://www.reutersagency.com/feed/?best-topics=business-financial&post_type=best",
                "timeout": 5
            },
            {
                "name": "Bloomberg Quint",
                "url": "https://www.bloombergquint.com/feeds/markets.rss",
                "timeout": 5
            }
        ]
        
        news_items = []
        for source in sources:
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                response = requests.get(source['url'], headers=headers, timeout=source['timeout'])
                response.raise_for_status()
                
                feed = feedparser.parse(response.content)
                for entry in feed.entries[:15]:  # Get more entries to ensure enough financial news
                    title = entry.title.strip()
                    if not any(kw in title.lower() for kw in ['finance', 'stock', 'market', 'economy', 'rupee', 'bank', 'investment', 'tax', 'gdp', 'inflation']):
                        continue
                        
                    sentiment = self._analyze_sentiment(title)
                    news_items.append({
                        "source": source['name'],
                        "title": title,
                        "sentiment": sentiment,
                        "link": entry.get('link', '#'),
                        "published": entry.get('published', '')
                    })
            except Exception as e:
                logger.error(f"Failed to fetch news from {source['name']}: {str(e)}")
                continue
                
        # Remove duplicates and sort by date
        unique_news = {n['title']: n for n in news_items}.values()
        return sorted(unique_news, key=lambda x: x.get('published', ''), reverse=True)[:15]
    
    def _analyze_sentiment(self, text: str) -> str:
        """Enhanced sentiment analysis"""
        text = text.lower()
        positive = any(w in text for w in ['rise', 'growth', 'profit', 'gain', 'high', 'bull', 'surge', 'increase', 'boom', 'rally'])
        negative = any(w in text for w in ['fall', 'drop', 'loss', 'decline', 'low', 'bear', 'crash', 'plunge', 'slump', 'recession'])
        
        if positive and not negative:
            return "positive"
        elif negative and not positive:
            return "negative"
        return "neutral"
    
    def _get_sample_news(self):
        """Quality sample news for fallback"""
        return [
            {
                "source": "Economic Times",
                "title": "Indian markets hit record high amid global rally",
                "link": "https://economictimes.indiatimes.com",
                "sentiment": "positive"
            },
            {
                "source": "Moneycontrol",
                "title": "Buy Bajaj Finance; target of Rs 9000: Emkay Global Financial",
                "link": "https://www.moneycontrol.com",
                "sentiment": "positive"
            },
            {
                "source": "RBI",
                "title": "RBI maintains repo rate at 6.5%",
                "link": "https://www.rbi.org.in",
                "sentiment": "neutral"
            },
            {
                "source": "Business Standard",
                "title": "India's GDP growth forecast raised to 7.5% for FY25",
                "link": "https://www.business-standard.com",
                "sentiment": "positive"
            },
            {
                "source": "Economic Times",
                "title": "Gold prices surge to record high amid global uncertainty",
                "link": "https://economictimes.indiatimes.com",
                "sentiment": "positive"
            },
            {
                "source": "Moneycontrol",
                "title": "Mutual fund inflows hit 6-month high in equity schemes",
                "link": "https://www.moneycontrol.com",
                "sentiment": "positive"
            },
            {
                "source": "Business Standard",
                "title": "Inflation eases to 4.8% in June, RBI may hold rates",
                "link": "https://www.business-standard.com",
                "sentiment": "neutral"
            }
        ]

# Initialize session state
if 'state' not in st.session_state:
    st.session_state.state = SessionState()

state = st.session_state.state

# --- Helper Functions ---
def format_currency(value: float) -> str:
    """Format number as Indian currency"""
    try:
        return f"₹{value:,.2f}"
    except (ValueError, TypeError):
        return str(value)

def validate_date(date_str: str) -> bool:
    """Validate date format YYYY-MM-DD"""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def calculate_savings_metrics(income: float, expenses: float) -> Tuple[float, float]:
    """Calculate savings and savings rate"""
    try:
        savings = float(income) - float(expenses)
        savings_rate = (savings / float(income)) * 100 if income > 0 else 0.0
        return savings, savings_rate
    except Exception as e:
        logger.error(f"Error in savings calculation: {str(e)}")
        return 0.0, 0.0

def calculate_net_worth(assets: Dict[str, float], liabilities: Dict[str, float]) -> float:
    """Calculate net worth from assets and liabilities"""
    try:
        total_assets = sum(assets.values())
        total_liabilities = sum(liabilities.values())
        return total_assets - total_liabilities
    except Exception as e:
        logger.error(f"Error in net worth calculation: {str(e)}")
        return 0.0

def create_savings_gauge(savings_rate: float):
    """Create interactive savings gauge chart"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=savings_rate,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Savings Rate (%)"},
        gauge={
            'axis': {'range': [0, 50]},
            'steps': [
                {'range': [0, 10], 'color': "#FF6B6B"},
                {'range': [10, 20], 'color': "#FFD166"},
                {'range': [20, 50], 'color': "#06D6A0"}
            ],
            'threshold': {
                'line': {'color': "#073B4C", 'width': 4},
                'thickness': 0.75,
                'value': savings_rate
            }
        }
    ))
    fig.update_layout(
        margin=dict(t=50, b=10), 
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
        font_color="#073B4C"
    )
    return fig

def get_market_data(ticker: str) -> pd.DataFrame:
    """Fetch market data with caching"""
    if ticker in state.market_data_cache:
        return state.market_data_cache[ticker]
        
    try:
        data = yf.Ticker(ticker).history(period="1mo")
        if not data.empty:
            state.market_data_cache[ticker] = data
        return data
    except Exception as e:
        logger.error(f"Failed to fetch market data for {ticker}: {str(e)}")
        return pd.DataFrame()

def get_fallback_response(query: str) -> str:
    """Enhanced fallback responses when API is unavailable"""
    query = query.lower()
    now = datetime.now().strftime("%Y-%m-%d")
    
    if "invest" in query:
        return f"""**Investment Options (as of {now})**:
        
        - **Equity Mutual Funds**:  
          Average returns: 12-15% over 5+ years  
          Best for: Long-term wealth creation  
          Top performers: Axis Bluechip, Mirae Asset Large Cap
        
        - **Fixed Deposits**:  
          Current rates: 6-7.5% for 1 year  
          Best for: Risk-averse investors  
          Top banks: SBI (7.1%), HDFC (7.25%)
        
        - **Direct Stocks**:  
          Potential returns: 15%+ for quality stocks  
          Best for: Experienced investors  
          Current market leaders: Reliance, TCS, HDFC Bank
        
        - **Gold ETFs**:  
          1-year return: ~12%  
          Best for: Portfolio diversification  
          Options: Nippon India Gold ETF, SBI Gold ETF"""
    
    elif "budget" in query:
        return f"""**Budgeting Strategies (as of {now})**:
        
        1. **50/30/20 Rule**  
           - 50% Needs (rent, groceries, bills)  
           - 30% Wants (dining, entertainment)  
           - 20% Savings & Debt Repayment
        
        2. **Zero-Based Budgeting**  
           - Assign every rupee a purpose  
           - Track all expenses daily  
           - Apps: Moneycontrol, ET Markets
        
        3. **Envelope System**  
           - Cash-based budgeting  
           - Physical envelopes for categories  
           - Prevents overspending
        
        4. **Automated Savings**  
           - Set up SIPs and auto-transfers  
           - Pay yourself first  
           - Apps: Groww, Kuvera"""
    
    elif "tax" in query:
        return f"""**Tax Saving Options (FY 2024-25)**:
        
        **Section 80C (₹1.5L deduction)**:
        - ELSS Funds (Lock-in: 3 years)  
        - PPF (7.1% interest, 15-year term)  
        - NPS (Additional ₹50k under 80CCD)  
        - 5-year Tax Saver FDs (Current rate: ~7%)
        
        **Health Insurance (Section 80D)**:
        - Self/Family: ₹25,000 deduction  
        - Senior Parents: Additional ₹50,000  
        - Critical Illness: Additional ₹50,000
        
        **Home Loan Benefits**:
        - Principal repayment under 80C  
        - Interest deduction up to ₹2L under 24B"""
    
    return f"""**General Financial Advice (as of {now})**:
    
    1. **Emergency Fund**  
       - Cover 6-12 months expenses  
       - Keep in liquid funds/FDs  
       - Start with ₹50,000 minimum
    
    2. **Debt Management**  
       - Pay credit cards in full  
       - Target loans >10% interest first  
       - Consider balance transfers
    
    3. **Investment Principles**  
       - Start early, invest regularly  
       - Diversify across asset classes  
       - Rebalance portfolio annually
    
    4. **Retirement Planning**  
       - Target 25× annual expenses  
       - Use NPS for tax benefits  
       - Consider SWPs in retirement"""

# --- UI Components ---
def create_news_ticker():
    """Create animated news ticker with working links"""
    news_items = state.get_news()
    
    st.markdown("""
    <style>
    .news-ticker {
        background: #f0f9ff;
        border: 1px solid #b3e0ff;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 20px;
        overflow: hidden;
        white-space: nowrap;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    .news-container {
        display: inline-block;
        animation: scroll 60s linear infinite;
        padding-left: 100%;
    }
    .news-item {
        margin-right: 40px;
        display: inline-block;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 14px;
        text-decoration: none !important;
    }
    .positive { background-color: #d4edda; color: #155724; }
    .neutral { background-color: #e2f0fd; color: #1a4b8c; }
    .negative { background-color: #f8d7da; color: #721c24; }
    @keyframes scroll {
        0% { transform: translateX(0); }
        100% { transform: translateX(-100%); }
    }
    </style>
    """, unsafe_allow_html=True)
    
    news_html = ' '.join([
        f'<a href="{item["link"]}" target="_blank" class="news-item {item["sentiment"]}" title="{item["source"]}">• {html.escape(item["title"])}</a>'
        for item in news_items
    ])
    
    st.markdown(f"""
    <div class="news-ticker">
        <div class="news-container">
            {news_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

def create_balance_sheet_ui():
    """Interactive balance sheet showing assets vs liabilities"""
    st.header("📊 Personal Balance Sheet")
    
    with st.expander("Assets", expanded=True):
        cols = st.columns(2)
        updated_assets = {}
        
        with cols[0]:
            st.subheader("Asset Type")
            for asset in state.financial_data['assets']:
                st.text(asset.replace('_', ' ').title())
        
        with cols[1]:
            st.subheader("Value (₹)")
            for asset, value in state.financial_data['assets'].items():
                updated_assets[asset] = st.number_input(
                    f"Enter {asset.replace('_', ' ')} value",
                    value=float(value),
                    min_value=0.0,
                    step=10000.0,
                    format="%.2f",
                    key=f"asset_{asset}"
                )
        
        if st.button("Update Assets", key="update_assets"):
            state.financial_data['assets'] = updated_assets
            st.success("Assets updated successfully!")
    
    with st.expander("Liabilities", expanded=True):
        cols = st.columns(2)
        updated_liabilities = {}
        
        with cols[0]:
            st.subheader("Liability Type")
            for liability in state.financial_data['liabilities']:
                st.text(liability.replace('_', ' ').title())
        
        with cols[1]:
            st.subheader("Amount Owed (₹)")
            for liability, value in state.financial_data['liabilities'].items():
                updated_liabilities[liability] = st.number_input(
                    f"Enter {liability.replace('_', ' ')} amount",
                    value=float(value),
                    min_value=0.0,
                    step=10000.0,
                    format="%.2f",
                    key=f"liability_{liability}"
                )
        
        if st.button("Update Liabilities", key="update_liabilities"):
            state.financial_data['liabilities'] = updated_liabilities
            st.success("Liabilities updated successfully!")
    
    # Net worth calculation
    total_assets = sum(state.financial_data['assets'].values())
    total_liabilities = sum(state.financial_data['liabilities'].values())
    net_worth = total_assets - total_liabilities
    
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Assets", format_currency(total_assets))
    col2.metric("Total Liabilities", format_currency(total_liabilities))
    col3.metric("Net Worth", 
               format_currency(net_worth),
               delta_color="inverse" if net_worth < 0 else "normal")

def create_behavioral_finance_sidebar():
    """Sidebar with behavioral finance information"""
    with st.sidebar:
        st.markdown("""
        <style>
        .sidebar .sidebar-content {
            background-color: #f0f9ff;
            border-right: 1px solid #b3e0ff;
        }
        .info-card {
            background-color: white;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 15px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            border: 1px solid #b3e0ff;
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="info-card">
            <h3>🧠 Behavioral Finance</h3>
            <p>Understanding how psychology affects your money decisions</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(BEHAVIORAL_FINANCE_INFO, unsafe_allow_html=True)

def create_budget_ui():
    """Budget planning interface"""
    st.header("📊 Budget Planner")
    
    with st.expander("Income & Expenses", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            income = st.number_input(
                "Monthly Income (₹)",
                value=state.financial_data['income'],
                min_value=0.0,
                step=1000.0,
                format="%.2f"
            )
            expenses = st.number_input(
                "Monthly Expenses (₹)",
                value=state.financial_data['expenses'],
                min_value=0.0,
                step=1000.0,
                format="%.2f"
            )
            
            if st.button("Update Budget", key="budget_update"):
                try:
                    if income <= 0 or expenses <= 0:
                        st.error("Values must be positive")
                    elif expenses > income:
                        st.error("Expenses cannot exceed income")
                    else:
                        state.financial_data['income'] = income
                        state.financial_data['expenses'] = expenses
                        savings, savings_rate = calculate_savings_metrics(income, expenses)
                        state.financial_data['savings'] = savings
                        st.success("Budget updated successfully!")
                except Exception as e:
                    st.error(f"Error updating budget: {str(e)}")
        
        with col2:
            savings = state.financial_data['savings']
            savings_rate = calculate_savings_metrics(state.financial_data['income'], state.financial_data['expenses'])[1]
            
            st.metric("Monthly Savings", format_currency(savings))
            st.metric("Savings Rate", f"{savings_rate:.1f}%")
            
            fig = create_savings_gauge(savings_rate)
            st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("Budget Categories"):
        st.write("Adjust your budget allocation percentages:")
        cols = st.columns(3)
        for i, (category, percent) in enumerate(state.financial_data['budget_categories'].items()):
            with cols[i % 3]:
                new_percent = st.number_input(
                    f"{category} Allocation (%)",
                    value=percent,
                    min_value=0.0,
                    max_value=100.0,
                    step=1.0,
                    key=f"budget_{category}"
                )
                if new_percent != percent:
                    state.financial_data['budget_categories'][category] = new_percent
                    st.success(f"{category} allocation updated to {new_percent}%")

def create_investments_ui():
    """Investments tracking interface"""
    st.header("📈 Investments")
    
    tab1, tab2 = st.tabs(["Your Portfolio", "Market Research"])
    
    with tab1:
        total_invested = sum(inv['amount'] for inv in state.financial_data['investments'])
        current_value = sum(inv['current_value'] for inv in state.financial_data['investments'])
        return_pct = ((current_value - total_invested) / total_invested * 100) if total_invested > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Invested", format_currency(total_invested))
        col2.metric("Current Value", format_currency(current_value))
        col3.metric("Return", f"{return_pct:.2f}%")
        
        with st.expander("Add New Investment"):
            with st.form("add_investment_form"):
                col1, col2 = st.columns(2)
                
                with col1:
                    inv_type = st.selectbox(
                        "Investment Type",
                        ["Fixed Deposit", "Mutual Fund", "Stocks", "ETF", "PPF", "NPS", "Gold", "Real Estate", "Other"]
                    )
                    inv_name = st.text_input("Name/Description")
                    inv_amount = st.number_input("Amount (₹)", min_value=0.0)
                    inv_date = st.text_input(
                        "Date (YYYY-MM-DD)",
                        value=datetime.now().strftime("%Y-%m-%d")
                    )
                
                with col2:
                    inv_ticker = st.text_input("Ticker Symbol (optional)")
                    inv_notes = st.text_area("Notes")
                
                if st.form_submit_button("Add Investment"):
                    try:
                        if not all([inv_type, inv_name, inv_amount, inv_date]):
                            st.error("All fields are required")
                        elif not validate_date(inv_date):
                            st.error("Invalid date format (YYYY-MM-DD)")
                        elif inv_amount <= 0:
                            st.error("Amount must be positive")
                        else:
                            new_investment = {
                                "type": inv_type,
                                "name": inv_name,
                                "amount": float(inv_amount),
                                "date": inv_date,
                                "current_value": float(inv_amount),
                                "ticker": inv_ticker,
                                "notes": inv_notes
                            }
                            state.financial_data['investments'].append(new_investment)
                            st.success("Investment added successfully!")
                    except Exception as e:
                        st.error(f"Error adding investment: {str(e)}")
        
        if state.financial_data['investments']:
            with st.expander("Manage Investments"):
                selected_inv = st.selectbox(
                    "Select Investment",
                    [inv['name'] for inv in state.financial_data['investments']],
                    key="investment_select"
                )
                
                for inv in state.financial_data['investments']:
                    if inv['name'] == selected_inv:
                        with st.form(f"update_{inv['name']}"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.text_input("Type", value=inv['type'], disabled=True)
                                st.number_input("Amount (₹)", value=inv['amount'], disabled=True)
                                st.text_input("Date", value=inv['date'], disabled=True)
                            
                            with col2:
                                new_value = st.number_input(
                                    "Current Value (₹)",
                                    value=inv['current_value'],
                                    min_value=0.0
                                )
                                st.text_area("Notes", value=inv['notes'], disabled=True)
                            
                            if st.form_submit_button("Update Value"):
                                try:
                                    if new_value <= 0:
                                        st.error("Value must be positive")
                                    else:
                                        inv['current_value'] = new_value
                                        st.success("Investment value updated successfully!")
                                except Exception as e:
                                    st.error(f"Error updating investment: {str(e)}")
    
    with tab2:
        with st.form("market_research_form"):
            ticker = st.text_input(
                "Enter Stock/ETF Symbol",
                value="RELIANCE.NS",
                placeholder="RELIANCE.NS, ^NSEI, TCS.NS"
            )
            
            if st.form_submit_button("Get Market Data"):
                try:
                    if not ticker.strip():
                        st.error("Please enter a ticker symbol")
                    else:
                        data = get_market_data(ticker)
                        if data.empty:
                            st.error("No data found for this ticker")
                        else:
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(
                                x=data.index,
                                y=data['Close'],
                                name="Closing Price",
                                line=dict(color='royalblue', width=2)
                            ))
                            fig.update_layout(
                                title=f"{ticker} Price History",
                                xaxis_title="Date",
                                yaxis_title="Price (₹)",
                                margin=dict(l=40, r=40, t=40, b=40)
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                            
                            current = data['Close'].iloc[-1]
                            prev_close = data['Close'].iloc[-2] if len(data) > 1 else current
                            change = ((current - prev_close) / prev_close * 100) if prev_close != 0 else 0
                            
                            col1, col2, col3 = st.columns(3)
                            col1.metric("Current Price", format_currency(current))
                            col2.metric("Daily Change", f"{change:.2f}%")
                            col3.metric("52 Week Range", 
                                       f"{format_currency(data['Close'].min())} - {format_currency(data['Close'].max())}")
                except Exception as e:
                    st.error(f"Market research error: {str(e)}")

def create_savings_ui():
    """Savings goals interface"""
    st.header("🎯 Savings Goals")
    
    with st.expander("Add New Goal"):
        with st.form("add_goal_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                goal_name = st.text_input("Goal Name")
                goal_amount = st.number_input("Target Amount (₹)", min_value=0.0)
            
            with col2:
                goal_deadline = st.text_input(
                    "Target Date (YYYY-MM-DD)",
                    value=(datetime.now() + timedelta(days=180)).strftime("%Y-%m-%d")
                )
            
            if st.form_submit_button("Add Goal"):
                try:
                    if not all([goal_name, goal_amount, goal_deadline]):
                        st.error("All fields are required")
                    elif not validate_date(goal_deadline):
                        st.error("Invalid date format (YYYY-MM-DD)")
                    elif goal_amount <= 0:
                        st.error("Amount must be positive")
                    else:
                        new_goal = {
                            "name": goal_name,
                            "target": float(goal_amount),
                            "deadline": goal_deadline,
                            "saved": 0.0,
                            "created": datetime.now().strftime("%Y-%m-%d")
                        }
                        state.financial_data['goals'].append(new_goal)
                        st.success("Goal added successfully!")
                except Exception as e:
                    st.error(f"Error adding goal: {str(e)}")
    
    if state.financial_data['goals']:
        selected_goal = st.selectbox(
            "Select Goal",
            [goal['name'] for goal in state.financial_data['goals']],
            key="goal_select"
        )
        
        for goal in state.financial_data['goals']:
            if goal['name'] == selected_goal:
                progress = (goal['saved'] / goal['target']) * 100 if goal['target'] > 0 else 0
                
                col1, col2 = st.columns(2)
                col1.metric("Target Amount", format_currency(goal['target']))
                col2.metric("Amount Saved", format_currency(goal['saved']))
                
                st.progress(int(progress))
                st.metric("Progress", f"{progress:.1f}%")
                
                with st.form(f"add_to_{goal['name']}"):
                    add_amount = st.number_input(
                        "Add to Savings (₹)",
                        min_value=0.0,
                        key=f"add_{goal['name']}"
                    )
                    
                    if st.form_submit_button("Update Savings"):
                        try:
                            if add_amount <= 0:
                                st.error("Amount must be positive")
                            else:
                                goal['saved'] += add_amount
                                state.financial_data['savings'] += add_amount
                                st.success(f"Added ₹{add_amount:,.2f} to {goal['name']}")
                        except Exception as e:
                            st.error(f"Error updating savings: {str(e)}")

def create_learning_ui():
    """Financial education interface"""
    st.header("📚 Learning Center")
    
    tab1, tab2 = st.tabs(["Calculators", "Education"])
    
    with tab1:
        calculator_type = st.radio(
            "Select Calculator",
            ["SIP Calculator", "EMI Calculator"],
            horizontal=True
        )
        
        if calculator_type == "SIP Calculator":
            with st.form("sip_calculator"):
                col1, col2 = st.columns(2)
                
                with col1:
                    sip_years = st.slider(
                        "Investment Period (years)",
                        min_value=1,
                        max_value=40,
                        value=10
                    )
                    sip_monthly = st.number_input(
                        "Monthly Investment (₹)",
                        min_value=1000,
                        value=5000
                    )
                
                with col2:
                    sip_rate = st.slider(
                        "Expected Annual Return (%)",
                        min_value=1,
                        max_value=30,
                        value=12
                    )
                
                if st.form_submit_button("Calculate"):
                    monthly_rate = sip_rate / 100 / 12
                    months = sip_years * 12
                    future_value = sip_monthly * (((1 + monthly_rate)**months - 1) / monthly_rate) * (1 + monthly_rate)
                    st.metric("Estimated Future Value", format_currency(future_value))
        
        else:  # EMI Calculator
            with st.form("emi_calculator"):
                col1, col2 = st.columns(2)
                
                with col1:
                    emi_principal = st.number_input(
                        "Loan Amount (₹)",
                        min_value=1000,
                        value=1000000
                    )
                    emi_interest = st.slider(
                        "Interest Rate (% p.a.)",
                        min_value=1,
                        max_value=30,
                        value=10
                    )
                
                with col2:
                    emi_tenure = st.slider(
                        "Loan Tenure (years)",
                        min_value=1,
                        max_value=30,
                        value=10
                    )
                
                if st.form_submit_button("Calculate"):
                    monthly_rate = emi_interest / 100 / 12
                    months = emi_tenure * 12
                    emi = emi_principal * monthly_rate * (1 + monthly_rate)**months / ((1 + monthly_rate)**months - 1)
                    st.metric("Monthly EMI", format_currency(emi))
    
    with tab2:
        topic = st.selectbox(
            "Select Topic",
            ["Budgeting Basics", "Investing 101", "Tax Planning", "Retirement Strategies"],
            index=1
        )
        
        if topic == "Budgeting Basics":
            st.markdown("""
            ### 50/30/20 Budgeting Rule
            
            **50% Needs:**
            - Rent/EMI
            - Groceries
            - Utilities
            - Transportation
            
            **30% Wants:**
            - Dining out
            - Entertainment
            - Travel
            - Hobbies
            
            **20% Savings:**
            - Emergency fund
            - Investments
            - Debt repayment
            
            **Pro Tip:** Use apps like Moneycontrol or ET Markets to track spending automatically.
            """)
        elif topic == "Tax Planning":
            st.markdown("""
            ### Tax Saving Instruments (FY 2024-25)
            
            **Section 80C (₹1.5L deduction):**
            - ELSS Mutual Funds (3yr lock-in, ~12% returns)
            - PPF (15yr tenure, 7.1% tax-free)
            - Life Insurance Premiums (must be 10x annual premium)
            - 5-year Tax Saver FDs (current rates ~7%)
            
            **Section 80D (Health Insurance):**
            - Self/Family: ₹25,000
            - Senior Citizens: ₹50,000
            - Parents (Senior): Additional ₹75,000
            
            **New Tax Regime Benefits:**
            - No deductions but lower tax slabs
            - Better for those with few investments
            - Income up to ₹7L tax-free
            """)
        elif topic == "Retirement Strategies":
            st.markdown("""
            ### Retirement Planning in India
            
            **1. Corpus Calculation:**
            - Rule of 25: 25 × Annual expenses
            - Example: ₹50,000/month = ₹1.5 Crore corpus
            - Adjust for inflation (use 6-7% inflation rate)
            
            **2. Investment Vehicles:**
            - NPS (Tax benefits + annuity)
            - Mutual Fund SIPs (Equity for growth)
            - Senior Citizen Savings Scheme (8.2% interest)
            
            **3. Withdrawal Strategy:**
            - SWP from mutual funds (Systematic Withdrawal Plan)
            - FD laddering for regular income
            - Annuity plans for guaranteed income
            """)
        else:  # Investing 101
            st.markdown("""
            ### Investment Options in India
            
            **By Risk Profile:**
            
            *Low Risk (4-8% returns)*:
            - FDs, PPF, SCSS, Debt Funds
            
            *Medium Risk (8-12% returns)*:
            - Hybrid Funds, Balanced Advantage Funds
            
            *High Risk (12%+ returns)*:
            - Equity Funds, Direct Stocks, Sectoral Funds
            
            **Current Market Trends:**
            - Large caps outperforming mid/small caps
            - Banking sector showing strength
            - IT sector facing headwinds
            - Gold prices at all-time highs
            
            **Resources:**
            - Value Research for fund ratings
            - Screener.in for stock analysis
            - SEBI website for regulations
            """)

def chat_interface():
    """AI chat interface with financial context"""
    st.header("💬 PaisaPaglu AI Advisor")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    for chat in st.session_state.chat_history:
        st_message(**chat)
    
    user_input = st.chat_input("Ask your financial question...")
    
    if user_input:
        st.session_state.chat_history.append({
            "message": user_input,
            "is_user": True,
            "key": f"user_{len(st.session_state.chat_history)}"
        })
        
        if not API_ENABLED:
            response = get_fallback_response(user_input)
        else:
            # Enhanced prompt with behavioral finance context
            prompt = f"""As a certified financial advisor, provide detailed, personalized advice considering:
            
            **User Financial Snapshot**:
            - Income: ₹{state.financial_data['income']:,.2f}/month
            - Expenses: ₹{state.financial_data['expenses']:,.2f}/month
            - Savings Rate: {calculate_savings_metrics(state.financial_data['income'], state.financial_data['expenses'])[1]:.1f}%
            - Net Worth: ₹{calculate_net_worth(state.financial_data['assets'], state.financial_data['liabilities']):,.2f}
            - Goals: {len(state.financial_data['goals'])} active savings goals
            
            **Question**: {user_input}
            
            **Behavioral Considerations**:
            {FINANCIAL_BIASES}
            
            **Response Guidelines**:
            1. Start with key takeaways
            2. Provide specific, actionable steps
            3. Include current market context
            4. Suggest tools/resources
            5. Highlight behavioral pitfalls
            6. Format with clear headings
            
            **Current Market Context**:
            - Nifty 50: {yf.Ticker('^NSEI').history(period='1d')['Close'].iloc[-1] if not yf.Ticker('^NSEI').history(period='1d').empty else 'N/A'}
            - Gold: ₹{yf.Ticker('GC=F').history(period='1d')['Close'].iloc[-1]*82 if not yf.Ticker('GC=F').history(period='1d').empty else 'N/A'}/10g
            - 10yr G-Sec: ~7.2% yield
            
            **Recommended Structure**:
            ### Key Recommendations
            [Concise bullet points]
            
            ### Detailed Analysis
            [Behavioral + financial analysis]
            
            ### Action Plan
            [Step-by-step guidance]
            
            ### Resources
            [Tools, apps, reading]"""
            
            # Use web search for current data when needed
            if any(kw in user_input.lower() for kw in ['current', 'today', 'now', 'recent', 'latest']):
                response = gemini.generate_with_web_search(prompt)
            else:
                response = gemini.generate(prompt)
        
        st.session_state.chat_history.append({
            "message": response,
            "is_user": False,
            "key": f"ai_{len(st.session_state.chat_history)}"
        })
        
        st.rerun()

# --- Main Application ---
def main():
    # Application Configuration
    st.set_page_config(
        page_title="PaisaPaglu AI",
        page_icon="💰",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for the entire app
    st.markdown("""
    <style>
    :root {
        --primary: #073B4C;
        --secondary: #06D6A0;
        --accent: #118AB2;
        --background: #f8f9fa;
        --card-bg: white;
    }
    
    body {
        color: #073B4C;
        background-color: var(--background);
    }
    
    .stApp {
        background-color: var(--background);
    }
    
    .stButton>button {
        background-color: var(--secondary);
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1rem;
    }
    
    .stButton>button:hover {
        background-color: #05B384;
        color: white;
    }
    
    .stTextInput>div>div>input {
        border-radius: 8px;
        border: 1px solid #b3e0ff;
    }
    
    .stNumberInput>div>div>input {
        border-radius: 8px;
        border: 1px solid #b3e0ff;
    }
    
    .stSelectbox>div>div>select {
        border-radius: 8px;
        border: 1px solid #b3e0ff;
    }
    
    .financial-card {
        background-color: var(--card-bg);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        border: 1px solid #b3e0ff;
    }
    
    .dashboard-header {
        margin-bottom: 20px;
        text-align: center;
    }
    
    .stTabs [role="tablist"] {
        background-color: #f0f9ff;
        border-radius: 8px;
        padding: 8px;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: var(--secondary) !important;
        color: white !important;
        border-radius: 6px;
    }
    
    .stMetric {
        background-color: var(--card-bg);
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #b3e0ff;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Application Header
    st.markdown("""
    <div class="dashboard-header">
        <h1 style="color: #073B4C;">💰 PaisaPaglu</h1>
        <p style="color: #118AB2; font-size: 1.1rem;">
            Your Personal Finance Assistant with Behavioral Insights
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Behavioral Finance Sidebar
    create_behavioral_finance_sidebar()
    
    # News Ticker
    create_news_ticker()
    
    # Main Application Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🏦 Balance Sheet", 
        "📊 Budget", 
        "📈 Investments", 
        "🎯 Savings", 
        "📚 Learning", 
        "💬 Advisor"
    ])
    
    with tab1:
        create_balance_sheet_ui()
    
    with tab2:
        create_budget_ui()
    
    with tab3:
        create_investments_ui()
    
    with tab4:
        create_savings_ui()
    
    with tab5:
        create_learning_ui()
    
    with tab6:
        chat_interface()
    
    # Footer
    st.markdown(f"""
    <div style="text-align: center; margin-top: 30px; color: #666; font-size: 0.9em;">
        <hr style="border-top: 1px solid #b3e0ff; margin-bottom: 15px;">
        <p>PaisaPaglu AI • Version 2.1 • Last updated: {datetime.now().strftime('%Y-%m-%d')}</p>
        <p>Note: This is a demo application. Consult a certified financial advisor for personalized advice.</p>
        <p>&copy; Mayur Khekare. Made with &hearts;.</p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()