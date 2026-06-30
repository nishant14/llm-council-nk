# Expose LLM Council behind nginx at a sub-path (`/content/`)

## Context

The user wants to reach this locally-built app (`backend` on :8001, Vite/React `frontend` normally on :5173) through an existing nginx reverse proxy on a different machine ("machine A"), at `https://<domain>/content/` — not at the domain root, since root is already owned by another app. The user has working infrastructure today: a tunnel terminates `https://council.199611202.xyz` on "machine B" (this app's host), which nginx on machine A can `proxy_pass` to.

A prior attempt to do this with nginx `sub_filter` rewriting HTML failed: `sub_filter` only rewrites HTML attribute values, but Vite's *dev server* serves a live ES module graph full of root-relative absolute imports (`/@vite/client`, `/@react-refresh`, `/node_modules/.vite/deps/react.js`, etc.) that are never touched by `sub_filter`, so most assets 301-redirected to the wrong place. The conclusion (confirmed correct — this is a known, well-documented Vite/dev-server limitation, not something specific to this app or a reason to abandon Vite): don't try to path-rewrite a proxied dev server. Instead, (a) build the frontend for production, where Vite's `base` config fully and correctly prefixes every asset path and import specifier at build time, and (b) make the app itself natively aware of the `/content/` prefix so nginx can be a pure 1:1 pass-through with zero rewriting anywhere in the chain.

User-confirmed decisions:
- **No framework rewrite.** Vite handles sub-path deployment natively via `base`; the dev-server proxying problem doesn't apply to a production build.
- **Sub-path:** `/content/`
- **Mode:** production build (`vite build`), not the dev server
- **Topology:** cross-machine — nginx (machine A) → tunnel → this app (machine B). nginx must do zero path rewriting; the app must natively serve everything under `/content/` itself.

Design was validated against the real files with a `TestClient`-driven check of the trickiest part (Starlette route/mount precedence, SSE-through-mount behavior, CORS-on-inner-app, forwarded-header handling). Two things came out of that validation and are folded into this plan: (1) the health-check route must move off bare `/` or it silently shadows the SPA's `index.html`, and (2) without `X-Forwarded-Proto` wired through nginx → tunnel → uvicorn, the very first navigation to `/content` (no trailing slash) 307-redirects to an `http://` URL, breaking behind TLS.

## Approach

### 1. `frontend/vite.config.js` — prefix only in production builds

Switch to the function form of `defineConfig` and set `base` conditionally so `npm run dev` is completely unaffected:

```js
export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/content/' : '/',
  plugins: [react()],
  server: { host: true, allowedHosts: true, proxy: { '/api': { target: 'http://localhost:8001', changeOrigin: true } } }
}))
```

### 2. `frontend/src/api.js` — derive `API_BASE` from Vite's injected base

Replace:
```js
const API_BASE = '';
```
with:
```js
const API_BASE = import.meta.env.BASE_URL.replace(/\/$/, '');
```
In dev, `BASE_URL` is `/` → `API_BASE` is `''` (identical to today). In the production build, `BASE_URL` is `/content/` → `API_BASE` is `/content`, so every existing `fetch(`${API_BASE}/api/...`)` call (no other code changes needed — every call site already templates through `API_BASE`) correctly hits `/content/api/...`.

### 3. `backend/main.py` — serve the built SPA and self-mount under `/content` (prod-only, env-gated)

- Rename the health check from `@app.get("/")` to `@app.get("/healthz")`. **Required**, not cosmetic: confirmed via test that an explicit `Route("/")` always wins over a later `Mount("/", StaticFiles(...))` at that exact path, so leaving it at `/` would make `/content/` return the JSON health check instead of `index.html`.
- Add `from fastapi.staticfiles import StaticFiles` and `from pathlib import Path`.
- After all existing route definitions, guard-mount the built frontend (guarded so local dev, where `frontend/dist` doesn't exist, doesn't crash on startup):
  ```python
  _frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
  if _frontend_dist.is_dir():
      app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="static")
  ```
  Known limitation (confirmed, acceptable): `StaticFiles(html=True)` serves `index.html` at the mount root and for real files, but is **not** a true wildcard SPA fallback — `GET /content/some/unmatched/path` will 404, not serve `index.html`. This app has no client-side routing (no react-router, single page) so it's a non-issue today; flag it in CLAUDE.md so it's not silently rediscovered if routing is ever added later.
- Env-gated self-mount so local dev is byte-for-byte unaffected:
  ```python
  import os
  ...
  DEPLOY_PREFIX = os.getenv("DEPLOY_PREFIX", "")
  asgi_app = app
  if DEPLOY_PREFIX:
      root_app = FastAPI()
      root_app.mount(DEPLOY_PREFIX, app)
      asgi_app = root_app

  if __name__ == "__main__":
      uvicorn.run(
          asgi_app,
          host="0.0.0.0",
          port=8001,
          forwarded_allow_ips="*" if DEPLOY_PREFIX else None,
      )
  ```
  `forwarded_allow_ips="*"` is required in the proxied/prod case: uvicorn's default only trusts `X-Forwarded-*` headers from `127.0.0.1`, and in this tunnel topology the connecting peer won't be localhost. Without this, `request.url.scheme` stays `http` even behind the TLS tunnel, and Starlette's automatic trailing-slash redirect on the mount (`/content` → `/content/`) emits an `http://` Location, breaking under TLS. (Confirmed via direct test — this was the one real gap found in the original design.)
  - CORS: no change needed. Confirmed the existing `CORSMiddleware` on the inner `app` still applies to every request reaching it through the wrapper mount — `Mount` is a transparent ASGI passthrough, doesn't need duplicating on `root_app`.
  - SSE: confirmed `StreamingResponse` passes through the mount layer untouched — no buffering or header interference from the extra mount.

Production startup on machine B becomes:
```bash
cd frontend && npm run build && cd ..
DEPLOY_PREFIX=/content uv run python -m backend.main
```
Local dev (`uv run python -m backend.main`, no env var) is unchanged — same as today.

Optionally add a small `start_prod.sh` mirroring the existing `start.sh`'s style, running those two commands, since `start.sh` itself stays dev-only (don't touch it).

### 4. nginx config on machine A (outside this repo — provide as instructions, not an automated edit)

```nginx
location /content/ {
    proxy_pass https://council.199611202.xyz/content/;
    proxy_http_version 1.1;
    proxy_set_header Host council.199611202.xyz;
    proxy_ssl_server_name on;
    proxy_ssl_name council.199611202.xyz;
    proxy_redirect https://council.199611202.xyz/ /;
    proxy_redirect http://council.199611202.xyz/ /;
    proxy_buffering off;
    proxy_read_timeout 600s;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto https;
}
```
- `proxy_set_header X-Forwarded-Proto https;` is the fix for the forwarded-scheme gap above — must reach uvicorn unmodified, so whatever terminates the tunnel on machine B must also pass it through rather than stripping it.
- The `location`/`proxy_pass` trailing slashes are both `/content/` — confirmed this performs an identity path transform (no rewriting), so `/content/api/conversations` arrives upstream exactly as `/content/api/conversations`. Keep these two trailing slashes character-identical if this is ever edited.
- `proxy_buffering off` + `proxy_read_timeout 600s` are already sufficient for the SSE endpoint's 2s keep-alives across a multi-stage run.

### 5. Required external/infra change (not in this repo, but blocking)

Whatever currently terminates `https://council.199611202.xyz` on machine B must be repointed from port **5173** (today's Vite dev server) to port **8001** (the FastAPI process, now serving both the built SPA and the API under `/content/`). After this change there is no separate frontend process in the production path — confirm this repointing happens, or the chain will reach a dead/wrong service.

### 6. Update `CLAUDE.md`

Add a short section documenting: the `DEPLOY_PREFIX` env var and what it does, the `/healthz` rename (and why bare `/` is now reserved for the SPA), the `frontend/dist` static mount and its SPA-fallback limitation, and the production deployment commands — consistent with CLAUDE.md's own stated purpose of tracking implementation details for future sessions.

## Verification

1. Local dev regression check: run `uv run python -m backend.main` (no `DEPLOY_PREFIX`) and `cd frontend && npm run dev` as today; confirm the app still works exactly as before at `http://localhost:5173` (no `/content` prefix anywhere), and `curl http://localhost:8001/healthz` returns the health JSON.
2. Build check: `cd frontend && npm run build`, confirm `frontend/dist/index.html` references assets under `/content/assets/...` (inspect the built HTML directly).
3. Prod-mode smoke test on machine B: `DEPLOY_PREFIX=/content uv run python -m backend.main`, then `curl http://localhost:8001/content/healthz`, `curl http://localhost:8001/content/` (should return the built `index.html`), and `curl -X POST http://localhost:8001/content/api/conversations` (should create a conversation) — all without nginx involved yet, to isolate backend correctness.
4. End-to-end through nginx: once machine B's tunnel is repointed at :8001 and nginx has the `/content/` location block, load `https://<machine-A-domain>/content/` in a browser (not `/content` without trailing slash first, to also separately test the redirect case), open the Network tab, and confirm: the page renders, all JS/CSS assets load from `/content/assets/...` with 200s (not 301s to a wrong app), the API calls go to `/content/api/...`, and sending a message successfully streams through all 3 stages via the SSE endpoint without stalling or erroring.
5. Confirm no mixed-content/redirect-to-http warnings in the browser console on first load of the bare `/content` URL (tests the `X-Forwarded-Proto` fix).

**Status:** steps 1–3 verified locally (including a curl-simulated `X-Forwarded-Proto: https` header in place of step 5's check). Steps 4–5 — the actual nginx config on machine A and the tunnel repoint on machine B — are infra changes outside this repo. **To be tested** once both are in place.
