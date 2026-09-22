"""
wwise_auto_import.pyw
=====================
Automatic audio integration script for Wwise with real-time log interface,
adaptive batching, and direct path mapping (no staging folder required).
"""

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
import threading

from waapi import WaapiClient, CannotConnectToWaapiException

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
AUDIO_EXTENSIONS = {".wav", ".aif", ".aiff", ".mp3", ".ogg", ".wem"}
WWISE_IMPORT_TARGET_PATH = r"\Actor-Mixer Hierarchy\Default Work Unit"
WWISE_SOUND_TYPE_TAG = "Sound SFX"
IMPORT_LANGUAGE = "SFX"
IMPORT_OPERATION = "useExisting"

# Fast mode batch size (tries importing 50 files at once)
FAST_BATCH_SIZE = 50

class WwiseImporterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Wwise Auto Importer - Progress")
        self.root.geometry("600x450")
        self.root.minsize(500, 350)

        # Style interface
        style = ttk.Style()
        style.theme_use('clam')

        # Widgets
        self.label_status = ttk.Label(root, text="Waiting for launch...", font=("Segoe UI", 10, "bold"))
        self.label_status.pack(pady=(10, 5), anchor="w", padx=15)

        self.progress = ttk.Progressbar(root, orient="horizontal", length=570, mode="indeterminate")
        self.progress.pack(pady=5, padx=15, fill="x")
        self.progress.start(10)

        # Text area (embedded console)
        log_frame = ttk.Frame(root)
        log_frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.log_area = tk.Text(log_frame, wrap="word", bg="#1e1e1e", fg="#00ff66", font=("Consolas", 9))
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_area.yview)
        self.log_area.configure(yscrollcommand=scrollbar.set)

        self.log_area.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Close button (disabled during processing)
        self.btn_close = ttk.Button(root, text="Close", command=root.destroy, state="disabled")
        self.btn_close.pack(pady=10)

        # Start processing in a separate thread to keep UI responsive
        threading.Thread(target=self.run_import_process, daemon=True).start()

    def log(self, message):
        """Safely appends a message to the graphical console."""
        def update():
            self.log_area.insert(tk.END, message + "\n")
            self.log_area.see(tk.END)
        self.root.after(0, update)

    def set_status(self, text):
        def update():
            self.label_status.config(text=text)
        self.root.after(0, update)

    def run_import_process(self):
        try:
            self.log("Connecting to Wwise via WAAPI...")
            try:
                client = WaapiClient()
            except CannotConnectToWaapiException:
                self.root.after(0, lambda: messagebox.showerror(
                    "Connection Error",
                    "Unable to connect to Wwise.\nCheck that the project is open and WAAPI is enabled."
                ))
                self.finish_process()
                return

            self.log("Connected to Wwise successfully.")
            self.set_status("Analyzing existing assets...")

            # Retrieve existing assets
            result = client.call(
                "ak.wwise.core.object.get",
                {"waql": '$ from type Sound'},
                options={"return": ["name"]},
            )
            existing_names = {obj["name"].strip().lower() for obj in result.get("return", [])}
            self.log(f"{len(existing_names)} assets already present in the project.")

            # Select folder via Tkinter
            self.root.after(0, self.ask_folder_and_process, client, existing_names)

        except Exception as e:
            self.log(f"Critical Error: {e}")
            self.finish_process()

    def ask_folder_and_process(self, client, existing_names):
        folder = filedialog.askdirectory(title="Select the folder containing the sounds to import")
        if not folder:
            self.log("No folder selected. Aborting.")
            client.disconnect()
            self.finish_process()
            return

        # Start heavy processing in worker thread
        threading.Thread(target=self.process_files, args=(client, existing_names, folder), daemon=True).start()

    def process_files(self, client, existing_names, folder):
        try:
            self.set_status("Recursive scan of audio files...")
            all_files = []
            for dirpath, _, filenames in os.walk(folder):
                for fname in filenames:
                    if Path(fname).suffix.lower() in AUDIO_EXTENSIONS:
                        all_files.append(os.path.join(dirpath, fname))

            self.log(f"{len(all_files)} audio files found in total.")

            new_files = []
            for f in all_files:
                if Path(f).stem.strip().lower() not in existing_names:
                    new_files.append(f)

            self.log(f"{len(new_files)} new files to import.")

            if not new_files:
                self.root.after(0, lambda: messagebox.showinfo("Completed", "No sounds added."))
                client.disconnect()
                self.finish_process()
                return

            # Direct absolute path mapping (no temporary staging folder needed)
            self.set_status("Importing into Wwise...")
            imported_count = 0
            failed_count = 0
            total_files = len(new_files)

            for i in range(0, total_files, FAST_BATCH_SIZE):
                batch = new_files[i:i + FAST_BATCH_SIZE]
                batch_start_idx = i + 1
                batch_end_idx = min(i + FAST_BATCH_SIZE, total_files)

                self.log(f"\nProcessing batch [{batch_start_idx}-{batch_end_idx}/{total_files}] ({len(batch)} files)...")

                imports = []
                for f in batch:
                    sound_name = Path(f).stem
                    abs_path = os.path.normpath(os.path.abspath(f))
                    target_path_clean = WWISE_IMPORT_TARGET_PATH.rstrip("\\")
                    obj_path = f"{target_path_clean}\\<{WWISE_SOUND_TYPE_TAG}>{sound_name}"
                    imports.append({"audioFile": abs_path, "objectPath": obj_path})

                args = {
                    "importOperation": IMPORT_OPERATION,
                    "default": {"importLanguage": IMPORT_LANGUAGE},
                    "imports": imports,
                }

                try:
                    # Attempt fast batch import
                    client.call("ak.wwise.core.audio.import", args)
                    imported_count += len(batch)
                    self.log(f"  -> Batch [{batch_start_idx}-{batch_end_idx}] imported successfully.")
                except Exception as batch_err:
                    self.log(f"  -> WARNING: Batch failed ({batch_err}). Switching to 1-by-1 fallback mode for this batch...")

                    # Fallback mode: process each file in this batch individually to isolate errors
                    for item_offset, f in enumerate(batch):
                        item_idx = batch_start_idx + item_offset
                        sound_name = Path(f).stem
                        abs_path = os.path.normpath(os.path.abspath(f))
                        target_path_clean = WWISE_IMPORT_TARGET_PATH.rstrip("\\")
                        obj_path = f"{target_path_clean}\\<{WWISE_SOUND_TYPE_TAG}>{sound_name}"

                        single_import = [{"audioFile": abs_path, "objectPath": obj_path}]
                        single_args = {
                            "importOperation": IMPORT_OPERATION,
                            "default": {"importLanguage": IMPORT_LANGUAGE},
                            "imports": single_import,
                        }

                        try:
                            client.call("ak.wwise.core.audio.import", single_args)
                            imported_count += 1
                            self.log(f"    [{item_idx}/{total_files}] Success: {sound_name}")
                        except Exception as single_err:
                            failed_count += 1
                            self.log(f"    [{item_idx}/{total_files}] FAILED (Corrupted file?) {sound_name}: {single_err}")

            self.log(f"\nImport completed: {imported_count} successful, {failed_count} failure(s).")

            # Cleanup connection
            client.disconnect()

            self.set_status("Operation completed successfully!")

            if imported_count > 0:
                success_message = f"Successfully imported {imported_count} sounds!\n({failed_count} file(s) ignored/corrupted)."
            else:
                success_message = "No sounds added."

            self.root.after(0, lambda: messagebox.showinfo("Completed", success_message))

        except Exception as e:
            self.log(f"Error during processing: {e}")
        finally:
            self.finish_process()

    def finish_process(self):
        def update():
            self.progress.stop()
            self.progress.pack_forget()
            self.btn_close.config(state="normal")
        self.root.after(0, update)

if __name__ == "__main__":
    root = tk.Tk()
    app = WwiseImporterApp(root)
    root.mainloop()