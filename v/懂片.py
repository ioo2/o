# -*- coding: utf-8 -*-
import sys
import json
import time
import hmac
import hashlib
import os
import requests
sys.path.append('..')
try:
    from base.spider import Spider as BaseSpider
except Exception:
    BaseSpider = None
requests.packages.urllib3.disable_warnings()
if BaseSpider is None:
    class BaseSpider(object):
        def __init__(self):
            self.extend = ''
        def init(self, extend=""):
            pass
        def getName(self):
            return ""
        def isVideoFormat(self, url):
            return False
        def manualVideoCheck(self):
            return False
        def destroy(self):
            pass
        def localProxy(self, param):
            return None
        def fetch(self, url, params=None, headers=None, cookies=None,
                  timeout=15, verify=False, encoding="utf-8", **kwargs):
            resp = requests.get(url, params=params, headers=headers,
                                cookies=cookies, timeout=timeout,
                                verify=verify, **kwargs)
            resp.encoding = encoding
            return resp
class Spider(BaseSpider):
    SIGN_KEY = "8b9a908a05eac640e1ee06f52acaa741bfe4ba9e004eeffdbeb635e532e06666"
    KINDS = [
        ("series", "剧集"),
        ("anime", "动漫"),
        ("movie", "电影"),
        ("variety", "综艺"),
        ("short_drama", "短剧"),
    ]
    WINDOWS = [
        ("day", "日榜"),
        ("week", "周榜"),
        ("month", "月榜"),
        ("total", "总榜"),
    ]
    def __init__(self):
        try:
            super().__init__()
        except Exception:
            pass
        self.host = "https://dongpian17.com"
        self.name = "懂片帝"
        self.ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"
        self.session = requests.Session()
        self.account = ""
        self.password = ""
        self.cookie_str = ""
        self._logged_in = False
    def init(self, extend=""):
        try:
            super().init(extend)
        except Exception:
            pass
        try:
            if not extend:
                extend = getattr(self, 'extend', '')
            if isinstance(extend, str):
                try:
                    ext = json.loads(extend) if extend.strip() else {}
                except Exception:
                    ext = {}
            elif isinstance(extend, dict):
                ext = extend
            else:
                ext = {}
            self.host = ext.get("host", self.host).rstrip("/")
            self.name = ext.get("name", self.name)
            self.ua = ext.get("ua", self.ua)
            self.account = ext.get("account", self.account)
            self.password = ext.get("password", self.password)
            self.cookie_str = ext.get("cookie", self.cookie_str)
            if self.cookie_str:
                self._apply_cookie(self.cookie_str)
                self._logged_in = True
        except Exception:
            pass
    def _apply_cookie(self, cookie_str):
        try:
            for kv in cookie_str.split(";"):
                kv = kv.strip()
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    self.session.cookies.set(k.strip(), v.strip())
        except Exception:
            pass
    def _login(self):
        if not self.account or not self.password:
            return False
        try:
            path = "/v1/users/password/login"
            headers = self._headers("POST", path, "")
            headers["Content-Type"] = "application/json"
            resp = self.session.post(self.host + path, headers=headers,
                                     json={"account": self.account, "password": self.password},
                                     timeout=15, verify=False)
            data = json.loads(resp.text)
            if resp.status_code == 200 and not data.get("error"):
                self._logged_in = True
                return True
        except Exception:
            pass
        return False
    def _anonymous_login(self):
        try:
            import uuid
            path = "/v1/users/anonymous"
            headers = self._headers("POST", path, "")
            headers["Content-Type"] = "application/json"
            anon_id = "web_{}".format(uuid.uuid4())
            resp = self.session.post(self.host + path, headers=headers,
                                     json={"anonymous_id": anon_id},
                                     timeout=15, verify=False)
            if resp.status_code in (200, 201):
                self._logged_in = True
                return True
        except Exception:
            pass
        return False
    def _ensure_login(self):
        if self._logged_in:
            return True
        if self.account and self.password:
            return self._login()
        return self._anonymous_login()
    def _headers(self, method, path, search):
        ts = str(int(time.time() * 1000))
        nonce = os.urandom(16).hex()
        msg = "{}\n{}{}\n{}\n{}".format(method, path, search, ts, nonce)
        sign = hmac.new(self.SIGN_KEY.encode(), msg.encode(), hashlib.sha256).hexdigest()
        return {
            "User-Agent": self.ua,
            "Accept": "application/json",
            "x-ai-movie-client-name": "movie-search-frontend",
            "x-ai-movie-client-version": "1.0.0",
            "x-ai-movie-build-version": "dongpiandi-v2026.10.04.1-episode-resume-efd9a7f2e87e-web",
            "x-ai-movie-protocol-version": "2026-07-05.library-v2.playback-v1",
            "x-ai-movie-timestamp": ts,
            "x-ai-movie-nonce": nonce,
            "x-ai-movie-signature": sign,
        }
    def _get(self, path, search=""):
        try:
            resp = self.session.get(self.host + path + search,
                                    headers=self._headers("GET", path, search),
                                    timeout=15, verify=False)
            return json.loads(resp.text)
        except Exception:
            return {}
    def _post(self, path, search, body):
        try:
            headers = self._headers("POST", path, search)
            headers["Content-Type"] = "application/json"
            resp = self.session.post(self.host + path + search, headers=headers,
                                     json=body, timeout=15, verify=False)
            return json.loads(resp.text)
        except Exception:
            return {}
    def _resolve_line(self, ticket, retried=False):
        d2 = self._post("/v1/playback/resolve-line", "?view=compact", {"ticket": ticket})
        if d2.get("code") == "playback_user_session_required" and not retried:
            if self._ensure_login():
                d2 = self._post("/v1/playback/resolve-line", "?view=compact", {"ticket": ticket})
        return d2.get("line", {}) or {}
    def homeContent(self, filter):
        classes = []
        for tid, tname in self.KINDS:
            classes.append({"type_id": tid, "type_name": tname})
        filters = {}
        if filter:
            window_values = [{"n": n, "v": v} for v, n in self.WINDOWS]
            for tid, _ in self.KINDS:
                filters[tid] = [{
                    "key": "window",
                    "name": "榜单",
                    "value": window_values,
                }]
        return {"class": classes, "filters": filters}
    def homeVideoContent(self):
        data = self._get("/v1/feed/home", "?scope=public&mode=preview&sections=3&cards=12")
        videos = []
        for sec in data.get("sections", []):
            if sec.get("id") == "feed_sec_everyone_watching" or sec.get("type") == "trend":
                for card in sec.get("cards", []):
                    videos.append(self._parse_card(card))
                break
        if not videos:
            for sec in data.get("sections", []):
                for card in sec.get("cards", []):
                    videos.append(self._parse_card(card))
                if videos:
                    break
        return {"list": videos}
    def categoryContent(self, tid, pg, filter, extend):
        window = "day"
        if extend and extend.get("window"):
            window = extend["window"]
        search = "?sort=trending&window={}&page={}&limit=20".format(window, pg)
        if tid and tid != "all":
            search += "&kind=" + tid
        data = self._get("/v1/browse/catalog", search)
        videos = []
        for card in data.get("cards", []):
            videos.append(self._parse_card(card))
        pagination = data.get("pagination", {}) or {}
        has_more = bool(pagination.get("has_more"))
        try:
            page = int(pg)
        except Exception:
            page = 1
        pagecount = page + 1 if has_more else page
        return {
            "page": page,
            "pagecount": pagecount,
            "limit": 20,
            "total": pagecount * 20,
            "list": videos,
        }
    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        data = self._get("/v1/catalog/" + vid)
        card = data.get("card", data) if isinstance(data, dict) else {}
        episodes = card.get("episodes") or []
        episode_count = card.get("episode_count") or len(episodes)
        if episode_count > len(episodes):
            episodes = self._fetch_all_episodes(vid, episodes)
        play_urls = []
        for ep in episodes:
            title = ep.get("title") or ep.get("display_name") or "第{}集".format(ep.get("number", ""))
            token = ep.get("token", "")
            if token:
                play_urls.append("{}${}".format(title, token))
        vod = self._parse_card(card)
        vod["vod_id"] = vid
        vod["vod_play_from"] = "恒轩"
        vod["vod_play_url"] = "#".join(play_urls)
        return {"list": [vod]}
    def searchContent(self, key, quick):
        try:
            from urllib.parse import quote
            q = quote(key)
        except Exception:
            q = key
        data = self._get("/v1/browse/catalog", "?q={}&page=1&limit=20".format(q))
        videos = []
        for card in data.get("cards", []):
            videos.append(self._parse_card(card))
        return {"list": videos}
    def playerContent(self, flag, id, vipFlags):
        token = id
        data = self._get("/v1/playback/resolve/" + token, "?view=compact")
        lines = data.get("line_options", []) or []
        play_url = ""
        url_kind = ""
        official_lines = [ln for ln in lines if self._is_official_line(ln)]
        fallback_lines = official_lines + [ln for ln in lines if ln not in official_lines]
        candidates = [ln for ln in fallback_lines if ln.get("selected")] or fallback_lines
        for ln in candidates:
            ticket = (ln.get("url") or "").replace("resolve://", "")
            if not ticket:
                continue
            line = self._resolve_line(ticket)
            if line.get("url"):
                play_url = line["url"]
                url_kind = line.get("url_kind", "")
                break
        if not play_url:
            for ln in fallback_lines:
                if ln.get("url_kind") == "m3u8" and not ln.get("resolve_required") and ln.get("url"):
                    play_url = ln["url"]
                    url_kind = "m3u8"
                    break
        return {
            "parse": 0,
            "playUrl": "",
            "url": play_url,
            "header": {"User-Agent": self.ua},
        }
    def getName(self):
        return self.name
    def localProxy(self, param):
        pass
    def isVideoFormat(self, url):
        pass
    def manualVideoCheck(self):
        pass
    def destroy(self):
        pass
    def _short_line_name(self, label):
        if "官方" in label:
            base = label.split("·")[0].strip()
            for seg in reversed(base.split("-")):
                if "官方" in seg:
                    name = seg.strip()
                    if "4K" in base.upper() and not name.upper().startswith("4K"):
                        name = "4K" + name
                    return name
        return label
    def _is_official_line(self, ln):
        label = ln.get("label") or ""
        provider = (ln.get("provider_id") or "").lower()
        if "官方" in label:
            return True
        if provider.startswith("official") or provider.startswith("bytevod"):
            return True
        return False
    def _fetch_all_episodes(self, vid, inline_eps):
        episodes = list(inline_eps)
        try:
            offset = len(episodes)
            while True:
                data = self._get("/v1/catalog/{}/episodes".format(vid),
                                 "?limit=48&offset={}".format(offset))
                eps = data.get("episodes", []) or []
                if not eps:
                    break
                episodes.extend(eps)
                page_info = data.get("episode_pagination", {}) or {}
                if not page_info.get("has_more"):
                    break
                offset += len(eps)
        except Exception:
            pass
        return episodes
    def _parse_card(self, card):
        remarks = card.get("remarks", "") or ""
        return {
            "vod_id": str(card.get("id", "")),
            "vod_name": card.get("title", "") or card.get("normalized_title", ""),
            "vod_pic": card.get("poster_url", "") or card.get("backdrop_url", ""),
            "vod_remarks": remarks,
            "vod_year": str(card.get("year", "") or ""),
            "vod_area": card.get("area", "") or "",
            "vod_director": "、".join(card.get("directors", []) or []),
            "vod_actor": "、".join(card.get("actors", []) or []),
            "vod_content": card.get("content", "") or card.get("description", "") or card.get("blurb", ""),
        }
