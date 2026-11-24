import logging
import re

from langchain_core.documents import Document as LCDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)")
TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
TABLE_SEP_RE = re.compile(r"^\s*\|?(\s*:?-{3,}:?\s*\|)+\s*:?-{0,}:?\s*\|?\s*$")
# 加粗标记，PDF 转出的标题和表头常被包在 ** 里；不处理 __，避免误删 __init__ 这类标识符
EMPHASIS_RE = re.compile(r"\*\*")
# 目录里标题和页码之间的引导点，如“一、总则 . . . . . 3”
TOC_LEADER_RE = re.compile(r"(\.\s*){5,}")
TOC_TITLES = {"目录", "contents", "tableofcontents"}
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
# 独占一行的图片，alt 文本是视觉模型生成的描述
IMAGE_LINE_RE = re.compile(r"^\s*!\[([^\]]*)\]\(([^)]+)\)\s*$")
# 图注，如“图 1-1 微服务总体架构”“Figure 2. xxx”
CAPTION_RE = re.compile(r"^\s*(图|Figure|Fig\.)\s*[\d一二三四五六七八九十]", re.IGNORECASE)


def clean_inline(text: str) -> str:
    """去掉加粗标记，把单元格内的 <br> 换行替换成空格。"""
    return EMPHASIS_RE.sub("", text).replace("<br>", " ").strip()


# 代码特征：花括号、引号、赋值或函数调用（如 r = db.get(...)）。
# 不单独用 = 和 [ ] 判断，书名式标题里也会出现，如“1.1 Agent = LLM + 工具”“8.2 xxx [可选阅读]”
CODE_CHARS_RE = re.compile(r"[{}\"]|\w+\s*=\s*\w+\.\w+\(|\w\(.*\)")
# 带章节编号的标题，几乎不会是误识别，直接信任：“1.2”“第 3 章”“一、”“实验 1-2”，
# 以及书籍的固定结构标题（引言、后记、附录等）。后者没有编号，不列出来会被当成误识别，
# 导致“后记”的内容挂到最后一章下面
NUMBERED_HEADING_RE = re.compile(
    r"^(\d+(\.\d+)*\s|第\s*[\d一二三四五六七八九十]+\s*[章节]|[一二三四五六七八九十]+、|实验\s*\d"
    r"|引言|前言|序言|后记|附录|致谢|参考文献)")
MAX_HEADING_CHARS = 60


def is_real_heading(title: str) -> bool:
    """
    判断 # 开头的行是否是真正的标题。

    PDF 里代码块的注释（如“# 第二次迭代 - LLM 看到上述轨迹”）会被解析器原样输出成 # 开头的行，
    被当成一级标题后，后面所有内容的章节路径都会错掉，直到下一个真正的标题为止。
    过长或含有代码字符的行按正文处理。

    :param title: 去掉 # 和加粗标记后的标题文本
    :return: True 表示是真正的标题
    """
    if NUMBERED_HEADING_RE.match(title):
        return True
    return len(title) <= MAX_HEADING_CHARS and not CODE_CHARS_RE.search(title)


def is_toc_title(title: str) -> bool:
    """判断标题是否为“目录”，忽略中间的空格（含全角空格）和大小写。"""
    return re.sub(r"\s+", "", title).lower() in TOC_TITLES


# 纯文本的章节标题：“一、基本要求”“第二章 总则”，单独成行且不以句号结尾
TXT_HEADING_RE = re.compile(r"^\s*([一二三四五六七八九十]+、|第[一二三四五六七八九十\d]+[章节])\s*\S.{0,30}$")
# Setext 风格标题的下划线：标题下一行全是 = 或 -
TXT_UNDERLINE_RE = re.compile(r"^\s*(=+|-+)\s*$")
# 用 Tab 或两个以上空格分隔的列
TXT_COLUMN_SEP_RE = re.compile(r"\t+| {2,}")


def txt_to_markdown(text: str) -> str:
    """
    把纯文本规范文档转成 Markdown，让 split_markdown 能按章节切分、按表格逐行切分。

    识别规则：
        - 标题下一行是 ===（一级）或 ---（二级）时，转成 # / ## 标题
        - “一、xxx”“第二章 xxx”这类单独成行的短标题，转成 ## 标题
        - 连续两行以上、列数相同（至少 2 列）、用 Tab 或多个空格对齐的行，转成 Markdown 表格

    :param text: txt 原文
    :return: Markdown 文本
    """
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i].rstrip()
        nxt = lines[i + 1].rstrip() if i + 1 < len(lines) else ""
        if line.strip() and TXT_UNDERLINE_RE.match(nxt) and len(nxt.strip()) >= 3:
            out.append(("# " if nxt.strip()[0] == "=" else "## ") + line.strip())
            i += 2
            continue
        if TXT_HEADING_RE.match(line) and not line.rstrip().endswith(("。", "；", "，", "：")):
            out.append("## " + line.strip())
            i += 1
            continue

        # 收集列数相同的连续对齐行
        cells = TXT_COLUMN_SEP_RE.split(line.strip())
        j = i
        rows = []
        while j < len(lines):
            row = TXT_COLUMN_SEP_RE.split(lines[j].strip())
            if len(row) < 2 or len(row) != len(cells):
                break
            rows.append(row)
            j += 1
        if len(rows) >= 2:
            # 单元格里的 | 会破坏表格语法，替换成全角
            md_rows = ["| " + " | ".join(c.replace("|", "｜") for c in r) + " |" for r in rows]
            out.extend([md_rows[0], "|" + " --- |" * len(cells), *md_rows[1:], ""])
            i = j
            continue
        out.append(line)
        i += 1
    return "\n".join(out)


def parse_blocks(md_text: str) -> list[tuple[str, list[str], object]]:
    """
    把 Markdown 解析成块列表，目录章节和带引导点的目录表格会被跳过。
    :return: [(块类型 text/table/image, 标题路径, 内容)]，text 的内容是字符串，table 的内容是行列表，
             image 的内容是 {"desc": 描述, "caption": 图注, "path": 图片路径}
    """
    blocks, text_buf, table_buf = [], [], []
    # 标题栈 [(级别, 标题)]，允许跳级，比如 h1 后面直接出现 h3
    stack: list[tuple[int, str]] = []
    # 目录章节的级别，处于目录章节内时丢弃内容，遇到同级或更高级的标题时结束
    toc_level = None

    def path():
        return [title for _, title in stack]

    def flush_text():
        content = "\n".join(text_buf).strip()
        if content and toc_level is None:
            blocks.append(("text", path(), content))
        text_buf.clear()

    def flush_table():
        # 超过一半的行带引导点，判定为没有“目录”标题的目录表格
        is_toc = sum(bool(TOC_LEADER_RE.search(r)) for r in table_buf) > len(table_buf) / 2
        if table_buf and toc_level is None and not is_toc:
            last = blocks[-1] if blocks else None
            # 跨页表格会被拆成两张表头相同的表，中间没有其他内容时合并回一张
            if last and last[0] == "table" and last[1] == path() and last[2][0] == table_buf[0]:
                last[2].extend(line for line in table_buf[1:] if not TABLE_SEP_RE.match(line))
            else:
                blocks.append(("table", path(), list(table_buf)))
        table_buf.clear()

    # pymupdf4llm 会把图片上识别到的文字包在 <!-- Start of picture text --> 注释里，去掉注释保留文字
    lines = HTML_COMMENT_RE.sub("", md_text).splitlines()
    # 带编号的标题达到一定数量，才认为正文是按编号组织的
    numbered = sum(1 for line in lines
                   if (h := HEADING_RE.match(line)) and NUMBERED_HEADING_RE.match(clean_inline(h.group(2)))) >= 3
    # 图注已合并进图片块的行号，正文中不再重复
    used_captions: set[int] = set()
    for i, line in enumerate(lines):
        if TABLE_ROW_RE.match(line):
            flush_text()
            table_buf.append(line)
            continue
        flush_table()
        if i in used_captions:
            continue
        img = IMAGE_LINE_RE.match(line)
        if img:
            flush_text()
            # 图注一般紧跟在图片下方，向后找第一个非空行（被过滤掉的小图会留下多个空行）
            caption = ""
            j = next((k for k in range(i + 1, len(lines)) if lines[k].strip()), None)
            if j is not None and CAPTION_RE.match(lines[j]):
                caption = clean_inline(lines[j])
                used_captions.add(j)
            desc = clean_inline(img.group(1))
            # 没有描述（未启用视觉模型或识别失败）的图片无法检索，直接丢弃
            if desc and toc_level is None:
                blocks.append(("image", path(), {"desc": desc, "caption": caption, "path": img.group(2)}))
            continue
        m = HEADING_RE.match(line)
        title = clean_inline(m.group(2)) if m else ""
        level = len(m.group(1)) if m else 0
        # 正文按编号组织（1.1、1.2.3）时，没有编号、却会顶掉某个编号标题的“标题”多半是误识别，
        # 典型的是代码块里的注释“# 第一次迭代”。没有编号但级别更低的小标题（“深度思考”）仍保留
        breaks_numbered = (numbered and not NUMBERED_HEADING_RE.match(title)
                           and any(lv >= level and NUMBERED_HEADING_RE.match(t) for lv, t in stack))
        if m and is_real_heading(title) and not breaks_numbered:
            flush_text()
            if toc_level is not None and level <= toc_level:
                toc_level = None
            # 弹出同级和更低级的标题，再压入当前标题
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, title))
            if is_toc_title(title):
                toc_level = level
        else:
            text_buf.append(line)
    flush_text()
    flush_table()
    return blocks


def _split_row(line: str) -> list[str]:
    """拆分表格行。首尾各只去掉一个 |，否则首列为空的行（如 ||auth-service|）会整体左移一列。"""
    line = line.strip()
    line = line[1:] if line.startswith("|") else line
    line = line[:-1] if line.endswith("|") else line
    return [clean_inline(c) for c in line.split("|")]


def parse_table(lines: list[str]) -> tuple[list[str], list[list[str]]]:
    """
    把 Markdown 表格行解析成表头和数据行，跳过 | --- | 分隔行。

    纵向合并的单元格只有一行有值，其余行为空。PDF 中这个值在合并区域的垂直中间那一行，
    无法可靠判断该向上还是向下补齐，所以保留为空（table_to_docs 会跳过空值），宁缺勿错。
    """
    rows = [_split_row(line) for line in lines if not TABLE_SEP_RE.match(line)]
    return rows[0], rows[1:]


# 单元格里出现“二、”“3.”这类章节或列表编号，说明 PDF 解析时把表格外的内容并进了表格
SECTION_IN_CELL_RE = re.compile(r"(^|\s)([一二三四五六七八九十]+、|\d+\.\s)")
MAX_CELL_CHARS = 200


def is_broken_table(rows: list[list[str]]) -> bool:
    """
    粗略判断表格是否解析错误：单元格过长，或单元格里混入了章节、列表编号。
    解析错误的表格按行切会产生列名错位的 chunk，应降级为普通文本处理。
    """
    for row in rows:
        for cell in row:
            if len(cell) > MAX_CELL_CHARS or SECTION_IN_CELL_RE.search(cell):
                return True
    return False


def _pack(items: list[tuple[int, str]], max_chars: int):
    """把（行号，行文本）按字数上限打包成批，单行超长时单独成一批。"""
    batch, size = [], 0
    for item in items:
        # 加上当前行会超出上限时，先把已攒的一批输出
        if batch and size + len(item[1]) > max_chars:
            yield batch
            batch, size = [], 0
        batch.append(item)
        size += len(item[1])
    if batch:
        yield batch


def table_to_docs(header: list[str], rows: list[list[str]],
                  context: str, base_metadata: dict,
                  small_table_rows: int = 5, max_chars: int = 500, group_by: str | None = None) -> list[LCDocument]:
    """
    把表格转换成 chunk：小表整表一块；大表按分组列聚合，再按字数上限打包。
    :param group_by: 分组列名，如“模块”；为None或表头中不存在时整表作为一组
    :param context: 表格的上下文，如“费用报销流程 > 差旅标准”
    :param small_table_rows: 不超过该行数的小表整表作为一个 chunk
    """

    def fmt(row):
        return "；".join(f"{h}: {v}" for h, v in zip(header, row) if v.strip())

    if len(rows) <= small_table_rows:
        content = context + "\n" + "\n".join(fmt(r) for r in rows)
        return [LCDocument(page_content=content, metadata=dict(base_metadata))]

    # 按分组列聚合，dict 保持首次出现的顺序
    groups: dict[str | None, list[tuple[int, str]]] = {}
    idx = header.index(group_by) if group_by in header else None
    for i, r in enumerate(rows, start=1):
        key = r[idx] if idx is not None and idx < len(r) else None
        groups.setdefault(key, []).append((i, fmt(r)))

    docs = []
    for key, items in groups.items():
        ctx = f"{context} > {group_by}: {key}" if key is not None else context
        for batch in _pack(items, max_chars):
            docs.append(LCDocument(
                page_content=ctx + "\n" + "\n".join(text for _, text in batch),
                # Chroma 的 metadata 只支持标量，用起止行号代替行号列表
                metadata={**base_metadata, "row_start": batch[0][0], "row_end": batch[-1][0]},
            ))
    return docs


def split_markdown(md_text: str, title: str, base_metadata: dict) -> list[LCDocument]:
    """统一切分入口：段落按长度切，表格按行切，每个 chunk 都带标题路径。"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
        separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
    )
    docs = []
    for kind, path, content in parse_blocks(md_text):
        # 一级标题和文件名相同时去掉，避免“数据库设计规范 > 数据库设计规范”
        if path and path[0] == title:
            path = path[1:]
        context = " > ".join([title, *path])
        meta = {**base_metadata, "section": context, "type": kind}
        if kind == "text":
            for piece in text_splitter.split_text(content):
                docs.append(LCDocument(page_content=f"{context}\n{piece}", metadata=meta))
        elif kind == "image":
            # 一张图一个 chunk，图注放在描述前面，问“图 5-3 是什么”时也能命中
            label = f"【图片】{content['caption']}" if content["caption"] else "【图片】"
            docs.append(LCDocument(
                page_content=f"{context}\n{label}\n{content['desc']}",
                metadata={**meta, "image_path": content["path"]},
            ))
        else:
            header, rows = parse_table(content)
            if is_broken_table(rows):
                # 表格结构不可信，按普通文本切分，避免生成列名错位的 chunk
                logger.warning("表格疑似解析错误，降级为文本切分：%s", context)
                meta["type"] = "text"
                text = "\n".join(" ".join(c for c in row if c) for row in [header, *rows])
                for piece in text_splitter.split_text(text):
                    docs.append(LCDocument(page_content=f"{context}\n{piece}", metadata=dict(meta)))
            else:
                docs.extend(table_to_docs(header, rows, context, meta))
    return docs
