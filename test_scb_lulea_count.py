"""Verify SCB new-API authentication and Lulea workplace count safely.

Uses public OpenAPI to determine required version and request parameters.
Outputs only HTTP status, schema parameter names, and aggregate count.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://apiafr.scb.se"
SPEC = BASE + "/swagger/v1/swagger.json"
PATH = "/v{v}/arbetsstallen/kommun/{kommunKod}/count"
def read(url, key=None):
    h = {"Accept":"application/json", "User-Agent":"Lulea-statistik/1.0"}
    if key: h["X-API-Key"] = key
    req=urllib.request.Request(url,headers=h)
    try:
        with urllib.request.urlopen(req,timeout=30) as resp:
            return resp.status, resp.read(200000)
    except urllib.error.HTTPError as exc:
        return exc.code, b""

def main():
    key=os.environ.get("SCB_API_KEY","").strip()
    if not key: raise SystemExit("SCB_API_KEY missing (set in repository Actions secrets)")
    status,raw=read(SPEC)
    if status!=200: raise SystemExit(f"OpenAPI schema HTTP {status}")
    spec=json.loads(raw)
    operation=spec.get("paths",{}).get(PATH,{}).get("get")
    if not operation: raise SystemExit("Verified municipality count endpoint absent from OpenAPI")
    params=spec.get("paths",{}).get(PATH,{}).get("parameters",[])+operation.get("parameters",[])
    print("OpenAPI version:",spec.get("info",{}).get("version","unknown"))
    for p in params:
        print("Parameter",p.get("name"),"location",p.get("in"),"required",p.get("required",False))
    version=os.environ.get("SCB_API_VERSION","1")
    if version!="1": raise SystemExit("Version not yet validated; only v1 supported")
    url=BASE+PATH.replace("{v}",version).replace("{kommunKod}","2580")
    print("Trying authorized GET municipality workplace count, Lulea 2580")
    try:
        status,raw=read(url,key)
    except Exception as exc:
        raise SystemExit(f"SCB transport failure: {type(exc).__name__}") from None
    print("SCB workplace count HTTP:",status)
    if status!=200:
        raise SystemExit("SCB count request failed; inspect API key scope, version, and required query parameters")
    try:
        result=json.loads(raw)
    except ValueError:
        raise SystemExit("SCB count response not JSON") from None
    if isinstance(result,int) and result>=0:
        total=result
    elif isinstance(result,dict):
        count_keys=("count","antal","total","totalCount","antalArbetsstallen")
        matches=[result[k] for k in count_keys if isinstance(result.get(k),int) and result[k]>=0]
        if len(matches)!=1: raise SystemExit("Unknown count response structure; not logging raw response")
        total=matches[0]
    else: raise SystemExit("Unknown count response structure; not logging raw response")
    print("VERIFIED SCB workplaces in Lulea (2580):",total)
    print("No workplace records or personal information have been downloaded")
if __name__=="__main__":
    main()
