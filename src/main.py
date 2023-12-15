import os
import tempfile
import time
import json
from uuid import uuid4
from typing import List
from bson import ObjectId
from pydantic import BaseModel
from pymongo import MongoClient
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from dotenv import load_dotenv
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
