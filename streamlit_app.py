import streamlit as st
import pandas as pd
import sqlite3
import altair as alt
import os

st.set_page_config(page_title="Fairfax Real Estate Dashboard", layout="wide")

# --- CHECK FOR DATABASE BEFORE CACHING ---
db_path = "fairfax_real_estate_sales_small.db"
if not os.path.exists(db_path):
    st.error("❌ Database file not found. Please upload 'fairfax_real_estate_sales_small.db' to the repo.")
    st.stop()

# --- CONNECTION ---
conn = sqlite3.connect(db_path)

# --- LOAD DATA ---
@st.cache_data
def load_data():
    df = pd.read_sql_query("SELECT * FROM sales", conn)
    df['sale_date'] = pd.to_datetime(df['sale_date'])
    df['sale_validity'] = df['sale_validity'].fillna("Unknown").str.strip().str.upper()
    return df

df = load_data()


# --- SIDEBAR FILTERS ---
st.sidebar.title("Filters")

# Sale validity filter
validity_options = sorted(df['sale_validity'].unique())
default_validity = ['VALID'] if 'VALID' in validity_options else [validity_options[0]]
validity_filter = st.sidebar.multiselect("Sale Validity", options=validity_options, default=default_validity)

# Date range filter
min_date = df['sale_date'].min().date()
max_date = df['sale_date'].max().date()
start_date = st.sidebar.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date)
end_date = st.sidebar.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)

# Convert to UTC-aware if needed
start_date = pd.to_datetime(start_date).tz_localize("UTC")
end_date = pd.to_datetime(end_date).tz_localize("UTC")

# --- FILTER DATA ---
filtered_df = df[
    (df['sale_date'] >= start_date) &
    (df['sale_date'] <= end_date) &
    (df['sale_validity'].isin(validity_filter))
]

# --- DASHBOARD CONTENT ---
st.title("📊 Fairfax County Real Estate Sales Dashboard")

col1, col2, col3 = st.columns(3)
col1.metric("🧾 Total Sales", f"{len(filtered_df):,}")
col2.metric("💰 Total Volume", f"${filtered_df['price'].sum():,.0f}")
col3.metric("🏠 Avg. Sale Price", f"${filtered_df['price'].mean():,.0f}")

st.markdown("---")

# --- MONTHLY TREND CHART ---
monthly_avg = (
    filtered_df
    .groupby(filtered_df['sale_date'].dt.to_period("M"))['price']
    .mean()
    .reset_index()
)
monthly_avg['sale_date'] = monthly_avg['sale_date'].astype(str)

st.subheader("📈 Average Sale Price by Month")
chart = alt.Chart(monthly_avg).mark_line(point=True).encode(
    x='sale_date:T',
    y='price:Q',
    tooltip=['sale_date', 'price']
).properties(width=800, height=400)
st.altair_chart(chart)

# --- SALES TABLE ---
st.subheader("📋 Filtered Sales")
st.dataframe(
    filtered_df[['sale_date', 'property_id', 'price', 'tax_year', 'sale_validity']]
    .sort_values(by='sale_date', ascending=False)
    .head(100),
    use_container_width=True
)
