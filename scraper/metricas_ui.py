"""Recuentos explícitos encontrados en elementos accesibles del HTML renderizado.

No interpreta números sueltos como métricas, ni cuenta comentarios individuales,
ni usa endpoints internos. Un elemento que indique "Repostear" sin cifra no
representa un número de republicaciones.
"""
from __future__ import annotations

import re
from collections import defaultdict
from bs4 import BeautifulSoup

_NUM = r"(?:\d{1,3}(?:[.,]\d{3})+|\d+)"
_CAMPOS = {
    "likes": r"likes?|me\s+gusta",
    "comentarios": r"comments?|comentarios?",
    "reposts": r"reposts?|reposteos?|republicaciones?|republicados?",
    "compartidos": r"shares?|compartidos?",
    "visualizaciones": r"views?|visualizaciones?|reproducciones?|plays?",
}


def _numero(valor: str) -> int:
    return int(valor.replace(",", "").replace(".", ""))


def _campo(texto: str) -> tuple[str, int] | None:
    texto = " ".join(texto.split()).strip()
    if not texto or len(texto) > 100:
        return None
    # Evitar frases de subtítulos o mensajes extensos que casualmente mencionan métricas.
    inicio = r"(?:ver(?:\s+todos?|\s+los|\s+las)?|view\s+all|see\s+all)?\s*"
    for campo, etiqueta in _CAMPOS.items():
        patrones = (
            rf"^{inicio}(?P<n>{_NUM})\s+(?:{etiqueta})$",
            rf"^(?:{etiqueta})\s*:\s*(?P<n>{_NUM})$",
            rf"^(?:{etiqueta})\s+(?P<n>{_NUM})$",
        )
        for patron in patrones:
            m = re.fullmatch(patron, texto, flags=re.IGNORECASE)
            if m:
                return campo, _numero(m['n'])
    return None


# Para HTML como: «Me gusta 14 Comentar 2 Republicar 1 Compartir».
# No se permite asociar hacia ATRÁS: el 1 posterior a Republicar nunca
# es un contador del botón Compartir siguiente.
_ACCIONES = {
    "likes": {"me gusta", "like", "likes"},
    "comentarios": {"comentar", "comentario", "comment", "comments"},
    "reposts": {"republicar", "repostear", "repost", "reposts", "repostar"},
    "compartidos": {"compartir", "share"},
}


def _es_control(etiqueta) -> bool:
    return etiqueta.name == "button" or etiqueta.get("role") == "button"


def _accion_control(etiqueta) -> str | None:
    """Identifica el botón a partir de su etiqueta, no de texto del post."""
    if not _es_control(etiqueta):
        return None
    textos = [etiqueta.get("aria-label"), etiqueta.get("title")]
    texto = " ".join(etiqueta.get_text(" ", strip=True).split())
    if len(texto) <= 60:
        textos.append(texto)
    # Botones que solo contienen un icono con etiqueta accesible.
    icono = etiqueta.select_one("svg[aria-label]")
    if icono:
        textos.append(icono.get("aria-label"))
    for candidato in textos:
        normal = " ".join((candidato or "").casefold().split())
        for nombre, permitidos in _ACCIONES.items():
            if normal in permitidos:
                return nombre
    return None


def _contadores_junto_a_acciones(sopa) -> dict[str, list[tuple[int, str]]]:
    """Solo número en SPAN directamente DESPUÉS de botón en barra de acciones.

    La barra ha de contener al menos dos acciones distintas como hermanos,
    evitando tomar como métricas controles aislados de comentarios o captions.
    """
    hallazgos = defaultdict(list)
    zona = sopa.select_one("main article") or sopa.select_one("article") or sopa.select_one("main") or sopa.body or sopa
    for control in zona.select('button, [role="button"]'):
        campo = _accion_control(control)
        if not campo:
            continue
        padre = control.parent
        if padre is None:
            continue
        hermanos = [elem for elem in padre.find_all(recursive=False) if hasattr(elem, "name")]
        acciones_grupo = {_accion_control(elem) for elem in hermanos if _es_control(elem)}
        acciones_grupo.discard(None)
        if len(acciones_grupo) < 2:
            continue
        vecino = control.find_next_sibling()
        if vecino is None or vecino.name not in {"span", "small", "strong", "b"}:
            continue
        # No considerar contenedores complejos que pueden contener otras métricas.
        if vecino.find(True):
            continue
        texto_numero = " ".join(vecino.get_text(" ", strip=True).split())
        if not re.fullmatch(_NUM, texto_numero):
            continue
        hallazgos[campo].append((_numero(texto_numero), "ui:accion_contador_adyacente"))
    return hallazgos


def extraer_recuentos_ui(html: str, tipo: str) -> dict:
    """Solo recuentos concretos de controles; ambigüedad => None.

    Fuentes: aria-label/title de controles y texto de botón, nunca cualquier
    frase del body. Los candidatos con dos valores diferentes se descartan.
    """
    sopa = BeautifulSoup(html, "html.parser")
    candidatos: dict[str, list[tuple[int, str]]] = defaultdict(list)
    # Botones, enlaces y elementos ARIA suelen mostrar las cantidades accesibles.
    for elemento in sopa.select('button, [role="button"], a, [aria-label], [title]'):
        for atributo in ("aria-label", "title"):
            literal = elemento.get(atributo)
            if not isinstance(literal, str):
                continue
            par = _campo(literal)
            if par:
                candidatos[par[0]].append((par[1], f"ui:{atributo}"))
        if elemento.name in {"button", "a"} or elemento.get("role") == "button":
            # Un botón entero (no una descripción/caption) que indique el número.
            contenido = elemento.get_text(" ", strip=True)
            par = _campo(contenido)
            if par:
                candidatos[par[0]].append((par[1], "ui:control_texto"))
            # Un control con el icono etiquetado y el contador numérico
            # como texto. 'Repostear' sin un número no es un recuento.
            elif re.fullmatch(_NUM, contenido) and len(contenido) <= 20:
                icono = elemento.select_one("svg[aria-label], svg title")
                if icono:
                    texto_icono = (icono.get("aria-label") or icono.get_text(" ", strip=True)).casefold().strip()
                    iconos = {
                        "comentarios": {"comentar", "comentario", "comment", "comments"},
                        "reposts": {"repost", "repostear", "republicar", "repostar", "reposteos"},
                        "compartidos": {"compartir", "share"},
                        "likes": {"like", "me gusta"},
                        "visualizaciones": {"views", "visualizaciones"},
                    }
                    for nombre, etiquetas in iconos.items():
                        if texto_icono in etiquetas:
                            candidatos[nombre].append((_numero(contenido), "ui:icono_contador"))
    # Los pares botón -> contador numérico contiguo en una misma barra de
    # acciones son preferibles a etiquetas sueltas que pueden corresponder
    # a botones internos de comentarios u otros elementos.
    precisos = _contadores_junto_a_acciones(sopa)
    resultado = {}
    fuentes = {}
    conflictos = {}
    for campo in _CAMPOS:
        valores_precisos = {numero for numero, _ in precisos[campo]}
        valores_genericos = {numero for numero, _ in candidatos[campo]}
        if len(valores_precisos) == 1:
            resultado[campo] = next(iter(valores_precisos))
            fuentes[campo] = "ui:accion_contador_adyacente"
            if valores_genericos - valores_precisos:
                conflictos[campo] = sorted(valores_precisos | valores_genericos)
        elif len(valores_precisos) > 1:
            resultado[campo] = None
            conflictos[campo] = sorted(valores_precisos)
        elif len(valores_genericos) == 1:
            resultado[campo] = next(iter(valores_genericos))
            fuentes[campo] = candidatos[campo][0][1]
        else:
            resultado[campo] = None
            if len(valores_genericos) > 1:
                conflictos[campo] = sorted(valores_genericos)
    if tipo != "reel":
        resultado["visualizaciones"] = None
        fuentes.pop("visualizaciones", None)
    return {**resultado, "fuentes_ui": fuentes, "conflictos_ui": conflictos}
