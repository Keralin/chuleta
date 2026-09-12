"""Command line. Reports in Spanish, code in English.

Irreversible actions (accepting offers, paying clauses) require the player's
name spelled out; listings, bids and lineups are reversible and just go."""

import argparse
import json
import sys

from . import auth
from .api import ApiError, Client, club_of
from .matching import POS, normalize
from .sources.clubs import club_names
from .sources.last_season import last_season_points
from .sources.season_points import historical_per_game
from .sources.news import team_news
from .sources.press import club_lineup
from .strategy import cash, clauses, lineup, scout, sniper, vacancies


def _json(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=1, default=str))


def _find_mine(client, league_id, team_id, name):
    """Squad entry whose nickname or name contains `name` (accent-insensitive)."""
    q = normalize(name)
    hits = [p for p in client.team(league_id, team_id)["players"]
            if q in normalize(p["playerMaster"].get("nickname", "")) or q in normalize(p["playerMaster"].get("name", ""))]
    if len(hits) != 1:
        raise SystemExit(f"'{name}' casa con {len(hits)} jugadores de tu plantilla; afina el nombre.")
    return hits[0]


def _my_listing(client, league_id, player_master_id):
    for e in client.market(league_id):
        if e["playerMaster"]["id"] == player_master_id and e.get("playerTeam"):
            return e
    return None


# --- account ---------------------------------------------------------------
def cmd_login(a):
    if not a.redirect:
        print("1) Abre esta URL, entra con tu cuenta y, cuando el navegador falle al abrir\n"
              "   'authredirect://...', copia esa URL entera (DevTools > Network, con 'Preserve log').\n"
              "2) Ejecuta: chuleta login \"authredirect://...\"\n")
        print(auth.start_login())
        return
    auth.finish_login(a.redirect)
    me = Client().me()
    print(f"Sesión guardada. Hola, {me.get('managerName') or me.get('id')}.")


def cmd_ligas(a):
    for lg in Client().leagues():
        print(f"{lg['id']}  {lg['name']}  (equipo {lg['team']['id']})")


def cmd_plantilla(a):
    c = Client(); lid, tid = c.default_ids(); t = c.team(lid, tid)
    if a.json:
        return _json(t)
    print(f"Caja {t['teamMoney']:,} | {len(t['players'])} jugadores")
    for p in sorted(t["players"], key=lambda p: (int(p["playerMaster"]["positionId"]), -int(p["playerMaster"]["marketValue"]))):
        pm = p["playerMaster"]
        print(f"  {POS.get(int(pm['positionId']), '?')} {pm['nickname']:<18} {club_of(pm)[0][:16]:<16} "
              f"valor {int(pm['marketValue']):>11,} cláusula {p.get('buyoutClause') or 0:>11,} "
              f"media {float(pm.get('averagePoints') or 0):4.1f} {pm.get('playerStatus')}")


# --- analysis --------------------------------------------------------------
def cmd_mercado(a):
    c = Client(); lid, tid = c.default_ids()
    rows = scout.study(c, lid, horizon=a.horizon)
    if a.json:
        return _json(rows)
    print(f"{'JUGADOR':<16}{'POS':<4}{'EQUIPO':<16}{'VENDE':<11}{'ENTRADA':>11}{'TEND/D':>9}{'PROY%':>7}"
          f"{'25/26':>6}{'PJ':>3}{'MIN':>5}{'MEDIA':>6}{'PROB':>5}  VEREDICTO")
    print("-" * 104)
    for r in rows:
        prob = f"{r['prob']}%" if r["prob"] is not None else "?"
        marg = f"{r['margen_pct']:+.1f}" if r["margen_pct"] is not None else "?"
        hist = "?" if r["ptos_25_26"] is None else str(r["ptos_25_26"])
        verdict = "VETO: " + "; ".join(r["vetos"]) if r["vetos"] else ("compra" if (r["margen_pct"] or 0) > 5 else "neutro")
        print(f"{r['nombre'][:15]:<16}{r['pos']:<4}{r['equipo'][:15]:<16}{r['vendedor'][:10]:<11}{r['entrada']:>11,}"
              f"{r['tend_dia']:>+9,}{marg:>7}{hist:>6}{r['pj']:>3}{r['minutos']:>5}{r['media']:>6.1f}{prob:>5}  {verdict}")
    print(f"\ncaja disponible: {c.team(lid, tid)['teamMoney']:,}")


def cmd_historial(a):
    c = Client(); q = normalize(a.jugador); clubs = club_names(c)
    hits = [p for p in c.players() if q in normalize(f"{p.get('nickname', '')} {p.get('name', '')}")]
    if not hits:
        return print(f"Ningún jugador casa con '{a.jugador}'.")
    for p in hits[:5]:
        detail = c.player(p["id"])
        print(f"\n{p.get('nickname')} [{club_of(detail if detail.get('team') else p, clubs)[0]}]  "
              f"valor {int(p['marketValue']):,} | media {p.get('averagePoints')} | estado {p.get('playerStatus')}")
        prev = None
        for h in c.value_history(p["id"])[-a.dias:]:
            v = int(h["marketValue"])
            print(f"    {str(h.get('date'))[:10]}  {v:>12,}  {f'{v - prev:+,}' if prev is not None else ''}")
            prev = v
        for s in sorted(detail.get("playerStats") or [], key=lambda s: s.get("weekNumber") or 0):
            mins = ((s.get("stats") or {}).get("mins_played") or [0])[0]
            print(f"    J{s['weekNumber']:<3} {s['totalPoints']:>3} pts  {mins} min")


def cmd_trading(a):
    c = Client(); lid, tid = c.default_ids(); me = int(c.me()["id"])
    names = {str(p["id"]): p.get("nickname") or p.get("name") for p in c.players()}
    buys, sells = cash.my_trades(c, lid, me)
    team = {str(p["playerMaster"]["id"]): p for p in c.team(lid, tid)["players"]}
    listings = {str(e["playerMaster"]["id"]): e for e in c.market(lid) if (e.get("playerTeam") or {}).get("manager", {}).get("id") == str(me)}
    print("== CARTERA (compradas, sin vender) ==")
    tc = tv = 0
    for pid, cost in buys.items():
        if pid in sells or pid not in team:
            continue
        value = int(team[pid]["playerMaster"]["marketValue"]); tc += cost; tv += value
        extra = ""
        if pid in listings:
            extra = f" | en venta a {listings[pid]['salePrice']:,}"
            for o in c.offers(lid, team[pid]["playerTeamId"]):
                extra += f" | oferta {o['money']:,} ({o['money'] / value * 100:.0f}%)"
        print(f"  {names.get(pid, pid):<16} coste {cost:>12,} | vale {value:>12,} | {value - cost:>+11,} ({(value - cost) / cost * 100:+.1f}%){extra}")
    if tc:
        print(f"  {'TOTAL':<16} coste {tc:>12,} | vale {tv:>12,} | {tv - tc:>+11,} ({(tv - tc) / tc * 100:+.1f}%)")
    print("\n== REALIZADAS ==")
    for pid, amount in sells.items():
        cost = buys.get(pid)
        print(f"  {names.get(pid, pid):<16} " + (f"coste {cost:>12,} | venta {amount:>12,} | {amount - cost:>+11,}" if cost else f"plantilla inicial | venta {amount:>12,}"))
    print("\n== ANUNCIOS ==")
    for pid, e in listings.items():
        offers = c.offers(lid, team[pid]["playerTeamId"]) if pid in team else []
        value = int(e["playerMaster"]["marketValue"])
        print(f"  {names.get(pid, pid):<16} pide {e['salePrice']:>11,} valor {value:>11,} | " +
              (", ".join(f"{o['money']:,} ({o['money'] / value * 100:.0f}%, hasta {str(o.get('expirationDate'))[5:16]})" for o in offers) or "sin oferta"))


def cmd_caja(a):
    c = Client(); lid, tid = c.default_ids(); real = c.team(lid, tid)["teamMoney"]; me = c.me().get("managerName")
    rows = cash.estimate(c, lid)
    if a.json:
        return _json(rows)
    print(f"{'MÁNAGER':<14}{'GASTADO':>14}{'INGRESADO':>13}{'CAJA ESTIMADA':>16}")
    for r in rows:
        tag = f"  (real: {real:,})" if r["manager"] == me else ""
        print(f"{r['manager']:<14}{r['gastado']:>14,}{r['ingresado']:>13,}{r['caja']:>16,}{tag}")
        for other, amt in r["traspasos"]:
            print(f"    traspaso con {other}: {amt:,}")
    print("\nLas subidas de cláusula no salen en el feed: la caja real es igual o menor.")


def cmd_clausulas(a):
    c = Client(); lid, tid = c.default_ids()
    res = clauses.analyze(c, lid, tid)
    if a.json:
        return _json(res)
    print("== Riesgo en tu plantilla ==")
    for r in res["mine"]:
        print(f"  {r['nombre']:<18} {r['pos']} cláusula {r['clausula']:>11,} ratio {r['ratio_hoy']:.2f} -> {r['ratio_al_abrir']:.2f} al abrir ({r['dias_protegido']}d){'  a valor: cualquiera puede pagarla' if r['ratio_al_abrir'] <= 1.05 else ''}")
    print("\n== Objetivos en plantillas rivales ==")
    for r in res["rivals"]:
        print(f"  {r['nombre']:<18} {r['pos']} de {r['manager']:<12} cláusula {r['clausula']:>11,} ratio {r['ratio_al_abrir']:.2f} abre en {r['dias_protegido']}d")


def cmd_onces(a):
    for p in sorted(club_lineup(a.club), key=lambda p: -(p["prob"] or 0)):
        flag = " LESIONADO" if p["lesionado"] else ("" if p["disponible"] else " NO DISPONIBLE")
        print(f"  {str(p['prob']) + '%' if p['prob'] is not None else '?':>4}  {p['nombre']}{flag}")


def cmd_noticias(a):
    for n in team_news(a.club)[:a.n]:
        print(f"  [{n['tipo']:<12}] {n['fecha']}  {n['titular']}")


def cmd_bajas(a):
    c = Client(); lid, _ = c.default_ids()
    rows = vacancies.study(c, lid, club_filter=a.club)
    if a.json:
        return _json(rows)
    if not rows:
        return print("Sin bajas relevantes.")
    for r in rows:
        print(f"\n{r['equipo']}: BAJA {r['baja']} ({r['pos']}, {r['estado']}) media {r['media']:.1f} | {r['ptos']} pts | {r['ptos_25_26'] if r['ptos_25_26'] is not None else '?'} en 25/26")
        for h in r["herederos"]:
            prob = f"{h['prob']}%" if h["prob"] is not None else "?"
            mk = h["mercado"]
            print(f"   hereda: {h['nombre']:<18} prensa {prob:>4} media {h['media']:.1f} ({h['ptos']} pts) 25/26 {h['ptos_25_26']} valor {h['valor']:,}"
                  + (f" | EN MERCADO ({(mk.get('playerTeam') or {}).get('manager', {}).get('managerName') or 'SISTEMA'})" if mk else ""))


def cmd_alinear(a):
    c = Client(); lid, tid = c.default_ids(); team = c.team(lid, tid)
    best = lineup.optimize(team, recent_minutes=lineup.recent_minutes(c, team),
                            last_season=last_season_points, history=historical_per_game)
    if a.json:
        return _json(best)
    d, m, f = best["formation"]
    print(f"Mejor formación: {d}-{m}-{f}  (puntos esperados {best['total']})\n")
    for line, key in (("POR", "goalkeeper"), ("DEF", "defender"), ("MED", "midfield"), ("DEL", "striker")):
        for e in ([best[key]] if key == "goalkeeper" else best[key]):
            tag = "" if e["tag"] == "prensa" else f" [{e['tag']}]"
            print(f"  {line}  {e['nombre']:<20} juega {e['prob']:>3}%  esperados {e['score']:.1f}{tag}")
    print(f"\nBanquillo: {', '.join(best['bench'])}")
    if a.aplicar:
        c.save_lineup(tid, best["goalkeeper"]["id"], [e["id"] for e in best["defender"]],
                      [e["id"] for e in best["midfield"]], [e["id"] for e in best["striker"]])
        print("Alineación guardada.")
    else:
        print("(propuesta; añade --aplicar para guardarla)")


# --- actions ---------------------------------------------------------------
def cmd_listar(a):
    c = Client(); lid, tid = c.default_ids(); p = _find_mine(c, lid, tid, a.jugador)
    c.list_player(lid, p["playerTeamId"], a.precio)
    print(f"{p['playerMaster']['nickname']} listado a {a.precio:,} (valor {int(p['playerMaster']['marketValue']):,}). Deshacer: chuleta retirar.")


def cmd_retirar(a):
    c = Client(); lid, tid = c.default_ids(); p = _find_mine(c, lid, tid, a.jugador)
    e = _my_listing(c, lid, p["playerMaster"]["id"])
    if not e:
        return print("No está listado.")
    c.unlist_player(lid, e["id"]); print(f"Anuncio de {p['playerMaster']['nickname']} retirado.")


def cmd_acepta(a):
    c = Client(); lid, tid = c.default_ids(); p = _find_mine(c, lid, tid, a.jugador)
    e = _my_listing(c, lid, p["playerMaster"]["id"])
    offers = c.offers(lid, p["playerTeamId"]) if e else []
    if not offers:
        return print("Sin oferta pendiente.")
    o = max(offers, key=lambda o: o["money"])
    value = int(p["playerMaster"]["marketValue"])
    if not a.si:
        return print(f"Oferta por {p['playerMaster']['nickname']}: {o['money']:,} ({o['money'] / value * 100:.0f}% del valor). "
                     f"Es irreversible: repite con --si para aceptarla.")
    r = c.accept_offer(lid, e["id"], o["id"], o["money"])
    print(f"Aceptada: {p['playerMaster']['nickname']} vendido por {o['money']:,} ({r.get('status')}).")


def cmd_puja(a):
    c = Client(); lid, _ = c.default_ids()
    e = next((e for e in c.market(lid) if e["id"] == a.market_id), None)
    if not e:
        return print("Ese marketId no está en el mercado.")
    value = int(e["playerMaster"]["marketValue"])
    money = a.dinero or value + 10
    if money < value:
        return print(f"La puja mínima es el valor actual: {value:,}.")
    r = c.offer(lid, e["id"], money) if e.get("playerTeam") else c.bid(lid, e["id"], money)
    print(f"{'Oferta' if e.get('playerTeam') else 'Puja'} de {money:,} por {e['playerMaster']['nickname']} registrada ({str(r)[:60]}).")


def cmd_sniper(a):
    if a.accion == "armar":
        plan = sniper.arm(a.market_id, a.tope)
        print("Plan: " + ", ".join(f"{t['market_id']} tope {t['cap']:,}" for t in plan))
    elif a.accion == "ver":
        plan = sniper.targets()
        print("Plan: " + (", ".join(f"{t['market_id']} tope {t['cap']:,}" for t in plan) if plan else "vacío"))
    elif a.accion == "limpiar":
        sniper.clear(); print("Plan vaciado.")
    elif a.accion == "ejecutar":
        c = Client(); lid, _ = c.default_ids()
        sniper.run(c, lid, dry_run=a.simular)
    elif a.accion == "cron":
        c = Client(); lid, _ = c.default_ids()
        hm = sniper.cycle_utc(c, lid)
        if not hm:
            return print("Mercado vacío: no puedo leer la hora del ciclo.")
        print(f"Tu liga resuelve a las {hm[0]:02d}:{hm[1]:02d} UTC. Línea de crontab (5 min antes):")
        print("  " + sniper.cron_line(*hm))


def main(argv=None):
    from . import __version__
    ap = argparse.ArgumentParser(prog="chuleta", description="Tu chuleta para el mercado de LALIGA Fantasy")
    ap.add_argument("--version", action="version", version=f"chuleta {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("login", help="iniciar sesión (dos pasos)"); s.add_argument("redirect", nargs="?"); s.set_defaults(f=cmd_login)
    sub.add_parser("ligas", help="tus ligas").set_defaults(f=cmd_ligas)
    s = sub.add_parser("plantilla", help="tu plantilla y caja"); s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_plantilla)
    s = sub.add_parser("mercado", help="qué comprar y por qué no el resto"); s.add_argument("--horizon", type=int, default=7); s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_mercado)
    s = sub.add_parser("historial", help="curva de valor y puntos por jornada"); s.add_argument("jugador"); s.add_argument("--dias", type=int, default=10); s.set_defaults(f=cmd_historial)
    sub.add_parser("trading", help="cartera, realizadas y anuncios").set_defaults(f=cmd_trading)
    s = sub.add_parser("caja", help="caja estimada de cada mánager"); s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_caja)
    s = sub.add_parser("clausulas", help="riesgo propio y objetivos rivales"); s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_clausulas)
    s = sub.add_parser("onces", help="once probable de un club (slug futbolfantasy)"); s.add_argument("club"); s.set_defaults(f=cmd_onces)
    s = sub.add_parser("noticias", help="titulares tipados de un club"); s.add_argument("club"); s.add_argument("-n", type=int, default=12); s.set_defaults(f=cmd_noticias)
    s = sub.add_parser("bajas", help="quién hereda los minutos de un lesionado"); s.add_argument("club", nargs="?"); s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_bajas)
    s = sub.add_parser("alinear", help="mejor XI por puntos esperados"); s.add_argument("--aplicar", action="store_true"); s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_alinear)
    s = sub.add_parser("listar", help="poner a un jugador en venta"); s.add_argument("jugador"); s.add_argument("precio", type=int); s.set_defaults(f=cmd_listar)
    s = sub.add_parser("retirar", help="quitar un anuncio"); s.add_argument("jugador"); s.set_defaults(f=cmd_retirar)
    s = sub.add_parser("acepta", help="aceptar la oferta pendiente por un jugador (irreversible)"); s.add_argument("jugador"); s.add_argument("--si", action="store_true"); s.set_defaults(f=cmd_acepta)
    s = sub.add_parser("sniper", help="francotirador: armar <marketId> <tope> | ver | limpiar | ejecutar [--simular] | cron")
    s.add_argument("accion", choices=["armar", "ver", "limpiar", "ejecutar", "cron"]); s.add_argument("market_id", nargs="?"); s.add_argument("tope", nargs="?", type=int)
    s.add_argument("--simular", action="store_true"); s.set_defaults(f=cmd_sniper)
    s = sub.add_parser("puja", help="pujar u ofertar por un marketId (valor+10 por defecto)"); s.add_argument("market_id"); s.add_argument("dinero", nargs="?", type=int); s.set_defaults(f=cmd_puja)
    a = ap.parse_args(argv)
    try:
        a.f(a)
    except (ApiError, auth.AuthError) as e:
        print(f"[error] {e}", file=sys.stderr); sys.exit(1)


if __name__ == "__main__":
    main()
