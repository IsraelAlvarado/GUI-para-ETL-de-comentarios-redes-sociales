import re
import unicodedata
from datetime import datetime
from textblob import TextBlob
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure

# ── Stopwords en español e inglés (mínimas, sin dependencias extra) ────────────
_STOPWORDS_ES = {
    "de", "la", "el", "en", "y", "a", "los", "las", "un", "una",
    "es", "se", "que", "por", "con", "su", "para", "como", "más",
    "pero", "si", "ya", "también", "del", "al", "lo", "le", "da",
}
_STOPWORDS_EN = {
    "the", "a", "an", "is", "in", "it", "of", "to", "and", "for",
    "on", "with", "at", "by", "this", "that", "are", "was", "be",
    "as", "or", "but", "not", "from", "have", "had", "has", "he",
    "she", "we", "they", "i", "you",
}
STOPWORDS = _STOPWORDS_ES | _STOPWORDS_EN


class ETLEngine:
    """
    Encapsula las tres fases del proceso ETL sobre texto.

    Uso rápido:
        resultado = ETLEngine.run("Hola mundo, esto es una prueba!")
        print(resultado["polaridad"], resultado["categoria"])
    """

    # ── EXTRACT ───────────────────────────────────────────────────────────────
    @staticmethod
    def extract(raw_text: str) -> dict:
        """
        Fase E: recibe texto crudo y devuelve metadata de origen.
        En una versión real aquí se conectaría a la API / archivo / stream.
        """
        return {
            "raw_text":  raw_text,
            "source":    "ManualInput",
            "timestamp": datetime.now(),
        }

    # ── TRANSFORM ─────────────────────────────────────────────────────────────
    @staticmethod
    def transform(raw_text: str) -> dict:
        """
        Fase T: limpieza, normalización y extracción de features.

        Pasos:
          1. Normalización unicode  → quita acentos raros, normaliza a NFC
          2. Limpieza estructural   → URLs, menciones, hashtags, emojis
          3. Normalización léxica   → lowercase, espacios múltiples
          4. Métricas básicas       → longitud, palabras, oraciones
          5. Filtrado de stopwords  → palabras con contenido semántico
          6. Análisis de sentimiento(TextBlob sobre texto limpio)
          7. Clasificación          → categoría + intensidad
        """

        # 1. Normalización unicode
        text_nfc = unicodedata.normalize("NFC", raw_text)

        # 2. Limpieza estructural
        text_clean = re.sub(r"https?://\S+|www\.\S+", "", text_nfc)   # URLs
        text_clean = re.sub(r"@\w+", "", text_clean)                   # menciones
        text_clean = re.sub(r"#\w+", "", text_clean)                   # hashtags
        text_clean = re.sub(r"[^\w\s\.,!?áéíóúüñÁÉÍÓÚÜÑ]", " ", text_clean)  # símbolos

        # 3. Normalización léxica
        text_lower = text_clean.lower().strip()
        text_norm  = re.sub(r"\s+", " ", text_lower)

        # 4. Métricas básicas
        sentences  = [s.strip() for s in re.split(r"[.!?]+", text_norm) if s.strip()]
        words_all  = text_norm.split()
        word_count = len(words_all)
        char_count = len(text_norm.replace(" ", ""))
        avg_word_len = (
            round(sum(len(w) for w in words_all) / word_count, 2)
            if word_count else 0
        )

        # 5. Palabras con contenido semántico (sin stopwords)
        content_words = [w for w in words_all if w.isalpha() and w not in STOPWORDS]
        lexical_density = (
            round(len(content_words) / word_count, 3) if word_count else 0
        )

        # 6. Análisis de sentimiento
        blob        = TextBlob(text_norm)
        polaridad   = round(blob.sentiment.polarity, 4)
        subjetividad = round(blob.sentiment.subjectivity, 4)

        # 7. Clasificación
        categoria  = ETLEngine._clasificar(polaridad, subjetividad)
        intensidad = ETLEngine._intensidad(polaridad)

        return {
            # Texto procesado
            "texto_original": raw_text.strip(),
            "texto_limpio":   text_norm,
            # Métricas de texto
            "num_palabras":   word_count,
            "num_oraciones":  len(sentences),
            "num_caracteres": char_count,
            "avg_longitud_palabra": avg_word_len,
            "densidad_lexica": lexical_density,
            "palabras_clave": content_words[:10],  # top 10 palabras de contenido
            # Sentimiento
            "polaridad":      polaridad,
            "subjetividad":   subjetividad,
            # Clasificación derivada
            "categoria":      categoria,
            "intensidad":     intensidad,
        }

    # ── LOAD ──────────────────────────────────────────────────────────────────
    @staticmethod
    def load(transformed: dict, hashtag: str = "ManualInput") -> dict:
        """
        Fase L: construye el documento final listo para insertar en MongoDB.
        Añade metadatos de carga y el hashtag de agrupación.
        """
        return {
            "hashtag":         hashtag,
            "texto":           transformed["texto_original"],
            "texto_limpio":    transformed["texto_limpio"],
            "polaridad":       transformed["polaridad"],
            "subjetividad":    transformed["subjetividad"],
            "categoria":       transformed["categoria"],
            "intensidad":      transformed["intensidad"],
            "metricas": {
                "num_palabras":        transformed["num_palabras"],
                "num_oraciones":       transformed["num_oraciones"],
                "num_caracteres":      transformed["num_caracteres"],
                "avg_longitud_palabra":transformed["avg_longitud_palabra"],
                "densidad_lexica":     transformed["densidad_lexica"],
                "palabras_clave":      transformed["palabras_clave"],
            },
            "fecha": datetime.now(),
        }

    # ── Pipeline completo ─────────────────────────────────────────────────────
    @classmethod
    def run(cls, raw_text: str, hashtag: str = "ManualInput") -> dict:
        """
        Ejecuta E → T → L y devuelve el documento MongoDB.
        """
        if not raw_text or not raw_text.strip():
            raise ValueError("El texto de entrada no puede estar vacío.")

        transformed = cls.transform(raw_text)
        document    = cls.load(transformed, hashtag)
        return document

    # ── Helpers de clasificación ──────────────────────────────────────────────
    @staticmethod
    def _clasificar(polaridad: float, subjetividad: float) -> str:
        if polaridad >  0.3:
            return "Muy Positivo" if subjetividad > 0.5 else "Positivo Objetivo"
        elif polaridad >  0.05:
            return "Positivo"
        elif polaridad < -0.3:
            return "Muy Negativo" if subjetividad > 0.5 else "Negativo Objetivo"
        elif polaridad < -0.05:
            return "Negativo"
        else:
            return "Neutral Subjetivo" if subjetividad > 0.5 else "Neutral"

    @staticmethod
    def _intensidad(polaridad: float) -> str:
        abs_pol = abs(polaridad)
        if abs_pol >= 0.6:  return "Alta"
        if abs_pol >= 0.3:  return "Media"
        if abs_pol >= 0.05: return "Baja"
        return "Mínima"