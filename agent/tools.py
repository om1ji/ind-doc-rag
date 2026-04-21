import httpx
from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from .config import EMBED_BASE_URL, QDRANT_URL, DOCS_API_URL

_qdrant = QdrantClient(url=QDRANT_URL)
_embeddings = OpenAIEmbeddings(
    model="bge-m3",
    base_url=f"{EMBED_BASE_URL}/v1",
    api_key="none",
)


def _make_store(collection: str) -> QdrantVectorStore:
    return QdrantVectorStore(
        client=_qdrant,
        collection_name=collection,
        embedding=_embeddings,
    )


def _format_docs(docs: list) -> str:
    results = []
    for doc in docs:
        meta = doc.metadata
        results.append(
            f"[{meta.get('section_path', '')}]\n{doc.page_content}\n"
            f"source: {meta.get('source', '')} | page: {meta.get('page_num', '')}"
        )
    return "\n\n---\n\n".join(results)


@tool
async def industrial_machines_search(query: str) -> str:
    """Поиск информации по техническим паспортам плавильных печей.

    База содержит паспорта четырёх печей:
    - ОПП-1 (ёмкость ванны 6,0 т)
    - ОПП-1,2-07 (1,2 т)
    - ОПП-2,0-1 (2,0 т)
    - ОПП-3,0 (3,0 т)

    Используй при вопросах о: технических характеристиках (габариты, масса, температура,
    мощность горелок, ёмкость ванны), комплектности поставки, конструктивных элементах,
    сроках и периодичности обслуживания/ремонта, сведениях об изготовителе.

    Формулируй запрос конкретно: включай модель печи если известна, и искомый параметр.
    Примеры: "ёмкость ванны ОПП-1", "габаритные размеры ОПП-3,0", "периодичность ремонта".

    Структура результата в metadata:
    - page_content: текст фрагмента — основной ответ
    - device_name: название печи
    - device_model: модель (например "ОПП-1,2-07")
    - section_path: раздел паспорта (например "Технические характеристики")
    - page_num: страница источника
    - parent_content: расширенный контекст (используй если page_content недостаточен)

    Если результаты нерелевантны — попробуй переформулировать запрос с другими словами
    (например "характеристики" → "параметры", "масса" → "вес").
    Если после 2 переформулировок нет результата — вызови get_document.
    """
    store = _make_store("documents")
    docs = await store.asimilarity_search(query, k=5)
    return _format_docs(docs) if docs else "Ничего не найдено."


@tool
async def law_search(query: str) -> str:
    """Поиск по нормативно-правовым документам в области промышленной безопасности.

    База содержит:
    - Федеральный закон № 116-ФЗ «О промышленной безопасности опасных производственных объектов»

    Используй при вопросах о: классификации ОПО и классах опасности (I–IV),
    обязанностях эксплуатирующей организации, требованиях к декларации промышленной
    безопасности, лицензировании, страховании гражданской ответственности,
    техническом освидетельствовании, производственном контроле, инцидентах и авариях.

    Формулируй запрос близко к юридическому языку закона.
    Примеры: "класс опасности объекта с расплавами металлов",
    "обязанности организации при эксплуатации ОПО", "требования к декларации безопасности",
    "страхование ответственности за причинение вреда".

    Структура результата:
    - page_content: текст нормы — основной ответ
    - metadata.section_path: статья/раздел (например "Статья 2. Опасные производственные объекты")
    - metadata.chunk_type: "norm"
    - metadata.source: файл-источник
    - parent_content: полный текст статьи если норма была разбита (поле может отсутствовать)

    При ответе пользователю: цитируй конкретную статью из section_path,
    не пересказывай — приводи точную формулировку закона.
    """
    store = _make_store("law")
    docs = await store.asimilarity_search(query, k=5)
    return _format_docs(docs) if docs else "Ничего не найдено."


@tool
async def naming_search(query: str) -> str:
    """Инструмент для определения типового наименования (именного кода) ОПО согласно ПП РФ №1363 от 03.09.2025.

    Используй этот инструмент когда нужно:
    - Определить типовое наименование ОПО по виду производства или оборудования
    - Найти именной код ОПО для регистрации в государственном реестре
    - Узнать границы ОПО и особенности идентификации для конкретного производства

    Входной запрос: описание производства, оборудования или вида деятельности на объекте.

    Структура каждого результата в поле metadata:
    - chunk_type: "opo_row" (строка таблицы) или "opo_table_summary" (сводка)
    - section: раздел промышленности (например "XIII. Металлургическая промышленность")
    - name: типовое наименование ОПО — это и есть ответ на запрос
    - processes: перечень опасных процессов, характерных для этого ОПО
    - boundaries: как определяются границы объекта
    - id_rules: особенности идентификации при регистрации

    Для ответа пользователю используй поле name как типовое наименование, section как раздел классификации.
    """
    store = _make_store("naming")
    docs = await store.asimilarity_search(query, k=5)
    return _format_docs(docs) if docs else "Ничего не найдено."


@tool
async def get_document(file: str) -> str:
    """Возвращает полный текст документа из базы знаний.

    Сначала получи список доступных документов (передай file=""),
    затем запроси нужный файл по имени из списка.
    Используй когда нужен полный документ по конкретной модели или теме.

    Args:
        file: точное имя файла из списка (например "opp-1.md") или "" для списка файлов
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{DOCS_API_URL}/{file}" if file else DOCS_API_URL
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


ALL_TOOLS = [industrial_machines_search, law_search, naming_search, get_document]
