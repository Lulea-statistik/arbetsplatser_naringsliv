"""Safe SCB PFX connectivity probe: no row-level registry data is persisted.

Uses mTLS (PKCS#12) and the documented category/code-table endpoint.
Never prints the certificate, password, API response or personal identifiers.
"""
import base64
import json
import os
import time
from urllib.parse import urlparse
from requests_pkcs12 import get

URL = "https://privateapi.scb.se/nv0101/v1/sokpavar/api/ae/kategoriermedkodtabeller"
def main():
    b64 = os.environ.get("SCB_PFX_BASE64", "").strip()
    password = os.environ.get("SCB_PFX_PASSWORD", "")
    if not b64 or not password:
        raise SystemExit("Missing SCB_PFX_BASE64 or SCB_PFX_PASSWORD GitHub Actions secret")
    try:
        certificate = base64.b64decode(b64, validate=True)
    except (ValueError, base64.binascii.Error):
        raise SystemExit("SCB_PFX_BASE64 is not valid base64") from None
    if len(certificate) < 500 or len(certificate) > 200000:
        raise SystemExit("Unexpected PFX certificate file size")
    count = int(os.environ.get("SCB_TEST_CALLS", "1"))
    if not 1 <= count <= 1000:
        raise SystemExit("SCB_TEST_CALLS must be 1..1000")
    print(f"Testing authenticated SCB API, calls planned={count}; response bodies are not stored")
    good = 0
    for i in range(count):
        try:
            response = get(URL, pkcs12_data=certificate, pkcs12_password=password, timeout=30)
        except Exception as exc:
            # Do not log exception: some TLS libraries can echo sensitive paths.
            raise SystemExit(f"Connection or certificate authentication failed on call {i+1}. Inspect credentials and network.") from None
        if response.status_code != 200:
            raise SystemExit(f"SCB API HTTP {response.status_code} on call {i+1}; stopping to avoid unnecessary requests")
        try:
            value = response.json()
        except ValueError:
            raise SystemExit(f"SCB returned non-JSON on call {i+1}") from None
        if not isinstance(value, (dict, list)):
            raise SystemExit(f"Unexpected SCB response type on call {i+1}") 
        good += 1
        if good == 1 or good == count or good % 100 == 0:
            print(f"SCB authenticated request validated: {good}/{count}")
        if i + 1 < count:
            time.sleep(0.4)  # < 5 calls/s for this workflow
    print(f"SUCCESS: {good} SCB category requests; no workplace/person data published")
if __name__ == "__main__":
    main()
