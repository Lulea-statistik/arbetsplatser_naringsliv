"""Secure SCB new-API count smoke test for workplace municipality 2580.

Only prints safe status and an aggregate count. No registry records are retained.
"""
import http.client
import json
import os
import random
import time
import urllib.error
import urllib.request

BASE = "https://apiafr.scb.se"
ENDPOINT = BASE + "/v1/arbetsstallen/kommun/2580/count"
RETRY_CODES = {429, 500, 502, 503, 504}

def request(url, key):
    headers = {"Accept": "application/json", "User-Agent": "Lulea-statistik-SCB-test/1.0", "X-API-Key": key}
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=25) as response:
                status = response.status
                data = response.read(500000)
        except urllib.error.HTTPError as exc:
            status, data = exc.code, b""
        except (urllib.error.URLError, http.client.RemoteDisconnected, ConnectionError, TimeoutError, OSError) as exc:
            if attempt == 3:
                raise SystemExit(f"Connection failed after 4 attempts ({type(exc).__name__}); API key not yet evaluated") from None
            wait = min(2 ** (attempt + 1), 12)
            print(f"Temporary network issue ({type(exc).__name__}), retrying in {wait} seconds", flush=True)
            time.sleep(wait)
            continue
        if status in RETRY_CODES and attempt < 3:
            wait = min(2 ** (attempt + 1), 12)
            print(f"Temporary HTTP {status}, retrying in {wait} seconds", flush=True)
            time.sleep(wait)
            continue
        return status, data
    raise SystemExit("Connection attempts exhausted")

def main():
    key = os.environ.get("SCB_API_KEY", "").strip()
    if not key:
        raise SystemExit("Missing SCB_API_KEY secret")
    print("Checking SCB new API: workplace count, municipality Lulea (2580)")
    status, raw = request(ENDPOINT, key)
    print("SCB HTTP:", status)
    if status in (401, 403):
        raise SystemExit(f"Authentication or access denied (HTTP {status}); check SCB key and API access")
    if status == 404:
        raise SystemExit("Endpoint/version not found (HTTP 404); inspect published OpenAPI")
    if status != 200:
        raise SystemExit(f"SCB API returned HTTP {status}; count could not be verified")
    try:
        result = json.loads(raw)
    except ValueError:
        raise SystemExit("Count endpoint returned non-JSON; response content not logged") from None
    if type(result) is int and result >= 0:
        count = result
    elif isinstance(result, dict):
        matches = [v for k, v in result.items()
                   if k.casefold() in {"count", "antal", "total", "totalcount", "antalarbetsstallen"}
                   and type(v) is int and v >= 0]
        if len(matches) != 1:
            raise SystemExit("Count request succeeded but response schema needs adapting; no records logged")
        count = matches[0]
    else:
        raise SystemExit("Count request succeeded but response schema needs adapting; no records logged")
    print(f"SUCCESS: {count} workplaces reported for Lulea, 2580")
    print("No workplace-level or personal records downloaded or published")

if __name__ == "__main__":
    main()
