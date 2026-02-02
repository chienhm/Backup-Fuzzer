# Backup Fuzzer

Backup Fuzzer được thiết kế để `fuzzing` và phát hiện các file backup, file tạm, file cấu hình, và các file ẩn nhạy cảm trên máy chủ web. Công cụ hỗ trợ đa luồng (multi-threading), tái sử dụng kết nối (connection pooling), và cung cấp khả năng tùy biến payload linh hoạt.

## 🚀 Tính Năng

*   **Tối ưu hóa tốc độ**: Sử dụng `ThreadPoolExecutor` kết hợp với `requests.Session` để tái sử dụng kết nối TCP, giảm thiểu handshake overhead, giúp quét nhanh hơn.
*   **Hỗ trợ keyword `FUZZ`**: Cho phép chỉ định vị trí chính xác để inject payload trong URL.
*   **Cơ chế lọc thông minh**: Lọc theo Status Code, Kích thước file (Size), và Nội dung (Regex).
*   **Log Scanning Mode**: Chế độ chuyên biệt để quét file logs (`access.log`, `error.log`...) với khả năng xử lý log rotation (`.1`, `.gz`).
*   **Domain Fuzzing**: Tạo payload dựa trên tên miền để tìm các file backup liên quan đến tên miền.
*   **Rate Limit Protection**: Tự động phát hiện lỗi 429 (Too Many Requests) và tạm dừng để tránh bị chặn IP.
*   **Massive User-Agents**: Tích hợp danh sách User-Agent để giả lập nhiều loại trình duyệt và thiết bị, giúp tránh bị chặn bởi các cơ chế bảo mật cơ bản.
*   **Giao diện trực quan**: Thanh tiến trình (tqdm) tự động điều chỉnh theo kích thước màn hình, hiển thị màu sắc trạng thái HTTP.
*   **Smart 404 Detection**: Tự động nhận diện trang Soft 404 dựa trên hành vi của server để loại bỏ False Positives (vẫn đang phát triển).
*   **403 Bypass Engine**: Tự động thử nghiệm các kỹ thuật bypass ACL/WAF khác nhau.

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
*   `--scan-logs [FILE]`: Kích hoạt chế độ quét logs.
    *   Nếu không điền `[FILE]`: Sử dụng danh sách log mặc định tích hợp sẵn.
    *   Nếu điền `[FILE]`: Sử dụng danh sách từ file của bạn.
    *   Tự động tối ưu payload: Loại bỏ các đuôi `.php` vô nghĩa, thêm đuôi rotation (`.1`, `.2.gz`).
*   `--fuzz-date [RANGE]`: Fuzzing file backup theo ngày tháng.
    *   `TODAY`: Quét các format ngày hôm nay.
    *   `MM-YYYY` (vd: `12-2023`): Quét toàn bộ ngày trong tháng 12/2023.
    *   `[Start-End]-YYYY` (vd: `[1-3]-2024`): Quét từ tháng 1 đến tháng 3 năm 2024.
    *   Hỗ trợ đa dạng format: `YYYYMMDD`, `DDMMYY`, `logs-2024-01-01.txt`...
*   `--fuzz-year [YEAR]`: Fuzzing theo năm (vd: `2023`, `2024`).
*   `--fuzz-domain`: Tạo payload biến thể từ domain target (vd: `example.com.zip`, `com.example.tar.gz`).
*   `--smart-404`: Bật tính năng nhận diện Soft 404 thông minh.
*   `-bypass-403`: Kích hoạt tự động Bypass 403 Forbidden bằng nhiều kỹ thuật (Header, URL manipulation).
*   `--only-bypass-403`: CHỈ chạy bypass 403 cho danh sách URL đầu vào (bỏ qua mọi fuzzing).

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

### 6. Quét File Logs (Rất hữu ích)
Tìm các file log hệ thống, log server, log framework:
```bash
python3 fuzzing_backup.py -u https://example.com/logs/ --scan-logs --smart-404
```

### 7. Tìm File Backup Theo Ngày (Date Fuzzing)
Tìm các file backup database hoặc source code được nén theo ngày trong tháng 1/2025:
```bash
# Sẽ sinh ra: data_20250101.sql, backup-01-01-2025.zip, ...
python3 fuzzing_backup.py -u https://example.com/db_backup/ --fuzz-date 1-2025
```

### 8. Tìm Backup theo Tên Miền (Domain Fuzzing)
Tự động sinh ra các file nén dựa trên các thành phần của domain (vd: `example.zip`, `example.com.tar.gz`, `www.rar`...):
```bash
python3 fuzzing_backup.py -u https://example.com/ --fuzz-domain
```

### 9. Quét tổng hợp với Smart 404
Kết hợp tìm backup file config, fuzz domain, và bật lọc 404 thông minh:
```bash
python3 fuzzing_backup.py -u https://example.com/config.php \
    --fuzz-domain --smart-404 \
    -b .bak,.old,.zip,.7z
```

### 10. Chế độ chỉ Bypass (Không Fuzz)
Dùng để kiểm tra file admin hoặc endpoint nhạy cảm đã biết nhưng bị chặn.
```bash
python3 fuzzing_backup.py -u https://target.com/admin/ --only-bypass-403
```

### 11. Fuzz Backup kết hợp Bypass
Tìm file backup, nếu file đó bị 403 thì tự động kích hoạt bypass để thử lấy nội dung.
```bash
python3 fuzzing_backup.py -u https://target.com/.env --bypass-403
```
