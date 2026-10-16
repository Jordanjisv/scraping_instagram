import unittest
from scraper.detalles import extraer_detalle_html

class TestMetaSinRecuentos(unittest.TestCase):
    def test_reel_real_sin_cabecera_de_cifras_recupera_fecha_autor_y_caption(self):
        html = '''<meta property="og:description" content='pedroiniguezp el October 14, 2026: "Llega a Quito el Seminario de Comunicación Política @talkcomunicaciones #Quito"'>'''
        dato = extraer_detalle_html(html, "reel")
        self.assertEqual(dato["fecha_publicacion"], "2026-10-14")
        self.assertEqual(dato["autor_declarado"], "pedroiniguezp")
        self.assertIn("Llega a Quito", dato["descripcion_publicacion"])
        self.assertIn("@talkcomunicaciones", dato["menciones"])
        self.assertIsNone(dato["comentarios"])
        self.assertEqual(dato["fuente_fecha_publicacion"], "og:description")

    def test_cabecera_original_con_likes_comentarios_se_conserva(self):
        html = '''<meta property="og:description" content='10 likes, 0 comments - alondra_cgp el May 27, 2026: "Descripción"'>'''
        dato = extraer_detalle_html(html, "p")
        self.assertEqual((dato["likes"], dato["comentarios"]), (10, 0))
        self.assertEqual(dato["autor_declarado"], "alondra_cgp")
        self.assertEqual(dato["fecha_publicacion"], "2026-05-27")

    def test_mencion_de_reposts_en_caption_no_es_recuento(self):
        html = '''<meta name="description" content='pedroiniguezp el October 14, 2026: "Conoce los reposts y los 4 comentarios de ayer"'>'''
        dato = extraer_detalle_html(html, "reel")
        self.assertEqual(dato["fecha_publicacion"], "2026-10-14")
        self.assertIsNone(dato["reposts"])
        self.assertIsNone(dato["comentarios"])

    def test_comentario_4_sin_control_validado_no_es_contador(self):
        html = '''<html><meta name="description" content='pedroiniguezp el October 14, 2026: "Texto"'><span>Comentario 4</span><span>Comentario 2435</span><button aria-label="Republicar"></button></html>'''
        dato = extraer_detalle_html(html, "reel")
        self.assertIsNone(dato["comentarios"])
        self.assertIsNone(dato["reposts"])
        self.assertEqual(dato["fecha_publicacion"], "2026-10-14")

if __name__ == "__main__":
    unittest.main()
