from pyscript import Element
from pyodide.ffi import create_proxy
from datetime import datetime
from dataclasses import dataclass
from js import fetch, console, localStorage, indexedDB, document
import json
from js import Promise
import asyncio
import micropip
from pyodide.ffi import create_proxy

async def setup_sqlite():
    await micropip.install("sqlite3")
    global sqlite3
    import sqlite3

async def init_db():
    conn = sqlite3.connect('deals.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS deals
                 (timestamp TEXT, product TEXT, store TEXT, price REAL, target_price REAL)''')
    conn.commit()
    conn.close()
    return True

async def init():
    await setup_sqlite()
    await init_db()

asyncio.ensure_future(init())

@dataclass
class Product:
    name: str
    target_price: float

PRODUCTS_AND_PRICES = [
    Product("Crema d'Oro", 11.00),
    Product("Hafermilch", 0.98),
    Product("Red Bull", 0.99),
]

async def log_deal(product, store, price, target_price):
    conn = sqlite3.connect('deals.db')
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO deals VALUES (?, ?, ?, ?, ?)",
              (timestamp, product, store, price, target_price))
    conn.commit()
    conn.close()

async def send_email(subject, message):
    console.log(f"Email sent: Subject: {subject}, Message: {message}")

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

async def get_stored_deals():
    try:
        conn = sqlite3.connect('deals.db')
        c = conn.cursor()
        c.execute("SELECT * FROM deals ORDER BY timestamp DESC LIMIT 10")
        deals = c.fetchall()
        conn.close()
        return deals
    except sqlite3.OperationalError:
        console.log("Deals table not found. It may not have been created yet.")
        return []

async def update_deals_output():
    deals = await get_stored_deals()
    deals_list = document.getElementById("deals-list")
    deals_list.innerHTML = ""
    for deal in deals:
        li = document.createElement("li")
        li.textContent = f"{deal[1]} at {deal[2]} for €{deal[3]:.2f} (Target: €{deal[4]:.2f}) - {deal[0]}"
        deals_list.appendChild(li)

async def find_deals():
    try:
        console.log("Finding deals")
        lat, lon = await convert_location()
        console.log(f"Coordinates: {lat}, {lon}")

        if lat and lon:
            console.log(f"Searching deals for coordinates: {lat}, {lon}")
            Element("output").write(f"Searching for deals near {lat}, {lon}...")
            
            for item in PRODUCTS_AND_PRICES:
                try:
                    deals = await fetch_deals(item.name, item.target_price, lat, lon)
                    for deal in deals:
                        if deal['price'] <= item.target_price:
                            message = f"Deal alert! {deal['store']} offers {deal['product']} for €{deal['price']:.2f}! (Target price: €{item.target_price:.2f})"
                            await send_email("Deal Alert!", message)
                            await log_deal(deal['product'], deal['store'], deal['price'], item.target_price)
                            Element("output").write(message)
                    
                    # Update the deals output after processing each item
                    await update_deals_output()

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
update_deals_output_proxy = create_proxy(update_deals_output)

# Expose the proxies to the global scope
globals()['convert_location_proxy'] = convert_location_proxy
globals()['find_deals_proxy'] = find_deals_proxy
globals()['update_deals_output_proxy'] = update_deals_output_proxy

def start_deal_search():
    find_deals_proxy()
    update_deals_output_proxy()

def convert_location_wrapper():
    convert_location_proxy()
