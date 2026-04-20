# AI + 区块链热点监控服务

这是一个可运行的 MVP，用于实现你提到的需求：

- 抓取 **AI 相关区块链热点应用落地信息**（权威媒体 + 大链新闻 + X 热门 + X 大V + GitHub 热门 + GitHub Release + Dune + DefiLlama）
- 支持 **每4小时自动采集**（默认）或自定义 cron/interval
- 支持添加 **项目/代币监控目标**
- 支持添加并绑定 **X 上 KOL（followers > 20w）**，进行热点监控
- 支持 **Telegram 推送 + Telegram 指令控制任务启停**
- 支持 **LLM 语义分类 + 中文 AI 深度观点**（无 Key 自动降级规则分析）

## 功能概览

1. **数据源（默认全部开启监控）**
   - 权威区块链媒体（CoinDesk / Cointelegraph / Decrypt / The Block）
   - 主流大链新闻（BTC / ETH / SOL 专题 RSS）
   - X 热门话题（Recent Search）
   - X 大V / KOL 动态（默认账号 + 自定义账号）
   - X 大V / KOL 热门帖子（按互动热度筛选 Top N）
   - GitHub 热门飙升项目（基于星标与更新活跃度）
   - GitHub 项目版本发布（Release）
   - Dune 链上数据信号
   - DefiLlama 协议信号

2. **热点识别**
   - LLM 语义分类（adoption 判定 + 置信度 + 中文 AI 深度观点）
   - 无 LLM Key 时自动使用规则分析（基于事件内容生成差异化中文观点）
   - 标题保持原始语言，AI观点统一中文输出

3. **监控能力**
   - 可配置项目/代币关键词（watch target）
   - 可配置 KOL（粉丝门槛默认 200,000）
   - target 与 KOL 可绑定，实现重点账号关联监控

4. **调度模式**
   - 默认 interval：每 4 小时执行一次
   - 或 cron（仅在 interval 设为 0 时生效）

5. **控制面**
   - HTTP 接口控制任务：`/tasks/start`、`/tasks/stop`、`/tasks/status`
   - Telegram 指令控制任务：`/task_start`、`/task_stop`、`/status`、`/collect`

## 技术栈

- FastAPI
- SQLite
- APScheduler
- feedparser
- httpx

## 快速开始

### 1) 安装依赖

```bash
pip install -r requirements.txt
```

### 2) 配置环境变量

```bash
cp .env.example .env
```

关键配置：

- `X_BEARER_TOKEN`：X API Bearer Token（不填也可运行，仅跳过 X 数据源）
- `COLLECTION_CRON`：cron 表达式（UTC；当 `COLLECTION_INTERVAL_MINUTES=0` 时生效）
- `COLLECTION_INTERVAL_MINUTES`：默认 `240`（每4小时）
- `KOL_MIN_FOLLOWERS`：KOL 最低粉丝阈值，默认 200000
- `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`：Telegram 消息推送和指令控制
- `TELEGRAM_HOTSPOT_PUSH_LIMIT`：每轮推送热点条目上限（默认 5）
- `LLM_API_KEY` / `LLM_MODEL`：语义分类与中文深度观点模型
- `DUNE_API_KEY` + `DUNE_QUERY_IDS`：Dune 数据源
- `GITHUB_RELEASE_REPOS`：GitHub Release 监控仓库列表
- `X_DEFAULT_KOL_HANDLES`：默认监控的大V账号列表（已内置一批常用 Web3 KOL）
- `X_KOL_HOT_TOP_N`：每轮从 KOL 动态中提取的热门帖子数量（默认 5）

### 3) 启动服务

```bash
PYTHONPATH=src uvicorn hot_monitor.main:app --host 0.0.0.0 --port 8000
```

访问：

- `GET /health`
- `GET /x/health`（查看 X 数据源健康状态）
- `GET /docs`（Swagger）

## API 示例

### 添加监控项目/代币

```bash
curl -X POST http://127.0.0.1:8000/targets \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Bittensor",
    "symbol": "TAO",
    "keywords": ["bittensor", "tao", "subnet", "ai compute"]
  }'
```

### 添加 KOL（要求 followers >= 200000）

```bash
curl -X POST http://127.0.0.1:8000/kols \
  -H "Content-Type: application/json" \
  -d '{
    "handle": "cz_binance",
    "display_name": "CZ",
    "followers": 9500000,
    "platform": "x"
  }'
```

### 将 KOL 绑定到某个 target

```bash
curl -X POST http://127.0.0.1:8000/targets/1/kols \
  -H "Content-Type: application/json" \
  -d '{"kol_id": 1}'
```

### 手动触发一次采集

```bash
curl -X POST http://127.0.0.1:8000/collect
```

### 通过 HTTP 控制任务启停

```bash
curl -X POST http://127.0.0.1:8000/tasks/stop
curl -X POST http://127.0.0.1:8000/tasks/start
curl http://127.0.0.1:8000/tasks/status
```

### 查看热点与监控事件

```bash
curl "http://127.0.0.1:8000/hotspots?limit=20"
curl "http://127.0.0.1:8000/monitor-events?limit=50"
```

### 查看 X 数据源健康状态（推荐排障）

```bash
# 读取最近一次 X 采集状态（不主动请求 X API）
curl "http://127.0.0.1:8000/x/health"

# 主动探测一次 X API 可用性（会立即发起一次 X 查询）
curl "http://127.0.0.1:8000/x/health?probe=true"

# 查看运行配置与关键状态（包含 x_health_status / x_last_error_code）
curl "http://127.0.0.1:8000/config"
```

常见字段说明：
- `x_health_status`: `ok` / `degraded` / `error` / `disabled`
- `x_available`: 最近一次运行中是否有成功的 X 调用
- `x_last_error_code`: 最近一次 X 错误 HTTP 状态码（如 `402`）
- `x_last_error`: 最近一次 X 错误摘要（便于定位权限或额度问题）

### Telegram 指令

给 bot 发送以下指令：

- `/collect`：立即采集
- `/task_start`：恢复定时任务
- `/task_stop`：暂停定时任务
- `/status`：查看任务状态
- `/kol_add <handle>`：添加 X KOL 白名单（动态生效）
- `/kol_del <handle>`：删除 X KOL 白名单（动态生效）
- `/kol_list`：查看当前白名单

### Telegram 推送模板（按来源分组）

推送会按数据源分组（例如权威媒体、BTC/ETH/SOL 链新闻、X 大V、GitHub 热门项目等），每条热点仅包含：

- 标题（保持原始语言）
- AI 深度观点（中文）
- 出处链接（`Link`）

可通过 `GET /telegram/last-digest` 查看最近一次生成的消息体。

### 动态 KOL 白名单接口（不改 .env、不重启）

可通过 API 动态增删 KOL 白名单，采集任务下一轮立即生效：

```bash
curl http://127.0.0.1:8000/kols/whitelist
curl -X POST http://127.0.0.1:8000/kols/whitelist -H "Content-Type: application/json" -d '{"handle":"aeyakovenko"}'
curl -X DELETE http://127.0.0.1:8000/kols/whitelist/aeyakovenko
```

## 如何开始用 Telegram 测试

1. 在 Telegram 里找到 `@BotFather`，执行 `/newbot` 创建机器人，拿到 `TELEGRAM_BOT_TOKEN`
2. 给你的机器人发一条任意消息（例如 `/start`）
3. 在浏览器访问：
   `https://api.telegram.org/bot<你的TOKEN>/getUpdates`
   从返回 JSON 里找到 `message.chat.id`，填到 `TELEGRAM_CHAT_ID`
4. 在 `.env` 中至少配置：

```env
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=123456789
TELEGRAM_NOTIFY_ON_COLLECT=true
TELEGRAM_HOTSPOT_PUSH_LIMIT=5
```

5. 启动服务后测试：
   - 发送 `/collect` 给 bot，应该收到热点简报
   - 发送 `/status` 查看任务状态
   - 发送 `/task_stop` / `/task_start` 测试定时任务暂停与恢复

推送模板当前固定为按来源分组的精简结构：
- 分组标题（来源）
- 原始语言标题
- 中文 AI 深度观点
- 出处链接

可通过 `TELEGRAM_HOTSPOT_PUSH_LIMIT` 配置每次推送最多包含的热点条数。

## 开机自动启动（仅此项）

已提供一键脚本安装 user 级 systemd 服务：

```bash
bash scripts/install_autostart.sh /workspace
```

常用命令：

```bash
systemctl --user status hot-monitor.service
systemctl --user restart hot-monitor.service
journalctl --user -u hot-monitor.service -f
```

## 项目结构

```text
src/hot_monitor/
  analyzer.py            # 热点识别与相关性打分
  config.py              # 环境变量配置
  controller.py          # 任务启停与 Telegram 指令控制
  database.py            # SQLite schema 与 DAO
  integrations/
    llm_classifier.py    # LLM语义分类与中文AI深度观点
    telegram_bot.py      # Telegram 推送与命令轮询
  main.py                # FastAPI 入口
  scheduler.py           # 定时任务
  service.py             # 采集、分析、入库、关联监控主流程
  sources/
    defillama.py         # DefiLlama 数据抓取
    dune.py              # Dune 查询结果抓取
    github_releases.py   # GitHub Release 抓取
    github_trending.py   # GitHub 热门项目抓取
    news_rss.py          # RSS 新闻抓取
    source_grouping.py   # 数据源分组映射
    x_client.py          # X API 客户端
```

## 注意事项

- X 官方 API 规则可能变更，建议在生产中增加：
  - API 错误重试与退避
  - 去重缓存 / 队列
  - 多语言关键词体系
  - 更强的语义分类（可接 LLM）
- 当前是 SQLite 单机版，后续可升级到 Postgres + Redis + worker 架构。
