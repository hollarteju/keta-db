import base64

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PublicKey,
)
import json
import secrets
from decimal import Decimal


def decode_base64(value: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except Exception as exc:
        raise ValueError(
            "Invalid base64 value"
        ) from exc


def verify_ed25519_signature(
    public_key_base64: str,
    signature_base64: str,
    message: str,
) -> bool:
    try:
        public_key_bytes = decode_base64(
            public_key_base64
        )

        signature_bytes = decode_base64(
            signature_base64
        )

        public_key = Ed25519PublicKey.from_public_bytes(
            public_key_bytes
        )

        public_key.verify(
            signature_bytes,
            message.encode("utf-8"),
        )

        return True

    except (
        ValueError,
        InvalidSignature,
    ):
        return False




def decimal_to_string(value) -> str:
    return format(
        Decimal(str(value)),
        "f",
    )


def generate_nonce() -> str:
    return base64.urlsafe_b64encode(
        secrets.token_bytes(32)
    ).decode("utf-8")


def build_withdrawal_challenge(
    *,
    challenge_id: int,
    withdrawal_id: str,
    user_id: str,
    amount,
    currency: str,
    network: str,
    destination: str,
    nonce: str,
) -> str:
    payload = {
        "version": 1,
        "type": "WITHDRAWAL",
        "challenge_id": challenge_id,
        "withdrawal_id": withdrawal_id,
        "user_id": user_id,
        "amount": decimal_to_string(amount),
        "currency": currency,
        "network": network,
        "destination": destination,
        "nonce": nonce,
    }

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )