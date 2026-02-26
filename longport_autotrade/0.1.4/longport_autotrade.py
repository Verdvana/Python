#!/usr/bin/python3
import os
import sys
import time
import json
import signal
import threading
import logging
from datetime import datetime, timedelta, time as dtime
from decimal import Decimal

# 第三方库
import finnhub
import pytz  # [新增] 用于处理美股时区(冬令时/夏令时)
from longport.openapi import TradeContext, Config, OrderType, OrderSide, TimeInForceType

# ==========================================
# 1. 用户配置区域 (可在此修改策略参数)
# ==========================================

# 交易目标配置
# 格式: {"TICKER": {"budget": 投资金额(USD), "strategy_type": "dxyz_momentum"}}
TARGET_STOCKS = {
    "DXYZ": {
        "budget": 1000,          # 投资该股票的总金额
        "strategy_type": "dxyz_dynamic" 
    }
}

# 全局策略参数
POLLING_INTERVAL = 5            # 监控频率 (秒)
STOP_LOSS_PCT = 0.03            # 硬止损线 (下跌 3% 强制卖出)
BUY_MOMENTUM_THRESHOLD = 0.015  # 买入动量阈值 (日内涨幅超过 1.5% 且趋势向上才买)

# [新增] 2.b 滑点控制 & 冷却期配置
SLIPPAGE_PCT = 0.01             # 滑点容忍度 (1%)，防止市价单买在高位
COOLDOWN_MINUTES = 30           # [新增] 1.A 卖出后冷却时间(分钟)，防止止损后立即重复买入

# [新增] 3.a 最小成交量过滤 (防止无量空涨)
MIN_VOLUME_THRESHOLD = 10000    

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

# 读取环境变量
LP_APP_KEY = get_env_variable("LONGPORT_APP_KEY")
LP_APP_SECRET = get_env_variable("LONGPORT_APP_SECRET")
LP_ACCESS_TOKEN = get_env_variable("LONGPORT_ACCESS_TOKEN")
FINNHUB_API_KEY = get_env_variable("FINNHUB_API_KEY")

# 初始化 Finnhub
finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)

# 初始化 Longport Config
lp_config = Config(
    app_key=LP_APP_KEY,
    app_secret=LP_APP_SECRET,
    access_token=LP_ACCESS_TOKEN
)

# ==========================================
# 3. 状态管理 (断点续传 & 冷却期)
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
            if symbol not in self.state:
                self.state[symbol] = {}
            
            if quantity == 0:
                # 清空持仓数据，但保留冷却时间等元数据
                self.state[symbol]["quantity"] = 0
                self.state[symbol]["entry_price"] = 0
                self.state[symbol]["highest_price"] = 0
            else:
                self.state[symbol].update({
                    "quantity": quantity,
                    "entry_price": avg_price,
                    "highest_price": high_price,
                    "last_update": str(datetime.now())
                })
            self.save_state()

    def get_position(self, symbol):
        with self.lock:
            # 只有当 quantity > 0 时才认为有持仓
            data = self.state.get(symbol, {})
            if data.get("quantity", 0) > 0:
                return data
            return None

    # [新增] 1.A 设置冷却期 (解决死循环买入问题)
    def set_cooldown(self, symbol):
        with self.lock:
            if symbol not in self.state:
                self.state[symbol] = {}
            # 设置未来解除锁定的时间戳
            unlock_time = datetime.now() + timedelta(minutes=COOLDOWN_MINUTES)
            self.state[symbol]["cooldown_until"] = unlock_time.timestamp()
            self.save_state()
            logger.info(f"[{symbol}] 进入冷却期，{COOLDOWN_MINUTES}分钟内不执行买入。")

    # [新增] 1.A 检查是否在冷却期
    def is_in_cooldown(self, symbol):
        with self.lock:
            data = self.state.get(symbol, {})
            cooldown_ts = data.get("cooldown_until", 0)
            # 如果当前时间小于解锁时间，说明还在冷却中
            if cooldown_ts and time.time() < cooldown_ts:
                return True
            return False

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
        """执行买入 (优化了价格计算和资金检查)"""
        # [修改] 2.c 资金管理：检查是否足够买1股
        if current_price <= 0:
            return False
            
        quantity = int(budget / current_price)
        if quantity < 1:
            logger.warning(f"{symbol} 资金不足以购买 1 股 (Price: {current_price}, Budget: {budget})，跳过")
            return False

        # [修改] 2.a/b 动态滑点计算 (向上偏移以保证买入)
        limit_price = current_price * (1 + SLIPPAGE_PCT)
        
        logger.info(f"正在买入 {symbol} | 数量: {quantity} | 触发价: {current_price} | 限价: {limit_price:.2f}")
        
        try:
            self.ctx.submit_order(
                symbol=symbol,
                order_type=OrderType.LO, # Limit Order
                side=OrderSide.Buy,
                submitted_quantity=quantity,
                submitted_price=Decimal(f"{limit_price:.2f}"), # 使用计算后的限价
                time_in_force=TimeInForceType.Day
            )
            # 更新状态
            state_manager.update_position(symbol, quantity, current_price, current_price)
            logger.info(f"买入指令已发送: {symbol}")
            return True
        except Exception as e:
            logger.error(f"买入失败 {symbol}: {e}")
            return False

    def execute_sell(self, symbol, quantity, current_price, reason="Unknown"):
        """执行卖出"""
        # [修改] 2.a/b 动态滑点计算 (卖出向下偏移以保证成交)
        limit_price = current_price * (1 - SLIPPAGE_PCT)
        
        logger.info(f"正在卖出 {symbol} | 原因: {reason} | 触发价: {current_price} | 限价: {limit_price:.2f}")
        try:
            self.ctx.submit_order(
                symbol=symbol,
                order_type=OrderType.LO,
                side=OrderSide.Sell,
                submitted_quantity=quantity,
                submitted_price=Decimal(f"{limit_price:.2f}"),
                time_in_force=TimeInForceType.Day
            )
            state_manager.update_position(symbol, 0, 0, 0) # 清空持仓
            
            # [新增] 1.A 卖出成功后，触发冷却期，防止立即买回
            state_manager.set_cooldown(symbol)
            
            logger.info(f"卖出指令已发送: {symbol}")
            return True
        except Exception as e:
            logger.error(f"卖出失败 {symbol}: {e}")
            return False

trader = Trader()

# ==========================================
# 5. 策略引擎 (DXYZ 核心逻辑)
# ==========================================

# [新增] 1.B & 4.c 智能交易时间检查函数
def is_market_open():
    """
    检查当前是否为美股交易时间 (09:30 - 16:00 ET)。
    使用 pytz 自动处理冬令时(EST)和夏令时(EDT)的转换。
    修复：强制使用 UTC 时间作为基准进行转换，避免服务器本地时区设置造成的时间偏移。
    """
    try:
        # 1. 设置美东时区对象
        tz_ny = pytz.timezone('America/New_York')
        
        # 2. [修复] 获取当前的纽约时间 (更稳健的方式)
        # 并不是直接调用 datetime.now(tz_ny)，而是先获取 UTC 时间再转时区
        # 这能防止服务器系统时区(System Local Time)设置不当时导致的计算错误
        now_utc = datetime.now(pytz.utc)
        now_ny = now_utc.astimezone(tz_ny)
        
        # 3. 检查是否是周末 (0=周一 ... 4=周五, 5=周六, 6=周日)
        if now_ny.weekday() >= 5:
            return False

        # 4. 检查具体时间段
        current_time = now_ny.time()
        market_start = dtime(9, 30)
        market_end = dtime(16, 0)
        
        # 调试日志：如果发现关盘，打印一下当前脚本计算出的纽约时间，方便排查
        is_open = market_start <= current_time <= market_end
        if not is_open and now_ny.minute % 30 == 0 and now_ny.second < 5: 
            # 限制日志频率，避免刷屏，仅在整点或半点打印
            logger.info(f"市场检查: 当前纽约时间 {now_ny.strftime('%Y-%m-%d %H:%M:%S')} (非交易时段)")

        return is_open
    except Exception as e:
        logger.error(f"时区时间检查错误: {e}")
        return False # 出错则默认不交易以保安全


def dxyz_strategy_logic(symbol, config, running_event):
    """DXYZ 专用策略: 结合趋势跟踪与动态阶梯移动止损"""
    logger.info(f"启动策略监控: {symbol}")
    
    # [新增] 心跳计数器，用于在交易时段打印存活日志
    heartbeat_counter = 0

    while running_event.is_set():
        # [新增] 1.B 盘中时间检查
        if not is_market_open():
            logger.info("当前非美股交易时间 (09:30-16:00 ET) 或周末，休眠等待...")
            time.sleep(60) # 非交易时间休眠久一点
            continue

        try:
            # [新增] 4.b 异常重试机制 (API 鲁棒性)
            quote = None
            retry_count = 0
            while retry_count < 3:
                try:
                    quote = finnhub_client.quote(symbol)
                    break # 成功获取则跳出循环
                except Exception as api_err:
                    retry_count += 1
                    logger.warning(f"获取行情失败，重试 {retry_count}/3: {api_err}")
                    time.sleep(2)
            
            if not quote:
                logger.error(f"无法获取 {symbol} 价格，跳过本次循环")
                time.sleep(POLLING_INTERVAL)
                continue

            current_price = float(quote['c'])  # 当前价格
            open_price = float(quote['o'])     # 今日开盘价
            # [新增] 3.a 读取成交量
            current_volume = float(quote.get('v', 0)) # v 是当日常量

            if current_price is None or current_price == 0:
                time.sleep(POLLING_INTERVAL)
                continue
            
            # 计算日内涨幅
            day_change_pct = (current_price - open_price) / open_price if open_price else 0

            # 2. 读取当前持仓状态
            position = state_manager.get_position(symbol)

            # =========================================================
            # [修复] 增加心跳日志 (每约 60 秒打印一次)，证明脚本未卡死
            # =========================================================
            heartbeat_counter += 1
            if heartbeat_counter % 12 == 0: # 5秒一次循环，12次约60秒
                pos_str = "持仓中" if position else "空仓监控"
                logger.info(f"[{symbol}] 运行中 | {pos_str} | 现价: {current_price} | 涨幅: {day_change_pct:.2%}")

            # --- 场景 A: 持有仓位 (监控卖出) ---
            if position:
                entry_price = position['entry_price']
                highest_price = position['highest_price']
                quantity = position['quantity']

                # 更新最高价 (用于移动止盈)
                if current_price > highest_price:
                    highest_price = current_price
                    state_manager.update_position(symbol, quantity, entry_price, highest_price)
                    # logger.info(f"{symbol} 创新高: {highest_price}") 

                # 计算当前盈亏比
                pnl_pct = (current_price - entry_price) / entry_price
                # 计算最高浮盈比例
                max_pnl_pct = (highest_price - entry_price) / entry_price
                # 计算从最高点的回撤
                drawdown_pct = (highest_price - current_price) / highest_price

                # [修改] 3.b 动态阶梯止盈逻辑 (参数化)
                current_trailing_limit = None 

                if max_pnl_pct > 0.20:
                    current_trailing_limit = 0.10  # 盈利 > 20% 时，允许 10% 回撤
                elif max_pnl_pct > 0.10:
                    current_trailing_limit = 0.06  # 盈利 > 10% 时，允许 6% 回撤
                elif max_pnl_pct > 0.03:
                    current_trailing_limit = 0.03  # 盈利 > 3% 时，允许 3% 回撤

                # 策略 1: 硬止损 (保本底线)
                if pnl_pct < -STOP_LOSS_PCT:
                    trader.execute_sell(symbol, quantity, current_price, reason=f"触发硬止损 (当前 {pnl_pct:.2%})")
                
                # 策略 2: 动态移动止盈
                elif current_trailing_limit is not None and drawdown_pct > current_trailing_limit:
                    reason_msg = f"触发动态移动止盈 (最高浮盈 {max_pnl_pct:.2%}, 回撤 {drawdown_pct:.2%})"
                    trader.execute_sell(symbol, quantity, current_price, reason=reason_msg)

                else:
                    pass # 持仓正常，继续持有

            # --- 场景 B: 空仓 (监控买入) ---
            else:
                # [新增] 1.A 冷却期检查
                if state_manager.is_in_cooldown(symbol):
                    # 降低冷却期日志频率，避免刷屏
                    if heartbeat_counter % 12 == 0:
                        logger.info(f"{symbol} 处于冷却期，跳过买入检查")
                    time.sleep(POLLING_INTERVAL)
                    continue

                # 策略: 日内动量策略
                # day_change_pct 已经在上面计算过了
                
                # [修改] 3.a 动量买入条件增强 (价格涨幅 + 成交量过滤)
                # 修复：兼容 Finnhub 接口未返回成交量(即为 0.0)的情况，防止因获取不到数据而错过行情
                volume_ok = (current_volume > MIN_VOLUME_THRESHOLD) or (current_volume == 0.0)
                price_trend_ok = day_change_pct > BUY_MOMENTUM_THRESHOLD

                if price_trend_ok and volume_ok:
                    logger.info(f"{symbol} 触发买入信号: 日涨幅 {day_change_pct:.2%} | 成交量 {current_volume}")
                    trader.execute_buy(symbol, config['budget'], current_price)
                elif price_trend_ok and not volume_ok:
                    logger.info(f"{symbol} 价格达标但成交量不足 ({current_volume})，不操作")
                else:
                    pass # 观察中，不满足条件时不打印日志，避免日志爆炸

        except Exception as e:
            logger.error(f"策略循环错误 ({symbol}): {e}")
        
        time.sleep(POLLING_INTERVAL)

# ==========================================
# 6. 主程序流程
# ==========================================

def main():
    # 打印欢迎信息
    print("========================================")
    print("   Longport AutoTrade v0.1.5 (Heartbeat Added)")
    print("========================================")

    # 交互式启动选择
    if os.path.exists(STATE_FILE):
        choice = input("检测到之前的交易状态文件。是否继续上次的交易状态? (y/n): ").strip().lower()
        if choice == 'y':
            state_manager.load_state()
        else:
            state_manager.reset_state()
    else:
        state_manager.reset_state()

    # 信号处理 (Ctrl+C 优雅退出)
    running_event = threading.Event()
    running_event.set()

    def signal_handler(sig, frame):
        print("\n正在停止脚本，请稍候...")
        running_event.clear()
        state_manager.save_state()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # 启动多线程策略
    threads = []
    for ticker, config in TARGET_STOCKS.items():
        t = threading.Thread(
            target=dxyz_strategy_logic, 
            args=(ticker, config, running_event),
            name=f"Thread-{ticker}"
        )
        t.start()
        threads.append(t)

    print(f"监控已启动: {list(TARGET_STOCKS.keys())}")
    print("美股交易时间 (ET): 09:30 - 16:00 (含冬夏令时自动切换)")
    print("按 Ctrl+C 安全停止脚本并保存状态。")

    # 主线程维持运行
    while running_event.is_set():
        time.sleep(1)

    for t in threads:
        t.join()

if __name__ == "__main__":
    main()
