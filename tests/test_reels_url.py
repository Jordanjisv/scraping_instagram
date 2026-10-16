import unittest
from scraper.urls import normalizar_url_publicacion

BASE = "https://www.instagram.com/alondra_cgp/"

class PruebasAliasReels(unittest.TestCase):
    def test_reels_alias_perfil(self):
        self.assertEqual(
            normalizar_url_publicacion("/alondra_cgp/reels/DX9Ml4kB-NI/", BASE),
            "https://www.instagram.com/reel/DX9Ml4kB-NI/"
        )

    def test_reels_alias_normal(self):
        self.assertEqual(
            normalizar_url_publicacion("/reels/DX9Ml4kB-NI/", BASE),
            "https://www.instagram.com/reel/DX9Ml4kB-NI/"
        )

    def test_externo_no_permitido(self):
        self.assertIsNone(normalizar_url_publicacion("https://ejemplo.com/reels/ABC/", BASE))
