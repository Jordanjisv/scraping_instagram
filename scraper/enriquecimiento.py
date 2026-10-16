"""Enriquecimiento local de publicaciones: nunca realiza peticiones a Instagram.

Copiar este archivo a scraper/enriquecimiento.py del proyecto.
"""

from __future__ import annotations

import re
from typing import Any

_HASHTAG = re.compile(r"(?<!\w)#[\w]+", flags=re.UNICODE)
_MENCION = re.compile(r"(?<![\w@])@[A-Za-z0-9._]+")


def _unicos(menciones: list[str]) -> list[str]:
    return list(dict.fromkeys(valor.casefold() for valor in menciones))


def extraer_hashtags_y_menciones(texto: str | None) -> tuple[list[str], list[str]]:
    """Devuelve hashtags y menciones presentes en el texto, sin duplicados."""
    texto = texto or ""
    return _unicos(_HASHTAG.findall(texto)), _unicos(_MENCION.findall(texto))


def _entero_comprobado(valor: Any) -> int | None:
    """Un dato ausente o mal formado queda como None, nunca como cero."""
    if type(valor) is int and valor >= 0:
        return valor
    return None


def enriquecer_registros(
    publicaciones: list[dict], metricas_por_url: dict[str, dict]
) -> list[dict]:
    """Une publicaciones con las métricas verificadas por URL.

    No asigna a otras URLs las métricas de una publicación concreta.
    """
    salida: list[dict] = []
    urls_vistas: set[str] = set()

    for publicacion in publicaciones:
        url = publicacion.get("url")
        if not isinstance(url, str) or not url:
            raise ValueError("Una publicación carece de URL")
        if url in urls_vistas:
            raise ValueError(f"URL repetida en el archivo de origen: {url}")
        urls_vistas.add(url)

        alt = publicacion.get("texto_alternativo") or ""
        etiquetas, menciones = extraer_hashtags_y_menciones(alt)
        dato = metricas_por_url.get(url) or {}

        likes = _entero_comprobado(dato.get("likes"))
        comentarios = _entero_comprobado(dato.get("comentarios"))
        vistas = _entero_comprobado(dato.get("visualizaciones"))
        alcance = _entero_comprobado(dato.get("alcance"))

        estado = (
            "verificado"
            if likes is not None and comentarios is not None
            else "parcial"
            if any(valor is not None for valor in (likes, comentarios, vistas, alcance))
            else "sin_verificar"
        )

        salida.append(
            {
                **publicacion,
                "hashtags": etiquetas,
                "menciones": menciones,
                "likes": likes,
                "comentarios": comentarios,
                "visualizaciones": vistas,
                "alcance": alcance,
                "fuente_metricas": dato.get("fuente_metricas"),
                "fecha_metricas_utc": dato.get("fecha_observacion_utc"),
                "estado_metricas": estado,
            }
        )

    return salida
