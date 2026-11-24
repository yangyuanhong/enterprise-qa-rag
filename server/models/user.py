"""
用户模型：对应 t_user 表。
"""
from datetime import datetime

from extensions import db, BaseModel


class User(BaseModel):
    """用户表模型，role 取值 admin（管理员）或 user（普通用户）。"""

    __tablename__ = "t_user"

    id = db.Column(db.Integer, primary_key=True, comment="主键")
    username = db.Column(db.String(50), unique=True, nullable=False, comment="登录账号")
    password = db.Column(db.String(32), nullable=False, comment="MD5 密码")
    nickname = db.Column(db.String(50), nullable=False, default="", comment="昵称")
    role = db.Column(db.String(20), nullable=False, default="user", comment="角色")
    status = db.Column(db.SmallInteger, nullable=False, default=1, comment="1 启用 0 禁用")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now, comment="创建时间")
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.now,
                           onupdate=datetime.now, comment="更新时间")

    def to_dict(self):
        """转换为字典，注意不返回密码字段。"""
        return {
            "id": self.id,
            "username": self.username,
            "nickname": self.nickname,
            "role": self.role,
            "status": self.status,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }
