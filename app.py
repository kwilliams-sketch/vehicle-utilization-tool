import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Configuration
st.set_page_config(page_title="Host Revenue Optimizer", page_icon="🚗", layout="wide")
st.title("🚗 VIN-Level Fleet Optimizer")
st.markdown("### Individualized tracking for every vehicle in your fleet.")

# 2. Sidebar Settings
with st.sidebar:
    st.header("1. Upload Trip Export")
    uploaded_file = st.file_uploader("Drop your CSV here", type="csv")
    
    st.divider()
    st.header("2. Global Assumptions")
    days_in_period = st.number_input("Days in this Period (e.g. 30)", value=30, min_value=1)
    market_avg = st.number_input("Est. Market Daily Rate ($)", value=75, min_value=1)

# Helper function to turn "$1,200.00" into 1200.00
def clean_currency(column):
    if column.dtype == 'object':
        # Removes $, commas, and whitespace
        return pd.to_numeric(column.replace(r'[\$,\s]', '', regex=True), errors='coerce').fillna(0)
    return column

if uploaded_file is not None:
    try:
        # 3. Data Loading
        df_raw = pd.read_csv(uploaded_file)
        df_raw.columns = df_raw.columns.str.strip().str.lower().str.replace(' ', '_')

        # 4. DATA CLEANING
        df_raw['trip_days'] = pd.to_numeric(df_raw['trip_days'], errors='coerce').fillna(0)
        df_raw['total_earnings'] = clean_currency(df_raw['total_earnings'])

        # 5. Transform Raw Trips into VIN-Specific Summary
        # We group by VIN first, but keep vehicle_name for the label
        summary = df_raw.groupby('vin').agg({
            'vehicle_name': 'first', # Keeps the name associated with that VIN
            'trip_days': 'sum',
            'total_earnings': 'sum'
        }).reset_index()

        # Filter out VINs with 0 days (canceled or blocked)
        summary = summary[summary['trip_days'] > 0]

        # Map to app variables
        summary['display_name'] = summary['vehicle_name'] + " (" + summary['vin'].str[-5:] + ")" # Name + Last 5 of VIN
        summary['days_booked'] = summary['trip_days']
        summary['days_available'] = days_in_period
        summary['daily_rate'] = summary['total_earnings'] / summary['days_booked']
        summary['market_rate'] = market_avg
        
        # 6. Math Engine
        summary['utilization'] = summary['days_booked'] / summary['days_available']
        TARGET_UTIL = 0.75
        summary['potential_monthly_rev'] = (summary['days_available'] * TARGET_UTIL) * summary['market_rate']
        
        total_current = summary['total_earnings'].sum()
        total_potential = summary['potential_monthly_rev'].sum()
        revenue_gap = total_potential - total_current

        # 7. Display Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Earnings", f"${total_current:,.2f}")
        m2.metric("Target Revenue", f"${total_potential:,.2f}")
        
        gap_color = "inverse" if revenue_gap > 0 else "normal"
        m3.metric("Revenue Gap", f"${revenue_gap:,.2f}", delta=f"{-revenue_gap:,.2f}", delta_color=gap_color)

        st.divider()

        # 8. Visuals
        col_chart, col_list = st.columns([2, 1])

        with col_chart:
            fig = px.scatter(
                summary, x="daily_rate", y="utilization", 
                size="days_booked", color="display_name",
                hover_name="vin", # Show the full VIN on hover
                labels={"daily_rate": "Avg Daily Rate ($)", "utilization": "Utilization (%)"},
                title="Fleet Performance by VIN",
                template="plotly_white"
            )
            fig.add_hline(y=0.75, line_dash="dot", annotation_text="75% Target")
            st.plotly_chart(fig, use_container_width=True)

        with col_list:
            st.subheader("📋 VIN-Level Insights")
            summary = summary.sort_values(by='total_earnings', ascending=False)
            
            for _, row in summary.iterrows():
                u = row['utilization']
                
                # Using the Last 5 of VIN in the header for quick ID
                with st.expander(f"{row['display_name']}"):
                    st.caption(f"Full VIN: {row['vin']}")
                    st.write(f"**Utilization:** {u:.0%}")
                    st.write(f"**Avg Daily:** ${row['daily_rate']:.2f}")
                    
                    if u > 0.85:
                        st.error("Underpriced: High demand.")
                    elif u < 0.50:
                        st.warning("Overpriced: Low demand.")
                    else:
                        st.success("Dialed In: Optimal.")

    except Exception as e:
        st.error(f"Error processing VIN data: {e}")
else:
    st.info("Upload your trip export CSV. The app will now group data by VIN to separate identical vehicles.")
