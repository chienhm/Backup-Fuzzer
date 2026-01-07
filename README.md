# Backup Fuzzer

Backup Fuzzer được thiết kế để `fuzzing` và phát hiện các file backup, file tạm, file cấu hình, và các file ẩn nhạy cảm trên máy chủ web. Công cụ hỗ trợ đa luồng (multi-threading), tái sử dụng kết nối (connection pooling), và cung cấp khả năng tùy biến payload linh hoạt.

## 🚀 Tính Năng

*   **Tối ưu hóa tốc độ**: Sử dụng `ThreadPoolExecutor` kết hợp với `requests.Session` để tái sử dụng kết nối TCP, giảm thiểu handshake overhead, giúp quét nhanh hơn.
*   **Hỗ trợ keyword `FUZZ`**: Cho phép chỉ định vị trí chính xác để inject payload trong URL.
*   **Cơ chế lọc thông minh**: Lọc theo Status Code, Kích thước file (Size), và Nội dung (Regex).
*   **Massive User-Agents**: Tích hợp danh sách User-Agent để giả lập nhiều loại trình duyệt và thiết bị, giúp tránh bị chặn bởi các cơ chế bảo mật cơ bản.
*   **Giao diện trực quan**: Thanh tiến trình (tqdm) tự động điều chỉnh theo kích thước màn hình, hiển thị màu sắc trạng thái HTTP.

## 📦 Cài Đặt

Yêu cầu **Python 3.x**. Cài đặt các thư viện phụ thuộc:

```bash
pip install -r requirements.txt
```

## 📖 Hướng Dẫn Sử Dụng

Cú pháp cơ bản:
```bash
python3 fuzzing_backup.py [OPTIONS]
```

### 1. Các Tùy Chọn (Options)

#### 🔹 Input (Đầu vào)
*   `-u URL`, `--url URL`: URL mục tiêu để quét. Hỗ trợ keyword `FUZZ`.
*   `-L FILE`, `--list-url FILE`: File chứa danh sách các URL mục tiêu.
*   `-w FILE`, `--wordlist FILE`: File chứa danh sách từ khóa (Wordlist). **Bắt buộc** nếu sử dụng keyword `FUZZ`.
*   `-e EXT`, `--extension EXT`: Phần mở rộng mặc định (ví dụ: `php`, `aspx`) để thêm vào các endpoint nếu chưa có.

#### 🔹 Connection & Performance (Kết nối & Hiệu năng)
*   `-t INT`, `--threads INT`: Số luồng chạy song song. **Mặc định: 50**.
*   `-T FLOAT`, `--timeout FLOAT`: Thời gian chờ tối đa cho mỗi request (giây). **Mặc định: 5s**.
*   `-D FLOAT`, `--delay FLOAT`: Thời gian nghỉ giữa các request (giây).
*   `-p URL`, `--proxy URL`: Proxy để định tuyến traffic (ví dụ: `http://127.0.0.1:8080`).
*   `-H HEADER`, `--header HEADER`: Thêm HTTP Header tùy chỉnh (ví dụ: `-H "Authorization: Basic..."`).
*   `--random-agent`: Sử dụng ngẫu nhiên User-Agent cho mỗi request thay vì User-Agent mặc định.

#### 🔹 Payload Generation (Tạo Payload)
*   `-b EXT`, `--backup-ext EXT`: Tùy chỉnh danh sách đuôi mở rộng (Suffix). Ví dụ: `.bak,.old`.
*   `-i STR`, `--infix STR`: Tùy chỉnh danh sách chuỗi chèn giữa (Infix).
*   `-pre STR`, `--prefix STR`: Tùy chỉnh danh sách tiền tố (Prefix).
*   `--no-suffix`: Tắt tạo payload kiểu nối đuôi (vd: `index.php.bak`).
*   `--no-prefix`: Tắt tạo payload kiểu tiền tố (vd: `old_index.php`).
*   `--no-infix`: Tắt tạo payload kiểu chèn giữa.

#### 🔹 Filtering & Output (Lọc & Xuất kết quả)
*   `-mc CODE`: Các status code cần hiển thị. Mặc định: `200,403`. Dùng `all` để hiện tất cả.
*   `-fc CODE`: Các status code cần ẩn đi.
*   `-S BYTES`, `--exclude-size BYTES`: Bỏ qua các response có kích thước cụ thể (bytes).
*   `-x REGEX`, `--exclude-text REGEX`: Bỏ qua response nếu nội dung khớp với Regex.
*   `-g REGEX`, `--grep REGEX`: Chỉ hiển thị response nếu nội dung khớp với Regex.
*   `-o FILE`, `--output FILE`: Ghi kết quả tìm thấy ra file.

---

## 💡 Ví Dụ

### 1. Quét cơ bản (Basic Scan)
Tìm các file backup (như `.bak`, `.old`, `~`, ...) của file `config.php`:
```bash
python3 fuzzing_backup.py -u https://example.com/config.php
```

### 2. Quét hiệu suất cao (High Performance)
Quét danh sách URL từ file `urls.txt` với **100 luồng**, timeout **3 giây** để bỏ qua nhanh các request treo:
```bash
python3 fuzzing_backup.py -L urls.txt -t 100 -T 3
```

### 3. Sử dụng Fuzzing Mode (FUZZ Keyword)
Inject payload từ wordlist vào vị trí `FUZZ`:
```bash
python3 fuzzing_backup.py -u "https://example.com/api/v1/FUZZ/users" -w common_dirs.txt
```

### 4. Bypass & Custom Headers
Chạy qua Burp Suite Proxy, sử dụng Random User-Agent và thêm Header xác thực:
```bash
python3 fuzzing_backup.py -u https://dev.example.com/admin.php \
    -p http://127.0.0.1:8080 \
    --random-agent \
    -H "Authorization: Bearer KEY123" \
    -H "X-Forwarded-For: 127.0.0.1"
```

### 5. Lọc nhiễu (Advanced Filtering)
Chỉ hiển thị code 200, bỏ qua các trang có kích thước 1024 bytes và 500 bytes:
```bash
python3 fuzzing_backup.py -u https://example.com/ -w paths.txt -mc 200 -S 1024,500
```
