import base64
import os
from Crypto.Cipher import DES3

def encrypt_field(value: str) -> str:
    key = os.getenv("FLW_ENCRYPTION_KEY").encode()
    block_size = 8
    pad_diff = block_size - (len(value) % block_size)
    padded = value + (chr(pad_diff) * pad_diff)
    cipher = DES3.new(key, DES3.MODE_ECB)
    encrypted = cipher.encrypt(padded.encode())
    return base64.b64encode(encrypted).decode()
