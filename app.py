from flask import Flask, render_template, jsonify
from utils.bybit_client import get_account_info
import os

app = Flask(__name__)

@app.route('/')
def index():
    data = get_account_info()
    
    wallet_resp = data.get('wallet', {})
    positions_resp = data.get('positions', {})
    
    # Process Wallet Data
    wallet_data = []
    if wallet_resp and wallet_resp.get('retCode') == 0:
        result = wallet_resp.get('result', {})
        list_data = result.get('list', [])
        if list_data:
            account_data = list_data[0]
            coins = account_data.get('coin', [])
            for coin in coins:
                wallet_data.append({
                    'coin': coin.get('coin'),
                    'equity': coin.get('equity'),
                    'wallet_balance': coin.get('walletBalance'),
                    'usd_value': coin.get('usdValue')
                })

    # Process Position Data
    positions_data = []
    if positions_resp and positions_resp.get('retCode') == 0:
        result = positions_resp.get('result', {})
        list_data = result.get('list', [])
        for pos in list_data:
            # Filter out closed positions or zero size if needed, 
            # but usually 'list' contains active positions. 
            # Example fields: symbol, side, size, avgPrice, markPrice, unrealisedPnl
            if float(pos.get('size', 0)) > 0:
                positions_data.append({
                    'symbol': pos.get('symbol'),
                    'side': pos.get('side'),
                    'size': pos.get('size'),
                    'entry_price': pos.get('avgPrice'),
                    'mark_price': pos.get('markPrice'),
                    'pnl': pos.get('unrealisedPnl')
                })

    import json
    with open("app_debug.json", "w") as f:
        json.dump({
            "wallet": wallet_resp,
            "positions": positions_resp,
            "positions_data": positions_data
        }, f, indent=2)

    return render_template(
        'index.html', 
        wallet_data=wallet_data, 
        positions_data=positions_data,
        wallet_raw=wallet_resp,
        positions_raw=positions_resp
    )

if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(debug=False, port=5000)
