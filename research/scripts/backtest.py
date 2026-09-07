import json, statistics as stx
from collections import defaultdict
from pathlib import Path
S=str(Path(__file__).resolve().parents[1] / "data")
MONTHS={m:i+1 for i,m in enumerate("enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split())}
def load(path):
    out=[]
    for m in json.load(open(path)):
        if not m.get("date"): continue
        y,mo,rest=m["date"].split("-",2); d,hm=rest.split(" "); m["ts"]=(int(y),MONTHS[mo],int(d),hm); out.append(m)
    return sorted(out,key=lambda m:m["ts"])
ms=load(f"{S}/matches_2324.json")+load(f"{S}/matches_2425.json")
tab=json.load(open(f"{S}/result_table.json")); edges=tab["edges"]
def p_res(gap,home):
    g=gap if home else -gap
    for lo,hi in zip(edges[:-1],edges[1:]):
        if lo<=g<hi:
            t=tab["t24"][f"{lo},{hi}"]; W,D,L=t["W"],t["D"],t["L"]
            return (W,D,L) if home else (L,D,W)
    return (1/3,1/3,1/3)
gd=defaultdict(float); pj=defaultdict(int)
prof=defaultdict(lambda: {"W":[], "D":[], "L":[], "all":[]})
K=["A_resultado_perfil","B_lineal_actual","C_media"]; errs={k:[] for k in K}; ranks={k:[] for k in K}
for m in ms:
    a,b=m["teams"]; sa,sb=m["score"]
    ga=gd[a]/pj[a] if pj[a] else 0.0; gb=gd[b]/pj[b] if pj[b] else 0.0
    is_test=(m["ts"][0]==2024 and m["ts"][1]>=8) or m["ts"][0]==2025
    for side,team,opp,gf,gc,home,gt,go in (("local",a,b,sa,sb,1,ga,gb),("visitante",b,a,sb,sa,0,gb,ga)):
        res="W" if gf>gc else "D" if gf==gc else "L"
        W,D,L=p_res(ga-gb,home)
        starters=[p for p in m["players"] if p["side"]==side and p["starter"]]
        preds={k:[] for k in K}; actual=[]
        for p in starters:
            pr=prof[(team,p["name"])]
            if is_test and len(pr["all"])>=8 and pj[team]>=3 and pj[opp]>=3:
                avg=stx.mean(pr["all"])
                byres={k:(stx.mean(pr[k]) if len(pr[k])>=3 else avg*{"W":7.1,"D":5.1,"L":2.8}[k]/5.0) for k in "WDL"}
                preds["A_resultado_perfil"].append(W*byres["W"]+D*byres["D"]+L*byres["L"])
                preds["B_lineal_actual"].append(avg*max(0.4,min(1.8,(1-0.20*go)*(1+0.22*gt)*(1.14 if home else 0.86))))
                preds["C_media"].append(avg); actual.append(p["pts"])
            pr[res].append(p["pts"]); pr["all"].append(p["pts"])
        if len(actual)>=6:
            for k in K:
                errs[k]+=[abs(x-y) for x,y in zip(preds[k],actual)]
                top=sorted(range(len(actual)),key=lambda i:-preds[k][i])[:3]
                ranks[k].append(stx.mean(actual[i] for i in top)-stx.mean(actual))
    gd[a]+=sa-sb; gd[b]+=sb-sa; pj[a]+=1; pj[b]+=1
print("evaluado en 24/25 (entrenado con 23/24 + lo previo de 24/25):",len(errs["C_media"]),"titulares-partido")
for k in K: print(f"{k:22} MAE {stx.mean(errs[k]):.3f} | top-3 elegidos vs media del equipo {stx.mean(ranks[k]):+.2f} pts")
