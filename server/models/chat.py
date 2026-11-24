"""
会话与消息模型：对应 t_chat_session、t_chat_message 表。
"""
from datetime import datetime

from extensions import BaseModel, db


class ChatSession(BaseModel):
    """会话模型，一个用户可以有多个会话，每个会话包含多条消息。"""

    __tablename__ = "t_chat_session"

    id = db.Column(db.Integer, primary_key=True, comment="主键")
    user_id = db.Column(db.Integer, db.ForeignKey("t_user.id", ondelete="CASCADE"),
                        nullable=False, comment="所属用户ID")
    title = db.Column(db.String(100), nullable=False, default="新对话", comment="会话标题")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now,
                           onupdate=datetime.now, comment="最后活跃时间")

    messages = db.relationship("ChatMessage", backref="session", lazy="dynamic",
                               passive_deletes=True, order_by="ChatMessage.id")

    def to_dict(self):
        """转换为字典。"""
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
            "updated_at": self.updated_at.strftime("%Y-%m-%d %H:%M:%S") if self.updated_at else None,
        }


class ChatMessage(BaseModel):
    """消息模型，role 为 user（提问）或 assistant（回答），sources 存放引用片段。"""

    __tablename__ = "t_chat_message"

    id = db.Column(db.Integer, primary_key=True, comment="主键")
    session_id = db.Column(db.Integer, db.ForeignKey("t_chat_session.id", ondelete="CASCADE"),
                           nullable=False, comment="所属会话ID")
    role = db.Column(db.String(20), nullable=False, comment="user / assistant")
    content = db.Column(db.Text, nullable=False, comment="消息内容")
    sources = db.Column(db.JSON, nullable=True, comment="引用片段")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now, comment="创建时间")

    def to_dict(self):
        """转换为字典。"""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "sources": self.sources or [],
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }
