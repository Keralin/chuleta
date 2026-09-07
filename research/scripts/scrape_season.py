"""Scrape one LaLiga season from futbolfantasy match pages.

usage: python3 scrape_season.py <end-year> <out.json>
  end-year 2026 = season 2025/26 (the site keys seasons by the closing year).
Each match: teams, score, date and per-player LaLiga Fantasy points (starters flagged).
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from chuleta import http as net
from ff_match import parse

year, out = sys.argv[1], sys.argv[2]
cal = net.get_text(f"https://www.futbolfantasy.com/laliga/calendario/{year}")
slugs = sorted(set(re.findall(r"/partidos/(\d+-[a-z0-9-]+)", cal)), key=lambda s: int(s.split("-")[0]))
rows, bad = [], 0
for i, s in enumerate(slugs):
    try:
        r = parse(s)
        if r and r["score"]:
            rows.append(r)
        else:
            bad += 1
    except Exception:
        bad += 1
    if i % 40 == 0:
        print(i, len(rows), bad, flush=True)
json.dump(rows, open(out, "w"), ensure_ascii=False)
print("done", len(rows), "bad", bad)
