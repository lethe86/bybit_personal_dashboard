import hashlib
import hmac
import json
import time
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

# Handle environment variables
load_dotenv()

def get_env_var(key, default=None):
    """Robustly fetch environment variables."""
    # Try multiple common prefixes or exact match
    val = os.environ.get(f"BYBIT_{key}") or os.environ.get(key) or default
    return val

class SimpleBybitClient:
    def __init__(self, api_key=None, api_secret=None, testnet=None):
        self.api_key = api_key or get_env_var('API_KEY')
        self.api_secret = api_secret or get_env_var('API_SECRET')
        
        testnet_val = str(get_env_var('TESTNET', 'true')).lower()
        self.testnet = testnet if testnet is not None else (testnet_val == 'true')

        self.base_url = "https://api-testnet.bybit.com" if self.testnet else "https://api.bybit.com"
        self.session = requests.Session()
        self.recv_window = str(5000)
        self.time_offset = 0
        self.sync_time()

    def sync_time(self):
        try:
            time_url = self.base_url + "/v5/market/time"
            resp = self.session.get(time_url, timeout=5)
            if resp.status_code == 200:
                server_time = int(resp.json()['result']['timeSecond']) * 1000
                local_time = int(time.time() * 1000)
                self.time_offset = server_time - local_time
        except Exception as e:
            print(f"DEBUG: Time sync failed: {e}")

    def get_time(self):
        return int(time.time() * 1000) + self.time_offset

    def gen_signature(self, payload, timestamp):
        param_str = str(timestamp) + self.api_key + self.recv_window + payload
        hash = hmac.new(bytes(self.api_secret, "utf-8"), param_str.encode("utf-8"), hashlib.sha256)
        return hash.hexdigest()

    def _request(self, method, endpoint, params=None):
        if params is None:
            params = {}
        
        timestamp = str(self.get_time())
        # For GET request, payload is query string
        clean_params = {k: v for k, v in params.items() if v is not None}
        payload = "&".join([f"{k}={v}" for k, v in sorted(clean_params.items())])
        
        signature = self.gen_signature(payload, timestamp)
        
        headers = {
            'X-BAPI-API-KEY': self.api_key,
            'X-BAPI-SIGN': signature,
            'X-BAPI-SIGN-TYPE': '2',
            'X-BAPI-TIMESTAMP': timestamp,
            'X-BAPI-RECV-WINDOW': self.recv_window,
            'Content-Type': 'application/json'
        }
        
        url = self.base_url + endpoint + "?" + payload
        
        try:
            response = self.session.request(method, url, headers=headers, timeout=10)
            return response.json()
        except Exception as e:
            return {"retCode": -1, "retMsg": str(e)}

    def get_wallet_balance(self, accountType="UNIFIED", **kwargs):
        params = {"accountType": accountType}
        params.update(kwargs)
        return self._request("GET", "/v5/account/wallet-balance", params)

    def get_positions(self, category="linear", symbol=None, **kwargs):
        params = {"category": category}
        if symbol:
            params["symbol"] = symbol
        params.update(kwargs)
        return self._request("GET", "/v5/position/list", params)

    def get_closed_pnl(self, category="linear", limit=50, **kwargs):
        params = {"category": category, "limit": limit}
        params.update(kwargs)
        return self._request("GET", "/v5/position/closed-pnl", params)

    def get_closed_pnl_history(self):
        """Fetch closed PnL for the current month by chunking 7-day windows."""
        now_dt = datetime.now()
        # First day of current month at 00:00:00
        start_of_month = now_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        end_time = int(time.time() * 1000)
        start_time = int(start_of_month.timestamp() * 1000)
        
        all_records = []
        # Chunk 7 days (604800000 ms)
        chunk_size = 7 * 24 * 60 * 60 * 1000
        
        current_end = end_time
        
        # We iterate backwards from now until we hit the start of the month
        while current_end > start_time:
            current_start = max(start_time, current_end - chunk_size)
            
            # Fetch for this chunk
            params = {
                "category": "linear",
                "limit": 50,
                "startTime": current_start,
                "endTime": current_end
            }
            
            try:
                resp = self._request("GET", "/v5/position/closed-pnl", params)
                if resp.get('retCode') == 0:
                    records = resp.get('result', {}).get('list', [])
                    all_records.extend(records)
            except Exception as e:
                print(f"Error fetching PnL chunk: {e}")
            
            current_end = current_start # Move window back
            
        # Deduplicate
        seen_ids = set()
        unique_records = []
        for rec in all_records:
            if rec.get('orderId') not in seen_ids:
                seen_ids.add(rec.get('orderId'))
                unique_records.append(rec)
        
        unique_records.sort(key=lambda x: int(x.get('updatedTime', 0)), reverse=True)
        return {"retCode": 0, "result": {"list": unique_records}}

def get_bybit_client():
    return SimpleBybitClient()

def get_account_info():
    try:
        client = get_bybit_client()
        # Basic validation: ensure we have keys
        if not client.api_key or not client.api_secret:
            return {"error": "API Key or Secret is missing from environment variables."}

        wallet = client.get_wallet_balance(accountType="UNIFIED")
        positions = client.get_positions(category="linear", settleCoin="USDT")
        closed_pnl = client.get_closed_pnl_history()
        return {"wallet": wallet, "positions": positions, "closed_pnl": closed_pnl}
    except Exception as e:
        return {"error": str(e)}
