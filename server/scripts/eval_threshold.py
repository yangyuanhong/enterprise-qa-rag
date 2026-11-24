"""
相似度阈值测定脚本：分别用“知识库里有答案”和“与知识库无关”的两组问题检索，
统计每个问题的最高相似度，帮助确定 Config.SCORE_THRESHOLD。

阈值应落在两组分数之间：高于无关问题的最高分（否则闲聊会带出无关来源），
低于相关问题的最低分（否则正常问题检索不到内容）。两组分数有重叠时，说明单靠阈值无法完全区分，
只能在“漏掉相关内容”和“混入无关内容”之间取舍。

用法（在 server 目录下执行，需要 Ollama 和 Chroma 中已有向量数据）：
    uv run python scripts/eval_threshold.py
    uv run python scripts/eval_threshold.py --kb-id 4
    uv run python scripts/eval_threshold.py --kb-id 4 --rerank   # 测 rerank 分数，对应 RERANK_THRESHOLD

问题按需修改为自己知识库的真实问题，每组建议准备 20～30 个。
"""
import argparse
import os
import sys

SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SERVER_DIR)

from config import Config  # noqa: E402
from services.rerank_service import RerankService  # noqa: E402
from services.vector_store import VectorStore  # noqa: E402

# 知识库里有答案的问题
RELEVANT = [
    "熔断阈值推荐设置多少？",
    "核心交易接口的响应时间上限是多少？",
    "网关的限流是多少 QPS？",
    "inventory-service 归哪个团队负责？",
    "支付接口失败了能自动重试吗？",
    "周五下午能发布上线吗？",
    "Kafka 消费者要怎么配置？",
    "Docker 镜像可以用 latest 标签吗？",
    "服务名有什么命名规则？",
    "什么是优雅停机？",
    "单元测试覆盖率要求多少？",
    "错误码 10005 是什么意思？",
    "账号被锁定了怎么办？",
    "日志里哪些信息要脱敏？",
    "向量数据库推荐用什么？",
    "金额字段应该用什么类型？",
    "代码里能用 print 打日志吗？",
    "常量怎么命名？",
    "Python 单元测试用什么框架？",
]

# 与知识库无关、但措辞像技术问题的问题，最容易误召回（前端框架表、Python 规范等）
NOT_INDEXED = [
    "前端用什么 CSS 框架？",
    "年假有几天？",
]

# 与知识库无关的问题（闲聊、通用知识、其他领域）
IRRELEVANT = [
    "你好",
    "谢谢",
    "今天天气怎么样",
    "帮我写一首关于秋天的诗",
    "Python 的列表推导式怎么写",
    "推荐几部好看的电影",
    "1 加 1 等于几",
    "北京有哪些好玩的地方",
    "怎么做红烧肉",
    "讲个笑话",
]


def top_score(question: str, kb_id: int | None, rerank: bool) -> tuple[float, str]:
    """返回问题检索结果的最高分和对应片段的开头；rerank 为 True 时返回 rerank 后的最高分。"""
    if rerank:
        candidates = VectorStore.search(question, k=Config.RERANK_CANDIDATES, kb_id=kb_id)
        results = RerankService.rerank(question, [d for d, _ in candidates])
    else:
        results = VectorStore.search(question, k=1, kb_id=kb_id)
    if not results:
        return 0.0, ""
    doc, score = results[0]
    return float(score), doc.page_content.split("\n")[-1][:30]


def main() -> None:
    parser = argparse.ArgumentParser(description="测定检索相似度阈值")
    parser.add_argument("--kb-id", type=int, default=None, help="限定知识库ID，默认检索全部")
    parser.add_argument("--rerank", action="store_true", help="测 rerank 分数，而不是向量相似度")
    args = parser.parse_args()
    threshold = Config.RERANK_THRESHOLD if args.rerank else Config.SCORE_THRESHOLD

    groups = {}
    for name, questions in [("相关问题", RELEVANT), ("无关问题", IRRELEVANT + NOT_INDEXED)]:
        print(f"\n===== {name} =====")
        scores = []
        for q in questions:
            score, snippet = top_score(q, args.kb_id, args.rerank)
            scores.append(score)
            mark = "通过" if score >= threshold else "过滤"
            print(f"  {score:.3f} [{mark}] {q}  →  {snippet}")
        groups[name] = scores

    low_relevant, high_irrelevant = min(groups["相关问题"]), max(groups["无关问题"])
    name = "RERANK_THRESHOLD" if args.rerank else "SCORE_THRESHOLD"
    print(f"\n当前阈值 {name}：{threshold}")
    print(f"相关问题最低分：{low_relevant:.3f}，无关问题最高分：{high_irrelevant:.3f}")
    if high_irrelevant < low_relevant:
        print(f"两组分数没有重叠，建议阈值：{(high_irrelevant + low_relevant) / 2:.2f}")
    else:
        print("两组分数有重叠，单靠阈值无法完全区分，请查看上面标注错误的问题再取舍")


if __name__ == "__main__":
    main()
