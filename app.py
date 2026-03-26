import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Configuration & Styling
st.set_page_config(page_title="Host Revenue Optimizer", page_icon="🚗", layout="wide")
st.title("🚗 Vehicle Utilization & Pricing Optimizer")
st.markdown("### Turn your fleet data into a high-yield strategy.")

# 2. Sidebar / File Upload
with st.sidebar:
    st.header("Upload Data")
    uploaded_file = st.file_uploader("Drop your fleet_data.csv here", type="csv")
    st.info("Ensure your CSV has: vehicle_alias, days_available, days_booked, daily_rate, market_rate")

if uploaded_file is not None:
    # 3. Data Processing
    df = pd.read_csv(uploaded_file)
    
    # --- NEW: The Sanitizer ---
    # This strips whitespace and makes everything lowercase to prevent KeyErrors
    df.columns = df.columns.str.strip().str.lower()
    # ---------------------------

    # Now we use lowercase names to match the sanitizer
    try:
        df['utilization'] = df['days_booked'] / df['days_available']
        df['current_monthly_rev'] = df['days_booked'] * df['daily_rate']
        
        # ... rest of your logic (ensure all column names here are lowercase) ...
        TARGET_UTIL = 0.75
        df['potential_monthly_rev'] = (df['days_available'] * TARGET_UTIL) * df['market_rate']
        
        # [The rest of your existing metric and chart code goes here]

    except KeyError as e:
        st.error(f"🚨 **Column Missing:** The app couldn't find the column: `{e}`")
        st.info("Please ensure your CSV has these exact headers: `vehicle_alias`, `days_available`, `days_booked`, `daily_rate`, `market_rate`")
    
    # 4. Revenue Forecasting Logic
    TARGET_UTIL = 0.75
    df['potential_monthly_rev'] = (df['days_available'] * TARGET_UTIL) * df['market_rate']
    
    total_current = df['current_monthly_rev'].sum()
    total_potential = df['potential_monthly_rev'].sum()
    revenue_gap = total_potential - total_current

    # 5. Top Level Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Current Monthly Revenue", f"${total_current:,.2f}")
    m2.metric("Target Revenue (75% Util)", f"${total_potential:,.2f}")
    m3.metric("Revenue Gap", f"${revenue_gap:,.2f}", 
              delta=f"{-revenue_gap:,.2f}", 
              delta_color="inverse" if revenue_gap > 0 else "normal")

    st.divider()

    # 6. Visualizations (The Map)
    col_chart, col_list = st.columns([2, 1])

    with col_chart:
        st.subheader("📊 Fleet Performance Map")
        fig = px.scatter(
            df, x="daily_rate", y="utilization", 
            size="days_booked", color="vehicle_alias",
            hover_name="vehicle_alias",
            labels={"daily_rate": "Daily Rate ($)", "utilization": "Utilization (%)"},
            trendline="ols"
        )
        fig.add_hline(y=0.75, line_dash="dot", annotation_text="75% Target")
        st.plotly_chart(fig, use_container_width=True)

    with col_list:
        st.subheader("📋 Action Items")
        for _, row in df.iterrows():
            u = row['utilization']
            price = row['daily_rate']
            market = row['market_rate']
            
            with st.expander(f"{row['vehicle_alias']}"):
                if u > 0.85 and price <= market:
                    st.error(f"Underpriced: Raise to ${market + 10}+")
                elif u < 0.50 and price > market:
                    st.warning(f"Overpriced: Drop to ${market - 5}")
                elif 0.65 <= u <= 0.85:
                    st.success("Dialed In: No changes needed")
                else:
                    st.info("Review: Check photos/visibility")

    # 7. Final Insight
    if revenue_gap > 0:
        st.warning(f"💡 You are missing out on **${revenue_gap:,.2f}** this month. Most of this is due to pricing friction on low-utilization vehicles.")
    else:
        st.balloons()
        st.success("🔥 Your fleet is performing above market expectations!")

else:
    st.write("Waiting for data... please upload a CSV in the sidebar to begin.") 
