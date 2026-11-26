# -*- coding: utf-8 -*-
# ONE18.py - FongMi/TVBox python spider, converted from Hamo JS plugin com.butterfly.one (one.js)

import re
import json
import time
import base64
import hashlib
import random
import datetime
import requests
from urllib.parse import quote
from base.spider import Spider as BaseSpider

BRAND = ""
LINE_NAME = "恒轩"
BRAND_ACTOR = ""
NO_SOURCE_NOTE = "该内容暂无可播放线路"
DEFAULT_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
APP_KEY = "l*bv%Ziq000Biaog"
APP_IV = "8597506002939249"
SIGN_SALT = "m4n2hjPeYWkD6tFpqKF^3HO^h24P@idT"
APP_VERSION = "1.6.0"
SEED_HOSTS = [
    "https://api.2b37894.com",
    "https://api.35a46dd.com",
    "https://api.43b8477.com",
    "https://api.5ce3771.com",
    "https://api.61c76a0.com",
    "https://api.632d809.com",
    "https://api.3459381.com",
    "https://api.em1oifd0.com",
    "https://api.j7y675.com",
]
PAGE_SIZE = 24
TIMEOUT = 8
POSTER_RATIO = 1.78

CATEGORIES = [
    ("newest", "最新"),
    ("hot", "热门"),
    ("jp", "日本"),
    ("cn", "国产"),
    ("us", "欧美"),
    ("live", "ONE 直播"),
]
PARTITION_IDS = ("jp", "cn", "us")

PLAIN_HOSTS = [
    "https://imgpw807.s7n7ue8.com",
    "https://imgpw807.2u7qzt7.com",
    "https://img807.hkq57tt.com",
    "https://imgsu807.hkq57tt.com",
]
ENC_HOSTS = ["gdliren123.com", "u3wwetf.com", "m6qzbb4.com", "bdsy56.com", "gzjsqx.com", "k8b3rsp.com"]
BAD_HOSTS = ["imgsu807.hkq57tt.com"]
IMG_PROXY = "https://wsrv.nl/?url="
VIDEO_FALLBACK_HOST = "https://46e9nz.mfpt8g.com"


def _make_sboxes():
    p = 1
    q = 1
    sbox = [0] * 256
    while True:
        p = p ^ ((p << 1) & 0xFF) ^ (0x1B if p & 0x80 else 0x00)
        q = (q ^ (q << 1)) & 0xFF
        q = (q ^ (q << 2)) & 0xFF
        q = (q ^ (q << 4)) & 0xFF
        if q & 0x80:
            q ^= 0x09
        q &= 0xFF

        def rotl(x, n):
            return ((x << n) | (x >> (8 - n))) & 0xFF

        sbox[p] = (q ^ rotl(q, 1) ^ rotl(q, 2) ^ rotl(q, 3) ^ rotl(q, 4) ^ 0x63) & 0xFF
        if p == 1:
            break
    sbox[0] = 0x63
    inv = [0] * 256
    for i, v in enumerate(sbox):
        inv[v] = i
    return sbox, inv


_SBOX, _INV_SBOX = _make_sboxes()


def _mul_table(a):
    t = [0] * 256
    for i in range(256):
        x = i
        r = 0
        aa = a
        while x:
            if x & 1:
                r ^= aa
            aa = ((aa << 1) ^ (0x1B if aa & 0x80 else 0)) & 0xFF
            x >>= 1
        t[i] = r
    return t


_MUL2 = _mul_table(2)
_MUL3 = _mul_table(3)
_MUL9 = _mul_table(9)
_MUL11 = _mul_table(11)
_MUL13 = _mul_table(13)
_MUL14 = _mul_table(14)
_RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]


def _aes_expand_key(key):
    w = list(key)
    for i in range(4, 44):
        t = w[4 * (i - 1):4 * i]
        if i % 4 == 0:
            t = [_SBOX[t[1]] ^ _RCON[i // 4 - 1], _SBOX[t[2]], _SBOX[t[3]], _SBOX[t[0]]]
        for j in range(4):
            w.append(w[4 * (i - 4) + j] ^ t[j])
    return w


def _aes_enc_block(w, block):
    s = [block[i] ^ w[i] for i in range(16)]
    for rnd in range(1, 10):
        s = [_SBOX[b] for b in s]
        s = [s[0], s[5], s[10], s[15], s[4], s[9], s[14], s[3], s[8], s[13], s[2], s[7], s[12], s[1], s[6], s[11]]
        out = [0] * 16
        for c in range(4):
            a0, a1, a2, a3 = s[4 * c], s[4 * c + 1], s[4 * c + 2], s[4 * c + 3]
            out[4 * c] = _MUL2[a0] ^ _MUL3[a1] ^ a2 ^ a3
            out[4 * c + 1] = a0 ^ _MUL2[a1] ^ _MUL3[a2] ^ a3
            out[4 * c + 2] = a0 ^ a1 ^ _MUL2[a2] ^ _MUL3[a3]
            out[4 * c + 3] = _MUL3[a0] ^ a1 ^ a2 ^ _MUL2[a3]
        s = [out[i] ^ w[16 * rnd + i] for i in range(16)]
    s = [_SBOX[b] for b in s]
    s = [s[0], s[5], s[10], s[15], s[4], s[9], s[14], s[3], s[8], s[13], s[2], s[7], s[12], s[1], s[6], s[11]]
    return bytes(s[i] ^ w[160 + i] for i in range(16))


def _aes_dec_block(w, block):
    s = [block[i] ^ w[160 + i] for i in range(16)]
    for rnd in range(9, 0, -1):
        s = [s[0], s[13], s[10], s[7], s[4], s[1], s[14], s[11], s[8], s[5], s[2], s[15], s[12], s[9], s[6], s[3]]
        s = [_INV_SBOX[b] for b in s]
        s = [s[i] ^ w[16 * rnd + i] for i in range(16)]
        out = [0] * 16
        for c in range(4):
            a0, a1, a2, a3 = s[4 * c], s[4 * c + 1], s[4 * c + 2], s[4 * c + 3]
            out[4 * c] = _MUL14[a0] ^ _MUL11[a1] ^ _MUL13[a2] ^ _MUL9[a3]
            out[4 * c + 1] = _MUL9[a0] ^ _MUL14[a1] ^ _MUL11[a2] ^ _MUL13[a3]
            out[4 * c + 2] = _MUL13[a0] ^ _MUL9[a1] ^ _MUL14[a2] ^ _MUL11[a3]
            out[4 * c + 3] = _MUL11[a0] ^ _MUL13[a1] ^ _MUL9[a2] ^ _MUL14[a3]
        s = out
    s = [s[0], s[13], s[10], s[7], s[4], s[1], s[14], s[11], s[8], s[5], s[2], s[15], s[12], s[9], s[6], s[3]]
    s = [_INV_SBOX[b] for b in s]
    return bytes(s[i] ^ w[i] for i in range(16))


def _aes_cbc_encrypt(key, iv, data):
    w = _aes_expand_key(key)
    pad = 16 - (len(data) % 16)
    data = data + bytes([pad]) * pad
    out = b""
    prev = iv
    for i in range(0, len(data), 16):
        blk = bytes(data[i + j] ^ prev[j] for j in range(16))
        enc = _aes_enc_block(w, blk)
        out += enc
        prev = enc
    return out


def _aes_cbc_decrypt(key, iv, data):
    w = _aes_expand_key(key)
    out = b""
    prev = iv
    for i in range(0, len(data), 16):
        blk = data[i:i + 16]
        dec = _aes_dec_block(w, blk)
        out += bytes(dec[j] ^ prev[j] for j in range(16))
        prev = blk
    if out:
        pad = out[-1]
        if 1 <= pad <= 16:
            out = out[:-pad]
    return out


_KEY_B = APP_KEY.encode("utf-8")
_IV_B = APP_IV.encode("utf-8")



def _md5_hex(s):
    return hashlib.md5(str(s).encode("utf-8")).hexdigest()


def _make_uuid():
    hexs = []
    for _ in range(32):
        hexs.append("0123456789abcdef"[random.randint(0, 15)])
    s = "".join(hexs)
    return s[0:8] + "-" + s[8:12] + "-4" + s[13:16] + "-a" + s[17:20] + "-" + s[20:32]


def _enc_uri_component(v):
    return quote(str(v), safe="-_.!~*'()")


def _enc_query(params):
    if not params:
        return ""
    parts = []
    for k, v in params.items():
        if v is None or v == "":
            continue
        parts.append(_enc_uri_component(k) + "=" + _enc_uri_component(v))
    return "&".join(parts)


def _clean(s):
    out = str(s) if s is not None else ""
    out = re.sub(r"<[^>]*>", " ", out)
    out = out.replace("&nbsp;", " ")
    out = out.replace("&amp;", "&")
    out = out.replace("&quot;", '"')
    out = out.replace("&#39;", "'")
    out = out.replace("&lt;", "<")
    out = out.replace("&gt;", ">")
    return re.sub(r"\s+", " ", out).strip()


def _pick(*vals):
    for v in vals:
        if v is not None and str(v).strip() != "":
            return v
    return ""


def _parse_int(v):
    if v is None or isinstance(v, bool):
        return 0
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    m = re.match(r"^[+-]?\d+", str(v).lstrip())
    if not m:
        return 0
    try:
        return int(m.group(0))
    except Exception:
        return 0


def _truthy(v):
    if v is None or v is False:
        return False
    if isinstance(v, (int, float)) and v == 0:
        return False
    if isinstance(v, str) and v == "":
        return False
    return True


def _js_or(*vals):
    for v in vals:
        if _truthy(v):
            return v
    return None


def _parse_payload(text):
    if text is None:
        return None
    s = str(text).strip()
    if not s:
        return None
    if s.startswith("{"):
        try:
            return json.loads(s)
        except Exception:
            return None
    try:
        plain = _aes_cbc_decrypt(_KEY_B, _IV_B, base64.b64decode(s))
        return json.loads(plain.decode("utf-8"))
    except Exception:
        return None


def _episode_name(name):
    return str(name or "").replace("$", "_").replace("#", "_")


def _month_start(offset):
    off = _parse_int(offset)
    today = datetime.date.today()
    y = today.year
    m = today.month - off
    while m <= 0:
        m += 12
        y -= 1
    while m > 12:
        m -= 12
        y += 1
    return "%04d-%02d-01" % (y, m)


def _month_label(offset):
    off = _parse_int(offset)
    today = datetime.date.today()
    y = today.year
    m = today.month - off
    while m <= 0:
        m += 12
        y -= 1
    while m > 12:
        m -= 12
        y += 1
    return str(y) + "年" + str(m) + "月"


_LIVE_TAG_RE = re.compile(r"^\[(ONE\s*直播[^\]]*)\]\s*", re.I)
_KANA_RE = re.compile(r"[぀-ヿ]")
_CJK_RE = re.compile(r"[㐀-鿿]")
_LAT_RE = re.compile(r"[a-z]", re.I)
_CODE_RE = re.compile(r"\b[a-z]{2,5}[-_]\d{2,5}\b", re.I)
_TAG_US = re.compile(r"^(欧美|美国|英国|德国|法国|意大利|西班牙|荷兰|瑞典|瑞士|奥地利|波兰|捷克|匈牙利|罗马尼亚|保加利亚|俄罗斯|乌克兰|白俄罗斯|拉脱维亚|立陶宛|爱沙尼亚|巴西|墨西哥|阿根廷|哥伦比亚|秘鲁|智利|古巴|委内瑞拉|拉美|拉丁|加拿大|澳洲|澳大利亚|新西兰|印度|泰国|越南|菲律宾|印尼|马来西亚|阿拉伯|异域|土耳其|迪拜|以色列|伊朗|黑人|金发|白人|碧眼|西方|外国|欧美无码|欧美精品)$")
_TAG_JP = re.compile(r"^(日本|日系|日韩|日本无码|日本精品)$")
_TAG_CN = re.compile(r"^(国产|国语|华语|国产精品|国产无码|港台|台湾|香港|新加坡)$")
_CLASSIFY_US_RE = re.compile(r"(p站|pornhub|onlyfans|fansly|faphouse|pjgirls|deeper|tushy|vixen|blacked|brazzers|realitykings|naught(y|iamerica)|bangbros|teamskeet|mylf|chaturbate|cb站|推特|x站|洋马|白人|金发|碧眼|欧美|美国|英国|德国|法国|俄罗斯|乌克兰|巴西|拉美|拉丁|大洋马|洋妞|老外|外国|bbc|bwc|尼哥|黑大炮|捷克|西班牙|意大利|加拿大|澳洲|印度|泰国|越南|菲律宾|印尼|马来西亚|阿拉伯|异域|土耳其|迪拜|以色列|韩国|韩系|波兰|匈牙利|罗马尼亚|latina|ebony|russian|blonde)", re.I)
_CLASSIFY_JP_RE = re.compile(r"(无码|有码|人妻|女优|痴女|素人|日系|日本|和服|风俗|fc2|heyzo|jav|myfans|oppai|s1|sod|falen|moodyz|prestige|ideapocket|ipx|ssni|miaa|madonna|ダスッ|カリ比アン|加勒比|一本道|天然むすめ|tokyo\s*hot|10musume|heydouga|无修正|中文字幕|熟女|女教师|痴汉|电车|东京|大阪|温泉)", re.I)
_CLASSIFY_CN_RE = re.compile(r"(ai短剧|短剧|探花|门事件|绿播|福利姬|网红|主播|大秀|微密圈|抖音|快手|b站|私拍|旗袍|学生妹|御姐|大圈|传媒|天美|麻豆|星空|糖心|91|抖阴|杏吧|蜜桃|精东|国产|国语|华语|coser|cosplay|推特福利|私人订制|定制合集)", re.I)
_STRONG_US = re.compile(r"(p站|onlyfans|fansly|faphouse|pjgirls|deeper|tushy|vixen|blacked|brazzers|realitykings|bangbros|teamskeet|mylf|chaturbate|cb站|推特|fansone|manyvids)", re.I)
_STRONG_CN = re.compile(r"(ai短剧|短剧|探花|门事件|绿播|微密圈|抖音|快手|b站|91|抖阴|杏吧|麻豆|天美|糖心|精东|国语|华语|国产精品)", re.I)
_PREVIEW_FILE_RE = re.compile(r"preview|sample|_pr\.mp4|-pr\.mp4", re.I)
_GIF_RE = re.compile(r"\.gif(\?|$)", re.I)
_H265_RE = re.compile(r"h265", re.I)


def _strip_live_tag(title):
    t = str(title or "")
    m = _LIVE_TAG_RE.match(t)
    if not m:
        return (t, False)
    return (t[m.end():].strip(), True)


def _model_name(mid):
    m = _parse_int(mid)
    if m == 1:
        return "图集"
    if m == 2 or m == 3:
        return "视频"
    if m == 4:
        return "图文"
    if m == 5:
        return "音频"
    if m == 6:
        return "长视频"
    return "内容"


def _size_label(v):
    n = _parse_int(v)
    if not n:
        return ""
    if n >= 1073741824:
        return "%.1f GB" % (n / 1073741824.0)
    if n >= 1048576:
        return str(int(round(n / 1048576.0))) + " MB"
    if n >= 1024:
        return str(int(round(n / 1024.0))) + " KB"
    return str(n) + " B"


def _duration_seconds(a):
    if not a:
        return 0
    v = _parse_int(_js_or(a.get("video_length"), a.get("length"), a.get("duration")))
    return v if v > 0 else 0


def _seconds_to_text(sec):
    sec = _parse_int(sec)
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60

    def p(n):
        return ("0" if n < 10 else "") + str(n)

    return ((str(h) + ":") if h else "") + p(m) + ":" + p(s)


def _tag_list(a):
    arr = (a or {}).get("tags")
    if not arr and a:
        arr = a.get("tag_list")
    out = []
    for t in arr or []:
        if isinstance(t, str):
            v = t
        elif isinstance(t, dict):
            v = t.get("slug") or t.get("name") or t.get("title") or t.get("tag_name") or ""
        else:
            v = ""
        v = re.sub(r"\s+", " ", str(v)).strip()
        if v and v not in out:
            out.append(v)
    return out


def _region_by_tags(a):
    tags = _tag_list(a)
    us = 0
    jp = 0
    cn = 0
    for t in tags:
        if _TAG_US.search(t):
            us += 1
        elif _TAG_JP.search(t):
            jp += 1
        elif _TAG_CN.search(t):
            cn += 1
    if us and us >= jp and us >= cn:
        return "us"
    if jp and jp >= cn:
        return "jp"
    if cn:
        return "cn"
    return ""


def _classify_by_text(a):
    title = str(_pick(a.get("title"), a.get("video_name"), "") or "")
    t = title + " " + str(a.get("author") or "")
    low = t.lower()
    if _KANA_RE.search(t):
        return "jp"
    if _CLASSIFY_US_RE.search(low):
        return "us"
    if _CODE_RE.search(low):
        return "jp"
    if _CLASSIFY_JP_RE.search(t):
        return "jp"
    if _CLASSIFY_CN_RE.search(t):
        return "cn"
    cjk = len(_CJK_RE.findall(t))
    lat = len(_LAT_RE.findall(t))
    if lat > cjk * 1.5 and lat > 6:
        return "us"
    return "cn"


def _classify_part(a):
    title = str(_pick(a.get("title"), a.get("video_name"), "") or "")
    if "[ONE直播" in title:
        return "live"
    if re.search(r"直播回放", title) and re.search(r"one直播", title, re.I):
        return "live"
    if _STRONG_US.search(title):
        return "us"
    if _STRONG_CN.search(title):
        return "cn"
    if _KANA_RE.search(title):
        return "jp"
    if _CODE_RE.search(title):
        return "jp"
    by_tag = _region_by_tags(a)
    if by_tag:
        return by_tag
    return _classify_by_text(a)


def _is_preview_only(a):
    if a is None:
        return True
    if str(a.get("video_download") or ""):
        return False
    f = str(a.get("video_file") or "")
    if not f:
        if not str(a.get("preview_video") or ""):
            return False
        return True
    if str(a.get("preview_video") or "") == f:
        return True
    if _PREVIEW_FILE_RE.search(f):
        return True
    return False


_COMPACT_KEYS = [
    "id", "model_id", "title", "video_name", "author", "published_at", "views", "like_number",
    "collection_number", "is_limit_free", "size", "video_length", "length", "duration", "description",
    "tags", "thumbnail", "thumb", "video_cover", "cover", "thumb_tiny",
    "multi_pic_thumbnail", "thumbnail_list", "video_download", "video_file", "preview_video",
]


def _compact_article(a):
    if not a:
        return a
    o = {}
    for k in _COMPACT_KEYS:
        if k in a and a[k] is not None:
            o[k] = a[k]
    if o.get("description"):
        o["description"] = str(o["description"])[:160]
    return o


def _host_is_bad(h):
    for b in BAD_HOSTS:
        if b in str(h):
            return True
    return False


def _path_of(url):
    m = re.match(r"^https?://[^/]+(/.*)$", str(url or ""))
    return m.group(1) if m else str(url or "")



class _MonthBook:
    def __init__(self, spider):
        self.sp = spider
        self.months = {}
        self.hot_cache = {}

    def state(self, offset):
        st = self.months.get(offset)
        if st is None:
            st = {"items": [], "seen": set(), "p6": 1, "p3": 1, "d6": False, "d3": False}
            self.months[offset] = st
        return st

    def step(self, offset):
        st = self.state(offset)
        if not st["d6"] and (st["d3"] or st["p6"] <= st["p3"]):
            model, page = 6, st["p6"]
        elif not st["d3"]:
            model, page = 3, st["p3"]
        else:
            return False
        arr = self.sp._fetch_month_page(model, offset, page, 40, "published_at")
        if len(arr) < 40:
            if model == 6:
                st["d6"] = True
            else:
                st["d3"] = True
        if model == 6:
            st["p6"] = page + 1
        else:
            st["p3"] = page + 1
        for it in arr:
            if not isinstance(it, dict):
                continue
            iid = str(it.get("id"))
            if iid in st["seen"]:
                continue
            if _is_preview_only(it):
                continue
            st["seen"].add(iid)
            st["items"].append(_compact_article(it))
        return not (st["d6"] and st["d3"])

    def done(self, offset):
        st = self.state(offset)
        return bool(st["d6"] and st["d3"])

    def items(self, offset):
        st = self.state(offset)
        return sorted(st["items"], key=lambda a: str(a.get("published_at") or ""), reverse=True)

    def partition(self, pid, offset):
        return [a for a in self.items(offset) if _classify_part(a) == pid]

    def hot_month(self, offset):
        if offset in self.hot_cache:
            return self.hot_cache[offset]
        arr = []
        seen = set()
        for model in (6, 3):
            chunk = self.sp._fetch_month_page(model, offset, 1, 60, "like_number")
            for it in chunk:
                if not isinstance(it, dict):
                    continue
                iid = str(it.get("id"))
                if iid in seen:
                    continue
                if _is_preview_only(it):
                    continue
                seen.add(iid)
                arr.append(it)
        arr = sorted(arr, key=lambda a: -_parse_int(a.get("like_number")))
        self.hot_cache[offset] = arr
        return arr


class Spider(BaseSpider):
    def __init__(self):
        super().__init__()
        self.siteUrl = SEED_HOSTS[0]
        self._custom_host = ""
        self._uuid = _make_uuid()
        self._token = ""
        self._host = ""
        self._api = []
        self._image = []
        self._resource = []
        self._fimg = []
        self._video = []
        self._video_hls = []
        self._audio = []
        self._vplay = []
        self._vdl = []
        self._audl = []

    def init(self, extend=""):
        host = ""
        if isinstance(extend, dict):
            host = str(extend.get("host") or "")
        elif isinstance(extend, str) and extend.strip():
            try:
                parsed = json.loads(extend)
                if isinstance(parsed, dict):
                    host = str(parsed.get("host") or "")
            except Exception:
                host = ""
        host = host.strip()
        if host.startswith("http"):
            self._custom_host = host.rstrip("/")
            self.siteUrl = self._custom_host
        return self.siteUrl

    def getName(self):
        return "ONE"

    def isVideoFormat(self, url):
        low = str(url or "").lower()
        return (".m3u8" in low) or (".mp4" in low) or (".flv" in low) or (".mpd" in low)

    def manualVideoCheck(self):
        return False

    # ============ session / transport (ported from JS) ============

    def _headers(self, token=None):
        ts = str(int(time.time()))
        sign = _md5_hex(_md5_hex("0.0.0.0.3." + ts + ".." + self._uuid) + SIGN_SALT)
        return {
            "platform": "3",
            "uuid": self._uuid,
            "timestamp": ts,
            "token": self._token if token is None else token,
            "app-version": APP_VERSION,
            "sign": sign,
            "user-key": "",
            "ip": "0.0.0.0",
            "User-Agent": DEFAULT_UA,
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def _post_raw(self, host, path, params, token=None):
        qs = _enc_query(params)
        body = ""
        if qs:
            body = base64.b64encode(_aes_cbc_encrypt(_KEY_B, _IV_B, qs.encode("utf-8"))).decode("ascii")
        resp = requests.post(host + "/v2.5/" + path, data=body.encode("utf-8"), headers=self._headers(token), timeout=TIMEOUT)
        if resp is None or resp.status_code < 200 or resp.status_code >= 300:
            raise Exception("ONE http " + str(resp.status_code if resp is not None else ""))
        return _parse_payload(resp.text)

    def _host_candidates(self):
        out = []
        for h in [self._custom_host, self._host] + list(self._api) + list(SEED_HOSTS):
            h = str(h or "").rstrip("/")
            if h and h not in out:
                out.append(h)
        return out

    def _apply_domains(self, domain):
        if not isinstance(domain, dict):
            return

        def take(key, attr):
            v = domain.get(key)
            if isinstance(v, list) and v:
                setattr(self, attr, list(v))

        take("api", "_api")
        take("image", "_image")
        take("resource", "_resource")
        take("flutter_img", "_fimg")
        take("video", "_video")
        take("video_hls", "_video_hls")
        take("audio", "_audio")
        take("flutter_video_play", "_vplay")
        take("flutter_video_download", "_vdl")
        take("audio_download", "_audl")

    def _bootstrap(self, force=False):
        if not force and self._token and self._host:
            return
        last_err = None
        for h in self._host_candidates():
            try:
                js = self._post_raw(h, "bootstrap", None, token="")
                if js and js.get("code") == 200 and js.get("data"):
                    data = js["data"]
                    user = data.get("user") or {}
                    self._host = h
                    self.siteUrl = h
                    self._token = str(user.get("token") or "")
                    self._apply_domains(data.get("domain"))
                    return
                last_err = Exception("bootstrap " + str(js.get("code") if isinstance(js, dict) else js))
            except Exception as e:
                last_err = e
        raise last_err or Exception("ONE 初始化失败")

    def _call(self, path, params):
        retried = False
        bootstrapped = bool(self._token)
        last_err = None
        for _attempt in range(3):
            for h in self._host_candidates():
                try:
                    js = self._post_raw(h, path, params)
                    if js is None:
                        last_err = Exception("empty response")
                        continue
                    if js.get("code") == 200:
                        self._host = h
                        self.siteUrl = h
                        return js.get("data")
                    if js.get("code") == 401:
                        last_err = Exception("401 " + str(js.get("message") or ""))
                        break
                    raise Exception("ONE " + str(js.get("code")) + " " + str(js.get("message") or ""))
                except Exception as e:
                    last_err = e
            if not retried and (("401" in str(last_err)) or not bootstrapped):
                retried = True
                self._bootstrap(True)
                bootstrapped = True
                continue
            raise last_err or Exception("ONE 请求失败")
        raise Exception("ONE 请求失败")

    def _fetch_month_page(self, model, offset, page, size, sort_mode):
        try:
            arr = self._call("article/discovery", {
                "model_id": model,
                "published_at": _month_start(offset),
                "page": page,
                "size": size,
                "sort": sort_mode or "published_at",
            })
            return arr if isinstance(arr, list) else []
        except Exception:
            return []

    def _fetch_article(self, aid):
        data = self._call("article/detail", {"id": aid})
        if not data:
            raise Exception("ONE 未返回详情：" + str(aid))
        return data

    # ============ image / video lines (ported from JS) ============

    def _img_hosts(self):
        out = []

        def add(arr):
            for h in arr or []:
                h = str(h or "").rstrip("/")
                if not h or h in out or _host_is_bad(h):
                    continue
                out.append(h)

        add(self._fimg)
        add(self._resource)
        add(PLAIN_HOSTS)
        return out

    def _pick_img_host(self, p):
        hosts = self._img_hosts()
        if not hosts:
            return "https://img807.hkq57tt.com"
        h = 0
        for ch in p:
            h = (h * 31 + ord(ch)) & 0xFFFFFFFF
        return hosts[h % len(hosts)]

    def _abs_image(self, path):
        if not path:
            return ""
        p = str(path)
        if re.match(r"^https?://", p):
            for eh in ENC_HOSTS:
                if eh in p:
                    return self._pick_img_host(_path_of(p)) + _path_of(p)
            return p
        return self._pick_img_host(p) + ("" if p.startswith("/") else "/") + p

    def _best_image(self, a):
        if not a:
            return ""
        cands = [a.get("thumbnail"), a.get("thumb"), a.get("video_cover"), a.get("cover"), a.get("thumb_tiny")]
        if isinstance(a.get("multi_pic_thumbnail"), list) and a.get("multi_pic_thumbnail"):
            cands = cands + list(a["multi_pic_thumbnail"])
        if isinstance(a.get("thumbnail_list"), list) and a.get("thumbnail_list"):
            cands = cands + list(a["thumbnail_list"])
        gif = ""
        for c in cands:
            u = self._abs_image(c)
            if not u:
                continue
            if _GIF_RE.search(u):
                if not gif:
                    gif = u
                continue
            return u
        if gif:
            return IMG_PROXY + quote(gif, safe="") + "&output=jpg&w=520"
        return ""

    def _video_hosts(self):
        out = []

        def add(arr):
            for h in arr or []:
                h = str(h or "").rstrip("/")
                if not h or h in out or _host_is_bad(h):
                    continue
                out.append(h)

        add(self._video)
        add(self._vdl)
        add(self._vplay)
        add(self._audl)
        add(self._audio)
        if not out:
            out = ["https://46e9nz.mfpt8g.com", "https://f86xxm.upmf83.com"]
        return out

    def _abs_video(self, path, kind=None):
        if not path:
            return ""
        p = str(path)
        if re.match(r"^https?://", p):
            return p
        if kind == "hls":
            hosts = self._video_hls
        elif kind == "audio":
            hosts = self._audio
        else:
            hosts = self._video
        if not hosts:
            hosts = [VIDEO_FALLBACK_HOST]
        return hosts[0] + ("" if p.startswith("/") else "/") + p

    def _line_groups(self, a):
        groups = []
        hosts = self._video_hosts()

        def mp4_urls(path):
            if not path:
                return []
            p = str(path)
            if re.match(r"^https?://", p):
                return [p]
            urls = []
            for i in range(min(len(hosts), 5)):
                urls.append(hosts[i] + ("" if p.startswith("/") else "/") + p)
            return urls

        preview_only = _is_preview_only(a)
        dl = mp4_urls(a.get("video_download"))
        if dl:
            groups.append({"kind": "dl", "name": " ", "urls": dl})
        vf = mp4_urls(a.get("video_file"))
        if vf and str(a.get("video_file")) != str(a.get("video_download") or ""):
            groups.append({"kind": "file", "name": "预告 MP4" if preview_only else " ", "urls": vf})
        if (not dl and not vf) or preview_only:
            if a.get("video_hls"):
                groups.append({"kind": "hls", "name": "HLS 备用", "urls": [self._abs_video(a.get("video_hls"), "hls")]})
            if a.get("video_hls_h265"):
                groups.append({"kind": "hls265", "name": "HLS H.265 备用", "urls": [self._abs_video(a.get("video_hls_h265"), "hls")]})
        if a.get("audio_file"):
            groups.append({"kind": "audio", "name": "音频专线", "urls": [self._abs_video(a.get("audio_file"), "audio")]})
        if a.get("audio_hls"):
            groups.append({"kind": "audiohls", "name": "音频 HLS", "urls": [self._abs_video(a.get("audio_hls"), "hls")]})
        if not groups and a.get("preview_video"):
            groups.append({"kind": "preview", "name": "精彩预览", "urls": [self._abs_video(a.get("preview_video"))]})
        return groups

    def _flat_lines(self, a):
        lines = []
        for g in self._line_groups(a):
            for i, u in enumerate(g["urls"]):
                nm = g["name"] + " · 线路 " + str(i + 1) if len(g["urls"]) > 1 else g["name"]
                if _H265_RE.search(u):
                    nm += "（H.265）"
                lines.append({"kind": g["kind"], "name": nm, "url": u})
        return lines

    # ============ item shaping (ported from JS) ============

    def _article_status(self, a, prefix=""):
        live = _strip_live_tag(_clean(_pick(a.get("title"), a.get("video_name"), "")))
        bits = [BRAND]
        if prefix:
            bits.append(prefix)
        bits.append("直播回放" if live[1] else _model_name(a.get("model_id")))
        if a.get("author"):
            bits.append(_clean(a.get("author")))
        if a.get("published_at"):
            bits.append(str(a.get("published_at"))[:10])
        if _truthy(a.get("views")):
            bits.append("观看 " + str(a.get("views")))
        sl = _size_label(a.get("size"))
        if sl:
            bits.append(sl)
        sec = _duration_seconds(a)
        if sec > 0:
            bits.append(_seconds_to_text(sec))
        return " | ".join(bits)

    def _to_card(self, a, prefix=""):
        live = _strip_live_tag(_clean(_pick(a.get("title"), a.get("video_name"), "ONE #" + str(a.get("id")))))
        card = {
            "vod_id": str(a.get("id")),
            "vod_name": live[0],
            "vod_pic": self._best_image(a),
            "vod_remarks": self._article_status(a, prefix),
            "style": {"type": "rect", "ratio": POSTER_RATIO},
        }
        tags = _tag_list(a)
        if tags:
            card["vod_class"] = ",".join(tags[:8])
        return card

    def _desc_tail(self, a):
        bits = [_model_name(a.get("model_id"))]
        if a.get("author"):
            bits.append(_clean(a.get("author")))
        if a.get("published_at"):
            bits.append(str(a.get("published_at"))[:10])
        if _truthy(a.get("views")):
            bits.append("观看 " + str(a.get("views")))
        if _truthy(a.get("like_number")):
            bits.append("赞 " + str(a.get("like_number")))
        if _truthy(a.get("collection_number")):
            bits.append("收藏 " + str(a.get("collection_number")))
        if _truthy(a.get("is_limit_free")):
            bits.append("限时免费")
        dsec = _duration_seconds(a)
        if dsec > 0:
            bits.append(_seconds_to_text(dsec))
        sl = _size_label(a.get("size"))
        if sl:
            bits.append(sl)
        head = " · ".join(bits)
        body = _clean(_pick(a.get("description"), a.get("video_name")))
        return (head + "\n\n【简介】\n" + body) if body else head

    def _brand_block(self):
        lines = [
          
                ]
        return "\n".join(lines)

    # ============ accumulated feeds (ported from JS) ============

    def _serve(self, entries, page, size):
        frm = (page - 1) * size
        out = []
        for e in entries[frm:frm + size]:
            out.append(self._to_card(e["a"], e.get("p") or ""))
        return out

    def _newest_items(self, book, page, size):
        st = {"items": [], "seen": set(), "off": 0, "emptyRun": 0, "done": False}
        need = page * size
        nsteps = 0
        while len(st["items"]) < need and not st["done"] and st["off"] < 400:
            arr = book.items(st["off"])
            nadded = 0
            label = _month_label(st["off"])
            for a in arr:
                key = str(a.get("id"))
                if key in st["seen"]:
                    continue
                st["seen"].add(key)
                st["items"].append({"a": a, "p": label})
                nadded += 1
            if len(st["items"]) >= need:
                break
            if not book.done(st["off"]):
                if nsteps >= 3:
                    break
                nsteps += 1
                book.step(st["off"])
                continue
            if not arr and not nadded:
                st["emptyRun"] += 1
                if st["emptyRun"] >= 8:
                    st["done"] = True
                    break
            else:
                st["emptyRun"] = 0
            st["off"] += 1
        return self._serve(st["items"], page, size)

    def _hot_items(self, book, page, size):
        st = {"items": [], "seen": set(), "off": 0, "emptyRun": 0, "done": False}
        need = page * size
        while len(st["items"]) < need and not st["done"] and st["off"] < 400:
            arr = book.hot_month(st["off"])
            if not arr:
                st["emptyRun"] += 1
                st["off"] += 1
                if st["emptyRun"] >= 8:
                    st["done"] = True
                continue
            st["emptyRun"] = 0
            label = _month_label(st["off"]) + " 热门"
            for a in arr:
                key = str(a.get("id"))
                if key in st["seen"]:
                    continue
                st["seen"].add(key)
                st["items"].append({"a": a, "p": label})
            st["off"] += 1
        return self._serve(st["items"], page, size)

    def _region_items(self, book, pid, page, size):
        st = {"items": [], "seen": set(), "off": 0, "emptyRun": 0, "done": False}
        need = page * size
        steps = 0
        while len(st["items"]) < need and not st["done"] and st["off"] < 400:
            arr = book.partition(pid, st["off"])
            added = 0
            label = _month_label(st["off"])
            for a in arr:
                key = str(a.get("id"))
                if key in st["seen"]:
                    continue
                st["seen"].add(key)
                st["items"].append({"a": a, "p": label})
                added += 1
            if len(st["items"]) >= need:
                break
            if not book.done(st["off"]):
                if steps >= 3:
                    break
                steps += 1
                book.step(st["off"])
                continue
            if not arr and not added:
                st["emptyRun"] += 1
                if st["emptyRun"] >= 8:
                    st["done"] = True
                    break
            else:
                st["emptyRun"] = 0
            st["off"] += 1
        return self._serve(st["items"], page, size)

    def _live_items(self, page, size):
        data = self._call("article/search", {
            "keyword": "ONE直播",
            "model_id": 0,
            "series_category": 0,
            "page": page,
            "size": size,
        })
        out = []
        if isinstance(data, list):
            for a in data:
                if isinstance(a, dict):
                    out.append(self._to_card(a))
        return out

    # ============ container entry points ============

    def _to_page(self, pg):
        try:
            page = int(pg)
        except Exception:
            page = 1
        if page < 1:
            page = 1
        return page

    def _page_form(self, page, cards, limit):
        n = len(cards)
        if n == 0:
            return {"page": page, "pagecount": page, "limit": 1, "total": 0, "list": []}
        return {"page": page, "pagecount": page + 1, "limit": limit, "total": (page + 1) * limit, "list": cards}

    def homeContent(self, filter):
        classes = [{"type_id": cid, "type_name": cname} for cid, cname in CATEGORIES]
        return {"class": classes}

    def homeVideoContent(self):
        try:
            self._bootstrap(False)
            book = _MonthBook(self)
            return {"list": self._newest_items(book, 1, PAGE_SIZE)}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg, filter, extend):
        page = self._to_page(pg)
        cat = str(tid or "").strip() or "newest"
        cards = []
        try:
            self._bootstrap(False)
            book = _MonthBook(self)
            if cat == "newest":
                cards = self._newest_items(book, page, PAGE_SIZE)
            elif cat == "hot":
                cards = self._hot_items(book, page, PAGE_SIZE)
            elif cat == "live":
                cards = self._live_items(page, PAGE_SIZE)
            elif cat in PARTITION_IDS:
                cards = self._region_items(book, cat, page, PAGE_SIZE)
            else:
                cards = []
        except Exception:
            cards = []
        result = self._page_form(page, cards, PAGE_SIZE)
        result["type_id"] = cat
        return result

    def searchContent(self, key, quick, pg="1"):
        page = self._to_page(pg)
        kw = _clean(str(key or ""))
        if not kw:
            return {"page": page, "pagecount": page, "limit": 1, "total": 0, "list": []}
        cards = []
        try:
            self._bootstrap(False)
            data = self._call("article/search", {
                "keyword": kw,
                "model_id": 0,
                "series_category": 0,
                "page": page,
                "size": PAGE_SIZE,
            })
            if isinstance(data, list):
                cards = [self._to_card(a) for a in data if isinstance(a, dict)]
        except Exception:
            cards = []
        return self._page_form(page, cards, PAGE_SIZE)

    def detailContent(self, ids):
        if isinstance(ids, (list, tuple)):
            raw = str(ids[0]) if ids else ""
        else:
            raw = str(ids or "")
        raw = raw.strip()
        if not raw:
            return {"list": [], "msg": "缺少内容 ID"}
        aid = raw
        try:
            self._bootstrap(False)
            a = self._fetch_article(aid)
        except Exception as e:
            return {"list": [], "msg": str(e) or "ONE 请求失败"}
        live = _strip_live_tag(_clean(_pick(a.get("title"), a.get("video_name"), "ONE #" + aid)))
        cover = self._best_image(a)
        lines = self._flat_lines(a)
        tags = _tag_list(a)
        content = self._brand_block() + "\n" + self._desc_tail(a)
        vod = {
            "vod_id": raw,
            "vod_name": live[0],
            "vod_pic": cover,
            "vod_bg": cover,
            "vod_background": cover,
            "vod_banner": cover,
            "vod_actor": _clean(a.get("author")) if a.get("author") else BRAND_ACTOR,
            "vod_remarks": self._article_status(a),
            "vod_content": content,
            "vod_play_from": LINE_NAME,
        }
        if tags:
            vod["vod_class"] = ",".join(tags[:12])
        if a.get("published_at"):
            vod["vod_year"] = str(a.get("published_at"))[:4]
        if lines:
            eps = []
            for ln in lines:
                env = {"u": ln["url"], "h": self._host or self.siteUrl}
                eps.append(_episode_name(ln["name"]) + "$" + json.dumps(env, ensure_ascii=False))
            vod["vod_play_url"] = "#".join(eps)
        else:
            vod["vod_content"] = content + "\n" + NO_SOURCE_NOTE
            env = {"notice": NO_SOURCE_NOTE}
            vod["vod_play_url"] = _episode_name("暂无播放源") + "$" + json.dumps(env, ensure_ascii=False)
        return {"list": [vod]}

    def playerContent(self, flag, id, vipFlags):
        raw = str(id or "").strip()
        if raw.startswith("{"):
            obj = None
            try:
                obj = json.loads(raw)
            except Exception:
                obj = None
            if isinstance(obj, dict):
                if obj.get("notice"):
                    return {"parse": 0, "msg": str(obj["notice"])}
                url = str(obj.get("u") or "").strip()
                host = str(obj.get("h") or "").strip() or self.siteUrl
                if url:
                    return {"parse": 0, "jx": 0, "url": url, "header": {"User-Agent": DEFAULT_UA, "Referer": host.rstrip("/") + "/"}}
                return {"parse": 0, "jx": 0, "url": "", "msg": "缺少播放地址"}
        if raw.startswith("http"):
            return {"parse": 0, "jx": 0, "url": raw, "header": {"User-Agent": DEFAULT_UA, "Referer": self.siteUrl.rstrip("/") + "/"}}
        return {"parse": 0, "jx": 0, "url": "", "msg": "缺少播放地址"}

    def liveContent(self, url):
        return ""

    def localProxy(self, params):
        return [404, "text/plain; charset=utf-8", "Not Found"]

# --- System Signature ---
#‍​​‌‌‌​​​​​‌‌‌​​‌​​‌‌​‌‌‌​​‌‌​‌​​​​‌‌​‌​‌​​‌‌​‌​​​​‌‌​‌‌​​​‌‌​‌​​​​‌‌​​‌​​​‌‌​‌‌​‍
# Source: https://sub.lytvs.top/trap?token=tk_0c32cd61&t=1795709256789&sig=c7bf4c43e68698ec
