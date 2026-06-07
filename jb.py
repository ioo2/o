# -*- coding: utf-8 -*-
# 恒轩：https://www.jubaba.cc
import json
import random
import re
import sys
from base64 import b64decode, b64encode
import requests
from Crypto.Hash import MD5
from pyquery import PyQuery as pq

sys.path.append('..')
from base.spider import Spider

class Spider(Spider):
    def init(self, extend=""):
        self.host = "https://www.jubaba.cc"
        self.headers.update({
            'referer': f'{self.host}/',
            'origin': self.host,
        })
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.get(self.host)

    def getName(self):
        return "恒轩"

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'sec-ch-ua': '"Chromium";v="134", "Not:A-Brand";v="8"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

    config = {
        "1": [{"key": "by", "name": "排序", "value": [{"n": "时间", "v": "time"}, {"n": "人气", "v": "hits"}, {"n": "评分", "v": "score"}]}],
        "2": [{"key": "by", "name": "排序", "value": [{"n": "时间", "v": "time"}, {"n": "人气", "v": "hits"}, {"n": "评分", "v": "score"}]}],
        "3": [{"key": "by", "name": "排序", "value": [{"n": "时间", "v": "time"}, {"n": "人气", "v": "hits"}, {"n": "评分", "v": "score"}]}],
        "4": [{"key": "by", "name": "排序", "value": [{"n": "时间", "v": "time"}, {"n": "人气", "v": "hits"}, {"n": "评分", "v": "score"}]}],
    }

    def clean_vod_name(self, raw_name):
        return re.sub(r'年番\d+$|第.+季$|\d+$|:.*$', '', raw_name).strip()

    # ===================== 【首页展示】最新修复 =====================
    def homeContent(self, filter):
        data = self.getpq()
        result = {}
        classes = []
        for k in data('ul.swiper-wrapper').eq(0)('li').items():
            a = k('a')
            href = a.attr('href')
            if href and 'type' in href:
                type_name = a.text().strip()
                if type_name == '推荐':
                    type_name = '恒轩'
                tid = re.search(r'type/(\d+)', href)
                if tid:
                    classes.append({
                        'type_name': type_name,
                        'type_id': tid.group(1)
                    })
        result['class'] = classes
        result['list'] = self.getlist(data('.tab-content.ewave-pannel_bd li'))
        result['filters'] = self.config
        return result

    def homeVideoContent(self):
        pass

    # ===================== 【列表展示】最新修复 =====================
    def categoryContent(self, tid, pg, filter, extend):
        area = extend.get('area', '')
        by = extend.get('by', '')
        year = extend.get('year', '')
        path = f"/vodshow/{tid}-{area}-{by}-----{pg}---{year}.html"
        data = self.getpq(path)
        result = {}
        result['list'] = self.getlist(data('ul.ewave-vodlist.clearfix li'))
        result['page'] = pg
        result['pagecount'] = 999
        result['limit'] = 90
        result['total'] = 999999
        return result

    # ===================== 【详情页展示】最新修复 =====================
    def detailContent(self, ids):
        data = self.getpq(f"/voddetail/{ids[0]}.html")
        v = data('.ewave-content__detail')
        vod_name = v('h1').text().strip()

        vod = {
            'type_name': data('.breadcrumb a').eq(1).text().strip(),
            'vod_name': vod_name,
            'vod_year': v('.data.hidden-sm').text().strip(),
            'vod_remarks': self.clean_vod_name(vod_name),
            'vod_actor': data('p').eq(1).text().replace('主演：', '').strip(),
            'vod_director': data('p').eq(2).text().replace('导演：', '').strip(),
            'vod_content': v('.desc.hidden-xs').text().strip(),
            'vod_pic': v('.ewave-content__thumb img').attr('data-original'),
            'vod_play_from': '恒轩',
            'vod_play_url': ''
        }

        nd = list(data('ul.nav-tabs.swiper-wrapper li').items())
        pd = list(data('ul.ewave-content__playlist').items())
        line_priority = ['自营b', '自营e', '自营c', '自营d', 'LZ有广', 'BF有广', 'YZ有广']
        play_url = ''

        for line in line_priority:
            for idx, ele in enumerate(nd):
                if ele.text().strip() == line and idx < len(pd):
                    play_url = '#'.join([f"{j.text()}${j('a').attr('href')}" for j in pd[idx]('li').items()])
                    break
            if play_url:
                break

        vod['vod_play_url'] = play_url
        return {'list': [vod]}

    # ===================== 【搜索】最新修复 =====================
    def searchContent(self, key, quick, pg="1"):
        if pg == "1":
            path = f"-------------.html?wd={key}"
        else:
            path = f"{key}----------{pg}---.html"
        data = self.getpq(f"/vodsearch/{path}")
        return {'list': self.getlist(data('ul.ewave-vodlist__media.clearfix li')), 'page': pg}

    # ===================== 【播放解析】正常可用 =====================
    def playerContent(self, flag, id, vipFlags):
        try:
            data = self.getpq(id)
            jstr = json.loads(data('.ewave-player__video script').eq(0).text().split('=', 1)[-1])
            res = self.session.post(f"{self.host}/bbplayer/api.php", data={'vid': jstr['url']}).json()['data']
            if re.search(r'\.m3u8|\.mp4', res['url']):
                url = res['url']
            elif res['urlmode'] == 1:
                url = self.decode1(res['url'])
            elif res['urlmode'] == 2:
                url = self.decode2(res['url'])
            else:
                url = jstr['url']
            return {'parse': 0, 'url': url, 'header': {'User-Agent': 'okhttp/3.12.1'}, 'click': ''}
        except Exception as e:
            return {'parse': 1, 'url': f"{self.host}{id}", 'header': {}, 'click': ''}

    def localProxy(self, param):
        pass

    def liveContent(self, url):
        pass

    def getpq(self, path='', min=0, max=3):
        r = self.session.get(f"{self.host}{path}")
        data = r.text
        try:
            if '人机验证' in data:
                jstr = pq(data)('script').eq(-1).html()
                token, tpath, stt = self.extract(jstr)
                body = {'value': self.encrypt(self.host, stt), 'token': self.encrypt(token, stt)}
                self.session.post(f"{self.host}{tpath}", data=body)
                return self.getpq(path, min + 1, max) if min <= max else pq(data)
            return pq(data)
        except:
            return pq(data.encode('utf-8'))

    def encrypt(self, s, staticchars):
        out = ""
        for c in s:
            i = staticchars.find(c)
            if i != -1:
                c = staticchars[(i + 3) % 62]
            a, b = random.randint(0, 61), random.randint(0, 61)
            out += staticchars[a] + c + staticchars[b]
        return self.e64(out)

    def extract(self, js):
        token = re.search(r'token = encrypt\("([^"]+)"\)', js).group(1)
        url = re.search(r"url = '([^']+)'", js).group(1)
        sc = re.search(r'staticchars = "([^"]+)"', js).group(1)
        return token, url, sc

    def decode1(self, val):
        url = self._custom_str_decode(val)
        p = url.split('/')
        k1 = json.loads(self.d64(p[1]))
        k2 = json.loads(self.d64(p[0]))
        return self._de_string(k1, k2, self.d64('/'.join(p[2:])))

    def _custom_str_decode(self, val):
        d = self.d64(val)
        k = self.md5("test")
        return self.d64(''.join(chr(ord(d[i]) ^ ord(k[i % len(k)])) for i in range(len(d))))

    def _de_string(self, ka, va, s):
        return ''.join(va[ka.index(c)] if c in ka else c for c in s)

    # ===================== 【最新解密KEY】 =====================
    def decode2(self, url):
        key = "7ydF9kE2RbD8sG4hJ6lPzNxQwTmZrVaBcXfHjKuLoAeSiCpMvOtpnIWqgUY"
        url = self.d64(url)
        r, i = "", 1
        while i < len(url):
            idx = key.find(url[i])
            r += key[(idx + 59) % 62] if idx != -1 else url[i]
            i += 3
        return r

    # ===================== 【通用列表】最新修复 =====================
    def getlist(self, data):
        v = []
        for item in data.items():
            t = item('.ewave-vodlist__thumb')
            a = item('.text-overflow a') or t
            href = a.attr('href')
            vid = re.search(r'/(\d+)\.html', href)
            if not vid:
                continue
            v.append({
                'vod_id': vid.group(1),
                'vod_name': self.clean_vod_name(t.attr('title') or a.text()),
                'vod_pic': t.attr('data-original') or t.attr('src'),
                'vod_remarks': item('.pic-text').text().strip()
            })
        return v

    def e64(self, t):
        return b64encode(t.encode()).decode()

    def d64(self, t):
        return b64decode(t).decode()

    def md5(self, t):
        h = MD5.new()
        h.update(t.encode())
        return h.hexdigest()
