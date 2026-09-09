<p align="center"><img src="assets/wordmark.svg" alt="Chuleta" width="560"></p>

# Chuleta 📋⚽

Una mesa de trading para el **LALIGA Fantasy** oficial, desde la terminal.
Lee la API del juego (no oficial) y futbolfantasy.com y te dice, con los datos
sobre la mesa, qué comprar, qué vender, a quién alinear y cuánta caja tienen de
verdad tus rivales.

Solo librería estándar de Python (3.11+). Licencia MIT.

## Qué hace 🔍

| Comando | Qué te da |
|---|---|
| `chuleta mercado` | Todos los jugadores del mercado con el filtro de compra de cuatro patas (tendencia de valor sobre el histórico real de la API, minutos y partidos, probabilidad de titular según la prensa, puntos históricos) y vetos duros: lesionado o sancionado, cayendo fuerte, cayendo sin minutos (traspaso en marcha), descartado por la prensa estando sano, titulares de traspaso o conflicto. |
| `chuleta alinear [--aplicar]` | Mejor XI y formación por **puntos esperados**: P(juega) x puntos por partido x un factor de rival y casa calibrado con tres temporadas completas (ver `research/`). Un jugador que jugó 60+ minutos la última jornada cuenta como titular aunque la prensa aún no lo haya actualizado. |
| `chuleta bajas [club]` | Titulares lesionados o sancionados por club y los compañeros de su posición que van a heredar sus minutos, con su probabilidad en la prensa y si están en el mercado. |
| `chuleta caja` | Caja estimada de cada mánager, reconstruida desde el feed público de actividad. |
| `chuleta clausulas` | Tu exposición a cláusulas y los objetivos en plantillas rivales, con los días que faltan para que abran. |
| `chuleta trading` | Cartera con beneficio latente, ventas realizadas, anuncios y ofertas de la máquina de hoy. |
| `chuleta historial <nombre>` | Curva de valor día a día y puntos por jornada. |
| `chuleta onces <club>` / `chuleta noticias <club>` | Once probable de la prensa y titulares tipados (lesión, traspaso, no disponible). |
| `chuleta sniper armar <marketId> <tope>` / `ver` / `limpiar` / `ejecutar` / `cron` | Francotirador fantasma: puja en los últimos segundos (valor + 10 si nadie puja; tu tope en el último minuto si hay rivales). `cron` lee la hora del ciclo de tu liga y te da la línea de crontab. |
| `chuleta listar <nombre> <precio>` / `retirar` / `acepta --si` / `puja <marketId>` | Actuar. Aceptar una oferta es irreversible y pide confirmación con `--si`. |

## Empezar 🚀

```bash
uv tool install git+https://github.com/Keralin/chuleta   # o: pipx install git+https://github.com/Keralin/chuleta
chuleta login                       # imprime una URL; entra con tu cuenta de Google
chuleta login "authredirect://..."  # pega la URL que el navegador no consigue abrir
chuleta ligas
chuleta mercado
chuleta alinear
```

La sesión y la caché viven en `~/.chuleta` (cámbialo con `CHULETA_HOME`). Si
tienes varias ligas, fija una con `CHULETA_LEAGUE=<id>`.

## Ejemplo 👀

`chuleta mercado` un miércoles cualquiera (los mánagers de la liga van anonimizados):

```
JUGADOR         POS EQUIPO          VENDE          ENTRADA   TEND/D  PROY% 25/26 PJ  MIN MEDIA PROB  VEREDICTO
--------------------------------------------------------------------------------------------------------
Y. Zabiri       DEL R. Racing Club  Manager1      8,150,924 +364,713  +18.3     ?  4  206   5.5  80%  compra
Rafita          DEF Málaga CF       Manager1      6,414,914  +96,923   +4.2     ?  4  337   4.2  70%  neutro
Berenguer       DEL Athletic Club   Manager2    14,953,750 +244,498  -28.2   148  4  234   4.5  50%  neutro
Moi Gómez       MED C.A. Osasuna    Manager1      3,850,301 +220,425  +24.2   104  4  240   6.5   0%  VETO: estado injured; noticia 2026-09-08: Parte médico oficial de Moi Gómez y periodo estimado de baja; noticia 2026-09-07: Moi Gómez se someterá a pruebas este martes y apunta a baja ante el Es
Jon Martin      DEF Real Sociedad   SISTEMA     27,469,625 +207,209   -0.8   112  5  366   3.2   0%  VETO: estado suspended; noticia 2026-09-07: Jon Martín es expulsado en el Martínez Valero y se pierde la jornada 5
Suazo           DEF Sevilla FC      SISTEMA      4,307,631  -44,714   -8.4    94  4  360   2.0  80%  VETO: cayendo fuerte
Iñigo           DEF R. Racing Club  SISTEMA        539,237   -5,749   -9.0     ?  4    0   0.0    ?  VETO: cayendo fuerte
```

`chuleta alinear`:

```
Mejor formación: 4-3-3  (puntos esperados 62.2)

  POR  Ryan                 juega  95%  esperados 8.2
  DEF  Huijsen              juega  70%  esperados 5.6
  DEF  Xavi Espart          juega  50%  esperados 5.2
  DEF  Rafita               juega  70%  esperados 2.7
  DEF  Javi Rodríguez       juega  50%  esperados 1.2
  MED  Fermín               juega  50%  esperados 8.3
  MED  Ibañez               juega  90%  esperados 6.7
  MED  Blanco               juega  90%  esperados 5.3
  DEL  Lucas Boyé           juega  90%  esperados 8.8
  DEL  Mariano              juega  60%  esperados 5.8 [jugó la última]
  DEL  Miguel Sierra        juega  70%  esperados 4.4

Banquillo: Agirrezabala, Moi Gómez, Y. Zabiri, Dolan
(propuesta; añade --aplicar para guardarla)
```

## Mecánicas del juego en las que se apoya

Los valores se actualizan cada día a las 00:15 (Madrid). Las subastas y las
ofertas de la máquina se resuelven una vez al día a una hora que depende de
cuándo se creó TU liga (cada liga tiene su ciclo; el instante exacto es el
`expirationDate` de cada anuncio). Una puja debe ser al menos el valor actual
del jugador. La máquina ofrece entre el 90% y el 110% del valor por cada anuncio
en cada ciclo, pidas lo que pidas. El XI guardado antes del primer partido de la
jornada puntúa toda la jornada. La cláusula tiene como suelo el valor de mercado
mientras está bloqueada; subirla cuesta el 50% del incremento. La puja máxima es
la caja más el 20% del valor de la plantilla, y un saldo negativo al empezar la
jornada puntúa cero. Cada mánager cobra 100.000 € por punto de jornada.

## Lo que dicen los datos 📊

`research/` guarda los scrapers y las conclusiones de tres temporadas de puntos
por jugador y partido (2023/24 a 2025/26): ganar vale 7,1 puntos por titular,
empatar 5,1, perder 2,8; la fuerza del rival cuesta ~22% por gol de diferencia;
y un backtest cruzado enseña por qué el modelo de alineación pondera el rival a
un cuarto de su efecto medido. Los datos raspados no se redistribuyen; los
scrapers sí.

## Gracias

A Jon Ortega y su [fantasybot](https://github.com/jonortega20/fantasybot): fue
la chispa para meternos con LALIGA Fantasy desde la terminal y la referencia
para entender cómo se habla con el juego. Chuleta creció a partir de esa idea
hacia el lado del mercado: los flips, los vetos, la caja de los rivales y el
francotirador. Si te gusta esto, pásate también por su repo.

Y a La liga friki, los cuatro colegas con los que se ha probado cada comando
a golpe de puja real 🍺

---

## English

Chuleta is a command-line trading desk for the official **LALIGA Fantasy**
game. It reads the game's (unofficial) API and futbolfantasy.com and tells
you, with the data on the table, what to buy, what to sell, who to line up
and how much cash your rivals really have. Standard library only, Python
3.11+, MIT.

- `chuleta mercado`: market screening with a four-leg buy filter (value trend
  on the API's real history, minutes, press starting odds, historic points) and
  hard vetoes (injured or suspended, falling hard, falling with zero minutes,
  press-dropped while fit, transfer or conflict headlines).
- `chuleta alinear [--aplicar]`: best XI by expected points, P(plays) x points
  per game x a fixture factor calibrated on three full seasons.
- `chuleta bajas [club]`: injured or suspended starters and the teammates set
  to inherit their minutes.
- `chuleta caja`, `clausulas`, `trading`, `historial`, `onces`, `noticias`:
  rival cash from the activity feed, clause exposure and targets, ledger, value
  curves, probable XIs, typed headlines.
- `chuleta sniper armar|ver|limpiar|ejecutar|cron`: ghost-mode sniper that bids
  in the last seconds (value + 10 alone, your cap in the last minute when
  contested); `cron` reads your league's cycle time and prints the crontab line.
- `chuleta listar` / `retirar` / `acepta --si` / `puja`: act; accepting an
  offer is irreversible and asks for `--si`.

Quick start: `uv tool install git+https://github.com/Keralin/chuleta` (or `pipx install ...`), `chuleta login` (Google sign-in, two steps),
`chuleta ligas`, `chuleta mercado`. Session and cache live in `~/.chuleta`
(`CHULETA_HOME`); pin a league with `CHULETA_LEAGUE=<id>`.

Auctions resolve once a day at a time set by your league's creation time (each
listing's `expirationDate`). A bid must be at least the current value; the
machine offers 90-110% of value per listing per cycle; the maximum bid is cash
plus 20% of squad value; a negative balance at kick-off scores zero; every
manager earns 100,000 EUR per gameweek point. See `research/README.md` for the
three-season study behind the lineup model. Reports are in Spanish; code and
comments in English.

Thanks to Jon Ortega and his [fantasybot](https://github.com/jonortega20/fantasybot),
the spark for driving LALIGA Fantasy from a terminal; Chuleta grew from that
idea towards the market side of the game.
