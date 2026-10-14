"""Fetch Luleå (2580) workplaces from an authenticated SCB API request.

Requires SCB_API_URL, SCB_API_KEY, SCB_API_QUERY_JSON. The URL, HTTP method,
authentication header and search body must follow the account's SCB OpenAPI
specification; none of these are guessed here.
"""
import datetime as dt
import json
import os
import pathlib
import urllib.error
import urllib.request

def pick(row, *keys):
    normalized={str(k).casefold():v for k,v in row.items()}
    for key in keys:
        v=normalized.get(key.casefold())
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""

def main():
    url=os.environ.get("SCB_API_URL","").strip()
    key=os.environ.get("SCB_API_KEY","").strip()
    query=os.environ.get("SCB_API_QUERY_JSON","").strip()
    if not url.startswith("https://") or not key or not query:
        raise SystemExit("SCB connection not configured. Set SCB_API_URL, SCB_API_KEY and SCB_API_QUERY_JSON secrets.")
    method=os.environ.get("SCB_API_METHOD","POST").upper()
    if method not in {"GET","POST"}:
        raise SystemExit("Only GET and POST supported")
    header_name=os.environ.get("SCB_API_KEY_HEADER","x-api-key")
    if not header_name or any(ch in header_name for ch in "\r\n:"):
        raise SystemExit("Invalid API authentication header")
    payload=json.loads(query)
    headers={"Accept":"application/json",header_name:key}
    body=None
    if method=="POST":
        headers["Content-Type"]="application/json"
        body=json.dumps(payload,ensure_ascii=False).encode("utf-8")
    elif payload:
        raise SystemExit("For GET, provide SCB filter in SCB_API_URL and set SCB_API_QUERY_JSON={}")
    req=urllib.request.Request(url,data=body,headers=headers,method=method)
    try:
        with urllib.request.urlopen(req,timeout=90) as response:
            result=json.load(response)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"SCB API returned HTTP {exc.code} (check endpoint, credentials and request shape)") from None
    if isinstance(result,list):
        rows=result
    elif isinstance(result,dict):
        rows=next((result[k] for k in ("items","data","results","arbetsstallen","workplaces") if isinstance(result.get(k),list)),None)
    else:
        rows=None
    if rows is None:
        raise SystemExit("Unknown SCB response schema; inspect OpenAPI mapping before publishing")
    if len(rows)>=5000:
        raise SystemExit("Page contains 5000 records; pagination must be configured before publishing a complete municipality extract")
    output=[]
    for index,row in enumerate(rows):
        if not isinstance(row,dict):
            raise SystemExit(f"Row {index} is not an object")
        municipality=pick(row,"KommunKod","Kommunkod","ArbetsstalleKommunKod","ArbetsställeKommunKod","municipalityCode","kommun")
        if not municipality:
            raise SystemExit("No verified municipality field in SCB response; refusing to publish")
        if municipality not in ("2580","Luleå","LULEÅ"):
            raise SystemExit(f"Other municipality received ({municipality}); refusing unverified extract")
        name=pick(row,"ArbetsstalleNamn","ArbetsställeNamn","Arbetsstallenamn","Benamning","Namn","name")
        addr=pick(row,"Besoksadress","Besöksadress","Gatuadress","ArbetsstalleAdress","ArbetsställeAdress","address")
        if not name and not addr:
            raise SystemExit("Cannot map names or addresses from SCB response")
        output.append({"name":name,"address":addr,
            "sni":pick(row,"SniKod","SNI","SNI2007","SNI2025","sni"),
            "size_class":pick(row,"Storleksklass","AntalAnstalldaKlass","StorleksklassAnstallda","sizeClass")})
    if not output:
        raise SystemExit("No workplaces returned for Luleå; preserving previous published data")
    if os.environ.get("SCB_PUBLICATION_APPROVED", "").lower() != "true":
        raise SystemExit("Publication blocked pending review of SCB terms and personal-data risks. Set SCB_PUBLICATION_APPROVED=true after approval.")
    path=pathlib.Path("docs/data/arbetsstallen_lulea.json")
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps({"municipality":"2580","source":"SCB företagsregister",
        "fetched_at":dt.datetime.now(dt.timezone.utc).date().isoformat(),
        "records":output},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Luleå workplaces validated:",len(output))
if __name__=="__main__":
    main()
