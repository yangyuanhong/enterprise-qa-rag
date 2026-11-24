"""
图片服务：用视觉大模型把文档中的图片转成文字描述，让图片内容也能被检索到。

处理方式：解析器把图片导出到磁盘，并在 Markdown 中留下 ![](图片路径) 占位；
本服务逐个识别图片，把占位改写成 ![图片描述](相对路径)，切分时再生成 type=image 的 chunk。
"""
import base64
import logging
import os
import re
from collections.abc import Callable

from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama
from PIL import Image

from config import BASE_DIR, Config

logger = logging.getLogger(__name__)

IMAGE_MD_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
# 传给模型的图片前后文字长度，用于让模型知道图片在讲什么（通常图注就在图片下方）
CONTEXT_CHARS = 150

PROMPT = """你是企业文档的图片解析助手。请用简体中文描述这张图片，描述会被存入知识库供员工检索。

要求：
1. 完整转录图中出现的所有文字、数字和单位，不要遗漏或改写。
2. 架构图、流程图：说明有哪些组件或步骤，以及它们之间的连接、先后关系。
3. 柱状图、折线图等图表：说明标题，并逐项列出每个类别对应的数值。
4. 表格截图：按“列名: 值”的格式逐行列出。
5. 直接输出描述内容，不要写“这张图片展示了”之类的开场白，不超过 300 字。

图片所在位置的上下文（仅供参考，可能包含图注）：
{context}"""


class ImageService:
    """图片识别，视觉模型懒加载，未配置 VISION_MODEL 时不启用。"""

    _llm: ChatOllama | None = None

    @classmethod
    def enabled(cls) -> bool:
        return bool(Config.VISION_MODEL)

    @classmethod
    def _get_llm(cls) -> ChatOllama:
        if cls._llm is None:
            cls._llm = ChatOllama(model=Config.VISION_MODEL, base_url=Config.OLLAMA_BASE_URL, temperature=0)
        return cls._llm

    @classmethod
    def describe(cls, image_path: str, context: str = "") -> str:
        """
        调用视觉模型生成图片描述。

        :param image_path: 图片绝对路径
        :param context: 图片前后的文字，帮助模型理解图片用途
        :return: 图片描述
        """
        with open(image_path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        ext = os.path.splitext(image_path)[1].lstrip(".").lower() or "png"
        message = HumanMessage(content=[
            {"type": "text", "text": PROMPT.format(context=context or "无")},
            {"type": "image_url", "image_url": {"url": f"data:image/{ext};base64,{data}"}},
        ])
        return str(cls._get_llm().invoke([message]).content).strip()

    @classmethod
    def replace_images(cls, md_text: str, on_progress: Callable[[int, int], None] | None = None) -> str:
        """
        识别 Markdown 中的所有图片，把 ![](绝对路径) 改写成 ![图片描述](相对 server 目录的路径)。
        装饰性小图会被删除；识别失败的图片保留占位但描述为空，切分时会跳过。

        :param md_text: 解析器输出的 Markdown
        :param on_progress: 进度回调，每处理一张图片前调用 on_progress(当前序号, 图片总数)
        :return: 改写后的 Markdown
        """
        total = len(IMAGE_MD_RE.findall(md_text))
        done = 0

        def replace(m: re.Match) -> str:
            nonlocal done
            done += 1
            if on_progress:
                on_progress(done, total)
            abs_path = os.path.normpath(m.group(1))
            if not os.path.exists(abs_path):
                return ""
            with Image.open(abs_path) as img:
                too_small = min(img.size) < Config.IMAGE_MIN_SIZE
            if too_small:
                os.remove(abs_path)
                return ""

            before = IMAGE_MD_RE.sub("", md_text[max(0, m.start() - CONTEXT_CHARS):m.start()])
            after = IMAGE_MD_RE.sub("", md_text[m.end():m.end() + CONTEXT_CHARS])
            try:
                desc = cls.describe(abs_path, f"{before.strip()}\n[图片位置]\n{after.strip()}")
            except Exception as e:  # noqa: BLE001 单张图片失败不影响整篇文档入库
                logger.warning("图片识别失败：%s，%s", abs_path, e)
                desc = ""
            # 描述放进 alt 文本，去掉换行和方括号，保证仍是合法的单行 Markdown 图片语法
            desc = re.sub(r"\s+", " ", desc).replace("[", "【").replace("]", "】")
            rel_path = os.path.relpath(abs_path, BASE_DIR).replace("\\", "/")
            return f"![{desc}]({rel_path})"

        return IMAGE_MD_RE.sub(replace, md_text)
