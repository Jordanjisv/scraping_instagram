"""Lectura conservadora de recuentos publicados en metadatos HTML.

El módulo no navega por la web. Si una métrica no aparece explícitamente,
devuelve None (no cero).
"""
import re
from bs4 import BeautifulSoup

_NUMERO = r"(?:\d{1,3}(?:[.,]\d{3})+|\d+)"
_PATRONES = (
    re.compile(rf"^\s*(?P<likes>{_NUMERO})\s+likes?\s*,\s*(?P<comentarios>{_NUMERO})\s+comments?\b", re.IGNORECASE),
    re.compile(rf"^\s*(?P<likes>{_NUMERO})\s+me\s+gusta\s*,\s*(?P<comentarios>{_NUMERO})\s+comentarios?\b", re.IGNORECASE),
)


def interpretar_recuentos(descripcion: str | None) -> tuple[int | None, int | None]:
    """Extrae recuentos explícitos al comienzo del metadato."""
    for patron in _PATRONES:
        coincidencia = patron.match(descripcion or "")
        if coincidencia:
            likes = int(coincidencia.group("likes").replace(",", "").replace(".", ""))
            comentarios = int(coincidencia.group("comentarios").replace(",", "").replace(".", ""))
            return likes, comentarios
    return None, None


def extraer_metricas_html(html: str) -> dict:
    """Devuelve valores explícitos, procedencia y tiempos candidatos visibles."""
    sopa = BeautifulSoup(html, "html.parser")
    resultados = {
        "likes": None,
        "comentarios": None,
        "fuente_metricas": None,
        "fechas_html_candidatas": [],
    }

    for selector, fuente in (
        ('meta[property="og:description"]', "og:description"),
        ('meta[name="description"]', "description"),
    ):
        etiqueta = sopa.select_one(selector)
        contenido = etiqueta.get("content", "") if etiqueta else ""
        likes, comentarios = interpretar_recuentos(contenido)
        if likes is not None and comentarios is not None:
            resultados["likes"] = likes
            resultados["comentarios"] = comentarios
            resultados["fuente_metricas"] = fuente
            break

    resultados["fechas_html_candidatas"] = list(dict.fromkeys(
        etiqueta["datetime"]
        for etiqueta in sopa.select("time[datetime]")
        if etiqueta.get("datetime")
    ))
    return resultados
