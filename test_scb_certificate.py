"""SCB certificate connectivity test; publishes no retrieved content.

Retries transient transport/HTTP failures with bounded exponential backoff.
Emits only exception class and HTTP status, never exception detail/URLs/secrets.
"""
import base64
import binascii
import os
import time
import requests
from requests_pkcs12 import get

URL = "https://privateapi.scb.se/nv0101/v1/sokpavar/api/ae/kategoriermedkodtabeller"
MAX_RETRIES = 3

def fetch_with_retry(cert, password, sequence):
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = get(URL, pkcs12_data=cert, pkcs12_password=password, timeout=(15, 45))
        except requests.exceptions.RequestException as exc:
            kind = type(exc).__name__
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"Call {sequence}: transport error {kind} after {attempt+1} attempts") from None
            wait = min(4 * (2 ** attempt), 30)
            print(f"Call {sequence}: transport error {kind}; retry in {wait}s ({attempt+1}/{MAX_RETRIES})", flush=True)
            time.sleep(wait)
            continue
        if response.status_code in (429, 500, 502, 503, 504):
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"Call {sequence}: HTTP {response.status_code} after {attempt+1} attempts")
            retry_header = response.headers.get("Retry-After", "")
            wait = int(retry_header) if retry_header.isdecimal() else 4 * (2 ** attempt)
            wait = max(2, min(wait, 60))
            print(f"Call {sequence}: HTTP {response.status_code}; retry in {wait}s", flush=True)
            time.sleep(wait)
            continue
        if response.status_code != 200:
            raise RuntimeError(f"Call {sequence}: SCB HTTP {response.status_code}; not retrying")
        try:
            value = response.json()
        except ValueError:
            raise RuntimeError(f"Call {sequence}: SCB returned non-JSON; not retrying") from None
        if not isinstance(value, (dict, list)):
            raise RuntimeError(f"Call {sequence}: unexpected response structure")
        return
    raise RuntimeError("Unexpected retry loop failure")

def main():
    b64 = os.environ.get("SCB_PFX_BASE64", "").strip()
    password = os.environ.get("SCB_PFX_PASSWORD", "")
    if not b64 or not password:
        raise SystemExit("Missing PFX certificate or password secret")
    try:
        certificate = base64.b64decode(b64, validate=True)
    except (ValueError, binascii.Error):
        raise SystemExit("SCB_PFX_BASE64 is not valid Base64") from None
    if not 500 <= len(certificate) <= 200000:
        raise SystemExit("Unexpected PFX certificate size")
    count = int(os.environ.get("SCB_TEST_CALLS", "1"))
    if not 1 <= count <= 1000:
        raise SystemExit("SCB_TEST_CALLS must be between 1 and 1000")
    print(f"SCB PFX check: {count} calls; no response data is stored", flush=True)
    success = 0
    started = time.monotonic()
    for i in range(1, count+1):
        try:
            fetch_with_retry(certificate, password, i)
        except RuntimeError as err:
            raise SystemExit(f"FAIL after {success}/{count} successful calls: {err}") from None
        success += 1
        if i == 1 or i % 25 == 0 or i == count:
            print(f"Authenticated requests: {i}/{count}", flush=True)
        elapsed = time.monotonic() - started
        # Average <2 requests/s, comfortably under SCB's 5 requests/s quota.
        minimum_elapsed = i * 0.6
        if elapsed < minimum_elapsed:
            time.sleep(minimum_elapsed - elapsed)
    print(f"SUCCESS: {success}/{count}; no registry records written", flush=True)

if __name__ == "__main__":
    main()
