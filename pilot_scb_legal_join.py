"""Small SCB workplace-to-legal-entity join pilot; aggregate output only.

Maximum 20 total API attempts, <= 0.6 sec between requests.
No SCB identifiers, personal names, addresses or row-level data written/logged.
First 15 workplaces are NOT a representative sample.
"""
import collections,json,os,time,urllib.parse,urllib.request,urllib.error
BASE="https://apiafr.scb.se/v1"
MAX_CALLS=20
calls=0
last_call=0.0

def api(path,key):
    global calls,last_call
    for attempt in range(2):
        if calls>=MAX_CALLS:raise RuntimeError("Request budget reached")
        pause=0.6-(time.monotonic()-last_call)
        if pause>0:time.sleep(pause)
        last_call=time.monotonic()
        calls+=1
        request=urllib.request.Request(BASE+path,headers={
            "Accept":"application/json","X-API-Key":key,
            "User-Agent":"Lulea-SCB-legal-join-pilot/1.0"})
        try:
            with urllib.request.urlopen(request,timeout=35) as response:return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in (429,500,502,503,504) or attempt==1:
                # No URLs in exception output: request path can contain an identifier
                raise RuntimeError(f"SCB HTTP {error.code}; individual values suppressed") from None
        except (OSError,ValueError):
            if attempt==1:raise RuntimeError("SCB network/response issue") from None
        time.sleep(2)
    raise RuntimeError("Retries exhausted")

def main():
    key=os.environ.get("SCB_API_KEY")
    if not key:raise RuntimeError("SCB_API_KEY missing")
    rows=api("/arbetsstallen/kommun/2580?limit=15",key).get("arbetsstallen")
    if not isinstance(rows,list) or len(rows)!=15:raise RuntimeError("Expected 15 workplaces")
    cache={}
    result=collections.Counter()
    for row in rows:
        if not isinstance(row,dict):raise RuntimeError("Unexpected workplace type")
        org=row.get("peOrgNr")
        if not isinstance(org,str) or not org:raise RuntimeError("Missing peOrgNr")
        if org not in cache:
            unit=api("/juridiskaenheter/"+urllib.parse.quote(org,safe=""),key)
            if not isinstance(unit,dict):raise RuntimeError("Unexpected legal unit type")
            # Keep only form and whether an explicit business name is present
            cache[org]=(str(unit.get("jurform") or ""),bool(unit.get("namn")))
            del unit
        form,has_unit_name=cache[org]
        if form=="10":category="fysisk_person"
        elif form:category="annan_juridisk_form"
        else:category="juridisk_form_saknas"
        result[category]+=1
        if not row.get("ben") and has_unit_name:result["arbetsstallen_utan_eget_namn_med_enhetsnamn"]+=1
        if not row.get("ben"):result["arbetsstallen_utan_eget_namn"]+=1
    print("SCB legal join pilot: 15 workplace rows, unique legal entities",len(cache),flush=True)
    print("Request count:",calls,flush=True)
    print("Aggregate outcome (first 15, not representative):",dict(sorted(result.items())),flush=True)
    print("No individual records or identifiers stored or printed",flush=True)
if __name__=="__main__":main()
