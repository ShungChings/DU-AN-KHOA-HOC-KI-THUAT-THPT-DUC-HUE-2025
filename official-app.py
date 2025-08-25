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

# =============== CẤU HÌNH BIẾN TOÀN CỤC ===============
# Khởi tạo biến toàn cục trước khi sử dụng
SCAN_INTERVAL_IN = 10  # Khoảng thời gian (giây) để xác nhận xe vào
SCAN_INTERVAL_OUT = 20  # Khoảng thời gian (giây) để xác nhận xe ra
LOGIN_USER = "admin"
LOGIN_PASS = "Duchue@123"
COOLDOWN_SECONDS = 5  # Tránh ghi trùng trong khoảng thời gian ngắn

# Thiết lập biến để tránh xung đột với các module khác
# Sử dụng tên riêng cho các widget để tránh xung đột
TFrame = tk.Frame
TLabel = tk.Label
TButton = tk.Button
TCanvas = tk.Canvas
TEntry = tk.Entry
TStringVar = tk.StringVar
TCombobox = ttk.Combobox

# Lấy đường dẫn thư mục hiện tại
current_dir = os.path.dirname(os.path.abspath(__file__))

# Khởi tạo pygame cho âm thanh
pygame.mixer.init()

# Tải file âm thanh
try:
    success_sound = os.path.join(current_dir, "success.wav")
    fail_sound = os.path.join(current_dir, "fail.wav")
    
    pygame.mixer.music.load(success_sound)  # Âm thanh khi quét thành công
    pygame.mixer.music.load(fail_sound)    # Âm thanh khi quét thất bại
    print("Đã tải thành công file âm thanh")
except Exception as e:
    print(f"Lỗi khi tải file âm thanh: {e}. Bỏ qua tính năng âm thanh.")
    success_sound = None
    fail_sound = None
# =============== CẤU HÌNH FILE ===============
SCAN_FILE = "scan_log.xlsx"      # Excel thống kê quét (có lịch sử nhiều ngày)
REGISTER_FILE = "registered.txt" # Danh sách đăng ký (TXT)
CONFIG_FILE = "config.json"     # File cấu hình thông tin đăng nhập và thời gian quét
CAMERAS_CONFIG_FILE = "cameras.json"  # File lưu trữ cấu hình các camera

os.makedirs(os.path.dirname(SCAN_FILE) or ".", exist_ok=True)
os.makedirs(os.path.dirname(REGISTER_FILE) or ".", exist_ok=True)

# Tạo file config.json nếu chưa có
if not os.path.exists(CONFIG_FILE):
    config_data = {
        "login_user": LOGIN_USER,
        "login_pass": LOGIN_PASS,
        "scan_interval_in": SCAN_INTERVAL_IN,
        "scan_interval_out": SCAN_INTERVAL_OUT,
        "default_camera": 0  # Mặc định là camera đầu tiên
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)

# Tạo file cameras.json nếu chưa có
if not os.path.exists(CAMERAS_CONFIG_FILE):
    cameras_data = {
        "cameras": [
            {"id": 0, "name": "Camera mặc định", "type": "usb", "enabled": True},
            {"id": 1, "name": "Camera USB 2", "type": "usb", "enabled": True}
        ],
        "last_used": 0,
        "ip_cameras": [
            {"id": "ip1", "name": "Camera IP 1", "address": "192.168.1.100:8080", "enabled": True},
            {"id": "ip2", "name": "Camera IP 2", "address": "192.168.1.101:8080", "enabled": True}
        ]
    }
    with open(CAMERAS_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cameras_data, f, indent=4)

# Đọc thông tin đăng nhập và cấu hình từ file config
try:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    # Cập nhật các biến toàn cục đã khởi tạo
    LOGIN_USER = config_data.get("login_user", LOGIN_USER)
    LOGIN_PASS = config_data.get("login_pass", LOGIN_PASS)
    SCAN_INTERVAL_IN = config_data.get("scan_interval_in", SCAN_INTERVAL_IN)
    SCAN_INTERVAL_OUT = config_data.get("scan_interval_out", SCAN_INTERVAL_OUT)
    default_camera = config_data.get("default_camera", 0)
except Exception as e:
    print(f"Lỗi đọc config: {e}. Sử dụng giá trị mặc định.")
    default_camera = 0

# Đữ liệu camera từ file cameras.json
try:
    with open(CAMERAS_CONFIG_FILE, "r", encoding="utf-8") as f:
        cameras_data = json.load(f)
    usb_cameras = cameras_data.get("cameras", [])
    ip_cameras = cameras_data.get("ip_cameras", [])
    last_used_camera = cameras_data.get("last_used", 0)
except Exception as e:
    print(f"Lỗi đọc cameras config: {e}. Sử dụng giá trị mặc định.")
    usb_cameras = [
        {"id": 0, "name": "Camera mặc định", "type": "usb", "enabled": True},
        {"id": 1, "name": "Camera USB 2", "type": "usb", "enabled": True}
    ]
    ip_cameras = [
        {"id": "ip1", "name": "Camera IP 1", "address": "192.168.1.100:8080", "enabled": True},
        {"id": "ip2", "name": "Camera IP 2", "address": "192.168.1.101:8080", "enabled": True}
    ]
    last_used_camera = 0

# Khởi tạo file excel nếu chưa có
if not os.path.exists(SCAN_FILE):
    pd.DataFrame(columns=["Ngày", "Biển số", "Trạng thái", "Thời gian vào", "Thời gian ra"]).to_excel(SCAN_FILE, index=False)
# Khởi tạo file txt nếu chưa có
if not os.path.exists(REGISTER_FILE):
    open(REGISTER_FILE, "w", encoding="utf-8").close()

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
    with open(REGISTER_FILE, "r", encoding="utf-8") as f:
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
    with open(REGISTER_FILE, "a", encoding="utf-8") as f:
        f.write(plate_raw.strip().upper() + "\n")
    return True

def read_registered_list() -> list:
    items = []
    with open(REGISTER_FILE, "r", encoding="utf-8") as f:
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

    df = pd.read_excel(SCAN_FILE)

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
    df.to_excel(SCAN_FILE, index=False)

def read_today_scans() -> pd.DataFrame:
    today = datetime.now().strftime("%Y-%m-%d")
    if not os.path.exists(SCAN_FILE):
        return pd.DataFrame(columns=["Ngày", "Biển số", "Trạng thái", "Thời gian vào", "Thời gian ra"])
    df = pd.read_excel(SCAN_FILE)
    if df.empty:
        return df
    return df[df["Ngày"] == today].copy()

# =============== YOLO MODEL (thay đường dẫn của bạn) ===============
# Lưu ý: cần có 'yolov5' sẵn (local hub), và 2 file weight theo dự án của bạn
# - model/LP_detector_nano_61.pt  (detect biển số)
# - model/LP_ocr_nano_62.pt       (OCR biển số)
try:
    yolo_LP_detect = torch.hub.load('yolov5', 'custom', path='model/LP_detector_nano_61.pt', force_reload=False, source='local')
    yolo_license_plate = torch.hub.load('yolov5', 'custom', path='model/LP_ocr_nano_62.pt', force_reload=False, source='local')
    yolo_license_plate.conf = 0.60
except Exception as e:
    yolo_LP_detect = None
    yolo_license_plate = None
    print("⚠️ Không load được YOLO models:", e)

# =============== HELPER DỰ ÁN (deskew + read_plate) ===============
# Import module function sau khi đã thêm đường dẫn
try:
    from function import utils_rotate
    from function import helper
except ImportError as e:
    print(f"Lỗi import module function: {e}")
    # Tạo các hàm giả để tránh lỗi
    class utils_rotate:
        @staticmethod
        def deskew(img, cc, ct):
            return img
    
    class helper:
        @staticmethod
        def read_plate(model, img):
            return "unknown"

# =============== BIẾN TOÀN CỤC CHO ỨNG DỤNG ===============
recent_seen = {}      # plate_norm -> last_time (epoch)
plate_status = {}     # plate_norm -> { "first_seen": timestamp, "status": "pending" }

# Phát âm thanh
# Hàm phát âm thanh đã sửa để xử lý trường hợp file âm thanh không tồn tại
def play_sound(success):
    """Phát âm thanh khi quét thành công hoặc thất bại"""
    global success_sound, fail_sound
    try:
        if success and success_sound:
            pygame.mixer.music.load(success_sound)
            pygame.mixer.music.play()
        elif not success and fail_sound:
            pygame.mixer.music.load(fail_sound)
            pygame.mixer.music.play()
            time.sleep(0.2)
            pygame.mixer.music.load(fail_sound)
            pygame.mixer.music.play()
    except Exception as e:
        print(f"Lỗi khi phát âm thanh: {e}")

# =============== CHỨC NĂNG CẬP NHẬT THÔNG TIN CẤU HÌNH ===============
def update_config():
    """Cập nhật file config với các giá trị mới"""
    config_data = {
        "login_user": LOGIN_USER,
        "login_pass": LOGIN_PASS,
        "scan_interval_in": SCAN_INTERVAL_IN,
        "scan_interval_out": SCAN_INTERVAL_OUT,
        "default_camera": app.camera_source if hasattr(app, 'camera_source') else 0
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)

def update_cameras_config():
    """Cập nhật file cameras.json với các giá trị mới"""
    global usb_cameras, ip_cameras
    
    # Xây dựng dữ liệu để lưu
    cameras_data = {
        "cameras": usb_cameras,
        "last_used": app.camera_source if hasattr(app, 'camera_source') else 0,
        "ip_cameras": ip_cameras
    }
    
    with open(CAMERAS_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cameras_data, f, indent=4)

def set_scan_intervals():
    """Mở cửa sổ để cài đặt thời gian quét vào/ra"""
    # Sử dụng các toàn cục đã được khai báo
    global SCAN_INTERVAL_IN, SCAN_INTERVAL_OUT
    
    # Tạo cửa sổ mới
    dialog = tk.Toplevel()
    dialog.title("Cài đặt thời gian quét")
    dialog.geometry("400x250")
    dialog.resizable(False, False)
    
    # Tạo frame chính
    main_frame = TFrame(dialog, bg="#f0f0f0", padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)
    
    # Tiêu đề
    TLabel(main_frame, text="Cài đặt thời gian quét", font=("Arial", 14, "bold"), 
           bg="#f0f0f0").pack(pady=(0, 20))
    
    # Nhập thời gian quét vào
    in_frame = TFrame(main_frame, bg="#f0f0f0")
    in_frame.pack(fill="x", pady=10)
    TLabel(in_frame, text="Thời gian chờ xác nhận xe vào (giây):", 
           font=("Arial", 10), bg="#f0f0f0", width=30, anchor="w").pack(side="left")
    in_entry = TEntry(in_frame, font=("Arial", 10), width=10)
    in_entry.pack(side="right")
    in_entry.insert(0, str(SCAN_INTERVAL_IN))
    
    # Nhập thời gian quét ra
    out_frame = TFrame(main_frame, bg="#f0f0f0")
    out_frame.pack(fill="x", pady=10)
    TLabel(out_frame, text="Thời gian chờ xác nhận xe ra (giây):", 
           font=("Arial", 10), bg="#f0f0f0", width=30, anchor="w").pack(side="left")
    out_entry = TEntry(out_frame, font=("Arial", 10), width=10)
    out_entry.pack(side="right")
    out_entry.insert(0, str(SCAN_INTERVAL_OUT))
    
    # Nút xác nhận
    def confirm():
        try:
            global SCAN_INTERVAL_IN, SCAN_INTERVAL_OUT
            SCAN_INTERVAL_IN = int(in_entry.get())
            SCAN_INTERVAL_OUT = int(out_entry.get())
            update_config()
            dialog.destroy()
            messagebox.showinfo("Thành công", "Đã cập nhật thời gian quét!")
        except ValueError:
            messagebox.showerror("Lỗi", "Vui lòng nhập số nguyên hợp lệ!")
    
    button_frame = TFrame(main_frame, bg="#f0f0f0")
    button_frame.pack(pady=20)
    TButton(button_frame, text="Xác nhận", command=confirm, 
            bg="#3498db", fg="white", font=("Arial", 10, "bold"), 
            padx=20, pady=5).pack(side="left", padx=10)
    TButton(button_frame, text="Hủy", command=dialog.destroy, 
            bg="#95a5a6", fg="white", font=("Arial", 10, "bold"), 
            padx=20, pady=5).pack(side="left")
    
    # Center dialog
    dialog.transient(app)
    dialog.grab_set()
    app.wait_window(dialog)

# =============== CHỨC NĂNG CHUYỂN CAMERA ===============
def scan_available_cameras():
    """Quét và phát hiện tất cả các camera có sẵn"""
    global usb_cameras
    available_cameras = []
    
    # Thử từ camera 0 đến 10
    for i in range(0, 11):
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            available_cameras.append({"id": i, "name": f"Camera USB {i+1}", "type": "usb", "enabled": True})
            cap.release()
    
    # Lấy danh sách các camera đã có trong cấu hình và kết hợp
    camera_ids = [cam["id"] for cam in available_cameras]
    
    # Cập nhật danh sách camera hiện tại
    updated_cameras = []
    for cam in available_cameras:
        # Tìm camera cũ trong danh sách (nếu có)
        for old_cam in usb_cameras:
            if old_cam["id"] == cam["id"]:
                # Giữ lại cấu hình cũ (nếu có)
                cam.update({k: v for k, v in old_cam.items() if k not in ["id", "name", "type", "enabled"]})
                break
        updated_cameras.append(cam)
    
    # Thêm các camera cũ không còn tồn tại
    for old_cam in usb_cameras:
        if old_cam["id"] not in camera_ids:
            updated_cameras.append(old_cam)
    
    # Cập nhật usb_cameras
    usb_cameras = updated_cameras
    
    # Lưu lại cấu hình
    update_cameras_config()
    
    return available_cameras

def switch_camera(camera_source):
    """Chuyển đổi camera"""
    global last_used_camera
    
    # Dừng camera hiện tại
    if hasattr(app, 'cap') and app.cap is not None:
        app.stop_camera()
    
    # Cập nhật camera nguồn
    app.camera_source = camera_source
    
    # Cập nhật cấu hình
    update_cameras_config()
    
    # Bật camera mới
    app.start_camera()
    return True

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

        # Khởi tạo đăng nhập trước
        self._build_login()

        # Biến camera
        self.cap = None
        self.camera_source = default_camera  # Mặc định camera đầu tiên
        self.prev_frame_time = 0
        self.registered_set = load_registered_set()
        self.canvas_tab = None  # Khởi tạo biến canvas_tab
        
        # Flag để kiểm tra đã đăng nhập
        self.logged_in = False

    # --------- LOGIN ---------
    def _build_login(self):
        # Tạo nền gradient
        self.canvas = TCanvas(self, width=1100, height=750, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Tạo màu gradient
        for i in range(10):
            # Sáng dần từ trên xuống dưới
            color_val = 255 - i*25
            if color_val < 200: color_val = 200
            color = f'#{color_val:02x}{color_val:02x}{color_val:02x}'
            self.canvas.create_rectangle(0, i*75, 1100, (i+1)*75, fill=color, outline=color)
        
        # Logo và form đăng nhập
        logo_frame = TFrame(self, bg="#f5f5f5")
        logo_frame.place(relx=0.5, rely=0.2, anchor="center")
        
        # Tải và hiển thị logo
        try:
            logo = Image.open("logo.png")  # Có thể thay thế bằng file logo thực tế
            logo = logo.resize((150, 150), Image.LANCZOS)
            logo_photo = ImageTk.PhotoImage(logo)
            logo_label = TFrame(logo_frame, bg="#f5f5f5")
            logo_label.pack(pady=10)
            TLabel(logo_label, image=logo_photo, bg="#f5f5f5")
            logo_label.image = logo_photo  # Giữ tham chiếu
        except:
            # Nếu không có file logo, hiển thị biểu tượng văn bản
            TLabel(logo_frame, text="🚗", font=("Arial", 80), bg="#f5f5f5").pack(pady=10)
        
        TLabel(logo_frame, text="HỆ THỐNG ĐIỂM DANH XE", 
               font=("Arial", 18, "bold"), bg="#f5f5f5", fg="#2c3e50").pack(pady=5)
        
        # Form đăng nhập
        login_container = TFrame(self, bg="white", relief="flat", bd=0)
        login_container.place(relx=0.5, rely=0.5, anchor="center")
        
        login_container_frame = TFrame(login_container, bg="white", relief="ridge", bd=2, padx=40, pady=40)
        login_container_frame.pack(padx=10, pady=10)
        
        TLabel(login_container_frame, text="Đăng nhập", 
               font=("Arial", 20, "bold"), bg="white", fg="#2c3e50").grid(row=0, column=0, columnspan=2, pady=20)
        
        TLabel(login_container_frame, text="Tài khoản", font=("Arial", 12), bg="white", fg="#34495e").grid(row=1, column=0, padx=8, pady=8, sticky="e")
        TLabel(login_container_frame, text="Mật khẩu", font=("Arial", 12), bg="white", fg="#34495e").grid(row=2, column=0, padx=8, pady=8, sticky="e")
        
        self.var_user = TStringVar()
        self.var_pass = TStringVar()
        
        e1 = tk.Entry(login_container_frame, textvariable=self.var_user, font=("Arial", 12), width=26)
        e2 = tk.Entry(login_container_frame, textvariable=self.var_pass, font=("Arial", 12), show="*", width=26)
        e1.grid(row=1, column=1, padx=8, pady=8)
        e2.grid(row=2, column=1, padx=8, pady=8)
        
        login_btn = TButton(login_container_frame, text="Đăng nhập", 
                            font=("Arial", 12, "bold"), bg="#27ae60", fg="white",
                            width=16, height=2, command=self._do_login)
        login_btn.grid(row=3, column=0, columnspan=2, pady=20)
        
        # Thêm văn bản bản quyền
        TLabel(login_container_frame, text="© 2023 Hệ thống điểm danh xe", 
               font=("Arial", 8), bg="white", fg="#95a5a6").grid(row=4, column=0, columnspan=2, pady=10)

    def _do_login(self):
        # Lấy giá trị và chuẩn hóa chuỗi
        username = self.var_user.get().strip()
        password = self.var_pass.get().strip()
        
        # Kiểm tra trống
        if not username or not password:
            messagebox.showerror("Lỗi", "Vui lòng nhập đầy đủ tài khoản và mật khẩu!")
            return
            
        # So sánh trực tiếp với thông tin đăng nhập đã được định nghĩa sẵn
        # In ra để kiểm tra
        print(f"Đang nhập: {username} / {password}")
        print(f"Đang so sánh với: {LOGIN_USER} / {LOGIN_PASS}")
        
        if username == LOGIN_USER and password == LOGIN_PASS:
            # Đăng nhập OK -> chuyển sang main UI
            self.logged_in = True
            try:
                # Xóa canvas đăng nhập
                self.canvas.destroy()
                
                # Tạo container mới
                container = TFrame(self, bg="#f5f5f5")
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
                
            except Exception as e:
                messagebox.showerror("Lỗi", f"Đã xảy ra lỗi khi chuyển sang giao diện chính: {e}")
                # Quay lại màn hình đăng nhập nếu có lỗi
                self.logged_in = False
                self._build_login()
        else:
            # Thông báo chi tiết hơn khi đăng nhập thất bại
            messagebox.showerror("Lỗi đăng nhập", 
                               f"Tài khoản hoặc mật khẩu không đúng!")

    # --------- MAIN UI (NOTEBOOK) ---------
    def _build_tab_camera(self):
        # Header
        header = TFrame(self.tab_camera, bg="white", height=80)
        header.pack(fill="x", padx=10, pady=10)
        header.pack_propagate(False)
        
        TLabel(header, text="Camera quét xe", font=("Arial", 16, "bold"), 
               bg="white", fg="#2c3e50").pack(expand=True)
        
        # Khung hiển thị camera
        camera_container = TFrame(self.tab_camera, bg="black", relief="ridge", bd=2)
        camera_container.pack(padx=10, pady=10, fill="both", expand=True)
        
        self.lbl_video = TLabel(camera_container, bd=0, bg="black")
        self.lbl_video.pack(fill="both", expand=True)
        
        # Thêm ô hiển thị biển số đang nhận diện
        self.plate_info_frame = TFrame(self.tab_camera, height=60, bg="#ecf0f1", relief="ridge", bd=2)
        self.plate_info_frame.pack(fill="x", padx=10, pady=5)
        self.plate_info_frame.pack_propagate(False)
        
        self.lbl_plate_info = TLabel(self.plate_info_frame, text="", 
                                    font=("Arial", 18, "bold"), bg="#ecf0f1", fg="#2c3e50")
        self.lbl_plate_info.pack(expand=True)
        
        # Status line
        self.status_bar = TFrame(self.tab_camera, bg="#34495e", height=35)
        self.status_bar.pack(fill="x", padx=10, pady=5)
        self.status_bar.pack_propagate(False)
        
        self.lbl_status = TLabel(self.status_bar, text="Trạng thái: Sẵn sàng", 
                                font=("Arial", 10), bg="#34495e", fg="white", anchor="w")
        self.lbl_status.pack(fill="x", padx=10, pady=5)
        
        # Nút điều khiển
        controls = TFrame(self.tab_camera, bg="#f5f5f5")
        controls.pack(pady=15, padx=10, fill="x")
        
        # Dùng màu sắc và font rõ ràng hơn
        TButton(controls, text="Bật camera", width=16, height=2, 
                command=self.start_camera, bg="#27ae60", fg="white", 
                font=("Arial", 11, "bold")).pack(side="left", padx=8)
        
        TButton(controls, text="Tắt camera", width=16, height=2, 
                command=self.stop_camera, bg="#e74c3c", fg="white", 
                font=("Arial", 11, "bold")).pack(side="left", padx=8)
        
        # Thêm nút chuyển camera
        self.camera_button = TButton(controls, text="Chuyển camera", width="16", height=2, 
                                    command=self._show_camera_selection, bg="#3498db", fg="white", 
                                    font=("Arial", 11, "bold"))
        self.camera_button.pack(side="left", padx=8)
        
        # Thêm nút quét camera
        TButton(controls, text="Quét camera", width="14", height=2, 
                command=self._scan_cameras, bg="#16a085", fg="white", 
                font=("Arial", 11, "bold")).pack(side="left", padx=8)
        
        TButton(controls, text="Làm mới DS đăng ký", width="18", height=2, 
                command=self._refresh_registered_cache, bg="#3498db", fg="white", 
                font=("Arial", 11, "bold")).pack(side="left", padx=8)
        
        # Nút cài đặt thời gian quét
        TButton(controls, text="Cài đặt thời gian quét", width="16", height=2, 
                command=set_scan_intervals, bg="#9b59b6", fg="white", 
                font=("Arial", 11, "bold")).pack(side="left", padx=8)
        
        # Thêm thông tin cấu hình
        config_frame = TFrame(self.tab_camera, bg="#f5f5f5")
        config_frame.pack(fill="x", padx=10, pady=5)
        
        TLabel(config_frame, text=f"Cấu hình: Thời gian quét vào: {SCAN_INTERVAL_IN} giây, Thời gian quét ra: {SCAN_INTERVAL_OUT} giây", 
               font=("Arial", 10), bg="#f5f5f5", fg="#7f8c8d").pack(anchor="w")

    def _scan_cameras(self):
        """Quét và phát hiện các camera có sẵn"""
        # Hiển thị thông báo đang quét
        self.lbl_status.config(text="Trạng thái: Đang quét các camera...")
        self.update()
        
        # Quét các camera USB
        available_cameras = scan_available_cameras()
        
        # Hiển thị thông báo kết quả
        if available_cameras:
            messagebox.showinfo("Quét camera", f"Đã phát hiện {len(available_cameras)} camera USB:\n" + 
                              "\n".join([cam["name"] for cam in available_cameras]))
        else:
            messagebox.showwarning("Quét camera", "Không phát hiện camera nào!")
        
        # Cập nhật lại trạng thái
        self.lbl_status.config(text=f"Trạng thái: Sẵn sàng (Camera: {self.camera_source})")
        
        # Làm mới danh sách camera
        self._update_camera_list()

    def _update_camera_list(self):
        """Cập nhật danh sách camera trong combobox"""
        # Xóa mục hiện tại
        self.camera_box['values'] = []
        
        # Tạo danh sách camera mới
        camera_list = []
        
        # Thêm các camera USB
        for cam in usb_cameras:
            if cam["enabled"]:
                camera_list.append(f"USB - {cam['name']}")
        
        # Thêm các camera IP
        for cam in ip_cameras:
            if cam["enabled"]:
                camera_list.append(f"IP - {cam['name']}")
        
        # Cập nhật danh sách
        self.camera_box['values'] = camera_list
        
        # Cập nhật camera hiện tại (nó sẽ tồn tại)
        current_camera_name = "Camera mặc định"
        if isinstance(self.camera_source, str) and self.camera_source.startswith("rtsp"):
            # Camera IP
            for cam in ip_cameras:
                if cam["enabled"] and cam["address"] in self.camera_source:
                    current_camera_name = f"IP - {cam['name']}"
                    break
        elif isinstance(self.camera_source, int):
            # Camera USB
            for cam in usb_cameras:
                if cam["enabled"] and cam["id"] == self.camera_source:
                    current_camera_name = f"USB - {cam['name']}"
                    break
        
        # Thiết lập camera hiện tại
        try:
            current_index = camera_list.index(current_camera_name)
            self.camera_box.current(current_index)
        except ValueError:
            # Không tìm thấy camera hiện tại, đặt về mặc định
            self.camera_box.current(0)

    def _show_camera_selection(self):
        """Hiển thị cửa sổ chọn camera"""
        dialog = tk.Toplevel()
        dialog.title("Chọn camera")
        dialog.geometry("550x450")
        dialog.resizable(False, False)
        
        # Tạo frame chính
        main_frame = TFrame(dialog, bg="#f0f0f0", padx=20, pady=20)
        main_frame.pack(fill="both", expand=True)
        
        # Tiêu đề
        TLabel(main_frame, text="Chọn nguồn camera", font=("Arial", 14, "bold"), 
               bg="#f0f0f0").pack(pady=(0, 20))
        
        # Tạo notebook để phân loại camera
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill="both", expand=True)
        
        # Tab camera USB
        tab_usb = TFrame(notebook, bg="#f0f0f0")
        notebook.add(tab_usb, text="Camera USB")
        
        # Tab camera IP
        tab_ip = TFrame(notebook, bg="#f0f0f0")
        notebook.add(tab_ip, text="Camera IP")
        
        # Tab thêm camera mới
        tab_add = TFrame(notebook, bg="#f0f0f0")
        notebook.add(tab_add, text="Thêm mới")
        
        # ---- Camera USB ----
        usb_label = TLabel(tab_usb, text="Danh sách camera USB:", font=("Arial", 12), bg="#f0f0f0")
        usb_label.pack(anchor="w", pady=(10, 5))
        
        # Tạo frame chứa danh sách camera USB
        usb_list_frame = TFrame(tab_usb, bg="white", relief="ridge", bd=1)
        usb_list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Tạo frame header
        usb_header = TFrame(usb_list_frame, bg="#34495e", height=30)
        usb_header.pack(fill="x")
        usb_header.pack_propagate(False)
        
        TLabel(usb_header, text="STT", font=("Arial", 10, "bold"), 
               bg="#34495e", fg="white", width=5).pack(side="left", padx=5)
        TLabel(usb_header, text="Tên camera", font=("Arial", 10, "bold"), 
               bg="#34495e", fg="white").pack(side="left", fill="x", expand=True, padx=5)
        TLabel(usb_header, text="ID", font=("Arial", 10, "bold"), 
               bg="#34495e", fg="white", width=5).pack(side="left", padx=5)
        
        # Thêm danh sách camera USB
        usb_items = []
        if usb_cameras:
            for i, cam in enumerate(usb_cameras):
                if cam["enabled"]:
                    item_frame = TFrame(usb_list_frame, bg="white", height=30)
                    item_frame.pack(fill="x", pady=1)
                    
                    # Radio button để chọn camera
                    var = tk.IntVar()
                    if cam["id"] == self.camera_source:
                        var.set(cam["id"])
                    
                    rb = tk.Radiobutton(item_frame, variable=var, value=cam["id"], 
                                       bg="white", command=lambda c=cam: self._select_usb_camera(c))
                    rb.pack(side="left", padx=5)
                    
                    # Tên camera
                    label = TLabel(item_frame, text=cam["name"], font=("Arial", 10), 
                                  bg="white", anchor="w")
                    label.pack(side="left", fill="x", expand=True, padx=5)
                    
                    # ID camera
                    id_label = TLabel(item_frame, text=str(cam["id"]), font=("Arial", 10), 
                                    bg="white", width=5)
                    id_label.pack(side="left", padx=5)
                    
                    usb_items.append(item_frame)
        
        if not usb_items:
            TLabel(usb_list_frame, text="Không tìm thấy camera USB nào.", 
                  font=("Arial", 10), bg="white", fg="#95a5a6").pack(pady=20)
        
        # ---- Camera IP ----
        ip_label = TLabel(tab_ip, text="Danh sách camera IP:", font=("Arial", 12), bg="#f0f0f0")
        ip_label.pack(anchor="w", pady=(10, 5))
        
        # Tạo frame chứa danh sách camera IP
        ip_list_frame = TFrame(tab_ip, bg="white", relief="ridge", bd=1)
        ip_list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Tạo frame header
        ip_header = TFrame(ip_list_frame, bg="#34495e", height=30)
        ip_header.pack(fill="x")
        ip_header.pack_propagate(False)
        
        TLabel(ip_header, text="STT", font=("Arial", 10, "bold"), 
               bg="#34495e", fg="white", width=5).pack(side="left", padx=5)
        TLabel(ip_header, text="Tên camera", font=("Arial", 10, "bold"), 
               bg="#34495e", fg="white").pack(side="left", fill="x", expand=True, padx=5)
        TLabel(ip_header, text="Địa chỉ", font=("Arial", 10, "bold"), 
               bg="#34495e", fg="white", width=15).pack(side="left", padx=5)
        
        # Thêm danh sách camera IP
        ip_items = []
        if ip_cameras:
            for i, cam in enumerate(ip_cameras):
                if cam["enabled"]:
                    item_frame = TFrame(ip_list_frame, bg="white", height=30)
                    item_frame.pack(fill="x", pady=1)
                    
                    # Radio button để chọn camera
                    var = tk.StringVar()
                    if cam["id"] == self.camera_source or (isinstance(self.camera_source, str) and cam["address"] in self.camera_source):
                        var.set(cam["id"])
                    
                    rb = tk.Radiobutton(item_frame, variable=var, value=cam["id"], 
                                       bg="white", command=lambda c=cam: self._select_ip_camera(c))
                    rb.pack(side="left", padx=5)
                    
                    # Tên camera
                    label = TLabel(item_frame, text=cam["name"], font=("Arial", 10), 
                                  bg="white", anchor="w")
                    label.pack(side="left", fill="x", expand=True, padx=5)
                    
                    # Địa chỉ
                    addr_label = TLabel(item_frame, text=cam["address"], font=("Arial", 10), 
                                      bg="white", width=15)
                    addr_label.pack(side="left", padx=5)
                    
                    ip_items.append(item_frame)
        
        if not ip_items:
            TLabel(ip_list_frame, text="Không tìm thấy camera IP nào.", 
                  font=("Arial", 10), bg="white", fg="#95a5a6").pack(pady=20)
        
        # ---- Thêm camera mới ----
        add_frame = TFrame(tab_add, bg="#f0f0f0")
        add_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Chọn loại camera
        type_label = TLabel(add_frame, text="Loại camera:", font=("Arial", 11, "bold"), bg="#f0f0f0")
        type_label.pack(anchor="w", pady=(10, 5))
        
        self.camera_type_var = tk.StringVar(value="usb")
        type_frame = TFrame(add_frame, bg="#f0f0f0")
        type_frame.pack(fill="x", pady=5)
        
        tk.Radiobutton(type_frame, text="Camera USB", variable=self.camera_type_var, 
                       value="usb", bg="#f0f0f0").pack(side="left", padx=10)
        tk.Radiobutton(type_frame, text="Camera IP", variable=self.camera_type_var, 
                       value="ip", bg="#f0f0f0").pack(side="left", padx=10)
        
        # Input cho thông tin camera
        input_frame = TFrame(add_frame, bg="white", relief="ridge", bd=1, padx=20, pady=20)
        input_frame.pack(fill="x", pady=20)
        
        # Tên camera
        name_label = TLabel(input_frame, text="Tên camera:", font=("Arial", 10), bg="white")
        name_label.grid(row=0, column=0, sticky="w", pady=5)
        
        self.camera_name_var = tk.StringVar()
        name_entry = tk.Entry(input_frame, textvariable=self.camera_name_var, font=("Arial", 10), width=30)
        name_entry.grid(row=0, column=1, padx=10, pady=5)
        
        # ID/Địa chỉ camera
        id_label = TLabel(input_frame, text="ID camera:", font=("Arial", 10), bg="white")
        id_label.grid(row=1, column=0, sticky="w", pady=5)
        
        self.camera_id_var = tk.IntVar()
        id_entry = tk.Entry(input_frame, textvariable=self.camera_id_var, font=("Arial", 10), width=10)
        id_entry.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        
        # Sự kiện thay đổi loại camera
        def on_camera_type_change(*args):
            if self.camera_type_var.get() == "ip":
                # Cập nhật label và input cho camera IP
                id_label.config(text="Địa chỉ IP:")
                id_entry.config(width=20)
                self.camera_id_var.set("")
                self.camera_id_var = tk.StringVar()
                id_entry.config(textvariable=self.camera_id_var)
            else:
                # Cập nhật label và input cho camera USB
                id_label.config(text="ID camera:")
                id_entry.config(width=10)
                self.camera_id_var = tk.IntVar()
                id_entry.config(textvariable=self.camera_id_var)
        
        self.camera_type_var.trace_add("write", on_camera_type_change)
        
        # Nút thêm camera
        add_button_frame = TFrame(add_frame, bg="#f0f0f0")
        add_button_frame.pack(fill="x", pady=20)
        
        TButton(add_button_frame, text="Thêm camera", 
                command=lambda: self._add_new_camera(dialog), 
                bg="#27ae60", fg="white", font=("Arial", 10, "bold"), 
                padx=20, pady=5).pack(side="left", padx=5)
        
        TButton(add_button_frame, text="Đóng", 
                command=dialog.destroy, 
                bg="#95a5a6", fg="white", font=("Arial", 10, "bold"), 
                padx=20, pady=5).pack(side="left", padx=5)
        
        # Center dialog
        dialog.transient(self)
        dialog.grab_set()
        self.wait_window(dialog)
    
    def _select_usb_camera(self, camera):
        """Chọn camera USB"""
        # Dừng camera hiện tại
        if hasattr(self, 'cap') and self.cap is not None:
            self.stop_camera()
        
        # Thiết lập camera mới
        self.camera_source = camera["id"]
        
        # Bật camera mới
        self.start_camera()
        
        # Cập nhật cấu hình
        update_cameras_config()
        
        # Đóng dialog
        self._show_selection_success(f"Đã chuyển sang camera: {camera['name']}")
    
    def _select_ip_camera(self, camera):
        """Chọn camera IP"""
        # Dừng camera hiện tại
        if hasattr(self, 'cap') and self.cap is not None:
            self.stop_camera()
        
        # Tạo URL cho camera IP
        ip_url = f"rtsp://{camera['address']}/stream"
        
        # Thiết lập camera mới
        self.camera_source = ip_url
        
        # Bật camera mới
        self.start_camera()
        
        # Cập nhật cấu hình
        update_cameras_config()
        
        # Đóng dialog
        self._show_selection_success(f"Đã chuyển sang camera: {camera['name']} ({camera['address']})")
    
    def _add_new_camera(self, dialog):
        """Thêm camera mới"""
        camera_type = self.camera_type_var.get()
        camera_name = self.camera_name_var.get().strip()
        
        if not camera_name:
            messagebox.showerror("Lỗi", "Vui lòng nhập tên camera!")
            return
        
        if camera_type == "usb":
            camera_id = self.camera_id_var.get()
            if not isinstance(camera_id, int) or camera_id < 0:
                messagebox.showerror("Lỗi", "ID camera không hợp lệ!")
                return
            
            # Kiểm tra camera đã tồn tại
            for cam in usb_cameras:
                if cam["id"] == camera_id:
                    messagebox.showerror("Lỗi", f"ID camera {camera_id} đã tồn tại!")
                    return
            
            # Thêm camera mới
            usb_cameras.append({
                "id": camera_id,
                "name": camera_name,
                "type": "usb",
                "enabled": True
            })
            
            messagebox.showinfo("Thành công", f"Đã thêm camera USB: {camera_name} (ID: {camera_id})")
        else:
            camera_address = self.camera_id_var.get().strip()
            
            # Kiểm tra định dạng địa chỉ
            if not self._is_valid_ip_address(camera_address):
                messagebox.showerror("Lỗi", "Địa chỉ IP không hợp lệ!")
                return
            
            # Thêm cổng mặc định nếu không có
            if ":" not in camera_address:
                camera_address += ":8080"
            
            # Kiểm tra camera đã tồn tại
            for cam in ip_cameras:
                if cam["address"] == camera_address:
                    messagebox.showerror("Lỗi", f"Camera với địa chỉ {camera_address} đã tồn tại!")
                    return
            
            # Tạo ID duy nhất
            camera_id = f"ip{len(ip_cameras) + 1}"
            
            # Thêm camera mới
            ip_cameras.append({
                "id": camera_id,
                "name": camera_name,
                "address": camera_address,
                "enabled": True
            })
            
            messagebox.showinfo("Thành công", f"Đã thêm camera IP: {camera_name} ({camera_address})")
        
        # Lưu cấu hình
        update_cameras_config()
        
        # Đóng dialog
        dialog.destroy()
        
        # Mở lại dialog để hiển thị camera vừa thêm
        self._show_camera_selection()
    
    def _show_selection_success(self, message):
        """Hiển thị thông báo thành công khi chọn camera"""
        messagebox.showinfo("Thành công", message)
        
        # Cập nhật giao diện camera
        self.lbl_status.config(text=f"Trạng thái: Đã chuyển camera")
        
        # Làm mới danh sách camera
        self._update_camera_list()
    
    def _is_valid_ip_address(self, address):
        """Kiểm tra xem chuỗi có phải là địa chỉ IP hợp lệ không"""
        try:
            # Kiểm tra có cổng hay không
            if ":" in address:
                ip_part, port_part = address.split(":", 1)
                ip_parts = ip_part.split(".")
                
                # Kiểm tra cổng
                try:
                    port = int(port_part)
                    if port < 1 or port > 65535:
                        return False
                except ValueError:
                    return False
            else:
                ip_parts = address.split(".")
            
            # Kiểm tra IP
            if len(ip_parts) != 4:
                return False
            
            for part in ip_parts:
                if not 0 <= int(part) <= 255:
                    return False
            
            return True
        except ValueError:
            return False

    def _refresh_registered_cache(self):
        self.registered_set = load_registered_set()
        messagebox.showinfo("Thông báo", "Đã tải lại danh sách đăng ký (TXT).")

    def start_camera(self):
        if yolo_LP_detect is None or yolo_license_plate is None:
            messagebox.showerror("Lỗi", "Model YOLO chưa sẵn sàng!")
            return
        if self.cap is None:
            # Tùy theo nguồn camera
            if isinstance(self.camera_source, str) and self.camera_source.startswith("rtsp"):
                # Camera IP
                self.cap = cv2.VideoCapture(self.camera_source)
            else:
                # Camera mặc định hoặc USB
                self.cap = cv2.VideoCapture(self.camera_source, cv2.CAP_DSHOW)
            
            if not self.cap.isOpened():
                self.cap.release()
                self.cap = None
                messagebox.showerror("Lỗi", "Không mở được camera!")
                return
        self.lbl_status.config(text="Trạng thái: Camera đang chạy (nhấn Tắt camera để dừng)")
        self._update_frame()

    def stop_camera(self):
        self.lbl_status.config(text=f"Trạng thái: Đã tắt camera (Camera: {self.camera_source})")
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
                            
                            if time_diff >= SCAN_INTERVAL_IN and plate_status[plate_norm]["status"] == "pending":
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
                            
                            elif time_diff >= SCAN_INTERVAL_OUT and plate_status[plate_norm]["status"] == "in":
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
        
        # Tạo Treeview trực tiếp trong scrollable_frame
        self.tree_today = ttk.Treeview(scrollable_frame, columns=cols, show="headings", height=15)
        for c in cols:
            self.tree_today.heading(c, text=c)
            self.tree_today.column(c, anchor="center", width=160 if c == "Biển số" else 130)
        
        # Pack Treeview vào scrollable_frame
        self.tree_today.pack(fill="both", expand=True)
        
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
        
        # Cập nhật thanh cuộn - sửa lỗi object of type 'frame' has no len()
        if hasattr(self, "canvas_tab") and self.canvas_tab:
            try:
                # Sử dụng bbox thay vì len
                bbox = self.canvas_tab.bbox("all")
                if bbox:
                    self.canvas_tab.configure(scrollregion=bbox)
            except Exception as e:
                print(f"Lỗi khi cập nhật thanh cuộn: {e}")

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
        tk.Button(toolbar, text="Xóa đã chọn", width="12", height=2, 
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
        
        # Pack Treeview và thanh cuộn vào tree_container
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
            messagebox.showinfo("Thành công", f"Đã thêm {plate} vào {REGISTER_FILE}")
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
            with open(REGISTER_FILE, "w", encoding="utf-8") as f:
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