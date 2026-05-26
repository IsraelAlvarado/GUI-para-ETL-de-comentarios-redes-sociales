"""
database.py — Gestión de conexión y operaciones MongoDB.
"""
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient, DESCENDING


class DatabaseManager:
    def __init__(self, user: str, password: str, cluster_url: str,
                 db_name: str = "SentimentAnalysisDB"):
        self.uri = (
            f"mongodb+srv://{user}:{password}@{cluster_url}/"
            "?retryWrites=true&w=majority"
        )
        self.client     = MongoClient(self.uri, serverSelectionTimeoutMS=8000)
        self.db         = self.client[db_name]
        self.collection = self.db["analisis_sentimientos"]

    # ── Lectura ───────────────────────────────────────────────────────────────
    def get_all(self, limit: int = 200) -> list:
        """Retorna los últimos `limit` documentos ordenados por fecha desc."""
        return list(self.collection.find().sort("fecha", DESCENDING).limit(limit))

    def get_count(self) -> int:
        return self.collection.count_documents({})

    def search(self, query: str, limit: int = 200) -> list:
        """Búsqueda por texto en campos texto / categoria / hashtags / idioma."""
        pattern = {"$regex": query, "$options": "i"}
        return list(
            self.collection.find(
                {"$or": [
                    {"texto":     pattern},
                    {"categoria": pattern},
                    {"idioma":    pattern},
                    {"intensidad": pattern},
                    {"hashtags":  pattern},
                ]}
            ).sort("fecha", DESCENDING).limit(limit)
        )

    # ── Escritura / eliminación ───────────────────────────────────────────────
    def insert(self, doc: dict):
        return self.collection.insert_one(doc)

    def delete_by_ids(self, ids: list[str]) -> int:
        """Elimina documentos por lista de ObjectId strings."""
        object_ids = []
        for i in ids:
            try:
                object_ids.append(ObjectId(i))
            except Exception:
                pass
        if not object_ids:
            return 0
        result = self.collection.delete_many({"_id": {"$in": object_ids}})
        return result.deleted_count

    def delete_all(self) -> int:
        result = self.collection.delete_many({})
        return result.deleted_count

    # ── Export ────────────────────────────────────────────────────────────────
    def export_all(self) -> list:
        """Retorna todos los documentos sin límite (para exportar a CSV/JSON)."""
        return list(self.collection.find().sort("fecha", DESCENDING))

    def test_connection(self) -> bool:
        """Verifica la conexión al cluster."""
        try:
            self.client.admin.command("ping")
            return True
        except Exception:
            return False

    def close(self):
        self.client.close()