# -*- coding: utf-8 -*-
import re
import json
import urllib.parse
try:
    import requests as _requests
    _HAS_REQUESTS = True
except Exception:
    _requests = None
    _HAS_REQUESTS = False
try:
    from base.spider import Spider as _BaseSpider
except Exception:
    class _BaseSpider:
        pass

def _log(*args):
    try:
        print("腾爱优聚合", *args)
    except Exception:
        pass

def _enc(value):
    return urllib.parse.quote(str(value), safe="!'()*-._~")

_CATEGORY = {
    "1": ("qq",       "腾讯视频"),
    "2": ("qiyi",     "奇艺视频"),
    "3": ("youku",    "优酷视频"),
    "4": ("mgtv",     "芒果视频"),
    "5": ("bilibili", "bilibili"),
}
_KEY_TO_NUM = {v[0]: k for k, v in _CATEGORY.items()}

class Spider(_BaseSpider):
    name = "腾爱优聚合"

    def init(self, extend=""):
        _log("init ->", extend)
        self.host = "http://cj.tianwe.cn"
        self.header = {
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) "
                           "Chrome/150.0.0.0 Safari/537.36"),
        }
        self.parse_api = "https://jx.kptv.us/?url="
        self.parse_sites = [
            "https://niubi.69mini.com/api/?key=0a93b8f6303b79f7be0465c30d305c44&url=",
            "http://8.134.205.252:39466/ceshi/qianyi.php?key=rkd&url=",
            "http://114.66.51.153:2006/api/?key=9df31116c47da6a984097931955ad8d2&url=",
            "https://v.gimy.bot/jx/api.php?url=",
            "https://player.gimy.bot/u/parse.php?url=",
            "https://api.jxapi.cc/api/?key=e0df4139f1e7f09375e864cc4937570e&url=",
            "http://zxy-th1.jsszks.dpdns.org:8090/?url=",
        ]
        self.custom_jx = self._parse_extend(extend)
        self.timeout = 10
        if _HAS_REQUESTS:
            self.session = _requests.Session()
            self.session.headers.update(self.header)

    @staticmethod
    def _parse_extend(extend):
        if not extend:
            return ""
        s = str(extend).strip()
        try:
            d = json.loads(s)
            if isinstance(d, dict):
                return str(d.get("parse", "") or d.get("jx", "")).strip()
        except Exception:
            pass
        if "url=" in s or "?" in s:
            return s
        return ""

    def getName(self):
        return self.name

    def destroy(self):
        pass

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        pass

    def localProxy(self, param):
        return None

    def _http_get(self, url):
        try:
            if _HAS_REQUESTS:
                sess = getattr(self, "session", None) or _requests
                r = sess.get(url, timeout=getattr(self, "timeout", 15), verify=False)
                r.encoding = "utf-8"
                return r.text
            import urllib.request
            req = urllib.request.Request(url, headers=self.header)
            with urllib.request.urlopen(req, timeout=getattr(self, "timeout", 15)) as resp:
                data = resp.read()
                try:
                    return data.decode("utf-8")
                except Exception:
                    return data.decode("latin-1")
        except Exception as exc:
            _log("myfetch err ", exc)
            return ""

    def _get_json(self, url):
        try:
            return json.loads(self._http_get(url))
        except Exception:
            return None

    def homeContent(self, filter=False):
        try:
            classes = [
                {"type_id": "1", "type_pid": "0", "type_name": "腾讯视频"},
                {"type_id": "2", "type_pid": "0", "type_name": "奇艺视频"},
                {"type_id": "3", "type_pid": "0", "type_name": "优酷视频"},
                {"type_id": "4", "type_pid": "0", "type_name": "芒果视频"},
                {"type_id": "5", "type_pid": "0", "type_name": "bilibili"},
            ]
            type_filter = {
                "key": "class",
                "name": "类型",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "电视剧", "v": "2"},
                    {"n": "电影", "v": "1"},
                    {"n": "动漫", "v": "4"},
                    {"n": "综艺", "v": "3"},
                    {"n": "少儿", "v": "5"},
                    {"n": "纪录片", "v": "6"},
                    {"n": "短剧", "v": "7"},
                ],
            }
            year_filter = {
                "key": "year",
                "name": "年份",
                "value": [
                    {"n": "全部", "v": ""},
                    {"n": "2026", "v": "2026"},
                    {"n": "2025", "v": "2025"},
                    {"n": "2024", "v": "2024"},
                    {"n": "2023", "v": "2023"},
                    {"n": "2022", "v": "2022"},
                ],
            }
            filters = {}
            for c in classes:
                filters[c["type_id"]] = [type_filter, year_filter]
            result = {"class": classes, "list": []}
            if filter:
                result["filters"] = filters
            return result
        except Exception as exc:
            _log("homeContent err", exc)
            return {"class": [], "list": []}

    def homeVideoContent(self):
        return {"list": []}

    def categoryContent(self, tid, pg, filter=False, extend=None):
        extend = extend or {}
        key = self._to_key(tid) or "qq"
        try:
            page = int(pg) if pg else 1
        except Exception:
            page = 1
        params = ["from=" + key, "ac=detail", "limit=24", "pg=" + str(page)]
        t = extend.get("class") or "2"
        params.append("t=" + t)
        if extend.get("year"):
            params.append("year=" + _enc(extend["year"]))
        url = self.host + "/api.php/provide/vod/?" + "&".join(params)
        _log("api category url ->", url)
        data = self._get_json(url)
        if not data:
            return {"list": [], "page": page, "pagecount": 1, "limit": 0, "total": 0}
        vod_list = []
        if isinstance(data.get("list"), list):
            vod_list = [
                {
                    "vod_id": str(v.get("vod_id", "")),
                    "vod_name": v.get("vod_name", ""),
                    "vod_pic": v.get("vod_pic", ""),
                    "vod_remarks": v.get("vod_remarks", ""),
                }
                for v in data["list"]
            ]
        pc = data.get("pagecount") or 1
        try:
            pc = int(pc)
        except Exception:
            pc = 1
        return {
            "list": vod_list,
            "page": page,
            "pagecount": pc,
            "limit": len(vod_list),
            "total": pc * len(vod_list) if vod_list else 0,
        }

    def detailContent(self, ids):
        if not ids:
            return {"list": []}
        vid = str(ids)
        if isinstance(ids, (list, tuple)):
            vid = str(ids[0])
        vid = vid.split("$")[-1].strip()
        url = (self.host + "/api.php/provide/vod/?" +
               "&".join(["ac=detail", "ids=" + vid]))
        _log("detailurl", url)
        data = self._get_json(url)
        if not data:
            return {"list": []}
        vod_list = []
        if isinstance(data.get("list"), list):
            for item in data["list"]:
                if not item.get("vod_id"):
                    continue
                vod_list.append({
                    "vod_id": str(item.get("vod_id", "")),
                    "vod_name": item.get("vod_name", ""),
                    "vod_pic": item.get("vod_pic", ""),
                    "vod_remarks": item.get("vod_remarks", ""),
                    "vod_year": item.get("vod_year", ""),
                    "type_name": item.get("type_name", ""),
                    "vod_area": item.get("vod_area", ""),
                    "vod_lang": item.get("vod_lang", ""),
                    "vod_content": item.get("vod_content", ""),
                    "vod_play_from": item.get("vod_play_from", ""),
                    "vod_play_url": item.get("vod_play_url", ""),
                })
        return {"list": vod_list}

    def searchContent(self, key, quick, pg="1"):
        if not key:
            return {"list": []}
        url = (self.host + "/api.php/provide/vod/?ac=detail&wd=" +
               _enc(key) + "&pg=" + str(pg))
        _log("api searchUrl:", url)
        data = self._get_json(url)
        if not data:
            return {"list": [], "page": str(pg), "pagecount": 1}
        vod_list = []
        if isinstance(data.get("list"), list):
            vod_list = [
                {
                    "vod_id": str(v.get("vod_id", "")),
                    "vod_name": v.get("vod_name") or v.get("name") or "",
                    "vod_pic": v.get("vod_pic") or v.get("pic") or "",
                    "vod_remarks": v.get("vod_remarks") or "",
                }
                for v in data["list"]
                if v.get("vod_id")
            ]
        pc = data.get("pagecount") or 1
        try:
            pc = int(pc)
        except Exception:
            pc = 1
        return {"list": vod_list, "page": str(pg), "pagecount": pc}

    def playerContent(self, flag, id, vipFlags):
        _log("开始获取播放地址: ", id)
        try:
            if self._is_direct(id):
                return {"parse": 0, "url": id, "header": dict(self.header), "playUrl": ""}
            if getattr(self, "custom_jx", ""):
                _log("使用自定义解析:", self.custom_jx + id)
                return {"parse": 1, "url": self.custom_jx + id, "header": dict(self.header), "playUrl": ""}
            play_url = self._parse_video_url(id)
            if play_url:
                return {"parse": 0, "url": play_url, "header": dict(self.header), "playUrl": ""}
            web_url = self._webview_jx(id)
            if web_url:
                return {"parse": 1, "url": web_url, "header": dict(self.header), "playUrl": ""}
        except Exception as exc:
            _log("play失败: ", exc)
        return {"parse": 1, "url": id, "header": dict(self.header), "playUrl": ""}

    def _webview_jx(self, video_url):
        for site in (getattr(self, "parse_sites", None) or []):
            if site:
                return site + video_url
        return ""

    def _is_direct(self, url):
        s = str(url)
        return any(k in s for k in ("m3u", "mp4"))

    def _parse_video_url(self, video_url):
        parse_api = self.parse_api
        resolve_url = parse_api + video_url
        _log("正在请求解析地址:", resolve_url)
        try:
            text1 = self._http_get(resolve_url)
            token = self._extract_token(text1)
            if not token:
                raise Exception("解析源无 token")
            host = parse_api.split("//")[1].split("/")[0]
            api_url = ("https://" + host + "/api/resolve.php?token=" + _enc(token))
            text2 = self._http_get(api_url)
            data = json.loads(text2) if text2 else {}
            play_url = self._format_url(data.get("url"))
            if not play_url:
                raise Exception("解析源链接为空")
            _log("解析成功并返回 ->", play_url)
            return play_url
        except Exception as exc:
            _log("解析失败: ", exc)
            return ""

    @staticmethod
    def _extract_token(text):
        m = re.search(r'apiToken\s*:\s*["\']([^"\']+)["\']', text or "")
        return m.group(1) if m else None

    @staticmethod
    def _format_url(url):
        if not url:
            return ""
        url = str(url).replace("\\", "")
        url = re.sub(r"^(https?:\/)((?!\/))", r"\1/", url, flags=re.IGNORECASE)
        return url

    @staticmethod
    def _to_key(tid):
        if tid is None:
            return None
        s = str(tid).strip()
        if s in _CATEGORY:
            return _CATEGORY[s][0]
        if s in _KEY_TO_NUM:
            return s
        return s
