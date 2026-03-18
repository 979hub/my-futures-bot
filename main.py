from fastapi import FastAPI, Request
import ccxt
import os
import uvicorn

app = FastAPI()

# --- 核心修改：手动指定 demo-fapi 地址 ---
exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_API_SECRET'),
    'enableRateLimit': True,
    # 强制覆盖 API 地址为币安最新的 Demo Trading 地址
    'urls': {
        'api': {
            'fapiPublic': 'https://demo-fapi.binance.com/fapi/v1',
            'fapiPrivate': 'https://demo-fapi.binance.com/fapi/v1',
        },
    },
    'options': {
        'defaultType': 'future'
    }
})

# 注意：这里不再使用 set_sandbox_mode(True)，因为地址已经在上面手动指定了

PASSPHRASE = os.getenv('WEBHOOK_PASSPHRASE')

@app.get("/")
def home():
    return {"status": "Bot is online!", "mode": "Binance Demo Trading"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
    except:
        return {"status": "error", "msg": "Invalid JSON"}

    if data.get('passphrase') != PASSPHRASE:
        return {"status": "error", "msg": "Auth failed"}
    
    try:
        symbol = data.get('ticker').upper()
        action = str(data.get('action', '')).lower()
        side = str(data.get('order_side', 'buy')).lower()
        amount = float(data.get('quantity'))
        
        params = {}
        if 'exit' in action or 'close' in action:
            params['reduceOnly'] = True
            
        if side == 'buy':
            order = exchange.create_market_buy_order(symbol, amount, params)
        else:
            order = exchange.create_market_sell_order(symbol, amount, params)
            
        print(f"成功下单: {symbol} | {side}")
        return {"status": "success", "order_id": order['id']}
    except Exception as e:
        print(f"下单报错: {str(e)}")
        return {"status": "error", "msg": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)
