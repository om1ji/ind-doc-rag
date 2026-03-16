"""
Простая RAG система: Qdrant + Ollama (Qwen2.5)
Запуск: python rag_demo.py
"""

import json
import urllib.request
import urllib.error

# ─────────────────────────────────────────
# НАСТРОЙКИ — измени если нужно
# ─────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434"
QDRANT_URL = "http://localhost:6333"
EMBED_MODEL = "nomic-embed-text"   # ollama pull nomic-embed-text
LLM_MODEL   = "qwen2.5vl:7b"            # уже есть у тебя
COLLECTION  = "rag_demo"
TOP_K       = 3                    # сколько чанков брать для контекста


# ─────────────────────────────────────────
# ТЕСТОВЫЕ ТЕКСТЫ (наша "база знаний")
# ─────────────────────────────────────────
DOCUMENTS = [
    {
        "id": 1,
        "text": """Станок токарный ТВ-320. Технические характеристики:
Максимальный диаметр обработки над станиной: 320 мм.
Максимальная длина обрабатываемой детали: 1000 мм.
Мощность главного привода: 4 кВт.
Частота вращения шпинделя: 50–2000 об/мин.
Масса станка: 1100 кг.
Напряжение питания: 380 В, 50 Гц."""
    },
    {
        "id": 2,
        "text": """Компрессор винтовой КВ-55. Технические характеристики:
Производительность: 8.5 м³/мин.
Рабочее давление: 8 бар (максимум 10 бар).
Мощность электродвигателя: 55 кВт.
Напряжение питания: 380 В, 3 фазы, 50 Гц.
Объём ресивера: 500 л.
Уровень шума: 68 дБ.
Масса: 850 кг."""
    },
    {
        "id": 3,
        "text": """Сварочный полуавтомат MIG-500. Технические характеристики:
Сварочный ток: 50–500 А.
Напряжение холостого хода: 48 В.
Диаметр сварочной проволоки: 0.8–1.6 мм.
Потребляемая мощность: 18 кВт.
Напряжение питания: 380 В, 50 Гц.
Масса: 62 кг.
Степень защиты: IP21S."""
    },
    {
        "id": 4,
        "text": """Фрезерный станок ФС-400. Технические характеристики:
Размер рабочего стола: 400 × 1600 мм.
Мощность шпинделя: 7.5 кВт.
Частота вращения шпинделя: 100–6000 об/мин.
Максимальное перемещение по оси X: 1000 мм.
Максимальное перемещение по оси Y: 400 мм.
Максимальное перемещение по оси Z: 500 мм.
Масса станка: 3200 кг."""
    },
    {
        "id": 5,
        "text": """Пресс гидравлический ПГ-100. Технические характеристики:
Усилие пресса: 100 тонн (1000 кН).
Ход ползуна: 400 мм.
Скорость ползуна (рабочий ход): 10 мм/с.
Мощность гидростанции: 11 кВт.
Напряжение питания: 380 В, 50 Гц.
Размер стола: 700 × 700 мм.
Масса: 4500 кг."""
    },
]


# ─────────────────────────────────────────
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ─────────────────────────────────────────

def http_post(url, data):
    """POST запрос без внешних зависимостей."""
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode("utf-8"))


def http_put(url, data):
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, method="PUT",
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read().decode("utf-8"))


def http_get(url):
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read().decode("utf-8"))


def get_embedding(text):
    """Получить эмбеддинг через Ollama."""
    result = http_post(f"{OLLAMA_URL}/api/embeddings", {
        "model": EMBED_MODEL,
        "prompt": text
    })
    return result["embedding"]


def ask_llm(prompt):
    """Отправить запрос в Ollama LLM."""
    result = http_post(f"{OLLAMA_URL}/api/generate", {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False
    })
    return result["response"]


# ─────────────────────────────────────────
# QDRANT: создание коллекции и индексация
# ─────────────────────────────────────────

def create_collection(vector_size):
    """Создать коллекцию в Qdrant (или пересоздать)."""
    # Удаляем если уже есть
    try:
        req = urllib.request.Request(
            f"{QDRANT_URL}/collections/{COLLECTION}",
            method="DELETE"
        )
        urllib.request.urlopen(req)
    except:
        pass

    # Создаём новую
    http_put(f"{QDRANT_URL}/collections/{COLLECTION}", {
        "vectors": {
            "size": vector_size,
            "distance": "Cosine"
        }
    })
    print(f"✅ Коллекция '{COLLECTION}' создана (размер вектора: {vector_size})")


def index_documents():
    """Создать эмбеддинги и загрузить документы в Qdrant."""
    print("\n📄 Индексация документов...")

    # Получаем первый эмбеддинг чтобы узнать размерность
    sample_embedding = get_embedding(DOCUMENTS[0]["text"])
    create_collection(len(sample_embedding))

    points = []
    for doc in DOCUMENTS:
        print(f"   Обрабатываю: {doc['text'][:50]}...")
        embedding = get_embedding(doc["text"])
        points.append({
            "id": doc["id"],
            "vector": embedding,
            "payload": {"text": doc["text"]}
        })

    # Загружаем все точки в Qdrant
    http_put(f"{QDRANT_URL}/collections/{COLLECTION}/points", {
        "points": points
    })
    print(f"✅ Загружено {len(points)} документов в Qdrant\n")


# ─────────────────────────────────────────
# RAG: поиск + генерация ответа
# ─────────────────────────────────────────

def search(query):
    """Найти похожие документы в Qdrant."""
    query_vector = get_embedding(query)
    result = http_post(
        f"{QDRANT_URL}/collections/{COLLECTION}/points/search",
        {
            "vector": query_vector,
            "limit": TOP_K,
            "with_payload": True
        }
    )
    return result["result"]


def rag_answer(question):
    """Полный RAG пайплайн: поиск → формирование промпта → ответ LLM."""
    print(f"🔍 Ищу релевантные документы для: '{question}'")
    hits = search(question)

    if not hits:
        return "Не нашёл релевантных документов в базе."

    # Собираем контекст
    context_parts = []
    print(f"\n📎 Найдено {len(hits)} релевантных фрагментов:")
    for i, hit in enumerate(hits, 1):
        score = hit["score"]
        text = hit["payload"]["text"]
        print(f"   [{i}] score={score:.3f} | {text[:60]}...")
        context_parts.append(f"[Документ {i}]:\n{text}")

    context = "\n\n".join(context_parts)

    # Формируем промпт
    prompt = f"""Ты — технический ассистент на производственном предприятии.
Используй ТОЛЬКО информацию из предоставленных документов для ответа.
Если информации нет в документах — так и скажи.

ДОКУМЕНТЫ:
{context}

ВОПРОС: {question}

ОТВЕТ:"""

    print("\n🤖 Генерирую ответ...\n")
    return ask_llm(prompt)


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def main():
    print("=" * 55)
    print("  RAG ДЕМО: Qdrant + Ollama (Qwen2.5)")
    print("=" * 55)

    # Шаг 1: Индексация
    index_documents()

    # Шаг 2: Интерактивный чат
    print("💬 Задавай вопросы! (введи 'выход' для завершения)\n")
    print("Примеры вопросов:")
    print("  - Какая мощность у токарного станка?")
    print("  - Какое давление у компрессора?")
    print("  - Какой сварочный ток у полуавтомата?")
    print("  - Какие станки питаются от 380В?\n")

    while True:
        question = input("Вопрос: ").strip()
        if question.lower() in ("выход", "exit", "quit", "q"):
            print("👋 Пока!")
            break
        if not question:
            continue

        answer = rag_answer(question)
        print(f"\n{'─'*50}")
        print(f"Ответ: {answer}")
        print(f"{'─'*50}\n")


if __name__ == "__main__":
    main()