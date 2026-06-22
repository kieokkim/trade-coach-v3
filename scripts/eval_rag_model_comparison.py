import json
import sys
import time
from pathlib import Path

sys.path.insert(0, ".")

from tools.ict_rag import _get_client
from tools.ict_search_text import ICT_SEARCH_TEXT
from chromadb.utils import embedding_functions

MODELS_TO_TEST = {
    "current":  "paraphrase-multilingual-MiniLM-L12-v2",
    "e5_large": "intfloat/multilingual-e5-large",
    "bge_m3":   "BAAI/bge-m3",
}

TEST_QUERIES = {
    "가격 공백이 생겨서 진입했는데 실패했어요": "FVG",
    "기관이 대량 주문한 자리에서 반응이 나온다던데": "OrderBlock",
    "런던 시간대에 진입하면 좋다고 들었어요": "Killzone",
    "직전 저점이 깨지는 시점": "BOS",
    "비싼 구간인지 싼 구간인지 봐야 한다던데": "프리미엄_디스카운트",
}


def build_test_collection(name, texts_dict, model_name):
    client = _get_client()
    try:
        client.delete_collection(name)
    except Exception:
        pass
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=model_name
    )
    col = client.get_or_create_collection(name=name, embedding_function=embed_fn)
    ids = list(texts_dict.keys())
    docs = list(texts_dict.values())
    col.add(ids=ids, documents=docs, metadatas=[{"name": k} for k in ids])
    return col, embed_fn


def evaluate(col, embed_fn, label):
    correct = 0
    details = []
    for query, expected in TEST_QUERIES.items():
        result = col.query(query_texts=[query], n_results=3)
        top = result["metadatas"][0][0]["name"]
        dist = result["distances"][0][0]
        top3 = [m["name"] for m in result["metadatas"][0]]
        hit = top == expected
        if hit:
            correct += 1
        mark = "✅" if hit else "❌"
        print(f"  {mark} [{query[:25]}...] → {top} ({dist:.3f}) (정답: {expected}) top3: {top3}")
        details.append({
            "query": query,
            "expected": expected,
            "top1": top,
            "distance": round(dist, 4),
            "top3": top3,
            "hit": hit,
        })
    rate = correct / len(TEST_QUERIES) * 100
    print(f"\n{label} 정확도: {rate:.0f}% ({correct}/{len(TEST_QUERIES)})\n")
    return rate, details


if __name__ == "__main__":
    results = {}

    for key, model_name in MODELS_TO_TEST.items():
        print(f"{'='*60}")
        print(f"모델: {key} ({model_name})")
        print(f"{'='*60}")

        t0 = time.time()
        print(f"  로딩 중...")
        col, embed_fn = build_test_collection(f"test_{key}", ICT_SEARCH_TEXT, model_name)
        load_time = time.time() - t0
        print(f"  로딩 완료 ({load_time:.1f}s)\n")

        rate, details = evaluate(col, embed_fn, key)
        results[key] = {
            "model": model_name,
            "accuracy": rate,
            "load_time_sec": round(load_time, 1),
            "details": details,
        }

    print(f"\n{'='*60}")
    print("최종 비교")
    print(f"{'='*60}")
    for key, r in results.items():
        print(f"  {key:12s} | {r['accuracy']:5.0f}% | {r['load_time_sec']:5.1f}s | {r['model']}")

    best = max(results, key=lambda k: results[k]["accuracy"])
    print(f"\n채택: {best} ({results[best]['model']}) — 정확도 {results[best]['accuracy']:.0f}%")

    out_path = Path("scripts/eval_rag_model_comparison_result.json")
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"결과 저장: {out_path}")
