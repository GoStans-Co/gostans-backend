import json
import uuid
import hashlib
import hmac
import base64
import requests
from datetime import datetime
from urllib.parse import urlparse
from django.conf import settings


# Your CyberSource keys (better to load from .env)

MERCHANT_ID = settings.CYBERSOURCE["MERCHANT_ID"]
KEY_ID = settings.CYBERSOURCE["API_KEY_ID"]
SECRET_KEY = settings.CYBERSOURCE["SECRET_KEY"]
CYBERSOURCE_API_BASE = settings.CYBERSOURCE_HOST
CYBERSOURCE_API_BASE = settings.CYBERSOURCE_HOST


def generate_http_signature(resource, method, payload):
    host = urlparse(CYBERSOURCE_API_BASE).netloc
    date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")
    digest = base64.b64encode(hashlib.sha256(payload.encode()).digest()).decode()
    digest_header = f"SHA-256={digest}"

    signature_string = "\n".join([
        f"host: {host}",
        f"date: {date}",
        f"(request-target): {method.lower()} {resource}",
        f"digest: {digest_header}",
        f"v-c-merchant-id: {MERCHANT_ID}"
    ])

    decoded_key = base64.b64decode(SECRET_KEY)
    signature = base64.b64encode(
        hmac.new(decoded_key, signature_string.encode(), hashlib.sha256).digest()
    ).decode()

    auth_header = (
        f'keyid="{KEY_ID}", '
        f'algorithm="HmacSHA256", '
        f'headers="host date (request-target) digest v-c-merchant-id", '
        f'signature="{signature}"'
    )

    return {
        "host": host,
        "date": date,
        "digest": digest_header,
        "signature": auth_header
    }

def process_cybersource_payment(amount, currency, card, billing):
    resource = "/pts/v2/payments"
    url = CYBERSOURCE_API_BASE + resource

    payload = {
        "clientReferenceInformation": {
            "code": f"tour-booking-{uuid.uuid4().hex[:8]}"
        },
        "paymentInformation": {
            "card": {
                "number": card["number"],
                "expirationMonth": card["exp_month"],
                "expirationYear": card["exp_year"],
                "securityCode": card["cvv"]
            }
        },
        "orderInformation": {
            "amountDetails": {
                "totalAmount": str(round(float(amount), 2)),
                "currency": currency
            },
            "billTo": {
                "firstName": billing["first_name"],
                "lastName": billing["last_name"],
                "address1": billing["address1"],
                "locality": billing["locality"],
                "administrativeArea": billing["administrative_area"],
                "postalCode": billing["postal_code"],
                "country": billing["country"],
                "email": billing["email"],
                "phoneNumber": billing["phone_number"]
            }
        }
    }

    json_payload = json.dumps(payload)
    sig_headers = generate_http_signature(resource, "POST", json_payload)

    headers = {
        "Content-Type": "application/json",
        "v-c-merchant-id": MERCHANT_ID,
        "Date": sig_headers["date"],
        "Host": sig_headers["host"],
        "Digest": sig_headers["digest"],
        "Authorization": f'Signature {sig_headers["signature"]}'
    }

    response = requests.post(url, data=json_payload, headers=headers)

    try:
        result = response.json()
    except Exception:
        return {"status": "FAILED", "error": "Invalid response from CyberSource"}

    if response.status_code == 201 and result.get("status") == "AUTHORIZED":
        return {
            "status": "COMPLETED",
            "payment_id": result.get("id"),
            "auth_code": result.get("processorInformation", {}).get("authorizationCode"),
            "gateway_response": result.get("status"),
        }
    else:
        return {
            "status": "FAILED",
            "error": result.get("message", "Payment failed"),
            "cybersource_response": result
        }
    

def save_card_profile(user, card_info, billing_info):
    resource = "/customer/v1/payment-instruments"
    url = CYBERSOURCE_API_BASE + resource

    payload = {
        "card": {
            "number": card_info["number"],
            "expirationMonth": card_info["exp_month"],
            "expirationYear": card_info["exp_year"],
            "securityCode": card_info["cvv"],
            "type": "001"  # 001 = Visa, 002 = Mastercard, etc.
        },
        "billTo": {
            "firstName": billing_info["first_name"],
            "lastName": billing_info["last_name"],
            "address1": billing_info["address1"],
            "locality": billing_info["locality"],
            "administrativeArea": billing_info["administrative_area"],
            "postalCode": billing_info["postal_code"],
            "country": billing_info["country"],
            "email": billing_info["email"],
            "phoneNumber": billing_info["phone_number"]
        }
    }

    json_payload = json.dumps(payload)
    sig_headers = generate_http_signature(resource, "POST", json_payload)

    headers = {
        "Content-Type": "application/json",
        "v-c-merchant-id": MERCHANT_ID,
        "Date": sig_headers["date"],
        "Host": sig_headers["host"],
        "Digest": sig_headers["digest"],
        "Authorization": f'Signature {sig_headers["signature"]}'
    }

    response = requests.post(url, data=json_payload, headers=headers)

    try:
        result = response.json()
    except Exception:
        return {"error": "Invalid response"}

    if response.status_code in (200, 201):
        return {
            "profile_id": str(user.id),  # or customerProfileId if you manage full profiles
            "token_id": result.get("id"),
            "card_type": result["card"]["type"],
            "last4": result["card"]["number"][-4:],
            "exp_month": result["card"]["expirationMonth"],
            "exp_year": result["card"]["expirationYear"]
        }
    else:
        return {"error": result.get("message", "Failed to tokenize card")}

