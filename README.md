# Slowloris Pro

```
   _____ _               _                _     
  / ____| |             | |              (_)    
 | (___ | | _____      _| |     ___  _ __ _ ___ 
  \___ \| |/ _ \ \ /\ / / |    / _ \| '__| / __|
  ____) | | (_) \ V  V /| |___| (_) | |  | \__ \
 |_____/|_|\___/ \_/\_/ |______\___/|_|  |_|___/
```

> **Advanced, proxy-aware Slowloris implementation in Python.**

---

## Table of Contents
1. [Features](#features)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Usage](#usage)
5. [Command-Line Arguments](#command-line-arguments)
6. [Examples](#examples)
7. [Proxy File Format](#proxy-file-format)
8. [Disclaimer](#disclaimer)

## Features
* Fully-threaded, high-performance Slowloris attack.
* Supports **HTTP / HTTPS / SOCKS4 / SOCKS5** proxies.
* Randomised keep-alive headers & user-agents.
* Custom connection counts, timeouts, keep-alive intervals & attack duration.
* Colourised, real-time logging output (requires `colorama`).

## Requirements
* Python **3.9+** (tested on 3.11/3.12)
* [PySocks](https://pypi.org/project/PySocks/) – proxy support
* [colorama](https://pypi.org/project/colorama/) – coloured logs (optional but recommended)

Install dependencies:
```bash
pip install -r requirements.txt
```
—or manually—
```bash
pip install pysocks colorama
```

## Installation
Clone or download the repository and change into the project directory:
```bash
git clone https://github.com/yourname/slowloris-pro.git
cd slowloris-pro
```

## Usage
```bash
python main.py <target> [options]
```

### Command-Line Arguments
| Flag | Default | Description |
|------|---------|-------------|
| `target` | — | Target URL or IP address (positional) |
| `-p, --port` | `80` | Target port |
| `-s, --sockets` | `500` | Number of concurrent sockets |
| `--proxy-file` | `None` | Path to proxy file (one proxy per line) |
| `--ssl` | _off_ | Enable SSL/TLS for direct connections |
| `--timeout` | `10` | Socket connection timeout (seconds) |
| `--keepalive` | `15` | Seconds between keep-alive header batches |
| `--threads` | `50` | Max worker threads |
| `--sleep-min` | `0.1` | Minimum random delay between keep-alives (seconds) |
| `--sleep-max` | `0.5` | Maximum random delay between keep-alives (seconds) |
| `--duration` | `60` | Attack duration (seconds) |
| `--debug` | _off_ | Enable verbose debug logging |
| `-h, --help` | — | Show full help message |

## Examples
Run a 5-minute HTTPS attack using 1000 sockets:
```bash
python main.py https://example.com -s 1000 --ssl --duration 300
```

Use an HTTP proxy list:
```bash
python main.py 203.0.113.10 --proxy-file proxies.txt
```

Enable coloured debug logs:
```bash
python main.py example.com --debug
```

## Proxy File Format
Each line must describe **one** proxy:
```
# type://[username:password@]host:port
http://1.2.3.4:8080
socks5://user:pass@8.8.8.8:1080
https://203.0.113.10:443
```
If the scheme is omitted, `http` is assumed.

## Disclaimer
This project is provided **for educational & testing purposes only**. Performing a Denial-of-Service attack on systems without explicit permission is **illegal** and unethical. The authors assume **no liability** for any misuse of this software.

---
MIT License © 2025 Your Name
