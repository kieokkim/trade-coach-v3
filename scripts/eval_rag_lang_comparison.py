import sys
sys.path.insert(0, ".")

from tools.ict_rag import _get_client
from tools.ict_search_text import ICT_SEARCH_TEXT, ICT_SEARCH_TEXT_EN
from chromadb.utils import embedding_functions

EMBED_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"


def build_test_collection(name, texts_dict):
    client = _get_client()
    try:
        client.delete_collection(name)
    except Exception:
        pass
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBED_MODEL
    )
    col = client.get_or_create_collection(name=name, embedding_function=embed_fn)
    ids = list(texts_dict.keys())
    docs = list(texts_dict.values())
    col.add(ids=ids, documents=docs, metadatas=[{"name": k} for k in ids])
    return col


TEST_QUERIES = {
    "가격 공백이 생겨서 진입했는데 실패했어요": "FVG",
    "기관이 대량 주문한 자리에서 반응이 나온다던데": "OrderBlock",
    "런던 시간대에 진입하면 좋다고 들었어요": "Killzone",
    "직전 저점이 깨지는 시점": "BOS",
    "비싼 구간인지 싼 구간인지 봐야 한다던데": "프리미엄_디스카운트",
}


def evaluate(col, label):
    correct = 0
    for query, expected in TEST_QUERIES.items():
        result = col.query(query_texts=[query], n_results=3)
        top = result["metadatas"][0][0]["name"]
        dist = result["distances"][0][0]
        top3 = [m["name"] for m in result["metadatas"][0]]
        match = "✅" if top == expected else "❌"
        if top == expected:
            correct += 1
        print(f"  {match} [{query[:25]}...] → {top} ({dist:.3f}) (정답: {expected}) top3: {top3}")
    rate = correct / len(TEST_QUERIES) * 100
    print(f"\n{label} 정확도: {rate:.0f}% ({correct}/{len(TEST_QUERIES)})\n")
    return rate


if __name__ == "__main__":
    print("=== 한국어 검색 텍스트 ===")
    col_ko = build_test_collection("test_ko", ICT_SEARCH_TEXT)
    rate_ko = evaluate(col_ko, "한국어")

    print("=== 영어 검색 텍스트 ===")
    col_en = build_test_collection("test_en", ICT_SEARCH_TEXT_EN)
    rate_en = evaluate(col_en, "영어")

    print(f"=== 최종 비교 ===")
    print(f"한국어: {rate_ko:.0f}% | 영어: {rate_en:.0f}%")
    winner = "영어" if rate_en > rate_ko else "한국어" if rate_ko > rate_en else "동점"
    print(f"채택: {winner}")
