import os
import tempfile
import time
import json
from uuid import uuid4
from typing import List
from bson import ObjectId
from loguru import logger
from pydantic import BaseModel
from pymongo import MongoClient
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from dotenv import load_dotenv

from src.helpers import upload_pinata, create_json_and_qr_code, verify_signature, verify_organizer_signature

load_dotenv()


import os

app = FastAPI()
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
os.getenv("ACCESS_KEY")
client = MongoClient(os.getenv("MONGO_URL"))
db = client.your_database
collection = db.your_collection
user_collection = db.your_user_collection

class UserNFTItem(BaseModel):
    certificationType: str
    name: str
    nftImageUrl: str
    obtainedDate: str
    obtainedFrom: str


class User(BaseModel):
    wallet_id: str
    nfts: List[UserNFTItem] = []
@app.get("/nft")
async def get_nft_items():
    items = []
    for item in collection.find():
        if isinstance(item.get("_id"), ObjectId):
            item["_id"] = str(item["_id"])
        items.append(item)
    print(items)
    return items


@app.post("/user_create")
async def create_or_get_user(user_data: User):
    existing_user = user_collection.find_one({"wallet_id": user_data.wallet_id})

    if existing_user:
        if isinstance(existing_user.get("_id"), ObjectId):
            existing_user["_id"] = str(existing_user["_id"])

        new_nft = user_data.nfts[0] if user_data.nfts else None
        if new_nft:
            user_collection.update_one(
                {"wallet_id": user_data.wallet_id},
                {"$push": {"nfts": new_nft.dict()}}
            )
            existing_user['nfts'].append(new_nft.dict())
        return existing_user['nfts']
    else:
        new_user_data = user_data.dict(by_alias=True)
        result = user_collection.insert_one(new_user_data)
        new_user_id = str(result.inserted_id)
        new_user_data["_id"] = new_user_id
        return new_user_data['nfts']

@app.get("/all_events")
def all_events():
    events = []
    for event in db.events.find():
        if isinstance(event.get("_id"), ObjectId):
            event["_id"] = str(event["_id"])
        events.append(event)
    return events


@app.post("/create_event")
async def create_event(event_name: str = Form(...),
                       issued_place: str = Form(...),
                       certification_type: str = Form(...),
                       image: UploadFile = File(...)):

    print(event_name, issued_place, certification_type, image.filename)
    image_content = await image.read()
    image_file_name = f"{uuid4()}.jpg"
    with open(image_file_name, 'wb') as file:
        file.write(image_content)
    ipfs_hash = upload_pinata(image_file_name)
    os.remove(image_file_name)

    event_data = {}
    event_data['event_name'] = event_name
    event_data['issued_place'] = issued_place
    event_data['certification_type'] = certification_type
    event_data['image_ipfs_hash'] = ipfs_hash
    event_data['is_active'] = True
    event_data['event_id'] = str(uuid4())
    event_data['timestamp'] = int(time.time())
    event_data['qr_ipfs_hash'] = create_json_and_qr_code(event_name, event_data['event_id'], event_data['timestamp'])

    logger.info(event_data)

    result = db.events.insert_one(event_data)
    return {"_id": str(result.inserted_id), "ipfs_hash": ipfs_hash}


class AttendEventRequest(BaseModel):
    event_id: str
    signature: str
    signature_address: str

class EndEventRequest(BaseModel):
    event_id: str
    signature: str
@app.post("/attend_event")
def attend_event(request: AttendEventRequest):
    event = db.events.find_one({"event_id": request.event_id})
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found.")

    if isinstance(event.get("_id"), ObjectId):
        event["_id"] = str(event["_id"])
    print(event)
    if verify_signature(event["event_name"], event["event_id"], event["timestamp"], request.signature,
                        request.signature_address):
        db.events.update_one(
            {"event_id": request.event_id},
            {"$push": {"attendees": request.signature_address}}
        )
        return {"message": "Attendance recorded successfully."}
    else:
        raise HTTPException(status_code=400, detail="Signature verification failed.")

@app.post("/end_event/{event_id}")
async def end_event(request: EndEventRequest):
    try:
        event_id = request.event_id
        signature = request.signature

        current_event = db.events.find_one({"event_id": event_id})
        if not current_event:
            return {"error": "Event not found"}

        issued_place = current_event.get('issued_place')
        print("Issued Place:", issued_place)  # Debug print

        organizer_info = db.organizers_public_address.find_one({"key": issued_place})
        if not organizer_info:
            return {"error": "Organizer's public address not found"}

        print("Organizer Info:", organizer_info)  # Debug print

        if verify_organizer_signature(event_id, signature, organizer_info['value']):
            db.events.update_one(
                {"event_id": event_id},
                {"$set": {"is_active": False}}
            )
            return {"message": "Event ended successfully"}
        else:
            return {"error": "Invalid signature"}

    except Exception as e:
        return {"error": str(e)}
