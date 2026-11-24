"""
重排序服务：用 Cross-Encoder 模型给“问题 + 候选片段”逐对打分，修正向量检索的排序。

向量检索把问题和片段分别转成向量再比较，速度快但只能判断大致相关；
rerank 模型把问题和片段放在一起逐字对照，判断更准但更慢，所以只用来给向量检索召回的少量候选重新排序。

模型通过 fastembed 在本进程内运行（基于 onnxruntime，CPU 即可），Ollama 不支持 rerank 接口。
"""
import logging
import math
import os

from langchain_core.documents import Document as LCDocument

from config import Config

logger = logging.getLogger(__name__)

# Windows 未开启开发者模式时不支持符号链接，huggingface_hub 每次下载都会打印警告，缓存仍可正常使用
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")


class RerankService:
    """Rerank 模型懒加载单例，首次调用时才加载（首次运行还需下载模型，耗时较长）。"""

    _encoder = None

    @classmethod
    def enabled(cls) -> bool:
        return bool(Config.RERANK_MODEL)

    @classmethod
    def _get_encoder(cls):
        if cls._encoder is None:
            # 延迟导入：未启用 rerank 时不加载 onnxruntime
            from fastembed.rerank.cross_encoder import TextCrossEncoder
            logger.info("加载 rerank 模型：%s", Config.RERANK_MODEL)
            cls._encoder = TextCrossEncoder(Config.RERANK_MODEL, cache_dir=Config.MODEL_CACHE_DIR)
        return cls._encoder

    @classmethod
    def rerank(cls, query: str, docs: list[LCDocument]) -> list[tuple[LCDocument, float]]:
        """
        给候选片段重新打分并按分数从高到低排序。

        :param query: 用户问题
        :param docs: 向量检索召回的候选片段
        :return: [(片段, 分数)]，分数经 sigmoid 换算到 0~1，越大越相关
        """
        if not docs:
            return []
        logits = cls._get_encoder().rerank(query, [d.page_content for d in docs])
        # 模型输出的是没有上下限的 logit，换算成 0~1 便于设置阈值和展示
        scored = [(doc, 1 / (1 + math.exp(-float(logit)))) for doc, logit in zip(docs, logits)]
        return sorted(scored, key=lambda x: x[1], reverse=True)
