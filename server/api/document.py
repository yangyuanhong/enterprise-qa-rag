"""
文档管理接口（仅管理员）：分页查询、上传并向量化、删除、重建索引。
"""
from flask import Blueprint, g, request
from flask_sqlalchemy import pagination

from extensions import db
from models import Document, KnowledgeBase
from services import index_task
from services.document_service import DocumentService
from utils.decorators import admin_required
from utils.response import error, page_data, success

document_bp = Blueprint('document', __name__)


@document_bp.get("")
@admin_required
def list_documents():
    """
    分页查询文档。

    查询参数：page、size、kb_id（按知识库筛选）、keyword（按文件名搜索）
    """

    page = request.args.get("page", 1, type=int)
    size = request.args.get("size", 10, type=int)
    kb_id = request.args.get("kb_id", type=int)
    keyword = (request.args.get("keyword") or "").strip()

    query = Document.query
    if kb_id:
        query = query.filter_by(kb_id=kb_id)
    if keyword:
        query = query.filter(Document.file_name.like("%" + keyword + "%"))
    pagination = query.order_by(Document.id.desc()).paginate(page=page, per_page=size, error_out=False)
    return success(page_data([d.to_dict() for d in pagination.items], pagination.total, page, size))


@document_bp.post("/upload")
@admin_required
def upload_document():
    """
    上传文档：保存文件后加入后台处理队列并立即返回，解析和向量化在后台执行。

    表单字段：file 文件，kb_id 知识库ID
    """
    file = request.files.get("file")
    kb_id = request.form.get("kb_id", type=int)
    if file is None or not file.filename:
        return error("请选择文件")
    if not DocumentService.allowed_file(file.filename):
        return error("仅支持 txt、md、pdf、docx、csv 格式")
    if not kb_id or db.session.get(KnowledgeBase, kb_id) is None:
        return error("请选择正确的知识库")
    doc = DocumentService.save_upload(file, kb_id, g.current_user.id)
    index_task.submit(doc)
    return success(doc.to_dict(), "上传成功，已加入处理队列，可在列表中查看进度")


@document_bp.post("/<int:doc_id>/reindex")
@admin_required
def reindex_document(doc_id):
    """重新向量化文档（例如更换嵌入模型或调整切分参数后），加入后台队列后立即返回。"""
    doc = db.session.get(Document, doc_id)
    if doc is None:
        return error("文档不存在")
    if doc.status in Document.UNFINISHED:
        return error("文档正在处理中，请等待处理完成")
    index_task.submit(doc)
    return success(doc.to_dict(), "已加入处理队列")


@document_bp.delete("/<int:doc_id>")
@admin_required
def delete_document(doc_id):
    """删除文档及其向量。"""
    doc = db.session.get(Document, doc_id)
    if doc is None:
        return error("文档不存在")
    # 处理中删除会和后台任务冲突：任务可能在删除后又把向量写回向量库
    if doc.status in Document.UNFINISHED:
        return error("文档正在处理中，请等待处理完成后再删除")
    DocumentService.delete_document(doc)
    return success(msg="删除成功")
