from datetime import date, datetime, timedelta

from sqlalchemy import func

from extensions import db
from models import ChatMessage, ChatSession, Document, KnowledgeBase, User


class StatsService:
    """统计查询方法集合"""

    @staticmethod
    def overview() -> dict:
        """
        概览卡片数据：用户数、知识库数、文档数、问答总数、今日问答数。

        :return: dict
        """
        today_start = datetime.combine(date.today(), datetime.min.time())
        question_query = ChatMessage.query.filter_by(role="user")
        return {
            "user_count": User.query.count(),
            "kb_count": KnowledgeBase.query.count(),
            "doc_count": Document.query.count(),
            "question_count": question_query.count(),
            "today_question_count": question_query.filter(ChatMessage.created_at >= today_start).count(),
        }

    @staticmethod
    def question_trend(days: int = 7) -> dict:
        """
        近 N 天每日提问数量（折线图），没有数据的日期补 0。

        :param days: 天数
        :return: {"dates": [...], "counts": [...]}
        """
        start = date.today() - timedelta(days=days - 1)
        day_col = func.date(ChatMessage.created_at)
        rows = (db.session.query(day_col, func.count(ChatMessage.id))
                .filter(ChatMessage.role == "user",
                        ChatMessage.created_at >= datetime.combine(start, datetime.min.time()))
                .group_by(day_col).all())
        # 数据库返回的日期可能是 date 或字符串，统一转成字符串作为 key
        count_map = {str(d): c for d, c in rows}

        dates, counts = [], []
        for i in range(days):
            d = str(start + timedelta(days=i))
            dates.append(d[5:])  # 只显示 MM-DD
            counts.append(count_map.get(d, 0))
        return {"dates": dates, "counts": counts}

    @staticmethod
    def doc_distribution() -> list:
        """
        各知识库文档数量（饼图）。

        :return: [{"name": 知识库名, "value": 文档数}]
        """
        rows = (db.session.query(KnowledgeBase.name, func.count(Document.id))
                .outerjoin(Document, Document.kb_id == KnowledgeBase.id)
                .group_by(KnowledgeBase.id, KnowledgeBase.name).all())
        return [{"name": name, "value": count} for name, count in rows]

    @staticmethod
    def active_users(limit: int = 5) -> dict:
        """
        提问次数最多的用户 Top N（柱状图）。

        :param limit: 返回条数
        :return: {"names": [...], "counts": [...]}
        """
        count_col = func.count(ChatMessage.id).label("cnt")
        rows = (db.session.query(User.nickname, count_col)
                .join(ChatSession, ChatSession.user_id == User.id)
                .join(ChatMessage, ChatMessage.session_id == ChatSession.id)
                .filter(ChatMessage.role == "user")
                .group_by(User.id, User.nickname)
                .order_by(count_col.desc())
                .limit(limit).all())
        return {"names": [r[0] for r in rows], "counts": [r[1] for r in rows]}
