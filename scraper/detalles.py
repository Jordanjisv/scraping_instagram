"""Extracción conservadora de metadatos HTML de publicaciones autorizadas.

No realiza peticiones HTTP ni usa API. Los datos ausentes son None, no 0.
"""
from __future__ import annotations

import re
from datetime import date, datetime

from bs4 import BeautifulSoup

from scraper.analisis import extraer_hashtags
from scraper.metricas import extraer_metricas_html
from scraper.metricas_ui import extraer_recuentos_ui

_MENCION = re.compile(r"(?<![\w@])@[A-Za-z0-9._]+")
_NUMERO = r"(?:\d{1,3}(?:[.,]\d{3})+|\d+)"
_ETIQUETAS = {
    "likes": r"likes?|me\s+gusta",
    "comentarios": r"comments?|comentarios?",
    "visualizaciones": r"views?|visualizaciones?|reproducciones?|plays?",
    "reposts": r"reposts?|republicaciones?",
    "compartidos": r"shares?|compartidos?",
}
_MESES = {
    "jan": 1, "january": 1, "enero": 1, "feb": 2, "february": 2, "febrero": 2,
    "mar": 3, "march": 3, "marzo": 3, "apr": 4, "april": 4, "abril": 4,
    "may": 5, "mayo": 5, "jun": 6, "june": 6, "junio": 6,
    "jul": 7, "july": 7, "julio": 7, "aug": 8, "august": 8, "agosto": 8,
    "sep": 9, "sept": 9, "september": 9, "septiembre": 9, "setiembre": 9,
    "oct": 10, "october": 10, "octubre": 10, "nov": 11, "november": 11,
    "noviembre": 11, "dec": 12, "december": 12, "diciembre": 12,
}


def _cantidad_en_cabecera(cabecera: str, etiqueta: str) -> int | None:
    """Busca cantidades explícitas en la cabecera, nunca dentro del caption."""
    patron = rf"(?<![\w.,])(?P<valor>{_NUMERO})\s+(?:{_ETIQUETAS[etiqueta]})\b"
    coincidencia = re.search(patron, cabecera, flags=re.IGNORECASE)
    if not coincidencia:
        return None
    return int(coincidencia.group("valor").replace(",", "").replace(".", ""))


def _partes_descripcion(texto: str) -> tuple[str, str | None, str | None, str | None]:
    """Interpreta OG con *o sin* cabecera de likes/comentarios.

    Instagram puede usar dos formas válidas:
    - '10 likes, 0 comments - autor el May 27, 2026: "Texto"'
    - 'autor el October 14, 2026: "Texto"'

    En ambos casos, el autor y la fecha existen aunque los contadores no.
    """
    coincidencia = re.match(
        r'(?:(?P<cabecera>.*?)\s+-\s+)?'
        r'(?P<autor>[A-Za-z0-9._]+)\s+'
        r'(?P<fecha>(?:el|on)\s+[^:\n]{1,100}):\s*["“]',
        texto,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not coincidencia:
        return (texto.split(" - ", 1)[0], None, None, None)
    cabecera = (coincidencia.group("cabecera") or "").strip()
    autor = coincidencia.group("autor")
    fecha_textual = coincidencia.group("fecha").strip()
    cuerpo = texto[coincidencia.end():].strip()
    if cuerpo.endswith(('".', '”.')):
        cuerpo = cuerpo[:-2]
    elif cuerpo.endswith(('"', '”')):
        cuerpo = cuerpo[:-1]
    return cabecera, autor, cuerpo.strip() or None, fecha_textual


def _fecha_de_meta(texto: str | None) -> str | None:
    """Convierte la fecha de calendario declarada en OG; no infiere la hora."""
    if not texto:
        return None
    texto = texto.casefold()
    mes_expr = "|".join(sorted(map(re.escape, _MESES), key=len, reverse=True))
    patrones = (
        rf"\b(?:on|el)\s+(?P<mes>{mes_expr})\s+(?P<dia>\d{{1,2}}),?\s+(?P<ano>\d{{4}})\b",
        rf"\b(?:el|on)\s+(?P<dia>\d{{1,2}})\s+de\s+(?P<mes>{mes_expr})\s+de\s+(?P<ano>\d{{4}})\b",
    )
    for patron in patrones:
        match = re.search(patron, texto)
        if not match:
            continue
        try:
            return date(int(match["ano"]), _MESES[match["mes"]], int(match["dia"])).isoformat()
        except ValueError:
            return None
    return None


def extraer_menciones(texto: str | None) -> list[str]:
    """Menciones textuales, no equivalen a coautorías verificadas."""
    return list(dict.fromkeys(valor.casefold() for valor in _MENCION.findall(texto or "")))


def extraer_detalle_html(html: str, tipo: str, texto_alt: str = "") -> dict:
    sopa = BeautifulSoup(html, "html.parser")
    origen = None
    descripcion_meta = ""
    for selector, nombre in (
        ('meta[property="og:description"]', "og:description"),
        ('meta[name="description"]', "description"),
    ):
        etiqueta = sopa.select_one(selector)
        valor = etiqueta.get("content", "").strip() if etiqueta else ""
        if valor:
            descripcion_meta = valor
            origen = nombre
            break

    cabecera, autor, descripcion, fecha_textual = _partes_descripcion(descripcion_meta)
    metricas = extraer_metricas_html(html)
    likes = metricas["likes"]
    comentarios = metricas["comentarios"]
    if likes is None:
        likes = _cantidad_en_cabecera(cabecera, "likes")
    if comentarios is None:
        comentarios = _cantidad_en_cabecera(cabecera, "comentarios")

    vistas = (_cantidad_en_cabecera(cabecera, "visualizaciones") if tipo == "reel" else None)
    reposts = _cantidad_en_cabecera(cabecera, "reposts")
    compartidos = _cantidad_en_cabecera(cabecera, "compartidos")

    # Segundo origen: controles accesibles del DOM, cuando la cabecera OG
    # no muestra métricas. Nunca inferir números a partir de iconos aislados.
    recuentos_ui = extraer_recuentos_ui(html, tipo)
    recuentos = {
        "likes": likes,
        "comentarios": comentarios,
        "visualizaciones": vistas,
        "reposts": reposts,
        "compartidos": compartidos,
    }
    fuentes_por_metrica = {}
    conflictos = dict(recuentos_ui["conflictos_ui"])
    for nombre, valor in recuentos.items():
        valor_ui = recuentos_ui[nombre]
        if valor is None and valor_ui is not None:
            recuentos[nombre] = valor_ui
            fuentes_por_metrica[nombre] = recuentos_ui["fuentes_ui"][nombre]
        elif valor is not None:
            fuentes_por_metrica[nombre] = metricas["fuente_metricas"] or origen or "meta:descripcion"
            if valor_ui is not None and valor_ui != valor:
                # Diferencia entre metadatos y UI: no reemplazar silenciosamente.
                conflictos[nombre] = [valor, valor_ui]
    likes = recuentos["likes"]
    comentarios = recuentos["comentarios"]
    vistas = recuentos["visualizaciones"]
    reposts = recuentos["reposts"]
    compartidos = recuentos["compartidos"]

    candidatos = metricas["fechas_html_candidatas"]
    fechas_html = set()
    for valor in candidatos:
        try:
            fechas_html.add(datetime.fromisoformat(valor.replace("Z", "+00:00")).date().isoformat())
        except ValueError:
            pass
    fecha_og = _fecha_de_meta(fecha_textual)
    if fecha_og:
        fecha_publicacion, fuente_fecha = fecha_og, origen
    elif len(fechas_html) == 1:
        fecha_publicacion, fuente_fecha = next(iter(fechas_html)), "time[datetime]"
    else:
        fecha_publicacion, fuente_fecha = None, None

    texto_para_analizar = descripcion or texto_alt or ""
    cuenta_disponible = any(
        numero is not None for numero in (likes, comentarios, vistas, reposts, compartidos)
    )
    return {
        "autor_declarado": autor,
        "descripcion_publicacion": descripcion,
        "fuente_descripcion": origen if descripcion else None,
        "texto_usado_analisis": "descripcion_publicacion" if descripcion else (
            "texto_alternativo" if texto_alt else None
        ),
        "hashtags": extraer_hashtags(texto_para_analizar),
        "menciones": extraer_menciones(texto_para_analizar),
        "likes": likes,
        "comentarios": comentarios,
        "visualizaciones": vistas,
        "reposts": reposts,
        "compartidos": compartidos,
        "alcance": None,
        "fuente_metricas": metricas["fuente_metricas"] or (origen if cuenta_disponible and origen else (
            "ui:html" if cuenta_disponible else None
        )),
        "fuentes_por_metrica": fuentes_por_metrica,
        "conflictos_metricas": conflictos,
        "fecha_publicacion": fecha_publicacion,
        "fuente_fecha_publicacion": fuente_fecha,
        "fechas_html_candidatas": candidatos,
    }
