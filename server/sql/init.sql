-- =============================================================
-- 企业内部知识库问答系统 数据库初始化脚本
-- 数据库：db_enterprise_qa    MySQL 版本：26.7
-- 执行方式：mysql -uroot -p < init.sql
-- 说明：所有测试账号密码均为 123456，存储的是 MD5 值
--       e10adc3949ba59abbe56e057f20f883e
-- =============================================================

CREATE DATABASE IF NOT EXISTS db_enterprise_qa
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE db_enterprise_qa;

-- 按依赖关系倒序删除，方便重复执行
DROP TABLE IF EXISTS t_chat_message;
DROP TABLE IF EXISTS t_chat_session;
DROP TABLE IF EXISTS t_document;
DROP TABLE IF EXISTS t_knowledge_base;
DROP TABLE IF EXISTS t_user;

-- -------------------------------------------------------------
-- 用户表：admin 管理员 / user 普通用户
-- -------------------------------------------------------------
CREATE TABLE t_user (
    id          INT          NOT NULL AUTO_INCREMENT COMMENT '主键',
    username    VARCHAR(50)  NOT NULL COMMENT '登录账号',
    password    CHAR(32)     NOT NULL COMMENT '密码（MD5 加密，32 位小写）',
    nickname    VARCHAR(50)  NOT NULL DEFAULT '' COMMENT '昵称',
    role        VARCHAR(20)  NOT NULL DEFAULT 'user' COMMENT '角色：admin 管理员，user 普通用户',
    status      TINYINT      NOT NULL DEFAULT 1 COMMENT '状态：1 启用，0 禁用',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_username (username)
) ENGINE = InnoDB COMMENT = '用户表';

-- -------------------------------------------------------------
-- 知识库表：对文档进行分类，例如人事制度、IT 运维
-- -------------------------------------------------------------
CREATE TABLE t_knowledge_base (
    id          INT          NOT NULL AUTO_INCREMENT COMMENT '主键',
    name        VARCHAR(100) NOT NULL COMMENT '知识库名称',
    description VARCHAR(500) NOT NULL DEFAULT '' COMMENT '描述',
    created_by  INT          NULL COMMENT '创建人ID',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_name (name)
) ENGINE = InnoDB COMMENT = '知识库表';

-- -------------------------------------------------------------
-- 文档表：记录上传的文件以及向量化状态
-- -------------------------------------------------------------
CREATE TABLE t_document (
    id          INT          NOT NULL AUTO_INCREMENT COMMENT '主键',
    kb_id       INT          NOT NULL COMMENT '所属知识库ID',
    file_name   VARCHAR(255) NOT NULL COMMENT '原始文件名',
    file_path   VARCHAR(500) NOT NULL COMMENT '服务器存储路径（相对 server 目录）',
    file_type   VARCHAR(20)  NOT NULL COMMENT '文件类型：txt/md/pdf/docx',
    file_size   INT          NOT NULL DEFAULT 0 COMMENT '文件大小（字节）',
    chunk_count INT          NOT NULL DEFAULT 0 COMMENT '切分后的片段数量',
    status      TINYINT      NOT NULL DEFAULT 0 COMMENT '状态：0 排队中，1 已向量化，2 失败，3 处理中',
    progress    VARCHAR(100) NOT NULL DEFAULT '' COMMENT '处理进度，如“识别图片 3/5”',
    error_msg   VARCHAR(500) NOT NULL DEFAULT '' COMMENT '失败原因',
    uploaded_by INT          NULL COMMENT '上传人ID',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
    PRIMARY KEY (id),
    KEY idx_kb_id (kb_id),
    CONSTRAINT fk_doc_kb FOREIGN KEY (kb_id) REFERENCES t_knowledge_base (id) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '文档表';

-- -------------------------------------------------------------
-- 会话表：用户的一次对话
-- -------------------------------------------------------------
CREATE TABLE t_chat_session (
    id          INT          NOT NULL AUTO_INCREMENT COMMENT '主键',
    user_id     INT          NOT NULL COMMENT '所属用户ID',
    title       VARCHAR(100) NOT NULL DEFAULT '新对话' COMMENT '会话标题',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后活跃时间',
    PRIMARY KEY (id),
    KEY idx_user_id (user_id),
    CONSTRAINT fk_session_user FOREIGN KEY (user_id) REFERENCES t_user (id) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '会话表';

-- -------------------------------------------------------------
-- 消息表：会话中的每一条问答
-- -------------------------------------------------------------
CREATE TABLE t_chat_message (
    id          INT          NOT NULL AUTO_INCREMENT COMMENT '主键',
    session_id  INT          NOT NULL COMMENT '所属会话ID',
    role        VARCHAR(20)  NOT NULL COMMENT '角色：user 用户提问，assistant 助手回答',
    content     TEXT         NOT NULL COMMENT '消息内容',
    sources     JSON         NULL COMMENT '回答引用的知识片段（JSON 数组）',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    KEY idx_session_id (session_id),
    KEY idx_created_at (created_at),
    CONSTRAINT fk_msg_session FOREIGN KEY (session_id) REFERENCES t_chat_session (id) ON DELETE CASCADE
) ENGINE = InnoDB COMMENT = '消息表';

-- =============================================================
-- 测试数据
-- 时间使用 NOW() 往前推，保证管理后台"近 7 天"图表始终有数据
-- =============================================================

-- 用户：密码均为 123456 的 MD5
INSERT INTO t_user (id, username, password, nickname, role, status, created_at) VALUES
(1, 'admin',    'e10adc3949ba59abbe56e057f20f883e', '系统管理员', 'admin', 1, DATE_SUB(NOW(), INTERVAL 30 DAY)),
(2, 'zhangsan', 'e10adc3949ba59abbe56e057f20f883e', '张三',       'user',  1, DATE_SUB(NOW(), INTERVAL 20 DAY)),
(3, 'lisi',     'e10adc3949ba59abbe56e057f20f883e', '李四',       'user',  1, DATE_SUB(NOW(), INTERVAL 15 DAY)),
(4, 'wangwu',   'e10adc3949ba59abbe56e057f20f883e', '王五',       'user',  0, DATE_SUB(NOW(), INTERVAL 5 DAY));

-- 知识库
INSERT INTO t_knowledge_base (id, name, description, created_by, created_at) VALUES
(1, '人事制度', '员工手册、考勤休假等人事相关制度', 1, DATE_SUB(NOW(), INTERVAL 30 DAY)),
(2, 'IT运维',   'VPN、办公网络、设备使用等 IT 支持文档', 1, DATE_SUB(NOW(), INTERVAL 30 DAY)),
(3, '财务报销', '差旅、费用报销流程与标准', 1, DATE_SUB(NOW(), INTERVAL 30 DAY));

-- 文档：status=0 待处理，执行 scripts/init_vector.py 后会被向量化并改为 1
INSERT INTO t_document (id, kb_id, file_name, file_path, file_type, file_size, chunk_count, status, uploaded_by, created_at) VALUES
(1, 1, '员工手册.md',       'data/samples/员工手册.md',       'md', 0, 0, 0, 1, DATE_SUB(NOW(), INTERVAL 10 DAY)),
(2, 1, '考勤与休假制度.md', 'data/samples/考勤与休假制度.md', 'md', 0, 0, 0, 1, DATE_SUB(NOW(), INTERVAL 9 DAY)),
(3, 2, 'VPN使用指南.md',    'data/samples/VPN使用指南.md',    'md', 0, 0, 0, 1, DATE_SUB(NOW(), INTERVAL 8 DAY)),
(4, 3, '费用报销流程.md',   'data/samples/费用报销流程.md',   'md', 0, 0, 0, 1, DATE_SUB(NOW(), INTERVAL 7 DAY));

-- 会话
INSERT INTO t_chat_session (id, user_id, title, created_at, updated_at) VALUES
(1, 2, '年假怎么计算',     DATE_SUB(NOW(), INTERVAL 6 DAY), DATE_SUB(NOW(), INTERVAL 6 DAY)),
(2, 2, 'VPN 连接问题',     DATE_SUB(NOW(), INTERVAL 4 DAY), DATE_SUB(NOW(), INTERVAL 4 DAY)),
(3, 3, '出差报销标准',     DATE_SUB(NOW(), INTERVAL 3 DAY), DATE_SUB(NOW(), INTERVAL 3 DAY)),
(4, 3, '试用期多久',       DATE_SUB(NOW(), INTERVAL 1 DAY), DATE_SUB(NOW(), INTERVAL 1 DAY)),
(5, 1, '测试知识库问答',   NOW(), NOW());

-- 消息（user 提问 / assistant 回答成对出现）
INSERT INTO t_chat_message (session_id, role, content, sources, created_at) VALUES
(1, 'user',      '入职满一年有几天年假？', NULL, DATE_SUB(NOW(), INTERVAL 6 DAY)),
(1, 'assistant', '根据《考勤与休假制度》，累计工作满 1 年不满 10 年的员工，每年享有 5 天带薪年假。', '[{"file_name": "考勤与休假制度.md", "content": "累计工作满1年不满10年的，年休假5天"}]', DATE_SUB(NOW(), INTERVAL 6 DAY)),
(1, 'user',      '年假可以跨年使用吗？', NULL, DATE_SUB(NOW(), INTERVAL 5 DAY)),
(1, 'assistant', '当年年假原则上当年休完，确有需要可顺延至次年 3 月 31 日前使用。', '[{"file_name": "考勤与休假制度.md", "content": "未休年假可顺延至次年3月31日"}]', DATE_SUB(NOW(), INTERVAL 5 DAY)),
(2, 'user',      'VPN 连不上怎么办？', NULL, DATE_SUB(NOW(), INTERVAL 4 DAY)),
(2, 'assistant', '请先确认客户端版本为最新，账号为域账号，若仍失败请联系 IT 服务台分机 8000。', '[{"file_name": "VPN使用指南.md", "content": "常见问题：连接失败请检查客户端版本"}]', DATE_SUB(NOW(), INTERVAL 4 DAY)),
(2, 'user',      'VPN 服务器地址是多少？', NULL, DATE_SUB(NOW(), INTERVAL 2 DAY)),
(2, 'assistant', 'VPN 服务器地址为 vpn.example.com，端口 443。', '[{"file_name": "VPN使用指南.md", "content": "服务器地址：vpn.example.com"}]', DATE_SUB(NOW(), INTERVAL 2 DAY)),
(3, 'user',      '出差住宿标准是多少？', NULL, DATE_SUB(NOW(), INTERVAL 3 DAY)),
(3, 'assistant', '一线城市普通员工住宿标准为每晚 500 元，其他城市每晚 350 元。', '[{"file_name": "费用报销流程.md", "content": "住宿标准：一线城市500元/晚"}]', DATE_SUB(NOW(), INTERVAL 3 DAY)),
(3, 'user',      '报销需要多久到账？', NULL, DATE_SUB(NOW(), INTERVAL 2 DAY)),
(3, 'assistant', '审批通过后，财务会在 5 个工作日内打款到工资卡。', '[{"file_name": "费用报销流程.md", "content": "审批通过后5个工作日内打款"}]', DATE_SUB(NOW(), INTERVAL 2 DAY)),
(4, 'user',      '试用期一般多久？', NULL, DATE_SUB(NOW(), INTERVAL 1 DAY)),
(4, 'assistant', '试用期一般为 3 个月，表现优秀者可申请提前转正。', '[{"file_name": "员工手册.md", "content": "试用期为3个月"}]', DATE_SUB(NOW(), INTERVAL 1 DAY)),
(5, 'user',      '公司上班时间是几点？', NULL, NOW()),
(5, 'assistant', '公司实行弹性工作制，核心工作时间为 10:00-16:00，每日工作满 8 小时。', '[{"file_name": "考勤与休假制度.md", "content": "核心工作时间10:00-16:00"}]', NOW());
