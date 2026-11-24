"""
文档服务：负责文件保存、内容解析、文本切分和向量化入库。

处理流程：上传文件 → 保存到 uploads 目录 → 写入 t_document（待处理）
         → 解析出纯文本 → 切分成片段 → 写入 Chroma → 更新状态为已向量化
"""
import os
import shutil
import uuid

import anydoc
import pymupdf4llm
from docx import Document as DocxDocument
from docx.table import Table
from langchain_core.documents import Document as LCDocument
from utils.text_splitter import split_markdown, txt_to_markdown

from config import BASE_DIR, Config
from extensions import db
from models import Document
from services.image_service import ImageService
from services.vector_store import VectorStore


class DocumentService:
    """文档相关业务逻辑。"""

    @staticmethod
    def allowed_file(filename: str) -> bool:
        """
        判断文件扩展名是否允许上传。

        :param filename: 文件名
        :return: True 允许
        """
        return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS

    @staticmethod
    def save_upload(file_storage, kb_id: int, user_id: int) -> Document:
        """
        保存上传的文件并创建文档记录。

        为避免文件名冲突和路径穿越，磁盘上使用 uuid 作为文件名，原始文件名只存数据库。

        :param file_storage: Flask 的 FileStorage 对象
        :param kb_id: 知识库ID
        :param user_id: 上传人ID
        :return: 新建的 Document 对象
        """
        original_name = os.path.basename(file_storage.filename)
        ext = original_name.rsplit(".", 1)[1].lower()
        os.makedirs(Config.UPLOAD_DIR, exist_ok=True)

        disk_name = f"{uuid.uuid4().hex}.{ext}"
        abs_path = os.path.join(Config.UPLOAD_DIR, disk_name)
        file_storage.save(abs_path)

        doc = Document(
            kb_id=kb_id,
            file_name=original_name,
            # 存相对 server 目录的路径，统一用 / 分隔，项目换目录也能找到文件
            file_path=os.path.relpath(abs_path, BASE_DIR).replace("\\", "/"),
            file_type=ext,
            file_size=os.path.getsize(abs_path),
            status=Document.STATUS_PENDING,
            uploaded_by=user_id,
        )
        db.session.add(doc)
        db.session.commit()
        return doc

    @staticmethod
    def extract_text(abs_path: str, file_type: str, image_dir: str | None = None) -> str:
        """
        从文件中提取 Markdown 文本。

        :param abs_path: 文件绝对路径
        :param file_type: 扩展名 txt/md/pdf/docx/csv 等
        :param image_dir: 图片导出目录，传入时 PDF 中的图片会保存到该目录，并在 Markdown 中留下 ![](路径) 占位
        :return: 文本内容
        """
        if file_type == "csv":
            # 优先按 UTF-8 读取，失败再尝试 GBK（Windows 记事本常见编码）
            try:
                with open(abs_path, "rb") as f:
                    return anydoc.to_markdown_bytes(f.read(), "csv")
            except Exception as e:
                raise ValueError(f"文件读取失败")

        if file_type in ("md", "txt"):
            # 优先按 UTF-8 读取，失败再尝试 GBK（Windows 记事本常见编码）
            try:
                with open(abs_path, encoding="utf-8") as f:
                    text = f.read()
            except UnicodeDecodeError:
                with open(abs_path, encoding="gbk", errors="ignore") as f:
                    text = f.read()
            # txt 没有 # 标题，不转换的话整篇只有一个章节，切出的大块混着多个主题，检索时很难命中
            return txt_to_markdown(text) if file_type == "txt" else text
        if file_type == "pdf":
            # anydoc 会把相邻的表格和正文合并成一张表，PDF 改用 pymupdf4llm 识别标题和表格
            # 注意：PyMuPDF 为 AGPL 协议，闭源商用需购买商业授权
            try:
                # header/footer=False 去掉每页重复的页眉页脚，避免混进正文
                return pymupdf4llm.to_markdown(abs_path, header=False, footer=False,
                                               write_images=bool(image_dir), image_path=image_dir or "")
            except Exception as e:  # noqa: BLE001 加密、损坏等情况统一转为业务异常
                raise ValueError(f"PDF 解析失败：{e}") from e
        if file_type in ("doc", "docx", "docm", "xls", "xlsx", "xlsm", "xlsb",
                         "ppt", "pps", "pot", "pptx", "pptm", "ppsx", "ppsm", "odt",
                         "ods", "odp", "rtf", "epub"):
            # reader = PdfReader(abs_path)
            # print(reader.pages[0].extract_text())
            # print("=" * 30)
            # return "\n".join(page.extract_text() or "" for page in reader.pages)
            try:
                return anydoc.to_markdown(abs_path)
            except (anydoc.EncryptedError, anydoc.UnsupportedError) as error:
                # No document comes out of these, so record the file and take the next one.
                raise ValueError(f"不支持的文件类型：{file_type}")
        # if file_type == "docx":
        #     return DocumentService._extract_docx(abs_path)
        raise ValueError(f"不支持的文件类型：{file_type}")

    @staticmethod
    def _extract_docx(abs_path: str) -> str:
        """
        提取 docx 文本，按原文顺序读取段落和表格。

        表格每行转为一行文本，单元格之间用 " | " 分隔，
        这样"字段名 | 类型 | 说明"这类规范表格也能被检索到。

        :param abs_path: 文件绝对路径
        :return: 文本内容
        """
        docx = DocxDocument(abs_path)
        lines = []
        # iter_inner_content 按文档中的先后顺序返回 Paragraph 和 Table
        for block in docx.iter_inner_content():
            if isinstance(block, Table):
                for row in block.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    lines.append(" | ".join(cells))
                lines.append("")
            elif block.text.strip():
                lines.append(block.text)
        return "\n".join(lines)

    # @staticmethod
    # def split_text(text: str, doc: Document) -> list[LCDocument]:
    #     """
    #     把长文本切分成多个片段，并为每个片段附加 metadata。
    #
    #     :param text: 文档全文
    #     :param doc: 文档记录
    #     :return: LangChain Document 列表
    #     """
    #     headers = [("#", "h1"), ("##", "h2"), ("###", "h3")]
    #     md_splitter = MarkdownHeaderTextSplitter(
    #         headers_to_split_on=headers,
    #         strip_headers=False,  # 保留标题文本在正文里，有助于检索命中
    #     )
    #     text_splitter = RecursiveCharacterTextSplitter(
    #         chunk_size=Config.CHUNK_SIZE,
    #         chunk_overlap=Config.CHUNK_OVERLAP,
    #         # 中文文档按段落、换行、句号等依次尝试切分
    #         separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
    #     )
    #     metadata = {"kb_id": doc.kb_id, "doc_id": doc.id, "file_name": doc.file_name}
    #     header_docs = md_splitter.split_text(text)
    #     for header_doc in header_docs:
    #         header_doc.metadata.update(metadata)
    #     return text_splitter.split_documents(header_docs)

    @staticmethod
    def _set_progress(doc: Document, progress: str) -> None:
        """更新处理阶段并立即提交，前端轮询列表时能看到最新进度。"""
        doc.status = Document.STATUS_PROCESSING
        doc.progress = progress
        db.session.commit()

    @staticmethod
    def index_document(doc: Document) -> Document:
        """
        对文档执行向量化：解析 → 识别图片 → 切分 → 删除旧向量 → 写入新向量 → 更新状态。
        每进入一个阶段都会更新 progress，失败时把状态置为 2 并记录原因，不抛出异常。
        耗时较长，接口中应通过 services.index_task.submit 放到后台执行。

        :param doc: 文档记录
        :return: 更新后的文档记录
        """
        try:
            abs_path = os.path.join(BASE_DIR, doc.file_path)
            DocumentService._set_progress(doc, "解析文档")
            image_dir = None
            if ImageService.enabled():
                # 重建索引时先清掉旧图片，图片会按新的解析结果重新导出
                image_dir = os.path.join(Config.IMAGE_DIR, str(doc.id))
                shutil.rmtree(image_dir, ignore_errors=True)
            text = DocumentService.extract_text(abs_path, doc.file_type, image_dir)
            if image_dir:
                text = ImageService.replace_images(
                    text, on_progress=lambda i, n: DocumentService._set_progress(doc, f"识别图片 {i}/{n}"))
            if not text.strip():
                raise ValueError("文档内容为空或无法解析")

            DocumentService._set_progress(doc, "切分文本")
            # 标题用去掉扩展名的文件名，拼在每个 chunk 开头作为上下文
            title = str(doc.file_name).rsplit(".", 1)[0]
            base_metadata = {"kb_id": doc.kb_id, "doc_id": doc.id, "file_name": doc.file_name}
            chunks = split_markdown(text, title, base_metadata)

            DocumentService._set_progress(doc, f"写入向量库 · {len(chunks)} 个片段")
            # 先删旧向量，保证重建索引时不会重复
            VectorStore.delete_by_doc(doc.id)
            doc.chunk_count = VectorStore.add_chunks(
                chunks, on_progress=lambda i, n: DocumentService._set_progress(doc, f"写入向量库 {i}/{n}"))
            doc.file_size = os.path.getsize(abs_path)
            doc.status = Document.STATUS_DONE
            doc.error_msg = ""
        except Exception as e:  # noqa: BLE001 入门项目统一捕获，记录到数据库便于排查
            db.session.rollback()
            doc.status = Document.STATUS_FAILED
            doc.error_msg = str(e)[:500]
        doc.progress = ""
        db.session.commit()
        return doc

    @staticmethod
    def delete_document(doc: Document) -> None:
        """
        删除文档：向量、磁盘文件、数据库记录。

        :param doc: 文档记录
        """
        VectorStore.delete_by_doc(doc.id)
        # 只删除上传目录下的文件，data/samples 中的示例文档保留
        abs_path = os.path.normpath(os.path.join(BASE_DIR, doc.file_path))
        if abs_path.startswith(os.path.normpath(Config.UPLOAD_DIR) + os.sep):
            if os.path.exists(abs_path):
                os.remove(abs_path)
        shutil.rmtree(os.path.join(Config.IMAGE_DIR, str(doc.id)), ignore_errors=True)
        db.session.delete(doc)
        db.session.commit()
