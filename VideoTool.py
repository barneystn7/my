import flet as ft
import subprocess
import threading
import json
import os
import re

# --- تنظیمات رنگ و استایل ---
COLOR_BG = "#1a1a1a"
COLOR_CARD = "#2d2d2d"
COLOR_PRIMARY = "#3b8ed0"
COLOR_SUCCESS = "#00c853"
COLOR_TEXT_SEC = "#aaaaaa"

class VideoEditorApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.setup_page()
        
        # متغیرهای ذخیره اطلاعات
        self.selected_file = None
        self.tracks_data = []
        
        self.build_ui()

    def setup_page(self):
        self.page.title = "ویرایشگر هوشمند ویدیو"
        
        # تنظیمات پنجره
        self.page.window.width = 520
        self.page.window.height = 600 # کمی کوتاه‌تر شد چون یک دکمه حذف شد
        self.page.window.center()
        
        # تنظیمات اسکرول و جهت
        self.page.scroll = ft.ScrollMode.AUTO
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.bgcolor = COLOR_BG
        self.page.rtl = True  # برنامه راست‌چین است
        self.page.padding = 0 # صفر کردن پدینگ برای چسبیدن اسکرول‌بار به لبه
        
        # تنظیم فونت
        self.page.fonts = {"Persian": "Tahoma"}
        self.page.theme = ft.Theme(font_family="Persian")
        
        # فعال‌سازی درگ اند دراپ
        self.page.on_file_drop = self.on_file_drop

    def build_ui(self):
        # 1. انتخاب فایل
        self.txt_file_path = ft.TextField(
            label="مسیر فایل ویدیو", 
            read_only=True, 
            expand=True, 
            text_size=12, 
            border_color=COLOR_PRIMARY, 
            prefix_icon=ft.Icons.VIDEO_FILE 
        )
        
        self.btn_browse = ft.IconButton(
            icon=ft.Icons.FOLDER_OPEN,
            icon_color=COLOR_PRIMARY,
            tooltip="انتخاب فایل",
            on_click=lambda _: self.file_picker.pick_files()
        )

        # 2. لیست ترک‌ها (با اسکرول داخلی ثابت)
        self.track_list = ft.ListView(
            expand=True, 
            spacing=5, 
            padding=5,
            auto_scroll=False 
        )
        
        self.track_container = ft.Container(
            content=self.track_list,
            border=ft.border.all(1, "#444444"),
            border_radius=8,
            bgcolor=COLOR_CARD,
            padding=5,
            height=150, # ارتفاع ثابت
        )

        # 3. زمان‌بندی
        self.txt_start = ft.TextField(label="شروع", value="00:00:00.000", width=130, text_align="center", text_size=13)
        self.txt_end = ft.TextField(label="پایان", value="00:00:05.500", width=130, text_align="center", text_size=13)

        # 4. تنظیمات هوشمند (سوییچ + آکاردئون)

        # --- الف) بخش فشرده‌سازی ---
        self.slider_crf = ft.Slider(min=18, max=35, divisions=17, value=28, label="{value}")
        self.txt_crf_info = ft.Text("CRF: 28 (استاندارد)", size=12, color=COLOR_PRIMARY)
        self.slider_crf.on_change = lambda e: setattr(self.txt_crf_info, "value", f"CRF: {int(e.control.value)}") or self.page.update()

        # آکاردئون فشرده‌سازی
        self.exp_compress = ft.ExpansionTile(
            title=ft.Text("تنظیمات فشرده‌سازی", size=13),
            leading=ft.Icon(ft.Icons.COMPRESS, size=20),
            collapsed_text_color=COLOR_TEXT_SEC,
            initially_expanded=False,
            visible=True, # پیش‌فرض روشن
            controls=[
                ft.Container(
                    content=ft.Column([self.txt_crf_info, self.slider_crf]),
                    padding=15, bgcolor="#222222", border_radius=10
                )
            ]
        )
        # سوییچ فشرده‌سازی
        self.sw_compress = ft.Switch(
            label="فشرده‌سازی (CRF)", value=True, active_color=COLOR_PRIMARY,
            on_change=lambda e: self.toggle_visibility(self.exp_compress, e.control.value)
        )

        # --- ب) بخش سینماتیک ---
        self.sl_con = self.create_slider("کنتراست", 0.5, 2.0, 1.2)
        self.sl_bri = self.create_slider("روشنایی", -0.5, 0.5, -0.05)
        self.sl_sat = self.create_slider("غلظت رنگ", 0.0, 3.0, 1.3)
        self.sl_gam_r = self.create_slider("قرمز", 0.5, 1.5, 1.2, "red") 
        self.sl_gam_b = self.create_slider("آبی", 0.5, 1.5, 0.85, "blue")

        # آکاردئون سینماتیک
        self.exp_cine = ft.ExpansionTile(
            title=ft.Text("تنظیمات رنگ و نور", size=13),
            leading=ft.Icon(ft.Icons.COLOR_LENS, size=20),
            collapsed_text_color=COLOR_TEXT_SEC,
            initially_expanded=False,
            visible=True,
            controls=[
                ft.Container(
                    content=ft.Column([
                        self.sl_con, self.sl_bri, self.sl_sat,
                        ft.Divider(height=10, color="transparent"),
                        ft.Text("تعادل رنگ RGB", size=12, color=COLOR_TEXT_SEC),
                        self.sl_gam_r, self.sl_gam_b
                    ]),
                    padding=15, bgcolor="#222222", border_radius=10
                )
            ]
        )
        # سوییچ سینماتیک
        self.sw_cine = ft.Switch(
            label="حالت سینماتیک", value=True, active_color=COLOR_PRIMARY,
            on_change=lambda e: self.toggle_visibility(self.exp_cine, e.control.value)
        )

        # سایر سوییچ‌ها (حذف صدا پاک شد)
        self.sw_boomerang = ft.Switch(label="افکت بومرنگ", active_color=COLOR_PRIMARY)

        # 5. دکمه‌ها
        self.btn_run = ft.ElevatedButton(
            text="شروع پردازش",
            icon=ft.Icons.ROCKET_LAUNCH,
            style=ft.ButtonStyle(
                bgcolor=COLOR_SUCCESS,
                color="white",
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=20
            ),
            width=300,
            on_click=self.start_processing
        )
        
        self.progress_bar = ft.ProgressBar(value=0, color=COLOR_SUCCESS, bgcolor="#444444", visible=False)
        self.txt_status = ft.Text("منتظر فایل...", size=12, color=COLOR_TEXT_SEC)

        self.file_picker = ft.FilePicker(on_result=self.on_pick)
        self.page.overlay.append(self.file_picker)

        # === چیدمان نهایی (Main Layout) ===
        main_layout = ft.Container(
            padding=20, # فاصله محتوا از لبه‌ها
            content=ft.Column([
                # هدر
                ft.Container(
                    content=ft.Text("📥 فایل را اینجا رها کنید", weight="bold", size=18),
                    alignment=ft.alignment.center,
                    padding=10
                ),
                
                # انتخاب فایل
                ft.Row([self.txt_file_path, self.btn_browse], alignment="center"),
                
                # لیست ترک‌ها
                ft.Text("ترک‌های فایل:", weight="bold"),
                self.track_container, 
                
                ft.Divider(height=1, color="#444444"),
                
                # تایم‌لاین
                # چیدمان: [پایان (راست)] -> [فلش] -> [شروع (چپ)]
                ft.Row(
                    [
                        self.txt_end,  
                        ft.Icon(ft.Icons.ARROW_BACK, color="grey"), 
                        self.txt_start 
                    ],
                    alignment="center"
                ),
                
                ft.Divider(height=1, color="#444444"),
                
                # تنظیمات
                self.sw_boomerang,
                # سوییچ حذف صدا حذف شد
                
                ft.Divider(height=10, color="transparent"),
                
                # گروه فشرده‌سازی
                ft.Column([
                    self.sw_compress,
                    self.exp_compress
                ], spacing=0),

                ft.Divider(height=5, color="transparent"),

                # گروه سینماتیک
                ft.Column([
                    self.sw_cine,
                    self.exp_cine
                ], spacing=0),
                
                # فوتر
                ft.Container(height=15),
                ft.Row([self.btn_run], alignment="center"),
                self.progress_bar,
                ft.Container(self.txt_status, alignment=ft.alignment.center),
                ft.Container(height=20) 
            ])
        )

        self.page.add(main_layout)

    # --- توابع کمکی ---
    def toggle_visibility(self, control, is_visible):
        """نمایش یا مخفی کردن آکاردئون بر اساس سوییچ"""
        control.visible = is_visible
        self.page.update()

    def create_slider(self, label, min_v, max_v, def_v, color=COLOR_PRIMARY):
        txt = ft.Text(f"{label}: {def_v}", size=12)
        sl = ft.Slider(min=min_v, max=max_v, divisions=30, value=def_v, active_color=color, label="{value}")
        sl.on_change = lambda e: setattr(txt, "value", f"{label}: {round(e.control.value, 2)}") or self.page.update()
        return ft.Column([txt, sl], spacing=0)

    # --- منطق برنامه ---
    def on_pick(self, e):
        if e.files: self.load_file(e.files[0].path)

    def on_file_drop(self, e):
        if e.files:
            # رویداد دراپ لیست فایل‌ها را برمی‌گرداند
            self.load_file(e.files[0].path)
        elif getattr(e, "path", None):
            # سازگاری با نسخه‌هایی که هنوز path را ست می‌کنند
            self.load_file(e.path)

    def load_file(self, path):
        if not path.lower().endswith(('.mp4', '.mkv', '.mov', '.avi', '.webm', '.flv')):
            self.page.snack_bar = ft.SnackBar(ft.Text("فرمت فایل پشتیبانی نمی‌شود!"), bgcolor="red")
            self.page.snack_bar.open = True
            self.page.update()
            return

        self.selected_file = path
        self.txt_file_path.value = path
        self.txt_status.value = "در حال تحلیل فایل..."
        self.progress_bar.visible = True
        self.page.update()
        
        threading.Thread(target=self.analyze_file, args=(path,), daemon=True).start()

    def analyze_file(self, path):
        try:
            cmd = ["ffprobe", "-v", "error", "-show_entries", "stream=index,codec_type,codec_name:stream_tags=language,title", "-of", "json", path]
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            res = subprocess.run(cmd, capture_output=True, text=True, startupinfo=si)
            data = json.loads(res.stdout)
            
            self.tracks_data = []
            type_map = {"video": "ویدیو", "audio": "صدا", "subtitle": "زیرنویس"}
            counters = {"video": 0, "audio": 0, "subtitle": 0}

            for s in data.get("streams", []):
                t = s.get("codec_type", "unknown")
                if t not in counters: counters[t] = 0
                track = {
                    "idx": counters[t],
                    "real_index": s["index"],
                    "type": t,
                    "codec": s.get("codec_name", "").upper(),
                    "lang": s.get("tags", {}).get("language", "-").upper(),
                    "label": type_map.get(t, t),
                    "control": ft.Checkbox(value=True)
                }
                self.tracks_data.append(track)
                counters[t] += 1
            
            self.update_list_ui()
            
        except Exception as e:
            self.txt_status.value = f"خطا: {e}"
        finally:
            self.progress_bar.visible = False
            self.page.update()

    def update_list_ui(self):
        self.track_list.controls.clear()
        for t in self.tracks_data:
            if t['type'] == 'video': icon = ft.Icons.VIDEOCAM
            elif t['type'] == 'audio': icon = ft.Icons.AUDIOTRACK
            else: icon = ft.Icons.SUBTITLES
            
            self.track_list.controls.append(
                ft.Container(
                    content=ft.Row([
                        t['control'],
                        ft.Icon(icon, size=16, color=COLOR_TEXT_SEC),
                        ft.Text(t['codec'], width=60, text_align="center", size=12),
                        ft.Text(t['label'], expand=1, text_align="center", size=12, color=COLOR_TEXT_SEC),
                        ft.Text(t['lang'], width=40, text_align="center", size=12),
                    ], alignment="start"),
                    bgcolor="#333333", border_radius=5, padding=ft.padding.symmetric(horizontal=5, vertical=2)
                )
            )
        self.txt_status.value = f"✅ {len(self.tracks_data)} ترک بارگذاری شد."
        self.page.update()

    def start_processing(self, e):
        if not self.selected_file: return
        
        cfg = {
            "start": self.txt_start.value, "end": self.txt_end.value,
            "boomerang": self.sw_boomerang.value,
            # "mute": حذف شد چون از لیست ترک‌ها خوانده می‌شود
            "compress": self.sw_compress.value, "cine": self.sw_cine.value,
            "crf": int(self.slider_crf.value),
            "con": self.sl_con.controls[1].value, "bri": self.sl_bri.controls[1].value,
            "sat": self.sl_sat.controls[1].value,
            "gr": self.sl_gam_r.controls[1].value, "gb": self.sl_gam_b.controls[1].value,
            "tracks": [t for t in self.tracks_data if t['control'].value]
        }
        
        self.btn_run.disabled = True
        self.progress_bar.visible = True
        self.progress_bar.value = None
        self.txt_status.value = "در حال پردازش..."
        self.page.update()
        threading.Thread(target=self.run_ffmpeg, args=(cfg,), daemon=True).start()

    def run_ffmpeg(self, cfg):
        try:
            inp = self.selected_file
            d, f = os.path.split(inp)
            name, ext = os.path.splitext(f)
            safe_time = cfg['start'].replace(":", "-").replace(".", "")
            out = os.path.join(d, f"{name}_EDIT_{safe_time}{ext}")
            
            cmd = ['ffmpeg', '-y', '-ss', cfg['start'], '-to', cfg['end'], '-i', inp]
            filters = []
            video_tracks = [t for t in cfg['tracks'] if t['type'] == 'video']
            
            if video_tracks:
                vid_idx = video_tracks[0]['idx']
                last_stream = f"[0:v:{vid_idx}]"
                if cfg['cine']:
                    filters.append(f"{last_stream}unsharp=5:5:1.0:5:5:0.0,eq=contrast={cfg['con']}:brightness={cfg['bri']}:saturation={cfg['sat']}:gamma_r={cfg['gr']}:gamma_b={cfg['gb']}[v_cine]")
                    last_stream = "[v_cine]"
                if cfg['boomerang']:
                    filters.append(f"{last_stream}split=2[f][r];[r]reverse[rev];[f][rev]concat=n=2:v=1:a=0[outv]")
                    last_stream = "[outv]"
                elif cfg['cine']: 
                    filters.append(f"{last_stream}null[outv]")
                    last_stream = "[outv]"
                
                if filters: cmd.extend(['-filter_complex', ";".join(filters), '-map', last_stream])
                else: cmd.extend(['-map', f"0:v:{vid_idx}"])
                
                if cfg['compress'] or filters: cmd.extend(['-c:v', 'libx264', '-crf', str(cfg['crf']), '-preset', 'fast'])
                else: cmd.extend(['-c:v', 'copy'])

            # --- بخش صدا (اصلاح شده) ---
            # فقط صداهای تیک خورده در لیست اضافه می‌شوند.
            # اگر هیچ صدایی تیک نخورده باشد، خودکار بی‌صدا می‌شود.
            has_audio = False
            for t in cfg['tracks']:
                if t['type'] == 'audio':
                    cmd.extend(['-map', f"0:a:{t['idx']}"])
                    has_audio = True
            
            if has_audio:
                cmd.extend(['-c:a', 'copy']) # کپی صدا
            
            # --- بخش زیرنویس ---
            has_sub = False
            for t in cfg['tracks']:
                if t['type'] == 'subtitle':
                    cmd.extend(['-map', f"0:s:{t['idx']}"])
                    has_sub = True
            if has_sub: cmd.extend(['-c:s', 'copy'])
            
            cmd.append(out)
            si = subprocess.STARTUPINFO(); si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.run(cmd, check=True, startupinfo=si)
            
            self.page.snack_bar = ft.SnackBar(ft.Text("✅ فایل ذخیره شد!"), bgcolor=COLOR_SUCCESS, action="باز کردن", on_action=lambda _: self.open_folder(out))
            self.page.snack_bar.open = True
            self.txt_status.value = "پایان."
        except Exception as e:
            self.page.snack_bar = ft.SnackBar(ft.Text(f"خطا: {str(e)}"), bgcolor="red")
            self.page.snack_bar.open = True
            self.txt_status.value = "خطا."
        finally:
            self.btn_run.disabled = False
            self.progress_bar.visible = False
            self.page.update()

    def open_folder(self, file_path):
        try: os.startfile(os.path.dirname(file_path))
        except: pass

if __name__ == "__main__":
    ft.app(target=VideoEditorApp)