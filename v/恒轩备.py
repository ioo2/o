# coding=utf-8
#!/usr/bin/python
import sys
sys.path.append('..')
from base.spider import Spider
import json
import urllib.parse
import re
from lxml import etree
from urllib.parse import urljoin

class Spider(Spider):
    
    def getName(self):
        return "恒轩影院"
    
    def init(self, extend):
        pass
    
    def homeContent(self, filter):
        result = {}
        cateManual = {
            "电视剧": "2",
            "电影": "1", 
            "动漫": "3",
            "综艺": "4",
                  }
        classes = [{'type_name': k, 'type_id': v} for k, v in cateManual.items()]
        result['class'] = classes
        
        filters = {
            "1": [{"key": "by", "name": "排序", "value": [{"n": "按时间", "v": "time"}, {"n": "按人气", "v": "hit"}]}],
            "2": [{"key": "by", "name": "排序", "value": [{"n": "按时间", "v": "time"}, {"n": "按人气", "v": "hit"}]}],
            "3": [{"key": "by", "name": "排序", "value": [{"n": "按时间", "v": "time"}, {"n": "按人气", "v": "hit"}]}],
            "4": [{"key": "by", "name": "排序", "value": [{"n": "按时间", "v": "time"}, {"n": "按人气", "v": "hit"}]}],
            "6": [{"key": "by", "name": "排序", "value": [{"n": "按时间", "v": "time"}, {"n": "按人气", "v": "hit"}]}]
        }
        result['filters'] = filters
        return result
    
    def homeVideoContent(self):
        try:
            rsp = self.fetch("http://qiyoudy5.com/")
            root = self.parse_html(rsp.content)
            if not root:
                return {'list': []}
            
            videos = []
            # 轮播图
            for a in root.xpath("//div[contains(@class,'carousel')]//a[contains(@class,'stui-vodlist__thumb')]"):
                try:
                    name = a.xpath(".//span[@class='pic-text text-center']/text()")[0].strip() if a.xpath(".//span[@class='pic-text text-center']/text()") else a.xpath("./@title")[0] if a.xpath("./@title") else "未知"
                    style = a.xpath("./@style")[0] if a.xpath("./@style") else ""
                    pic = re.search(r"background:\s*url\((.*?)\)", style).group(1) if re.search(r"background:\s*url\((.*?)\)", style) else ""
                    sid = a.xpath("./@href")[0] if a.xpath("./@href") else ""
                    videos.append({"vod_id": sid, "vod_name": name, "vod_pic": pic, "vod_remarks": "推荐"})
                except:
                    continue
            
            # 视频列表
            for a in root.xpath("//ul[contains(@class,'stui-vodlist')]//a[contains(@class,'stui-vodlist__thumb')]"):
                try:
                    name = a.xpath("./@title")[0] if a.xpath("./@title") else "未知"
                    pic = a.xpath("./@data-original")[0] if a.xpath("./@data-original") else ""
                    sid = a.xpath("./@href")[0] if a.xpath("./@href") else ""
                    remark = a.xpath(".//span[@class='pic-text text-right']/text()")[0] if a.xpath(".//span[@class='pic-text text-right']/text()") else ""
                    videos.append({"vod_id": sid, "vod_name": name, "vod_pic": pic, "vod_remarks": remark})
                except:
                    continue
            
            return {'list': videos}
        except:
            return {'list': []}
    
    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        try:
            order = extend.get('by', 'time') if extend else 'time'
            url = f'http://qiyoudy5.com/list/{tid}_{pg}.html?order={order}'
            rsp = self.fetch(url)
            root = self.parse_html(rsp.content)
            
            if not root:
                return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 90, 'total': 0}
            
            videos = []
            for a in root.xpath("//a[contains(@class,'stui-vodlist__thumb')]"):
                try:
                    name = a.xpath("./@title")[0] if a.xpath("./@title") else "未知"
                    pic = a.xpath("./@data-original")[0] if a.xpath("./@data-original") else ""
                    sid = a.xpath("./@href")[0] if a.xpath("./@href") else ""
                    remark = a.xpath(".//span[@class='pic-text text-right']/text()")[0] if a.xpath(".//span[@class='pic-text text-right']/text()") else ""
                    videos.append({"vod_id": sid, "vod_name": name, "vod_pic": pic, "vod_remarks": remark})
                except:
                    continue
            
            current_page = int(root.xpath("//ul[contains(@class,'stui-page')]//a[@class='active']/text()")[0]) if root.xpath("//ul[contains(@class,'stui-page')]//a[@class='active']/text()") else pg
            
            page_numbers = []
            for link in root.xpath("//ul[contains(@class,'stui-page')]//a[contains(@href,'list')]/@href"):
                match = re.search(r'list/\d+_(\d+)\.html', link)
                if match:
                    page_numbers.append(int(match.group(1)))
            total_page = max(page_numbers) if page_numbers else 1
            
            return {
                'list': videos,
                'page': current_page,
                'pagecount': total_page if total_page > 0 else 9999,
                'limit': 90,
                'total': 999999
            }
        except:
            return {'list': [], 'page': pg, 'pagecount': 1, 'limit': 90, 'total': 0}
    
    def detailContent(self, array):
        try:
            tid = array[0]
            url = f'http://qiyoudy5.com{tid}'
            rsp = self.fetch(url)
            root = self.parse_html(rsp.content)
            
            if not root:
                return {'list': []}
            
            # 基本信息
            detail_node = root.xpath("//div[contains(@class,'stui-content__detail')]") or root.xpath("//div[@class='stui-player__detail']")
            pic = title = area = director = actor = year = desc = ""
            
            if detail_node:
                detail_node = detail_node[0]
                pic = self.get_first(root.xpath("//meta[@property='og:image']/@content") or detail_node.xpath(".//img/@data-original"))
                title = self.get_first(detail_node.xpath(".//h1//text()"))
                if not title:
                    page_title = self.get_first(root.xpath("//title/text()"))
                    title = re.search(r"《(.*?)》", page_title).group(1) if page_title and re.search(r"《(.*?)》", page_title) else ""
                
                area = self.get_first(root.xpath("//meta[@property='og:video:area']/@content"))
                director = self.get_first(root.xpath("//meta[@property='og:video:director']/@content"))
                actor = self.get_first(root.xpath("//meta[@property='og:video:actor']/@content"))
                year_info = self.get_first(root.xpath("//p[@class='data']//text()[contains(.,'年份：')]"))
                year = re.search(r"年份：(\d{4})", year_info).group(1) if year_info and re.search(r"年份：(\d{4})", year_info) else ""
                desc = self.get_first(root.xpath("//meta[@property='og:description']/@content"))
            
          
            tabs = []
            # 收集所有有内容的tab播放列表
            for tab in root.xpath("//ul[contains(@class,'nav-tabs')]/li"):
                tab_id = self.get_first(tab.xpath(".//a/@href")).replace("#", "")
                if not tab_id:
                    continue
                episodes = []
                # 提取当前tab下的所有剧集
                for a in root.xpath(f"//div[@id='{tab_id}']//ul[contains(@class,'stui-content__playlist')]//a"):
                    name = self.get_first(a.xpath("./text()")) or "播放"
                    href = self.get_first(a.xpath("./@href"))
                    if href:
                        episodes.append({"name": name, "url": href})
                # 只保留有内容的tab
                if episodes:
                    tabs.append(episodes)

          
            selected_episodes = []
            if len(tabs) >= 3:  
                selected_episodes = tabs[2]
            elif len(tabs) >= 2:  
                selected_episodes = tabs[1]
            elif len(tabs) >= 1:  
                selected_episodes = tabs[0]

            # 处理剧集格式
            all_episodes = [f"{ep['name']}${ep['url']}|" for ep in selected_episodes]
            
            playFrom = ["恒轩"]  
            playUrl = []
            
            if all_episodes:
                processed_episodes = []
                for ep in all_episodes:
                    if "$" in ep:
                        ep_name, ep_url = ep.split("$", 1)
                        ep_url = ep_url.rstrip("|")  # 移除末尾的|
                        processed_episodes.append(f"{ep_name}${ep_url}")
                playUrl.append("#".join(processed_episodes))
            
            vod = {
                "vod_id": tid,
                "vod_name": title,
                "vod_pic": pic,
                "vod_year": year,
                "vod_area": area,
                "vod_actor": actor,
                "vod_director": director,
                "vod_content": desc
            }
            
            if playFrom and playUrl:
                vod['vod_play_from'] = "$$$".join(playFrom)
                vod['vod_play_url'] = "$$$".join(playUrl)
            
            return {'list': [vod]}
        except:
            return {'list': []}
    
    def searchContent(self, key, quick, page='1'):
        try:
            url = "http://qiyoudy5.com/search.php"
            post_data = {
                'searchword': key,
            }
            
            headers = {
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "http://qiyoudy5.com/",
                "Origin": "http://qiyoudy5.com"
            }
            
            rsp = self.post(url, data=post_data, headers=headers)
            
            root = self.parse_html(rsp.content)
            
            if not root:
                return {'list': []}
            
            videos = []
            
            selectors = [
                "//ul[contains(@class,'stui-vodlist__media')]//li",
                "//ul[contains(@class,'stui-vodlist')]//li",
                "//a[contains(@class,'stui-vodlist__thumb')]"
            ]
            
            result_items = []
            for selector in selectors:
                result_items = root.xpath(selector)
                if result_items:
                    break
            
            for item in result_items:
                try:
                    if item.tag == 'a':
                        href = self.get_first(item.xpath("./@href"))
                        title = self.get_first(item.xpath("./@title"))
                        pic = self.get_first(item.xpath("./@data-original"))
                        remark = self.get_first(item.xpath(".//span[contains(@class,'pic-text')]/text()"))
                    else:
                        link = item.xpath(".//a[contains(@class,'stui-vodlist__thumb')]") or item.xpath(".//a")
                        if not link:
                            continue
                        link = link[0]
                        href = self.get_first(link.xpath("./@href"))
                        title = self.get_first(link.xpath("./@title"))
                        pic = self.get_first(link.xpath("./@data-original"))
                        if not pic:
                            style = self.get_first(link.xpath("./@style"))
                            if style and "background-image" in style:
                                pic_match = re.search(r"background-image:\s*url\(['\"]?(.*?)['\"]?\)", style)
                                if pic_match:
                                    pic = pic_match.group(1)
                        remark = self.get_first(item.xpath(".//span[contains(@class,'pic-text')]/text()"))
                    
                    if href and title:
                        videos.append({
                            "vod_id": href,
                            "vod_name": title.strip(),
                            "vod_pic": pic,
                            "vod_remarks": remark or ""
                        })
                except Exception as e:
                    continue
            
            if not videos:
                for a in root.xpath("//a[contains(@href,'/vod/')]"):
                    try:
                        href = self.get_first(a.xpath("./@href"))
                        title = self.get_first(a.xpath("./@title")) or self.get_first(a.xpath(".//text()"))
                        pic = self.get_first(a.xpath("./@data-original"))
                        remark = self.get_first(a.xpath(".//span[contains(@class,'pic-text')]/text()"))
                        
                        if href and title:
                            videos.append({
                                "vod_id": href,
                                "vod_name": title.strip(),
                                "vod_pic": pic,
                                "vod_remarks": remark or ""
                            })
                    except:
                        continue
            
            seen = set()
            unique_videos = []
            for video in videos:
                identifier = (video["vod_id"], video["vod_name"])
                if identifier not in seen:
                    seen.add(identifier)
                    unique_videos.append(video)
            
            return {'list': unique_videos}
            
        except Exception as e:
            return {'list': []}
    
    def playerContent(self, flag, id, vipFlags):
        try:
            # 处理备用链接
            main_url = id
            backup_url = None
            
            # 分离主备链接
            if "|" in id:
                parts = id.split("|")
                if len(parts) >= 2:
                    main_url = parts[0].strip()
                    backup_url = parts[1].strip()
            
            # 获取主链接播放地址
            url = f"http://qiyoudy5.com{main_url}"
            play_info = self._get_play_url(url)
            
            # 如果主链接解析失败，尝试备用链接
            if play_info["parse"] == 1 and backup_url and backup_url.strip():
                backup_full_url = f"http://qiyoudy5.com{backup_url}"
                play_info = self._get_play_url(backup_full_url)
            
            return play_info
            
        except:
            return {"parse": 1, "playUrl": "", "url": f"http://qiyoudy5.com{id}", "header": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "http://qiyoudy5.com/",
            }}
    
    def _get_play_url(self, url):
        """辅助函数：获取播放地址"""
        try:
            rsp = self.fetch(url)
            _, html_content = self.parse_html(rsp.content, return_content=True)
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": url,
            }
            
            # 尝试解析API接口
            for pattern in [r"http://api\.yongfan99\.com:81/content\.php\?[^'\"]+", r"content\.php\?vid=[^&]+&type=[^'\"]+"]:
                match = re.search(pattern, html_content)
                if match:
                    api_url = match.group(0)
                    if not api_url.startswith('http'):
                        api_url = "http://api.yongfan99.com:81/" + api_url
                    try:
                        api_rsp = self.fetch(api_url, headers=headers)
                        m3u8_match = re.search(r'http[s]?://[^\s"\']+\.m3u8[^\s"\']*', api_rsp.text)
                        if m3u8_match:
                            return {"parse": 0, "playUrl": "", "url": m3u8_match.group(0), "header": headers}
                    except:
                        pass
            
            # 尝试解析iframe
            for pattern in [r'<iframe[^>]*src=[\'"]([^\'"]+)[\'"][^>]*>', r'src\s*=\s*[\'"]((?:http[^\'"]*)?/play/[^\'"]*)[\'"]']:
                for iframe_src in re.findall(pattern, html_content):
                    if not iframe_src.startswith('http'):
                        iframe_src = urljoin(url, iframe_src)
                    try:
                        iframe_rsp = self.fetch(iframe_src, headers=headers)
                        m3u8_match = re.search(r'http[s]?://[^\s"\']+\.m3u8[^\s"\']*', iframe_rsp.text)
                        if m3u8_match:
                            return {"parse": 0, "playUrl": "", "url": m3u8_match.group(0), "header": headers}
                    except:
                        continue
            
            # 直接在页面中查找m3u8链接
            m3u8_match = re.search(r'http[s]?://[^\s"\']+\.m3u8[^\s"\']*', html_content)
            if m3u8_match:
                return {"parse": 0, "playUrl": "", "url": m3u8_match.group(0), "header": headers}
            
            # 解析失败，返回原链接
            return {"parse": 1, "playUrl": "", "url": url, "header": headers}
            
        except:
            return {"parse": 1, "playUrl": "", "url": url, "header": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "http://qiyoudy5.com/",
            }}

    def parse_html(self, content, return_content=False):
        encodings = ['utf-8', 'gbk', 'gb2312', 'iso-8859-1']
        html_content = None
        for encoding in encodings:
            try:
                html_content = content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if html_content is None:
            html_content = content.decode('utf-8', errors='replace')
        
        html_content = self.clean_html(html_content)
        root = etree.HTML(html_content)
        
        if return_content:
            return root, html_content
        return root

    def get_first(self, array, default=""):
        return array[0] if array else default

    def clean_html(self, html_content):
        html_content = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', html_content)
        replacements = {'&nbsp;': ' ', '&amp;': '&', '&lt;': '<', '&gt;': '>', '&quot;': '"'}
        for old, new in replacements.items():
            html_content = html_content.replace(old, new)
        return html_content

    def isVideoFormat(self, url):
        return any(fmt in url for fmt in ['.m3u8', '.mp4', '.avi', '.mkv', '.flv', '.webm'])

    def manualVideoCheck(self):
        return True

    def localProxy(self, param):
        return {}