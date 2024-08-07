from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Union, Literal, Dict
import uuid
import time
import asyncio
import redis



app = FastAPI()

class OrderData(BaseModel):
    order: Literal["start", "stop"]
    type: str
    data: Dict[str, Union[int, float]]
    message: str
    result: Union[None, str]

class InfoData(BaseModel):
    info_type: str
    status: str
    duration: int
    configuration: List[Union[int, float]]

# dla testowania 
orders = [
    OrderData(order="startas", type="test", data={"t": 10, "x": 1, "y": 2, "z": 3}, message="", result=None),
    OrderData(order="stop", type="process", data={"t": 5, "x": 4, "y": 3.5, "z": 2}, message="", result=None),
    OrderData(order="start", type="setup", data={"t": 15, "x": 3, "y": 2, "z": 1}, message="", result=None),
]

def generate_id():
    return str(uuid.uuid4())

info_data = []

r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)


async def process_order(order_data: OrderData):
    order_id = generate_id()
    try:
        order_dict = order_data.dict()
        insert_order_to_redis(order_id, order_dict)
        
        # czas na zapisanie 
        await asyncio.sleep(2)
        order = get_order_from_redis(order_id)
        
        if order.get("result") is True:
            info = get_info_from_redis(order.get("type"))
            
            info["info_type"] = order.get("type")
            info_data.append(info)
            
            print(info)
            return {
                "order_id": order_id,
                "command": order.get("order"),
                "type": order.get("type"),
                "setting": order.get("data"),
                "message": order.get("message"),
                "result": order.get("result"),
            }
        elif order.get("result") == "exception":
            return {"status": "error", "message": order.get("message")}
        else:
            return {
                "order_id": order_id,
                "status": "Error with processing order",
                "message": order.get("message"),
                "result": order.get("result")
            }
    except Exception as e:
        return {
            "order_id": order_id,
            "status": "Error",
            "detail": str(e)
        }
        
    finally:
        await clean_order(order_id)


async def clean_order(order_id: str):
    try:
        delete_order(order_id)
    except Exception as e:
        print(f"Error with{order_id}: {e}")

@app.post("/post_order", status_code=status.HTTP_200_OK)
async def post_order(order: OrderData):
    order_id = generate_id()
    try:
        order_dict = order.dict()
        insert_order_to_redis(order_dict)
        await asyncio.sleep(2)
        order = get_order_from_redis(order_id)
        if order.get("result") is True:
            info = get_info_from_redis(order.get("type"))
            
            info["info_type"] = order.get("type")
            info_data.append(info)
            await clean_order(order_id)
            return {"status": " inserted successfully"}
        
        elif order.get("result") == "exception":
            return {"status": "error", "message": order.get("message")}
        else:
            return {
                "order_id": order_id,
                "status": "Error processing order",
                "message": order.get("message"),
                "result": order.get("result")
            }
    except Exception as e:
         raise HTTPException(status_code=500, detail=str(e))

@app.post("/response")
async def process_orders_endpoint():
    results = []

    tasks = [process_order(order_data) for order_data in orders] 
    results = await asyncio.gather(*tasks) # każdy task jest osobnym argumentem
  
    return JSONResponse(content={"results": results, "processed_info": info_data}, status_code=200)
    
@app.get("/order/{order_id}", status_code=status.HTTP_200_OK)
def read_order(order_id: str):
    try:
        order = get_order_from_redis(order_id)
        if order:
            return order
        else:
            raise HTTPException(status_code=404, detail="Order not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def insert_order_to_redis(order_id, order_data):
    key = f"order:{order_id}"
    r.json().set(key, '.', order_data)

def get_order_from_redis(order_id):
    key = f"order:{order_id}"
    return r.json().get(key)

def insert_info_to_redis(info_data):
    key = f"info:{info_data['info_type']}"
    r.json().set(key, '.', info_data)

def get_info_from_redis(info_type):
    key = f"info:{info_type}"
    return r.json().get(key)

def delete_order(order_id: str):
    r.delete(f"order:{order_id}")
