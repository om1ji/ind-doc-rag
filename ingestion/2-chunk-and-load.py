import re
import uuid
import asyncio
import aiohttp
import argparse
from dataclasses import dataclass
from pathlib import Path
import json

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

EMBEDDING_MODEL = "bge-m3:latest"
QDRANT_URL = "http://localhost:6333"
OLLAMA_URL = "http://localhost:11434"
MAX_CONCURRENT = 4


@dataclass
class Chunk:
    text: str
    heading: str
    doc_name: str
    chunk_index: int


async def generate_metadata(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    chunk_text: str,
    doc_description: str,
) -> dict:
    prompt = f"""Ты помощник по классификации документов.

Описание документа: {doc_description}

Текст фрагмента:
{chunk_text[:1000]}

Верни ТОЛЬКО валидный JSON без пояснений:
{{
  "doc_type": "law | order | passport | standard",
  "topic": "identification | class | naming | safety | maintenance | other",
  "has_numbers": true | false,
  "key_terms": ["термин1", "термин2"],
  "summary": "краткое резюме фрагмента в 1 предложении"
}}"""

    async with semaphore:
        async with session.post(
            f"{OLLAMA_URL}/api/chat",
            json={
                "model": "llama3.1:latest",
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.0},
            },
        ) as response:
            response.raise_for_status()
            data = await response.json()
            text = data["message"]["content"]

            # Чистим на случай если модель добавила ```json
            text = re.sub(r"```json|```", "", text).strip()
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {
                    "doc_type": "unknown",
                    "topic": "other",
                    "has_numbers": False,
                    "key_terms": [],
                    "summary": "",
                }


def clean_text(text: str) -> str:
    # Убираем markdown ссылки: [текст](url) → текст
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    # Убираем жирный и курсив
    text = re.sub(r"\*+([^\*]+)\*+", r"\1", text)
    # Убираем лишние пробелы и переносы
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_law(md_path: str, min_chunk_size: int = 100) -> list[Chunk]:
    content = Path(md_path).read_text(encoding="utf-8")
    doc_name = Path(md_path).stem

    # Разбиваем по статьям, главам и приложениям
    pattern = r"(?=\*{1,2}(?:Статья\s+[\d\.]+|ГЛАВА\s+[IVX]+|Приложение\s+\d+))"
    sections = re.split(pattern, content, flags=re.MULTILINE)

    chunks = []
    chunk_index = 0

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Извлекаем заголовок (первая строка)
        first_line = section.splitlines()[0]
        heading = re.sub(r"\*+", "", first_line).strip()
        heading = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", heading)

        # Чистим тело
        body = clean_text(section)

        if len(body) < min_chunk_size:
            continue

        chunks.append(
            Chunk(
                text=body,
                heading=heading,
                doc_name=doc_name,
                chunk_index=chunk_index,
            )
        )
        chunk_index += 1

    return chunks


async def get_embedding_async(
    session: aiohttp.ClientSession,
    semaphore: asyncio.Semaphore,
    text: str,
    index: int,
    total: int,
) -> list[float]:
    async with semaphore:
        async with session.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": EMBEDDING_MODEL, "input": text},
        ) as response:
            response.raise_for_status()
            data = await response.json()
            print(f"  Эмбеддинг {index + 1}/{total}...")
            return data["embeddings"][0]


async def get_embeddings_async(texts: list[str]) -> list[list[float]]:
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    async with aiohttp.ClientSession() as session:
        tasks = [
            get_embedding_async(session, semaphore, text, i, len(texts))
            for i, text in enumerate(texts)
        ]
        return await asyncio.gather(*tasks)


async def enrich_and_upload(
    chunks: list[Chunk],
    client: QdrantClient,
    collection_name: str,
    doc_description: str,
):
    texts = [chunk.text for chunk in chunks]
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async with aiohttp.ClientSession() as session:
        # Параллельно генерируем эмбеддинги и метаданные
        embedding_tasks = [
            get_embedding_async(session, semaphore, text, i, len(texts))
            for i, text in enumerate(texts)
        ]
        metadata_tasks = [
            generate_metadata(session, semaphore, chunk.text, doc_description)
            for chunk in chunks
        ]

        print("Генерируем эмбеддинги и метаданные параллельно...")
        embeddings, metadatas = await asyncio.gather(
            asyncio.gather(*embedding_tasks),
            asyncio.gather(*metadata_tasks),
        )

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "page_content": chunk.text,
                "metadata": {
                    "heading": chunk.heading,
                    "doc_name": chunk.doc_name,
                    "chunk_index": chunk.chunk_index,
                    # Сгенерированные метаданные
                    "doc_type": meta.get("doc_type", "unknown"),
                    "topic": meta.get("topic", "other"),
                    "has_numbers": meta.get("has_numbers", False),
                    "key_terms": meta.get("key_terms", []),
                    "summary": meta.get("summary", ""),
                },
            },
        )
        for chunk, embedding, meta in zip(chunks, embeddings, metadatas)
    ]

    client.upsert(collection_name=collection_name, points=points)
    print(f"✓ Загружено {len(points)} чанков в {collection_name}")


def chunk_by_headers(
    md_path: str, max_chunk_size: int = 1500, min_chunk_size: int = 100
) -> list[Chunk]:
    content = Path(md_path).read_text(encoding="utf-8")
    doc_name = Path(md_path).stem

    # Разбиваем по заголовкам любого уровня (# ## ### и т.д.)
    sections = re.split(r"(?=^#{1,4}\s)", content, flags=re.MULTILINE)

    chunks = []
    chunk_index = 0

    for section in sections:
        section = clean_text(section)
        if len(section) < min_chunk_size:
            continue

        lines = section.splitlines()
        heading = (
            re.sub(r"^#+\s*", "", lines[0]).strip() if lines else f"chunk_{chunk_index}"
        )

        # Если секция слишком большая — режем по абзацам
        if len(section) > max_chunk_size:
            paragraphs = re.split(r"\n{2,}", section)
            buffer = ""
            for para in paragraphs:
                if (
                    len(buffer) + len(para) > max_chunk_size
                    and len(buffer) >= min_chunk_size
                ):
                    chunks.append(
                        Chunk(
                            text=buffer.strip(),
                            heading=heading,
                            doc_name=doc_name,
                            chunk_index=chunk_index,
                        )
                    )
                    chunk_index += 1
                    buffer = para
                else:
                    buffer = f"{buffer}\n\n{para}".strip() if buffer else para
            if len(buffer) >= min_chunk_size:
                chunks.append(
                    Chunk(
                        text=buffer.strip(),
                        heading=heading,
                        doc_name=doc_name,
                        chunk_index=chunk_index,
                    )
                )
                chunk_index += 1
        else:
            chunks.append(
                Chunk(
                    text=section,
                    heading=heading,
                    doc_name=doc_name,
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1

    return chunks


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Загрузка документов в Qdrant")
    parser.add_argument("--file", type=str, help="Конкретный .md файл для загрузки")
    parser.add_argument(
        "--store-name",
        type=str,
        default="passport-docs",
        help="Название коллекции в Qdrant",
    )
    parser.add_argument(
        "--description",
        type=str,
        default="технический документ",
        help="Описание документа для генерации метаданных",
    )
    args = parser.parse_args()

    converted_dir = Path("../files/converted")

    if args.file:
        md_path = (
            converted_dir / args.file
            if not Path(args.file).is_absolute()
            else Path(args.file)
        )
        if not md_path.exists():
            raise FileNotFoundError(f"Файл не найден: {md_path}")
        md_files = [md_path]
    else:
        md_files = list(converted_dir.glob("*.md"))
        if not md_files:
            raise FileNotFoundError(f"Нет .md файлов в {converted_dir}")

    print(f"Найдено файлов: {len(md_files)}")
    print(f"Коллекция: {args.store_name}")

    all_chunks = []
    for md_file in md_files:
        print(f"  Чанкуем {md_file.name}...")
        chunks = chunk_by_headers(str(md_file))
        all_chunks.extend(chunks)
        print(f"  → {len(chunks)} чанков")

    print(f"\nВсего чанков: {len(all_chunks)}")

    client = QdrantClient(url=QDRANT_URL)
    asyncio.run(
        enrich_and_upload(all_chunks, client, args.store_name, args.description)
    )
