"""
问答接口：会话管理、消息历史、流式提问。
用户只能访问自己的会话。
"""
from flask import Blueprint, Response, g, request, stream_with_context

from extensions import db
from models import ChatMessage, ChatSession
from services.agent_service import AgentService
from utils.decorators import login_required
from utils.response import error, success

chat_bp = Blueprint("chat", __name__)


def _get_own_session(session_id: int):
    """
    获取属于当前用户的会话。

    :param session_id: 会话ID
    :return: ChatSession 或 None
    """
    return ChatSession.query.filter_by(id=session_id, user_id=g.current_user.id).first()


@chat_bp.get("/sessions")
@login_required
def list_sessions():
    """查询当前用户的会话列表，按最后活跃时间倒序。"""
    rows = (ChatSession.query.filter_by(user_id=g.current_user.id)
            .order_by(ChatSession.updated_at.desc(), ChatSession.id.desc()).all())
    return success([s.to_dict() for s in rows])


@chat_bp.post("/sessions")
@login_required
def create_session():
    """新建会话。"""
    session = ChatSession(user_id=g.current_user.id, title="新对话")
    db.session.add(session)
    db.session.commit()
    return success(session.to_dict())


@chat_bp.delete("/sessions/<int:session_id>")
@login_required
def delete_session(session_id):
    """删除会话及其消息。"""
    session = _get_own_session(session_id)
    if session is None:
        return error("会话不存在")
    db.session.delete(session)
    db.session.commit()
    return success(msg="删除成功")


@chat_bp.get("/sessions/<int:session_id>/messages")
@login_required
def list_messages(session_id):
    """查询会话的全部消息。"""
    session = _get_own_session(session_id)
    if session is None:
        return error("会话不存在")
    rows = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.id).all()
    return success([m.to_dict() for m in rows])


@chat_bp.post("/ask")
@login_required
def ask():
    """
    流式提问，返回 text/event-stream。
    请求体：{"session_id":1, "question":"...", "kb_id":可选}
    """
    body = request.get_json(silent=True) or {}
    question = (body.get("question") or "").strip()
    if not question:
        return error("问题不能为空")
    if len(question) > 1000:
        return error("问题不能超过 1000 字")

    session = _get_own_session(body.get("session_id") or 0)
    if session is None:
        return error("会话不存在")

    generator = AgentService.stream_answer(session.id, question, body.get("kb_id") or None)
    return Response(
        stream_with_context(generator),
        mimetype="text/event-stream",
        # 禁止缓存和代理缓冲，保证逐字推送
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
