"""
统一响应格式：所有接口都返回 {"code": 0, "msg": "...", "data": ...}。
code 为 0 表示成功，非 0 表示失败，前端据此统一处理。
"""
from flask import jsonify


def success(data=None, msg="success"):
    """
    返回成功响应

    :param data: 业务数据
    :param msg: 提示信息
    :return: Flask Response，HTTP 状态码 200
    """
    return jsonify({"code": 0, "msg": msg, "data": data})


def error(msg="error", code=1, http_status=200):
    """
    返回失败响应。

    :param msg: 错误提示
    :param code: 业务错误码，401 未登录，403无权限，其它为普通业务错误
    :param http_status: HTTP 状态码，鉴权失败时使用 401/403
    :return: (Response, 状态码) 元组
    """
    return jsonify({"code": code, "msg": msg, "data": None}), http_status


def page_data(items, total, page, size):
    """
    构造分页数据结构。

    :param items: 当前页数据列表
    :param total: 总条数
    :param page: 当前页码
    :param size: 每页条数
    :return: dict
    """
    return {"list": items, "total": total, "page": page, "size": size}
