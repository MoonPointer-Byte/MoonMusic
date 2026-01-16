import warnings

# 屏蔽干扰性警告
warnings.filterwarnings("ignore", category=UserWarning, module="pygame")
warnings.filterwarnings("ignore", category=DeprecationWarning)

import flet as ft
import asyncio
import time
import random

# 引入模块化层
from core.data import DataHelper
from core.player import PlayerManager
from services.crawler import CrawlerService


def main(page: ft.Page):
    page.title = "MoonMusicPC"
    page.theme_mode = "dark"
    page.window_width = 460
    page.window_height = 850
    page.padding = 0
    page.bgcolor = "#121212"
    page.window_icon = "logo.png"

    # 初始化核心层
    helper = DataHelper()
    crawler = CrawlerService(helper)
    player = PlayerManager()

    # 常量定义
    COLOR_CARD = "#252525"
    COLOR_PRIMARY = "#3D5AFE"
    COLOR_ACCENT = "#00E676"

    def show_snack(msg, color=COLOR_PRIMARY):
        page.snack_bar = ft.SnackBar(ft.Text(msg), bgcolor=color)
        page.snack_bar.open = True
        page.update()

    # --- UI 组件定义 ---
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
    full_play_btn = ft.IconButton(ft.Icons.PAUSE_CIRCLE_FILLED, icon_color="white", icon_size=70,
                                  on_click=lambda e: player.pause_resume([full_play_btn]))
    mini_song_label = ft.Text("等待播放", size=12, weight="bold", no_wrap=True)
    full_song_label = ft.Text("暂无音乐", size=24, weight="bold", text_align="center", max_lines=1,
                              overflow=ft.TextOverflow.ELLIPSIS)
    full_artist_label = ft.Text("未知歌手", size=16, color="grey", text_align="center")
    full_cover_img = ft.Image(src="", width=300, height=300, border_radius=20, fit="cover")

    fav_icon_btn = ft.IconButton(ft.Icons.FAVORITE_BORDER, icon_color="white", icon_size=30)

    # 注册UI到播放器
    player.register_ui(page, mini_slider, full_slider, mini_time_label, full_time_label)

    # === 播放与逻辑 ===
    async def preload_next_song():
        next_s = player.get_next_song()
        if not next_s: return
        url = next_s['url']
        if next_s['source'] == "QQ" and not url:
            url = await crawler.get_qq_purl(next_s['id'], next_s.get('media_id'))
        if url:
            ext = "m4a" if "m4a" in url or "qqmusic" in url else "mp3"
            await helper.download_file(url, "temp_cache", f"cache_{next_s['id']}.{ext}")

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

        mini_player_container.visible = True
        mini_song_label.value = f"{target_song['name']} [{target_song['source']}]"
        full_song_label.value = "缓冲中..."
        full_artist_label.value = target_song['artist']
        if target_song['pic']: full_cover_img.src = target_song['pic']

        is_fav = helper.is_favorite(target_song)
        fav_icon_btn.icon = ft.Icons.FAVORITE if is_fav else ft.Icons.FAVORITE_BORDER
        fav_icon_btn.icon_color = "red" if is_fav else "white"

        player.stop()
        full_play_btn.icon = ft.Icons.PAUSE_CIRCLE_FILLED
        mini_slider.disabled = True
        full_slider.disabled = True
        page.update()

        play_url = target_song['url']
        if target_song['source'] == "QQ" and not play_url:
            play_url = await crawler.get_qq_purl(target_song['id'], target_song.get('media_id'))
            if not play_url:
                show_snack("资源获取失败", "#FF5252")
                if player.auto_play and index_change == 1:
                    await asyncio.sleep(2)
                    await play_index_handler(1)
                return

        ext = "m4a" if "m4a" in play_url or "qqmusic" in play_url else "mp3"
        ok, path = await helper.download_file(play_url, "temp_cache", f"cache_{target_song['id']}.{ext}")

        if ok:
            full_song_label.value = target_song['name']
            success = player.load_and_play(path)
            if success:
                asyncio.create_task(preload_next_song())
            else:
                show_snack("文件损坏", "#FF5252")
                if player.auto_play and index_change == 1:
                    await asyncio.sleep(2)
                    await play_index_handler(1)
        else:
            show_snack("下载失败", "#FF5252")
            if player.auto_play and index_change == 1:
                await asyncio.sleep(2)
                await play_index_handler(1)

    player.set_callback(lambda: asyncio.create_task(play_index_handler(1)))

    async def download_item(s):
        url = s['url']
        if s['source'] == "QQ" and not url:
            url = await crawler.get_qq_purl(s['id'], s.get('media_id'))
        if url:
            ext = "m4a" if "m4a" in url else "mp3"
            await helper.download_file(url, "downloads", f"{s['name']}.{ext}")
            show_snack(f"已下载: {s['name']}")
        else:
            show_snack("无法下载", "#FF5252")

    async def download_current_handler(e):
        s = player.get_current_song()
        if s:
            await download_item(s)
        else:
            show_snack("当前没有播放歌曲")

    # --- 布局组件定义 ---
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

    mini_player_container = ft.Container(
        content=ft.Column([
            mini_slider,
            ft.Row([
                ft.Row([ft.Icon(ft.Icons.MUSIC_NOTE, color=COLOR_PRIMARY, size=16),
                        ft.Container(content=mini_song_label, width=220)], spacing=10),
                ft.Row([mini_time_label,
                        ft.IconButton(ft.Icons.KEYBOARD_ARROW_UP, icon_color="grey", on_click=open_full_player)],
                       spacing=0)
            ], alignment="spaceBetween")
        ], spacing=5),
        bgcolor="#1E1E1E", padding=ft.padding.symmetric(horizontal=15, vertical=8),
        border_radius=ft.BorderRadius(15, 15, 0, 0), visible=False, on_click=open_full_player, ink=True
    )

    auto_play_icon = ft.IconButton(ft.Icons.AUTORENEW, icon_color="white54", tooltip="自动播放: 关")
    auto_play_icon.on_click = lambda e: (
        setattr(player, 'auto_play', not player.auto_play),
        setattr(auto_play_icon, 'icon_color', COLOR_ACCENT if player.auto_play else "white54"),
        show_snack(f"自动播放已{'开启' if player.auto_play else '关闭'}"),
        page.update()
    )

    def toggle_fav(e):
        s = player.get_current_song()
        if s:
            is_added = helper.toggle_favorite(s)
            fav_icon_btn.icon = ft.Icons.FAVORITE if is_added else ft.Icons.FAVORITE_BORDER
            fav_icon_btn.icon_color = "red" if is_added else "white"
            show_snack("已收藏" if is_added else "已取消收藏")
            if not music_input.value: render_music_home()
            page.update()

    fav_icon_btn.on_click = toggle_fav

    # 播放列表
    playlist_content = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    def build_playlist_ui():
        playlist_content.controls.clear()
        current_idx = player.current_index
        if not player.playlist:
            playlist_content.controls.append(
                ft.Container(content=ft.Text("播放列表为空", color="grey"), alignment=ft.Alignment(0, 0), padding=20))
        else:
            for idx, s in enumerate(player.playlist):
                is_playing = (idx == current_idx)

                def make_play_func(i):
                    return lambda e: (
                        setattr(playlist_layer, 'offset', ft.Offset(0, 1)),
                        setattr(playlist_layer, 'visible', False),
                        player.set_playlist(player.playlist, i),
                        asyncio.create_task(play_index_handler(0))
                    )

                item = ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Icon(ft.Icons.GRAPHIC_EQ, color=COLOR_ACCENT,
                                            size=20) if is_playing else ft.Text(str(idx + 1), color="grey", size=14),
                            width=30, alignment=ft.Alignment(0, 0)
                        ),
                        ft.Column([
                            ft.Text(s['name'], color=COLOR_ACCENT if is_playing else "white", weight="bold", size=14,
                                    no_wrap=True),
                            ft.Text(f"{s['artist']} - {s.get('source', '未知')}", size=12, color="grey", no_wrap=True)
                        ], expand=True, spacing=2),
                        ft.IconButton(ft.Icons.CLOSE, icon_color="grey", icon_size=16, tooltip="移除",
                                      on_click=lambda e, i=idx: (player.playlist.pop(i), build_playlist_ui()))
                    ], alignment="spaceBetween"),
                    padding=10, border_radius=10,
                    bgcolor="#33ffffff" if is_playing else "transparent",
                    on_click=make_play_func(idx), ink=True
                )
                playlist_content.controls.append(item)
        page.update()

    playlist_layer = ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.Text("当前播放列表", size=18, weight="bold"),
                    ft.IconButton(ft.Icons.KEYBOARD_ARROW_DOWN, on_click=lambda e: (
                    setattr(playlist_layer, 'offset', ft.Offset(0, 1)), page.update()))
                ], alignment="spaceBetween"),
                padding=ft.padding.only(left=20, right=10, top=10)
            ),
            ft.Divider(color="white10", height=1),
            playlist_content
        ]),
        bgcolor="#1E1E1E", width=460, height=500, border_radius=ft.BorderRadius(20, 20, 0, 0),
        bottom=0, left=0, right=0, offset=ft.Offset(0, 1), animate_offset=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
        visible=True, shadow=ft.BoxShadow(blur_radius=50, color="black"),
    )

    def open_playlist(e):
        build_playlist_ui()
        playlist_layer.visible = True
        playlist_layer.offset = ft.Offset(0, 0)
        page.update()

    # 全屏播放器层
    full_player_layer = ft.Container(
        content=ft.Column([
            ft.Container(content=ft.Row(
                [ft.IconButton(ft.Icons.KEYBOARD_ARROW_DOWN, icon_color="white", on_click=close_full_player),
                 ft.Text("正在播放", size=18, weight="bold"), fav_icon_btn], alignment="spaceBetween"),
                padding=ft.padding.only(top=40, left=20, right=20)),
            ft.Container(
                content=ft.Container(content=full_cover_img, shadow=ft.BoxShadow(blur_radius=40, color="black"),
                                     border_radius=20), alignment=ft.Alignment(0, 0), expand=True),
            ft.Container(content=ft.Column([
                ft.Column([full_song_label, full_artist_label], horizontal_alignment="center", spacing=5),
                ft.Container(height=20),
                ft.Column([full_slider, ft.Row([full_time_label], alignment="center")], spacing=5),
                ft.Container(height=10),
                ft.Row([
                    ft.IconButton(ft.Icons.SKIP_PREVIOUS_ROUNDED, icon_color="white", icon_size=45,
                                  on_click=lambda e: asyncio.create_task(play_index_handler(-1))),
                    full_play_btn,
                    ft.IconButton(ft.Icons.SKIP_NEXT_ROUNDED, icon_color="white", icon_size=45,
                                  on_click=lambda e: asyncio.create_task(play_index_handler(1)))
                ], alignment="center", spacing=40),
                ft.Row([auto_play_icon, ft.IconButton(ft.Icons.DOWNLOAD_ROUNDED, icon_color="white",
                                                      on_click=lambda e: asyncio.create_task(
                                                          download_current_handler(e))),
                        ft.IconButton(ft.Icons.QUEUE_MUSIC, icon_color="white", on_click=open_playlist)],
                       alignment="spaceEvenly")
            ]), padding=ft.padding.only(left=30, right=30, bottom=50))
        ]),
        bgcolor="#121212",
        gradient=ft.LinearGradient(begin=ft.Alignment(0, -1), end=ft.Alignment(0, 1), colors=["#2c3e50", "#000000"]),
        left=0, top=0, right=0, bottom=0, visible=False, offset=ft.Offset(0, 1), animate_offset=300, animate_opacity=300
    )

    # --- 音乐页面 ---
    music_input = ft.TextField(hint_text="全网搜歌...", expand=True, border_radius=15, bgcolor=COLOR_CARD,
                               border_color="transparent")
    music_platform_dd = ft.Dropdown(options=[ft.dropdown.Option("all", "全部"), ft.dropdown.Option("netease", "网易云"),
                                             ft.dropdown.Option("qq", "QQ音乐"), ft.dropdown.Option("kugou", "酷狗")],
                                    value="all", width=100, text_size=12, bgcolor=COLOR_CARD,
                                    border_color="transparent", border_radius=15)
    music_list = ft.ListView(expand=True, spacing=10, padding=20)

    def create_song_list_items(songs):
        items = []
        for idx, s in enumerate(songs):
            def make_play(i): return lambda e: (
                player.set_playlist(songs, i), asyncio.create_task(play_index_handler(0)))

            def make_dl(sd): return lambda e: asyncio.create_task(download_item(sd))

            src_col = {"网易": "#C20C0C", "QQ": "#31c27c", "酷狗": "#0091ff"}.get(s.get('source', ''), "grey")
            items.append(ft.Container(
                content=ft.Row([
                    ft.Image(src=s['pic'], width=50, height=50, border_radius=5, fit="cover"),
                    ft.Column([
                        ft.Row([ft.Text(s['name'], weight="bold", size=14),
                                ft.Container(content=ft.Text(s.get('source', '未知'), size=10, color="white"),
                                             bgcolor=src_col, padding=4, border_radius=4)], spacing=5),
                        ft.Text(s['artist'], size=12, color="grey")
                    ], spacing=2, expand=True),
                    ft.IconButton(ft.Icons.PLAY_CIRCLE_FILL, icon_color=COLOR_ACCENT, on_click=make_play(idx)),
                    ft.IconButton(ft.Icons.DOWNLOAD_ROUNDED, icon_color="white54", on_click=make_dl(s))
                ]), bgcolor=COLOR_CARD, padding=10, border_radius=10
            ))
        return items

    def render_music_home():
        music_list.controls.clear()
        if music_input.value: return

        def load_list_data(data_list, title):
            music_list.controls.clear()
            music_list.controls.append(
                ft.Row([
                    ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: render_music_home()),
                    ft.Text(title, size=20, weight="bold")
                ], spacing=10)
            )
            if not data_list:
                music_list.controls.append(
                    ft.Container(content=ft.Text("暂无记录", color="grey"), alignment=ft.Alignment(0, 0), padding=50))
            else:
                music_list.controls.extend(create_song_list_items(data_list))
            page.update()

        def build_card(icon, title, color_start, color_end, count, click_handler):
            return ft.Container(
                content=ft.Stack([
                    ft.Container(content=ft.Icon(icon, size=80, color="#26ffffff"), right=-20, bottom=-20),
                    ft.Column([
                        ft.Icon(icon, color="white", size=30),
                        ft.Column([ft.Text(title, weight="bold", size=18, color="white"),
                                   ft.Text(f"{count} 首歌曲", size=12, color="white70")], spacing=0)
                    ], alignment="spaceBetween", expand=True)
                ]),
                gradient=ft.LinearGradient(begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1),
                                           colors=[color_start, color_end]),
                padding=20, border_radius=20, on_click=click_handler, ink=True,
                shadow=ft.BoxShadow(blur_radius=15, color="#4d000000", offset=ft.Offset(0, 5)),
                expand=True, height=130
            )

        music_list.controls.append(
            ft.Container(content=ft.Text("我的音乐库", size=26, weight="bold"), padding=ft.padding.only(bottom=5)))
        row = ft.Row([
            build_card(ft.Icons.FAVORITE_ROUNDED, "我的收藏", "#FF512F", "#DD2476", len(helper.favorites),
                       lambda e: load_list_data(helper.favorites, "我的收藏")),
            build_card(ft.Icons.HISTORY_TOGGLE_OFF_ROUNDED, "最近播放", "#4FACFE", "#00F2FE", len(helper.history),
                       lambda e: load_list_data(helper.history, "最近播放"))
        ], alignment="center", spacing=15)
        music_list.controls.append(row)

        if helper.history:
            music_list.controls.append(ft.Container(height=20))
            music_list.controls.append(ft.Text("继续聆听", size=18, weight="bold"))
            music_list.controls.extend(create_song_list_items(helper.history[:3]))
        page.update()

    async def on_search_music(e):
        if not music_input.value:
            render_music_home()
            return
        music_list.controls = [ft.ProgressBar(color=COLOR_PRIMARY)];
        page.update()
        songs = await crawler.search_all(music_input.value, platform=music_platform_dd.value)
        music_list.controls.clear()
        if not songs:
            music_list.controls.append(ft.Text("未找到结果", color="grey"))
        else:
            music_list.controls.extend(create_song_list_items(songs))
        page.update()

    music_input.on_submit = on_search_music
    music_input.on_change = lambda e: render_music_home() if e.control.value == "" else None
    render_music_home()

    music_view = ft.Column(
        [ft.Container(padding=ft.padding.only(left=20, top=30), content=ft.Text("Music", size=28, weight="bold")),
         ft.Container(padding=ft.padding.symmetric(horizontal=20), content=ft.Row([music_input, music_platform_dd])),
         music_list, mini_player_container], expand=True)

    # --- 搜图页面 ---
    img_input = ft.TextField(hint_text="搜图 (如: 4K壁纸)...", expand=True, border_radius=15, bgcolor=COLOR_CARD,
                             border_color="transparent")
    img_body = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=15)

    async def download_img_handler(url):
        show_snack("正在下载...", COLOR_PRIMARY)
        ext = "jpg"
        if ".png" in url:
            ext = "png"
        elif ".gif" in url:
            ext = "gif"
        elif ".webp" in url:
            ext = "webp"
        filename = f"img_{int(time.time())}_{random.randint(1000, 9999)}.{ext}"
        success, result = await helper.download_file(url, "downloads/images", filename)
        if success:
            show_snack(f"下载成功！{result}", COLOR_ACCENT)
        else:
            show_snack(f"下载失败: {result}", "#FF5252")

    async def on_search_img(keyword=None):
        if keyword: img_input.value = keyword
        val = img_input.value
        if not val: render_img_home(); return

        img_body.controls.clear()
        img_body.controls.append(ft.Row([
            ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: (setattr(img_input, 'value', ''), render_img_home())),
            ft.Text(f"搜索: {val}", size=20, weight="bold")
        ], spacing=10))
        img_body.controls.append(ft.ProgressBar(color=COLOR_PRIMARY));
        page.update()

        imgs = await crawler.search_images_bing(val)
        img_body.controls.pop()

        if not imgs:
            img_body.controls.append(
                ft.Container(content=ft.Text("未找到相关图片", color="grey"), alignment=ft.Alignment(0, 0), padding=50))
        else:
            grid = ft.GridView(expand=True, runs_count=2, spacing=10, run_spacing=10, controls=[
                ft.Container(
                    content=ft.Stack([
                        ft.Image(src=i['thumb'], fit="cover", border_radius=10, width=float("inf"),
                                 height=float("inf")),
                        ft.Container(on_click=lambda e, src=i['url']: asyncio.create_task(page.launch_url(src)),
                                     expand=True),
                        ft.Container(
                            content=ft.IconButton(ft.Icons.DOWNLOAD_ROUNDED, icon_color="white", bgcolor="#66000000",
                                                  icon_size=20,
                                                  on_click=lambda e, u=i['url']: asyncio.create_task(
                                                      download_img_handler(u))),
                            bottom=5, right=5, border_radius=50)
                    ]),
                    aspect_ratio=1, border_radius=10, clip_behavior=ft.ClipBehavior.HARD_EDGE
                ) for i in imgs
            ])
            img_body.controls.append(ft.Container(content=grid, height=600, expand=True))
        page.update()

    img_input.on_submit = lambda e: asyncio.create_task(on_search_img())
    img_input.on_change = lambda e: render_img_home() if e.control.value == "" else None

    def render_img_home():
        if img_input.value: return
        img_body.controls.clear()

        def build_big_card(title, subtitle, icon, color1, color2, keyword):
            return ft.Container(
                content=ft.Stack([
                    ft.Container(content=ft.Icon(icon, size=80, color="#26ffffff"), right=-20, bottom=-20),
                    ft.Column([ft.Icon(icon, color="white", size=30),
                               ft.Column([ft.Text(title, weight="bold", size=18, color="white"),
                                          ft.Text(subtitle, size=12, color="white70")], spacing=0)
                               ], alignment="spaceBetween", expand=True)
                ]),
                gradient=ft.LinearGradient(begin=ft.Alignment(-1, -1), end=ft.Alignment(1, 1), colors=[color1, color2]),
                padding=20, border_radius=20, on_click=lambda e: asyncio.create_task(on_search_img(keyword)), ink=True,
                shadow=ft.BoxShadow(blur_radius=15, color="#4d000000", offset=ft.Offset(0, 5)), expand=True, height=130
            )

        def create_gallery_item(title, subtitle, icon, color, keyword):
            return ft.Container(
                content=ft.Row([
                    ft.Container(content=ft.Icon(icon, color="white", size=24), width=50, height=50, border_radius=10,
                                 bgcolor=color, alignment=ft.Alignment(0, 0)),
                    ft.Column([ft.Text(title, weight="bold", size=14), ft.Text(subtitle, size=12, color="grey")],
                              spacing=2, expand=True),
                    ft.IconButton(ft.Icons.ARROW_FORWARD_IOS, icon_size=16, icon_color="grey",
                                  on_click=lambda e: asyncio.create_task(on_search_img(keyword)))
                ]), bgcolor=COLOR_CARD, padding=10, border_radius=10,
                on_click=lambda e: asyncio.create_task(on_search_img(keyword)), ink=True
            )

        img_body.controls.append(
            ft.Container(content=ft.Text("发现美图", size=26, weight="bold"), padding=ft.padding.only(bottom=5)))
        img_body.controls.append(ft.Row([
            build_big_card("壁纸精选", "4K 超清壁纸", ft.Icons.WALLPAPER, "#8E2DE2", "#4A00E0", "4K壁纸"),
            build_big_card("二次元", "动漫 / 头像", ft.Icons.FACE_RETOUCHING_NATURAL, "#fc6767", "#ec008c",
                           "二次元头像")
        ], spacing=15))
        img_body.controls.append(ft.Container(height=10))
        img_body.controls.append(ft.Text("热门标签", size=18, weight="bold"))
        tags_data = [("赛博朋克", "未来科技风格城市", ft.Icons.COMPUTER, "#00c6ff", "赛博朋克城市"),
                     ("极简主义", "干净简约的设计", ft.Icons.BRUSH, "#333333", "极简主义壁纸"),
                     ("自然风光", "山川湖海 4K", ft.Icons.LANDSCAPE, "#56ab2f", "自然风光 4K"),
                     ("萌宠治愈", "猫咪与狗狗", ft.Icons.PETS, "#f8b500", "可爱猫咪")]
        for t in tags_data: img_body.controls.append(create_gallery_item(*t))
        page.update()

    render_img_home()
    img_view = ft.Column(
        [ft.Container(padding=ft.padding.only(top=30, left=20), content=ft.Text("Image", size=28, weight="bold")),
         ft.Container(padding=ft.padding.symmetric(horizontal=20), content=img_input),
         ft.Container(content=img_body, padding=20, expand=True)], expand=True)

    # --- 搜人页面 ---
    user_input = ft.TextField(hint_text="输入B站/抖音/小红书/微博 用户名...", expand=True, border_radius=15,
                              bgcolor=COLOR_CARD, border_color="transparent",
                              on_submit=lambda e: asyncio.create_task(on_search_user()))
    user_platform_dd = ft.Dropdown(options=[ft.dropdown.Option("all", "全部"), ft.dropdown.Option("bilibili", "B站"),
                                            ft.dropdown.Option("xiaohongshu", "小红书"),
                                            ft.dropdown.Option("douyin", "抖音"),
                                            ft.dropdown.Option("weibo", "微博")],
                                   value="all", width=100, text_size=12, bgcolor=COLOR_CARD, border_color="transparent",
                                   border_radius=15)
    user_list = ft.ListView(expand=True, spacing=10, padding=20)

    async def on_search_user():
        if not user_input.value: return
        user_list.controls = [ft.ProgressBar(color=COLOR_PRIMARY)];
        page.update()
        await asyncio.sleep(0.1)
        results = await crawler.search_social_users(user_input.value, platform=user_platform_dd.value)
        user_list.controls.clear()
        if not results: user_list.controls.append(ft.Text("未找到相关用户", color="grey"))
        for u in results:
            bg = {"Bilibili": "#FB7299", "小红书": "#FF2442", "抖音": "#000000", "微博": "#E6162D"}.get(u['platform'],
                                                                                                        COLOR_CARD)
            item = ft.Container(content=ft.Row([
                ft.Image(src=u['pic'], width=50, height=50, border_radius=25, fit="cover"),
                ft.Column([
                    ft.Row([ft.Text(u['name'], weight="bold"),
                            ft.Container(content=ft.Text(u['platform'], size=10), bgcolor=bg, padding=3,
                                         border_radius=3)]),
                    ft.Text(u['desc'], size=12, color="grey", no_wrap=True)
                ], expand=True),
                ft.IconButton(ft.Icons.OPEN_IN_NEW, icon_color="white",
                              on_click=lambda e, url=u['url']: asyncio.create_task(page.launch_url(url)))
            ]), bgcolor=COLOR_CARD, padding=10, border_radius=10)
            user_list.controls.append(item)
        page.update()

    user_view = ft.Column([ft.Container(content=ft.Text("Social Search", size=28, weight="bold"),
                                        padding=ft.padding.only(left=20, top=30)),
                           ft.Container(content=ft.Row([user_input, user_platform_dd]),
                                        padding=ft.padding.symmetric(horizontal=20)),
                           user_list], expand=True)

    # --- 设置页面 ---
    input_netease = ft.TextField(label="网易云 Cookie", multiline=True, bgcolor="#2b2b2b", border_color="grey",
                                 text_size=12, height=100, value=helper.cookies.get("netease", ""))
    input_qq_uin = ft.TextField(label="QQ号 (uin)", bgcolor="#2b2b2b", border_color="grey", text_size=12, height=45,
                                value=helper.qq_uin)
    input_qq_cookie = ft.TextField(label="QQ音乐 Cookie", multiline=True, bgcolor="#2b2b2b", border_color="grey",
                                   text_size=12, height=80, value=helper.cookies.get("qq", ""))
    input_kugou = ft.TextField(label="酷狗 Cookie", multiline=True, bgcolor="#2b2b2b", border_color="grey",
                               text_size=12, height=100, value=helper.cookies.get("kugou", ""))

    tab_body = ft.Container(content=ft.Container(content=input_netease, padding=10))
    style_active = ft.ButtonStyle(color="white", bgcolor=COLOR_PRIMARY)
    style_inactive = ft.ButtonStyle(color="grey", bgcolor="transparent")
    btn_netease = ft.TextButton("网易云", style=style_active)
    btn_qq = ft.TextButton("QQ音乐", style=style_inactive)
    btn_kugou = ft.TextButton("酷狗", style=style_inactive)

    def switch_tab(p):
        content_map = {
            "netease": ft.Container(content=input_netease, padding=10),
            "qq": ft.Container(content=ft.Column([input_qq_uin, input_qq_cookie], spacing=10), padding=10),
            "kugou": ft.Container(content=input_kugou, padding=10)
        }
        tab_body.content = content_map[p]
        btn_netease.style = style_active if p == "netease" else style_inactive
        btn_qq.style = style_active if p == "qq" else style_inactive
        btn_kugou.style = style_active if p == "kugou" else style_inactive
        page.update()

    btn_netease.on_click = lambda e: switch_tab("netease")
    btn_qq.on_click = lambda e: switch_tab("qq")
    btn_kugou.on_click = lambda e: switch_tab("kugou")

    settings_layer = ft.Container(content=ft.Container(
        content=ft.Column([
            ft.Text("VIP 配置", size=20, weight="bold", color="white"),
            ft.Row([btn_netease, btn_qq, btn_kugou], alignment="center"),
            ft.Divider(height=1, color="grey"),
            ft.Container(content=tab_body, height=180),
            ft.Row([
                ft.TextButton("取消", on_click=lambda e: setattr(settings_layer, 'visible', False) or page.update()),
                ft.ElevatedButton("保存", bgcolor=COLOR_PRIMARY, color="white", on_click=lambda e: (
                    helper.set_cookie("netease", input_netease.value),
                    helper.set_cookie("qq", input_qq_cookie.value),
                    helper.set_qq_uin(input_qq_uin.value),
                    helper.set_cookie("kugou", input_kugou.value),
                    setattr(settings_layer, 'visible', False), page.update(), show_snack("配置已保存")
                ))
            ], alignment="end")
        ], tight=True), padding=25, bgcolor="#1E1E1E", border_radius=15, width=350,
        shadow=ft.BoxShadow(blur_radius=20, color="black")
    ), alignment=ft.Alignment(0, 0), bgcolor="#CC000000", visible=False, on_click=lambda e: None, left=0, top=0,
        right=0, bottom=0)

    # --- 主导航 ---
    main_content = ft.Container(content=music_view, expand=True)
    page.navigation_bar = ft.NavigationBar(
        selected_index=0, bgcolor="#1A1A1A",
        on_change=lambda e: (
            setattr(main_content, 'content', [music_view, img_view, user_view][e.control.selected_index]),
            page.update()),
        destinations=[ft.NavigationBarDestination(icon=ft.Icons.MUSIC_NOTE, label="听歌"),
                      ft.NavigationBarDestination(icon=ft.Icons.IMAGE, label="搜图"),
                      ft.NavigationBarDestination(icon=ft.Icons.PERSON_SEARCH, label="搜人")]
    )

    page.add(ft.Stack([
        main_content,
        ft.Container(content=ft.IconButton(ft.Icons.SETTINGS, on_click=lambda e: (
        setattr(settings_layer, 'visible', True), page.update())), top=30, right=20),
        full_player_layer,
        playlist_layer,
        settings_layer
    ], expand=True))


if __name__ == "__main__":
    ft.run(main)