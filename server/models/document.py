"""
文档模型：对应 t_document 表。
"""
from datetime import datetime

from extensions import db, BaseModel


class Document(BaseModel):
    """文档模型，记录上传文件信息和向量化状态。"""

    __tablename__ = "t_document"

    # 状态常量，便于代码中引用
    STATUS_PENDING = 0  # 排队中，等待后台任务处理
    STATUS_DONE = 1  # 已向量化
    STATUS_FAILED = 2  # 失败
    STATUS_PROCESSING = 3  # 处理中，progress 字段记录当前阶段
    # 未完成的状态，前端据此判断是否需要轮询刷新
    UNFINISHED = (STATUS_PENDING, STATUS_PROCESSING)

    id = db.Column(db.Integer, primary_key=True, comment="主键")
    kb_id = db.Column(db.Integer, db.ForeignKey("t_knowledge_base.id", ondelete="CASCADE"),
                      nullable=False, comment="所属知识库ID")
    file_name = db.Column(db.String(255), nullable=False, comment="原始文件名")
    file_path = db.Column(db.String(500), nullable=False, comment="存储路径（相对 server 目录）")
    file_type = db.Column(db.String(20), nullable=False, comment="文件类型")
    file_size = db.Column(db.Integer, nullable=False, default=0, comment="文件大小（字节）")
    chunk_count = db.Column(db.Integer, nullable=False, default=0, comment="片段数量")
    status = db.Column(db.SmallInteger, nullable=False, default=0, comment="0 排队中 1 已向量化 2 失败 3 处理中")
    progress = db.Column(db.String(100), nullable=False, default="", comment="处理进度，如“识别图片 3/5”")
    error_msg = db.Column(db.String(500), nullable=False, default="", comment="失败原因")
    uploaded_by = db.Column(db.Integer, nullable=True, comment="上传人ID")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now, comment="上传时间")

    def to_dict(self):
        """转换为字典，附带知识库名称。"""
        return {
            "id": self.id,
            "kb_id": self.kb_id,
            "kb_name": self.knowledge_base.name if self.knowledge_base else "",
            "file_name": self.file_name,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "chunk_count": self.chunk_count,
            "status": self.status,
            "progress": self.progress,
            "error_msg": self.error_msg,
            "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S") if self.created_at else None,
        }
