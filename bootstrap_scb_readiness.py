"""Read-only bootstrap readiness check, no individual record persistence.

Prepares an eventual private CFAR-level event store but deliberately performs
no per-workplace export until a reviewed private destination is configured.
"""
import collections
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BASE="https://apiafr.scb.se/v1/arbetsstallen/kommun/2580"
COUNT=BASE+"/count"
MAX_CALLS=20
LIMIT=2000
calls=0
last_call=0.0

def fetch(path,key):
    global calls,last_call
    headers={"Accept":"application/json","X-API-Key":key,"User-Agent":"Lulea-statistik-bootstrap-readiness/1.0"}
    for attempt in range(3):
        if calls>=MAX_CALLS:raise RuntimeError("API call budget exceeded")
        delay=0.55-(time.monotonic()-last_call)
        if delay>0:time.sleep(delay)
        last_call=time.monotonic()
        calls+=1
        try:
            with urllib.request.urlopen(urllib.request.Request(path,headers=headers),timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code not in (429,500,502,503,504) or attempt==2:
                raise RuntimeError(f"SCB HTTP {exc.code}") from None
        except (OSError,ValueError):
            if attempt==2:raise RuntimeError("SCB connection or response error") from None
        time.sleep((attempt+1)*3)
    raise RuntimeError("Retry exhausted")

def count_value(obj):
    if type(obj)==int:return obj
    if isinstance(obj,dict):
        candidates=[v for k,v in obj.items() if k.lower() in ("count","total","totalcount","antal") and type(v)==int]
        if len(candidates)==1:return candidates[0]
    raise RuntimeError("Unexpected count schema")

def main():
    key=os.environ.get("SCB_API_KEY","").strip()
    if not key:raise RuntimeError("Missing SCB_API_KEY")
    expected=count_value(fetch(COUNT,key))
    seen=set()
    cursor=None
    cursors=set()
    counts=collections.Counter()
    total=0
    pages=0
    while True:
        params={"limit":LIMIT}
        if cursor is not None:params["cursorId"]=cursor
        obj=fetch(BASE+"?"+urllib.parse.urlencode(params),key)
        if not isinstance(obj,dict) or not isinstance(obj.get("pagination"),dict) or not isinstance(obj.get("arbetsstallen"),list):
            raise RuntimeError("Invalid page schema")
        rows=obj["arbetsstallen"]
        page=obj["pagination"]
        if not 1<=len(rows)<=LIMIT:raise RuntimeError("Empty/oversized page")
        for row in rows:
            if not isinstance(row,dict):raise RuntimeError("Invalid row type")
            cfar=row.get("cfarNr")
            if type(cfar)!=int or cfar in seen:raise RuntimeError("Missing or duplicate CFAR")
            seen.add(cfar)
            # Classify *presence* only; never log identifiers or row values.
            pe=row.get("peOrgNr")
            counts["peOrgNr_present" if pe is not None else "peOrgNr_missing"]+=1
            counts["legal_form_not_verified"]+=1
            counts["name_present" if row.get("ben") else "name_missing"]+=1
            counts["status_present" if row.get("aeStat") is not None else "status_missing"]+=1
            counts["industry_present" if row.get("primarNaringsgren") is not None else "industry_missing"]+=1
        total+=len(rows);pages+=1
        if total>expected:raise RuntimeError("Over-count against SCB count")
        print(f"Bootstrap diagnostic page {pages}: {total}/{expected}; no individual records saved",flush=True)
        if not page.get("hasMore"):break
        next_cursor=page.get("nextCursorId")
        if type(next_cursor)!=int or next_cursor in cursors:
            raise RuntimeError("Invalid/repeated cursor")
        cursor=next_cursor;cursors.add(cursor)
        del obj,rows
    if total!=expected:raise RuntimeError("Incomplete bootstrap diagnostic")
    # Only summary counts are allowed out. No file publication or artifacts.
    print(f"SUCCESS: {total} unique workplaces checked in {pages} pages / {calls} requests",flush=True)
    print("Field completeness (aggregate):",dict(sorted(counts.items())),flush=True)
    print("Private bootstrap NOT started: legal form and private EU/EEA storage still require approval",flush=True)

if __name__=="__main__":main()
