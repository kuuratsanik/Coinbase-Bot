"""Pluggable notification channels.

``console`` uses only stdout. ``webhook`` POSTs JSON with the stdlib ``urllib``
(no dependency) and powers Slack/Discord/Telegram/custom endpoints.
"""

from __future__ import annotations

import json
import urllib.request

from src.trading.base import Notifier
from src.trading.registry import register_notifier


class ConsoleNotifier(Notifier):
    id = "console"
    name = "Console"

    def notify(self, subject: str, message: str) -> bool:
        print(f"[notify] {subject}\n{message}")
        return True


class NullNotifier(Notifier):
    id = "null"
    name = "No-op"

    def notify(self, subject: str, message: str) -> bool:
        return True


class WebhookNotifier(Notifier):
    id = "webhook"
    name = "Webhook"

    def __init__(self, url: str = "", timeout: float = 10.0, field: str = "text"):
        self.url = url
        self.timeout = timeout
        self.field = field

    def notify(self, subject: str, message: str) -> bool:
        if not self.url:
            raise ValueError("webhook notifier requires a url")
        payload = json.dumps({self.field: f"*{subject}*\n{message}"}).encode()
        req = urllib.request.Request(
            self.url, data=payload, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310 (user-supplied URL by design)
            return 200 <= resp.status < 300


@register_notifier("console")
def _make_console(probe: bool = False, **config) -> ConsoleNotifier:
    return ConsoleNotifier()


@register_notifier("webhook")
def _make_webhook(probe: bool = False, **config) -> WebhookNotifier:
    if probe:
        return WebhookNotifier()
    return WebhookNotifier(**config)
