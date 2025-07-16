import hashlib
import hmac

def verify_telegram_auth(data: dict, bot_token: str) -> bool:
    
    check_hash = data.pop('hash', '')
    sorted_data = sorted([f"{k}={v}" for k, v in data.items()])
    data_check_string = '\n'.join(sorted_data)
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    hmac_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac_hash == check_hash

def verify_facebook_token(access_token):
    
    user_info_url = f"https://graph.facebook.com/me?fields=id,name,email,picture&access_token={access_token}"
    response = requests.get(user_info_url)
    
    if response.status_code != 200:
        return None

    return response.json()