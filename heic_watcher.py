import os
import time
import logging
from pathlib import Path

from dotenv import load_dotenv
from PIL import Image
from pillow_heif import register_heif_opener

load_dotenv()
register_heif_opener()

BASE_DIR = Path(os.getenv("LOCALAPPDATA")) / "HEIC2JPGWatcher"

WATCH_FOLDER = BASE_DIR / "incoming"
OUTPUT_FOLDER = BASE_DIR / "converted"
ARCHIVE_FOLDER = BASE_DIR / "archived"
LOG_FOLDER = BASE_DIR / "logs"

JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "100"))
SCAN_INTERVAL = float(os.getenv("SCAN_INTERVAL", "2"))

LOG_FOLDER.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_FOLDER / "heic_watcher.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)

def setup_folders():
    WATCH_FOLDER.mkdir(parents=True, exist_ok=True)
    (OUTPUT_FOLDER / "jpg").mkdir(parents=True, exist_ok=True)
    (OUTPUT_FOLDER / "png").mkdir(parents=True, exist_ok=True)
    ARCHIVE_FOLDER.mkdir(parents=True, exist_ok=True)

def is_heic(path):
    return path.suffix.lower() in {".heic", ".heif"}

def convert(path):
    try:
        jpg_path = OUTPUT_FOLDER / "jpg" / f"{path.stem}.jpg"
        png_path = OUTPUT_FOLDER / "png" / f"{path.stem}.png"

        with Image.open(path) as img:
            img.save(png_path, "PNG")

            if img.mode in ("RGBA", "LA"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[-1])
                img = bg
            else:
                img = img.convert("RGB")

            img.save(jpg_path, "JPEG", quality=JPEG_QUALITY)

        archive_path = ARCHIVE_FOLDER / path.name
        if archive_path.exists():
            archive_path = ARCHIVE_FOLDER / f"{path.stem}_{int(time.time())}.heic"

        path.replace(archive_path)

        logging.info(f"Converted & archived: {path.name}")

    except Exception as e:
        logging.error(f"Error: {e}")

def main():
    setup_folders()

    while True:
        try:
            for file in WATCH_FOLDER.iterdir():
                if file.is_file() and is_heic(file):
                    convert(file)
            time.sleep(SCAN_INTERVAL)
        except Exception as e:
            logging.error(f"Loop error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()