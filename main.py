from fastapi import FastAPI, Request
import ccxt, os, uvicorn

app = FastAPI()

# 读取并清理环境变量（防止空格干扰）
API_KEY = os.getenv('BINANCE_API_KEY', '').strip()
API_SECRET = os.getenv('BINANCE_API_SECRET', '').strip()
PASSPHRASE = os.getenv('WEBHOOK_PASSPHRASE', '').strip()

# 初始化交易所
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

# --- 💡 关键修复部分 💡 ---
# 如果你是从 testnet.binancefuture.com (旧站) 拿的 Key，用这一行：
exchange.set_sandbox_mode(True) 

# 如果你是从币安 App/官网“模拟交易” (新站) 拿的 Key，
# 且上面那行报错，请注释掉上面那行，改用下面这三行：
# exchange.urls['api']['fapiPublic'] = 'https://demo-fapi.binance.com/fapi/v1'
# exchange.urls['api']['fapiPrivate'] = 'https://demo-fapi.binance.com/fapi/v1'
# -------------------------

@app.get("/")
def check():
    return {
        "status": "Running",
        "key_prefix": API_KEY[:5],
        "using_sandbox": exchange.urls['api']['fapiPublic']
    }

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    if data.get('passphrase') != PASSPHRASE:
        return {"status": "error", "msg": "Auth failed"}
    
    try:
        symbol = data.get('ticker', 'BTCUSDT').upper()
        side = data.get('order_side', 'buy').lower()
        amount = float(data.get('quantity'))
        
        # 下单执行
        order = exchange.create_market_buy_order(symbol, amount) if side == 'buy' else exchange.create_market_sell_order(symbol, amount)
        return {"status": "success", "order_id": order['id']}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)
