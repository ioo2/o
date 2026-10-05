# -*- coding: utf-8 -*-

import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from base.spider import Spider
class Spider(Spider):
    sources = {
        's1': {'name': '电影天堂', 'api': 'http://caiji.dyttzyapi.com/api.php/provide/vod'},
        's2': {'name': '量子', 'api': 'https://cj.lziapi.com/api.php/provide/vod'},
        's3': {'name': '暴风', 'api': 'https://bfzyapi.com/api.php/provide/vod'},
        's4': {'name': '非凡', 'api': 'https://cj.ffzyapi.com/api.php/provide/vod'},
    }
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    play_from_map = {
        "s1": "恒轩-dyttm3uu8",
        "s2": "恒轩-lzm3u8",
        "s4": "恒轩-ffm3u8"
    }
    def getName(self):
        return "全网聚合"
    def init(self, extend=""):
        pass
    def fetch(self, url, timeout=8):
        try:
            r = requests.get(
                url,
                headers=self.headers,
                timeout=timeout,
                verify=False
            )
            return r.text
        except Exception:
            return ""
    def clean_item(self, item, source_key, source_name, is_detail=False):
        item = dict(item)
        if not is_detail:
            item["vod_id"] = f"{source_key}@@{item.get('vod_id', '')}"
        remarks = item.get("vod_remarks", "")
        item["vod_remarks"] = f"{source_name} | {remarks}"
        if item.get("vod_play_from"):
            if source_key in self.play_from_map:
                item["vod_play_from"] = self.play_from_map[source_key]
            else:
                froms = item["vod_play_from"].split("$$$")
                froms = [f"{source_name}-{x}" for x in froms]
                item["vod_play_from"] = "$$$".join(froms)
        item.pop("vod_down_from", None)
        item.pop("vod_down_url", None)
        return item
    def homeContent(self, filter):
        classes = []
        filters = {}
        def load_class(key, source):
            url = f"{source['api']}?ac=list"
            html = self.fetch(url, 4)
            try:
                data = json.loads(html)
            except:
                data = {}
            vals = [{"n": "全部(最新)", "v": ""}]
            for c in data.get("class", []):
                vals.append({
                    "n": c.get("type_name", ""),
                    "v": c.get("type_id", "")
                })
            return key, vals
        with ThreadPoolExecutor(max_workers=16) as executor:
            futures = []
            for key, source in self.sources.items():
                classes.append({
                    "type_id": key,
                    "type_name": source["name"]
                })
                futures.append(executor.submit(load_class, key, source))
            for future in as_completed(futures):
                try:
                    key, vals = future.result()
                    filters[key] = [{
                        "key": "cateId",
                        "name": "分类",
                        "value": vals
                    }]
                except:
                    pass
        return {
            "class": classes,
            "filters": filters,
            "list": []
        }
    def categoryContent(self, tid, pg, filter, extend):
        if tid not in self.sources:
            return {"list": []}
        source = self.sources[tid]
        cate_id = ""
        if isinstance(extend, dict):
            cate_id = extend.get("cateId", "")
        url = f"{source['api']}?ac=detail&pg={pg}"
        if cate_id:
            url += f"&t={cate_id}"
        html = self.fetch(url)
        try:
            data = json.loads(html)
        except:
            data = {}
        result = []
        for item in data.get("list", []):
            result.append(
                self.clean_item(
                    item,
                    tid,
                    source["name"],
                    False
                )
            )
        return {
            "list": result,
            "page": data.get("page", pg),
            "pagecount": data.get("pagecount", 1),
            "limit": data.get("limit", 20),
            "total": data.get("total", len(result))
        }
    def detailContent(self, ids):
        if isinstance(ids, list):
            ids = ids[0]
        if "@@" not in ids:
            return {"list": []}
        source_key, real_id = ids.split("@@", 1)
        if source_key not in self.sources:
            return {"list": []}
        source = self.sources[source_key]
        url = f"{source['api']}?ac=detail&ids={real_id}"
        html = self.fetch(url)
        try:
            data = json.loads(html)
        except:
            data = {}
        result = []
        for item in data.get("list", []):
            cleaned = self.clean_item(
                item,
                source_key,
                source["name"],
                True
            )
            cleaned["vod_id"] = ids
            result.append(cleaned)
        return {"list": result}
    def search_one(self, source_key, source, keyword, pg):
        url = f"{source['api']}?ac=detail&wd={keyword}&pg={pg}"
        html = self.fetch(url, 6)
        try:
            data = json.loads(html)
        except:
            data = {}
        result = []
        for item in data.get("list", []):
            result.append(
                self.clean_item(
                    item,
                    source_key,
                    source["name"],
                    False
                )
            )
        return {
            "list": result,
            "pagecount": data.get("pagecount", 1)
        }
    def searchContent(self, key, quick=False, pg=1):
        result = []
        max_page = 1
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = []
            for source_key, source in self.sources.items():
                futures.append(
                    executor.submit(
                        self.search_one,
                        source_key,
                        source,
                        key,
                        pg
                    )
                )
            for future in as_completed(futures):
                try:
                    data = future.result()
                    result.extend(data["list"])
                    if data["pagecount"] > max_page:
                        max_page = data["pagecount"]
                except:
                    pass
        return {
            "list": result,
            "page": pg,
            "pagecount": max_page,
            "limit": 40,
            "total": 9999
        }
    def playerContent(self, flag, id, vipFlags):
        return {
            "parse": 0,
            "playUrl": "",
            "url": id,
            "header": self.headers
        }
    def localProxy(self, param):
        return [200, "text/plain", "ok"]
if __name__ == "__main__":
    Spider().run()
