# DU-AN-KHOA-HOC-KI-THUAT-THPT-DUC-HUE-2025
# **BÀI LUẬN CHI TIẾT VỀ PHẦN MỀM HỆ THỐNG ĐIỂM DANH XE BẰNG CÔNG NGHỆ NHẬN DIỆN BIỂN SỐ**

---

## **PHẦN 1: MỞ ĐẦU - GIỚI THIỆU TỔNG QUAN**

Trong bối cảnh đô thị hóa nhanh chóng và số hóa toàn diện, quản lý phương tiện giao thông và an ninh tại các khu vực công cộng, doanh nghiệp, chung cư trở thành một thách thức lớn. Để giải quyết vấn đề này, **Hệ thống điểm danh xe bằng công nghệ nhận diện biển số** đã ra đời, mang đến giải pháp thông minh, hiện đại và hiệu quả.

Phần mềm được xây dựng dựa trên công nghệ AI và máy ảnh, tự động nhận diện biển số xe mà không cần sự can thiệp của con người. Hệ thống có khả năng hoạt động 24/7, tích hợp với quản lý dữ liệu và cung cấp bản ghi chi tiết về hoạt động ra/vào của phương tiện.

---

## **PHẦN 2: BỐI CẢNH VÀ NHU CẦU THỰC TẾ**

### 2.1. Thực trạng quản lý xe hiện tại
- Phần lớn các hệ thống quản lý xe tại các bãi giữ xe, khu chung cư, trường học vẫn sử dụng phương pháp thủ công:
  + Ghi chép sổ sách hoặc bảng điện tử
  + Nhân viên thu vé hoặc kiểm tra biển số
  + Dễ xảy ra sai sót, thất thoát dữ liệu
  
### 2.2. Những thách thức
- **Tăng phương tiện:** Số lượng ô tô và xe máy gia tăng nhanh chóng, vượt quá công suất bãi giữ xe
- **An ninh:** Nguy cơ trộm cắp phương tiện, xe vào không được phép ra vào khu vực hạn chế
- **Quản lý phiền hà:** Lãng phí nhân sự, tốn thời gian chờ đợi cho tài xế

### 2.3. Nhu cầu cấp thiết
- Cần hệ thống tự động hóa giúp tăng hiệu quả quản lý
- Giảm thiểu chi phí vận hành, nhân sự
- Cung cấp dữ liệu chính xác và đầy đủ để phân tích, báo cáo
- Nâng cao trải nghiệm người dùng, giảm thời gian chờ đợi

---

## **PHẦN 3: MỤC TIÊU VÀ TÍNH NĂNG CỦA PHẦN MỀM**

### 3.1. Mục tiêu phát triển
- Xây dựng hệ thống tự động nhận diện biển số xe với độ chính xác cao
- Quản lý dữ liệu xe ra/vào toàn diện, phân tích theo thời gian
- Cảnh báo và kiểm soát phương tiện từ chối ra vào
- Giao diện quản lý thân thiện, dễ sử dụng

### 3.2. Các tính năng nổi bật

#### 3.2.1. **Nhận diện biển số thông minh**
- Sử dụng mô hình YOLO (You Only Look Once) để phát hiện biển số
- OCR (Optical Character Recognition) để đọc ký tự trên biển số
- Xử lý nhiều góc quay, điều kiện ánh sáng khác nhau
- Thời gian nhận diện dưới 1 giây, độ chính xác >95%

#### 3.2.2. **Quản lý đa camera**
- Hỗ trợ kết nối đồng thời nhiều camera USB và Camera IP
- Dễ dàng chuyển đổi giữa các nguồn camera bằng giao diện
- Tự động phát hiện và liệt kê các camera có sẵn
- Lưu trữ cấu hình camera để sử dụng sau này

#### 3.2.3. **Quản lý phương tiện**
- Danh sách đăng ký xe tự động lưu vào file TXT
- Phân biệt xe đã đăng ký và xe chưa đăng ký
- Lịch sử ra/vào xe được lưu trữ trong file Excel
- Tránh trùng lặp dữ liệu, bỏ qua các biển số đã quét gần đây

#### 3.2.4. **Báo cáo và thống kê**
- Thống kê hoạt động theo ngày, tháng, năm
- Xuất báo cáo chi tiết về thời gian vào/ra
- Phân tích tần suất sử dụng, giờ cao điểm
- Giao diện hiển thị lịch sử quét theo dạng bảng

#### 3.2.5. **Hệ thống cảnh báo**
- Âm thanh thông báo khi xe vào/ra
- Màu sắc khác biệt trên giao diện cho xe đăng ký/ chưa đăng ký
- Hiển thị trạng thái phù hợp (xuống dòng, chờ xử lý, xe vào, xe ra)

#### 3.2.6. **Bảo mật và cấu hình**
- Mật khẩu đăng nhập tùy chỉnh
- Cảnh báo truy cập bất hợp pháp
- Tùy chỉnh thời gian chờ xác nhận xe vào/ra
- Lưu cấu hình tự động khi thay đổi thông số

---

## **PHẦN 4: CÔNG NGHỆ SỬ DỤNG**

### 4.1. Framework và ngôn ngữ lập trình
- **Python:** Ngôn ngữ chính phát triển phần mềm, mạnh mẽ trong xử lý AI
- **Tkinter:** Xây dựng giao diện người dùng (GUI)
- **PyInstaller:** Đóng gói phần mềm thành file .exe độc lập
- **OpenCV:** Xử lý hình ảnh, video từ camera

### 4.2. Công nghệ AI và Machine Learning
- **YOLO (You Only Look Once):** Mô hình phát hiện đối tượng và biển số trong thời gian thực
  + Cách hoạt động: Phân chia ảnh thành các lưới, dự đoán đối tượng trong mỗi ô lưới
  + Ưu điểm: Nhanh, chính xác, có thể thực hiện trên thiết bị thông thường
  
- **OCR (Nhận dạng ký tự quang học):** Đọc nội dung biển số
  + Sử dụng mô hình Deep Learning được huấn luyện đặc biệt
  + Xử lý hình ảnh biển số bị góc xiên, tối hoặc sáng quá mức

### 4.3. Xử lý dữ liệu
- **Pandas:** Xử lý và phân tích dữ liệu lịch sử
- **OpenPyXL:** Làm việc với file Excel
- **JSON:** Lưu trữ cấu hình hệ thống
- **SQLite:** Lưu trữ dữ liệu cài đặt và thông tin đăng nhập

### 4.4. Âm thanh & Giao diện
- **Pygame:** Phát âm thanh cảnh báo, thông báo
- **Pillow & ImageTk:** Xử lý hình ảnh, hiển thị trên giao diện

---

## **PHẦN 5: CẤU TRÚC PHẦN MỀM**

### 5.1. Kiến trúc tổng thể
Hệ thống được chia thành các module chức năng rõ ràng, dễ bảo trì và mở rộng:

```
Hệ thống điểm danh xe
│
├── Giao diện người dùng (Tkinter GUI)
│
├── Module nhận diện biển số (YOLO + OCR)
│
├── Module quản lý dữ liệu 
│   └─ Lưu file TXT (danh sách xe đăng ký)
│   └─ Lưu file Excel (lịch sử quét)
│
├── Module quản lý camera
│   └─ Hỗ trợ USB và IP Camera
│   └─ Quát lý nhiều nguồn camera
│
├── Module âm thanh (pygame)
│
└── Module cấu hình (JSON)
```

### 5.2. Giao diện người dùng
- **Màn hình đăng nhập:** Bảo vệ hệ thống bằng thông tin đăng nhập
- **Tab "Camera quét xe"**
  + Hiển thị hình ảnh trực tiếp từ camera
  + Khu vực hiển thị biển số được nhận diện
  + Nút điều khiển camera (Bật/Tắt/Chuyển)
  + Thông tin trạng thái hệ thống
  
- **Tab "Danh sách quét hôm nay"**
  + Bảng thống kê các xe đã quét trong ngày
  + Cột: Ngày, Biển số, Trạng thái, Thời gian vào, Thời gian ra
  
- **Tab "Đăng ký xe"**
  + Form nhập biển số cần đăng ký
  + Bảng danh sách xe đã đăng ký
  + Chức năng xóa, sao chép biển số

### 5.3. Quản lý file cấu hình
- **config.json:** Thông tin đăng nhập, thời gian quét
- **cameras.json:** Danh sách và cấu hình các camera
- **registered.txt:** Danh sách biển số xe đã đăng ký
- **scan_log.xlsx:** Lịch sử quét xe đầy đủ

---

## **PHẦN 6: QUY TRÌNH HOẠT ĐỘNG**

### 6.1. Luồng xử lý khi nhận diện biển số

```
[Camera] 
    ↓
[QR code - Frame hình ảnh]
    ↓
[YOLO] Phát hiện vật thể hình chữ nhật 
    ↓
[Cắt vùng biển số]
    ↓
[OCR] Đọc ký tự trên biển số
    ↓
[So sánh với danh sách đăng ký]
    ↓
[Kiểm tra thời gian đã thấy lần trước]
    ↓
[Xác định xe vào/ra]
    ↓
[Ghi vào file Excel & Cập nhật giao diện]
    ↓
[Phát âm thanh cảnh báo]
```

### 6.2. Xử lý xe vào
- Phát hiện biển số xe chưa từng thấy hoặc đã qua thời gian chờ (SCAN_INTERVAL_IN)
- Kiểm tra xe đã đăng ký hay chưa
- Thêm mới hoặc cập nhật thông tin thời gian vào
- Hiển thị thông báo màu xanh đối với xe đăng ký, đỏ đối với xe chưa đăng ký

### 6.3. Xử lý xe ra
- Kiểm tra thời gian đã thấy xe đó lần trước (SCAN_INTERVAL_OUT)
- Cập nhật thông tin thời gian ra nếu đã thấy trước đó
- Xóa dữ liệu xe khỏi danh sách đang chờ

### 6.4. Tránh trùng lặp
- Cơ chế COOLDOWN_SECONDS (thường 5 giây) để loại bỏ các biển số được quét liên tục
- Sử dụng hàm normalize_plate() để chuẩn hóa chuỗi biển số (bỏ dấu cách, ký tự đặc biệt)

---

## **PHẦN 7: ƯU ĐIỂM VÀ LỢI ÍCH**

### 7.1. Đối với đơn vị quản lý
- **Tiết kiệm chi phí vận hành:** Giảm cần nhân viên kiểm soát xe
- **Tăng hiệu quả quản lý:** Theo dõi chính xác, tự động, không sai sót
- **Dữ liệu toàn diện:** Báo cáo chi tiết, phân tích xu hướng sử dụng
- **Nâng cao bảo mật:** Kiểm soát lối vào, phát hiện xe lạ
- **Linh hoạt cấu hình:** Tùy chỉnh dễ dàng các thông số hoạt động

### 7.2. Đối với khách hàng/người dùng
- **Trải nghiệm tốt:** Ra/vào cửa tự động, không cần chờ đợi
- **Thông báo tức thì:** Biết xe của mình đã được ghi nhận
- **Bảo mật phương tiện:** Giảm nguy cơ trộm cắp, sử dụng trái phép
- **Minh bạch thông tin:** Tra cứu lịch sử di chuyển của xe

### 7.3. Đối với môi trường
- **Giảm tiêu thụ giấy:** Xóa bỏ sổ sách giấy tờ
- **Tiết kiệm năng lượng:** Tối ưu hóa hệ thống đèn, chiếu sáng tại bãi giữ xe
- **Giảm phát thải khí nhà kính:** Giảm thời gian chờ xe, giảm lưu lượng xe đứng

---

## **PHẦN 8: TRIỂN KHAI VÀ TRIỂN VỌNG**

### 8.1. Quy trình triển khai
1. **Khảo sát, đánh giá nhu cầu:** Xác định số lượng phương tiện, dòng xe, điều kiện ánh sáng
2. **Lắp đặt camera, hệ thống mạng:** Đảm bảo độ phủ sóng, ánh sáng phù hợp
3. **Cài đặt, cấu hình phần mềm:** Cập nhật danh sách xe đăng ký, thiết lập thông số
4. **Đào tạo người dùng:** Hướng dẫn vận hành, xử lý sự cố
5. **Vận hành thử nghiệm:** Kiểm tra và tối ưu hóa

### 8.2. Giải pháp mở rộng
- **Kết nối với hệ thống an ninh:** Tích hợp camera IP toàn khuôn viên
- **API tích hợp:** Kết nối với phần mềm quản lý bãi giữ xe khác, hệ thống thu phí
- **Ứng dụng di động:** Quản lý từ xa, nhận thông báo qua điện thoại
- **Hệ thống cảnh báo thông minh:** Phát hiện đỗ sai quy định, chiếm giữ nơi đỗ

### 8.3. Phát triển trong tương lai
- **AI cải tiến:** Tăng độ chính xác nhận diện trong điều kiện khó (mưa, tối)
- **Công nghệ IoT:** Kết hợp cảm biến trong bãi giữ xe
- **Blockchain:** Lưu trữ dữ liệu an toàn, chống làm giả thông tin
- **Cảnh báo dự đoán:** Dự báo nhu cầu bãi giữ xe, giờ cao điểm

---

## **KẾT LUẬN**

Hệ thống điểm danh xe bằng công nghệ nhận diện biển số là giải pháp hiện đại, hiệu quả cho việc quản lý phương tiện tại các khu vực cần kiểm soát. Sự kết hợp giữa AI, công nghệ camera và hệ thống quản lý đưa ra một phương pháp toàn diện, thay thế hoàn toàn các phương pháp thủ công truyền thống.

Với khả năng hoạt động 24/7, xử lý nhanh chóng và lưu trữ dữ liệu đầy đủ, phần mềm không chỉ giúp tăng hiệu quả quản lý mà còn nâng cao trải nghiệm người dùng, đảm bảo an ninh và mở ra nhiều triển khai mở rộng trong tương lai.

Đây là một bước tiến quan trọng trên con đường ứng dụng công nghệ IVAN (Internet Vehicle Access Network) vào đời sống, hướng tới một hệ thống thông minh giao thông đô thị hiệu quả.


(c) Copyright by Phan Hoài Ân, student of class 11A1.
