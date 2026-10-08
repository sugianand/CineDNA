# CineDNA

Discover movies by how they feel, not just by genre.

CineDNA is a React + FastAPI movie recommendation prototype. Its starter catalog contains hand-curated Movie DNA profiles. The current natural-language interpreter is **rule-based**, not yet an LLM or vector-search system.

## Publish CineDNA as one website

This repo includes a multi-stage Dockerfile and a Render Blueprint (`render.yaml`). One container serves the React website and FastAPI API on the same domain, with no separate backend URL to configure.

1. Sign in to [Render](https://render.com/) and connect GitHub.
2. Choose **New → Blueprint** and select `sugianand/CineDNA`.
3. Review the free web service and deploy.
4. Share the public `onrender.com` URL Render assigns.

Render can automatically redeploy new commits on `main`. Free instances may sleep when idle.

Alternatively, create a Render Web Service with **Docker** runtime from this repo. The health check is `/api/health`.

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
