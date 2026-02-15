from flask import Flask, render_template, jsonify
from utils.bybit_client import get_account_info
import os
import time

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

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
                    'pnl': pos.get('unrealisedPnl'),
                    'leverage': pos.get('leverage', '1'),
                    'position_value': pos.get('positionValue'),
                    'liq_price': pos.get('liqPrice'),
                    'break_even_price': pos.get('breakEvenPrice'),
                    'im': pos.get('positionIM'),
                    'mm': pos.get('positionMM'),
                    'tp': pos.get('takeProfit'),
                    'sl': pos.get('stopLoss')
                })

    # Process Closed PnL Data
    closed_pnl_data = []
    closed_pnl_resp = data.get('closed_pnl', {})
    if closed_pnl_resp and closed_pnl_resp.get('retCode') == 0:
        result = closed_pnl_resp.get('result', {})
        list_data = result.get('list', [])
        for pnl in list_data:
            closed_pnl_data.append({
                'symbol': pnl.get('symbol'),
                'order_type': pnl.get('orderType'),
                'side': pnl.get('side'),
                'qty': pnl.get('qty'),
                'entry_price': pnl.get('avgEntryPrice'),
                'exit_price': pnl.get('avgExitPrice'),
                'closed_pnl': pnl.get('closedPnl'),
                'created_time': pnl.get('createdTime'), # Timestamp in ms
                'leverage': pnl.get('leverage', '1')
            })

    # Debug logging removed for production


    return render_template(
        'index.html', 
        wallet_data=wallet_data, 
        positions_data=positions_data,
        closed_pnl_data=closed_pnl_data,
        wallet_raw=wallet_resp,
        positions_raw=positions_resp
    )

@app.route('/api/data')
def get_data():
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
            if float(pos.get('size', 0)) > 0:
                positions_data.append({
                    'symbol': pos.get('symbol'),
                    'side': pos.get('side'),
                    'size': pos.get('size'),
                    'entry_price': pos.get('avgPrice'),
                    'mark_price': pos.get('markPrice'),
                    'pnl': pos.get('unrealisedPnl'),
                    'leverage': pos.get('leverage', '1'),
                    'position_value': pos.get('positionValue'),
                    'liq_price': pos.get('liqPrice'),
                    'break_even_price': pos.get('breakEvenPrice'),
                    'im': pos.get('positionIM'),
                    'mm': pos.get('positionMM'),
                    'tp': pos.get('takeProfit'),
                    'sl': pos.get('stopLoss')
                })

    # Process Closed PnL Data
    closed_pnl_data = []
    closed_pnl_resp = data.get('closed_pnl', {})
    if closed_pnl_resp and closed_pnl_resp.get('retCode') == 0:
        result = closed_pnl_resp.get('result', {})
        list_data = result.get('list', [])
        for pnl in list_data:
            closed_pnl_data.append({
                'symbol': pnl.get('symbol'),
                'order_type': pnl.get('orderType'),
                'side': pnl.get('side'),
                'qty': pnl.get('qty'),
                'entry_price': pnl.get('avgEntryPrice'),
                'exit_price': pnl.get('avgExitPrice'),
                'closed_pnl': pnl.get('closedPnl'),
                'created_time': pnl.get('createdTime'), # Timestamp in ms
                'leverage': pnl.get('leverage', '1')
            })
                
    return {
        "wallet": wallet_data,
        "positions": positions_data,
        "closed_pnl": closed_pnl_data,
        "timestamp": time.time()
    }

if __name__ == '__main__':
    print("Starting Flask server...")
    app.run(debug=True, port=5000)
