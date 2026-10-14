"""Compare batched legal-unit retrieval with workplace matching, without publishing identifiers.

A schema/coverage pilot only, NOT an approved individual publication pipeline.
"""
import collections,json,os,time,urllib.parse,urllib.request,urllib.error,datetime
BASE="https://apiafr.scb.se/v1"
LIMIT=2000
BUDGET=60
MAX_EXTRA_LOOKUPS=0
# Pilot additional legal entities headquartered in Norrbotten county (25).
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
    # The Lulea municipality is a subset of Norrbotten county.
    # Batch-fetch county records to improve coverage without individual lookups.
    county_count=0
    county_added=0
    for rows,page_no in pages("/juridiskaenheter/lan/25",key):
        county_count+=len(rows)
        for unit in rows:
            org=unit.get("peOrgNr")
            if not isinstance(org,str) or not org:raise RuntimeError("Missing county legal unit key")
            if org not in units:
                units[org]=(str(unit.get("jurform") or ""),bool(unit.get("namn")))
                county_added+=1
        print("County legal-unit page",page_no,"cumulative",county_count,flush=True)
    print("County additional unique legal entities:",county_added,flush=True)
    total=len(workplaces)
    links={org for org,_ in workplaces.values()}
    matched=links & units.keys()
    unmatched=links-units.keys()
    # Small diagnostic sample only; no identifiers or individual values leave memory.
    direct=collections.Counter()
    for org in sorted(unmatched)[:MAX_EXTRA_LOOKUPS]:
        try:
            entity=request("/juridiskaenheter/"+urllib.parse.quote(org,safe=""),key)
            if not isinstance(entity,dict):raise RuntimeError("Unexpected direct unit schema")
            form=str(entity.get("jurform") or "")
            group="fysisk_person" if form=="10" else "annan_juridisk_form" if form else "okand_form"
            direct[group]+=1
        except RuntimeError:
            direct["misslyckat_uppslag"]+=1
    print("Supplemental direct-lookups (non-representative):",dict(sorted(direct.items())),
          "attempted",sum(direct.values()),"of",len(unmatched),flush=True)
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
    print("Legal entities in combined municipality/county batch:",len(units))
    print("Matched workplace units:",len(matched),"unmatched units:",len(unmatched))
    print("Matched workplace rows:",matched_workplaces,"unmatched rows:",total-matched_workplaces)
    print("Workplace classification counts:",dict(sorted(categories.items())))
    print("Missing-name diagnostics:",dict(sorted(missing_names.items())))
    # Publish only municipality-wide aggregate classification from the paginated join.
    # Do not mix the tiny supplemental direct-lookup sample into these totals.
    if sum(categories.values())!=total:raise RuntimeError("Classification totals mismatch")
    report={"municipality":"2580",
            "fetched_at":datetime.datetime.now(datetime.timezone.utc).date().isoformat(),
            "source":"SCB, allmänna företagsregistret – egen bearbetning",
            "workplace_count":total,
            "scope":"Juridiska enheter med säte i Norrbottens län; omatchade kan ha säte utanför länet",
            "juridisk_form_groups":dict(sorted(categories.items())),
            "match_rate_workplaces":round(matched_workplaces/total,6),
            "matched_workplaces_without_name_with_legal_unit_name":missing_names["enhetsnamn_finns"],
            "personal_data":"No company identifiers, names or addresses in this file"}
    os.makedirs("docs/data",exist_ok=True)
    with open("docs/data/scb_legal_form_coverage.json","w",encoding="utf-8") as fh:
        json.dump(report,fh,ensure_ascii=False,indent=2);fh.write("\n")
    print("Requests used:",calls,"/",BUDGET)
    print("No identifiers or individual register values saved")
if __name__=="__main__":main()
