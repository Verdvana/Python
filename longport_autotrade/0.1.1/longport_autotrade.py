#!/usr/bin/python3
import time
import math
import json
import os
import pandas as pd
import numpy as np
import yfinance as yf
import finnhub
from decimal import Decimal
from longport.openapi import Config, TradeContext, OrderType, OrderSide, TimeInForceType

# ==========================================
# 1. 配置区
# ==========================================
APP_KEY = "1820cfed626d47cb7675f017cb92e3dc"
APP_SECRET = "19bac0de0c2eaee7f298d55b9a726ea6b513d0793ddd798b30222e43872b05f8"
ACCESS_TOKEN = "m_eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJsb25nYnJpZGdlIiwic3ViIjoiYWNjZXNzX3Rva2VuIiwiZXhwIjoxNzc4MTM3NzEyLCJpYXQiOjE3NzAzNjE3MTIsImFrIjoiMTgyMGNmZWQ2MjZkNDdjYjc2NzVmMDE3Y2I5MmUzZGMiLCJhYWlkIjoyMTI2NTA3NSwiYWMiOiJsYl9wYXBlcnRyYWRpbmciLCJtaWQiOjE1NzQyMzM4LCJzaWQiOiJQQzM2d0twNU1Ra1pLRm1UemMxNDZBPT0iLCJibCI6MywidWwiOjAsImlrIjoibGJfcGFwZXJ0cmFkaW5nXzIxMjY1MDc1In0.OWsPUu7aNNLITv4kUlDaGD8u9iyUWQOWQKAarZNZvI2I8_T-amiHt4805RaduaFoevJtN_826pBpg0hZYXsf3DGoSlpIr66tMft9P9EOB0zSzoqfNFeEFaaCB1YGIqhsDupIP-9rE5QvOif8yGhhwPhaTPdZzBybaEt9tL5d8jz50Es2_iqN9t2LiayQ4x2nx_6eXjjcFGWMtgMJPF4amf4y7ncWWFr3TUo4KZR9Pd03aQ3QpNJg2GAkmHshL2Om0K3BoEZap0n5uLn8snCwI2BwPZ2XhXz457jND40eVSafp8oYcW2rDBXxQsj6-bWUpOzCRK8C9KSfnYU8FLTxbPmdChWPXXkmhGKN7wbD-RcS39Fo25Tu7AuSXd29uQ0FqqQagUmmb2Xf_2eUFspdrdsG4PucsXVxnUIJSiOvudnNoEXTyxdhKek3B8VI2b0gCtJ5wGBeX46eOBgLPq3dX51ymBZGIpIAO-SnsoqSqaoIK-opfDo8gH_BQ8K7NJUGgRkBC_p0YieFDjnrnydSViMnu9DSaavtFJV3O4klswvh1jZ0YU3wSEeK8vjk130VVLZC1wehBz5QK_5rPKFFoZkmrRm0W3UiBXXrMgCzxT9Sfx5naC4eI2wTnNwGD6Q7lCRX4NAFNP7yeIPBArt2Zwk8vvQXGdCtbEcbivNQFwk" 

# Finnhub 配置 (去 finnhub.io 注册获取免费 API Key)
FINNHUB_API_KEY = "d62qoq1r01qnpu82b9kgd62qoq1r01qnpu82b9l0" 

SYMBOL_YF = "DXYZ"
SYMBOL_LP = "DXYZ.US"
TOTAL_BUDGET = 100      
STOP_LOSS_PCT = 0.05    
STATE_FILE = "trade_state.json" # 存储交易状态的文件

finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)

# ==========================================
# 2. 状态管理逻辑
# ==========================================
def save_state(is_holding, buy_price, hold_quantity):
    """保存当前交易状态到本地文件"""
    state = {
        "is_holding": is_holding,
        "buy_price": str(buy_price),
        "hold_quantity": hold_quantity,
        "last_update": time.strftime('%Y-%m-%d %H:%M:%S')
    }
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def load_state():
    """启动时加载上次的交易状态"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                return (
                    state["is_holding"],
                    Decimal(state["buy_price"]),
                    state["hold_quantity"]
                )
        except Exception as e:
            print(f"状态文件读取异常，将重新开始: {e}")
    return False, Decimal("0"), 0

# ==========================================
# 3. 数据获取
# ==========================================
def get_strategy_data(symbol_yf):
    try:
        ticker = yf.Ticker(symbol_yf)
        df = ticker.history(period="2d", interval="5m")
        if df.empty or len(df) < 20:
            return None, None, None

        df['ma5'] = df['Close'].rolling(window=5).mean()
        df['ma20'] = df['Close'].rolling(window=20).mean()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss.replace(0, np.nan)
        df['rsi'] = 100 - (100 / (1 + rs))
        
        curr_metrics = df.iloc[-1]
        prev_metrics = df.iloc[-2]

        quote = finnhub_client.quote(symbol_yf)
        realtime_price = Decimal(str(quote['c'])) if quote.get('c') else Decimal(str(curr_metrics['Close']))

        return curr_metrics, prev_metrics, realtime_price
    except Exception as e:
        print(f"数据获取异常: {e}")
        return None, None, None

# ==========================================
# 4. 核心交易逻辑
# ==========================================
def run_bot():
    config = Config(app_key=APP_KEY, app_secret=APP_SECRET, access_token=ACCESS_TOKEN)
    t_ctx = TradeContext(config)
    
    # 【优化点1】启动时加载状态
    is_holding, buy_price, hold_quantity = load_state()
    
    if is_holding:
        print(f"📦 检测到历史持仓：{hold_quantity} 股 | 买入成本: {buy_price}")
    else:
        print("🚀 未检测到历史持仓，开始全新监控。")

    print(f"--- 机器人运行中 | 监控: {SYMBOL_LP} | 止损率: {STOP_LOSS_PCT*100}% ---")

    try:
        while True:
            curr, prev, current_price = get_strategy_data(SYMBOL_YF)
            if curr is None or current_price == 0:
                time.sleep(20)
                continue
            
            ma5_curr, ma20_curr = curr['ma5'], curr['ma20']
            ma5_prev, ma20_prev = prev['ma5'], prev['ma20']
            rsi = curr['rsi']

            print(f"[{time.strftime('%H:%M:%S')}] 现价: {current_price} | MA5: {ma5_curr:.2f} | RSI: {rsi:.1f} | 持仓: {is_holding}")

            # 1. 强制止损判断（不做利润校验，跌破就跑）
            if is_holding and current_price <= buy_price * (Decimal("1") - Decimal(str(STOP_LOSS_PCT))):
                print(f"🚨 [止损触发] 当前价 {current_price} 低于止损线")
                if submit_order(t_ctx, OrderSide.Sell, current_price, hold_quantity):
                    is_holding, buy_price, hold_quantity = False, Decimal("0"), 0
                    save_state(is_holding, buy_price, hold_quantity)

            # 2. 买入信号
            elif not is_holding:
                if ma5_prev <= ma20_prev and ma5_curr > ma20_curr and rsi < 70:
                    qty = math.floor(TOTAL_BUDGET / float(current_price))
                    if qty > 0:
                        print(f"🟢 [买入信号] 尝试以 {current_price} 买入 {qty} 股")
                        if submit_order(t_ctx, OrderSide.Buy, current_price, qty):
                            is_holding, buy_price, hold_quantity = True, current_price, qty
                            save_state(is_holding, buy_price, hold_quantity)

            # 3. 卖出信号（均线死叉 + 【优化点2】利润保护）
            elif is_holding:
                if ma5_prev >= ma20_prev and ma5_curr < ma20_curr:
                    # 只有当前价格大于买入价格时才卖出
                    if current_price > buy_price:
                        print(f"🔴 [卖出信号] 死叉达成且有利润，平仓 {hold_quantity} 股")
                        if submit_order(t_ctx, OrderSide.Sell, current_price, hold_quantity):
                            is_holding, buy_price, hold_quantity = False, Decimal("0"), 0
                            save_state(is_holding, buy_price, hold_quantity)
                    else:
                        print(f"⏳ [等待] 出现死叉但目前亏损({current_price} < {buy_price})，继续持有等待反弹。")

            time.sleep(30)

    except KeyboardInterrupt:
        print("\n用户手动停止")
    finally:
        t_ctx.close()

def submit_order(ctx, side, price, qty):
    try:
        resp = ctx.submit_order(
            symbol=SYMBOL_LP,
            order_type=OrderType.LO,
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
