
from bs4 import BeautifulSoup


def numero_opcional(valor):
    if valor is None or not valor.isdecimal():
        return None

    return int(valor)


def extraer_publicaciones_locales(html: str) -> list[dict]:
    sopa = BeautifulSoup(html, "html.parser")

    registros = []

    for enlace in sopa.select("a.registro[href]"):
        registros.append({
            "url": enlace["href"],
            "descripcion": (
                enlace.get("data-descripcion")
                or enlace.get_text(" ", strip=True)
            ),
            "fecha_publicacion": enlace.get("data-fecha"),
            "likes": numero_opcional(
                enlace.get("data-likes")
            ),
            "comentarios": numero_opcional(
                enlace.get("data-comentarios")
            ),
        })

    return registros
