from fastapi import FastAPI, Request
import ccxt, os, uvicorn

app = FastAPI()

# 初始化币安合约测试网
exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_API_SECRET'),
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})
exchange.set_sandbox_mode(True)

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
    except:
        return {"status": "error", "msg": "Invalid JSON"}

    # 暗号校验
    if data.get('passphrase') != os.getenv('WEBHOOK_PASSPHRASE'):
        return {"status": "error", "msg": "Auth failed"}
    
    try:
        symbol = data.get('ticker').upper()
        # action 用于判断是否为平仓 (如 SELLEXIT)
        action = str(data.get('action', '')).lower()
        # order_side 是 TV 告诉我们的物理方向 (buy/sell)
        side = str(data.get('order_side', 'buy')).lower()
        amount = float(data.get('quantity'))
        
        params = {}
        # 如果动作包含 exit 或 close，开启只减仓模式保护
        if 'exit' in action or 'close' in action:
            params['reduceOnly'] = True
            
        if side == 'buy':
            order = exchange.create_market_buy_order(symbol, amount, params)
        else:
            order = exchange.create_market_sell_order(symbol, amount, params)
            
        print(f"成功: {action} {symbol} {amount}")
        return {"status": "success", "order_id": order['id']}
    except Exception as e:
        print(f"报错: {str(e)}")
        return {"status": "error", "msg": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)