import re, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2])); sys.path.insert(0, str(Path(__file__).resolve().parent))
from chuleta import http as net
from ff_match import parse
out=[]
for comp in ("champions","europa-league","copa-del-rey"):
    for season in ("2025-2026","2024-2025"):
        c=net.get_text(f"https://www.futbolfantasy.com/{comp}/calendario/{season}")
        slugs=sorted(set(re.findall(r"/partidos/(\d+-[a-z0-9-]+)",c)),key=lambda s:int(s.split("-")[0]))
        for s in slugs:
            try:
                r=parse(s)
                if r and r["date"]: out.append({"comp":comp,"season":season,"slug":s,"teams":r["teams"],"date":r["date"],"score":r["score"]})
            except Exception: pass
        print(comp,season,len(out),flush=True)
json.dump(out,open(str(Path(__file__).resolve().parents[1] / "data" / "comps.json"),"w"),ensure_ascii=False); print("done",len(out))
