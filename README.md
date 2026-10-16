# CineDNA

Discover movies by how they feel, not just by genre.

CineDNA is a React + FastAPI movie recommendation prototype. It combines hand-curated Movie DNA profiles with a broader, live TMDB candidate catalog for title and vibe searches when a free TMDB API Read Access Token is configured. The current natural-language interpreter and generated Movie DNA profiles are **heuristic/rule-based**, not yet an LLM or vector-search system. Without the token, only the small offline catalog is available.

## Published sites

CineDNA uses a split Render deployment so the interface loads from the CDN even
when the free API service is waking from an idle period:

- Website: [cinedna-app.onrender.com](https://cinedna-app.onrender.com)
- API: [cinedna-hpji.onrender.com](https://cinedna-hpji.onrender.com)

The static website calls `/api/health` as soon as it loads. That starts warming
the API before the user submits a search. A custom domain can be attached to the
static site later without changing this architecture.

## Deploy with the Render Blueprint

This repo includes a multi-stage Dockerfile and a Render Blueprint
(`render.yaml`). The Blueprint creates a CDN-backed React static site and a
FastAPI web service.

1. Sign in to [Render](https://render.com/) and connect GitHub.
2. Create a free TMDB API Read Access Token.
3. Choose **New → Blueprint** and select `sugianand/CineDNA`.
4. Enter the token when Render prompts for `TMDB_READ_TOKEN`, then deploy.
5. Share the static site's public `onrender.com` URL.

For a service that was already created from this Blueprint, add
`TMDB_READ_TOKEN` under **Environment** in the Render Dashboard and redeploy.
Render preserves that secret on future Blueprint syncs.

Render automatically redeploys new commits on `main`. Free API instances may
sleep when idle, but the static site remains immediately available and warms the
API in the background.

Alternatively, create a Render Web Service with **Docker** runtime from this
repo. The health check is `/api/health`. If the frontend is hosted separately,
set `CORS_ORIGINS` on the web service and `VITE_API_URL` while building the
frontend.

## Local development

Backend (Python 3.12+):

```bash
cd backend
python -m venv .venv
# Activate your virtual environment.
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend (Node.js 22+, separate terminal):

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` requests to the backend.

Docker (optional):

```bash
docker build -t cinedna .
docker run --rm -p 10000:10000 cinedna
```

Open `http://localhost:10000` to see the combined site.

Run API smoke tests from the `backend` directory:

```bash
python -m unittest discover -s tests -v
```

## API

- `GET /api/health`: service health and catalog size
- `GET /api/movies`: starter catalog
- `POST /api/search`: recommendations for a natural-language query
- `GET /docs`: interactive API documentation

## Roadmap

Add LLM-based query understanding, semantic embeddings, more movies, poster art, and personalized recommendations.
