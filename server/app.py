"""
应用入口：创建 Flask 应用、注册扩展和蓝图。
启动：uv run python app.py，默认监听 http://127.0.0.1:5000
"""
import os
from typing import cast

from flask import Flask
from flask.json.provider import DefaultJSONProvider
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from api import register_blueprints
from config import Config
from extensions import db
from utils.response import error


def create_app() -> Flask:
    """
    应用工厂函数

    :return: 配置完成的 Flask应用
    """
    app = Flask(__name__)
    app.config.from_object(Config)
    # 中文JSON不转义
    cast(DefaultJSONProvider, app.json).ensure_ascii = False

    os.makedirs(Config.UPLOAD_DIR, exist_ok=True)

    db.init_app(app)
    # 开发环境前端走 Vite 代理，这里放开 /api 跨域，方便直接调试
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    register_blueprints(app)
    register_error_handlers(app)

    @app.get("/api/health")
    def health():
        """健康检查接口。"""
        return {"status": "ok"}

    return app


def register_error_handlers(app: Flask) -> None:
    """
    注册全局异常处理，所有错误都返回统一 JSON 格式。

    :param app: Flask 应用
    """

    @app.errorhandler(HTTPException)
    def handle_http_error(e: HTTPException):
        """处理 404、405、413 等 HTTP 异常。"""
        msg = "上传文件不能超过 20MB" if e.code == 413 else e.description
        return error(msg, code=e.code, http_status=e.code)

    @app.errorhandler(Exception)
    def handle_exception(e: Exception):
        """处理未捕获的异常，回滚数据库事务并返回 500。"""
        db.session.rollback()
        app.logger.exception(e)
        return error(f"服务器内部错误：{e}", code=500, http_status=500)


finalApp = create_app()

if __name__ == "__main__":
    # 后台处理队列在进程内，重启后已丢失，把上次未完成的文档标记为失败。
    # 放在这里而不是 create_app 中，避免脚本里调用 create_app 时误标正在处理的文档
    from services.index_task import recover_interrupted
    recover_interrupted(finalApp)
    # threaded=True 允许流式问答时同时处理其他请求
    finalApp.run(host="127.0.0.1", port=5000, debug=True, threaded=True)
