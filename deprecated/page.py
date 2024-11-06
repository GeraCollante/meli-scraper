import streamlit as st
import pandas as pd
import meli_scraper as ms
import car_features as cf
from datetime import date
import yaml

st.set_page_config(layout="wide")

def load_yaml(filepath):
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)

df = None
    
car_df_columns = [
    "title",
    "model",
    "brand",
    "thumbnail",
    "item_condition",
    "price_usd",
    "vehicle_year",
    "kilometers",
    "condition",
    "fuel_type",
    "transmission",
    "engine",
    "trim",
    "doors",
    "passenger_capacity",
    "power",
    "single_owner",
    "traction_control",
    "has_air_conditioning",
    "address_state_name",
    "address_city_name",
    "ratio"
]
    
# Search bar
st.title("Search Bar Example")
search_term = st.text_input("Enter a search term:")
is_car = st.checkbox("Is this a car?")

# Sliders section
sliders_dict = load_yaml("sliders_constraints.yml")
col1, col2, col3 = st.columns(3)
min_price, max_price = cf.create_slider(col1, "price [USD]", sliders_dict["price"])
min_km, max_km = cf.create_slider(col2, "km", sliders_dict["km"])
min_year, max_year = cf.create_slider(col3, "year",  sliders_dict["year"])


# Filters
option = st.selectbox(
    'Sort by: ',
    car_df_columns
    )

@st.cache
def search_ms(search_term, search_type="item", car=False):
    query = ms.Searcher("item", search_term, {})
    df = query.get_items(car=car)
    return df

@st.cache
def convert_df(input_df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return input_df.to_html(escape=False, formatters=dict(thumbnail=path_to_image_html))

def path_to_image_html(x, width=150):
    return f'<img src="'+ x + '" width="' + str(width) +'" >'

@st.cache
def create_and_update_df(df, columns, sort_by):
    if df:
        html = convert_df(df[columns].sort_values(by=sort_by))
        st.markdown(
            html,
            unsafe_allow_html=True
        )

        
## Search section
if search_term:
    df = search_ms(search_term, car=is_car)
    st.write(f"You searched for: {search_term}")
    df = df[df['kilometers'].between(min_km, max_km, inclusive="both")]
    df = df[df['price'].between(min_price, max_price, inclusive="both")]
    df = df[df['vehicle_year'].between(min_year, max_year, inclusive="both")]

    df['price_usd'] = df['price'].apply(lambda x: str(int(x)) + 'USD')
    
    create_and_update_df(df, car_df_columns, option)
    
#     df["thumbnail"] = df["thumbnail"].apply(ms.path_to_image_html)
#     st.dataframe(ms.pretty_display(df), width=None)
else:
    st.write("Please enter a search term to see results")
