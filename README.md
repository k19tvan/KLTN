# REC-8K Video Transformation Studio

A modular tracking, curation, and visualization platform for transforming static **REC-8K** (Referring Expression Counting) image benchmarks into dynamic 6-second video benchmarks with controlled object dynamics (appearing & disappearing target objects).

---

## 🌟 Key Features

1. **Curated Dataset Extraction**:
   - Parses `../dataset/REC-8K/annotations.json` across 11 category types (`action`, `color`, `orientation`, `age`, `gender`, `location`, `accessory`, `clothing`, `variety`, `size`, `material`).
   - Automatically filters for candidate samples with counting points strictly smaller than 15 ($0 < \text{points} < 15$).
   - Deterministically extracts a balanced set of 50 samples per category (and all available for rarer categories, totaling 392 curated samples).
   - Saved and managed under `storage/dataset.json`.

2. **Visual Grounding Inspector**:
   - High-resolution image canvas viewer.
   - Interactive toggle to display or hide counting points.
   - High-contrast numbered circular markers ($1, 2, \dots, N$) plotted directly on target object coordinates.
   - Coordinate readout list with direct image link.

3. **LLM-Powered 6-Second Video Scripting**:
   - Integrated with `langchain_openai` configured via `.env` (`BASE_URL`, `API_KEY`, `MODEL_NAME`).
   - Python interface:
     ```python
     create_script(image, description, disappear_cnt, appear_cnt)
     ```
   - Automatically drafts chronological 6-second video prompts (0-2s establishing, 2-4s dynamic transition, 4-6s stabilization).
   - Built-in graceful offline fallback generator if the self-hosted LLM server is temporarily offline.
   - One-click "Copy Prompt" button for easy transfer to external video generation tools (Runway, Kling, Luma Dream Machine, Pika, Sora).

4. **Persistent Video Ingestion & HTML5 Player**:
   - Drag-and-drop video dropzone in the UI supporting `.mp4`, `.webm`, and `.mov`.
   - Files are automatically saved to `storage/videos/{sample_id}.mp4` so they **persist permanently across backend restarts and browser reloads**.
   - Built-in video player with scrub controls, loop toggle, "Replace Video", and "Remove Video" actions.

5. **Project Completion Tracking**:
   - Real-time progress bars: `% Scripted` and `% Videos Ready`.
   - Filter by Category, Lifecycle Status (`Pending`, `Scripted`, `Video Ready`), and text search.

---

## 🚀 Quick Start

### 1. Configure `.env`
Edit or copy `.env.example` to `.env`:
```ini
BASE_URL=http://localhost:8000/v1
API_KEY=your_api_key_or_EMPTY
MODEL_NAME=meta-llama/Llama-3.1-8B-Instruct
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
```

### 2. Run the Application (Clean Code Rule E1)
Launch the server with a single command:
```bash
./run.sh
```
Or directly:
```bash
python3 main.py
```
Open your browser at: **`http://localhost:8000`**

### 3. Run Unit Tests (Clean Code Rule E2)
Run the automated test suite (< 3s total):
```bash
python3 -m unittest discover tests
```

---

## 🏛️ Architecture & Clean Code Compliance

This project follows Robert C. Martin's *Clean Code* catalog as referenced in `/workspace/projects/my-skills/skills/clean-code-skills/skills`:
- **Functions (F1)**: Request parameters encapsulated in dataclasses/models (`ScriptRequest`, `ScriptInput`).
- **Functions (F2)**: Pure functions returning explicit objects; no output mutation arguments.
- **Functions (F3)**: No boolean flag arguments directing split behavior.
- **Python Conventions (P1-P3)**:
  - No wildcard imports (`P1`).
  - `SampleStatus` implemented as an `Enum`, eliminating magic strings (`P2`).
  - Strict type hints on public interfaces (`P3`).
- **General (G5, G25, G30)**:
  - DRY persistence helpers (`G5`).
  - Named constants for paths, video duration (6s), and point threshold (15) (`G25`).
  - Single-responsibility functions (`G30`).

---

## 📁 Project Structure

```text
video_generation/
├── .env                       # LLM and server configuration
├── .env.example               # Configuration template
├── config.py                  # Strongly-typed configuration settings
├── main.py                    # Application entry point & FastAPI static mounting
├── run.sh                     # Executable launch script
├── README.md                  # Project documentation
├── domain/
│   ├── __init__.py
│   └── models.py              # Pydantic domain models (Sample, ScriptParams, Stats)
├── services/
│   ├── __init__.py
│   ├── dataset_service.py     # Extraction, query filters, atomic JSON persistence
│   ├── llm_service.py         # langchain_openai client & create_script() function
│   └── video_service.py       # Video file persistence under storage/videos/
├── api/
│   ├── __init__.py
│   └── routes.py              # REST API endpoints (/api/stats, /api/samples, etc.)
├── static/
│   ├── index.html             # Responsive Single-Page Application UI
│   ├── app.js                 # Frontend application & Canvas point rendering logic
│   └── style.css              # Styling and dark theme
├── storage/
│   ├── dataset.json           # Persisted dataset and sample state
│   └── videos/                # Uploaded video files ({sample_id}.mp4)
├── tests/
│   ├── test_dataset_service.py # Dataset extraction and boundary tests
│   ├── test_llm_service.py     # Script generation tests
│   └── test_api_endpoints.py   # REST API and upload integration tests
└── packages/                  # Bundled dependencies
```
