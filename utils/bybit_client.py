import hashlib
import hmac
import json
import time
import requests
import os
from datetime import datetime
from dotenv import load_dotenv

# Force load from current directory
env_path = os.path.join(os.getcwd(), '.env')
load_dotenv(env_path)

API_KEY = os.getenv('BYBIT_API_KEY') or os.getenv('API_KEY')
API_SECRET = os.getenv('BYBIT_API_SECRET') or os.getenv('API_SECRET')
TESTNET = os.getenv('BYBIT_TESTNET', 'true').lower() == 'true'





class SimpleBybitClient:
    def __init__(self, api_key, api_secret, testnet=False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.base_url = "https://api-testnet.bybit.com" if testnet else "https://api.bybit.com"
        self.session = requests.Session()
        self.recv_window = str(5000)
        self.time_offset = 0
        self.sync_time()

    def sync_time(self):
        try:
            time_url = self.base_url + "/v5/market/time"
            resp = self.session.get(time_url)
            if resp.status_code == 200:
                server_time = int(resp.json()['result']['timeSecond']) * 1000
                local_time = int(time.time() * 1000)
                self.time_offset = server_time - local_time
                print(f"DEBUG: Time synchronized. Offset: {self.time_offset}ms")
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
        url = self.base_url + endpoint + "?" + payload
        
        try:
            response = self.session.request(method, url, headers=headers)
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
        
        print(f"DEBUG: Fetching history from {start_of_month} ({start_time}) to NOW ({end_time})")
        
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
                    # Append new records
                    all_records.extend(records)
            except Exception as e:
                print(f"Error fetching PnL chunk: {e}")
            
            current_end = current_start # Move window back
            
        # Deduplicate by orderId just in case of overlap
        seen_ids = set()
        unique_records = []
        for rec in all_records:
            if rec['orderId'] not in seen_ids:
                seen_ids.add(rec['orderId'])
                unique_records.append(rec)
        
        # Sort by updatedTime descending
        unique_records.sort(key=lambda x: int(x.get('updatedTime', 0)), reverse=True)
            
        return {"retCode": 0, "result": {"list": unique_records}}

def get_bybit_client():
    return SimpleBybitClient(API_KEY, API_SECRET, TESTNET)

def get_account_info():
    try:
        client = get_bybit_client()
        wallet = client.get_wallet_balance(accountType="UNIFIED")
        positions = client.get_positions(category="linear", settleCoin="USDT") # Defaulting to USDT Linear perps
        closed_pnl = client.get_closed_pnl_history()
        return {"wallet": wallet, "positions": positions, "closed_pnl": closed_pnl}
    except Exception as e:
        print(f"Error getting account info: {e}")
        return {}
