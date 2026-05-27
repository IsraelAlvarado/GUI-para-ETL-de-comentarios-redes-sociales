# ◈ ETL Sentiment App

> Pipeline de extracción, limpieza, transformación y visualización de comentarios de redes sociales, con almacenamiento en MongoDB Atlas y GUI de escritorio en PySide6.

---

## Tabla de contenidos

1. [Descripción general](#descripción-general)
2. [Arquitectura del pipeline ETL](#arquitectura-del-pipeline-etl)
3. [Tecnologías utilizadas](#tecnologías-utilizadas)
4. [Estructura del proyecto](#estructura-del-proyecto)
5. [Instalación y configuración](#instalación-y-configuración)
6. [Variables de entorno](#variables-de-entorno)
7. [Uso de la aplicación](#uso-de-la-aplicación)
8. [Módulos principales](#módulos-principales)
9. [Análisis de sentimientos](#análisis-de-sentimientos)
10. [Base de datos](#base-de-datos)
11. [Capturas de pantalla](#capturas-de-pantalla)
12. [Contribución](#contribución)

---

## Descripción general

**ETL Sentiment App** es una aplicación de escritorio que automatiza el ciclo completo de análisis de sentimientos sobre textos provenientes de redes sociales u otras fuentes. El flujo integra tres fases clásicas de ingeniería de datos:

```
  [Texto crudo]
       │
  ┌────▼─────┐
  │ EXTRACT  │  Entrada manual o carga masiva desde CSV / Excel / TSV
  └────┬─────┘
       │
  ┌────▼───────┐
  │ TRANSFORM  │  Limpieza NLP, normalización, extracción de features,
  │            │  análisis de polaridad y subjetividad (TextBlob)
  └────┬───────┘
       │
  ┌────▼─────┐
  │  LOAD    │  Inserción en MongoDB Atlas con metadatos enriquecidos
  └────┬─────┘
       │
  ┌────▼──────────┐
  │  DASHBOARD    │  Visualización de distribuciones, categorías y tabla
  └───────────────┘
```

---

## Arquitectura del pipeline ETL

### E — Extract

- **Entrada manual:** el usuario escribe o pega un comentario en la interfaz.
- **Carga masiva:** selección de un archivo `.csv`, `.tsv`, `.xlsx` o `.xls`. El sistema detecta automáticamente las columnas de tipo texto y permite elegir la columna objetivo.

### T — Transform

El módulo `ETLEngine.transform()` aplica los siguientes pasos en orden:

| Paso | Operación | Detalle |
|------|-----------|---------|
| 1 | Normalización Unicode | `unicodedata.normalize("NFC", ...)` |
| 2 | Limpieza estructural | Elimina URLs, `@menciones`, `#hashtags` y símbolos |
| 3 | Normalización léxica | Lowercase, colapso de espacios múltiples |
| 4 | Métricas básicas | Palabras, oraciones, caracteres, longitud media |
| 5 | Filtrado de stopwords | ES + EN integradas, sin dependencias externas |
| 6 | Análisis de sentimiento | `TextBlob` → polaridad `[-1, 1]` y subjetividad `[0, 1]` |
| 7 | Clasificación | 8 categorías + nivel de intensidad |

### L — Load

El documento final se inserta en la colección `analisis_sentimientos` de MongoDB Atlas con la siguiente estructura:

```json
{
  "hashtag":      "ManualInput",
  "texto":        "Texto original del comentario",
  "texto_limpio": "texto normalizado sin ruido",
  "polaridad":    0.35,
  "subjetividad": 0.62,
  "categoria":    "Muy Positivo",
  "intensidad":   "Media",
  "metricas": {
    "num_palabras":         12,
    "num_oraciones":        2,
    "num_caracteres":       58,
    "avg_longitud_palabra": 4.25,
    "densidad_lexica":      0.583,
    "palabras_clave":       ["producto", "excelente", "recomiendo"]
  },
  "fecha": "2025-06-01T14:22:10.123Z"
}
```

---

## Tecnologías utilizadas

| Capa | Tecnología | Versión |
|------|-----------|---------|
| GUI de escritorio | PySide6 | 6.11.1 |
| Gráficas embebidas | Matplotlib (backend QtAgg) | — |
| NLP / Sentimientos | TextBlob | 0.20.0 |
| Tokenización NLTK | NLTK | 3.9.4 |
| Manipulación de datos | Pandas | 3.0.3 |
| Cálculo numérico | NumPy | 2.4.6 |
| Base de datos | MongoDB Atlas (pymongo) | 4.17.0 |
| Variables de entorno | python-dotenv | — |
| Lenguaje | Python | ≥ 3.10 |

---

## Estructura del proyecto

```
ETL/
├── main.py                     # Punto de entrada; inicializa QApplication y DB
├── requirements.txt
├── .env                        # Credenciales (no versionar)
└── src/
    ├── __init__.py
    ├── database.py             # DatabaseManager → conexión MongoDB Atlas
    ├── etl_engine.py           # ETLEngine: lógica Extract / Transform / Load
    ├── processor.py            # SentimentProcessor (wrapper TextBlob legado)
    ├── gui.py                  # MainWindow + router de login
    └── views/
        ├── login_view.py       # LoginWidget — pantalla de autenticación
        └── dashboard_view.py   # AnalisisView, DashboardView, AppLayout
```

---

## Instalación y configuración

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/etl-sentiment-app.git
cd etl-sentiment-app/ETL
```

### 2. Crear y activar entorno virtual

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Descargar corpus NLTK requerido por TextBlob

```python
python -c "import nltk; nltk.download('punkt'); nltk.download('averaged_perceptron_tagger')"
```

### 5. Configurar variables de entorno

Crea el archivo `.env` en la raíz del proyecto (ver sección siguiente).

### 6. Ejecutar la aplicación

```bash
python main.py
```

---

## Variables de entorno

Crea un archivo `.env` en `ETL/` con el siguiente contenido:

```env
DB_USER=tu_usuario_mongodb
DB_PASS=tu_contraseña_mongodb
DB_CLUSTER=cluster0.xxxxxxx.mongodb.net
```

> **Importante:** nunca subas `.env` al repositorio. Agrega la línea `.env` a tu `.gitignore`.

---

## Uso de la aplicación

### Credenciales de acceso

| Usuario | Contraseña | Rol |
|---------|-----------|-----|
| `admin` | `root` | Administrador — acceso completo |
| `user` | `root` | Lectura — solo Dashboard |

### Análisis individual (admin)

1. Escribe o pega el texto en el campo **Texto de entrada**.
2. Presiona **▶ Ejecutar ETL** o la tecla `Enter`.
3. El pipeline muestra su progreso: Extract → Transform → Load.
4. El resultado aparece como una tarjeta con polaridad, subjetividad, intensidad, categoría y palabras clave.

### Carga masiva desde archivo (admin)

1. Haz clic en **📂 Seleccionar archivo…** y elige un `.csv`, `.tsv`, `.xlsx` o `.xls`.
2. Selecciona la columna que contiene el texto a analizar.
3. Presiona **⚡ Procesar Dataset**.
4. La barra de progreso muestra el avance fila por fila; las tarjetas se van generando en tiempo real.

### Dashboard (todos los roles)

- **Distribución de Polaridad** — histograma con los últimos 100 registros.
- **Registros por Categoría** — gráfica de barras horizontales por categoría de sentimiento.
- **Tabla de datos** — texto, polaridad (coloreada), subjetividad, categoría, intensidad y fecha.
- Botón **⟳ Actualizar** para refrescar desde MongoDB.

---

## Módulos principales

### `etl_engine.py` — ETLEngine

```python
# Uso básico
from src.etl_engine import ETLEngine

doc = ETLEngine.run("Este producto es absolutamente increíble, lo recomiendo!")
print(doc["polaridad"])   # → 0.65
print(doc["categoria"])   # → "Muy Positivo"
print(doc["intensidad"])  # → "Alta"
```

Métodos públicos:

| Método | Descripción |
|--------|-------------|
| `ETLEngine.extract(raw_text)` | Fase E: captura metadata de origen |
| `ETLEngine.transform(raw_text)` | Fase T: limpieza NLP completa + features |
| `ETLEngine.load(transformed, hashtag)` | Fase L: construye documento MongoDB |
| `ETLEngine.run(raw_text, hashtag)` | Pipeline E→T→L en un solo paso |

### `database.py` — DatabaseManager

```python
from src.database import DatabaseManager

db = DatabaseManager(
    user="tu_user",
    password="tu_pass",
    cluster_url="cluster0.abc.mongodb.net"
)

# Insertar documento
db.collection.insert_one(doc)

# Consultar últimos registros
resultados = list(db.collection.find().sort("fecha", -1).limit(100))
```

---

## Análisis de sentimientos

La clasificación utiliza dos dimensiones de TextBlob para producir 8 categorías:

| Categoría | Polaridad | Subjetividad |
|-----------|-----------|--------------|
| Muy Positivo | > 0.3 | > 0.5 |
| Positivo Objetivo | > 0.3 | ≤ 0.5 |
| Positivo | 0.05 – 0.3 | cualquiera |
| Neutral Subjetivo | -0.05 – 0.05 | > 0.5 |
| Neutral | -0.05 – 0.05 | ≤ 0.5 |
| Negativo | -0.3 – -0.05 | cualquiera |
| Negativo Objetivo | < -0.3 | ≤ 0.5 |
| Muy Negativo | < -0.3 | > 0.5 |

Niveles de intensidad según valor absoluto de polaridad:

| Intensidad | `\|polaridad\|` |
|-----------|----------------|
| Alta | ≥ 0.6 |
| Media | 0.3 – 0.6 |
| Baja | 0.05 – 0.3 |
| Mínima | < 0.05 |

---

## Base de datos

La aplicación se conecta a **MongoDB Atlas** usando una URI SRV:

```
mongodb+srv://<user>:<password>@<cluster>/?retryWrites=true&w=majority
```

- **Base de datos:** `SentimentAnalysisDB`
- **Colección:** `analisis_sentimientos`
- **Índice sugerido:** campo `fecha` (descendente) para acelerar la consulta del dashboard.

```javascript
// Crear índice en MongoDB Shell
db.analisis_sentimientos.createIndex({ fecha: -1 })
```

---



> Desarrollado con Python · PySide6 · MongoDB Atlas · TextBlob

<img width="2545" height="1595" alt="image" src="https://github.com/user-attachments/assets/ca8443c7-c00c-4a8b-b87f-979292e9c1ac" />
<img width="2555" height="1600" alt="image" src="https://github.com/user-attachments/assets/88ce68c3-aa7f-42b8-94f3-fa9487c041f6" />
<img width="2560" height="1579" alt="image" src="https://github.com/user-attachments/assets/e21fd3b8-af4a-46f9-ae7d-acecb246fb6c" />
<img width="2552" height="1600" alt="image" src="https://github.com/user-attachments/assets/852dacb5-ee8b-4d38-9f46-da8b14237f97" />
<img width="2550" height="1600" alt="image" src="https://github.com/user-attachments/assets/6e5deb33-8b2d-4778-9beb-d6bf24f04250" />
<img width="2494" height="1305" alt="image" src="https://github.com/user-attachments/assets/5483fa40-69e1-486a-94d5-d83e9b9965fb" />





