import flet as ft
import asyncio
import time
import random

# 引入模块化层
from core.data import DataHelper
from core.player import PlayerManager
from services.crawler import CrawlerService


def main(page: ft.Page):
    # 移动端设置
    page.title = "MoonMusic"
    page.theme_mode = "dark"
    page.padding = 0
    page.bgcolor = "#121212"
    # 适配手机安全区域（刘海/灵动岛）
    page.scroll = ft.ScrollMode.HIDDEN

    # 初始化
    helper = DataHelper()
    crawler = CrawlerService(helper)
    player = PlayerManager()

    # 常量
    COLOR_CARD = "#252525"
    COLOR_PRIMARY = "#3D5AFE"
    COLOR_ACCENT = "#00E676"

    def show_snack(msg, color=COLOR_PRIMARY):
        page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
        page.snack_bar.open = True
        page.update()

    # --- UI 组件 ---
    # 定义滑块
    mini_slider = ft.Slider(min=0, max=100, value=0, height=10, active_color=COLOR_ACCENT, disabled=True,
                            on_change_start=lambda e: setattr(player, 'is_dragging', True),
                            on_change_end=lambda e: (
                            setattr(player, 'is_dragging', False), player.seek(e.control.value)))
    full_slider = ft.Slider(min=0, max=100, value=0, height=30, active_color=COLOR_ACCENT, thumb_color="white",
                            on_change_start=lambda e: setattr(player, 'is_dragging', True),
                            on_change_end=lambda e: (
                            setattr(player, 'is_dragging', False), player.seek(e.control.value)))

    mini_time_label = ft.Text("00:00 / 00:00", size=10, color="grey")
    full_time_label = ft.Text("00:00 / 00:00", color="white54")

    # 播放按钮 (需要控制图标切换)
    full_play_btn = ft.IconButton(ft.Icons.PLAY_CIRCLE_FILLED, icon_color="white", icon_size=70,
                                  on_click=lambda e: player.pause_resume())
    # 迷你播放器的播放按钮（可选，这里我添加一个用于同步）
    # 如果你想在迷你播放器加暂停按钮，可以在这里定义

    mini_song_label = ft.Text("等待播放", size=12, weight="bold", no_wrap=True)
    full_song_label = ft.Text("暂无音乐", size=24, weight="bold", text_align="center", max_lines=1,
                              overflow=ft.TextOverflow.ELLIPSIS)
    full_artist_label = ft.Text("未知歌手", size=16, color="grey", text_align="center")
    full_cover_img = ft.Image(src="assets/logo.png", width=300, height=300, border_radius=20, fit="cover")

    fav_icon_btn = ft.IconButton(ft.Icons.FAVORITE_BORDER, icon_color="white", icon_size=30)

    # 注册组件到 Player
    # 注意：full_play_btn 放在列表中传进去，以便 Player 更新图标
    player.register_ui(page, mini_slider, full_slider, mini_time_label, full_time_label, [full_play_btn])

    # --- 核心播放逻辑 ---
    async def play_index_handler(index_change=0):
        target_song = None
        if index_change == 0:
            target_song = player.get_current_song()
        elif index_change == 1:
            target_song = player.move_next()
        elif index_change == -1:
            target_song = player.move_prev()

        if not target_song: return
        helper.add_history(target_song)

        # UI 更新
        mini_player_container.visible = True
        mini_song_label.value = f"{target_song['name']} [{target_song['source']}]"
        full_song_label.value = "缓冲中..."
        full_artist_label.value = target_song['artist']
        if target_song['pic']: full_cover_img.src = target_song['pic']

        is_fav = helper.is_favorite(target_song)
        fav_icon_btn.icon = ft.Icons.FAVORITE if is_fav else ft.Icons.FAVORITE_BORDER
        fav_icon_btn.icon_color = "red" if is_fav else "white"

        player.stop()
        mini_slider.disabled = True
        full_slider.disabled = True
        page.update()

        # 获取链接
        play_url = target_song['url']
        if target_song['source'] == "QQ" and not play_url:
            play_url = await crawler.get_qq_purl(target_song['id'], target_song.get('media_id'))

        if not play_url:
            show_snack("资源失效", "#FF5252")
            if player.auto_play and index_change == 1:
                await asyncio.sleep(2)
                await play_index_handler(1)
            return

        # 移动端直接播 URL（或者下载后播本地）
        # 这里为了流畅度，先尝试直接播URL，同时触发下载缓存
        # ft.Audio 支持直接播 URL
        full_song_label.value = target_song['name']
        player.load_and_play(play_url)

        # 后台下载缓存（可选，视需求而定）
        # ext = "m4a" if "m4a" in play_url else "mp3"
        # asyncio.create_task(helper.download_file(play_url, "cache", f"{target_song['id']}.{ext}"))

    player.set_callback(lambda: asyncio.create_task(play_index_handler(1)))

    async def download_current_handler(e):
        s = player.get_current_song()
        if not s: return show_snack("无歌曲")
        url = s['url']
        if not url and s['source'] == "QQ": url = await crawler.get_qq_purl(s['id'], s.get('media_id'))
        if url:
            ext = "m4a" if "m4a" in url else "mp3"
            # 移动端保存到应用私有目录
            ok, path = await helper.download_file(url, "downloads", f"{s['name']}.{ext}")
            show_snack(f"保存至: {path}" if ok else "下载失败")

    # --- 布局 ---
    def open_full_player(e):
        full_player_layer.visible = True
        full_player_layer.offset = ft.Offset(0, 0)
        full_player_layer.opacity = 1
        page.update()

    def close_full_player(e):
        full_player_layer.offset = ft.Offset(0, 1)
        full_player_layer.opacity = 0
        full_player_layer.visible = False
        page.update()

    # 迷你播放器条
    mini_player_container = ft.Container(
        content=ft.Column([
            mini_slider,
            ft.Row([
                ft.Row([ft.Icon(ft.Icons.MUSIC_NOTE, color=COLOR_PRIMARY, size=16),
                        ft.Container(content=mini_song_label, width=200)], spacing=10),
                ft.Row([mini_time_label,
                        ft.IconButton(ft.Icons.KEYBOARD_ARROW_UP, icon_color="grey", on_click=open_full_player)],
                       spacing=0)
            ], alignment="spaceBetween")
        ], spacing=5),
        bgcolor="#1E1E1E", padding=ft.padding.symmetric(horizontal=15, vertical=8),
        border_radius=ft.BorderRadius(15, 15, 0, 0), visible=False, on_click=open_full_player, ink=True
    )

    auto_play_icon = ft.IconButton(ft.Icons.AUTORENEW, icon_color="white54")

    def toggle_auto(e):
        player.auto_play = not player.auto_play
        auto_play_icon.icon_color = COLOR_ACCENT if player.auto_play else "white54"
        show_snack(f"自动播放: {player.auto_play}")
        page.update()

    auto_play_icon.on_click = toggle_auto

    def toggle_fav(e):
        s = player.get_current_song()
        if s:
            is_fav = helper.toggle_favorite(s)
            fav_icon_btn.icon = ft.Icons.FAVORITE if is_fav else ft.Icons.FAVORITE_BORDER
            fav_icon_btn.icon_color = "red" if is_fav else "white"
            page.update()

    fav_icon_btn.on_click = toggle_fav

    # 播放列表抽屉
    playlist_content = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)
    playlist_layer = ft.Container(
        content=ft.Column([
            ft.Container(content=ft.Row([ft.Text("播放列表", size=18, weight="bold"),
                                         ft.IconButton(ft.Icons.KEYBOARD_ARROW_DOWN, on_click=lambda e: (
                                         setattr(playlist_layer, 'offset', ft.Offset(0, 1)), page.update()))],
                                        alignment="spaceBetween"), padding=10),
            ft.Divider(height=1), playlist_content
        ]),
        bgcolor="#1E1E1E", height=500, border_radius=ft.BorderRadius(20, 20, 0, 0),
        bottom=0, left=0, right=0, offset=ft.Offset(0, 1), animate_offset=300, visible=True,
        shadow=ft.BoxShadow(blur_radius=50)
    )

    def open_playlist(e):
        playlist_content.controls.clear()
        if not player.playlist: playlist_content.controls.append(ft.Text("空列表", padding=20))
        for i, s in enumerate(player.playlist):
            color = COLOR_ACCENT if i == player.current_index else "white"

            def play_me(idx): return lambda e: (
            setattr(playlist_layer, 'offset', ft.Offset(0, 1)), player.set_playlist(player.playlist, idx),
            asyncio.create_task(play_index_handler(0)))

            playlist_content.controls.append(ft.Container(
                content=ft.Row([ft.Text(f"{i + 1}. {s['name']}", color=color, no_wrap=True, width=250),
                                ft.Text(s['artist'], size=12, color="grey")]),
                padding=10, on_click=play_me(i), ink=True
            ))
        playlist_layer.visible = True
        playlist_layer.offset = ft.Offset(0, 0)
        page.update()

    # 全屏层
    full_player_layer = ft.Container(
        content=ft.Column([
            ft.Container(content=ft.Row(
                [ft.IconButton(ft.Icons.KEYBOARD_ARROW_DOWN, icon_color="white", on_click=close_full_player),
                 fav_icon_btn], alignment="spaceBetween"), padding=ft.padding.only(top=20, left=10, right=10)),
            ft.Container(content=full_cover_img, alignment=ft.Alignment(0, 0), expand=True, padding=20),
            ft.Container(content=ft.Column([
                ft.Text("正在播放", size=12, color="grey", text_align="center"),
                full_song_label, full_artist_label,
                ft.Container(height=20),
                full_slider, ft.Row([full_time_label], alignment="center"),
                ft.Container(height=20),
                ft.Row([
                    ft.IconButton(ft.Icons.SKIP_PREVIOUS, icon_size=40, icon_color="white",
                                  on_click=lambda e: asyncio.create_task(play_index_handler(-1))),
                    full_play_btn,
                    ft.IconButton(ft.Icons.SKIP_NEXT, icon_size=40, icon_color="white",
                                  on_click=lambda e: asyncio.create_task(play_index_handler(1)))
                ], alignment="center", spacing=30),
                ft.Row([auto_play_icon, ft.IconButton(ft.Icons.DOWNLOAD, icon_color="white",
                                                      on_click=lambda e: asyncio.create_task(
                                                          download_current_handler(e))),
                        ft.IconButton(ft.Icons.QUEUE_MUSIC, icon_color="white", on_click=open_playlist)],
                       alignment="spaceEvenly", spacing=20)
            ]), padding=20)
        ]),
        bgcolor="#121212",
        gradient=ft.LinearGradient(colors=["#2c3e50", "#000000"], begin=ft.Alignment(0, -1), end=ft.Alignment(0, 1)),
        expand=True, offset=ft.Offset(0, 1), animate_offset=300, visible=False, top=0, left=0, right=0, bottom=0
    )

    # --- 页面内容 ---
    music_input = ft.TextField(hint_text="搜全网...", expand=True, border_radius=15, bgcolor=COLOR_CARD,
                               border_color="transparent", on_submit=lambda e: asyncio.create_task(search_m()))
    music_dd = ft.Dropdown(options=[ft.dropdown.Option("all", "全部"), ft.dropdown.Option("netease", "网易"),
                                    ft.dropdown.Option("qq", "QQ")], value="all", width=80, border_radius=15,
                           bgcolor=COLOR_CARD, border_color="transparent")
    music_list = ft.ListView(expand=True, spacing=5, padding=10)

    async def search_m():
        if not music_input.value: return
        music_list.controls = [ft.ProgressBar()];
        page.update()
        songs = await crawler.search_all(music_input.value, music_dd.value)
        music_list.controls.clear()
        for i, s in enumerate(songs):
            def play_it(idx=i, sl=songs): return lambda e: (
            player.set_playlist(sl, idx), asyncio.create_task(play_index_handler(0)))

            music_list.controls.append(ft.Container(
                content=ft.Row([
                    ft.Image(src=s['pic'], width=40, height=40, border_radius=5),
                    ft.Column([ft.Text(s['name'], weight="bold"),
                               ft.Text(f"{s['artist']} ({s['source']})", size=12, color="grey")], spacing=2,
                              expand=True),
                    ft.IconButton(ft.Icons.PLAY_ARROW, on_click=play_it())
                ]), padding=5, bgcolor=COLOR_CARD, border_radius=10
            ))
        page.update()

    # 构建主视图 (使用 SafeArea 适配刘海屏)
    music_view = ft.Column([
        ft.Container(content=ft.Row([music_input, music_dd]), padding=10),
        music_list,
        mini_player_container
    ], expand=True)

    # 简单的 Tab 切换
    t_tabs = ft.Tabs(
        selected_index=0,
        tabs=[ft.Tab(text="音乐", icon=ft.Icons.MUSIC_NOTE), ft.Tab(text="搜图", icon=ft.Icons.IMAGE)],
        on_change=lambda e: setattr(main_content, 'content',
                                    music_view if e.control.selected_index == 0 else ft.Text("搜图页面 (待开发)",
                                                                                             color="white")) or page.update()
    )

    main_content = ft.Container(content=music_view, expand=True)

    # 根布局
    page.add(
        ft.SafeArea(
            ft.Stack([
                ft.Column([
                    ft.Container(content=ft.Text("MoonMusic", size=20, weight="bold"), padding=10),
                    main_content,
                    t_tabs
                ], expand=True),
                full_player_layer,
                playlist_layer
            ], expand=True)
        )
    )


if __name__ == "__main__":
    ft.run(main)