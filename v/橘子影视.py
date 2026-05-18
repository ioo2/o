import re, sys, urllib3
from base.spider import Spider
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sys.path.append('..')

class Spider(Spider):
    
    headers = {
        'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        'Accept-Encoding': "gzip"
    }
    host = ''

    def init(self, extend=''):
        if extend:
            extend = extend.strip()
            if extend.startswith('http'):
                self.host = extend.rstrip('/')

    def homeContent(self, filter):
        url = f'{self.host}/api.php?type=getsort'
        response = self.fetch(url, headers=self.headers, verify=False).json()
        classes, filters = [], {}
        
        if 'list' in response:
            for i in response['list']:
                type_id = str(i['type_id'])
                classes.append({'type_id': type_id, 'type_name': i['type_name']})
                
                if 'type_extend' in i and i['type_extend']:
                    extend = i['type_extend']
                    filter_list = []
                    
                    if 'class' in extend and extend['class']:
                        value_list = [{"n": "全部", "v": "全部"}]
                        for val in extend['class'].split(','):
                            if val.strip():
                                value_list.append({"n": val.strip(), "v": val.strip()})
                        filter_list.append({"key": "class", "name": "类型", "init": "全部", "value": value_list})
                    
                    if 'year' in extend and extend['year']:
                        value_list = [{"n": "全部", "v": "全部"}]
                        for val in extend['year'].split(','):
                            if val.strip():
                                value_list.append({"n": val.strip(), "v": val.strip()})
                        filter_list.append({"key": "year", "name": "年份", "init": "全部", "value": value_list})
                    
                    if filter_list:
                        filters[type_id] = filter_list
        return {'class': classes, 'filters': filters}

    def homeVideoContent(self):
        url = f'{self.host}/api.php?type=getHome'
        response = self.fetch(url, headers=self.headers, verify=False).json()
        videos = []
        
        for j in response.values():
            if isinstance(j, dict) and 'list' in j:
                lis = j.get('list')
                if isinstance(lis, list):
                    videos.extend(lis)
        return {'list': videos}

    def categoryContent(self, tid, pg, filter, extend):
        tag = extend.get('class', '全部') if extend else '全部'
        year = extend.get('year', '全部') if extend else '全部'
        
        url = f"{self.host}/api.php?type=getvod&type_id={tid}&page={pg}&tag={tag}&year={year}"
        response = self.fetch(url, headers=self.headers, verify=False).json()
        
        return {'list': response.get('list', []), 'page': int(pg), 'pagecount': response.get('pagecount', 1), 'total': response.get('total', 0)}

    def searchContent(self, key, quick, pg="1"):
        url = f'{self.host}/api.php?type=getsearch&text={key}'
        response = self.fetch(url, headers=self.headers, verify=False).json()
        raw_list = response.get('list', [])
        
        seen_ids = set()
        new_list = []
        for item in raw_list:
            vod_id = item.get("vod_id")
            if vod_id and vod_id not in seen_ids:
                seen_ids.add(vod_id)
                new_list.append(item)

        return {
            'list': new_list,
            'page': int(pg),
            'pagecount': response.get('pagecount', 1),
            'total': len(new_list)
        }

    def detailContent(self, ids):
        url = f'{self.host}/api.php?type=getVodinfo&id={ids[0]}'
        response = self.fetch(url, headers=self.headers, verify=False).json()
        
        final_url = ""
        
        if 'vod_player' in response and 'list' in response['vod_player']:
            for i in response['vod_player']['list']:
                play_url = i.get('url', '')
                if play_url:
                    processed_urls = []
                    for item in play_url.split('#'):
                        if item.strip():
                            processed_urls.append(f"{item.strip()}@{ids[0]}")
                    final_url = '#'.join(processed_urls)
                    break
        
        if not final_url:
            final_url = "无数据"

        video = {
            'vod_name': response.get('vod_name', ''),
            'vod_pic': response.get('vod_pic', ''),
            'vod_id': response.get('vod_id', ''),
            'vod_class': response.get('vod_class', ''),
            'vod_actor': response.get('vod_actor', ''),
            'vod_blurb': response.get('vod_blurb', ''),
            'vod_content': response.get('vod_content', response.get('vod_blurb', '')),
            'vod_remarks': response.get('vod_remarks', ''),
            'vod_play_from': '恒轩',
            'vod_play_url': final_url
        }
        return {'list': [video]}

    def playerContent(self, flag, id, vipflags):
        jx = 0
        ua = 'Dalvik/2.1.0 (Linux; U; Android 14; Xiaomi 15 Build/SQ3A.220705.004)'
        ua2 = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'
        url = ''
        parts = id.split('@')
        vod_url = parts[0]
        vod_id = parts[1] if len(parts) > 1 else ''
        
        try:
            jx_url = f'{self.host}/api.php?type=jx&vodurl={vod_url}&vodid={vod_id}'
            response = self.fetch(jx_url, headers=self.headers, verify=False).json()
            if 'url' in response and response['url']:
                play_url = response['url']
                if play_url.startswith('http'):
                    url = play_url
        except Exception:
            pass
            
        if not url:
            url = vod_url
            if re.search(r'(?:www\.iqiyi|v\.qq|v\.youku|www\.mgtv|www\.bilibili)\.com', vod_url):
                jx = 1
                ua = ua2
                
        return {'jx': jx, 'parse': 0, 'url': url, 'header': {'User-Agent': ua}}

    def getName(self): pass
    def isVideoFormat(self, url): pass
    def manualVideoCheck(self): pass
    def destroy(self): pass
    def localProxy(self, param): pass
