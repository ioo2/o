import re, sys, json, base64
from Crypto.Cipher import AES
from urllib.parse import urljoin
from Crypto.Util.Padding import unpad

from base.spider import Spider
sys.path.append('..')

class Spider(Spider):
    headers = {'User-Agent': 'okhttp/4.12.0'}
    FIXED_CONFIG = {
        'host': 'http://cms.9513tv.vip',
        'cmskey': 'ziKv8NzFSwNoBUYRJclwwjRaiTWBb7ON',
        'RawPlayUrl': 0
    }
    
    PLAY_LINE_PRIORITY = ['移动', '天翼云', '腾讯', '爱奇艺', '优酷', '芒果']

    def init(self, extend=''):
        self.host = self.FIXED_CONFIG['host']
        self.cmskey = self.FIXED_CONFIG.get('cmskey', '')
        self.raw_play_url = 1 if self.FIXED_CONFIG.get('RawPlayUrl', 0) == 1 else 0

    def homeVideoContent(self):
        data = self.fetch(f"{self.host}/api.php/app/index_video?token=", headers=self.headers).json()
        videos = []
        for item in data['list']:
            videos.extend(item['vlist'])
        return {'list': videos}

    def homeContent(self, filter):
        data = self.fetch(f"{self.host}/api.php/app/nav?token=", headers=self.headers).json()
        keys = ["class", "area", "lang", "year", "letter", "by", "sort"]
        filters = {}
        classes = []
        for item in data['list']:
            has_non_empty_field = False
            jsontype_extend = item["type_extend"]
            classes.append({"type_name": item["type_name"], "type_id": item["type_id"]})
            for key in keys:
                if key in jsontype_extend and jsontype_extend[key].strip() != "":
                    has_non_empty_field = True
                    break
            if has_non_empty_field:
                filters[str(item["type_id"])] = []
            for dkey in jsontype_extend:
                if dkey in keys and jsontype_extend[dkey].strip() != "":
                    values = jsontype_extend[dkey].split(",")
                    value_array = []
                    for value in values:
                        if value.strip() != "":
                            value_array.append({"n": value.strip(), "v": value.strip()})
                    filters[str(item["type_id"])].append({"key": dkey, "name": dkey, "value": value_array})
        return {"class": classes, "filters": filters}

    def categoryContent(self, tid, pg, filter, extend):
        query_params = [f"tid={tid}", f"pg={pg}", f"limit=18"]
        for k in ['class', 'area', 'lang', 'year']:
            if extend.get(k):
                query_params.append(f"{k}={extend.get(k)}")
        url = f"{self.host}/api.php/app/video?" + "&".join(query_params)
        data = self.fetch(url, headers=self.headers).json()
        return data

    def searchContent(self, key, quick, pg="1"):
        data = self.fetch(f"{self.host}/api.php/app/search?text={key}&pg={pg}", headers=self.headers).json()
        for item in data['list']:
            item.pop('type', None)
        return {'list': data['list'], 'page': pg}

    def detailContent(self, ids):
        
        data = self.fetch(f"{self.host}/api.php/app/video_detail?id={ids[0]}", headers=self.headers).json()['data']
        play_line_map = {}
        
        for item in data['vod_url_with_player']:
            line_name = item['name'].strip()
            
            if line_name not in self.PLAY_LINE_PRIORITY:
                continue
            url_list = item['url'].split('#')
            decrypted_urls = []
            for j in url_list:
                if not j:
                    continue
                
                url_parts = j.split('$', 1)
                if len(url_parts) == 2:
                    decrypted_urls.append(f"{url_parts[0]}${self.lvdou(url_parts[1])}")
            
            if decrypted_urls:
                play_line_map[line_name] = '#'.join(decrypted_urls)
        
        
        final_play_url = ''
        for priority_line in self.PLAY_LINE_PRIORITY:
            if priority_line in play_line_map:
                final_play_url = play_line_map[priority_line]
                break
        
        
        data.pop('vod_url_with_player')
        data['vod_play_from'] = '恒轩'  
        data['vod_play_url'] = final_play_url  
        return {'list': [data]}

    def playerContent(self, flag, video_id, vipFlags):
        jx = 0
        if self.check_paly_url(video_id):
            if self.raw_play_url == 1:
                video_id = self.raw_url(video_id)
        elif re.search(r'(?:www\.iqiyi|v\.qq|v\.youku|www\.mgtv|www\.bilibili)\.com', video_id):
            jx = 1
        return {'jx': jx, 'playUrl': '', 'parse': 0, 'url': video_id, 'header': self.headers}

    def lvdou(self, text):
        key = self.cmskey[:16].encode("utf-8")
        iv = self.cmskey[-16:].encode("utf-8")
        url_prefix = "lvdou+"
        if original_text := text.startswith(url_prefix) and text:
            ciphertext_b64 = text[len(url_prefix):]
            try:
                cipher = AES.new(key, AES.MODE_CBC, iv)
                ct_bytes = base64.b64decode(ciphertext_b64)
                pt_bytes = cipher.decrypt(ct_bytes)
                return unpad(pt_bytes, AES.block_size).decode('utf-8')
            except Exception:
                return text
        return text

    def raw_url(self, original_url):
        try:
            response = self.fetch(original_url, allow_redirects=False, stream=True, timeout=20)
            if 300 <= response.status_code < 400 and (redirect_location := response.headers.get('Location')):
                return urljoin(original_url, redirect_location)
            return original_url
        except Exception:
            return original_url

    def check_paly_url(self, content):
        pattern = r"https?://.*(?:\.(?:mp4|m3u8|flv|avi|mkv|ts|mov|wmv|webm)|lyyytv\.cn/)"
        return bool(re.search(pattern, content, re.IGNORECASE))

    
    def getName(self):
        pass
    def localProxy(self, param):
        pass
    def isVideoFormat(self, url):
        pass
    def manualVideoCheck(self):
        pass
    def destroy(self):
        pass
