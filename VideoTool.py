import customtkinter as ctk
from tkinter import filedialog, Menu, END
import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD
import subprocess
import threading
import os
import pyperclip 
import re

# تنظیمات ظاهری
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

PERSIAN_FONT = ("Tahoma", 12)
HEADER_FONT = ("Tahoma", 20, "bold")
DIGIT_FONT = ("Arial", 14, "bold") 

class SuccessDialog(ctk.CTkToplevel):
    def __init__(self, parent, file_path):
        super().__init__(parent)
        self.file_path = file_path.replace("/", "\\")
        self.title("موفقیت")
        self.geometry("400x250")
        self.resizable(False, False)
        self.attributes("-topmost", True)
        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - 200
            y = parent.winfo_y() + (parent.winfo_height() // 2) - 125
            self.geometry(f"+{x}+{y}")
        except: pass
        ctk.CTkLabel(self, text="✅", font=("Arial", 60)).pack(pady=(20, 10))
        ctk.CTkLabel(self, text="ویدیو با موفقیت ساخته شد", font=HEADER_FONT, text_color="lightgreen").pack(pady=5)
        
        filename = os.path.basename(file_path)
        if len(filename) > 40: filename = filename[:37] + "..."
        ctk.CTkLabel(self, text=filename, text_color="gray70", font=("Arial", 12)).pack(pady=5)
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=20, fill="x", padx=20)
        
        ctk.CTkButton(btn_frame, text="بستن", command=self.destroy, fg_color="transparent", border_width=1, text_color="gray90", font=PERSIAN_FONT).pack(side="left", expand=True, padx=5)
        ctk.CTkButton(btn_frame, text="📂 باز کردن پوشه", command=self.open_folder, fg_color="#3B8ED0", hover_color="#36719F", font=PERSIAN_FONT).pack(side="right", expand=True, padx=5)

    def open_folder(self):
        if os.path.exists(self.file_path):
            subprocess.Popen(f'explorer /select,"{self.file_path}"')
            self.destroy()

class VideoEditorApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self)
        self.title("برش‌دهنده هوشمند")
        self.geometry("520x550") 
        self.resizable(True, True)
        self.selected_file_path = None

        self.bind_all("<Key>", self.handle_global_keys)

        self.frame_welcome = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_welcome.pack(fill="both", expand=True, padx=20, pady=20)
        self.build_welcome_ui()
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.on_drop)

    def handle_global_keys(self, event):
        if event.state & 4:
            if event.keysym.lower() in ['c', 'v', 'x', 'a']: return 
            widget = self.focus_get()
            if not isinstance(widget, tk.Entry): return
            code = event.keycode
            if code == 67:   self.perform_action(widget, "copy")
            elif code == 86: self.perform_action(widget, "paste")
            elif code == 88: self.perform_action(widget, "cut")
            elif code == 65: self.perform_action(widget, "select_all")
            return "break"

    def perform_action(self, widget, action):
        try:
            if action == "copy" and widget.selection_present():
                pyperclip.copy(widget.selection_get())
            elif action == "cut" and widget.selection_present():
                pyperclip.copy(widget.selection_get())
                widget.delete("sel.first", "sel.last")
            elif action == "paste":
                text = pyperclip.paste()
                if text:
                    try: widget.delete("sel.first", "sel.last")
                    except: pass
                    widget.insert("insert", text)
            elif action == "select_all":
                widget.select_range(0, END)
                widget.icursor(END)
        except: pass

    def setup_context_menu(self, ctk_entry):
        entry = ctk_entry._entry
        menu = Menu(self, tearoff=0)
        menu.add_command(label="Cut", command=lambda: self.perform_action(entry, "cut"))
        menu.add_command(label="Copy", command=lambda: self.perform_action(entry, "copy"))
        menu.add_command(label="Paste", command=lambda: self.perform_action(entry, "paste"))
        menu.add_separator()
        menu.add_command(label="Select All", command=lambda: self.perform_action(entry, "select_all"))
        def show_menu(event):
            entry.focus_set()
            menu.tk_popup(event.x_root, event.y_root)
        entry.bind("<Button-3>", show_menu)
        entry.bind("<Button-1>", lambda e: entry.focus_set())

    def build_welcome_ui(self):
        ctk.CTkLabel(self.frame_welcome, text="", height=50).pack()
        ctk.CTkLabel(self.frame_welcome, text="📂", font=("Arial", 80)).pack(pady=10)
        ctk.CTkLabel(self.frame_welcome, text="فایل ویدیو را اینجا رها کنید", font=HEADER_FONT).pack(pady=5)
        ctk.CTkLabel(self.frame_welcome, text="- یا -", text_color="gray", font=PERSIAN_FONT).pack(pady=10)
        ctk.CTkButton(self.frame_welcome, text="انتخاب فایل از سیستم", height=50, font=PERSIAN_FONT, command=self.browse_file_initial).pack(pady=10, padx=50, fill="x")

    def on_drop(self, event):
        file_path = event.data.strip('{}')
        if self.is_valid_video(file_path):
            self.transition_to_editor(file_path)
        else: self.bell()

    def browse_file_initial(self):
        filename = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.mkv *.mov *.avi *.webm")])
        if filename: self.transition_to_editor(filename)

    def is_valid_video(self, path):
        return path.lower().endswith(('.mp4', '.mkv', '.mov', '.avi', '.webm', '.flv'))

    def transition_to_editor(self, file_path):
        self.selected_file_path = file_path
        self.frame_welcome.pack_forget()
        self.build_editor_screen()
        self.entry_file.delete(0, "end")
        self.entry_file.insert(0, file_path)

    def build_editor_screen(self):
        self.scroll_frame = ctk.CTkScrollableFrame(self, width=500)
        self.scroll_frame.pack(fill="both", expand=True)

        ctk.CTkLabel(self.scroll_frame, text="تنظیمات ویرایش", font=HEADER_FONT).pack(pady=10)

        # فایل
        self.frame_file = ctk.CTkFrame(self.scroll_frame)
        self.frame_file.pack(pady=5, padx=20, fill="x")
        ctk.CTkButton(self.frame_file, text="🔄", width=40, command=self.browse_file_update).pack(side="left", padx=10)
        self.entry_file = ctk.CTkEntry(self.frame_file, placeholder_text="مسیر فایل...", justify="right", font=("Arial", 12))
        self.entry_file.pack(side="right", fill="x", expand=True, padx=10, pady=10)
        self.setup_context_menu(self.entry_file)

        # زمان
        self.frame_time = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.frame_time.pack(pady=5, padx=20, fill="x")
        self.time_container = ctk.CTkFrame(self.frame_time, fg_color="transparent")
        self.time_container.pack(expand=True)

        self.entry_start = ctk.CTkEntry(self.time_container, width=140, placeholder_text="Start", justify="left", font=DIGIT_FONT)
        self.entry_start.pack(side="left", padx=(0, 5)) 
        self.entry_start.insert(0, "00:00:00.000")
        self.setup_context_menu(self.entry_start)

        lbl_sep = ctk.CTkLabel(self.time_container, text="➜", font=("Arial", 20, "bold"), text_color="gray")
        lbl_sep.pack(side="left", padx=5)

        self.entry_end = ctk.CTkEntry(self.time_container, width=140, placeholder_text="End", justify="left", font=DIGIT_FONT)
        self.entry_end.pack(side="left", padx=(5, 0))
        self.entry_end.insert(0, "00:00:05.500")
        self.setup_context_menu(self.entry_end)

        # چک باکس‌ها
        self.check_container = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.check_container.pack(pady=5, padx=20, anchor="e")

        self.check_boomerang = self.add_checkbox("افکت بومرنگ (رفت و برگشت)")
        self.check_mute = self.add_checkbox("حذف صدا")
        
        # --- فشرده سازی ---
        self.frame_compress_header = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.frame_compress_header.pack(pady=5, padx=20, fill="x")
        self.btn_compress_acc = ctk.CTkButton(self.frame_compress_header, text="🔽 تنظیمات", width=80, height=24, fg_color="gray30", hover_color="gray40", command=self.toggle_compress_accordion, font=PERSIAN_FONT)
        self.btn_compress_acc.pack(side="left")
        self.check_compress = ctk.CTkCheckBox(self.frame_compress_header, text="فشرده‌سازی هوشمند (CRF)", font=PERSIAN_FONT)
        self.check_compress.pack(side="right", anchor="e")
        self.check_compress.select()

        self.frame_compress_settings = ctk.CTkFrame(self.scroll_frame, fg_color=("gray90", "gray20"))
        self.lbl_compress_info = ctk.CTkLabel(self.frame_compress_settings, text="CRF: 28 (فشرده و استاندارد)", font=PERSIAN_FONT, text_color="cyan")
        self.lbl_compress_info.pack(pady=(10, 0))
        self.slider_crf = ctk.CTkSlider(self.frame_compress_settings, from_=18, to=35, number_of_steps=17, command=self.update_compress_label)
        self.slider_crf.set(28)
        self.slider_crf.pack(fill="x", padx=20, pady=10)

        # --- سینماتیک ---
        self.frame_cine_header = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.frame_cine_header.pack(pady=5, padx=20, fill="x")
        self.btn_cine_acc = ctk.CTkButton(self.frame_cine_header, text="🔽 تنظیمات", width=80, height=24, fg_color="gray30", hover_color="gray40", command=self.toggle_cine_accordion, font=PERSIAN_FONT)
        self.btn_cine_acc.pack(side="left")
        self.check_cinematic = ctk.CTkCheckBox(self.frame_cine_header, text="حالت سینماتیک (رنگ و نور)", font=PERSIAN_FONT)
        self.check_cinematic.pack(side="right", anchor="e")
        self.check_cinematic.select()

        self.frame_cine_settings = ctk.CTkFrame(self.scroll_frame, fg_color=("gray90", "gray20"))
        self.create_slider("کنتراست", 0.5, 2.0, 1.2, "contrast")
        self.create_slider("روشنایی", -0.5, 0.5, -0.05, "brightness")
        self.create_slider("غلطت رنگ", 0.0, 3.0, 1.3, "saturation")
        ctk.CTkLabel(self.frame_cine_settings, text="--- تعادل رنگ ---", font=PERSIAN_FONT).pack(pady=2)
        self.create_slider("قرمز", 0.5, 1.5, 1.2, "gamma_r", "#ff5555")
        self.create_slider("آبی", 0.5, 1.5, 0.85, "gamma_b", "#5555ff")

        # دکمه شروع
        self.btn_run = ctk.CTkButton(self.scroll_frame, text="شروع پردازش", height=45, font=HEADER_FONT, fg_color="green", hover_color="darkgreen", command=self.start_process_thread)
        self.btn_run.pack(pady=20, padx=20, fill="x")

        # وضعیت
        self.status_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        self.status_frame.pack(pady=5, padx=20, fill="x", anchor="e")
        self.status_frame.columnconfigure(0, weight=1)

        self.label_status = ctk.CTkLabel(
            self.status_frame,
            text="\u202Bآماده...\u202C",
            text_color="gray",
            font=PERSIAN_FONT,
            anchor="e",
            justify="right",
        )
        self.label_status.grid(row=0, column=0, sticky="e")

        self.progress_bar = ctk.CTkProgressBar(self.status_frame)
        self.progress_bar.set(0)
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=5)

        self.label_size = ctk.CTkLabel(
            self.status_frame,
            text="حجم فایل: \u202A0.00 MB\u202C",
            font=("Arial", 12),
            anchor="e",
            justify="right",
        )
        self.label_size.grid(row=2, column=0, sticky="e", pady=5)

    def add_checkbox(self, text):
        wrapper = ctk.CTkFrame(self.check_container, fg_color="transparent")
        wrapper.pack(pady=5, anchor="e", fill="x")
        wrapper.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            wrapper,
            text=text.strip(),
            font=PERSIAN_FONT,
            anchor="e",
            justify="right",
            text_color="white",
        ).grid(row=0, column=0, sticky="e", padx=(0, 6))

        cb = ctk.CTkCheckBox(wrapper, text="", width=22)
        cb.grid(row=0, column=1, padx=(0, 8))

        cb.select()
        return cb

    def browse_file_update(self):
        filename = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.mkv *.mov *.avi")])
        if filename:
            self.entry_file.delete(0, "end")
            self.entry_file.insert(0, filename)

    def create_slider(self, name, min_val, max_val, default_val, attr_name, color=None):
        frame = ctk.CTkFrame(self.frame_cine_settings, fg_color="transparent")
        frame.pack(fill="x", padx=10, pady=2)
        lbl = ctk.CTkLabel(frame, text=f"{name} ({default_val})", font=PERSIAN_FONT)
        lbl.pack(side="right", padx=5)
        args = {'from_': min_val, 'to': max_val, 'number_of_steps': 30, 'command': lambda v: self.update_cine_label(lbl, name, v)}
        if color: args['progress_color'] = color
        slider = ctk.CTkSlider(frame, **args)
        slider.set(default_val)
        slider.pack(side="left", fill="x", expand=True)
        setattr(self, f"slider_{attr_name}", slider)

    def update_cine_label(self, label_widget, name, value):
        label_widget.configure(text=f"{name} ({round(value, 3)})")

    def update_compress_label(self, value):
        val = int(value)
        desc = ""
        if val <= 21: desc = "کیفیت عالی (حجم بالا)"
        elif val <= 26: desc = "استاندارد (پیشنهادی)"
        elif val <= 30: desc = "فشرده و بهینه"
        else: desc = "حجم کم (کیفیت پایین)"
        self.lbl_compress_info.configure(text=f"CRF: {val} ({desc})")

    def toggle_cine_accordion(self):
        if self.frame_cine_settings.winfo_ismapped():
            self.frame_cine_settings.pack_forget()
            self.btn_cine_acc.configure(text="🔽 تنظیمات")
        else:
            self.frame_cine_settings.pack(after=self.frame_cine_header, pady=5, padx=20, fill="x")
            self.btn_cine_acc.configure(text="🔼 بستن")

    def toggle_compress_accordion(self):
        if self.frame_compress_settings.winfo_ismapped():
            self.frame_compress_settings.pack_forget()
            self.btn_compress_acc.configure(text="🔽 تنظیمات")
        else:
            self.frame_compress_settings.pack(after=self.frame_compress_header, pady=5, padx=20, fill="x")
            self.btn_compress_acc.configure(text="🔼 بستن")

    def sanitize_time(self, time_str):
        time_str = time_str.replace(',', '.')
        if time_str.count(':') == 3:
            parts = time_str.rsplit(':', 1)
            return f"{parts[0]}.{parts[1]}"
        return time_str

    def time_to_seconds(self, time_str):
        try:
            h, m, s = time_str.split(':')
            return int(h) * 3600 + int(m) * 60 + float(s)
        except: return 0

    def start_process_thread(self):
        threading.Thread(target=self.run_ffmpeg, daemon=True).start()

    def run_ffmpeg(self):
        output_file = None
        try:
            input_file = self.entry_file.get().strip('"')
            if not input_file or not os.path.exists(input_file):
                self.label_status.configure(text="❌ خطا: فایل یافت نشد.", text_color="red")
                return

            start_t = self.sanitize_time(self.entry_start.get())
            end_t = self.sanitize_time(self.entry_end.get())
            safe_start = start_t.replace(":", "-").replace(".", "-")
            safe_end = end_t.replace(":", "-").replace(".", "-")
            directory, filename = os.path.split(input_file)
            name, ext = os.path.splitext(filename)
            output_file = os.path.join(directory, f"{name}_{safe_start}_to_{safe_end}{ext}")

            # محاسبه زمان کل برای پیشرفت
            total_duration = self.time_to_seconds(end_t) - self.time_to_seconds(start_t)
            if total_duration <= 0: total_duration = 1 
            # اگر بومرنگ باشد، زمان پردازش دو برابر است
            if self.check_boomerang.get(): total_duration *= 2

            self.btn_run.configure(state="disabled", text="در حال پردازش...")
            self.label_status.configure(text="🚀 شروع شد...", text_color="orange")
            self.progress_bar.set(0)

            cmd = ['ffmpeg', '-y', '-ss', start_t, '-to', end_t, '-i', input_file]
            filter_chains = []
            last_stream = "[0:v]"

            if self.check_cinematic.get():
                con = round(self.slider_contrast.get(), 2)
                bri = round(self.slider_brightness.get(), 2)
                sat = round(self.slider_saturation.get(), 2)
                g_r = round(self.slider_gamma_r.get(), 2)
                g_b = round(self.slider_gamma_b.get(), 2)
                cine_filter = f"{last_stream}unsharp=5:5:1.0:5:5:0.0,eq=contrast={con}:brightness={bri}:saturation={sat}:gamma_r={g_r}:gamma_b={g_b}[v_cine]"
                filter_chains.append(cine_filter)
                last_stream = "[v_cine]"

            if self.check_boomerang.get():
                boom_filter = f"{last_stream}split=2[f][r];[r]reverse[rev];[f][rev]concat=n=2:v=1:a=0[outv]"
                filter_chains.append(boom_filter)
                last_stream = "[outv]"
            elif filter_chains: 
                filter_chains.append(f"{last_stream}null[outv]")
                last_stream = "[outv]"

            if filter_chains:
                cmd.extend(['-filter_complex', ";".join(filter_chains)])
                cmd.extend(['-map', last_stream])

            crf_val = str(int(self.slider_crf.get())) if self.check_compress.get() else '20'
            cmd.extend(['-c:v', 'libx264', '-preset', 'slow', '-crf', crf_val])
            
            if self.check_mute.get(): cmd.append('-an')
            
            cmd.append(output_file)

            # استفاده از startupinfo برای مخفی کردن پنجره در ویندوز
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                universal_newlines=True, 
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
            )
            
            # ریجکس بهبود یافته که فضاهای خالی را هم قبول کند
            time_pattern = re.compile(r"time=\s*(\d{2}:\d{2}:\d{2}\.\d{2})")

            while True:
                line = process.stderr.readline()
                if not line and process.poll() is not None: 
                    break
                if line:
                    match = time_pattern.search(line)
                    if match:
                        try:
                            current_seconds = self.time_to_seconds(match.group(1))
                            progress = current_seconds / total_duration
                            # محدود کردن درصد به 1 (100%)
                            if progress > 1: progress = 1
                            self.progress_bar.set(progress)
                            self.label_status.configure(text=f"⏳ {int(progress*100)}%")
                        except: pass
                    
                    if output_file and os.path.exists(output_file):
                        try:
                            size_mb = os.path.getsize(output_file) / (1024 * 1024)
                            self.label_size.configure(text=f"حجم: \u202A{size_mb:.2f} MB\u202C")
                        except: pass

        except Exception as e:
            self.label_status.configure(text=f"خطا: {str(e)}", text_color="red")
        
        finally:
            self.progress_bar.set(1)
            self.label_status.configure(text="✅ تمام شد!", text_color="green")
            self.btn_run.configure(state="normal", text="شروع پردازش")
            # تضمین نمایش پاپ‌آپ اگر فایل ساخته شده باشد
            if output_file and os.path.exists(output_file):
                self.after(0, lambda: SuccessDialog(self, output_file))

if __name__ == "__main__":
    app = VideoEditorApp()
    app.mainloop()