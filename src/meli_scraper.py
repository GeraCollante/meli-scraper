import re
import yaml

import requests
import json
import pandas as pd

from IPython.core.display import HTML
from bs4 import BeautifulSoup
from pygments import formatters, highlight, lexers
from tqdm import tqdm

pd.set_option("display.max_columns", None)
pd.set_option("max_colwidth", 400)

path_to_image_html = lambda x: '<img src="'+ x + '" width="90" >'

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


def get_json(url, params):
    # Use the requests.get function to send the HTTP request and retrieve the response
    response = requests.get(url, params=params)

    # Check the response status code to ensure that the request was successful
    if response.status_code != 200:
        raise ValueError(f'Request to {url} failed with status code {response.status_code}')

    # Use the json.loads function to parse the JSON data in the response
    return json.loads(response.text)


def pretty_json(my_json):
    # Use the json.dumps function to convert the JSON data to a string
    json_str = json.dumps(my_json, indent=4, sort_keys=True)

    # Use the highlight function to colorize the JSON string
    colorful_json = highlight(json_str, lexers.JsonLexer(), formatters.TerminalFormatter())

    # Print the colorized JSON string
    print(colorful_json)


def get_dolarblue():
    URL = "https://www.dolarsi.com/api/api.php?type=valoresprincipales"

    # Use the requests.get function to send the HTTP request and retrieve the response
    response = requests.get(URL)

    # Check the response status code to ensure that the request was successful
    if response.status_code != 200:
        raise ValueError(f'Request to {URL} failed with status code {response.status_code}')

    # Parse the JSON data in the response
    json_data = response.json()

    # Get the exchange rate from the JSON data
    # exchange_rate = float(json_data[1]["casa"]["venta"].replace(",", "."))
    exchange_rate = float(json_data[1]["casa"]["venta"].replace(".", "").replace(",", "."))

    return exchange_rate


def pretty_display(df):
    """
    Display the DataFrame as an HTML table with images.
    """
    # Set the 'thumbnail' column to display as images
    df_formatters = {'thumbnail': path_to_image_html}

    # Convert the DataFrame to an HTML table
    html = df.to_html(escape=False, formatters=df_formatters)

    # Display the HTML table
    return HTML(html)

# blue = get_dolarblue()


def convert_usd(currency, price):
    return price/blue if currency == 'ARS' else price


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


def get_features(x):
    try:
        response = requests.get(x)
        if response.status_code != 200:
            raise ValueError(f'Error: Invalid URL {x}')

        soup = BeautifulSoup(response.text, 'html.parser')
        features = {}

        # Extract sold information
        sold = soup.find('span', class_='ui-pdp-subtitle')
        if sold:
            sold = str2int(sold.text)
            features['sold'] = sold

        # Extract review information
        review_script = soup.find("script", type="application/ld+json")
        if review_script:
            review_data = eval(review_script.text)
            reviews = review_data.get('review', [])
            rating = review_data.get('aggregateRating', {})
            features['reviews'] = reviews
            if '@type' in rating:
                del rating['@type']
            features = {**features, **rating}

        # Extract table information
        table = soup.find_all('table')
        if table:
            features_df = pd.concat(pd.read_html(str(table)))
            features_dict = dict(zip(features_df[0], features_df[1]))
            features = {**features, **features_dict}

        return features
    except Exception as e:
        return None
    
    
class Searcher:
    """
    A class for searching for items on the MercadoLibre website.

    Parameters
    ----------
    type_search : str
        The type of search to perform. Options are 'cat' (category search), 'item' (item search), or 'seller' (seller search).
    query : str
        The query to search for.
    params : dict, optional
        A dictionary of additional parameters to include in the search query.

    Attributes
    ----------
    type_search : str
        The type of search to perform.
    query : str
        The query to search for.
    filters : list
        A list of filters to apply to the search results.
    filters_dict : dict
        A dictionary of filters to apply to the search results.
    items : list
        A list of items returned from the search query.
    df : pandas.DataFrame
        A DataFrame containing the search results.
    params : dict
        A dictionary of parameters for the search query.
    url : str
        The URL for the search query.
    query_info : dict
        A dictionary containing the results of the search query.
    total_items : int
        The total number of items returned by the search query.
    """
    def __init__(self, type_search, query, params={}, country="A"):
        self.type_search = type_search
        self.query = query
        self.filters = []
        self.filters_dict = {}
        self.items = []
        self.df = pd.DataFrame()

        # set params for the query
        self.params = {
            "filters": "availability=available",
            "sort_by": "price",
        }
        self.params.update(params)
        
        # set the type of query
        if type_search == "cat":
            self.url = f"https://api.mercadolibre.com/sites/ML{country}/search?category=" + query
        elif type_search == "item":
            self.url = f"https://api.mercadolibre.com/sites/ML{country}/search?q=" + query.replace(" ", "%20")
        elif type_search == "seller":
            self.url = f"https://api.mercadolibre.com/sites/ML{country}/search?seller_id=" + query.replace(" ", "%20")
        else:
            raise ValueError("Error: Unknown search type.")
        
        # get the json
        self.query_info = get_json(self.url, params)
        self.total_items = self.query_info["paging"]["total"]


    def update(self, params):
        """
        Update the query with the new params.

        Parameters
        ----------
        params : dict
            The new params to update the query.
        """
        if not isinstance(params, dict):
            raise TypeError("Params must be a dictionary.")
        
        # Check if filters_dict exists, if not create it
        if not self.filters_dict:
            self.get_filters()
        
        # Map the values in `params` to their corresponding values in `self.filters_dict`
        # if they exist, or use the original value if not.
        params = {k:(self.filters_dict[k][v] if self.filters_dict[k].get(v) else v) for k,v in params.items()}
        
        # Update the params
        self.params.update(params)
        
        # Update the query
        self.query_info = get_json(self.url, self.params)
        if self.query_info:
            self.total_items = self.query_info["paging"]["total"]
        else:
            self.total_items = 0


    def load_params(self, filename):
        """
        This functions takes a filename of a .yml file and loads the params

        Parameters
        ----------
        filename : str
            The filename of the .yml file
        """
        with open(filename, 'r') as stream:
            try:
                params = yaml.safe_load(stream)
                self.update(params)
            except yaml.YAMLError as exc:
                print(exc)


    def get_items(self, params={}, car = False, full = True, disable_tqdm = False):
        """
        Iterate using index to retrieve the data
        and collect the items in a list.

        Parameters
        ----------
        params : dict, optional
            List of params, by default {}
        car : bool, optional
            In case of retrieve data of car set this to True, by default False
        full : bool, optional
            To get all the items availables, by default True

        Returns
        -------
        pd.DataFrame
            Dataframe with the items.
        """
        self.params.update(params)
        self.items.clear()
        
        step = 50

        if not full:
            self.total_items = 50

        if self.total_items > 1050:
            # print("Max items quantity is 1050.")
            self.total_items = 1050

        for i in tqdm(range(0, self.total_items, step), desc="Getting items", leave=False, disable=disable_tqdm):
            self.params["offset"] = i
            
            results = get_json(self.url, self.params).get("results", [])
            
            for result in results:
                dict_atrib = {}

                # Principal features
                dict_atrib["ID"] = result["id"]
                dict_atrib["TITLE"] = result["title"]
                dict_atrib["SELLER_ID"] = result.get("seller", {}).get("id", None)
                dict_atrib["SELLER_LINK"] = result.get("seller", {}).get("nickname", None)
                dict_atrib["PRICE"] = result["price"]
                dict_atrib["CURRENCY_ID"] = result["currency_id"]
                dict_atrib["AVAILABLE_QUANTITY"] = result["available_quantity"]
                # dict_atrib["SOLD_QUANTITY"] = result["sold_quantity"]
                dict_atrib["CONDITION"] = result["condition"]
                dict_atrib["PERMALINK"] = result["permalink"]
                dict_atrib["THUMBNAIL"] = result["thumbnail"]

                # Attributes of the item
                for attribute in result["attributes"]:
                    dict_atrib[attribute["id"]] = attribute["value_name"]

                #if not car:
                    #dict_atrib["QUANTITY_INSTALLMENTS"] = result["installments"].get("quantity")
                    #dict_atrib["AMOUNT_INSTALLMENTS"] = result["installments"].get("amount")
                    #dict_atrib["RATE_INSTALLMENTS"] = result["installments"].get("rate")

                # Others features
                dict_atrib["SHIPPING"] = result["shipping"]["free_shipping"]
                #dict_atrib["ADDRESS_STATE_ID"] = result["address"]["state_id"]
                #dict_atrib["ADDRESS_STATE_NAME"] = result["address"]["state_name"]
                #dict_atrib["ADDRESS_CITY_ID"] = result["address"]["city_id"]
                #dict_atrib["ADDRESS_CITY_NAME"] = result["address"]["city_name"]
                dict_atrib["CATEGORY_ID"] = result["category_id"]
                dict_atrib["DOMAIN_ID"] = result["domain_id"]

                self.items.append(dict_atrib)

        # Create the dataframe
        self.df = pd.DataFrame(self.items)
        
        # Add remaining features of car
        if car:
            self.df['PRICE'] = self.df.apply(lambda row: convert_usd(row['CURRENCY_ID'], row['PRICE']), axis=1)
            self.df['CURRENCY_ID'] = 'USD'
            self.df['KILOMETERS'] = pd.to_numeric(self.df.KILOMETERS.str.replace(' km',''), errors='coerce')
            self.df['VEHICLE_YEAR'] = self.df.VEHICLE_YEAR.astype(int)
            self.df['RATIO'] = self.df.VEHICLE_YEAR/(self.df.PRICE * self.df.KILOMETERS)*1_000_000

        self.df.columns = [x.lower() for x in self.df.columns]
        return self.df


    def get_filters(self):
        """
        Get the filters of the query.
        """
        self.filters.clear()
        
        for filt in self.query_info["available_filters"]:
            filt_id = filt["id"]
            filt_name = filt["name"]
            values = filt["values"]
            my_dict = {}
            
            for value in values:
                row = {
                    "filt_id": filt_id,
                    "filt_name": filt_name,
                    "key" : value["id"],
                    "value" : value["name"],
                    "results" : value["results"]
                }
                self.filters.append(row)
                
                # Create a dict of value: key (key is for meli API, not for human)
                my_dict[value["name"]] = value["id"]
                
            # Update the filters dict
            self.filters_dict[filt_id] = my_dict


    def show_filters(self):
        """
        Show the filters available.
        """
        try:
            self.get_filters()
        except Exception as e:
            print(f"Failed to retrieve filters: {e}")
            return {}

        grouped_df = pd.DataFrame(self.filters).groupby('filt_id')

        for key, _ in grouped_df:
            print(f'FILTER: {key}')
            filter_table = grouped_df.get_group(key)[['value', 'key', 'results']].set_index('value')
            print(filter_table.to_markdown(), "\n\n")


    def to_csv(self, filename):
        """
        Write the dataframe to a csv file.

        Parameters
        ----------
        filename : str
            The name of the file.
        """
        self.df.to_csv(filename, index=False)


if __name__ == "__main__":
    type_search = "item"
    query = "bmw"
    params = {'ITEM_CONDITION': '2230581', 'FUEL_TYPE':'64364', 'BRAND':'66352', 'MODEL':'66398', 'DOORS':'[4-4]'}
    query = Searcher(type_search, query, params)
    # items = query.get_items(params, car=True)
    print(query.show_filters())
    print(query.update({'COLOR':'Gris'}))
    print(query.show_filters())
