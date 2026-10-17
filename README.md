# CineDNA

Discover movies by how they feel, not just by genre.

CineDNA is a React + FastAPI movie recommendation prototype. It combines hand-curated Movie DNA profiles with a broader, live TMDB candidate catalog for title and vibe searches when a free TMDB API Read Access Token is configured. The current natural-language interpreter and generated Movie DNA profiles are **heuristic/rule-based**, not yet an LLM or vector-search system. Without the token, only the small offline catalog is available.

## Deploy on Vercel

Import `sugianand/CineDNA` as **one Vercel project**. Set **Root Directory** to
the repository root (`.`), not `frontend` or `backend`, select the **Vite**
framework preset, and use **Node.js 22.x**. The root `vercel.json` supplies:

| Setting | Value |
| --- | --- |
| Install command | `npm --prefix frontend ci --no-audit --no-fund` |
| Build command | `npm --prefix frontend run build` |
| Output directory | `frontend/dist` |
| Python runtime | 3.12, pinned in `.python-version` |
| Python dependencies | Root `requirements.txt` includes `backend/requirements.txt` |

The React SPA is served as static assets. `api/index.py` exports the existing
FastAPI ASGI app without starting Uvicorn or binding a port. API rewrites precede
the catch-all `/index.html` rewrite, so client-side URLs can be refreshed and
API requests still return JSON. Existing `/health`, `/movies`, `/search`,
`/docs`, `/redoc`, and `/openapi.json` backend URLs are also routed to the function.
The Python bundle excludes frontend files and tests. Its duration budget is
30 seconds; TMDB requests already use bounded timeouts and an offline fallback.

### Environment variables

Set these in **Vercel → Project Settings → Environment Variables**, choosing
Production and Preview as appropriate, then deploy or redeploy:

| Variable | Required? | Purpose / Vercel value |
| --- | --- | --- |
| `TMDB_READ_TOKEN` | For the live catalog | TMDB **API Read Access Token** (bearer token). Server-side secret. Without it, the bundled offline catalog still works. |
| `VITE_API_URL` | No | Leave **unset** for this deployment so requests use the same origin. For a separate API only, use its origin without a trailing slash or `/api`. Vite embeds this public value at build time. Remove any old Render URL and rebuild. |
| `CORS_ORIGINS` | No | Only for a separately hosted frontend: comma-separated allowed origins. Same-origin Vercel and preview URLs need no setting. Defaults to `http://localhost:5173` for local development. |
| `VERCEL_GIT_COMMIT_SHA` | Automatic | Vercel Git deployment metadata, used by `/api/health` as `revision`; do not enter manually. Non-Git deployments can report `local`. |
| `RENDER_GIT_COMMIT` | Legacy / automatic | Render revision fallback; do not migrate this variable to Vercel. |
| `PORT` | Docker only | Uvicorn port, defaults to `10000` in the Dockerfile. Unnecessary on Vercel. |

`OPENAI_API_KEY` and `OPENAI_MODEL` appeared in the old backend example file but
are not read anywhere in the application. No OpenAI key, model setting, database,
or storage service is required. The example files now list only used settings.
The app does not automatically load `.env` files; for local API development,
export the values in your shell or pass `--env-file .env` to Uvicorn.

### Verify and switch from Render

1. Deploy a Vercel preview with `TMDB_READ_TOKEN` configured if live search is needed.
2. Check `/api/health`: `status` should be `ok`, `tmdb_enabled` should match your
   token configuration, and `revision` should match the deployed Git commit.
3. Test a title search, a vibe search, and opening/refreshing a shared movie URL.
   Check `/docs` and confirm an unknown `/api/...` URL returns an API 404, not HTML.
4. Promote the verified deployment or merge the migration branch and deploy `main`.
   Update any custom domain/DNS and public links to the Vercel project.
5. After checking the production site, retire the old Render services separately.

There is no persistent server-side file storage or database to migrate: the
catalog is Python data bundled with the function, and recent searches are stored
in browser `localStorage`. Browser history stays with its origin, so a new domain
starts with empty recent searches. The Dockerfile and `render.yaml` remain as
optional fallback deployments; Vercel does not use their ports, URLs, or services.

References: [Vite SPA rewrites](https://vercel.com/docs/frameworks/frontend/vite)
and [Python ASGI functions in /api](https://vercel.com/docs/functions/runtimes/python/api-directory).

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

Run Vercel entrypoint smoke tests from the repository root after installing the
root `requirements.txt`:

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
