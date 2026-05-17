# -*- coding: utf-8 -*-
import re,json,urllib.parse
from base.spider import Spider

class Spider(Spider):
    def_headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    }
    host = 'https://www.ht10010.com'

    def getName(self):
        return '枫叶影院'

    def init(self, extend=''):
        pass

    def homeContent(self, filter):
        return {'class':[
            {'type_id':'2','type_name':'电视剧'},
            {'type_id':'1','type_name':'电影'},
            {'type_id':'4','type_name':'动漫'},
            {'type_id':'3','type_name':'综艺'},
        ]}

    def homeVideoContent(self):
        return {'list':[]}

    def categoryContent(self, tid, pg, filter, extend):
        html = self._fetch(f'/type/{tid}.html')
        return {'page':int(pg),'pagecount':99,'limit':36,'total':999,'list':self._extractList(html)}

    def detailContent(self, ids):
        result = {'list':[]}
        vid = ids[0].split(',')[0].strip()
        try:
            html = self._fetch(f'/detail/{vid}.html')
            if not html: return result
            title = re.search(r'<h3[^>]*class="[^"]*slide-info-title[^"]*"[^>]*>([^<]*)</h3>', html)
            vod_name = title.group(1).strip() if title else ''
            pic = re.search(r'<img[^>]*class="[^"]*lazy[^"]*"[^>]*data-src="([^"]*)"', html)
            vod_pic = self._fixPic(pic.group(1)) if pic else ''
            dir_m = re.search(r'导演：</strong>\s*([^<]*)', html)
            vod_director = dir_m.group(1).strip() if dir_m else ''
            act_m = re.search(r'演员：</strong>(.*?)</div>', html)
            if act_m: vod_actor = re.sub(r'<[^>]+>', ' ', act_m.group(1)).strip()
            else: vod_actor = ''
            vod_content = ''
            tab_area = re.search(r'<div class="anthology-tab[^"]*"[^>]*>(.*?)</div>\s*<div class="anthology-list', html, re.S)
            single_ep_list = []
            if tab_area:
                raw_tabs = re.findall(r'<a[^>]*class="[^"]*swiper-slide[^"]*"[^>]*>(.*?)</a>', tab_area.group(1))
                tabs = [re.sub(r'<[^>]+>','',t).replace('&nbsp;','').replace('\u00a0','').strip() for t in raw_tabs]
                tabs = [t for t in tabs if t]
                tab_blocks = re.findall(r'<div class="anthology-list-box[^"]*"[^>]*>(.*?)</div>\s*</div>', html, re.S)
                priority_idx = -1
                for idx, t in enumerate(tabs):
                    if '4k' in t.lower() or '至臻' in t:
                        priority_idx = idx
                        break
                if priority_idx != -1 and priority_idx < len(tab_blocks):
                    block_4k = tab_blocks[priority_idx]
                    eps_4k = re.findall(r'<a[^>]*href="(/play/[^"]*)"[^>]*>(.*?)</a>', block_4k)
                    if eps_4k:
                        for href, name in eps_4k:
                            m = re.search(r'/play/(.*?)\.html', href)
                            if m: single_ep_list.append(f'{name.strip()}${m.group(1)}')
                if not single_ep_list:
                    for block in tab_blocks:
                        eps = re.findall(r'<a[^>]*href="(/play/[^"]*)"[^>]*>(.*?)</a>', block)
                        for href, name in eps:
                            m = re.search(r'/play/(.*?)\.html', href)
                            if m: single_ep_list.append(f'{name.strip()}${m.group(1)}')
                        if single_ep_list: break
                single_ep_list.reverse()
            play_from = ['恒轩']
            play_url = ['#'.join(single_ep_list)] if single_ep_list else ['']
            result['list'].append({
                'vod_id':vid,
                'vod_name':vod_name,
                'vod_pic':vod_pic,
                'vod_director':vod_director,
                'vod_actor':vod_actor,
                'vod_content':vod_content,
                'vod_play_from':'$$$'.join(play_from),
                'vod_play_url':'$$$'.join(play_url)
            })
        except: pass
        return result

    def searchContent(self, key, quick, pg='1'):
        html = self._fetch(f'/cupfox-search/{urllib.parse.quote(key)}----------{pg}---.html')
        return {'list':self._extractList(html),'page':int(pg),'pagecount':1,'limit':36,'total':0}

    def playerContent(self, flag, id, vipFlags):
        try:
            url = f'{self.host}/play/{id}.html'
            html = self._fetch(url)
            if not html: return {'parse':1,'url':url,'header':self.def_headers}
            m = re.search(r'var\s+player_aaaa\s*=\s*(\{.*?\});', html, re.S)
            if m:
                try:
                    pd = json.loads(m.group(1))
                    pu = pd.get('url','')
                    if pu:
                        header = {'User-Agent': self.def_headers['User-Agent'], 'Referer': self.host + '/'}
                        if pu.endswith('.m3u8') or pu.endswith('.mp4'):
                            return {'parse': 0, 'url': pu, 'header': header}
                        if pu.startswith('http'):
                            return {'parse': 1, 'url': pu, 'header': header}
                except: pass
            return {'parse':1,'url':url,'header':self.def_headers}
        except: return {'parse':1,'url':id,'header':self.def_headers}

    def localProxy(self, param=''): return {}
    def isVideoFormat(self, url): return False
    def manualVideoCheck(self): return False

    def _fetch(self, url):
        try:
            if not url.startswith('http'): url = self.host + url
            rsp = self.fetch(url, headers=self.def_headers, verify=False)
            return rsp.text if rsp else ''
        except: return ''

    def _fixPic(self, u):
        if not u: return ''
        if u.startswith('//'): return 'https:' + u
        return u.replace('&amp;','&')

    def _extractList(self, html):
        videos, seen = [], set()
        cards = re.findall(r'<a[^>]*class="public-list-exp"[^>]*href="/detail/(\d+)\.html"[^>]*title="([^"]*)"[^>]*>.*?<img[^>]*data-src="([^"]*)"', html, re.S)
        for vid, title, pic in cards:
            if vid in seen: continue
            seen.add(vid)
            remark_block = re.findall(r'<div[^>]*class="public-list-box[^"]*"[^>]*>.*?href="/detail/' + vid + r'\.html".*?' r'<i[^>]*class="ft2"[^>]*>([^<]*)</i>', html, re.S)
            remark = remark_block[0].strip() if remark_block else ''
            videos.append({'vod_id':vid,'vod_name':title.strip(),'vod_pic':self._fixPic(pic),'vod_remarks':remark})
        return videos
