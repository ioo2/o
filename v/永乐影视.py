# coding=utf-8
#!/usr/bin/env python3
import re
import sys
import urllib.parse
import requests
from bs4 import BeautifulSoup
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def getName(self):
        return "永乐视频"

    def init(self, extend=""):
        self.host = "https://www.ylys.tv/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': self.host
        }
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update(self.headers)

    def fetch(self, url, timeout=30):
        try:
            resp = self.session.get(url, timeout=timeout, verify=False)
            if resp.encoding == 'ISO-8859-1':
                resp.encoding = 'UTF-8'
            return resp
        except Exception:
            return None

    def homeContent(self, filter):
        res = {
            "class": [
                {"type_id": "2", "type_name": "剧集"},
                {"type_id": "1", "type_name": "电影"},
                {"type_id": "4", "type_name": "动漫"},
                {"type_id": "3", "type_name": "综艺"}
             ],
            "filters": self._get_filters(),
            "list": []
        }
        rsp = self.fetch(self.host)
        if rsp and rsp.status_code == 200:
            res["list"] = self._extract_videos(rsp.text, 20)
        return res

    def categoryContent(self, tid, pg, filter, extend):
        res = {"list": [], "page": int(pg), "pagecount": 99, "limit": 20, "total": 1980}
        if int(pg) > 1:
            url = f"{self.host}/vodtype/{tid}/page/{pg}/"
        else:
            url = f"{self.host}/vodtype/{tid}/"
        rsp = self.fetch(url)
        if rsp and rsp.status_code == 200:
            res["list"] = self._extract_videos(rsp.text)
        return res

    def searchContent(self, key, quick, pg=1):
        res = {"list": []}
        kw = urllib.parse.quote(key)
        if int(pg) > 1:
            url = f"{self.host}/vodsearch/{kw}-------------/page/{pg}/"
        else:
            url = f"{self.host}/vodsearch/{kw}-------------/"
        rsp = self.fetch(url)
        if rsp and rsp.status_code == 200:
            res["list"] = self._extract_search_results(rsp.text)
        return res

    def detailContent(self, ids):
        res = {"list": []}
        vid = ids[0]
        rsp = self.fetch(f"{self.host}/voddetail/{vid}/")
        if not rsp or rsp.status_code != 200:
            return res
        html = rsp.text
        play_from, play_url = self._extract_play_info(html, vid)
        if play_from:
            res["list"] = [{
                "vod_id": vid,
                "vod_name": self._extract_title(html),
                "vod_pic": self._extract_pic(html),
                "vod_content": self._extract_desc(html),
                "vod_remarks": self._extract_remarks(html),
                "vod_play_from": "$$$".join(play_from),
                "vod_play_url": "$$$".join(play_url)
            }]
        return res

    def playerContent(self, flag, id, vipFlags):
        res = {"parse": 1, "playUrl": "", "url": ""}
        if "-" not in id:
            return res
        rsp = self.fetch(f"{self.host}/play/{id}/")
        if not rsp or rsp.status_code != 200:
            return res
        m3u8_reg = re.search(r'var player_aaaa=.*?"url":"([^"]+\.m3u8)"', rsp.text, re.S | re.I)
        if m3u8_reg:
            real_url = m3u8_reg.group(1).replace(r'\u002F', '/').replace(r'\/', '/')
            res["parse"] = 0
            res["url"] = real_url
        else:
            res["url"] = f"{self.host}/play/{id}/"
        return res

    def _get_filters(self):
        return {
            "1": [{"key": "class", "name": "类型", "value": [
                {"n": "全部", "v": ""}, {"n": "动作片", "v": "6"}, {"n": "喜剧片", "v": "7"},
                {"n": "爱情片", "v": "8"}, {"n": "科幻片", "v": "9"}, {"n": "恐怖片", "v": "11"}
            ]}],
            "2": [{"key": "class", "name": "类型", "value": [
                {"n": "全部", "v": ""}, {"n": "国产剧", "v": "13"}, {"n": "港台剧", "v": "14"},
                {"n": "日剧", "v": "15"}, {"n": "韩剧", "v": "33"}, {"n": "欧美剧", "v": "16"}
            ]}],
            "3": [{"key": "class", "name": "类型", "value": [
                {"n": "全部", "v": ""}, {"n": "内地综艺", "v": "27"}, {"n": "港台综艺", "v": "28"},
                {"n": "日本综艺", "v": "29"}, {"n": "韩国综艺", "v": "36"}
            ]}],
            "4": [{"key": "class", "name": "类型", "value": [
                {"n": "全部", "v": ""}, {"n": "国产动漫", "v": "31"}, {"n": "日本动漫", "v": "32"},
                {"n": "欧美动漫", "v": "42"}, {"n": "其他动漫", "v": "43"}
            ]}]
        }

    def _extract_videos(self, html, limit=0):
        video_list = []
        item_reg = r'<a href="/voddetail/(\d+)/".*?title="([^"]+)".*?<div class="module-item-note">([^<]+)</div>.*?data-original="([^"]+)"'
        for vid, name, remark, pic in re.findall(item_reg, html, re.S | re.I):
            full_img = self.host + pic if pic.startswith('/') else pic
            video_list.append({
                "vod_id": vid.strip(),
                "vod_name": name.strip(),
                "vod_pic": full_img.strip(),
                "vod_remarks": remark.strip()
            })
        return video_list[:limit] if limit and len(video_list) > limit else video_list

    def _extract_search_results(self, html):
        video_list = []
        soup = BeautifulSoup(html, "html.parser")
        for item in soup.select(".module-card-item"):
            a_tag = item.select_one('a[href^="/voddetail/"]')
            if not a_tag:
                continue
            href = a_tag.get("href", "")
            vid_match = re.search(r"/voddetail/(\d+)/", href)
            if not vid_match:
                continue
            vid = vid_match.group(1)
            title_tag = item.select_one(".module-card-item-title strong")
            img_tag = item.select_one("img")
            note_tag = item.select_one(".module-item-note")
            img_src = ""
            if img_tag:
                img_src = img_tag.get("data-original") or img_tag.get("src")
            full_img = self.host + img_src if (img_src and img_src.startswith('/')) else img_src
            title = title_tag.get_text(strip=True) if title_tag else ""
            remark = note_tag.get_text(strip=True) if note_tag else ""
            video_list.append({
                "vod_id": vid,
                "vod_name": title,
                "vod_pic": full_img,
                "vod_remarks": remark
            })
        return video_list

    def _extract_play_info(self, html, vid):
        
        tab_reg = r'<(?:div|a)[^>]*class="[^"]*module-tab-item[^"]*"[^>]*>(?:.*?<span>([^<]+)</span>.*?<small>(\d+)</small>|.*?<span>([^<]+)</span>.*?<small class="no">(\d+)</small>)</(?:div|a)>'
        all_valid_lines = []
        for match in re.findall(tab_reg, html, re.S | re.I):
            line_name = match[0] or match[2]
            lid = self._get_line_id(html, vid, line_name)
            
            ep_reg = rf'<a class="module-play-list-link" href="/play/{vid}-{lid}-(\d+)/"[^>]*>.*?<span>([^<]+)</span></a>'
            ep_items = re.findall(ep_reg, html, re.S | re.I)
            ep_join = "#".join([f"{ep_name}${vid}-{lid}-{num}" for num, ep_name in ep_items])
            if ep_join:
                all_valid_lines.append({"lid": lid, "eps": ep_join})
        
        target_eps = ""
        for line in all_valid_lines:
            if line["lid"] == "1":
                target_eps = line["eps"]
                break
        
        if not target_eps and all_valid_lines:
            target_eps = all_valid_lines[0]["eps"]
        
        if target_eps:
            return ["恒轩"], [target_eps]
        return [], []

    def _get_line_id(self, html, vid, line_name):
        lid_reg = re.search(rf'<a[^>]*href="/play/{vid}-(\d+)-1/"[^>]*>.*?<span>{re.escape(line_name)}</span>', html, re.S | re.I)
        if lid_reg:
            return lid_reg.group(1)
        line_map = {"全球3线": "3", "大陆0线": "1", "大陆3线": "4", "大陆5线": "2", "大陆6线": "3"}
        return line_map.get(line_name, "1")

    def _extract_title(self, html):
        title_reg = re.search(r'<meta property="og:title" content="([^"]+)-[^-]+$', html, re.S | re.I)
        return title_reg.group(1).strip() if title_reg else ""

    def _extract_pic(self, html):
        pic_reg = re.search(r'<meta property="og:image" content="([^"]+)"', html, re.S | re.I)
        if not pic_reg:
            return ""
        pic_url = pic_reg.group(1).strip()
        return self.host + pic_url if pic_url.startswith('/') else pic_url

    def _extract_desc(self, html):
        desc_reg = re.search(r'<meta property="og:description" content="([^"]+)"', html, re.S | re.I)
        return desc_reg.group(1).strip() if desc_reg else "暂无简介"

    def _extract_remarks(self, html):
        year_reg = re.search(r'<a title="(\d+)" href="/vodshow/\d+-----------\1/">', html, re.S | re.I)
        year = year_reg.group(1) if year_reg else "未知年份"
        area_reg = re.search(r'<a title="([^"]+)" href="/vodshow/\d+-%E5%A2%A8%E8%A5%BF%E5%93%A5----------/">', html, re.S | re.I)
        area = area_reg.group(1) if area_reg else "未知产地"
        type_reg = re.search(r'vod_class":"([^"]+)"', html, re.S | re.I)
        typ = type_reg.group(1).replace(",", "/") if type_reg else "未知类型"
        return f"{year} | {area} | {typ}"

# 本地调试入口（框架运行可保留，无base模块仅本地测试报错，不影响框架使用）
if __name__ == "__main__":
    spider = Spider()
    spider.init()
    # 测试详情
    detail_data = spider.detailContent(["86027"])
    if detail_data["list"]:
        print("影片名称：", detail_data["list"][0]["vod_name"])
        print("播放线路：", detail_data["list"][0]["vod_play_from"])
    # 测试搜索
    search_data = spider.searchContent("仙逆", False, 1)
    print("搜索结果数量：", len(search_data["list"]))
    # 测试解析播放地址
    play_data = spider.playerContent("", "86027-1-1", {})
    print("解析播放地址：", play_data["url"])
