"""100-record diagnostic sample, with strictly aggregate and schema-only output.

No peOrgNr, cfarNr, names, addresses, coordinates or individual records are
saved, printed or written to artifacts. The sample is NOT representative.
"""
import datetime as dt
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

URL="https://apiafr.scb.se/v1/arbetsstallen/kommun/2580?limit=100"
SAFE_FIELDS=("cfarNr","peOrgNr","ben","primarNaringsgren","postAdress",
             "belagenhetsadress","aeStat","anstKl","reklamSparrTyp",
             "telefonSparrTyp","epostSparrTyp")

def read_api(key):
    headers={"Accept":"application/json","X-API-Key":key,"User-Agent":"Lulea-statistik-sample-audit/1.0"}
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(URL,headers=headers),timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429,500,502,503,504) or attempt==3:
                raise RuntimeError(f"SCB HTTP {e.code}") from None
        except (OSError,ValueError) as e:
            if attempt==3:raise RuntimeError(f"SCB network or JSON issue: {type(e).__name__}") from None
        time.sleep((attempt+1)*3)
    raise RuntimeError("Retries exhausted")

def run():
    key=os.environ.get("SCB_API_KEY","").strip()
    if not key:raise SystemExit("Missing SCB_API_KEY")
    data=read_api(key)
    if not isinstance(data,dict) or not isinstance(data.get("arbetsstallen"),list):
        raise RuntimeError("Unexpected API response")
    records=data["arbetsstallen"]
    if len(records)!=100:
        raise RuntimeError(f"Expected 100 sample rows; received {len(records)}")
    # Deliberately only COUNT whether key fields exist. Never collect field values.
    counts={field:sum(1 for row in records if row.get(field) is not None)
            for field in SAFE_FIELDS}
    nested={}
    for field in ("primarNaringsgren","postAdress","belagenhetsadress"):
        nested[field]=sorted({k for row in records if isinstance(row.get(field),dict)
                              for k in row[field].keys()})
    result={
        "source":"SCB, allmänna företagsregistret – egen bearbetning",
        "municipality":"2580",
        "fetched_at":dt.datetime.now(dt.timezone.utc).date().isoformat(),
        "sample_size":len(records),
        "method":"Första 100 posterna från API:et; inte ett slumpmässigt eller representativt urval.",
        "fields_present_count":counts,
        "nested_field_names":nested,
        "publication_note":"Ingen enskild post, namn, personnummer, CFAR-nummer, adress eller koordinat publiceras.",
        "legal_form_verified":False
    }
    os.makedirs("docs/data",exist_ok=True)
    with open("docs/data/scb_sample_audit.json","w",encoding="utf-8") as fh:
        json.dump(result,fh,ensure_ascii=False,indent=2)
        fh.write("\n")
    print("SCB sample verified: 100 records; only non-identifying aggregates and property names written")
if __name__=="__main__":run()
