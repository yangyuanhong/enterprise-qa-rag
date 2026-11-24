"""
文档后台处理任务：上传和重建索引接口只把文档加入队列并立即返回，
解析、识图、切分、写入向量库在后台线程中执行，前端通过轮询文档列表查看进度。

设计说明：
    - 同一时间只处理一个文档。识图和 rerank 都依赖 GPU 上的大模型，多个文档并发会抢显存，整体反而更慢。
    - 线程池在 Flask 进程内，服务重启时队列中的任务会丢失，启动时由 recover_interrupted 把这些文档标记为失败。
    - 只适合单进程部署（app.run）。用 gunicorn 多进程部署时，每个进程各有一个队列，
      且某个进程重启会把其他进程正在处理的文档误标为失败。届时应换成 Celery / RQ，只需修改 submit 的提交方式。
"""
import logging
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, current_app

from extensions import db
from models import Document
from services.document_service import DocumentService

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="doc-index")


def submit(doc: Document) -> None:
    """
    把文档标记为排队中并加入后台处理队列，立即返回。需要在请求上下文中调用。

    :param doc: 文档记录
    """
    doc.status = Document.STATUS_PENDING
    doc.progress = "排队中"
    doc.error_msg = ""
    db.session.commit()
    # 后台线程没有请求上下文，把 app 对象传过去，在线程里自己创建应用上下文
    app = current_app._get_current_object()  # noqa: SLF001 Flask 官方推荐的取真实 app 对象的方式
    _executor.submit(_run, app, doc.id)


def _run(app: Flask, doc_id: int) -> None:
    """后台线程执行的任务。每个任务使用独立的应用上下文和数据库会话，按ID重新查询文档。"""
    with app.app_context():
        doc = db.session.get(Document, doc_id)
        if doc is None:
            return
        try:
            DocumentService.index_document(doc)
        except Exception:  # noqa: BLE001 index_document 自身已捕获业务异常，这里兜底数据库连接等意外错误
            logger.exception("文档处理任务异常：doc_id=%s", doc_id)
            db.session.rollback()
            doc = db.session.get(Document, doc_id)
            if doc is not None:
                doc.status = Document.STATUS_FAILED
                doc.progress = ""
                doc.error_msg = "处理任务异常中断，请查看服务端日志后重建索引"
                db.session.commit()


def recover_interrupted(app: Flask) -> int:
    """
    服务启动时调用：把排队中、处理中的文档标记为失败。
    进程内的任务队列在重启后已经不存在，不处理的话这些文档会一直停留在“处理中”。

    :param app: Flask 应用
    :return: 被标记为失败的文档数量
    """
    with app.app_context():
        count = (Document.query
                 .filter(Document.status.in_(Document.UNFINISHED))
                 .update({"status": Document.STATUS_FAILED,
                          "progress": "",
                          "error_msg": "服务重启，处理任务已中断，请点击“重建索引”重新处理"},
                         synchronize_session=False))
        db.session.commit()
        if count:
            logger.warning("服务重启，%s 个未完成的文档已标记为失败", count)
        return count
