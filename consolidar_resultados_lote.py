"""Consolida datos ya observados sin nuevas visitas a la web."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from scraper.analisis import extraer_hashtags
from scraper.detalles import extraer_menciones

BASE = Path(__file__).resolve().parent / "resultados"


def leer(ruta: Path, defecto):
    return json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else defecto


def cuenta(valor):
    return valor if type(valor) is int and valor >= 0 else None


def consolidar(enlaces: list[dict], detalles: dict, metricas: dict) -> list[dict]:
    """Une todo por URL. Nunca asigna métricas a otra publicación."""
    salida = []
    vistos = set()
    for item in enlaces:
        url = item["url"]
        if url in vistos:
            raise ValueError(f"URL duplicada: {url}")
        vistos.add(url)

        det = detalles.get(url) or {}
        ver = metricas.get(url) or {}
        descripcion = det.get("descripcion_publicacion")
        texto_alt = item.get("texto_alternativo") or ""
        texto_mostrar = descripcion or texto_alt or None
        fuente_texto = (
            "descripcion_publicacion" if descripcion
            else "texto_alternativo" if texto_alt else None
        )

        def obtenido(campo):
            ver_val = ver.get(campo)
            det_val = det.get(campo)
            return cuenta(ver_val) if cuenta(ver_val) is not None else cuenta(det_val)

        autor = det.get("autor_declarado")
        perfil = item.get("perfil_consultado")
        vinculo = det.get("vinculo_perfil")
        if not vinculo:
            if not autor or not perfil:
                vinculo = "no_determinado"
            elif autor.casefold() == perfil.casefold():
                vinculo = "autor_principal"
            elif f"@{perfil.casefold()}" in extraer_menciones(descripcion or ""):
                vinculo = "perfil_mencionado"
            else:
                vinculo = "contenido_de_otro_autor"

        etiquetas = extraer_hashtags(texto_mostrar)
        menciones = extraer_menciones(texto_mostrar)
        salida.append({
            **item,
            "autor_declarado": autor,
            "vinculo_perfil": vinculo,
            "colaboracion_confirmada": det.get("colaboracion_confirmada"),
            "atribucion_metricas": det.get("atribucion_metricas", "contenido_original" if autor else None),
            "descripcion_publicacion": descripcion,
            "descripcion_para_mostrar": texto_mostrar,
            "fuente_texto_mostrado": fuente_texto,
            "fecha_publicacion": det.get("fecha_publicacion"),
            "fuente_fecha_publicacion": det.get("fuente_fecha_publicacion"),
            "hashtags": etiquetas,
            "menciones": menciones,
            "cantidad_hashtags": len(etiquetas),
            "cantidad_menciones": len(menciones),
            "likes": obtenido("likes"),
            "comentarios": obtenido("comentarios"),
            "visualizaciones": obtenido("visualizaciones") if item.get("tipo") == "reel" else None,
            "reposts": obtenido("reposts"),
            "compartidos": obtenido("compartidos"),
            "alcance": None,
            "fuente_metricas": ver.get("fuente_metricas") or det.get("fuente_metricas"),
            "fuentes_por_metrica": det.get("fuentes_por_metrica") or ver.get("fuentes_por_metrica") or {},
            "conflictos_metricas": det.get("conflictos_metricas") or ver.get("conflictos_metricas") or {},
            "fecha_metricas_utc": ver.get("fecha_observacion_utc") or det.get("fecha_observacion_utc"),
            "estado_lectura": det.get("estado", "aun_no_procesada"),
        })
    return salida


def main():
    enlaces = leer(BASE / "enlaces_publicaciones.json", [])
    detalles = leer(BASE / "detalles_publicaciones.json", {})
    metricas = leer(BASE / "metricas_verificadas.json", {})
    if not isinstance(enlaces, list) or not isinstance(detalles, dict) or not isinstance(metricas, dict):
        raise ValueError("Formato JSON inesperado en los archivos de entrada")

    salida = consolidar(enlaces, detalles, metricas)
    BASE.mkdir(parents=True, exist_ok=True)
    ruta_json = BASE / "publicaciones_enriquecidas.json"
    ruta_csv = BASE / "publicaciones_enriquecidas.csv"
    ruta_json.write_text(json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8")
    if salida:
        columnas = list(salida[0].keys())
        with ruta_csv.open("w", encoding="utf-8-sig", newline="") as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=columnas)
            escritor.writeheader()
            for fila in salida:
                escritor.writerow({
                    clave: " | ".join(valor) if isinstance(valor, list) else valor
                    for clave, valor in fila.items()
                })

    print("\n--- RESUMEN CONSOLIDADO ---")
    print("Enlaces totales:", len(salida))
    print("Estados de lectura:", dict(Counter(d["estado_lectura"] for d in salida)))
    for campo in ("likes", "comentarios", "visualizaciones", "reposts", "compartidos", "fecha_publicacion"):
        print(f"Con {campo} conocido:", sum(d[campo] is not None for d in salida))
    print("Con descripción completa (meta):", sum(bool(d["descripcion_publicacion"]) for d in salida))
    print("Con texto utilizable (descripción o alt):", sum(bool(d["descripcion_para_mostrar"]) for d in salida))
    print("Con autor principal del perfil:", sum(d["vinculo_perfil"] == "autor_principal" for d in salida))
    print("JSON:", ruta_json)
    print("CSV:", ruta_csv)


if __name__ == "__main__":
    main()
