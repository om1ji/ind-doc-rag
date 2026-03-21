import argparse
import logging
import tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import cv2
import fitz
import numpy as np
from docling.document_converter import DocumentConverter

logging.basicConfig(level=logging.INFO)


# ── Preprocessing (crop + deskew) ────────────────────────────────────────────


def detect_skew_angle(img: np.ndarray) -> float:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY_INV)

    lines = cv2.HoughLinesP(
        thresh,
        rho=1,
        theta=np.pi / 180,
        threshold=200,
        minLineLength=img.shape[1] * 0.4,
        maxLineGap=20,
    )

    if lines is None:
        return 0.0

    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if abs(angle) < 10:
            angles.append(angle)

    return float(np.median(angles)) if angles else 0.0


def deskew(img: np.ndarray) -> np.ndarray:
    angle = detect_skew_angle(img)
    if abs(angle) < 0.1:
        return img

    print(f"  → наклон: {angle:.2f}°, выравниваем...")
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(
        img,
        M,
        (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )


def crop_page(img: np.ndarray) -> np.ndarray:
    h, w = img.shape[:2]
    return img[20 : h - 100, 60 : w - 20]


def _process_page(args: tuple) -> tuple[int, Path]:
    i, pix_samples, pix_height, pix_width, pix_n, out_dir = args
    img = np.frombuffer(pix_samples, dtype=np.uint8).reshape(
        pix_height, pix_width, pix_n
    )
    if pix_n == 4:
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)

    img = crop_page(deskew(img))

    path = out_dir / f"page_{i:04d}.png"
    cv2.imwrite(str(path), img)
    return i, path


def preprocess_pdf(pdf_path: Path, dpi: int = 100, max_workers: int = 8) -> Path:
    print(f"Предобработка {pdf_path.name}...")
    doc = fitz.open(str(pdf_path))

    pages_data = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)

        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
            pages_data.append(
                (i, bytes(pix.samples), pix.height, pix.width, pix.n, tmp)
            )
        doc.close()

        results = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for future in as_completed(
                {executor.submit(_process_page, a): a[0] for a in pages_data}
            ):
                i, path = future.result()
                results[i] = path
                print(f"  ✓ Страница {i + 1}")

        out_pdf = pdf_path.with_stem(pdf_path.stem + "_preprocessed")
        out_doc = fitz.open()
        for img_path in (results[i] for i in sorted(results)):
            img_cv = cv2.imread(str(img_path))
            _, jpeg_buf = cv2.imencode(".jpg", img_cv, [cv2.IMWRITE_JPEG_QUALITY, 85])
            out_doc.insert_pdf(
                fitz.open("pdf", fitz.open("jpeg", jpeg_buf.tobytes()).convert_to_pdf())
            )
        out_doc.save(str(out_pdf), deflate=True)
        out_doc.close()

    return out_pdf


# ── Conversion ────────────────────────────────────────────────────────────────


def convert_to_markdown(
    source: Path, output_dir: Path, converter: DocumentConverter
) -> None:
    print(f"Конвертируем {source.name}...")
    doc = converter.convert(str(source)).document
    output_path = output_dir / (source.stem + ".md")
    output_path.write_text(doc.export_to_markdown(), encoding="utf-8")
    print(f"✓ Сохранено: {output_path}")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Предобработка и конвертация документов в Markdown"
    )
    parser.add_argument("--file", type=str, help="Имя конкретного файла из ../files/")
    parser.add_argument(
        "--dpi", type=int, default=100, help="DPI растеризации (по умолчанию: 100)"
    )
    parser.add_argument(
        "--workers", type=int, default=8, help="Число потоков (по умолчанию: 8)"
    )
    args = parser.parse_args()

    files_dir = Path("../files")
    output_dir = Path("../files/converted")
    output_dir.mkdir(exist_ok=True)

    if args.file:
        source = files_dir / args.file
        if not source.exists():
            raise FileNotFoundError(f"Файл не найден: {source}")
        sources = [source]
    else:
        sources = list(files_dir.glob("*.pdf")) + list(files_dir.glob("*.docx"))
        if not sources:
            raise FileNotFoundError(f"Нет файлов в {files_dir}")

    print(f"Найдено файлов: {len(sources)}")
    converter = DocumentConverter()
    preprocessed = []

    for source in sources:
        if source.suffix.lower() == ".pdf":
            source = preprocess_pdf(source, dpi=args.dpi, max_workers=args.workers)
            preprocessed.append(source)
        convert_to_markdown(source, output_dir, converter)

    for p in preprocessed:
        p.unlink(missing_ok=True)

    print(f"\nГотово. Обработано файлов: {len(sources)}")
