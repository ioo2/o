# -*- coding: utf-8 -*-
# 麦田影院 - 单线路恒轩(崩溃修复版)
import re
import sys
import json
from urllib.parse import quote, unquote, urljoin
from pyquery import PyQuery as pq
from xml.etree import ElementTree as ET
sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.host = "https://www.mtyy5.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 11; MI 11) AppleWebKit/537.36 TVBox/1.0',
            'Accept': 'text/html,application/xml;q=0.9,*/*;q=0.8',
            'Referer': self.host,
            'Connection': 'keep-alive'
        }
        self.source_map = {"NBY":"高清NB源","1080zyk":"超清YZ源","ffm3u8":"极速FF源","lzm3u8":"稳定LZ源","yzzy":"YZ源"}
        self.DEFAULT_PIC = "https://pic.rmb.bdstatic.com/bjh/1d0b02d0f57f0a4212da8865de018520.jpeg"

    def getName(self):
        return "麦田影院"

    def clean_text(self, text):
        if not text: return ""
        try:
            if isinstance(text, bytes):
                text = text.decode('utf-8', errors='ignore') if 'utf-8' in str(text) else text.decode('gbk', errors='ignore')
            if '\\u' in text: text = text.encode('utf-8').decode('unicode_escape', errors='ignore')
            return re.sub(r'[\x00-\x1f\x7f]', '', text).strip()
        except:
            return str(text)

    def fetch_page(self, url, headers=None):
        try:
            resp = self.fetch(url, headers=headers or self.headers, timeout=15)
            resp.encoding = 'utf-8'
            if resp.status_code != 200: raise Exception(f"HTTP {resp.status_code}")
            return resp.text
        except Exception as e:
            self.log(f"Fetch err: {str(e)}")
            return ""

    def homeContent(self, filter):
        html = self.fetch_page(self.host)
        doc = pq(html) if html else pq('')
        result = {'class': [], 'list': []}
        for a in doc('div.head-nav a[href*="/vodtype/"]').items():
            if (cid := re.search(r'/vodtype/(\d+)\.html', a.attr('href'))):
                result['class'].append({'type_name': self.clean_text(a.text()), 'type_id': cid.group(1)})
        for box in doc('.public-list-box.public-pic-b').items():
            if (link := box.find('a.public-list-exp')) and (vid := re.search(r'/voddetail/(\d+)\.html', link.attr('href'))):
                img = link.find('img')
                pic = urljoin(self.host, img.attr('data-src') or img.attr('src') or "")
                result['list'].append({
                    'vod_id': vid.group(1),
                    'vod_name': self.clean_text(link.attr('title') or img.attr('alt') or ""),
                    'vod_pic': pic if pic else self.DEFAULT_PIC,
                    'vod_remarks': self.clean_text(box.find('.public-prt').text())
                })
        return result

    def categoryContent(self, tid, pg, filter, extend):
        url = f"{self.host}/vodtype/{tid}-{pg}.html" if int(pg) > 1 else f"{self.host}/vodtype/{tid}.html"
        html = self.fetch_page(url)
        doc = pq(html) if html else pq('')
        videos = []
        for box in doc('.public-list-box.public-pic-b').items():
            if (link := box.find('a')) and (vid := re.search(r'/voddetail/(\d+)\.html', link.attr('href'))):
                img = link.find('img')
                pic = urljoin(self.host, img.attr('data-src') or img.attr('src') or "")
                videos.append({
                    'vod_id': vid.group(1),
                    'vod_name': self.clean_text(link.attr('title') or img.attr('alt') or ""),
                    'vod_pic': pic if pic else self.DEFAULT_PIC,
                    'vod_remarks': self.clean_text(box.find('.public-prt').text())
                })
        return {'list': videos, 'page': pg, 'pagecount': 999, 'limit': 20, 'total': 9999}

    # 核心修复：全量空值校验，避免无播放源/空地址崩溃
    def detailContent(self, ids):
        if not ids or len(ids) == 0: return {"list": []}
        vid = ids[0]
        html = self.fetch_page(f"{self.host}/voddetail/{vid}.html")
        if not html: return {"list": []}
        doc = pq(html)
        # 基础信息空值校验
        pic = urljoin(self.host, doc('.role-card img').attr('data-src') or "")
        vod_info = {
            "vod_id": vid,
            "vod_name": self.clean_text(doc('h1.player-title-link').text() or ""),
            "vod_pic": pic if pic else self.DEFAULT_PIC,
            "vod_content": self.clean_text(doc('.card-text').text() or ""),
            "vod_play_from": "恒轩",  # 固定线路名
            "vod_play_url": ""        # 初始化空地址
        }
        # 解析播放源前置校验
        play_href = doc('.anthology-list-play a:first').attr('href') or ""
        play_url = urljoin(self.host, play_href) if play_href else f"{self.host}/vodplay/{vid}-1-1.html"
        play_html = self.fetch_page(play_url)
        if not play_html: return {"list": [vod_info]}
        play_doc = pq(play_html)
        sources = {}
        # 遍历播放源，过滤空值
        for tab in play_doc('a.vod-playerUrl[data-form]').items():
            form = tab.attr('data-form') or ""
            if not form: continue
            sname = self.source_map.get(form, self.clean_text(tab.text()))
            idx = list(play_doc('a.vod-playerUrl[data-form]')).index(tab[0])
            eps = []
            # 剧集地址空值过滤
            for e in play_doc('.anthology-list-box').eq(idx).find('a').items():
                e_text = self.clean_text(e.text())
                e_href = urljoin(self.host, e.attr('href') or "")
                if e_text and e_href:
                    eps.append(f"{e_text}${e_href}")
            if eps: sources[sname] = '#'.join(eps)
        # 核心逻辑：优先NBY，无则取第一个，全无为空（彻底避免next迭代器崩溃）
        play_data = ""
        if "高清NB源" in sources and sources["高清NB源"]:
            play_data = sources["高清NB源"]
        elif sources:
            # 转列表后取第一个，避免空迭代器报错
            source_vals = list(sources.values())
            play_data = source_vals[0] if source_vals and source_vals[0] else ""
        # 赋值播放地址
        vod_info["vod_play_url"] = play_data
        return {"list": [vod_info]}

    def searchContent(self, key, quick, pg="1"):
        try:
            rss_url = f"{self.host}/rss.xml?wd={quote(key)}"
            if (html := self.fetch_page(rss_url, headers={**self.headers, 'Accept': 'application/xml'})):
                root = ET.fromstring(html)
                videos = []
                seen = set()
                for item in root.findall('.//item'):
                    link = self.clean_text(item.findtext('link') or "")
                    if not link or (vid := re.search(r'/voddetail/(\d+)\.html', link)) is None:
                        continue
                    vid_str = vid.group(1)
                    if vid_str in seen: continue
                    seen.add(vid_str)
                    title = self.clean_text(item.findtext('title') or "")
                    if title:
                        videos.append({
                            "vod_id": vid_str,
                            "vod_name": title,
                            "vod_pic": self.DEFAULT_PIC,
                            "vod_remarks": f"主演: {self.clean_text(item.findtext('author') or '')[:15]}..." if item.findtext('author') else ""
                        })
                if videos: return {"list": videos, "page": int(pg)}
        except Exception as e:
            self.log(f"RSS err: {str(e)}")
        try:
            search_url = f"{self.host}/vodsearch/{quote(key)}---{pg}---.html"
            html = self.fetch_page(search_url)
            doc = pq(html) if html else pq('')
            videos = []
            seen = set()
            for box in doc('.public-list-box.public-pic-b').items():
                if (link := box.find('a')) and (vid := re.search(r'/voddetail/(\d+)\.html', link.attr('href'))):
                    vid_str = vid.group(1)
                    if vid_str in seen: continue
                    seen.add(vid_str)
                    img = link.find('img')
                    pic = urljoin(self.host, img.attr('data-src') or img.attr('src') or "")
                    videos.append({
                        "vod_id": vid_str,
                        "vod_name": self.clean_text(link.attr('title') or img.attr('alt') or ""),
                        "vod_pic": pic if pic else self.DEFAULT_PIC,
                        "vod_remarks": self.clean_text(box.find('.public-prt').text() or "")
                    })
            return {"list": videos, "page": int(pg)}
        except Exception as e:
            self.log(f"Web search err: {str(e)}")
            return {"list": [], "page": int(pg)}

    def isVideoUrl(self, url):
        return any(ext in url.lower() for ext in ['.mp4', '.m3u8', '.flv'])

    def playerContent(self, flag, id, vipFlags):
        if not id: return {"parse": 1, "url": "", "header": self.headers}
        play_url = urljoin(self.host, id)
        if not play_url.startswith(('http', 'https')):
            return {"parse": 1, "url": play_url, "header": self.headers}
        html = self.fetch_page(play_url)
        if not html: return {"parse": 1, "url": play_url, "header": self.headers}
        if (match := re.search(r'var player_aaaa=({[^}]+?url:[^}]+})', html, re.DOTALL)):
            try:
                data = json.loads(re.sub(r',\s*([}\]])', r'\1', match.group(1)))
                main = unquote(data.get('url', '')).strip()
                backup = unquote(data.get('url_next', '')).strip()
                play_addr = main if self.isVideoUrl(main) else backup if self.isVideoUrl(backup) else play_url
                return {
                    "parse": 0 if self.isVideoUrl(play_addr) else 1,
                    "url": play_addr,
                    "header": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": play_url}
                }
            except Exception as e:
                self.log(f"Player parse err: {str(e)}")
        return {"parse": 1, "url": play_url, "header": self.headers}
