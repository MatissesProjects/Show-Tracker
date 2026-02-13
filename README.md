# Show Tracker

A tool to analyze viewing history and discover media based on shared actors, directors, and creators.

## Tech Stack
- **Backend:** Python (Flask) + SQLite (SQLAlchemy)
- **Frontend:** Vue.js (3.x) + Tailwind CSS

## Getting Started

### Prerequisites
- Python 3.8+

### Setup
1. **Create Virtual Environment:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. **Install Dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

### Running the Application
1. **Start the Flask Backend:**
   ```powershell
   python app.py
   ```
   The API will be available at `http://localhost:5000`.

2. **Open the Frontend:**
   Open `frontend/index.html` in your web browser.

### Running Tests
Execute the following command to run the backend test suite:
```powershell
.\venv\Scripts\python.exe -m pytest
```

## Project Structure
- `app.py`: Flask application entry point.
- `models.py`: Database schema (Media, People, Watch History).
- `frontend/`: Vue.js frontend code.
- `tests/`: Pytest suite for backend logic.
- `conductor/`: Project planning and track management.
