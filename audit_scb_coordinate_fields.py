"""Inspect coordinate field availability for Lulea workplaces; no row values leave runner.
Coordinates are never inferred from addresses.
"""
import collections,json,os,time,urllib.parse,urllib.request
BASE="https://apiafr.scb.se/v1/arbetsstallen/kommun/2580"
MAX_CALLS=9
PAGE_SIZE=2000
calls=0
last=0.0

def fetch(cursor,key):
    global calls,last
    if calls>=MAX_CALLS:raise RuntimeError("Coordinate audit call limit")
    delay=0.6-(time.monotonic()-last)
    if delay>0:time.sleep(delay)
    last=time.monotonic();calls+=1
    params={"limit":PAGE_SIZE}
    if cursor is not None:params["cursorId"]=cursor
    req=urllib.request.Request(BASE+"?"+urllib.parse.urlencode(params),headers={
      "Accept":"application/json","X-API-Key":key,"User-Agent":"Lulea-coordinate-field-audit/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=45) as stream:return json.load(stream)
    except Exception:
        raise RuntimeError("SCB response failed; details suppressed") from None

def main():
    key=os.environ["SCB_API_KEY"]
    counts=collections.Counter()
    keys=collections.Counter()
    nested=collections.Counter()
    types=collections.Counter()
    total=0;cursor=None;used=set()
    while True:
        data=fetch(cursor,key)
        rows=data.get("arbetsstallen")
        page=data.get("pagination")
        if not isinstance(rows,list) or not isinstance(page,dict):raise RuntimeError("Invalid API structure")
        for row in rows:
            if not isinstance(row,dict):raise RuntimeError("Invalid record")
            total+=1
            for k,v in row.items():
                keys[k]+=1
                if any(part in k.casefold() for part in ("koord","lat","lon","xkoord","ykoord","geometri","position","sweref","wgs")):
                    types[k+"="+type(v).__name__]+=1
                    if v is not None:counts[k+"_present"]+=1
            for field in ("belagenhetsadress","postAdress"):
                address=row.get(field)
                if isinstance(address,dict):
                    for k,v in address.items():
                        nested[field+"."+k]+=1
                        if any(part in k.casefold() for part in ("koord","lat","lon","position","sweref","wgs")):
                            types[field+"."+k+"="+type(v).__name__]+=1
                            if v is not None:counts[field+"."+k+"_present"]+=1
        print("Audited workplace records:",total,flush=True)
        if not page.get("hasMore"):break
        cursor=page.get("nextCursorId")
        if type(cursor)!=int or cursor in used:raise RuntimeError("Repeated/invalid cursor")
        used.add(cursor)
    print("Total:",total,"API calls:",calls,flush=True)
    print("Top-level schema field names:",",".join(sorted(keys)),flush=True)
    print("Address object field names:",",".join(sorted(nested)),flush=True)
    print("Coordinate candidate field types:",dict(sorted(types.items())),flush=True)
    print("Coordinate candidates non-null:",dict(sorted(counts.items())),flush=True)
    print("NO coordinates, addresses or identifiers exported; no geocoding performed",flush=True)
if __name__=="__main__":main()
