"""Inspect SCB's public OpenAPI metadata and test a safe authenticated GET.

Never print API keys, API response content, record values, or tokenized URLs.
No individual business/workplace data is persisted or published.
"""
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

HOST = "apiafr.scb.se"
ROOT = "https://" + HOST
CANDIDATES = [
    "/openapi/v1.json", "/swagger/v1/swagger.json", "/openapi.json",
    "/swagger.json", "/scalar/openapi.json", "/openapi/v1/openapi.json",
    "/swagger/v1/swagger.json", "/api/openapi.json"
]

def request(path, api_key=None, header="x-api-key"):
    url = urllib.parse.urlsplit(urllib.parse.urljoin(ROOT, path))
    if url.hostname != HOST or url.scheme != "https":
        raise ValueError("Host not permitted")
    headers = {"Accept": "application/json", "User-Agent": "Lulea-statistik-SCB-schema-probe/1.0"}
    if api_key:
        headers[header] = api_key
    try:
        with urllib.request.urlopen(urllib.request.Request(url.geturl(), headers=headers), timeout=20) as response:
            body = response.read(4_000_000)
            return response.status, body
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception as exc:
        print("Transport issue:", type(exc).__name__)
        return None, b""

def main():
    print("SCB schema inspection; no company or workplace records are downloaded.")
    status, scalar = request("/scalar/")
    print("Scalar page HTTP:", status)
    paths = list(CANDIDATES)
    if status == 200:
        page = scalar.decode("utf-8", errors="replace")
        for link in re.findall(r'''(?:url|specUrl|openapi|href|src)\s*[:=]\s*["']([^"']+)["']''', page, flags=re.I):
            if "openapi" in link.lower() or "swagger" in link.lower():
                resolved = urllib.parse.urljoin(ROOT+"/scalar/", link)
                u = urllib.parse.urlsplit(resolved)
                if u.hostname == HOST and u.path not in paths:
                    paths.insert(0, u.path)
    schema = None
    for path in paths[:16]:
        status, data = request(path)
        print("Schema candidate", path, "HTTP", status)
        if status != 200:
            continue
        try:
            obj = json.loads(data)
        except (ValueError, UnicodeDecodeError):
            continue
        if not isinstance(obj, dict) or not isinstance(obj.get("paths"), dict):
            continue
        schema = obj
        print("Valid OpenAPI schema found:", path)
        break
    if schema is None:
        print("No accessible OpenAPI document. Consult Scalar browser UI to supply the exact spec URL.")
        return
    schemes = schema.get("components", {}).get("securitySchemes", {})
    for name, cfg in schemes.items():
        print("Authentication scheme:", name, cfg.get("type"), cfg.get("in"), cfg.get("name"))
    for endpoint, methods in schema["paths"].items():
        method_list = [m.upper() for m in methods if m.lower() in ("get","post")]
        if method_list:
            print("Endpoint:", ",".join(method_list), endpoint)
    # Do not call data endpoints until the request structure, allowed fields and
    # privacy filtering have been reviewed.
    print("Schema discovery complete. No record-level request was made.")

if __name__ == "__main__":
    main()
