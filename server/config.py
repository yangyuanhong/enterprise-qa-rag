"""
配置模块：从 .env 文件读取所有配置项，集中管理
"""
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv

# server 目录的绝对路径，所有相对路径都以它为基准
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 加载server/.env中的环境变量
load_dotenv(os.path.join(BASE_DIR, '.env'))


class Config:
    """应用配置类，Flask 通过 app.config.from_object(Config) 加载。"""

    # ---------- 数据库 ----------
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_NAME = os.getenv("DB_NAME", "db_enterprise_qa")
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    # 密码做URL编码，防止含@：/ 等特殊字符时连接串解析出错
    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{DB_USER}:{quote_plus(DB_PASSWORD)}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 连接池回收时间，防止MySQL 断开空闲连接后报错
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_recycle": 3600, "pool_pre_ping": True}

    # ---------- JWT ----------
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret")
    JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

    # ---------- Ollama 大模型 ----------
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    LLM_MODEL = os.getenv("LLM_MODEL", "qwen3:8b")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "qwen3-embedding:4b")
    # 视觉模型：把文档中的图片转成文字描述后再切分入库，设为空字符串则不识别图片
    VISION_MODEL = os.getenv("VISION_MODEL", "qwen3-vl:8b-instruct")

    # ---------- Chroma 向量库 ----------
    CHROMA_DIR = os.path.join(BASE_DIR, os.getenv("CHROMA_DIR", "chroma_db"))
    CHROMA_COLLECTION = os.getenv("CHROMA_COLLECTION", "enterprise_kb")

    # ---------- RAG 参数 ----------
    CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
    CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))
    TOP_K = int(os.getenv("TOP_K", "4"))
    # 相似度阈值：低于该值的片段视为不相关，不交给大模型，也不作为参考来源展示。
    # 与 embedding 模型强相关，更换模型后需用真实问题重新测定（见 scripts/eval_threshold.py）
    SCORE_THRESHOLD = float(os.getenv("SCORE_THRESHOLD", "0.45"))

    # ---------- Rerank 重排序 ----------
    # 向量检索先召回 RERANK_CANDIDATES 条，再由 rerank 模型逐条打分，取前 TOP_K 条。设为空字符串则不启用
    RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3-int8")
    RERANK_CANDIDATES = int(os.getenv("RERANK_CANDIDATES", "20"))
    # rerank 分数经 sigmoid 换算到 0~1，低于该值视为不相关；启用 rerank 后不再使用 SCORE_THRESHOLD
    RERANK_THRESHOLD = float(os.getenv("RERANK_THRESHOLD", "0.3"))
    # 关键词检索：问题里的专有名词命中的片段数不超过该值时，这些片段一定进入候选并保留在结果中；
    # 超过说明这个词太常见（如 Python），不作为关键词使用
    KEYWORD_MAX_HITS = int(os.getenv("KEYWORD_MAX_HITS", "3"))
    # 模型文件缓存目录，首次使用时从 Hugging Face 下载
    MODEL_CACHE_DIR = os.path.join(BASE_DIR, os.getenv("MODEL_CACHE_DIR", "models_cache"))

    # ---------- 文件上传 ----------
    UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
    # 从文档中提取的图片，按文档ID分子目录存放：uploads/images/<doc_id>/
    IMAGE_DIR = os.path.join(UPLOAD_DIR, "images")
    # 宽或高小于该像素的图片视为图标、线条等装饰，不做识别
    IMAGE_MIN_SIZE = int(os.getenv("IMAGE_MIN_SIZE", "100"))
    ALLOWED_EXTENSIONS = {"txt", "md", "pdf", "docx", "csv"}
    # 单个文件最大 20MB
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024
