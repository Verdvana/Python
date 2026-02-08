# Longport AutoTrade (DXYZ 策略专版)

这是一个基于 Python 的自动化股票交易脚本，专为 **DXYZ (Destiny Tech100 Inc.)** 等高波动性标的设计。

该脚本采用 **双 API 架构**：利用 **Finnhub API** 进行低成本的实时行情监控，并通过 **Longport Open API (长桥证券)** 执行交易指令。

---

## 📋 目录

1. [核心功能](#-核心功能)
2. [DXYZ 策略运行逻辑](#-dxyz-策略运行逻辑)
3. [环境依赖与安装](#-环境依赖与安装)
4. [配置与使用方法](#-配置与使用方法)
5. [优缺点分析](#-优缺点分析)
6. [版本更新](#-版本更新)
7. [免责声明](#-免责声明)

---

## ✨ 核心功能

* **双 API 驱动**：
    * **行情 (Data)**: 使用 Finnhub 获取实时报价，独立于交易接口，避免单一接口频率限制。
    * **交易 (Execution)**: 使用 Longport SDK 进行毫秒级下单、撤单及资产查询。
* **多股并行监控**：
    * 支持同时配置多个目标股票（如 DXYZ, NVDA）。
    * 利用 `threading` 多线程技术，每只股票独立监控，互不阻塞。
* **状态持久化 (断点续传)**：
    * 脚本实时将持仓状态（成本价、最高价、持仓量）写入 `trade_state.json`。
    * **异常恢复**：若程序崩溃或手动停止，重启时可选择“恢复状态”，继续执行原有的止损/止盈逻辑，防止策略失效。
* **安全敏感信息管理**：
    * 所有 API Key 和 Token 均通过系统 **环境变量** 读取，杜绝代码硬编码导致的信息泄露。
* **无缝实盘切换**：
    * 只需更改环境变量中的 Token，即可在“长桥模拟盘”与“实盘”间无缝切换，无需修改代码逻辑。

---

## 🧠 策略运行逻辑
###  DXYZ 

本脚本的核心目标是：**在严格控制回撤（不亏大钱）的基础上，通过移动止盈追求利润最大化。**

### 1. 入场机制 (Buy Signal)
* **前提**：当前该股票无持仓。
* **触发条件**：
    * 脚本通过 Finnhub 轮询实时价格。
    * 计算 **日内涨幅** `(当前价 - 开盘价) / 开盘价`。
    * 若涨幅超过 `BUY_MOMENTUM_THRESHOLD` (默认 **1%**)，视为动量确立，执行市价买入。

### 2. 离场机制 (Exit Signal) - 双重风控
一旦持有仓位，脚本将启动以下两条防线：

#### A. 硬止损 (Hard Stop Loss) —— 保命线
* **触发条件**：当前价格跌破入场成本价的 `STOP_LOSS_PCT` (默认 **3%**)。
* **执行动作**：**无条件市价卖出**。
* **目的**：防止深度套牢，将单次交易最大亏损锁定在 3% 以内。

#### B. 移动止盈 (Trailing Stop) —— 锁利线
* **逻辑**：脚本会实时记录持仓期间出现的 **最高价格 (Highest Price)**。
* **触发条件**：当前价格从 **最高价** 回撤超过 `TRAILING_STOP_PCT` (默认 **5%**)，且当前处于盈利状态。
* **执行动作**：**市价卖出**。
* **目的**：在趋势反转时离场，保住已经获得的利润（例如从赚20%回撤到赚15%时离场），而不是等到跌回成本价。

---

## 🛠 环境依赖与安装

### 1. 系统要求
* Python 3.8 或更高版本
* 支持 Windows / macOS / Linux

### 2. 安装 Python 库
在终端中运行以下命令安装所需依赖：

```bash
pip install longport finnhub-python
```

---

## ⚙️ 配置与使用方法

### 第一步：获取 API 凭证

1.  **Longport (长桥证券)**:
    * 登录 [长桥开发者中心](https://open.longportapp.com/)。
    * 申请 Open API 权限，获取 `App Key`, `App Secret`。
    * 生成 `Access Token` (注意：**Paper** 为模拟盘 Token，**Live** 为实盘 Token)。
2.  **Finnhub**:
    * 注册 [Finnhub.io](https://finnhub.io/)。
    * 在 Dashboard 获取免费的 `API Key`。

### 第二步：设置环境变量 (关键)

**为了安全，请勿将 Key 直接写入代码！** 请在终端设置环境变量。

**macOS / Linux:**
```bash
export LONGPORT_APP_KEY="你的长桥AppKey"
export LONGPORT_APP_SECRET="你的长桥AppSecret"
export LONGPORT_ACCESS_TOKEN="你的长桥AccessToken"
export FINNHUB_API_KEY="你的FinnhubKey"
```

**Windows (PowerShell):**
```powershell
$env:LONGPORT_APP_KEY="你的长桥AppKey"
$env:LONGPORT_APP_SECRET="你的长桥AppSecret"
$env:LONGPORT_ACCESS_TOKEN="你的长桥AccessToken"
$env:FINNHUB_API_KEY="你的FinnhubKey"
```

### 第三步：调整策略参数 (可选)

打开 `longport_autotrade.py`，在文件顶部的配置区域进行修改：

```python
TARGET_STOCKS = {
    "DXYZ": {
        "budget": 2000,          # 投资金额 (USD)
        "strategy_type": "dxyz_dynamic"
    }
}
POLLING_INTERVAL = 5            # 监控频率 (秒)
STOP_LOSS_PCT = 0.03            # 3% 硬止损
TRAILING_STOP_PCT = 0.05        # 5% 回撤止盈
```

### 第四步：运行脚本

```bash
python longport_autotrade.py
```

* **启动交互**：脚本启动时会检测是否存在历史状态文件。
    * 输入 `y`: **继续运行**（恢复上次的持仓数据，适用于盘中重启）。
    * 输入 `n`: **重新开始**（清空状态，适用于新的一天）。
* **手动退出**：在终端按 `Ctrl + C`，脚本会保存当前状态并安全退出。

---

## ⚖️ 优缺点分析

| 维度 | 优点 (Pros) | 缺点 (Cons) |
| :--- | :--- | :--- |
| **执行速度** | 毫秒级下单，严格执行纪律，克服人性贪婪与恐惧。 | 极端行情（如熔断、跳空）下可能存在滑点 (Slippage)。 |
| **成本** | 利用 Finnhub 免费版数据，降低订阅成本。 | Finnhub 免费版有频率限制 (约 60次/分钟)，可能存在秒级延迟。 |
| **风控** | 结合硬止损与移动止盈，最大程度保护本金。 | 在震荡市（横盘整理）中可能会频繁止损，造成连续小额磨损。 |
| **稳定性** | 具备状态保存功能，不怕断网或程序崩溃。 | 依赖本地网络环境，如果本地断网，监控将失效。 |

---

## 📅 版本更新

* **v0.1.0**: 初始版本发布。
    * 集成 Longport Trade API 与 Finnhub Quote API。
    * 利用 `yfinance` 获取 5 分钟线计算 MA、RSI 等技术指标，同时通过 `Finnhub` 获取秒级实时现价，弥补指标延迟。
    * 内置经典的“均线金叉/死叉 + RSI 过滤”策略。
    * 
* **v0.1.1**: 初始版本发布。
    * 添加 JSON 状态管理与多线程支持。
    * 增加了 `current_price > buy_price` 的判定，确保非止损情况下不亏损平仓。
* **v0.1.2**: 初始版本发布。
    * 
    * 实现 DXYZ 专用移动止损策略。

---

## ⚠️ 免责声明 (Disclaimer)

1.  **风险提示**：本软件仅供 **技术交流与学习** 使用。股票交易（尤其是 DXYZ 及其衍生品）具有极高的资金风险。自动化交易可能因网络延迟、API 故障、交易所数据错误或代码逻辑漏洞导致资金损失。
2.  **实盘慎用**：作者不对使用本脚本产生的任何直接或间接盈亏负责。**强烈建议**先在长桥证券的 **模拟账户 (Paper Trading)** 中进行充分测试，确认策略稳定后再切换至实盘。
3.  **API 规范**：请严格遵守 Finnhub 和 Longport 的 API 使用协议，避免因高频调用导致 IP 被封禁。