# TASKS_VERCEL.md

> **AMENDED by `docs/adr/0001-vercel-migration.md` (the authority).** This is
> **not** a move *off* Streamlit. The decision is **tandem**: add a Vercel/Next.js
> frontend that runs **alongside** the kept Streamlit app, both over one shared
> `src/` backend. Read this file as "build the Vercel frontend," not "replace
> Streamlit." Where a phase below describes a cutover or decommission (esp.
> Phase 9.3), the ADR overrides it. The Phase 1–8 build work is otherwise
> unchanged. Repo layout is **single root** (Decision 5), not a `web/`-only
> split, so both frontends import `src/` directly.

Roadmap for building a **Vercel/Next.js frontend** for the **Global Market
Liquidity & Central Bank Tracker**, running in tandem with the existing Streamlit
app on a shared Python backend.

Each task lists a goal, the files involved, an acceptance check, and a rough
estimate. Estimates assume an experienced full-stack dev working with Claude
Code.

**Total estimate: 30 to 45 hours across 10 phases.**

---

## Why this is a re-platform, not a lift-and-shift

Read this before touching anything.

Streamlit is a **stateful, long-running Python server**. It holds a websocket
to every browser, reruns `app.py` top to bottom on each interaction, and keeps
`st.session_state` in process memory. Vercel hosts **static assets + stateless
serverless/edge functions**; there is no persistent process to host a Streamlit
server. You cannot `streamlit run app.py` on Vercel.

Therefore the move requires splitting the current single app into two halves:

| Current (Streamlit)                         | Target (Vercel)                                        |
|---------------------------------------------|--------------------------------------------------------|
| `app.py` orchestration + `st.*` UI          | **Next.js (React) frontend** — static/SSR on Vercel    |
| `st.session_state`, sidebar, crisis buttons | React state + URL query params                          |
| Server-rendered Plotly via `st.plotly_chart`| **`react-plotly.js`** rendering client-side             |
| `st.cache_data` in-process cache            | **Persistent store** (Vercel KV / Upstash, or Supabase)|
| `src/ingestion/*`, `src/processing/*`       | **Python serverless functions** under `/api` (reused)  |
| `data/cache/*.csv` + `manifest.json`        | External store — serverless filesystem is ephemeral    |
| `.streamlit/config.toml` + CSS in `theme.py`| CSS/Tailwind in the Next.js app                         |

**Good news:** the entire `src/processing/*` layer (normalize, regimes,
correlation, summary) and the two ingestion clients (`fred_client.py`,
`equity_client.py`) are pure pandas/numpy with no Streamlit imports. They port
into serverless functions almost verbatim. The work is the UI rewrite, the
cache rewrite, and the wiring.

### Recommended architecture

```
Browser ──> Next.js frontend (Vercel static/SSR)
              │  fetch()
              ▼
            /api/series?region=...   (Vercel Python serverless function)
              │  reuses src/ingestion + src/processing
              ▼
            Persistent cache (Vercel KV / Upstash Redis)  ──fallback──> FRED + yfinance
```

The frontend asks one JSON endpoint for everything it needs to draw a region
(central-bank series, equity series, regime segments, correlation, KPI
summary). The Python function does all the math (so we keep the existing,
tested processing code) and the React layer only renders.

### Alternative (lighter, lower fidelity) — documented, not recommended

A single Python serverless function could render the existing Plotly figures to
static HTML/JSON and serve them, skipping the React rewrite. This keeps far more
of the current code but loses Streamlit's interactivity model (sidebar reruns,
session state, the styled component grid) and still needs the cache rewrite. Use
this only if the React rewrite is out of scope. The phases below assume the
recommended architecture and call out where the alternative diverges.

---

## Phase 0: Decisions & spike (2 to 3 hours) — DONE (see `docs/adr/0001-vercel-migration.md`)

Status: architecture decisions locked in ADR 0001; spike artifact `api/ping.py`
written; bundle size measured locally (211 MB raw / 125 MB trimmed, under the
250 MB limit). The one open item is the live yfinance-from-Vercel check, which
requires a preview deploy and is carried into Phase 1 (this container's egress
policy blocks the data-source hosts, so it cannot be validated locally).

**0.1 Lock the architecture decisions**
- Confirm frontend framework: **Next.js (App Router)** is the Vercel-native
  default. Confirm charting: **`react-plotly.js`** (keeps visual parity with the
  current Plotly figures) vs a lighter lib (Recharts/visx — would require
  rebuilding dual-axis + regime shading from scratch).
- Confirm cache backend: **Vercel KV (Upstash Redis)** is the simplest managed
  option; **Supabase Postgres** is an alternative if you want queryable history.
- Accept: a short ADR (architecture decision record) committed under `docs/`.

**0.2 Serverless feasibility spike**
- Deploy a throwaway `/api/ping.py` that imports `pandas`, `numpy`, `requests`,
  and `yfinance`, and returns the unzipped dependency size.
- Verify the bundle fits Vercel's serverless size limit (250 MB unzipped) and
  that `yfinance` actually returns data from a Vercel function (it can be
  blocked or rate-limited from cloud IP ranges).
- Accept: a deployed preview where `/api/ping` returns 200 with a live `^GSPC`
  close and the bundle is under the size limit. **If yfinance fails from
  Vercel, escalate** — switch the equity source (e.g. a Stooq/FRED equity
  series, or a keyed provider) before continuing.

---

## Phase 1: Repo restructure & Vercel project (3 to 4 hours)

**1.1 Target layout**
- Reshape the repo into a Vercel-friendly structure without losing the reusable
  Python:
  ```
  global-liquidity-tracker/
    api/                  # Vercel Python serverless functions
      series.py           # main data endpoint
      _lib/               # symlink/copy of reusable src logic
    web/  (or app root)   # Next.js app: app/, components/, lib/, styles/
    src/                  # existing Python — ingestion + processing reused by api/
    vercel.json
    package.json
    requirements.txt      # Python deps for serverless (trimmed)
  ```
- Decide whether the Next.js app lives at repo root or in `web/`; set Vercel
  "Root Directory" accordingly.
- Accept: `vercel dev` runs locally and serves the Next.js placeholder + a
  Python `/api` route.

**1.2 `vercel.json`**
- Configure Python functions, route rewrites (`/api/*` → functions), and
  function `maxDuration` (raise above the 10s Hobby default if a cold FRED +
  yfinance fetch is slow; requires Pro for >10s).
- Accept: `vercel.json` validates and preview deploy builds both runtimes.

**1.3 Node/Next.js scaffold**
- `package.json`, `next.config.js`, App Router skeleton, TypeScript.
- Accept: `npm run build` succeeds; placeholder page deploys to a preview URL.

---

## Phase 2: Python serverless API (4 to 6 hours)

**2.1 Reuse the ingestion + processing layers**
- Make `src/ingestion/fred_client.py`, `equity_client.py`, and all of
  `src/processing/*` importable from `api/`. Keep them framework-free (they
  already are).
- **TANDEM (amends original):** do **not** drop the `st.secrets` path —
  Streamlit still uses it. `fred_client._get_api_key()` already tries
  `st.secrets` then falls back to `os.environ`; that frontend-agnostic order is
  exactly right and stays. On Vercel, `streamlit` isn't installed so the
  `st.secrets` branch is skipped and `os.environ` is used.
- Accept: a local script imports the clients and processing from inside `api/`
  with no Streamlit installed (the import must not require `streamlit`).

**2.2 The `/api/series` endpoint**
- Implement a Vercel Python function that accepts `region`, `start`, `end`,
  `view` (`raw`/`rebased`), `baseline_year` and returns a single JSON payload:
  central-bank series, equity series, regime segments, correlation result
  (latest 30/90/360 + rolling line), and the `KpiSummary` fields.
- Move the millions→trillions conversion and the date-range clamp (incl. the
  `Full History` sentinel) into the function — currently done in `app.py`.
- Serialize pandas Series as date/value arrays (ISO dates, JSON numbers; emit
  `null` for NaN).
- Accept: `GET /api/series?region=United%20States` returns valid JSON for all
  three regions with non-empty series and a correlation block.

**2.3 Slim serverless requirements (two-file split, not a trim)**
- **TANDEM (amends original):** do **not** strip the root `requirements.txt` —
  Streamlit Cloud installs from it and still needs `streamlit`/`plotly`/
  `python-dotenv`. Instead the **slim** serverless set lives in
  `api/requirements.txt` (`pandas`, `numpy`, `requests`, `yfinance`), already
  added in Phase 0. The `@vercel/python` builder installs the requirements.txt
  adjacent to the function entrypoint, so the Vercel bundle excludes
  streamlit/plotly while the root stays fat.
- **Verify the resolution on a preview** (open Phase 0.2 item): confirm the
  function bundles `api/requirements.txt`, not the fat root one. If the builder
  only reads root `requirements.txt`, fall back to a `pyproject.toml` dependency
  list for Vercel (Streamlit Cloud ignores it) or a build-time prune.
- Accept: serverless bundle builds with the slim deps and stays under the size
  limit; the Streamlit app still installs and runs from the root requirements.

---

## Phase 3: Persistent caching (3 to 5 hours)

This replaces both `src/ingestion/cache.py` (filesystem CSV + `manifest.json`)
and `@st.cache_data`. **The serverless filesystem is ephemeral and read-only
except `/tmp`**, which does not survive between invocations — the current cache
design cannot work as-is.

**3.1 Choose and provision the store**
- Provision **Vercel KV (Upstash Redis)** (recommended) or **Supabase**. Add
  connection env vars to the Vercel project.
- Accept: the function can read/write a test key in the store from a preview
  deploy.

**3.2 Rewrite the cache layer**
- Port the 24-hour freshness + stale-fallback logic from `cache.py` to the new
  store: key per series, store `{fetched_at, payload}`, serve fresh-within-24h
  from the store, refetch + overwrite when stale, **fall back to the stale value
  with a `stale: true` flag when the live fetch raises** (preserve current
  behavior and the UI warning). No bare `except` (project convention).
- Accept: first request hits FRED/yfinance and writes the store; second request
  within 24h serves from the store with no network call; a simulated fetch
  failure returns the stale payload with `stale: true`.

**3.3 Optional warmup cron**
- Add a Vercel Cron that refreshes all six series daily so user requests always
  hit warm cache and never pay the cold-fetch latency (helps stay under the
  function timeout).
- Accept: the cron route runs on schedule and refreshes all `fetched_at`
  timestamps.

---

## Phase 4: Frontend data + state (3 to 4 hours)

**4.1 API client + types**
- `web/lib/api.ts`: typed fetch wrapper for `/api/series`. TypeScript types
  mirroring the JSON payload.
- Accept: a typed `getSeries(region, …)` returns parsed data in a component.

**4.2 App state (replaces `st.session_state`)**
- Region, view mode (raw/rebased), baseline year, date range, and theme held in
  React state and reflected in URL query params (so views are shareable —
  something Streamlit could not do cleanly).
- Port the crisis-window logic from `config/settings.py` / `render_crisis_buttons`
  so a crisis button sets the date range.
- Accept: changing region/view/dates refetches and the URL updates; reload
  restores the same view.

**4.3 Loading, error, and stale states**
- Spinner during fetch, error panel on empty range / failed fetch, and the
  "served from stale cache" warning (mirrors the current `st.warning`).
- Accept: each state renders correctly, including the empty-range `st.stop()`
  equivalent.

---

## Phase 5: Frontend charts (4 to 6 hours)

Port the three Plotly figures from `src/ui/charts.py` to `react-plotly.js`.

**5.1 Dual-axis chart**
- Brass central-bank line on the primary y-axis, verdigris equity line on the
  secondary axis, trillions formatting + currency-aware axis titles, shared
  hover. Rebuild the Plotly template (`get_plotly_template`) as a JS layout
  object — keep **one** shared template, never set colors ad-hoc (project rule).
- Accept: visual parity with the current dual-axis chart for all three regions.

**5.2 Regime shading**
- Render each expansion/contraction segment as a Plotly `vrect` behind the
  lines (sage / clay, low opacity from the palette). Segments come from the API.
- Accept: shaded bands match the slope sign and sit behind the data lines.

**5.3 Rebased view + correlation chart**
- Rebased single-axis-at-100 view toggled from app state; the rolling
  correlation line chart below the main chart.
- Accept: toggling raw↔rebased redraws cleanly; correlation chart matches the
  current panel.

---

## Phase 6: Frontend theme & components (4 to 6 hours)

Reproduce the "Brass and Verdigris on Paper" design from `src/ui/theme.py` and
`src/ui/components.py`. Do **not** regress toward framework defaults.

**6.1 Theme + typography**
- Port the palette (`PALETTE` / `PALETTE_DARK`), the radial gradient wash,
  rounded panels, hairline borders, and fonts (Fraunces headings, IBM Plex Sans
  body, IBM Plex Mono metrics) into CSS/Tailwind. Port the animations
  (`fadeUp`, `fadeIn`, `drawRule`, `pulse`, `breathe`, `sheen`).
- Accept: headings render serif, metrics mono, paper background and gradient
  present.

**6.2 Components**
- Rebuild hero header, sidebar/region selector, KPI card row (with sparklines),
  insight line, correlation metric grid (positive/negative colored), regime key,
  crisis bookmark buttons (brass on hover/active), "What is this?" expander, and
  footer — porting `components.py`.
- Accept: every section from the current app is present and styled consistently.

**6.3 Dark "terminal" variant**
- Wire the `PALETTE_DARK` swap as a theme toggle (the current app keys the chart
  remount off theme — handle the equivalent in React).
- Accept: dark variant renders cleanly with the same brass/verdigris accents.

---

## Phase 7: Secrets & environment (1 hour)

**7.1 Vercel env vars**
- Set `FRED_API_KEY` (and KV/Supabase connection vars) in the Vercel project for
  Production, Preview, and Development. Update `.env.example` and add
  `vercel env pull` notes for local `vercel dev`.
- Accept: `/api/series` works on a preview deploy with no key in the repo;
  `.env` / secrets remain gitignored.

---

## Phase 8: Testing & CI (3 to 4 hours)

**8.1 Keep the Python processing tests**
- The existing `tests/` (cache, normalize, regimes, correlation, summary) still
  cover the math.
- **TANDEM (amends original):** **keep** the existing `test_cache.py` for the
  filesystem store — Streamlit still uses it. **Add** a separate test for the new
  KV-backed store (mock the store; no live network) rather than replacing the
  filesystem one. Both implementations honor the same freshness/stale contract.
- Accept: `pytest` passes for both cache implementations and the ported modules.

**8.2 API contract test**
- Add a test that calls the `/api/series` handler with mocked ingestion and
  asserts the JSON shape (keys, types, NaN→null).
- Accept: the contract test passes and guards the frontend ↔ API boundary.

**8.3 Frontend checks**
- ESLint + `tsc --noEmit` + a smoke test that renders the chart with fixture
  data. Add `ruff` for Python.
- Accept: `npm run lint && npm run build` and `ruff check .` pass.

**8.4 CI**
- GitHub Actions running pytest, ruff, and the Next.js build on PRs (Vercel
  builds previews automatically; CI guards the Python side).
- Accept: CI is green on the migration PR.

---

## Phase 9: Deploy & cutover (2 to 3 hours)

**9.1 Connect the repo to Vercel**
- Import the GitHub repo into Vercel, set Root Directory, env vars, and the
  Python runtime. Confirm preview deploys on every PR.
- Accept: the migration branch produces a working preview URL; all three regions
  render with charts, regime shading, correlation, KPIs, crisis buttons, and
  both themes.

**9.2 Production deploy + domain**
- Promote to production; attach a custom domain if desired.
- Accept: production URL loads fast on repeat visits (cache warm), no key
  leakage, all features working.

**9.3 Decommission Streamlit + update docs**
- **AMENDED by ADR 0001 (Decision 6): tandem is the end state — do NOT
  decommission Streamlit.** Keep `app.py`, `.streamlit/`, and `src/ui/*`; both
  frontends run permanently over the shared backend. The steps below that take
  Streamlit down / archive its UI no longer apply; the doc updates become
  *extend* `CLAUDE.md` to add the Vercel face, not *replace* the Streamlit one.
- Take down the Streamlit Community Cloud app (or leave a redirect). **Update
  `CLAUDE.md`** — the Hosting, Tech stack, Caching, and Design sections all
  describe Streamlit and must be rewritten for the Vercel/Next.js architecture.
  Update `README.md` setup/run/deploy steps. Remove or archive `app.py`,
  `.streamlit/`, and `src/ui/*` once the React UI fully replaces them.
- Accept: a new contributor can clone, `vercel dev`, and run the app from the
  README alone; `CLAUDE.md` no longer claims Streamlit.

---

## Phase 10: Post-migration hardening (optional, 2 to 3 hours)

- **Edge caching:** set `Cache-Control` / `s-maxage` on `/api/series` so
  Vercel's edge serves repeat requests without invoking the function.
- **Observability:** Vercel Analytics + function logs; alert on FRED/yfinance
  failures.
- **Rate-limit safety:** confirm the warmup cron + edge cache keep FRED/yfinance
  calls well under their limits.
- Accept: repeat page loads are served from edge cache; a synthetic upstream
  failure surfaces the stale warning instead of an error.

---

## Risks & open questions

1. **yfinance on serverless (highest risk).** Cloud IP ranges are sometimes
   blocked or throttled by Yahoo, and cold-start + download can blow the 10s
   Hobby timeout. Mitigations: warmup cron + edge cache, raise `maxDuration`
   (Pro), or swap the equity source. Resolve in the Phase 0 spike.
2. **Serverless bundle size.** pandas + numpy + yfinance is large; verify it
   fits the 250 MB unzipped limit (Phase 0.2).
3. **Function timeout.** Cold dual-source fetch may exceed Hobby's 10s. The
   warmup cron and persistent cache are the primary mitigations.
4. **Cache backend cost/limits.** Vercel KV / Upstash and Supabase have free
   tiers; six small series fit comfortably, but confirm before relying on it.
5. **Scope of the UI rewrite.** Phases 5–6 are the bulk of the effort. If the
   timeline is tight, ship the "lighter alternative" (server-rendered Plotly)
   first, then iterate to the React UI.

## Suggested build order

Do Phase 0 first and do not skip the spike — it de-risks the two things most
likely to kill the migration (yfinance on Vercel, bundle size). Then build a
thin vertical slice: `/api/series` for one region (Phase 1–3) wired to a minimal
React chart (Phase 4–5), deployed to a preview. Confirm the data path end to end
on Vercel before investing in the full theme port (Phase 6) and cutover
(Phase 9).
