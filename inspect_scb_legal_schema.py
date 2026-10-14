"""Inspect SCB OpenAPI legal-entity and legal-form schemas safely.

Outputs only endpoint paths, operation methods, parameter names, property
names and enum/description metadata. No company IDs or source records.
"""
import json
import urllib.request

URL="https://apiafr.scb.se/swagger/v1/swagger.json"

def main():
    req=urllib.request.Request(URL,headers={"Accept":"application/json","User-Agent":"Lulea-statistik-schema-audit/1.0"})
    with urllib.request.urlopen(req,timeout=40) as r:
        spec=json.load(r)
    paths=spec.get("paths",{})
    for path,methods in sorted(paths.items()):
        if any(term in path.lower() for term in ("juridisk","jurform","kodtabell","arbetsstallen")):
            for method,operation in sorted(methods.items()):
                if method.lower() not in ("get","post"):continue
                params=[p.get("name","") for p in operation.get("parameters",[])]
                print("API",method.upper(),path,"parameters",",".join(params))
    schemas=spec.get("components",{}).get("schemas",{})
    for name,definition in sorted(schemas.items()):
        if any(term in name.lower() for term in ("juridisk","jurform","naringsgren","arbetsstalle")):
            fields=list(definition.get("properties",{}))
            print("SCHEMA",name,"fields",",".join(sorted(fields)))
    print("Schema discovery complete. No business records fetched.")
if __name__=="__main__":main()
