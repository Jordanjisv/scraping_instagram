"""Dashboard local: datos por URL, rankings y revisión detallada. No visita Instagram."""
from __future__ import annotations
import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st

from scraper.analisis import analizar_registros
from scraper.detalles import extraer_menciones
from scraper.presentacion import metricas_visibles, mostrar_conteo

BASE = Path(__file__).resolve().parent / "resultados"
ENRIQUECIDO = BASE / "publicaciones_enriquecidas.json"
RUTA = ENRIQUECIDO if ENRIQUECIDO.is_file() else BASE / "enlaces_publicaciones.json"
NOMBRES = {
    "likes": "Me gusta", "comentarios": "Comentarios", "visualizaciones": "Visualizaciones",
    "reposts": "Republicaciones", "compartidos": "Compartidos", "alcance": "Alcance",
}

st.set_page_config(page_title="Análisis de publicaciones", page_icon="📊", layout="wide")
st.title("📊 Análisis de publicaciones y sus métricas")
st.caption("Resultados almacenados localmente; el dashboard no accede a Instagram.")
try:
    registros = json.loads(RUTA.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as e:
    st.error(f"No se pudo leer {RUTA.name}: {e}")
    st.stop()
if not isinstance(registros, list) or not all(isinstance(r, dict) for r in registros):
    st.error("El archivo debe contener una lista JSON de publicaciones.")
    st.stop()


CAMPOS = metricas_visibles(registros)

def nombre_corto(r):
    url = str(r.get("url") or "")
    match = re.search(r"/(?:reels?|p)/([A-Za-z0-9_-]+)/?", url)
    codigo = match.group(1) if match else str(r.get("codigo") or "sin_codigo")
    autor = r.get("autor_declarado") or "autor N/D"
    return f"{r.get('tipo', 'post').upper()} · {codigo} · {autor}"


def valor_metrica(r, campo):
    valor = r.get(campo)
    return valor if type(valor) is int and valor >= 0 else None


def ver_metrica(r, campo):
    numero = valor_metrica(r, campo)
    return f"{numero:,}" if numero is not None else "N/D"


def textos(r):
    descripcion = r.get("descripcion_para_mostrar") or r.get("descripcion_publicacion") or r.get("texto_alternativo") or ""
    return str(descripcion)


# Perfil: es una instantánea distinta de los 60 enlaces obtenidos.
PERFIL_JSON = BASE / "perfil.json"
perfil = None
if PERFIL_JSON.is_file():
    try:
        perfil = json.loads(PERFIL_JSON.read_text(encoding="utf-8"))
        if not isinstance(perfil, dict):
            perfil = None
    except (OSError, json.JSONDecodeError):
        st.warning("No se pudo leer el perfil.json. Ejecuta inspeccionar_perfil.py nuevamente.")

st.subheader("👤 Información visible del perfil")
if perfil:
    usuario = perfil.get("usuario") or "N/D"
    nombre = perfil.get("nombre") or "Nombre no disponible"
    st.write(f"**{nombre}** · @{usuario}")
    url_perfil = str(perfil.get("url") or "")
    if re.fullmatch(r"https://(?:www\.)?instagram\.com/[A-Za-z0-9._]+/", url_perfil):
        st.link_button("Abrir perfil en Instagram", url_perfil)
    c1, c2, c3 = st.columns(3)
    aproximados = perfil.get("conteos_aproximados") or {}
    for caja, campo, titulo in ((c1, "seguidores", "Seguidores"),
                                (c2, "seguidos", "Seguidos"),
                                (c3, "publicaciones", "Publicaciones del perfil")):
        caja.metric(titulo, mostrar_conteo(perfil.get(campo), bool(aproximados.get(campo))))
    if perfil.get("categoria"):
        st.write("**Categoría:**", perfil["categoria"])
    if perfil.get("biografia"):
        st.write("**Biografía:**", perfil["biografia"])
    if perfil.get("verificado") is True:
        st.caption("Insignia verificada observada en el HTML")
    enlaces = [e for e in (perfil.get("enlaces_externos") or [])
               if isinstance(e, str) and e.startswith("https://")]
    for indice, enlace in enumerate(enlaces[:10], start=1):
        st.link_button(f"Enlace externo {indice}", enlace)
    if perfil.get("imagen_perfil_url"):
        st.caption("La referencia a la foto de perfil está guardada en perfil.json.")
    st.caption("Datos del perfil observados: " + str(perfil.get("fecha_observacion_utc") or "N/D") +
               ". El total de publicaciones del perfil puede diferir del número de URLs obtenidas.")
    with st.expander("Procedencia de la información del perfil"):
        st.json(perfil.get("fuentes") or {})
else:
    st.info("Aún no hay una instantánea del perfil. Ejecuta: python inspeccionar_perfil.py")

st.divider()
st.sidebar.header("Filtrar publicaciones")
tipo = st.sidebar.selectbox("Tipo", ["Todos", "p", "reel"])
vinculos = sorted({r.get("vinculo_perfil") or "no_determinado" for r in registros})
vinculo = st.sidebar.selectbox("Relación con el perfil", ["Todos"] + vinculos)
busqueda = st.sidebar.text_input("Buscar URL, autor, texto, #hashtag o @mención").strip().casefold()
ordenes = ["Más likes", "Más comentarios", "Más reposts"]
if "compartidos" in CAMPOS:
    ordenes.append("Más compartidos")
if "visualizaciones" in CAMPOS:
    ordenes.append("Más visualizaciones")
ordenes += ["Más menciones", "Más hashtags", "Fecha", "Orden original"]
criterio = st.sidebar.selectbox("Ordenar por", ordenes)
solo_con = st.sidebar.checkbox("Solo publicaciones con métricas disponibles")

seleccionados = []
for r in registros:
    if tipo != "Todos" and r.get("tipo") != tipo:
        continue
    if vinculo != "Todos" and (r.get("vinculo_perfil") or "no_determinado") != vinculo:
        continue
    if solo_con and not any(valor_metrica(r, k) is not None for k in CAMPOS):
        continue
    buscar_en = " ".join(str(r.get(k) or "") for k in ("url", "autor_declarado", "descripcion_para_mostrar", "descripcion_publicacion", "texto_alternativo"))
    buscar_en += " " + " ".join(r.get("hashtags") or []) + " " + " ".join(r.get("menciones") or [])
    if busqueda and busqueda not in buscar_en.casefold():
        continue
    seleccionados.append(r)

orden_claves = {
    "Más likes": "likes", "Más comentarios": "comentarios", "Más reposts": "reposts",
    "Más compartidos": "compartidos", "Más visualizaciones": "visualizaciones",
    "Más menciones": "cantidad_menciones", "Más hashtags": "cantidad_hashtags",
}
if criterio in orden_claves:
    campo_orden = orden_claves[criterio]
    seleccionados.sort(key=lambda r: (r.get(campo_orden) is not None and type(r.get(campo_orden)) is int, r.get(campo_orden) or 0), reverse=True)
elif criterio == "Fecha":
    seleccionados.sort(key=lambda r: r.get("fecha_publicacion") or "", reverse=True)

indicadores = [("Publicaciones analizadas", len(seleccionados)),
               ("Con likes", sum(valor_metrica(r, "likes") is not None for r in seleccionados)),
               ("Con comentarios", sum(valor_metrica(r, "comentarios") is not None for r in seleccionados)),
               ("Con reposts", sum(valor_metrica(r, "reposts") is not None for r in seleccionados))]
if "visualizaciones" in CAMPOS:
    indicadores.append(("Con visualizaciones", sum(valor_metrica(r, "visualizaciones") is not None for r in seleccionados)))
for caja, (titulo, valor) in zip(st.columns(len(indicadores)), indicadores):
    caja.metric(titulo, valor)

st.caption("N/D significa que no existe un recuento verificado; no equivale a cero. "
           "Las visualizaciones se conservan en el JSON, pero no se muestran hasta contar con cifras reales. "
           "Una mención no demuestra colaboración y las métricas de otro autor pertenecen al contenido original.")
if not ENRIQUECIDO.is_file():
    st.warning("No existe el consolidado. Ejecuta: python consolidar_resultados_lote.py")
if not seleccionados:
    st.warning("Ninguna publicación coincide con los filtros.")
    st.stop()

vista, resumen = st.tabs(["🔎 Métricas por publicación", "📈 Rankings y estadísticas"])
with vista:
    st.subheader("Detalle de una publicación")
    indices = list(range(len(seleccionados)))
    elegido = st.selectbox("Seleccionar publicación", indices, format_func=lambda i: nombre_corto(seleccionados[i]))
    actual = seleccionados[elegido]
    link = str(actual.get("url") or "")
    if re.fullmatch(r"https://(?:www\.)?instagram\.com/(?:p|reels?)/[A-Za-z0-9_-]+/", link):
        st.link_button("Abrir publicación original", link)
    st.write("**Autor declarado:**", actual.get("autor_declarado") or "N/D")
    st.write("**Relación con el perfil:**", actual.get("vinculo_perfil") or "N/D")
    st.write("**Fecha de publicación:**", actual.get("fecha_publicacion") or "N/D")
    a, b, c = st.columns(3)
    a.metric("Me gusta", ver_metrica(actual, "likes"))
    b.metric("Comentarios", ver_metrica(actual, "comentarios"))
    c.metric("Reposts", ver_metrica(actual, "reposts"))
    campos_opcionales = [c for c in ("compartidos", "visualizaciones", "alcance") if c in CAMPOS]
    campos_extra = [(NOMBRES[c], ver_metrica(actual, c)) for c in campos_opcionales]
    campos_extra.append(("Menciones", len(actual.get("menciones") or extraer_menciones(textos(actual)))))
    for caja, (titulo, valor) in zip(st.columns(len(campos_extra)), campos_extra):
        caja.metric(titulo, valor)
    st.write("**Hashtags:**", ", ".join(actual.get("hashtags") or []) or "N/D")
    st.write("**Menciones:**", ", ".join(actual.get("menciones") or []) or "N/D")
    st.write("**Descripción o texto alternativo:**")
    st.write(textos(actual) or "N/D")
    st.caption(f"Fuente del texto: {actual.get('fuente_texto_mostrado') or 'N/D'} · Fuente general de métricas: {actual.get('fuente_metricas') or 'N/D'} · Observación UTC: {actual.get('fecha_metricas_utc') or 'N/D'}")
    if actual.get("conflictos_metricas"):
        st.warning(f"Hay valores discrepantes que requieren revisión: {actual['conflictos_metricas']}")
    with st.expander("Fuentes de cada métrica"):
        st.json(actual.get("fuentes_por_metrica") or {})

    st.subheader("Tabla completa: una fila por publicación")
    columnas = ["tipo", "url", "autor_declarado", "vinculo_perfil", "fecha_publicacion",
                *CAMPOS, "cantidad_menciones", "cantidad_hashtags", "menciones", "hashtags", "estado_lectura"]
    filas = []
    for r in seleccionados:
        datos = {k: r.get(k) for k in columnas}
        datos["cantidad_menciones"] = len(r.get("menciones") or [])
        datos["cantidad_hashtags"] = len(r.get("hashtags") or [])
        for k in CAMPOS:
            datos[k] = ver_metrica(r, k)
        for k in ("hashtags", "menciones"):
            datos[k] = ", ".join(r.get(k) or [])
        filas.append(datos)
    tabla = pd.DataFrame(filas)
    st.dataframe(tabla, hide_index=True, width="stretch",
                 column_config={"url": st.column_config.LinkColumn("Publicación", display_text="Abrir enlace")})
    st.download_button("Descargar tabla filtrada (CSV)",
                       data=tabla.to_csv(index=False).encode("utf-8-sig"),
                       file_name="metricas_por_publicacion.csv", mime="text/csv")

with resumen:
    analisis = analizar_registros([
        {**r, "texto_alternativo": textos(r)} for r in seleccionados
    ])
    izquierda, derecha = st.columns(2)
    with izquierda:
        st.subheader("Publicaciones vs. reels")
        tipos = pd.DataFrame(list(analisis["tipos"].items()), columns=["Tipo", "Cantidad"]).set_index("Tipo")
        st.bar_chart(tipos)
    with derecha:
        st.subheader("Hashtags más frecuentes")
        if analisis["hashtags_frecuentes"]:
            st.bar_chart(pd.DataFrame(analisis["hashtags_frecuentes"], columns=["Hashtag", "Registros"]).set_index("Hashtag"))
        else:
            st.info("No se encontraron hashtags")

    for clave in ("likes", "comentarios", "reposts"):
        st.subheader(f"Publicaciones con más {NOMBRES[clave].lower()}")
        con_dato = [r for r in seleccionados if valor_metrica(r, clave) is not None]
        con_dato.sort(key=lambda r: valor_metrica(r, clave), reverse=True)
        top = con_dato[:10]
        if not top:
            st.info(f"Todavía no hay recuentos de {NOMBRES[clave].lower()} disponibles.")
        else:
            grafico = pd.DataFrame([
                {"Publicación": nombre_corto(r), NOMBRES[clave]: valor_metrica(r, clave)}
                for r in top
            ]).set_index("Publicación")
            st.bar_chart(grafico)

st.caption(f"Origen: {RUTA.name}. Si acabas de procesar nuevas URLs, ejecuta consolidar_resultados_lote.py y actualiza esta página.")
