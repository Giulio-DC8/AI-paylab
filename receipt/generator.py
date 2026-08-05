import json
import datetime
from cryptography.exceptions import InvalidSignature
from receipt.keys import load_private_key, load_public_key


def create_receipt(payment_result):
    """Creates a receipt and signs it for real with Ed25519."""
    receipt_data = {
        "receipt_id": "rcpt_" + payment_result["transaction_id"],
        "protocol": payment_result["protocol"],
        "merchant": payment_result["merchant"],
        "amount": payment_result["amount"],
        "status": payment_result["status"],
        "reason": payment_result["reason"],
        "issued_at": datetime.datetime.now().isoformat(),
    }

    payload_string = json.dumps(receipt_data, sort_keys=True)
    payload_bytes = payload_string.encode()

    private_key = load_private_key()
    signature_bytes = private_key.sign(payload_bytes)

    receipt_data["signature"] = signature_bytes.hex()
    return receipt_data


def verify_receipt(receipt):
    """Verifies the Ed25519 signature using only the public key."""
    receipt_copy = receipt.copy()
    signature_hex = receipt_copy.pop("signature")
    signature_bytes = bytes.fromhex(signature_hex)

    payload_string = json.dumps(receipt_copy, sort_keys=True)
    payload_bytes = payload_string.encode()

    public_key = load_public_key()

    try:
        public_key.verify(signature_bytes, payload_bytes)
        return True
    except InvalidSignature:
        return False