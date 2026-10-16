import unittest

from scraper.metricas import extraer_metricas_html, interpretar_recuentos


class PruebasMetricas(unittest.TestCase):
    def test_recuentos_reales_observados(self):
        texto = '10 likes, 0 comments - cuenta el May 27, 2026: "Texto"'
        self.assertEqual(interpretar_recuentos(texto), (10, 0))

    def test_numeros_con_miles(self):
        self.assertEqual(interpretar_recuentos('1,234 likes, 2,345 comments'), (1234, 2345))
        self.assertEqual(interpretar_recuentos('1.234 likes, 2.345 comments'), (1234, 2345))

    def test_formato_espanol(self):
        self.assertEqual(interpretar_recuentos('23 Me gusta, 5 comentarios'), (23, 5))

    def test_recuentos_ocultos_son_none(self):
        self.assertEqual(interpretar_recuentos('Publicación sin métricas visibles'), (None, None))

    def test_abreviatura_no_se_inventa(self):
        self.assertEqual(interpretar_recuentos('1.2K likes, 9 comments'), (None, None))

    def test_se_extrae_desde_html_con_fuente_y_fechas(self):
        html = '''<html><head><meta property="og:description" content="10 likes, 0 comments - perfil: Texto"></head>
        <body><time datetime="2026-05-27T22:59:38.000Z">27 mayo</time></body></html>'''
        resultado = extraer_metricas_html(html)
        self.assertEqual(resultado['likes'], 10)
        self.assertEqual(resultado['comentarios'], 0)
        self.assertEqual(resultado['fuente_metricas'], 'og:description')
        self.assertEqual(resultado['fechas_html_candidatas'], ['2026-05-27T22:59:38.000Z'])

    def test_no_confundir_ausencia_con_cero(self):
        resultado = extraer_metricas_html('<html><body>Me gusta</body></html>')
        self.assertIsNone(resultado['likes'])
        self.assertIsNone(resultado['comentarios'])
        self.assertIsNone(resultado['fuente_metricas'])


if __name__ == '__main__':
    unittest.main()
