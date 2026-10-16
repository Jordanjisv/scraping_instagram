
import unittest

from scraper.analisis import (
    extraer_hashtags,
    analizar_registros
)


class PruebasAnalisis(unittest.TestCase):

    def test_hashtags_unicode_sin_duplicados(self):
        resultado = extraer_hashtags(
            "#Política #POLÍTICA #IA_2026"
        )

        self.assertEqual(
            resultado,
            ["#política", "#ia_2026"]
        )

    def test_texto_sin_etiquetas(self):
        self.assertEqual(
            extraer_hashtags("Texto sin etiquetas"),
            []
        )

    def test_resumen_con_texto_ausente(self):
        registros = [
            {
                "tipo": "p",
                "texto_alternativo": "Hola #Datos #Ecuador"
            },
            {
                "tipo": "reel",
                "texto_alternativo": "#datos"
            },
            {
                "tipo": "reel",
                "texto_alternativo": ""
            }
        ]

        resultado = analizar_registros(registros)

        self.assertEqual(resultado["total"], 3)
        self.assertEqual(resultado["con_texto"], 2)
        self.assertEqual(
            resultado["porcentaje_con_texto"],
            66.7
        )
        self.assertEqual(
            resultado["tipos"],
            {"p": 1, "reel": 2}
        )
        self.assertEqual(
            resultado["hashtags_frecuentes"][0],
            ("#datos", 2)
        )

    def test_lista_vacia(self):
        resultado = analizar_registros([])

        self.assertEqual(resultado["total"], 0)
        self.assertEqual(
            resultado["promedio_caracteres"],
            0.0
        )
        self.assertEqual(
            resultado["hashtags_frecuentes"],
            []
        )


if __name__ == "__main__":
    unittest.main()
