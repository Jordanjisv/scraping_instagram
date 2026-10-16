
import unittest
from scraper.urls import normalizar_url_publicacion

BASE = "https://www.instagram.com/alondra_cgp/"


class PruebasURLs(unittest.TestCase):

    def test_publicacion_con_usuario(self):
        resultado = normalizar_url_publicacion(
            "/alondra_cgp/p/ABC123/", BASE
        )
        self.assertEqual(
            resultado,
            "https://www.instagram.com/p/ABC123/"
        )

    def test_reel_sin_usuario(self):
        resultado = normalizar_url_publicacion(
            "/reel/XYZ_123/", BASE
        )
        self.assertEqual(
            resultado,
            "https://www.instagram.com/reel/XYZ_123/"
        )

    def test_parametros_no_duplican_url(self):
        resultado = normalizar_url_publicacion(
            "/otra/reel/CODIGO/?igsh=demo", BASE
        )
        self.assertEqual(
            resultado,
            "https://www.instagram.com/reel/CODIGO/"
        )

    def test_historia_no_es_publicacion(self):
        self.assertIsNone(
            normalizar_url_publicacion(
                "/stories/highlights/123/", BASE
            )
        )

    def test_dominio_ajeno_se_descarta(self):
        self.assertIsNone(
            normalizar_url_publicacion(
                "https://ejemplo.com/p/ABC123/", BASE
            )
        )

    def test_ruta_no_valida_se_descarta(self):
        self.assertIsNone(
            normalizar_url_publicacion(
                "/alondra_cgp/", BASE
            )
        )


if __name__ == "__main__":
    unittest.main()
