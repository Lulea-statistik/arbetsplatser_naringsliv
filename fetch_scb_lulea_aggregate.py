"""Fetch and verify all Lulea workplace pages, emitting only non-personal aggregate counts.

Never persist individual register records, names, addresses, identifiers, or raw responses.
SCB provides cursorId pagination and maximum 5000 items per request.
"""
import collections
import datetime as dt
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

BASE="https://apiafr.scb.se/v1/arbetsstallen/kommun/2580"
COUNT="https://apiafr.scb.se/v1/arbetsstallen/kommun/2580/count"
LIMIT=2000

def query(url,key):
    headers={"Accept":"application/json","X-API-Key":key,"User-Agent":"Lulea-statistik-public-aggregate/1.0"}
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=35) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            if error.code not in (429,500,502,503,504) or attempt==3:
                raise RuntimeError(f"SCB returned HTTP {error.code}") from None
        except (OSError,ValueError):
            if attempt==3: raise RuntimeError("SCB temporary connection or JSON failure") from None
        time.sleep(2**attempt*3)
    raise RuntimeError("Retry limit reached")

def aggregate():
    key=os.environ.get("SCB_API_KEY","").strip()
    if not key: raise RuntimeError("SCB_API_KEY secret missing")
    count_response=query(COUNT,key)
    if isinstance(count_response,int):
        expected=count_response
    elif isinstance(count_response,dict):
        values=[v for k,v in count_response.items() if k.lower() in ("count","total","totalcount","antal") and type(v)==int]
        if len(values)!=1: raise RuntimeError("Count schema unexpected")
        expected=values[0]
    else: raise RuntimeError("Count response type unexpected")
    if expected<1:raise RuntimeError("Count zero or invalid")
    print("SCB reported Lulea workplaces:",expected,flush=True)
    cursor=None
    seen_cursors=set()
    seen_cfar=set()
    n=0
    pages=0
    by_size=collections.Counter()
    by_industry=collections.Counter()
    by_status=collections.Counter()
    by_marketing=collections.Counter()
    valid_address=0
    with_restriction=0
    while True:
        params={"limit":str(LIMIT)}
        if cursor is not None:params["cursorId"]=str(cursor)
        data=query(BASE+"?"+urllib.parse.urlencode(params),key)
        if not isinstance(data,dict) or not isinstance(data.get("pagination"),dict) or not isinstance(data.get("arbetsstallen"),list):
            raise RuntimeError("Unexpected SCB page response schema")
        records=data["arbetsstallen"]
        pagination=data["pagination"]
        if not records or len(records)>LIMIT:
            raise RuntimeError("Empty or oversized SCB page")
        for record in records:
            if not isinstance(record,dict):raise RuntimeError("Unexpected workplace record type")
            # Explicit data minimization: copy only approved fields for aggregate calculations.
            # peOrgNr, names, exact address details and contact data are never
            # transferred into the analysis projection or output.
            selected = {field: record.get(field) for field in
                        ("cfarNr", "anstKl", "aeStat", "primarNaringsgren", "belagenhetsadress",
                         "reklamSparrTyp", "telefonSparrTyp", "epostSparrTyp")}
            # Keep only a boolean indicating address availability, never an address.
            has_location = isinstance(selected["belagenhetsadress"], dict) and bool(selected["belagenhetsadress"])
            selected.pop("belagenhetsadress")
            cfar=selected["cfarNr"]
            if not isinstance(cfar,int):raise RuntimeError("Missing CFAR")
            if cfar in seen_cfar:raise RuntimeError("Duplicate CFAR across pages")
            seen_cfar.add(cfar)
            klass=selected["anstKl"]
            by_size[str(klass) if klass is not None else "saknas"]+=1
            industry=selected["primarNaringsgren"]
            industry_code=industry.get("avdelningsKod") if isinstance(industry,dict) else None
            by_industry[str(industry_code) if industry_code else "saknas"]+=1
            by_status[str(selected["aeStat"]) if selected["aeStat"] is not None else "saknas"]+=1
            by_marketing[str(selected["reklamSparrTyp"]) if selected["reklamSparrTyp"] is not None else "saknas"]+=1
            if has_location:
                valid_address+=1
            if all(selected[field] is not None for field in
                   ("reklamSparrTyp", "telefonSparrTyp", "epostSparrTyp")):
                with_restriction+=1
        page_count=len(records)
        n+=page_count
        # Release raw SCB response before requesting the next page.
        del record, selected, records, data
        pages+=1
        print(f"Page {pages}: {page_count} records, cumulative {n}/{expected}",flush=True)
        if n>expected+LIMIT:raise RuntimeError("Received more rows than expected")
        if pagination.get("hasMore") is not True:
            break
        next_cursor=pagination.get("nextCursorId")
        if not isinstance(next_cursor,int) or next_cursor in seen_cursors or next_cursor==cursor:
            raise RuntimeError("Missing/repeated pagination cursor")
        cursor=next_cursor
        seen_cursors.add(cursor)
        if pages>1000:raise RuntimeError("Safety page limit")
        time.sleep(0.8)
    if n!=expected:
        raise RuntimeError(f"Total mismatch: collected {n}; SCB reports {expected}. Do not publish")
    # For newly published breakdowns, protect rare groups by combining cells <5.
    def safe_distribution(counter):
        result={}
        small=0
        for label,count in counter.items():
            if count<5: small+=count
            else: result[label]=count
        if small:
            # If the combined remainder is also small, combine with largest group.
            if small<5 and result:
                biggest=max(result,key=result.get)
                result[biggest+" (inkl. färre än 5 i andra kategorier)"]=result.pop(biggest)+small
            else: result["Övriga kategorier (sammanslagna)"]=small
        return dict(sorted(result.items()))
    summary={"municipality":"2580","source":"SCB, allmänna företagsregistret – egen bearbetning","fetched_at":dt.datetime.now(dt.timezone.utc).date().isoformat(),
             "workplace_count":n,"pages":pages,"records_with_location_address":valid_address,
             "records_with_reklam_telefon_epost_spärrfält":with_restriction,
             "employment_size_class_distribution":safe_distribution(by_size),
             "categorical_distributions":{
               "anstKl":safe_distribution(by_size),
               "aeStat":safe_distribution(by_status),
               "sniAvdelning":safe_distribution(by_industry),
               "reklamSparrTyp":safe_distribution(by_marketing)},
             "distribution_note":"Sällsynta kategorier (färre än fem poster) har slagits samman för offentlig presentation."}
    # Aggregate data only; no addresses, company names or unique business IDs.
    os.makedirs("docs/data",exist_ok=True)
    with open("docs/data/scb_lulea_aggregate.json","w",encoding="utf-8") as f:
        json.dump(summary,f,ensure_ascii=False,indent=2)
        f.write("\n")
    print("SUCCESS: complete municipality extraction and privacy-safe aggregate written")

if __name__=="__main__":
    aggregate()
