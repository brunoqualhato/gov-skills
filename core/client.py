"""HTTP client configured for Brazilian Government APIs and Open Data portals."""

import time
import httpx
from typing import Any, Dict, Optional, Iterator
from pathlib import Path
from rich.console import Console

from .config import settings

console = Console()


class GovHttpClient:
    """Resilient HTTP client for querying Brazilian Government APIs."""

    def __init__(self, base_url: str = "", timeout: float = settings.DEFAULT_TIMEOUT, headers: Optional[Dict[str, str]] = None):
        self.base_url = base_url.rstrip("/")
        default_headers = {
            "User-Agent": settings.USER_AGENT,
            "Accept": "application/json, text/plain, */*",
        }
        if headers:
            default_headers.update(headers)

        client_kwargs = {
            "headers": default_headers,
            "timeout": timeout,
            "follow_redirects": True,
        }
        if self.base_url:
            client_kwargs["base_url"] = self.base_url

        self.client = httpx.Client(**client_kwargs)

    def get_json(self, endpoint: str, params: Optional[Dict[str, Any]] = None, retries: int = settings.MAX_RETRIES) -> Any:
        """Performs a GET request and returns JSON with retry backoff."""
        url = endpoint if endpoint.startswith("http") else f"{self.base_url}/{endpoint.lstrip('/')}"
        delay = 1.0

        for attempt in range(1, retries + 1):
            try:
                response = self.client.get(url, params=params)
                if response.status_code == 429:
                    # Rate limit hit, wait and retry
                    time.sleep(delay * 2)
                    delay *= 2
                    continue
                response.raise_for_status()
                return response.json()
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                if attempt == retries:
                    console.print(f"[bold red]Erro ao acessar {url}: {exc}[/bold red]")
                    raise
                time.sleep(delay)
                delay *= 1.5

        return None

    def download_file(self, url: str, destination_path: Path, chunk_size: int = 1024 * 1024) -> Path:
        """Streams and downloads a remote file (zip, parquet, csv) to local disk."""
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        console.print(f"[cyan]Baixando: {url} -> {destination_path.name}...[/cyan]")

        with self.client.stream("GET", url) as response:
            response.raise_for_status()
            total_bytes = int(response.headers.get("Content-Length", 0))
            downloaded = 0

            with open(destination_path, "wb") as f:
                for chunk in response.iter_bytes(chunk_size=chunk_size):
                    f.write(chunk)
                    downloaded += len(chunk)

        console.print(f"[green]✓ Download concluído: {destination_path} ({downloaded / (1024*1024):.2f} MB)[/green]")
        return destination_path

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
