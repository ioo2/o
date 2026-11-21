# -*- coding: utf-8 -*-
import sys
import json
import time
import hmac
import hashlib
import os
import re
import requests
from urllib.parse import quote
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
    RETRY_BASE = 0.4
    SEARCH_TRIES = 5
    FEED_TRIES = 4
    DETAIL_TRIES = 3
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
        self._time_offset = 0.0
        self._cache = {}
        self._last_anon_at = 0.0
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
        except Exception as e:
            pass
    def _cache_get(self, key):
        try:
            item = self._cache.get(key)
            if not item:
                return None
            expire_at, value = item
            if expire_at < time.time():
                self._cache.pop(key, None)
                return None
            return value
        except Exception:
            return None
    def _cache_put(self, key, value, ttl=180):
        try:
            now = time.time()
            if len(self._cache) > 120:
                for k in [k for k, v in self._cache.items() if v[0] < now]:
                    self._cache.pop(k, None)
                if len(self._cache) > 120:
                    self._cache.clear()
            self._cache[key] = (now + ttl, value)
        except Exception:
            pass
    def _apply_cookie(self, cookie_str):
        try:
            for kv in cookie_str.split(";"):
                kv = kv.strip()
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    self.session.cookies.set(k.strip(), v.strip())
        except Exception as e:
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
            data = self._json(resp)
            if resp.status_code == 200 and not data.get("error"):
                self._logged_in = True
                return True
        except Exception as e:
            pass
        return False
    def _anonymous_login(self):
        try:
            import uuid
            if time.time() - self._last_anon_at < 20:
                return self._logged_in
            path = "/v1/users/anonymous"
            headers = self._headers("POST", path, "")
            headers["Content-Type"] = "application/json"
            anon_id = "web_{}".format(uuid.uuid4())
            resp = self.session.post(self.host + path, headers=headers,
                                     json={"anonymous_id": anon_id},
                                     timeout=15, verify=False)
            self._last_anon_at = time.time()
            if resp.status_code in (200, 201):
                self._logged_in = True
                return True
        except Exception as e:
            pass
        return False
    def _ensure_login(self):
        if self._logged_in:
            return True
        if self.account and self.password:
            return self._login()
        return self._anonymous_login()
    def _sync_clock(self, resp):
        try:
            from email.utils import parsedate_to_datetime
            date_str = resp.headers.get("Date", "")
            if not date_str:
                return
            server_ts = parsedate_to_datetime(date_str).timestamp()
            offset = server_ts - time.time()
            if abs(offset) > 5:
                self._time_offset = offset
        except Exception:
            pass
    def _headers(self, method, path, search):
        ts = str(int((time.time() + self._time_offset) * 1000))
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
    def _json(self, resp):
        try:
            text = resp.text
            if not text or text.lstrip()[:1] not in ("{", "["):
                return {}
            return json.loads(text)
        except Exception:
            return {}
    def _get(self, path, search="", retry_auth=True):
        try:
            resp = self.session.get(self.host + path + search,
                                    headers=self._headers("GET", path, search),
                                    timeout=20, verify=False)
        except Exception as e:
            return {}
        if resp.status_code == 401 and retry_auth:
            self._sync_clock(resp)
            self._logged_in = False
            self._last_anon_at = 0.0
            if self._ensure_login():
                return self._get(path, search, retry_auth=False)
            return {}
        if resp.status_code >= 400:
            return {}
        return self._json(resp)
    def _post(self, path, search, body):
        try:
            headers = self._headers("POST", path, search)
            headers["Content-Type"] = "application/json"
            resp = self.session.post(self.host + path + search, headers=headers,
                                     json=body, timeout=20, verify=False)
            if resp.status_code == 401:
                self._sync_clock(resp)
                self._logged_in = False
                self._last_anon_at = 0.0
                if self._ensure_login():
                    headers = self._headers("POST", path, search)
                    headers["Content-Type"] = "application/json"
                    resp = self.session.post(self.host + path + search, headers=headers,
                                             json=body, timeout=20, verify=False)
            return self._json(resp)
        except Exception as e:
            return {}
    def _source_failed(self, data):
        if not isinstance(data, dict):
            return True
        if data.get("error") or data.get("statusCode"):
            return True
        for item in (data.get("source_statuses") or []):
            status = str(item.get("status", "")).lower()
            if status in ("failed", "error", "unavailable", "timeout", "rate_limited"):
                return True
        return False
    def _get_retry(self, path, search="", tries=3, need_cards=True, base=None):
        base = self.RETRY_BASE if base is None else base
        tries = max(1, int(tries))
        last = {}
        for i in range(tries):
            data = self._get(path, search)
            if isinstance(data, dict) and data:
                last = data
                if not need_cards:
                    return data
                failed = self._source_failed(data)
                if failed:
                    pass
                elif data.get("cards"):
                    return data
                elif i >= 1:
                    return data
            if i < tries - 1:
                time.sleep(base * (i + 1))
        return last
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
        return {"list": []}
    def categoryContent(self, tid, pg, filter, extend):
        window = "day"
        if extend and extend.get("window"):
            window = extend["window"]
        search = "?sort=trending&window={}&page={}&limit=20".format(window, pg)
        if tid and tid != "all":
            search += "&kind=" + tid
        cache_key = "cat:{}:{}:{}".format(tid, pg, window)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        data = self._get_retry("/v1/browse/catalog", search, tries=self.FEED_TRIES)
        videos = self._cards_to_videos(data.get("cards"))
        pagination = data.get("pagination", {}) or {}
        has_more = bool(pagination.get("has_more"))
        try:
            page = int(pg)
        except Exception:
            page = 1
        pagecount = page + 1 if has_more else page
        result = {
            "page": page,
            "pagecount": pagecount,
            "limit": 20,
            "total": pagecount * 20,
            "list": videos,
        }
        if videos:
            self._cache_put(cache_key, result, ttl=120)
        return result
    def searchContent(self, key, quick, pg="1"):
        raw = self._norm_key(key)
        if not raw:
            return {"list": []}
        try:
            page = max(1, int(pg))
        except Exception:
            page = 1
        cache_key = "s:{}:{}".format(raw.lower(), page)
        cached = self._cache_get(cache_key)
        if cached is not None:
            return cached
        videos = self._search_page(raw, page)
        if not videos:
            alt = self._fallback_key(raw)
            if alt and alt != raw:
                videos = self._search_page(alt, page)
        if not videos:
            time.sleep(0.8)
            videos = self._search_page(raw, page)
        result = {"list": videos}
        if videos:
            self._cache_put(cache_key, result, ttl=180)
        return result
    def detailContent(self, ids):
        vid = ids[0] if isinstance(ids, list) else ids
        vid = str(vid or "").strip()
        data = self._get_retry("/v1/catalog/" + quote(vid, safe=""), "", tries=self.DETAIL_TRIES,
                               need_cards=False)
        card = data.get("card") if isinstance(data, dict) and isinstance(data.get("card"), dict) else data
        if not isinstance(card, dict):
            card = {}
        episodes = card.get("episodes") or []
        episode_count = card.get("episode_count") or card.get("total_episode_count") or len(episodes)
        try:
            episode_count = int(episode_count)
        except Exception:
            episode_count = len(episodes)
        if episode_count > len(episodes) and episodes:
            episodes = self._fetch_all_episodes(vid, episodes)
        play_urls = []
        for ep in episodes:
            title = ep.get("title") or ep.get("display_name") or "第{}集".format(ep.get("number", ""))
            token = ep.get("token", "")
            if token:
                play_urls.append("{}${}".format(title, token))
        vod = self._parse_card(card)
        vod["vod_id"] = vid
        select_line_id = ""
        if episodes:
            first_token = episodes[0].get("token", "")
            if first_token:
                rdata = self._get_retry("/v1/playback/resolve/" + first_token, "?view=compact",
                                        tries=self.DETAIL_TRIES, need_cards=False)
                lines = rdata.get("line_options", []) or []
                target_line = None
                for ln in lines:
                    lab = ln.get("label","")
                    if "4K海外-官方C" in lab:
                        target_line = ln
                        break
                if target_line is not None:
                    select_line_id = target_line.get("id","")
                else:
                    official = [ln for ln in lines if self._is_official_line(ln)]
                    select_line_id = official[0].get("id","") if official else (lines[0].get("id","") if lines else "")
        final_eps = []
        for pu in play_urls:
            title, token = pu.split("$", 1)
            final_eps.append("{}${}@@{}".format(title, token, select_line_id))
        vod["vod_play_from"] = "恒轩"
        vod["vod_play_url"] = "#".join(final_eps)
        return {"list": [vod]}
    def playerContent(self, flag, id, vipFlags):
        token = id
        line_id = ""
        if "@@" in id:
            token, line_id = id.split("@@", 1)
        data = self._get_retry("/v1/playback/resolve/" + token, "?view=compact",
                               tries=self.DETAIL_TRIES, need_cards=False)
        lines = data.get("line_options", []) or []
        play_url = ""
        url_kind = ""
        target = None
        if line_id:
            for ln in lines:
                if ln.get("id") == line_id:
                    target = ln
                    break
        if target is not None:
            if target.get("url_kind") == "m3u8" and not target.get("resolve_required") and target.get("url"):
                play_url = target["url"]
                url_kind = "m3u8"
            else:
                ticket = (target.get("url") or "").replace("resolve://", "")
                if ticket:
                    line = self._resolve_line(ticket)
                    if line.get("url"):
                        play_url = line["url"]
                        url_kind = line.get("url_kind", "")
        if not play_url:
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
        return None
    def isVideoFormat(self, url):
        return True
    def manualVideoCheck(self):
        return False
    def destroy(self):
        try:
            self._cache.clear()
            self.session.close()
        except Exception:
            pass
    def _resolve_line(self, ticket, retried=False):
        d2 = self._post("/v1/playback/resolve-line", "?view=compact", {"ticket": ticket})
        if d2.get("code") == "playback_user_session_required" and not retried:
            if self._ensure_login():
                d2 = self._post("/v1/playback/resolve-line", "?view=compact", {"ticket": ticket})
        return d2.get("line", {}) or {}
    def _norm_key(self, key):
        s = str(key or "")
        try:
            s = "".join(chr(ord(c) - 0xFEE0) if 0xFF01 <= ord(c) <= 0xFF5E else c for c in s)
        except Exception:
            pass
        s = s.replace("\u3000", " ")
        for ch in ['《', '》', '<', '>', '"', '“', '”', "'", '‘', '’', '「', '」', '【', '】']:
            s = s.replace(ch, "")
        s = " ".join(s.split()).strip()
        return s
    def _fallback_key(self, q):
        t = q
        t = re.sub(r"(在线观看|完整版|高清|免费观看|全集|未删减|国语版|粤语版|国语|粤语)$", "", t).strip()
        t = re.sub(r"第[0-9一二三四五六七八九十]+[季部]$", "", t).strip()
        t = re.sub(r"[\(（]?(19|20)\d{2}[\)）]?$", "", t).strip()
        t = re.sub(r"[第]?[0-9]+$", "", t).strip()
        if t and t != q:
            return t
        parts = [p for p in re.split(r"[\s]+", q) if p]
        if len(parts) > 1:
            return parts[0]
        return ""
    def _search_page(self, q, page=1, limit=20):
        search = "?q={}&page={}&limit={}".format(quote(q, safe=""), page, limit)
        data = self._get_retry("/v1/browse/catalog", search, tries=self.SEARCH_TRIES)
        return self._cards_to_videos(data.get("cards") if isinstance(data, dict) else None)
    def _cards_to_videos(self, cards):
        videos = []
        seen = set()
        for card in cards or []:
            try:
                vod = self._parse_card(card)
            except Exception:
                continue
            vid = vod.get("vod_id") or ""
            if not vid or vid in seen:
                continue
            if not vod.get("vod_name"):
                continue
            seen.add(vid)
            videos.append(vod)
        return videos
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
            guard = 0
            while guard < 60:
                guard += 1
                data = self._get_retry("/v1/catalog/{}/episodes".format(quote(vid, safe="")),
                                       "?limit=48&offset={}".format(offset),
                                       tries=self.DETAIL_TRIES, need_cards=False)
                eps = data.get("episodes", []) or []
                if not eps:
                    break
                episodes.extend(eps)
                page_info = data.get("episode_pagination", {}) or {}
                if not page_info.get("has_more"):
                    break
                offset += len(eps)
        except Exception as e:
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
