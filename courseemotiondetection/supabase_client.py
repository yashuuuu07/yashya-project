import os
import requests
from dotenv import load_dotenv

load_dotenv()

class SupabaseAuth:
    def __init__(self, url, key):
        self.url = f"{url}/auth/v1"
        self.headers = {
            "apikey": key,
            "Content-Type": "application/json"
        }

    def sign_up(self, credentials):
        response = requests.post(f"{self.url}/signup", headers=self.headers, json=credentials)
        data = response.json()
        if not response.ok:
            error_msg = data.get('msg') or data.get('error_description') or data.get('message') or data.get('error') or f"Status {response.status_code}"
            print(f"DEBUG: Signup Failed - {response.status_code}: {response.text}")
            raise Exception(error_msg)
        
        # Wrap response
        class Resp: pass
        r = Resp()
        # GoTrue /signup returns user data under 'user' key OR at top level depending on version
        user_data = data.get('user', data)
        r.user = Resp()
        r.user.id = user_data.get('id')
        r.user.email = user_data.get('email')
        return r

    def sign_in_with_password(self, credentials):
        # Many GoTrue versions prefer grant_type in the body
        payload = {
            "email": credentials.get('email'),
            "password": credentials.get('password'),
            "grant_type": "password"
        }
        # We also keep it in the query param for maximum compatibility
        response = requests.post(f"{self.url}/token?grant_type=password", headers=self.headers, json=payload)
        
        try:
            data = response.json()
        except:
            data = {}
            
        if not response.ok:
            error_msg = data.get('error_description') or data.get('error') or data.get('message') or data.get('msg') or f"Status {response.status_code}"
            print(f"DEBUG: Login Failed - {response.status_code}: {response.text}")
            raise Exception(error_msg)
        
        class Resp: pass
        r = Resp()
        r.user = Resp()
        r.user.id = data['user']['id']
        r.user.email = data['user']['email']
        r.access_token = data['access_token']
        return r

    def sign_out(self):
        return True

class SupabaseTable:
    def __init__(self, url, key, table_name, token=None):
        self.url = f"{url}/rest/v1/{table_name}"
        auth_header = f"Bearer {token}" if token else f"Bearer {key}"
        self.headers = {
            "apikey": key,
            "Authorization": auth_header,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        self.params = {}

    def select(self, columns="*"):
        self.params["select"] = columns
        return self

    def insert(self, data):
        self.data = data
        self.method = "POST"
        return self

    def upsert(self, data):
        self.data = data
        self.method = "POST"
        self.headers["Prefer"] = "resolution=merge-duplicates,return=representation"
        return self

    def update(self, data):
        self.data = data
        self.method = "PATCH"
        return self

    def delete(self):
        self.method = "DELETE"
        return self

    def eq(self, column, value):
        self.params[column] = f"eq.{value}"
        return self

    def order(self, column, desc=False):
        self.params["order"] = f"{column}.{'desc' if desc else 'asc'}"
        return self

    def limit(self, count):
        self.params["limit"] = count
        return self

    def single(self):
        self.headers["Accept"] = "application/vnd.pgrst.object+json"
        return self

    def execute(self):
        if hasattr(self, 'method'):
            if self.method == "POST":
                res = requests.post(self.url, headers=self.headers, params=self.params, json=self.data)
            elif self.method == "PATCH":
                res = requests.patch(self.url, headers=self.headers, params=self.params, json=self.data)
            elif self.method == "DELETE":
                res = requests.delete(self.url, headers=self.headers, params=self.params)
        else:
            res = requests.get(self.url, headers=self.headers, params=self.params)
        
        class Resp: pass
        r = Resp()
        try:
            r.data = res.json()
        except:
            r.data = None
            
        if res.status_code >= 400:
            raise Exception(f"DB Error: {res.text}")
        return r

class CustomSupabaseClient:
    def __init__(self, url, key):
        self.url = url
        self.key = key
        self.auth = SupabaseAuth(url, key)

    def table(self, name, token=None):
        return SupabaseTable(self.url, self.key, name, token=token)

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase = CustomSupabaseClient(url, key)

def get_supabase():
    return supabase
