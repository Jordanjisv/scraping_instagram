"""Reglas reutilizables para la presentación; sin dependencias de Streamlit."""

def cantidad_valida(registro: dict, campo: str) -> bool:
    valor = registro.get(campo)
    return type(valor) is int and valor >= 0


def metricas_visibles(registros: list[dict]) -> list[str]:
    """Conservar básicos, ocultar opcionales cuando no hay una sola cifra confirmada."""
    basicas = ["likes", "comentarios", "reposts"]
    opcionales = ["compartidos", "visualizaciones", "alcance"]
    return basicas + [campo for campo in opcionales if any(cantidad_valida(r, campo) for r in registros)]


def mostrar_conteo(valor, aproximado: bool = False) -> str:
    if type(valor) is not int or valor < 0:
        return "N/D"
    return f"≈ {valor:,}" if aproximado else f"{valor:,}"
