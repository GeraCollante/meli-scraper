#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import requests
import json
from pygments import highlight, lexers, formatters
import sys
from pprint import PrettyPrinter
from bs4 import BeautifulSoup

from tqdm import tqdm
tqdm.pandas()
from IPython.core.display import HTML# Create a dataframe using pandas library

cd ..

get_ipython().run_line_magic('load_ext', 'autoreload')
get_ipython().run_line_magic('autoreload', '2')

pd.set_option('display.max_columns', None)
pd.set_option('max_colwidth', 400)
pd.set_option('display.max_columns', 500)


from meli_scraper import pretty_display
import meli_scraper as ms

query = ms.Searcher("item", "auriculares", {"HEADPHONE_FORMAT":"182351", "IS_WIRELESS":"242085", 
                                            "price": "30000.0-75000.0",
                                            "ITEM_CONDITION":"2230284"})

query.show_filters()


def explore_by_param(query, param):
    """
    Explores items based on a specified parameter by going beyond the 1050 item limit imposed by MercadoLibre's API.

    Args:
        query (object): A query object with query_info and update methods.
        param (str): The filter ID to apply.

    Returns:
        list: A list of items with the specified filter applied.
    """

    # Items grouped by a specific parameter of the available filters
    items_grouped_by_filter = [
        item["values"]
        for item in query.query_info["available_filters"]
        if item["id"] == param
    ][0]

    items_list = []

    # Start to iterate between the different parameters of the filter
    for item in tqdm(items_grouped_by_filter):
        try:
            # Update the query and subsequently the items collected by get_items function
            query.update({param: item["id"]})
        except Exception as e:
            print(f"Error: {e}")
            continue
        items_list.append(query.get_items(disable_tqdm=True))

    return items_list


dfs = explore_by_param(query, "VOLUME_CAPACITY")

final_df = pd.concat(dfs)

final_df.groupby(["brand", "model"]).agg(max_price=("price", "max"),
                                         min_price=("price", "min"),
                                         mean_price=("price", "mean"),
                                         n_devices=("id", "size")
                                        ).sort_values("n_devices").tail(20)

final_df = final_df.sort_values(by="sold_quantity",ascending=False).drop_duplicates(subset=["seller_link", "title"], keep="first")

final_df = final_df[final_df.price<45_000]

final_df = final_df[final_df.price>15_000]

final_df.drop(columns=["reviews", "ratingValue", "reviewCount"]).drop_duplicates()


final_df = final_df.drop(columns=["reviews"]).drop_duplicates(subset=["id"])

final_df["review_info"] = final_df.id.progress_apply(get_review_info)


final_df.sort_values("ratingCount", ascending=False)

features = final_df["permalink"].progress_apply(ms.get_features)

final_df = final_df.join(pd.DataFrame(features).permalink.apply(pd.Series))

final_df_ = final_df.dropna(subset=["ratingValue"])


final_df_ = final_df_.drop_duplicates(subset=["reviews"])


final_df_["review_info"] = final_df_.id.progress_apply(get_review_info)


get_review_info("MLA1451044135")


import requests
from bs4 import BeautifulSoup

def get_review_info(item_id):
    """
    Fetches the average rating and rating label for a given MercadoLibre item ID.

    Args:
        item_id (str): The MercadoLibre item ID (e.g., "MLA1436287318").

    Returns:
        dict: A dictionary containing 'average_rating' and 'rating_label'.
              Returns None for values if they are not found.
    """
    # Construct the URL using the provided item_id
    url = (
        f"https://www.mercadolibre.com.ar/noindex/catalog/reviews/{item_id}?noIndex=true&access=view_all&modal=true&controlled=true"
    )
    
    # Define headers to mimic a browser request
    # headers = {
    #     "User-Agent": (
    #         "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    #         "AppleWebKit/537.36 (KHTML, like Gecko) "
    #         "Chrome/116.0.0.0 Safari/537.36"
    #     )
    # }

    try:
        # Send a GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses

        # Parse the HTML content with BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        return soup

        # Extract the average rating
        average_rating_element = soup.find(
            class_='ui-review-capability__rating__average ui-review-capability__rating__average--desktop'
        )
        print(average_rating_element)
        average_rating = (
            average_rating_element.get_text(strip=True)
            if average_rating_element else None
        )

        # Extract the rating label
        rating_label_element = soup.find(
            class_='ui-review-capability__rating__label'
        )
        rating_label = (
            rating_label_element.get_text(strip=True)
            if rating_label_element else None
        )

        return {
            'average_rating': average_rating,
            'rating_label': rating_label
        }

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")  # e.g., 404 Not Found
    except requests.exceptions.ConnectionError:
        print("Error connecting to the website. Please check your network.")
    except requests.exceptions.Timeout:
        print("The request timed out.")
    except requests.exceptions.RequestException as err:
        print(f"An error occurred: {err}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    # In case of any error, return None values
    return {
        'average_rating': None,
        'rating_label': None
    }


final_df_[final_df_.ratingValue>=4.8].sort_values("ratingCount", ascending=False).drop(columns=["reviews"]).head(20)

import plotly.express as px

px.scatter(final_df_, x="ratingValue", y="price")

final_df_.sort_values("reviewCount", ascending=False)[["title", "reviews", "ratingValue", "reviewCount"]]

features = df["permalink"].progress_apply(ms.get_features)

features.dropna()

import re

def str2int(x):
    """
    Extract all integers from a string and return them as a single integer.
    """
    matches = re.findall(r'\d+', x)
    if matches:
        # Concatenate all matches into a single string
        concatenated = ''.join(matches)
        # Check if the concatenated string can be converted to an integer
        if concatenated.isdigit():
            return int(concatenated)
    return None

def extract_features(url):
    """
    Extracts relevant features from a given URL.

    Args:
        url (str): The URL from which to extract the features.

    Returns:
        dict: A dictionary containing the extracted features or None if an error occurs.
    """

    try:
        response = requests.get(url)
        if response.status_code != 200:
            raise ValueError(f'Error: Invalid URL {url}')

        soup = BeautifulSoup(response.text, 'html.parser')
        features = {}

        # Extract sold information
        sold_element = soup.find('span', class_='ui-pdp-subtitle')
        if sold_element:
            sold_count = str2int(sold_element.text)
            features['sold'] = sold_count

        # Extract review information
        review_script = soup.find("script", type="application/ld+json")
        if review_script:
            review_data = eval(review_script.text)
            reviews = review_data.get('review', [])
            aggregate_rating = review_data.get('aggregateRating', {})
            features['reviews'] = reviews
            if '@type' in aggregate_rating:
                del aggregate_rating['@type']
            features.update(aggregate_rating)

        # Extract table information
        table_elements = soup.find_all('table')
        if table_elements:
            features_df = pd.concat(pd.read_html(str(table_elements)))
            features_dict = dict(zip(features_df[0], features_df[1]))
            features.update(features_dict)

        return features
    except Exception as e:
        print(f"Error: {e}")
        return None


final_df["permalink"].iloc[:5].progress_apply(extract_features)

df_ = final_df.join(my_features.apply(pd.Series))

df_ = df_.dropna(subset=["reviewCount"])


from bs4 import BeautifulSoup
import requests

def get_bag_dimensions(url):
    class_ = "andes-table__column andes-table__column--left ui-vpp-striped-specs__row__column"
    
    # Send a GET request to the specified URL
    response = requests.get(url)
    
    # Create a BeautifulSoup object with the response content
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Find the elements with the specified class
    elements = soup.find_all(class_=class_)
    
    # Extract the bag dimensions from the elements
    dimensions = []
    for element in elements:
        dimensions.append(element.get_text())
    
    return dimensions


final_df["bag_dims"] = final_df.permalink.progress_apply(get_bag_dimensions)


final_df["dims"] =final_df["bag_dims"].apply(lambda x: [item for item in x if 'cm' in item])

import plotly.express as px

px.scatter(df_.reset_index(), 
           x="ratingValue", 
           y="price", 
           template="plotly_white",
           size="reviewCount",
           color="brand",
           height=600,
           width=600,
           hover_data=["title", "price", "index"])

final_df = final_df[final_df.reviewCount>10]

final_df["ratings"] = final_df["id"].progress_apply(get_ratings)

final_df = pd.concat([final_df, pd.DataFrame(final_df.features)], axis=1)

final_df = pd.concat([final_df, final_df.features.apply(pd.Series)], axis=1)



final_df = pd.concat([final_df, ratings.rename("stars")], axis=1)


# In[236]:


final_df = final_df.join(final_df.stars.apply(pd.Series))


# In[45]:


ratings = final_df["id"].progress_apply(get_ratings)


# In[46]:


final_df["ratings"] = ratings


# In[50]:


final_df = final_df.join(final_df.ratings.apply(pd.Series))


# In[53]:


final_df.sort_values(by="1_star", ascending=False)


# In[204]:


final_df = final_df.join(ratings.apply(pd.Series))


# In[166]:


final_df = pd.concat([final_df, features.rename("features")], axis=1)


# In[169]:


final_df = final_df.join(final_df.features.apply(pd.Series))


# In[244]:


final_df


# In[17]:


query.update({
    'IS_CARRY_ON': '242085',
    'ITEM_CONDITION':'2230284',
    'WITH_WHEELS':'242085'
})


# In[ ]:


query.update({'price':'8000.0-15000.0', 
              'ITEM_CONDITION':'2230284', 
              'GENDER':'339666',
              'category':'MLA1271'})
# , 
#               'ITEM_CONDITION':'2230284',
#               'FILTRABLE_SIZE':'12189531',
#               'MAIN_COLOR':'2450308',
#               # 'category': 'MLA120350',
#               #'BACKPACK_CAPACITY': '[15L-21L)',
#               'GENDER':'339665',
#               #'MAIN_COLOR':'Negro'
#              })

query.show_filters()

query.update({'price':'*-10000.0', 
              'ITEM_CONDITION':'2230284',
              'FILTRABLE_SIZE':'12189531',
              'MAIN_COLOR':'2450308',
              # 'category': 'MLA120350',
              #'BACKPACK_CAPACITY': '[15L-21L)',
              'GENDER':'339665',
              #'MAIN_COLOR':'Negro'
             })
#               'ITEM_CONDITION':'2230284', 
#               # 'category':'MLA373840', 
#               # 'VIDEO_GAME_PLATFORM':'PS4'
#              })
query.show_filters()

df = query.get_items(car=False)

df = df[df.sold_quantity>1]


df = df[df.price<100_000]


# In[158]:


features = df.permalink.progress_apply(ms.get_features)


# In[33]:


df = df.join(pd.Series(features, name="features"))


# In[34]:


df = df.join(df.features.apply(pd.Series))


# In[35]:


df = df.dropna(subset=["ratingValue"])


# In[38]:


df.columns


# In[37]:


import plotly.express as px


# In[49]:


df = df.reset_index()


# In[57]:


# df


# In[58]:


# df[df["index"]==14]


# In[59]:


df.columns


# In[125]:


get_ipython().system('pip install --upgrade selenium')


# In[1]:


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service
import time

# Especifica la ruta al geckodriver si no está en el PATH
geckodriver_path = '/home/gerac/geckodriver'
service = Service(executable_path=geckodriver_path)

# Inicializar el WebDriver de Firefox con el servicio
driver = webdriver.Firefox(service=service)

try:
    # Navegar a Google
    driver.get('https://www.google.com')

    # Esperar a que el elemento de búsqueda esté presente
    time.sleep(2)  # Espera 2 segundos

    # Encontrar el cuadro de búsqueda por su nombre
    search_box = driver.find_element(By.NAME, 'q')

    # Escribir una consulta en el cuadro de búsqueda
    search_box.send_keys('Selenium con Python')

    # Presionar Enter
    search_box.send_keys(Keys.RETURN)

    # Esperar unos segundos para ver los resultados
    time.sleep(5)

finally:
    # Cerrar el navegador
    driver.quit()


# In[111]:


from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_ratings(MLA: str) -> dict:
    """
    Extracts ratings from the given URL using Selenium.

    Args:
        MLA (str): The code used to construct the URL from which to extract the ratings.

    Returns:
        dict: A dictionary of extracted ratings in decimal format.
    """
    
    # Strings
    base_url = "https://articulo.mercadolibre.com.ar/noindex/catalog/reviews/"
    url_params = "?noIndex=true&access=view_all&modal=true"
    css_rating = 'span.ui-review-capability-rating__level__progress-bar__fill-background'
    css_mean_review_value = 'p.ui-review-capability__rating__average.ui-review-capability__rating__average--desktop'
    css_n_reviews = "p.ui-review-capability__rating__label"

    # Set up a Selenium webdriver instance with the specified options
    url = f"{base_url}{MLA}{url_params}"
    options = Options()
    options.headless = True
    driver = webdriver.Chrome(options=options)

    try:
        # Load the webpage in the webdriver
        driver.get(url)

        # Wait for the DOM to finish loading
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, css_rating)))

        # Find all the span elements with the specified class and extract the width attribute from each span
        spans = driver.find_elements(By.CSS_SELECTOR, css_rating)
        ratings = [float(span.get_attribute('style').split(':')[1].replace(';','').strip('%')) / 100 for span in spans]
        
        # Fetch mean review value and number of reviews
        mean_review_value = driver.find_element(By.CSS_SELECTOR, css_mean_review_value).text
        n_reviews = driver.find_element(By.CSS_SELECTOR, css_n_reviews).text
        
        # Construct the ratings dictionary
        ratings_dict = {'5_star': ratings[0], 
                        '4_star': ratings[1], 
                        '3_star': ratings[2], 
                        '2_star': ratings[3], 
                        '1_star': ratings[4],
                        'mean_review_value': mean_review_value,
                        'n_reviews': n_reviews}
    finally:
        # Close the webdriver
        driver.quit()

    return ratings_dict


# In[115]:


MLA = "MLA674386940"
url=f"https://articulo.mercadolibre.com.ar/noindex/catalog/reviews/{MLA}?noIndex=true&access=view_all&modal=true"

# Set up a Selenium webdriver instance with the specified options
driver = webdriver.Chrome(options=options)

# Load the webpage in the webdriver
driver.get(url)

# Wait for the DOM to finish loading
wait = WebDriverWait(driver, 5)
wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'span.ui-review-capability-rating__level__progress-bar__fill-background')))

# Find all the span elements with the specified class
spans = driver.find_elements(By.CSS_SELECTOR, 'span.ui-review-capability-rating__level__progress-bar__fill-background')


# In[114]:


get_ipython().run_line_magic('pip', 'install webdriver-manager')


# In[104]:


df = df[df.reviewCount>10]


# In[116]:


final_df["ratings"] = final_df["id"].progress_apply(get_ratings)


# In[112]:


df["ratings"] = df["id"].progress_apply(get_ratings)


# In[39]:


df = df.join(df["ratings"].apply(pd.Series))


# In[49]:
