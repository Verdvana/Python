#!/usr/bin/python3
import os
import sys
import time
import json
import signal
import threading
import logging
from datetime import datetime
from decimal import Decimal

# 第三方库
import finnhub
# 修复核心：导入 OrderType 枚举 
from longport.openapi import TradeContext, Config, OrderType 

# ==========================================
# 1. 用户配置区域 (可在此修改策略参数)
# ==========================================

# 交易目标配置
TARGET_STOCKS = {
    "DXYZ": {
        "budget": 1000,          # 投资该股票的总金额
        "strategy_type": "dxyz_dynamic" 
    }
}

# 全局策略参数
POLLING_INTERVAL = 5            # 监控频率 (秒)
STOP_LOSS_PCT = 0.03            # 硬止损线 (下跌 3% 强制卖出)
BUY_MOMENTUM_THRESHOLD = 0.015  # 买入动量阈值 (日内涨幅超过 1.5% 入场)

# 状态文件路径
STATE_FILE = "trade_state.json"

# 日志设置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(threadName)s - %(message)s',
    handlers=[logging.StreamHandler(), logging.FileHandler("autotrade.log")]
)
logger = logging.getLogger(__name__)

# ==========================================
# 2. 环境与 API 初始化
# ==========================================

def get_env_variable(var_name):
    value = os.getenv(var_name)
    if not value:
        logger.error(f"Missing environment variable: {var_name}")
        sys.exit(1)
    return value

LP_APP_KEY = get_env_variable("LONGPORT_APP_KEY")
LP_APP_SECRET = get_env_variable("LONGPORT_APP_SECRET")
LP_ACCESS_TOKEN = get_env_variable("LONGPORT_ACCESS_TOKEN")
FINNHUB_API_KEY = get_env_variable("FINNHUB_API_KEY")

finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)

lp_config = Config(
    app_key=LP_APP_KEY,
    app_secret=LP_APP_SECRET,
    access_token=LP_ACCESS_TOKEN
)

# ==========================================
# 3. 状态管理 (断点续传)
# ==========================================

class StateManager:
    def __init__(self):
        self.state = {}
        self.lock = threading.Lock()

    def load_state(self):
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    self.state = json.load(f)
                logger.info("已加载上次的交易状态。")
            except Exception as e:
                logger.error(f"加载状态失败: {e}")
                self.state = {}
        else:
            self.state = {}

    def save_state(self):
        with self.lock:
            with open(STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=4)
        logger.info("交易状态已保存。")

    def reset_state(self):
        self.state = {}
        self.save_state()
        logger.info("交易状态已重置。")

    def update_position(self, symbol, quantity, avg_price, high_price):
        with self.lock:
            if quantity == 0:
                if symbol in self.state:
                    del self.state[symbol]
            else:
                self.state[symbol] = {
                    "quantity": quantity,
                    "entry_price": avg_price,
                    "highest_price": high_price,
                    "last_update": str(datetime.now())
                }
            self.save_state()

    def get_position(self, symbol):
        with self.lock:
            return self.state.get(symbol, None)

state_manager = StateManager()

# ==========================================
# 4. 交易执行逻辑
# ==========================================

class Trader:
    def __init__(self):
        try:
            self.ctx = TradeContext(lp_config)
            logger.info("Longport 交易环境连接成功")
        except Exception as e:
            logger.error(f"Longport 连接失败: {e}")
            sys.exit(1)

    def execute_buy(self, symbol, budget, current_price):
        """执行限价买入"""
        quantity = int(budget / current_price)
        if quantity < 1:
            logger.warning(f"{symbol} 资金不足以购买 1 股 (Price: {current_price}, Budget: {budget})")
            return False

        logger.info(f"正在买入 {symbol} | 数量: {quantity} | 预估价格: {current_price}")
        
        try:
            # 修复：order_type 使用 OrderType.LO 枚举 
            # 增加 round 处理确保 Decimal 转换精准 
            self.ctx.submit_order(
                symbol=symbol,
                order_type=OrderType.LO, 
                side="Buy",
                submitted_quantity=quantity,
                submitted_price=Decimal(str(round(current_price * 1.01, 2))), 
                time_in_force="Day"
            )
            state_manager.update_position(symbol, quantity, current_price, current_price)
            logger.info(f"买入指令已发送: {symbol}")
            return True
        except Exception as e:
            logger.error(f"买入失败 {symbol}: {e}")
            return False

    def execute_sell(self, symbol, quantity, current_price, reason="Unknown"):
        """执行限价卖出"""
        logger.info(f"正在卖出 {symbol} | 原因: {reason} | 价格: {current_price}")
        try:
            # 修复：order_type 使用 OrderType.LO 枚举 
            self.ctx.submit_order(
                symbol=symbol,
                order_type=OrderType.LO,
                side="Sell",
                submitted_quantity=quantity,
                submitted_price=Decimal(str(round(current_price * 0.99, 2))),
                time_in_force="Day"
            )
            state_manager.update_position(symbol, 0, 0, 0)
            logger.info(f"卖出指令已发送: {symbol}")
            return True
        except Exception as e:
            logger.error(f"卖出失败 {symbol}: {e}")
            return False

trader = Trader()

# ==========================================
# 5. 策略引擎 (DXYZ 核心逻辑)
# ==========================================

def dxyz_strategy_logic(symbol, config, running_event):
    logger.info(f"启动策略监控: {symbol}")
    
    while running_event.is_set():
        try:
            quote = finnhub_client.quote(symbol)
            current_price = float(quote['c'])
            open_price = float(quote['o'])
            
            if current_price is None or current_price == 0:
                logger.warning(f"无法获取 {symbol} 价格，跳过本次循环")
                time.sleep(POLLING_INTERVAL)
                continue

            position = state_manager.get_position(symbol)

            # --- 场景 A: 持有仓位 ---
            if position:
                entry_price = position['entry_price']
                highest_price = position['highest_price']
                quantity = position['quantity']

                if current_price > highest_price:
                    highest_price = current_price
                    state_manager.update_position(symbol, quantity, entry_price, highest_price)
                    logger.info(f"{symbol} 创新高: {highest_price}")

                pnl_pct = (current_price - entry_price) / entry_price
                max_pnl_pct = (highest_price - entry_price) / entry_price
                drawdown_pct = (highest_price - current_price) / highest_price

                current_trailing_limit = None 

                if max_pnl_pct > 0.20:
                    current_trailing_limit = 0.10
                elif max_pnl_pct > 0.10:
                    current_trailing_limit = 0.06
                elif max_pnl_pct > 0.03:
                    current_trailing_limit = 0.03

                if pnl_pct < -STOP_LOSS_PCT:
                    trader.execute_sell(symbol, quantity, current_price, reason="触发硬止损")
                elif current_trailing_limit is not None and drawdown_pct > current_trailing_limit:
                    reason_msg = f"移动止盈 (最高浮盈 {max_pnl_pct:.2%}, 回撤 {drawdown_pct:.2%})"
                    trader.execute_sell(symbol, quantity, current_price, reason=reason_msg)
                else:
                    logger.info(f"持仓中 {symbol}: 现价 {current_price} | 浮盈 {pnl_pct:.2%}")

            # --- 场景 B: 空仓 ---
            else:
                day_change_pct = (current_price - open_price) / open_price
                if day_change_pct > BUY_MOMENTUM_THRESHOLD:
                    logger.info(f"{symbol} 触发买入信号: 日涨幅 {day_change_pct:.2%}")
                    trader.execute_buy(symbol, config['budget'], current_price)
                else:
                    logger.info(f"观察中 {symbol}: 现价 {current_price} | 日涨幅 {day_change_pct:.2%} (阈值 {BUY_MOMENTUM_THRESHOLD:.1%})")

        except Exception as e:
            logger.error(f"策略循环错误 ({symbol}): {e}")
        
        time.sleep(POLLING_INTERVAL)

# ==========================================
# 6. 主程序流程
# ==========================================

def main():
    print("========================================")
    print("   Longport AutoTrade v0.1.4 (Fixed Type)")
    print("========================================")

    if os.path.exists(STATE_FILE):
        choice = input("是否继续上次的交易状态? (y/n): ").strip().lower()
        if choice == 'y':
            state_manager.load_state()
        else:
            state_manager.reset_state()
    else:
        state_manager.reset_state()

    running_event = threading.Event()
    running_event.set()

    def signal_handler(sig, frame):
        print("\n正在停止脚本...")
        running_event.clear()
        state_manager.save_state()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    threads = []
    for ticker, config in TARGET_STOCKS.items():
        t = threading.Thread(
            target=dxyz_strategy_logic, 
            args=(ticker, config, running_event),
            name=f"Thread-{ticker}"
        )
        t.start()
        threads.append(t)

    while running_event.is_set():
        time.sleep(1)

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()