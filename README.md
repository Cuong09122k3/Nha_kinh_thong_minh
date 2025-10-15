## 🌿 Dự án 2: Hệ thống vườn nhà kính thông minh

**Môn học:** IoT và Ứng dụng  
**Mục tiêu:** Xây dựng hệ thống **nhà kính thông minh ứng dụng công nghệ IoT** để giám sát và điều khiển tự động các thông số môi trường như nhiệt độ, độ ẩm, ánh sáng và mực nước, nhằm tối ưu hóa sự phát triển của cây trồng.

---

### ⚙️ Công nghệ và Kỹ năng chính

#### 💾 Lập trình và Mô phỏng
- **MicroPython**: Ngôn ngữ gọn nhẹ của Python dùng cho vi điều khiển.  

#### ☁️ Công nghệ IoT
- **ESP32** làm bộ xử lý trung tâm, kết nối **Wi-Fi** để truyền và nhận dữ liệu.  
- Giao thức **MQTT** được sử dụng để:  
  - Gửi dữ liệu từ các cảm biến lên **broker**.  
  - Nhận lệnh điều khiển thiết bị từ người dùng.  
  - Kiểm thử bằng công cụ **MQTT.fx**.

#### 🌡️ Cảm biến và Cơ cấu chấp hành
- **DHT22**: Đo nhiệt độ và độ ẩm môi trường.  
- **LDR Sensor**: Đo cường độ ánh sáng.  
- **HC-SR04**: Đo mực nước trong bể chứa.  
- **Module Relay**: Đóng/ngắt thiết bị (máy bơm, quạt, đèn) dựa trên dữ liệu cảm biến hoặc lệnh điều khiển từ người dùng.

#### 🖥️ Hiển thị
- **Màn hình OLED** hiển thị trực tiếp thông tin và trạng thái của hệ thống.

---

### 📚 Kết quả đạt được
- Hoàn thiện mô hình mô phỏng nhà kính thông minh chạy ổn định
- Dữ liệu cảm biến được cập nhật theo thời gian thực qua giao thức MQTT.  
- Cho phép người dùng điều khiển thiết bị từ xa thông qua ứng dụng MQTT.fx hoặc dashboard tùy chỉnh.

---
