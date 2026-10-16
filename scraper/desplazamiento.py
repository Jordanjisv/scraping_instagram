
def desplazar_hasta_objetivo(
    pagina,
    obtener_urls,
    objetivo=25,
    max_desplazamientos=10,
    max_sin_cambios=3,
):
    """Reúne URLs visibles con desplazamiento limitado."""

    encontrados = set(obtener_urls(pagina))
    sin_cambios = 0

    for _ in range(max_desplazamientos):
        if len(encontrados) >= objetivo:
            break

        pagina.mouse.wheel(0, 700)
        pagina.wait_for_timeout(600)

        actuales = set(obtener_urls(pagina))
        nuevos = actuales - encontrados

        encontrados.update(actuales)

        if nuevos:
            sin_cambios = 0
        else:
            sin_cambios += 1

        if sin_cambios >= max_sin_cambios:
            break

    return sorted(encontrados)
