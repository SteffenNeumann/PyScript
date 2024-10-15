from pyscript import Element
from pyodide.ffi import create_proxy
from datetime import datetime
from dataclasses import dataclass
from js import fetch, console, localStorage, indexedDB
import json

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
    try:
        db = await indexedDB.open("DealsDB", 1)
        db.onupgradeneeded = lambda event: event.target.result.createObjectStore("deals", {"keyPath": "timestamp"})
        return db
    except Exception as e:
        console.log(f"Error initializing database: {str(e)}")
        return None
    
async def log_deal(product, store, price, target_price):
    db = await indexedDB.open("DealsDB", 1)
    transaction = db.transaction(["deals"], "readwrite")
    object_store = transaction.objectStore("deals")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await object_store.add({"timestamp": timestamp, "product": product, "store": store, "price": price, "target_price": target_price})

async def send_email(subject, message):
    console.log(f"Email sent: Subject: {subject}, Message: {message}")

async def fetch_deals(product, target_price, lat, lon):
    try:
        url = f"https://www.meinprospekt.de/webapp/?query={product}&lat={lat}&lng={lon}"
        response = await fetch(url)
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
    console.log("Finding deals...")
    lat, lon = await convert_location()
    if lat and lon:
        Element("output").write(f"Searching for deals near {lat}, {lon}...")
        await init_db()

        for item in PRODUCTS_AND_PRICES:
            deals = await fetch_deals(item.name, item.target_price, lat, lon)
            for deal in deals:
                if deal['price'] <= item.target_price:
                    message = f"Deal alert! {deal['store']} offers {deal['product']} for €{deal['price']:.2f}! (Target price: €{item.target_price:.2f})"
                    await send_email("Deal Alert!", message)
                    await log_deal(deal['product'], deal['store'], deal['price'], item.target_price)
                    Element("output").write(message)
    else:
        Element("output").write("Please provide a valid location to search for deals.")

convert_location_proxy = create_proxy(convert_location)
find_deals_proxy = create_proxy(find_deals)

# Expose the proxies to the global scope
globals()['convert_location_proxy'] = convert_location_proxy
globals()['find_deals_proxy'] = find_deals_proxy

def start_deal_search():
    find_deals_proxy()

def convert_location_wrapper():
    convert_location_proxy()
