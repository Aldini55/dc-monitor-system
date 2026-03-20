
import os
import urllib.request
import urllib.parse
import json
import logging

logger = logging.getLogger("telegram")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

def send_alert(severity: str, hostname: str, metric: str, value: float, threshold: float):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return

    icons = {
        "critical": "🔴",
        "warning": "🟠",
        "info": "🔵"
    }
    
    icon = icons.get(severity, "⚪")
    
    message = (
        f"{icon} *DC Monitor Alert*\n"
        f"*Severity:* {severity.upper()}\n"
        f"*Server:* `{hostname}`\n"
        f"*Metric:* {metric.replace('_', ' ').title()}\n"
        f"*Value:* {value:.1f}\n"
        f"*Threshold:* {threshold:.1f}"
    )

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    params = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
    }
    
    data = urllib.parse.urlencode(params).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                logger.info(f"Telegram alert sent: {hostname} {metric} {value:.1f}")
            else:
                logger.warning(f"Telegram returned status {resp.status}")
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")