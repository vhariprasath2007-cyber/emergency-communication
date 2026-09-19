import json
import os
import re
import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS


EMERGENCY_TYPES = {
    "accident",
    "medical",
    "fire",
    "trapped",
    "natural_disaster",
    "other",
}
EMERGENCY_STATUSES = {"ACTIVE", "RESOLVED", "CANCELLED"}
MAX_DESCRIPTION_LENGTH = 2000
MEMORY_STORE: dict[str, dict[str, Any]] = {}
FRONTEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))


def create_app(test_config: dict[str, Any] | None = None) -> Flask:
    app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
    app.config.from_mapping(
        JSON_SORT_KEYS=False,
        CORS_ORIGINS=os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5500,http://127.0.0.1:5500,http://localhost:5000,http://127.0.0.1:5000",
        ),
        DEMO_MODE=os.getenv("DEMO_MODE", "true").lower() == "true",
    )
    if test_config:
        app.config.update(test_config)

    origins = app.config["CORS_ORIGINS"]
    CORS(app, origins=origins.split(",") if isinstance(origins, str) else origins)

    @app.route("/")
    def index() -> Any:
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/script.js")
    def serve_root_script() -> Any:
        root_dir = os.path.abspath(os.path.join(FRONTEND_DIR, ".."))
        return send_from_directory(root_dir, "script.js")

    @app.get("/api/health")
    def health() -> Any:
        return jsonify({
            "status": "ok",
            "service": "ai-emergency-assistant",
            "firebase": firebase_enabled(),
            "gemini": bool(os.getenv("GEMINI_API_KEY")),
        })

    @app.post("/api/emergency")
    def create_emergency() -> Any:
        payload = request.get_json(silent=True) or {}
        errors = validate_emergency_payload(payload)
        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400

        location = normalize_location(payload.get("location"))
        emergency_type = payload["emergency_type"]
        description = payload["description"].strip()
        ai_message = generate_emergency_message(emergency_type, description, location)
        emergency_id = f"EMG-{uuid.uuid4().hex[:10].upper()}"
        emergency = {
            "emergency_id": emergency_id,
            "user_name": clean_optional_text(payload.get("user_name"), 120),
            "emergency_type": emergency_type,
            "description": description,
            "latitude": location["latitude"],
            "longitude": location["longitude"],
            "location_label": location["label"],
            "ai_message": ai_message,
            "status": "ACTIVE",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        save_emergency(emergency)
        return jsonify(emergency), 201

    @app.post("/api/chat")
    def chat() -> Any:
        payload = request.get_json(silent=True) or {}
        message = payload.get("message")
        if not isinstance(message, str) or not message.strip():
            return jsonify({"error": "message is required"}), 400
        if len(message) > MAX_DESCRIPTION_LENGTH:
            return jsonify({"error": f"message must be {MAX_DESCRIPTION_LENGTH} characters or fewer"}), 400

        reply = generate_chat_reply(message.strip(), payload.get("context") or {})
        return jsonify({"reply": reply}), 200

    @app.get("/api/emergency/<emergency_id>")
    def get_emergency(emergency_id: str) -> Any:
        emergency = get_saved_emergency(emergency_id)
        if not emergency:
            return jsonify({"error": "Emergency not found"}), 404
        return jsonify(emergency), 200

    @app.put("/api/emergency/<emergency_id>/status")
    def update_status(emergency_id: str) -> Any:
        payload = request.get_json(silent=True) or {}
        status = payload.get("status")
        if status not in EMERGENCY_STATUSES:
            return jsonify({"error": "status must be ACTIVE, RESOLVED, or CANCELLED"}), 400

        emergency = get_saved_emergency(emergency_id)
        if not emergency:
            return jsonify({"error": "Emergency not found"}), 404

        emergency["status"] = status
        emergency["updated_at"] = datetime.now(timezone.utc).isoformat()
        save_emergency(emergency)
        return jsonify(emergency), 200

    @app.errorhandler(404)
    def not_found(_: Any) -> Any:
        return jsonify({"error": "Route not found"}), 404

    @app.errorhandler(500)
    def server_error(_: Any) -> Any:
        return jsonify({"error": "Internal server error"}), 500

    return app


def validate_emergency_payload(payload: dict[str, Any]) -> list[str]:
    errors = []
    emergency_type = payload.get("emergency_type")
    description = payload.get("description")
    if emergency_type not in EMERGENCY_TYPES:
        errors.append(f"emergency_type must be one of: {', '.join(sorted(EMERGENCY_TYPES))}")
    if not isinstance(description, str) or not description.strip():
        errors.append("description is required")
    elif len(description.strip()) > MAX_DESCRIPTION_LENGTH:
        errors.append(f"description must be {MAX_DESCRIPTION_LENGTH} characters or fewer")

    location = payload.get("location")
    if location is not None and not isinstance(location, dict):
        errors.append("location must be an object")
    elif isinstance(location, dict):
        for key, minimum, maximum in (("latitude", -90, 90), ("longitude", -180, 180)):
            value = location.get(key)
            if value is not None and (not isinstance(value, (int, float)) or not minimum <= value <= maximum):
                errors.append(f"location.{key} must be between {minimum} and {maximum}")
    return errors


def normalize_location(location: dict[str, Any] | None) -> dict[str, Any]:
    location = location or {}
    return {
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
        "label": clean_optional_text(location.get("label"), 160) or "Location shared by user",
    }


def clean_optional_text(value: Any, max_length: int) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned[:max_length] or None


def save_emergency(emergency: dict[str, Any]) -> None:
    if firebase_enabled():
        firestore = get_firestore_client()
        firestore.collection("emergencies").document(emergency["emergency_id"]).set(emergency)
        return
    if not current_app_demo_mode():
        raise RuntimeError("Firebase is not configured and DEMO_MODE is disabled")
    MEMORY_STORE[emergency["emergency_id"]] = emergency


def get_saved_emergency(emergency_id: str) -> dict[str, Any] | None:
    if firebase_enabled():
        document = get_firestore_client().collection("emergencies").document(emergency_id).get()
        return document.to_dict() if document.exists else None
    return MEMORY_STORE.get(emergency_id)


def firebase_enabled() -> bool:
    return bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("FIREBASE_PROJECT_ID"))


def current_app_demo_mode() -> bool:
    return os.getenv("DEMO_MODE", "true").lower() == "true"


@lru_cache(maxsize=1)
def get_firestore_client() -> Any:
    import firebase_admin
    from firebase_admin import firestore

    if not firebase_admin._apps:
        firebase_admin.initialize_app()
    return firestore.client()


def generate_emergency_message(emergency_type: str, description: str, location: dict[str, Any]) -> dict[str, str]:
    prompt = (
        "You are an emergency communication assistant. Organize information, do not diagnose, "
        "do not claim the person is safe, and do not replace emergency professionals. "
        "Return only JSON with keys summary, help_required, alert_text. "
        f"Emergency type: {emergency_type}. Description: {description}. "
        f"Location: {location['label']}."
    )
    result = ask_gemini(prompt)
    if result:
        return {
            "summary": str(result.get("summary", "Immediate assistance may be required.")),
            "help_required": str(result.get("help_required", "Contact local emergency services.")),
            "alert_text": str(result.get("alert_text", description)),
        }
    return {
        "summary": f"A {emergency_type.replace('_', ' ')} has been reported and may require immediate assistance.",
        "help_required": "Contact local emergency services and provide the shared location.",
        "alert_text": f"EMERGENCY ALERT: {description} Location: {location['label']}.",
    }


def generate_chat_reply(message: str, context: dict[str, Any]) -> str:
    prompt = (
        "You are a calm emergency communication assistant. Give concise practical guidance, "
        "encourage contacting local emergency services for immediate danger, and never claim to "
        "be a professional responder. User message: " + message + " Context: " + json.dumps(context)
    )
    result = ask_gemini(prompt, json_output=False)
    if isinstance(result, str) and result:
        return result
    return "If there is immediate danger, contact your local emergency services now. I can help organize the details for an alert."


def ask_gemini(prompt: str, json_output: bool = True) -> Any:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        config = {"temperature": 0.2}
        if json_output:
            config["response_mime_type"] = "application/json"
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            contents=prompt,
            config=config,
        )
        text = response.text.strip()
        return json.loads(text) if json_output else text
    except Exception:
        return None


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)