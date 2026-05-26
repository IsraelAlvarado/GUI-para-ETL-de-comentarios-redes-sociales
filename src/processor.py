from textblob import TextBlob

class SentimentProcessor:
    @staticmethod
    def analizar(texto):
        """
        Analiza el texto y retorna (polaridad, subjetividad).
        Polaridad: -1.0 (muy negativo) a 1.0 (muy positivo).
        Subjetividad: 0.0 (objetivo) a 1.0 (subjetivo).
        """
        analysis = TextBlob(texto)
        return analysis.sentiment.polarity, analysis.sentiment.subjectivity