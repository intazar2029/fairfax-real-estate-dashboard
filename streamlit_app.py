import streamlit as st
import pandas as pd
import sqlite3
import altair as alt

# Connect to the database
conn = sqlite3.connect("fairfax_real_estate_sales.db")

# Load data
@st.cache_data
def load_data():
    return pd.read_sql_query("SELECT * FROM sales", conn)

df = load_data()

# Convert date column
df['sale_date'] = pd.to_datetime(df['sale_date'])

# Sidebar filters
st.sidebar.header("Filters")
start_date = st.sidebar.date_input("Start Date", value=df['sale_date'].min().date())
end_date = st.sidebar.date_input("End Date", value=df['sale_date'].max().date())
# Clean and prep the options
df['sale_validity'] = df['sale_validity'].fillna('Unknown').str.strip()

validity_options = df['sale_validity'].unique().tolist()

# Set a safe default only if it's in the options
default_option = 'VALID' if 'VALID' in validity_options else validity_options[0]

validity_filter = st.sidebar.multiselect(
    "Sale Validity",
    options=validity_options,
    default=[default_option]
)

# Apply filters
# Ensure dates from sidebar are converted to timezone-aware
start_date = pd.to_datetime(start_date).tz_localize("UTC")
end_date = pd.to_datetime(end_date).tz_localize("UTC")

# Filter with timezone-aware comparison
filtered_df = df[
    (df['sale_date'] >= start_date) &
    (df['sale_date'] <= end_date) &
    (df['sale_validity'].isin(validity_filter))
]


# Main app
st.title("Fairfax County Real Estate Sales Dashboard")

# KPI Metrics
st.metric("Total Sales", f"{len(filtered_df):,}")
st.metric("Total Volume", f"${filtered_df['price'].sum():,.0f}")
st.metric("Avg. Sale Price", f"${filtered_df['price'].mean():,.0f}")

# Line chart of average monthly price
monthly_avg = filtered_df.groupby(filtered_df['sale_date'].dt.to_period('M'))['price'].mean().reset_index()
monthly_avg['sale_date'] = monthly_avg['sale_date'].astype(str)
st.subheader("Average Sale Price by Month")
line_chart = alt.Chart(monthly_avg).mark_line().encode(
    x='sale_date:T',
    y='price:Q'
).properties(width=700)
st.altair_chart(line_chart)

# Show raw data
st.subheader("Filtered Sales")
st.dataframe(filtered_df[['sale_date', 'property_id', 'price', 'sale_validity']].sort_values(by='sale_date', ascending=False).head(100))
