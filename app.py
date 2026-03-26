import streamlit as st
import pandas as pd
import plotly.express as px
import calendar

# 1. Page Configuration
st.set_page_config(page_title="Monthly Fleet Optimizer", page_icon="🚗", layout="wide")
st.title("📅 Monthly Performance & Trend Optimizer")
st.markdown("### Tracking by VIN & Month-over-Month Trends")

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
    st.info("The app groups by VIN and calculates the specific days in each month.")

if uploaded_file is not None:
    try:
        # 3. Data Loading & Cleaning
        df_raw = pd.read_csv(uploaded_file)
        df_raw.columns = df_raw.columns.str.strip().str.lower().str.replace(' ', '_')

        # Filter for valid trips
        if 'trip_status' in df_raw.columns:
            valid_statuses = ['completed', 'started', 'checked out', 'checked in']
            df_raw = df_raw[df_raw['trip_status'].str.lower().isin(valid_statuses)]

        # 4. Date Parsing
        df_raw['trip_start'] = pd.to_datetime(df_raw['trip_start'], errors='coerce')
        df_raw = df_raw.dropna(subset=['trip_start'])
        df_raw['month_year'] = df_raw['trip_start'].dt.to_period('M')

        # 5. Month Selector
        available_months = sorted(df_raw['month_year'].unique(), reverse=True)
        selected_month = st.selectbox("Select Month for Analysis", available_months)
        
        # Filter data for the specific month
        df_month = df_raw[df_raw['month_year'] == selected_month].copy()
        num_days = calendar.monthrange(selected_month.year, selected_month.month)[1]

        # 6. Current Month Summary (Grouped by VIN)
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

        # 7. Metrics
        total_actual = summary['total_earnings'].sum()
        total_potential = (num_days * target_util * market_avg) * len(summary)
        revenue_gap = total_potential - total_actual

        c1, c2, c3 = st.columns(3)
        c1.metric(f"Earnings ({selected_month})", f"${total_actual:,.2f}")
        c2.metric("Target Revenue", f"${total_potential:,.2f}")
        
        # Color the gap based on performance
        gap_color = "inverse" if revenue_gap > 0 else "normal"
        c3.metric("Revenue Gap", f"${revenue_gap:,.2f}", delta=f"{-revenue_gap:,.2f}", delta_color=gap_color)

        st.divider()

        # 8. Charts: Current Month Bar & 6-Month Trend
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader(f"Utilization by VIN: {selected_month}")
            fig_bar = px.bar(
                summary.sort_values('utilization'), 
                x="utilization", y="display_name", orientation='h',
                color="utilization", color_continuous_scale="RdYlGn", range_x=[0, 1],
                labels={"utilization": "Utilization %", "display_name": "Vehicle (VIN)"}
            )
            fig_bar.add_vline(x=target_util, line_dash="dot", annotation_text=f"Target {target_util:.0%}")
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_right:
            st.subheader("📈 6-Month Earnings Trend")
            # Group all data by month for the trend line
            trend = df_raw.copy()
            trend['total_earnings'] = clean_currency(trend['total_earnings'])
            trend_summary = trend.groupby('month_year').agg({'total_earnings': 'sum'}).reset_index()
            trend_summary['month_year'] = trend_summary['month_year'].astype(str)
            
            fig_trend = px.line(trend_summary.tail(6), x='month_year', y='total_earnings', 
                               markers=True, title="Total Fleet Revenue Trends")
            st.plotly_chart(fig_trend, use_container_width=True)

        # 9. Detailed Action Table
        st.subheader("🚗 Vehicle Action Items")
        st.dataframe(
            summary[['display_name', 'utilization', 'daily_rate', 'total_earnings']]
            .rename(columns={'display_name': 'Vehicle (VIN)'})
            .style.format({'utilization': '{:.1%}', 'daily_rate': '${:.2f}', 'total_earnings': '${:.2f}'}),
            use_container_width=True
        )

    except Exception as e:
        st.error(f"Error processing data: {e}")
        st.info("Check if your CSV headers include: 'vin', 'trip_days', 'total_earnings', and 'trip_start'.")
else:
    st.info("Upload your CSV. You can then toggle between months and see the 6-month revenue trend.")
