# Wwise Auto Importer via WAAPI

An automated, user-friendly Python tool designed to streamline audio asset integration into Audiokinetic Wwise using the Wwise Authoring API (WAAPI) and WAQL.

## 🚀 Key Features

* **Smart Delta Sync:** Automatically scans a selected directory, queries the active Wwise project via WAQL (`$ from type Sound`), and filters out already integrated assets to import *only* new files.
* **Adaptive Fallback Batching:** Balances speed and reliability by processing assets in fast chunks (50 files at a time). If a batch encounters an error (e.g., a corrupted file), it automatically falls back to a 1-by-1 processing mode to isolate the culprit, save healthy assets, and keep the pipeline moving.
* **Direct Path Mapping:** Bypasses temporary staging folders entirely, mapping direct absolute paths to prevent system drive (`C:`) disk space saturation when handling massive multi-gigabyte asset libraries.
* **Real-Time Graphical Interface:** Built with `tkinter` and multi-threading (`threading`) to provide an embedded console with live logs and a progress indicator, ensuring the UI never freezes.
* **Console-Free Execution:** Runs natively as a `.pyw` script via `pythonw.exe`, launching straight into a clean desktop utility without opening a black command-line window.

---

## 📋 Prerequisites

1. **Python 3.x** installed on your system.
2. The official WAAPI client library for Python:
   ```bash
   pip install waapi-client

---

🛠️ Configuration
You can customize the script behavior by editing the configuration variables at the top of wwise_auto_import.pyw:

# Audio formats to scan
AUDIO_EXTENSIONS = {".wav", ".aif", ".aiff", ".mp3", ".ogg", ".wem"}

# Target Wwise object path where new sounds will be created
WWISE_IMPORT_TARGET_PATH = r"\Actor-Mixer Hierarchy\Default Work Unit"

# Wwise sound object type tag
WWISE_SOUND_TYPE_TAG = "Sound SFX"

# Import language
IMPORT_LANGUAGE = "SFX"

# Import operation behavior ("useExisting", "replaceExisting", "createNew")
IMPORT_OPERATION = "useExisting"

---

🎮 How to Use
Double-click on wwise_auto_import.pyw.

Select the source folder containing your audio assets using the native dialog window.

Watch the embedded console log the analysis, delta check, and real-time import progress.

Once completed, a success summary dialog will appear detailing the imported and skipped/corrupted files.