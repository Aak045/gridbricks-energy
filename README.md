# Gridbricks Energy

A full-stack application for analyzing UK wind generation forecasts and evaluating forecast accuracy using Elexon BMRS data.

**Live application:** https://gridbricks-energy.vercel.app  
**Demo video:** https://youtu.be/Py1E6EMiQro

## Overview

Gridbricks Energy helps users compare forecast wind generation with actual wind generation over a selected period. It calculates forecast accuracy metrics and presents the results in an interactive dashboard.

The assignment focuses on data relevant to electricity purchasing decisions in January 2026.

## Features

- Retrieve wind generation forecast data from Elexon BMRS.
- Retrieve actual wind generation data.
- Filter analysis by settlement date.
- Compare forecast and actual generation for matched periods.
- Calculate Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and Mean Absolute Percentage Error (MAPE).
- Visualize forecast accuracy through a dashboard and chart.

## Technology Stack

- **Frontend:** React, TypeScript, Vite
- **Backend:** Python, FastAPI
- **Data source:** Elexon BMRS API
- **Containerization:** Docker, Docker Compose
- **Testing:** pytest
- **Deployment:** Vercel

## Project Structure

- `backend/` — FastAPI application, data retrieval and analysis logic, backend tests, and backend dependencies.
- `frontend/` — React application, dashboard components, styling, and frontend dependencies.
- `docker-compose.yml` — Configuration for running services locally with Docker Compose.
- `vercel.json` — Vercel deployment and routing configuration.
- `README.md` — Project documentation and setup instructions.
- `.gitignore` — Excludes configured files and directories from Git.

## Run Locally

### Prerequisites

Install Python, Node.js with npm, and Docker Desktop if you want to use Docker Compose.

### Option 1: Docker Compose

From the project root, run:

```bash
docker compose up --build
```

Open the local URL and port configured by the project's Docker Compose setup.

### Option 2: Run services separately

Start the backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

In a separate terminal, start the frontend:

```bash
cd frontend
npm install
npm run dev
```

Use the local URLs and ports reported by the development servers and configured API settings.

## Testing

From the backend directory, run:

```bash
python -m pytest test_main.py -v
```

## Deployment

The application is deployed at:

https://gridbricks-energy.vercel.app

The backend health endpoint is available at:

https://gridbricks-energy.vercel.app/api/health

## Data and Interpretation Notes

Forecast accuracy depends on matching forecasts and actual generation to comparable settlement periods. Forecast publication time is also important when evaluating what information would have been available when a purchasing decision was made.

MAE and RMSE are expressed in the underlying generation unit. MAPE can be sensitive to zero or near-zero actual values and should be interpreted accordingly.

The dashboard supports analysis; it does not execute electricity purchases or guarantee financial savings.

## AI Tool Disclosure

AI assistance was used during development for coding support, debugging, explanation, and documentation. Generated suggestions were reviewed and tested as part of the development process.

## Limitations and Future Improvements

Potential improvements include stricter forecast-publication-time selection for historical decision analysis, clearer data freshness indicators, additional edge-case tests, and more detailed analysis of forecast errors.

