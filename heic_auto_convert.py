import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image
from pillow_heif import register_heif_opener

load_dotenv()
register_heif_opener()


def get_app_base_dir() -> Path:
    return Path(os.getenv("USERPROFILE", str(Path.home()))) / "HEIC2JPG"


APP_BASE_DIR = get_app_base_dir()

WATCH_FOLDER = Path(os.getenv("WATCH_FOLDER", str(APP_BASE_DIR / "incoming")))
OUTPUT_FOLDER = Path(os.getenv("OUTPUT_FOLDER", str(APP_BASE_DIR / "converted")))
ARCHIVE_FOLDER = Path(os.getenv("ARCHIVE_FOLDER", str(APP_BASE_DIR / "archived")))

JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "100"))
SCAN_INTERVAL = float(os.getenv("SCAN_INTERVAL", "2"))
FILE_READY_WAIT_SECONDS = float(os.getenv("FILE_READY_WAIT_SECONDS", "1"))
MAX_READY_CHECKS = int(os.getenv("MAX_READY_CHECKS", "10"))


def setup_folders():
    WATCH_FOLDER.mkdir(parents=True, exist_ok=True)
    (OUTPUT_FOLDER / "jpg").mkdir(parents=True, exist_ok=True)
    (OUTPUT_FOLDER / "png").mkdir(parents=True, exist_ok=True)
    ARCHIVE_FOLDER.mkdir(parents=True, exist_ok=True)


def is_heic(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in {".heic", ".heif"}


def wait_for_file(path: Path) -> bool:
    previous_size = -1

    for _ in range(MAX_READY_CHECKS):
        if not path.exists():
            return False

        try:
            current_size = path.stat().st_size
        except OSError:
            time.sleep(FILE_READY_WAIT_SECONDS)
            continue

        if current_size > 0 and current_size == previous_size:
            return True

        previous_size = current_size
        time.sleep(FILE_READY_WAIT_SECONDS)

    return False


def unique_archive_path(path: Path) -> Path:
    archive_path = ARCHIVE_FOLDER / path.name
    if not archive_path.exists():
        return archive_path

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    return ARCHIVE_FOLDER / f"{path.stem}_{timestamp}{path.suffix}"


def get_output_paths(path: Path):
    jpg_path = OUTPUT_FOLDER / "jpg" / f"{path.stem}.jpg"
    png_path = OUTPUT_FOLDER / "png" / f"{path.stem}.png"
    return jpg_path, png_path


def convert_file(path: Path):
    print(f"\nProcessing: {path.name}")

    jpg_path, png_path = get_output_paths(path)

    try:
        with Image.open(path) as img:
            img.save(png_path, "PNG")
            print(f"PNG created: {png_path}")

            if img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img_rgb = bg
            else:
                img_rgb = img.convert("RGB")

            img_rgb.save(jpg_path, "JPEG", quality=JPEG_QUALITY, optimize=True)
            print(f"JPG created: {jpg_path}")

        archive_path = unique_archive_path(path)
        path.replace(archive_path)
        print(f"Archived: {archive_path}")

    except Exception as e:
        print(f"ERROR processing {path.name}: {e}")


def scan_and_process():
    heic_files = sorted([p for p in WATCH_FOLDER.iterdir() if is_heic(p)])

    for path in heic_files:
        if wait_for_file(path):
            convert_file(path)
        else:
            print(f"Skipped unreadable file: {path.name}")


def main():
    setup_folders()

    print("=== HEIC AUTO CONVERTER ===")
    print(f"Base dir:  {APP_BASE_DIR}")
    print(f"Watching:  {WATCH_FOLDER}")
    print(f"Output:    {OUTPUT_FOLDER}")
    print(f"Archive:   {ARCHIVE_FOLDER}")
    print("Outputs:   JPG + PNG")
    print(f"Scan every {SCAN_INTERVAL} second(s)")

    while True:
        try:
            scan_and_process()
            time.sleep(SCAN_INTERVAL)
        except KeyboardInterrupt:
            print("\nStopping...")
            break
        except Exception as e:
            print(f"Loop error: {e}")
            time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    main()