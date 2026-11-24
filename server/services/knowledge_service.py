"""
知识库服务：知识库路由中转
"""
from models import KnowledgeBase
from utils.response import success

class KnowledgeService:

    @classmethod
    def query_knowledge(cls) -> list[dict]:
        """查询全部知识库。"""
        rows = KnowledgeBase.query.order_by(KnowledgeBase.id).all()
        return [kb.to_dict() for kb in rows]