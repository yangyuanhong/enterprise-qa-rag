"""
用户管理接口（仅管理员）：分页查询、新增、编辑、删除、重置密码。
"""
from flask import Blueprint, g, request

from extensions import db
from models import User
from services.auth_service import AuthService
from utils.decorators import admin_required
from utils.response import error, page_data, success

user_bp = Blueprint("user", __name__)

# 新增用户和重置密码时使用的默认密码
DEFAULT_PASSWORD = "123456"


@user_bp.get("")
@admin_required
def list_users():
    """
    分页查询用户。

    查询参数：page 页码，size 每页条数，keyword 按账号/昵称模糊搜索
    """
    page = request.args.get("page", 1, type=int)
    size = request.args.get("size", 10, type=int)
    keyword = (request.args.get("keyword") or "").strip()

    query = User.query
    if keyword:
        like = f"%{keyword}%"
        query = query.filter(db.or_(User.username.like(like), User.nickname.like(like)))
    pagination = query.order_by(User.id.desc()).paginate(page=page, per_page=size, error_out=False)
    return success(page_data([u.to_dict() for u in pagination.items], pagination.total, page, size))


@user_bp.post("")
@admin_required
def create_user():
    """
    新增用户。

    请求体：{"username", "nickname", "role", "password"(可选，默认 123456)}
    """
    body = request.get_json(silent=True) or {}
    username = (body.get("username") or "").strip()
    if not username:
        return error("账号不能为空")
    if User.query.filter_by(username=username).first():
        return error("账号已存在")
    role = body.get("role", "user")
    if role not in ("admin", "user"):
        return error("角色不正确")
    # noinspection PyArgumentList
    user = User(
        username=username,
        nickname=(body.get("nickname") or username).strip(),
        role=role,
        password=AuthService.md5(body.get("password") or DEFAULT_PASSWORD),
        status=1,
    )
    db.session.add(user)
    db.session.commit()
    return success(user.to_dict(), "新增成功")


@user_bp.put("/<int:user_id>")
@admin_required
def update_user(user_id):
    """
    编辑用户昵称、角色、状态。

    请求体：{"nickname", "role", "status"}
    """
    user = db.session.get(User, user_id)
    if user is None:
        return error("用户不存在")
    body = request.get_json(silent=True) or {}
    if user.id == g.current_user.id and (body.get("status") == 0 or body.get("role") == "user"):
        return error("不能禁用自己或取消自己的管理员权限")

    if "nickname" in body:
        user.nickname = (body["nickname"] or "").strip()
    if body.get("role") in ("admin", "user"):
        user.role = body["role"]
    if body.get("status") in (0, 1):
        user.status = body["status"]
    db.session.commit()
    return success(user.to_dict(), "保存成功")


@user_bp.put("/<int:user_id>/reset-password")
@admin_required
def reset_password(user_id):
    """把用户密码重置为默认密码 123456。"""
    user = db.session.get(User, user_id)
    if user is None:
        return error("用户不存在")
    user.password = AuthService.md5(DEFAULT_PASSWORD)
    db.session.commit()
    return success(msg=f"密码已重置为 {DEFAULT_PASSWORD}")


@user_bp.delete("/<int:user_id>")
@admin_required
def delete_user(user_id):
    """删除用户（其会话和消息由外键级联删除）。"""
    if user_id == g.current_user.id:
        return error("不能删除自己")
    user = db.session.get(User, user_id)
    if user is None:
        return error("用户不存在")
    db.session.delete(user)
    db.session.commit()
    return success(msg="删除成功")
