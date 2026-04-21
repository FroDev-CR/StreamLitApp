# 📦 WorkSync — E&A

Aplicación web para extraer órdenes de SupplyPro y crearlas automáticamente en Jobber, desarrollada para **E&A Concrete LLC**.

## Funcionalidades

- Extracción automática de órdenes desde SupplyPro (sin necesidad de browser)
- Tabla editable para revisar y seleccionar órdenes antes de subir
- Creación automática de clientes, propiedades y jobs en Jobber vía API
- Descarga de órdenes en CSV y Excel
- Reporte de subida con links directos a cada job en Jobber
- Interfaz en español e inglés

## Stack

- **Streamlit** — interfaz web
- **requests + BeautifulSoup** — scraping de SupplyPro
- **Jobber GraphQL API** — creación de jobs (OAuth 2.0)
- **pandas / openpyxl** — procesamiento y exportación de datos

## Configuración en Streamlit Cloud

En **Manage app → Settings → Secrets**, agrega:

```toml
JOBBER_CLIENT_ID     = "tu_client_id"
JOBBER_CLIENT_SECRET = "tu_client_secret"
APP_URL              = "https://tu-app.streamlit.app/"
```

El `APP_URL` debe coincidir exactamente con el **Redirect URI** configurado en tu app de Jobber.

## Uso

1. Abre la app y conecta tu cuenta de Jobber desde el panel izquierdo
2. Haz clic en **Exportar órdenes de SupplyPro**
3. Revisa la tabla, desmarca las órdenes que no quieras subir
4. Haz clic en **Subir a Jobber**
5. Descarga el reporte con los links a cada job creado
