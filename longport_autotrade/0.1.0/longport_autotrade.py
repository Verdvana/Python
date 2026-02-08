#!/usr/bin/python3
import time
import math
import pandas as pd
import numpy as np
import yfinance as yf
import finnhub
from decimal import Decimal
from longport.openapi import Config, TradeContext, OrderType, OrderSide, TimeInForceType

# ==========================================
# 1. 账户与 API 配置区
# ==========================================
# 长桥配置
APP_KEY = ""
APP_SECRET = ""
ACCESS_TOKEN = "" 

# Finnhub 配置 (去 finnhub.io 注册获取免费 API Key)
FINNHUB_API_KEY = "" 
finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)

SYMBOL_YF = "DXYZ"       # yfinance 使用的格式
SYMBOL_LP = "DXYZ.US"    # 长桥使用的格式

TOTAL_BUDGET = 100      
STOP_LOSS_PCT = 0.05    

# ==========================================
# 2. 数据获取逻辑 (yfinance 算指标 + Finnhub 拿现价)
# ==========================================
def get_strategy_data(symbol_yf):
    try:
        # 1. 使用 yfinance 获取 5 分钟线计算指标
        ticker = yf.Ticker(symbol_yf)
        # 获取最近 5 天的数据以确保 MA20 计算准确
        df = ticker.history(period="2d", interval="5m")
        
        if df.empty or len(df) < 20:
            return None, None

        # 计算指标
        df['ma5'] = df['Close'].rolling(window=5).mean()
        df['ma20'] = df['Close'].rolling(window=20).mean()
        
        # 计算 RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, np.nan)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        curr_metrics = df.iloc[-1]
        prev_metrics = df.iloc[-2]

        # 2. 使用 Finnhub 获取最新实时报价 (弥补 yfinance 的延迟)
        quote = finnhub_client.quote(symbol_yf)
        realtime_price = Decimal(str(quote['c'])) if quote.get('c') else Decimal(str(curr_metrics['Close']))

        return curr_metrics, prev_metrics, realtime_price
    except Exception as e:
        print(f"数据获取异常: {e}")
        return None, None, None

# ==========================================
# 3. 核心交易逻辑
# ==========================================
def run_bot():
    config = Config(app_key=APP_KEY, app_secret=APP_SECRET, access_token=ACCESS_TOKEN)
    # 仅初始化交易上下文
    t_ctx = TradeContext(config)
    
    is_holding = False
    buy_price = Decimal("0")
    hold_quantity = 0

    print(f"--- 机器人已启动 | 模式: yfinance指标+Finnhub现价 | 监控: {SYMBOL_LP} ---")

    try:
        while True:
            curr, prev, current_price = get_strategy_data(SYMBOL_YF)
            
            if curr is None or current_price == 0:
                print("等待数据更新...")
                time.sleep(20)
                continue
            
            ma5_curr, ma20_curr = curr['ma5'], curr['ma20']
            ma5_prev, ma20_prev = prev['ma5'], prev['ma20']
            rsi = curr['rsi']

            print(f"[{time.strftime('%H:%M:%S')}] 现价: {current_price} | MA5: {ma5_curr:.2f} | RSI: {rsi:.1f}")

            # 1. 止损判断
            if is_holding and current_price <= buy_price * (Decimal("1") - Decimal(str(STOP_LOSS_PCT))):
                print(f"🚨 [止损触发] 当前价 {current_price} 跌破买入价 {buy_price} 的止损线")
                if submit_order(t_ctx, OrderSide.Sell, current_price, hold_quantity):
                    is_holding, hold_quantity = False, 0

            # 2. 买入信号 (金叉 + RSI)
            elif not is_holding:
                if ma5_prev <= ma20_prev and ma5_curr > ma20_curr and rsi < 70:
                    qty = math.floor(TOTAL_BUDGET / float(current_price))
                    if qty > 0:
                        print(f"🟢 [买入信号] 尝试以 {current_price} 买入 {qty} 股")
                        if submit_order(t_ctx, OrderSide.Buy, current_price, qty):
                            is_holding, buy_price, hold_quantity = True, current_price, qty

            # 3. 卖出信号 (死叉)
            elif is_holding:
                if ma5_prev >= ma20_prev and ma5_curr < ma20_curr:
                    print(f"🔴 [卖出信号] 均线死叉，平仓 {hold_quantity} 股")
                    if submit_order(t_ctx, OrderSide.Sell, current_price, hold_quantity):
                        is_holding, hold_quantity = False, 0

            time.sleep(30) # 30秒轮询一次

    except KeyboardInterrupt:
        print("\n用户手动停止")
    finally:
        t_ctx.close()
        print("长桥连接已关闭")

def submit_order(ctx, side, price, qty):
    try:
        # 注意：下单必须使用带 .US 的 Symbol
        resp = ctx.submit_order(
            symbol=SYMBOL_LP,
            order_type=OrderType.LO, # 限价单
            side=side,
            submitted_price=price,
            submitted_quantity=qty,
            time_in_force=TimeInForceType.Day
        )
        print(f"✅ 订单已提交! ID: {resp.order_id}")
        return True
    except Exception as e:
        print(f"❌ 下单失败: {e}")
        return False

if __name__ == "__main__":
    run_bot()
