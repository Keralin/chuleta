"""Parse a futbolfantasy match page: per-player LaLiga Fantasy points, minutes, side."""
import re, html, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from chuleta import http as net

def clean(s):
    return html.unescape(re.sub(r"<[^>]+>", " ", s)).strip()

def parse(slug):
    h = net.get_text(f"https://www.futbolfantasy.com/partidos/{slug}")
    i = h.find('data-tab="puntos"')
    if i < 0:
        return None
    seg = h[i:]
    j = seg.find("</section>")
    seg = seg[:j] if j > 0 else seg
    # score: first "N - M" pattern in the page header area
    title = re.search(r"<title>(.*?)</title>", h, flags=re.S).group(1)
    m = re.search(r"(.+?)\s+(\d{1,2})-(\d{1,2})\s+(.+?)\s+-\s+LaLiga", title)
    score = (int(m.group(2)), int(m.group(3))) if m else None
    teams = (m.group(1).strip(), m.group(4).strip()) if m else (None, None)
    d = re.search(r"(\d{1,2}) de (\w+) del (\d{4}) a las (\d{1,2}):(\d{2})", h, flags=re.I)
    date = f"{d.group(3)}-{d.group(2).lower()}-{int(d.group(1)):02d} {int(d.group(4)):02d}:{d.group(5)}" if d else None
    tables = re.findall(r"<table.*?</table>", seg, flags=re.S)
    out = []
    for side, tbl in zip(("local", "visitante"), tables[:2]):
        starter = True
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", tbl, flags=re.S):
            if 'class="name bold">Suplentes' in row:
                starter = False
                continue
            cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.S)
            if len(cells) < 10:
                continue
            name_cell = clean(cells[0])
            if name_cell in ("Titulares", "Suplentes", "") or name_cell.startswith("Ver la ficha"):
                continue
            mm = re.search(r"(\d+)'", name_cell)
            mins = int(mm.group(1)) if mm else 0
            name = re.sub(r"\s*\d+'.*$", "", name_cell).strip()
            pts_vals = re.findall(r"-?\d+(?:\.\d+)?", clean(cells[-1]))
            if not pts_vals:
                continue
            out.append({"side": side, "name": name, "mins": mins, "starter": starter, "pts": float(pts_vals[0])})
    return {"slug": slug, "teams": teams, "score": score, "date": date, "players": out}

if __name__ == "__main__":
    r = parse(sys.argv[1] if len(sys.argv) > 1 else "20345-alaves-villarreal")
    print(json.dumps({"slug": r["slug"], "teams": r["teams"], "score": r["score"], "n": len(r["players"]), "titulares": sum(p["starter"] for p in r["players"])}, ensure_ascii=False))
    for p in r["players"][:14]:
        print(p)
