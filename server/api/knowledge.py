"""
知识库接口：列表（所有登录用户可查，用于问答时选择范围），增删改（仅管理员）。
"""
from flask import Blueprint, g, request

from extensions import db
from models import KnowledgeBase
from services.knowledge_service import KnowledgeService
from utils.decorators import admin_required, login_required
from utils.response import error, success

knowledge_bp = Blueprint("knowledge", __name__)


@knowledge_bp.get("")
@login_required
def list_knowledge():
    return success(KnowledgeService.query_knowledge())

@knowledge_bp.post("")
@admin_required
def create_knowledge():
    """
    新增知识库。

    请求体：{"name", "description"}
    """
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return error("名称不能为空")
    if KnowledgeBase.query.filter_by(name=name).first():
        return error("知识库名称已存在")

    kb = KnowledgeBase(name=name, description=(body.get("description") or "").strip(),
                       created_by=g.current_user.id)
    db.session.add(kb)
    db.session.commit()
    return success(kb.to_dict(), "新增成功")


@knowledge_bp.put("/<int:kb_id>")
@admin_required
def update_knowledge(kb_id):
    """
    编辑知识库名称和描述。

    请求体：{"name", "description"}
    """
    kb = db.session.get(KnowledgeBase, kb_id)
    if kb is None:
        return error("知识库不存在")
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return error("名称不能为空")
    if KnowledgeBase.query.filter(KnowledgeBase.name == name, KnowledgeBase.id != kb_id).first():
        return error("知识库名称已存在")

    kb.name = name
    kb.description = (body.get("description") or "").strip()
    db.session.commit()
    return success(kb.to_dict(), "保存成功")


@knowledge_bp.delete("/<int:kb_id>")
@admin_required
def delete_knowledge(kb_id):
    """删除知识库。为避免误删，知识库下还有文档时不允许删除。"""
    kb = db.session.get(KnowledgeBase, kb_id)
    if kb is None:
        return error("知识库不存在")
    if kb.documents.count() > 0:
        return error("请先删除该知识库下的文档")
    db.session.delete(kb)
    db.session.commit()
    return success(msg="删除成功")
