"""Sample API Service availability and compare saved results; emit JSON Lines."""

import argparse
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen


def positive(value: str) -> float:
    number = float(value)
    if not 0 < number < float("inf"):
        raise argparse.ArgumentTypeError("Expected a finite positive number")
    return number


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--duration", type=positive, default=300)
    parser.add_argument("--interval", type=positive, default=0.5)
    parser.add_argument("--timeout", type=positive, default=2)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text())
    base = args.api_url.rstrip("/")
    run = f"/api/v1/runs/{snapshot['run_id']}"
    targets = [
        ("ready", "/health/ready"),
        ("summary", run),
        ("metrics", run + "/metrics"),
        ("events", run + "/events"),
    ]
    started = time.monotonic()
    counts = {name: {"requests": 0, "failures": 0} for name, _ in targets}
    print(
        json.dumps({"type": "start", "run_id": snapshot["run_id"], **vars(args)}, default=str),
        flush=True,
    )
    try:
        while time.monotonic() - started < args.duration:
            cycle = time.monotonic()
            for name, path in targets:
                before = time.monotonic()
                record = {
                    "type": "request",
                    "endpoint": name,
                    "utc": datetime.now(UTC).isoformat(),
                    "elapsed_s": round(before - started, 6),
                    "status": None,
                    "ok": False,
                    "error": None,
                }
                try:
                    with urlopen(base + path, timeout=args.timeout) as response:
                        record["status"] = response.status
                        body = json.load(response)
                    record["ok"] = record["status"] == 200
                    if name != "ready" and body != snapshot[name]:
                        record["ok"] = False
                        record["error"] = "Result differs from saved snapshot"
                except HTTPError as exc:
                    record["status"] = exc.code
                    record["error"] = str(exc)
                    exc.close()
                except (OSError, ValueError) as exc:
                    record["error"] = f"{type(exc).__name__}: {exc}"
                record["latency_ms"] = round((time.monotonic() - before) * 1000, 3)
                counts[name]["requests"] += 1
                counts[name]["failures"] += int(not record["ok"])
                print(json.dumps(record), flush=True)
            remaining = args.duration - (time.monotonic() - started)
            time.sleep(max(0, min(args.interval - (time.monotonic() - cycle), remaining)))
    finally:
        print(
            json.dumps(
                {"type": "summary", "elapsed_s": time.monotonic() - started, "counts": counts}
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
