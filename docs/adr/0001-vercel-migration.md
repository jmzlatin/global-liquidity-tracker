# ADR 0001 — Re-platform from Streamlit Community Cloud to Vercel

- **Status:** Accepted (Phase 0)
- **Date:** 2026-06-14
- **Deciders:** project owner + Claude Code
- **Supersedes:** the Streamlit "Hosting" and "Tech stack" sections of `CLAUDE.md`
  (those are rewritten in Phase 9.3, not here)
- **Context doc:** `TASKS_VERCEL.md` (10-phase migration roadmap)

This ADR records the decisions called for in **Phase 0.1** of `TASKS_VERCEL.md`
and the results of the **Phase 0.2** feasibility spike. It is intentionally a
single committed record so later phases have a fixed reference for "why".

---

## Context

The app currently runs as a single stateful Streamlit server on Streamlit
Community Cloud. Streamlit holds a websocket per browser, reruns `app.py` top to
bottom on every interaction, and keeps `st.session_state` in process memory.
Vercel hosts static assets plus stateless serverless/edge functions — there is
no persistent process, so `streamlit run app.py` cannot work there.

The move is therefore a **re-platform**, splitting one stateful app into a
stateless React frontend plus stateless Python data functions, with an external
cache replacing the in-process `@st.cache_data` and the on-disk
`data/cache/*.csv` store (the serverless filesystem is ephemeral and read-only
outside `/tmp`).

The reusable asset: `src/processing/*` (normalize, regimes, correlation,
summary) and the two ingestion clients (`fred_client.py`, `equity_client.py`)
are pure pandas/numpy/requests with no Streamlit imports. They port into
serverless functions almost verbatim. The work is the UI rewrite, the cache
rewrite, and the wiring.

---

## Decision 1 — Frontend framework: **Next.js (App Router) + TypeScript**

Next.js is the Vercel-native default and gives us file-based routing, first-class
Python serverless functions under `/api`, preview deploys per PR, and shareable
URL state (something Streamlit could not do cleanly). App Router over Pages
Router: it is the current default and pairs with React Server Components for the
static shell while charts stay client components.

**Rejected:** plain Vite SPA (loses Vercel's integrated `/api` Python runtime and
preview ergonomics); SvelteKit/Remix (smaller ecosystem fit for our Plotly +
React needs, no upside here).

## Decision 2 — Charting: **`react-plotly.js`**

Keeps visual parity with the existing Plotly figures (`src/ui/charts.py`): the
dual-axis brass/verdigris lines, the `vrect` regime shading, trillions axis
formatting, and the rolling-correlation panel all map directly onto Plotly
layout objects. The shared `build_plotly_template()` becomes one shared JS layout
object — never set colors ad-hoc (existing project rule carries over).

**Rejected:** Recharts / visx. Lighter, but dual-axis + behind-the-lines regime
shading would be rebuilt from scratch, and we would lose the exact look the UI
elevation pass already produced. Not worth the regression risk in a migration.

## Decision 3 — Cache backend: **Vercel KV (Upstash Redis)**

Simplest managed key/value store, native to Vercel, generous free tier. We store
one key per series — `{ fetched_at, payload }` — and port the existing 24-hour
freshness + stale-fallback logic from `src/ingestion/cache.py` onto it (Phase 3).
Six small series fit the free tier comfortably. Redis TTLs also model the
24-hour freshness window naturally.

**Rejected (for now):** Supabase Postgres. Worth it only if we later want
queryable historical snapshots; overkill for a six-key freshness cache today.
Revisit if a "history" feature appears.

## Decision 4 — Serverless data layer: **Python functions under `/api`, reusing `src/`**

Keep the tested pandas/numpy math instead of porting it to TypeScript. The
frontend calls one JSON endpoint (`/api/series`) that returns everything needed
to draw a region (central-bank series, equity series, regime segments,
correlation block, KPI summary). `FRED_API_KEY` is read from `os.environ`; the
`st.secrets` path in `fred_client._get_api_key()` is dropped in Phase 2.

## Decision 5 — Repo layout & build order

Next.js app at the **repo root** (Vercel Root Directory = repo root), `/api` for
Python functions, existing `src/` kept and imported by `/api`. Follow the
roadmap's suggested order: Phase 0 spike → thin vertical slice (one region,
`/api/series` → minimal React chart, deployed to a preview) → full theme port →
cutover. Do not invest in the full theme port (Phase 6) before the data path is
proven end-to-end on Vercel.

---

## Phase 0.2 spike results

Goal: de-risk the two things most likely to kill the migration — **serverless
bundle size** and **yfinance reachability from cloud infrastructure**.

### What was measured locally (this container)

Installed the proposed serverless dependency set (`pandas`, `numpy`, `requests`,
`yfinance`) into an isolated target directory and measured the unzipped size and
data-source reachability. Reproducible via `api/ping.py` + the commands in
`docs/adr/0001-spike-commands.md`.

| Check | Result |
|---|---|
| Unzipped bundle, default `pip install --target` | **211 MB** |
| Unzipped bundle, after stripping `__pycache__` / `tests` / `*.pyc` | **125 MB** |
| Vercel serverless limit (unzipped) | 250 MB |
| Largest contributors | pandas 76 MB, numpy 45 MB + 28 MB (`numpy.libs`), **`curl_cffi` 31 MB** (pulled in by modern yfinance) |
| `requests` import + live call | OK (library imports fine) |
| `pandas` / `numpy` / `yfinance` import | OK once installed |

**Bundle-size verdict: PASS, with a caveat.** The raw 211 MB fits under 250 MB,
but headroom is thin and `curl_cffi` (a yfinance transitive dep) is a surprising
31 MB. Simple build-time trimming of bytecode/tests already brings it to 125 MB.
**Action for Phase 2.3:** trim the deployed bundle (strip caches/tests, prefer
slim wheels) and keep `streamlit`/`plotly`/`python-dotenv` out of the serverless
requirements. Re-measure on a real Vercel build.

### yfinance reachability — INCONCLUSIVE here, must verify on Vercel

The live-fetch half of the spike **could not be validated in this container**:
its network egress allowlist blocks the data-source hosts. All three returned
403 / "Host not in allowlist":

- `query1/query2.finance.yahoo.com` (yfinance) — explicitly "Host not in
  allowlist … add to your network egress settings"
- `api.stlouisfed.org` (FRED)
- `stooq.com` (candidate fallback equity source)

This is **this container's** policy, not Yahoo blocking a cloud IP, so it neither
confirms nor refutes the real risk. The genuine test — does `yfinance` return a
live `^GSPC` close from a **Vercel** function — remains **open** and is the one
acceptance check from Phase 0.2 that requires an actual Vercel preview deploy.

`api/ping.py` is written to be that test: deployed to a Vercel preview it imports
the four deps, fetches a recent `^GSPC` close, and reports the on-disk package
size, returning 200 only if the fetch succeeds.

### Contingency if yfinance fails from Vercel (pre-decided, per Phase 0.2)

If the preview shows yfinance blocked/throttled or blowing the function timeout,
switch the equity source **before** building further. Preferred order:

1. **Stooq** CSV endpoint (no key) for index history — already a candidate; its
   reachability is part of the same preview test.
2. A FRED equity series (e.g. `SP500`) — keeps everything on the FRED key we
   already have, at the cost of index coverage for Euro Stoxx 50 / Nikkei 225.
3. A keyed provider (Alpha Vantage / Tiingo) as a last resort.

Mitigations that apply regardless: the Phase 3 persistent cache + Phase 3.3
warmup cron + Phase 10 edge cache keep upstream calls rare and off the user
request path, which also addresses the 10s Hobby timeout risk.

---

## Consequences

- **Positive:** keep the entire tested processing layer; gain shareable URLs,
  per-PR preview deploys, and edge caching; lose the single-server cost model.
- **Negative / cost:** the UI rewrite (Phases 5–6) is the bulk of the effort;
  `>10s` `maxDuration` needs Vercel Pro; we now depend on an external cache store.
- **Open risk carried into Phase 1:** yfinance-from-Vercel is unproven (see
  above). The first preview deploy of `api/ping.py` must close it before we
  commit to the data path.

---

## Acceptance (Phase 0)

- [x] **0.1** Architecture decisions locked in a committed ADR (this document).
- [x] **0.2** Spike artifact (`api/ping.py`) written; bundle size measured
      (211 MB raw / 125 MB trimmed, under 250 MB).
- [ ] **0.2 (requires Vercel)** Deploy `api/ping.py` to a preview; confirm it
      returns 200 with a live `^GSPC` close. Blocked locally by container egress;
      tracked as the first action of Phase 1.
