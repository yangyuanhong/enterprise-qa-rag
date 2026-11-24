"""
接口层：每个模块一个蓝图，统一在 register_blueprints 中注册，前缀 /api。
"""
from api.auth import auth_bp
from api.user import user_bp
from api.stats import stats_bp
from api.knowledge import knowledge_bp
from api.document import document_bp
from api.chat import chat_bp


def register_blueprints(app):
    """
    注册所有蓝图。

    :param app: Flask 应用
    """
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(user_bp, url_prefix="/api/users")
    app.register_blueprint(stats_bp, url_prefix="/api/stats")
    app.register_blueprint(knowledge_bp, url_prefix="/api/knowledge")
    app.register_blueprint(document_bp, url_prefix="/api/documents")
    app.register_blueprint(chat_bp, url_prefix="/api/chat")
