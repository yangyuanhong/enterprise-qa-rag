"""
知识库模型：对应 t_knowledge_base 表。
"""
from datetime import datetime

from extensions import db, BaseModel


class KnowledgeBase(BaseModel):
    """知识库（文档分类）模型，一个知识库下有多个文档"""
    __tablename__ = "t_knowledge_base"

    id = db.Column(db.Integer, primary_key=True, comment="主键")
    name = db.Column(db.String(100), unique=True, nullable=False, comment="知识库名称")
    description = db.Column(db.String(500), nullable=False, default="", comment="描述")
    created_by = db.Column(db.Integer, nullable=True, comment="创建人ID")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now, comment="创建时间")

    # 一对多关系：删除知识库时由数据库外键级联删除文档记录
    documents = db.relationship("Document", backref="knowledge_base", lazy="dynamic",
                                passive_deletes=True)

    def to_dict(self):
        """转换为字典，附带文档数量。"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "doc_count": self.documents.count(),
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }
