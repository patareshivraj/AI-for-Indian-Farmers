# Farm 360 - AI Layer & Intelligence Engine 🌾🤖

Welcome to the Farm 360 AI Layer. This repository contains the autonomous intelligence engine responsible for dynamically discovering, extracting, and matching government agricultural schemes to Indian farmers using LLaMA 3.3.

This document serves as the **Integration Hand-off Guide** for Frontend and Backend developers to easily connect their microservices or UIs to this AI engine.

---

## 🚀 Quick Start (Local Development)

To run this AI layer locally on your machine without Docker:

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/patareshivraj/AI-for-Indian-Farmers.git
   cd AI-for-Indian-Farmers
   ```

2. **Set up the Virtual Environment:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   source .venv/bin/activate  # On Mac/Linux
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set your Groq AI Key:**
   *(Ask the AI Architect for the Development Key)*
   ```bash
   # On Windows PowerShell
   $env:GROQ_API_KEY="your_groq_api_key_here"
   # On Mac/Linux
   export GROQ_API_KEY="your_groq_api_key_here"
   ```

5. **Run the Database Migrations & Start Server:**
   ```bash
   python manage.py migrate
   python manage.py runserver
   ```
   *The AI API is now running locally at `http://127.0.0.1:8000/api/v1/`.*

*(Note: Celery is configured to run synchronously (`CELERY_TASK_ALWAYS_EAGER = True`) for local development, so you do not need Redis to test the AI locally).*

---

## 🔌 Integration Guide for Backend Developers

If you are building the main Django/Node backend and need to interact with the AI Layer, you have two options:

### Option 1: Trigger via REST API
You can simply make HTTP POST requests from your backend microservice to our AI Layer endpoints.
- **Generate AI Match:** Send a `POST` to `/api/v1/recommendations/generate/` with `{"farmer_id": "123"}`. The AI will wake up, evaluate the farmer, and save the score.

### Option 2: Trigger via CLI (Cron Jobs)
The AI layer comes with pre-built management commands. You can set up Crontab or Celery beat in your architecture to run these nightly:
1. `python manage.py discover_schemes` (Harvests new URLs via DuckDuckGo)
2. `python manage.py process_schemes_ai` (Extracts unstructured text into JSON using Groq)
3. `python manage.py consolidate_schemes` (Deduplicates schemes into Golden Records)
4. `python manage.py recommend_schemes` (Runs the recommendation engine against Farmer profiles)

---

## 📱 Integration Guide for Frontend Developers

If you are building the Mobile App (React Native/Flutter) or Web UI (React/Next.js), you can consume the structured AI data directly via our REST APIs.

### Base URL: `http://127.0.0.1:8000/api/v1/`

### 1. View All Schemes (Discovery Feed)
Get a list of all dynamically discovered government schemes.
- **Endpoint:** `GET /schemes/`
- **Features:** Paginated (limit/offset), searchable.
- **Example Search:** `GET /schemes/?search=tractor`

### 2. View Personalized Farmer Matches
Get the AI's personalized recommendations for a specific farmer.
- **Endpoint:** `GET /recommendations/?farmer_id=TEST-FARMER-001`
- **Response Format:**
  ```json
  [
    {
      "id": 1,
      "total_score": 80,
      "ai_reasoning": "The farmer profile matches the criteria for small farmers...",
      "matched_conditions": ["Farmer category is Marginal"],
      "unclear_conditions": ["State", "District"],
      "scheme": {
         "canonical_name": "PMFBY Scheme",
         "benefits": ["Crop Insurance"],
         "apply_url": "https://pmfby.gov.in/apply"
      }
    }
  ]
  ```

### 3. Provide AI Feedback (Crucial for UI)
When a farmer clicks "Apply" or swipes away a scheme, the frontend MUST notify the AI layer so it learns over time.
- **Endpoint:** `PATCH /recommendations/{id}/feedback/`
- **Payload:** `{"action": "apply"}` or `{"action": "dismiss"}`

---

## 📂 Architecture Overview

- **`models.py`:** Contains the `SchemeMaster` (Golden Records) and `SchemeRecommendation` (AI Match Score) tables.
- **`ai_processor.py`:** The Groq integration that extracts text into JSON.
- **`intelligence.py`:** The Deduplication funnel.
- **`recommender.py`:** The prompt engineering pipeline that calculates the 0-100 eligibility score.
- **`api_views.py`:** The Django REST Framework viewsets exposing the data to the frontend.

For any architectural questions, please contact the AI Systems team.
