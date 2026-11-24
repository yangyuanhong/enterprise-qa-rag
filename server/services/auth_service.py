"""
认证服务：密码 MD5 加密、登录校验、JWT 生成与解析。
"""
import hashlib
from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app

from models import User


class AuthService:
    """认证相关的静态方法集合。"""

    @staticmethod
    def md5(raw_password: str) -> str:
        """
        对明文密码做 MD5 加密，返回 32 位小写十六进制字符串。

        注意：MD5 不加盐容易被彩虹表破解，这里按学习项目要求使用
        生产环境建议改用 bcrypt / argon2 等专用密码哈希算法。
        """
        return hashlib.md5(raw_password.encode("utf-8")).hexdigest()

    @staticmethod
    def login(username: str, password: str):
        """
        校验用户名和密码。

        :param username: 账号
        :param password: 明文密码
        :return: (User, None) 成功；(None, 错误信息) 失败
        """
        user = User.query.filter_by(username=username).first()
        if user is None or user.password != AuthService.md5(password):
            return None, "用户名或密码错误"
        if user.status != 1:
            return None, "账号已被禁用，请联系管理员"
        return user, None

    @staticmethod
    def create_token(user: User) -> str:
        """
        为用户生成 JWT，载荷中包含用户ID、角色和过期时间。
        eyJhbGciOiJIUzI1NiJ9.eyJ1aWQiOjEsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc2MH0.签名
        头部（算法）            载荷（uid、role、过期时间 exp）                   用 JWT_SECRET 计算


        :param user: 用户对象
        :return: token 字符串
        """
        expire = datetime.now(timezone.utc) + timedelta(hours=current_app.config["JWT_EXPIRE_HOURS"])
        payload = {"uid": user.id, "role": user.role, "exp": expire}
        return jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")

    @staticmethod
    def decode_token(token: str):
        """
        解析并校验 JWT。

        :param token: token 字符串
        :return: 载荷 dict: 无效时间或过期返回Node
        """
        try:
            return jwt.decode(token, current_app.config["JWT_SECRET"], algorithms=["HS256"])
        except jwt.PyJWTError:
            return None
       