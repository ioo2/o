# -*- coding: utf-8 -*-
import base64
import hashlib
import hmac
import json
import math
import os
import re
import time
from urllib.parse import quote,unquote
from fastapi import FastAPI,Query
from fastapi.middleware.cors import CORSMiddleware
try:
    from Crypto.Cipher import AES as _CryptoAES
except Exception:
    _CryptoAES = None
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _AESGCM
except Exception:
    _AESGCM = None
from functools import lru_cache

_SBOX = (
    0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5, 0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
    0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59, 0x47, 0xF0, 0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4, 0x72, 0xC0,
    0xB7, 0xFD, 0x93, 0x26, 0x36, 0x3F, 0xF7, 0xCC, 0x34, 0xA5, 0xE5, 0xF1, 0x71, 0xD8, 0x31, 0x15,
    0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05, 0x9A, 0x07, 0x12, 0x80, 0xE2, 0xEB, 0x27, 0xB2, 0x75,
    0x09, 0x83, 0x2C, 0x1A, 0x1B, 0x6E, 0x5A, 0xA0, 0x52, 0x3B, 0xD6, 0xB3, 0x29, 0xE3, 0x2F, 0x84,
    0x53, 0xD1, 0x00, 0xED, 0x20, 0xFC, 0xB1, 0x5B, 0x6A, 0xCB, 0xBE, 0x39, 0x4A, 0x4C, 0x58, 0xCF,
    0xD0, 0xEF, 0xAA, 0xFB, 0x43, 0x4D, 0x33, 0x85, 0x45, 0xF9, 0x02, 0x7F, 0x50, 0x3C, 0x9F, 0xA8,
    0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5, 0xBC, 0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2,
    0xCD, 0x0C, 0x13, 0xEC, 0x5F, 0x97, 0x44, 0x17, 0xC4, 0xA7, 0x7E, 0x3D, 0x64, 0x5D, 0x19, 0x73,
    0x60, 0x81, 0x4F, 0xDC, 0x22, 0x2A, 0x90, 0x88, 0x46, 0xEE, 0xB8, 0x14, 0xDE, 0x5E, 0x0B, 0xDB,
    0xE0, 0x32, 0x3A, 0x0A, 0x49, 0x06, 0x24, 0x5C, 0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79,
    0xE7, 0xC8, 0x37, 0x6D, 0x8D, 0xD5, 0x4E, 0xA9, 0x6C, 0x56, 0xF4, 0xEA, 0x65, 0x7A, 0xAE, 0x08,
    0xBA, 0x78, 0x25, 0x2E, 0x1C, 0xA6, 0xB4, 0xC6, 0xE8, 0xDD, 0x74, 0x1F, 0x4B, 0xBD, 0x8B, 0x8A,
    0x70, 0x3E, 0xB5, 0x66, 0x48, 0x03, 0xF6, 0x0E, 0x61, 0x35, 0x57, 0xB9, 0x86, 0xC1, 0x1D, 0x9E,
    0xE1, 0xF8, 0x98, 0x11, 0x69, 0xD9, 0x8E, 0x94, 0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF,
    0x8C, 0xA1, 0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68, 0x41, 0x99, 0x2D, 0x0F, 0xB0, 0x54, 0xBB, 0x16,
)
_RCON = (0x00, 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36)

@lru_cache(maxsize=8)
def _aes_round_keys(key):
    words = [int.from_bytes(key[i:i + 4], "big") for i in range(0, 16, 4)]
    for index in range(4, 44):
        value = words[index - 1]
        if index % 4 == 0:
            value = ((value << 8) & 0xFFFFFFFF) | (value >> 24)
            value = sum(_SBOX[(value >> shift) & 0xFF] << shift for shift in (24, 16, 8, 0))
            value ^= _RCON[index // 4] << 24
        words.append(words[index - 4] ^ value)
    return tuple(b"".join(words[round_index * 4 + i].to_bytes(4, "big") for i in range(4)) for round_index in range(11))

def _xtime(value):
    return ((value << 1) ^ (0x11B if value & 0x80 else 0)) & 0xFF

def _aes_block(key, block):
    keys = _aes_round_keys(key)
    state = [value ^ keys[0][index] for index, value in enumerate(block)]
    for round_index in range(1, 11):
        state = [_SBOX[value] for value in state]
        state = [state[4 * ((column + row) % 4) + row] for column in range(4) for row in range(4)]
        if round_index < 10:
            mixed = []
            for column in range(4):
                a0, a1, a2, a3 = state[column * 4:column * 4 + 4]
                mixed.extend((
                    _xtime(a0) ^ (_xtime(a1) ^ a1) ^ a2 ^ a3,
                    a0 ^ _xtime(a1) ^ (_xtime(a2) ^ a2) ^ a3,
                    a0 ^ a1 ^ _xtime(a2) ^ (_xtime(a3) ^ a3),
                    (_xtime(a0) ^ a0) ^ a1 ^ a2 ^ _xtime(a3),
                ))
            state = mixed
        state = [value ^ keys[round_index][index] for index, value in enumerate(state)]
    return bytes(state)

def _gf_mul(left, right):
    result, value = 0, right
    for index in range(128):
        if left & (1 << (127 - index)):
            result ^= value
        value = (value >> 1) ^ (0xE1000000000000000000000000000000 if value & 1 else 0)
    return result

def _ghash(key_hash, aad, data):
    value = 0
    payload = aad + b"\0" * (-len(aad) % 16) + data + b"\0" * (-len(data) % 16)
    payload += (len(aad) * 8).to_bytes(8, "big") + (len(data) * 8).to_bytes(8, "big")
    for offset in range(0, len(payload), 16):
        value = _gf_mul(value ^ int.from_bytes(payload[offset:offset + 16], "big"), key_hash)
    return value.to_bytes(16, "big")

def _ctr_crypt(key, nonce, data):
    counter = bytearray(nonce + b"\0\0\0\1")
    output = bytearray()
    for offset in range(0, len(data), 16):
        number = (int.from_bytes(counter[12:], "big") + 1) & 0xFFFFFFFF
        counter[12:] = number.to_bytes(4, "big")
        stream = _aes_block(key, bytes(counter))
        output.extend(a ^ b for a, b in zip(data[offset:offset + 16], stream))
    return bytes(output)

def _pure_gcm_encrypt(key, nonce, data, aad):
    encrypted = _ctr_crypt(key, nonce, data)
    key_hash = int.from_bytes(_aes_block(key, b"\0" * 16), "big")
    tag = bytes(a ^ b for a, b in zip(_aes_block(key, nonce + b"\0\0\0\1"), _ghash(key_hash, aad, encrypted)))
    return encrypted + tag

def _pure_gcm_decrypt(key, nonce, data, aad):
    encrypted, tag = data[:-16], data[-16:]
    key_hash = int.from_bytes(_aes_block(key, b"\0" * 16), "big")
    expected = bytes(a ^ b for a, b in zip(_aes_block(key, nonce + b"\0\0\0\1"), _ghash(key_hash, aad, encrypted)))
    if not hmac.compare_digest(tag, expected):
        raise ValueError("Invalid GCM tag")
    return _ctr_crypt(key, nonce, encrypted)

def _gcm_encrypt(key, data, aad=b""):
    nonce = os.urandom(12)
    if _CryptoAES is not None:
        cipher = _CryptoAES.new(key, _CryptoAES.MODE_GCM, nonce=nonce, mac_len=16)
        cipher.update(aad)
        encrypted, tag = cipher.encrypt_and_digest(data)
        return nonce + encrypted + tag
    if _AESGCM is not None:
        return nonce + _AESGCM(key).encrypt(nonce, data, aad)
    return nonce + _pure_gcm_encrypt(key, nonce, data, aad)

def _gcm_decrypt(key, payload, aad=b""):
    if len(payload) <= 28:
        raise ValueError("Invalid encrypted payload")
    nonce, data = payload[:12], payload[12:]
    if _CryptoAES is not None:
        cipher = _CryptoAES.new(key, _CryptoAES.MODE_GCM, nonce=nonce, mac_len=16)
        cipher.update(aad)
        return cipher.decrypt_and_verify(data[:-16], data[-16:])
    if _AESGCM is not None:
        return _AESGCM(key).decrypt(nonce, data, aad)
    return _pure_gcm_decrypt(key, nonce, data, aad)

app = FastAPI()
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])

resolve_key = b"Y8rQ3mV1sT5kL9xZ"
ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"

def _valid_play(data, encoded=False):
    if not isinstance(data, dict):
        return None
    url = str(data.get("url", "")).strip()
    if not re.match(r"https?://", url, re.I):
        return None
    if encoded:
        try:
            timestamp = float(data.get("ts"))
            timestamp = timestamp / 1000 if timestamp > 1000000000000 else timestamp
            if abs(time.time() - timestamp) > 60:
                return None
        except Exception:
            return None
    match = re.search(r"[?&]x-expires=(\d+)", url, re.I)
    if match and int(match.group(1)) <= int(time.time()) + 10:
        return None
    headers = {}
    for key in ("header", "headers", "Header", "useHeaders", "use_headers"):
        value = data.get(key) if isinstance(data, dict) else None
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                value = None
        if isinstance(value, dict):
            headers = {str(n):str(c) for n,c in value.items() if str(n).strip() and str(c).strip()}
            break
    if not headers:
        headers={"User-Agent":ua}
    return {"url":url,"header":headers}

def _local_resolve(token):
    try:
        payload = token.replace("-", "+").replace("_", "/")
        payload += "=" * (-len(payload) % 4)
        plain = _gcm_decrypt(resolve_key, base64.b64decode(payload), b"").decode("utf-8").strip()
        if re.match(r"https?://", plain, re.I):
            return {"url":plain,"header":{"User-Agent":ua}}
        return _valid_play(json.loads(plain))
    except Exception:
        return None

@app.get("/resolve")
async def resolve(token:str=Query("")):
    token = unquote(token)
    if not token:
        return {"url":"","header":{}}
    ret = _local_resolve(token)
    if ret:
        return ret
    return {"url":"","header":{}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app,host="127.0.0.1",port=8000)
