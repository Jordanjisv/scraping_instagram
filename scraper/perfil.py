"""Datos públicos visibles en HTML de un perfil; no usa API ni peticiones de red.

Conserva None cuando faltan datos. Las cifras abreviadas se marcan aproximadas.
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit, parse_qs
from bs4 import BeautifulSoup

_NUM = r"(?:\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?)\s*(?:mil(?:lones)?|millones?|[kKmM])?"
_ETIQUETAS = {
    "publicaciones": r"posts?|publicaciones?",
    "seguidores": r"followers?|seguidores?",
    "seguidos": r"following|seguidos?",
}


def interpretar_cantidad(texto: str) -> tuple[int | None, bool]:
    """Convierte número visible; marca aproximación (K/M/mil)."""
    texto = " ".join(str(texto).strip().casefold().split())
    m = re.fullmatch(r"(\d[\d.,]*)\s*(mil(?:lones)?|millones?|[km])?", texto)
    if not m:
        return None, False
    base, sufijo = m.groups()
    if sufijo:
        if base.count(".") + base.count(",") > 1:
            return None, False
        try:
            numero = float(base.replace(",", "."))
        except ValueError:
            return None, False
        factor = 1_000_000 if sufijo in {"m", "millon", "millones", "millón", "millones", "millones"} or sufijo.startswith("millon") or sufijo == "millones" else 1_000
        return int(round(numero * factor)), True
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", base):
        return int(base.replace(",", "").replace(".", "")), False
    if base.isdecimal():
        return int(base), False
    return None, False


def _metadato(sopa, atributo, nombre) -> str:
    etiqueta = sopa.find("meta", attrs={atributo: nombre})
    return (etiqueta.get("content") or "").strip() if etiqueta else ""


def _conteo_en_texto(texto: str, campo: str) -> tuple[int | None, bool]:
    patron = rf"(?<![\w.,])(?P<numero>{_NUM})\s+(?:{_ETIQUETAS[campo]})\b"
    for m in re.finditer(patron, texto, re.IGNORECASE):
        valor, aprox = interpretar_cantidad(m.group("numero"))
        if valor is not None:
            return valor, aprox
    return None, False


def _enlace_externo(href: str) -> str | None:
    if href.startswith("/"):
        return None
    try:
        partes = urlsplit(href)
        if partes.scheme not in {"http", "https"} or not partes.hostname:
            return None
        if partes.hostname.lower() in {"instagram.com", "www.instagram.com", "l.instagram.com"}:
            # Los enlaces públicos del perfil suelen redirigir por l.instagram.com
            if partes.hostname.lower() == "l.instagram.com":
                destino = (parse_qs(partes.query).get("u") or [""])[0]
                return _enlace_externo(destino) if destino != href else None
            return None
        return href
    except ValueError:
        return None


def extraer_perfil_html(html: str, usuario: str) -> dict:
    """Lee únicamente datos que pueden asociarse con evidencia a la página.

    No infiere el número de posts del número de enlaces descargados.
    """
    sopa = BeautifulSoup(html, "html.parser")
    cabecera = sopa.select_one("main header") or sopa.select_one("header")
    texto_cabecera = cabecera.get_text(" ", strip=True) if cabecera else ""
    meta_descripcion = _metadato(sopa, "name", "description")
    meta_og_descripcion = _metadato(sopa, "property", "og:description")
    meta_titulo = _metadato(sopa, "property", "og:title") or _metadato(sopa, "name", "title")

    datos = {
        "usuario": usuario,
        "url": f"https://www.instagram.com/{usuario}/",
        "nombre": None,
        "biografia": None,
        "categoria": None,
        "enlaces_externos": [],
        "imagen_perfil_url": None,
        "verificado": None,
        "publicaciones": None,
        "seguidores": None,
        "seguidos": None,
        "conteos_aproximados": {},
        "fuentes": {},
    }
    for campo in ("publicaciones", "seguidores", "seguidos"):
        # Texto del encabezado visible como fuente preferente; metadatos de apoyo.
        for fuente, texto in (("header_visible", texto_cabecera), ("meta_description", meta_descripcion),
                              ("og_description", meta_og_descripcion)):
            valor, aproximado = _conteo_en_texto(texto, campo)
            if valor is not None:
                datos[campo] = valor
                datos["conteos_aproximados"][campo] = aproximado
                datos["fuentes"][campo] = fuente
                break

    # Título OG habitual: Nombre (@usuario) • Instagram ...
    titular = re.match(r"(.{1,150}?)\s*\(@([A-Za-z0-9._]+)\)", meta_titulo)
    if titular and titular.group(2).casefold() == usuario.casefold():
        datos["nombre"] = titular.group(1).strip()
        datos["fuentes"]["nombre"] = "og_title"
    elif cabecera:
        for candidato in cabecera.select("h1, h2"):
            valor = candidato.get_text(" ", strip=True)
            if valor and valor.casefold() not in {usuario.casefold(), f"@{usuario.casefold()}"}:
                datos["nombre"] = valor[:160]
                datos["fuentes"]["nombre"] = "header_visible"
                break

    if cabecera:
        # El alt/imagen externa se guarda como referencia, no se descarga.
        imagen = cabecera.select_one('img[alt*="profile" i], img[alt*="perfil" i]')
        if imagen and isinstance(imagen.get("src"), str):
            datos["imagen_perfil_url"] = imagen["src"]
            datos["fuentes"]["imagen_perfil_url"] = "header_img"

        verificacion = cabecera.select_one(
            'svg[aria-label="Verified"], svg[aria-label="Verificado"], '
            '[title="Verified"], [title="Verificado"]'
        )
        if verificacion:
            datos["verificado"] = True
            datos["fuentes"]["verificado"] = "insignia_html"

        # La etiqueta semántica de biografía es la fuente más directa.
        biografia = cabecera.select_one('[data-testid="user-profile-bio"], [data-testid="profile-bio"]')
        if biografia:
            texto = biografia.get_text("\n", strip=True)
            if texto:
                datos["biografia"] = texto[:4000]
                datos["fuentes"]["biografia"] = "header_bio"
        if not datos["biografia"]:
            # Meta description suele delimitar la biografía entre comillas.
            # A diferencia de los span[dir=auto], no incluye historias destacadas.
            patron_bio_meta = (
                rf"\(@{re.escape(usuario)}\).*?"
                r"(?:en|on)\s+Instagram\s*:\s*[\"“](.+?)[\"”]\s*$"
            )
            coincidencia = re.search(patron_bio_meta, meta_descripcion, re.IGNORECASE | re.DOTALL)
            if coincidencia:
                texto = coincidencia.group(1).strip()
                if texto:
                    datos["biografia"] = texto[:4000]
                    datos["fuentes"]["biografia"] = "meta_description_biografia"
        if not datos["biografia"]:
            # Evitar unir TODOS los spans: así se incorporan historias destacadas,
            # nombre del perfil, etiquetas de acciones o títulos ajenos a la bio.
            # Elegir una única pieza plausible, o dejar None si no hay evidencia.
            candidatos = []
            for elem in cabecera.select('span[dir="auto"]'):
                texto = elem.get_text(" ", strip=True)
                if (len(texto) >= 45 and len(texto) <= 600
                        and texto.casefold() != usuario.casefold()
                        and not any(_conteo_en_texto(texto, c)[0] is not None for c in _ETIQUETAS)):
                    candidatos.append(texto)
            if candidatos:
                datos["biografia"] = max(candidatos, key=len)[:4000]
                datos["fuentes"]["biografia"] = "header_texto_largo_aproximado"

        cat = cabecera.select_one('[data-testid="profile-category"], [data-testid="user-category"]')
        if cat:
            categoria = cat.get_text(" ", strip=True)
            if categoria:
                datos["categoria"] = categoria[:160]
                datos["fuentes"]["categoria"] = "header_category"

        enlaces = []
        for a in cabecera.select("a[href]"):
            url = _enlace_externo(a["href"])
            if url and url not in enlaces:
                enlaces.append(url)
        datos["enlaces_externos"] = enlaces[:15]
        if enlaces:
            datos["fuentes"]["enlaces_externos"] = "header_links"

    if not datos["imagen_perfil_url"]:
        og_imagen = _metadato(sopa, "property", "og:image")
        if og_imagen.startswith("https://"):
            datos["imagen_perfil_url"] = og_imagen
            datos["fuentes"]["imagen_perfil_url"] = "og_image"

    return datos
