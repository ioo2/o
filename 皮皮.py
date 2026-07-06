import re, sys, uuid
from base.spider import Spider
sys.path.append('..')
class Spider(Spider):
    host, config, local_uuid, parsing_config = '', '', '', []
    headers = {
        'User-Agent': "Dart/2.19 (dart:io)",
        'Accept-Encoding': "gzip",
        'appto-local-uuid': local_uuid,
        'token': "eyJhbGciOiJIUzI1NiJ9.eyJkYXRhIjp7InVzZXJfY2hlY2siOiI4ZTEyNDE1Y2UyOGQzMGM4MWE3MDBiNWYxMDgzZTU2OCIsInVzZXJfbmFtZSI6IjEwMTAxMiJ9LCJleHAiOjE4MDQ3MzkyODAuNjA4MTA4MywiaWF0IjoxNzczMjAzMjgxLCJpc3MiOiJBcHBUbyIsImp0aSI6ImZmZDMyYjk4N2VkMTg1ZjNiNGQ5Zjc5NzU2YWRjNGQ5IiwibmJmIjoxNzczMjAzMjgxLCJzdWIiOiJBcHBUbyJ9.tDhURwWVzsPy0-yXvo_d3bgsmoq9Ri5n0Y4fQsvxKy0"
    }
    DANMU_SOURCE_LIST = [
        "https://logvar-danmu.rinrin.top/87654321|0",
        "https://logvar-danmu.rinrin.top|0",
        "https://danmu.iyo.us.ci/theft-dastardly-prognosis-hula-agenda2-dropkick|3",
        "https://justdanmu.irisnb.com/iris-danmu|0",
        "https://danmu.qianting168.com/456765847636987622146901|3",
        "https://dm.ljiaovm.com/luosen|3",
        "https://danm.lubao2.de5.net/87654321|3",
        "https://dm.abai.ccwu.cc/abai|0"
    ]

    def init(self, extend=''):
        try:
            host = extend.strip()
            if not host.startswith('http'):
                return {}
            if not re.match(r'^https?://[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*(:\d+)?/?$', host):
                host_ = self.fetch(host).json()
                self.host = host_['domain']
            else:
                self.host = host
            self.local_uuid = str(uuid.uuid4())
            self.headers['appto-local-uuid'] = self.local_uuid
            response = self.fetch(f'{self.host}/apptov5/v1/config/get?p=android&__platform=android', headers=self.headers).json()
            config = response['data']
            self.config = config
            parsing_conf = config['get_parsing']['lists']
            parsing_config = {}
            for i in parsing_conf:
                if len(i['config']) != 0:
                    label = []
                    for j in i['config']:
                        if j['type'] == 'json':
                            label.append(j['label'])
                    parsing_config.update({i['key']: label})
            self.parsing_config = parsing_config
            return None
        except Exception as e:
            print(f'初始化异常：{e}')
            return {}

    def detailContent(self, ids):
        response = self.fetch(f"{self.host}/apptov5/v1/vod/getVod?id={ids[0]}", headers=self.headers).json()
        data3 = response['data']
        videos = []
        vod_play_url = ''
        vod_play_from = ''
        play_list = data3.get('vod_play_list', [])
        target_play = None
        for item in play_list:
            show_name = item.get('player_info', {}).get('show', '').strip()
            if "蓝光R线" in show_name:
                continue
            if "蓝光B线" in show_name:
                urls = item.get('urls', [])
                if urls and len(urls) > 0:
                    target_play = item
                    break
        if not target_play:
            for item in play_list:
                show_name = item.get('player_info', {}).get('show', '').strip()
                if "蓝光R线" in show_name:
                    continue
                urls = item.get('urls', [])
                if urls and len(urls) > 0:
                    target_play = item
                    break
        if target_play:
            play_url = ''
            for j in target_play['urls']:
                play_url += f"{j['name']}${target_play['player_info']['from']}@{j['url']}#"
            vod_play_from = '恒轩'
            vod_play_url = play_url.rstrip('#')
        videos.append({
            'vod_id': data3.get('vod_id'),
            'vod_name': data3.get('vod_name'),
            'vod_content': data3.get('vod_content'),
            'vod_remarks': data3.get('vod_remarks'),
            'vod_director': data3.get('vod_director'),
            'vod_actor': data3.get('vod_actor'),
            'vod_year': data3.get('vod_year'),
            'vod_area': data3.get('vod_area'),
            'vod_play_from': vod_play_from,
            'vod_play_url': vod_play_url
        })
        return {'list': videos}

    def searchContent(self, key, quick, pg='1'):
        url = f"{self.host}/apptov5/v1/search/lists?wd={key}&page={pg}&type=&__platform=android"
        response = self.fetch(url, headers=self.headers).json()
        data = response['data']['data']
        for i in data:
            if i.get('vod_pic').startswith('mac://'):
                i['vod_pic'] = i['vod_pic'].replace('mac://', 'http://', 1)
        return {'list': data, 'page': pg, 'total': response['data']['total']}

    def playerContent(self, flag, id, vipflags):
        default_ua = 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1'
        parsing_config = self.parsing_config
        parts = id.split('@')
        result = {
            'parse': 0,
            'url': '',
            'header': {'User-Agent': default_ua},
            'danmaku': ''
        }
        if len(parts) != 2:
            result['url'] = id
            return result
        playfrom, rawurl = parts
        label_list = parsing_config.get(playfrom)
        if not label_list:
            result['url'] = rawurl
            return result

        origin_danmu_url = f"{self.host}/apptov5/v1/danmu/get?playfrom={playfrom}&url={rawurl}"
        origin_fail = False
        try:
            danmu_resp = self.fetch(origin_danmu_url, headers=self.headers).text
            fail1 = "网页解析失败，可能是不支持的网页类型，请检查网页或稍后重试"
            fail2 = "URL拼写可能存在错误，请检查"
            if fail1 in danmu_resp or fail2 in danmu_resp:
                origin_fail = True
        except Exception as e:
            print(f"原弹幕接口请求失败：{e}")
            origin_fail = True

        if origin_fail:
            valid_danmu = ""
            for source in self.DANMU_SOURCE_LIST:
                try:
                    resp_text = self.fetch(source, headers={"User-Agent": default_ua}).text
                    fail1 = "网页解析失败，可能是不支持的网页类型，请检查网页或稍后重试"
                    fail2 = "URL拼写可能存在错误，请检查"
                    if fail1 not in resp_text and fail2 not in resp_text:
                        valid_danmu = source
                        break
                    print(f"弹幕源{source}解析失败，自动切换下一条")
                except Exception as e:
                    print(f"弹幕源{source}访问异常，跳转下一条，错误：{e}")
                    continue
            result['danmaku'] = valid_danmu
        else:
            result['danmaku'] = origin_danmu_url

        for label in label_list:
            payload = {
                'play_url': rawurl,
                'label': label,
                'key': playfrom
            }
            try:
                response = self.post(
                    f"{self.host}/apptov5/v1/parsing/proxy?__platform=android",
                    data=payload,
                    headers=self.headers
                ).json()
            except Exception as e:
                print(f"请求异常: {e}")
                continue
            if not isinstance(response, dict):
                continue
            if response.get('code') == 422:
                continue
            data = response.get('data')
            if not isinstance(data, dict):
                continue
            url = data.get('url')
            if not url:
                continue
            ua = data.get('UA') or data.get('UserAgent') or default_ua
            result = {
                'parse': 0,
                'url': url,
                'header': {'User-Agent': ua},
                'danmaku': result['danmaku']
            }
            break
        return result

    def homeContent(self, filter):
        config = self.config
        if not config:
            return {}
        home_cate = config['get_home_cate']
        classes = []
        for i in home_cate:
            if isinstance(i.get('extend', []), dict):
                classes.append({'type_id': i['cate'], 'type_name': i['title']})
        return {'class': classes}

    def homeVideoContent(self):
        response = self.fetch(f'{self.host}/apptov5/v1/home/data?id=1&mold=1&__platform=android', headers=self.headers).json()
        data = response['data']
        vod_list = []
        for i in data['sections']:
            for j in i['items']:
                vod_pic = j.get('vod_pic')
                if vod_pic.startswith('mac://'):
                    vod_pic = vod_pic.replace('mac://', 'http://', 1)
                vod_list.append({
                    "vod_id": j.get('vod_id'),
                    "vod_name": j.get('vod_name'),
                    "vod_pic": vod_pic,
                    "vod_remarks": j.get('vod_remarks')
                })
        return {'list': vod_list}

    def categoryContent(self, tid, pg, filter, extend):
        response = self.fetch(f"{self.host}/apptov5/v1/vod/lists?area={extend.get('area','')}&lang={extend.get('lang','')}&year={extend.get('year','')}&order={extend.get('sort','time')}&type_id={tid}&type_name=&page={pg}&pageSize=21&__platform=android", headers=self.headers).json()
        data = response['data']
        data2 = data['data']
        for i in data['data']:
            if i.get('vod_pic', '').startswith('mac://'):
                i['vod_pic'] = i['vod_pic'].replace('mac://', 'http://', 1)
        return {'list': data2, 'page': pg, 'total': data['total']}

    def getName(self):
        pass
    def isVideoFormat(self, url):
        pass
    def manualVideoCheck(self):
        pass
    def destroy(self):
        pass
    def localProxy(self, param):
        pass