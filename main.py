from fastapi import FastAPI, Request
import ccxt, os, uvicorn

app = FastAPI()

# 获取环境变量
API_KEY = os.getenv('BINANCE_API_KEY', '').strip()
API_SECRET = os.getenv('BINANCE_API_SECRET', '').strip()
PASSPHRASE = os.getenv('WEBHOOK_PASSPHRASE', '').strip()

# 初始化交易所 - 我们这次尝试最标准的方法
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

# --- 关键：手动指定 Demo 交易地址 ---
exchange.urls['api']['fapiPublic'] = 'https://demo-fapi.binance.com/fapi/v1'
exchange.urls['api']['fapiPrivate'] = 'https://demo-fapi.binance.com/fapi/v1'

@app.get("/")
def debug_info():
    # 这里的目的是让你在浏览器就能看到机器人读到的 Key 是否正确（隐藏中间部分）
    masked_key = f"{API_KEY[:5]}****{API_KEY[-5:]}" if len(API_KEY) > 10 else "未读取到Key"
    return {
        "status": "Online",
        "read_api_key_prefix": masked_key,
        "endpoint": "https://demo-fapi.binance.com",
        "tip": "如果Key前5位不对，说明环境变量没填对或没生效"
    }

@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    if data.get('passphrase') != PASSPHRASE:
        return {"status": "error", "msg": "Auth failed"}
    
    try:
        symbol = data.get('ticker').upper()
        side = data.get('order_side', 'buy').lower()
        amount = float(data.get('quantity'))
        
        # 下单测试
        order = exchange.create_market_buy_order(symbol, amount) if side == 'buy' else exchange.create_market_sell_order(symbol, amount)
        return {"status": "success", "order_id": order['id']}
    except Exception as e:
        # 打印详细报错到日志
        print(f"DEBUG Error: {str(e)}")
        return {"status": "error", "msg": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)
