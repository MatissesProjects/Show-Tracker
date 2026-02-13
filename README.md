# 🎬 Show Tracker | Media Intelligence Dashboard

Show Tracker is a personal data-intelligence tool that transforms your raw streaming history into a powerful recommendation engine. By analyzing thousands of data points from your viewing habits, it identifies your "Talent Core" and "Genre DNA" to help you discover what to watch next with cinematic precision.

![Show Tracker UI](https://img.shields.io/badge/UI-Dark_Mode-blueviolet)
![Engine](https://img.shields.io/badge/Intelligence-TVmaze_%2B_OMDb-indigo)
![Database](https://img.shields.io/badge/Storage-SQLite-blue)

## 🚀 Key Features

### 1. Deep History Ingestion
*   **Netflix Integration:** Import your full `ViewingActivity.csv` and watch as thousands of entries are instantly processed.
*   **Smart Deduplication:** Automatically groups 5,000+ individual episode entries into clean, manageable unique series records.

### 2. Media Intelligence (Enrichment)
*   **Metadata Harvesting:** Connects to OMDb to pull rich metadata, including Cast, Directors, Genres, IMDb Ratings, and Plot Summaries.
*   **Taste Profiling:** Ranks your "Top Talent" by how many unique shows/films you've watched them in, not just episode counts.

### 3. Proactive Discovery Engine
*   **Match Scoring:** Every potential show is given a "Compatibility Score" based on your specific history and "Thumbs Up" feedback.
*   **Interactive Carousel:** A sleek, horizontal discovery section that proactively finds new works featuring your favorite actors.
*   **Netflix Tagging:** Automatically identifies if a recommendation is currently available on Netflix.

### 4. Interactive Analytics
*   **Drill-Down Filtering:** Click any actor or genre in your sidebar to instantly pivot the recommendation engine to that specific talent or category.
*   **Training Mode:** Use the Thumbs Up/Down system to refine your profile. "Liked" talent receive a +30 score boost in future suggestions.

---

## 🛠️ Tech Stack
*   **Backend:** Python Flask + SQLAlchemy (SQLite)
*   **Frontend:** Vue.js 3 (Composition API) + Tailwind CSS
*   **Intelligence:** TVmaze API (Proactive Search) & OMDb API (Metadata)

---

## 🏁 Getting Started

### Prerequisites
*   Python 3.8+
*   An OMDb API Key (Free at [omdbapi.com](http://www.omdbapi.com/apikey.aspx))

### Setup
1. **Initialize Environment:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

2. **Configure API:**
   Create a `.env` file in the root and add your key:
   ```env
   OMDB_API_KEY=your_key_here
   ```

### Running the System
You must run both servers simultaneously:

1. **Start Intelligence API (Backend):**
   ```powershell
   python app.py
   ```

2. **Start Cinematic UI (Frontend):**
   ```powershell
   python -m http.server 5001 --directory frontend
   ```
   Access the dashboard at `http://localhost:5001`.

### 📂 How to get your data
1.  Go to [Netflix Account Settings](https://www.netflix.com/YourAccount).
2.  select a profile. - Or if there are multiple select Manage Profiles and select yours
3.  Click **Watch history**.
4.  Click **Download All** at the bottom of the page.
5.  Upload the resulting `NetflixViewingHistory.csv` into the dashboard using the **IMPORT FEED** button.

---

## 📂 Project Architecture
*   `utils/recommender.py`: The heart of the scoring and cross-referencing logic.
*   `utils/parser.py`: Handles complex Netflix CSV parsing and title normalization.
*   `utils/enricher.py`: Manages the data pipeline between OMDb and the local DB.
*   `models.py`: Relational schema for Media, People, and Watch History.
