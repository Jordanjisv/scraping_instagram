
import re
from collections import Counter


def extraer_hashtags(texto: str | None) -> list[str]:
    encontrados = re.findall(
        r"(?<!\w)#[\w]+",
        texto or ""
    )

    return list(dict.fromkeys(
        etiqueta.casefold()
        for etiqueta in encontrados
    ))


def analizar_registros(registros: list[dict]) -> dict:
    tipos = Counter(
        registro.get("tipo", "desconocido")
        for registro in registros
    )

    textos = [
        (registro.get("texto_alternativo") or "").strip()
        for registro in registros
    ]

    textos_validos = [
        texto for texto in textos if texto
    ]

    etiquetas = Counter()

    for texto in textos_validos:
        etiquetas.update(extraer_hashtags(texto))

    total = len(registros)
    completos = len(textos_validos)

    promedio_caracteres = (
        round(
            sum(len(texto) for texto in textos_validos)
            / completos,
            1
        )
        if completos else 0.0
    )

    return {
        "total": total,
        "tipos": dict(tipos),
        "con_texto": completos,
        "porcentaje_con_texto": (
            round(100 * completos / total, 1)
            if total else 0.0
        ),
        "promedio_caracteres": promedio_caracteres,
        "hashtags_frecuentes": etiquetas.most_common(10),
    }
