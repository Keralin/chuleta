"""Command line. Reports in Spanish, code in English.

Irreversible actions (accepting offers, paying clauses) require the player's
name spelled out; listings, bids and lineups are reversible and just go."""

import argparse
import json
import sys
from datetime import datetime, timezone

from . import auth
from .api import ApiError, Client, club_of
from .matching import POS, match_name, normalize
from .sources.clubs import club_names
from .sources.last_season import last_season_points
from .sources.season_points import historical_per_game
from .sources.news import team_news
from .sources.press import club_lineup, probable_lineups
from .strategy import cash, clauses, lineup, schedule, scout, sniper, trend, vacancies, values


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
    rows = scout.study(c, lid, horizon=a.horizon, patient=not a.forced)
    if a.json:
        return _json(rows)
    print(f"{'JUGADOR':<16}{'POS':<4}{'EQUIPO':<16}{'VENDE':<11}{'ENTRADA':>11}{'TEND/D':>9}{'PROY%':>7}"
          f"{'25/26':>6}{'PJ':>3}{'MIN':>5}{'MEDIA':>6}{'PROB':>5}  VEREDICTO")
    print("-" * 104)
    for r in rows:
        prob = f"{r['prob']}%" if r["prob"] is not None else "?"
        marg = f"{r['margen_pct']:+.1f}" if r["margen_pct"] is not None else "?"
        hist = "?" if r["ptos_25_26"] is None else str(r["ptos_25_26"])
        verdict = "VETO: " + "; ".join(r["vetos"]) if r["vetos"] else (
            "compra" if (r["margen_pct"] or 0) >= values.BUY_MARGIN_PCT else "neutro")
        print(f"{r['nombre'][:15]:<16}{r['pos']:<4}{r['equipo'][:15]:<16}{r['vendedor'][:10]:<11}{r['entrada']:>11,}"
              f"{r['tend_dia']:>+9,}{marg:>7}{hist:>6}{r['pj']:>3}{r['minutos']:>5}{r['media']:>6.1f}{prob:>5}  {verdict}")
    salida = "forzada" if a.forced else "esperando oferta >=105%"
    print(f"\ncaja disponible: {c.team(lid, tid)['teamMoney']:,}"
          f" | PROY% a {a.horizon}d con salida {salida}"
          f" ({values.exit_rate(not a.forced) * 100:.1f}% del valor,"
          f" {values.roll_odds(a.horizon) * 100:.0f}% de ver la tirada en {a.horizon} dias)")


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


def cmd_valores(a):
    """Daily value movement of your squad: who rises, who turned, who brakes."""
    c = Client(); lid, tid = c.default_ids(); team = c.team(lid, tid)
    press = probable_lineups()
    rows = []
    for p in team["players"]:
        pm = p["playerMaster"]
        s = trend.summary(c.value_history(pm["id"]), int(pm.get("marketValue") or 0) or None)
        if not s:
            continue
        info = match_name(pm.get("nickname", ""), pm.get("name", ""), press)
        rows.append({"nombre": pm.get("nickname"), "pos": POS.get(int(pm.get("positionId") or 0), "?"),
                     "estado": pm.get("playerStatus"), "prob": (info or {}).get("prob"),
                     "aviso": _squad_warning(pm.get("playerStatus"), info), **s})
    rows.sort(key=lambda r: -r["hoy"])
    if a.json:
        return _json(rows)
    print(f"{'JUGADOR':<18}{'POS':<5}{'VALOR':>13}{'HOY':>13}{'%':>7}{'ACELERA':>11}{'RACHA':>10}  AVISO")
    for r in rows:
        print(f"{r['nombre'][:17]:<18}{r['pos']:<5}{r['valor']:>13,}{r['hoy']:>+13,}{r['pct']:>+7.1f}"
              f"{round(r['aceleracion']):>+11,}{r['sentido'] + ' ' + str(r['racha']) + 'd':>10}  {r['aviso']}")
    total = sum(r["valor"] for r in rows); hoy = sum(r["hoy"] for r in rows)
    print(f"\nplantilla {total:,} ({hoy:+,} hoy) | caja {int(team['teamMoney']):,}")
    hurt = [r for r in rows if r["aviso"]]
    if hurt:
        print("aviso: " + " | ".join(f"{r['nombre']} {r['aviso']}" for r in hurt))


def _squad_warning(status, info):
    """Why a player of ours deserves a look today: the API status, or the press
    when it knows about an injury the API has not registered yet."""
    out = []
    if status and status != "ok":
        out.append(status.upper())
    if info and info.get("lesionado"):
        out.append("prensa: lesionado")
    if info and not info.get("disponible", True):
        out.append("prensa: no disponible")
    # a missing press entry is a name that did not match, not a dropped player,
    # so it says nothing worth a line in a column read every day
    return ", ".join(out)


def cmd_rivales(a):
    """What every manager can spend, what he is short of and what he is selling."""
    c = Client(); lid, tid = c.default_ids()
    money = {r["manager"]: r["caja"] for r in cash.estimate(c, lid)}
    listed = {}
    for e in c.market(lid):
        seller = ((e.get("playerTeam") or {}).get("manager") or {}).get("managerName")
        if seller:
            listed.setdefault(seller, []).append(e["playerMaster"].get("nickname"))
    rows = []
    for r in c.standings(lid):
        name = r["team"]["manager"]["managerName"]; mine = str(r["team"]["id"]) == str(tid)
        t = c.team(lid, str(r["team"]["id"]))
        caja = int(t["teamMoney"]) if mine else money.get(name, 0)
        value = int(t["teamValue"])
        squad = {k: 0 for k in ("POR", "DEF", "MED", "DEL")}
        rate = 0.0
        for p in t["players"]:
            pm = p["playerMaster"]
            squad[POS.get(int(pm.get("positionId") or 0), "POR")] += 1
            curve = values.curve(c, pm["id"], live=int(pm.get("marketValue") or 0) or None)
            if curve:
                rate += curve[1]
        rows.append({"manager": name, "yo": mine, "posicion": r.get("position"), "puntos": r.get("points"),
                     "caja": caja, "valor_equipo": value, "deuda": int(value * 0.2),
                     "puede_gastar": caja + int(value * 0.2), "plantilla": squad, "valor_dia": round(rate),
                     "jugadores": len(t["players"]), "en_venta": listed.get(name, [])})
    rows.sort(key=lambda r: -r["puede_gastar"])
    if a.json:
        return _json(rows)
    print(f"{'MÁNAGER':<14}{'PTS':>5}{'CAJA':>15}{'PUEDE GASTAR':>15}{'EQUIPO':>14}{'VALOR/DÍA':>12}{'%':>7}  PLANTILLA")
    for r in rows:
        s = r["plantilla"]
        pct = r["valor_dia"] / r["valor_equipo"] * 100 if r["valor_equipo"] else 0.0
        print(f"{r['manager'][:13]:<14}{r['puntos']:>5}{r['caja']:>15,}{r['puede_gastar']:>15,}"
              f"{r['valor_equipo']:>14,}{r['valor_dia']:>+12,}{pct:>+7.2f}"
              f"  {r['jugadores']} ({s['POR']}-{s['DEF']}-{s['MED']}-{s['DEL']})"
              + ("  <- tú" if r["yo"] else ""))
        if r["en_venta"]:
            print(f"    en venta: {', '.join(r['en_venta'])}")
    print("\nCaja de los rivales estimada del feed público: las subidas de cláusula no salen, así que es un máximo.")
    print("VALOR/DÍA es la suma de la tendencia diaria de cada jugador, y % lo mismo sobre el valor de su plantilla.")


def cmd_caja(a):
    c = Client(); lid, tid = c.default_ids(); real = c.team(lid, tid)["teamMoney"]; me = c.me().get("managerName")
    rows = cash.estimate(c, lid)
    if a.json:
        return _json(rows)
    print(f"{'MÁNAGER':<14}{'GASTADO':>14}{'INGRESADO':>13}{'CAJA ESTIMADA':>16}")
    for r in rows:
        tag = f"  (real: {real:,})" if r["manager"] == me else ""
        print(f"{r['manager']:<14}{r['gastado']:>14,}{r['ingresado']:>13,}{r['caja']:>16,}{tag}")
        for verb, other, amt in r["traspasos"]:
            print(f"    {verb} {other}: {amt:,}")
    print("\nLas subidas de cláusula no salen en el feed: la caja real es igual o menor.")


def cmd_clausulas(a):
    c = Client(); lid, tid = c.default_ids()
    res = clauses.analyze(c, lid, tid)
    if a.json:
        return _json(res)
    print("== Riesgo en tu plantilla ==")
    print(f"  {'JUGADOR':<18}{'POS':<4}{'CLÁUSULA':>12}{'RATIO':>7}{'PJ':>4}{'MIN':>6}{'PTS/P':>7}  CUÁNDO")
    for r in res["mine"]:
        reach = "  a valor: cualquiera puede pagarla" if r["ratio_al_abrir"] <= 1.05 else ""
        print(f"  {r['nombre'][:17]:<18}{r['pos']:<4}{r['clausula']:>12,}"
              f"{r['ratio_al_abrir']:>7.2f}{r['pj']:>4}{r['minutos']:>6}{r['pts_partido']:>7.1f}"
              f"  {r['abre']}{reach}")
    print("\n== Objetivos en plantillas rivales ==")
    for r in res["rivals"]:
        print(f"  {r['nombre']:<18} {r['pos']} de {r['manager']:<12} cláusula {r['clausula']:>11,} ratio {r['ratio_al_abrir']:.2f} {r['abre']}")


def cmd_calendario(a):
    """When each gameweek opens, which is when the lineup freezes."""
    c = Client()
    now = datetime.now(timezone.utc)
    week = c.current_week()
    first_week = int(week.get("weekNumber") or 1)
    rows = []
    for w in range(first_week, first_week + a.jornadas):
        try:
            first, last, n = schedule.window(c.calendar(w))
        except ApiError:
            continue
        rows.append({"jornada": w, "primero": first, "ultimo": last, "partidos": n,
                     "congela_en": schedule.until(first, now),
                     "con_horarios": schedule.scheduled(first, last, n),
                     "en_curso": bool(week.get("isLive")) and w == first_week})
    if a.json:
        return _json(rows)
    print(f"{'JORNADA':<9}{'CONGELA':>18}{'ÚLTIMO PARTIDO':>18}{'PARTIDOS':>10}  FALTAN")
    for r in rows:
        fmt = lambda t: t.astimezone().strftime("%d/%m %H:%M") if t else "?"
        print(f"J{r['jornada']:<8}{fmt(r['primero']):>18}{fmt(r['ultimo']):>18}{r['partidos']:>10}"
              f"  {r['congela_en']}" + ("  <- en curso" if r["en_curso"] else "")
              + ("" if r["con_horarios"] else "  (horarios sin confirmar)"))
    print("\nLa alineación se congela al empezar el primer partido de la jornada y cuenta para todos sus partidos,")
    print("incluidos los aplazados. Solo esos 11 puntúan.")


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
    s = sub.add_parser("mercado", help="qué comprar y por qué no el resto"); s.add_argument("--horizon", type=int, default=7); s.add_argument("--forced", action="store_true", help="valorar la salida como venta forzada por fecha límite"); s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_mercado)
    s = sub.add_parser("historial", help="curva de valor y puntos por jornada"); s.add_argument("jugador"); s.add_argument("--dias", type=int, default=10); s.set_defaults(f=cmd_historial)
    sub.add_parser("trading", help="cartera, realizadas y anuncios").set_defaults(f=cmd_trading)
    s = sub.add_parser("caja", help="caja estimada de cada mánager"); s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_caja)
    s = sub.add_parser("valores", help="qué sube y qué baja hoy en tu plantilla"); s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_valores)
    s = sub.add_parser("rivales", help="caja, tope de gasto y plantilla de cada rival"); s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_rivales)
    s = sub.add_parser("clausulas", help="riesgo propio y objetivos rivales"); s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_clausulas)
    s = sub.add_parser("calendario", help="cuándo se congela la alineación de cada jornada")
    s.add_argument("--jornadas", type=int, default=5); s.add_argument("--json", action="store_true")
    s.set_defaults(f=cmd_calendario)
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
