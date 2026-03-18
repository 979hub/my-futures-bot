from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
import hmac, hashlib, time, os, httpx, uvicorn

app = FastAPI()

# 模拟你 JS 里的 Nginx 伪装页面
NGINX_404 = "<h1>404 Not Found</h1><hr><p>nginx</p>"

# 币安签名算法 (对应你的 generateSignature)
def generate_signature(query_string, secret):
    return hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()

@app.api_route("/{path:path}", methods=["GET", "POST"])
async def catch_all(request: Request, path: str):
    # 1. 伪装逻辑：非 POST 请求直接报 Nginx 404
    if request.method != "POST":
        return HTMLResponse(content=NGINX_404, status_code=404)

    try:
        data = await request.json()
        
        # 从环境变量读取密钥
        API_KEY = os.getenv('BINANCE_API_KEY', '').strip()
        API_SECRET = os.getenv('BINANCE_API_SECRET', '').strip()
        PASSPHRASE = os.getenv('WEBHOOK_PASSPHRASE', '').strip()

        # 2. 校验暗号 (对应你 JS 的 passphrase 校验)
        if not data.get('passphrase') or data.get('passphrase') != PASSPHRASE:
            print("[警告] 拦截到非法请求。")
            return Response(content="Not Found", status_code=404)

        # 3. 核心清洗逻辑 (完全复刻你的 JS 逻辑)
        # 例子: "BINANCE:BTCUSDT.P" -> "BTCUSDT"
        raw_symbol = data.get('symbol', 'BTCUSDT')
        symbol = raw_symbol.split(':')[-1].replace("!", "").replace(".P", "").upper()
        side = data.get('side', 'BUY').upper()
        qty = abs(float(data.get('qty', 0)))
        timestamp = int(time.time() * 1000)

        print(f"[信号] 收到交易指令: {symbol} {side} 数量: {qty}")

        # 4. 构建请求 (指向 demo-fapi 测试网)
        query_string = f"symbol={symbol}&side={side}&type=MARKET&quantity={qty}&recvWindow=10000&timestamp={timestamp}"
        signature = generate_signature(query_string, API_SECRET)
        
        # 如果要实盘，就把 demo-fapi 改成 fapi
        binance_url = f"https://demo-fapi.binance.com/fapi/v1/order?{query_string}&signature={signature}"

        # 5. 发送请求
        async with httpx.AsyncClient() as client:
            response = await client.post(binance_url, headers={'X-MBX-APIKEY': API_KEY})
            res_data = response.json()

        # 6. 反馈结果
        if response.status_code == 200:
            print(f"[成功] 币安已执行下单")
            return res_data
        else:
            print(f"[币安返回报错] {res_data}")
            return Response(content=str(res_data), status_code=400)

    except Exception as e:
        print(f"运行时错误: {str(e)}")
        return Response(content="Not Found", status_code=404)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)
