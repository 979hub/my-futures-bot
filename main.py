from fastapi import FastAPI, Request
import ccxt
import uvicorn
import os

app = FastAPI()

# --- 配置区 ---
# 建议在正式环境使用 os.getenv('BINANCE_API_KEY')
API_KEY = "Lkz7YBGBEmhvvw0TuEH2RBkGemxNPgaIJDp3YB60Zmmqv29unHSJh4tecjDVtmgd"
API_SECRET = "Oap296HNhuef9KiCq4Mgm0xrOLAxwZq4VC42pYZ93i5TmL9SMkp7lg9XgWFflEdZ"
WEBHOOK_PASSPHRASE = "ss999"

# 初始化币安合约对象
# 注意：不要调用 exchange.set_sandbox_mode(True)，因为它会指向已失效的旧测试网
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',  # 必选：设置为 U 本位合约
    }
})

# 核心修改：强制指定为币安最新的 Demo Trading 接口地址
exchange.urls['api']['fapiPublic'] = 'https://demo-fapi.binance.com/fapi/v1'
exchange.urls['api']['fapiPrivate'] = 'https://demo-fapi.binance.com/fapi/v1'

@app.post("/webhook")
async def webhook(request: Request):
    # 1. 获取原始数据并解析 JSON
    try:
        data = await request.json()
        print(f"收到信号: {data}")
    except Exception:
        return {"status": "error", "msg": "Invalid JSON"}

    # 2. 暗号校验
    received_passphrase = data.get('passphrase')
    if received_passphrase != WEBHOOK_PASSPHRASE:
        print(f"安全校验失败: 收到暗号 {received_passphrase}")
        return {"status": "error", "msg": "Auth failed"}
    
    # 3. 参数解析与格式化
    try:
        # TradingView 传来的 ticker 可能是 "BTCUSDT" 或 "BTCUSDT.P"
        raw_symbol = data.get('ticker', '').upper().replace(".P", "")
        # 确保格式为 BTC/USDT (CCXT 标准格式)
        if "USDT" in raw_symbol and "/" not in raw_symbol:
            symbol = raw_symbol.replace("USDT", "/USDT")
        else:
            symbol = raw_symbol

        action = str(data.get('action', '')).lower()  # 例如: buy, sell, buy-exit
        side = str(data.get('order_side', 'buy')).lower() # 物理方向: buy 或 sell
        amount = float(data.get('quantity', 0))

        if amount <= 0:
            return {"status": "error", "msg": "Quantity must > 0"}

        # 4. 构建交易参数
        params = {}
        # 如果 action 包含 exit，代表是平仓指令，开启只减仓模式防止反向开仓
        if 'exit' in action or 'close' in action:
            params['reduceOnly'] = True
            
        print(f"执行交易 -> 品种: {symbol}, 方向: {side}, 数量: {amount}, 只减仓: {params.get('reduceOnly', False)}")

        # 5. 执行市价单
        if side == 'buy':
            order = exchange.create_market_buy_order(symbol, amount, params)
        elif side == 'sell':
            order = exchange.create_market_sell_order(symbol, amount, params)
        else:
            return {"status": "error", "msg": f"Invalid order_side: {side}"}
            
        print(f"下单成功! ID: {order['id']}")
        return {"status": "success", "order_id": order['id']}

    # --- 详细识别 API 错误类型 ---
    except ccxt.InsufficientFunds as e:
        err = f"余额不足: {str(e)}"
    except ccxt.AuthenticationError as e:
        err = f"API Key 验证失败: 请确认使用的是 Demo 交易的 Key"
    except ccxt.InvalidOrder as e:
        err = f"订单参数无效: {str(e)} (检查最小下单量)"
    except ccxt.NetworkError as e:
        err = f"网络连接超时: 请确认服务器可访问币安 API"
    except Exception as e:
        err = f"系统错误: {str(e)}"

    print(f"下单失败: {err}")
    return {"status": "error", "msg": err}

if __name__ == "__main__":
    # 如果是在本地运行，端口可以改成 8000 避免权限问题
    uvicorn.run(app, host="0.0.0.0", port=80)
