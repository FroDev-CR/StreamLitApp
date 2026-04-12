import re
import pandas as pd
from io import StringIO

from config_ea import CLIENT_NAME_MAP


def transformar_ordenes(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Transforma el DataFrame crudo de SupplyPro al formato final E&A.
    Replica la lógica de Spe_EA.py usando operaciones en memoria
    en lugar de archivos temporales.
    """
    # Replicar el roundtrip CSV para preservar la estructura exacta
    # (la tabla de SupplyPro tiene ~56 filas de metadatos antes del encabezado real)
    csv_str = df_raw.to_csv(index=False)
    raw = pd.read_csv(StringIO(csv_str), header=None, dtype=str)

    sub = raw.iloc[57:-4].reset_index(drop=True) if len(raw) > 61 else raw.copy()

    headers = [str(x).strip().replace('\n', ' ') for x in sub.iloc[0]]
    df = sub.iloc[1:].copy()
    df.columns = headers
    df = df.reset_index(drop=True)
    df = df.map(lambda v: str(v).strip().replace('\n', ' '))

    # Renombrar columnas
    df.rename(columns={
        'Builder Order #':            'Number order',
        'Account':                    'Client Name',
        'Subdivision':                'Job title',
        'Lot / Block Plan/Elv/Swing': 'lote number',
        'Job Address':                'Job Address',
        'Task Task Filter':           'instruction',
        'Total Excl Tax':             'total',
        'Request Acknowledged Actual':'Start Date',
    }, inplace=True)

    drop_cols = [
        c for c in df.columns
        if any(x in c for x in ['Supplier Order', 'Order Status', 'Builder Status'])
    ]
    df.drop(columns=drop_cols, inplace=True)

    # Fecha: conservar solo MM/DD/YYYY
    df['Start Date'] = df['Start Date'].apply(
        lambda x: m.group(0) if (m := re.search(r'\d{1,2}/\d{1,2}/\d{4}', x)) else ''
    )

    # Dirección limpia
    df['Full Property Address'] = (
        df['Job Address'].astype(str).str.strip()
        .str.replace('Lennar Options from CRM', '', regex=False)
        .str.replace('\u00C2', '', regex=False)
        .str.replace('\u00A0+', ' ', regex=True)
        .str.strip()
    )
    df.drop(columns=['Job Address'], inplace=True)

    # Normalizar Client Name
    df['Client Name'] = df['Client Name'].apply(
        lambda x: next(
            (rep for pat, rep in CLIENT_NAME_MAP.items() if re.match(pat, x)),
            x
        )
    )

    # Limpiar instruction
    df['instruction'] = (
        df['instruction']
        .str.replace(r'\s*[\(\[].*?[\)\]]', '', regex=True)
        .str.replace(r'^Concrete Labor -\s*', '', regex=True)
        .str.strip()
    )

    # Lote: primeros 4 dígitos
    df['lote number'] = df['lote number'].str.extract(r'^(\d{4})')[0].fillna('')

    # Subdivisión limpia
    df['job_title_clean'] = (
        df['Job title']
        .str.replace(r'^GAL\s*-\s*', '', regex=True)
        .str.replace(r'\d+', '', regex=True)
        .str.strip()
    )

    # Campo compuesto final
    df['Job title Final'] = df.apply(
        lambda r: f"{r['job_title_clean']} / LOT {r['lote number']} / {r['instruction']}",
        axis=1,
    )

    # Filtrar filas inválidas
    df = df[
        df['Number order'].notna() &
        df['Number order'].str.strip().ne('') &
        (df['Number order'].str.lower() != 'nan')
    ]

    # Columnas finales
    final = df[['Client Name', 'Job title Final', 'Full Property Address', 'total', 'Start Date']]
    final = final[
        ~final.apply(lambda row: row.astype(str).str.lower().eq('nan').any(), axis=1)
    ]

    return final.reset_index(drop=True)
