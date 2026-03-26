import streamlit as st
import pandas as pd
import plotly.express as px

# 1. Page Configuration
st.set_page_config(page_title="Host Revenue Optimizer", page_icon="🚗", layout="wide")
st.title("🚗 Professional Fleet Revenue Optimizer")
st.markdown("### VIN-Level Analytics with Automatic Date Detection")

# Helper function to clean currency strings
def clean_currency(column):
    if column.dtype == 'object':
        return pd.to_numeric(column.replace(r'[\$,\s]', '', regex=True), errors='coerce').fillna(0)
    return column

# 2. Sidebar / Upload
with st.sidebar:
    st.header("1. Upload Trip Export")
    uploaded_file = st.file_uploader("Drop your Turo/Host CSV here", type="csv")
    
    st.divider()
    st.header("2. Market Benchmark")
    market_avg = st.number_input("Target Daily Rate ($)", value=75, min_value=1)
    st.info("The app will automatically detect the date range from your file.")

if uploaded_file is not None:
    try:
        # 3. Data Loading & Initial Cleaning
        df_raw = pd.read_csv(uploaded_file)
        df_raw.columns = df_raw.columns.str.strip().str.lower().str.replace(' ', '_')

        # Filter for only "Completed" or "Started" trips (ignores Canceled)
        if 'trip_status' in df_raw.columns:
            valid_statuses = ['completed', 'started', 'checked out', 'checked in']
            df_raw = df_raw[df_raw['trip_status'].str.lower().isin(valid_statuses)]

        # 4. Automatic Date Detection
        df_raw['trip_start'] = pd.to_datetime(df_raw['trip_start'], errors='coerce')
        df_raw['trip_end'] = pd.to_datetime(df_raw['trip_end'], errors='coerce')
        
        start_date = df_raw['trip_start'].min()
        end_date = df_raw['trip_end'].max()
        
        # Calculate span of the report
        if pd.notnull(start_date) and pd.notnull(end_date):
            days_in_period = (end_date - start_date).days
            if days_in_period <= 0: days_in_period = 1 
        else:
            days_in_period = 30 # Fallback

        st.sidebar.success(f"📅 Report Span: {days_in_period} Days")
        st.sidebar.caption(f"{start_date.date()} to {end_date.date()}")

        # 5. Math Readiness
        df_raw['trip_days'] = pd.to_numeric(df_raw['trip_days'], errors='coerce').fillna(0)
        df_raw['total_earnings'] = clean_currency(df_raw['total_earnings'])

        # 6. Transform into VIN Summary
        summary = df_raw.groupby('vin').agg({
            'vehicle_name': 'first',
            'trip_days': 'sum',
            'total_earnings': 'sum'
        }).reset_index()

        # Final Calculations
        summary['display_name'] = summary['vehicle_name'] + " (" + summary['vin'].str[-5:] + ")"
        summary['utilization'] = (summary['trip_days'] / days_in_period).clip(upper=1.0)
        summary['daily_rate'] = summary['total_earnings'] / summary['trip_days']
        
        # Revenue Forecasting
        TARGET_UTIL = 0.75
        summary['potential_rev'] = (days_in_period * TARGET_UTIL) * market_avg
        
        total_current = summary['total_earnings'].sum()
        total_potential = summary['potential_rev'].sum()
        revenue_gap = total_potential - total_current

        # 7. Layout - Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Actual Earnings", f"${total_current:,.2f}")
        m2.metric(f"Target ({TARGET_UTIL:.0%})", f"${total_potential:,.2f}")
        m3.metric("Revenue Gap", f"${revenue_gap:,.2f}", delta=f"{-revenue_gap:,.2f}", delta_color="inverse")

        st.divider()

        # 8. Visuals
        col_chart, col_list = st.columns([2, 1])

        with col_chart:
            fig = px.scatter(
                summary, x="daily_rate", y="utilization", 
                size="trip_days", color="display_name",
                hover_name="vin",
                labels={"daily_rate": "Daily Rate ($)", "utilization": "Utilization (%)"},
                title=f"Fleet Performance ({days_in_period} Day Span)",
                template="plotly_white",
                range_y=[0, 1.1] # Caps the view at 110% for clarity
            )
            fig.add_hline(y=0.75, line_dash="dot", annotation_text="75% Target")
            st.plotly_chart(fig, use_container_width=True)

        with col_list:
            st.subheader("📋 VIN Action Plan")
            for _, row in summary.sort_values('utilization', ascending=False).iterrows():
                with st.expander(f"{row['display_name']}"):
                    st.write(f"**Util:** {row['utilization']:.1%}")
                    st.write(f"**Earned:** ${row['total_earnings']:,.2f}")
                    
                    if row['utilization'] > 0.85:
                        st.error("Action: Raise Daily Price")
                    elif row['utilization'] < 0.50:
                        st.warning("Action: Lower Daily Price")
                    else:
                        st.success("Action: Strategy Dialed In")

    except Exception as e:
        st.error(f"Critical Error: {e}")
        st.info("Check if your CSV columns match the Turo/Standard format.")

else:
    st.info("Please upload your trip export CSV to begin. The app will automatically handle date ranges and canceled trips.")
