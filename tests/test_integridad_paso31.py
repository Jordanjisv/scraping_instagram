import unittest
from consolidar_resultados_lote import consolidar
from scraper.detalles import extraer_detalle_html

class PruebasIntegracionPaso31(unittest.TestCase):
    def test_metricas_de_reel_se_asocian_a_su_codigo(self):
        url = "https://www.instagram.com/reel/DefIk_UJHIa/"
        otro = "https://www.instagram.com/reel/OTRO/"
        d = extraer_detalle_html('<button aria-label="4 comentarios"></button>', 'reel')
        d.update({"estado": "con_recuentos", "fecha_observacion_utc":"2026-10-16T06:00:00Z"})
        filas = consolidar([{"url": url, "tipo":"reel"}, {"url": otro, "tipo": "reel"}], {url:d}, {})
        self.assertEqual(filas[0]["comentarios"],4)
        self.assertIsNone(filas[1]["comentarios"])
        self.assertIsNone(filas[0]["reposts"])
        self.assertEqual(filas[0]["fuentes_por_metrica"]["comentarios"], "ui:aria-label")

    def test_menciones_para_ranking_por_publicacion(self):
        url = "https://www.instagram.com/p/ABC/"
        filas = consolidar([{"url": url, "tipo":"p", "texto_alternativo":"Hola @ana @luis y @ana #Ecuador #Ecuador"}], {}, {})
        self.assertEqual(filas[0]["cantidad_menciones"],2)
        self.assertEqual(filas[0]["cantidad_hashtags"],1)

    def test_numero_cero_es_dato_y_null_no(self):
        a="https://www.instagram.com/p/ABC/"
        b="https://www.instagram.com/p/DEF/"
        filas = consolidar([{"url":a,"tipo":"p"},{"url":b,"tipo":"p"}], {a:{"comentarios":0}}, {})
        self.assertEqual(filas[0]["comentarios"],0)
        self.assertIsNone(filas[1]["comentarios"])

if __name__ == "__main__":
    unittest.main()
