import firebase_admin
import os
import json
import random
import time
import asyncio
import threading
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from firebase_admin import credentials, db

TEMPLATE = {
    "Items": {},
    "Vers": 0,
}

STOCK = {
    1: {
        "ItemName": "Lucky Block",
        "Chance": 100,
        "AmountUpperBound": 4,
        "AmountLowerBound": 1,
    },
    2: {
        "ItemName": "Shiny Lucky Block",
        "Chance": 60,
        "AmountUpperBound": 2,
        "AmountLowerBound": 1,
    },
    3: {
        "ItemName": "Rainbow Lucky Block",
        "Chance": 40,
        "AmountUpperBound": 2,
        "AmountLowerBound": 1,
    },
    4: {
        "ItemName": "Prism Lucky Block",
        "Chance": 30,
        "AmountUpperBound": 1,
        "AmountLowerBound": 1,
    },
}

current_stock = {}

if not firebase_admin._apps:
    if "FIREBASE_KEY" in os.environ:
        firebase_key = json.loads(os.environ["FIREBASE_KEY"])
        cred = credentials.Certificate(firebase_key)
    else:
        cred = credentials.Certificate("firebase_key.json")

    firebase_admin.initialize_app(cred, {
        "databaseURL": "https://global-stock.firebaseio.com/"
    })

app = FastAPI()
stock_ref = db.reference("Stocks")

def generate_new_stock():
    global current_stock
    temp_stock = {}
    for stock_id, stock_info in STOCK.items():
        rand_num = random.randint(1, 100)
        if rand_num <= stock_info["Chance"]:
            stock_amount = random.randint(
                stock_info["AmountLowerBound"], stock_info["AmountUpperBound"]
            )
            temp_stock[stock_info["ItemName"]] = stock_amount
        else:
            temp_stock[stock_info["ItemName"]] = 0

    current_stock = temp_stock

    try:
        data = stock_ref.get()
        new_version = data.get("Vers", 0) + 1

        payload = {
            "Items": temp_stock,
            "Vers": new_version
        }
        stock_ref.set(payload)
    except Exception as e:
        print("[Firebase Error]", e)
    return payload

def get_next_5_minute_mark(current_time):
    return ((current_time // 300) + 1) * 300

def stock_refresh_loop():
    while True:
        current_time = int(time.time())
        next_mark = get_next_5_minute_mark(current_time)
        refresh_time = next_mark - 5

        if current_time >= refresh_time:
            next_mark = get_next_5_minute_mark(current_time + 60)
            refresh_time = next_mark - 5

        wait_time = refresh_time - current_time
        print(f"Waiting {wait_time} sec until stock refresh at {time.strftime('%H:%M:%S', time.localtime(refresh_time))}")
        time.sleep(wait_time)

        payload = generate_new_stock()
        print(f"Stock refreshed at {time.strftime('%H:%M:%S')} -> {payload}")

        time.sleep(1)

@app.get("/")
def root():
    return {"message": "Stock API is running!"}

@app.get("/stock")
def get_stock():
    try:
        data = stock_ref.get()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
threading.Thread(target=stock_refresh_loop, daemon=True).start()
