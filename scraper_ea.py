import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import StringIO
from urllib.parse import urljoin

from config_ea import USERNAME, PASSWORD, SUPPLYPRO_URL

BASE_URL = 'https://www.hyphensolutions.com/MH2Supply/'
HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )
}


def _form_data(soup) -> tuple[dict, str]:
    """Extrae datos e action de un <form>."""
    form = soup.find('form')
    data = {
        inp.get('name'): inp.get('value', '')
        for inp in form.find_all('input')
        if inp.get('name')
    }
    action = urljoin(BASE_URL, form.get('action', 'Login.asp'))
    return data, action


def ejecutar_extraccion() -> pd.DataFrame:
    """
    Extrae la tabla de órdenes de SupplyPro para E&A usando HTTP directo.
    No requiere browser — compatible con Streamlit Cloud.
    """
    session = requests.Session()
    session.headers.update(HEADERS)

    # ── 1. GET login page ──────────────────────────────────────────────────
    resp = session.get(SUPPLYPRO_URL, timeout=30)
    resp.raise_for_status()

    # ── 2. POST credenciales ───────────────────────────────────────────────
    data, action = _form_data(BeautifulSoup(resp.text, 'lxml'))
    data['user_name'] = USERNAME
    data['password']  = PASSWORD
    resp = session.post(action, data=data, timeout=30)
    resp.raise_for_status()

    # ── 3. Sesión duplicada: releer form y reenviar con force_signon ───────
    if 'force_signon' in resp.text:
        data2, action2 = _form_data(BeautifulSoup(resp.text, 'lxml'))
        data2['user_name']    = USERNAME
        data2['password']     = PASSWORD
        data2['force_signon'] = 'on'
        resp = session.post(action2, data=data2, timeout=30)
        resp.raise_for_status()

    # ── 4. Buscar link "Newly Received Orders" ─────────────────────────────
    soup = BeautifulSoup(resp.text, 'lxml')
    link = soup.find('a', string=lambda s: s and 'Newly Received Orders' in s)
    if not link:
        raise RuntimeError(
            "No se encontró 'Newly Received Orders'. "
            "Posible error de login o cambio en la interfaz."
        )

    resp = session.get(link['href'], timeout=30)
    resp.raise_for_status()

    # ── 5. Aplicar filtro "Show All Except EPOs" ───────────────────────────
    soup = BeautifulSoup(resp.text, 'lxml')
    select = soup.find('select', {'name': 'ref_epo_filter'})
    if not select:
        raise RuntimeError("No se encontró el filtro 'ref_epo_filter'.")

    filter_form = select.find_parent('form')
    if not filter_form:
        raise RuntimeError("No se encontró el formulario del filtro.")

    # Recolectar todos los inputs del form
    filter_data = {
        inp.get('name'): inp.get('value', '')
        for inp in filter_form.find_all('input')
        if inp.get('name')
    }
    # Todos los selects con su valor actual, excepto ref_epo_filter
    for sel_el in filter_form.find_all('select'):
        name = sel_el.get('name')
        if name and name != 'ref_epo_filter':
            selected = sel_el.find('option', selected=True)
            filter_data[name] = selected.get('value', '') if selected else ''

    # Valor "Show All Except EPOs" = 'N' (confirmado por inspección)
    filter_data['ref_epo_filter'] = 'N'

    filter_url = filter_form.get('action', link['href'])
    resp = session.post(filter_url, data=filter_data, timeout=60)
    resp.raise_for_status()

    # ── 6. Extraer tabla ───────────────────────────────────────────────────
    soup = BeautifulSoup(resp.text, 'lxml')
    th = next(
        (t for t in soup.find_all('th') if 'Builder' in t.get_text()),
        None,
    )
    if not th:
        raise RuntimeError("No se encontró la tabla de órdenes en la respuesta.")

    table_html = str(th.find_parent('table'))
    df = pd.read_html(StringIO(table_html))[0]

    # ── 7. Cerrar sesión ───────────────────────────────────────────────────
    try:
        sign_out = soup.find('a', string=lambda s: s and 'Sign Out' in s)
        if sign_out:
            session.get(sign_out['href'], timeout=10)
    except Exception:
        pass

    return df
