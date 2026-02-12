import platform
import subprocess
import re
from typing import Dict, Any


def ping_once(ip: str) -> Dict[str, Any]:
    """Ping a single IP and return a small status object.

    Returns:
      {
        'online': bool,
        'latency_ms': float or None,
        'error': str or None
      }
    """
    if not ip:
        return {"online": False, "latency_ms": None, "error": "empty_ip"}

    system = platform.system().lower()
    if system == "windows":
        cmd = ["ping", "-n", "1", "-w", "1000", ip]
    else:
        # Unix-like: use 1 ping with 1-second timeout
        cmd = ["ping", "-c", "1", "-W", "1", ip]

    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
    except Exception as e:
        return {"online": False, "latency_ms": None, "error": str(e)}

    online = result.returncode == 0
    latency = None
    if online:
        text = result.stdout or ""
        # Try multiple patterns to parse latency across platforms
        patterns = [
            r"time[=<]\s*([0-9\.]+)\s*ms",  # "time=23.4 ms"
            r"time\s*([0-9\.]+)\s*ms",  # "time 23.4 ms"
            r"time[=<]([0-9\.]+)\s*ms",  # "time<1ms"
            r"time[=<]\s*([0-9\.]+)\s*ms",  # redundant typo safety
            r"round-trip min/avg/max/stddev = [\d\.]+/([\d\.]+)/[\d\.]+/[\d\.]+ ms",  # Windows avg line
            r"rtt min/avg/max/mdev = [\d\.]+/([\d\.]+)/[\d\.]+/[\d\.]+ ms",  # Unix avg line
        ]
        for pat in patterns:
            m = re.search(pat, text)
            if m:
                try:
                    latency = float(m.group(1))
                    break
                except ValueError:
                    latency = None

    return {
        "online": online,
        "latency_ms": latency,
        "error": None if online else "unreachable",
    }
