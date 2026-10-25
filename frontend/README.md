# GridBricks Energy

A full-stack web application for UK wind generation forecasting and forecast accuracy analysis using Elexon BMRS data.

## Features

- View available wind generation forecasts.
- Retrieve actual wind generation data from Elexon.
- Compare forecasts with actual generation.
- Calculate Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and Mean Absolute Percentage Error (MAPE).
- Filter analysis by settlement date.
- Run the backend using Docker.

## Technology Stack

- Frontend: React, TypeScript, Vite
- Backend: Python, FastAPI
- Data source: Elexon BMRS API
- Containerization: Docker and Docker Compose
- Testing: pytest

## Project Structure

- `backend/` — FastAPI application, Elexon API integration, Dockerfile, and tests.
- `frontend/` — React and TypeScript application.
- `docker-compose.yml` — Docker Compose configuration.
- `.gitignore` — Excludes generated files and local secrets.

## Prerequisites

- Docker Desktop
- Node.js and npm (for local frontend development)
- Python (for running backend tests locally)

## Run with Docker

From the project root, run:

```bash
docker compose up --build -d
