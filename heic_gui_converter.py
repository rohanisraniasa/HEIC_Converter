import os
import shutil
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

from dotenv import load_dotenv
from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()

APP_NAME = "HEIC Converter"
CONFIG_DIR = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "HEIC2JPGWatcher"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
ENV_PATH = CONFIG_DIR / ".env"


def get_downloads_folder() -> Path:
    return Path.home() / "Downloads"


def load_config() -> dict:
    if ENV_PATH.exists():
        load_dotenv(dotenv_path=ENV_PATH, override=True)

    base_folder = os.getenv("BASE_FOLDER", "").strip()

    if not base_folder:
        base_folder = str(get_downloads_folder() / "HEIC Converter")

    return {
        "BASE_FOLDER": base_folder,
        "JPEG_QUALITY": os.getenv("JPEG_QUALITY", "100").strip(),
    }


def save_config(base_folder: Path, jpeg_quality: str = "100") -> None:
    content = (
        f'BASE_FOLDER={base_folder}\n'
        f'JPEG_QUALITY={jpeg_quality}\n'
    )
    ENV_PATH.write_text(content, encoding="utf-8")


def ensure_working_folders(base_folder: Path) -> dict:
    incoming = base_folder / "incoming"
    converted = base_folder / "converted"
    jpg = converted / "jpg"
    png = converted / "png"
    archived = base_folder / "archived"

    incoming.mkdir(parents=True, exist_ok=True)
    jpg.mkdir(parents=True, exist_ok=True)
    png.mkdir(parents=True, exist_ok=True)
    archived.mkdir(parents=True, exist_ok=True)

    return {
        "base": base_folder,
        "incoming": incoming,
        "converted": converted,
        "jpg": jpg,
        "png": png,
        "archived": archived,
    }


def open_folder(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.startfile(str(path))


class HeicConverterApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("850x620")
        self.root.minsize(760, 560)

        self.selected_files = []
        self.config = load_config()
        self.jpeg_quality = self.config["JPEG_QUALITY"]

        self.base_folder = Path(self.config["BASE_FOLDER"])
        self.first_run_setup_if_needed()
        self.folders = ensure_working_folders(self.base_folder)

        self.build_ui()
        self.refresh_folder_labels()

    def first_run_setup_if_needed(self) -> None:
        """
        If config does not exist yet, prompt user once for the working folder.
        """
        if ENV_PATH.exists():
            return

        default_folder = get_downloads_folder() / "HEIC Converter"

        answer = messagebox.askyesno(
            "First Run Setup",
            "Choose a base working folder now?\n\n"
            "Yes = pick a location manually\n"
            "No = use a folder in Downloads"
        )

        if answer:
            chosen = filedialog.askdirectory(
                title="Select Base Working Folder",
                initialdir=str(get_downloads_folder())
            )
            if chosen:
                self.base_folder = Path(chosen)
            else:
                self.base_folder = default_folder
        else:
            self.base_folder = default_folder

        save_config(self.base_folder, self.jpeg_quality)

    def build_ui(self) -> None:
        title = tk.Label(
            self.root,
            text="HEIC to JPG + PNG Converter",
            font=("Segoe UI", 15, "bold")
        )
        title.pack(pady=(14, 8))

        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", padx=20, pady=(0, 8))

        self.base_folder_label = tk.Label(
            top_frame,
            text="",
            justify="left",
            anchor="w",
            font=("Segoe UI", 10)
        )
        self.base_folder_label.pack(fill="x")

        action_frame = tk.Frame(self.root)
        action_frame.pack(fill="x", padx=20, pady=(4, 8))

        tk.Button(
            action_frame,
            text="Select HEIC Files",
            width=18,
            command=self.select_files
        ).grid(row=0, column=0, padx=5, pady=5)

        tk.Button(
            action_frame,
            text="Select Folder",
            width=18,
            command=self.select_folder_files
        ).grid(row=0, column=1, padx=5, pady=5)

        tk.Button(
            action_frame,
            text="Convert Selected",
            width=18,
            command=self.convert_files
        ).grid(row=0, column=2, padx=5, pady=5)

        tk.Button(
            action_frame,
            text="Clear Selection",
            width=18,
            command=self.clear_selection
        ).grid(row=0, column=3, padx=5, pady=5)

        config_frame = tk.Frame(self.root)
        config_frame.pack(fill="x", padx=20, pady=(0, 8))

        tk.Button(
            config_frame,
            text="Change Base Folder",
            width=18,
            command=self.change_base_folder
        ).grid(row=0, column=0, padx=5, pady=5)

        tk.Button(
            config_frame,
            text="Open Base Folder",
            width=18,
            command=lambda: open_folder(self.folders["base"])
        ).grid(row=0, column=1, padx=5, pady=5)

        tk.Button(
            config_frame,
            text="Open Incoming",
            width=18,
            command=lambda: open_folder(self.folders["incoming"])
        ).grid(row=0, column=2, padx=5, pady=5)

        folder_frame = tk.Frame(self.root)
        folder_frame.pack(fill="x", padx=20, pady=(0, 8))

        tk.Button(
            folder_frame,
            text="Open JPG Folder",
            width=18,
            command=lambda: open_folder(self.folders["jpg"])
        ).grid(row=0, column=0, padx=5, pady=5)

        tk.Button(
            folder_frame,
            text="Open PNG Folder",
            width=18,
            command=lambda: open_folder(self.folders["png"])
        ).grid(row=0, column=1, padx=5, pady=5)

        tk.Button(
            folder_frame,
            text="Open Archived",
            width=18,
            command=lambda: open_folder(self.folders["archived"])
        ).grid(row=0, column=2, padx=5, pady=5)

        tk.Button(
            folder_frame,
            text="Open Downloads",
            width=18,
            command=lambda: open_folder(get_downloads_folder())
        ).grid(row=0, column=3, padx=5, pady=5)

        self.selection_label = tk.Label(
            self.root,
            text="No files selected.",
            justify="left",
            anchor="w"
        )
        self.selection_label.pack(fill="x", padx=20, pady=(0, 8))

        self.log_box = scrolledtext.ScrolledText(
            self.root,
            wrap=tk.WORD,
            height=20,
            font=("Consolas", 10)
        )
        self.log_box.pack(fill="both", expand=True, padx=20, pady=(0, 16))

    def refresh_folder_labels(self) -> None:
        self.base_folder_label.config(
            text=(
                f"Base Folder: {self.folders['base']}\n"
                f"Incoming: {self.folders['incoming']}\n"
                f"JPG Output: {self.folders['jpg']}\n"
                f"PNG Output: {self.folders['png']}\n"
                f"Archived: {self.folders['archived']}\n"
                f"Config (.env): {ENV_PATH}"
            )
        )

    def log(self, message: str) -> None:
        self.log_box.insert(tk.END, message + "\n")
        self.log_box.see(tk.END)
        self.root.update_idletasks()

    def select_files(self) -> None:
        files = filedialog.askopenfilenames(
            title="Select HEIC Files",
            filetypes=[("HEIC files", "*.heic *.heif")]
        )
        if not files:
            return

        self.selected_files = [Path(file) for file in files]
        self.selection_label.config(text=f"{len(self.selected_files)} file(s) selected.")
        self.log(f"Selected {len(self.selected_files)} file(s).")

    def select_folder_files(self) -> None:
        folder = filedialog.askdirectory(
            title="Select Folder Containing HEIC Files",
            initialdir=str(self.folders["incoming"])
        )
        if not folder:
            return

        folder_path = Path(folder)
        files = sorted([
            p for p in folder_path.iterdir()
            if p.is_file() and p.suffix.lower() in {".heic", ".heif"}
        ])

        if not files:
            messagebox.showinfo("No HEIC Files", "No HEIC or HEIF files were found in that folder.")
            return

        self.selected_files = files
        self.selection_label.config(
            text=f"{len(self.selected_files)} file(s) selected from folder."
        )
        self.log(f"Selected {len(self.selected_files)} file(s) from {folder_path}.")

    def clear_selection(self) -> None:
        self.selected_files = []
        self.selection_label.config(text="No files selected.")
        self.log("Selection cleared.")

    def change_base_folder(self) -> None:
        chosen = filedialog.askdirectory(
            title="Choose New Base Working Folder",
            initialdir=str(self.folders["base"].parent if self.folders["base"].parent.exists() else get_downloads_folder())
        )
        if not chosen:
            return

        new_base = Path(chosen)
        save_config(new_base, self.jpeg_quality)
        self.base_folder = new_base
        self.folders = ensure_working_folders(self.base_folder)
        self.refresh_folder_labels()

        self.log(f"Base folder changed to: {self.base_folder}")
        messagebox.showinfo(
            "Base Folder Updated",
            f"New base folder saved.\n\n{self.base_folder}"
        )

    def unique_output_path(self, folder: Path, stem: str, suffix: str) -> Path:
        path = folder / f"{stem}{suffix}"
        if not path.exists():
            return path

        counter = 1
        while True:
            candidate = folder / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    def unique_archive_path(self, source: Path) -> Path:
        path = self.folders["archived"] / source.name
        if not path.exists():
            return path

        counter = 1
        while True:
            candidate = self.folders["archived"] / f"{source.stem}_{counter}{source.suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    def copy_to_incoming_if_needed(self, source: Path) -> Path:
        """
        Optional convenience: if user selected a file outside the base folder,
        make a copy in incoming first so the working folder stays obvious.
        """
        incoming_target = self.folders["incoming"] / source.name

        if source.resolve().parent == self.folders["incoming"].resolve():
            return source

        target = incoming_target
        if target.exists():
            counter = 1
            while True:
                candidate = self.folders["incoming"] / f"{source.stem}_{counter}{source.suffix}"
                if not candidate.exists():
                    target = candidate
                    break
                counter += 1

        shutil.copy2(source, target)
        self.log(f"Copied to incoming: {target}")
        return target

    def convert_one_file(self, source: Path) -> None:
        working_source = self.copy_to_incoming_if_needed(source)

        jpg_path = self.unique_output_path(self.folders["jpg"], working_source.stem, ".jpg")
        png_path = self.unique_output_path(self.folders["png"], working_source.stem, ".png")
        archive_path = self.unique_archive_path(working_source)

        self.log(f"Processing: {working_source}")

        with Image.open(working_source) as img:
            img.save(png_path, "PNG")
            self.log(f"Created PNG: {png_path}")

            if img.mode in ("RGBA", "LA"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1])
                jpg_img = background
            else:
                jpg_img = img.convert("RGB")

            jpg_img.save(jpg_path, "JPEG", quality=int(self.jpeg_quality), optimize=True)
            self.log(f"Created JPG: {jpg_path}")

        shutil.move(str(working_source), str(archive_path))
        self.log(f"Archived original: {archive_path}")

    def convert_files(self) -> None:
        if not self.selected_files:
            messagebox.showwarning("No Files", "Please select one or more HEIC files first.")
            return

        success_count = 0
        fail_count = 0

        for source in self.selected_files:
            try:
                if not source.exists():
                    self.log(f"Skipped missing file: {source}")
                    fail_count += 1
                    continue

                if source.suffix.lower() not in {".heic", ".heif"}:
                    self.log(f"Skipped non-HEIC file: {source}")
                    fail_count += 1
                    continue

                self.convert_one_file(source)
                success_count += 1

            except Exception as exc:
                self.log(f"ERROR: {source} -> {exc}")
                fail_count += 1

        self.log("")
        self.log(f"Done. Success: {success_count}, Failed: {fail_count}")

        messagebox.showinfo(
            "Conversion Complete",
            f"Finished.\n\nSuccess: {success_count}\nFailed: {fail_count}"
        )

        self.selected_files = []
        self.selection_label.config(text="No files selected.")

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    root = tk.Tk()
    app = HeicConverterApp(root)
    app.run()


if __name__ == "__main__":
    main()