# Phase 0.2 spike — reproducible commands

Local measurements behind ADR 0001. Run from a clean checkout. These reproduce
the bundle-size and reachability numbers in `0001-vercel-migration.md`. The
*live yfinance-from-Vercel* check is **not** reproducible locally — it requires
deploying `api/ping.py` to a Vercel preview (see bottom).

## Bundle size (the 250 MB serverless limit)

```bash
# Install the proposed serverless deps into an isolated target dir.
python3 -m pip install --target /tmp/spike/pkgs pandas numpy requests yfinance

# Raw unzipped size (recorded: ~211 MB).
du -sh /tmp/spike/pkgs

# Per-package breakdown (pandas, numpy, numpy.libs, curl_cffi dominate).
du -sh /tmp/spike/pkgs/* | sort -rh | head -15

# Trimmed size after stripping bytecode + tests (recorded: ~125 MB).
cp -r /tmp/spike/pkgs /tmp/spike/pkgs_trim
find /tmp/spike/pkgs_trim -type d -name __pycache__ -exec rm -rf {} +
find /tmp/spike/pkgs_trim -type d \( -name tests -o -name test \) -exec rm -rf {} +
find /tmp/spike/pkgs_trim -name '*.pyc' -delete
du -sh /tmp/spike/pkgs_trim
```

## Data-source reachability

```bash
PYTHONPATH=/tmp/spike/pkgs python3 - <<'PY'
import requests
for url in [
    "https://api.stlouisfed.org/fred/series/observations",
    "https://query1.finance.yahoo.com/v8/finance/chart/^GSPC",
    "https://stooq.com/q/d/l/?s=^spx&i=d",
]:
    try:
        print(requests.get(url, timeout=15).status_code, url)
    except Exception as exc:  # spike only
        print("ERR", url, exc)
PY
```

In **this container** all three return 403 ("Host not in allowlist") because of
the environment's network egress policy — this is not Yahoo blocking a cloud IP,
so it neither confirms nor refutes the real risk. The genuine test runs on
Vercel.

## The real check (Vercel preview — Phase 1 first action)

```bash
# Deploy a preview with api/ping.py present, then:
curl -s https://<preview-url>/api/ping | jq
```

Expect `ok: true`, a numeric `yfinance.gspc_close`, and
`bundle_unzipped_mb_estimate` under 250. If yfinance reports an error or empty
frame, escalate and switch the equity source per ADR 0001 "Contingency".
