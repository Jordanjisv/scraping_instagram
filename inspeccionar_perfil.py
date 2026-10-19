"""Guarda una instantánea de la información visible del perfil, sin API Meta."""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from scraper.perfil import extraer_perfil_html

BASE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description="Información visible de un perfil autorizado")
    parser.add_argument("--usuario", default="alondra_cgp", help="Usuario sin arroba")
    parser.add_argument("--perfil-chrome", default=os.getenv("IG_CHROME_PROFILE", str(Path.home() / "InstagramScraper" / "ChromeProfile" )))
    parser.add_argument("--diagnostico", action="store_true", help="Ver fuentes sin guardar HTML")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9._]{1,30}", args.usuario):
        parser.error("--usuario contiene caracteres no válidos")

    url = f"https://www.instagram.com/{args.usuario}/"
    Path(args.perfil_chrome).mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        contexto = p.chromium.launch_persistent_context(
            user_data_dir=args.perfil_chrome, channel="chrome", headless=False
        )
        try:
            pagina = contexto.new_page()
            respuesta = pagina.goto(url, wait_until="domcontentloaded", timeout=45000)
            codigo = respuesta.status if respuesta else None
            destino = urlsplit(pagina.url)
            print("HTTP:", codigo, "| URL final:", pagina.url)
            if (codigo != 200 or destino.hostname not in {"instagram.com", "www.instagram.com"} or
                    destino.path.rstrip("/") != f"/{args.usuario}"):
                print("El perfil no está disponible o hubo una redirección no esperada. No se guardaron datos.")
                return 1
            try:
                pagina.locator("main header").first.wait_for(state="attached", timeout=10000)
            except PlaywrightTimeout:
                pass
            pagina.wait_for_timeout(1500)
            html = pagina.content()
            datos = extraer_perfil_html(html, args.usuario)
            datos["fecha_observacion_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            datos["estado_lectura"] = (
                "con_conteos" if any(datos[c] is not None for c in ("seguidores", "seguidos", "publicaciones"))
                else "sin_conteos_confirmados"
            )
            if args.diagnostico:
                from bs4 import BeautifulSoup
                sopa = BeautifulSoup(html, "html.parser")
                header = sopa.select_one("main header") or sopa.select_one("header")
                meta = sopa.select_one('meta[name="description"]')
                print("Header visible (recorte):", header.get_text(" ", strip=True)[:400] if header else "[ausente]")
                print("Meta description (recorte):", (meta.get("content") or "")[:250] if meta else "[ausente]")
            print("\n--- PERFIL ---")
            for clave in ("usuario", "nombre", "seguidores", "seguidos", "publicaciones", "biografia", "categoria", "enlaces_externos", "verificado"):
                print(f"{clave}: {datos.get(clave)}")
            print("Fuentes:", datos["fuentes"])
            if datos["estado_lectura"] != "con_conteos":
                print("No hay conteos confiables. Se conserva cualquier instantánea anterior.")
                return 2
            carpeta = BASE / "resultados"
            carpeta.mkdir(exist_ok=True)
            ruta = carpeta / "perfil.json"
            temporal = ruta.with_suffix(".json.tmp")
            temporal.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding="utf-8")
            temporal.replace(ruta)
            print("Perfil guardado:", ruta)
            return 0
        finally:
            contexto.close()


if __name__ == "__main__":
    raise SystemExit(main())
