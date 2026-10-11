#!/usr/bin/env python3
"""
Prefora Questions Scraper
=========================
A robust, asynchronous, background-capable Python script to scrape questions
from the questions endpoint for all subjects, handle pagination, and store them
efficiently into the custom database table.

Features:
- Full pagination handling (page-based, limit-based, and partition-based by year & exam type)
- High-efficiency asynchronous I/O with concurrency pooling and rate limiting
- Batch PostgreSQL upsert operations with conflict handling and sequence synchronization
- In-memory duplicate deduplication
- Background daemon mode with configurable sync interval and PID tracking
- Graceful shutdown handling (SIGINT/SIGTERM) with buffered data flush
- Resumable checkpointing (remembers scraped subjects and partitions across restarts)
- Comprehensive logging and progress metrics
"""

import argparse
import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

# Add workspace root to sys.path so modules and models can be imported
workspace_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(workspace_root))

from common.config import settings
from common.database import AsyncSessionLocal, engine
from models.question_model import Question
from modules.subjects.service import DEFAULT_SUBJECTS

# Map canonical subject names to API slugs (and known aliases)
SUBJECT_API_SLUGS: dict[str, list[str]] = {
    "english": ["english", "use-of-english", "english-language"],
    "mathematics": ["mathematics", "maths"],
    "physics": ["physics"],
    "chemistry": ["chemistry"],
    "biology": ["biology"],
    "economics": ["economics"],
    "government": ["government"],
    "commerce": ["commerce"],
    "accounting": ["accounting", "financial-accounting"],
    "crs": ["crk", "crs", "christian-religious-knowledge"],
    "irs": ["irk", "irs", "islamic-religious-knowledge"],
    "geography": ["geography"],
    "civiceducation": ["civiledu", "civic-education", "civic"],
    "insurance": ["insurance"],
    "currentaffairs": ["currentaffairs", "general-paper"],
    "history": ["history"],
    "literature": ["englishlit", "literature", "literature-in-english"],
    "agricultural-science": ["agricultural-science", "agric", "agric-science"],
}

# Standard exam bodies in Nigeria
EXAM_TYPES = ["utme", "waec", "neco", "post-utme"]

logger = logging.getLogger("questions_scraper")


def setup_logging(log_file: str | None = None, log_level: str = "INFO") -> None:
    """Configures console and optional file logging."""
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(process)d] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def normalize_question_item(raw: dict[str, Any], canonical_subject: str) -> dict[str, Any] | None:
    """
    Normalizes a question item from API response into the Question model schema.
    """
    if not isinstance(raw, dict):
        return None

    raw_id = raw.get("id")
    if raw_id is None:
        return None

    try:
        qid = int(raw_id)
    except (ValueError, TypeError):
        return None

    q_text = str(raw.get("question") or "").strip()
    if not q_text:
        return None

    options = raw.get("option")
    if not isinstance(options, dict):
        options = {}

    has_passage_raw = raw.get("hasPassage", raw.get("has_passage"))
    has_passage: bool | None = None
    if has_passage_raw is not None:
        if isinstance(has_passage_raw, bool):
            has_passage = has_passage_raw
        elif isinstance(has_passage_raw, (int, str)):
            has_passage = str(has_passage_raw).strip() in ("1", "true", "True")

    return {
        "external_id": qid,
        "subject": canonical_subject,
        "question": q_text,
        "option": options,
        "section": raw.get("section") or None,
        "image": (raw.get("image") or None) if isinstance(raw.get("image"), str) else None,
        "answer": str(raw.get("answer") or "").strip() or None,
        "solution": raw.get("solution") or None,
        "examtype": (raw.get("examtype") or "").strip().lower() or None,
        "examyear": str(raw.get("examyear") or "").strip() or None,
        "has_passage": has_passage,
        "category": raw.get("category") or canonical_subject,
        "isDeleted": False,
    }


class QuestionScraper:
    def __init__(
        self,
        source: str = "aloc",
        api_url: str | None = None,
        aloc_url: str = "https://questions.aloc.com.ng/api/v2",
        token: str | None = None,
        subjects: list[str] | None = None,
        years: list[int] | None = None,
        exam_types: list[str] | None = None,
        concurrency: int = 5,
        batch_size: int = 50,
        delay: float = 0.1,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        checkpoint_file: str = "scripts/scraper_checkpoint.json",
        resume: bool = True,
        dry_run: bool = False,
        update_existing: bool = False,
    ):
        self.source = source
        self.api_url = api_url or "http://localhost:8000/questions"
        self.aloc_url = aloc_url.rstrip("/")
        self.token = token or settings.aloc_access_token
        self.subjects = subjects or list(SUBJECT_API_SLUGS.keys())
        self.years = years or list(range(2001, 2025))
        self.exam_types = exam_types or EXAM_TYPES
        self.concurrency = concurrency
        self.batch_size = batch_size
        self.delay = delay
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.checkpoint_file = checkpoint_file
        self.resume = resume
        self.dry_run = dry_run
        self.update_existing = update_existing

        self.semaphore = asyncio.Semaphore(self.concurrency)
        self.known_items: set[tuple[str, int]] = set()
        self.write_buffer: list[dict[str, Any]] = []
        self.db_lock = asyncio.Lock()

        self._stop_requested = False
        self.checkpoint_data: dict[str, Any] = {
            "completed_partitions": [],
            "stats": {"total_fetched": 0, "total_inserted": 0, "total_skipped": 0},
            "last_updated": None,
        }

        # Per-run statistics
        self.stats = {
            "fetched": 0,
            "inserted": 0,
            "skipped": 0,
            "errors": 0,
            "subject_breakdown": {s: 0 for s in self.subjects},
        }

    def request_stop(self) -> None:
        """Flags the scraper for clean termination."""
        logger.info("Shutdown signal received! Gracefully finishing active batches...")
        self._stop_requested = True

    def load_checkpoint(self) -> None:
        """Loads state checkpoint from file if present and resume=True."""
        if not self.resume:
            logger.info("Resume disabled; starting fresh scraper cycle.")
            return

        cp_path = Path(self.checkpoint_file)
        if cp_path.exists():
            try:
                with open(cp_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.checkpoint_data.update(data)
                completed_count = len(self.checkpoint_data.get("completed_partitions", []))
                logger.info(f"Loaded checkpoint with {completed_count} completed partitions.")
            except Exception as e:
                logger.warning(f"Failed to load checkpoint file: {e}")

    def save_checkpoint(self) -> None:
        """Persists current state to checkpoint file."""
        try:
            self.checkpoint_data["last_updated"] = datetime.now(timezone.utc).isoformat()
            self.checkpoint_data["stats"] = {
                "total_fetched": self.stats["fetched"],
                "total_inserted": self.stats["inserted"],
                "total_skipped": self.stats["skipped"],
            }
            Path(self.checkpoint_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(self.checkpoint_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")

    async def initialize_known_ids(self) -> None:
        """Loads existing question (subject, external_id) keys from DB to prevent duplicate queries and inserts."""
        if self.dry_run:
            logger.info("Dry run mode: skipping database known ID preload.")
            return

        try:
            async with AsyncSessionLocal() as session:
                logger.info("Preloading existing question keys from database...")
                stmt = select(Question.subject, Question.external_id).where(Question.external_id.is_not(None))
                res = await session.execute(stmt)
                self.known_items = {(row[0], row[1]) for row in res.all()}
                logger.info(f"Preloaded {len(self.known_items)} existing question keys from database.")
        except Exception as e:
            logger.error(f"Failed to query existing question keys from DB: {e}")

    async def flush_buffer(self, force: bool = False) -> None:
        """Flushes the in-memory write buffer to PostgreSQL in batch."""
        async with self.db_lock:
            if not self.write_buffer or (len(self.write_buffer) < self.batch_size and not force):
                return

            records = list(self.write_buffer)
            self.write_buffer.clear()

        if self.dry_run:
            logger.info(f"[DRY-RUN] Would insert {len(records)} questions into database.")
            self.stats["inserted"] += len(records)
            return

        try:
            async with AsyncSessionLocal() as session:
                stmt = pg_insert(Question).values(records)

                if self.update_existing:
                    stmt = stmt.on_conflict_do_update(
                        constraint="uq_question_subject_external_id",
                        set_={
                            "question": stmt.excluded.question,
                            "option": stmt.excluded.option,
                            "section": stmt.excluded.section,
                            "image": stmt.excluded.image,
                            "answer": stmt.excluded.answer,
                            "solution": stmt.excluded.solution,
                            "examtype": stmt.excluded.examtype,
                            "examyear": stmt.excluded.examyear,
                            "has_passage": stmt.excluded.has_passage,
                            "category": stmt.excluded.category,
                            "updated_at": func.now(),
                        },
                    )
                else:
                    stmt = stmt.on_conflict_do_nothing(constraint="uq_question_subject_external_id")

                await session.execute(stmt)
                await session.commit()

                self.stats["inserted"] += len(records)
                logger.info(
                    f"Successfully saved batch of {len(records)} questions to DB. "
                    f"(Total inserted: {self.stats['inserted']})"
                )
        except Exception as e:
            logger.error(f"Database error writing batch: {e}")
            self.stats["errors"] += 1
            # Re-queue on failure so items aren't lost
            async with self.db_lock:
                self.write_buffer.extend(records)

    async def enqueue_question(self, question: dict[str, Any]) -> None:
        """Queues a question for batch insertion and updates counts."""
        ext_id = question.get("external_id")
        subject = question["subject"]
        item_key = (subject, ext_id) if ext_id is not None else None

        if item_key and item_key in self.known_items and not self.update_existing:
            self.stats["skipped"] += 1
            return

        if item_key:
            self.known_items.add(item_key)
        self.stats["subject_breakdown"][subject] = (
            self.stats["subject_breakdown"].get(subject, 0) + 1
        )

        async with self.db_lock:
            self.write_buffer.append(question)

        if len(self.write_buffer) >= self.batch_size:
            await self.flush_buffer()

    async def _fetch_with_retry(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """Executes an HTTP GET with retry and rate-limiting."""
        for attempt in range(1, self.max_retries + 1):
            if self._stop_requested:
                return None
            try:
                response = await client.get(url, params=params, headers=headers)

                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    backoff = self.retry_delay * (2 ** (attempt - 1))
                    logger.warning(
                        f"Rate limit hit (429) on {url}. Backing off for {backoff:.1f}s..."
                    )
                    await asyncio.sleep(backoff)
                elif response.status_code in (404, 400):
                    # Partition has no questions or invalid combination
                    return None
                else:
                    logger.warning(
                        f"HTTP {response.status_code} for {url} (attempt {attempt}/{self.max_retries})"
                    )
                    await asyncio.sleep(self.retry_delay)
            except (httpx.RequestError, httpx.TimeoutException) as e:
                logger.warning(
                    f"Network error on {url} (attempt {attempt}/{self.max_retries}): {e}"
                )
                await asyncio.sleep(self.retry_delay * attempt)
            except Exception as e:
                logger.error(f"Unexpected error requesting {url}: {e}")
                return None

        self.stats["errors"] += 1
        return None

    async def scrape_aloc_partition(
        self,
        client: httpx.AsyncClient,
        subject: str,
        api_slug: str,
        year: int | None = None,
        exam_type: str | None = None,
    ) -> int:
        """
        Fetches questions for a specific partition (subject, year, exam_type) from ALOC v2 API.
        """
        partition_key = f"{subject}:{year or 'all'}:{exam_type or 'all'}"
        if partition_key in self.checkpoint_data.get("completed_partitions", []):
            return 0

        async with self.semaphore:
            if self._stop_requested:
                return 0

            url = f"{self.aloc_url}/q/50"
            params: dict[str, Any] = {"subject": api_slug}
            if year:
                params["year"] = str(year)
            if exam_type:
                params["type"] = exam_type

            headers = {
                "AccessToken": self.token,
                "Accept": "application/json",
            }

            data = await self._fetch_with_retry(client, url, params=params, headers=headers)
            if self.delay > 0:
                await asyncio.sleep(self.delay)

            if not data or not isinstance(data, dict):
                return 0

            raw_items = data.get("data", [])
            if isinstance(raw_items, dict):
                raw_items = [raw_items]
            elif not isinstance(raw_items, list):
                raw_items = []

            count = 0
            for item in raw_items:
                norm = normalize_question_item(item, subject)
                if norm:
                    self.stats["fetched"] += 1
                    await self.enqueue_question(norm)
                    count += 1

            if count > 0:
                logger.debug(
                    f"[{subject}] Year {year or 'any'} ({exam_type or 'any'}): +{count} questions"
                )

            self.checkpoint_data.setdefault("completed_partitions", []).append(partition_key)
            return count

    async def scrape_backend_subject(
        self,
        client: httpx.AsyncClient,
        subject: str,
        year: int | None = None,
        exam_type: str | None = None,
    ) -> int:
        """
        Fetches paginated questions from the backend /questions endpoint.
        Handles page-based pagination (page=1, page=2, ...).
        """
        page = 1
        limit = 50
        total_partition_questions = 0

        while not self._stop_requested:
            async with self.semaphore:
                params: dict[str, Any] = {
                    "subject": subject,
                    "limit": limit,
                    "page": page,
                }
                if year:
                    params["year"] = str(year)
                if exam_type:
                    params["type"] = exam_type

                headers = {"Accept": "application/json"}
                data = await self._fetch_with_retry(client, self.api_url, params=params, headers=headers)
                if self.delay > 0:
                    await asyncio.sleep(self.delay)

                if not data or not isinstance(data, dict):
                    break

                res_data = data.get("data", {})
                if isinstance(res_data, dict):
                    raw_items = res_data.get("data", [])
                elif isinstance(res_data, list):
                    raw_items = res_data
                else:
                    raw_items = []

                if not raw_items:
                    break

                page_count = 0
                for item in raw_items:
                    norm = normalize_question_item(item, subject)
                    if norm:
                        self.stats["fetched"] += 1
                        await self.enqueue_question(norm)
                        page_count += 1

                total_partition_questions += page_count

                # Inspect pagination metadata
                pagination = data.get("pagination") or {}
                total_pages = pagination.get("total_pages")
                if total_pages and page >= total_pages:
                    break

                # If fewer items returned than limit, we've reached the end
                if len(raw_items) < limit:
                    break

                page += 1

        return total_partition_questions

    async def scrape_aloc_batch_pool(
        self,
        client: httpx.AsyncClient,
        subject: str,
        api_slug: str,
        max_batches: int = 15,
        stagnant_threshold: int = 3,
    ) -> int:
        """
        Performs random pool discovery via /m?subject={slug} to capture unindexed questions.
        Stops when consecutive batches return zero new questions.
        """
        stagnant_count = 0
        total_discovered = 0

        for b in range(1, max_batches + 1):
            if self._stop_requested:
                break

            async with self.semaphore:
                url = f"{self.aloc_url}/m"
                params = {"subject": api_slug}
                headers = {"AccessToken": self.token, "Accept": "application/json"}

                data = await self._fetch_with_retry(client, url, params=params, headers=headers)
                if self.delay > 0:
                    await asyncio.sleep(self.delay)

                if not data or not isinstance(data, dict):
                    break

                raw_items = data.get("data", [])
                if not isinstance(raw_items, list) or not raw_items:
                    break

                new_in_batch = 0
                for item in raw_items:
                    norm = normalize_question_item(item, subject)
                    if norm:
                        qid = norm.get("external_id")
                        self.stats["fetched"] += 1
                        item_key = (subject, qid) if qid is not None else None
                        if item_key is None or item_key not in self.known_items:
                            new_in_batch += 1
                            await self.enqueue_question(norm)

                total_discovered += new_in_batch
                if new_in_batch == 0:
                    stagnant_count += 1
                else:
                    stagnant_count = 0

                if stagnant_count >= stagnant_threshold:
                    logger.debug(f"[{subject}] Pool discovery reached saturation after {b} batches.")
                    break

        return total_discovered

    async def scrape_all_subjects(self) -> None:
        """Runs the complete scraping cycle across all subjects and partitions."""
        start_time = time.time()
        logger.info(
            f"Starting scraper cycle. Source: '{self.source}', Subjects: {len(self.subjects)}, "
            f"Years: {len(self.years)}, Concurrency: {self.concurrency}"
        )

        await self.initialize_known_ids()
        self.load_checkpoint()

        limits = httpx.Limits(
            max_connections=self.concurrency * 2,
            max_keepalive_connections=self.concurrency,
        )
        timeout = httpx.Timeout(20.0, connect=10.0)

        async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
            for subject in self.subjects:
                if self._stop_requested:
                    break

                logger.info(f"=== Scraping Subject: {subject.upper()} ===")
                subject_start_time = time.time()
                slugs = SUBJECT_API_SLUGS.get(subject, [subject])
                primary_slug = slugs[0]

                tasks = []
                if self.source == "backend":
                    # Scraping via backend /questions endpoint
                    for year in self.years:
                        for et in self.exam_types:
                            tasks.append(
                                self.scrape_backend_subject(
                                    client, subject=subject, year=year, exam_type=et
                                )
                            )
                else:
                    # Scraping directly via ALOC API
                    for year in self.years:
                        for et in self.exam_types:
                            tasks.append(
                                self.scrape_aloc_partition(
                                    client,
                                    subject=subject,
                                    api_slug=primary_slug,
                                    year=year,
                                    exam_type=et,
                                )
                            )

                # Execute partitioned tasks with concurrency control
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for res in results:
                    if isinstance(res, Exception):
                        logger.error(f"Error during partition scraping: {res}")
                        self.stats["errors"] += 1

                # If scraping ALOC directly, also execute pool discovery to catch unindexed items
                if self.source != "backend" and not self._stop_requested:
                    pool_found = await self.scrape_aloc_batch_pool(
                        client, subject=subject, api_slug=primary_slug
                    )
                    logger.info(f"[{subject}] Pool discovery contributed +{pool_found} extra questions.")

                # Flush any remaining items for this subject
                await self.flush_buffer(force=True)
                self.save_checkpoint()

                sub_time = time.time() - subject_start_time
                count_for_subj = self.stats["subject_breakdown"].get(subject, 0)
                logger.info(
                    f"Completed subject '{subject}' in {sub_time:.1f}s. "
                    f"New questions stored: {count_for_subj}"
                )

        # Final flush on cycle completion
        await self.flush_buffer(force=True)
        self.save_checkpoint()

        total_time = time.time() - start_time
        self.print_summary(total_time)

    def print_summary(self, elapsed: float) -> None:
        """Prints formatted summary statistics."""
        logger.info("==================================================")
        logger.info("              SCRAPER RUN SUMMARY                 ")
        logger.info("==================================================")
        logger.info(f"Elapsed Time    : {elapsed:.2f} seconds ({elapsed / 60:.1f} mins)")
        logger.info(f"Total Fetched   : {self.stats['fetched']}")
        logger.info(f"Total Inserted  : {self.stats['inserted']}")
        logger.info(f"Total Skipped   : {self.stats['skipped']} (duplicates)")
        logger.info(f"Total Errors    : {self.stats['errors']}")
        logger.info("--------------------------------------------------")
        logger.info("Breakdown by Subject:")
        for subj, cnt in self.stats["subject_breakdown"].items():
            logger.info(f"  - {subj:20}: {cnt} questions")
        logger.info("==================================================")


def write_pid_file(pid_file: str) -> None:
    """Writes the current process PID to file."""
    try:
        Path(pid_file).parent.mkdir(parents=True, exist_ok=True)
        with open(pid_file, "w") as f:
            f.write(str(os.getpid()))
    except Exception as e:
        logger.warning(f"Could not write PID file {pid_file}: {e}")


def remove_pid_file(pid_file: str) -> None:
    """Removes the PID file on exit."""
    try:
        p = Path(pid_file)
        if p.exists():
            p.unlink()
    except Exception:
        pass


async def run_scraper(args: argparse.Namespace) -> None:
    """Entry point for the async scraper execution."""
    raw_subjects = [s.strip().lower() for s in args.subjects.split(",")] if args.subjects else None
    alias_map = {
        "math": "mathematics",
        "maths": "mathematics",
        "crk": "crs",
        "irk": "irs",
        "civic": "civiceducation",
        "civiledu": "civiceducation",
        "lit": "literature",
        "englishlit": "literature",
        "agric": "agricultural-science",
        "agric-science": "agricultural-science",
    }
    subjects = [alias_map.get(s, s) for s in raw_subjects] if raw_subjects else None

    years: list[int] = []
    if args.years:
        for part in args.years.split(","):
            part = part.strip()
            if "-" in part:
                start, end = part.split("-", 1)
                years.extend(range(int(start), int(end) + 1))
            else:
                years.append(int(part))
    else:
        years = list(range(2001, 2025))

    exam_types = [et.strip().lower() for et in args.exam_types.split(",")] if args.exam_types else None

    scraper = QuestionScraper(
        source=args.source,
        api_url=args.api_url,
        aloc_url=args.aloc_url,
        token=args.token,
        subjects=subjects,
        years=years,
        exam_types=exam_types,
        concurrency=args.concurrency,
        batch_size=args.batch_size,
        delay=args.delay,
        max_retries=args.max_retries,
        checkpoint_file=args.checkpoint_file,
        resume=not args.no_resume,
        dry_run=args.dry_run,
        update_existing=args.update_existing,
    )

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, scraper.request_stop)
        except NotImplementedError:
            # Signal handlers not implemented on some non-Unix platforms
            pass

    if args.pid_file:
        write_pid_file(args.pid_file)

    try:
        if args.daemon:
            logger.info(
                f"Starting Question Scraper in DAEMON mode (Interval: {args.interval}s / "
                f"{args.interval / 3600:.1f} hours)"
            )
            cycle = 1
            while not scraper._stop_requested:
                logger.info(f"--- Daemon Cycle #{cycle} Starting ---")
                await scraper.scrape_all_subjects()
                if scraper._stop_requested:
                    break
                logger.info(f"Cycle #{cycle} finished. Sleeping for {args.interval} seconds...")
                cycle += 1
                try:
                    await asyncio.sleep(args.interval)
                except asyncio.CancelledError:
                    break
        else:
            await scraper.scrape_all_subjects()
    finally:
        if args.pid_file:
            remove_pid_file(args.pid_file)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scrape and synchronize questions into the custom database table with pagination support."
    )
    parser.add_argument(
        "--source",
        choices=["aloc", "backend", "auto"],
        default="aloc",
        help="Source of questions: 'aloc' (ALOC API, default) or 'backend' (Prefora /questions endpoint).",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:8000/questions",
        help="Backend questions endpoint URL when --source=backend.",
    )
    parser.add_argument(
        "--aloc-url",
        default="https://questions.aloc.com.ng/api/v2",
        help="ALOC API base URL.",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="ALOC AccessToken (defaults to ALOC_ACCESS_TOKEN from .env).",
    )
    parser.add_argument(
        "--subjects",
        default=None,
        help="Comma-separated subjects (e.g. 'english,mathematics,physics'). Defaults to all.",
    )
    parser.add_argument(
        "--years",
        default="2001-2024",
        help="Comma-separated years or range (e.g. '2005-2024' or '2015,2016,2017').",
    )
    parser.add_argument(
        "--exam-types",
        default="utme,waec,neco,post-utme",
        help="Comma-separated exam types (default: 'utme,waec,neco,post-utme').",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Max concurrent async requests (default: 5).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Database insert batch size (default: 50).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.1,
        help="Delay between requests in seconds to respect rate limits (default: 0.1).",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Max retries per request on failure (default: 3).",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run continuously in background daemon mode.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=86400,
        help="Seconds between scraping cycles in daemon mode (default: 86400 = 24h).",
    )
    parser.add_argument(
        "--pid-file",
        default="scripts/scraper.pid",
        help="File path to store process ID (default: 'scripts/scraper.pid').",
    )
    parser.add_argument(
        "--checkpoint-file",
        default="scripts/scraper_checkpoint.json",
        help="File path to persist scraping state for resuming (default: 'scripts/scraper_checkpoint.json').",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignore existing checkpoint and start from scratch.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape and process without writing to the database.",
    )
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Update existing rows on primary key conflict instead of skipping.",
    )
    parser.add_argument(
        "--log-file",
        default="scraper.log",
        help="Path to write log output (default: 'scraper.log').",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity level (default: INFO).",
    )

    args = parser.parse_args()
    setup_logging(log_file=args.log_file, log_level=args.log_level)

    try:
        asyncio.run(run_scraper(args))
    except KeyboardInterrupt:
        logger.info("Process interrupted by user. Exiting cleanly.")


if __name__ == "__main__":
    main()
