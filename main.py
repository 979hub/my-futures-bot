from fastapi import FastAPI, Request
import ccxt
import uvicorn
import os

app = FastAPI()

# --- 配置 ---
API_KEY = "Lkz7YBGBEmhvvw0TuEH2RBkGemxNPgaIJDp3YB60Zmmqv29unHSJh4tecjDVtmgd"
API_SECRET = "Oap296HNhuef9KiCq4Mgm0xrOLAxwZq4VC42pYZ93i5TmL9SMkp7lg9XgWFflEdZ"
WEBHOOK_PASSPHRASE = "ss999"

exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
        'adjustForTimeDifference': True, # 自动同步服务器时间
    }
})

# 强制 Demo 域名
demo_base = 'https://demo-fapi.binance.com'
exchange.urls['api']['fapiPublic'] = demo_base + '/fapi/v1'
exchange.urls['api']['fapiPrivate'] = demo_base + '/fapi/v1'

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
    except:
        return {"status": "error", "msg": "Invalid JSON"}

    if data.get('passphrase') != WEBHOOK_PASSPHRASE:
        return {"status": "error", "msg": "Auth failed"}
    
    try:
        symbol = data.get('ticker', '').upper().replace(".P", "")
        if "USDT" in symbol and "/" not in symbol:
            symbol = symbol.replace("USDT", "/USDT")

        side = str(data.get('order_side', 'buy')).lower()
        amount = float(data.get('quantity', 0))
        
        # 下单
        order = exchange.create_order(
            symbol=symbol,
            type='market',
            side=side,
            amount=amount
        )
        return {"status": "success", "order_id": order['id']}
    except Exception as e:
        print(f"交易报错: {str(e)}")
        return {"status": "error", "msg": str(e)}

if __name__ == "__main__":
    # 修改端口为 8080，避免权限问题
    print("服务启动中，监听端口 8080...")
    uvicorn.run(app, host="0.0.0.0", port=8080)
