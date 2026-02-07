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
APP_KEY = "1820cfed626d47cb7675f017cb92e3dc"
APP_SECRET = "19bac0de0c2eaee7f298d55b9a726ea6b513d0793ddd798b30222e43872b05f8"
ACCESS_TOKEN = "m_eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJsb25nYnJpZGdlIiwic3ViIjoiYWNjZXNzX3Rva2VuIiwiZXhwIjoxNzc4MTM3NzEyLCJpYXQiOjE3NzAzNjE3MTIsImFrIjoiMTgyMGNmZWQ2MjZkNDdjYjc2NzVmMDE3Y2I5MmUzZGMiLCJhYWlkIjoyMTI2NTA3NSwiYWMiOiJsYl9wYXBlcnRyYWRpbmciLCJtaWQiOjE1NzQyMzM4LCJzaWQiOiJQQzM2d0twNU1Ra1pLRm1UemMxNDZBPT0iLCJibCI6MywidWwiOjAsImlrIjoibGJfcGFwZXJ0cmFkaW5nXzIxMjY1MDc1In0.OWsPUu7aNNLITv4kUlDaGD8u9iyUWQOWQKAarZNZvI2I8_T-amiHt4805RaduaFoevJtN_826pBpg0hZYXsf3DGoSlpIr66tMft9P9EOB0zSzoqfNFeEFaaCB1YGIqhsDupIP-9rE5QvOif8yGhhwPhaTPdZzBybaEt9tL5d8jz50Es2_iqN9t2LiayQ4x2nx_6eXjjcFGWMtgMJPF4amf4y7ncWWFr3TUo4KZR9Pd03aQ3QpNJg2GAkmHshL2Om0K3BoEZap0n5uLn8snCwI2BwPZ2XhXz457jND40eVSafp8oYcW2rDBXxQsj6-bWUpOzCRK8C9KSfnYU8FLTxbPmdChWPXXkmhGKN7wbD-RcS39Fo25Tu7AuSXd29uQ0FqqQagUmmb2Xf_2eUFspdrdsG4PucsXVxnUIJSiOvudnNoEXTyxdhKek3B8VI2b0gCtJ5wGBeX46eOBgLPq3dX51ymBZGIpIAO-SnsoqSqaoIK-opfDo8gH_BQ8K7NJUGgRkBC_p0YieFDjnrnydSViMnu9DSaavtFJV3O4klswvh1jZ0YU3wSEeK8vjk130VVLZC1wehBz5QK_5rPKFFoZkmrRm0W3UiBXXrMgCzxT9Sfx5naC4eI2wTnNwGD6Q7lCRX4NAFNP7yeIPBArt2Zwk8vvQXGdCtbEcbivNQFwk" 

# Finnhub 配置 (去 finnhub.io 注册获取免费 API Key)
FINNHUB_API_KEY = "d62qoq1r01qnpu82b9kgd62qoq1r01qnpu82b9l0" 
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
