import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class LegalChunk:
    text: str
    doc: str
    article: str
    point: str
    chunk_index: int


def chunk_law(md_path: str) -> list[LegalChunk]:
    content = Path(md_path).read_text(encoding="utf-8")
    doc_name = Path(md_path).stem

    chunks = []
    chunk_index = 0
    current_article = "Преамбула"

    # Разбиваем по статьям и приложениям
    sections = re.split(
        r'(?=\*\*Статья\s+\d+[\.\d]*|Приложение\s+\d+)',
        content,
        flags=re.MULTILINE
    )

    for section in sections:
        if not section.strip():
            continue

        # Определяем заголовок статьи/приложения
        article_match = re.match(
            r'\*?\*?(Статья\s+[\d\.]+|Приложение\s+\d+)[^\n]*',
            section.strip()
        )
        if article_match:
            current_article = article_match.group(0).strip("*").strip()

        # Разбиваем на пункты внутри статьи
        points = re.split(r'(?=^\d+\.\s)', section, flags=re.MULTILINE)

        for point in points:
            point = point.strip()
            if not point or len(point) < 50:
                continue

            # Номер пункта
            point_match = re.match(r'^(\d+)\.\s', point)
            point_num = point_match.group(1) if point_match else "0"

            # Убираем markdown-разметку ссылок
            clean = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', point)
            clean = re.sub(r'\*+', '', clean).strip()

            chunks.append(LegalChunk(
                text=f"{current_article}, п.{point_num}\n\n{clean}",
                doc=doc_name,
                article=current_article,
                point=point_num,
                chunk_index=chunk_index,
            ))
            chunk_index += 1

    return chunks


if __name__ == "__main__":
    chunks = chunk_law("fz116.md")
    for c in chunks:
        print(f"[{c.article} / п.{c.point}]")
        print(c.text[:200])
        print("---")
    print(f"\nВсего чанков: {len(chunks)}")