"""
扩展实例模块：在这里创建扩展对象，在 app.py 中调用 init_app 绑定，避免循环导入。
"""
from typing import ClassVar

from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy.query import Query

# 全局数据库对象，模型和服务层都从这里导入
db = SQLAlchemy()


class BaseModel(db.Model):
    """
    模型抽象基类。db.Model 是运行时动态生成的，IDE 无法推断其属性，
    这里显式声明 query 的类型，消除 PyCharm "未解析的特性引用" 警告。
    """
    __abstract__ = True
    query: ClassVar[Query]
