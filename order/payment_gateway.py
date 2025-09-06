import json
import base64
import hashlib

import requests
from urllib.parse import urlparse
from django.conf import settings

from email.utils import formatdate
from datetime import datetime, timedelta
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend


MERCHANT_ID = settings.CYBERSOURCE["MERCHANT_ID"]
KEY_ID = settings.CYBERSOURCE["API_KEY_ID"]
PRIVATE_KEY_PATH = settings.CYBERSOURCE["PRIVATE_KEY_PATH"]
CYBERSOURCE_API_BASE = "https://apitest.cybersource.com/pts/v2/payments"


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

# -----------------------------
# Generate JWT for CyberSource
# -----------------------------

def generate_cybersource_jwt(payload: dict) -> str:
    """Generate JWT for CyberSource REST API using message body digest."""
    # 1 Load private key
    with open(PRIVATE_KEY_PATH, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(),
            password=None,
            backend=default_backend()
        )

    # 2 Hash the request body (digest)
    payload_json = json.dumps(payload, separators=(",", ":"))
    digest_bytes = hashlib.sha256(payload_json.encode("utf-8")).digest()
    digest_b64 = base64.b64encode(digest_bytes).decode("utf-8")
    digest_value = f"SHA-256={digest_b64}"

    # 3 JWT claim set / payload
    claim_set = {
        "iat": formatdate(timeval=None, localtime=False, usegmt=True),  # RFC1123
        "digest": digest_value,
        "digestAlgorithm": "SHA-256"
    }

    # JWT header
    jwt_header = {
        "alg": "RS256",
        "kid": KEY_ID,
        "v-c-merchant-id": MERCHANT_ID
    }

    # 5️⃣ Base64 encode header & payload
    header_b64 = base64url_encode(json.dumps(jwt_header, separators=(",", ":")).encode())
    payload_b64 = base64url_encode(json.dumps(claim_set, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    # 6️⃣ Sign JWT
    signature = private_key.sign(
        signing_input,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    signature_b64 = base64url_encode(signature)

    # 7️⃣ Return full JWT
    return f"{header_b64}.{payload_b64}.{signature_b64}"

def generate_manual_jwt():
    private_key_path = PRIVATE_KEY_PATH
    key_id = KEY_ID
    merchant_id = MERCHANT_ID

    with open(private_key_path, "rb") as key_file:
        private_key = serialization.load_pem_private_key(
            key_file.read(), password=None, backend=default_backend()
        )

    payload = {
        "name": "gostans booking",
        "iat": formatdate(timeval=None, localtime=False, usegmt=True),  # RFC1123 date
        "sub": merchant_id,
        "iss": merchant_id,
        "aud": "apitest.cybersource.com",
    }
    

    headers = {
        "alg": "RS256",
        "typ": "JWT",
 "x5c": ["MIICaTCCAdKgAwIBAgIWMTc1NDA1MTE5NzMwNzAyNDA3NjQ1NTANBgkqhkiG9w0BAQsFADAeMRwwGgYDVQQDDBNDeWJlclNvdXJjZUNlcnRBdXRoMB4XDTI1MDgwMTEyMjYzN1oXDTI4MDgwMTEyMjYzN1owPjEbMBkGA1UEAwwSZ29zdGFuc18xNzUxODgxODM0MR8wHQYDVQQFExYxNzU0MDUxMTk3MzA3MDI0MDc2NDU1MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAigVwJpThkOrSOsfqgquZdkkcQKnROEPvY+s2IE+/Z1V/32QYVxtj4E3RzL+zw0swEJFev6w2PT220x1acarnBYV2O0lZZLv91IxAajo/CHnQjqHHT4GrP1g6Z7/2LqcQ1//Z47/trLJjXsuMMGJURldMaAR1QJvBvo1L7WDy3hfHh0ysM/tjWmi4aflqjXdftikzEHEMjedvjSxoBt9nAEui6gsYDMfRiIdUwlsVKW2MEfw1phUIXC79fqtAZg01gBqx/YO4p+gtXhba/s/yq3unpA+kLnu66rrHNl837Z4u6j7TOEVEQqJnNcZSh+EBsWTRFh6MRLejHSeFiMXq4QIDAQABMA0GCSqGSIb3DQEBCwUAA4GBAANzQz4O0CB85RWDRVVm+C0U+yM8klovFoLceVLaAt3XvEJlbFKMAXTk+pUyaVQ+wTTm3sbpzrIyyNU6ZVMSssiyRzapGdz5OihEV0Grd30YzUbqJu7hndqV4JDhmR+zTrNkx67iQEbkdwZJYJhz4forcG985+h/z7jieKYyLypQ"],
        "kid": KEY_ID,
    }

    header_b64 = base64url_encode(json.dumps(headers, separators=(",", ":")).encode())
    payload_b64 = base64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    signature = private_key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    signature_b64 = base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"



def process_cybersource_payment(amount, currency, billing):
    resource = "/pts/v2/payments"
    url = CYBERSOURCE_API_BASE 
    # jwt_token = generate_manual_jwt()

    payload ={
        "clientReferenceInformation": {
            "code": "TC50171_3"
        },
        "paymentInformation": {
            "card": {
            "number": "4111111111111111",
            "expirationMonth": "12",
            "expirationYear": "2031",
            "securityCode": "123"
            }
        },
        "orderInformation": {
            "amountDetails": {
            "totalAmount": "102.81",
            "currency": "USD"
            },
            "billTo": {
            "firstName": "John",
            "lastName": "Doe",
            "address1": "1 Market St",
            "locality": "san francisco",
            "administrativeArea": "CA",
            "postalCode": "94105",
            "country": "US",
            "email": "test@cybs.com",
            "phoneNumber": "4158880000"
            }
        }
    }
    

    json_payload = json.dumps(payload)
    jwt_token = generate_cybersource_jwt(json_payload)
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "v-c-merchant-id": MERCHANT_ID,
        "Content-Type": "application/json",
        "Host": "apitest.cybersource.com"
    }


    print("🔐 Headers:", headers)
    print("📤 Payload:", json_payload)
    print("👉 URL:", url)
 
    response = requests.post(url, data=json_payload, headers=headers)

    print("🔁 Raw response from CyberSource:", response.status_code, response.text)
    print("📡 v-c-correlation-id:", response.headers.get("v-c-correlation-id"))
    
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
            "cybersource_response": result,
        }
    

