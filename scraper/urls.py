"""Normalización de enlaces a publicaciones públicos del DOM."""
import re
from urllib.parse import urljoin, urlsplit

TIPOS = {"p", "reel", "reels", "tv"}
DOMINIOS = {"instagram.com", "www.instagram.com"}


def normalizar_url_publicacion(href: str, url_base: str) -> str | None:
    """Convierte /reels/CODIGO/ y /reel/CODIGO/ a /reel/CODIGO/."""
    partes = urlsplit(urljoin(url_base, href))
    if partes.scheme != "https" or partes.netloc not in DOMINIOS:
        return None
    segmentos = [x for x in partes.path.split("/") if x]
    if len(segmentos) == 2 and segmentos[0] in TIPOS:
        tipo, codigo = segmentos
    elif len(segmentos) == 3 and segmentos[1] in TIPOS:
        _, tipo, codigo = segmentos
    else:
        return None
    if not re.fullmatch(r"[A-Za-z0-9_-]+", codigo):
        return None
    if tipo == "reels":
        tipo = "reel"
    return f"https://www.instagram.com/{tipo}/{codigo}/"
