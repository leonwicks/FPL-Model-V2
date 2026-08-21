from __future__ import annotations

import logging
import random
import ssl
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC
from typing import Self

import httpx

RETRY_STATUSES = {429, 500, 502, 503, 504}


def _tls_verify() -> bool | ssl.SSLContext:
    """Use the Windows certificate store without disabling TLS verification.

    Some managed Windows networks install inspection roots whose Basic Constraints
    extension predates OpenSSL's strict validation requirement.  The system trust
    store accepts that established root, but Python 3.13 enables the stricter check
    by default.  Removing only that compatibility flag retains certificate-chain and
    hostname verification.
    """
    if sys.platform != "win32":
        return True
    context = ssl.create_default_context()
    context.verify_flags &= ~ssl.VERIFY_X509_STRICT
    return context


@dataclass(frozen=True)
class HttpPayload:
    url: str
    content: bytes
    status_code: int
    content_type: str
    retrieved_at_utc: str
    attempts: int


class HttpClient:
    def __init__(
        self,
        source: str,
        *,
        user_agent: str = "FPLResearchBot/0.1 (+local, non-commercial research)",
        connect_timeout: float = 10,
        read_timeout: float = 60,
        max_attempts: int = 5,
        min_delay: float = 0,
        jitter: float = 0.25,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.source = source
        self.max_attempts = max_attempts
        self.min_delay = min_delay
        self.jitter = jitter
        self.sleep = sleep
        self._last_request = 0.0
        self.log = logging.getLogger(f"football_data.http.{source}")
        self.session = httpx.Client(
            headers={"User-Agent": user_agent, "Accept": "*/*"},
            timeout=httpx.Timeout(read_timeout, connect=connect_timeout),
            follow_redirects=True,
            verify=_tls_verify(),
        )

    def close(self) -> None:
        self.session.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get(self, url: str, *, headers: dict[str, str] | None = None) -> HttpPayload:
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            elapsed = time.monotonic() - self._last_request
            delay = self.min_delay - elapsed
            if delay > 0:
                self.sleep(delay + random.uniform(0, self.jitter))
            started = time.monotonic()
            try:
                response = self.session.get(url, headers=headers)
                self._last_request = time.monotonic()
                duration_ms = round((self._last_request - started) * 1000)
                self.log.info(
                    "http_request",
                    extra={
                        "source": self.source,
                        "url": url,
                        "status": response.status_code,
                        "duration_ms": duration_ms,
                        "attempt": attempt,
                        "response_bytes": len(response.content),
                    },
                )
                if (
                    response.status_code in RETRY_STATUSES
                    and attempt < self.max_attempts
                ):
                    retry_after = response.headers.get("Retry-After")
                    self.sleep(
                        float(retry_after)
                        if retry_after and retry_after.isdigit()
                        else min(60, 2 ** (attempt - 1) + random.random())
                    )
                    continue
                response.raise_for_status()
                return HttpPayload(
                    str(response.url),
                    response.content,
                    response.status_code,
                    response.headers.get("content-type", "application/octet-stream"),
                    _utc_now(),
                    attempt,
                )
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if attempt == self.max_attempts:
                    break
                self.sleep(min(60, 2 ** (attempt - 1) + random.random()))
        raise RuntimeError(
            f"Failed to retrieve {url} after {self.max_attempts} attempts"
        ) from last_error


def _utc_now() -> str:
    from datetime import datetime

    return datetime.now(UTC).isoformat()
