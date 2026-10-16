import unittest
from procesar_publicaciones_lote import redireccion_equivalente, clasificar_vinculo
from consolidar_resultados_lote import consolidar


class PruebasCorreccionesLote(unittest.TestCase):
    def test_reel_plural_equivalente(self):
        self.assertTrue(redireccion_equivalente(
            "https://www.instagram.com/reel/DX9Ml4kB-NI/",
            "https://www.instagram.com/reels/DX9Ml4kB-NI/",
        ))

    def test_rechazar_otro_identificador(self):
        self.assertFalse(redireccion_equivalente(
            "https://www.instagram.com/reel/AAA/",
            "https://www.instagram.com/reels/BBB/",
        ))

    def test_rechazar_dominio_ajeno(self):
        self.assertFalse(redireccion_equivalente(
            "https://www.instagram.com/reel/AAA/",
            "https://instagram.com.ejemplo.org/reels/AAA/",
        ))

    def test_rechazar_login(self):
        self.assertFalse(redireccion_equivalente(
            "https://www.instagram.com/reel/AAA/",
            "https://www.instagram.com/accounts/login/",
        ))

    def test_mencion_no_es_coautoria(self):
        self.assertEqual(clasificar_vinculo("alondra_cgp", "oime_ecuador", ["@alondra_cgp"]), "perfil_mencionado")
        self.assertEqual(clasificar_vinculo("alondra_cgp", "oime_ecuador", []), "contenido_de_otro_autor")
        self.assertEqual(clasificar_vinculo("alondra_cgp", "alondra_cgp", []), "autor_principal")

    def test_consolidar_con_tercero_no_borra_metricas(self):
        url = "https://www.instagram.com/p/AAA/"
        base = [{
            "url": url, "tipo": "p", "perfil_consultado": "alondra_cgp",
            "texto_alternativo": "Texto alternativo #Tema @alondra_cgp",
        }]
        detalles = {url: {
            "autor_declarado": "oime_ecuador", "estado": "otro_autor_con_recuentos",
            "descripcion_publicacion": "Mención @alondra_cgp #Tema", "likes": 15,
            "comentarios": 0, "fecha_publicacion": "2026-05-27",
            "vinculo_perfil": "perfil_mencionado", "reposts": 2,
        }}
        fila = consolidar(base, detalles, {})[0]
        self.assertEqual(fila["likes"], 15)
        self.assertEqual(fila["comentarios"], 0)
        self.assertEqual(fila["reposts"], 2)
        self.assertEqual(fila["vinculo_perfil"], "perfil_mencionado")
        self.assertIsNone(fila["colaboracion_confirmada"])
        self.assertEqual(fila["fecha_publicacion"], "2026-05-27")
        self.assertEqual(fila["fuente_texto_mostrado"], "descripcion_publicacion")

    def test_alt_como_fallback_y_valores_desconocidos(self):
        url = "https://www.instagram.com/reel/AAA/"
        fila = consolidar([{
            "url": url, "tipo": "reel", "perfil_consultado": "alondra_cgp",
            "texto_alternativo": "Alt disponible #Video",
        }], {}, {})[0]
        self.assertIsNone(fila["descripcion_publicacion"])
        self.assertEqual(fila["descripcion_para_mostrar"], "Alt disponible #Video")
        self.assertEqual(fila["fuente_texto_mostrado"], "texto_alternativo")
        self.assertIsNone(fila["likes"])
        self.assertIsNone(fila["visualizaciones"])
        self.assertIsNone(fila["reposts"])
        self.assertIsNone(fila["alcance"])


if __name__ == "__main__":
    unittest.main()
