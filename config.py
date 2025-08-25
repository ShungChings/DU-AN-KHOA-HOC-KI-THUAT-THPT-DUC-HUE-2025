import os
import json
import torch
import pandas as pd
from datetime import datetime

# =============== CẤU HÌNH FILE ===============
SCAN_FILE = "scan_log.xlsx"      # Excel thống kê quét (có lịch sử nhiều ngày)
REGISTER_FILE = "registered.txt" # Danh sách đăng ký (TXT)
CONFIG_FILE = "config.json"     # File cấu hình thông tin đăng nhập và thời gian quét
CONFIG_SOUND = "sound_config.json" # File cấu hình âm thanh

os.makedirs(os.path.dirname(SCAN_FILE) or ".", exist_ok=True)
os.makedirs(os.path.dirname(REGISTER_FILE) or ".", exist_ok=True)

# Tạo file config.json nếu chưa có
if not os.path.exists(CONFIG_FILE):
    config_data = {
        "login_user": "admin",
        "login_pass": "123456",
        "scan_interval_in": 10,  # Khoảng thời gian (giây) để xác nhận xe vào
        "scan_interval_out": 20   # Khoảng thời gian (giây) để xác nhận xe ra
    }
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_data, f, indent=4)

# Tạo file cấu hình âm thanh nếu chưa có
if not os.path.exists(CONFIG_SOUND):
    sound_config = {
        "success_sound": "success.wav",
        "fail_sound": "fail.wav"
    }
    with open(CONFIG_SOUND, "w", encoding="utf-8") as f:
        json.dump(sound_config, f, indent=4)

# Đọc thông tin đăng nhập và cấu hình từ file config
try:
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config_data = json.load(f)
    
    class Config:
        # Các thuộc tính cấu hình
        LOGIN_USER = config_data.get("login_user", "admin")
        LOGIN_PASS = config_data.get("login_pass", "123456")
        SCAN_INTERVAL_IN = config_data.get("scan_interval_in", 10)
        SCAN_INTERVAL_OUT = config_data.get("scan_interval_out", 20)
        
        # Thêm các thuộc tính file
        SCAN_FILE_PATH = SCAN_FILE
        REGISTER_FILE_PATH = REGISTER_FILE
        CONFIG_FILE_PATH = CONFIG_FILE
        CONFIG_SOUND_PATH = CONFIG_SOUND
        
except Exception as e:
    print(f"Lỗi đọc config: {e}. Sử dụng giá trị mặc định.")
    
    class Config:
        # Giá trị mặc định cho các thuộc tính cấu hình
        LOGIN_USER = "admin"
        LOGIN_PASS = "123456"
        SCAN_INTERVAL_IN = 10
        SCAN_INTERVAL_OUT = 20
        
        # Giá trị mặc định cho các thuộc tính file
        SCAN_FILE_PATH = SCAN_FILE
        REGISTER_FILE_PATH = REGISTER_FILE
        CONFIG_FILE_PATH = CONFIG_FILE
        CONFIG_SOUND_PATH = CONFIG_SOUND

# Khởi tạo file excel nếu chưa có
if not os.path.exists(SCAN_FILE):
    pd.DataFrame(columns=["Ngày", "Biển số", "Trạng thái", "Thời gian vào", "Thời gian ra"]).to_excel(SCAN_FILE, index=False)

# Khởi tạo file txt nếu chưa có
if not os.path.exists(REGISTER_FILE):
    open(REGISTER_FILE, "w", encoding="utf-8").close()

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

# Đọc cấu hình âm thanh
try:
    with open(CONFIG_SOUND, "r", encoding="utf-8") as f:
        sound_config = json.load(f)
    
    SOUND_SUCCESS = sound_config.get("success_sound", "success.wav")
    SOUND_FAIL = sound_config.get("fail_sound", "fail.wav")
except Exception as e:
    print(f"Lỗi đọc cấu hình âm thanh: {e}. Sử dụng giá trị mặc định.")
    SOUND_SUCCESS = "success.wav"
    SOUND_FAIL = "fail.wav"