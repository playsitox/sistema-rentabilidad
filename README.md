# Sistema de Rentabilidad (Datos Persistentes)

Sistema multi-usuario para que negocios puedan:

1. **Analizar Costos y Precios** → margen real de cada producto  
2. **Ver el Estado de Situación de Rentabilidad** → radiografía completa  
3. **Proyectar Cash Flow** → anticipar liquidez y estabilidad  

Esta versión usa **Supabase (PostgreSQL)** para que los datos **no se borren** aunque la app se duerma.

---

## 1. Crear la base de datos en Supabase (gratis)

1. Andá a [supabase.com](https://supabase.com) y creá una cuenta
2. Click en **New project**
3. Elegí un nombre, una contraseña fuerte (guardala) y la región más cercana
4. Esperá 1-2 minutos a que se cree el proyecto
5. Andá a **Project Settings → Database**
6. Buscá la sección **Connection string** → **URI**
7. Copiá la URL que empieza con `postgresql://...`  
   (reemplazá `[YOUR-PASSWORD]` por la contraseña que elegiste)

---

## 2. Configurar el secreto en Streamlit Cloud

Después de subir el código a GitHub y crear la app en [share.streamlit.io](https://share.streamlit.io):

1. Entrá a tu app → **Settings** (o ⋮ → Settings)
2. Andá a la pestaña **Secrets**
3. Pegá exactamente esto (reemplazando la URL por la tuya):

```toml
DATABASE_URL = "postgresql://postgres.xxxxx:tu-password@aws-0-sa-east-1.pooler.supabase.com:6543/postgres"
```

4. Guardá y reiniciá la app

---

## 3. Subir a GitHub y desplegar

1. Creá un repositorio en GitHub
2. Subí todos los archivos de este proyecto
3. En [share.streamlit.io](https://share.streamlit.io) → **Create app**
4. Main file path: `app.py`
5. Configurá el secreto `DATABASE_URL` como se explicó arriba

---

## Cómo funciona

| Entorno              | Base de datos          | Datos se pierden? |
|----------------------|------------------------|-------------------|
| Local (sin secrets)  | SQLite                 | No (archivo local)|
| Streamlit Cloud + Supabase | PostgreSQL (Supabase) | **No**            |
| Streamlit Cloud sin secrets | SQLite (efímero)   | Sí                |

---

## Desarrollo local

```bash
pip install -r requirements.txt
streamlit run app.py
```

Para probar con Supabase en local, creá el archivo `.streamlit/secrets.toml` con tu `DATABASE_URL`.

---

## Estructura

```
├── app.py
├── requirements.txt
├── .gitignore
├── .streamlit/
│   └── secrets.toml.example
├── modules/
│   ├── cost_price_analyzer.py
│   ├── profitability_status.py
│   └── cashflow_projected.py
└── utils/
    ├── database.py          # Soporta SQLite + PostgreSQL
    └── auth.py
```
