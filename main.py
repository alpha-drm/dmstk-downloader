import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from typing import List, Optional, Tuple
from urllib.parse import unquote, urlparse

import browser_cookie3
import coloredlogs
import requests
from bs4 import BeautifulSoup
from colorama import Back, Fore, Style, init
from pyfiglet import Figlet

# --- CONFIGURATION & CONSTANTS ---
LOG_DIR = "logs"
DOWNLOAD_DIR = os.path.join(os.getcwd(), "Courses")
CACHE_DIR = os.path.join(os.getcwd(), "cache")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:143.0) Gecko/20100101 Firefox/143.0"
)

ISO_639_1_TO_2 = {
    "en": "eng",
    "es": "spa",
    "fr": "fra",
    "it": "ita",
    "pt": "por",
    "de": "deu",
    "tr": "tur",
    "ru": "rus",
    "id": "ind",
    "ro": "rom",
    "ja": "jpn",
    "ar": "ara",
    "nl": "nld",
    "pl": "pol",
    "sv": "swe",
    "fi": "fin",
    "no": "nor",
    "da": "dan",
    "cs": "ces",
    "el": "ell",
    "hi": "hin",
    "th": "tha",
    "vi": "vie",
}

logger = logging.getLogger("Dmstk-Dl")


# --- DATA MODELS ---
@dataclass
class LessonData:
    """Represents a single lesson or final project unit."""

    title: str
    url: Optional[str]
    basics_path: str
    unit_title: str
    type: str  # 'video_unit', 'final_project', 'final_project_locked'
    order_index: int

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "LessonData":
        return cls(**data)


# --- UTILITIES ---
def setup_logging():
    """Initializes the logging system with console and file handlers."""
    os.makedirs(LOG_DIR, exist_ok=True)
    log_filename = f"{time.strftime('%Y-%m-%d_%H-%M-%S')}.log"
    log_filepath = os.path.join(LOG_DIR, log_filename)

    log_format = "[%(asctime)s] [%(name)s] [%(levelname)s]: %(message)s"
    coloredlogs.install(level=logging.INFO, logger=logger, fmt=log_format)

    file_handler = logging.FileHandler(log_filepath, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(file_handler)


def banner():
    """Displays the CLI ASCII banner."""
    print()
    init(autoreset=True)
    text_ascii = "Dmstk-Dl"
    author = "Author: alphaDRM | CLI Version"
    width = shutil.get_terminal_size().columns
    padding = (width - len(author)) // 2
    font = Figlet(font="ansi_shadow", width=width, justify="center")
    print(Fore.RED + font.renderText(text_ascii))
    print(" " * padding + Back.RED + Fore.WHITE + author)
    print()


def display_summary(
    title: str,
    total_lessons: int,
    quality: str,
    langs: list,
    audios: list,
    output_path: str,
):
    """Displays a pre-download summary of the selected configuration."""
    print(Fore.CYAN + "\n" + "=" * 100)
    print(Fore.CYAN + " " * 40 + "DOWNLOAD SUMMARY")
    print(Fore.CYAN + "=" * 100)
    print(Fore.WHITE + f" Course Title : {Fore.GREEN}{title}")
    print(Fore.WHITE + f" Total Lessons: {Fore.GREEN}{total_lessons}")
    print(Fore.WHITE + f" Resolution   : {Fore.GREEN}{quality}p")
    print(
        Fore.WHITE
        + f" Subtitles    : {Fore.GREEN}{', '.join(langs) if langs else 'None'}"
    )
    print(
        Fore.WHITE
        + f" Extra Audio  : {Fore.GREEN}{', '.join(audios) if audios else 'None'}"
    )
    print(Fore.WHITE + f" Output Path  : {Fore.YELLOW}{output_path}")
    print(Fore.CYAN + "=" * 100 + Style.RESET_ALL + "\n")


def sanitize_filename(
    name: str, base_path: str, limit: int = 220, temp_suffix_len: int = 10
) -> str:
    """Removes invalid characters and shortens the filename if it exceeds OS limits."""
    cleaned = re.sub(r'[<>:"/\\|?*]', "", name).strip()
    base_path_abs = os.path.abspath(base_path)

    full_path = os.path.join(base_path_abs, cleaned)
    if len(full_path) <= (limit - temp_suffix_len):
        return cleaned.rstrip(" .")

    base_len = len(os.path.join(base_path_abs, ""))
    available = max(0, limit - base_len - temp_suffix_len)
    return cleaned[:available].rstrip(" .")


def iso639_2(lang: str) -> str:
    """Converts a 2-letter language code to a 3-letter code for FFmpeg metadata."""
    return ISO_639_1_TO_2.get(lang.lower(), lang.lower())


def get_cache_filepath(url: str) -> str:
    """Generates an MD5 hash of the URL to use as a cache filename."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, f"{url_hash}.json")


# --- CORE CLASSES ---
class SessionManager:
    """Handles HTTP session creation and cookie injection."""

    @staticmethod
    def create(
        browser: str, cookie_file: Optional[str] = None
    ) -> Optional[requests.Session]:
        """Creates a requests.Session injected with authentication cookies."""
        session = requests.Session()
        session.headers.update({"User-Agent": USER_AGENT})

        if cookie_file:
            return SessionManager._load_from_file(session, cookie_file)
        return SessionManager._load_from_browser(session, browser)

    @staticmethod
    def _load_from_file(
        session: requests.Session, path: str
    ) -> Optional[requests.Session]:
        if not os.path.exists(path):
            logger.error(f"Cookie file not found: {path}")
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            jar = requests.cookies.RequestsCookieJar()

            # Normalize list vs dict
            items = (
                data
                if isinstance(data, list)
                else [{"name": k, "value": v} for k, v in data.items()]
            )
            for c in items:
                if "name" in c and "value" in c:
                    jar.set(
                        c["name"],
                        c["value"],
                        domain=c.get("domain", ".domestika.org"),
                        path="/",
                    )

            session.cookies.update(jar)
            logger.info(f"Cookies successfully loaded from {path}")
            return session
        except Exception as e:
            logger.error(f"Error parsing JSON cookies: {e}")
            return None

    @staticmethod
    def _load_from_browser(
        session: requests.Session, browser_name: str
    ) -> Optional[requests.Session]:
        try:
            cj = getattr(browser_cookie3, browser_name)(domain_name="domestika")
            session.cookies.update({c.name: c.value for c in cj})
            logger.info(f"Cookies extracted from browser: {browser_name}")
            return session
        except Exception as e:
            logger.error(f"Error loading cookies from {browser_name}: {e}")
            return None


class DomestikaParser:
    """Handles HTML/JSON scraping and parsing to extract course structure."""

    def __init__(self, session: requests.Session):
        self.session = session

    def get_initial_props(self, url: str) -> dict:
        """Extracts the raw JSON from the __INITIAL_PROPS__ script tag."""
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
        except requests.RequestException:
            logger.warning(f"Failed to access URL: {url}")
            return {}

        soup = BeautifulSoup(resp.content, "html.parser")
        script = soup.find("script", string=re.compile(r"window\.__INITIAL_PROPS__"))

        if not script:
            return {}

        match = re.search(r"JSON\.parse\('(.+?)'\);", script.string)
        if match:
            clean_json = match.group(1).replace('\\"', '"').replace("\\\\", "\\")
            return json.loads(clean_json)

        return {}

    def extract_lessons_from_props(
        self, props: dict, unit_title: str, unit_url: str
    ) -> List[LessonData]:
        """Converts raw JSON properties into structured LessonData objects."""
        lessons = []

        try:
            resp = self.session.get(unit_url)
            resp.raise_for_status()
        except requests.RequestException:
            logger.warning(f"Failed to access unit URL: {unit_url}")
            return []

        soup = BeautifulSoup(resp.content, "html.parser")
        basics_text = ""
        is_dmstk_basics = soup.select_one("h2.h3.course-header-new__subtitle")
        if is_dmstk_basics:
            basics_text = is_dmstk_basics.get_text(strip=True)
            basics_text = re.sub(r"[^A-Za-z0-9\s-]", "", basics_text)

        # Standard Videos
        videos = props.get("videos", [])
        for i, el in enumerate(videos, 1):
            lessons.append(
                LessonData(
                    title=el["video"]["title"],
                    url=el["video"]["playbackURL"],
                    basics_path=basics_text,
                    unit_title=unit_title,
                    type="video_unit",
                    order_index=i,
                )
            )

        # Final Project
        next_index = len(videos) + 1
        if props.get("video"):
            check = self.session.get(unit_url, allow_redirects=False)
            if check.status_code == 200:
                lessons.append(
                    LessonData(
                        title="Final Project",
                        url=props["video"]["playbackURL"],
                        basics_path=basics_text,
                        unit_title=unit_title,
                        type="final_project",
                        order_index=next_index,
                    )
                )
            else:
                logger.warning(f"Locked final project detected at {unit_title}.")
                lessons.append(
                    LessonData(
                        title="Final Project (Locked)",
                        url=None,
                        basics_path=basics_text,
                        unit_title=unit_title,
                        type="final_project_locked",
                        order_index=next_index,
                    )
                )

        return lessons

    def parse_course_structure(
        self, course_url: str
    ) -> Tuple[str, Optional[str], List[LessonData], Optional[str]]:
        """
        Parses the entire course structure.
        Returns: (Course Title, Cover URL, List of Lessons, Resources URL)
        """
        resp = self.session.get(course_url)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")

        # 1. Title & Cover
        title_el = soup.find(
            "h1",
            class_=lambda c: (
                c and ("course-header-new__title" in c or "my-[10px]" in c)
            ),
        )
        course_title = title_el.text.strip() if title_el else "Unknown_Course"

        cover_url = None
        cover_match = re.search(
            r"https://imgproxy\.domestika\.org/unsafe/s:\d+:\d+/rs:fill/ex:true/el:true/plain/src://course-covers/\d+/\d+/\d+/\d+-original\.(jpg|jpeg|png|webp|avif)\?\d+",
            str(soup),
        )
        if cover_match:
            cover_url = cover_match.group(0)

        # 2. Additional Resources
        resources_url = None
        res_tag = soup.find(
            "li",
            string=lambda t: (
                t and ("Recursos adicionales" in t or "Additional Resources" in t)
            ),
        )
        if res_tag and res_tag.find("a"):
            resources_url = res_tag.find("a")["href"]

        # 3. Units & Lessons Extraction
        all_lessons = []
        units = soup.select("h4.unit-item__title a")

        if units:
            logger.info("Standard/Basics course structure detected.")
            for unit in units:
                u_title = unit.get_text(strip=True)
                u_link = unit.get("href")
                logger.info(f"Scraping unit: {u_title}")
                props = self.get_initial_props(u_link)
                all_lessons.extend(
                    self.extract_lessons_from_props(props, u_title, u_link)
                )
        else:
            logger.info("Intensive/Guided course structure detected.")
            first_unit_node = soup.select_one(
                "ul.units-list li.unit-subitem h5.unit-subitem__title a"
            )

            if first_unit_node:
                u_link = first_unit_node["href"]
                props = self.get_initial_props(u_link)
                all_lessons.extend(
                    self.extract_lessons_from_props(
                        props, "Contenido del Curso", u_link
                    )
                )

                fp_tag = soup.select_one('a[href$="/final_project"]')
                if fp_tag:
                    fp_link = fp_tag["href"]
                    fp_props = self.get_initial_props(fp_link)
                    all_lessons.extend(
                        self.extract_lessons_from_props(
                            fp_props, "Proyecto Final", fp_link
                        )
                    )
            else:
                logger.error("Could not detect known course structure.")

        return course_title, cover_url, all_lessons, resources_url


class ContentDownloader:
    """Manages the download processes using external tools like N_m3u8DL-RE and FFmpeg."""

    def __init__(self, session: requests.Session):
        self.session = session

    def download_file(self, url: str, path: str):
        """Standard file downloader for covers, zips, etc."""
        try:
            with self.session.get(url, stream=True) as r:
                r.raise_for_status()
                with open(path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
        except Exception as e:
            logger.error(f"Error downloading file from {url}: {e}")

    def download_resources(self, resources_url: str, save_dir: str):
        """Parses the resources page and downloads attachments."""
        try:
            resp = self.session.get(resources_url)
            soup = BeautifulSoup(resp.content, "html.parser")
            links = soup.select("h3.material-item__title a[href]")

            if not links:
                return

            os.makedirs(save_dir, exist_ok=True)
            logger.info(f"Downloading {len(links)} additional resources...")

            for link in links:
                file_url = link["href"]
                head = self.session.head(file_url, allow_redirects=True)
                filename = os.path.basename(urlparse(head.url).path)
                filename = unquote(filename)
                self.download_file(file_url, os.path.join(save_dir, filename))

        except Exception as e:
            logger.error(f"Failed to fetch additional resources: {e}")

    def download_video_lesson(
        self,
        lesson: LessonData,
        base_dir: str,
        file_prefix: str,
        quality: str,
        langs: list,
        audios: list,
    ):
        """Downloads the video stream using N_m3u8DL-RE and merges additional audio if required."""
        if lesson.type == "final_project_locked":
            logger.warning(f"[{lesson.title}] - Access denied (Locked). Skipping.")
            return

        unit_folder = sanitize_filename(lesson.unit_title, base_dir)
        save_path = (
            os.path.join(base_dir, lesson.basics_path, unit_folder)
            if lesson.basics_path
            else os.path.join(base_dir, unit_folder)
        )
        os.makedirs(save_path, exist_ok=True)

        filename_clean = sanitize_filename(lesson.title, save_path)
        full_filename = f"{file_prefix} - {filename_clean}"
        final_mp4 = os.path.join(save_path, f"{full_filename}.mp4")

        if os.path.exists(final_mp4):
            logger.warning(f"File already exists, skipping: '{full_filename}.mp4'")
            return

        logger.info(f"Processing Video: {full_filename}")

        # 1. N_m3u8DL-RE Command
        cmd = [
            "N_m3u8DL-RE",
            "-sv",
            f"res={quality}|720|540|360",
            "--save-dir",
            save_path,
            "--save-name",
            full_filename,
            "--tmp-dir",
            ".tmp",
            "--no-log",
            lesson.url,
        ]

        if langs:
            cmd += ["-ss", f"lang={'|'.join(langs)}:for=all"]
        if audios:
            cmd += ["-sa", f"lang={'|'.join(audios)}:for=all"]

        proc = subprocess.run(cmd, check=False)
        if proc.returncode != 0:
            logger.error(f"Download stream failed for {full_filename}")
            return

        # 2. Post-Processing Merge
        if audios:
            self._merge_audio_tracks(save_path, full_filename, audios)

    def _merge_audio_tracks(
        self, directory: str, filename_base: str, requested_audios: list
    ):
        """Searches for isolated .m4a files and muxes them into the main video using FFmpeg."""
        video_candidates = [
            f
            for f in os.listdir(directory)
            if f.startswith(filename_base) and f.endswith((".mp4", ".mkv"))
        ]
        if not video_candidates:
            return

        video_path = os.path.join(directory, video_candidates[0])
        temp_output = os.path.join(directory, f"{filename_base}_temp.mp4")

        cmd_ffmpeg = ["ffmpeg", "-y", "-i", video_path]
        maps = ["-map", "0:v", "-map", "0:a"]
        files_to_delete = []
        input_idx = 1
        found_extra = False

        for lang in requested_audios:
            lang_matches = [
                f
                for f in os.listdir(directory)
                if f.endswith(".m4a")
                and f.startswith(filename_base)
                and lang in f.lower()
            ]
            if lang_matches:
                audio_path = os.path.join(directory, lang_matches[0])
                cmd_ffmpeg += ["-i", audio_path]
                maps += ["-map", f"{input_idx}:a"]
                cmd_ffmpeg += [
                    f"-metadata:s:a:{input_idx}",
                    f"language={iso639_2(lang)}",
                ]

                files_to_delete.append(audio_path)
                input_idx += 1
                found_extra = True

        if found_extra:
            cmd_ffmpeg += maps + ["-c:v", "copy", "-c:a", "aac", temp_output]
            logger.info("Muxing additional audio tracks into the final video...")
            if subprocess.run(cmd_ffmpeg, check=False).returncode == 0:
                os.replace(temp_output, os.path.join(directory, f"{filename_base}.mp4"))
                for f in files_to_delete:
                    os.remove(f)


# --- MAIN EXECUTION ---
def main():
    parser = argparse.ArgumentParser(description="Dmstk-Downloader - Course Scraper")
    parser.add_argument("url", nargs="?", help="Course URL")
    parser.add_argument(
        "-b",
        "--browser",
        default="firefox",
        choices=["firefox", "chrome", "edge"],
        help="Browser to extract cookies from",
    )
    parser.add_argument("-c", "--cookies", help="Path to JSON cookies file")
    parser.add_argument(
        "-q",
        "--quality",
        default="1080",
        help="Target video resolution (e.g., 1080, 720)",
    )
    parser.add_argument(
        "-l",
        "--lang",
        action="append",
        help="Subtitle languages to download (e.g., es, en)",
    )
    parser.add_argument(
        "-a",
        "--audio",
        action="append",
        help="Additional audio tracks to download (e.g., es, en)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Force scrape by ignoring cached course structure",
    )

    args = parser.parse_args()

    langs = args.lang if args.lang else ["es|es_la"]
    audios = args.audio if args.audio else []

    setup_logging()
    banner()

    if not args.url:
        logger.error("A course URL is required.")
        return

    # Validate url
    regex = r"(https://www\.domestika\.org/.+?/courses/\d+-[-\w]+)(/course)?/?$"
    match = re.match(regex, args.url)
    if match:
        clean_url = match.group(1) + "/course"

    # 1. Login/Session Setup
    session = SessionManager.create(args.browser, args.cookies)
    if not session:
        return

    # 2. Check Cache or Parse Course
    cache_filepath = get_cache_filepath(clean_url)

    if os.path.exists(cache_filepath) and not args.no_cache:
        logger.info("Found cached course structure. Loading from cache...")
        try:
            with open(cache_filepath, "r", encoding="utf-8") as f:
                cached_data = json.load(f)

            title = cached_data.get("course_title", "Unknown_Course")
            cover = cached_data.get("cover_url")
            res_url = cached_data.get("resources_url")
            lessons = [LessonData.from_dict(l) for l in cached_data.get("lessons", [])]
        except Exception as e:
            logger.warning(
                f"Cache file corrupted or outdated ({e}). Forcing new scrape..."
            )
            args.no_cache = True

    if not os.path.exists(cache_filepath) or args.no_cache:
        parser_logic = DomestikaParser(session)
        logger.info("Analyzing course page...")
        try:
            title, cover, lessons, res_url = parser_logic.parse_course_structure(
                clean_url
            )

            # Save to Cache
            cache_payload = {
                "course_title": title,
                "url": clean_url,
                "cover_url": cover,
                "resources_url": res_url,
                "lessons": [l.to_dict() for l in lessons],
            }
            with open(cache_filepath, "w", encoding="utf-8") as f:
                json.dump(cache_payload, f, ensure_ascii=False, indent=4)
            logger.info("Course structure saved to cache.")

        except Exception as e:
            logger.critical(f"Failed to analyze the course: {e}")
            return

    # 3. Create Directories and Show Summary
    course_folder_name = sanitize_filename(title, DOWNLOAD_DIR)
    course_path = os.path.join(DOWNLOAD_DIR, course_folder_name)
    os.makedirs(course_path, exist_ok=True)

    display_summary(
        title=title,
        total_lessons=len(lessons),
        quality=args.quality,
        langs=langs,
        audios=audios,
        output_path=course_path,
    )

    # 4. Start Downloading
    downloader = ContentDownloader(session)

    # A. Cover Image
    if cover:
        ext = cover.split("?")[0].split(".")[-1]
        downloader.download_file(cover, os.path.join(course_path, f"cover.{ext}"))

    # B. Video Lessons
    for lesson in lessons:
        file_prefix = f"{lesson.order_index:02d}"
        downloader.download_video_lesson(
            lesson, course_path, file_prefix, args.quality, langs, audios
        )

    # C. Additional Resources
    if res_url:
        res_path = os.path.join(course_path, "Additional Resources")
        downloader.download_resources(res_url, res_path)
    else:
        logger.info("No additional resources found or accessible.")

    logger.info("Download process finished successfully.")


if __name__ == "__main__":
    main()
