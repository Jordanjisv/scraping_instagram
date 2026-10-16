# Instagram Scraper — Arquitectura de Software

Proyecto académico en **Python 3.13** que recopila y analiza información visible de un perfil de Instagram mediante **Playwright + BeautifulSoup**, sin usar las API de Meta. Presenta los resultados con **Streamlit**.

## ¿Qué hace?

- Obtiene información visible del perfil: nombre, biografía, seguidores, seguidos y total de publicaciones.
- Recopila enlaces de publicaciones y reels y procesa sus descripciones, fechas, autores, hashtags y menciones.
- Registra likes, comentarios y republicaciones **solo cuando el HTML muestra un contador verificable**.
- Exporta resultados locales en **JSON y CSV**, evita duplicados y permite reanudar el procesamiento.
- Muestra estadísticas, filtros, rankings y detalles por publicación en un dashboard.

**Resultado de la práctica:** 60 publicaciones registradas y 88 pruebas unitarias aprobadas.

**Nota:** `N/D` no significa cero. Las visualizaciones, los compartidos y el alcance pueden no estar disponibles; el dashboard oculta métricas sin datos comprobados.

## Instalación (Windows)

Requiere Python 3.13 y Google Chrome.

```powershell
py -3.13 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Ejecución

```powershell
# 1. Obtener información del perfil
.\venv\Scripts\python.exe inspeccionar_perfil.py --usuario alondra_cgp

# 2. Recopilar enlaces con Chrome
.\venv\Scripts\python.exe inspeccionar_sesion_actualizado.py

# 3. Procesar un lote pequeño y consolidar resultados
.\venv\Scripts\python.exe ejecutar_flujo_completo.py --limite 3

# 4. Abrir el dashboard
.\venv\Scripts\python.exe -m streamlit run dashboard.py
```

## Pruebas

```powershell
.\venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

El código está organizado en `scraper/` (extracción y análisis), `tests/` (pruebas) y `dashboard.py` (visualización). Los datos recopilados se guardan en `resultados/` y **no se publican en el repositorio**. Ejecutar únicamente sobre contenido cuyo acceso y tratamiento estén autorizados y respetando las restricciones de la plataforma.
