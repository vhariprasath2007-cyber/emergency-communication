import pytest

from app import MEMORY_STORE, create_app


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    monkeypatch.delenv("FIREBASE_PROJECT_ID", raising=False)
    monkeypatch.setenv("DEMO_MODE", "true")
    MEMORY_STORE.clear()
    return create_app({"TESTING": True}).test_client()


def test_create_get_and_update_emergency(client):
    response = client.post("/api/emergency", json={
        "emergency_type": "accident",
        "description": "My friend was in a bike accident near the main road.",
        "location": {"latitude": 12.92, "longitude": 80.12, "label": "Main road"},
    })

    assert response.status_code == 201
    emergency = response.get_json()
    assert emergency["status"] == "ACTIVE"
    assert emergency["ai_message"]["summary"]

    fetched = client.get(f"/api/emergency/{emergency['emergency_id']}")
    assert fetched.status_code == 200

    updated = client.put(
        f"/api/emergency/{emergency['emergency_id']}/status",
        json={"status": "RESOLVED"},
    )
    assert updated.status_code == 200
    assert updated.get_json()["status"] == "RESOLVED"


def test_validation_and_chat(client):
    invalid = client.post("/api/emergency", json={"emergency_type": "unknown"})
    assert invalid.status_code == 400

    chat = client.post("/api/chat", json={"message": "What details should I share?"})
    assert chat.status_code == 200
    assert chat.get_json()["reply"]


def test_missing_emergency(client):
    response = client.get("/api/emergency/EMG-MISSING")
    assert response.status_code == 404


def test_module_exposes_app():
    import app as app_module

    assert hasattr(app_module, "app")
    assert app_module.app is not None
    assert app_module.app.name == "app"