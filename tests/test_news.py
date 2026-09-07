"""News radar: typed headlines are parsed and matched to players by whole words."""

import unittest
from datetime import datetime

from chuleta.sources import news

HTML = '''
<a href="https://www.futbolfantasy.com/laliga/noticias/149745-x" class="noticia">
  <img src="https://static.futbolfantasy.com/uploads/images/tiponoticia/icono_big_traspaso.png">
  <div class="date"><span class="day">%s</span> <span class="time">22:50</span></div>
  <h2 class="titular">Presa cede y se abre a negociar la salida de Pathé Ciss</h2>
</a>
<a href="https://www.futbolfantasy.com/laliga/noticias/149000-y" class="noticia">
  <div class="date"><span class="day">%s</span> <span class="time">10:00</span></div>
  <h2 class="titular">Lejeune renueva hasta 2028</h2>
</a>
''' % (datetime.now().strftime("%d/%m"), datetime.now().strftime("%d/%m"))


class NewsRadar(unittest.TestCase):
    def test_parse_types_and_titles(self):
        items = news._parse(HTML, "rayo-vallecano")
        self.assertEqual(items[0]["tipo"], "traspaso")
        self.assertIn("Pathé Ciss", items[0]["titular"])
        self.assertEqual(items[1]["tipo"], "general")

    def test_bad_news_matches_player(self):
        news.team_news = lambda slug: news._parse(HTML, slug)
        self.assertEqual(len(news.bad_news_for("Pathé I. Ciss", "Pathe Ciss", "rayo-vallecano")), 1)
        self.assertEqual(news.bad_news_for("Lejeune", "Florian Lejeune", "rayo-vallecano"), [])


if __name__ == "__main__":
    unittest.main()
