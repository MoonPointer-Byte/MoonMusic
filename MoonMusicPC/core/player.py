import asyncio
import os
import time
import uuid
import pygame
import flet as ft
from mutagen.mp3 import MP3


class PlayerManager:
    def __init__(self):
        self.is_playing = False
        self.paused = False
        self.duration = 0
        self.playlist = []
        self.current_index = -1
        self.auto_play = False
        self.on_auto_play_callback = None
        self.page = None

        # UI 组件引用
        self.mini_slider = None
        self.full_slider = None
        self.mini_time = None
        self.full_time = None

        self.monitor_task = None
        self.is_dragging = False
        self.start_time_offset = 0
        self.current_play_token = None
        self.play_start_time = 0

    def register_ui(self, page, mini_slider, full_slider, mini_time, full_time):
        self.page = page
        self.mini_slider = mini_slider
        self.full_slider = full_slider
        self.mini_time = mini_time
        self.full_time = full_time

    def set_callback(self, callback):
        self.on_auto_play_callback = callback

    def set_playlist(self, songs, start_index):
        self.playlist = songs
        self.current_index = start_index

    def get_current_song(self):
        if 0 <= self.current_index < len(self.playlist):
            return self.playlist[self.current_index]
        return None

    def get_next_song(self):
        if not self.playlist: return None
        next_idx = (self.current_index + 1) % len(self.playlist)
        return self.playlist[next_idx]

    def move_next(self):
        if not self.playlist: return None
        self.current_index = (self.current_index + 1) % len(self.playlist)
        return self.playlist[self.current_index]

    def move_prev(self):
        if not self.playlist: return None
        self.current_index = (self.current_index - 1 + len(self.playlist)) % len(self.playlist)
        return self.playlist[self.current_index]

    def load_and_play(self, filepath, duration=180):
        new_token = str(uuid.uuid4())
        self.current_play_token = new_token

        if self.monitor_task: self.monitor_task.cancel()
        if not os.path.exists(filepath): return False

        try:
            try:
                audio = MP3(filepath)
                self.duration = audio.info.length
            except:
                self.duration = duration
        except:
            self.duration = duration

        for slider in [self.mini_slider, self.full_slider]:
            if slider:
                slider.max = self.duration
                slider.value = 0
                slider.disabled = False

        try:
            if pygame.mixer.music.get_busy(): pygame.mixer.music.stop()
            pygame.mixer.music.load(filepath)
            pygame.mixer.music.play()

            self.is_playing = True
            self.paused = False
            self.start_time_offset = 0
            self.play_start_time = time.time()

            self.monitor_task = asyncio.create_task(self._progress_loop(new_token))
            return True
        except Exception as e:
            print(f"底层播放异常: {e}")
            self.is_playing = False
            return False

    async def _progress_loop(self, my_token):
        is_started = False
        for _ in range(20):
            if self.current_play_token != my_token: return
            if pygame.mixer.music.get_busy():
                is_started = True
                break
            await asyncio.sleep(0.1)

        if not is_started:
            if self.current_play_token == my_token:
                self.is_playing = False
                if self.auto_play and self.on_auto_play_callback:
                    await asyncio.sleep(3)
                    if self.current_play_token == my_token:
                        await self.on_auto_play_callback()
            return

        while self.is_playing:
            if self.current_play_token != my_token: return
            if self.paused:
                await asyncio.sleep(0.5)
                continue

            if not pygame.mixer.music.get_busy() and not self.is_dragging:
                await asyncio.sleep(0.5)
                if not pygame.mixer.music.get_busy():
                    if self.current_play_token != my_token: return
                    self.is_playing = False
                    played_time = time.time() - self.play_start_time

                    if self.auto_play and self.on_auto_play_callback:
                        if played_time < 5.0: await asyncio.sleep(3.0)
                        if self.current_play_token == my_token:
                            await self.on_auto_play_callback()
                    break

            if not self.is_dragging and pygame.mixer.music.get_busy():
                try:
                    current_pos_ms = pygame.mixer.music.get_pos()
                    if current_pos_ms != -1:
                        current_seconds = (current_pos_ms / 1000) + self.start_time_offset
                        if current_seconds > self.duration: current_seconds = self.duration
                        time_str = self._fmt_time(current_seconds)
                        if self.mini_slider: self.mini_slider.value = current_seconds
                        if self.full_slider: self.full_slider.value = current_seconds
                        if self.mini_time: self.mini_time.value = time_str
                        if self.full_time: self.full_time.value = time_str
                        try:
                            self.page.update()
                        except:
                            pass
                except:
                    break
            await asyncio.sleep(0.5)

    def _fmt_time(self, seconds):
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        total_mins = int(self.duration // 60)
        total_secs = int(self.duration % 60)
        return f"{mins:02}:{secs:02} / {total_mins:02}:{total_secs:02}"

    def seek(self, seconds):
        try:
            pygame.mixer.music.play(start=seconds)
            self.start_time_offset = seconds
            self.paused = False
        except:
            pass

    def pause_resume(self, icon_controls):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.pause()
            self.paused = True
            for icon in icon_controls: icon.icon = ft.Icons.PLAY_CIRCLE_FILLED
        else:
            pygame.mixer.music.unpause()
            self.paused = False
            self.is_playing = True
            for icon in icon_controls: icon.icon = ft.Icons.PAUSE_CIRCLE_FILLED
            if self.monitor_task is None or self.monitor_task.done():
                self.monitor_task = asyncio.create_task(self._progress_loop(self.current_play_token))
        self.page.update()

    def stop(self):
        self.current_play_token = None
        try:
            pygame.mixer.music.stop()
        except:
            pass
        self.is_playing = False
        self.paused = False