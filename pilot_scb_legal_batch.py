"""Compare batched legal-unit retrieval with workplace matching, without publishing identifiers.

A schema/coverage pilot only, NOT an approved individual publication pipeline.
"""
import collections,json,os,time,urllib.parse,urllib.request,urllib.error
BASE="https://apiafr.scb.se/v1"
LIMIT=100
BUDGET=8
calls=0
last=0.0

def request(path,key):
    global calls,last
    if calls>=BUDGET:raise RuntimeError("SCB call budget exceeded")
    pause=0.65-(time.monotonic()-last)
    if pause>0:time.sleep(pause)
    last=time.monotonic();calls+=1
    req=urllib.request.Request(BASE+path,headers={"X-API-Key":key,"Accept":"application/json","User-Agent":"Lulea-statistik-legal-batch-pilot/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=40) as f:return json.load(f)
    except urllib.error.HTTPError as e:
        raise RuntimeError("SCB HTTP "+str(e.code)) from None
    except (OSError,ValueError):
        raise RuntimeError("SCB request failure") from None

def main():
    key=os.environ.get("SCB_API_KEY")
    if not key:raise RuntimeError("Missing SCB_API_KEY")
    wp=request("/arbetsstallen/kommun/2580?limit=100",key)
    rows=wp.get("arbetsstallen")
    if not isinstance(rows,list) or len(rows)!=100:raise RuntimeError("Unexpected workplace sample")
    ids={r.get("peOrgNr") for r in rows}
    if None in ids:raise RuntimeError("Missing unit reference")
    # Compare a single page from the municipality-filtered unit endpoint.
    units=request("/juridiskaenheter/kommun/2580?limit=2000",key)
    unit_rows=units.get("juridiskaEnheter",units.get("juridiskaenheter"))
    if not isinstance(unit_rows,list):
        # Only schema keys, no business values.
        print("Unit response top-level keys:",",".join(sorted(units.keys())),flush=True)
        raise RuntimeError("Unexpected legal-unit collection key; inspect schema")
    lookup={}
    for item in unit_rows:
        if not isinstance(item,dict):raise RuntimeError("Unexpected unit record")
        pe=item.get("peOrgNr")
        if isinstance(pe,str):lookup[pe]=(str(item.get("jurform") or ""),bool(item.get("namn")))
    found=[lookup[i] for i in ids if i in lookup]
    codes=collections.Counter("physical_person" if form=="10" else "other_legal_form" if form else "unknown"
                              for form,_ in found)
    print("Workplace sample:",len(rows),"distinct legal unit references:",len(ids),flush=True)
    print("Municipality legal unit page:",len(unit_rows),"has_more:",bool(units.get("pagination",{}).get("hasMore")),flush=True)
    print("Join coverage, unique references:",len(found),"of",len(ids),flush=True)
    print("Matched juridical-form groups:",dict(sorted(codes.items())),flush=True)
    print("Requests:",calls,"of",BUDGET,"; no raw identifiers, names or addresses exported",flush=True)
    print("NOTE: municipality legal-unit coverage is not necessarily complete for workplaces with head offices elsewhere",flush=True)
if __name__=="__main__":main()
