import requests
import re
import lxml.html
import math
import pandas as pd
import logging
from urllib3.exceptions import InsecureRequestWarning
import urllib3
import chardet
from itertools import cycle

# Suppress only the InsecureRequestWarning
urllib3.disable_warnings(InsecureRequestWarning)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define headers for HTTP requests
headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}

# List of proxies
proxies = [
    {"http": "", "https": ""},
    {"http": "", "https": ""},
    {"http": "", "https": ""},
]

# Create a cycle object for round-robin proxy rotation
proxy_pool = cycle(proxies)

def get_with_proxy(url, headers):
    """
    Fetches a URL using a proxy from the proxy pool.
    Retries with different proxies if the request fails.
    """
    for _ in range(len(proxies)):
        proxy = next(proxy_pool)
        try:
            response = requests.get(url, headers=headers, proxies=proxy, verify=False, timeout=10)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logging.warning(f"Proxy {proxy} failed: {e}")
    logging.error(f"All proxies failed for URL: {url}")
    return None

def get_subdivision(headers):
    """
    Fetches and parses the subdivision data from a specific JS file.
    Returns a list of regions with their respective subregions.
    """
    response = get_with_proxy('https://www.jalan.net/js/quick/jalan_qs.js', headers)
    if not response:
        logging.error("Failed to fetch subdivision data.")
        return []

    # Regex patterns to extract region and subregion data
    pattern = re.compile(r'KenData\("(?P<region>[^"]+)",\s*"(?P<region_code>\d+)",\s*new\s*Array\((?P<subregions>.*?)\)\s*\)', re.DOTALL)
    subregion_pattern = re.compile(r'LrgData\("(?P<subregion>[^"]+)",\s*"(?P<subregion_code>\d+)"\)', re.DOTALL)

    regions = []
    for match in pattern.finditer(response.text):
        region_name = match.group('region')
        region_code = match.group('region_code')
        subregions = []

        for sub_match in subregion_pattern.finditer(match.group('subregions')):
            subregions.append({
                'subregion': sub_match.group('subregion'),
                'subregion_code': sub_match.group('subregion_code')
            })

        regions.append({
            'region': region_name,
            'region_code': region_code,
            'subregions': subregions
        })

    return regions

def clean_price(price_str):
    # Remove non-numeric characters except for commas and periods
    cleaned_price = re.sub(r'[^\d,.]', '', price_str)
    # Replace commas with nothing and convert to float
    cleaned_price = cleaned_price.replace(',', '')
    try:
        return float(cleaned_price)
    except ValueError:
        return None

def get_make_urls(pref, sub_arr):
    """
    Creates URLs for the given prefecture and its subregions.
    """
    url_arr = []
    for sub_id in sub_arr:
        url = f"https://www.jalan.net/{pref}/LRG_{sub_id}/"
        url_arr.append(url)
    return url_arr

def get_dom(url, headers):
    """
    Fetches and parses the HTML content from the given URL.
    Returns the parsed DOM or None if the request fails.
    """
    response = get_with_proxy(url, headers)
    if response:
        detected_encoding = chardet.detect(response.content)['encoding']
        response.encoding = detected_encoding
        dom = lxml.html.fromstring(response.text)
        return dom
    logging.error(f"Failed to fetch and parse DOM for URL: {url}")
    return None

def make_page_url(url, pages):
    """
    Generates paginated URLs based on the number of pages.
    """
    p_arr = []
    for i in range(1, pages + 1):
        p_url = f"{url}page{i}.html"
        p_arr.append(p_url)
    return p_arr

# Base URL for the website
base_url = 'https://www.jalan.net/'

# Get subdivision data
sub_div = get_subdivision(headers)
if not sub_div:
    logging.error("No subdivision data available. Exiting...")
    exit()

# Get DOM for the base URL
dom = get_dom(base_url, headers)
if dom is None:
    logging.error("Failed to fetch base DOM. Exiting...")
    exit()

# Extract prefecture values
raw_pref_vals = dom.xpath("//div[contains(@class,'areaSelect')]//select[contains(@name,'kenCd')]//option/@value")
pref_vals = [item for item in raw_pref_vals if item]

# Generate listing URLs for each prefecture
listing_urls = []
for pref in pref_vals:
    sub_arr = [k["subregion_code"] for sub in sub_div if pref in sub["region_code"] for k in sub["subregions"]]
    listing_urls += get_make_urls(pref, sub_arr)

# Scrape data from the listing URLs
detail_array = []
for listing_url in listing_urls:
    logging.info(f"Fetching response for prefecture URL: {listing_url}")
    list_dom = get_dom(listing_url, headers)
    if list_dom is None:
        continue

    try:
        count = int(list_dom.xpath("//span[contains(@class,'listInformation--count')]//text()")[0])
        pages = math.ceil(count / 30)
    except (IndexError, ValueError) as e:
        logging.warning(f"Failed to determine the number of pages for URL {listing_url}: {e}")
        pages = 1
    page_urls = make_page_url(listing_url, pages)
    hotel_url_list = []
    for p_url in page_urls:
        logging.info(f"Fetching page URL: {p_url}")
        p_dom = get_dom(p_url, headers)
        if p_dom is not None:
            hotel_url_list += p_dom.xpath("//a[contains(@class,'planDetailLink')]/@href")

    for hotel_url in hotel_url_list:
        hotel_url = f"https://www.jalan.net{hotel_url}"
        logging.info(f"Fetching response for property URL: {hotel_url}")
        hotel_dom = get_dom(hotel_url, headers)
        if hotel_dom is None:
            continue

        try:
            name = hotel_dom.xpath("//div[contains(@id,'hotel_name')]/a/text()")[0]
            price = hotel_dom.xpath("//div[contains(@class,'p-planOverview__charge')]//p/em/text()")[0]
            hotel_type = hotel_dom.xpath("//div[contains(@id,'roomTypeNameId')]//p//span/text()")[0]
            map_url = "https://www.jalan.net" + hotel_dom.xpath("//a[contains(@target,'map')]//@onclick")[0].split("open('")[-1].split("',")[0]
            map_dom = get_dom(map_url, headers)
            address = map_dom.xpath("//div[contains(@class,'map__yadInfo')]//p//text()")[-1]

            dict_vals = {
                "hotel_name": name,
                "hotelurl": hotel_url,
                "hotel_location": address,
                "price": price,
                "hotel_type": hotel_type
            }
            detail_array.append(dict_vals)
        except IndexError as e:
            logging.error(f"Failed to parse hotel data for URL {hotel_url}: {e}")

# Convert the details to a DataFrame and save to CSV
df = pd.DataFrame(detail_array)
df.to_csv("jalan_data.csv", index=False, encoding='utf-8-sig')
logging.info("Data saved to jalan_data.csv")

# Generate summary report
df['cleaned_price'] = df['price'].apply(clean_price)

# Generate summary report
summary = {
    "Total Hotels": len(df),
    "Average Price": df['cleaned_price'].mean() if not df['cleaned_price'].isnull().all() else 0,
    "Most Common Hotel Type": df['hotel_type'].mode()[0] if not df.empty else 'N/A'
}

summary_df = pd.DataFrame([summary])
summary_df.to_csv("jalan_summary.csv", index=False, encoding='utf-8-sig')
logging.info("Summary report saved to jalan_summary.csv")
