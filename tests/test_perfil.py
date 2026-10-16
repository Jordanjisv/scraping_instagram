import unittest
from scraper.perfil import extraer_perfil_html, interpretar_cantidad
from scraper.presentacion import metricas_visibles, mostrar_conteo


class PruebasPerfil(unittest.TestCase):
    def test_valor_entero_formato_miles(self):
        self.assertEqual(interpretar_cantidad("1.234"), (1234, False))
        self.assertEqual(interpretar_cantidad("1,234"), (1234, False))

    def test_abreviaturas_aproximadas(self):
        self.assertEqual(interpretar_cantidad("1,2 mil"), (1200, True))
        self.assertEqual(interpretar_cantidad("3.5K"), (3500, True))

    def test_datos_desde_header_y_meta(self):
        html = '''<html><head><meta property="og:title" content="Nombre Académico (@alondra_cgp) • Instagram">
          <meta name="description" content="123 Posts, 1,234 Followers, 56 Following - See Instagram photos">
          </head><body><main><header><span>125 publicaciones 1.250 seguidores 57 seguidos</span>
          <div data-testid="user-profile-bio">Investigación académica y tecnología</div>
          <a href="https://ejemplo.org">Web</a></header></main></body></html>'''
        p = extraer_perfil_html(html, "alondra_cgp")
        self.assertEqual((p["publicaciones"], p["seguidores"], p["seguidos"]), (125, 1250, 57))
        self.assertEqual(p["nombre"], "Nombre Académico")
        self.assertEqual(p["biografia"], "Investigación académica y tecnología")
        self.assertEqual(p["enlaces_externos"], ["https://ejemplo.org"])
        self.assertEqual(p["fuentes"]["seguidores"], "header_visible")

    def test_metadatos_cuando_header_no_tiene_conteos(self):
        html = '<meta name="description" content="16 Posts, 2.5K Followers, 34 Following - Instagram">'
        p = extraer_perfil_html(html, "cuenta_ejemplo")
        self.assertEqual((p["publicaciones"], p["seguidores"], p["seguidos"]), (16, 2500, 34))
        self.assertTrue(p["conteos_aproximados"]["seguidores"])

    def test_cifras_ausentes_no_se_inventan(self):
        p = extraer_perfil_html('<header>Seguir Mensaje</header>', "cuenta_ejemplo")
        self.assertIsNone(p["seguidores"])
        self.assertIsNone(p["publicaciones"])
        self.assertIsNone(p["verificado"])

    def test_no_hacer_equivalentes_reposts_y_visualizaciones(self):
        self.assertEqual(metricas_visibles([{"likes": 2, "comentarios": 0, "reposts": 1, "visualizaciones": None, "alcance": None}]), ["likes", "comentarios", "reposts"])
        self.assertIn("visualizaciones", metricas_visibles([{"visualizaciones": 150}]))

    def test_mostrar_cifras(self):
        self.assertEqual(mostrar_conteo(None), "N/D")
        self.assertEqual(mostrar_conteo(1200, True), "≈ 1,200")
        self.assertEqual(mostrar_conteo(0), "0")

    def test_biografia_no_incluye_historias_destacadas(self):
        html = '''<html><head>
        <meta property="og:title" content="Alondra Enríquez (@alondra_cgp) • Instagram">
        <meta name="description" content='2,595 seguidores, 2,516 siguiendo, 349 publicaciones - Alondra Enríquez (@alondra_cgp) en Instagram: "Esposa, mamá de Camilo y Ami, Socióloga, Consultora 💪🏽 político-Digital 👩🏻‍💻, política guiada en datos 🧡 #Ecuatoriana"'>
        </head><body><main><header>
        <span>alondra_cgp Alondra Enríquez 349 publicaciones 2595 seguidores 2444 seguidos</span>
        <span dir="auto">Alondra Enríquez</span>
        <span dir="auto">Esposa, mamá de Camilo y Ami, Socióloga, Consultora 💪🏽 político-Digital 👩🏻‍💻, política guiada en datos 🧡 #Ecuatoriana</span>
        <span dir="auto">Entrevistas 💙</span><span dir="auto">Eventos Golden🧡</span>
        <span dir="auto">RRSS</span><span dir="auto">Familia❤️</span>
        </header></main></body></html>'''
        p = extraer_perfil_html(html, "alondra_cgp")
        self.assertEqual(p["seguidores"], 2595)
        self.assertEqual(p["seguidos"], 2444)
        self.assertEqual(p["publicaciones"], 349)
        self.assertEqual(p["fuentes"]["seguidos"], "header_visible")
        self.assertEqual(p["fuentes"]["biografia"], "meta_description_biografia")
        self.assertTrue(p["biografia"].startswith("Esposa, mamá de Camilo"))
        self.assertNotIn("Entrevistas", p["biografia"])
        self.assertNotIn("Eventos", p["biografia"])

    def test_biografia_sin_meta_no_unir_resaltadas(self):
        html = '''<main><header>
        <span dir="auto">Usuario Ejemplo</span>
        <span dir="auto">Entrevistas</span><span dir="auto">Familia</span>
        <span dir="auto">Se realizan investigaciones en ingeniería de software y análisis de datos.</span>
        </header></main>'''
        p = extraer_perfil_html(html, "usuario_ejemplo")
        self.assertEqual(
            p["biografia"],
            "Se realizan investigaciones en ingeniería de software y análisis de datos.",
        )

    def test_biografia_ausente_no_compone_historias(self):
        html = '''<main><header><span dir="auto">Eventos</span><span dir="auto">Familia</span></header></main>'''
        p = extraer_perfil_html(html, "usuario_ejemplo")
        self.assertIsNone(p["biografia"])

    def test_biografia_header_explicito_prevalece(self):
        html = '''<html><head><meta name="description" content='45 seguidores, 5 siguiendo, 3 publicaciones - Usuario (@user123) en Instagram: "Bio antigua"'></head>
        <main><header><div data-testid="profile-bio">Bio reciente visible</div></header></main></html>'''
        p = extraer_perfil_html(html, "user123")
        self.assertEqual(p["biografia"], "Bio reciente visible")
        self.assertEqual(p["fuentes"]["biografia"], "header_bio")

    def test_excluir_enlaces_a_instagram(self):
        html = '<main><header><a href="https://instagram.com/otro">Otro</a><a href="https://ejemplo.org/">Web</a></header></main>'
        p = extraer_perfil_html(html, "alondra_cgp")
        self.assertEqual(p["enlaces_externos"], ["https://ejemplo.org/"])


if __name__ == "__main__":
    unittest.main()
