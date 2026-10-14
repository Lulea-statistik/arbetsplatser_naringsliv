"""Compare batched legal-unit retrieval with workplace matching, without publishing identifiers.

A schema/coverage pilot only, NOT an approved individual publication pipeline.
"""
import collections,json,os,time,urllib.parse,urllib.request,urllib.error
BASE="https://apiafr.scb.se/v1"
LIMIT=2000
BUDGET=30
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

def pages(endpoint,key):
    cursor=None
    cursors=set()
    page_count=0
    while True:
        params={"limit":LIMIT}
        if cursor is not None:params["cursorId"]=cursor
        body=request(endpoint+"?"+urllib.parse.urlencode(params),key)
        pagination=body.get("pagination")
        if not isinstance(pagination,dict):raise RuntimeError("Missing pagination")
        rows=body.get("arbetsstallen") if endpoint.startswith("/arbetsstallen") else body.get("jes")
        if not isinstance(rows,list) or not 1<=len(rows)<=LIMIT:
            raise RuntimeError("Invalid page data")
        page_count+=1
        yield rows,page_count
        if pagination.get("hasMore") is not True:break
        nxt=pagination.get("nextCursorId")
        if type(nxt)!=int or nxt in cursors or nxt==cursor:
            raise RuntimeError("Invalid or repeated cursor")
        cursors.add(nxt);cursor=nxt

def main():
    key=os.environ.get("SCB_API_KEY")
    if not key:raise RuntimeError("Missing SCB_API_KEY")
    workplaces={}
    count_wp=0
    for rows,page_no in pages("/arbetsstallen/kommun/2580",key):
        for row in rows:
            cfar=row.get("cfarNr")
            if type(cfar)!=int or cfar in workplaces:raise RuntimeError("Duplicate or absent CFAR")
            org=row.get("peOrgNr")
            if not isinstance(org,str) or not org:raise RuntimeError("Missing unit link")
            workplaces[cfar]=(org,bool(row.get("ben")))
        count_wp+=len(rows)
        print("Workplace page",page_no,"total",count_wp,flush=True)
    units={}
    for rows,page_no in pages("/juridiskaenheter/kommun/2580",key):
        for unit in rows:
            org=unit.get("peOrgNr")
            if not isinstance(org,str) or not org:raise RuntimeError("Missing legal unit key")
            if org in units:raise RuntimeError("Duplicate legal unit key")
            units[org]=(str(unit.get("jurform") or ""),bool(unit.get("namn")))
        print("Legal-unit page",page_no,"total",len(units),flush=True)
    total=len(workplaces)
    links={org for org,_ in workplaces.values()}
    matched=links & units.keys()
    unmatched=links-units.keys()
    matched_workplaces=sum(org in units for org,_ in workplaces.values())
    categories=collections.Counter()
    missing_names=collections.Counter()
    for org,has_wp_name in workplaces.values():
        if org in units:
            form,has_unit_name=units[org]
            label="fysisk_person" if form=="10" else "annan_juridisk_form" if form else "okand_form"
            categories[label]+=1
            if not has_wp_name:
                missing_names["saknar_arbetsstallenamn"]+=1
                if has_unit_name:missing_names["enhetsnamn_finns"]+=1
        else:
            categories["ej_matchad"]+=1
    print("Full workplace total:",total,"distinct legal unit links:",len(links))
    print("Legal entities with registered office Lulea:",len(units))
    print("Matched workplace units:",len(matched),"unmatched units:",len(unmatched))
    print("Matched workplace rows:",matched_workplaces,"unmatched rows:",total-matched_workplaces)
    print("Workplace classification counts:",dict(sorted(categories.items())))
    print("Missing-name diagnostics:",dict(sorted(missing_names.items())))
    print("Requests used:",calls,"/",BUDGET)
    print("No identifiers or individual register values saved")
if __name__=="__main__":main()
