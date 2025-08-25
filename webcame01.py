import os
import time
from datetime import datetime

import cv2
import torch
import pandas as pd
from PIL import Image, ImageTk

import tkinter as tk
from tkinter import ttk, messagebox

# =============== CẤU HÌNH FILE ===============
SCAN_FILE = "scan_log.xlsx"      # Excel thống kê quét (có lịch sử nhiều ngày)
REGISTER_FILE = "registered.txt" # Danh sách đăng ký (TXT)

os.makedirs(os.path.dirname(SCAN_FILE) or ".", exist_ok=True)
os.makedirs(os.path.dirname(REGISTER_FILE) or ".", exist_ok=True)

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
def save_scan_to_excel(plate_raw: str, status_text: str):
    """Ghi vào Excel:
       - Nếu cùng NGÀY và biển số đã có -> cập nhật 'Thời gian ra' (nếu đang trống)
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
            if pd.isna(df.at[idx, "Thời gian ra"]) or df.at[idx, "Thời gian ra"] in [None, "", "nan"]:
                df.at[idx, "Thời gian ra"] = now_time
                updated = True
                break
        if not updated:
            # đã có bản ghi vào/ra đầy đủ -> thêm bản ghi mới (lần vào tiếp theo)
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
# Bạn đã có 2 module này trong project gốc
import function.utils_rotate as utils_rotate
import function.helper as helper

# =============== ỨNG DỤNG TKINTER ===============
LOGIN_USER = "admin"
LOGIN_PASS = "123456"

COOLDOWN_SECONDS = 5  # tránh ghi trùng trong khoảng thời gian ngắn
recent_seen = {}      # plate_norm -> last_time (epoch)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Hệ thống điểm danh xe")
        self.geometry("1100x750")
        self.resizable(False, False)

        # Khởi tạo đăng nhập trước
        self._build_login()

        # Biến camera
        self.cap = None
        self.prev_frame_time = 0
        self.registered_set = load_registered_set()

    # --------- LOGIN ---------
    def _build_login(self):
        self.login_frame = tk.Frame(self, bg="#ecf0f1")
        self.login_frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        tk.Label(self.login_frame, text="🔑 Đăng nhập", font=("Arial", 20, "bold"), bg="#ecf0f1", fg="#2c3e50").pack(pady=30)

        form = tk.Frame(self.login_frame, bg="#ecf0f1")
        form.pack()

        tk.Label(form, text="Tài khoản", bg="#ecf0f1", font=("Arial", 12)).grid(row=0, column=0, padx=8, pady=8, sticky="e")
        tk.Label(form, text="Mật khẩu", bg="#ecf0f1", font=("Arial", 12)).grid(row=1, column=0, padx=8, pady=8, sticky="e")

        self.var_user = tk.StringVar()
        self.var_pass = tk.StringVar()

        e1 = tk.Entry(form, textvariable=self.var_user, font=("Arial", 12), width=26)
        e2 = tk.Entry(form, textvariable=self.var_pass, font=("Arial", 12), show="*", width=26)
        e1.grid(row=0, column=1, padx=8, pady=8)
        e2.grid(row=1, column=1, padx=8, pady=8)

        tk.Button(self.login_frame, text="Đăng nhập", font=("Arial", 12, "bold"), bg="#27ae60", fg="white",
                  width=16, command=self._do_login).pack(pady=20)

    def _do_login(self):
        if self.var_user.get() == LOGIN_USER and self.var_pass.get() == LOGIN_PASS:
            # Đăng nhập OK -> chuyển sang main UI
            self.login_frame.destroy()
            self._build_main_ui()
        else:
            messagebox.showerror("Lỗi", "Sai tài khoản hoặc mật khẩu!")

    # --------- MAIN UI (NOTEBOOK) ---------
    def _build_main_ui(self):
        self.notebook = ttk.Notebook(self)
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

    # ---- Tab Camera ----
    def _build_tab_camera(self):
        # Khung hiển thị camera
        self.lbl_video = tk.Label(self.tab_camera, bd=2, relief="groove")
        self.lbl_video.pack(padx=10, pady=10)

        # Status line
        self.lbl_status = tk.Label(self.tab_camera, text="Trạng thái: Sẵn sàng", anchor="w")
        self.lbl_status.pack(fill="x", padx=10)

        # Nút điều khiển
        controls = tk.Frame(self.tab_camera)
        controls.pack(pady=5)
        tk.Button(controls, text="Bật camera", width=16, command=self.start_camera).grid(row=0, column=0, padx=8)
        tk.Button(controls, text="Tắt camera", width=16, command=self.stop_camera).grid(row=0, column=1, padx=8)
        tk.Button(controls, text="Làm mới DS đăng ký", width=18, command=self._refresh_registered_cache).grid(row=0, column=2, padx=8)

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

    def _update_frame(self):
        if self.cap is None:
            return

        ok, frame = self.cap.read()
        if not ok:
            self.stop_camera()
            return

        # YOLO detect biển số
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
                # cooldown để tránh spam
                now = time.time()
                last = recent_seen.get(plate_norm, 0)
                if now - last >= COOLDOWN_SECONDS:
                    recent_seen[plate_norm] = now

                    is_registered = plate_norm in self.registered_set
                    status_text = "ĐẠT" if is_registered else "KHÔNG ĐẠT"
                    color = (0, 255, 0) if is_registered else (0, 0, 255)

                    # Lưu Excel (vào/ra)
                    save_scan_to_excel(found_text, "ĐÃ ĐĂNG KÝ" if is_registered else "CHƯA ĐĂNG KÝ")

                    # Vẽ label
                    cv2.putText(frame, f"{found_text} ({status_text})", (x1, max(25, y1 - 10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

        # FPS
        new_t = time.time()
        fps = 0 if self.prev_frame_time == 0 else 1 / (new_t - self.prev_frame_time)
        self.prev_frame_time = new_t
        cv2.putText(frame, f"FPS: {int(fps)}", (7, 35), cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 255, 0), 2)

        # Hiển thị lên Tkinter
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        im = Image.fromarray(frame_rgb)
        imgtk = ImageTk.PhotoImage(image=im)
        self.lbl_video.imgtk = imgtk
        self.lbl_video.configure(image=imgtk)

        # Lặp
        self.after(10, self._update_frame)

    # ---- Tab Danh sách hôm nay ----
    def _build_tab_today(self):
        topbar = tk.Frame(self.tab_today)
        topbar.pack(fill="x", pady=6)

        tk.Button(topbar, text="Làm mới", width=12, command=self.reload_today_table).pack(side="left", padx=6)
        tk.Label(topbar, text="(Dữ liệu lấy từ Excel)").pack(side="left")

        cols = ("Ngày", "Biển số", "Trạng thái", "Thời gian vào", "Thời gian ra")
        self.tree_today = ttk.Treeview(self.tab_today, columns=cols, show="headings")
        for c in cols:
            self.tree_today.heading(c, text=c)
            self.tree_today.column(c, anchor="center", width=160 if c == "Biển số" else 130)
        self.tree_today.pack(fill="both", expand=True, padx=10, pady=8)

        self.reload_today_table()

    def reload_today_table(self):
        df = read_today_scans()
        # clear
        for i in self.tree_today.get_children():
            self.tree_today.delete(i)
        # fill
        for _, row in df.iterrows():
            self.tree_today.insert("", "end", values=[row.get("Ngày",""), row.get("Biển số",""),
                                                      row.get("Trạng thái",""), row.get("Thời gian vào",""),
                                                      row.get("Thời gian ra","")])

    # ---- Tab Đăng ký xe ----
    def _build_tab_register(self):
        form = tk.Frame(self.tab_register)
        form.pack(fill="x", pady=10)

        tk.Label(form, text="Nhập biển số cần đăng ký:").pack(side="left", padx=8)
        self.entry_reg = tk.Entry(form, width=24, font=("Arial", 12))
        self.entry_reg.pack(side="left", padx=6)

        tk.Button(form, text="Thêm", width=10, command=self._add_registered_plate).pack(side="left", padx=6)
        tk.Button(form, text="Làm mới danh sách", command=self._reload_registered_table).pack(side="left", padx=6)

        self.tree_reg = ttk.Treeview(self.tab_register, columns=("Biển số",), show="headings", height=18)
        self.tree_reg.heading("Biển số", text="Biển số")
        self.tree_reg.column("Biển số", anchor="center", width=300)
        self.tree_reg.pack(fill="both", expand=True, padx=10, pady=8)

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
        for i in self.tree_reg.get_children():
            self.tree_reg.delete(i)
        for p in read_registered_list():
            self.tree_reg.insert("", "end", values=(p,))

    # --------- HỦY ---------
    def destroy(self):
        self.stop_camera()
        super().destroy()


if __name__ == "__main__":
    # Gợi ý cài đặt:
    # pip install opencv-python torch torchvision pandas openpyxl pillow
    app = App()
    app.mainloop()
