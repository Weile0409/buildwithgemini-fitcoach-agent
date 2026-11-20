# FitCoach AI

FitCoach AI is an intelligent fitness and athletic coaching assistant built with the Google Agent Development Kit (ADK) and deployed to Google Cloud Agent Platform. It helps athletes and fitness enthusiasts design structured training regimens, estimate strength metrics, track completed workouts in a persistent database, discover nearby fitness facilities, and generate visual badges and demonstration videos.

![FitCoach AI Demo](./demo.gif)

---

## What the Agent Actually Does

Based on the implemented tools and services wired into `app/agent.py`:

- **Long-term Memory (Vertex AI Memory Bank)**: Automatically retains user profile facts, preferences, injury history, and fitness goals across sessions via `PreloadMemoryTool` and Vertex AI Memory Bank.
- **Persistent Workout Logging (Google Cloud Firestore)**: Stores completed workout sessions and queries exercise history using the native Firestore client (`log_workout`, `get_user_workout_history`).
- **Structured Training Routines**: Fetches built-in workout regimens (`list_routines`, `get_routine_details`) across strength, hypertrophy, and conditioning.
- **Physical Sandbox Computations (Agent Engine Code Execution)**: Executes safe Python calculations inside an Agent Engine Sandbox environment to compute One-Rep Max benchmarks (`estimate_one_rep_max`) using Brzycki and Epley formulas.
- **Public Exercise Directory**: Queries and searches exercises with step-by-step form cues and primary muscle group classifications (`search_public_exercises`).
- **Local Gym & Facility Lookup (Google Maps Places API)**: Geocodes addresses and searches nearby athletic centers and gym facilities (`geocode_address`, `find_nearby_places`).
- **Visual Image Generation (Google Cloud Storage & Gemini Image Gen)**: Generates customized motivational badges and gear artwork using `gemini-3.1-flash-lite-image`, uploads them to Google Cloud Storage (`gs://fitcoach-assets-...`), and exposes public HTTPS URLs (`generate_fitness_image`).
- **Video Generation (Gemini Omni Preview & Google Cloud Storage)**: Generates short exercise form demonstration clips using Google's Omni model `gemini-omni-flash-preview` via the Interactions API, saving session artifacts and streaming video files to Google Cloud Storage (`generate_fitness_video`).
- **Rich Display Cards (A2UI)**: Renders interactive, structured UI cards, columns, headers, and media directly into the chat interface using `A2uiSchemaManager` (version 0.8 Basic Catalog) and an `after_model_callback`.

*(Note: Gear recommendations and pace/heart-rate zone formulas mentioned in early concept notes were evaluated and remain planned for future iterations).*

---

## Architecture & Google Cloud Integrations

| Capability | Component / Service | Implementation |
|---|---|---|
| **Core Framework** | Google Agent Development Kit (ADK) | `google.adk` (Agent, App, Runner) |
| **Model** | Gemini 2.5 Flash | Vertex AI Reasoning Engines / Agent Runtime |
| **Cross-Session Memory** | Vertex AI Memory Bank | `VertexAiMemoryBankService` |
| **Code Execution** | Agent Engine Sandbox | `AgentEngineSandboxCodeExecutor` |
| **Database** | Google Cloud Firestore | Native Firestore client (`google.cloud.firestore`) |
| **Asset Storage** | Google Cloud Storage | Public bucket asset persistence (`google.cloud.storage`) |
| **Image Generation** | Gemini 3.1 Flash Lite Image | `genai.Client` in global region |
| **Video Generation** | Gemini Omni Flash Preview | `genai.Client.interactions` in global region |
| **Location & Maps** | Google Places API (New) | Google Maps textSearch & geocoding REST |
| **Agent Protocol** | Agent-to-Agent (A2A) | `a2a-sdk` standard endpoints |

---

## Running Locally

### 1. Prerequisites
- Python 3.11+
- `uv` package manager installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- Google Cloud CLI (`gcloud`) authenticated with project access

### 2. Environment Setup
Clone the repository and install the project dependencies:
```bash
cd fitcoach-agent
uv sync
```

Set up your required environment variables:
```bash
export GOOGLE_GENAI_USE_VERTEXAI=true
export GOOGLE_CLOUD_PROJECT="<YOUR_GCP_PROJECT_ID>"
export GOOGLE_CLOUD_LOCATION="us-east1"
export GOOGLE_MAPS_API_KEY="<YOUR_GOOGLE_MAPS_API_KEY>"
```

### 3. Launch Agent Playground
Start the local ADK developer playground with live reload and memory bank connection:
```bash
uv run adk web . --port 8080 --reload_agents --memory_service_uri=agentengine://<YOUR_MEMORY_BANK_ID>
```

### 4. Run the Custom Chat Frontend
To run the included lightweight chat interface and A2UI card renderer:
```bash
cd frontend
pip install -r requirements.txt
export AGENT_ENGINE_RESOURCE_NAME="<YOUR_AGENT_ENGINE_RESOURCE_NAME>"
export AGENT_DIRECTORY="app"
python main.py
```
Open a browser and navigate to the local port indicated in the terminal output.

---

## Deployment

Deploy the agent to Vertex AI Agent Platform using `agents-cli`:
```bash
agents-cli deploy \
  --project "<YOUR_GCP_PROJECT_ID>" \
  --update-env-vars GOOGLE_MAPS_API_KEY="<YOUR_GOOGLE_MAPS_API_KEY>"
```

Deploy the frontend proxy to Cloud Run:
```bash
cd frontend
gcloud run deploy fitcoach-frontend \
  --source . \
  --region us-east1 \
  --allow-unauthenticated \
  --set-env-vars AGENT_ENGINE_RESOURCE_NAME="<YOUR_AGENT_ENGINE_RESOURCE_NAME>",AGENT_DIRECTORY="app"
```
