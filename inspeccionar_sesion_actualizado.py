import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from scraper.desplazamiento import desplazar_hasta_objetivo
from scraper.urls import normalizar_url_publicacion

URL = "https://www.instagram.com/alondra_cgp/"
PERFIL = Path.home() / "InstagramScraper" / "ChromeProfile"
OBJETIVO = 50
MAX_DESPLAZAMIENTOS = 12


def obtener_urls_visibles(pagina, textos_alt):
    """Lee enlaces y alt del HTML actual sin visitar cada publicación."""
    sopa = BeautifulSoup(pagina.content(), "html.parser")
    urls = set()

    for enlace in sopa.select("a[href]"):
        url_normalizada = normalizar_url_publicacion(enlace["href"], URL)
        if url_normalizada is None:
            continue

        urls.add(url_normalizada)
        imagen = enlace.select_one("img[alt]")
        if imagen is not None:
            texto = imagen.get("alt", "").strip()
            if texto and not textos_alt.get(url_normalizada):
                textos_alt[url_normalizada] = texto

    return urls


def main():
    PERFIL.mkdir(parents=True, exist_ok=True)
    textos_alt = {}

    with sync_playwright() as p:
        contexto = p.chromium.launch_persistent_context(
            user_data_dir=str(PERFIL),
            channel="chrome",
            headless=False,
        )

        try:
            pagina = contexto.new_page()
            respuesta = pagina.goto(
                URL,
                wait_until="domcontentloaded",
                timeout=45000,
            )
            pagina.locator("body").wait_for(state="visible")

            print("Estado HTTP:", respuesta.status if respuesta else "Sin respuesta")
            print("URL final:", pagina.url)

            pagina.mouse.move(450, 350)
            iniciales = obtener_urls_visibles(pagina, textos_alt)
            print("Publicaciones inicialmente visibles:", len(iniciales))
            print("Iniciando desplazamiento automático controlado...")

            urls = desplazar_hasta_objetivo(
                pagina,
                lambda p_actual: obtener_urls_visibles(p_actual, textos_alt),
                objetivo=OBJETIVO,
                max_desplazamientos=MAX_DESPLAZAMIENTOS,
                max_sin_cambios=3,
            )

            sopa_final = BeautifulSoup(pagina.content(), "html.parser")
            print("Enlaces HTML al finalizar:", len(sopa_final.select("a[href]")))
            print("Imágenes HTML al finalizar:", len(sopa_final.select("img")))

            print("\n--- RESULTADOS ---")
            print("Publicaciones únicas encontradas:", len(urls))
            for numero, url in enumerate(urls[:25], start=1):
                print(f"{numero}. {url}")

            fecha = datetime.now(timezone.utc).isoformat(timespec="seconds")
            registros = []
            for url in urls:
                tipo, codigo = urlsplit(url).path.strip("/").split("/")
                registros.append({
                    "perfil_consultado": "alondra_cgp",
                    "tipo": tipo,
                    "codigo": codigo,
                    "url": url,
                    "fecha_observacion_utc": fecha,
                    "texto_alternativo": textos_alt.get(url, ""),
                })

            columnas = [
                "perfil_consultado",
                "tipo",
                "codigo",
                "url",
                "fecha_observacion_utc",
                "texto_alternativo",
            ]

            carpeta = Path(__file__).resolve().parent / "resultados"
            carpeta.mkdir(exist_ok=True)
            ruta_json = carpeta / "enlaces_publicaciones.json"
            ruta_csv = carpeta / "enlaces_publicaciones.csv"

            ruta_json.write_text(
                json.dumps(registros, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            with ruta_csv.open("w", encoding="utf-8-sig", newline="") as archivo:
                escritor = csv.DictWriter(archivo, fieldnames=columnas)
                escritor.writeheader()
                escritor.writerows(registros)

            print("\n--- EXPORTACIÓN ---")
            print("Registros guardados:", len(registros))
            print(
                "Publicaciones con texto alternativo:",
                sum(bool(registro["texto_alternativo"]) for registro in registros),
            )
            print("JSON:", ruta_json)
            print("CSV:", ruta_csv)
            print("Inspección finalizada correctamente.")
        finally:
            contexto.close()


if __name__ == "__main__":
    main()
