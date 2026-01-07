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

def create_variations(filename, active_suffixes, active_infixes, active_prefixes):
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
    if active_suffixes or active_prefixes: variations.add('%23' + filename + '%23')
    return list(variations)

def generate_mutations(base_url, endpoint, active_suffixes, active_infixes, active_prefixes):
    if not endpoint: return []
    parts = endpoint.split('/')
    filename = parts[-1]
    
    if parts[:-1]: parent_path = "/".join(parts[:-1]) + "/"
    else: parent_path = ""
        
    if not base_url.endswith('/'): base_url += '/'
    full_base = base_url + parent_path

    variations = create_variations(filename, active_suffixes, active_infixes, active_prefixes)
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

def check_url(session, url, base_headers, proxies, filters, use_random_agent, delay, match_codes, filter_codes, output_file, timeout):
    try:
        if delay > 0: time.sleep(delay)

        current_headers = base_headers.copy()
        if use_random_agent:
            current_headers['User-Agent'] = random.choice(USER_AGENTS)

        res = session.get(url, headers=current_headers, proxies=proxies, timeout=timeout, allow_redirects=False, verify=False)
        
        status = res.status_code
        size_bytes = len(res.content)
        
        # --- FILTER STATUS ---
        if filter_codes and status in filter_codes: return
        if 'all' not in match_codes and status not in match_codes: return
        # ---------------------

        if filters['exclude_sizes'] and size_bytes in filters['exclude_sizes']: return 

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
    if not args.random_agent: base_headers['User-Agent'] = 'Mozilla/5.0 (BackupFuzzer/26.0)'
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
                 
                 variations = create_variations(filename, active_suffixes, active_infixes, active_prefixes)
                 for v in variations:
                     all_scan_urls.append(target.replace('FUZZ', parent + v))
            continue

        parsed = urllib.parse.urlparse(target)
        base = f"{parsed.scheme}://{parsed.netloc}"
        if wordlist_endpoints:
            for ep in wordlist_endpoints:
                all_scan_urls.extend(generate_mutations(base, ep, active_suffixes, active_infixes, active_prefixes))
        else:
            path = parsed.path
            if not path or path == "/": continue
            ep = normalize_endpoint(path, args.ext)
            all_scan_urls.extend(generate_mutations(base, ep, active_suffixes, active_infixes, active_prefixes))

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

    try:
        executor = ThreadPoolExecutor(max_workers=args.threads)
        futures = [executor.submit(check_url, session, link, base_headers, proxies, filters, args.random_agent, args.delay, match_codes, filter_codes, args.output_file, args.timeout) for link in all_scan_urls]
        
        for _ in tqdm(as_completed(futures), total=total, unit="req", dynamic_ncols=True, mininterval=0.2,
                      bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"):
            pass
    except KeyboardInterrupt:
        print(f"\n{Colors.RED}[!] Stopping...{Colors.RESET}")
        executor.shutdown(wait=False)
        os._exit(0)

if __name__ == "__main__":
    main()