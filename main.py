from fastapi import FastAPI, Request
import ccxt
import os
import uvicorn

app = FastAPI()

# 1. 初始化币安合约
# 注意：不要再调用 set_sandbox_mode(True)
exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_API_SECRET'),
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future', # 默认合约模式
    }
})

# 2. 强制指向新的 Demo Trading 接口地址
# 覆盖 CCXT 默认的合约 API 路径
exchange.urls['api']['fapiPublic'] = 'https://demo-fapi.binance.com/fapi/v1'
exchange.urls['api']['fapiPrivate'] = 'https://demo-fapi.binance.com/fapi/v1'

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
    except Exception:
        return {"status": "error", "msg": "Invalid JSON"}

    # 安全校验
    passphrase = os.getenv('WEBHOOK_PASSPHRASE')
    if passphrase and data.get('passphrase') != passphrase:
        return {"status": "error", "msg": "Auth failed"}
    
    try:
        # 清理 ticker (例如把 BTCUSDT.P 变成 BTC/USDT)
        symbol = data.get('ticker', '').upper().replace(".P", "")
        # 如果 symbol 不包含斜杠，CCXT 会自动处理 BTCUSDT，但建议加上
        if "/" not in symbol and "USDT" in symbol:
            symbol = symbol.replace("USDT", "/USDT")

        action = str(data.get('action', '')).lower()
        side = str(data.get('order_side', 'buy')).lower()
        amount = float(data.get('quantity', 0))
        
        params = {}
        # 只减仓逻辑
        if 'exit' in action or 'close' in action:
            params['reduceOnly'] = True
            
        print(f"执行 Demo 交易: {symbol} {side} {amount} | Params: {params}")

        # 下单
        if side == 'buy':
            order = exchange.create_market_buy_order(symbol, amount, params)
        else:
            order = exchange.create_market_sell_order(symbol, amount, params)
            
        print(f"下单成功: {order['id']}")
        return {"status": "success", "order_id": order['id']}

    # --- 详细的 API 错误捕获 ---
    except ccxt.AuthenticationError:
        error_msg = "API Key 错误：请确保使用的是 Demo Trading 的 Key"
    except ccxt.InsufficientFunds:
        error_msg = "Demo 账户余额不足"
    except ccxt.InvalidOrder as e:
        error_msg = f"订单无效: {str(e)} (检查数量是否符合最小值要求)"
    except ccxt.NetworkError:
        error_msg = "网络请求失败，请检查服务器是否能访问 demo-fapi.binance.com"
    except Exception as e:
        error_msg = f"发生错误: {str(e)}"

    print(f"操作失败: {error_msg}")
    return {"status": "error", "msg": error_msg}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)
