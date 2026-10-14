"""Fetch SCB public code labels and audit legal entity response shape.

Do not print or write legal-entity values, identifiers or individual records.
"""
import json,os,time,urllib.parse,urllib.request
BASE="https://apiafr.scb.se/v1"
TABLES={"anstKl":"anstklkoder","aeStat":"aestatkoder","jurForm":"jurformkoder","reklamSparrTyp":"reklamsparrtypkoder"}
calls=0
def read(path,key):
    global calls
    if calls>=8:raise RuntimeError("Maximum of 8 SCB requests")
    if calls:time.sleep(0.6)
    calls+=1
    request=urllib.request.Request(BASE+path,headers={"Accept":"application/json","X-API-Key":key,"User-Agent":"Lulea-SCB-codes-audit/1.0"})
    with urllib.request.urlopen(request,timeout=40) as resp:return json.load(resp)
def parse_codes(body):
    if isinstance(body,list):items=body
    elif isinstance(body,dict):
        candidates=[x for x in body.values() if isinstance(x,list)]
        if len(candidates)!=1:raise RuntimeError("Unexpected code table wrapper")
        items=candidates[0]
    else:raise RuntimeError("Unexpected code table type")
    result={}
    for item in items:
        if not isinstance(item,dict):continue
        k=item.get("kod")
        label=item.get("klartext") or item.get("benamning") or item.get("text")
        if k is not None and isinstance(label,str) and label.strip():result[str(k)]=label.strip()
    if not result:raise RuntimeError("No codetext parsed")
    return result
def main():
    key=os.environ["SCB_API_KEY"]
    catalog={}
    for name,endpoint in TABLES.items():
        catalog[name]=parse_codes(read("/kodtabeller/"+endpoint,key))
        print("Fetched code text table:",name,"entries:",len(catalog[name]),flush=True)
    # Look at one legal unit only in runner memory; output keys/types, never values.
    page=read("/arbetsstallen/kommun/2580?limit=1",key)
    workplaces=page.get("arbetsstallen",[])
    if len(workplaces)!=1:raise RuntimeError("Unexpected workplace response")
    pe=workplaces[0].get("peOrgNr")
    if not isinstance(pe,str) or not pe:raise RuntimeError("Missing legal unit identifier")
    unit=read("/juridiskaenheter/"+urllib.parse.quote(pe,safe=""),key)
    if not isinstance(unit,dict):raise RuntimeError("Unexpected legal unit response")
    # Only structural keys; strings or exact values cannot enter the public output.
    keys=sorted(unit.keys())
    print("Legal unit schema keys:",",".join(keys),flush=True)
    print("Possible legal-form keys:",",".join(k for k in keys if "jur" in k.lower() or "form" in k.lower()),flush=True)
    print("Possible name keys:",",".join(k for k in keys if "namn" in k.lower() or "ben" in k.lower()),flush=True)
    # Code tables are public, non-record reference data and safe to distribute.
    os.makedirs("docs/data",exist_ok=True)
    with open("docs/data/scb_code_labels.json","w",encoding="utf-8") as f:
        json.dump({"source":"SCB – kodtabeller, egen bearbetning","tables":catalog},f,ensure_ascii=False,indent=2,sort_keys=True)
        f.write("\n")
    print("SUCCESS: only public code-table labels were saved; calls:",calls,flush=True)
if __name__=="__main__":main()
