"""Embeddings — provider-switchable via settings.

Default: OpenAI text-embedding-3-small (1536 dims) — handles Hindi adequately.
Alternative: voyage-multilingual-2 (1024 dims) — better Hindi, set
embedding_provider=voyage and embedding_dims=1024 BEFORE creating the
Pinecone index (dims are locked at index creation).
"""
from app.core.config import get_settings

_BATCH = 64


def embed_texts(texts: list[str]) -> list[list[float]]:
    s = get_settings()
    if s.embedding_provider == "voyage":
        return _voyage(texts, s)
    return _openai(texts, s)


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]


def _openai(texts: list[str], s) -> list[list[float]]:
    from openai import OpenAI

    client = OpenAI(api_key=s.openai_api_key)
    out: list[list[float]] = []
    for i in range(0, len(texts), _BATCH):
        resp = client.embeddings.create(model=s.embedding_model, input=texts[i : i + _BATCH])
        out.extend(d.embedding for d in resp.data)
    return out


def _voyage(texts: list[str], s) -> list[list[float]]:
    import voyageai

    client = voyageai.Client(api_key=s.voyage_api_key)
    out: list[list[float]] = []
    for i in range(0, len(texts), _BATCH):
        resp = client.embed(texts[i : i + _BATCH], model="voyage-multilingual-2",
                            input_type="document")
        out.extend(resp.embeddings)
    return out
