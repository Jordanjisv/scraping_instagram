"""Consulta secuencialmente publicaciones autorizadas usando Chrome y HTML.

No usa API de Instagram/Meta ni endpoints internos. No evita bloqueos.
Guardar en la raíz del proyecto scraping-instagram.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from scraper.detalles import extraer_detalle_html
from scraper.urls import normalizar_url_publicacion
from scraper.metricas_ui import extraer_recuentos_ui
from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parent
RESULTADOS = BASE / "resultados"
RUTA_ENLACES = RESULTADOS / "enlaces_publicaciones.json"
RUTA_DETALLES = RESULTADOS / "detalles_publicaciones.json"
RUTA_METRICAS = RESULTADOS / "metricas_verificadas.json"
PERFIL_CHROME = Path("D:/PlaywrightProfiles/InstagramPractica")


def cargar_json(ruta: Path, defecto):
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else defecto


def guardar_json(ruta: Path, datos) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    temporal.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    temporal.replace(ruta)


def es_url_publicacion(url: str) -> bool:
    try:
        partes = urlsplit(url)
    except (ValueError, TypeError):
        return False
    return (
        partes.scheme == "https"
        and partes.hostname in {"instagram.com", "www.instagram.com"}
        and bool(re.fullmatch(r"/(?:p|reel)/[A-Za-z0-9_-]+/?", partes.path))
    )


def redireccion_equivalente(url_solicitada: str, url_final: str) -> bool:
    """Solo acepta /reel/CODIGO/ -> /reels/CODIGO/ en Instagram.

    No admite un shortcode distinto, dominios extraños ni páginas de acceso.
    """
    original, final = urlsplit(url_solicitada), urlsplit(url_final)
    if final.scheme != "https" or final.hostname not in {"instagram.com", "www.instagram.com"}:
        return False
    partes_orig = [parte for parte in original.path.split("/") if parte]
    partes_final = [parte for parte in final.path.split("/") if parte]
    if len(partes_orig) != 2 or len(partes_final) != 2:
        return False
    tipo_orig, codigo_orig = partes_orig
    tipo_final, codigo_final = partes_final
    return (codigo_orig == codigo_final and
            (tipo_orig == tipo_final or
             (tipo_orig == "reel" and tipo_final == "reels")))


def clasificar_vinculo(perfil: str | None, autor: str | None, menciones: list[str]) -> str:
    """Una mención no demuestra una publicación colaborativa."""
    if not perfil or not autor:
        return "no_determinado"
    if perfil.casefold() == autor.casefold():
        return "autor_principal"
    if f"@{perfil.casefold()}" in (menciones or []):
        return "perfil_mencionado"
    return "contenido_de_otro_autor"


def detener_por_restriccion(url_actual: str, estado_http: int | None) -> bool:
    if estado_http in {401, 403, 429}:
        return True
    ruta = urlsplit(url_actual).path.lower()
    return any(
        palabra in ruta
        for palabra in ("/challenge/", "/accounts/login/", "/checkpoint/", "/suspended/")
    )


def diagnostico_html(html: str, tipo: str) -> None:
    """Imprime pistas acotadas del DOM, sin guardar el HTML ni identidades de comentadores."""
    sopa = BeautifulSoup(html, "html.parser")
    print("--- DIAGNÓSTICO HTML LIMITADO ---")
    for selector in ('meta[property="og:description"]', 'meta[name="description"]'):
        meta = sopa.select_one(selector)
        valor = meta.get("content", "") if meta else ""
        print(selector, ":", valor[:180] if valor else "[ausente]")
    ui = extraer_recuentos_ui(html, tipo)
    print("Recuentos identificados en controles:", {
        k: ui[k] for k in ("likes", "comentarios", "reposts", "compartidos", "visualizaciones")
    })
    print("Fuentes de controles:", ui["fuentes_ui"])
    print("Conflictos entre controles:", ui["conflictos_ui"])
    claves = ("coment", "repost", "republic", "reposte", "compart", "share", "view", "visualiza")
    encontrados = set()
    print("Controles relevantes (máximo 15; sin comentarios individuales):")
    for tag in sopa.select('button, [role="button"], [aria-label], [title]'):
        valores = [tag.get("aria-label", ""), tag.get("title", "")]
        if tag.name == "button" or tag.get("role") == "button":
            valores.append(tag.get_text(" ", strip=True)[:90])
        for valor in valores:
            if not isinstance(valor, str):
                continue
            txt = " ".join(valor.split())[:120]
            if txt and len(txt) <= 120 and any(clave in txt.casefold() for clave in claves):
                if txt not in encontrados:
                    print("  •", txt)
                    encontrados.add(txt)
                if len(encontrados) >= 15:
                    break
        if len(encontrados) >= 15:
            break
    if not encontrados:
        print("  [No se encontraron controles relevantes]")
    # Diagnóstico estructural de los controles ambiguos del reel reportado.
    # Solo revela etiquetas y estructura DOM, NO nombres ni texto de comentarios.
    print("Estructura de controles con posibles recuentos (máximo 8):")
    revisados = set()
    total = 0
    for tag in sopa.select('button, [role="button"], [aria-label], [title]'):
        if total >= 8:
            break
        pares = [("aria-label", tag.get("aria-label", "")),
                 ("title", tag.get("title", ""))]
        if tag.name == "button" or tag.get("role") == "button":
            pares.append(("texto_control", tag.get_text(" ", strip=True)))
        for fuente, valor in pares:
            if not isinstance(valor, str):
                continue
            corto = " ".join(valor.split())
            # No imprimir contenidos largos ni cuerpos de comentarios.
            if not re.fullmatch(r"(?i)(?:comentarios?|comments?|republicar|repostear|reposts?)\s*\d{0,6}", corto):
                continue
            clave = (id(tag), fuente, corto)
            if clave in revisados:
                continue
            revisados.add(clave)
            control = tag if (tag.name == "button" or tag.get("role") == "button") else tag.find_parent(["button", "a"])
            print("  - etiqueta:", corto[:40], "| origen:", fuente,
                  "| elemento:", tag.name, "| rol:", tag.get("role", "[ninguno]"),
                  "| control_padre:", control.name if control else "[ninguno]",
                  "| longitud_texto:", len(tag.get_text(" ", strip=True)))
            total += 1
            if total >= 8:
                break
    if not total:
        print("  [No se encontraron etiquetas cortas para diagnóstico estructural]")
    print("--- FIN DIAGNÓSTICO ---")


def procesar_enlaces(limite: int, pausa: float, reprocesar: bool,
                     reprocesar_ajenos: bool = False, solo_url: str | None = None,
                     diagnostico: bool = False, reintentar_errores: bool = False) -> None:
    if not RUTA_ENLACES.is_file():
        raise FileNotFoundError(f"Antes debes generar los enlaces: {RUTA_ENLACES}")

    entradas = cargar_json(RUTA_ENLACES, [])
    if not isinstance(entradas, list):
        raise ValueError("enlaces_publicaciones.json debe contener una lista")

    detalles = cargar_json(RUTA_DETALLES, {})
    metricas = cargar_json(RUTA_METRICAS, {})
    if not isinstance(detalles, dict) or not isinstance(metricas, dict):
        raise ValueError("Los archivos de detalles y métricas deben contener objetos por URL")

    entradas_validas = []
    visto = set()
    for fila in entradas:
        url = fila.get("url") if isinstance(fila, dict) else None
        if not es_url_publicacion(url):
            print("Omitida URL inválida o ajena:", url)
            continue
        if url in visto:
            continue
        visto.add(url)
        entradas_validas.append(fila)

    if solo_url:
        normalizada = normalizar_url_publicacion(solo_url, "https://www.instagram.com/")
        if not normalizada or normalizada not in visto:
            raise ValueError("--solo-url debe existir en enlaces_publicaciones.json")
        pendientes = [fila for fila in entradas_validas if fila["url"] == normalizada]
    else:
        pendientes = [
            fila for fila in entradas_validas
            if (reprocesar or fila["url"] not in detalles or
                (reprocesar_ajenos and detalles[fila["url"]].get("estado") == "autor_fuera_del_perfil") or
                (reintentar_errores and detalles[fila["url"]].get("estado") in {
                    "error_lectura", "html_sin_evidencia", "sin_recuentos_publicos"
                }))
        ]
    if limite:
        pendientes = pendientes[:limite]

    print(f"Enlaces válidos: {len(entradas_validas)}")
    print(f"Pendientes en esta ejecución: {len(pendientes)}")
    if not pendientes:
        print("No hay publicaciones pendientes. Puedes usar --reprocesar para actualizar valores.")
        return

    PERFIL_CHROME.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        contexto = playwright.chromium.launch_persistent_context(
            user_data_dir=str(PERFIL_CHROME), channel="chrome", headless=False
        )
        try:
            pagina = contexto.new_page()
            for numero, fila in enumerate(pendientes, start=1):
                url = fila["url"]
                print(f"\n[{numero}/{len(pendientes)}] {url}")
                try:
                    respuesta = pagina.goto(
                        url, wait_until="domcontentloaded", timeout=45000
                    )
                    estado_http = respuesta.status if respuesta else None
                    if detener_por_restriccion(pagina.url, estado_http):
                        print("Acceso restringido o autenticación requerida. Deteniendo el lote.")
                        break
                    if not redireccion_equivalente(url, pagina.url):
                        print("Redirección a otra publicación o dirección; lote detenido.")
                        print("URL solicitada:", url)
                        print("URL final:", pagina.url)
                        print("Estado HTTP:", estado_http)
                        break
                    if pagina.url != url:
                        print("Redirección equivalente confirmada:", pagina.url)
                    if estado_http != 200:
                        print(f"Respuesta HTTP: {estado_http}; se registra error sin inventar datos")
                        registro = {
                            "url": url, "estado": f"http_{estado_http}",
                            "fecha_observacion_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")
                        }
                    else:
                        try:
                            pagina.locator('meta[property="og:description"]').first.wait_for(
                                state="attached", timeout=9000
                            )
                        except PlaywrightTimeout:
                            pass  # Puede existir solamente meta[name=description].

                        # Los controles React pueden aparecer después de domcontentloaded.
                        pagina.wait_for_timeout(1500)
                        html = pagina.content()
                        tipo = fila.get("tipo") or urlsplit(url).path.strip("/").split("/")[0]
                        if diagnostico:
                            diagnostico_html(html, tipo)
                        registro = extraer_detalle_html(html, tipo, fila.get("texto_alternativo", ""))
                        registro["url"] = url
                        registro["tipo"] = tipo
                        registro["fecha_observacion_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
                        autor = registro.get("autor_declarado")
                        perfil = fila.get("perfil_consultado")
                        registro["vinculo_perfil"] = clasificar_vinculo(
                            perfil, autor, registro.get("menciones", [])
                        )
                        # No inferir una coautoría a partir de una mención o del feed.
                        registro["colaboracion_confirmada"] = None
                        registro["atribucion_metricas"] = (
                            "contenido_original" if autor else "autor_no_verificado"
                        )
                        hay_recuentos = any(
                            registro.get(clave) is not None
                            for clave in ("likes", "comentarios", "visualizaciones", "reposts", "compartidos")
                        )
                        sin_metadatos = not (registro.get("autor_declarado") or
                                              registro.get("descripcion_publicacion") or
                                              registro.get("fecha_publicacion") or hay_recuentos)
                        if sin_metadatos:
                            # HTTP 200 no significa que el HTML sea la publicación.
                            registro["estado"] = "html_sin_evidencia"
                        elif registro["vinculo_perfil"] not in ("autor_principal", "no_determinado"):
                            registro["estado"] = "otro_autor_con_recuentos" if hay_recuentos else "otro_autor_sin_recuentos"
                            print(f"Autor declarado: {autor}; métricas de la publicación original, NO del perfil")
                        else:
                            registro["estado"] = "con_recuentos" if hay_recuentos else "sin_recuentos_publicos"
                        print(
                            "Estado:", registro["estado"],
                            "| likes:", registro.get("likes"),
                            "| comentarios:", registro.get("comentarios"),
                            "| vistas:", registro.get("visualizaciones"),
                            "| reposts:", registro.get("reposts"),
                            "| fecha:", registro.get("fecha_publicacion"),
                        )

                    detalles[url] = registro
                    guardar_json(RUTA_DETALLES, detalles)  # Checkpoint tras cada URL.
                    if any(
                        registro.get(clave) is not None
                        for clave in ("likes", "comentarios", "visualizaciones", "reposts", "compartidos")
                    ):
                        metricas[url] = {
                            "likes": registro.get("likes"),
                            "comentarios": registro.get("comentarios"),
                            "visualizaciones": registro.get("visualizaciones"),
                            "reposts": registro.get("reposts"),
                            "compartidos": registro.get("compartidos"),
                            "alcance": None,
                            "autor_declarado": registro.get("autor_declarado"),
                            "vinculo_perfil": registro.get("vinculo_perfil"),
                            "atribucion_metricas": registro.get("atribucion_metricas"),
                            "fuente_metricas": registro.get("fuente_metricas"),
                            "fechas_html_candidatas": registro.get("fechas_html_candidatas", []),
                            "fuentes_por_metrica": registro.get("fuentes_por_metrica", {}),
                            "conflictos_metricas": registro.get("conflictos_metricas", {}),
                            "fecha_observacion_utc": registro["fecha_observacion_utc"],
                        }
                        guardar_json(RUTA_METRICAS, metricas)
                except (PlaywrightError, OSError, ValueError) as error:
                    print("Error en esta URL:", type(error).__name__, str(error)[:150])
                    detalles[url] = {
                        "url": url,
                        "estado": "error_lectura",
                        "fecha_observacion_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    }
                    guardar_json(RUTA_DETALLES, detalles)

                if numero != len(pendientes):
                    time.sleep(pausa)
        finally:
            contexto.close()

    print("\nLote finalizado. Registros en el archivo de detalles:", len(detalles))
    print("Archivo:", RUTA_DETALLES)
    print("Métricas verificadas:", RUTA_METRICAS)


def main():
    parser = argparse.ArgumentParser(description="Procesamiento secuencial de publicaciones autorizadas")
    parser.add_argument("--limite", type=int, default=3, help="0 para todas las pendientes; 3 recomendado en primera prueba")
    parser.add_argument("--pausa", type=float, default=3.0, help="Segundos entre publicaciones")
    parser.add_argument("--reprocesar", action="store_true", help="Revisar todos los registros y actualizar una instantánea")
    parser.add_argument("--reprocesar-ajenos", action="store_true", help="Revisar registros antiguos donde se habían descartado métricas por autor distinto")
    parser.add_argument("--solo-url", type=str, help="Revisar una URL que ya exista en el JSON, incluso si ya se procesó")
    parser.add_argument("--diagnostico", action="store_true", help="Mostrar metadatos y controles relevantes sin guardar HTML")
    parser.add_argument("--reintentar-errores", action="store_true", help="Revisar solo registros con error o sin recuentos")
    args = parser.parse_args()
    if args.limite < 0 or args.pausa < 2:
        parser.error("--limite debe ser >= 0 y --pausa debe ser >= 2")
    procesar_enlaces(args.limite, args.pausa, args.reprocesar, args.reprocesar_ajenos,
                    args.solo_url, args.diagnostico, args.reintentar_errores)


if __name__ == "__main__":
    main()
