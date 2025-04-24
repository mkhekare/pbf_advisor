# app.py - Vercel-compatible Streamlit Finance App
import streamlit as st
from datetime import datetime
import pandas as pd
import plotly.express as px

# Initialize session state
if 'finance' not in st.session_state:
    st.session_state.finance = {
        'income': 50000,
        'expenses': 35000,
        'savings': 15000,
        'goals': [
            {'name': 'Emergency Fund', 'target': 100000, 'saved': 25000},
            {'name': 'Vacation', 'target': 50000, 'saved': 5000}
        ],
        'transactions': []
    }

# Helper functions
def format_currency(amount):
    return f"₹{amount:,.2f}"

def add_transaction(amount, category, note=""):
    st.session_state.finance['transactions'].append({
        'date': datetime.now().strftime("%Y-%m-%d"),
        'amount': amount,
        'category': category,
        'note': note
    })

# UI Layout
st.set_page_config(page_title="Finance Tracker", layout="wide")
st.title("💰 Personal Finance Dashboard")

# Main Metrics
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Monthly Income", format_currency(st.session_state.finance['income']))
with col2:
    st.metric("Monthly Expenses", format_currency(st.session_state.finance['expenses']))
with col3:
    st.metric("Current Savings", format_currency(st.session_state.finance['savings']))

# Budget Section
with st.expander("📝 Update Budget", expanded=True):
    income = st.number_input("Monthly Income (₹)", 
                           value=st.session_state.finance['income'],
                           step=1000)
    expenses = st.number_input("Monthly Expenses (₹)", 
                             value=st.session_state.finance['expenses'],
                             step=1000)
    
    if st.button("Update Budget"):
        st.session_state.finance.update({
            'income': income,
            'expenses': expenses,
            'savings': income - expenses
        })
        st.success("Budget updated!")

# Visualizations
tab1, tab2 = st.tabs(["Spending Breakdown", "Savings Progress"])

with tab1:
    if st.session_state.finance['transactions']:
        df = pd.DataFrame(st.session_state.finance['transactions'])
        fig = px.pie(df, names='category', values='amount', 
                    title="Spending by Category")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No transactions recorded yet")

with tab2:
    goals_df = pd.DataFrame(st.session_state.finance['goals'])
    goals_df['progress'] = (goals_df['saved'] / goals_df['target']) * 100
    fig = px.bar(goals_df, x='name', y='progress', 
                title="Goal Progress (%)",
                text='progress')
    fig.update_traces(texttemplate='%{y:.1f}%', textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

# Transaction Recording
with st.expander("➕ Record Transaction"):
    amount = st.number_input("Amount (₹)", min_value=0, step=100)
    category = st.selectbox("Category", 
                           ["Food", "Transport", "Housing", "Entertainment", "Other"])
    note = st.text_input("Note (Optional)")
    
    if st.button("Add Transaction"):
        add_transaction(amount, category, note)
        st.session_state.finance['expenses'] += amount
        st.session_state.finance['savings'] -= amount
        st.success("Transaction recorded!")

# Goal Management
with st.expander("🎯 Manage Goals"):
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Add New Goal")
        new_goal = st.text_input("Goal Name")
        new_target = st.number_input("Target Amount (₹)", min_value=0, step=1000)
        
        if st.button("Create Goal"):
            st.session_state.finance['goals'].append({
                'name': new_goal,
                'target': new_target,
                'saved': 0
            })
            st.success(f"Goal '{new_goal}' added!")
    
    with col2:
        st.subheader("Update Progress")
        selected_goal = st.selectbox("Select Goal", 
                                    [g['name'] for g in st.session_state.finance['goals']])
        amount = st.number_input("Amount to Add (₹)", min_value=0, step=1000)
        
        if st.button("Add to Goal"):
            for goal in st.session_state.finance['goals']:
                if goal['name'] == selected_goal:
                    goal['saved'] += amount
                    st.session_state.finance['savings'] -= amount
                    st.success(f"Added {format_currency(amount)} to {selected_goal}")

# Footer
st.markdown("---")
st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
