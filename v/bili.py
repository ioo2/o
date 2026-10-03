# -*- coding: utf-8 -*-
import copy
import html
import json
import re
import time
import hashlib
import base64
import uuid
import urllib.parse
try:
    import requests
    _HAS_REQUESTS = True
except Exception:
    _HAS_REQUESTS = False
    import urllib.request

SITE = "https://www.bilibili.com"
API = "https://api.bilibili.com"
UA = "vivo250"
_DEFAULT_COOKIE = (
    "SESSDATA=1446597f%2C1803701179%2Ca580e%2A81CjAws6bETS5cmCwXzYqvp-Q5wpCNBjRSN0rHt0qQmSwozT82SfYfyAxCDgD22Cck93kSVl9lODFRNFYyMGc0UTFCQzhvRy1IUVlBaEhJV3ZlSXhWWlcxSHFRZkdwTTRuQkNwSkt3UVhTTmIyeXJoQnFsbUI2dEhIV24zaFlvVC1iSmIwXzdTQXl3IIEC;"
)


def _sanitize_cookie(cookie_str):
    if not cookie_str:
        return ""
    clean = cookie_str.encode("ascii", "ignore").decode("ascii")
    for name in ["SESSDATA", "bili_jct", "DedeUserID", "bili_ticket", "buvid3", "buvid4"]:
        clean = clean.replace(";" + name, "; " + name)
    parts = []
    for item in clean.split(";"):
        item = item.strip()
        if "=" not in item:
            continue
        k, v = item.split("=", 1)
        v = v.strip().encode("ascii", "ignore").decode("ascii")
        if v:
            parts.append("{}={}".format(k.strip(), v))
    return "; ".join(parts)


class _Response:
    def __init__(self, text="", status=200, headers=None):
        self.text = text
        self.status_code = status
        self.headers = headers or {}

    def json(self):
        return json.loads(self.text)


class _Http:
    def __init__(self, cookie=""):
        self.session = requests.Session() if _HAS_REQUESTS else None
        self.cookie = _sanitize_cookie(cookie)
        if self.session and self.cookie:
            self._set_cookies(self.cookie)
        self._ensure_buvid()

    def _set_cookies(self, cookie_str):
        if not self.session:
            return
        self.session.cookies.clear()
        for item in cookie_str.split(";"):
            item = item.strip()
            if "=" in item:
                k, v = item.split("=", 1)
                self.session.cookies.set(k.strip(), v.strip(), domain=".bilibili.com")
                self.session.cookies.set(k.strip(), v.strip(), domain="api.bilibili.com")

    def update_cookie(self, cookie):
        self.cookie = _sanitize_cookie(cookie)
        if self.session:
            self._set_cookies(self.cookie)
        self._ensure_buvid()

    def _ensure_buvid(self):
        if "buvid3=" in self.cookie and "buvid4=" in self.cookie:
            return
        try:
            if _HAS_REQUESTS:
                r = self.session.get(API + "/x/frontend/finger/spi", headers={"User-Agent": UA, "Referer": SITE + "/"}, timeout=8, verify=False)
                if r.status_code == 200:
                    d = r.json().get("data", {})
                    b3, b4 = d.get("b_3", ""), d.get("b_4", "")
                    if b3:
                        self.cookie += "; buvid3=" + b3
                    if b4:
                        self.cookie += "; buvid4=" + b4
                    self._set_cookies(self.cookie)
                    return
        except Exception:
            pass
        if "buvid3=" not in self.cookie:
            self.cookie += "; buvid3=" + str(uuid.uuid4()).replace("-", "").upper() + "infoc"
        if "buvid4=" not in self.cookie:
            self.cookie += "; buvid4=" + str(uuid.uuid4()).replace("-", "").upper()
        self._set_cookies(self.cookie)

    def _refresh_buvid(self):
        try:
            if _HAS_REQUESTS:
                r = self.session.get(API + "/x/frontend/finger/spi", headers={"User-Agent": UA, "Referer": SITE + "/"}, timeout=8, verify=False)
                if r.status_code == 200:
                    d = r.json().get("data", {})
                    for name, val in [("buvid3", d.get("b_3", "")), ("buvid4", d.get("b_4", ""))]:
                        if val:
                            self.cookie = re.sub(name + r"=[^;]*", name + "=" + val, self.cookie)
                            if name + "=" not in self.cookie:
                                self.cookie += "; " + name + "=" + val
                    self._set_cookies(self.cookie)
        except Exception:
            pass

    def _headers(self, extra=None):
        h = {
            "User-Agent": UA,
            "Origin": SITE,
            "Referer": SITE + "/",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        }
        if self.cookie:
            safe = self.cookie.encode("ascii", "ignore").decode("ascii")
            if safe:
                h["Cookie"] = safe
        if extra:
            h.update(extra)
        return h

    def get(self, url, headers=None, timeout=18):
        h = self._headers(headers)
        if _HAS_REQUESTS:
            r = self.session.get(url, headers=h, timeout=timeout, verify=False)
            if r.status_code == 200 and "json" in r.headers.get("Content-Type", ""):
                try:
                    if r.json().get("code") in (-352, 352, -403):
                        self._refresh_buvid()
                        r = self.session.get(url, headers=self._headers(headers), timeout=timeout, verify=False)
                except Exception:
                    pass
            return r
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return _Response(r.read().decode("utf-8", "replace"), r.status, dict(r.headers))

    def post(self, url, data=None, headers=None, timeout=18):
        h = self._headers(headers)
        if _HAS_REQUESTS:
            return self.session.post(url, json=data, headers=h, timeout=timeout, verify=False)
        raw = json.dumps(data or {}, ensure_ascii=False).encode("utf-8")
        h["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=raw, headers=h, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return _Response(r.read().decode("utf-8", "replace"), r.status, dict(r.headers))


class Spider:
    name = "B影视"
    version = "3.0.4"
    host = API

    def __init__(self):
        self.extend = ""
        self.vmid = ""
        self.cookie = _DEFAULT_COOKIE
        self.http = _Http(self.cookie)
        self.s = self.http.session
        self.session = self.http.session
        self.sess = self.http.session

    def init(self, extend=""):
        if isinstance(extend, dict):
            self.extend = json.dumps(extend, ensure_ascii=False)
        else:
            self.extend = extend if isinstance(extend, str) else ""
        self.vmid = ""
        if self.extend:
            try:
                ext = json.loads(self.extend) if isinstance(self.extend, str) else self.extend
                if isinstance(ext, dict):
                    self.vmid = str(ext.get("vmid", ""))
                    if ext.get("cookie"):
                        self.cookie = _sanitize_cookie(urllib.parse.unquote(str(ext.get("cookie"))))
            except Exception:
                if "vmid=" in self.extend:
                    self.vmid = self.extend.split("vmid=")[-1].split("&")[0].strip()
                if "cookie=" in self.extend:
                    raw = self.extend.split("cookie=")[-1].split("&")[0].strip()
                    self.cookie = urllib.parse.unquote(raw)
                elif not self.vmid:
                    self.vmid = self.extend.strip()
        self.http.update_cookie(self.cookie)
        self.s = self.http.session
        self.session = self.http.session
        self.sess = self.http.session

    def getDependence(self):
        return []

    def getName(self):
        return self.name

    def destroy(self):
        try:
            if self.http.session:
                self.http.session.close()
        except Exception:
            pass

    def manualVideoCheck(self):
        return False

    def isVideoFormat(self, url):
        u = str(url).lower()
        if u.startswith("data:") or "127.0.0.1" in u or "localhost" in u:
            return True
        return u.split("?", 1)[0].endswith((".m3u8", ".mp4", ".flv", ".ts", ".mkv", ".m4s"))

    def action(self, action):
        return json.dumps({"code": 0, "msg": "ok"}, ensure_ascii=False)

    def homeContent(self, filter=None):
        classes = [
            {"type_name": "番剧", "type_id": "1"},
            {"type_name": "国创", "type_id": "4"},
            {"type_name": "电影", "type_id": "2"},
            {"type_name": "电视剧", "type_id": "5"},
            {"type_name": "纪录片", "type_id": "3"},
            {"type_name": "综艺", "type_id": "7"},
            {"type_name": "全部", "type_id": "全部"},
            {"type_name": "时间表", "type_id": "时间表"},
        ]
        filters = {
            "全部": [
                {
                    "key": "tid",
                    "name": "分类",
                    "value": [
                        {"n": "番剧", "v": "1"},
                        {"n": "国创", "v": "4"},
                        {"n": "电影", "v": "2"},
                        {"n": "电视剧", "v": "5"},
                        {"n": "记录片", "v": "3"},
                        {"n": "综艺", "v": "7"},
                    ],
                },
                {
                    "key": "order",
                    "name": "排序",
                    "value": [
                        {"n": "播放数量", "v": "2"},
                        {"n": "更新时间", "v": "0"},
                        {"n": "最高评分", "v": "4"},
                        {"n": "弹幕数量", "v": "1"},
                        {"n": "追看人数", "v": "3"},
                        {"n": "开播时间", "v": "5"},
                        {"n": "上映时间", "v": "6"},
                    ],
                },
                {
                    "key": "season_status",
                    "name": "付费",
                    "value": [
                        {"n": "全部", "v": "-1"},
                        {"n": "免费", "v": "1"},
                        {"n": "付费", "v": "2%2C6"},
                        {"n": "大会员", "v": "4%2C6"},
                    ],
                },
            ],
            "时间表": [
                {
                    "key": "tid",
                    "name": "分类",
                    "value": [
                        {"n": "番剧", "v": "1"},
                        {"n": "国创", "v": "4"},
                    ],
                },
            ],
        }
        return {"class": classes, "filters": filters, "list": []}

    def homeVideoContent(self):
        try:
            videos = self._get_rank("1", 1)[:5]
            for i in ["4", "2", "5", "3", "7"]:
                videos.extend(self._get_rank2(i, 1)[:5])
            return {"list": self._dedupe(videos)}
        except Exception:
            return {"list": []}

    def categoryContent(self, tid, pg=1, filter=None, extend=None):
        try:
            page = max(1, int(pg))
        except Exception:
            page = 1
        ext = extend if isinstance(extend, dict) else {}
        try:
            if tid == "1":
                videos = self._get_rank(tid, page)
                return {"list": videos, "page": page, "pagecount": 1, "limit": 20, "total": len(videos)}
            elif tid in ["2", "3", "4", "5", "7"]:
                videos = self._get_rank2(tid, page)
                return {"list": videos, "page": page, "pagecount": 1, "limit": 20, "total": len(videos)}
            elif tid == "全部":
                tid_val = ext.get("tid", "1")
                order = ext.get("order", "2")
                season_status = ext.get("season_status", "-1")
                videos = self._get_all(tid_val, page, order, season_status)
                return {"list": videos, "page": page, "pagecount": page + 1 if len(videos) >= 20 else page, "limit": 20, "total": 999999}
            elif tid == "时间表":
                tid_val = ext.get("tid", "1")
                videos = self._get_timeline(tid_val, page)
                return {"list": videos, "page": page, "pagecount": 1, "limit": 50, "total": len(videos)}
            else:
                return {"list": [], "page": page, "pagecount": 1, "limit": 20, "total": 0}
        except Exception:
            return {"list": [], "page": page, "pagecount": 1, "limit": 20, "total": 0}

    def detailContent(self, ids):
        vid = str(ids[0] if isinstance(ids, (list, tuple)) and ids else ids)
        if not vid:
            return {"list": []}
        try:
            jo = self.http.get(self.host + "/pgc/view/web/season?season_id=" + vid).json().get("result", {})
            id_val = jo.get("season_id", "")
            title = jo.get("title", "")
            pic = jo.get("cover", "")
            areas = jo["areas"][0].get("name", "") if jo.get("areas") else ""
            type_name = jo.get("share_sub_title", "")
            date = jo["publish"]["pub_time"][:4] if jo.get("publish", {}).get("pub_time") else ""
            dec = jo.get("evaluate", "")
            remark = jo.get("new_ep", {}).get("desc", "")
            stat = jo.get("stat", {})
            status = "弹幕: {}　点赞: {}　投币: {}　追番追剧: {}".format(
                self._zh(stat.get("danmakus", 0)), self._zh(stat.get("likes", 0)),
                self._zh(stat.get("coins", 0)), self._zh(stat.get("favorites", 0)),
            )
            score = "评分: {}　{}".format(jo["rating"].get("score", ""), jo.get("subtitle", "")) if jo.get("rating") else "暂无评分　{}".format(jo.get("subtitle", ""))
            vod = {
                "vod_id": id_val, "vod_name": title, "vod_pic": pic, "type_name": type_name,
                "vod_year": date, "vod_area": areas, "vod_remarks": remark,
                "vod_actor": status, "vod_director": score, "vod_content": dec,
            }
            episodes = jo.get("episodes", []) or []
            sections = jo.get("section", []) or jo.get("sections", []) or []
            if not episodes:
                positive_id = jo.get("positive", {}).get("id", "")
                if positive_id:
                    for sec in sections:
                        if str(sec.get("id", "")) == str(positive_id):
                            episodes = sec.get("episodes", []) or []
                            break
                if not episodes:
                    for sec in sections:
                        if sec.get("title", "") == "正片":
                            episodes = sec.get("episodes", []) or []
                            if episodes:
                                break
                if not episodes:
                    for sec in sections:
                        t = sec.get("title", "")
                        if "预告" not in t and "PV" not in t and "彩蛋" not in t:
                            eps = sec.get("episodes", []) or []
                            if eps:
                                episodes = eps
                                break
                if not episodes:
                    for sec in sections:
                        eps = sec.get("episodes", []) or []
                        if eps:
                            episodes = eps
                            break
            ja = []
            for tmp in episodes:
                t = str(tmp.get("title", ""))
                b = str(tmp.get("badge", "") or "")
                if "预告" not in t and "预告" not in b and "PV" not in t:
                    ja.append(tmp)
            playurls_base = []
            for tmp in ja:
                eid = str(tmp.get("id", "") or "")
                cid = str(tmp.get("cid", "") or "")
                aid = str(tmp.get("aid", "") or "")
                bvid = str(tmp.get("bvid", "") or "")
                link = str(tmp.get("link", "") or "")
                if not bvid and link and "/BV" in link:
                    try:
                        bvid = "BV" + link.split("/BV")[-1].split("/")[0].split("?")[0].strip()
                    except Exception:
                        pass
                part_name = str(tmp.get("title", "")).replace("#", "-").replace("$", "_").replace("$$$", "_")
                part_long = str(tmp.get("long_title", "")).replace("#", "-").replace("$", "_").replace("$$$", "_")
                part = "{} {}".format(part_name, part_long).strip()
                badge = str(tmp.get("badge", "") or "")
                if badge:
                    part = "{}[{}]".format(part, badge)
                if cid:
                    playurls_base.append("{}${}_{}_{}_{}".format(part, aid or "0", cid, eid or "0", bvid or "0"))
            vod["vod_play_from"] = "恒轩"
            vod["vod_play_url"] = "#".join(playurls_base) if playurls_base else ""
            return {"list": [vod]}
        except Exception:
            import traceback
            traceback.print_exc()
            return {"list": []}

    def searchContent(self, key, quick=False, pg="1"):
        try:
            page = max(1, int(pg))
        except Exception:
            page = 1
        keys = self._get_wbi_keys()
        if not keys:
            return {"list": [], "page": page, "pagecount": page}
        v = []
        for search_type in ["media_bangumi", "media_ft"]:
            try:
                params = {
                    "keyword": key, "page": page, "page_size": 20,
                    "platform": "pc", "search_type": search_type, "web_location": 1430654,
                }
                query = self._enc_wbi(params, keys)
                url = self.host + "/x/web-interface/wbi/search/type?" + query
                jo = self.http.get(url).json()
                if jo.get("code") == 0 and jo.get("data", {}).get("result"):
                    for vod in jo["data"]["result"]:
                        title = re.sub(r"<[^>]+>", "", str(vod.get("title", ""))).strip()
                        if "预告" in title:
                            continue
                        aid = str(vod.get("season_id", "")).strip()
                        img = str(vod.get("cover", "")).strip()
                        if img.startswith("//"):
                            img = "https:" + img
                        remark = str(vod.get("index_show", "")).strip()
                        v.append({"vod_id": aid, "vod_name": title, "vod_pic": img, "vod_remarks": remark})
            except Exception:
                pass
        return {"list": self._dedupe(v), "page": page, "pagecount": page + 1 if len(v) >= 20 else page}

    def playerContent(self, flag, ids, vipFlags=None):
        if isinstance(ids, (list, tuple)) and ids:
            raw = str(ids[0])
        else:
            raw = str(ids)
        danmaku = ""
        parts = raw.split("_")
        aid = cid = eid = bvid = ""
        if len(parts) >= 4:
            aid, cid, eid, bvid = parts[0], parts[1], parts[2], parts[3]
        elif len(parts) == 3:
            aid, cid, eid = parts[0], parts[1], parts[2]
        elif len(parts) == 2:
            eid, cid = parts[0], parts[1]
        if not cid:
            return {"parse": 0, "url": raw, "header": {"User-Agent": UA, "Referer": SITE + "/", "Cookie": self.cookie}, "jx": 1, "danmaku": danmaku}
        try:
            if bvid and bvid != "0":
                api_url = "{}/x/player/playurl?bvid={}&cid={}&qn=127&fnver=0&fnval=4048&fourk=1".format(API, bvid, cid)
            elif aid and aid != "0":
                api_url = "{}/x/player/playurl?avid={}&cid={}&qn=127&fnver=0&fnval=4048&fourk=1".format(API, aid, cid)
            elif eid and eid != "0":
                api_url = "{}/pgc/player/web/playurl?cid={}&qn=127&fnver=0&fnval=4048&fourk=1&ep_id={}".format(API, cid, eid)
            else:
                api_url = "{}/x/player/playurl?cid={}&qn=127&fnver=0&fnval=4048&fourk=1".format(API, cid)
            data = self.http.get(api_url, timeout=10).json()
            if data.get("code") == 0:
                result = data.get("result", {}) or data.get("data", {})
                dash = result.get("dash", {})
                videos = dash.get("video", [])
                audios = dash.get("audio", [])
                if videos and audios:
                    sorted_videos = self._sort_video_tracks(videos)
                    best_video = sorted_videos[0]
                    sorted_audios = sorted(audios, key=lambda x: x.get("id", 0), reverse=True)
                    best_audio = sorted_audios[0]
                    v_url = self._pick_url_for_mpd(best_video)
                    a_url = self._pick_url_for_mpd(best_audio, is_audio=True)
                    if v_url and a_url:
                        danmaku = "http://121.41.93.205/dm.php?url=" + urllib.parse.quote(raw, safe="")
                        return {"parse": 0, "url": v_url + "#" + a_url, "header": {"User-Agent": UA, "Referer": SITE + "/", "Cookie": self.cookie}, "jx": 0, "danmaku": danmaku}
                durl = result.get("durl", [])
                if durl and durl[0].get("url"):
                    danmaku = "http://121.41.93.205/dm.php?url=" + urllib.parse.quote(raw, safe="")
                    return {"parse": 0, "url": durl[0]["url"], "header": {"User-Agent": UA, "Referer": SITE + "/", "Cookie": self.cookie}, "jx": 0, "danmaku": danmaku}
        except Exception:
            pass
        url = SITE
        if eid and eid != "0":
            url = "https://www.bilibili.com/bangumi/play/ep" + eid
        elif aid and aid != "0":
            url = "https://www.bilibili.com/video/av" + aid
        elif bvid and bvid != "0":
            url = "https://www.bilibili.com/video/" + bvid
        danmaku = "http://121.41.93.205/dm.php?url=" + urllib.parse.quote(url, safe="")
        return {"parse": 0, "url": url, "header": {"User-Agent": UA, "Referer": SITE + "/", "Cookie": self.cookie}, "jx": 1, "danmaku": danmaku}

    @staticmethod
    def _sort_video_tracks(videos):
        def _prio(v):
            c = str(v.get("codecs", "")).lower()
            if "hev" in c or "h265" in c or "hvc" in c:
                return 0
            if "avc" in c or "h264" in c:
                return 1
            if "av1" in c or "av01" in c:
                return 2
            return 3
        groups = {}
        for v in videos:
            vid = v.get("id", 0)
            groups.setdefault(vid, []).append(v)
        out = []
        for vid in sorted(groups.keys(), reverse=True):
            out.extend(sorted(groups[vid], key=_prio))
        return out

    @staticmethod
    def _pick_url_for_mpd(item, is_audio=False):
        urls = []
        base = item.get("baseUrl", "") or item.get("base_url", "")
        if base:
            urls.append(base)
        for b in (item.get("backupUrl", []) or item.get("backup_url", []) or []):
            if b and b not in urls:
                urls.append(b)
        for url in urls:
            if "mcdn" in url and "bilivideo" in url:
                return url
        for url in urls:
            if "bilivideo" in url:
                return url
        for url in urls:
            if "mcdn" in url:
                return url
        return urls[0] if urls else ""

    def localProxy(self, param):
        return [404, "text/plain", b"Not Found", {}]

    def _get_result(self, url):
        videos = []
        try:
            jo = self.http.get(url).json()
            if jo.get("code") == 0:
                vod_list = jo.get("result", {}).get("list", []) or jo.get("data", {}).get("list", [])
                for vod in vod_list:
                    aid = str(vod.get("season_id", "")).strip()
                    title = str(vod.get("title", "")).strip()
                    img = str(vod.get("cover", "")).strip()
                    remark = str(vod.get("index_show", "")).strip() if not vod.get("new_ep") else str(vod["new_ep"].get("index_show", "")).strip()
                    if "预告" not in title and "预告" not in remark:
                        videos.append({"vod_id": aid, "vod_name": title, "vod_pic": img, "vod_remarks": remark})
        except Exception:
            pass
        return videos

    def _get_rank(self, tid, pg):
        return self._get_result("{}://{}/pgc/web/rank/list?season_type={}&pagesize=20&page={}&day=3".format("https", "api.bilibili.com", tid, pg))

    def _get_rank2(self, tid, pg):
        return self._get_result("{}://{}/pgc/season/rank/web/list?season_type={}&pagesize=20&page={}&day=3".format("https", "api.bilibili.com", tid, pg))

    def _get_all(self, tid, pg, order, season_status):
        return self._get_result("{}://{}/pgc/season/index/result?order={}&pagesize=20&type=1&season_type={}&page={}&season_status={}".format("https", "api.bilibili.com", order, tid, pg, season_status))

    def _get_timeline(self, tid, pg):
        videos = []
        try:
            jo = self.http.get("{}://{}/pgc/web/timeline/v2?season_type={}&day_before=2&day_after=4".format("https", "api.bilibili.com", tid)).json()
            if jo.get("code") == 0:
                result = jo.get("result", {})
                videos1 = []
                for vod in result.get("latest", []):
                    aid = str(vod.get("season_id", "")).strip()
                    title = str(vod.get("title", "")).strip()
                    img = str(vod.get("cover", "")).strip()
                    remark = str(vod.get("pub_index", "")) + "　" + str(vod.get("follows", "")).replace("系列", "")
                    if "预告" not in title and "预告" not in remark:
                        videos1.append({"vod_id": aid, "vod_name": title, "vod_pic": img, "vod_remarks": remark})
                videos2 = []
                for i in range(min(7, len(result.get("timeline", [])))):
                    for vod in result["timeline"][i].get("episodes", []):
                        if str(vod.get("published", "")) == "0" and "预告" not in vod.get("title", ""):
                            aid = str(vod.get("season_id", "")).strip()
                            title = str(vod.get("title", "")).strip()
                            img = str(vod.get("cover", "")).strip()
                            pub_ts = vod.get("pub_ts", 0)
                            try:
                                from datetime import datetime
                                date_str = datetime.fromtimestamp(pub_ts).strftime("%m-%d")
                            except Exception:
                                date_str = str(pub_ts)
                            remark = "{}   {}".format(date_str, vod.get("pub_index", ""))
                            videos2.append({"vod_id": aid, "vod_name": title, "vod_pic": img, "vod_remarks": remark})
                videos = videos2 + videos1
        except Exception:
            pass
        return videos

    def _get_wbi_keys(self):
        try:
            r = self.http.get(self.host + "/x/web-interface/nav")
            data = r.json()
            if data.get("code") == 0:
                wbi_img = data["data"].get("wbi_img", {})
                iu = wbi_img.get("img_url", "")
                su = wbi_img.get("sub_url", "")
                img_key = iu.split("/")[-1].split(".")[0] if iu else ""
                sub_key = su.split("/")[-1].split(".")[0] if su else ""
                if img_key and sub_key:
                    return {"img_key": img_key, "sub_key": sub_key}
        except Exception:
            pass
        return None

    def _enc_wbi(self, params, keys):
        mixin_key_enc_tab = [
            46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35,
            27, 43, 5, 49, 33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13,
            37, 48, 7, 16, 24, 55, 40, 61, 26, 17, 0, 1, 60, 51, 30, 4,
            22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36, 20, 52, 44,
        ]
        orig = keys["img_key"] + keys["sub_key"]
        mixin_key = "".join([orig[i] for i in mixin_key_enc_tab])[:32]
        params["wts"] = int(time.time())
        parts = []
        for k, v in sorted(params.items()):
            val = str(v).replace("!", "").replace("'", "").replace("(", "").replace(")", "").replace("*", "")
            parts.append("{}={}".format(urllib.parse.quote(str(k), safe=""), urllib.parse.quote(str(val), safe="")))
        query = "&".join(parts)
        w_rid = hashlib.md5((query + mixin_key).encode("utf-8")).hexdigest()
        return query + "&w_rid=" + w_rid

    @staticmethod
    def _zh(num):
        try:
            n = int(num)
        except Exception:
            return str(num)
        if n > 1e8:
            return "{:.2f}亿".format(n / 1e8)
        elif n > 1e4:
            return "{:.2f}万".format(n / 1e4)
        else:
            return str(n)

    @staticmethod
    def _dedupe(items):
        out, seen = [], set()
        for x in items:
            vid = x.get("vod_id")
            if vid and vid not in seen:
                seen.add(vid)
                out.append(x)
        return out


if __name__ == "__main__":
    s = Spider()
    s.init('{"vmid":""}')
    print(json.dumps(s.homeContent(), ensure_ascii=False))
    print(json.dumps(s.homeVideoContent(), ensure_ascii=False))