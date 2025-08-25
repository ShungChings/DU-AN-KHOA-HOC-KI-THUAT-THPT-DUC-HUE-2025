import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import os
import sys

# Thêm đường dẫn hiện tại vào sys.path để import module function
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

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

class LoginApp(tk.Toplevel):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.parent = parent
        self.config = config
        self.title("Đăng nhập hệ thống")
        self.geometry("500x400")
        self.resizable(False, False)
        
        # Thiết lập biến
        self.var_user = tk.StringVar()
        self.var_pass = tk.StringVar()
        self.logged_in = False
        
        # Xây dựng giao diện
        self._build_ui()
        
        # Lấy focus vào cửa sổ
        self.transient(parent)
        self.grab_set()
        self.wait_window(self)
        
    def _build_ui(self):
        # Tạo nền gradient
        self.canvas = tk.Canvas(self, width=500, height=400, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Tạo màu gradient
        for i in range(10):
            # Sáng dần từ trên xuống dưới
            color_val = 255 - i*25
            if color_val < 200: color_val = 200
            color = f'#{color_val:02x}{color_val:02x}{color_val:02x}'
            self.canvas.create_rectangle(0, i*40, 500, (i+1)*40, fill=color, outline=color)
        
        # Logo và form đăng nhập
        logo_frame = tk.Frame(self, bg="#f5f5f5")
        logo_frame.place(relx=0.5, rely=0.2, anchor="center")
        
        # Tải và hiển thị logo
        try:
            logo = Image.open("logo.png")  # Có thể thay thế bằng file logo thực tế
            logo = logo.resize((150, 150), Image.LANCZOS)
            logo_photo = ImageTk.PhotoImage(logo)
            logo_label = tk.Frame(logo_frame, bg="#f5f5f5")
            logo_label.pack(pady=10)
            tk.Label(logo_label, image=logo_photo, bg="#f5f5f5")
            logo_label.image = logo_photo  # Giữ tham chiếu
        except:
            # Nếu không có file logo, hiển thị biểu tượng văn bản
            tk.Label(logo_frame, text="🚗", font=("Arial", 80), bg="#f5f5f5").pack(pady=10)
        
        tk.Label(logo_frame, text="HỆ THỐNG ĐIỂM DANH XE", 
                font=("Arial", 18, "bold"), bg="#f5f5f5", fg="#2c3e50").pack(pady=5)
        
        # Form đăng nhập
        login_container = tk.Frame(self, bg="white", relief="flat", bd=0)
        login_container.place(relx=0.5, rely=0.5, anchor="center")
        
        login_container_frame = tk.Frame(login_container, bg="white", relief="ridge", bd=2, padx=40, pady=40)
        login_container_frame.pack(padx=10, pady=10)
        
        tk.Label(login_container_frame, text="Đăng nhập", 
                font=("Arial", 20, "bold"), bg="white", fg="#2c3e50").grid(row=0, column=0, columnspan=2, pady=20)
        
        tk.Label(login_container_frame, text="Tài khoản", font=("Arial", 12), bg="white", fg="#34495e").grid(row=1, column=0, padx=8, pady=8, sticky="e")
        tk.Label(login_container_frame, text="Mật khẩu", font=("Arial", 12), bg="white", fg="#34495e").grid(row=2, column=0, padx=8, pady=8, sticky="e")
        
        e1 = tk.Entry(login_container_frame, textvariable=self.var_user, font=("Arial", 12), width=26)
        e2 = tk.Entry(login_container_frame, textvariable=self.var_pass, font=("Arial", 12), show="*", width=26)
        e1.grid(row=1, column=1, padx=8, pady=8)
        e2.grid(row=2, column=1, padx=8, pady=8)
        
        login_btn = tk.Button(login_container_frame, text="Đăng nhập", 
                            font=("Arial", 12, "bold"), bg="#27ae60", fg="white",
                            width=16, height=2, command=self._do_login)
        login_btn.grid(row=3, column=0, columnspan=2, pady=20)
        
        # Thêm văn bản bản quyền
        tk.Label(login_container_frame, text="© 2023 Hệ thống điểm danh xe", 
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
        if username == self.config.LOGIN_USER and password == self.config.LOGIN_PASS:
            # Đăng nhập thành công
            self.logged_in = True
            self.destroy()
        else:
            # Thông báo chi tiết hơn khi đăng nhập thất bại
            messagebox.showerror("Lỗi đăng nhập", 
                              f"Tài khoản hoặc mật khẩu không đúng!\n\nThông tin đăng nhập đúng:\nTài khoản: {self.config.LOGIN_USER}\nMật khẩu: {self.config.LOGIN_PASS}")