import os
import re
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from flask import Flask, jsonify, request
from pymongo import MongoClient, ReturnDocument

app = Flask(__name__)
client = MongoClient(
    os.environ.get("MONGO_URI", "mongodb://mongo:27017"),
    serverSelectionTimeoutMS=3000,
)
db = client[os.environ.get("MONGO_DB", "ratings")]
items = db["items"]

VALID_TYPES = {"book", "show"}


def serialize(doc):
    doc["_id"] = str(doc["_id"])
    return doc


def parse_id(item_id):
    try:
        return ObjectId(item_id)
    except InvalidId:
        return None


def check_text(data, clean, errors, field, required, max_len):
    if field not in data or data[field] is None:
        if required:
            errors[field] = "required"
        return
    v = data[field]
    if not isinstance(v, str) or len(v.strip()) > max_len or (required and not v.strip()):
        errors[field] = f"must be text up to {max_len} characters" + (" and not empty" if required else "")
    else:
        clean[field] = v.strip()


def check_int(data, clean, errors, field, required, lo, hi):
    if field not in data or data[field] in (None, ""):
        if required:
            errors[field] = "required"
        return
    v = data[field]
    if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
        errors[field] = f"must be a whole number from {lo} to {hi}"
    else:
        clean[field] = v


def validate(data, partial=False):
    if not isinstance(data, dict):
        return None, {"body": "send a JSON object"}
    errors, clean = {}, {}
    req = not partial
    check_text(data, clean, errors, "title", req, 200)
    check_text(data, clean, errors, "genre", req, 50)
    check_text(data, clean, errors, "creator", False, 100)
    check_text(data, clean, errors, "notes", False, 1000)
    check_int(data, clean, errors, "year", False, 1000, 2100)
    check_int(data, clean, errors, "length", False, 1, 100000)
    check_int(data, clean, errors, "rating", req, 1, 5)
    if "type" in data or req:
        if data.get("type") not in VALID_TYPES:
            errors["type"] = "must be 'book' or 'show'"
        else:
            clean["type"] = data["type"]
    return clean, errors


@app.get("/api/health")
def health():
    try:
        client.admin.command("ping")
        return jsonify(status="ok", mongo="connected")
    except Exception:
        return jsonify(status="error", mongo="unreachable"), 503


@app.post("/api/items")
def create_item():
    clean, errors = validate(request.get_json(silent=True))
    if errors:
        return jsonify(errors=errors), 400
    now = datetime.now(timezone.utc).isoformat()
    clean["created_at"] = now
    clean["updated_at"] = now
    result = items.insert_one(clean)
    return jsonify(serialize(items.find_one({"_id": result.inserted_id}))), 201


@app.get("/api/items")
def list_items():
    query = {}
    if request.args.get("type"):
        query["type"] = request.args["type"]
    if request.args.get("genre"):
        query["genre"] = {"$regex": f"^{re.escape(request.args['genre'])}$", "$options": "i"}
    if request.args.get("q"):
        query["title"] = {"$regex": re.escape(request.args["q"]), "$options": "i"}
    docs = items.find(query).sort("created_at", -1)
    return jsonify([serialize(d) for d in docs])


@app.get("/api/items/<item_id>")
def get_item(item_id):
    oid = parse_id(item_id)
    doc = items.find_one({"_id": oid}) if oid else None
    if not doc:
        return jsonify(error="item not found"), 404
    return jsonify(serialize(doc))


@app.put("/api/items/<item_id>")
def update_item(item_id):
    oid = parse_id(item_id)
    if not oid:
        return jsonify(error="item not found"), 404
    clean, errors = validate(request.get_json(silent=True), partial=True)
    if errors:
        return jsonify(errors=errors), 400
    if not clean:
        return jsonify(error="nothing to update"), 400
    clean["updated_at"] = datetime.now(timezone.utc).isoformat()
    doc = items.find_one_and_update(
        {"_id": oid}, {"$set": clean}, return_document=ReturnDocument.AFTER
    )
    if not doc:
        return jsonify(error="item not found"), 404
    return jsonify(serialize(doc))


@app.delete("/api/items/<item_id>")
def delete_item(item_id):
    oid = parse_id(item_id)
    result = items.delete_one({"_id": oid}) if oid else None
    if not result or result.deleted_count == 0:
        return jsonify(error="item not found"), 404
    return "", 204