"""
Download Queue Engine - FIFO queue for downloading freesound files

Downloads are processed one at a time to avoid freezing the UI.
Each download fetches metadata (including tags) from the freesound page,
then downloads the audio file, and finally triggers callbacks.

Usage:
    from download_queue import DownloadQueue, get_download_queue

    queue = get_download_queue()
    queue.download_complete.connect(on_download_complete)
    queue.enqueue(url, on_complete=callback)
"""

import re
import threading
import configparser
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue
from typing import Optional, List, Dict, Any, Callable

from PyQt6.QtCore import QObject, QThread, pyqtSignal
import requests

from freesound_manager import FreesoundManager, FreesoundError


def _get_ignore_ssl_setting() -> bool:
    """Read the ignore_ssl_errors setting from settings.ini."""
    settings_path = Path("settings.ini")
    if settings_path.exists():
        config = configparser.ConfigParser()
        config.read(settings_path)
        return config.get("downloads", "ignore_ssl_errors", fallback="false").lower() == "true"
    return False


@dataclass
class DownloadRequest:
    """A single download request with metadata."""
    url: str
    on_complete: Optional[Callable[[Path, Dict[str, Any]], None]] = None
    on_error: Optional[Callable[[str, Exception], None]] = None
    priority: int = 0  # Lower = higher priority (for future use)

    # Filled during processing
    local_path: Optional[Path] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Exception] = None


class DownloadWorker(QThread):
    """Background worker that processes downloads from the queue."""

    # Signals for communication with main thread
    download_started = pyqtSignal(str, str)  # url, display_name
    download_progress = pyqtSignal(str, int)  # url, percent (0-100)
    download_complete = pyqtSignal(str, str, dict)  # url, local_path, metadata
    download_error = pyqtSignal(str, str)  # url, error_message
    queue_empty = pyqtSignal()  # Emitted when queue becomes empty

    def __init__(self, request_queue: Queue):
        super().__init__()
        self._queue = request_queue
        self._running = True
        self._freesound = FreesoundManager()

    def run(self):
        """Main worker loop - processes downloads one at a time."""
        while self._running:
            try:
                # Block until a request is available (with timeout for shutdown check)
                try:
                    request: DownloadRequest = self._queue.get(timeout=0.5)
                except:
                    continue

                if request is None:  # Shutdown signal
                    break

                self._process_download(request)
                self._queue.task_done()

                # Check if queue is now empty
                if self._queue.empty():
                    self.queue_empty.emit()

            except Exception as e:
                print(f"Download worker error: {e}")

    def _process_download(self, request: DownloadRequest):
        """Process a single download request."""
        url = request.url

        try:
            # First, fetch metadata including tags from the webpage
            metadata = self._fetch_full_metadata(url)
            display_name = metadata.get("sound_name", "Unknown").replace("_", " ")

            self.download_started.emit(url, display_name)

            # Check if already cached
            creator, sound_id = self._freesound.parse_url(url)
            cached = self._freesound._find_cached_file(creator, sound_id)

            if cached:
                # Already downloaded - just return metadata
                request.local_path = cached
                request.metadata = metadata
                self.download_complete.emit(url, str(cached), metadata)
            else:
                # Download the file
                sound_name = metadata.get("sound_name", f"sound_{sound_id}")
                local_path = self._freesound._download_sound(url, creator, sound_id, sound_name)

                request.local_path = local_path
                request.metadata = metadata
                self.download_complete.emit(url, str(local_path), metadata)

            # Call the completion callback if provided
            if request.on_complete:
                try:
                    request.on_complete(request.local_path, request.metadata)
                except Exception as e:
                    print(f"Download callback error: {e}")

        except Exception as e:
            request.error = e
            error_msg = str(e)
            self.download_error.emit(url, error_msg)

            # Call the error callback if provided
            if request.on_error:
                try:
                    request.on_error(url, e)
                except Exception:
                    pass

    def _fetch_full_metadata(self, url: str) -> Dict[str, Any]:
        """
        Fetch full metadata from freesound page including tags.

        Returns dict with:
            - creator: username of sound creator
            - sound_id: freesound ID number
            - sound_name: name of the sound (sanitized for filenames)
            - display_name: human-readable name
            - tags: list of tags from the freesound page
            - description: sound description (if available)
        """
        creator, sound_id = self._freesound.parse_url(url)

        metadata = {
            "creator": creator,
            "sound_id": sound_id,
            "sound_name": f"sound_{sound_id}",
            "display_name": f"Sound {sound_id}",
            "tags": [],
            "description": "",
        }

        try:
            verify_ssl = not _get_ignore_ssl_setting()
            response = requests.get(url, timeout=15, verify=verify_ssl)
            response.raise_for_status()
            html = response.text

            # Extract title
            title_match = re.search(r'<title>([^<]+)</title>', html, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
                if " - Freesound" in title:
                    title = title.replace(" - Freesound", "")
                metadata["display_name"] = title
                metadata["sound_name"] = self._freesound._sanitize_filename(title)

            # Extract tags - freesound uses a tags section with links
            # Pattern: <a href="/browse/tags/tagname/">tagname</a>
            tag_patterns = [
                # Pattern 1: Extract tag from /browse/tags/tagname/ URL path
                r'href="/browse/tags/([^/"]+)/"',
                # Pattern 2: class="tag" links
                r'class="tag[^"]*"[^>]*>([^<]+)</a>',
                # Pattern 3: data-tag attributes
                r'data-tag="([^"]+)"',
            ]

            tags = set()
            for pattern in tag_patterns:
                matches = re.findall(pattern, html, re.IGNORECASE)
                for match in matches:
                    # Clean up tag
                    tag = match.strip().lower()
                    # Skip empty or very long tags
                    if tag and len(tag) < 50:
                        # URL decode if needed
                        tag = tag.replace('%20', ' ').replace('+', ' ')
                        tags.add(tag)

            metadata["tags"] = list(tags)

            # Extract description (optional)
            desc_match = re.search(
                r'<div[^>]*id="sound_description"[^>]*>([^<]*(?:<[^>]+>[^<]*)*)</div>',
                html,
                re.IGNORECASE | re.DOTALL
            )
            if desc_match:
                desc = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()
                metadata["description"] = desc[:500]  # Limit length

        except Exception as e:
            print(f"Warning: Could not fetch full metadata for {url}: {e}")

        return metadata

    def stop(self):
        """Signal the worker to stop."""
        self._running = False


class DownloadQueue(QObject):
    """
    FIFO download queue manager.

    Downloads are queued and processed one at a time in a background thread.
    This prevents UI freezing when multiple downloads are needed.

    Signals:
        download_started(url, display_name): A download has begun
        download_complete(url, local_path, metadata): A download finished successfully
        download_error(url, error_message): A download failed
        queue_empty(): The queue has been fully processed
        queue_size_changed(size): The queue size changed
    """

    # Forwarded signals from worker
    download_started = pyqtSignal(str, str)  # url, display_name
    download_complete = pyqtSignal(str, str, dict)  # url, local_path, metadata
    download_error = pyqtSignal(str, str)  # url, error_message
    queue_empty = pyqtSignal()
    queue_size_changed = pyqtSignal(int)  # current queue size

    def __init__(self):
        super().__init__()
        self._queue: Queue[DownloadRequest] = Queue()
        self._worker: Optional[DownloadWorker] = None
        self._pending_urls: set = set()  # Track URLs currently in queue
        self._lock = threading.Lock()

    def _ensure_worker(self):
        """Start the worker thread if not running."""
        if self._worker is None or not self._worker.isRunning():
            self._worker = DownloadWorker(self._queue)
            # Connect signals
            self._worker.download_started.connect(self._on_download_started)
            self._worker.download_complete.connect(self._on_download_complete)
            self._worker.download_error.connect(self._on_download_error)
            self._worker.queue_empty.connect(self.queue_empty.emit)
            self._worker.start()

    def _on_download_started(self, url: str, display_name: str):
        """Forward download started signal."""
        self.download_started.emit(url, display_name)

    def _on_download_complete(self, url: str, local_path: str, metadata: dict):
        """Handle download completion."""
        with self._lock:
            self._pending_urls.discard(url)
            self.queue_size_changed.emit(len(self._pending_urls))
        self.download_complete.emit(url, local_path, metadata)

    def _on_download_error(self, url: str, error_msg: str):
        """Handle download error."""
        with self._lock:
            self._pending_urls.discard(url)
            self.queue_size_changed.emit(len(self._pending_urls))
        self.download_error.emit(url, error_msg)

    def enqueue(
        self,
        url: str,
        on_complete: Optional[Callable[[Path, Dict[str, Any]], None]] = None,
        on_error: Optional[Callable[[str, Exception], None]] = None
    ) -> bool:
        """
        Add a download to the queue.

        Args:
            url: Freesound URL to download
            on_complete: Callback(local_path, metadata) when download succeeds
            on_error: Callback(url, exception) when download fails

        Returns:
            True if added to queue, False if already pending
        """
        with self._lock:
            if url in self._pending_urls:
                return False  # Already in queue
            self._pending_urls.add(url)
            self.queue_size_changed.emit(len(self._pending_urls))

        request = DownloadRequest(
            url=url,
            on_complete=on_complete,
            on_error=on_error
        )
        self._queue.put(request)
        self._ensure_worker()
        return True

    def enqueue_many(
        self,
        urls: List[str],
        on_each_complete: Optional[Callable[[Path, Dict[str, Any]], None]] = None,
        on_all_complete: Optional[Callable[[], None]] = None
    ) -> int:
        """
        Add multiple downloads to the queue.

        Args:
            urls: List of freesound URLs to download
            on_each_complete: Callback for each individual download
            on_all_complete: Callback when all downloads in this batch finish

        Returns:
            Number of new downloads added (excludes duplicates)
        """
        added = 0
        remaining = [0]  # Use list to allow modification in closure

        def wrap_callback(local_path, metadata):
            if on_each_complete:
                on_each_complete(local_path, metadata)
            remaining[0] -= 1
            if remaining[0] <= 0 and on_all_complete:
                on_all_complete()

        for url in urls:
            if self.enqueue(url, on_complete=wrap_callback):
                added += 1
                remaining[0] += 1

        # If nothing was added (all cached), fire completion immediately
        if added == 0 and on_all_complete:
            on_all_complete()

        return added

    def is_pending(self, url: str) -> bool:
        """Check if a URL is currently in the download queue."""
        with self._lock:
            return url in self._pending_urls

    def pending_count(self) -> int:
        """Get the number of pending downloads."""
        with self._lock:
            return len(self._pending_urls)

    def clear(self):
        """Clear all pending downloads (doesn't stop current download)."""
        with self._lock:
            # Empty the queue
            while not self._queue.empty():
                try:
                    self._queue.get_nowait()
                except:
                    break
            self._pending_urls.clear()
            self.queue_size_changed.emit(0)

    def shutdown(self):
        """Shut down the download queue worker."""
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._queue.put(None)  # Shutdown signal
            # Wait briefly, then force terminate if still running
            if not self._worker.wait(1000):  # Wait up to 1 second
                self._worker.terminate()
                self._worker.wait(500)  # Brief wait after terminate


# Singleton instance
_download_queue: Optional[DownloadQueue] = None
_queue_lock = threading.Lock()


def get_download_queue() -> DownloadQueue:
    """Get the global download queue instance."""
    global _download_queue
    with _queue_lock:
        if _download_queue is None:
            _download_queue = DownloadQueue()
        return _download_queue
