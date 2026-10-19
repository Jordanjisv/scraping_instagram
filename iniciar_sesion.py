from pathlib import Path
from playwright.sync_api import sync_playwright

perfil = Path.home() / "InstagramScraper" / "ChromeProfile"
perfil.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    contexto = p.chromium.launch_persistent_context(
        user_data_dir=str(perfil),
        channel="chrome",
        headless=False
    )
    try:
        pagina = contexto.new_page()
        pagina.goto("https://www.instagram.com/")
        input("Inicia sesión si es necesario y luego presiona Enter...")
    finally:
        contexto.close()