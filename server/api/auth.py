"""
认证接口：登录、获取个人信息、修改密码
"""
from flask import Blueprint, g, request

from extensions import db
from services.auth_service import AuthService
from utils.decorators import login_required
from utils.response import error, success

auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/login")
def login():
    """
    用户登录。

    请求体：{"username": "admin", "password": "123456"}
    返回：{"token": "...", "user": {...}}
    """
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    if not username or not password:
        return error("请输入用户名和密码")

    user, err = AuthService.login(username, password)
    if err:
        return error(err)
    return success({"token": AuthService.create_token(user), "user": user.to_dict()}, "登录成功")


@auth_bp.get("/profile")
@login_required
def profile():
    """获取当前登录用户信息。"""
    return success(g.current_user.to_dict())


@auth_bp.put("/password")
@login_required
def change_password():
    """
    修改自己的密码。

    请求体：{"old_password": "...", "new_password": "..."}
    """
    body = request.get_json(silent=True) or {}
    old_pwd = body.get("old_password") or ""
    new_pwd = body.get("new_password") or ""
    user = g.current_user

    if user.password != AuthService.md5(old_pwd):
        return error("原密码错误")
    if len(new_pwd) < 6:
        return error("新密码长度不能少于 6 位")

    user.password = AuthService.md5(new_pwd)
    db.session.commit()
    return success(msg="密码修改成功")
