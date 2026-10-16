
import unittest
from scraper.desplazamiento import desplazar_hasta_objetivo


class PaginaFalsa:
    def __init__(self, estados):
        self.estados = estados
        self.indice = 0
        self.pasos = 0
        self.mouse = self

    def wheel(self, dx, dy):
        self.pasos += 1
        self.indice = min(
            self.indice + 1,
            len(self.estados) - 1
        )

    def wait_for_timeout(self, ms):
        pass

    def urls_visibles(self):
        return self.estados[self.indice]


class PruebasDesplazamiento(unittest.TestCase):

    def test_se_detiene_al_llegar_al_objetivo(self):
        pagina = PaginaFalsa([
            {"a"},
            {"a", "b"},
            {"a", "b", "c"}
        ])

        urls = desplazar_hasta_objetivo(
            pagina,
            lambda p: p.urls_visibles(),
            objetivo=3
        )

        self.assertEqual(urls, ["a", "b", "c"])
        self.assertEqual(pagina.pasos, 2)

    def test_se_detiene_si_no_hay_cambios(self):
        pagina = PaginaFalsa([
            {"a"},
            {"a"},
            {"a"},
            {"a", "b"}
        ])

        urls = desplazar_hasta_objetivo(
            pagina,
            lambda p: p.urls_visibles(),
            objetivo=10,
            max_sin_cambios=2
        )

        self.assertEqual(urls, ["a"])
        self.assertEqual(pagina.pasos, 2)

    def test_respeta_el_maximo_de_desplazamientos(self):
        pagina = PaginaFalsa([
            {"a"},
            {"a", "b"},
            {"a", "b", "c"}
        ])

        urls = desplazar_hasta_objetivo(
            pagina,
            lambda p: p.urls_visibles(),
            objetivo=10,
            max_desplazamientos=1
        )

        self.assertEqual(urls, ["a", "b"])
        self.assertEqual(pagina.pasos, 1)

    def test_no_desplaza_si_cumple_objetivo_desde_inicio(self):
        pagina = PaginaFalsa([
            {"a", "b"}
        ])

        urls = desplazar_hasta_objetivo(
            pagina,
            lambda p: p.urls_visibles(),
            objetivo=2
        )

        self.assertEqual(urls, ["a", "b"])
        self.assertEqual(pagina.pasos, 0)


if __name__ == "__main__":
    unittest.main()
