"""
向量库服务：封装 Chroma 向量数据库和 Ollama 嵌入模型。

每个文本片段写入时都带上 metadata：
    kb_id     所属知识库ID，用于按知识库过滤检索
    doc_id    所属文档ID，用于删除或重建某个文档的向量
    file_name 文件名，用于在回答中展示引用来源
"""
import logging
import re
import time
from collections.abc import Callable

from langchain_chroma import Chroma
from langchain_core.documents import Document as LCDocument
from langchain_ollama import OllamaEmbeddings

from config import Config

logger = logging.getLogger(__name__)

# 每批向量化的片段数和单批最多尝试次数
EMBED_BATCH_SIZE = 64
EMBED_RETRIES = 3


class VectorStore:
    """Chroma 向量库的单例封装，首次使用时才初始化，避免启动时就连接 Ollama。"""

    _instance: Chroma | None = None

    @classmethod
    def get(cls) -> Chroma:
        """
        获取 Chroma 实例（懒加载单例）。

        :return: langchain_chroma.Chroma 对象
        """
        if cls._instance is None:
            embeddings = OllamaEmbeddings(
                model=Config.EMBEDDING_MODEL,
                base_url=Config.OLLAMA_BASE_URL,
            )
            cls._instance = Chroma(
                collection_name=Config.CHROMA_COLLECTION,
                embedding_function=embeddings,
                persist_directory=Config.CHROMA_DIR,
                # 使用余弦距离，相似度分数更直观（越接近 1 越相似）
                collection_metadata={"hnsw:space": "cosine"},
            )
        return cls._instance

    @classmethod
    def add_chunks(cls, chunks: list[LCDocument],
                   on_progress: Callable[[int, int], None] | None = None) -> int:
        """
        把切分好的文本片段分批向量化后写入 Chroma，单批失败会重试。

        :param chunks: LangChain Document 列表，metadata 中需包含 kb_id、doc_id、file_name
        :param on_progress: 进度回调，每写完一批调用 on_progress(已写入数量, 总数)
        :return: 写入的片段数量
        """
        if not chunks:
            return 0
        # 分批写入：一次把上千个片段交给 Ollama 嵌入，单个请求要处理几十秒，
        # 期间模型可能被调度器换出，请求会以 400（/tokenize 连接被拒绝）失败
        for start in range(0, len(chunks), EMBED_BATCH_SIZE):
            batch = chunks[start:start + EMBED_BATCH_SIZE]
            for attempt in range(1, EMBED_RETRIES + 1):
                try:
                    cls.get().add_documents(batch)
                    break
                except Exception as e:  # noqa: BLE001 Ollama 临时不可用时重试，最后一次仍失败才抛出
                    if attempt == EMBED_RETRIES:
                        raise
                    logger.warning("写入向量库失败，第 %s 次重试（%s/%s）：%s",
                                   attempt, start, len(chunks), e)
                    time.sleep(2 * attempt)
            if on_progress:
                on_progress(min(start + EMBED_BATCH_SIZE, len(chunks)), len(chunks))
        return len(chunks)

    @classmethod
    def delete_by_doc(cls, doc_id: int) -> None:
        """
        删除某个文档的全部向量片段。

        :param doc_id: 文档ID
        """
        store = cls.get()
        result = store.get(where={"doc_id": doc_id}, include=[])
        if result["ids"]:
            store.delete(ids=result["ids"])

    @classmethod
    def search(cls, query: str, k: int, kb_id: int | None = None) -> list[tuple[LCDocument, float]]:
        """
        相似度检索。

        :param query: 查询文本
        :param k: 返回条数
        :param kb_id: 指定知识库ID时只在该库内检索，None 表示检索全部
        :return: [(片段, 相似度分数)] 列表，分数范围 0~1，越大越相似
        """
        search_filter = {"kb_id": kb_id} if kb_id else None
        return cls.get().similarity_search_with_relevance_scores(query, k=k, filter=search_filter)

    @classmethod
    def keyword_search(cls, term: str, limit: int, kb_id: int | None = None) -> list[LCDocument]:
        """
        查找原文中包含某个关键词的片段（不区分大小写），用于补充向量检索。

        向量检索对 jQuery、10005、CR-14 这类专有名词和编号不敏感，包含它们的片段可能排得很靠后；
        这里直接匹配原文，保证这类片段能进入候选。

        :param term: 关键词
        :param limit: 最多返回条数，调用方可传入“阈值 + 1”来判断关键词是否足够专一
        :param kb_id: 指定知识库ID时只在该库内检索
        :return: 命中的片段
        """
        result = cls.get().get(
            where={"kb_id": kb_id} if kb_id else None,
            where_document={"$regex": "(?i)" + re.escape(term)},
            include=["documents", "metadatas"],
            limit=limit,
        )
        return [LCDocument(page_content=text, metadata=meta)
                for text, meta in zip(result["documents"], result["metadatas"])]
