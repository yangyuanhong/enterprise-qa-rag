"""
问答 Agent 服务：基于 LangChain 1.x 的 create_agent 构建 RAG Agent。

工作原理：
    1. 收到问题后先用原问题检索一次，相关片段作为参考资料随问题一起交给大模型
       （由代码检索而不是等模型决定，避免模型凭自身知识作答、回答没有来源）
    2. 预检索不够用时，大模型还可以调用 search_knowledge_base 工具换关键词再查
    3. 大模型根据参考资料组织答案，流式输出给前端
    4. 问题、答案、引用来源都保存到 MySQL
"""
import json
import re
from datetime import datetime

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama

from config import Config
from extensions import db
from models import ChatMessage, ChatSession
from services.rerank_service import RerankService
from services.vector_store import VectorStore

# 系统提示词：约束 Agent 必须先检索、只依据检索结果回答
SYSTEM_PROMPT = """你是"示例科技有限公司"的企业内部知识库助手，负责解答员工关于公司制度、IT 支持、财务报销等问题。

工作要求：
1. 用户消息中如果附有【参考资料】，优先依据参考资料回答；资料与问题无关时忽略它。
   只有资料直接回答了问题才算相关，例如问 CSS 框架而资料只列了 Vue、React 等前端框架，属于不相关，不要拿来推测答案。
2. 参考资料不足以回答与公司相关的问题时，调用 search_knowledge_base 工具换用更具体的关键词再检索。
3. 只能依据参考资料和检索结果回答，不要用自身知识补充或编造知识库中没有的信息。
4. 检索后仍没有相关内容时，直接回答"知识库中暂未找到相关内容，建议咨询相关部门。"
5. 回答使用简体中文，条理清晰，必要时使用列表；在答案末尾注明参考的文件名。
   文件名只能取自【参考资料】或检索结果中“来源：”后面的文件名；没有参考资料时不要写任何文件名，也不要说“根据某某规范”。
6. 打招呼、致谢等寒暄可以直接简短回复，无需检索。
7. 你只负责解答公司内部相关的问题。写诗、讲笑话、推荐电影、通用编程教学等与公司无关的请求，
   礼貌说明你是企业知识库助手、只能解答公司制度和内部规范相关的问题，不要完成这类请求。"""

# 系统提示词第 4 条要求的兜底回复，回答中出现它说明知识库里没有答案
NOT_FOUND_TEXT = "知识库中暂未找到相关内容"
# 带入上下文的历史消息条数（一问一答算 2 条）
HISTORY_LIMIT = 6
# 问题中的专有名词：英文名称（jQuery、X-Request-Id、inventory-service）和 3 位以上的编号（10005）
KEYWORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.+-]*[A-Za-z0-9]|\d{3,}")


class AgentService:
    """知识库问答 Agent。"""

    @staticmethod
    def _build_llm() -> ChatOllama:
        """
        创建 Ollama 大模型对象。

        qwen3 是带思考能力的模型。reasoning=True 会把思考过程单独放到
        additional_kwargs["reasoning_content"] 中，content 只保留最终答案；
        实测 reasoning=False 时 <think> 内容反而会混进 content 里输出给用户。
        """
        return ChatOllama(
            model=Config.LLM_MODEL,
            base_url=Config.OLLAMA_BASE_URL,
            temperature=0.3,
            reasoning=True,
        )

    @staticmethod
    def _build_search_tool(kb_id: int | None, sources: list):
        """
        创建知识库检索工具。

        用闭包把 kb_id（检索范围）和 sources（收集引用来源的列表）传进工具函数，
        这样每次请求都有独立的工具实例，互不干扰。

        :param kb_id: 限定的知识库ID，None 表示全部知识库
        :param sources: 用于收集检索结果的列表，问答结束后保存到数据库
        :return: LangChain 工具对象
        """

        @tool
        def search_knowledge_base(query: str) -> str:
            """在企业内部知识库中检索与问题相关的内容。query 为检索关键词或完整问题。"""
            return AgentService._retrieve(query, kb_id, sources) or "未检索到相关内容。"

        return search_knowledge_base

    @staticmethod
    def _keyword_hits(query: str, kb_id: int | None) -> list:
        """
        从问题中提取专有名词（英文名、编号），返回原文包含它们的片段。

        只保留“专一”的关键词：命中片段数超过 KEYWORD_MAX_HITS 的词（如 Python、API）
        说明在知识库里很常见，不能代表用户想找的那一段，直接忽略。

        :param query: 用户问题
        :param kb_id: 限定的知识库ID
        :return: 命中的片段，按原文去重
        """
        hits = {}
        for term in dict.fromkeys(KEYWORD_RE.findall(query)):
            docs = VectorStore.keyword_search(term, limit=Config.KEYWORD_MAX_HITS + 1, kb_id=kb_id)
            if len(docs) <= Config.KEYWORD_MAX_HITS:
                hits.update({d.page_content: d for d in docs})
        return list(hits.values())

    @staticmethod
    def _retrieve(query: str, kb_id: int | None, sources: list) -> str:
        """
        检索知识库，过滤掉低于阈值的片段，并把命中的片段记录到 sources。
        预检索和检索工具共用这个函数。

        :param query: 检索文本
        :param kb_id: 限定的知识库ID，None 表示全部知识库
        :param sources: 收集引用来源的列表，同一片段只记录一次
        :return: 拼接好的参考资料文本，没有命中时返回空字符串
        """
        if RerankService.enabled():
            # 向量检索多召回一些候选，再补上包含问题中专有名词的片段，由 rerank 重新打分后取前 TOP_K 条
            candidates = [d for d, _ in VectorStore.search(query, k=Config.RERANK_CANDIDATES, kb_id=kb_id)]
            pinned = AgentService._keyword_hits(query, kb_id)
            # 按原文去重，同一片段可能同时被向量检索和关键词检索命中
            pool = list({d.page_content: d for d in candidates + pinned}.values())
            ranked = RerankService.rerank(query, pool)
            pinned_texts = {d.page_content for d in pinned}
            # rerank 对“还能用吗 / 禁止新增”这类需要推理的说法打分偏低，
            # 原文包含问题里专有名词的片段，即使分数低于阈值也保留
            hits = [(d, s) for d, s in ranked
                    if s >= Config.RERANK_THRESHOLD or d.page_content in pinned_texts][:Config.TOP_K]
        else:
            results = VectorStore.search(query, k=Config.TOP_K, kb_id=kb_id)
            hits = [(d, s) for d, s in results if s >= Config.SCORE_THRESHOLD]
        parts = []
        for i, (doc, score) in enumerate(hits, start=1):
            file_name = doc.metadata.get("file_name", "未知文件")
            parts.append(f"[{i}] 来源：{file_name}\n{doc.page_content}")
            if not any(s["content"] == doc.page_content for s in sources):
                sources.append({
                    "file_name": file_name,
                    "content": doc.page_content,
                    "score": round(float(score), 3),
                })
        return "\n\n".join(parts)

    @staticmethod
    def _load_history(session_id: int) -> list:
        """
        读取会话最近的历史消息，转换为 LangChain 消息对象，实现多轮对话。

        :param session_id: 会话ID
        :return: HumanMessage / AIMessage 列表（按时间正序）
        """
        rows = (ChatMessage.query.filter_by(session_id=session_id)
                .order_by(ChatMessage.id.desc()).limit(HISTORY_LIMIT).all())
        history = []
        for row in reversed(rows):
            cls = HumanMessage if row.role == "user" else AIMessage
            history.append(cls(content=row.content))
        return history

    @staticmethod
    def _sse(event: dict) -> str:
        """
        把字典格式化为一条 SSE（Server-Sent Events）消息。

        :param event: 事件数据
        :return: "data: {...}\\n\\n" 格式字符串
        """
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    @staticmethod
    def stream_answer(session_id: int, question: str, kb_id: int | None = None):
        """
        流式问答生成器，被接口层包装为 SSE 响应。

        依次产出的事件：
            {"type": "token",   "content": "..."}   答案片段（多次）
            {"type": "sources", "sources": [...]}   引用来源
            {"type": "done",    "message_id": 1}    结束
            {"type": "error",   "msg": "..."}       出错

        :param session_id: 会话ID
        :param question: 用户问题
        :param kb_id: 限定知识库ID，可选
        """
        # 生成器在接口函数返回后才执行，此时接口里查出的对象已脱离数据库会话，
        # 修改它不会被保存，所以这里按 ID 重新查询
        session = db.session.get(ChatSession, session_id)
        # 先读历史再保存本次提问，避免本次问题在上下文里重复出现
        history = AgentService._load_history(session_id)
        db.session.add(ChatMessage(session_id=session_id, role="user", content=question))
        # 新会话用问题前 20 个字作为标题
        if session.title == "新对话":
            session.title = question[:20]
        db.session.commit()

        sources: list = []
        answer = ""
        try:
            agent = create_agent(
                model=AgentService._build_llm(),
                tools=[AgentService._build_search_tool(kb_id, sources)],
                system_prompt=SYSTEM_PROMPT,
            )
            # 先检索一次，有命中时把参考资料拼进本轮消息。
            # 数据库保存的仍是原问题，历史从数据库读取，所以参考资料不会带进后续轮次
            context = AgentService._retrieve(question, kb_id, sources)
            # 没检索到资料时也要明确告诉模型，只给原问题的话，模型偶尔会凭自身知识编造答案和出处
            # （实测“年假有几天”编出了“10 天”和不存在的《员工手册2023版》）
            content = (f"【参考资料】（可能与问题无关，无关时请忽略）\n{context}\n\n【问题】{question}" if context else
                       f"【参考资料】知识库中没有检索到相关内容。如果这是与公司相关的问题，"
                       f"请调用检索工具换关键词再试一次，仍找不到就回答“{NOT_FOUND_TEXT}”，不要凭自身知识作答。\n\n"
                       f"【问题】{question}")
            inputs = {"messages": history + [HumanMessage(content=content)]}

            # stream_mode="messages" 会逐 token 返回大模型输出
            for chunk, metadata in agent.stream(inputs, stream_mode="messages"):
                # 只转发大模型节点生成的文本，跳过工具节点输出和工具调用参数
                if (isinstance(chunk, AIMessageChunk)
                        and metadata.get("langgraph_node") == "model"
                        and chunk.content):
                    text = chunk.content if isinstance(chunk.content, str) else str(chunk.content)
                    answer += text
                    yield AgentService._sse({"type": "token", "content": text})
        except Exception as e:  # noqa: BLE001 把错误推给前端展示
            answer = answer or f"抱歉，问答服务出错：{e}"
            yield AgentService._sse({"type": "error", "msg": str(e)})

        # 模型判断资料无关、回答“未找到”时，检索到的片段并没有被采用，不再作为来源展示，
        # 否则前端会出现“答案说没找到，下面却挂着来源”的矛盾
        if NOT_FOUND_TEXT in answer:
            sources.clear()
        yield AgentService._sse({"type": "sources", "sources": sources})

        # 保存回答
        reply = ChatMessage(session_id=session_id, role="assistant",
                            content=answer or "（无回答）", sources=sources)
        db.session.add(reply)
        # 刷新会话活跃时间，会话列表按它倒序排列
        session.updated_at = datetime.now()
        db.session.commit()
        yield AgentService._sse({"type": "done", "message_id": reply.id})
