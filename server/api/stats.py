"""
统计接口（仅管理员）：为后台首页图表提供数据。
"""
from flask import Blueprint

from services.stats_service import StatsService
from utils.decorators import admin_required
from utils.response import success

stats_bp = Blueprint("stats", __name__)


@stats_bp.get("/overview")
@admin_required
def overview():
    """概览卡片数据。"""
    return success(StatsService.overview())


@stats_bp.get("/trend")
@admin_required
def trend():
    """近 7 天提问趋势（折线图）。"""
    return success(StatsService.question_trend(7))


@stats_bp.get("/doc-distribution")
@admin_required
def doc_distribution():
    """各知识库文档分布（饼图）。"""
    return success(StatsService.doc_distribution())


@stats_bp.get("/active-users")
@admin_required
def active_users():
    """活跃用户 Top5（柱状图）。"""
    return success(StatsService.active_users(5))
