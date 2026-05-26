"""
etl_engine.py — Pipeline ETL sobre texto.
Fases: Extract → Transform → Load

Mejoras sobre v1:
  - Eliminados imports de matplotlib (no corresponden aquí)
  - Extrae hashtags, menciones y URLs ANTES de limpiar el texto
  - Mejor scoring de palabras clave (frecuencia + longitud)
  - Detección de idioma dominante (ES / EN / MIX)
  - Detección de negaciones y énfasis (caps ratio)
  - Conteo de emojis
  - Varianza de sentimiento por oración
  - Puntuación de legibilidad (aproximación Flesch adaptada)
"""

import re
import unicodedata
from collections import Counter
from datetime import datetime
from textblob import TextBlob


# ── Stop-words ────────────────────────────────────────────────────────────────
_SW_ES = {
    "de", "la", "el", "en", "y", "a", "los", "las", "un", "una", "es", "se",
    "que", "por", "con", "su", "para", "como", "más", "pero", "si", "ya",
    "también", "del", "al", "lo", "le", "da", "nos", "me", "mi", "tu", "te",
    "lo", "le", "les", "hay", "he", "ha", "han", "fue", "era", "son", "ser",
    "sus", "este", "esta", "ese", "esa", "muy", "bien", "así", "cada", "todo",
    "todos", "todas", "esto", "cuando", "donde", "porque", "sino", "aunque",
    "sin", "sobre", "entre", "hasta", "desde", "hacia", "ante", "bajo",
}
_SW_EN = {
    "the", "a", "an", "is", "in", "it", "of", "to", "and", "for", "on",
    "with", "at", "by", "this", "that", "are", "was", "be", "as", "or",
    "but", "not", "from", "have", "had", "has", "he", "she", "we", "they",
    "i", "you", "my", "your", "its", "our", "their", "do", "did", "will",
    "would", "could", "should", "been", "being", "so", "if", "then", "than",
    "when", "where", "which", "who", "what", "all", "there", "about", "up",
}
STOPWORDS = _SW_ES | _SW_EN

# Patrones de negación
_NEGATION_RE = re.compile(
    r"\b(no|nunca|jamás|tampoco|ni|never|not|don't|doesn't|isn't|wasn't|"
    r"wouldn't|couldn't|shouldn't|nada|nadie|ningún|ninguna)\b",
    re.IGNORECASE,
)

# Indicadores de idioma
_ES_MARKERS = {"que", "de", "en", "es", "la", "el", "los", "las", "y", "pero"}
_EN_MARKERS = {"the", "is", "are", "was", "were", "it", "this", "that", "you"}

# Regex para emojis (rango básico Unicode)
_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FFFF"
    "\U00002702-\U000027B0"
    "\U0000200D"
    "\U00002500-\U00002BEF]+",
    flags=re.UNICODE,
)


class ETLEngine:
    """
    Pipeline ETL sobre texto con análisis de sentimiento y métricas NLP.

    Uso rápido:
        doc = ETLEngine.run("Este producto es fantástico!")
        print(doc["polaridad"], doc["categoria"])
    """

    # ── EXTRACT ───────────────────────────────────────────────────────────────
    @staticmethod
    def extract(raw_text: str) -> dict:
        """Fase E: captura texto crudo + metadatos de origen."""
        hashtags  = re.findall(r"#(\w+)", raw_text)
        mentions  = re.findall(r"@(\w+)", raw_text)
        urls      = re.findall(r"https?://\S+|www\.\S+", raw_text)
        emojis    = _EMOJI_RE.findall(raw_text)

        return {
            "raw_text":   raw_text,
            "source":     "ManualInput",
            "timestamp":  datetime.now(),
            "hashtags":   hashtags,
            "menciones":  mentions,
            "urls":       urls,
            "num_emojis": len(emojis),
        }

    # ── TRANSFORM ─────────────────────────────────────────────────────────────
    @staticmethod
    def transform(raw_text: str) -> dict:
        """
        Fase T: limpieza, normalización y extracción de features.

        Pasos
        -----
        1. Captura metadatos estructurales (hashtags, menciones, emojis, URLs)
        2. Normalización unicode NFC
        3. Limpieza: URLs → menciones → hashtags → símbolos especiales
        4. Métricas de texto (palabras, oraciones, caracteres, avg word len)
        5. Detección de idioma dominante
        6. Detección de negación y énfasis (caps ratio)
        7. Palabras clave por frecuencia + longitud (filtradas por stopwords)
        8. Análisis de sentimiento con TextBlob
        9. Varianza de polaridad entre oraciones
        10. Legibilidad aproximada (índice Flesch adaptado)
        11. Clasificación: categoría + intensidad
        """
        # 1. Metadatos estructurales
        hashtags  = re.findall(r"#(\w+)", raw_text)
        mentions  = re.findall(r"@(\w+)", raw_text)
        urls      = re.findall(r"https?://\S+|www\.\S+", raw_text)
        emojis    = _EMOJI_RE.findall(raw_text)

        # Caps ratio: fracción de letras en mayúscula (antes de limpiar)
        letters = [c for c in raw_text if c.isalpha()]
        caps_ratio = round(
            sum(1 for c in letters if c.isupper()) / len(letters), 3
        ) if letters else 0.0

        # 2. Normalización unicode
        text_nfc = unicodedata.normalize("NFC", raw_text)

        # 3. Limpieza estructural
        t = re.sub(r"https?://\S+|www\.\S+", " ", text_nfc)
        t = re.sub(r"@\w+", " ", t)
        t = re.sub(r"#\w+", " ", t)
        t = _EMOJI_RE.sub(" ", t)
        t = re.sub(r"[^\w\s\.,!?áéíóúüñÁÉÍÓÚÜÑ]", " ", t)

        # 4. Normalización léxica
        text_norm = re.sub(r"\s+", " ", t.lower().strip())

        # 5. Métricas de texto
        sentences   = [s.strip() for s in re.split(r"[.!?]+", text_norm) if s.strip()]
        words_all   = text_norm.split()
        word_count  = len(words_all)
        char_count  = len(text_norm.replace(" ", ""))
        avg_word_len = (
            round(sum(len(w) for w in words_all) / word_count, 2)
            if word_count else 0.0
        )

        # 6. Detección de idioma
        word_set = set(words_all)
        es_score = len(word_set & _ES_MARKERS)
        en_score = len(word_set & _EN_MARKERS)
        if es_score > en_score:
            idioma = "ES"
        elif en_score > es_score:
            idioma = "EN"
        else:
            idioma = "MIX" if (es_score + en_score) > 0 else "UNK"

        # 7. Negaciones y palabras de contenido
        negation_count  = len(_NEGATION_RE.findall(text_norm))
        tiene_negacion  = negation_count > 0

        content_words = [
            w for w in words_all
            if w.isalpha() and w not in STOPWORDS and len(w) >= 3
        ]
        lexical_density = round(len(content_words) / word_count, 3) if word_count else 0.0

        # Palabras clave: frecuencia × bonus de longitud
        freq = Counter(content_words)
        scored = sorted(
            freq.items(),
            key=lambda x: x[1] * (1 + min(len(x[0]) / 10, 0.5)),
            reverse=True,
        )
        palabras_clave = [w for w, _ in scored[:10]]

        # 8. Sentimiento global
        blob         = TextBlob(text_norm)
        polaridad    = round(blob.sentiment.polarity, 4)
        subjetividad = round(blob.sentiment.subjectivity, 4)

        # Si hay negación fuerte, moderar polaridad positiva
        if tiene_negacion and negation_count >= 2 and polaridad > 0:
            polaridad = round(polaridad * 0.5, 4)

        # 9. Varianza de sentimiento por oración
        sent_pols = [
            TextBlob(s).sentiment.polarity
            for s in sentences if len(s.split()) >= 3
        ]
        if len(sent_pols) >= 2:
            mean_p  = sum(sent_pols) / len(sent_pols)
            variance = round(
                sum((p - mean_p) ** 2 for p in sent_pols) / len(sent_pols), 4
            )
        else:
            variance = 0.0

        # 10. Legibilidad (Flesch adaptado: 206.835 - 1.015*(W/S) - 84.6*(Syl/W))
        syllables_est = sum(_count_syllables(w) for w in words_all)
        if len(sentences) > 0 and word_count > 0:
            flesch = round(
                206.835
                - 1.015  * (word_count / len(sentences))
                - 84.6   * (syllables_est / word_count),
                1,
            )
            flesch = max(0.0, min(100.0, flesch))
        else:
            flesch = 0.0

        # 11. Clasificación
        categoria  = ETLEngine._clasificar(polaridad, subjetividad, tiene_negacion)
        intensidad = ETLEngine._intensidad(polaridad)

        return {
            # Texto
            "texto_original":      raw_text.strip(),
            "texto_limpio":        text_norm,
            # Metadatos estructurales
            "hashtags":            hashtags,
            "menciones":           mentions,
            "urls":                urls,
            "num_emojis":          len(emojis),
            "idioma":              idioma,
            "caps_ratio":          caps_ratio,
            # Métricas de texto
            "num_palabras":        word_count,
            "num_oraciones":       len(sentences),
            "num_caracteres":      char_count,
            "avg_longitud_palabra": avg_word_len,
            "densidad_lexica":     lexical_density,
            "palabras_clave":      palabras_clave,
            "legibilidad":         flesch,
            # Sentimiento
            "polaridad":           polaridad,
            "subjetividad":        subjetividad,
            "varianza_sentimiento": variance,
            "tiene_negacion":      tiene_negacion,
            "num_negaciones":      negation_count,
            # Clasificación
            "categoria":           categoria,
            "intensidad":          intensidad,
        }

    # ── LOAD ──────────────────────────────────────────────────────────────────
    @staticmethod
    def load(transformed: dict, source: str = "ManualInput") -> dict:
        """Fase L: construye el documento MongoDB listo para insertar."""
        return {
            "source":     source,
            "texto":      transformed["texto_original"],
            "texto_limpio": transformed["texto_limpio"],
            # Metadatos estructurales
            "hashtags":   transformed["hashtags"],
            "menciones":  transformed["menciones"],
            "idioma":     transformed["idioma"],
            "num_emojis": transformed["num_emojis"],
            # Sentimiento
            "polaridad":      transformed["polaridad"],
            "subjetividad":   transformed["subjetividad"],
            "varianza_sent":  transformed["varianza_sentimiento"],
            "tiene_negacion": transformed["tiene_negacion"],
            "categoria":      transformed["categoria"],
            "intensidad":     transformed["intensidad"],
            # Métricas
            "metricas": {
                "num_palabras":         transformed["num_palabras"],
                "num_oraciones":        transformed["num_oraciones"],
                "num_caracteres":       transformed["num_caracteres"],
                "avg_longitud_palabra": transformed["avg_longitud_palabra"],
                "densidad_lexica":      transformed["densidad_lexica"],
                "legibilidad":          transformed["legibilidad"],
                "caps_ratio":           transformed["caps_ratio"],
                "num_negaciones":       transformed["num_negaciones"],
                "palabras_clave":       transformed["palabras_clave"],
            },
            "fecha": datetime.now(),
        }

    # ── Pipeline completo ─────────────────────────────────────────────────────
    @classmethod
    def run(cls, raw_text: str, source: str = "ManualInput") -> dict:
        """Ejecuta E → T → L y retorna el documento MongoDB."""
        if not raw_text or not raw_text.strip():
            raise ValueError("El texto de entrada no puede estar vacío.")
        transformed = cls.transform(raw_text)
        return cls.load(transformed, source)

    # ── Clasificación ─────────────────────────────────────────────────────────
    @staticmethod
    def _clasificar(pol: float, subj: float, negacion: bool) -> str:
        if pol > 0.3:
            return "Muy Positivo" if subj > 0.5 else "Positivo Objetivo"
        elif pol > 0.05:
            return "Positivo"
        elif pol < -0.3:
            return "Muy Negativo" if subj > 0.5 else "Negativo Objetivo"
        elif pol < -0.05:
            return "Negativo"
        else:
            if negacion:
                return "Neutral Subjetivo"
            return "Neutral Subjetivo" if subj > 0.5 else "Neutral"

    @staticmethod
    def _intensidad(pol: float) -> str:
        a = abs(pol)
        if a >= 0.6:  return "Alta"
        if a >= 0.3:  return "Media"
        if a >= 0.05: return "Baja"
        return "Mínima"


# ── Helpers ───────────────────────────────────────────────────────────────────
def _count_syllables(word: str) -> int:
    """Estimación rápida de sílabas (vocales consecutivas = 1 sílaba)."""
    word  = word.lower()
    vowels = "aeiouáéíóúüàèìòù"
    count = 0
    prev_vowel = False
    for ch in word:
        is_v = ch in vowels
        if is_v and not prev_vowel:
            count += 1
        prev_vowel = is_v
    return max(1, count)