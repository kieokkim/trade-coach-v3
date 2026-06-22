import json
import logging
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

_CHROMA_PATH = Path(__file__).parent.parent / "data" / "chroma_db"
_CONCEPTS_PATH = Path(__file__).parent / "ict_concepts.json"
_EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"

_client = None
_collection = None


def _get_client():
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=str(_CHROMA_PATH))
    return _client


def _get_collection():
    global _collection
    if _collection is None:
        client = _get_client()
        embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=_EMBED_MODEL
        )
        _collection = client.get_or_create_collection(
            name="ict_concepts",
            embedding_function=embed_fn,
        )
    return _collection


def build_index(force: bool = False) -> int:
    collection = _get_collection()

    if not force and collection.count() > 0:
        logger.info("ICT 개념 인덱스 이미 존재 (%d건), 스킵", collection.count())
        return collection.count()

    if force:
        client = _get_client()
        try:
            client.delete_collection("ict_concepts")
        except Exception:
            pass
        global _collection
        _collection = None
        collection = _get_collection()

    concepts = json.loads(_CONCEPTS_PATH.read_text(encoding="utf-8"))

    ids, documents, metadatas = [], [], []
    for i, (concept_name, info) in enumerate(concepts.items()):
        definition = info.get("정의", "")
        key_points = info.get("핵심_포인트", [])
        mistake = info.get("실수_패턴", "")
        improvement = info.get("개선_방법", "")

        doc_text = (
            f"{concept_name}: {definition}\n"
            f"핵심 포인트: {' / '.join(key_points)}\n"
            f"흔한 실수: {mistake}\n"
            f"개선 방법: {improvement}"
        )

        ids.append(f"concept_{i}")
        documents.append(doc_text)
        metadatas.append({
            "name": concept_name,
            "mistake": mistake,
            "improvement": improvement,
        })

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    logger.info("ICT 개념 %d건 인덱싱 완료", len(ids))
    return len(ids)


def search_ict_concept_rag(query: str, top_k: int = 3) -> list[dict]:
    try:
        collection = _get_collection()
        if collection.count() == 0:
            build_index()

        results = collection.query(query_texts=[query], n_results=top_k)

        output = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]

        for doc, meta, dist in zip(docs, metas, dists):
            output.append({
                "name": meta.get("name", ""),
                "text": doc,
                "mistake": meta.get("mistake", ""),
                "improvement": meta.get("improvement", ""),
                "distance": dist,
            })
        return output
    except Exception as e:
        logger.warning("search_ict_concept_rag 실패: %s", e)
        return []


if __name__ == "__main__":
    count = build_index(force=True)
    print(f"✅ {count}건 인덱싱 완료\n")

    test_queries = [
        "가격 공백이 생겨서 진입했는데 실패했어요",
        "런던 시간대에 진입하면 좋다고 들었어요",
        "직전 저점이 깨지는 시점",
        "기관이 대량 주문한 자리에서 반응이 나온다던데",
    ]
    for q in test_queries:
        print(f"질의: {q}")
        results = search_ict_concept_rag(q, top_k=2)
        for r in results:
            print(f"  → {r['name']} (거리: {r['distance']:.3f})")
            print(f"    실수패턴: {r['mistake'][:80]}")
        print()
