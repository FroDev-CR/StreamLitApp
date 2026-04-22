# Spe_EA.py
import os
import re
import sys
import tkinter as tk
from tkinter import messagebox, ttk
import pandas as pd
import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# -----------------------------------
# Determinar base_dir
# -----------------------------------
if getattr(sys, 'frozen', False):
    exec_dir = os.path.dirname(sys.executable)
    app_bundle_dir = os.path.abspath(os.path.join(exec_dir, '..'))
    BASE_DIR = os.path.abspath(os.path.join(app_bundle_dir, '..'))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

RAW_CSV    = os.path.join(BASE_DIR, "ordenes_extraidas.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "EAndA")

# -----------------------------------
# Credenciales E&A
# -----------------------------------
USERNAME = 'lucydp'
PASSWORD = 'ROSEGATE'

# -----------------------------------
# Reglas Client Name
# -----------------------------------
client_name_map = {
    r'^LGI Homes.*':           'LGI Homes',
    r'^DRB Group.*':           'DRB Group',
    r'^Lennar Homes.*':        'Lennar Homes',
    r'^Century Communities.*': 'Century Communities'
}

# -----------------------------------
# Extraer Órdenes
# -----------------------------------
def exportar_ordenes():
    driver = None
    try:
        # En macOS usar SafariDriver
        if sys.platform == 'darwin':
            safari_opts = webdriver.SafariOptions()
            driver = webdriver.Safari(options=safari_opts)
        else:
            # En Windows/Linux usar Chrome headless
            chrome_opts = webdriver.ChromeOptions()
            chrome_opts.add_argument('--headless')
            chrome_opts.add_argument('--disable-gpu')
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_opts)

        wait = WebDriverWait(driver, 30)

        # Login
        driver.get('https://www.hyphensolutions.com/MH2Supply/Login.asp')
        wait.until(EC.presence_of_element_located((By.ID, 'user_name'))).send_keys(USERNAME)
        driver.find_element(By.ID, 'password').send_keys(PASSWORD)
        driver.find_element(By.CSS_SELECTOR, "input[type='submit']").click()
        time.sleep(5)

        # Navegar y filtrar
        wait.until(EC.element_to_be_clickable((By.LINK_TEXT, 'Newly Received Orders'))).click()
        wait.until(EC.presence_of_element_located((By.NAME, 'ref_epo_filter')))
        Select(driver.find_element(By.NAME, 'ref_epo_filter')).select_by_visible_text('Show All Except EPOs')
        time.sleep(5)

        # Extraer tabla
        th  = driver.find_element(By.XPATH, "//th[contains(normalize-space(.),'Builder')]")
        tbl = th.find_element(By.XPATH, './ancestor::table')
        df  = pd.read_html(tbl.get_attribute('outerHTML'))[0]
        df.to_csv(RAW_CSV, index=False, encoding='utf-8-sig')

        # Cerrar sesión de SupplyPro
        try:
            driver.find_element(By.LINK_TEXT, 'Sign Out').click()
            time.sleep(2)
        except Exception:
            pass

    except Exception as e:
        messagebox.showerror('Error extracción', str(e))
    finally:
        if driver:
            driver.quit()

# -----------------------------------
# Transformar Órdenes
# -----------------------------------
def transformar_ordenes():
    try:
        raw = pd.read_csv(RAW_CSV, header=None, dtype=str, encoding='utf-8-sig')
        sub = raw.iloc[57:-4].reset_index(drop=True) if len(raw) > 61 else raw.copy()

        headers = [str(x).strip().replace('\n',' ') for x in sub.iloc[0]]
        df = sub.iloc[1:].copy()
        df.columns = headers
        df = df.applymap(lambda v: str(v).strip().replace('\n',' '))

        # Renombrar columnas
        df.rename(columns={
            'Builder Order #': 'Number order',
            'Account': 'Client Name',
            'Subdivision': 'Job title',
            'Lot / Block Plan/Elv/Swing': 'lote number',
            'Job Address': 'Job Address',
            'Task Task Filter': 'instruction',
            'Total Excl Tax': 'total',
            'Request Acknowledged Actual': 'Start Date'
        }, inplace=True)
        drop_cols = [c for c in df.columns if any(x in c for x in ['Supplier Order','Order Status','Builder Status'])]
        df.drop(columns=drop_cols, inplace=True)

        # Fecha única
        df['Start Date'] = df['Start Date'].apply(
            lambda x: re.search(r"\d{1,2}/\d{1,2}/\d{4}", x).group(0)
            if re.search(r"\d{1,2}/\d{1,2}/\d{4}", x) else ''
        )

        # Dirección
        df['Full Property Address'] = df['Job Address'].astype(str).str.strip()
        df['Full Property Address'] = (
            df['Full Property Address']
            .str.replace('Lennar Options from CRM','',regex=False)
            .str.replace('\u00C2','',regex=False)
            .str.replace('\u00A0+',' ',regex=True)
            .str.strip()
        )
        df.drop(columns=['Job Address'], inplace=True)

        # Limpiar Client Name
        df['Client Name'] = df['Client Name'].apply(
            lambda x: next((rep for pat,rep in client_name_map.items() if re.match(pat, x)), x)
        )

        # Limpiar instruction
        df['instruction'] = df['instruction']\
            .str.replace(r"\s*[\(\[].*?[\)\]]","",regex=True)\
            .str.replace(r"^Concrete Labor -\s*","",regex=True)\
            .str.strip()

        # Lote: solo primeros 4 dígitos antes de cualquier espacio o slash
        df['lote number'] = df['lote number'].str.extract(r'^(\d{4})')[0].fillna('')

        # Limpiar job title: elimina todos los dígitos
        df['job_title_clean'] = df['Job title']\
            .str.replace(r"^GAL\s*-\s*","",regex=True)\
            .str.replace(r"\d+","",regex=True)\
            .str.strip()

        # Construir Job title Final en nuevo orden: Subdivisión, Lote, Task
        df['Job title Final'] = df.apply(
            lambda r: f"{r['job_title_clean']} / LOT {r['lote number']} / {r['instruction']}",
            axis=1
        )

        # Filtrar filas válidas
        df = df[
            df['Number order'].notna() &
            df['Number order'].str.strip().ne('') &
            (df['Number order'].str.lower()!='nan')
        ]

        # Seleccionar y exportar
        final = df[['Client Name','Job title Final','Full Property Address','total','Start Date']]
        final = final[~final.apply(lambda row: row.astype(str).str.lower().eq('nan').any(),axis=1)]

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        final.to_csv(os.path.join(OUTPUT_DIR,'ordeneslistas.csv'), index=False, encoding='utf-8-sig')

    except Exception as e:
        messagebox.showerror('Error transformación', str(e))

# -----------------------------------
# GUI
# -----------------------------------
if __name__ == '__main__':
    root = tk.Tk()
    root.title('E&A SupplyPro Extractor')
    root.geometry('400x200')

    progreso = ttk.Progressbar(root, mode='indeterminate')

    def run_all():
        progreso.pack(fill='x', padx=20, pady=5)
        progreso.start(10)
        root.update_idletasks()
        exportar_ordenes()
        transformar_ordenes()
        progreso.stop()
        progreso.pack_forget()
        messagebox.showinfo('Éxito','Operación completada para E&A')

    tk.Button(root, text='Exportar órdenes de SupplyPro E&A', command=run_all,
              bg='#00C2FF', fg='white', height=2, width=30).pack(pady=40)
    root.mainloop()
