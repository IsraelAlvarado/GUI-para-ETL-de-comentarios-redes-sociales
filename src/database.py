from pymongo import MongoClient
from datetime import datetime

class DatabaseManager:
    def __init__(self, user, password, cluster_url, db_name="SentimentAnalysisDB"):
        # Construimos la URI correctamente con tus credenciales
        self.uri = f"mongodb+srv://{user}:{password}@{cluster_url}/?retryWrites=true&w=majority"
        self.client = MongoClient(self.uri)
        self.db = self.client[db_name]
        self.collection = self.db["analisis_sentimientos"]

    def insertar_resultado(self, hashtag, texto, polaridad, subjetividad):
        documento = {
            "hashtag": hashtag,
            "texto": texto,
            "polaridad": polaridad,
            "subjetividad": subjetividad,
            "fecha": datetime.now()
        }
        return self.collection.insert_one(documento)

    def obtener_todos(self, hashtag):
        """Recupera los registros de un hashtag específico para el dashboard."""
        return list(self.collection.find({"hashtag": hashtag}))

    def cerrar_conexion(self):
        self.client.close()