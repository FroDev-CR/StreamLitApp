import pandas as pd
from io import StringIO
from playwright.sync_api import sync_playwright

from config_ea import USERNAME, PASSWORD, SUPPLYPRO_URL


def ejecutar_extraccion() -> pd.DataFrame:
    """
    Accede a SupplyPro con credenciales E&A, aplica el filtro
    'Show All Except EPOs' y retorna el DataFrame crudo de la tabla.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-setuid-sandbox',
            ],
        )
        page = browser.new_page()
        try:
            # Login
            page.goto(SUPPLYPRO_URL, wait_until='networkidle', timeout=30_000)
            page.fill('#user_name', USERNAME)
            page.wait_for_timeout(100)
            page.fill('#password', PASSWORD)
            page.click("input[type='submit']")
            page.wait_for_load_state('networkidle', timeout=30_000)

            # Sesión duplicada: rellenar password, marcar Force Sign In y reenviar
            force_checkbox = page.query_selector('input[name="force_signon"]')
            if force_checkbox:
                page.fill('#password', PASSWORD)
                force_checkbox.check()
                page.click("input[name='cmdSubmit']")
                page.wait_for_load_state('networkidle', timeout=30_000)

            # Verificar que el login fue exitoso
            page_text = page.inner_text('body')
            if 'Invalid' in page_text or 'incorrect' in page_text.lower():
                raise RuntimeError("Credenciales incorrectas.")

            # Navegar a Newly Received Orders
            # El link puede estar dentro de un submenú oculto — intentamos
            # via JS para evitar el bloqueo de visibilidad del menú
            clicked = page.evaluate("""
                () => {
                    const links = [...document.querySelectorAll('a')];
                    const target = links.find(a => a.textContent.trim() === 'Newly Received Orders');
                    if (target) { target.click(); return true; }
                    return false;
                }
            """)
            if not clicked:
                raise RuntimeError("No se encontró el link 'Newly Received Orders' en la página.")
            page.wait_for_selector('[name="ref_epo_filter"]', timeout=30_000)

            # Filtro Show All Except EPOs
            page.select_option('[name="ref_epo_filter"]', label='Show All Except EPOs')
            page.wait_for_timeout(5_000)

            # Extraer tabla (buscar por cabecera "Builder")
            th = page.locator('th:has-text("Builder")').first
            table_html = th.locator('xpath=ancestor::table').first.evaluate(
                'el => el.outerHTML'
            )

            df = pd.read_html(StringIO(table_html))[0]

            # Cerrar sesión
            try:
                page.click('text=Sign Out', timeout=5_000)
                page.wait_for_timeout(2_000)
            except Exception:
                pass

            return df

        finally:
            browser.close()
