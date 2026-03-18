from fastapi import FastAPI, Request
import ccxt
import os
import uvicorn

app = FastAPI()

# 初始化币安合约 Demo 环境
exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_API_SECRET'),
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future'  # 指定为合约
    }
})

# 强制指向 Demo 交易地址 (https://demo-fapi.binance.com)
exchange.urls['api']['fapiPublic'] = 'https://demo-fapi.binance.com/fapi/v1'
exchange.urls['api']['fapiPrivate'] = 'https://demo-fapi.binance.com/fapi/v1'

# 也可以使用 ccxt 的内置 sandbox 模式，它通常会自动处理地址
# 但明确指定上面两个 URL 是最稳妥的
exchange.set_sandbox_mode(True) 

@app.post("/webhook")
async def webhook(request: Request):
    # 1. 解析 JSON
    try:
        data = await request.json()
    except Exception:
        return {"status": "error", "msg": "Invalid JSON"}

    # 2. 安全校验 (暗号)
    passphrase = os.getenv('WEBHOOK_PASSPHRASE')
    if passphrase and data.get('passphrase') != passphrase:
        return {"status": "error", "msg": "Auth failed"}
    
    # 3. 提取字段
    try:
        symbol = data.get('ticker', '').upper().replace(".P", "") # 兼容 TV 格式
        action = str(data.get('action', '')).lower()
        side = str(data.get('order_side', 'buy')).lower()
        amount = float(data.get('quantity', 0))
        
        if amount <= 0:
            return {"status": "error", "msg": "Quantity must > 0"}

        params = {}
        # 只减仓逻辑
        if 'exit' in action or 'close' in action:
            params['reduceOnly'] = True
            
        print(f"正在向 DEMO 环境下单: {symbol} {side} {amount}")

        # 4. 执行下单操作
        if side == 'buy':
            order = exchange.create_market_buy_order(symbol, amount, params)
        else:
            order = exchange.create_market_sell_order(symbol, amount, params)
            
        print(f"成功: {symbol} 下单成功 ID: {order['id']}")
        return {"status": "success", "order_id": order['id']}

    # --- 精细化 API 错误识别 ---
    except ccxt.InsufficientFunds as e:
        error_msg = f"余额不足 (Demo): {str(e)}"
    except ccxt.AuthenticationError as e:
        error_msg = f"API 密钥错误: 请检查 Demo 交易的 Key/Secret 是否正确"
    except ccxt.InvalidOrder as e:
        error_msg = f"订单参数错误 (如最小下单量不足): {str(e)}"
    except ccxt.NetworkError as e:
        error_msg = f"网络请求失败 (无法连接到 demo-fapi): {str(e)}"
    except ccxt.ExchangeError as e:
        error_msg = f"交易所逻辑错误: {str(e)}"
    except Exception as e:
        error_msg = f"其他错误: {str(e)}"

    print(f"报错详情: {error_msg}")
    return {"status": "error", "msg": error_msg}

if __name__ == "__main__":
    # 生产环境建议端口 8080，如果用 80 端口确保有 root/管理员权限
    uvicorn.run(app, host="0.0.0.0", port=80)
