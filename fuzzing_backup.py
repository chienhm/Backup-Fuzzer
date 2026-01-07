#!/usr/bin/env python3
import requests
import argparse
import sys
import os
import urllib.parse
import re
import random
import time
import threading
import itertools
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from requests.adapters import HTTPAdapter

# Kiểm tra thư viện tqdm
try:
    from tqdm import tqdm
except ImportError:
    print("Error: Chưa cài 'tqdm'. Vui lòng chạy: pip install tqdm")
    sys.exit(1)

# --- CẤU HÌNH MÀU SẮC ---
class Colors:
    GREEN = '\033[92m'   # 2xx
    BLUE = '\033[94m'    # 3xx
    YELLOW = '\033[93m'  # 403
    RED = '\033[91m'     # 404, 5xx
    CYAN = '\033[96m'    # Info
    GREY = '\033[90m'    # Low priority
    RESET = '\033[0m'

# Khóa để ghi file an toàn khi chạy đa luồng
file_lock = threading.Lock()

# Global counter cho rate limit
RATE_LIMIT_COUNTER = 0
rate_limit_lock = threading.Lock()

# --- 1. USER-AGENTS (MASSIVE LIST v26) ---
USER_AGENTS = [
    # --- WINDOWS (CHROME) ---
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    
    # --- WINDOWS (EDGE) ---
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",

    # --- WINDOWS (FIREFOX) ---
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; rv:122.0) Gecko/20100101 Firefox/122.0",

    # --- MACOS (SAFARI/CHROME) ---
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",

    # --- LINUX ---
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",

    # --- ANDROID (MOBILE) ---
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-A536B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",

    # --- IPHONE (IOS) ---
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",

    # --- TABLETS ---
    "Mozilla/5.0 (iPad; CPU OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 13; SM-X900) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",

    # --- OTHER BROWSERS (OPERA/BRAVE COMPATIBLE) ---
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/108.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 OPR/108.0.0.0",
]

# --- 2. SUFFIX LIST ---
DEFAULT_SUFFIXES = [
    ".bak", ".bk", ".old", ".new", ".tmp", ".temp", ".save", ".safe", ".copy", ".dll", ".dat", ".db",
    ".php", ".txt", ".zip", ".tar", ".tar.gz", ".tgz", ".gz", ".7z", ".rar", ".bz2", ".sql",
    ".1", ".2", "_bak", "-bak", "_bk", "-bk", "_old", "-old", ".orig", ".original",
    ".dist", ".inc", ".log", ".swp", ".swo", "~", ".save", ".backup", ".copy", ".backup1", ".backup2",
    ".bak1", ".bak2", ".bkp", ".bkp1", ".bkp2", ".tmp1", ".tmp2", ".old1", ".old2", ".config", ".cfg", 
    ".ini" , ".backup.tar.gz", ".backup.zip", ".backup.tar", ".backup.tgz", ".backup.rar", ".conf",
    "1", "2", "3", "bin", "json", "xml", ".bin", ".json", ".xml", ".htaccess", ".htpasswd", "_"
]

# --- 3. PREFIX LIST ---
DEFAULT_PREFIXES = ["_", "__", "bk_", "new_", "old_", "bak_", "bk-", "new-", "old-", "bak-", "~", "copy of ", "copy_of_", "."]

# --- 4. INFIX LIST ---
DEFAULT_INFIXES = [
    "_bk", "_bk_1", "_bk_2", "_bk_l", "_bk_new", "_bk_old",
    "_backup", "_backup_1", "_backup_new",
    "_old", "_old_1", "_old_2", "_old_l", "_old_new",
    "_new", "_new_1", "_db", "dll", "_config", "-config",
    "_1", "_2", "_3", "-db", "-dll", "_conf", "-conf",
    "_copy", "_copy_1", "_json", "_xml", "-json", "-xml",
    "-bk", "-backup", "-old", "_bak", "-bak"
    "_v1", "_v2", "v1", "v2", "_v1.0", "_v2.0", "_v1.1", "_v2.1", "-v1", "-v2", "_version1",
    "_temp", "_tmp", "_test", "_check", "_final",
    "_backup_final", "_old_backup", "1", "2", "3"
]

# --- 5. LOG FILENAMES (COMMON) ---
COMMON_LOG_FILENAMES = [
    # General
    "error.log", "access.log", "debug.log", "system.log", "application.log", "app.log", "server.log",
    "error_log", "access_log", "debug_log", "log.txt", "errors.txt", "access.txt", "debug.txt", 
    "trace.log", "events.log", "activity.log", "apps.log", "messages.log", "apps.txt", "messages.txt",
    "audit.log", "auth.log", "daemon.log", "kern.log", "syslog", "logs.txt", "logfile.log", "logfile.txt",
    "combined.log", "combined_access.log", "info.log", "warning.log", "fatal.log", "info.txt", "warning.txt",
    "fatal.txt", "payment.log", "payment_errors.log", "payment_access.log", "payment_debug.log",
    "billing.log", "billing_errors.log", "billing_access.log", "billing_debug.log", "transaction.log",
    "transaction_errors.log", "transaction_access.log", "transaction_debug.log", "order.log", "web.log", "web.txt",
    "web_errors.log", "web_access.log", "web_debug.log", "api.log", "api_errors.log", "api_access.log", "api_debug.log",
    "database.log", "database_errors.log", "database_access.log", "database_debug.log", "cache.log",
    "cache_errors.log", "cache_access.log", "cache_debug.log", "queue.log", "queue_errors.log", "queue_access.log",
    "queue_debug.log", "job.log", "job_errors.log", "job_access.log", "job_debug.log", "worker.log",
    "worker_errors.log", "worker_access.log", "worker_debug.log", "monitor.log", "monitor_errors.log",
    "monitor_access.log", "monitor_debug.log", "alert.log", "alert_errors.log", "alert_access.log", "alert_debug.log",
    "audit.log", "audit_errors.log", "audit_access.log", "audit_debug.log",
    "cron.log", "mail.log", "maillog", "yum.log", "dmesg", "boot.log", "auth.log", "secure", "secure.log",
    "deployment.log", "deploy.log", "supervisor.log", "supervisord.log", "scheduler.log",
    
    # Web Servers
    "nginx.log", "apache.log", "httpd.log", "iis.log", 
    "nginx_error.log", "apache_error.log", "httpd_error.log", "iis_error.log",
    "nginx_access.log", "apache_access.log", "httpd_access.log", "iis_access.log",
    "nginx_debug.log", "apache_debug.log", "httpd_debug.log", "iis_debug.log", "iis7.log", 
    "iis8.log", "iis10.log", "iis_error7.log", "iis_error8.log", "iis_error10.log",
    "iis_access7.log", "iis_access8.log", "iis_access10.log", "iis_debug7.log", "iis_debug8.log",
    "iis_debug10.log",
    
    # Databases
    "mysql.log", "postgresql.log", "mongodb.log", "redis.log", "db.log", "database.log",
    "mysql_error.log", "postgresql_error.log", "mongodb_error.log", "redis_error.log",
    "mysql_access.log", "postgresql_access.log", "mongodb_access.log", "redis_access.log",
    "mysql_debug.log", "postgresql_debug.log", "mongodb_debug.log", "redis_debug.log",

    
    # Frameworks / Languages
    "laravel.log", "worker.log", "fpm.log", "php_errors.log", "php-error.log",
    "catalina.out", "spring.log",
    "production.log", "development.log", "test.log",
    "npm-debug.log", "yarn-error.log",
    "django.log", "flask.log", "rails.log", "tornado.log", "gunicorn.log", "uwsgi.log",
    
    # CMS / Specific
    "wordpress.log", "wp-debug.log", "magento.log", "exception.log", "database.log", "db.log", "sql.log",
    "drupal.log", "joomla.log", "prestashop.log", "error_report.log", "error_report.txt", "shop.log",
    "shop_errors.log", "shop_access.log", "shop_debug.log", "error_report.log", "error_report.txt"
]

def get_arguments():
    parser = argparse.ArgumentParser(
        description="Backup Fuzzer v26.0 (Massive User-Agents)",
        formatter_class=argparse.RawTextHelpFormatter,  
        epilog="""EXAMPLES:
  1. Scan single URL:
     python3 fuzzing_backup.py -u https://example.com/config.php

  2. Scan with custom suffix and prefix:
     python3 fuzzing_backup.py -u https://example.com/index.php -b .bak,.old -pre copy_

  3. Scan list of URLs with threads:
     python3 fuzzing_backup.py -L urls.txt -t 50

  4. Fuzzing with keyword FUZZ (requires wordlist):
     python3 fuzzing_backup.py -u "https://example.com/FUZZ" -w wordlist.txt
     python3 fuzzing_backup.py -L urls_with_fuzz.txt -w wordlist.txt

  5. Filter status and size:
     python3 fuzzing_backup.py -u https://example.com/admin.php -mc 200 -S 1234,4096
"""
    )
    
    req = parser.add_argument_group('INPUT')
    req.add_argument("-u", "--url", dest="url", help="URL mục tiêu đơn lẻ. Hỗ trợ keyword 'FUZZ' để đánh dấu vị trí inject (cần -w).")
    req.add_argument("-L", "--list-url", dest="url_list", help="File chứa danh sách URL mục tiêu. Hỗ trợ keyword 'FUZZ'.")
    req.add_argument("-w", "--wordlist", dest="wordlist", help="File wordlist (Bắt buộc nếu dùng FUZZ)")
    req.add_argument("-e", "--extension", dest="ext", help="Đuôi file gốc")
    
    # Custom Generators
    req.add_argument("-b", "--backup-ext", dest="backup_ext", help="Custom Suffix")
    req.add_argument("-i", "--infix", dest="infix", help="Custom Infix")
    req.add_argument("-pre", "--prefix", dest="prefix", help="Custom Prefix")

    # Modes
    modes = parser.add_argument_group('MODES')
    modes.add_argument("--fuzz-domain", action="store_true", help="Kích hoạt fuzz tạo file backup dựa trên domain")
    modes.add_argument("--fuzz-year", dest="fuzz_year", nargs='?', const=0, type=int, help="Kích hoạt fuzz theo năm. Gõ số năm bắt đầu (Vd: --fuzz-year 2018)")
    modes.add_argument("--fuzz-date", dest="fuzz_date", nargs='?', const="TODAY", help="Kích hoạt fuzz full ngày tháng. Cú pháp: [MM]-YYYY hoặc [StartMM-EndMM]-YYYY. VD: 12-2018, [1-7]-2018. Mặc định: TODAY")
    modes.add_argument("--scan-logs", dest="scan_logs", nargs='?', const="DEFAULT", help="Kích hoạt chế độ quét file logs. Có thể điền tên file log cụ thể để fuzz (VD: --scan-logs custom.log). Nếu để trống sẽ dùng list mặc định.")
    modes.add_argument("--smart-404", action="store_true", help="Tự động nhận diện Soft 404 để lọc False Positives")
    modes.add_argument("--no-suffix", action="store_true", help="Tắt quét nối đuôi (Suffix)")
    modes.add_argument("--no-prefix", action="store_true", help="Tắt quét tiền tố (Prefix)")
    modes.add_argument("--no-infix", action="store_true", help="Tắt quét chèn giữa (Infix)")

    # FILTERING & STATUS
    filt = parser.add_argument_group('FILTERING & STATUS')
    filt.add_argument("-S", "--exclude-size", dest="exclude_sizes", help="Bỏ qua size (BYTES).")
    filt.add_argument("-x", "--exclude-text", dest="exclude_text", help="Regex bỏ qua content")
    filt.add_argument("-g", "--grep", dest="grep", help="Regex tìm kiếm content")
    filt.add_argument("-mc", "--match-code", dest="match_code", default="200,403", help="Status code muốn hiển thị (Mặc định: 200,403). Dùng 'all' để hiện tất cả.")
    filt.add_argument("-fc", "--filter-code", dest="filter_code", help="Status code muốn ẩn (Mặc định: None)")

    # OUTPUT
    out = parser.add_argument_group('OUTPUT')
    out.add_argument("-o", "--output", dest="output_file", help="Đường dẫn file lưu kết quả (Ví dụ: result.txt)")

    conn = parser.add_argument_group('CONNECTION')
    conn.add_argument("-t", "--threads", dest="threads", type=int, default=10, help="Số luồng (Mặc định: 50)")
    conn.add_argument("-T", "--timeout", dest="timeout", type=float, default=5, help="Timeout (giây) (Mặc định: 5)")
    conn.add_argument("-D", "--delay", dest="delay", type=float, default=0, help="Delay (giây) giữa các request")
    conn.add_argument("-p", "--proxy", dest="proxy", help="Proxy URL")
    conn.add_argument("-H", "--header", dest="headers", action="append", help="Custom Header")
    conn.add_argument("--random-agent", dest="random_agent", action="store_true", help="Random User-Agent")
    
    return parser.parse_args()

def format_size(size_in_bytes):
    human_size = ""
    original_size = size_in_bytes
    units = ['B', 'KB', 'MB', 'GB']
    for unit in units:
        if size_in_bytes < 1024.0:
            human_size = f"{size_in_bytes:.2f} {unit}"
            break
        size_in_bytes /= 1024.0
    else:
        human_size = f"{size_in_bytes:.2f} TB"
    return f"{human_size} ({original_size} B)"

def normalize_endpoint(endpoint, extension=None):
    endpoint = endpoint.strip()
    if endpoint.startswith('/'): endpoint = endpoint[1:]
    if extension:
        if not extension.startswith('.'): extension = '.' + extension
        if not endpoint.endswith(extension): endpoint += extension
    return endpoint

def generate_year_payloads(start_year=None):
    """Tạo danh sách các pattern năm phổ biến"""
    year_patterns = set()
    now = datetime.now()
    current_year = now.year

    if start_year is not None:
        y_start = min(start_year, current_year)
        y_end = max(start_year, current_year)
        years = list(range(y_start, y_end + 1))
    else:
        years = [current_year, current_year - 1] 
    
    for y in years:
        year_patterns.add(str(y)) # 2024
        year_patterns.add(f"_{y}") # _2024
        year_patterns.add(f".{y}") # .2024
        year_patterns.add(f"-{y}") # -2024
    
    return list(year_patterns)

def generate_full_date_payloads(range_string):
    """
    Sinh pattern full ngày tháng dựa trên input:
    - TODAY (Ngày hiện tại)
    - 2024 (Nguyên năm 2024)
    - 12-2018 (Tháng 12 năm 2018)
    - [1-7]-2018 (Từ tháng 1 đến tháng 7 năm 2018)
    Format sinh ra: YYYYMMDD, DDMMYYYY, MMDDYYYY, YYYY-MM-DD...
    """
    targets_month_year = [] # List of tuple (month, year)
    
    # Handle TODAY
    if range_string == "TODAY":
        now = datetime.now()
        # Đối với TODAY, ta chỉ fuzz ngày hôm nay (và có thể hôm qua cho chắc)
        # Nhưng function này thiết kế theo month/year loop.
        # Để đơn giản, ta trả về trực tiếp bộ payload cho ngày hôm nay luôn
        # Thay vì loop qua month/year.
        date_patterns = set()
        dt = now
        
        # Danh sách các định dạng cần fuzz
        # Bao gồm cả Full Year (YYYY) và Short Year (YY)
        # Bao gồm các separator phổ biến (-, .)
        fmt_list = [
            "%Y%m%d",   # 20240125
            "%d%m%Y",   # 25012024
            "%Y-%m-%d", # 2024-01-25
            "%m%d%Y",   # 01252024
            "%Y-%d-%m", # 2024-25-01
            "%d-%m-%Y", # 25-01-2024
            "%m-%d-%Y", # 01-25-2024
            "%d%m%y",   # 250124 (Short Year)
            "%y%m%d",   # 240125 (Short Year)
        ]

        for fmt in fmt_list:
            val = dt.strftime(fmt)
            # Add variations: raw, _val, -val, .val
            date_patterns.add(val)
            date_patterns.add(f"_{val}")
            date_patterns.add(f"-{val}")
            date_patterns.add(f".{val}")
        
        return list(date_patterns)

    # Regex parse input
    # Case 1: [1-7]-2018
    match_range = re.match(r'^\[(\d+)-(\d+)\]-(\d{4})$', range_string)
    # Case 2: 12-2018
    match_single = re.match(r'^(\d{1,2})-(\d{4})$', range_string)
    # Case 3: 2024 (Full year)
    match_year = re.match(r'^(\d{4})$', range_string)
    
    if match_range:
        start_m = int(match_range.group(1))
        end_m = int(match_range.group(2))
        y = int(match_range.group(3))
        for m in range(start_m, end_m + 1):
            if 1 <= m <= 12: targets_month_year.append((m, y))
            
    elif match_single:
        m = int(match_single.group(1))
        y = int(match_single.group(2))
        if 1 <= m <= 12: targets_month_year.append((m, y))

    elif match_year:
        y = int(match_year.group(1))
        for m in range(1, 13):
            targets_month_year.append((m, y))

    else:
        print(f"{Colors.RED}[!] Format date fuzz không hợp lệ: {range_string}{Colors.RESET}")
        return []

    date_patterns = set()
    from calendar import monthrange

    for m, y in targets_month_year:
        days_in_month = monthrange(y, m)[1]
        for d in range(1, days_in_month + 1):
            try:
                dt = datetime(year=y, month=m, day=d)
            except ValueError:
                continue

            # Standardized format list + prefixing for loop
            fmt_list = [
                "%Y%m%d", "%d%m%Y", "%Y-%m-%d", "%m%d%Y", 
                "%Y-%d-%m", "%d-%m-%Y", "%m-%d-%Y",
                "%d%m%y", "%y%m%d"
            ]

            for fmt in fmt_list:
                val = dt.strftime(fmt)
                date_patterns.add(val)
                date_patterns.add(f"_{val}")
                date_patterns.add(f"-{val}")
                date_patterns.add(f".{val}")

    return list(date_patterns)

def create_variations(filename, active_suffixes, active_infixes, active_prefixes, date_payloads=None):
    if '.' in filename:
        stem, ext = filename.rsplit('.', 1)
        ext = '.' + ext 
    else:
        stem = filename
        ext = ""

    variations = set()
    if ext and active_infixes: 
        for infix in active_infixes: variations.add(stem + infix + ext)
    if active_suffixes:
        for suffix in active_suffixes:
            variations.add(filename + suffix)
            if ext and suffix.startswith('.'): variations.add(stem + suffix)
    if active_prefixes:
        for prefix in active_prefixes: variations.add(prefix + filename)
    
    # --- DATE FUZZING ---
    if date_payloads:
        for d in date_payloads:
            # Suffix style: config.php.2024, config.php_2024
            variations.add(filename + d)
             # Infix style: config_2024.php
            if ext: variations.add(stem + d + ext)

    if active_suffixes or active_prefixes: variations.add('%23' + filename + '%23')
    return list(variations)

def generate_domain_payloads(target_url, active_suffixes, active_infixes, active_prefixes, date_payloads=None):
    """
    Sinh ra payload dựa trên domain của target 
    Kết hợp với suffix, infix, prefix từ arguments.
    """
    try:
        parsed = urllib.parse.urlparse(target_url)
        hostname = parsed.hostname
        if not hostname: return []
    except: return []
    
    parts = hostname.split('.')
    domain_variations = set()

    # 1. Full hostname: sub.example.com
    domain_variations.add(hostname)
    
    # 2. Main domain + TLD: example.com
    if len(parts) >= 2:
        domain_variations.add(f"{parts[-2]}.{parts[-1]}")
    
    # 3. Individual parts: sub, example, com
    for part in parts:
        domain_variations.add(part)
    
    # 4. Without dots: subexamplecom
    domain_variations.add(hostname.replace('.', ''))
    
    # 5. Consecutive pairs: sub.example, example.com
    for i in range(len(parts) - 1):
        domain_variations.add(f"{parts[i]}.{parts[i+1]}")
        domain_variations.add(f"{parts[i]}{parts[i+1]}") # No dot pair
    
    # 6. Shuffle/Mixed (Permutations of parts)
    if len(parts) > 1 and len(parts) <= 4:
        perms = itertools.permutations(parts)
        for p in perms:
            domain_variations.add(".".join(p))
            domain_variations.add("".join(p))

    # 7. Reverse (Dao nguoc chuoi)
    domain_variations.add(hostname[::-1])
    domain_variations.add(hostname.replace('.', '')[::-1])

    # 8. Without vowels
    vowels = ['a', 'e', 'i', 'o', 'u']
    current_vars = list(domain_variations)
    for v in current_vars:
        no_vowel = v
        for char in vowels:
            no_vowel = no_vowel.replace(char, '')
        if no_vowel and no_vowel != v:
            domain_variations.add(no_vowel)

    # --- Combine with Suffixes/Prefixes/Infixes ---
    # Nếu người dùng KHÔNG nhập -b (custom suffix), thì dùng list mặc định CỘNG THÊM các extension nén phổ biến cho domain backup
    # Nếu người dùng có nhập -b, thì chỉ dùng cái họ nhập.
    
    # Tuy nhiên, để linh hoạt, ta sẽ dùng hàm create_variations cho từng biến thể domain.
    # Lưu ý: create_variations sẽ coi biến thể domain là "filename".
    
    payloads = []
    base_url = f"{parsed.scheme}://{parsed.netloc}/"
    
    for dv in domain_variations:
        # Gọi hàm create_variations để áp dụng logic prefix, suffix, infix
        # Lưu ý: create_variations sẽ tự tách extension nếu tên có dấu chấm (vd: example.com -> stem: example, ext: .com)
        # Điều này tạo ra các biến thể rất thú vị: example_bk.com, example.com.zip, old_example.com
        
        mutations = create_variations(dv, active_suffixes, active_infixes, active_prefixes, date_payloads)
        
        # Ngoài ra, với domain fuzzing, ta luôn muốn thử ghép trực tiếp các đuôi nén phổ biến
        # nếu nó chưa có trong active_suffixes
        
        # Nếu active_suffixes rỗng (do --no-suffix), ta tôn trọng nó.
        # Nếu active_suffixes có giá trị (mặc định hoặc custom), ta dùng nó.
        
        for m in mutations:
            payloads.append(base_url + m)
            
    return list(set(payloads))

def generate_mutations(base_url, endpoint, active_suffixes, active_infixes, active_prefixes, date_payloads=None):
    if not endpoint: return []
    parts = endpoint.split('/')
    filename = parts[-1]
    
    if parts[:-1]: parent_path = "/".join(parts[:-1]) + "/"
    else: parent_path = ""
        
    if not base_url.endswith('/'): base_url += '/'
    full_base = base_url + parent_path

    variations = create_variations(filename, active_suffixes, active_infixes, active_prefixes, date_payloads)
    return [full_base + v for v in variations]

def get_color_for_status(status_code):
    if 200 <= status_code < 300: return Colors.GREEN
    if 300 <= status_code < 400: return Colors.BLUE
    if status_code == 403: return Colors.YELLOW
    if status_code == 404: return Colors.RED
    if status_code >= 500: return Colors.RED
    return Colors.GREY

def save_to_file(filepath, content):
    """Ghi kết quả vào file với thread lock"""
    if not filepath: return
    with file_lock:
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(content + "\n")
        except Exception as e:
            pass

def detect_soft_404(session, base_url, headers, proxies):
    """
    Gửi request đến URL không tồn tại để lấy signature của Soft 404
    Trả về: (status_code, content_length) của trang 404
    """
    try:
        # Tạo random path kiểu UUID để chắc chắn 404
        random_path = f"soft404_probing_{random.randint(100000, 999999)}"
        probe_url = urllib.parse.urljoin(base_url, random_path)
        
        # Thử 2 lần để chắc chắn ổn định
        sizes = []
        chk_status = 0
        
        for _ in range(2):
            res = session.get(probe_url, headers=headers, proxies=proxies, timeout=5, allow_redirects=False, verify=False)
            sizes.append(len(res.content))
            chk_status = res.status_code
        
        # Nếu size ổn định (chênh lệch ít) -> lấy trung bình hoặc max
        if abs(sizes[0] - sizes[1]) < 10: 
            # print(f"{Colors.GREY}[*] Soft 404 Signature for {base_url}: Status={chk_status}, Size={sizes[0]}{Colors.RESET}")
            return (chk_status, sizes[0]) # Trả về size của trang lỗi
            
    except:
        pass
    return (None, None)

def check_url(session, url, base_headers, proxies, filters, use_random_agent, delay, match_codes, filter_codes, output_file, timeout, soft_404_signatures=None, retry_count=0):
    try:
        if delay > 0 and retry_count == 0: time.sleep(delay)

        current_headers = base_headers.copy()
        if use_random_agent:
            current_headers['User-Agent'] = random.choice(USER_AGENTS)

        res = session.get(url, headers=current_headers, proxies=proxies, timeout=timeout, allow_redirects=False, verify=False)
        
        status = res.status_code

        # --- RATE LIMIT HANDLING (429) ---
        if status == 429:
            global RATE_LIMIT_COUNTER
            with rate_limit_lock:
                RATE_LIMIT_COUNTER += 1
                curr_failed = RATE_LIMIT_COUNTER
            
            if curr_failed > 100:
                tqdm.write(f"{Colors.RED}[CRITICAL] Too Many 429 Errors (>100). Stop tool immediately to prevent IP Block.{Colors.RESET}")
                try: os._exit(1) # Kill forcedly
                except: sys.exit(1)

            if retry_count < 3: # Max 3 lần thử lại
                wait_t = 10 * (retry_count + 1)
                tqdm.write(f"{Colors.YELLOW}[!] 429 Too Many Requests tại {url}. Đang ngủ {wait_t}s rồi thử lại... (Total 429: {curr_failed}){Colors.RESET}")
                time.sleep(wait_t)
                return check_url(session, url, base_headers, proxies, filters, use_random_agent, delay, match_codes, filter_codes, output_file, timeout, soft_404_signatures, retry_count + 1)
            else:
                tqdm.write(f"{Colors.RED}[!] Bỏ qua {url} sau 3 lần gặp 429.{Colors.RESET}")
                return
        size_bytes = len(res.content)
        
        # --- FILTER STATUS ---
        if filter_codes and status in filter_codes: return
        if 'all' not in match_codes and status not in match_codes: return
        # ---------------------

        if filters['exclude_sizes'] and size_bytes in filters['exclude_sizes']: return 

        # --- SOFT 404 CHECK ---
        # Nếu đã bật Smart 404, ta kiểm tra xem response này có giống trang Soft 404 không
        if soft_404_signatures:
            # Lấy domain base để đối chiếu signature
            parsed = urllib.parse.urlparse(url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            
            if base in soft_404_signatures:
                sig_status, sig_size = soft_404_signatures[base]
                if sig_status and sig_size:
                     # Nếu status giống status 404 VÀ size xấp xỉ size 404 (chênh lệch < 5%)
                     # Hoặc nếu status trả về 200 nhưng size lại bằng size của trang lỗi 404
                     if status == sig_status and abs(size_bytes - sig_size) < (sig_size * 0.05 + 10):
                         return # Bỏ qua, đây là Soft 404

        content_for_search = str(res.headers) + "\n" + res.text 
        if filters['exclude_regex'] and filters['exclude_regex'].search(content_for_search): return
        if filters['grep_regex'] and not filters['grep_regex'].search(content_for_search): return

        size_str = format_size(size_bytes)
        color = get_color_for_status(status)
        
        # 1. In ra màn hình (Có màu)
        msg_console = f"{color}[{status}]{Colors.RESET} | {Colors.CYAN}{size_str:>20}{Colors.RESET} | {url}"
        tqdm.write(msg_console)

        # 2. Ghi ra file (Không màu, định dạng text thuần)
        if output_file:
            msg_file = f"[{status}] | {size_str} | {url}"
            save_to_file(output_file, msg_file)

    except Exception:
        pass

def main():
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    args = get_arguments()
    
    if not args.url and not args.url_list:
        print(f"{Colors.RED}[!] Lỗi: Thiếu -u hoặc -L.{Colors.RESET}"); sys.exit(1)

    # --- PARSE STATUS CODES ---
    match_codes = []
    if args.match_code.lower() == 'all':
        match_codes = ['all']
    else:
        try: match_codes = [int(c.strip()) for c in args.match_code.split(',')]
        except: print(f"{Colors.RED}[!] Lỗi -mc.{Colors.RESET}"); sys.exit(1)

    filter_codes = []
    if args.filter_code:
        try: filter_codes = [int(c.strip()) for c in args.filter_code.split(',')]
        except: print(f"{Colors.RED}[!] Lỗi -fc.{Colors.RESET}"); sys.exit(1)

    # --- SETUP PAYLOADS ---
    active_suffixes = DEFAULT_SUFFIXES
    if args.no_suffix: active_suffixes = []
    elif args.backup_ext:
        raw_exts = args.backup_ext.split(',')
        active_suffixes = ['.'+e.strip() if not e.strip().startswith('.') else e.strip() for e in raw_exts if e.strip()]

    active_infixes = DEFAULT_INFIXES
    if args.no_infix: active_infixes = []
    elif args.infix: active_infixes = [i.strip() for i in args.infix.split(',') if i.strip()]

    active_prefixes = DEFAULT_PREFIXES
    if args.no_prefix: active_prefixes = []
    elif args.prefix: active_prefixes = [p.strip() for p in args.prefix.split(',') if p.strip()]

    base_headers = {}
    if not args.random_agent: base_headers['User-Agent'] = 'Mozilla/5.0 (Backup-Fuzzer/2.7.0)'
    if args.headers:
        for h in args.headers:
            try: k, v = h.split(':', 1); base_headers[k.strip()] = v.strip()
            except: pass
    
    filters = {'exclude_sizes': [], 'exclude_regex': None, 'grep_regex': None}
    if args.exclude_sizes:
        filters['exclude_sizes'] = [int(float(s.strip())) for s in args.exclude_sizes.split(',')]
    if args.exclude_text: filters['exclude_regex'] = re.compile(args.exclude_text, re.IGNORECASE)
    if args.grep: filters['grep_regex'] = re.compile(args.grep, re.IGNORECASE)

    proxies = {"http": args.proxy, "https": args.proxy} if args.proxy else {}

    # --- TARGETS ---
    target_list = []
    if args.url: target_list.append(args.url)
    if args.url_list and os.path.exists(args.url_list):
        with open(args.url_list, 'r', encoding='utf-8', errors='ignore') as f:
            target_list.extend([line.strip() for line in f if line.strip()])

    print(f"{Colors.BLUE}" + "="*60)
    print(f" TARGETS  : {len(target_list)} URLs")
    if args.output_file:
        print(f" OUTPUT   : {args.output_file}")
    if 'all' in match_codes: print(f" MATCH    : ALL")
    else: print(f" MATCH    : {match_codes}")
    if filter_codes: print(f" FILTER   : {filter_codes}")
    print("="*60 + f"{Colors.RESET}\n")

    # --- GENERATE ---
    all_scan_urls = []
    wordlist_endpoints = []
    
    # Date Payloads
    date_payloads = []
    
    # 1. Year Fuzzing
    if args.fuzz_year is not None:
        # Nếu == 0 (const) => Không có năm chỉ định, dùng mặc định
        # Nếu > 0 => Có năm chỉ định
        start_y = args.fuzz_year if args.fuzz_year > 0 else None
        date_payloads.extend(generate_year_payloads(start_y))

    # 2. Full Date Fuzzing (MM-YYYY or Range)
    if args.fuzz_date:
        full_date_p = generate_full_date_payloads(args.fuzz_date)
        date_payloads.extend(full_date_p)

    if date_payloads:
        date_payloads = list(set(date_payloads))
        print(f"{Colors.YELLOW}[*] Loaded {len(date_payloads)} date patterns.{Colors.RESET}")

    if args.wordlist and os.path.exists(args.wordlist):
        with open(args.wordlist, 'r', encoding='utf-8', errors='ignore') as f:
            wordlist_endpoints = list(set([normalize_endpoint(line, args.ext) for line in f if line.strip()]))

    for target in target_list:
        if 'FUZZ' in target:
            if not wordlist_endpoints:
                 print(f"{Colors.YELLOW}[!] Warning: URL contains FUZZ but no wordlist provided. Skipping {target}.{Colors.RESET}")
                 continue
            
            for ep in wordlist_endpoints:
                 parts = ep.split('/')
                 filename = parts[-1]
                 parent = "/".join(parts[:-1])
                 if parent: parent += "/"
                 
                 # Note: FUZZ mode doesn't support automatic date/domain fuzzing deeply unless explicit logic added
                 variations = create_variations(filename, active_suffixes, active_infixes, active_prefixes, date_payloads)
                 for v in variations:
                     all_scan_urls.append(target.replace('FUZZ', parent + v))
            continue

        parsed = urllib.parse.urlparse(target)
        base = f"{parsed.scheme}://{parsed.netloc}"
        
        # --- LOG SCAN MODE ---
        if args.scan_logs:
            # Xác định thư mục mục tiêu
            path = parsed.path
            if not path.endswith('/'): path += '/'
            
            # Với chế độ Scan Logs, ta KHÔNG dùng suffix/prefix/infix của backup code (như .php.bak, copy_of_...)
            # Mà dùng định nghĩa riêng cho Log (Rotation, Compression...)
            
            # 1. Suffixes cho log rotation/backup thường gặp (Added into filenames: error.log.1, error.log.old)
            log_rot_suffixes = ['.1', '.2', '.3', '.4', '.5', '.old', '.bak', '.1.gz', '.2.gz', '.gz', '.zip', '.tar.gz', '.rar', '.7z', '.swp', '~']
            
            # 2. Infixes cho log (Added inside filenames: error.old.log, error-2024.log)
            # Dùng để biến đổi: error.log -> error[INFIX].log
            log_infixes = [
                '.1', '.2', # error.1.log
                '_old', '-old', '.old', # error_old.log
                '_bak', '-bak', '.bak', # error.bak.log
                '_backup', '-backup', '.backup',
                '_copy', '-copy',
                '_err', '-err', '_error', '-error',
                '_acc', '-acc', '_access', '-access',
                '_new', '-new',
                '_test', '-test',
                '_rotate', '-rotate'
            ]
            
            # 2. Log không dùng prefix biến dị như code (ko có copy_of_error.log)
            # Nên ta để trống hoặc minimal
            log_prefixes_empty = []

            # Xác định danh sách file logs cần quét
            target_log_filenames = []
            
            # 1. Ưu tiên lấy từ tham số --scan-logs (VD: --scan-logs custom.log)
            if args.scan_logs and args.scan_logs != "DEFAULT":
                target_log_filenames.extend([x.strip() for x in args.scan_logs.split(',') if x.strip()])
                print(f"{Colors.YELLOW}[*] Scanning specific log filenames from CLI: {len(target_log_filenames)} items{Colors.RESET}")
            
            # 2. Lấy thêm từ wordlist -w (nếu có)
            if wordlist_endpoints:
                 target_log_filenames.extend(wordlist_endpoints)
                 print(f"{Colors.YELLOW}[*] Merged {len(wordlist_endpoints)} items from wordlist (-w) into Log Scan.{Colors.RESET}")

            # 3. Nếu không có gì cả (chỉ bật cờ --scan-logs), dùng list mặc định
            if not target_log_filenames:
                 target_log_filenames = COMMON_LOG_FILENAMES
                 print(f"{Colors.CYAN}[*] No custom logs provided. Using built-in common list ({len(COMMON_LOG_FILENAMES)} items).{Colors.RESET}")
            
            # Remove duplicates
            target_log_filenames = list(set(target_log_filenames))

            # Thêm các logs vào endpoint
            for log_file in target_log_filenames:
                ep = path + log_file
                
                # Check file gốc (error.log)
                all_scan_urls.append(base + ep)
                
                # Check variations riêng cho Log (error.log.1, error.log.gz, error.log.2024...)
                # Lưu ý: generate_mutations vẫn xử lý date_payloads (error.log.2024) rất tốt
                all_scan_urls.extend(generate_mutations(base, ep, log_rot_suffixes, log_infixes, log_prefixes_empty, date_payloads))
            
            # --- DATE-BASED LOG FILENAMES (Mới) ---
            # Define common extensions for Date & Domain logs
            log_exts = ['.log', '.logs', '.txt', '.zip', '.sql', '.xml', '.rar', '.tar.gz', '.gz', '.7z']
            
            # Generate: 2022-01-01.log, 2022_01_01.zip, ...
            if date_payloads:
                # Các prefix thường gặp đi kèm date
                log_prefixes = ['log_', 'logs_', 'error_', 'access_', 'db_', 'database_', 'backup_', 'www_', 'data_', ''] 

                for d in date_payloads:
                    # Clean date string (nếu muốn): Xóa ký tự đầu nếu là separator để tránh trùng lặp xấu
                    clean_d = d.lstrip('._-') 
                    
                    for ext in log_exts:
                         # 1. Pure Date + Ext: 2022-07-21.zip
                         all_scan_urls.append(base + path + clean_d + ext)
                         
                         # 2. Prefix + Date + Ext: error_2022-07-21.log
                         for p in log_prefixes:
                              if p: all_scan_urls.append(base + path + p + clean_d + ext)

            # --- DOMAIN-BASED LOG FILENAMES (Mới) ---
            # Generate: fptplay.log, dev.fptplay.vn.zip, fptplay_error.log ...
            try:
                hostname = parsed.hostname
                if hostname:
                    domain_parts = hostname.split('.')
                    chk_names = set()
                    chk_names.add(hostname) # dev.fptplay.vn
                    chk_names.add(hostname.replace('.', '_')) # dev_fptplay_vn
                    
                    if len(domain_parts) >= 2:
                        chk_names.add(domain_parts[-2]) # fptplay
                        chk_names.add(f"{domain_parts[-2]}.{domain_parts[-1]}") # fptplay.vn
                        chk_names.add(f"{domain_parts[-2]}_{domain_parts[-1]}") # fptplay_vn
                    
                    # Log variation suffixes
                    # vd: fptplay.log, fptplay_error.log
                    log_suffixes = ['', '_error', '_access', '_backup', '_db', '_database', '-error', '-access', '-backup']

                    for name in chk_names:
                        for ext in log_exts:
                            for suf in log_suffixes:
                                all_scan_urls.append(base + path + name + suf + ext)
            except: pass

            continue
            continue

        if wordlist_endpoints:
            for ep in wordlist_endpoints:
                all_scan_urls.extend(generate_mutations(base, ep, active_suffixes, active_infixes, active_prefixes, date_payloads))
        else:
            path = parsed.path
            if not path or path == "/": continue
            ep = normalize_endpoint(path, args.ext)
            all_scan_urls.extend(generate_mutations(base, ep, active_suffixes, active_infixes, active_prefixes, date_payloads))
    
    # --- DOMAIN FUZZING (NEW) ---
    if args.fuzz_domain:
        print(f"{Colors.YELLOW}[*] Generating domain-based payloads...{Colors.RESET}")
        for target in target_list:
            all_scan_urls.extend(generate_domain_payloads(target, active_suffixes, active_infixes, active_prefixes, date_payloads))

    all_scan_urls = list(set(all_scan_urls))
    total = len(all_scan_urls)
    
    if total == 0:
        print(f"{Colors.RED}[!] Không có payload.{Colors.RESET}"); sys.exit(0)

    print(f"{Colors.BLUE}[*] Scanning {total} payloads...{Colors.RESET}\n")

    # --- OPTIMIZATION: SESSION REUSE ---
    session = requests.Session()
    adapter = HTTPAdapter(pool_connections=args.threads, pool_maxsize=args.threads)
    session.mount('http://', adapter)
    session.mount('https://', adapter)

    # --- SMART 404 DETECTION Đang Phát Triển Tiếp Phần Này---
    soft_404_signatures = {}
    if args.smart_404:
        print(f"{Colors.YELLOW}[*] Detecting Soft 404 signatures (this may take a few seconds)...{Colors.RESET}")
        
        # Lấy danh sách base domain duy nhất
        unique_bases = set()
        for url in all_scan_urls:
             try:
                 p = urllib.parse.urlparse(url)
                 unique_bases.add(f"{p.scheme}://{p.netloc}")
             except: pass
        
        for base in unique_bases:
            sig = detect_soft_404(session, base, base_headers, proxies)
            if sig[0] is not None:
                soft_404_signatures[base] = sig
                print(f"{Colors.GREY}   + {base} -> 404 Size: {sig[1]} bytes (Status: {sig[0]}){Colors.RESET}")


    try:
        executor = ThreadPoolExecutor(max_workers=args.threads)
        futures = [executor.submit(check_url, session, link, base_headers, proxies, filters, args.random_agent, args.delay, match_codes, filter_codes, args.output_file, args.timeout, soft_404_signatures) for link in all_scan_urls]
        
        for _ in tqdm(as_completed(futures), total=total, unit="req", dynamic_ncols=True, mininterval=0.2,
                      bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"):
            pass
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}[!] Stopping...{Colors.RESET}")
        executor.shutdown(wait=False)
        os._exit(0)

if __name__ == "__main__":
    main()
