import unittest

from scraper.detalles import extraer_detalle_html
from scraper.metricas_ui import extraer_recuentos_ui


def barra(likes="14", comentarios="2", reposts="1", compartir=False):
    # Construida con la estructura observada en el diagnóstico real del usuario.
    vista = (
        '<main><div class="acciones">'
        '<div role="button"><svg aria-label="Me gusta"></svg>Me gusta</div>'
        f'<span>{likes}</span>'
        '<div role="button"><svg aria-label="Comentar"></svg>Comentar</div>'
        f'<span>{comentarios}</span>'
        '<div role="button"><svg aria-label="Republicar"></svg>Republicar</div>'
        f'<span>{reposts}</span>'
        '<div role="button"><svg aria-label="Compartir"></svg>Compartir</div>'
    )
    if compartir:
        vista += '<span>5</span>'
    return vista + '</div></main>'


class TestContadoresAdyacentes(unittest.TestCase):
    def test_estructura_del_diagnostico_reposts_es_uno(self):
        r = extraer_recuentos_ui(barra(), "p")
        self.assertEqual((r["likes"], r["comentarios"], r["reposts"]), (14, 2, 1))
        self.assertIsNone(r["compartidos"])
        self.assertEqual(r["fuentes_ui"]["reposts"], "ui:accion_contador_adyacente")

    def test_no_usa_el_contador_del_boton_anterior_para_compartir(self):
        r = extraer_recuentos_ui(barra(), "p")
        self.assertEqual(r["reposts"], 1)
        self.assertIsNone(r["compartidos"])

    def test_cero_explicito_se_conserva(self):
        r = extraer_recuentos_ui(barra(reposts="0"), "p")
        self.assertEqual(r["reposts"], 0)

    def test_compartidos_tambien_si_tiene_su_propio_contador(self):
        r = extraer_recuentos_ui(barra(compartir=True), "p")
        self.assertEqual(r["compartidos"], 5)
        self.assertEqual(r["reposts"], 1)

    def test_solo_boton_con_numero_no_demuestra_barra_de_interacciones(self):
        html = '<main><div role="button">Republicar</div><span>35</span></main>'
        self.assertIsNone(extraer_recuentos_ui(html, "p")["reposts"])

    def test_no_leer_numero_previsto_del_control_anterior(self):
        html = ('<main><div>'
                '<div role="button">Comentar</div><span>2</span>'
                '<div role="button">Republicar</div>'
                '<div role="button">Compartir</div></div></main>')
        r = extraer_recuentos_ui(html, "p")
        self.assertIsNone(r["reposts"])
        self.assertEqual(r["comentarios"], 2)

    def test_no_inferir_reposts_de_texto_descriptivo(self):
        html = '<main><p>Mis 99 republicaciones ayer</p>' + barra() + '</main>'
        self.assertEqual(extraer_recuentos_ui(html,"p")["reposts"],1)

    def test_no_tomar_una_cifra_de_otro_boton_ambiguo(self):
        html = '<main><button aria-label="Comentario 2435"></button>' + barra() + '</main>'
        r = extraer_recuentos_ui(html, "p")
        self.assertEqual(r["comentarios"], 2)
        self.assertIn(2435, r["conflictos_ui"]["comentarios"])

    def test_dos_barras_con_conteos_distintos_se_marcan_conflicto(self):
        html = '<main>' + barra(reposts="1") + barra(reposts="2") + '</main>'
        r = extraer_recuentos_ui(html, "p")
        self.assertIsNone(r["reposts"])
        self.assertEqual(r["conflictos_ui"]["reposts"], [1, 2])

    def test_parser_completo_transmite_repost_y_fuente(self):
        meta = """<meta property="og:description" content='14 likes, 2 comments - alondra_cgp el May 27, 2026: "Texto"'>"""
        registro = extraer_detalle_html(meta + barra(), "p")
        self.assertEqual(registro["reposts"], 1)
        self.assertEqual(registro["likes"], 14)
        self.assertEqual(registro["comentarios"], 2)
        self.assertEqual(registro["fuentes_por_metrica"]["reposts"], "ui:accion_contador_adyacente")

    def test_dos_barras_con_misma_cantidad_son_consistentes(self):
        html = '<main>' + barra() + barra() + '</main>'
        self.assertEqual(extraer_recuentos_ui(html,"p")["reposts"], 1)


if __name__ == "__main__":
    unittest.main()
