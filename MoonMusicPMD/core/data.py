import json
import os
import re
import httpx


class DataHelper:
    def __init__(self):
        # 移动端建议使用简单的相对路径，Flet 会自动映射到应用沙盒
        self.config_file = "config.json"
        self.data_file = "userdata.json"
        self.base_headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        }
        self.cookies = {
            "netease": "",
            "qq": "",
            "kugou": ""
        }
        self.qq_uin = "0"
        self.favorites = []
        self.history = []

        self.load_config()
        self.load_userdata()

    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.cookies.update(data.get("cookies", {}))
                    self.qq_uin = data.get("qq_uin", "0")
            except:
                pass

    def save_config(self):
        data = {"cookies": self.cookies, "qq_uin": self.qq_uin}
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except:
            pass

    def load_userdata(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.favorites = data.get("favorites", [])
                    self.history = data.get("history", [])
            except:
                pass

    def save_userdata(self):
        data = {"favorites": self.favorites, "history": self.history}
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except:
            pass

    def toggle_favorite(self, song):
        found = False
        for i, s in enumerate(self.favorites):
            if s['id'] == song['id']:
                self.favorites.pop(i)
                found = True
                break
        if not found:
            self.favorites.insert(0, song)
        self.save_userdata()
        return not found

    def is_favorite(self, song):
        if not song: return False
        for s in self.favorites:
            if s['id'] == song['id']:
                return True
        return False

    def add_history(self, song):
        for i, s in enumerate(self.history):
            if s['id'] == song['id']:
                self.history.pop(i)
                break
        self.history.insert(0, song)
        if len(self.history) > 50:
            self.history.pop()
        self.save_userdata()

    def set_cookie(self, platform, cookie_str):
        if cookie_str:
            self.cookies[platform] = cookie_str.strip()
            self.save_config()

    def set_qq_uin(self, uin):
        if uin:
            clean_uin = uin.strip().lstrip('o')
            if clean_uin.isdigit():
                self.qq_uin = clean_uin
                self.save_config()

    def get_headers(self, platform):
        headers = self.base_headers.copy()
        if platform == "netease":
            headers["Referer"] = "https://music.163.com/"
            if self.cookies["netease"]: headers["Cookie"] = self.cookies["netease"]
        elif platform == "qq":
            headers["Referer"] = "https://y.qq.com/"
            if self.cookies["qq"]: headers["Cookie"] = self.cookies["qq"]
        elif platform == "kugou":
            headers["Referer"] = "https://www.kugou.com/"
            if self.cookies["kugou"]: headers["Cookie"] = self.cookies["kugou"]
        elif platform == "bilibili":
            headers["Referer"] = "https://www.bilibili.com/"
        return headers

    async def download_file(self, url, folder, filename):
        # 确保文件夹存在
        if not os.path.exists(folder): os.makedirs(folder)

        safe_name = re.sub(r'[\\/*?:"<>|]', "", filename).strip()
        filepath = os.path.join(folder, safe_name)

        if os.path.exists(filepath) and os.path.getsize(filepath) > 100 * 1024:
            return True, filepath

        async with httpx.AsyncClient(follow_redirects=True, verify=False) as client:
            try:
                headers = self.base_headers.copy()
                async with client.stream('GET', url, headers=headers) as resp:
                    if resp.status_code != 200: return False, f"HTTP {resp.status_code}"
                    with open(filepath, 'wb') as f:
                        async for chunk in resp.aiter_bytes():
                            f.write(chunk)
                # 简单校验
                if os.path.getsize(filepath) < 10 * 1024:
                    try:
                        os.remove(filepath)
                    except:
                        pass
                    return False, "文件过小"
                return True, filepath
            except Exception as e:
                return False, str(e)