"""
social_extractors.py — Conectores para extracción de texto desde redes sociales.
Cada clase verifica credenciales y dependencias antes de extraer.

Variables de entorno requeridas en .env:
  Twitter/X  → TWITTER_BEARER_TOKEN
  YouTube    → YT_API_KEY
  Reddit     → REDDIT_CLIENT_ID  +  REDDIT_CLIENT_SECRET
               REDDIT_USER_AGENT  (opcional, default: ETLSentimentApp/1.0)
  Instagram  → No disponible sin cuenta Business/Creator aprobada por Meta.
  Facebook   → No disponible sin aprobación de Graph API por Meta.
"""

import os
import re
import importlib.util
from typing import Callable


# ── Utilidades ────────────────────────────────────────────────────────────────

def _pkg_available(name: str) -> bool:
    """Devuelve True si el paquete Python está instalado."""
    return importlib.util.find_spec(name) is not None


class PlatformNotConfiguredError(Exception):
    """Se lanza cuando faltan variables de entorno requeridas."""


class PlatformNotInstalledError(Exception):
    """Se lanza cuando falta un paquete Python necesario."""


class PlatformUnavailableError(Exception):
    """Se lanza para plataformas sin soporte (Instagram, Facebook)."""


# ── Twitter / X ───────────────────────────────────────────────────────────────

class TwitterExtractor:
    NAME      = "Twitter / X"
    PACKAGE   = "tweepy"
    ENV_VARS  = ["TWITTER_BEARER_TOKEN"]
    INSTALL   = "pip install tweepy"

    @classmethod
    def is_installed(cls) -> bool:
        return _pkg_available(cls.PACKAGE)

    @classmethod
    def is_configured(cls) -> bool:
        return all(os.getenv(k) for k in cls.ENV_VARS)

    @classmethod
    def extract(
        cls,
        query: str,
        limit: int,
        progress_cb: Callable[[str], None] | None = None,
    ) -> list[str]:
        if not cls.is_installed():
            raise PlatformNotInstalledError(f"Instala tweepy: {cls.INSTALL}")
        if not cls.is_configured():
            raise PlatformNotConfiguredError(
                "Falta TWITTER_BEARER_TOKEN en .env"
            )

        import tweepy

        bearer = os.getenv("TWITTER_BEARER_TOKEN")
        client = tweepy.Client(bearer_token=bearer, wait_on_rate_limit=True)

        q = query.strip()
        if q.startswith("@"):
            search_q = f"from:{q[1:]} -is:retweet lang:es OR lang:en"
        elif q.startswith("#"):
            search_q = f"{q} -is:retweet lang:es OR lang:en"
        elif q.startswith("http"):
            # URL de tweet individual → devolver solo ese texto
            tweet_id = q.rstrip("/").split("/")[-1]
            resp = client.get_tweet(tweet_id, tweet_fields=["text"])
            return [resp.data.text] if resp.data else []
        else:
            search_q = f"{q} -is:retweet lang:es OR lang:en"

        texts = []
        try:
            paginator = tweepy.Paginator(
                client.search_recent_tweets,
                query=search_q,
                max_results=min(100, max(10, limit)),
                tweet_fields=["text", "lang"],
            )
            for tweet in paginator.flatten(limit=limit):
                texts.append(tweet.text)
                if progress_cb:
                    progress_cb(
                        f"[Twitter] #{len(texts)}  {tweet.text[:80].replace(chr(10), ' ')}…"
                    )
        except Exception as e:
            if progress_cb:
                progress_cb(f"[Twitter] Error: {e}")

        return texts


# ── YouTube ───────────────────────────────────────────────────────────────────

class YouTubeExtractor:
    NAME     = "YouTube"
    PACKAGE  = "googleapiclient"
    ENV_VARS = ["YT_API_KEY"]
    INSTALL  = "pip install google-api-python-client"

    @classmethod
    def is_installed(cls) -> bool:
        return _pkg_available("googleapiclient")

    @classmethod
    def is_configured(cls) -> bool:
        return bool(os.getenv("YT_API_KEY"))

    @staticmethod
    def _parse_video_id(raw: str) -> str:
        patterns = [
            r"(?:v=|/v/|youtu\.be/|/embed/)([A-Za-z0-9_\-]{11})",
            r"^([A-Za-z0-9_\-]{11})$",
        ]
        for p in patterns:
            m = re.search(p, raw)
            if m:
                return m.group(1)
        return raw.strip()

    @classmethod
    def extract(
        cls,
        url_or_id: str,
        limit: int,
        progress_cb: Callable[[str], None] | None = None,
    ) -> list[str]:
        if not cls.is_installed():
            raise PlatformNotInstalledError(f"Instala: {cls.INSTALL}")
        if not cls.is_configured():
            raise PlatformNotConfiguredError("Falta YT_API_KEY en .env")

        from googleapiclient.discovery import build

        api_key  = os.getenv("YT_API_KEY")
        video_id = cls._parse_video_id(url_or_id)
        youtube  = build("youtube", "v3", developerKey=api_key)

        texts     = []
        next_page = None

        while len(texts) < limit:
            try:
                resp = youtube.commentThreads().list(
                    part="snippet",
                    videoId=video_id,
                    maxResults=min(100, limit - len(texts)),
                    pageToken=next_page,
                    textFormat="plainText",
                    order="relevance",
                ).execute()
            except Exception as e:
                if progress_cb:
                    progress_cb(f"[YouTube] Error: {e}")
                break

            for item in resp.get("items", []):
                snippet = item["snippet"]["topLevelComment"]["snippet"]
                text = snippet.get("textDisplay", "").strip()
                if text:
                    texts.append(text)
                    if progress_cb:
                        progress_cb(
                            f"[YouTube] #{len(texts)}  {text[:80].replace(chr(10), ' ')}…"
                        )

            next_page = resp.get("nextPageToken")
            if not next_page:
                break

        return texts


# ── Reddit ────────────────────────────────────────────────────────────────────

class RedditExtractor:
    NAME     = "Reddit"
    PACKAGE  = "praw"
    ENV_VARS = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"]
    INSTALL  = "pip install praw"

    @classmethod
    def is_installed(cls) -> bool:
        return _pkg_available(cls.PACKAGE)

    @classmethod
    def is_configured(cls) -> bool:
        return all(os.getenv(k) for k in cls.ENV_VARS)

    @classmethod
    def extract(
        cls,
        target: str,
        limit: int,
        progress_cb: Callable[[str], None] | None = None,
    ) -> list[str]:
        if not cls.is_installed():
            raise PlatformNotInstalledError(f"Instala praw: {cls.INSTALL}")
        if not cls.is_configured():
            raise PlatformNotConfiguredError(
                "Faltan REDDIT_CLIENT_ID y REDDIT_CLIENT_SECRET en .env"
            )

        import praw

        reddit = praw.Reddit(
            client_id     = os.getenv("REDDIT_CLIENT_ID"),
            client_secret = os.getenv("REDDIT_CLIENT_SECRET"),
            user_agent    = os.getenv(
                "REDDIT_USER_AGENT", "ETLSentimentApp/1.0 by u/etlapp"
            ),
        )

        texts = []

        # Detectar si es URL de hilo específico o subreddit
        thread_m = re.search(r"reddit\.com/r/\w+/comments/(\w+)", target)
        sub_m    = re.search(r"r/(\w+)", target)

        if thread_m:
            # Hilo único
            post = reddit.submission(id=thread_m.group(1))
            body = (post.title + (" " + post.selftext) if post.selftext else post.title)
            texts.append(body.strip())
            if progress_cb:
                progress_cb(f"[Reddit] Post: {post.title[:80]}…")
            post.comments.replace_more(limit=0)
            for c in post.comments.list():
                if not hasattr(c, "body"):
                    continue
                if c.body in ("[deleted]", "[removed]", ""):
                    continue
                texts.append(c.body)
                if progress_cb:
                    progress_cb(f"[Reddit] Comentario #{len(texts)}: {c.body[:80]}…")
                if len(texts) >= limit:
                    break

        elif sub_m:
            sub = reddit.subreddit(sub_m.group(1))
            if progress_cb:
                progress_cb(f"[Reddit] Accediendo a r/{sub_m.group(1)}…")
            for post in sub.hot(limit=min(50, limit)):
                body = (post.title + " " + post.selftext).strip() if post.selftext else post.title
                texts.append(body)
                if progress_cb:
                    progress_cb(f"[Reddit] Post: {post.title[:80]}…")
                post.comments.replace_more(limit=0)
                for c in post.comments.list():
                    if not hasattr(c, "body"):
                        continue
                    if c.body in ("[deleted]", "[removed]", ""):
                        continue
                    texts.append(c.body)
                    if progress_cb:
                        progress_cb(f"[Reddit] Comentario #{len(texts)}: {c.body[:80]}…")
                    if len(texts) >= limit:
                        break
                if len(texts) >= limit:
                    break
        else:
            msg = "[Reddit] Formato no reconocido. Usa: r/subreddit o URL de hilo."
            if progress_cb:
                progress_cb(msg)

        return texts[:limit]


# ── Instagram (sin soporte) ───────────────────────────────────────────────────

class InstagramExtractor:
    NAME     = "Instagram"
    PACKAGE  = None
    ENV_VARS = []
    INSTALL  = None

    @classmethod
    def is_installed(cls) -> bool:
        return False

    @classmethod
    def is_configured(cls) -> bool:
        return False

    @classmethod
    def extract(cls, *_, **__) -> list[str]:
        raise PlatformUnavailableError(
            "Instagram Graph API requiere cuenta Business/Creator aprobada por Meta. "
            "No disponible en esta versión."
        )


# ── Facebook (sin soporte) ────────────────────────────────────────────────────

class FacebookExtractor:
    NAME     = "Facebook"
    PACKAGE  = None
    ENV_VARS = []
    INSTALL  = None

    @classmethod
    def is_installed(cls) -> bool:
        return False

    @classmethod
    def is_configured(cls) -> bool:
        return False

    @classmethod
    def extract(cls, *_, **__) -> list[str]:
        raise PlatformUnavailableError(
            "Facebook Graph API requiere tokens OAuth y aprobación de Meta. "
            "No disponible en esta versión."
        )


# ── Registro global ───────────────────────────────────────────────────────────

EXTRACTORS: dict[str, type] = {
    "Twitter / X": TwitterExtractor,
    "YouTube":     YouTubeExtractor,
    "Reddit":      RedditExtractor,
    "Instagram":   InstagramExtractor,
    "Facebook":    FacebookExtractor,
}