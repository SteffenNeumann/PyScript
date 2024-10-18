from pyscript import Element
from pyodide.ffi import create_proxy
from datetime import datetime
from dataclasses import dataclass
from js import fetch, console, localStorage, indexedDB
import json
from js import Promise
import asyncio
import micropip
from pyodide.ffi import create_proxy

async def setup_sqlite():
    await micropip.install("sqlite3")
    global sqlite3
    import sqlite3

def init():
    asyncio.ensure_future(setup_sqlite())

init()
@dataclass
class Product:
    name: str
    target_price: float

PRODUCTS_AND_PRICES = [
    Product("Crema d'Oro", 11.00),
    Product("Hafermilch", 0.98),
    Product("Red Bull", 0.99),
]

async def init_db():
    await setup_sqlite()
    conn = sqlite3.connect('deals.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS deals
                 (timestamp TEXT, product TEXT, store TEXT, price REAL, target_price REAL)''')
    conn.commit()
    conn.close()
    return True

async def log_deal(product, store, price, target_price):
    conn = sqlite3.connect('deals.db')
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO deals VALUES (?, ?, ?, ?, ?)",
              (timestamp, product, store, price, target_price))
    conn.commit()
    conn.close()
    
async def print_all_deals():
    console.log("Fetching deals from database...c")
    conn = sqlite3.connect('deals.db')
    c = conn.cursor()
    c.execute("SELECT * FROM deals")
    deals = c.fetchall()
    conn.close()
    console.log(f"Deals: {deals}")
    deals_output = Element("deals-output")
    deals_output.clear()
    for deal in deals:
        deals_output.write(f"Deal: {deal}<br>")

# Add this line to expose the function to PyScript
print_all_deals_proxy = create_proxy(lambda: asyncio.ensure_future(print_all_deals()))
globals()['print_all_deals_proxy'] = print_all_deals_proxy


async def send_email(subject, message):
    console.log(f"Email sent: Subject: {subject}, Message: {message}")

# async def fetch_deals(product, target_price, lat, lon):
#     try:
#         url = f"https://www.meinprospekt.de/webapp/?query={product}&lat={lat}&lng={lon}"
#         response = await fetch(url, method='GET')
async def fetch_deals(product, target_price, lat, lon):
    try:
        from js import encodeURIComponent
        proxy_url = "https://api.allorigins.win/raw?url="
        encoded_url = encodeURIComponent(f"https://www.meinprospekt.de/webapp/?query={product}&lat={lat}&lng={lon}")
        url = f"{proxy_url}{encoded_url}"
        response = await fetch(url, method='GET')
        if not response.ok:
            raise Exception(f"HTTP error! status: {response.status}")
        html = await response.text()
        # Here you would parse the HTML and extract the deals
        # For demonstration, we'll just return a dummy deal
        return [{"store": "DummyStore", "product": product, "price": target_price - 0.01}]
    except Exception as e:
        console.log(f"Error fetching deals: {str(e)}")
        return []


async def convert_location():
    location = Element("location-input").value
    console.log(f"Location input: {location}")
    if location:
        url = f"https://nominatim.openstreetmap.org/search?format=json&q={location}"
        response = await fetch(url)
        data = await response.json()
        if data and len(data) > 0:
            lat = data[0].lat
            lon = data[0].lon
            Element("output").write(f"Location converted: {lat}, {lon}")
            return lat, lon
        else:
            Element("output").write("Location not found. Please try a different location.")
    else:
        Element("output").write("Please enter a location to convert.")
    return None, None


async def find_deals():
    try:
        console.log("Finding deals")
        lat, lon = await convert_location()
        console.log(f"Coordinates: {lat}, {lon}")

        if lat and lon:
            console.log(f"Searching deals for coordinates: {lat}, {lon}")
            Element("output").write(f"Searching for deals near {lat}, {lon}...")
            
            try:
                await init_db()
            except Exception as e:
                console.error(f"Error in init_db: {str(e)}")
                raise

            for item in PRODUCTS_AND_PRICES:
                try:
                    deals = await fetch_deals(item.name, item.target_price, lat, lon)
                    for deal in deals:
                        if deal['price'] <= item.target_price:
                            message = f"Deal alert! {deal['store']} offers {deal['product']} for €{deal['price']:.2f}! (Target price: €{item.target_price:.2f})"
                            await send_email("Deal Alert!", message)
                            await log_deal(deal['product'], deal['store'], deal['price'], item.target_price)
                            Element("output").write(message)
                except Exception as e:
                    console.error(f"Error processing deal for {item.name}: {str(e)}")
        else:
            console.log("Unable to find deals without valid coordinates")
            Element("output").write("Please provide a valid location to search for deals.")
    except Exception as e:
        console.error(f"Error in find_deals: {str(e)}")
        Element("output").write(f"An error occurred: {str(e)}")


convert_location_proxy = create_proxy(convert_location)
find_deals_proxy = create_proxy(find_deals)

# Expose the proxies to the global scope
globals()['convert_location_proxy'] = convert_location_proxy
globals()['find_deals_proxy'] = find_deals_proxy

def start_deal_search():
    find_deals_proxy()

def convert_location_wrapper():
    convert_location_proxy()
