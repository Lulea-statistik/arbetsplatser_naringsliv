"""Inspect SCB's documented municipality search parameters and sanitized response shape.

Only prints parameter definitions and JSON property names/types, never values.
Makes a single authenticated request limited to one record if schema supports it.
"""
import json,os,urllib.request,urllib.parse,urllib.error
BASE="https://apiafr.scb.se"
SPEC=BASE+"/swagger/v1/swagger.json"
END="/v{v}/arbetsstallen/kommun/{kommunKod}"
def schema_ref(x,spec):
    if "$ref" in x:
        ref=x["$ref"]
        if ref.startswith("#/"):
            node=spec
            for segment in ref[2:].split("/"):
                node=node[segment.replace("~1","/").replace("~0","~")]
            return schema_ref(node,spec)
    return x
def shape(value,depth=0):
    if depth>2:return type(value).__name__
    if isinstance(value,dict):
        return {k:shape(v,depth+1) for k,v in list(value.items())[:75]}
    if isinstance(value,list):
        return {"type":"array","length":len(value),"item_shape":shape(value[0],depth+1) if value else None}
    return type(value).__name__
def main():
    key=os.environ.get("SCB_API_KEY","").strip()
    if not key:raise SystemExit("SCB_API_KEY missing")
    with urllib.request.urlopen(SPEC,timeout=20) as r: spec=json.load(r)
    op=spec["paths"][END]["get"]
    params=spec["paths"][END].get("parameters",[])+op.get("parameters",[])
    print("Operation:",op.get("operationId"),"summary:",op.get("summary"))
    pagination={}
    for param in params:
        p=schema_ref(param,spec)
        sch=schema_ref(p.get("schema",{}),spec)
        name=p.get("name","")
        print("Parameter:",name,"location:",p.get("in"),"required:",p.get("required"),"type:",sch.get("type"),"default:",sch.get("default"))
        if name.lower() in ("pagesize","size","limit","take","antal","perpage"):
            pagination[name]="1"
        if name.lower() in ("page","pagenumber","sida","pageindex","offset","skip","start"):
            pagination[name]="0" if name.lower() in ("offset","skip","start","pageindex") else "1"
    print("Response schema codes:",",".join(op.get("responses",{}).keys()))
    if not any(k.lower() in ("pagesize","size","limit","take","antal","perpage") for k in pagination):
        print("SKIPPED actual data request: no clearly recognized page-size parameter. Never download unbounded records.")
        return
    url=BASE+"/v1/arbetsstallen/kommun/2580?"+urllib.parse.urlencode(pagination)
    req=urllib.request.Request(url,headers={"X-API-Key":key,"Accept":"application/json"})
    try:
        with urllib.request.urlopen(req,timeout=30) as response:
            print("Sample HTTP:",response.status)
            # A small bound; do not print bodies, error payload, or any values.
            raw=response.read(150000)
    except urllib.error.HTTPError as ex:
        print("Sample HTTP:",ex.code)
        return
    except Exception as ex:
        print("Transport class:",type(ex).__name__)
        return
    try:
        data=json.loads(raw)
    except ValueError:
        print("Unrecognized/truncated JSON")
        return
    print("Sanitized JSON structure:",json.dumps(shape(data),ensure_ascii=False))
    print("No response data saved; publication remains blocked")
if __name__=="__main__":main()
