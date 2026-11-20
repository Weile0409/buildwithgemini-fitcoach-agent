# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
from zoneinfo import ZoneInfo

import sys
from pathlib import Path

# Ensure a2ui_compat is accessible as a2ui for A2uiSchemaManager and BasicCatalog
_app_dir = str(Path(__file__).parent)
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)
try:
    import a2ui_compat as _a2ui_compat
    sys.modules.setdefault("a2ui", _a2ui_compat)
except ImportError:
    pass

from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from .a2ui_utils import a2ui_callback

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors.agent_engine_sandbox_code_executor import AgentEngineSandboxCodeExecutor
from google.adk.memory import VertexAiMemoryBankService
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types


MODEL = "gemini-3.8-flash"


from typing import Any, Dict, List, Optional
from google.cloud import firestore

PROJECT_ID = "qwiklabs-gcp-04-31e92fc7c50b"
db = firestore.Client(project=PROJECT_ID)


def list_routines(category: Optional[str] = None, target_muscle: Optional[str] = None) -> List[Dict[str, Any]]:
    """List available workout routines from the catalog.

    Args:
        category: Optional filter by routine category (e.g., 'Strength', 'Cardio', 'Running', 'Mobility').
        target_muscle: Optional muscle to filter for (e.g., 'Chest', 'Legs', 'Back', 'Hips').

    Returns:
        A list of matching workout routines with their summary information.
    """
    routines_ref = db.collection("routines")
    docs = routines_ref.stream()
    results = []
    for doc in docs:
        data = doc.to_dict()
        if category and data.get("category", "").lower() != category.lower():
            continue
        if target_muscle:
            muscles = [m.lower() for m in data.get("target_muscles", [])]
            if target_muscle.lower() not in muscles:
                continue
        results.append({
            "id": data.get("id"),
            "name": data.get("name"),
            "category": data.get("category"),
            "level": data.get("level"),
            "target_muscles": data.get("target_muscles"),
            "duration_minutes": data.get("duration_minutes"),
            "equipment": data.get("equipment"),
            "description": data.get("description"),
        })
    return results


def get_routine_details(routine_id: str) -> Dict[str, Any]:
    """Get full details of a specific workout routine including all exercises, sets, and reps.

    Args:
        routine_id: The ID of the routine (e.g., 'full-body-strength', 'hiit-cardio-blast', 'half-marathon-tempo', 'mobility-recovery-flow').

    Returns:
        The full routine details, or an error dictionary if not found.
    """
    doc_ref = db.collection("routines").document(routine_id)
    doc = doc_ref.get()
    if not doc.exists:
        return {"error": f"Routine with ID '{routine_id}' not found."}
    return doc.to_dict()


def log_workout(
    user_id: str,
    routine_name: str,
    duration_minutes: int,
    completed_exercises: List[str],
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Log a completed workout session to the user's history in Firestore.

    Args:
        user_id: The identifier of the athlete/user (e.g. 'athlete_1').
        routine_name: Name of the completed routine or custom workout session.
        duration_minutes: Total minutes the session took.
        completed_exercises: List of exercise names completed during the session.
        notes: Optional athlete notes, reflections, or weights used (e.g., 'Hit 225 lbs squat').

    Returns:
        A dictionary confirming the log creation with its log ID.
    """
    log_data = {
        "user_id": user_id,
        "routine_name": routine_name,
        "duration_minutes": duration_minutes,
        "completed_exercises": completed_exercises,
        "notes": notes or "",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    update_time, doc_ref = db.collection("workout_logs").add(log_data)
    return {
        "status": "success",
        "log_id": doc_ref.id,
        "routine_name": routine_name,
        "duration_minutes": duration_minutes,
        "message": f"Successfully logged workout '{routine_name}' ({duration_minutes} min) for {user_id}."
    }


def get_user_workout_history(user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieve the recent workout history logs for a user.

    Args:
        user_id: The identifier of the user (e.g. 'athlete_1').
        limit: Max number of recent workouts to retrieve (default 5).

    Returns:
        A list of recent workout logs sorted from most recent to oldest.
    """
    logs_ref = db.collection("workout_logs")
    query = logs_ref.where("user_id", "==", user_id).limit(limit)
    docs = query.stream()
    logs = [doc.to_dict() for doc in docs]
    logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return logs


def estimate_one_rep_max(weight: float, reps: int, unit: str = "lbs") -> Dict[str, Any]:
    """Calculate estimated One-Rep Max (1RM) and percentage-based training loads.

    Uses standard sports science formulas (Epley & Brzycki) to project maximum strength
    and provides recommended training percentages (e.g. 70%, 80%, 90% for working sets).

    Args:
        weight: The weight lifted (must be > 0).
        reps: Number of repetitions completed with good form (typically 1 to 15).
        unit: Weight unit, either 'lbs' or 'kg' (default 'lbs').

    Returns:
        A dictionary containing estimated 1RM and percentage working set loads.
    """
    if weight <= 0 or reps <= 0:
        return {"error": "Weight and reps must be positive numbers."}

    if reps == 1:
        one_rep_max = round(weight, 1)
    else:
        # Average of Epley and Brzycki formulas
        epley = weight * (1 + reps / 30.0)
        brzycki = weight * (36.0 / (37.0 - reps)) if reps < 37 else epley
        one_rep_max = round((epley + brzycki) / 2.0, 1)

    percentages = {
        "90% (Heavy Strength / Peak)": round(one_rep_max * 0.90, 1),
        "85% (Strength Working Sets - 3-5 reps)": round(one_rep_max * 0.85, 1),
        "80% (Hypertrophy / Power - 6-8 reps)": round(one_rep_max * 0.80, 1),
        "70% (Volume / Endurance - 10-12 reps)": round(one_rep_max * 0.70, 1),
    }

    return {
        "input_weight": weight,
        "input_reps": reps,
        "unit": unit,
        "estimated_1rm": one_rep_max,
        "training_load_percentages": percentages,
        "formula": "Epley & Brzycki average",
    }


def search_public_exercises(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Search for exercises and anatomical technique data from the public Wger Workout & Exercise API.

    This queries the free open-source Wger Workout Manager API (https://wger.de/en/software/api)
    for exercise names, targeted muscle groups, equipment required, and descriptions.

    Args:
        query: Exercise name or muscle to search for (e.g., 'squat', 'bench', 'curl', 'plank').
        limit: Maximum number of exercise results to return (default 5).

    Returns:
        A list of matching exercises with category, muscles, equipment, and instructions.
    """
    import os
    import re
    import urllib.request
    import json

    # If an API key is provided via env var, it will be used in the Authorization header
    api_key = os.getenv("WGER_API_KEY", "").strip()

    url = "https://wger.de/api/v2/exerciseinfo/?limit=60"
    headers = {
        "Accept": "application/json",
        "User-Agent": "FitCoachAgent/1.0",
    }
    if api_key:
        headers["Authorization"] = f"Token {api_key}"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        return [{"error": f"Failed to fetch public exercise data: {str(e)}"}]

    results: List[Dict[str, Any]] = []
    clean_query = query.lower().strip()

    for item in data.get("results", []):
        category_name = item.get("category", {}).get("name", "General")
        muscles = [m.get("name_en") or m.get("name") for m in item.get("muscles", [])]
        equipment = [eq.get("name") for eq in item.get("equipment", [])]

        # Look for English translation (language 2) or default
        matched_name = None
        matched_desc = ""
        for translation in item.get("translations", []):
            name = translation.get("name", "")
            desc = translation.get("description", "")
            # Clean HTML tags from description
            desc_clean = re.sub(r"<[^>]+>", "", desc).strip()
            
            # Check if query matches name, category, or muscles
            if (
                clean_query in name.lower()
                or clean_query in category_name.lower()
                or any(clean_query in m.lower() for m in muscles if m)
            ):
                matched_name = name
                matched_desc = desc_clean
                break

        if matched_name:
            results.append({
                "name": matched_name,
                "category": category_name,
                "target_muscles": muscles,
                "equipment": equipment,
                "instructions": matched_desc[:300] + "..." if len(matched_desc) > 300 else matched_desc,
            })
            if len(results) >= limit:
                break

    return results


def geocode_address(address: str) -> Dict[str, Any]:
    """Convert a human-readable street address or location name into geographic latitude and longitude coordinates using the Google Geocoding API.

    Args:
        address: The address or location string (e.g. '1600 Amphitheatre Pkwy, Mountain View, CA' or 'Central Park, NY').

    Returns:
        A dictionary with status, formatted_address, latitude, longitude, and place_id.
    """
    import os
    import urllib.parse
    import urllib.request
    import json

    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key or api_key == "PASTE_KEY_HERE":
        return {"error": "GOOGLE_MAPS_API_KEY is not configured in environment or .env."}

    encoded_address = urllib.parse.quote(address)
    url = f"https://maps.googleapis.com/maps/api/geocode/json?address={encoded_address}&key={api_key}"

    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))

        if data.get("status") != "OK" or not data.get("results"):
            return {
                "error": f"Geocoding failed with status: {data.get('status')}",
                "error_message": data.get("error_message", "No matching coordinates found.")
            }

        result = data["results"][0]
        location = result["geometry"]["location"]
        return {
            "status": "OK",
            "name": address,
            "formatted_address": result.get("formatted_address"),
            "latitude": location.get("lat"),
            "longitude": location.get("lng"),
            "place_id": result.get("place_id"),
        }
    except Exception as e:
        return {"error": f"Failed to call Geocoding API: {str(e)}"}


def find_nearby_places(
    latitude: float,
    longitude: float,
    place_type: str = "gym",
    radius_meters: float = 3000.0,
    max_results: int = 5,
) -> List[Dict[str, Any]]:
    """Search for nearby places of a given type around a location using the Google Places API (New).

    Args:
        latitude: Center latitude coordinate.
        longitude: Center longitude coordinate.
        place_type: Type of place to search for (e.g., 'gym', 'fitness_center', 'athletic_field', 'park', 'sporting_goods_store').
        radius_meters: Radius in meters around the center point (default 3000m / 3km).
        max_results: Max number of places to return (default 5).

    Returns:
        A list of nearby places with name, formatted_address, and location coordinates.
    """
    import os
    import urllib.request
    import json

    api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    if not api_key or api_key == "PASTE_KEY_HERE":
        return [{"error": "GOOGLE_MAPS_API_KEY is not configured in environment or .env."}]

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,places.types",
    }

    payload = {
        "includedTypes": [place_type],
        "maxResultCount": min(max_results, 20),
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": latitude,
                    "longitude": longitude,
                },
                "radius": radius_meters,
            }
        },
    }

    try:
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=6) as response:
            result_data = json.loads(response.read().decode("utf-8"))

        places = []
        for p in result_data.get("places", []):
            display_name = p.get("displayName", {}).get("text", "Unknown Place")
            loc = p.get("location", {})
            places.append({
                "name": display_name,
                "address": p.get("formattedAddress"),
                "location": {
                    "latitude": loc.get("latitude"),
                    "longitude": loc.get("longitude"),
                },
                "types": p.get("types", []),
            })
        return places if places else [{"message": f"No {place_type} found within {radius_meters}m."}]
    except Exception as e:
        return [{"error": f"Failed to call Places API (New): {str(e)}"}]


BUCKET_NAME = "fitcoach-assets-qwiklabs-gcp-04-31e92fc7c50b"


async def generate_fitness_image(
    prompt: str,
    item_title: str,
    aspect_ratio: str = "1:1",
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """Generate a high-quality fitness or gear image using the gemini-3.1-flash-lite-image model.

    The generated image is saved as an artifact in the session (viewable in the Playground Artifacts panel)
    and uploaded to the public Cloud Storage bucket, returning its public HTTPS URL.

    Args:
        prompt: Detailed visual prompt describing the fitness scene, workout badge, athlete, or gear item.
        item_title: Short title or slug for the image filename (e.g., 'strength_badge', 'trail_running_shoe').
        aspect_ratio: Aspect ratio of the generated image: '1:1', '3:2', '2:3', '4:3', '16:9' (default '1:1').
        tool_context: ToolContext injected by ADK runtime for artifact management.

    Returns:
        A dictionary containing the image title, public Cloud Storage URL, and artifact version.
    """
    import re
    import time
    from google import genai
    from google.cloud import storage

    # Clean filename
    clean_slug = re.sub(r"[^a-zA-Z0-9_\-]", "_", item_title.strip().lower())
    timestamp = int(time.time())
    filename = f"{clean_slug}_{timestamp}.jpg"

    try:
        # Initialize Google GenAI client in global region for gemini-3.1-flash-lite-image
        genai_client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location="global",
        )

        response = genai_client.models.generate_content(
            model="gemini-3.1-flash-lite-image",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(
                    aspect_ratio=aspect_ratio,
                    image_size="1K",
                ),
            ),
        )

        image_bytes = None
        mime_type = "image/jpeg"
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.inline_data and part.inline_data.data:
                    image_bytes = part.inline_data.data
                    mime_type = part.inline_data.mime_type or "image/jpeg"
                    break

        if not image_bytes:
            return {"error": "Model did not return any image data."}

        # 1. Save with tool_context.save_artifact for Playground Artifacts panel (when artifact service is configured)
        artifact_version = None
        if tool_context and hasattr(tool_context, "save_artifact"):
            try:
                artifact_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                artifact_version = await tool_context.save_artifact(
                    filename=filename,
                    artifact=artifact_part,
                    custom_metadata={"prompt": prompt, "item_title": item_title},
                )
            except Exception as art_err:
                # Log or note artifact service state, but continue to upload to Cloud Storage
                artifact_version = f"local_preview (artifact service note: {art_err})"

        # 2. Upload directly to public Cloud Storage bucket in memory (no local file)
        gcs_client = storage.Client(project=PROJECT_ID)
        bucket = gcs_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(image_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

        return {
            "status": "success",
            "item_title": item_title,
            "filename": filename,
            "public_url": public_url,
            "artifact_version": artifact_version,
            "message": f"Successfully generated '{item_title}' image and uploaded to {public_url}",
        }
    except Exception as e:
        return {"error": f"Failed to generate and upload image: {str(e)}"}


async def generate_fitness_video(
    prompt: str,
    item_title: str,
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """Generate a short fitness or workout demonstration video using Google's Omni model (gemini-omni-flash-preview).

    The generated video is saved as an artifact in the session (viewable in the Playground Artifacts panel)
    and uploaded to the public Cloud Storage bucket, returning its public HTTPS URL.

    Args:
        prompt: Detailed visual prompt describing the exercise motion, athletic movement, or fitness gear demo.
        item_title: Short title or slug for the video filename (e.g., 'barbell_squat_form', 'kettlebell_swing').
        tool_context: ToolContext injected by ADK runtime for artifact management.

    Returns:
        A dictionary containing the video title, public Cloud Storage URL, and artifact status.
    """
    import base64
    import re
    import time
    from google import genai
    from google.cloud import storage

    clean_slug = re.sub(r"[^a-zA-Z0-9_\-]", "_", item_title.strip().lower())
    timestamp = int(time.time())
    filename = f"{clean_slug}_{timestamp}.mp4"
    mime_type = "video/mp4"

    try:
        # Initialize Google GenAI client in global region for gemini-omni-flash-preview
        genai_client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location="global",
        )

        interaction = genai_client.interactions.create(
            model="gemini-omni-flash-preview",
            input=prompt,
        )

        video_bytes = None
        if hasattr(interaction, "output_video") and interaction.output_video:
            video_bytes = base64.b64decode(interaction.output_video.data)
        elif hasattr(interaction, "outputs") and interaction.outputs:
            for out in interaction.outputs:
                if getattr(out, "type", None) == "video" and getattr(out, "data", None):
                    video_bytes = base64.b64decode(out.data)
                    break

        if not video_bytes:
            return {"error": "Model did not return any video data."}

        # 1. Save with tool_context.save_artifact for Playground Artifacts panel
        artifact_version = None
        if tool_context and hasattr(tool_context, "save_artifact"):
            try:
                artifact_part = types.Part.from_bytes(data=video_bytes, mime_type=mime_type)
                artifact_version = await tool_context.save_artifact(
                    filename=filename,
                    artifact=artifact_part,
                    custom_metadata={"prompt": prompt, "item_title": item_title},
                )
            except Exception as art_err:
                artifact_version = f"local_preview (artifact service note: {art_err})"

        # 2. Upload directly to public Cloud Storage bucket in memory (no local file)
        gcs_client = storage.Client(project=PROJECT_ID)
        bucket = gcs_client.bucket(BUCKET_NAME)
        blob = bucket.blob(filename)
        blob.upload_from_string(video_bytes, content_type=mime_type)

        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{filename}"

        return {
            "status": "success",
            "item_title": item_title,
            "filename": filename,
            "public_url": public_url,
            "artifact_version": artifact_version,
            "message": f"Successfully generated '{item_title}' video and uploaded to {public_url}",
        }
    except Exception as e:
        return {"error": f"Failed to generate and upload video: {str(e)}"}


SANDBOX_RESOURCE_NAME = "projects/885543739781/locations/us-central1/reasoningEngines/9121958856744763392/sandboxEnvironments/7295712923962310656"
MEMORY_BANK_ID = "9121958856744763392"
MEMORY_BANK_LOCATION = "us-central1"

code_executor = AgentEngineSandboxCodeExecutor(
    sandbox_resource_name=SANDBOX_RESOURCE_NAME
)


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: After each agent turn, extract and persist durable user memories into Vertex AI Memory Bank."""
    try:
        await callback_context.add_session_to_memory()
    except (ValueError, Exception):
        # Gracefully handle when memory service is not initialized/available (e.g. in unit tests without memory service)
        pass
    return None


def memory_bank_service_builder():
    """Builds the VertexAiMemoryBankService when deployed on Agent Runtime."""
    return VertexAiMemoryBankService(
        project=PROJECT_ID,
        location=MEMORY_BANK_LOCATION,
        agent_engine_id=MEMORY_BANK_ID,
    )


schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description="""You are FitCoach AI, an intelligent, motivating fitness, training, and athletic gear coach.
You remember the user's stated fitness goals, preferences, allergies, injuries, schedule, and personal records across sessions and use them to personalize your recommendations.
You help users explore workout routines, look up comprehensive exercise mechanics, calculate strength benchmarks (like 1RM), log completed workouts, review fitness history, find local fitness facilities using Google Maps, execute Python calculations/data analysis in a secure cloud sandbox, and generate visual fitness badges, workout cards, and gear concept images.
Always leverage your tools (PreloadMemoryTool, Firestore catalog & history, 1RM estimator, public exercise database, Geocoding, Places API, and image generation) and your Python code execution sandbox to provide accurate, engaging, and personalized recommendations.""",
    workflow_description="Analyze the user request, call necessary tools or code executor, and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=code_executor,
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
    tools=[
        PreloadMemoryTool(),
        list_routines,
        get_routine_details,
        log_workout,
        get_user_workout_history,
        estimate_one_rep_max,
        search_public_exercises,
        geocode_address,
        find_nearby_places,
        generate_fitness_image,
        generate_fitness_video,
    ],
)

app = App(
    root_agent=root_agent,
    name="app",
)

