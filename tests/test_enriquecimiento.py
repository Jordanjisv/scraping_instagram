import unittest

from scraper.enriquecimiento import (
    enriquecer_registros,
    extraer_hashtags_y_menciones,
)


class PruebasEnriquecimiento(unittest.TestCase):
    def test_etiquetas_y_menciones(self):
        hashtags, menciones = extraer_hashtags_y_menciones(
            "Hola #Ecuador #ECUADOR @Cuenta.Uno y @otra_cuenta"
        )
        self.assertEqual(hashtags, ["#ecuador"])
        self.assertEqual(menciones, ["@cuenta.uno", "@otra_cuenta"])

    def test_no_captura_arroba_de_email(self):
        _, menciones = extraer_hashtags_y_menciones("contacto@example.com")
        self.assertEqual(menciones, [])

    def test_metricas_se_asocian_unicamente_a_su_url(self):
        posts = [
            {"url": "u1", "tipo": "p", "texto_alternativo": "Hola #Demo"},
            {"url": "u2", "tipo": "reel", "texto_alternativo": "Hey @Cuenta"},
        ]
        metricas = {"u1": {"likes": 10, "comentarios": 0, "fuente_metricas": "og:description"}}
        resultado = enriquecer_registros(posts, metricas)
        self.assertEqual((resultado[0]["likes"], resultado[0]["comentarios"]), (10, 0))
        self.assertIsNone(resultado[1]["likes"])
        self.assertIsNone(resultado[1]["comentarios"])
        self.assertIsNone(resultado[1]["visualizaciones"])
        self.assertEqual(resultado[0]["estado_metricas"], "verificado")
        self.assertEqual(resultado[1]["estado_metricas"], "sin_verificar")

    def test_views_solo_cuando_hay_dato_numerico(self):
        posts = [{"url": "u1", "tipo": "reel", "texto_alternativo": ""}]
        metricas = {"u1": {"visualizaciones": 150}}
        resultado = enriquecer_registros(posts, metricas)
        self.assertEqual(resultado[0]["visualizaciones"], 150)
        self.assertEqual(resultado[0]["estado_metricas"], "parcial")
        self.assertIsNone(resultado[0]["alcance"])

    def test_metrica_invalida_no_se_inventa(self):
        posts = [{"url": "u1", "tipo": "p", "texto_alternativo": ""}]
        resultado = enriquecer_registros(posts, {"u1": {"likes": "10", "comentarios": True}})
        self.assertIsNone(resultado[0]["likes"])
        self.assertIsNone(resultado[0]["comentarios"])

    def test_rechaza_urls_duplicadas(self):
        posts = [{"url": "u1"}, {"url": "u1"}]
        with self.assertRaises(ValueError):
            enriquecer_registros(posts, {})


if __name__ == "__main__":
    unittest.main()
