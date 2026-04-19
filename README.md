# AI + 区块链热点监控服务

这是一个可运行的 MVP，用于实现你提到的需求：

- 抓取 **AI 相关区块链热点应用落地信息**（新闻 + X 平台）
- 支持 **每日定时** 或 **按分钟间隔** 自动采集
- 支持添加 **项目/代币监控目标**
- 支持添加并绑定 **X 上 KOL（followers > 20w）**，进行热点监控

## 功能概览

1. **数据源**
   - 区块链新闻 RSS（默认 CoinDesk / Cointelegraph / Decrypt）
   - X API（Recent Search + 指定 KOL 账号 recent posts）

2. **热点识别**
   - 内置 AI + 区块链关键词打分
   - 输出热点类别、热点分数、摘要

3. **监控能力**
   - 可配置项目/代币关键词（watch target）
   - 可配置 KOL（粉丝门槛默认 200,000）
   - target 与 KOL 可绑定，实现重点账号关联监控

4. **调度模式**
   - Cron（例如每天 08:00 UTC）
   - 或 interval（例如每 30 分钟）

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
- `COLLECTION_CRON`：cron 表达式（UTC）
- `COLLECTION_INTERVAL_MINUTES`：若 > 0，则优先使用 interval 调度
- `KOL_MIN_FOLLOWERS`：KOL 最低粉丝阈值，默认 200000

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

### 查看热点与监控事件

```bash
curl "http://127.0.0.1:8000/hotspots?limit=20"
curl "http://127.0.0.1:8000/monitor-events?limit=50"
```

## 项目结构

```text
src/hot_monitor/
  analyzer.py            # 热点识别与相关性打分
  config.py              # 环境变量配置
  database.py            # SQLite schema 与 DAO
  main.py                # FastAPI 入口
  scheduler.py           # 定时任务
  service.py             # 采集、分析、入库、关联监控主流程
  sources/
    news_rss.py          # RSS 新闻抓取
    x_client.py          # X API 客户端
```

## 注意事项

- X 官方 API 规则可能变更，建议在生产中增加：
  - API 错误重试与退避
  - 去重缓存 / 队列
  - 多语言关键词体系
  - 更强的语义分类（可接 LLM）
- 当前是 SQLite 单机版，后续可升级到 Postgres + Redis + worker 架构。
