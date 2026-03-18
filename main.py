from fastapi import FastAPI, Request
import ccxt
import uvicorn
import json

app = FastAPI()

# --- 配置区 (建议生产环境用环境变量) ---
API_KEY = "Lkz7YBGBEmhvvw0TuEH2RBkGemxNPgaIJDp3YB60Zmmqv29unHSJh4tecjDVtmgd"
API_SECRET = "Oap296HNhuef9KiCq4Mgm0xrOLAxwZq4VC42pYZ93i5TmL9SMkp7lg9XgWFflEdZ"
WEBHOOK_PASSPHRASE = "ss999"

# 初始化币安合约对象
# 注意：完全不要使用 set_sandbox_mode(True)
exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future', 
    }
})

# 【关键点】强制将所有合约请求重定向到 Demo 域名
# 币安 Demo 盘的根地址是特定的，我们需要覆盖 fapi 的所有端点
demo_base = 'https://demo-fapi.binance.com'
exchange.urls['api']['fapiPublic'] = demo_base + '/fapi/v1'
exchange.urls['api']['fapiPrivate'] = demo_base + '/fapi/v1'

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
    except:
        return {"status": "error", "msg": "Invalid JSON"}

    # 1. 暗号校验
    if data.get('passphrase') != WEBHOOK_PASSPHRASE:
        return {"status": "error", "msg": "Auth failed"}
    
    try:
        # 2. 符号处理：将 BTCUSDT 转换为 BTC/USDT
        symbol = data.get('ticker', '').upper().replace(".P", "")
        if "USDT" in symbol and "/" not in symbol:
            symbol = symbol.replace("USDT", "/USDT")

        action = str(data.get('action', '')).lower()
        side = str(data.get('order_side', 'buy')).lower()
        amount = float(data.get('quantity', 0))

        # 3. 参数构造
        params = {}
        # 如果动作包含平仓关键字，启用只减仓
        if any(x in action for x in ['exit', 'close', '平仓']):
            params['reduceOnly'] = True
            
        print(f"尝试下单 -> 品种: {symbol}, 方向: {side}, 数量: {amount}, 模式: {'只减仓' if 'reduceOnly' in params else '开仓'}")

        # 4. 执行市价单
        # 使用 create_order 通用方法更稳健
        order = exchange.create_order(
            symbol=symbol,
            type='market',
            side=side,
            amount=amount,
            params=params
        )
            
        print(f"下单成功! ID: {order['id']}")
        return {"status": "success", "order_id": order['id']}

    # --- 详细识别 API 错误类型 ---
    except ccxt.AuthenticationError as e:
        error_info = "API Key 验证失败！请确保你在【模拟交易】页面生成的 Key，而非实盘 Key。"
    except ccxt.InsufficientFunds as e:
        error_info = "Demo 账户余额不足。"
    except ccxt.InvalidOrder as e:
        # 币安常报：API key does not have permission for this action (即使是Demo也可能权限没勾选)
        # 或者：Order would immediately trigger (价格跳变)
        error_info = f"订单无效: {str(e)}"
    except ccxt.NetworkError as e:
        error_info = f"网络请求失败，无法连接到 Demo 域名: {str(e)}"
    except Exception as e:
        error_info = f"未知错误: {str(e)}"

    print(f"执行失败: {error_info}")
    return {"status": "error", "msg": error_info}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=80)
