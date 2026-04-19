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

### 3) 启动服务

```bash
PYTHONPATH=src uvicorn hot_monitor.main:app --host 0.0.0.0 --port 8000
```

访问：

- `GET /health`
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

### Telegram 指令

给 bot 发送以下指令：

- `/collect`：立即采集
- `/task_start`：恢复定时任务
- `/task_stop`：暂停定时任务
- `/status`：查看任务状态

### Telegram 推送模板（按来源分组）

推送会按数据源分组（例如权威媒体、BTC/ETH/SOL 链新闻、X 大V、GitHub 热门项目等），每条热点仅包含：

- 标题（保持原始语言）
- AI 深度观点（中文）
- 出处链接（`Link`）

可通过 `GET /telegram/last-digest` 查看最近一次生成的消息体。

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
