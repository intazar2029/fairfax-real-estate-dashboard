import streamlit as st
import pandas as pd
import sqlite3
import altair as alt
import os

st.set_page_config(page_title="Fairfax Real Estate Dashboard", layout="wide")

# --- DATABASE CHECK ---
db_path = "fairfax_real_estate_sales_small.db"
if not os.path.exists(db_path):
    st.error("❌ Database file not found. Please upload 'fairfax_real_estate_sales_small.db' to the repo.")
    st.stop()

# --- CONNECT TO DB ---
conn = sqlite3.connect(db_path)

@st.cache_data
def load_data():
    df = pd.read_sql_query("SELECT * FROM sales", conn)
    df['sale_date'] = pd.to_datetime(df['sale_date'])
    df['sale_validity'] = df['sale_validity'].fillna("Unknown").str.strip().str.upper()
    return df

df = load_data()
if df.empty:
    st.warning("⚠️ No sales data loaded. Please check your database file.")
    st.stop()

# --- SIDEBAR FILTERS ---
st.sidebar.title("Filters")

validity_options = sorted(df['sale_validity'].dropna().unique().tolist())
default_validity = ['VALID'] if 'VALID' in validity_options else [validity_options[0]]
validity_filter = st.sidebar.multiselect("Sale Validity", options=validity_options, default=default_validity)

min_date = df['sale_date'].min().date()
max_date = df['sale_date'].max().date()
start_date = st.sidebar.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date)
end_date = st.sidebar.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)

# Ensure both dates are timezone-aware
start_date = pd.to_datetime(start_date).tz_localize("UTC")
end_date = pd.to_datetime(end_date).tz_localize("UTC")

# --- FILTERED DATA ---
filtered_df = df[
    (df['sale_date'] >= start_date) &
    (df['sale_date'] <= end_date) &
    (df['sale_validity'].isin(validity_filter))
]

st.title("📊 Fairfax County Real Estate Sales Dashboard")

# --- KPI METRICS ---
col1, col2, col3 = st.columns(3)
col1.metric("🧾 Total Sales", f"{len(filtered_df):,}")
col2.metric("💰 Total Volume", f"${filtered_df['price'].sum():,.0f}")
col3.metric("🏠 Avg. Sale Price", f"${filtered_df['price'].mean():,.0f}")

st.markdown("---")

# --- LINE CHART: Monthly Average Price ---
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

# --- HEATMAP ---
st.subheader("📊 Heatmap: Avg. Sale Price by Year & Month")
heatmap_df = (
    filtered_df.copy()
    .assign(year=filtered_df['sale_date'].dt.year, month=filtered_df['sale_date'].dt.month)
    .groupby(['year', 'month'])['price']
    .mean()
    .reset_index()
)

heatmap = alt.Chart(heatmap_df).mark_rect().encode(
    x=alt.X('month:O', title='Month'),
    y=alt.Y('year:O', title='Year'),
    color=alt.Color('price:Q', scale=alt.Scale(scheme='viridis')),
    tooltip=['year', 'month', 'price']
).properties(width=500, height=400)
st.altair_chart(heatmap)

# --- FREQUENTLY SOLD PROPERTIES ---
st.subheader("🔁 Most Frequently Sold Properties")
top_props = filtered_df['property_id'].value_counts().head(10).reset_index()
top_props.columns = ['property_id', 'sales_count']
st.dataframe(top_props)

# --- HISTOGRAM ---
st.subheader("💸 Sale Price Distribution (< $1.5M)")
hist_df = filtered_df[filtered_df['price'] < 1_500_000]
hist_chart = alt.Chart(hist_df).mark_bar().encode(
    alt.X("price:Q", bin=alt.Bin(maxbins=30), title="Price Range"),
    y='count()',
    tooltip=['count()']
).properties(width=800, height=400)
st.altair_chart(hist_chart)

# --- YOY CHANGE ---
st.subheader("📈 Year-over-Year % Change in Avg. Price")
yoy = (
    filtered_df
    .groupby(filtered_df['sale_date'].dt.year)['price']
    .mean()
    .pct_change()
    .multiply(100)
    .round(2)
    .reset_index(name="YoY_Change")
)
yoy.columns = ['year', 'YoY_Change']
st.line_chart(yoy.set_index('year'))

# --- SALES TABLE ---
st.subheader("📋 Filtered Sales Table")
st.dataframe(
    filtered_df[['sale_date', 'property_id', 'price', 'tax_year', 'sale_validity']]
    .sort_values(by='sale_date', ascending=False)
    .head(100),
    use_container_width=True
)
