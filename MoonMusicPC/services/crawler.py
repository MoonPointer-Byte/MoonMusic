import json
import random
import urllib.parse
import asyncio
import httpx
from bs4 import BeautifulSoup

class CrawlerService:
    def __init__(self, helper):
        self.helper = helper

    async def search_netease(self, keyword):
        url = "https://music.163.com/api/search/get/web"
        params = {"s": keyword, "type": 1, "offset": 0, "total": "true", "limit": 10}
        async with httpx.AsyncClient(verify=False) as client:
            try:
                headers = self.helper.get_headers("netease")
                resp = await client.post(url, headers=headers, data=params)
                data = resp.json()
                songs = data['result']['songs']
                results = []
                for s in songs:
                    pic_url = s.get('album', {}).get('picUrl', '')
                    if not pic_url and s.get('artists'): pic_url = s['artists'][0].get('img1v1Url', '')
                    results.append({
                        "name": s['name'],
                        "artist": s['artists'][0]['name'],
                        "id": s['id'],
                        "media_id": s['id'],
                        "pic": pic_url,
                        "url": f"http://music.163.com/song/media/outer/url?id={s['id']}.mp3",
                        "source": "网易"
                    })
                return results
            except:
                return []

    async def get_qq_purl(self, songmid, media_id=None):
        if not media_id: media_id = songmid
        guid = str(random.randint(1000000000, 9999999999))
        file_types = [{"prefix": "M500", "ext": "mp3", "mid": media_id},
                      {"prefix": "C400", "ext": "m4a", "mid": media_id}]
        url = "https://u.y.qq.com/cgi-bin/musicu.fcg"
        data = {
            "req": {"module": "CDN.SrfCdnDispatchServer", "method": "GetCdnDispatch",
                    "param": {"guid": guid, "calltype": 0, "userip": ""}},
            "req_0": {
                "module": "vkey.GetVkeyServer",
                "method": "CgiGetVkey",
                "param": {
                    "guid": guid,
                    "songmid": [songmid] * 2,
                    "songtype": [0] * 2,
                    "uin": self.helper.qq_uin,
                    "loginflag": 1,
                    "platform": "20",
                    "filename": [f"{ft['prefix']}{ft['mid']}.{ft['ext']}" for ft in file_types]
                }
            }
        }
        async with httpx.AsyncClient(verify=False) as client:
            try:
                headers = self.helper.get_headers("qq")
                resp = await client.get(url, params={"data": json.dumps(data)}, headers=headers)
                js = resp.json()
                midurlinfos = js.get('req_0', {}).get('data', {}).get('midurlinfo', [])
                sip = js.get('req_0', {}).get('data', {}).get('sip', [])
                for info in midurlinfos:
                    if info.get('purl'):
                        base = sip[0] if sip else "http://ws.stream.qqmusic.qq.com/"
                        return f"{base}{info['purl']}"
                return ""
            except:
                return ""

    async def search_qq(self, keyword):
        search_url = f"https://c.y.qq.com/soso/fcgi-bin/client_search_cp?p=1&n=10&w={keyword}&format=json"
        async with httpx.AsyncClient(verify=False) as client:
            try:
                headers = self.helper.get_headers("qq")
                resp = await client.get(search_url, headers=headers)
                text = resp.text
                if text.startswith("callback("):
                    text = text[9:-1]
                elif text.endswith(")"):
                    text = text[text.find("(") + 1:-1]
                data = json.loads(text)
                songs = data['data']['song']['list']
                results = []
                for s in songs:
                    songmid = s['songmid']
                    media_mid = s.get('media_mid', s.get('strMediaMid', songmid))
                    albummid = s['albummid']
                    pic = f"https://y.gtimg.cn/music/photo_new/T002R300x300M000{albummid}.jpg" if albummid else ""
                    results.append({
                        "name": s['songname'],
                        "artist": s['singer'][0]['name'],
                        "id": songmid,
                        "media_id": media_mid,
                        "pic": pic,
                        "url": "",
                        "source": "QQ"
                    })
                return results
            except:
                return []

    async def search_kugou(self, keyword):
        search_url = f"http://mobilecdn.kugou.com/api/v3/search/song?format=json&keyword={keyword}&page=1&pagesize=6"
        async with httpx.AsyncClient(verify=False) as client:
            try:
                headers = self.helper.get_headers("kugou")
                resp = await client.get(search_url, headers=headers)
                data = resp.json()
                songs = data['data']['info']
                tasks = []
                for s in songs:
                    tasks.append(client.get(
                        f"http://www.kugou.com/yy/index.php?r=play/getdata&hash={s['hash']}&album_id={s.get('album_id', '')}",
                        headers=headers))
                detail_resps = await asyncio.gather(*tasks, return_exceptions=True)
                results = []
                for r in detail_resps:
                    if isinstance(r, httpx.Response):
                        try:
                            d = r.json()['data']
                            if d['play_url']:
                                results.append({
                                    "name": d['audio_name'],
                                    "artist": d['author_name'],
                                    "id": d['hash'],
                                    "media_id": d['hash'],
                                    "pic": d['img'],
                                    "url": d['play_url'],
                                    "source": "酷狗"
                                })
                        except:
                            pass
                return results
            except:
                return []

    async def search_all(self, keyword, platform="all"):
        tasks = []
        if platform in ["all", "netease"]: tasks.append(self.search_netease(keyword))
        if platform in ["all", "qq"]: tasks.append(self.search_qq(keyword))
        if platform in ["all", "kugou"]: tasks.append(self.search_kugou(keyword))
        results = await asyncio.gather(*tasks)
        merged = []
        if results:
            max_len = max(len(r) for r in results)
            for i in range(max_len):
                for r in results:
                    if i < len(r): merged.append(r[i])
        return merged

    async def search_images_bing(self, keyword):
        url = f"https://www.bing.com/images/search?q={keyword}&form=HDRSC2&first=1"
        async with httpx.AsyncClient(verify=False, follow_redirects=True) as client:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Referer": "https://www.bing.com/"
                }
                resp = await client.get(url, headers=headers, timeout=8)
                soup = BeautifulSoup(resp.text, 'html.parser')

                results = []
                iusc_links = soup.select('a.iusc')
                for link in iusc_links:
                    try:
                        m_str = link.get('m')
                        if m_str:
                            m_data = json.loads(m_str)
                            img_url = m_data.get('turl') or m_data.get('murl')
                            full_url = m_data.get('murl')
                            if img_url:
                                results.append({"url": full_url, "thumb": img_url})
                    except:
                        continue

                if not results:
                    imgs = soup.select('img.mimg')
                    for img in imgs:
                        src = img.get('src') or img.get('data-src')
                        if src and src.startswith('http'):
                            results.append({"url": src, "thumb": src})

                random.shuffle(results)
                return results[:24]
            except Exception as e:
                print(f"搜图出错: {e}")
                return []

    async def search_social_users(self, keyword, platform="all"):
        results = []

        async def fetch_bili(client):
            try:
                bili_url = f"https://api.bilibili.com/x/web-interface/search/type?search_type=bili_user&keyword={urllib.parse.quote(keyword)}"
                headers = self.helper.get_headers("bilibili")
                if "Cookie" not in headers: headers["Cookie"] = "buvid3=infoc;"
                resp = await client.get(bili_url, headers=headers)
                data = resp.json()
                local_res = []
                if data.get('code') == 0 and data.get('data') and data['data'].get('result'):
                    for user in data['data']['result'][:4]:
                        local_res.append({
                            "platform": "Bilibili",
                            "name": user['uname'],
                            "desc": f"粉丝: {user.get('fans', 0)} | {user.get('usign', '')[:20]}...",
                            "pic": user['upic'].replace("http://", "https://"),
                            "url": f"https://space.bilibili.com/{user['mid']}"
                        })
                return local_res
            except:
                return []

        async def fetch_weibo(client):
            try:
                encoded_q = urllib.parse.quote(keyword)
                weibo_url = f"https://m.weibo.cn/api/container/getIndex?containerid=100103type%3D3%26q%3D{encoded_q}&page_type=searchall"
                headers = {
                    "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
                    "Referer": "https://m.weibo.cn/"
                }
                resp = await client.get(weibo_url, headers=headers)
                data = resp.json()
                local_res = []
                cards = data.get('data', {}).get('cards', [])
                count = 0
                for card in cards:
                    if count >= 3: break
                    if 'card_group' in card:
                        for item in card['card_group']:
                            if item.get('card_type') == 11 and 'user' in item:
                                u = item['user']
                                local_res.append({
                                    "platform": "微博",
                                    "name": u.get('screen_name'),
                                    "desc": f"粉丝: {u.get('followers_count', 0)} | {u.get('description', '')[:20]}",
                                    "pic": u.get('profile_image_url', ''),
                                    "url": f"https://m.weibo.cn/u/{u.get('id')}"
                                })
                                count += 1
                return local_res
            except:
                return []

        async with httpx.AsyncClient(verify=False, timeout=4.0) as client:
            tasks = []
            if platform in ["all", "bilibili"]:
                tasks.append(fetch_bili(client))
            if platform in ["all", "weibo"]:
                tasks.append(fetch_weibo(client))

            if tasks:
                task_results = await asyncio.gather(*tasks, return_exceptions=True)
                for tr in task_results:
                    if isinstance(tr, list):
                        results.extend(tr)

            if platform in ["all", "douyin"]:
                results.append({
                    "platform": "抖音",
                    "name": f"搜索: {keyword}",
                    "desc": "点击直接跳转抖音网页版搜索",
                    "pic": "https://lf1-cdn-tos.bytegoofy.com/goofy/ies/douyin_web/public/favicon.ico",
                    "url": f"https://www.douyin.com/search/{urllib.parse.quote(keyword)}"
                })

            if platform in ["all", "xiaohongshu"]:
                results.append({
                    "platform": "小红书",
                    "name": f"搜索: {keyword}",
                    "desc": "点击直接跳转小红书搜索页",
                    "pic": "https://ci.xiaohongshu.com/fd579468-69cb-4190-8457-377eb60c1d68",
                    "url": f"https://www.xiaohongshu.com/search_result?keyword={urllib.parse.quote(keyword)}"
                })

        return results