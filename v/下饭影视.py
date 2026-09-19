# -*- coding: utf-8 -*-
import json
import time
import base64
from base64 import b64encode
from urllib.request import Request, urlopen
from urllib.parse import quote_plus, unquote

try:
    from base.spider import Spider as _BaseSpider
except Exception:
    _BaseSpider = object

BASE_URLS = [
    "http://manian.juxiafan.com",
    "http://195.225.24.128:6213",
    "http://jugaoqing.com",
    "http://jumianfei.com",
    "http://juyongjiu.com",
    "http://kuailezhuiju2.com",
    "http://zhuiju666.com",
    "http://194.147.100.155:7744",
]

AES_KEY = b"kZ6fT8oF6oM8eX6lF7eH2rJ3pW7gW0kC"
UA = "okhttp/4.12.0"
LIVE_TYPE_ID = 22023
SOURCE_PRIORITY = ["江苏2K极速专线", "4K高码2160", "剧下饭极速专线"]


def _build_sbox():
    sbox = [0] * 256
    p = q = 1
    while True:
        p = p ^ ((p << 1) ^ (0x1B if p & 0x80 else 0)) & 0xFF
        q ^= q << 1
        q ^= q << 2
        q ^= q << 4
        q ^= 0x09 if (q & 0x80) else 0
        q &= 0xFF
        xformed = q ^ ((q << 1) | (q >> 7)) & 0xFF
        xformed = (xformed ^ ((q << 2) | (q >> 6))) & 0xFF
        xformed = (xformed ^ ((q << 3) | (q >> 5))) & 0xFF
        xformed = (xformed ^ ((q << 4) | (q >> 4))) & 0xFF
        sbox[p] = xformed ^ 0x63
        if p == 1:
            break
    sbox[0] = 0x63
    return sbox


_SBOX = _build_sbox()
_RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36, 0x6C, 0xD8, 0xAB, 0x4D]


def _xtime(a):
    return ((a << 1) ^ (0x1B if a & 0x80 else 0)) & 0xFF


_COL2 = [_xtime(i) for i in range(256)]
_COL3 = [_xtime(i) ^ i for i in range(256)]


def _sort_sources(sources):
    def _key_func(src):
        name = src.get("sourceName", "")
        for idx, pri in enumerate(SOURCE_PRIORITY):
            if pri in name:
                return idx
        return 999
    return sorted(sources, key=_key_func)


def _expand_key(key):
    nk = len(key) // 4
    nr = nk + 6
    w = [list(key[4 * i:4 * i + 4]) for i in range(nk)]
    for i in range(nk, 4 * (nr + 1)):
        temp = list(w[i - 1])
        if i % nk == 0:
            temp = temp[1:] + temp[:1]
            temp = [_SBOX[b] for b in temp]
            temp[0] ^= _RCON[i // nk - 1]
        elif nk > 6 and i % nk == 4:
            temp = [_SBOX[b] for b in temp]
        w.append([w[i - nk][j] ^ temp[j] for j in range(4)])
    return w, nr


def _encrypt_block(block, w, nr):
    def _rk(r):
        return [x for word in w[r * 4:(r * 4) + 4] for x in word]
    s = list(block)
    rk0 = _rk(0)
    for j in range(16):
        s[j] ^= rk0[j]
    for r in range(1, nr):
        s = [_SBOX[b] for b in s]
        s = [s[0], s[5], s[10], s[15],
             s[4], s[9], s[14], s[3],
             s[8], s[13], s[2], s[7],
             s[12], s[1], s[6], s[11]]
        t = [0] * 16
        for c in range(4):
            i = c * 4
            a0, a1, a2, a3 = s[i], s[i + 1], s[i + 2], s[i + 3]
            t[i] = _COL2[a0] ^ _COL3[a1] ^ a2 ^ a3
            t[i + 1] = a0 ^ _COL2[a1] ^ _COL3[a2] ^ a3
            t[i + 2] = a0 ^ a1 ^ _COL2[a2] ^ _COL3[a3]
            t[i + 3] = _COL3[a0] ^ a1 ^ a2 ^ _COL2[a3]
        s = t
        rk = _rk(r)
        s = [s[j] ^ rk[j] for j in range(16)]
    s = [_SBOX[b] for b in s]
    s = [s[0], s[5], s[10], s[15],
         s[4], s[9], s[14], s[3],
         s[8], s[13], s[2], s[7],
         s[12], s[1], s[6], s[11]]
    rk = _rk(nr)
    s = [s[j] ^ rk[j] for j in range(16)]
    return bytes(s)


def _aes256_ecb_encrypt(plain, key):
    w, nr = _expand_key(key)
    out = bytearray()
    for i in range(0, len(plain), 16):
        out += _encrypt_block(bytes(plain[i:i + 16]), w, nr)
    return bytes(out)


def _aes_encrypt(plaintext, key=AES_KEY):
    data = plaintext.encode("utf-8") if isinstance(plaintext, str) else plaintext
    pad = 16 - len(data) % 16
    data = data + bytes([pad]) * pad
    try:
        from Crypto.Cipher import AES
        return b64encode(AES.new(key, AES.MODE_ECB).encrypt(data)).decode()
    except Exception:
        try:
            from cryptography.hazmat.primitives.ciphers import Cipher as _C
            from cryptography.hazmat.primitives.ciphers.algorithms import AES as _AES
            from cryptography.hazmat.primitives.ciphers.modes import ECB as _ECB
            from cryptography.hazmat.backends import default_backend as _B
            enc = _C(_AES(key), _ECB(), backend=_B()).encryptor()
            return b64encode(enc.update(data) + enc.finalize()).decode()
        except Exception:
            return b64encode(_aes256_ecb_encrypt(data, key)).decode()


def _http(method, url, body=None, content_type=None, timeout=12):
    headers = {"User-Agent": UA}
    data = None
    if body is not None:
        data = body.encode("utf-8") if isinstance(body, str) else body
        headers["Content-Length"] = str(len(data))
    if content_type:
        headers["Content-Type"] = content_type
    req = Request(url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", "replace")


def _sign(concat):
    return _aes_encrypt(concat)


def _fix_host(host):
    if host is None or (isinstance(host, str) and host.strip() == ""):
        host = BASE_URLS[0]
    return str(host).rstrip("/")


def _post(host, path, body=None, content_type=None):
    h = _fix_host(host)
    try:
        return _http("POST", h + path, body, content_type)
    except Exception:
        return "{}"


def _get(url, timeout=12):
    try:
        return _http("GET", url, timeout=timeout)
    except Exception:
        return "{}"


def _post_form(host, path, params):
    ts = str(int(time.time()))
    params["timestamp"] = ts
    items = sorted(params.items())
    concat = "&".join(k + "=" + quote_plus(str(v)) for k, v in items)
    ds = _sign(concat)
    form = "&".join(k + "=" + quote_plus(str(v)) for k, v in items)
    form += "&datasign=" + quote_plus(ds)
    return _post(host, path, form, "application/x-www-form-urlencoded")


def _post_json(host, path, params):
    params["timestamp"] = str(int(time.time()))
    items = sorted(params.items())
    concat = "&".join(k + "=" + str(v) for k, v in items)
    ds = _sign(concat)
    obj = dict(items)
    obj["datasign"] = ds
    body = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return _post(host, path, body, "application/json;charset=UTF-8")


def _home(host):
    resp = _post(host, "/api/v1/video/classifies", None, None)
    try:
        data = json.loads(resp).get("data") or []
    except Exception:
        data = []
    cls = [{"type_id": str(c.get("id")), "type_name": c.get("name") or ""}
           for c in data if c.get("id") and c.get("name")]
    cls.sort(key=lambda x: int(x["type_id"]) if str(x["type_id"]).isdigit() else 10 ** 9)
    if str(LIVE_TYPE_ID) not in [str(c.get("type_id")) for c in cls]:
        cls.append({"type_id": str(LIVE_TYPE_ID), "type_name": "直播"})
    return {"class": cls, "filters": {}}


def _normalize_main_title(title):
    if not title:
        return ""
    s = title.strip().lower()
    s = s.replace("Ⅱ", "2").replace("Ⅲ", "3").replace("Ⅳ", "4").replace("Ⅰ", "1")
    s = s.replace("：", "").replace("–", "").replace("—", "").replace(" ", "")
    keywords = [
        "第一季","第二季","第三季","第四季","第五季",
        "第1季","第2季","第3季","第4季","第5季",
        "第1部","第2部","第3部","第4部","第5部",
        "上部","下部","前篇","后篇","完结篇",
        "高清","4k","1080p","720p",
        "国语版","粤语版","中文版","英文版",
        "修复版","重制版","导演版","特别版","加长版",
        "原版","完整版","独家","官方","修复",
        "1季","2季","3季","4季","5季",
        "1部","2部","3部","4部","5部",
    ]
    for kw in keywords:
        s = s.replace(kw, "")
    return s.strip() or title.strip().lower()


def _build_list(resp, page=1, id_desc=False):
    try:
        data = json.loads(resp).get("data") or {}
    except Exception:
        data = {}
    raw_list = []
    for v in data.get("list") or []:
        if not v.get("id"):
            continue
        vid = str(v.get("id"))
        title = (v.get("name") or "").strip()
        raw_list.append({"vid":vid,"title":title,"obj":v})
    groups = {}
    for item in raw_list:
        mkey = _normalize_main_title(item["title"])
        if mkey not in groups:
            groups[mkey] = []
        groups[mkey].append(item)
    final = []
    for gkey, glist in groups.items():
        if len(glist) == 1:
            pick = glist[0]
        else:
            pick = None
            for x in glist:
                if " " in x["title"]:
                    pick = x
                    break
            if pick is None:
                pick = glist[0]
        final.append({
            "vod_id": pick["vid"],
            "vod_name": pick["obj"].get("name") or "",
            "vod_pic": pick["obj"].get("videoPic") or "",
            "vod_remarks": "",
        })
    if id_desc and final:
        final.sort(key=lambda x: (len(x["vod_name"]), x["vod_name"]))
    try:
        pg = int(page) or 1
    except (ValueError, TypeError):
        pg = 1
    try:
        pagecount = int(data.get("totalPage") or 1)
    except (ValueError, TypeError):
        pagecount = 1
    if pagecount < pg:
        pagecount = pg
    return {
        "page": pg,
        "pagecount": pagecount,
        "limit": data.get("limit") or 20,
        "total": data.get("totalCount") or 0,
        "list": final,
    }


def _category(host, tid, pg):
    page = 1
    try:
        page = int(pg or 1)
    except Exception:
        pass
    try:
        type_id = int(tid)
    except Exception:
        type_id = 0
    if type_id == LIVE_TYPE_ID:
        lst = []
        try:
            r = _get(_fix_host(host) + "/api/v1/video/liveVideo")
            data = (json.loads(r).get("data") or {})
            raw_list = []
            for v in data.get("list") or []:
                if not v.get("id"):
                    continue
                vid = str(v.get("id"))
                title = (v.get("name") or "").strip()
                raw_list.append({"vid":vid,"title":title,"obj":v})
            groups = {}
            for item in raw_list:
                mkey = _normalize_main_title(item["title"])
                if mkey not in groups:
                    groups[mkey] = []
                groups[mkey].append(item)
            for gkey, glist in groups.items():
                if len(glist) == 1:
                    pick = glist[0]
                else:
                    pick = None
                    for x in glist:
                        if " " in x["title"]:
                            pick = x
                            break
                    if pick is None:
                        pick = glist[0]
                lst.append({
                    "vod_id": pick["vid"],
                    "vod_name": pick["obj"].get("name") or "",
                    "vod_pic": pick["obj"].get("videoPic") or "",
                    "vod_remarks": "",
                })
        except Exception:
            pass
        return {"page": 1, "pagecount": 1, "limit": len(lst), "total": len(lst), "list": lst}
    resp = _post_json(host, "/api/v1/video/index", {"pageNum": page, "typeId": type_id})
    return _build_list(resp, page, False)


def _search(host, key, pg="1"):
    key = (key or "").strip().strip('"').strip("'")
    if not key:
        return {"page": 1, "pagecount": 0, "limit": 20, "total": 0, "list": []}
    if "%" in key:
        try:
            dec = unquote(key)
            if dec and dec != key:
                key = dec.strip()
        except Exception:
            pass
    if key and "\\u" in key and all(ord(ch) < 128 for ch in key):
        try:
            dec = key.encode("ascii").decode("unicode_escape")
            if dec and dec != key:
                key = dec
        except Exception:
            pass
    try:
        page = int(pg or 1)
    except (ValueError, TypeError):
        page = 1
    if page < 1:
        page = 1
    resp = _post_json(host, "/api/v1/video/search", {"keyword": key, "pageNum": page})
    return _build_list(resp, page, False)


def _reco(host):
    try:
        c = _category(host, "22016", "1")
        return (c or {}).get("list") or []
    except Exception:
        return []


def _fetch_detail(host, vid):
    resp = _post_form(host, "/api/v1/video/videoDetails", {"id": str(vid)})
    try:
        return json.loads(resp).get("data") or {}
    except Exception:
        return {}


def _detail(host, vid):
    data = _fetch_detail(host, vid)
    if not data:
        return {"list": []}
    sources = data.get("playerSource") or []
    sources = _sort_sources(sources)
    pick_src = None
    for src in sources:
        eps = src.get("episodes") or []
        if len(eps) > 0:
            pick_src = src
            break
    if not pick_src:
        return {"list": []}
    name = "恒轩"
    eps = pick_src.get("episodes") or []
    segs = []
    for i, ep in enumerate(eps, 1):
        ep_name = (ep.get("episodeName") or "") or ("第" + str(i) + "集")
        ep_name = ep_name.replace("$", "_").replace("#", "_")
        segs.append(ep_name + "$" + str(vid) + "_" + str(i))
    play_from = name
    play_url = "#".join(segs)
    return {"list": [{
        "vod_id": str(data.get("id") or vid),
        "vod_name": data.get("name") or "",
        "vod_pic": data.get("videoPic") or "",
        "vod_actor": data.get("actor") or "",
        "vod_director": data.get("director") or "",
        "vod_remarks": "",
        "vod_content": data.get("content") or "",
        "vod_year": data.get("year") or "",
        "vod_area": data.get("area") or "",
        "vod_play_from": play_from,
        "vod_play_url": play_url,
    }]}


def _analysis_url(host, source_code, pc):
    if not source_code or not pc:
        return ""
    try:
        r = _post_form(host, "/api/v1/player/analysisUrl", {"from": source_code, "code": pc})
        u = (json.loads(r).get("data") or "")
        if str(u).startswith("http"):
            return str(u)
    except Exception:
        pass
    return ""


def _play(host, flag, pid):
    try:
        vid, ep = pid.rsplit("_", 1)
        ep = int(ep)
    except Exception:
        return {"parse": 0, "url": pid, "header": {"User-Agent": UA}}
    data = _fetch_detail(host, vid)
    sources = data.get("playerSource") or []
    sources = _sort_sources(sources)
    pick_src = None
    for src in sources:
        eps = src.get("episodes") or []
        if eps and ep <= len(eps):
            pick_src = src
            break
    if not pick_src:
        return {"parse": 0, "url": "", "header": {"User-Agent": UA}}
    eps = pick_src.get("episodes") or []
    pc = (eps[ep - 1] or {}).get("playerCode") or ""
    parse_url = pick_src.get("parseUrl") or ""
    source_code = pick_src.get("sourceCode") or ""
    if parse_url and pc:
        j = _get(parse_url + pc)
        try:
            u = json.loads(j).get("url") or ""
        except Exception:
            u = ""
        if u:
            return {"parse": 0, "url": u, "header": {"User-Agent": UA}}
    if pc and not str(pc).startswith("http"):
        u = _analysis_url(host, source_code, pc)
        if u:
            headers = {"User-Agent": UA}
            if source_code == "huya":
                headers["Referer"] = "https://www.huya.com/"
            return {"parse": 0, "url": u, "header": headers}
        return {"parse": 0, "url": pc, "header": {"User-Agent": UA}}
    elif pc:
        return {"parse": 0, "url": pc, "header": {"User-Agent": UA}}
    return {"parse": 0, "url": "", "header": {"User-Agent": UA}}


class Spider(_BaseSpider):
    def __init__(self, *args, **kwargs):
        self._host = BASE_URLS[0]
        if kwargs.get("host"):
            self._host = _fix_host(kwargs["host"])
        if kwargs.get("extend") is not None:
            self.init(kwargs["extend"])
    def init(self, extend=None):
        if extend:
            s = str(extend).strip()
            if s.startswith("http"):
                self._host = _fix_host(s)
            elif s.startswith("base="):
                self._host = _fix_host(s[5:])
    def getName(self):
        return "恒轩4K影视"
    def homeContent(self, filter=False):
        result = _home(self._host)
        result["list"] = []
        return result
    def homeVideoContent(self):
        return {"list": []}
    def categoryContent(self, tid, pg="1", filter=None, extend=None):
        return _category(self._host, tid, pg)
    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        return _detail(self._host, ids[0])
    def searchContent(self, key, quick, pg="1"):
        return self.searchContentPage(key, quick, pg)
    def searchContentPage(self, key, quick, pg="1"):
        try:
            return _search(self._host, key, pg)
        except Exception:
            return {"page": 1, "pagecount": 1, "limit": 0, "total": 0, "list": []}
    def playerContent(self, flag, id, vipFlags=""):
        return _play(self._host, flag, id)
    def manualVideoCheck(self):
        return False
    def isVideoFormat(self, url):
        return False
    def localProxy(self, param):
        return {"list": [], "parse": 0, "url": ""}
    def liveContent(self, url):
        return {"list": []}


_HOST = BASE_URLS[0]


def init(extend=None):
    global _HOST
    if extend:
        s = str(extend).strip()
        if s.startswith("http"):
            _HOST = _fix_host(s)
        elif s.startswith("base="):
            _HOST = _fix_host(s[5:])


def homeContent(filter=False):
    try:
        r = _home(_HOST)
        r["list"] = []
    except Exception:
        r = {"class": [], "filters": {}, "list": []}
    return json.dumps(r, ensure_ascii=False)


def homeVideoContent():
    return json.dumps({"list": []}, ensure_ascii=False)


def categoryContent(tid, pg="1", filter=False, extend=None):
    return json.dumps(_category(_HOST, tid, pg), ensure_ascii=False)


def detailContent(ids):
    if not ids:
        return '{"list":[]}'
    return json.dumps(_detail(_HOST, ids[0]), ensure_ascii=False)


def searchContent(key, quick=False, pg="1"):
    return json.dumps(_search(_HOST, key, pg), ensure_ascii=False)


def playerContent(flag, id, vipFlags=None):
    sp = Spider()
    sp._host = _HOST
    res = sp.playerContent(flag, id, vipFlags)
    return json.dumps(res, ensure_ascii=False)


def manualVideoCheck():
    return False


def isVideoFormat(url):
    return False


if __name__ == "__main__":
    def show(label, s, n=220):
        txt = json.dumps(s, ensure_ascii=False) if not isinstance(s, str) else s
        print("== " + label + " ==")
        print(txt if len(txt) <= n else txt[:n])
        print()
    sp = Spider()
    show("Spider.homeContent", sp.homeContent(False))
    show("Spider.categoryContent", sp.categoryContent("22016", "1", False, None))
    show("Spider.categoryLive", sp.categoryContent("22023", "1", False, None))
    show("Spider.searchContent", sp.searchContent("斗罗大陆", True))
    show("Spider.detailContent", sp.detailContent(["621119"]))
    show("Spider.playerContent ep1", sp.playerContent("", "621119_1", None))
