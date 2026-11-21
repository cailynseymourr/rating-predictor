import os
from flask import Flask, jsonify
from pymongo import MongoClient

app = Flask(__name__)
client = MongoClient(
    os.environ.get("MONGO_URI", "mongodb://mongo:27017"),
    serverSelectionTimeoutMS=3000,
)
db = client[os.environ.get("MONGO_DB", "ratings")]


@app.get("/api/health")
def health():
    try:
        client.admin.command("ping")
        return jsonify(status="ok", mongo="connected")
    except Exception:
        return jsonify(status="error", mongo="unreachable"), 503