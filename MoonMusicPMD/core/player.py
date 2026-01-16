import flet as ft
import asyncio


class PlayerManager:
    def __init__(self):
        self.page = None
        # 初始化 Audio 组件
        self.audio = ft.Audio(
            autoplay=False,
            volume=1.0,
            on_position_changed=self._on_position_changed,
            on_duration_changed=self._on_duration_changed,
            on_state_changed=self._on_state_changed,
            on_seek_complete=lambda _: setattr(self, 'is_dragging', False)
        )

        self.playlist = []
        self.current_index = -1
        self.auto_play = False
        self.on_auto_play_callback = None

        # UI 组件引用
        self.mini_slider = None
        self.full_slider = None
        self.mini_time = None
        self.full_time = None
        self.play_icons = []  # 存储播放按钮引用以便切换图标

        self.duration = 0
        self.is_dragging = False
        self.is_playing = False  # 逻辑状态

    def register_ui(self, page, mini_slider, full_slider, mini_time, full_time, play_icons):
        self.page = page
        self.mini_slider = mini_slider
        self.full_slider = full_slider
        self.mini_time = mini_time
        self.full_time = full_time
        self.play_icons = play_icons

        # 关键：必须将 audio 组件加入 overlay 才能工作
        self.page.overlay.append(self.audio)
        self.page.update()

    def set_callback(self, callback):
        self.on_auto_play_callback = callback

    # --- 播放逻辑 ---
    def set_playlist(self, songs, start_index):
        self.playlist = songs
        self.current_index = start_index

    def get_current_song(self):
        if 0 <= self.current_index < len(self.playlist):
            return self.playlist[self.current_index]
        return None

    def get_next_song(self):
        if not self.playlist: return None
        return self.playlist[(self.current_index + 1) % len(self.playlist)]

    def move_next(self):
        if not self.playlist: return None
        self.current_index = (self.current_index + 1) % len(self.playlist)
        return self.playlist[self.current_index]

    def move_prev(self):
        if not self.playlist: return None
        self.current_index = (self.current_index - 1 + len(self.playlist)) % len(self.playlist)
        return self.playlist[self.current_index]

    def load_and_play(self, filepath_or_url):
        # flet.Audio 可直接播放 URL 或 本地路径
        self.audio.src = filepath_or_url
        self.audio.update()
        self.audio.play()
        self.is_playing = True
        self._update_icons(True)

        if self.mini_slider: self.mini_slider.disabled = False
        if self.full_slider: self.full_slider.disabled = False
        return True

    def pause_resume(self):
        if self.is_playing:
            self.audio.pause()
            self.is_playing = False
            self._update_icons(False)
        else:
            self.audio.resume()
            self.is_playing = True
            self._update_icons(True)
        self.audio.update()

    def stop(self):
        self.audio.pause()
        self.audio.seek(0)
        self.is_playing = False
        self._update_icons(False)
        self.audio.update()

    def seek(self, seconds):
        # flet seek 单位是毫秒
        self.audio.seek(int(seconds * 1000))
        self.audio.update()

    # --- 事件处理 ---
    def _on_duration_changed(self, e):
        self.duration = float(e.data) / 1000
        if self.mini_slider: self.mini_slider.max = self.duration
        if self.full_slider: self.full_slider.max = self.duration

    def _on_position_changed(self, e):
        if self.is_dragging: return
        curr = float(e.data) / 1000

        if self.mini_slider: self.mini_slider.value = curr
        if self.full_slider: self.full_slider.value = curr

        time_str = self._fmt_time(curr)
        if self.mini_time: self.mini_time.value = time_str
        if self.full_time: self.full_time.value = time_str

        try:
            self.page.update()
        except:
            pass

    def _on_state_changed(self, e):
        # e.data: "playing", "paused", "completed"
        state = e.data
        if state == "completed":
            self.is_playing = False
            self._update_icons(False)
            if self.auto_play and self.on_auto_play_callback:
                asyncio.create_task(self.on_auto_play_callback())

    def _update_icons(self, is_playing):
        icon = ft.Icons.PAUSE_CIRCLE_FILLED if is_playing else ft.Icons.PLAY_CIRCLE_FILLED
        for btn in self.play_icons:
            btn.icon = icon
        try:
            self.page.update()
        except:
            pass

    def _fmt_time(self, seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        total_mins = int(self.duration // 60)
        total_secs = int(self.duration % 60)
        return f"{mins:02}:{secs:02} / {total_mins:02}:{total_secs:02}"