import unittest
from scraper.metricas_ui import extraer_recuentos_ui
from scraper.detalles import extraer_detalle_html

class PruebasMetricasUI(unittest.TestCase):
    def test_comentarios_en_etiqueta_aria(self):
        html = '<button aria-label="Ver los 4 comentarios">Ver comentarios</button>'
        self.assertEqual(extraer_recuentos_ui(html, "reel")["comentarios"], 4)

    def test_reposts_y_compartidos_explicitos(self):
        html = '<button aria-label="5 reposts"></button><button title="3 compartidos"></button>'
        r = extraer_recuentos_ui(html, "reel")
        self.assertEqual((r["reposts"],r["compartidos"]),(5,3))

    def test_repostear_no_implica_numero(self):
        html = '<button aria-label="Repostear">Repostear</button>'
        self.assertIsNone(extraer_recuentos_ui(html,"reel")["reposts"])

    def test_prosa_no_es_contador(self):
        html = '<article><p>Celebramos los 4 comentarios y 30 reposts</p></article>'
        r = extraer_recuentos_ui(html,"reel")
        self.assertIsNone(r["comentarios"])
        self.assertIsNone(r["reposts"])

    def test_numero_con_icono_svg_comentar(self):
        html = '<button><svg aria-label="Comentar"></svg><span>4</span></button>'
        self.assertEqual(extraer_recuentos_ui(html,"reel")["comentarios"],4)

    def test_icono_sin_numero_no_infiere(self):
        html = '<button><svg aria-label="Repostear"></svg></button>'
        self.assertIsNone(extraer_recuentos_ui(html,"reel")["reposts"])

    def test_vistas_solo_en_reel(self):
        html = '<button aria-label="123 visualizaciones"></button>'
        self.assertIsNone(extraer_recuentos_ui(html,"p")["visualizaciones"])
        self.assertEqual(extraer_recuentos_ui(html,"reel")["visualizaciones"],123)

    def test_dos_numeros_contradictorios_no_se_inventa(self):
        html = '<button aria-label="4 comentarios"></button><button aria-label="7 comentarios"></button>'
        r = extraer_recuentos_ui(html,"reel")
        self.assertIsNone(r["comentarios"])
        self.assertEqual(r["conflictos_ui"]["comentarios"], [4,7])

    def test_meta_ausente_usa_ui(self):
        html = '<html><body><button aria-label="4 comentarios"></button><button aria-label="3 reposts"></button></body></html>'
        d = extraer_detalle_html(html,"reel")
        self.assertEqual((d["comentarios"],d["reposts"]),(4,3))
        self.assertEqual(d["fuentes_por_metrica"]["comentarios"],"ui:aria-label")
        self.assertIsNone(d["likes"])

    def test_meta_conteos_presentes_prioridad_y_conflicto(self):
        html = '''<meta property="og:description" content='8 likes, 0 comments - perfil el May 27, 2026: "Caption"'><button aria-label="4 comentarios"></button>'''
        d = extraer_detalle_html(html,"reel")
        self.assertEqual(d["comentarios"],0)
        self.assertEqual(d["conflictos_metricas"]["comentarios"],[0,4])

if __name__ == "__main__":
    unittest.main()
