# 抖音订单同步系统 (Douyin Order Sync) - 开发规范与架构指南

## ⚠️ 给 AI 助手的核心指令 (SYSTEM PROMPT)
**你在修改本项目代码时，必须严格遵守以下架构原则和开发规范。严禁擅自引入复杂的 MVC 架构或修改核心分页逻辑。**

---

## 1. 项目架构 (Flat Structure)
本项目采用 **扁平化模块** 结构，拒绝深层嵌套。所有功能通过以下几个文件拆分：

| 文件名 | 职责描述 |
| :--- | :--- |
| **`main.py`** | **入口调度**。负责启动死循环、捕捉 Docker 退出信号、调用 TaskManager 和 API。不包含具体业务逻辑。 |
| **`douyin_api.py`** | **核心 API 逻辑**。包含 `decrypt` (解密)、`get_token` (鉴权)、`fetch_orders` (分页拉取)。 |
| **`database.py`** | **数据存储**。包含 DB 连接初始化、`Order` 模型定义、`save_orders` (Upsert逻辑)。 |
| **`task_manager.py`**| **监控与通信**。负责向数据库汇报心跳 (Heartbeat)，并读取后台控制指令 (STOP/START)。 |
| **`config.py`** | **配置管理**。从 `.env` 读取环境变量 (APP_ID, SECRET, DB_URL)。 |
| **`.env`** | **敏感信息**。不要提交到 Git。 |

---

## 2. 关键开发规范 (Critical Rules)

### 2.1 API 分页逻辑 (Strict)
抖音接口的分页极其容易出错，**必须**遵循以下逻辑：
1.  **Cursor 类型**：`cursor` 参数必须且只能是 **`int` (整数)**。严禁传入字符串 `"0"` 或 `"第一页"`。
2.  **初始值**：第一页 `cursor = 0`。
3.  **循环策略**：采用 **“按天切分 + 内部循环”** 的双层结构。
    * 外层：按天遍历 (`start_time` 到 `end_time` 步长为 1 天)。
    * 内层：处理当天的 `cursor` 翻页。
4.  **死循环熔断**：必须检测 `next_cursor == current_cursor`，防止 API 返回假成功导致死循环。

### 2.2 数据库存储策略 (PostgreSQL + JSONB)
本项目使用 **PostgreSQL** 作为数据库。
1.  **JSON 处理**：`raw_data` 字段必须使用 PostgreSQL 原生的 **`JSONB`** 类型（不是 `JSON`，也不是 `Text`），以便支持高性能查询和索引。
2.  **Upsert 逻辑**：
    * 使用 SQLAlchemy 的 `dialects.postgresql.insert`。
    * 逻辑为：`INSERT INTO ... ON CONFLICT (order_id) DO UPDATE SET ...`。
3.  **表结构设计**：
    * `order_id`: VARCHAR / TEXT (Primary Key)
    * `sku_name`: VARCHAR / TEXT (快照)
    * `raw_data`: **JSONB** (存储原始 API 响应)

### 2.3 监控与状态 (Decoupling)
严禁在本项目中引入 Web 框架 (Flask/Django)。
* **状态汇报**：Worker 通过 `task_manager.py` 更新数据库表 `task_monitor`。
* **指令接收**：Worker 轮询数据库表中的 `target_command` 字段（如 'STOP'），实现后台控制。

### 2.4 Docker 适配
* **运行模式**：程序设计为 **驻守型 (Service Mode)**，通过 `while True` 循环运行。
* **路径处理**：严禁使用绝对路径 (如 `D:/...`)，必须使用 `os.path.join(BASE_DIR, ...)` 相对路径。
* **退出处理**：`main.py` 必须注册 `signal.SIGTERM` 和 `signal.SIGINT`，以支持 Docker 的优雅退出。

---

## 3. 依赖管理
* 新增第三方库后，必须更新 `requirements.txt`。
* 数据库驱动：使用 `psycopg2-binary`。
* ORM：使用 `SQLAlchemy`。
* 严禁随意更换加密库，`douyin_api.py` 中的 AES-GCM 解密逻辑经过验证，**非必要不修改**。