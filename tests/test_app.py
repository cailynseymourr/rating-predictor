import os

os.environ["MONGO_DB"] = "ratings_test"  # keep tests away from your real data

import pytest

from app import app, items


@pytest.fixture
def client():
    app.config["TESTING"] = True
    items.delete_many({})
    with app.test_client() as c:
        yield c
    items.delete_many({})


def make(title="Dune", genre="sci-fi", rating=5, **extra):
    return {"title": title, "type": "book", "genre": genre, "rating": rating, **extra}


def test_create_and_get(client):
    r = client.post("/api/items", json=make())
    assert r.status_code == 201
    item = r.get_json()
    assert item["title"] == "Dune"
    r = client.get(f"/api/items/{item['_id']}")
    assert r.status_code == 200


def test_list_and_filter(client):
    client.post("/api/items", json=make("Dune"))
    client.post("/api/items", json={**make("The Office", "comedy", 4), "type": "show"})
    assert len(client.get("/api/items").get_json()) == 2
    assert len(client.get("/api/items?type=show").get_json()) == 1
    assert len(client.get("/api/items?q=dun").get_json()) == 1


def test_update(client):
    item = client.post("/api/items", json=make()).get_json()
    r = client.put(f"/api/items/{item['_id']}", json={"rating": 3})
    assert r.status_code == 200
    assert r.get_json()["rating"] == 3


def test_delete(client):
    item = client.post("/api/items", json=make()).get_json()
    assert client.delete(f"/api/items/{item['_id']}").status_code == 204
    assert client.get(f"/api/items/{item['_id']}").status_code == 404


def test_validation_errors(client):
    r = client.post("/api/items", json={"title": "", "type": "movie", "rating": 9})
    assert r.status_code == 400
    errors = r.get_json()["errors"]
    assert "title" in errors and "type" in errors and "rating" in errors


def test_not_found(client):
    assert client.get("/api/items/000000000000000000000000").status_code == 404
    assert client.get("/api/items/not-an-id").status_code == 404


def test_predict_locked_under_10(client):
    for i in range(3):
        client.post("/api/items", json=make(f"Book {i}"))
    r = client.post("/api/predict", json={"title": "New", "type": "book", "genre": "sci-fi"})
    body = r.get_json()
    assert body["locked"] is True
    assert body["needed"] == 7


def test_predict_unlocked(client):
    for i in range(10):
        client.post("/api/items", json=make(f"Book {i}", rating=4 + (i % 2)))
    r = client.post("/api/predict", json={"title": "New", "type": "book", "genre": "sci-fi"})
    body = r.get_json()
    assert body["locked"] is False
    assert 1 <= body["predicted"] <= 5
    assert body["reasons"]


def test_predict_validation(client):
    r = client.post("/api/predict", json={"title": "", "type": "book", "genre": ""})
    assert r.status_code == 400