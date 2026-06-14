"""Phase 0.2 feasibility spike — throwaway Vercel Python serverless function.

Purpose: prove, on a real Vercel preview deploy, the two things most likely to
kill the migration (see docs/adr/0001-vercel-migration.md):

  1. The serverless deps (pandas, numpy, requests, yfinance) import inside a
     Vercel function and the unzipped bundle fits the 250 MB limit.
  2. yfinance actually returns a live ^GSPC close from a Vercel IP range (Yahoo
     sometimes blocks/throttles cloud infrastructure).

Delete this file once Phase 1 begins — it is a spike, not part of the API.

Deploy: drop this at api/ping.py, deploy a preview, GET /api/ping. A 200 with
ok=true and a numeric gspc_close confirms feasibility. A non-200 (or yfinance
error) is the signal to escalate and switch the equity source per the ADR.
"""

import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler


def _import_check() -> dict:
    """Import each serverless dep and record version or the import error."""
    results: dict[str, str] = {}
    for name in ("pandas", "numpy", "requests", "yfinance"):
        try:
            module = __import__(name)
            results[name] = getattr(module, "__version__", "unknown")
        except ImportError as exc:
            results[name] = f"IMPORT_ERROR: {exc}"
    return results


def _yfinance_check() -> dict:
    """Fetch a recent ^GSPC close to prove yfinance works from a Vercel IP.

    Returns a dict with ok flag and either the last close or the error string.
    No bare except (project convention): yfinance surfaces network failures as
    a variety of exceptions, so we name the broad base and report it verbatim.
    """
    started = time.monotonic()
    try:
        import yfinance as yf

        frame = yf.download(
            "^GSPC", period="5d", progress=False, auto_adjust=True
        )
        elapsed = round(time.monotonic() - started, 2)
        if frame.empty:
            return {"ok": False, "reason": "empty_frame", "elapsed_s": elapsed}
        close = frame["Close"]
        last = float(close.iloc[-1].item() if hasattr(close.iloc[-1], "item") else close.iloc[-1])
        return {"ok": True, "gspc_close": round(last, 2), "rows": int(len(frame)), "elapsed_s": elapsed}
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        return {
            "ok": False,
            "reason": f"{type(exc).__name__}: {exc}",
            "elapsed_s": round(time.monotonic() - started, 2),
        }


def _bundle_size_bytes() -> int:
    """Best-effort unzipped size of installed site-packages, for the size check."""
    total = 0
    seen: set[str] = set()
    for root in sys.path:
        if not root or root in seen or not os.path.isdir(root):
            continue
        seen.add(root)
        for dirpath, _dirnames, filenames in os.walk(root):
            for filename in filenames:
                try:
                    total += os.path.getsize(os.path.join(dirpath, filename))
                except OSError:
                    continue
    return total


def _build_payload() -> dict:
    """Assemble the full spike report."""
    imports = _import_check()
    yf_result = _yfinance_check()
    size_mb = round(_bundle_size_bytes() / (1024 * 1024), 1)
    return {
        "ok": yf_result["ok"] and all("ERROR" not in v for v in imports.values()),
        "python": sys.version.split()[0],
        "imports": imports,
        "yfinance": yf_result,
        "bundle_unzipped_mb_estimate": size_mb,
        "bundle_limit_mb": 250,
        "note": "Phase 0.2 spike. ok=true means deps import and yfinance returned a live ^GSPC close.",
    }


class handler(BaseHTTPRequestHandler):  # noqa: N801 — Vercel requires this exact name
    """Vercel Python runtime entrypoint."""

    def do_GET(self) -> None:  # noqa: N802 — http.server API
        payload = _build_payload()
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(200 if payload["ok"] else 503)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
