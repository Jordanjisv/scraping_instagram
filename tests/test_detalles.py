import unittest
from scraper.detalles import extraer_detalle_html


class PruebasDetalles(unittest.TestCase):
    def test_meta_real_10_y_0(self):
        html = '''<html><head><meta property="og:description"
        content='10 likes, 0 comments - alondra_cgp el May 27, 2026: "Texto #Ecuador @amigo"'></head>
        <body><time datetime="2026-05-27T22:59:38.000Z"></time>
        <time datetime="2026-05-27T22:59:37.000Z"></time></body></html>'''
        info = extraer_detalle_html(html, "p")
        self.assertEqual((info["likes"], info["comentarios"]), (10, 0))
        self.assertEqual(info["fecha_publicacion"], "2026-05-27")
        self.assertEqual(info["autor_declarado"], "alondra_cgp")
        self.assertEqual(info["hashtags"], ["#ecuador"])
        self.assertEqual(info["menciones"], ["@amigo"])
        self.assertEqual(info["descripcion_publicacion"], "Texto #Ecuador @amigo")

    def test_reel_con_visualizaciones_explicitas(self):
        html = '''<meta property="og:description" content='1,234 views, 100 likes, 8 comments - alondra_cgp on Oct 1, 2026: "Reel #Video"'>'''
        info = extraer_detalle_html(html, "reel")
        self.assertEqual((info["likes"], info["comentarios"], info["visualizaciones"]), (100, 8, 1234))
        self.assertEqual(info["fuente_metricas"], "og:description")
        self.assertIsNone(info["alcance"])

    def test_sin_metricas_no_es_cero(self):
        info = extraer_detalle_html("<html><body>Me gusta</body></html>", "p", "Texto #Dato")
        self.assertIsNone(info["likes"])
        self.assertIsNone(info["comentarios"])
        self.assertIsNone(info["visualizaciones"])
        self.assertEqual(info["hashtags"], ["#dato"])
        self.assertIsNone(info["descripcion_publicacion"])

    def test_no_inferir_vistas_en_caption(self):
        html = '''<meta property="og:description" content='30 likes, 2 comments - alondra_cgp on May 1, 2026: "Logramos 5000 views en la campaña"'>'''
        info = extraer_detalle_html(html, "reel")
        self.assertIsNone(info["visualizaciones"])

    def test_no_aplicar_vistas_a_post(self):
        html = '''<meta name="description" content='500 views, 30 likes, 2 comments - alondra_cgp on May 1, 2026: "Texto"'>'''
        info = extraer_detalle_html(html, "p")
        self.assertIsNone(info["visualizaciones"])

    def test_fecha_meta_prioridad_sobre_fechas_de_comentarios(self):
        html = '''<meta name="description" content='1 likes, 1 comments - alondra_cgp on May 1, 2026: "Texto"'><time datetime="2026-05-01T00:00:00Z"></time><time datetime="2026-06-01T00:00:00Z"></time>'''
        self.assertEqual(extraer_detalle_html(html, "p")["fecha_publicacion"], "2026-05-01")

    def test_reposts_y_compartidos_explicitos(self):
        html = '''<meta property="og:description" content='10 likes, 1 comments, 7 reposts, 11 shares - alondra_cgp el May 27, 2026: "Texto #Prueba"'>'''
        info = extraer_detalle_html(html, "p")
        self.assertEqual((info["reposts"], info["compartidos"]), (7, 11))
        self.assertEqual(info["fuente_fecha_publicacion"], "og:description")

    def test_no_inferir_reposts_del_caption(self):
        html = '''<meta property="og:description" content='10 likes, 1 comments - alondra_cgp on May 27, 2026: "Nuestro video logró 400 reposts y 1000 shares"'>'''
        info = extraer_detalle_html(html, "p")
        self.assertIsNone(info["reposts"])
        self.assertIsNone(info["compartidos"])

    def test_fecha_mismo_dia_time(self):
        html = '''<html><time datetime="2026-05-27T22:59:38.000Z"></time><time datetime="2026-05-27T22:59:37.000Z"></time></html>'''
        info = extraer_detalle_html(html, "p")
        self.assertEqual(info["fecha_publicacion"], "2026-05-27")
        self.assertEqual(info["fuente_fecha_publicacion"], "time[datetime]")

    def test_fecha_html_ambigua_sin_meta_no_se_adivina(self):
        html = '''<html><time datetime="2026-05-27T22:59:38.000Z"></time><time datetime="2026-06-01T12:00:00Z"></time></html>'''
        self.assertIsNone(extraer_detalle_html(html, "p")["fecha_publicacion"])

    def test_no_convierte_notacion_k_sin_verificar(self):
        html = '''<meta name="description" content='1.2K views, 2.4K likes, 3 comments - alondra_cgp on May 1, 2026: "Texto"'>'''
        info = extraer_detalle_html(html, "reel")
        self.assertIsNone(info["visualizaciones"])
        self.assertIsNone(info["likes"])
        self.assertEqual(info["comentarios"], 3)


if __name__ == "__main__":
    unittest.main()
