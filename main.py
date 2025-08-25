import os
import time
from datetime import datetime
import json
import sys
import threading
import builtins  # Thêm để tránh xung đột với các biến đã import

import cv2
import torch
import pandas as pd
from PIL import Image, ImageTk
import pygame  # Thêm thư viện âm thanh

import tkinter as tk
from tkinter import ttk, messagebox
import tkinter.font as font
from tkinter import simpledialog

# Import các module đã tạo
from config import Config, yolo_LP_detect, yolo_license_plate, SOUND_SUCCESS, SOUND_FAIL
from login import LoginApp

# Khởi tạo pygame cho âm thanh
pygame.mixer.init()

# =============== HÀM CHUẨN HÓA BIỂN SỐ ===============
def normalize_plate(s: str) -> str:
    if not isinstance(s, str):
        s = str(s)
    s = s.upper().strip()
    # bỏ khoảng trắng, gạch nối, gạch dưới, chấm
    for ch in [" ", "-", "_", ".", "–", "—"]:
        s = s.replace(ch, "")
    return s

# =============== ĐĂNG KÝ: TXT ===============
def load_registered_set() -> set:
    plates = set()
    with open(Config.REGISTER_FILE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            plate = line.strip()
            if plate:
                plates.add(normalize_plate(plate))
    return plates

def append_registered(plate_raw: str) -> bool:
    plate_norm = normalize_plate(plate_raw)
    reg = load_registered_set()
    if plate_norm in reg:
        return False
    with open(Config.REGISTER_FILE_PATH, "a", encoding="utf-8") as f:
        f.write(plate_raw.strip().upper() + "\n")
    return True

def read_registered_list() -> list:
    items = []
    with open(Config.REGISTER_FILE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            p = line.strip()
            if p:
                items.append(p)
    return items

# =============== LƯU SCAN: EXCEL ===============
def save_scan_to_excel(plate_raw: str, status_text: str, action="IN"):
    """Ghi vào Excel:
       - Nếu cùng NGÀY và biển số đã có và action="IN" -> cập nhật 'Thời gian ra' nếu có
       - Nếu chưa có -> thêm dòng mới với 'Thời gian vào' hiện tại
    """
    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%H:%M:%S")
    plate_norm = normalize_plate(plate_raw)

    df = pd.read_excel(Config.SCAN_FILE_PATH)

    # Lọc cùng ngày & cùng biển số (so khớp sau khi normalize)
    # Tạo cột phụ normalized để dò (không lưu vào file)
    if "normalized" not in df.columns:
        df["normalized"] = df["Biển số"].astype(str).apply(normalize_plate)
    else:
        df["normalized"] = df["Biển số"].astype(str).apply(normalize_plate)

    # Tồn tại record cùng ngày & chưa có thời gian ra? -> cập nhật ra
    mask = (df["Ngày"] == today) & (df["normalized"] == plate_norm)
    if mask.any():
        idxs = df[mask].index.tolist()
        updated = False
        for idx in idxs:
            if action == "OUT" and pd.isna(df.at[idx, "Thời gian ra"]) or df.at[idx, "Thời gian ra"] in [None, "", "nan"]:
                # Cập nhật thời gian ra
                df.at[idx, "Thời gian ra"] = now_time
                updated = True
                break
            elif action == "IN" and pd.isna(df.at[idx, "Thời gian vào"]) or df.at[idx, "Thời gian vào"] in [None, "", "nan"]:
                # Cập nhật thời gian vào
                df.at[idx, "Thời gian vào"] = now_time
                updated = True
                break
        
        if not updated:
            # Đã có bản ghi đầy đủ -> thêm bản ghi mới (lần vào tiếp theo)
            new_row = {
                "Ngày": today,
                "Biển số": plate_raw.upper(),
                "Trạng thái": status_text,
                "Thời gian vào": now_time,
                "Thời gian ra": None
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    else:
        # chưa có -> thêm bản ghi mới (xe vào)
        new_row = {
            "Ngày": today,
            "Biển số": plate_raw.upper(),
            "Trạng thái": status_text,
            "Thời gian vào": now_time,
            "Thời gian ra": None
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    # Xóa cột phụ rồi lưu
    if "normalized" in df.columns:
        df = df.drop(columns=["normalized"])
    df.to_excel(Config.SCAN_FILE_PATH, index=False)

def read_today_scans() -> pd.DataFrame:
    today = datetime.now().strftime("%Y-%m-%d")
    if not os.path.exists(Config.SCAN_FILE_PATH):
        return pd.DataFrame(columns=["Ngày", "Biển số", "Trạng thái", "Thời gian vào", "Thời gian ra"])
    df = pd.read_excel(Config.SCAN_FILE_PATH)
    if df.empty:
        return df
    return df[df["Ngày"] == today].copy()

# =============== BIẾN TOÀN CỤC CHO ỨNG DỤNG ===============
COOLDOWN_SECONDS = 5  # Tránh ghi trùng trong khoảng thời gian ngắn
recent_seen = {}      # plate_norm -> last_time (epoch)
plate_status = {}     # plate_norm -> { "first_seen": timestamp, "status": "pending" }

# Phát âm thanh
def play_sound(success):
    """Phát âm thanh khi quét thành công hoặc thất bại"""
    try:
        if success:
            pygame.mixer.music.load(SOUND_SUCCESS)
            pygame.mixer.music.play()
        else:
            # Phát âm thanh fail 2 lần
            pygame.mixer.music.load(SOUND_FAIL)
            pygame.mixer.music.play()
            time.sleep(0.2)
            pygame.mixer.music.load(SOUND_FAIL)
            pygame.mixer.music.play()
    except:
        pass  # Bỏ qua nếu không có âm thanh

# =============== CHỨC NĂNG CẬP NHẬT THÔNG TIN CẤU HÌNH ===============
def update_config():
    """Cập nhật file config với các giá trị mới"""
    config_data = {
        "login_user": Config.LOGIN_USER,
        "login_pass": Config.LOGIN_PASS,
        "scan_interval_in": Config.SCAN_INTERVAL_IN,
        "scan_interval_out": Config.SCAN_INTERVAL_OUT
    }
    with open(Config.CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)

def set_scan_intervals():
    """Mở cửa sổ để cài đặt thời gian quét vào/ra"""
    # Sử dụng các toàn cục đã được khai báo
    global Config
    
    # Tạo cửa sổ mới
    dialog = tk.Toplevel()
    dialog.title("Cài đặt thời gian quét")
    dialog.geometry("400x250")
    dialog.resizable(False, False)
    
    # Tạo frame chính
    main_frame = tk.Frame(dialog, bg="#f0f0f0", padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)
    
    # Tiêu đề
    tk.Label(main_frame, text="Cài đặt thời gian quét", font=("Arial", 14, "bold"), 
           bg="#f0f0f0").pack(pady=(0, 20))
    
    # Nhập thời gian quét vào
    in_frame = tk.Frame(main_frame, bg="#f0f0f0")
    in_frame.pack(fill="x", pady=10)
    tk.Label(in_frame, text="Thời gian chờ xác nhận xe vào (giây):", 
           font=("Arial", 10), bg="#f0f0f0", width=30, anchor="w").pack(side="left")
    in_entry = tk.Entry(in_frame, font=("Arial", 10), width=10)
    in_entry.pack(side="right")
    in_entry.insert(0, str(Config.SCAN_INTERVAL_IN))
    
    # Nhập thời gian quét ra
    out_frame = tk.Frame(main_frame, bg="#f0f0f0")
    out_frame.pack(fill="x", pady=10)
    tk.Label(out_frame, text="Thời gian chờ xác nhận xe ra (giây):", 
           font=("Arial", 10), bg="#f0f0f0", width=30, anchor="w").pack(side="left")
    out_entry = tk.Entry(out_frame, font=("Arial", 10), width=10)
    out_entry.pack(side="right")
    out_entry.insert(0, str(Config.SCAN_INTERVAL_OUT))
    
    # Nút xác nhận
    def confirm():
        try:
            # Cập nhật cấu hình
            old_config = Config
            Config.LOGIN_USER = old_config.LOGIN_USER
            Config.LOGIN_PASS = old_config.LOGIN_PASS
            Config.SCAN_INTERVAL_IN = int(in_entry.get())
            Config.SCAN_INTERVAL_OUT = int(out_entry.get())
            
            # Cập nhật các file path
            Config.SCAN_FILE = old_config.SCAN_FILE_PATH
            Config.REGISTER_FILE = old_config.REGISTER_FILE_PATH
            Config.CONFIG_FILE = old_config.CONFIG_FILE_PATH
            Config.CONFIG_SOUND = old_config.CONFIG_SOUND_PATH
            
            update_config()
            dialog.destroy()
            messagebox.showinfo("Thành công", "Đã cập nhật thời gian quét!")
            
            # Cập nhật hiển thị
            app.config_frame.config(text=f"Cấu hình: Thời gian quét vào: {Config.SCAN_INTERVAL_IN} giây, Thời gian quét ra: {Config.SCAN_INTERVAL_OUT} giây")
        except ValueError:
            messagebox.showerror("Lỗi", "Vui lòng nhập số nguyên hợp lệ!")
    
    button_frame = tk.Frame(main_frame, bg="#f0f0f0")
    button_frame.pack(pady=20)
    tk.Button(button_frame, text="Xác nhận", command=confirm, 
            bg="#3498db", fg="white", font=("Arial", 10, "bold"), 
            padx=20, pady=5).pack(side="left", padx=10)
    tk.Button(button_frame, text="Hủy", command=dialog.destroy, 
            bg="#95a5a6", fg="white", font=("Arial", 10, "bold"), 
            padx=20, pady=5).pack(side="left")
    
    # Center dialog
    dialog.transient(app)
    dialog.grab_set()
    app.wait_window(dialog)

# =============== ỨNG DỤNG CHÍNH ===============
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Hệ thống điểm danh xe")
        self.geometry("1100x750")
        self.resizable(False, False)

        # Thiết lập font
        heading_font = font.nametofont("TkHeadingFont")
        heading_font.configure(family="Arial", size=12, weight="bold")

        # Yêu cầu đăng nhập trước
        self._check_login()
        
        # Biến camera
        self.cap = None
        self.prev_frame_time = 0
        self.registered_set = load_registered_set()
        self.canvas_tab = None  # Khởi tạo biến canvas_tab

        # Xây dựng giao diện chính
        self._build_main_ui()

    def _check_login(self):
        """Kiểm tra xem đã đăng nhập chưa"""
        log = LoginApp(self, Config)
        if not log.logged_in:
            self.destroy()

    # --------- MAIN UI (NOTEBOOK) ---------
    def _build_main_ui(self):
        # Tạo container mới
        container = tk.Frame(self, bg="#f5f5f5")
        container.pack(fill="both", expand=True)
        
        # Xây dựng giao diện chính trong container mới
        self.notebook = ttk.Notebook(container)
        self.notebook.pack(fill="both", expand=True)
        
        # Tab 1: Camera
        self.tab_camera = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_camera, text="Camera quét xe")
        self._build_tab_camera()
        
        # Tab 2: Danh sách quét hôm nay
        self.tab_today = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_today, text="Danh sách quét hôm nay")
        self._build_tab_today()
        
        # Tab 3: Đăng ký xe
        self.tab_register = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_register, text="Đăng ký xe")
        self._build_tab_register()
        
        # Focus vào tab camera
        self.notebook.select(self.tab_camera)

    # --------- TAB CAMERA ---------
    def _build_tab_camera(self):
        # Header
        header = tk.Frame(self.tab_camera, bg="white", height=80)
        header.pack(fill="x", padx=10, pady=10)
        header.pack_propagate(False)
        
        tk.Label(header, text="Camera quét xe", font=("Arial", 16, "bold"), 
                bg="white", fg="#2c3e50").pack(expand=True)
        
        # Khung hiển thị camera
        camera_container = tk.Frame(self.tab_camera, bg="black", relief="ridge", bd=2)
        camera_container.pack(padx=10, pady=10, fill="both", expand=True)
        
        self.lbl_video = tk.Label(camera_container, bd=0, bg="black")
        self.lbl_video.pack(fill="both", expand=True)
        
        # Thêm ô hiển thị biển số đang nhận diện
        self.plate_info_frame = tk.Frame(self.tab_camera, height=60, bg="#ecf0f1", relief="ridge", bd=2)
        self.plate_info_frame.pack(fill="x", padx=10, pady=5)
        self.plate_info_frame.pack_propagate(False)
        
        self.lbl_plate_info = tk.Label(self.plate_info_frame, text="", 
                                      font=("Arial", 18, "bold"), bg="#ecf0f1", fg="#2c3e50")
        self.lbl_plate_info.pack(expand=True)
        
        # Status line
        self.status_bar = tk.Frame(self.tab_camera, bg="#34495e", height=35)
        self.status_bar.pack(fill="x", padx=10, pady=5)
        self.status_bar.pack_propagate(False)
        
        self.lbl_status = tk.Label(self.status_bar, text="Trạng thái: Sẵn sàng", 
                                  font=("Arial", 10), bg="#34495e", fg="white", anchor="w")
        self.lbl_status.pack(fill="x", padx=10, pady=5)
        
        # Nút điều khiển
        controls = tk.Frame(self.tab_camera, bg="#f5f5f5")
        controls.pack(pady=15, padx=10, fill="x")
        
        # Dùng màu sắc và font rõ ràng hơn
        tk.Button(controls, text="Bật camera", width=16, height=2, 
                 command=self.start_camera, bg="#27ae60", fg="white", 
                 font=("Arial", 11, "bold")).pack(side="left", padx=8)
        
        tk.Button(controls, text="Tắt camera", width=16, height=2, 
                 command=self.stop_camera, bg="#e74c3c", fg="white", 
                 font=("Arial", 11, "bold")).pack(side="left", padx=8)
        
        tk.Button(controls, text="Làm mới DS đăng ký", width=18, height=2, 
                 command=self._refresh_registered_cache, bg="#3498db", fg="white", 
                 font=("Arial", 11, "bold")).pack(side="left", padx=8)
        
        # Nút cài đặt thời gian quét
        tk.Button(controls, text="Cài đặt thời gian quét", width=16, height=2, 
                 command=set_scan_intervals, bg="#9b59b6", fg="white", 
                 font=("Arial", 11, "bold")).pack(side="left", padx=8)
        
        # Thêm thông tin cấu hình
        self.config_frame = tk.Frame(self.tab_camera, bg="#f5f5f5")
        self.config_frame.pack(fill="x", padx=10, pady=5)
        
        self.config_text = f"Cấu hình: Thời gian quét vào: {Config.SCAN_INTERVAL_IN} giây, Thời gian quét ra: {Config.SCAN_INTERVAL_OUT} giây"
        tk.Label(self.config_frame, text=self.config_text, 
                font=("Arial", 10), bg="#f5f5f5", fg="#7f8c8d").pack(anchor="w")

    def _refresh_registered_cache(self):
        self.registered_set = load_registered_set()
        messagebox.showinfo("Thông báo", "Đã tải lại danh sách đăng ký (TXT).")

    def start_camera(self):
        if yolo_LP_detect is None or yolo_license_plate is None:
            messagebox.showerror("Lỗi", "Model YOLO chưa sẵn sàng!")
            return
        if self.cap is None:
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap.release()
                self.cap = None
                messagebox.showerror("Lỗi", "Không mở được camera!")
                return
        self.lbl_status.config(text="Trạng thái: Camera đang chạy (nhấn Tắt camera để dừng)")
        self._update_frame()

    def stop_camera(self):
        self.lbl_status.config(text="Trạng thái: Đã tắt camera")
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.lbl_video.config(image="")
        self.lbl_plate_info.config(text="")

    def _update_frame(self):
        if self.cap is None:
            return

        ok, frame = self.cap.read()
        if not ok:
            self.stop_camera()
            return

        # YOLO detect biển số
        if yolo_LP_detect is not None and yolo_license_plate is not None:
            plates = yolo_LP_detect(frame, size=416)
            list_plates = plates.pandas().xyxy[0].values.tolist()
            
            for plate in list_plates:
                x1, y1, x2, y2 = map(int, plate[:4])
                crop_img = frame[y1:y2, x1:x2]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 225), 2)

                # OCR và deskew thử vài hướng
                found_text = None
                for cc in range(2):
                    for ct in range(2):
                        lp_text = helper.read_plate(yolo_license_plate, utils_rotate.deskew(crop_img, cc, ct))
                        if lp_text and lp_text != "unknown":
                            found_text = lp_text
                            break
                    if found_text:
                        break

                if found_text:
                    plate_norm = normalize_plate(found_text)
                    
                    # Kiểm tra cooldown
                    now = time.time()
                    last_seen = recent_seen.get(plate_norm, 0)
                    if now - last_seen >= COOLDOWN_SECONDS:
                        recent_seen[plate_norm] = now
                        
                        # Kiểm tra xem biển số đã được thấy trước đó chưa
                        if plate_norm in plate_status:
                            # Đã thấy trước đó, kiểm tra thời gian để xác định vào/ra
                            first_seen = plate_status[plate_norm]["first_seen"]
                            time_diff = now - first_seen
                            
                            if time_diff >= Config.SCAN_INTERVAL_IN and plate_status[plate_norm]["status"] == "pending":
                                # Xác nhận xe vào
                                is_registered = plate_norm in self.registered_set
                                status_text = "ĐÃ ĐĂNG KÝ" if is_registered else "CHƯA ĐĂNG KÝ"
                                
                                # Lưu Excel (vào)
                                save_scan_to_excel(found_text, status_text, "IN")
                                
                                # Cập nhật thông tin biển số
                                plate_color = "#27ae60" if is_registered else "#e74c3c"
                                
                                # Cập nhật trạng thái biển số
                                plate_status[plate_norm]["status"] = "in"
                                
                                self.lbl_plate_info.config(
                                    text=f"Xe vào: {found_text} ({status_text})",
                                    fg=plate_color
                                )
                                
                                # Phát âm thanh thành công
                                play_sound(is_registered)
                                
                                # Vẽ label trên ảnh
                                cv2.putText(frame, f"VÀO: {found_text} ({status_text})", (x1, max(25, y1 - 10)),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                            
                            elif time_diff >= Config.SCAN_INTERVAL_OUT and plate_status[plate_norm]["status"] == "in":
                                # Xác nhận xe ra
                                is_registered = plate_norm in self.registered_set
                                status_text = "ĐÃ ĐĂNG KÝ" if is_registered else "CHƯA ĐĂNG KÝ"
                                
                                # Lưu Excel (ra)
                                save_scan_to_excel(found_text, status_text, "OUT")
                                
                                # Cập nhật thông tin biển số
                                plate_color = "#27ae60" if is_registered else "#e74c3c"
                                
                                # Xóa thông tin biển số khỏi plate_status vì xe đã ra
                                del plate_status[plate_norm]
                                
                                self.lbl_plate_info.config(
                                    text=f"Xe ra: {found_text} ({status_text})",
                                    fg=plate_color
                                )
                                
                                # Phát âm thanh thành công
                                play_sound(is_registered)
                                
                                # Vẽ label trên ảnh
                                cv2.putText(frame, f"RA: {found_text} ({status_text})", (x1, max(25, y1 - 10)),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                            else:
                                # Chờ thêm
                                cv2.putText(frame, f"Chờ: {found_text}", (x1, max(25, y1 - 10)),
                                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 0), 2)
                        else:
                            # Lần đầu tiên thấy biển số này
                            plate_status[plate_norm] = {
                                "first_seen": now,
                                "status": "pending"
                            }
                            
                            # Vẽ label trên ảnh
                            cv2.putText(frame, f"Chờ: {found_text}", (x1, max(25, y1 - 10)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 0), 2)
        
        # FPS
        new_t = time.time()
        fps = 0 if self.prev_frame_time == 0 else 1 / (new_t - self.prev_frame_time)
        self.prev_frame_time = new_t
        cv2.putText(frame, f"FPS: {int(fps)}", (7, 35), cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 255, 0), 2)

        # Hiển thị lên Tkinter
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        im = Image.fromarray(frame_rgb)
        
        # Đảm bảo tỷ lệ khung hình
        video_height = 480
        ratio = video_height / im.height
        new_width = int(im.width * ratio)
        new_height = video_height
        im = im.resize((new_width, new_height), Image.LANCZOS)
        
        imgtk = ImageTk.PhotoImage(image=im)
        self.lbl_video.imgtk = imgtk
        self.lbl_video.configure(image=imgtk)

        # Tăng thời gian cập nhật frame để giảm tốn tài nguyên
        self.after(10, self._update_frame)

    # ---- Tab Danh sách hôm nay ----
    def _build_tab_today(self):
        # Header
        header = tk.Frame(self.tab_today, bg="white", height=80)
        header.pack(fill="x", padx=10, pady=10)
        header.pack_propagate(False)
        
        tk.Label(header, text="Danh sách quét hôm nay", font=("Arial", 16, "bold"), 
                bg="white", fg="#2c3e50").pack(expand=True)
        
        # Thanh công cụ
        toolbar = tk.Frame(self.tab_today, bg="white", height=50)
        toolbar.pack(fill="x", padx=10, pady=(0, 10))
        
        tk.Button(toolbar, text="Làm mới", width=12, height=2, 
                 command=self.reload_today_table, bg="#3498db", fg="white", 
                 font=("Arial", 10, "bold")).pack(side="left", padx=5, pady=5)
        
        tk.Label(toolbar, text="(Dữ liệu lấy từ Excel)", 
                font=("Arial", 10), bg="white", fg="#7f8c8d").pack(side="left", padx=10)
        
        # Tạo thanh cuộn tùy chỉnh
        self.canvas_tab = tk.Canvas(self.tab_today, bg="white")
        scrollbar = ttk.Scrollbar(self.tab_today, orient="vertical", command=self.canvas_tab.yview)
        scrollable_frame = tk.Frame(self.canvas_tab, bg="white")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas_tab.configure(scrollregion=self.canvas_tab.bbox("all"))
        )
        
        self.canvas_tab.create_window((0, 0), window=scrollable_frame, anchor="nw")
        self.canvas_tab.configure(yscrollcommand=scrollbar.set)
        
        self.canvas_tab.pack(side="left", fill="both", expand=True, padx=10, pady=(0, 10))
        scrollbar.pack(side="right", fill="y", padx=(0, 10))
        
        cols = ("Ngày", "Biển số", "Trạng thái", "Thời gian vào", "Thời gian ra")
        
        # Tạo header
        header_frame = tk.Frame(scrollable_frame, bg="#34495e", height=40)
        header_frame.pack(fill="x")
        
        for i, c in enumerate(cols):
            tk.Label(header_frame, text=c, 
                   font=("Arial", 11, "bold"), 
                   bg="#34495e", fg="white",
                   width=20 if i == 1 else 15,
                   anchor="center").grid(row=0, column=i, padx=2, pady=2, sticky="ew")
        
        # Tạo Treeview inner để keep styling consistent
        self.tree_inner_frame = tk.Frame(scrollable_frame)
        self.tree_inner_frame.pack(fill="both", expand=True)
        
        self.tree_today = ttk.Treeview(self.tree_inner_frame, columns=cols, show="headings", height=15)
        for c in cols:
            self.tree_today.heading(c, text=c)
            self.tree_today.column(c, anchor="center", width=160 if c == "Biển số" else 130)
        
        # Đặt Treeview trong frame với background màu trắng
        tree_container = tk.Frame(self.tree_inner_frame, highlightthickness=0)
        tree_container.pack(fill="both", expand=True)
        self.tree_today.pack(tree_container)
        
        self.reload_today_table()

    def reload_today_table(self):
        # Xóa các hàng hiện có
        for item in self.tree_today.get_children():
            self.tree_today.delete(item)
        
        # Đọc và hiển thị lại dữ liệu
        df = read_today_scans()
        for _, row in df.iterrows():
            self.tree_today.insert("", "end", values=[
                row.get("Ngày",""), 
                row.get("Biển số",""), 
                row.get("Trạng thái",""), 
                row.get("Thời gian vào",""), 
                row.get("Thời gian ra","")
            ])
        
        # Cập nhật thanh cuộn
        self.canvas_tab.update_idletasks()
        self.canvas_tab.configure(scrollregion=self.canvas_tab.bbox("all"))

    # ---- Tab Đăng ký xe ----
    def _build_tab_register(self):
        # Header
        header = tk.Frame(self.tab_register, bg="white", height=80)
        header.pack(fill="x", padx=10, pady=10)
        header.pack_propagate(False)
        
        tk.Label(header, text="Đăng ký xe", font=("Arial", 16, "bold"), 
                bg="white", fg="#2c3e50").pack(expand=True)
        
        # Form đăng ký
        form = tk.Frame(self.tab_register, bg="white", height=80, relief="ridge", bd=2)
        form.pack(fill="x", padx=10, pady=(0, 10))
        form.pack_propagate(False)
        
        tk.Label(form, text="Nhập biển số cần đăng ký:", 
                font=("Arial", 12), bg="white", fg="#34495e",
                padx=20, pady=20).pack(side="left")
        
        self.entry_reg = tk.Entry(form, width=24, font=("Arial", 12), bd=2)
        self.entry_reg.pack(side="left", padx=10)
        
        tk.Button(form, text="Thêm", width=10, height=2, 
                 command=self._add_registered_plate, bg="#27ae60", fg="white",
                 font=("Arial", 10, "bold")).pack(side="left", padx=6)
        
        tk.Button(form, text="Làm mới danh sách", width="14", height=2, 
                 command=self._reload_registered_table, bg="#3498db", fg="white",
                 font=("Arial", 10, "bold")).pack(side="left", padx=6)
        
        # Thanh công cụ bên dưới
        toolbar = tk.Frame(self.tab_register, bg="white", height=50)
        toolbar.pack(fill="x", padx=10, pady=(0, 10))
        
        # Nút xóa đã chọn
        tk.Button(toolbar, text="Xóa đã chọn", width=12, height=2, 
                 command=self._delete_selected_plates, bg="#e74c3c", fg="white",
                 font=("Arial", 10, "bold")).pack(side="left", padx=5, pady=5)
        
        # Khung danh sách biển số đã đăng ký
        tree_container = tk.Frame(self.tab_register, bg="white", relief="ridge", bd=2)
        tree_container.pack(fill="both", expand=True, padx=10)
        
        # Tạo Treeview với thanh cuộn
        self.tree_reg = ttk.Treeview(tree_container, columns=("Biển số",), show="tree headings", height=18)
        self.tree_reg.heading("#0", text="STT", anchor="center")
        self.tree_reg.heading("Biển số", text="Biển số", anchor="center")
        
        self.tree_reg.column("#0", width=60, anchor="center", stretch=False)
        self.tree_reg.column("Biển số", width=300, anchor="w", stretch=True)
        
        tree_scroll = ttk.Scrollbar(tree_container, orient="vertical", command=self.tree_reg.yview)
        self.tree_reg.configure(yscrollcommand=tree_scroll.set)
        
        self.tree_reg.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        
        # Thích với menu chuột phải
        self.tree_reg.bind("<Button-3>", self._show_context_menu)
        
        self._reload_registered_table()

    def _add_registered_plate(self):
        plate = self.entry_reg.get().strip().upper()
        if not plate:
            messagebox.showwarning("Thiếu dữ liệu", "Vui lòng nhập biển số.")
            return
        if append_registered(plate):
            messagebox.showinfo("Thành công", f"Đã thêm {plate} vào {Config.REGISTER_FILE_PATH}")
            self.entry_reg.delete(0, tk.END)
            self._reload_registered_table()
            self._refresh_registered_cache()
        else:
            messagebox.showwarning("Trùng", f"{plate} đã có trong danh sách đăng ký.")

    def _reload_registered_table(self):
        # Xóa các hàng hiện có
        self.tree_reg.delete(*self.tree_reg.get_children())
        
        # Thêm lại từ file
        plates = read_registered_list()
        for i, plate in enumerate(plates, 1):
            self.tree_reg.insert("", "end", text=str(i), values=(plate,))

    def _delete_selected_plates(self):
        # Lấy các item được chọn
        selected_items = self.tree_reg.selection()
        if not selected_items:
            messagebox.showinfo("Thông báo", "Vui lòng chọn ít nhất một biển số để xóa.")
            return
        
        # Xác nhận xóa
        if messagebox.askyesno("Xác nhận", f"Bạn có chắc chắn muốn xóa {len(selected_items)} biển số đã chọn không?"):
            plates_to_delete = []
            for item in selected_items:
                plate = self.tree_reg.item(item)["values"][0]
                plates_to_delete.append(plate)
            
            # Đọc danh sách hiện tại
            plates = read_registered_list()
            
            # Xóa các biển đã chọn
            new_plates = [p for p in plates if p not in plates_to_delete]
            
            # Ghi lại vào file
            with open(Config.REGISTER_FILE_PATH, "w", encoding="utf-8") as f:
                for p in new_plates:
                    f.write(p + "\n")
            
            # Làm mới lại giao diện
            self._reload_registered_table()
            self._refresh_registered_cache()
            messagebox.showinfo("Thành công", "Đã xóa các biển số đã chọn.")

    def _show_context_menu(self, event):
        # Tạo menu ngữ cảnh
        context_menu = tk.Menu(self, tearoff=0)
        context_menu.add_command(label="Xóa", command=self._delete_selected_plates)
        context_menu.add_separator()
        context_menu.add_command(label="Sao chép", command=lambda: self._copy_selected_plate(event))
        
        # Hiển thị menu tại vị trí chuột
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
            
    def _copy_selected_plate(self, event):
        selected_items = self.tree_reg.selection()
        if selected_items:
            plate = self.tree_reg.item(selected_items[0])["values"][0]
            # Sao chép vào clipboard
            self.clipboard_clear()
            self.clipboard_append(plate)
            messagebox.showinfo("Thông báo", f"Đã sao chép biển số: {plate}")

    # --------- HỦY ---------
    def destroy(self):
        # Kiểm tra đã đăng nhập chưa
        if hasattr(self, 'cap') and self.cap is not None:
            self.stop_camera()
        super().destroy()


if __name__ == "__main__":
    # Gợi ý cài đặt:
    # pip install opencv-python torch torchvision pandas openpyxl pillow pygame
    app = App()
    app.mainloop()