import streamlit as st
import pandas as pd
import plotly.express as px
import calendar

# 1. Page Configuration
st.set_page_config(page_title="Monthly Fleet Optimizer", page_icon="🚗", layout="wide")
st.title("📅 Month-over-Month Revenue Optimizer")
st.markdown("### Individual monthly performance breakdown per VIN.")

def clean_currency(column):
    if column.dtype == 'object':
        return pd.to_numeric(column.replace(r'[\$,\s]', '', regex=True), errors='coerce').fillna(0)
    return column

# 2. Sidebar / Upload
with st.sidebar:
    st.header("1. Data Source")
    uploaded_file = st.file_uploader("Upload Trip Export CSV", type="csv")
    
    st.divider()
    st.header("2. Benchmarks")
    market_avg = st.number_input("Target Daily Rate ($)", value=75, min_value=1)
    target_util = st.slider("Target Utilization %", 50, 90, 75) / 100

if uploaded_file is not None:
    try:
        # 3. Data Loading & Cleaning
        df_raw = pd.read_csv(uploaded_file)
        df_raw.columns = df_raw.columns.str.strip().str.lower().str.replace(' ', '_')

        # Filter for valid trips
        if 'trip_status' in df_raw.columns:
            valid_statuses = ['completed', 'started', 'checked out', 'checked in']
            df_raw = df_raw[df_raw['trip_status'].str.lower().isin(valid_statuses)]

        # 4. Date Parsing & Month Extraction
        df_raw['trip_start'] = pd.to_datetime(df_raw['trip_start'], errors='coerce')
        df_raw = df_raw.dropna(subset=['trip_start'])
        
        # Create Month/Year identifiers
        df_raw['month_year'] = df_raw['trip_start'].dt.to_period('M')
        
        # 5. Month Selector
        available_months = sorted(df_raw['month_year'].unique(), reverse=True)
        selected_month = st.selectbox("Select Month for Analysis", available_months)
        
        # Filter data for the specific month
        df_month = df_raw[df_raw['month_year'] == selected_month].copy()
        
        # Calculate days in the selected month
        num_days = calendar.monthrange(selected_month.year, selected_month.month)[1]
        st.info(f"Analyzing {selected_month} ({num_days} total days)")

        # 6. Transform into VIN Summary for that month
        df_month['trip_days'] = pd.to_numeric(df_month['trip_days'], errors='coerce').fillna(0)
        df_month['total_earnings'] = clean_currency(df_month['total_earnings'])

        summary = df_month.groupby('vin').agg({
            'vehicle_name': 'first',
            'trip_days': 'sum',
            'total_earnings': 'sum'
        }).reset_index()

        summary['display_name'] = summary['vehicle_name'] + " (" + summary['vin'].str[-5:] + ")"
        summary['utilization'] = (summary['trip_days'] / num_days).clip(upper=1.0)
        summary['daily_rate'] = summary['total_earnings'] / summary['trip_days']
        
        # Potential vs Actual
        potential_rev = (num_days * target_util) * market_avg
        total_actual = summary['total_earnings'].sum()
        total_potential = potential_rev * len(summary) # Per vehicle
        revenue_gap = total_potential - total_actual

        # 7. Dashboard Layout
        col1, col2, col3 = st.columns(3)
        col1.metric("Month Earnings", f"${total_actual:,.2f}")
        col2.metric("Target Revenue", f"${total_potential:,.2f}")
        col3.metric("Revenue Gap", f"${revenue_gap:,.2f}", delta=f"{-revenue_gap:,.2f}", delta_color="inverse")

        st.divider()

        # 8. Charts
        fig = px.bar(
            summary.sort_values('utilization'), 
            x="utilization", 
            y="display_name", 
            orientation='h',
            title=f"Utilization by VIN: {selected_month}",
            color="utilization",
            color_continuous_scale="RdYlGn",
            labels={"utilization": "Utilization %", "display_name": "Vehicle"},
            range_x=[0, 1]
        )
        fig.add_vline(x=target_util, line_dash="dot", annotation_text=f"Target {target_util:.0%}")
        st.plotly_chart(fig, use_container_width=True)

        # 9. Detailed Action Table
        st.subheader("📋 Monthly Action Items")
        st.dataframe(
            summary[['display_name', 'trip_days', 'utilization', 'daily_rate', 'total_earnings']]
            .style.format({'utilization': '{:.1%}', 'daily_rate': '${:.2f}', 'total_earnings': '${:.2f}'}),
            use_container_width=True
        )

    except Exception as e:
        st.error(f"Error processing monthly data: {e}")
else:
    st.info("Upload your CSV. You will then be able to toggle between months in the dropdown menu.")
