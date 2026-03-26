import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Configuration
st.set_page_config(page_title="Host Revenue Optimizer", page_icon="🚗", layout="wide")
st.title("🚗 Vehicle Utilization & Pricing Optimizer")
st.markdown("### Turn your fleet data into a high-yield strategy.")

# 2. Sidebar / File Upload
with st.sidebar:
    st.header("Upload Data")
    uploaded_file = st.file_uploader("Drop your fleet_data.csv here", type="csv")
    
    st.divider()
    st.subheader("Template Guide")
    st.info("""
    Your CSV must include these columns:
    - `vehicle_alias`
    - `days_available`
    - `days_booked`
    - `daily_rate`
    - `market_rate`
    """)
    
    # Downloadable template for the user to verify format
    template_df = pd.DataFrame({
        "vehicle_alias": ["Tesla Model 3", "Toyota Camry"],
        "days_available": [30, 30],
        "days_booked": [25, 12],
        "daily_rate": [120, 60],
        "market_rate": [110, 65]
    })
    st.download_button("Download CSV Template", data=template_df.to_csv(index=False).encode('utf-8'), file_name="template.csv")

if uploaded_file is not None:
    try:
        # 3. Data Loading & Sanitization
        df = pd.read_csv(uploaded_file)
        
        # Scrub column names: remove spaces, invisible characters, and lowercase everything
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')

        # 4. Calculation Logic (Defensive Mode)
        # We wrap this in a try/except to catch missing columns specifically
        df['utilization'] = df['days_booked'] / df['days_available']
        df['current_monthly_rev'] = df['days_booked'] * df['daily_rate']
        
        TARGET_UTIL = 0.75
        df['potential_monthly_rev'] = (df['days_available'] * TARGET_UTIL) * df['market_rate']
        
        total_current = df['current_monthly_rev'].sum()
        total_potential = df['potential_monthly_rev'].sum()
        revenue_gap = total_potential - total_current

        # 5. Top Level Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Current Monthly Revenue", f"${total_current:,.2f}")
        m2.metric("Target Revenue (75% Util)", f"${total_potential:,.2f}")
        
        # Display Gap: Red if positive (missing money), Green if negative (beating market)
        m3.metric("Revenue Gap", f"${revenue_gap:,.2f}", 
                  delta=f"{-revenue_gap:,.2f}", 
                  delta_color="inverse" if revenue_gap > 0 else "normal")

        st.divider()

        # 6. Visualizations & Action Items
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
                        st.error(f"**Underpriced**")
                        st.write(f"Raise rate closer to ${market + 10}")
                    elif u < 0.50 and price > market:
                        st.warning(f"**Overpriced**")
                        st.write(f"Drop rate closer to ${market - 5}")
                    elif 0.65 <= u <= 0.85:
                        st.success("**Dialed In**")
                        st.write("Maintain current strategy.")
                    else:
                        st.info("**Review Visibility**")
                        st.write("Price is okay; check photos/SEO.")

        # 7. Final Footer Insight
        if revenue_gap > 0:
            st.warning(f"💡 You could increase monthly revenue by **${revenue_gap:,.2f}** by optimizing underperforming vehicles.")
        else:
            st.balloons()
            st.success("🔥 Your fleet is currently outperforming the market target!")

    except KeyError as e:
        st.error(f"🚨 **Mapping Error:** The app couldn't find the column: `{e}`")
        st.write("### Debugging Info:")
        st.write("Your CSV columns were detected as:", list(df.columns))
        st.write("They need to match: `vehicle_alias`, `days_available`, `days_booked`, `daily_rate`, `market_rate`")
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")

else:
    st.info("👋 Welcome! Please upload your fleet CSV in the sidebar to generate your revenue report.")
