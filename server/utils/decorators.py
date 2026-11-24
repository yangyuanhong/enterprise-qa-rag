"""
权限装饰器：login_required 校验登录，admin_required 校验管理员角色。
校验通过后，当前用户对象挂在 flask.g.current_user 上，接口内直接使用。
"""
from functools import wraps

from flask import g, request

from extensions import db
from models import User
from services.auth_service import AuthService
from utils.response import error


def _load_current_user():
    """
    从请求头 Authorization: Bearer <token> 解析出当前用户。

    :return: (User, None) 成功；(None, 错误响应) 失败
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, error("请先登录", code=401, http_status=401)

    payload = AuthService.decode_token(auth_header[7:])
    if payload is None:
        return None, error("登录已过期，请重新登录", code=401, http_status=401)

    user = db.session.get(User, payload.get("uid"))
    if user is None or user.status != 1:
        return None, error("账号不存在或已被禁用", code=401, http_status=401)
    return user, None


def login_required(func):
    """装饰器：要求用户已登录。"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        user, err = _load_current_user()
        if err:
            return err
        g.current_user = user
        return func(*args, **kwargs)

    return wrapper


def admin_required(func):
    """装饰器：要求用户已登录且角色为管理员。"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        user, err = _load_current_user()
        if err:
            return err
        if user.role != "admin":
            return error("没有权限，仅管理员可操作", code=403, http_status=403)
        g.current_user = user
        return func(*args, **kwargs)

    return wrapper
