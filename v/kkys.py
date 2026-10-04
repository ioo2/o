# -*- coding: utf-8 -*-
import json
import re
import sys
import os
import time
import hmac
import hashlib
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from base.spider import Spider as BaseSpider
except ImportError:
    class BaseSpider:
        def __init__(self, query_params=None, t4_api=None):
            self.query_params = query_params or {}
            self.t4_api = t4_api or ''
            self.extend = ''
        def fetch(self, url, params=None, headers=None, cookies=None, timeout=10,** kw):
            import requests
            return requests.get(url, params=params, headers=headers,
                                cookies=cookies, timeout=timeout, verify=False)

def _gmul(a, b):
    p = 0
    for _ in range(8):
        if b & 1:
            p ^= a
        hi = a & 0x80
        a = (a << 1) & 0xff
        if hi:
            a ^= 0x1b
        b >>= 1
    return p

def _ginv(a):
    if a == 0:
        return 0
    for i in range(256):
        if _gmul(a, i) == 1:
            return i
    return 0

def _rotl(x, n):
    return ((x << n) | (x >> (8 - n))) & 0xff

_SBOX = [0] * 256
for _i in range(256):
    _b = _ginv(_i)
    _SBOX[_i] = _b ^ _rotl(_b, 1) ^ _rotl(_b, 2) ^ _rotl(_b, 3) ^ _rotl(_b, 4) ^ 0x63
_ISBOX = [0] * 256
for _i, _v in enumerate(_SBOX):
    _ISBOX[_v] = _i

def _expand(key):
    nk = len(key) // 4
    nr = nk + 6
    w = [list(key[4 * i:4 * i + 4]) for i in range(nk)]
    rc = 1
    for i in range(nk, 4 * (nr + 1)):
        t = w[i - 1][:]
        if i % nk == 0:
            t = t[1:] + t[:1]
            t = [_SBOX[x] for x in t]
            t[0] ^= rc
            rc = _gmul(rc, 2)
        elif nk > 6 and i % nk == 4:
            t = [_SBOX[x] for x in t]
        w.append([w[i - nk][j] ^ t[j] for j in range(4)])
    return w, nr

def _dec_block(blk, key):
    w, nr = _expand(key)
    s = list(blk)
    for c in range(4):
        for r in range(4):
            s[4 * c + r] ^= w[4 * nr + c][r]
    for rnd in range(nr - 1, 0, -1):
        for r in range(1, 4):
            row = [s[4 * c + r] for c in range(4)]
            row = row[-r:] + row[:-r]
            for c in range(4):
                s[4 * c + r] = row[c]
        s[:] = [_ISBOX[x] for x in s]
        for c in range(4):
            for r in range(4):
                s[4 * c + r] ^= w[4 * rnd + c][r]
        for c in range(4):
            a = [s[4 * c + i] for i in range(4)]
            s[4 * c + 0] = _gmul(a[0], 14) ^ _gmul(a[1], 11) ^ _gmul(a[2], 13) ^ _gmul(a[3], 9)
            s[4 * c + 1] = _gmul(a[0], 9) ^ _gmul(a[1], 14) ^ _gmul(a[2], 11) ^ _gmul(a[3], 13)
            s[4 * c + 2] = _gmul(a[0], 13) ^ _gmul(a[1], 9) ^ _gmul(a[2], 14) ^ _gmul(a[3], 11)
            s[4 * c + 3] = _gmul(a[0], 11) ^ _gmul(a[1], 13) ^ _gmul(a[2], 9) ^ _gmul(a[3], 14)
    for r in range(1, 4):
        row = [s[4 * c + r] for c in range(4)]
        row = row[-r:] + row[:-r]
        for c in range(4):
            s[4 * c + r] = row[c]
    s[:] = [_ISBOX[x] for x in s]
    for c in range(4):
        for r in range(4):
            s[4 * c + r] ^= w[c][r]
    return bytes(s)

def _aes_cbc_decrypt_py(data, key, iv):
    out = bytearray()
    prev = iv
    for i in range(0, len(data) - len(data) % 16, 16):
        blk = data[i:i + 16]
        d = _dec_block(blk, key)
        out += bytes(x ^ y for x, y in zip(d, prev))
        prev = blk
    return bytes(out)

def _aes_cbc_decrypt(data, key, iv):
    n = len(data) - len(data) % 16
    data = data[:n]
    if not data:
        return b""
    try:
        from Crypto.Cipher import AES as _AES
        return _AES.new(key, _AES.MODE_CBC, iv).decrypt(data)
    except Exception:
        pass
    try:
        from Cryptodome.Cipher import AES as _AES2
        return _AES2.new(key, _AES2.MODE_CBC, iv).decrypt(data)
    except Exception:
        pass
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
        d = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
        return d.update(data) + d.finalize()
    except Exception:
        pass
    return _aes_cbc_decrypt_py(data, key, iv)


class Spider(BaseSpider):
    HOST_VCACHE = "https://vcache.ybsdkl.cn"
    HOST_VLOGIC = "https://vlogic.ybsdkl.cn"
    IMG_HOST = "https://vres.mppcdrr.cn"
    UA = "com.kkdyD12997260706.t181523/3.5.0 Dalvik/2.1.0 (Linux; U; Android 13; 25098PN5AC Build/CP2A.260605.016)"
    UA_MEDIA = "okhttp/4.12.0"
    SIGN_KEY = b"ksggsr4tp6difdo1c3im8fqd3g"
    AES_KEY = b"ayt5wy5afwmwrpb19k9s3psx3dymyd0n"
    AES_IV = b"b3t069ijy7pirw0j"
    DEVICE = "appId=kkdy&deviceCreatedAt=1791100645895&deviceId=346214515d5c88f1&st=2&userId=55957380"
    TOKEN = ("NTU5NTczODB8MTc5MTA5MDkzM3w3MGEwODc5Yzc0MjA0NTAyMjE5ODI1NjM5ZWI4YWM4NTJmMGMx"
             "ODMxYzI4ODE4MmU3Mzg0OTIyMTI4Y2QxZmY4")
    DEVICE_INFO = ("eyJicmFuZCI6IlhpYW9taSIsIm1vZGVsIjoiMjUwOThQTjVBQyIsInR5cGUiOiJwaG9uZSIs"
                   "InJlc29sdXRpb25YIjoiMTIyMCIsInJlc29sdXRpb25ZIjoiMjQ0MSIsIm9yaWVudGF0aW9uIjoiMSIs"
                   "Im9zTmFtZSI6ImFuZHJvaWQiLCJvc1ZlcnNpb24iOiIxMyIsIm9zTGV2ZWwiOiIzMyIsImFiaSI6ImFy"
                   "bTY0LXY4YSIsImFuZHJvaWRJZCI6IjM0NjIxNDUxNWQ1Yzg4ZjEiLCJ1dWlkIjoiOTVkNzhkZTItNjc5"
                   "My00NzU1LWJmMWItZmU1NmQyOGM2MGU4IiwiZ2FpZCI6IiJ9")
    DISCLAIMER = (")
    CHANNELS = [
        ("6", "短剧"), ("2", "剧集"), ("3", "动漫"), ("4", "综艺纪录"), ("1", "电影"),
    ]

    def init(self, extend=""):
        self.extend = extend or ""
        self.timeout = 15
        self._cache = {}
        self._appinit = None
        return {"status": 0}

    def getName(self):
        return "可可影视"

    def _headers(self, logic=False):
        h = {
            "User-Agent": self.UA,
            "appId": "kkdy",
            "os": "android",
            "appVersion": "3.5.0",
            "package": "com.kkdyD12997260706.t181523",
            "deviceId": "346214515d5c88f1",
            "deviceCreatedAt": "1791100645895",
            "userId": "55957380",
            "channelId": "c900",
            "X-Token": self.TOKEN,
            "apiVer": "v2",
            "st": "2",
            "deviceInfo": self.DEVICE_INFO,
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9",
        }
        if logic:
            h["X-DEVICE"] = "1"
        else:
            h["x-d-video"] = "1"
        return h

    def _sign(self, path, params):
        ts = str(int(time.time() * 1000))
        qs = "&".join("%s=%s" % (k, params[k]) for k in sorted(params))
        plain = "get|%s|%s|%s|%s|" % (path, qs, ts, self.DEVICE)
        sig = hmac.new(self.SIGN_KEY, plain.encode("utf-8"), hashlib.sha1).hexdigest()
        return ts, sig

    def _decrypt(self, raw):
        if not raw:
            return ""
        if raw[:1] in (b"{", b"["):
            return raw.decode("utf-8", "ignore")
        body = raw[:len(raw) - len(raw) % 16]
        p = _aes_cbc_decrypt(body, self.AES_KEY, self.AES_IV)
        if p and 1 <= p[-1] <= 16:
            p = p[:-p[-1]]
        return p.decode("utf-8", "ignore")

    def _api(self, path, params, host=None):
        host = host or self.HOST_VCACHE
        url = host + path
        ck = url + "?" + "&".join("%s=%s" % (k, params[k]) for k in sorted(params))
        if ck in self._cache:
            return self._cache[ck]
        ts, sig = self._sign(path, params)
        h = self._headers(host == self.HOST_VLOGIC)
        h["ts"] = ts
        h["sign"] = sig
        text = ""
        for i in range(2):
            try:
                rsp = self.fetch(url, params=params, headers=h, timeout=self.timeout)
                text = self._decrypt(rsp.content if hasattr(rsp, "content") else rsp.text.encode())
                if text and '"code"' in text:
                    break
            except Exception:
                text = ""
            time.sleep(0.8)
        if len(self._cache) > 24:
            self._cache.clear()
        self._cache[ck] = text
        return text

    def _json(self, path, params, host=None):
        try:
            return json.loads(self._api(path, params, host) or "{}")
        except Exception:
            return {}

    def _img(self, item):
        grp = item.get("imageGroup") or "vod1"
        path = item.get("imagePath") or ""
        if not path:
            return ""
        if path.startswith("http"):
            return path
        return "%s/%s%s" % (self.IMG_HOST, grp, path)

    def _clean(self, s):
        return re.sub(r"<[^>]+>", "", s or "").strip()

    def _card(self, it):
        return {
            "vod_id": str(it.get("id", "")).lstrip("/"),
            "vod_name": self._clean(it.get("title")),
            "vod_pic": self._img(it),
            "vod_remarks": self._clean(it.get("bottomLabel") or it.get("topRightLabel") or ""),
        }

    def _filters(self):
        ai = self._appinit
        if ai is None:
            ai = self._json("/v5/config/appInit.capi",
                            {"os": "android", "appId": "kkdy", "userLevel": "2"})
            self._appinit = ai
        qmap = {}
        for blk in (ai.get("channelListQuery") or []):
            cid = str(blk.get("channelId"))
            groups = []
            for g in (blk.get("items") or []):
                vals = [{"n": "全部", "v": ""}]
                vals += [{"n": d.get("name", ""), "v": d.get("id", "")}
                         for d in (g.get("data") or []) if d.get("id")]
                groups.append({
                    "key": g.get("query", ""),
                    "name": {"sort": "排序", "category": "类型", "area": "地区",
                             "year": "年份", "language": "语言"}.get(g.get("query", ""), g.get("query", "")),
                    "value": vals,
                })
            qmap[cid] = groups
        return qmap

    def homeContent(self, filter):
        classes = [{"type_id": cid, "type_name": name} for cid, name in self.CHANNELS]
        filters = {}
        if filter:
            qmap = self._filters()
            for cid, _ in self.CHANNELS:
                if qmap.get(cid):
                    filters[cid] = qmap[cid]
        return {"class": classes, "filters": filters}

    def homeVideoContent(self):
        j = self._json("/v6/vod/home.capi", {"os": "android", "appId": "kkdy", "userLevel": "2"})
        out = []
        seen = set()
        for blk in (j.get("data", {}).get("blocks") or []):
            for it in (blk.get("data") or []):
                if not isinstance(it, dict) or "id" not in it:
                    continue
                if "vod/detail" not in (it.get("url") or ""):
                    continue
                c = self._card(it)
                if c["vod_id"] and c["vod_id"] not in seen:
                    seen.add(c["vod_id"])
                    out.append(c)
        return {"list": out}

    def categoryContent(self, tid, pg, filter, extend):
        pg = max(1, int(pg or 1))
        fl = json.loads(extend) if isinstance(extend, str) and extend.strip() else (extend or {})
        params = {"channelId": str(tid), "os": "android", "appId": "kkdy", "userLevel": "2"}
        for k in ("sort", "category", "area", "year", "language"):
            v = str(fl.get(k, "") or "").strip()
            if v and v != "全部":
                params[k] = v
        if "sort" not in params:
            params["sort"] = "3"
        if pg > 1:
            params["next"] = "page=%d" % pg
        j = self._json("/vod/channel/list.capi", params)
        lst = [self._card(it) for it in (j.get("data", {}).get("items") or []) if it.get("id")]
        nxt = j.get("data", {}).get("next") or ""
        return {"list": lst, "page": pg,
                "pagecount": pg + 1 if nxt else pg,
                "limit": len(lst) or 21, "total": 999999}

    def searchContent(self, key, quick, pg=1):
        pg = max(1, int(pg or 1))
        params = {"channelId": "0", "k": key, "next": "" if pg <= 1 else "page=%d" % pg,
                  "os": "android", "appId": "kkdy", "userChannel": "c900", "userLevel": "2"}
        j = self._json("/vod/search/query", params, host=self.HOST_VLOGIC)
        lst = [self._card(it) for it in (j.get("data", {}).get("items") or []) if it.get("id")]
        return {"list": lst, "page": pg}

    def _detail(self, vid):
        return self._json("/v2/vod/detail.capi",
                          {"vodId": str(vid), "os": "android", "appId": "kkdy", "userLevel": "2"})

    def _episodes(self, vid, site_id, ep_vod_id):
        return self._json("/v2/vod/episodes.capi",
                          {"vodId": str(vid), "siteId": site_id, "episodeVodId": str(ep_vod_id),
                           "os": "android", "appId": "kkdy", "userLevel": "2"})

    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, (list, tuple)) else str(ids).split(",")[0]
        vid = str(vid).split("|")[0].lstrip("/")
        j = self._detail(vid)
        d = j.get("data") or {}
        if not d:
            return {"list": []}
        content = (d.get("summary") or "").strip()
        if self.DISCLAIMER:
            content = self.DISCLAIMER + content
        def _names(arr):
            return " / ".join([x.get("name", "") for x in (arr or []) if isinstance(x, dict)])
        play_sources = d.get("playSources") or []
        tpl = None
        for src in play_sources:
            if src.get("list"):
                t = (src["list"][0].get("title") or "")
                if "第" in t:
                    tpl = t
                break
        def _gen_title(i):
            if tpl:
                return re.sub(r"\d+", str(i), tpl, count=1)
            return "第%d集" % i
        source_dump = []
        for src in play_sources:
            site_id = src.get("siteId") or ""
            ep_vod_id = src.get("episodeVodId", "")
            eps = src.get("list") or []
            total = int(src.get("total") or 0)
            parts = []
            if eps:
                for ep in eps:
                    name = (ep.get("title") or "").replace("$", "_")
                    v = "%s|%s|%s|%s" % (vid, site_id, ep_vod_id, ep.get("index", ""))
                    parts.append("%s$%s" % (name, v))
            elif total > 0:
                for i in range(1, total + 1):
                    v = "%s|%s|%s|%s" % (vid, site_id, ep_vod_id, i)
                    parts.append("%s$%s" % (_gen_title(i), v))
            if parts:
                source_dump.append(json.dumps({"siteId":site_id,"epVodId":ep_vod_id,"parts":parts},ensure_ascii=False))
        all_part_str = "#".join(source_dump)
        vod = {
            "vod_id": vid,
            "vod_name": d.get("title", ""),
            "vod_pic": self._img(d),
            "type_name": d.get("channelName", ""),
            "vod_year": (d.get("year") or {}).get("name", "") if isinstance(d.get("year"), dict) else "",
            "vod_area": _names(d.get("area")),
            "vod_remarks": d.get("bottomLabel", ""),
            "vod_score": str(d.get("score", "") or ""),
            "vod_director": _names(d.get("directors")),
            "vod_actor": _names(d.get("actors")),
            "vod_content": content,
            "vod_play_from": "恒轩",
            "vod_play_url": all_part_str,
        }
        return {"list": [vod]}

    def playerContent(self, flag, vid, vip_flags):
        raw_data = vid
        source_list = []
        try:
            source_list = [json.loads(item) for item in raw_data.split("#")]
        except Exception:
            pass
        url = ""
        for src_item in source_list:
            parts = src_item.get("parts",[])
            if not parts:
                continue
            first_ep = parts[0]
            ep_raw = first_ep.split("$")[-1]
            ep_parts = ep_raw.split("|")
            if len(ep_parts) <4:
                continue
            v_id, site_id, ep_vod_id, index = ep_parts[0],ep_parts[1],ep_parts[2],ep_parts[3]
            ep_data = self._episodes(v_id, site_id, ep_vod_id).get("data") or []
            for ep in ep_data:
                if str(ep.get("index")) == str(index):
                    pus = ep.get("playUrls") or []
                    if pus:
                        url = (pus[0].get("url") or "").strip()
                    break
            if url:
                break
        return {"parse": 0, "jx": 0, "url": url,
                "header": json.dumps({"User-Agent": self.UA_MEDIA}, ensure_ascii=False)}

    def isVideoFormat(self, url):
        return bool(url and re.search(r"\.(m3u8|mp4|ts)(\?|$)", url))

    def manualVideoCheck(self):
        return False

    def localProxy(self, param):
        return None
