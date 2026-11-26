
import base64
import json
import random
import re
import time
import requests
from urllib.parse import quote

from base.spider import Spider as BaseSpider

TIP_HOSTS = ["k5p0vw2fgfvc.xyz", "p9nwmo3jdquv.xyz", "93l9cunfmoc1.xyz", "y9ao7140l9ui.xyz", "ak8ib5fyxtww.xyz", "agnuprlu6fhz.xyz", "5idytkrilig6.xyz", "6rl8a5qg0y7m.xyz", "mr5qvcc0k438.xyz", "1cjvr80fr3f7.xyz"]
API_FALLBACK = "https://api.my1ffbvkv8mjf6q9.top/"
API_KEYS = ["6eIZ4cxM5pqzUXcF", "84UZNK33cSVylz6Y", "jeSWRcTwHyAKwJDB", "i1hvJx9vuRt5zEBS", "1Yy1KOa75R7cnmkg", "4MVTQQAJlMpUIAiL", "T0RVp7KIPamrtQ33", "8HbPxhX6fjhhhwok", "ugvseZc5Kkj8ecmV", "G7i3OPcfNhBnAYpc"]
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
CONFIG_KEYS = "picBaseUrl,newPicBaseUrl,newH5ImageSecret,playLines,chatDomain,heartBeatTime,registerVerify,goldProductTipTitle,goldProductTip,withdrawalGameNeedSms,uploadUrl,pc_play_line,h5_play_line,mp4Domain,maxVideoSize,maxImgSize,userUploadRule,reportReason,collectionTip,collection,invitation_reward_message,play_ads_show_times,chatUploadUrl,chatUrlPrefix,user_level_logo,actpoint_groups,actpoint_intro,uploadLogBaseUrl,officialUrl"
EXCLUDED_GROUPS = [3, 15, 26]
PAGE_SIZE = 10
DEFAULT_HOST = "https://xx9.com"
BLOCK_MSG = "主播视频接口请求失败，请稍后重试"
BRAND_ACTOR = " "
BRAND_DIRECTOR = " "
BRAND_GROUP = " "
BRAND_LINE = " "
TG_LINK = "TG群：https://t.me/tvshare23"
CLASSES = [
    ("7", "街拍街顶"), ("5", "网红主播"),("12", "偷拍自拍"), ("41", "绿帽偷情"), ("2", "原创大厂"),
    ("8", "强奸迷奸"), ("9", "OL丝袜"),  ("10", "乱伦人妻"),
    ("4", "sm女王"), ("6", "女同男同"), ("11", "其他分类"),
    ("40", "日韩女优大厂"), ("14", "日韩强奸迷奸"), ("16", "日韩群交喷射"), ("17", "日韩偷拍街拍"),
    ("13", "日韩OL人妻"), ("22", "日韩肛交sm"), ("20", "日韩网红主播"), ("19", "日韩同性乐园"),
    ("18", "日韩其他分类"), ("23", "日韩无码经典"), ("24", "日韩中文字幕"),
    ("29", "欧美大厂剧情"), ("42", "欧美素人网红"), ("28", "欧美sm虐待"), ("30", "欧美巨乳熟女"),
    ("43", "欧美肛交口交"), ("27", "欧美群交混战"), ("44", "欧美绿帽偷情"), ("33", "欧美偷拍街拍"),
    ("32", "欧美同性乐园"), ("45", "欧美黑屌爆操"), ("50", "欧美强奸野战"),
    ("37", "动漫3D"), ("35", "动漫无码"), ("34", "动漫有码"), ("36", "动漫字幕"),
    ("25", "经典三级片"), ("38", "天堂东南亚"), ("39", "印巴裔阿拉伯斯拉夫"), ("52", "ai短剧"),
]
def _sort_filter():
    return {"key": "sortType", "name": "排序", "init": "2", "value": [{"n": "最新发布", "v": "2"}, {"n": "最多播放", "v": "3"}]}

_AES_SBOX = (
    0x63,0x7c,0x77,0x7b,0xf2,0x6b,0x6f,0xc5,0x30,0x01,0x67,0x2b,0xfe,0xd7,0xab,0x76,
    0xca,0x82,0xc9,0x7d,0xfa,0x59,0x47,0xf0,0xad,0xd4,0xa2,0xaf,0x9c,0xa4,0x72,0xc0,
    0xb7,0xfd,0x93,0x26,0x36,0x3f,0xf7,0xcc,0x34,0xa5,0xe5,0xf1,0x71,0xd8,0x31,0x15,
    0x04,0xc7,0x23,0xc3,0x18,0x96,0x05,0x9a,0x07,0x12,0x80,0xe2,0xeb,0x27,0xb2,0x75,
    0x09,0x83,0x2c,0x1a,0x1b,0x6e,0x5a,0xa0,0x52,0x3b,0xd6,0xb3,0x29,0xe3,0x2f,0x84,
    0x53,0xd1,0x00,0xed,0x20,0xfc,0xb1,0x5b,0x6a,0xcb,0xbe,0x39,0x4a,0x4c,0x58,0xcf,
    0xd0,0xef,0xaa,0xfb,0x43,0x4d,0x33,0x85,0x45,0xf9,0x02,0x7f,0x50,0x3c,0x9f,0xa8,
    0x51,0xa3,0x40,0x8f,0x92,0x9d,0x38,0xf5,0xbc,0xb6,0xda,0x21,0x10,0xff,0xf3,0xd2,
    0xcd,0x0c,0x13,0xec,0x5f,0x97,0x44,0x17,0xc4,0xa7,0x7e,0x3d,0x64,0x5d,0x19,0x73,
    0x60,0x81,0x4f,0xdc,0x22,0x2a,0x90,0x88,0x46,0xee,0xb8,0x14,0xde,0x5e,0x0b,0xdb,
    0xe0,0x32,0x3a,0x0a,0x49,0x06,0x24,0x5c,0xc2,0xd3,0xac,0x62,0x91,0x95,0xe4,0x79,
    0xe7,0xc8,0x37,0x6d,0x8d,0xd5,0x4e,0xa9,0x6c,0x56,0xf4,0xea,0x65,0x7a,0xae,0x08,
    0xba,0x78,0x25,0x2e,0x1c,0xa6,0xb4,0xc6,0xe8,0xdd,0x74,0x1f,0x4b,0xbd,0x8b,0x8a,
    0x70,0x3e,0xb5,0x66,0x48,0x03,0xf6,0x0e,0x61,0x35,0x57,0xb9,0x86,0xc1,0x1d,0x9e,
    0xe1,0xf8,0x98,0x11,0x69,0xd9,0x8e,0x94,0x9b,0x1e,0x87,0xe9,0xce,0x55,0x28,0xdf,
    0x8c,0xa1,0x89,0x0d,0xbf,0xe6,0x42,0x68,0x41,0x99,0x2d,0x0f,0xb0,0x54,0xbb,0x16
)
_AES_INV_SBOX = [0] * 256
for _i, _v in enumerate(_AES_SBOX):
    _AES_INV_SBOX[_v] = _i
_AES_INV_SBOX = tuple(_AES_INV_SBOX)
_AES_RCON = (0x01,0x02,0x04,0x08,0x10,0x20,0x40,0x80,0x1b,0x36)


def _aes_xtime(a):
    return (((a << 1) ^ 0x1b) & 0xff) if (a & 0x80) else ((a << 1) & 0xff)


def _aes_gmul(a, b):
    p = 0
    while b:
        if b & 1:
            p ^= a
        a = _aes_xtime(a)
        b >>= 1
    return p


_AES_M02 = tuple(_aes_gmul(i, 0x02) for i in range(256))
_AES_M03 = tuple(_aes_gmul(i, 0x03) for i in range(256))
_AES_M09 = tuple(_aes_gmul(i, 0x09) for i in range(256))
_AES_M0B = tuple(_aes_gmul(i, 0x0b) for i in range(256))
_AES_M0D = tuple(_aes_gmul(i, 0x0d) for i in range(256))
_AES_M0E = tuple(_aes_gmul(i, 0x0e) for i in range(256))
_AES_SHIFT = (0,5,10,15,4,9,14,3,8,13,2,7,12,1,6,11)
_AES_INV_SHIFT = (0,13,10,7,4,1,14,11,8,5,2,15,12,9,6,3)


def _aes_expand_key(key):
    ek = list(key)
    for i in range(10):
        t = ek[-4:]
        t = t[1:] + t[:1]
        t = [_AES_SBOX[b] for b in t]
        t[0] ^= _AES_RCON[i]
        for _j in range(4):
            t = [t[k] ^ ek[-16 + k] for k in range(4)]
            ek += t
    return [ek[i:i + 16] for i in range(0, 176, 16)]


def _aes_encrypt_block(blk, rk):
    s = [a ^ b for a, b in zip(blk, rk[0])]
    for r in range(1, 10):
        s = [_AES_SBOX[b] for b in s]
        s = [s[_AES_SHIFT[i]] for i in range(16)]
        o = [0] * 16
        for c in range(4):
            a0, a1, a2, a3 = s[c * 4], s[c * 4 + 1], s[c * 4 + 2], s[c * 4 + 3]
            o[c * 4] = _AES_M02[a0] ^ _AES_M03[a1] ^ a2 ^ a3
            o[c * 4 + 1] = a0 ^ _AES_M02[a1] ^ _AES_M03[a2] ^ a3
            o[c * 4 + 2] = a0 ^ a1 ^ _AES_M02[a2] ^ _AES_M03[a3]
            o[c * 4 + 3] = _AES_M03[a0] ^ a1 ^ a2 ^ _AES_M02[a3]
        s = o
        s = [a ^ b for a, b in zip(s, rk[r])]
    s = [_AES_SBOX[b] for b in s]
    s = [s[_AES_SHIFT[i]] for i in range(16)]
    return bytes(a ^ b for a, b in zip(s, rk[10]))


def _aes_decrypt_block(blk, rk):
    s = [a ^ b for a, b in zip(blk, rk[10])]
    for r in range(9, 0, -1):
        s = [s[_AES_INV_SHIFT[i]] for i in range(16)]
        s = [_AES_INV_SBOX[b] for b in s]
        s = [a ^ b for a, b in zip(s, rk[r])]
        o = [0] * 16
        for c in range(4):
            a0, a1, a2, a3 = s[c * 4], s[c * 4 + 1], s[c * 4 + 2], s[c * 4 + 3]
            o[c * 4] = _AES_M0E[a0] ^ _AES_M0B[a1] ^ _AES_M0D[a2] ^ _AES_M09[a3]
            o[c * 4 + 1] = _AES_M09[a0] ^ _AES_M0E[a1] ^ _AES_M0B[a2] ^ _AES_M0D[a3]
            o[c * 4 + 2] = _AES_M0D[a0] ^ _AES_M09[a1] ^ _AES_M0E[a2] ^ _AES_M0B[a3]
            o[c * 4 + 3] = _AES_M0B[a0] ^ _AES_M0D[a1] ^ _AES_M09[a2] ^ _AES_M0E[a3]
        s = o
    s = [s[_AES_INV_SHIFT[i]] for i in range(16)]
    s = [_AES_INV_SBOX[b] for b in s]
    return bytes(a ^ b for a, b in zip(s, rk[0]))


def _aes_ecb_encrypt(key, plain):
    pad = 16 - (len(plain) % 16)
    data = plain + bytes([pad]) * pad
    rk = _aes_expand_key(key)
    out = bytearray()
    for i in range(0, len(data), 16):
        out += _aes_encrypt_block(data[i:i + 16], rk)
    return bytes(out)


def _aes_ecb_decrypt(key, cipher):
    if len(cipher) % 16 != 0:
        raise ValueError("ciphertext length must be a multiple of 16")
    rk = _aes_expand_key(key)
    out = bytearray()
    for i in range(0, len(cipher), 16):
        out += _aes_decrypt_block(cipher[i:i + 16], rk)
    if not out:
        raise ValueError("empty plaintext")
    pad = out[-1]
    if pad < 1 or pad > 16 or bytes(out[-pad:]) != bytes([pad]) * pad:
        raise ValueError("bad padding")
    return bytes(out[:-pad])


def _rand_str(n):
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    return "".join(random.choice(chars) for _ in range(n))


def _collapse_title(t):
    s = "" if t is None else str(t)
    s = re.sub(r"\s*\n\s*", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _fmt_duration(sec):
    try:
        sec = int(sec or 0)
    except Exception:
        sec = 0
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    if h > 0:
        return "%d:%02d:%02d" % (h, m, s)
    return "%02d:%02d" % (m, s)


def _fmt_views(n):
    try:
        n = int(n or 0)
    except Exception:
        n = 0
    if n >= 10000:
        w = (n // 100) / 100.0
        return "%s万次播放" % (("%.2f" % w).rstrip("0").rstrip("."))
    return "%d次播放" % n


def _format_remarks(card):
    return " | %s | %s" % (_fmt_duration(card.get("vodDuration")), _fmt_views(card.get("readNumber")))


def _clean_tags(tags):
    if not isinstance(tags, list):
        return []
    return [t for t in tags if isinstance(t, str) and t]


def _clean_name(value):
    return str(value or "").replace("$", "＄").replace("#", "＃").strip()


def _jwt_exp_ms(token):
    try:
        parts = str(token).split(".")
        if len(parts) < 2:
            return 0
        b64 = parts[1].replace("-", "+").replace("_", "/")
        b64 = b64 + "=" * (-len(b64) % 4)
        obj = json.loads(base64.b64decode(b64).decode("utf-8", "ignore"))
        return int(obj.get("exp") or 0) * 1000
    except Exception:
        return 0


class Spider(BaseSpider):
    def __init__(self):
        self.host = DEFAULT_HOST
        self._session = requests.Session()
        self._cache = {}
        self._imgcache = {}

    def init(self, extend=""):
        cfg = extend
        if isinstance(cfg, str) and cfg:
            try:
                cfg = json.loads(cfg)
            except Exception:
                cfg = None
        if isinstance(cfg, dict):
            host = cfg.get("host")
            if host:
                host = ("%s" % host).strip()
                if host.startswith("http"):
                    self.host = host.rstrip("/")

    def getName(self):
        return "主播视频"

    def isVideoFormat(self, url):
        u = url or ""
        return (".m3u8" in u) or (".mp4" in u)

    def manualVideoCheck(self):
        return False

    def _cache_get(self, key):
        item = self._cache.get(key)
        if not item:
            return None
        value, until = item
        if int(time.time() * 1000) > until:
            return None
        return value

    def _cache_set(self, key, value, ttl_ms):
        self._cache[key] = (value, int(time.time() * 1000) + int(ttl_ms))

    def _cache_del(self, key):
        self._cache.pop(key, None)

    def _request(self, method, url, data=None, headers=None, timeout=8):
        h = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}
        if headers:
            h.update(headers)
        resp = self._session.request(method, url, data=data, headers=h, timeout=timeout)
        resp.raise_for_status()
        return resp.content

    def _discover_api_base(self):
        cached = self._cache_get("xx9_api")
        if cached and cached.get("bases"):
            return cached
        bases = None
        for host in TIP_HOSTS:
            try:
                raw = self._request("GET", "https://" + host + "/zbtip.txt", timeout=3)
                body = json.loads(raw.decode("utf-8", "ignore"))
                if isinstance(body, dict) and body.get("status") == "success" and body.get("result"):
                    pool = [body["result"]]
                    if body.get("pool"):
                        for p in str(body["pool"]).split(","):
                            p = p.strip()
                            if p and p not in pool:
                                pool.append(p)
                    bases = pool
                    break
            except Exception:
                continue
        if not bases:
            bases = [API_FALLBACK]
        value = {"bases": bases, "idx": 0}
        self._cache_set("xx9_api", value, 12 * 3600 * 1000)
        return value

    def _api_call_raw(self, method, uri, key, payload, headers=None, api_base=None):
        api = api_base or self._discover_api_base()
        bases = api["bases"]
        last_err = None
        for attempt in range(len(bases)):
            base = bases[(api["idx"] + attempt) % len(bases)]
            now = int(time.time() * 1000)
            inner = {"method": 1 if method == "get" else 2, "uri": uri}
            inner[key] = None if payload is None else payload
            key_str = API_KEYS[now % 10]
            enc = base64.b64encode(_aes_ecb_encrypt(key_str.encode("utf-8"), json.dumps(inner, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))).decode("utf-8")
            try:
                raw = self._request("POST", base + "fast-endecode/main/request", data=json.dumps({"data": enc, "time": now}, separators=(",", ":")).encode("utf-8"), headers=dict({"Content-Type": "application/json"}, **(headers or {})), timeout=8)
                env = json.loads(raw.decode("utf-8", "ignore"))
                if not isinstance(env, dict) or not env.get("data") or not isinstance(env.get("time"), int):
                    raise ValueError("接口返回异常")
                plain = _aes_ecb_decrypt(API_KEYS[env["time"] % 10].encode("utf-8"), base64.b64decode(env["data"]))
                return json.loads(plain.decode("utf-8"))
            except Exception as e:
                last_err = e
                if attempt == 0 and len(bases) > 1:
                    api["idx"] = (api["idx"] + 1) % len(bases)
                    self._cache_set("xx9_api", api, 12 * 3600 * 1000)
        raise last_err or ValueError("网络请求失败")

    def _ensure_auth(self):
        jwt = self._cache_get("xx9_jwt")
        now = int(time.time() * 1000)
        if not jwt or not jwt.get("token") or (jwt.get("expMs") and now > jwt["expMs"] - 60000):
            res = self._api_call_raw("get", "app/jwt-token", "params", None, None)
            if not isinstance(res, dict) or res.get("code") != "0000" or not isinstance(res.get("result"), str):
                raise ValueError("获取 JwtToken 失败，请稍后重试")
            jwt = {"token": res["result"], "expMs": _jwt_exp_ms(res["result"]) or (now + 20 * 3600 * 1000)}
            self._cache_set("xx9_jwt", jwt, 20 * 3600 * 1000)
        guest = self._cache_get("xx9_guest")
        if not guest or not guest.get("accessToken"):
            if not guest or not guest.get("sign"):
                guest = {"sign": _rand_str(32)}
            reg = self._api_call_raw("post", "user/register/free", "body", {
                "channelCode": "", "key": "", "osType": "h5", "sign": guest["sign"],
                "machineCode": "safari", "version": "xx9.com", "domain": "", "verifyCode": "", "uuid": ""
            }, {"jwtToken": jwt["token"]})
            if not isinstance(reg, dict) or reg.get("code") != "0000" or not isinstance(reg.get("result"), dict) or not reg["result"].get("accessToken"):
                raise ValueError("游客注册失败，请稍后重试")
            guest["accessToken"] = reg["result"]["accessToken"]
            guest["id"] = reg["result"].get("id")
            self._cache_set("xx9_guest", guest, 30 * 24 * 3600 * 1000)
        return {"jwtToken": jwt["token"], "accessToken": guest["accessToken"]}

    def _api_call(self, method, uri, key, payload):
        auth = self._ensure_auth()
        headers = {"jwtToken": auth["jwtToken"], "accessToken": auth["accessToken"]}
        res = self._api_call_raw(method, uri, key, payload, headers)
        if isinstance(res, dict) and res.get("code") in ("1033", "1034"):
            self._cache_del("xx9_jwt")
            auth = self._ensure_auth()
            headers = {"jwtToken": auth["jwtToken"], "accessToken": auth["accessToken"]}
            res = self._api_call_raw(method, uri, key, payload, headers)
        elif isinstance(res, dict) and res.get("code") in ("1032", "1019"):
            self._cache_del("xx9_guest")
            auth = self._ensure_auth()
            headers = {"jwtToken": auth["jwtToken"], "accessToken": auth["accessToken"]}
            res = self._api_call_raw(method, uri, key, payload, headers)
        return res

    def _get_config(self):
        cached = self._cache_get("xx9_config")
        if cached and cached.get("picBaseUrl") and cached.get("h5PlayLines"):
            return cached
        res = self._api_call("get", "config/query", "params", {"groupKey": "APP", "key": CONFIG_KEYS})
        if not isinstance(res, dict) or res.get("code") != "0000" or not isinstance(res.get("result"), dict):
            raise ValueError("获取站点配置失败，请稍后重试")
        r = res["result"]
        try:
            h5 = json.loads(r.get("h5_play_line") or "[]")
        except Exception:
            h5 = []
        if not isinstance(h5, list):
            h5 = []
        cfg = {
            "picBaseUrl": r.get("picBaseUrl") or r.get("newPicBaseUrl") or "",
            "newH5ImageSecret": str(r.get("newH5ImageSecret") or "0"),
            "h5PlayLines": [x for x in h5 if isinstance(x, dict) and x.get("line") and x.get("name") != "海线1"],
            "mp4Domain": r.get("mp4Domain") or "",
        }
        if not cfg["picBaseUrl"] or not cfg["h5PlayLines"]:
            raise ValueError("站点配置不完整，请稍后重试")
        self._cache_set("xx9_config", cfg, 6 * 3600 * 1000)
        return cfg

    def _search_params(self, group_id, group_ids, keyword, page, sort_type):
        params = {"groupId": group_id, "keyword": keyword, "keywordType": 1, "page": page, "pageSize": PAGE_SIZE, "sortType": sort_type, "explore": False}
        if group_ids is not None:
            params["groupIds"] = group_ids
        return params

    def _do_search(self, params):
        cfg = self._get_config()
        res = self._api_call("post", "cms/vod/search", "params", params)
        if not isinstance(res, dict) or res.get("code") != "0000":
            raise ValueError((res.get("message") if isinstance(res, dict) else "") or "搜索失败，请稍后重试")
        data = res.get("data") if isinstance(res.get("data"), list) else []
        total = res.get("total") if isinstance(res.get("total"), int) else len(data)
        return {"cfg": cfg, "data": data, "total": total}

    def _fetch_detail(self, vod_id):
        res = self._api_call("get", "cms/vod/detail/" + str(vod_id), "params", {"needCdnAuth": True})
        if not isinstance(res, dict):
            raise ValueError("详情请求失败，请稍后重试")
        if res.get("code") != "0000":
            raise ValueError(res.get("message") or "服务器开小差了")
        result = res.get("result")
        if not isinstance(result, dict) or not isinstance(result.get("vod"), dict) or not result["vod"].get("title"):
            return None
        return result

    def _pic(self, remote, pic_base=""):
        if not remote:
            return ""
        if remote.startswith("http"):
            url = remote
        else:
            base = pic_base
            if not base:
                try:
                    base = self._get_config().get("picBaseUrl") or ""
                except Exception:
                    base = ""
            url = (base + ("" if remote.startswith("/") else "/") + remote) if base else remote
        try:
            proxy = self.getProxyUrl()
        except Exception:
            proxy = ""
        if proxy:
            return "%s&img=%s" % (proxy, quote(url, safe=""))
        return url

    def _card(self, card, pic_base):
        vod_id = str(card.get("id"))
        return {
            "vod_id": "vod/" + vod_id,
            "vod_name": _collapse_title(card.get("title")),
            "vod_pic": self._pic(card.get("vodPic") or "", pic_base),
            "vod_remarks": _format_remarks(card),
            "style": {"type": "rect", "ratio": 1.78},
        }

    def _content(self, title, group_names, vod_id):
        lines = [BRAND_GROUP, "当前主站域名：" + self.host, "━" * 28, "━" * 7]
        lines.append("标题：" + title)
        lines.append("分类：" + "、".join(group_names))
        lines.append(" ")
        lines.append("编号：" + vod_id)
        lines.append(BRAND_LINE)
        return "\n".join(lines).replace("导演", "")

    def _paged(self, cards, pg, total, limit):
        if total and limit:
            pagecount = (total + limit - 1) // limit
            if pagecount < 1:
                pagecount = 1
        else:
            pagecount = 1
        return {"list": cards, "page": int(pg), "pagecount": pagecount, "limit": int(limit), "total": int(total)}

    def homeContent(self, filter):
        classes = [{"type_id": tid, "type_name": name} for tid, name in CLASSES]
        result = {"class": classes}
        if filter:
            result["filters"] = {tid: [_sort_filter()] for tid, name in CLASSES}
        return result

    def homeVideoContent(self):
        try:
            cfg = self._get_config()
            res = self._api_call("post", "theme/index", "params", None)
            if not isinstance(res, dict) or res.get("code") != "0000" or not isinstance(res.get("data"), list):
                raise ValueError("首页加载失败，请稍后重试")
            items = []
            seen = set()
            for section in res["data"]:
                for card in (section.get("data") or []):
                    cid = str(card.get("id"))
                    if cid in seen:
                        continue
                    seen.add(cid)
                    items.append(self._card(card, cfg["picBaseUrl"]))
            return {"list": items}
        except Exception:
            return {"list": [], "msg": BLOCK_MSG}

    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        sort = "2"
        if isinstance(extend, dict) and extend.get("sortType"):
            sort = "%s" % extend["sortType"]
        elif isinstance(filter, dict) and filter.get("sortType"):
            sort = "%s" % filter["sortType"]
        if sort not in ("2", "3"):
            sort = "2"
        try:
            out = self._do_search(self._search_params(1, int(tid), "", pg, int(sort)))
            cards = [self._card(c, out["cfg"]["picBaseUrl"]) for c in out["data"]]
            return self._paged(cards, pg, out["total"], PAGE_SIZE)
        except Exception:
            return {"list": [], "page": pg, "pagecount": 1, "limit": PAGE_SIZE, "total": 0, "msg": BLOCK_MSG}

    def searchContent(self, key, quick, pg="1"):
        try:
            pg = int(pg)
        except Exception:
            pg = 1
        if not (key or "").strip():
            return {"list": [], "page": pg, "pagecount": 1, "limit": PAGE_SIZE, "total": 0}
        try:
            out = self._do_search(self._search_params(1, None, key, pg, 2))
            cards = [self._card(c, out["cfg"]["picBaseUrl"]) for c in out["data"]]
            return self._paged(cards, pg, out["total"], PAGE_SIZE)
        except Exception:
            return {"list": [], "page": pg, "pagecount": 1, "limit": PAGE_SIZE, "total": 0, "msg": BLOCK_MSG}

    def detailContent(self, ids):
        raw = ids[0] if ids else ""
        tid = str(raw).replace("vod/", "", 1)
        try:
            result = self._fetch_detail(tid)
        except Exception as e:
            return {"list": [], "msg": str(e) or BLOCK_MSG}
        if not result:
            return {"list": [], "msg": "未找到该影片"}
        try:
            return {"list": [self._detail_item(result, tid)]}
        except Exception as e:
            return {"list": [], "msg": str(e) or BLOCK_MSG}

    def _detail_item(self, result, tid):
        vod = result["vod"]
        title = _collapse_title(vod.get("title"))
        group_names = []
        for g in (vod.get("group_names") or []):
            if isinstance(g, dict) and g.get("groupName"):
                group_names.append(g["groupName"])
        cfg = self._get_config()
        pic = self._pic(vod.get("vodPic") or "", cfg["picBaseUrl"])
        addr = ""
        full = vod.get("vodFullPlayUrl") or []
        if full and isinstance(full[0], dict):
            addr = full[0].get("addr") or ""
        play_from = []
        play_url = []
        if addr:
            eps = []
            for idx, line in enumerate(cfg["h5PlayLines"]):
                eps.append("%s$play/%s/%d" % (_clean_name(line.get("name")), tid, idx))
            play_from.append("恒轩")
            play_url.append("#".join(eps))
        vod_item = {
            "vod_id": "vod/" + tid,
            "vod_name": title,
            "vod_pic": pic,
            "vod_bg": pic,
            "vod_background": pic,
            "vod_banner": pic,
            "vod_actor": BRAND_ACTOR,
            "vod_director": BRAND_DIRECTOR,
            "vod_remarks": _format_remarks(vod),
            "type_name": "、".join(group_names),
            "vod_content": self._content(title, group_names, tid),
            "style": {"type": "rect", "ratio": 1.78},
        }
        if play_from:
            vod_item["vod_play_from"] = "$$$".join(play_from)
            vod_item["vod_play_url"] = "$$$".join(play_url)
        return vod_item

    def playerContent(self, flag, id, vipFlags):
        try:
            parts = str(id or "").split("/")
            if len(parts) != 3 or parts[0] != "play":
                return {"parse": 0, "msg": "无效的播放标识"}
            vod_id = parts[1]
            try:
                line_idx = int(parts[2])
            except Exception:
                line_idx = 0
            cfg = self._get_config()
            result = self._fetch_detail(vod_id)
            if not result:
                return {"parse": 0, "msg": "未找到该影片"}
            vod = result["vod"]
            addr = ""
            full = vod.get("vodFullPlayUrl") or []
            if full and isinstance(full[0], dict):
                addr = full[0].get("addr") or ""
            if not addr:
                return {"parse": 0, "msg": "未取到播放地址，请稍后重试"}
            lines = cfg["h5PlayLines"]
            line = lines[line_idx] if 0 <= line_idx < len(lines) else lines[0]
            url = (line.get("line") or "") + addr
            if ".m3u8" not in url.lower():
                sep = "&" if "?" in url else "?"
                url = url + sep + "format=.m3u8"
            header = {"User-Agent": UA, "Referer": self.host + "/"}
            return {"parse": 0, "jx": 0, "playUrl": "", "url": url, "header": header}
        except Exception as e:
            return {"parse": 0, "msg": str(e) or "未取到播放地址，请稍后重试"}

    def _proxy_img(self, remote):
        if remote in self._imgcache:
            return [200, self._imgcache[remote][0], self._imgcache[remote][1]]
        cfg = self._get_config()
        last = None
        data = b""
        for _ in range(2):
            try:
                data = self._request("GET", remote, headers={"Referer": self.host + "/"}, timeout=8)
                break
            except Exception as e:
                last = e
        if not data:
            raise last or ValueError("图片下载失败")
        if len(data) > 20 * 1024 * 1024:
            return [502, "text/plain", ""]
        if cfg.get("newH5ImageSecret") == "1" and len(data) > 1:
            is_jpeg = data[0] == 0xff and data[1] == 0xd8 and data[2] == 0xff
            is_png = data[0] == 0x89 and data[1] == 0x50 and data[2] == 0x4e and data[3] == 0x47
            if not is_jpeg and not is_png:
                key = data[0]
                data = bytes(b ^ key for b in data[1:])
        mime = "image/jpeg"
        if data[:2] == b"\x89\x50":
            mime = "image/png"
        elif data[:2] == b"\x52\x49":
            mime = "image/webp"
        if data[:3] != b"\xff\xd8\xff" and data[:8] != b"\x89PNG\r\n\x1a\n" and data[:4] != b"RIFF":
            return [502, "text/plain", ""]
        if len(self._imgcache) > 16:
            self._imgcache.pop(next(iter(self._imgcache)))
        self._imgcache[remote] = (mime, data)
        return [200, mime, data]

    def localProxy(self, param):
        param = param or {}
        try:
            if param.get("img"):
                return self._proxy_img(param["img"])
        except Exception:
            return [502, "text/plain", ""]
        return [404, "text/plain", ""]

    def action(self, action):
        return {"msg": "ok"}

    def liveContent(self):
        return ""

    def destroy(self):
        self._imgcache = {}
        self._cache = {}

# --- System Signature ---
#‍​​‌‌‌​​​​​‌‌‌​​‌​​‌‌​‌‌‌​​‌‌​‌​​​​‌‌​‌​‌​​‌‌​‌​​​​‌‌​‌‌​​​‌‌​‌​​​​‌‌​​‌​​​‌‌​‌‌​‍
# Source: https://sub.lytvs.top/trap?token=tk_0c32cd61&t=1795702537099&sig=f7f0c4319872abc3
