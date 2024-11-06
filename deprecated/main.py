from bs4 import BeautifulSoup
import requests
import re
import pandas as pd
import numpy as np
from tqdm import tqdm


def get_soup(my_url: str) -> BeautifulSoup:
    my_src = requests.get(my_url).text
    return BeautifulSoup(my_src, 'lxml')


def get_second_page(my_url: str) -> str:
    soup = get_soup(my_url)
    return soup.find_all(class_="andes-pagination__link ui-search-link")[0].get('href')


def set_number_page(my_url: str, n_page: int) -> str:
    try:
        regex = re.search(r'(.*)(_\d{2}_)(.*)', my_url)
        return regex.group(1) + '_' + str(n_page) + '_' + regex.group(3)
    except:
        regex = re.search(r'(.*)(_\d{2})', my_url)
        return regex.group(1) + '_' + str(n_page)


def get_results(my_url: str) -> int:
    my_soup = get_soup(my_url)
    regex = my_soup.find('span', class_="ui-search-search-result__quantity-results").text
    rgx = re.search(r'(\d*).(\d*)', regex)
    return int(rgx.group(1) + rgx.group(2))


def get_dolar_blue() -> float:
    URL = 'https://www.dolarsi.com/api/api.php?type=valoresprincipales'
    json = requests.get(URL).json()
    blue = json[1]['casa']['venta']
    blue = float(blue.replace(',', '.'))
    return blue


def convert_usd(currency: float, price: str, blue: float) -> float:
    price = float(price.replace('.', ''))
    return price if currency == 'U$S' else price / blue


def get_bmw_model(title: str) -> pd.Series:
    rgx = re.search(r'(\d{3})(i|d)', title)
    try:
        return pd.Series([rgx.group(1), rgx.group(2)])
    except:
        return pd.Series([np.nan, np.nan])


def get_brand(title):
    try:
        return pd.Series(title.split()[0])
    except:
        return pd.Series(np.nan)


def get_model(title):
    try:
        return pd.Series(title.split()[1])
    except:
        return pd.Series(np.nan)


def get_cars(ml_url: str, brand: str) -> pd.DataFrame:
    n_results = get_results(ml_url)
    base_url = get_second_page(ml_url)

    cars = []

    for i in tqdm(range(0, n_results, 49)):
        # Get url for iterate
        scrap_url = set_number_page(base_url, i)
        # print(scrap_url)

        # Get content of url, soup and scrap in order
        my_soup = get_soup(scrap_url)
        sections = my_soup.find_all('a', class_="ui-search-result__content ui-search-link")

        for section in sections:
            # Title
            title = section.get('title')

            # Year
            yearkm = section.find('ul', class_="ui-search-card-attributes ui-search-item__group__element").get_text()
            year = yearkm[:4]

            # Km
            m = re.search(r'(\d*).(\d*)', yearkm[4:])
            km = m.group(1) + m.group(2)

            # Currency
            currency = section.find('span', class_="price-tag-symbol").text

            # Price
            price = section.find('span', class_="price-tag-fraction").text

            # Location
            location = section.find('span', class_="ui-search-item__group__element ui-search-item__location").text

            # Link
            link = section.get('href')

            car = {'title': title,
                   'year': year,
                   'km': km,
                   'currency': currency,
                   'price': price,
                   'location': location,
                   'link': link}

            cars.append(car)

    df = pd.DataFrame(cars)

    df.drop_duplicates(subset=['title', 'year', 'km', 'location'], inplace=True)
    df.reset_index(inplace=True, drop=True)

    # Get prices in dollars
    blue = get_dolar_blue()
    df['price'] = df.apply(lambda row: convert_usd(row['currency'], row['price'], blue), axis=1)

    # Parse year, price, km, currency
    pd.to_numeric(df['year'], errors='coerce')
    pd.to_numeric(df['price'], errors='coerce')
    pd.to_numeric(df['km'], errors='coerce')
    df['currency'] = 'U$S'
    df.year = df.year.astype(int)
    df.km = df.km.astype(int)
    df.price = df.price.astype(int)

    # Define ratio
    df['ratio'] = df.year / (df.km * df.price) * 1000000

    # Define brand
    df['brand'] = df.apply(lambda row: get_brand(row['title']), axis=1)

    # Define model
    df['model'] = df.apply(lambda row: get_model(row['title']), axis=1)

    if brand == 'bmw':
        df[['bmw_model', 'bmw_type']] = df.apply(lambda row: get_bmw_model(row['title']), axis=1)

    return df


#url = 'https://listado.mercadolibre.com.ar/sonic-chevrolet#D[A:sonic%20chevrolet]'
url = 'https://autos.mercadolibre.com.ar/dueno-directo/_PciaId_cordoba_ITEM*CONDITION_2230581#applied_filter_id' \
      '%3Dseller_type%26applied_filter_name%3DVendedor%26applied_filter_order%3D8%26applied_value_id%3Dprivate_seller' \
      '%26applied_value_name%3DDue%C3%B1o+directo%26applied_value_order%3D2%26applied_value_results%3D5895 '

url = "https://autos.mercadolibre.com.ar/dueno-directo/auto_PciaId_cordoba_VEHICLE*BODY*TYPE_452758#applied_filter_id%3Dseller_type%26applied_filter_name%3DVendedor%26applied_filter_order%3D8%26applied_value_id%3Dprivate_seller%26applied_value_name%3DDue%C3%B1o+directo%26applied_value_order%3D2%26applied_value_results%3D1163%26is_custom%3Dfalse"

brand = 'bmw' if 'bmw' in url else None

get_cars(url, brand).to_csv('cba.csv', index=False)