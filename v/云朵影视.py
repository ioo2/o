# -*- coding: utf-8 -*-
import sys
import json
import re
import time
from urllib.parse import quote, unquote, urljoin
sys.path.append('..')

try:
    from base.spider import Spider
except ImportError:
    import requests as rq
    class Spider:
        def fetch(self, url, headers=None, **kw):
            kw.pop('timeout', None)
            r = rq.get(url, headers=headers, timeout=15, **kw)
            r.encoding = 'utf-8'
            return r
        def post(self, url, data=None, headers=None, **kw):
            kw.pop('timeout', None)
            r = rq.post(url, data=data, headers=headers, timeout=15, **kw)
            r.encoding = 'utf-8'
            return r

class Spider(Spider):

    def getName(self):
        return "云朵影视"

    def init(self, extend=""):
        if isinstance(extend, list):
            self.extend = ''
        else:
            self.extend = extend or ''
        self.host = "https://ds3xy2yunsa.xyz"
        self.api_base = self.host + "/api.php/web"
        self.sign = "yda81x6d9ad3c4s"
        self.client_id = "8f3d2a1c7b6e5d4c9a0b1f2e3d4c5b6a"
        self.header = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'X-Client': self.client_id,
            'web-sign': self.sign,
            'Referer': self.host + '/',
            'Connection': 'keep-alive',
        }

        self.jx_api = [
            "https://test1.12321app.com/daoliansiquanjia.php?url=",
            "https://json.cfysoft.cc/api/?key=db40a4b2f15c4078301a068181bb2724&url=",
            "https://player.gimy.bot/u/parse.php?url="
        ]
        self._home_cache = []
        self._home_cache_time = 0
        self._class_list = []
        self._type_map = {}

    def _fetch_json(self, url, timeout=15):
        try:
            rsp = self.fetch(url, headers=self.header, timeout=timeout)
            rsp.encoding = 'utf-8'
            return json.loads(rsp.text)
        except Exception:
            return None

    def _fix_pic(self, pic):
        if not pic:
            return ''
        if pic.startswith('//'):
            return 'https:' + pic
        if pic.startswith('/'):
            return self.host + pic
        return pic

    def homeContent(self, filter):
        result = {}
        default_classes = [
            {'type_id': '1', 'type_name': '电影'},
            {'type_id': '2', 'type_name': '剧集'},
            {'type_id': '3', 'type_name': '动漫'},
            {'type_id': '4', 'type_name': '综艺'},
        ]
        classes = []
        data = self._fetch_json(self.api_base + '/index/home', timeout=15)
        if data and data.get('code') == 200 and data.get('data'):
            d = data['data']
            if d.get('categories'):
                for c in d['categories']:
                    tid = str(c.get('type_id', ''))
                    tname = c.get('type_name', '')
                    classes.append({'type_id': tid, 'type_name': tname})
                    if tid and tname:
                        self._type_map[tid] = tname
        if not classes:
            classes = default_classes
            for c in classes:
                self._type_map[c['type_id']] = c['type_name']
        self._class_list = classes
        result['class'] = classes
        return result

    def homeVideoContent(self):
        now = int(time.time())
        if self._home_cache and now - self._home_cache_time < 300:
            return {'list': self._home_cache[:72]}
        videos = []
        seen = set()
        data = self._fetch_json(self.api_base + '/index/home', timeout=15)
        if data and data.get('code') == 200 and data.get('data'):
            d = data['data']
            if d.get('categories'):
                for cat in d['categories']:
                    for v in cat.get('videos', []):
                        vid = str(v.get('vod_id', ''))
                        if vid and vid not in seen:
                            seen.add(vid)
                            videos.append({
                                'vod_id': vid,
                                'vod_name': v.get('vod_name', ''),
                                'vod_pic': self._fix_pic(v.get('vod_pic', '')),
                                'vod_remarks': v.get('vod_remarks', ''),
                            })
                        if len(videos) >= 72:
                            break
                    if len(videos) >= 72:
                        break
        self._home_cache = videos[:72]
        self._home_cache_time = now
        return {'list': self._home_cache}

    def categoryContent(self, tid, pg, filter, extend):
        pg = str(pg or '1')
        tid = str(tid or '1')
        type_name = self._type_map.get(tid, '')
        fallback = {'1': '电影', '2': '剧集', '3': '动漫', '4': '综艺'}
        if not type_name:
            type_name = fallback.get(tid, '')
        params = 'type_name=' + quote(type_name) + '&page=' + pg + '&sort=hits'
        url = self.api_base + '/filter/vod?' + params
        data = self._fetch_json(url, timeout=20)
        videos = []
        pagecount = int(pg)
        if data and data.get('code') == 200 and data.get('data'):
            items = data['data']
            if isinstance(items, list):
                for item in items:
                    videos.append({
                        'vod_id': str(item.get('vod_id', '')),
                        'vod_name': item.get('vod_name', ''),
                        'vod_pic': self._fix_pic(item.get('vod_pic', '')),
                        'vod_remarks': item.get('vod_remarks', ''),
                    })
            if len(videos) >= 20:
                pagecount = int(pg) + 1
        return {
            'list': videos,
            'page': pg,
            'pagecount': pagecount,
            'limit': len(videos) or 20,
            'total': pagecount * 20,
        }

    def detailContent(self, ids):
        if isinstance(ids, str):
            ids = [ids]
        vod_id = str(ids[0])
        detail_data = self._fetch_json(self.api_base + '/vod/get_detail?vod_id=' + vod_id, timeout=20)
        vod = {
            'vod_id': vod_id,
            'vod_name': '',
            'vod_pic': '',
            'type_name': '',
            'vod_year': '',
            'vod_area': '',
            'vod_remarks': '',
            'vod_actor': '',
            'vod_director': '',
            'vod_content': '',
            'vod_play_from': '恒轩',  
            'vod_play_url': '',
        }
        if detail_data and detail_data.get('code') == 200 and detail_data.get('data'):
            item = detail_data['data'][0] if detail_data['data'] else {}
            vod['vod_name'] = item.get('vod_name', '')
            vod['vod_pic'] = self._fix_pic(item.get('vod_pic', ''))
            vod['type_name'] = item.get('type_name', '')
            vod['vod_year'] = str(item.get('vod_year', ''))
            vod['vod_area'] = item.get('vod_area', '') if isinstance(item.get('vod_area'), str) else ','.join(item.get('vod_area', []))
            vod['vod_remarks'] = item.get('vod_remarks', '')
            vod['vod_actor'] = item.get('vod_actor', '')
            vod['vod_director'] = item.get('vod_director', '')

            content = item.get('vod_content', '')
            if content:
                content = re.sub(r'<[^>]+>', '', content).strip()
            vod['vod_content'] = content

            vod['vod_play_url'] = item.get('vod_play_url', '')
        return {'list': [vod]}

    def searchContent(self, key, quick, pg="1"):
        pg = str(pg or '1')
        url = self.api_base + '/search/index?wd=' + quote(key) + '&page=' + pg + '&limit=20'
        data = self._fetch_json(url, timeout=15)
        videos = []
        if data and data.get('code') == 200 and data.get('data'):
            for item in data['data']:
                videos.append({
                    'vod_id': str(item.get('vod_id', '')),
                    'vod_name': item.get('vod_name', ''),
                    'vod_pic': self._fix_pic(item.get('vod_pic', '')),
                    'vod_remarks': item.get('vod_remarks', ''),
                })
        return {'list': videos}

    def searchContentPage(self, key, quick, pg):
        return self.searchContent(key, quick, pg)

    def playerContent(self, flag, id, vipFlags):
        if not id:
            return {'parse': 1, 'playUrl': '', 'url': ''}

        ep_url = id.split('$')[-1] if '$' in id else id

        jx_join = "|".join([api + quote(ep_url) for api in self.jx_api])
        return {
            'parse': 1,
            'playUrl': jx_join,
            'url': '',
            'header': {
                'User-Agent': self.header['User-Agent'],
                'Referer': self.host + '/',
            },
        }

    def localProxy(self, param):
        try:
            import urllib.parse as up
            raw_url = ''
            referer = self.host + '/'
            if isinstance(param, dict):
                raw_url = param.get('url', '') or param.get('u', '')
                referer = param.get('referer', '') or param.get('ref', '') or referer
            elif isinstance(param, str):
                qs = up.parse_qs(param)
                raw_url = qs.get('url', [''])[0] or qs.get('u', [''])[0]
                referer = qs.get('referer', [''])[0] or qs.get('ref', [''])[0] or referer
            media_url = unquote(raw_url) if raw_url else ''
            referer = unquote(referer) if referer else self.host + '/'
            if not media_url:
                return [404, 'text/plain', b'']
            headers = {
                'User-Agent': self.header['User-Agent'],
                'Referer': referer,
            }
            rsp = self.fetch(media_url, headers=headers, timeout=30)
            content = rsp.content if hasattr(rsp, 'content') else rsp.text.encode('utf-8')
            ctype = rsp.headers.get('Content-Type', '') if hasattr(rsp, 'headers') else ''
            return [200, ctype or 'application/octet-stream', content]
        except Exception:
            return [500, 'text/plain', b'proxy error']

    def isVideoFormat(self, url):
        return bool(re.search(r'\.(m3u8|mp4|flv|mkv|avi)(\?|$)', url or '', re.I))
    def manualVideoCheck(self):
        return True
    def destroy(self):
        pass
    def close(self):
        self.destroy()

if __name__ == '__main__':
    spider = Spider()
    spider.init()