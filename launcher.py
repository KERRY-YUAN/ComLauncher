# -*- coding: utf-8 -*-
# File: launcher.py
# Version: Kerry, Ver. 2.5.5 (Version Button, Run Button Logic, Modal Style, API Fix)

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, font as tkfont, filedialog, Toplevel # Import Toplevel for modal window
import subprocess
import os
import threading
import queue
import time
import json
import webbrowser
import requests # For real API calls
import socket
import platform
import sys
from datetime import datetime, timezone # Import timezone for robust date parsing
import shlex # Added for safe command splitting
import shutil # Added for directory removal (uninstall)
import traceback # For detailed error logging
from functools import cmp_to_key # For custom sorting
# Attempt to import packaging for version parsing, but allow fallback
try:
    from packaging.version import parse as parse_version, InvalidVersion
except ImportError:
    print("[Launcher WARNING] 'packaging' library not found. Version sorting fallback will be basic string comparison.")
    parse_version = None
    InvalidVersion = Exception # Define for except block

# --- Configuration File ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "launcher_config.json")
ICON_PATH = os.path.join(BASE_DIR, "templates", "icon.ico") # Path to icon

# --- Default Values ---
DEFAULT_COMFYUI_INSTALL_DIR = "" # User must set this
DEFAULT_COMFYUI_PYTHON_EXE = "" # User must set this (can be portable or venv)
DEFAULT_COMFYUI_API_PORT = "8188"

# --- Performance Settings Defaults ---
DEFAULT_VRAM_MODE = "高负载(8GB以上)"
DEFAULT_CKPT_PRECISION = "半精度(FP16)"
DEFAULT_CLIP_PRECISION = "FP8 (E4M3FN)"
DEFAULT_UNET_PRECISION = "FP8 (E5M2)"
DEFAULT_VAE_PRECISION = "半精度(FP16)"
DEFAULT_CUDA_MALLOC = "启用"
DEFAULT_IPEX_OPTIMIZATION = "启用"
DEFAULT_XFORMERS_ACCELERATION = "启用"

# --- New Configuration Defaults ---
DEFAULT_GIT_EXE_PATH = r"D:\Program\ComfyUI_Program\ComfyUI\git\cmd\git.exe" if platform.system() == "Windows" else "/usr/bin/git" # Default Git path based on OS
DEFAULT_MAIN_REPO_URL = "https://gitee.com/AIGODLIKE/ComfyUI.git" # Default ComfyUI Main Repository
DEFAULT_NODE_CONFIG_URL = "https://raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main/custom-node-list.json" # Default Node Config URL
# MOD4 Default API Endpoint - User should set their specific Gemini endpoint
DEFAULT_ERROR_API_ENDPOINT = "" # e.g., https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest
DEFAULT_ERROR_API_KEY = "" # Default Error Analysis API Key

# --- Constants for Styling ---
UPDATE_INTERVAL_MS = 100
BG_COLOR = "#2d2d2d"
CONTROL_FRAME_BG = "#353535"
TAB_CONTROL_FRAME_BG = "#3c3c3c"
TEXT_AREA_BG = "#1e1e1e"
FG_COLOR = "#e0e0e0"
FG_MUTED = "#9e9e9e"
ACCENT_COLOR = "#007aff"
ACCENT_ACTIVE = "#005ecb"
STOP_COLOR = "#5a5a5a"
STOP_ACTIVE = "#ff453a"
STOP_RUNNING_BG = "#b71c1c"
STOP_RUNNING_ACTIVE_BG = "#d32f2f"
STOP_RUNNING_FG = "#ffffff"
BORDER_COLOR = "#484848"
FG_STDOUT = "#e0e0e0" # Default output color
FG_STDERR = "#ff6b6b" # Error color
FG_INFO = "#64d1b8"   # Info/Launcher/Update color
FG_WARN = "#ffd700"   # Warning color
FG_CMD = "#a0a0a0"    # Command color
FG_API = "#cccccc"    # API output color
FG_HIGHLIGHT = "#00e676" # Highlight color (e.g., for current version status)
FONT_FAMILY_UI = "Segoe UI"
FONT_FAMILY_MONO = "Consolas"
FONT_SIZE_NORMAL = 10
FONT_SIZE_MONO = 9
FONT_WEIGHT_BOLD = "bold"
# MOD1: Update version info
VERSION_INFO = "Kerry, Ver. 2.5.5" # MOD: Version updated

# Special marker for queue
_COMFYUI_READY_MARKER_ = "_COMFYUI_IS_READY_FOR_BROWSER_\n"

# --- Text/Output Methods (Standalone function) ---
def setup_text_tags(text_widget):
    """Configures text tags for ScrolledText widget coloring."""
    if not text_widget or not text_widget.winfo_exists():
        return
    # Define tags with specific foreground colors and font styles
    text_widget.tag_config("stdout", foreground=FG_STDOUT)
    text_widget.tag_config("stderr", foreground=FG_STDERR)
    text_widget.tag_config("info", foreground=FG_INFO, font=(FONT_FAMILY_MONO, FONT_SIZE_MONO, 'italic'))
    text_widget.tag_config("warn", foreground=FG_WARN)
    text_widget.tag_config("error", foreground=FG_STDERR, font=(FONT_FAMILY_MONO, FONT_SIZE_MONO, 'bold'))
    text_widget.tag_config("api_output", foreground=FG_API) # Tag for API analysis output
    text_widget.tag_config("cmd", foreground=FG_CMD, font=(FONT_FAMILY_MONO, FONT_SIZE_MONO, 'bold')) # Tag for commands
    text_widget.tag_config("highlight", foreground=FG_HIGHLIGHT, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL, 'bold')) # MOD: Added highlight tag

# --- Helper functions for Sorting (MOD2 remains unchanged) ---
def _parse_iso_date_for_sort(date_str):
    """Safely parses ISO date string, returns datetime object or None."""
    if not date_str:
        return None
    try:
        # Handle potential 'Z' timezone suffix and various ISO formats
        if date_str.endswith('Z'):
            date_str = date_str[:-1] + '+00:00'
        # Try parsing with timezone offset, then without
        try:
            return datetime.fromisoformat(date_str)
        except ValueError:
             # Fallback for formats like 'YYYY-MM-DD HH:MM:SS +ZZZZ'
             try:
                 return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S %z')
             except ValueError:
                 # print(f"[Launcher DEBUG] Could not parse date '{date_str}' for sorting.")
                 return None # Indicate parsing failure
    except Exception as e:
        print(f"[Launcher ERROR] Unexpected date parsing error for '{date_str}': {e}")
        return None

def _parse_version_string_for_sort(version_str):
    """Safely parses version string using packaging.version or falls back."""
    if not version_str:
        return None
    if parse_version: # Use packaging.version if available
        try:
            # Remove common prefixes like 'v' or type indicators for parsing
            if '/' in version_str:
                version_str = version_str.split('/')[-1].strip() # e.g., "tag / v1.2" -> "v1.2"
            if version_str.startswith('v'):
                version_str = version_str[1:]
            return parse_version(version_str)
        except InvalidVersion:
            # print(f"[Launcher DEBUG] InvalidVersion for '{version_str}' during sort.")
            return None # Treat unparseable versions as lowest priority (or handle differently if needed)
        except Exception as e:
            print(f"[Launcher ERROR] Unexpected version parsing error for '{version_str}': {e}")
            return None
    else: # Basic fallback if packaging isn't installed
        # Attempt simple numerical sort if possible (e.g., "0.2.31")
        parts = version_str.split('.')
        if all(part.isdigit() for part in parts):
            return tuple(map(int, parts))
        # Otherwise, return the string itself for basic lexical sort
        return version_str

def _compare_versions_for_sort(item1, item2):
    """
    Custom comparison function for sorting main body versions.
    Prioritizes date, then version string if dates are invalid/equal.
    Sorts descending (newest first).
    """
    date1 = _parse_iso_date_for_sort(item1.get('date_iso'))
    date2 = _parse_iso_date_for_sort(item2.get('date_iso'))
    name1 = item1.get('name')
    name2 = item2.get('name')

    # Compare dates first (descending)
    if date1 and date2:
        if date1 > date2: return -1
        if date1 < date2: return 1
        # Dates are equal or parsing failed for one, proceed to version
    elif date1 and not date2: # item1 has date, item2 doesn't -> item1 is newer
        return -1
    elif not date1 and date2: # item2 has date, item1 doesn't -> item2 is newer
        return 1
    # Neither has a valid date, proceed to version comparison

    # Compare versions if dates are inconclusive (descending)
    version1 = _parse_version_string_for_sort(name1)
    version2 = _parse_version_string_for_sort(name2)

    if version1 and version2:
        try: # Handle both Version objects and tuples/strings from fallback
            if version1 > version2: return -1
            if version1 < version2: return 1
        except TypeError: # Cannot compare different types (e.g., Version vs str) - treat as equal for version sort
             pass # Proceed to name fallback
    elif version1 and not version2: # Treat parseable version as higher than unparseable
        return -1
    elif not version1 and version2:
        return 1
    # Neither version parseable, or types incompatible, proceed to name fallback

    # Fallback: Lexicographical comparison of names (descending)
    if name1 and name2:
        if name1 > name2: return -1
        if name1 < name2: return 1
    elif name1: return -1 # name1 exists, name2 doesn't
    elif name2: return 1  # name2 exists, name1 doesn't

    return 0 # Treat as equal if all else fails

class ComLauncherApp:
    """Main class for the Tkinter application (ComLauncher)."""
    def __init__(self, root):
        """ Initializes the application. """
        self.root = root
        self.root.title("ComLauncher") # Changed program name
        try:
            # Set window icon if the file exists
            if os.path.exists(ICON_PATH):
                self.root.iconbitmap(ICON_PATH)
            else:
                print(f"[Launcher WARNING] Icon file not found at {ICON_PATH}, using default.")
        except tk.TclError as e:
            print(f"[Launcher WARNING] Failed to set window icon: {e}")
        except Exception as e:
            print(f"[Launcher ERROR] Unexpected error setting window icon: {e}")

        self.root.geometry("1000x750")
        self.root.configure(bg=BG_COLOR)
        self.root.minsize(800, 600)
        self.root.columnconfigure(0, weight=1)
        # MOD1: Configure row 1 (for version info) and row 2 (for notebook)
        self.root.rowconfigure(1, weight=0) # Version info row - no expand
        self.root.rowconfigure(2, weight=1) # Notebook row - expand

        # Process and state variables
        self.comfyui_process = None
        # REQ: Separate Queues for Logs
        self.comfyui_output_queue = queue.Queue() # Queue for ComfyUI logs
        self.launcher_log_queue = queue.Queue()   # Queue for Launcher, Git, Update, Fix, Analysis logs
        self.update_task_queue = queue.Queue() # Queue for background update tasks (Git operations)
        self.stop_event = threading.Event()
        self.backend_browser_triggered_for_session = False
        self.comfyui_ready_marker_sent = False
        self.comfyui_externally_detected = False
        self._update_task_running = False

        # Configuration variables (using StringVar for UI binding)
        self.comfyui_dir_var = tk.StringVar()
        self.python_exe_var = tk.StringVar()
        # self.comfyui_workflows_dir_var = tk.StringVar() # REQ: Removed
        self.comfyui_api_port_var = tk.StringVar()
        self.git_exe_path_var = tk.StringVar()
        self.main_repo_url_var = tk.StringVar()
        self.node_config_url_var = tk.StringVar()
        self.error_api_endpoint_var = tk.StringVar()
        self.error_api_key_var = tk.StringVar()

        # Performance variables
        self.vram_mode_var = tk.StringVar()
        self.ckpt_precision_var = tk.StringVar()
        self.clip_precision_var = tk.StringVar()
        self.unet_precision_var = tk.StringVar()
        self.vae_precision_var = tk.StringVar()
        self.cuda_malloc_var = tk.StringVar()
        self.ipex_optimization_var = tk.StringVar()
        self.xformers_acceleration_var = tk.StringVar()

        # Update Management specific variables
        self.current_main_body_version_var = tk.StringVar(value="未知 / Unknown")
        self.all_known_nodes = []
        self.local_nodes_only = []
        self.remote_main_body_versions = []
        self._node_history_modal_data = []
        self._node_history_modal_node_name = ""
        self._node_history_modal_path = ""
        self._node_history_modal_current_commit = "" # MOD: Store current commit for modal status

        # Store references to trace IDs for auto-save
        self._auto_save_trace_ids = {}
        self._auto_save_job = None

        # Base project dir for file dialogs (if needed)
        self.base_project_dir = os.path.dirname(os.path.abspath(__file__))


        self.config = {}

        # Initialize
        self.load_config()
        self.update_derived_paths() # Calculate paths and args based on loaded config
        self.setup_styles()
        self.setup_ui()
        self._setup_auto_save() # Setup auto-save traces AFTER UI elements are created

        # Start background tasks
        self.root.after(UPDATE_INTERVAL_MS, self.process_output_queues)
        self.update_worker_thread = threading.Thread(target=self._update_task_worker, daemon=True)
        self.update_worker_thread.start()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Set initial UI state and start initial background data loading
        self._update_ui_state()
        self.start_initial_data_load()

    # --- Configuration Handling ---
    def load_config(self):
        """Loads configuration from JSON file or uses defaults."""
        loaded_config = {}
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                print(f"[Launcher INFO] Configuration loaded from {CONFIG_FILE}")
            else:
                print("[Launcher INFO] Config file not found, using defaults...")
        except (json.JSONDecodeError, IOError, OSError) as e:
            print(f"[Launcher ERROR] Error loading config file '{CONFIG_FILE}': {e}. Using defaults.")
            loaded_config = {} # Reset to empty on error

        # Apply defaults and override with loaded config
        comfyui_dir_loaded = loaded_config.get("comfyui_dir", DEFAULT_COMFYUI_INSTALL_DIR)

        self.config = {
            "comfyui_dir": comfyui_dir_loaded,
            "python_exe": loaded_config.get("python_exe", DEFAULT_COMFYUI_PYTHON_EXE),
            "comfyui_api_port": loaded_config.get("comfyui_api_port", DEFAULT_COMFYUI_API_PORT),
            "vram_mode": loaded_config.get("vram_mode", DEFAULT_VRAM_MODE),
            "ckpt_precision": loaded_config.get("ckpt_precision", DEFAULT_CKPT_PRECISION),
            "clip_precision": loaded_config.get("clip_precision", DEFAULT_CLIP_PRECISION),
            "unet_precision": loaded_config.get("unet_precision", DEFAULT_UNET_PRECISION),
            "vae_precision": loaded_config.get("vae_precision", DEFAULT_VAE_PRECISION),
            "cuda_malloc": loaded_config.get("cuda_malloc", DEFAULT_CUDA_MALLOC),
            "ipex_optimization": loaded_config.get("ipex_optimization", DEFAULT_IPEX_OPTIMIZATION),
            "xformers_acceleration": loaded_config.get("xformers_acceleration", DEFAULT_XFORMERS_ACCELERATION),
            "git_exe_path": loaded_config.get("git_exe_path", DEFAULT_GIT_EXE_PATH),
            "main_repo_url": loaded_config.get("main_repo_url", DEFAULT_MAIN_REPO_URL),
            "node_config_url": loaded_config.get("node_config_url", DEFAULT_NODE_CONFIG_URL),
            "error_api_endpoint": loaded_config.get("error_api_endpoint", DEFAULT_ERROR_API_ENDPOINT),
            "error_api_key": loaded_config.get("error_api_key", DEFAULT_ERROR_API_KEY),
        }

        # Set UI variables from config
        self.comfyui_dir_var.set(self.config["comfyui_dir"])
        self.python_exe_var.set(self.config["python_exe"])
        self.comfyui_api_port_var.set(self.config["comfyui_api_port"])
        self.vram_mode_var.set(self.config["vram_mode"])
        self.ckpt_precision_var.set(self.config["ckpt_precision"])
        self.clip_precision_var.set(self.config["clip_precision"])
        self.unet_precision_var.set(self.config["unet_precision"])
        self.vae_precision_var.set(self.config["vae_precision"])
        self.cuda_malloc_var.set(self.config["cuda_malloc"])
        self.ipex_optimization_var.set(self.config["ipex_optimization"])
        self.xformers_acceleration_var.set(self.config["xformers_acceleration"])
        self.git_exe_path_var.set(self.config["git_exe_path"])
        self.main_repo_url_var.set(self.config["main_repo_url"])
        self.node_config_url_var.set(self.config["node_config_url"])
        self.error_api_endpoint_var.set(self.config["error_api_endpoint"])
        self.error_api_key_var.set(self.config["error_api_key"])

        # Save default config if file didn't exist or was empty/corrupt
        if not os.path.exists(CONFIG_FILE) or not loaded_config:
            print("[Launcher INFO] Attempting to save default configuration...")
            try:
                self.save_config_to_file(show_success=False)
            except Exception as e:
                print(f"[Launcher ERROR] Initial default config save failed: {e}")

    # REQ: Remove explicit save button, use auto-save
    # def save_settings(self): ... No longer needed ...

    def save_config_to_file(self, show_success=True):
        """Writes the self.config dictionary to the JSON file."""
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            # Avoid logging every auto-save unless explicitly requested
            if show_success:
                print(f"[Launcher INFO] Configuration saved to {CONFIG_FILE}")
                # Avoid showing messagebox for auto-saves
                # if self.root and self.root.winfo_exists(): messagebox.showinfo("设置已保存 / Settings Saved", "配置已成功保存。", parent=self.root)
        except Exception as e:
            print(f"[Launcher ERROR] Error saving config file: {e}")
            # Show error only if it's not an auto-save triggered error (how to detect?) - Let's always show save errors.
            if self.root and self.root.winfo_exists():
                messagebox.showerror("配置保存错误 / Config Save Error", f"无法将配置保存到文件：\n{e}", parent=self.root)

    # REQ: Auto-save for specific fields
    def _setup_auto_save(self):
        """Sets up trace for auto-saving specific configuration fields."""
        print("[Launcher INFO] Setting up auto-save traces...")
        # Variables to auto-save
        vars_to_trace = {
            # Settings Tab
            "comfyui_dir": self.comfyui_dir_var,
            "python_exe": self.python_exe_var,
            "comfyui_api_port": self.comfyui_api_port_var,
            "git_exe_path": self.git_exe_path_var,
            # Management Tab
            "main_repo_url": self.main_repo_url_var,
            "node_config_url": self.node_config_url_var,
            # Analysis Tab
            "error_api_endpoint": self.error_api_endpoint_var,
            "error_api_key": self.error_api_key_var,
            # Performance options
            "vram_mode": self.vram_mode_var,
            "ckpt_precision": self.ckpt_precision_var,
            "clip_precision": self.clip_precision_var,
            "unet_precision": self.unet_precision_var,
            "vae_precision": self.vae_precision_var,
            "cuda_malloc": self.cuda_malloc_var,
            "ipex_optimization": self.ipex_optimization_var,
            "xformers_acceleration": self.xformers_acceleration_var,
        }

        # Clear existing traces
        for var_name, var_instance in vars_to_trace.items():
            trace_id_key = f'_trace_id_{var_name}'
            if hasattr(self, trace_id_key):
                try:
                    trace_id = getattr(self, trace_id_key)
                    if trace_id:
                        var_instance.trace_vdelete('write', trace_id)
                except (tk.TclError, AttributeError):
                    pass # Ignore if trace doesn't exist or attribute is missing
                finally:
                    setattr(self, trace_id_key, None) # Clear the stored ID

        # Add new traces
        for var_name, var_instance in vars_to_trace.items():
            try:
                # Pass the config key name to the callback
                trace_id = var_instance.trace_add('write', lambda *args, key=var_name: self._schedule_auto_save(key))
                setattr(self, f'_trace_id_{var_name}', trace_id) # Store the new trace ID
            except Exception as e:
                print(f"[Launcher ERROR] Failed to set trace for {var_name}: {e}")

        print("[Launcher INFO] Auto-save traces set up.")

    def _schedule_auto_save(self, config_key_changed):
        """Schedules the auto-save action after a brief delay."""
        # Use root.after to debounce rapid typing/changes
        if self._auto_save_job is not None:
            self.root.after_cancel(self._auto_save_job)
            self._auto_save_job = None
        # Schedule the save after 1 second (1000ms)
        self._auto_save_job = self.root.after(1000, lambda key=config_key_changed: self._perform_auto_save(key))

    def _perform_auto_save(self, config_key_changed):
        """Performs the actual auto-save for changed configuration fields."""
        self._auto_save_job = None # Clear the job ID
        print(f"[Launcher INFO] Config field '{config_key_changed}' changed, auto-saving config...")

        # Update the specific config key from its corresponding StringVar
        key_to_var_map = {
            "comfyui_dir": self.comfyui_dir_var, "python_exe": self.python_exe_var,
            "comfyui_api_port": self.comfyui_api_port_var, "git_exe_path": self.git_exe_path_var,
            "main_repo_url": self.main_repo_url_var, "node_config_url": self.node_config_url_var,
            "error_api_endpoint": self.error_api_endpoint_var, "error_api_key": self.error_api_key_var,
            "vram_mode": self.vram_mode_var, "ckpt_precision": self.ckpt_precision_var,
            "clip_precision": self.clip_precision_var, "unet_precision": self.unet_precision_var,
            "vae_precision": self.vae_precision_var, "cuda_malloc": self.cuda_malloc_var,
            "ipex_optimization": self.ipex_optimization_var, "xformers_acceleration": self.xformers_acceleration_var,
        }

        if config_key_changed in key_to_var_map:
            try:
                new_value = key_to_var_map[config_key_changed].get()
                # Basic validation (e.g., port number)
                if config_key_changed == "comfyui_api_port":
                    try:
                        port_int = int(new_value)
                        if not (1 <= port_int <= 65535):
                            raise ValueError("Port out of range 1-65535")
                    except ValueError as e:
                        print(f"[Launcher WARNING] Invalid port value '{new_value}' entered, auto-save skipped for port. Error: {e}")
                        # Optionally revert UI or show temporary error? For now, just don't save.
                        # Consider reverting: self.comfyui_api_port_var.set(self.config.get(config_key_changed, DEFAULT_COMFYUI_API_PORT))
                        return # Skip saving if port is invalid

                # Update the internal config dictionary
                self.config[config_key_changed] = new_value
                # Update derived paths if a relevant path changed
                if config_key_changed in ["comfyui_dir", "python_exe", "git_exe_path", "comfyui_api_port"] or config_key_changed.startswith("vram_") or config_key_changed.endswith(("_precision", "_malloc", "_optimization", "_acceleration")):
                    self.update_derived_paths()
                # Save the entire config to file without showing success message
                self.save_config_to_file(show_success=False)
                # Update UI state if needed (e.g., API button enablement)
                self.root.after(0, self._update_ui_state)
            except Exception as e:
                print(f"[Launcher ERROR] Failed to get value or save during auto-save for '{config_key_changed}': {e}")
        else:
            print(f"[Launcher WARNING] Auto-save triggered for unknown key: '{config_key_changed}'")


    def update_derived_paths(self):
        """Updates internal path variables and base arguments based on current config."""
        # Load paths from config (which is kept up-to-date by auto-save)
        self.comfyui_install_dir = self.config.get("comfyui_dir", "")
        self.comfyui_portable_python = self.config.get("python_exe", "")
        self.git_exe_path = self.config.get("git_exe_path", DEFAULT_GIT_EXE_PATH)
        self.comfyui_api_port = self.config.get("comfyui_api_port", DEFAULT_COMFYUI_API_PORT)

        # Derive specific folder paths only if install_dir is valid
        if self.comfyui_install_dir and os.path.isdir(self.comfyui_install_dir):
            self.comfyui_nodes_dir = os.path.normpath(os.path.join(self.comfyui_install_dir, "custom_nodes"))
            self.comfyui_models_dir = os.path.normpath(os.path.join(self.comfyui_install_dir, "models"))
            self.comfyui_lora_dir = os.path.normpath(os.path.join(self.comfyui_install_dir, r"models\loras"))
            self.comfyui_input_dir = os.path.normpath(os.path.join(self.comfyui_install_dir, "input"))
            self.comfyui_output_dir = os.path.normpath(os.path.join(self.comfyui_install_dir, "output"))
            # REQ: Specific workflows path
            self.comfyui_workflows_dir = os.path.normpath(os.path.join(self.comfyui_install_dir, r"user\default\workflows"))
            self.comfyui_main_script = os.path.normpath(os.path.join(self.comfyui_install_dir, "main.py"))
        else:
            self.comfyui_nodes_dir = ""
            self.comfyui_models_dir = ""
            self.comfyui_lora_dir = ""
            self.comfyui_input_dir = ""
            self.comfyui_output_dir = ""
            self.comfyui_workflows_dir = ""
            self.comfyui_main_script = ""

        # Construct ComfyUI base arguments
        self.comfyui_base_args = [
            "--listen", "127.0.0.1", f"--port={self.comfyui_api_port}",
        ]

        # Add performance arguments based on selected options from config
        vram_mode = self.config.get("vram_mode", DEFAULT_VRAM_MODE)
        if vram_mode == "高负载(8GB以上)":
            self.comfyui_base_args.append("--highvram")
        elif vram_mode == "中负载(4GB以上)":
            self.comfyui_base_args.append("--lowvram") # Mapped to lowvram
        elif vram_mode == "低负载(2GB以上)":
            self.comfyui_base_args.append("--lowvram")
        # Handle "全负载(10GB以上)" - Assume this implies no specific VRAM flag or maybe highvram?
        elif vram_mode == "全负载(10GB以上)":
             # No flag needed, or maybe --highvram if that's the closest? Let's add --highvram.
             self.comfyui_base_args.append("--highvram")


        ckpt_prec = self.config.get("ckpt_precision", DEFAULT_CKPT_PRECISION)
        if ckpt_prec == "半精度(FP16)":
            self.comfyui_base_args.append("--force-fp16")

        clip_prec = self.config.get("clip_precision", DEFAULT_CLIP_PRECISION)
        if clip_prec == "半精度(FP16)":
            self.comfyui_base_args.append("--fp16-text-enc")
        elif clip_prec == "FP8 (E4M3FN)":
            self.comfyui_base_args.append("--fp8_e4m3fn-text-enc")
        elif clip_prec == "FP8 (E5M2)":
            self.comfyui_base_args.append("--fp8_e5m2-text-enc")

        unet_prec = self.config.get("unet_precision", DEFAULT_UNET_PRECISION)
        if unet_prec == "半精度(BF16)":
            self.comfyui_base_args.append("--bf16-model")
        elif unet_prec == "半精度(FP16)":
            self.comfyui_base_args.append("--fp16-model")
        elif unet_prec == "FP8 (E4M3FN)":
            self.comfyui_base_args.append("--fp8_e4m3fn-unet")
        elif unet_prec == "FP8 (E5M2)":
            self.comfyui_base_args.append("--fp8_e5m2-unet")

        vae_prec = self.config.get("vae_precision", DEFAULT_VAE_PRECISION)
        if vae_prec == "半精度(FP16)":
            self.comfyui_base_args.append("--fp16-vae")
        elif vae_prec == "半精度(BF16)":
            self.comfyui_base_args.append("--bf16-vae")

        if self.config.get("cuda_malloc", DEFAULT_CUDA_MALLOC) == "禁用":
            self.comfyui_base_args.append("--disable-cuda-malloc")

        if self.config.get("ipex_optimization", DEFAULT_IPEX_OPTIMIZATION) == "禁用":
            self.comfyui_base_args.append("--disable-ipex")

        if self.config.get("xformers_acceleration", DEFAULT_XFORMERS_ACCELERATION) == "禁用":
            self.comfyui_base_args.append("--disable-xformers")

        # print("--- Derived Paths and Args Updated ---") # Reduce console noise
        # print(f" Install Dir: {self.comfyui_install_dir}")
        # print(f" Nodes Dir: {self.comfyui_nodes_dir}")
        # print(f" Workflows Dir: {self.comfyui_workflows_dir}")
        # print(f" Python Exe: {self.comfyui_portable_python}")
        # print(f" Git Exe Path: {self.git_exe_path}")
        # print(f" API Port: {self.comfyui_api_port}")
        # print(f" Base Args: {' '.join(self.comfyui_base_args)}")


    # Function to open folders (Keep)
    def open_folder(self, path):
        """Opens a given folder path using the default file explorer."""
        # Update derived paths first to ensure we have the latest config
        self.update_derived_paths()
        target_path = ""
        # Map symbolic names to actual paths derived from config
        if path == 'nodes': target_path = self.comfyui_nodes_dir
        elif path == 'models': target_path = self.comfyui_models_dir
        elif path == 'lora': target_path = self.comfyui_lora_dir
        elif path == 'input': target_path = self.comfyui_input_dir
        elif path == 'output': target_path = self.comfyui_output_dir
        elif path == 'workflows': target_path = self.comfyui_workflows_dir
        else: target_path = path # Allow opening arbitrary paths if needed

        if not target_path:
             # Try to determine which folder failed based on the input 'path' symbolic name
             if path in ['nodes', 'models', 'lora', 'input', 'output', 'workflows']:
                  missing_base = not self.comfyui_install_dir or not os.path.isdir(self.comfyui_install_dir)
                  reason = "ComfyUI 安装目录未设置或无效" if missing_base else f"路径 '{path}' 无法派生"
                  messagebox.showwarning("路径无效 / Invalid Path", f"无法打开文件夹 '{path}'。\n原因: {reason}", parent=self.root)
                  print(f"[Launcher WARNING] Attempted to open folder '{path}', but path is invalid or base dir missing.")
             else:
                  messagebox.showwarning("路径无效 / Invalid Path", f"指定的文件夹路径为空。", parent=self.root)
             return

        if not os.path.isdir(target_path):
            messagebox.showwarning("路径无效 / Invalid Path", f"指定的文件夹不存在或无效:\n{target_path}", parent=self.root)
            print(f"[Launcher WARNING] Attempted to open non-existent directory: {target_path}")
            return
        try:
            if platform.system() == "Windows":
                # Use explorer.exe for robustness on Windows
                subprocess.run(['explorer', os.path.normpath(target_path)], check=False) # Changed check=False
            elif platform.system() == "Darwin": # macOS
                subprocess.run(['open', target_path], check=True)
            else: # Linux and other Unix-like systems
                subprocess.run(['xdg-open', target_path], check=True)
            print(f"[Launcher INFO] Opened folder: {target_path}")
        except FileNotFoundError as e:
             # Handle case where 'explorer', 'open', or 'xdg-open' isn't found
             messagebox.showerror("打开文件夹失败 / Failed to Open Folder", f"无法找到文件浏览器命令:\n'{e.filename}'\n错误: {e}", parent=self.root)
             print(f"[Launcher ERROR] Failed to find file explorer command: {e}")
        except Exception as e:
            messagebox.showerror("打开文件夹失败 / Failed to Open Folder", f"无法打开文件夹:\n{target_path}\n错误: {e}", parent=self.root)
            print(f"[Launcher ERROR] Failed to open folder {target_path}: {e}")


    # Function to browse directory (Keep)
    def browse_directory(self, var_to_set, initial_dir=""):
        """Opens a directory selection dialog."""
        # Use the current value of the variable as the initial directory if it's valid
        current_val = var_to_set.get()
        effective_initial_dir = current_val if os.path.isdir(current_val) else self.base_project_dir

        directory = filedialog.askdirectory(title="选择目录 / Select Directory", initialdir=effective_initial_dir, parent=self.root)
        if directory:
             normalized_path = os.path.normpath(directory)
             var_to_set.set(normalized_path)
             # Auto-save will handle saving the config

    # Function to browse file (Keep)
    def browse_file(self, var_to_set, filetypes, initial_dir=""):
        """Opens a file selection dialog."""
        current_val = var_to_set.get()
        effective_initial_dir = os.path.dirname(current_val) if current_val and os.path.isfile(current_val) else self.base_project_dir

        filepath = filedialog.askopenfilename(title="选择文件 / Select File", filetypes=filetypes, initialdir=effective_initial_dir, parent=self.root)
        if filepath:
             var_to_set.set(os.path.normpath(filepath))
             # Auto-save will handle saving the config

    # --- Styling Setup (Keep) ---
    def setup_styles(self):
        """Configures the ttk styles for the application."""
        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use('clam')
        except tk.TclError:
            print("[Launcher WARNING] 'clam' theme not available, using default theme.")

        neutral_button_bg="#555555"; neutral_button_fg=FG_COLOR; n_active_bg="#6e6e6e"; n_pressed_bg="#7f7f7f"; n_disabled_bg="#4a5a6a"; n_disabled_fg=FG_MUTED

        # Base style
        self.style.configure('.', background=BG_COLOR, foreground=FG_COLOR, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL), bordercolor=BORDER_COLOR)
        self.style.map('.', background=[('active', '#4f4f4f'), ('disabled', '#404040')], foreground=[('disabled', FG_MUTED)])

        # Frames
        self.style.configure('TFrame', background=BG_COLOR)
        self.style.configure('Control.TFrame', background=CONTROL_FRAME_BG) # Top control bar
        self.style.configure('TabControl.TFrame', background=TAB_CONTROL_FRAME_BG) # Frames inside tabs for controls
        self.style.configure('Settings.TFrame', background=BG_COLOR) # Specific frame styles if needed
        self.style.configure('Logs.TFrame', background=BG_COLOR) # For Logs tab frame
        self.style.configure('Analysis.TFrame', background=BG_COLOR) # For Analysis tab frame
        self.style.configure('Modal.TFrame', background=BG_COLOR) # For Modal window frame
        self.style.configure('Version.TFrame', background=BG_COLOR) # MOD1: Frame for version label

        # LabelFrame
        self.style.configure('TLabelframe', background=BG_COLOR, foreground=FG_COLOR, bordercolor=BORDER_COLOR, relief=tk.GROOVE)
        self.style.configure('TLabelframe.Label', background=BG_COLOR, foreground=FG_COLOR, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL, 'italic'))

        # Labels
        self.style.configure('TLabel', background=BG_COLOR, foreground=FG_COLOR)
        self.style.configure('Status.TLabel', background=CONTROL_FRAME_BG, foreground=FG_MUTED, padding=(5, 3))
        # MOD1: Updated Version.TLabel style (using BG_COLOR now) - kept for spacer
        self.style.configure('Version.TLabel', background=BG_COLOR, foreground=FG_MUTED, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL - 1))
        self.style.configure('Hint.TLabel', background=BG_COLOR, foreground=FG_MUTED, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL - 1), padding=(0, 0, 0, 0))
        self.style.configure('Highlight.TLabel', background=BG_COLOR, foreground=FG_HIGHLIGHT, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL, 'bold')) # Style for highlighted status in modal
        # MOD3: Style for modal header text
        self.style.configure('ModalHeader.TLabel', background=BG_COLOR, foreground=FG_COLOR, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL, 'bold'))


        # Buttons
        main_pady=(10, 6); main_fnt=(FONT_FAMILY_UI, FONT_SIZE_NORMAL); main_fnt_bld=(FONT_FAMILY_UI, FONT_SIZE_NORMAL, FONT_WEIGHT_BOLD)
        self.style.configure('TButton', padding=main_pady, anchor=tk.CENTER, font=main_fnt, borderwidth=0, relief=tk.FLAT, background=neutral_button_bg, foreground=neutral_button_fg)
        self.style.map('TButton', background=[('active', n_active_bg), ('pressed', n_pressed_bg), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])
        self.style.configure("Accent.TButton", padding=main_pady, font=main_fnt_bld, background=ACCENT_COLOR, foreground="white")
        self.style.map("Accent.TButton", background=[('pressed', ACCENT_ACTIVE), ('active', '#006ae0'), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])
        self.style.configure("Stop.TButton", padding=main_pady, font=main_fnt, background=STOP_COLOR, foreground=FG_COLOR)
        self.style.map("Stop.TButton", background=[('pressed', STOP_ACTIVE), ('active', '#6e6e6e'), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])
        self.style.configure("StopRunning.TButton", padding=main_pady, font=main_fnt, background=STOP_RUNNING_BG, foreground=STOP_RUNNING_FG)
        self.style.map("StopRunning.TButton", background=[('pressed', STOP_RUNNING_ACTIVE_BG), ('active', STOP_RUNNING_ACTIVE_BG), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])

        # Smaller buttons (like inside tabs or browse buttons)
        tab_pady=(6, 4); tab_fnt=(FONT_FAMILY_UI, FONT_SIZE_NORMAL - 1); tab_neutral_bg=neutral_button_bg; tab_n_active_bg=n_active_bg; tab_n_pressed_bg=n_pressed_bg
        self.style.configure("Tab.TButton", padding=tab_pady, font=tab_fnt, background=tab_neutral_bg, foreground=neutral_button_fg) # Generic small button
        self.style.map("Tab.TButton", background=[('pressed', tab_n_pressed_bg), ('active', tab_n_active_bg), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])
        self.style.configure("TabAccent.TButton", padding=tab_pady, font=tab_fnt, background=ACCENT_COLOR, foreground="white") # Accent small button
        self.style.map("TabAccent.TButton", background=[('pressed', ACCENT_ACTIVE), ('active', '#006ae0'), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])
        self.style.configure("Browse.TButton", padding=(4, 2), font=tab_fnt, background=tab_neutral_bg, foreground=neutral_button_fg) # Even smaller for browse
        self.style.map("Browse.TButton", background=[('pressed', tab_n_pressed_bg), ('active', tab_n_active_bg), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])
        self.style.configure("Modal.TButton", padding=tab_pady, font=tab_fnt, background=tab_neutral_bg, foreground=neutral_button_fg) # Modal buttons
        self.style.map("Modal.TButton", background=[('pressed', tab_n_pressed_bg), ('active', tab_n_active_bg), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])
        # MOD1: Style for the new Version Button (using Tab.TButton style)
        self.style.configure("Version.TButton", padding=(2, 1), font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL - 1), background=BG_COLOR, foreground=FG_MUTED, relief=tk.FLAT, borderwidth=0) # Flat look
        self.style.map("Version.TButton", foreground=[('active', FG_COLOR), ('pressed', FG_COLOR)], background=[('active', "#3f3f3f"), ('pressed', "#4f4f4f")])


        # Other Widgets
        self.style.configure('TCheckbutton', background=BG_COLOR, foreground=FG_COLOR, font=main_fnt); self.style.map('TCheckbutton', background=[('active', BG_COLOR)], indicatorcolor=[('selected', ACCENT_COLOR), ('pressed', ACCENT_ACTIVE), ('!selected', FG_MUTED)], foreground=[('disabled', FG_MUTED)])
        self.style.configure('TCombobox', fieldbackground=TEXT_AREA_BG, background=TEXT_AREA_BG, foreground=FG_COLOR, arrowcolor=FG_COLOR, bordercolor=BORDER_COLOR, insertcolor=FG_COLOR, padding=(5, 4), font=main_fnt); self.style.map('TCombobox', fieldbackground=[('readonly', TEXT_AREA_BG), ('disabled', CONTROL_FRAME_BG)], foreground=[('disabled', FG_MUTED), ('readonly', FG_COLOR)], arrowcolor=[('disabled', FG_MUTED)], selectbackground=[('!focus', ACCENT_COLOR), ('focus', ACCENT_ACTIVE)], selectforeground=[('!focus', 'white'), ('focus', 'white')])
        try:
            self.root.option_add('*TCombobox*Listbox.background', TEXT_AREA_BG); self.root.option_add('*TCombobox*Listbox.foreground', FG_COLOR); self.root.option_add('*TCombobox*Listbox.selectBackground', ACCENT_ACTIVE); self.root.option_add('*TCombobox*Listbox.selectForeground', 'white'); self.root.option_add('*TCombobox*Listbox.font', (FONT_FAMILY_UI, FONT_SIZE_NORMAL)); self.root.option_add('*TCombobox*Listbox.borderWidth', 1); self.root.option_add('*TCombobox*Listbox.relief', 'solid')
        except tk.TclError as e: print(f"[Launcher WARNING] Could not set Combobox Listbox styles: {e}")
        self.style.configure('TNotebook', background=BG_COLOR, borderwidth=0, tabmargins=[5, 5, 5, 0]); self.style.configure('TNotebook.Tab', padding=[15, 8], background=BG_COLOR, foreground=FG_MUTED, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL), borderwidth=0); self.style.map('TNotebook.Tab', background=[('selected', '#4a4a4a'), ('active', '#3a3a3a')], foreground=[('selected', 'white'), ('active', FG_COLOR)], focuscolor=self.style.lookup('TNotebook.Tab', 'background'))
        self.style.configure('Horizontal.TProgressbar', thickness=6, background=ACCENT_COLOR, troughcolor=CONTROL_FRAME_BG, borderwidth=0)
        self.style.configure('TEntry', fieldbackground=TEXT_AREA_BG, foreground=FG_COLOR, insertcolor='white', bordercolor=BORDER_COLOR, borderwidth=1, padding=(5,4)); self.style.map('TEntry', fieldbackground=[('focus', TEXT_AREA_BG)], bordercolor=[('focus', ACCENT_COLOR)], lightcolor=[('focus', ACCENT_COLOR)])
        self.style.configure('Treeview', background=TEXT_AREA_BG, foreground=FG_STDOUT, fieldbackground=TEXT_AREA_BG, rowheight=22); self.style.configure('Treeview.Heading', font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL, 'bold'), background=CONTROL_FRAME_BG, foreground=FG_COLOR); self.style.map('Treeview', background=[('selected', ACCENT_ACTIVE)], foreground=[('selected', 'white')])
        self.style.configure('Modal.TCanvas', background=BG_COLOR, borderwidth=0, highlightthickness=0);


    # --- UI Setup ---
    def setup_ui(self):
        """Builds the main UI structure."""
        # Top Control Frame
        control_frame = ttk.Frame(self.root, padding=(10, 10, 10, 5), style='Control.TFrame')
        control_frame.grid(row=0, column=0, sticky="ew")
        control_frame.columnconfigure(1, weight=1) # Spacer column

        self.status_label = ttk.Label(control_frame, text="状态: 初始化...", style='Status.TLabel', anchor=tk.W)
        self.status_label.grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Label(control_frame, text="", style='Status.TLabel').grid(row=0, column=1, sticky="ew") # Spacer
        self.progress_bar = ttk.Progressbar(control_frame, mode='indeterminate', length=350, style='Horizontal.TProgressbar')
        self.progress_bar.grid(row=0, column=2, padx=10)
        self.progress_bar.stop() # Start stopped
        # self.progress_bar.grid_remove() # Optionally hide initially
        self.stop_all_button = ttk.Button(control_frame, text="停止", command=self.stop_all_services, style="Stop.TButton", width=12)
        self.stop_all_button.grid(row=0, column=3, padx=(0, 5))
        self.run_all_button = ttk.Button(control_frame, text="运行 ComfyUI", command=self.start_comfyui_service_thread, style="Accent.TButton", width=12)
        self.run_all_button.grid(row=0, column=4, padx=(0, 0))

        # MOD1: Version Info Frame (Below Control Frame)
        version_frame = ttk.Frame(self.root, style='Version.TFrame', padding=(0, 0, 10, 5)) # Pad right and bottom
        version_frame.grid(row=1, column=0, sticky="ew")
        version_frame.columnconfigure(0, weight=1) # Allow spacer to push version to right
        ttk.Label(version_frame, text="", style="Version.TLabel").grid(row=0, column=0, sticky="ew") # Spacer
        # MOD1: Changed Label to Button and updated text/command
        version_button = ttk.Button(version_frame,
                                    text=VERSION_INFO, # Uses the updated constant
                                    style="Version.TButton", # Use the new style
                                    command=self._run_git_pull_pause) # Call the update function
        version_button.grid(row=0, column=1, sticky="e") # Place version button on right


        # Main Notebook (Tabs: 设置, 管理, 日志, 分析) - MOD1: Now in row 2
        self.notebook = ttk.Notebook(self.root, style='TNotebook')
        self.notebook.grid(row=2, column=0, sticky="nsew", padx=5, pady=(0, 5))
        self.notebook.enable_traversal()

        # --- Settings Tab ---
        self.settings_frame = ttk.Frame(self.notebook, padding="15", style='Settings.TFrame')
        self.settings_frame.columnconfigure(0, weight=1)
        self.notebook.add(self.settings_frame, text=' 设置 / Settings ')
        current_row = 0; frame_padx = 5; frame_pady = (0, 10); widget_pady = 3; widget_padx = 5; label_min_width = 25

        # Folder Access Buttons (REQ: Updated paths, added Workflows)
        folder_button_frame = ttk.Frame(self.settings_frame, style='Settings.TFrame')
        folder_button_frame.grid(row=current_row, column=0, sticky="ew", padx=frame_padx, pady=(0, widget_pady))
        folder_button_frame.columnconfigure((0,1,2,3,4,5), weight=1) # Equal weight
        button_pady_reduced = 1; button_padx_reduced = 3
        ttk.Button(folder_button_frame, text="Workflows", style='Tab.TButton', command=lambda: self.open_folder('workflows')).grid(row=0, column=0, padx=button_padx_reduced, pady=button_pady_reduced, sticky='ew')
        ttk.Button(folder_button_frame, text="Nodes", style='Tab.TButton', command=lambda: self.open_folder('nodes')).grid(row=0, column=1, padx=button_padx_reduced, pady=button_pady_reduced, sticky='ew')
        ttk.Button(folder_button_frame, text="Models", style='Tab.TButton', command=lambda: self.open_folder('models')).grid(row=0, column=2, padx=button_padx_reduced, pady=button_pady_reduced, sticky='ew')
        ttk.Button(folder_button_frame, text="Lora", style='Tab.TButton', command=lambda: self.open_folder('lora')).grid(row=0, column=3, padx=button_padx_reduced, pady=button_pady_reduced, sticky='ew')
        ttk.Button(folder_button_frame, text="Input", style='Tab.TButton', command=lambda: self.open_folder('input')).grid(row=0, column=4, padx=button_padx_reduced, pady=button_pady_reduced, sticky='ew')
        ttk.Button(folder_button_frame, text="Output", style='Tab.TButton', command=lambda: self.open_folder('output')).grid(row=0, column=5, padx=button_padx_reduced, pady=button_pady_reduced, sticky='ew')
        current_row += 1

        # Basic Settings Group (REQ: Removed Workflows Dir, added Open button)
        basic_group = ttk.LabelFrame(self.settings_frame, text=" 基本路径与端口 / Basic Paths & Ports ", padding=(10, 5))
        basic_group.grid(row=current_row, column=0, sticky="ew", padx=frame_padx, pady=frame_pady)
        basic_group.columnconfigure(1, weight=1) # Entry column expands
        basic_row = 0

        # ComfyUI Install Dir
        ttk.Label(basic_group, text="ComfyUI 安装目录:", width=label_min_width, anchor=tk.W).grid(row=basic_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        dir_entry = ttk.Entry(basic_group, textvariable=self.comfyui_dir_var)
        dir_entry.grid(row=basic_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx)
        dir_btn = ttk.Button(basic_group, text="浏览", width=6, style='Browse.TButton', command=lambda: self.browse_directory(self.comfyui_dir_var))
        dir_btn.grid(row=basic_row, column=2, sticky=tk.E, pady=widget_pady, padx=(0, widget_padx))
        basic_row += 1

        # REQ: Removed ComfyUI Workflows Dir entry

        # ComfyUI Python Exe
        ttk.Label(basic_group, text="ComfyUI Python 路径:", width=label_min_width, anchor=tk.W).grid(row=basic_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        py_entry = ttk.Entry(basic_group, textvariable=self.python_exe_var)
        py_entry.grid(row=basic_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx)
        py_btn = ttk.Button(basic_group, text="浏览", width=6, style='Browse.TButton', command=lambda: self.browse_file(self.python_exe_var, [("Python Executable", "python.exe"), ("All Files", "*.*")]))
        py_btn.grid(row=basic_row, column=2, sticky=tk.E, pady=widget_pady, padx=(0, widget_padx))
        basic_row += 1

        # Git Exe Path
        ttk.Label(basic_group, text="Git 可执行文件路径:", width=label_min_width, anchor=tk.W).grid(row=basic_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        git_entry = ttk.Entry(basic_group, textvariable=self.git_exe_path_var)
        git_entry.grid(row=basic_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx)
        git_btn = ttk.Button(basic_group, text="浏览", width=6, style='Browse.TButton', command=lambda: self.browse_file(self.git_exe_path_var, [("Git Executable", "git.exe"), ("All Files", "*.*")]))
        git_btn.grid(row=basic_row, column=2, sticky=tk.E, pady=widget_pady, padx=(0, widget_padx))
        basic_row += 1

        # ComfyUI API Port (REQ: Added Open button)
        port_frame = ttk.Frame(basic_group) # Frame to hold port entry and button
        port_frame.grid(row=basic_row, column=1, columnspan=2, sticky="ew") # Span entry and button columns
        port_frame.columnconfigure(0, weight=1) # Entry expands

        ttk.Label(basic_group, text="ComfyUI 监听与共享端口:", width=label_min_width, anchor=tk.W).grid(row=basic_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        comfyui_port_entry = ttk.Entry(port_frame, textvariable=self.comfyui_api_port_var, width=10) # Fixed width might be better here
        comfyui_port_entry.grid(row=0, column=0, sticky="w", pady=widget_pady, padx=widget_padx) # Align left, use west anchor
        port_open_btn = ttk.Button(port_frame, text="打开", width=6, style='Browse.TButton', command=self._open_frontend_browser_from_settings)
        port_open_btn.grid(row=0, column=1, sticky="w", pady=widget_pady, padx=(0, widget_padx)) # Place button next to entry

        basic_row += 1
        current_row += 1

        # Performance Group (REQ: Removed '自动', keep dropdowns)
        perf_group = ttk.LabelFrame(self.settings_frame, text=" 性能与显存优化 / Performance & VRAM Optimization ", padding=(10, 5))
        perf_group.grid(row=current_row, column=0, sticky="ew", padx=frame_padx, pady=frame_pady)
        perf_group.columnconfigure(1, weight=1); perf_row = 0

        # VRAM Mode
        ttk.Label(perf_group, text="显存优化:", width=label_min_width, anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx);
        vram_modes = ["全负载(10GB以上)", "高负载(8GB以上)", "中负载(4GB以上)", "低负载(2GB以上)"] # Removed "自动"
        vram_mode_combo = ttk.Combobox(perf_group, textvariable=self.vram_mode_var, values=vram_modes, state="readonly"); vram_mode_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); perf_row += 1
        # CKPT Precision
        ttk.Label(perf_group, text="CKPT模型精度:", width=label_min_width, anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx);
        ckpt_precisions = ["全精度(FP32)", "半精度(FP16)"]
        ckpt_precision_combo = ttk.Combobox(perf_group, textvariable=self.ckpt_precision_var, values=ckpt_precisions, state="readonly"); ckpt_precision_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); perf_row += 1
        # CLIP Precision
        ttk.Label(perf_group, text="CLIP编码精度:", width=label_min_width, anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx);
        clip_precisions = ["全精度(FP32)", "半精度(FP16)", "FP8 (E4M3FN)", "FP8 (E5M2)"]
        clip_precision_combo = ttk.Combobox(perf_group, textvariable=self.clip_precision_var, values=clip_precisions, state="readonly"); clip_precision_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); perf_row += 1
        # UNET Precision
        ttk.Label(perf_group, text="UNET模型精度:", width=label_min_width, anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx);
        unet_precisions = ["半精度(BF16)", "半精度(FP16)", "FP8 (E4M3FN)", "FP8 (E5M2)"]
        unet_precision_combo = ttk.Combobox(perf_group, textvariable=self.unet_precision_var, values=unet_precisions, state="readonly"); unet_precision_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); perf_row += 1
        # VAE Precision
        ttk.Label(perf_group, text="VAE模型精度:", width=label_min_width, anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx);
        vae_precisions = ["全精度(FP32)", "半精度(FP16)", "半精度(BF16)"]
        vae_precision_combo = ttk.Combobox(perf_group, textvariable=self.vae_precision_var, values=vae_precisions, state="readonly"); vae_precision_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); perf_row += 1
        # CUDA Malloc
        ttk.Label(perf_group, text="CUDA智能内存分配:", width=label_min_width, anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx);
        cuda_malloc_options = ["启用", "禁用"]
        cuda_malloc_combo = ttk.Combobox(perf_group, textvariable=self.cuda_malloc_var, values=cuda_malloc_options, state="readonly"); cuda_malloc_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); perf_row += 1
        # IPEX Optimization
        ttk.Label(perf_group, text="IPEX优化:", width=label_min_width, anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx);
        ipex_options = ["启用", "禁用"]
        ipex_combo = ttk.Combobox(perf_group, textvariable=self.ipex_optimization_var, values=ipex_options, state="readonly"); ipex_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); perf_row += 1
        # xformers Acceleration
        ttk.Label(perf_group, text="xformers加速:", width=label_min_width, anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx);
        xformers_options = ["启用", "禁用"]
        xformers_combo = ttk.Combobox(perf_group, textvariable=self.xformers_acceleration_var, values=xformers_options, state="readonly"); xformers_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); perf_row += 1

        current_row += 1
        # Spacer and Bottom Row (REQ: Removed Save button)
        self.settings_frame.rowconfigure(current_row, weight=1) # Spacer row

        # --- Management Tab ---
        self.update_frame = ttk.Frame(self.notebook, padding="15", style='TFrame')
        self.update_frame.columnconfigure(0, weight=1)
        self.update_frame.rowconfigure(1, weight=1) # Make bottom area (Node Management) expandable
        self.notebook.add(self.update_frame, text=' 管理 / Management ')

        update_current_row = 0
        # Repository Address Area (REQ: Auto-save handled by trace)
        repo_address_group = ttk.LabelFrame(self.update_frame, text=" 仓库地址 / Repository Address ", padding=(10, 5))
        repo_address_group.grid(row=update_current_row, column=0, sticky="ew", padx=frame_padx, pady=frame_pady)
        repo_address_group.columnconfigure(1, weight=1)
        repo_row = 0
        ttk.Label(repo_address_group, text="本体仓库地址:", width=label_min_width, anchor=tk.W).grid(row=repo_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        main_repo_entry = ttk.Entry(repo_address_group, textvariable=self.main_repo_url_var)
        main_repo_entry.grid(row=repo_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); repo_row += 1
        ttk.Label(repo_address_group, text="节点配置地址:", width=label_min_width, anchor=tk.W).grid(row=repo_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        node_config_entry = ttk.Entry(repo_address_group, textvariable=self.node_config_url_var)
        node_config_entry.grid(row=repo_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); repo_row += 1

        update_current_row += 1

        # Version & Node Management Area
        version_node_management_group = ttk.LabelFrame(self.update_frame, text=" 版本与节点管理 / Version & Node Management ", padding=(10, 5))
        version_node_management_group.grid(row=update_current_row, column=0, sticky="nsew", padx=frame_padx, pady=frame_pady)
        version_node_management_group.columnconfigure(0, weight=1); version_node_management_group.rowconfigure(0, weight=1)

        # Sub-notebook for 本体 and 节点
        node_notebook = ttk.Notebook(version_node_management_group, style='TNotebook')
        node_notebook.grid(row=0, column=0, sticky="nsew")
        node_notebook.enable_traversal()

        # --- 本体 Sub-tab ---
        self.main_body_frame = ttk.Frame(node_notebook, style='TFrame', padding=5)
        self.main_body_frame.columnconfigure(0, weight=1); self.main_body_frame.rowconfigure(1, weight=1) # Treeview expands
        node_notebook.add(self.main_body_frame, text=' 本体 / Main Body ')

        # Main Body Controls
        main_body_control_frame = ttk.Frame(self.main_body_frame, style='TabControl.TFrame', padding=(5, 5))
        main_body_control_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5), columnspan=2) # Span scrollbar too
        main_body_control_frame.columnconfigure(1, weight=1) # Spacer

        ttk.Label(main_body_control_frame, text="当前本体版本:", style='TLabel').grid(row=0, column=0, sticky=tk.W, padx=(0, 5));
        self.current_main_body_version_label = ttk.Label(main_body_control_frame, textvariable=self.current_main_body_version_var, style='TLabel', anchor=tk.W, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL, FONT_WEIGHT_BOLD))
        self.current_main_body_version_label.grid(row=0, column=0, sticky=tk.W, padx=(90, 5)) # Adjust padx
        ttk.Label(main_body_control_frame, text="", style='TLabel').grid(row=0, column=1, sticky="ew") # Spacer
        self.refresh_main_body_button = ttk.Button(main_body_control_frame, text="刷新版本", style="Tab.TButton", command=self._queue_main_body_refresh)
        self.refresh_main_body_button.grid(row=0, column=2, padx=(0, 5))
        self.activate_main_body_button = ttk.Button(main_body_control_frame, text="激活选中版本", style="TabAccent.TButton", command=self._queue_main_body_activation)
        self.activate_main_body_button.grid(row=0, column=3)

        # Main Body Versions List (REQ: Updated Columns)
        self.main_body_tree = ttk.Treeview(self.main_body_frame, columns=("version", "commit_id", "date", "description"), show="headings", style='Treeview')
        self.main_body_tree.heading("version", text="版本"); self.main_body_tree.column("version", width=150, stretch=tk.NO)
        self.main_body_tree.heading("commit_id", text="提交ID"); self.main_body_tree.column("commit_id", width=100, stretch=tk.NO, anchor=tk.CENTER) # Short ID display
        self.main_body_tree.heading("date", text="日期"); self.main_body_tree.column("date", width=120, stretch=tk.NO, anchor=tk.CENTER)
        self.main_body_tree.heading("description", text="描述"); self.main_body_tree.column("description", width=300, stretch=tk.YES)
        self.main_body_tree.grid(row=1, column=0, sticky="nsew")
        self.main_body_scrollbar = ttk.Scrollbar(self.main_body_frame, orient=tk.VERTICAL, command=self.main_body_tree.yview)
        self.main_body_tree.configure(yscrollcommand=self.main_body_scrollbar.set)
        self.main_body_scrollbar.grid(row=1, column=1, sticky="ns")
        self.main_body_tree.bind("<<TreeviewSelect>>", lambda event: self._update_ui_state())

        # --- 节点 Sub-tab ---
        self.nodes_frame = ttk.Frame(node_notebook, style='TFrame', padding=5)
        self.nodes_frame.columnconfigure(0, weight=1); self.nodes_frame.rowconfigure(2, weight=1) # Treeview expands
        node_notebook.add(self.nodes_frame, text=' 节点 / Nodes ')

        # Nodes Search and Control (REQ: Layout adjusted)
        nodes_control_frame = ttk.Frame(self.nodes_frame, style='TabControl.TFrame', padding=(5, 5))
        nodes_control_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5), columnspan=2) # Span scrollbar too

        # Search box and button on the left
        search_frame = ttk.Frame(nodes_control_frame, style='TabControl.TFrame')
        search_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.nodes_search_entry = ttk.Entry(search_frame, width=40)
        self.nodes_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_nodes_button = ttk.Button(search_frame, text="搜索", style="Tab.TButton", command=self._queue_node_list_refresh)
        self.search_nodes_button.pack(side=tk.LEFT, padx=(5, 0))

        # Other buttons on the right
        nodes_buttons_container = ttk.Frame(nodes_control_frame, style='TabControl.TFrame')
        nodes_buttons_container.pack(side=tk.RIGHT)
        self.refresh_nodes_button = ttk.Button(nodes_buttons_container, text="刷新列表", style="Tab.TButton", command=self._queue_node_list_refresh)
        self.refresh_nodes_button.pack(side=tk.LEFT, padx=(0, 5))
        self.switch_install_node_button = ttk.Button(nodes_buttons_container, text="切换版本", style="Tab.TButton", command=self._queue_node_switch_or_show_history) # Modified command
        self.switch_install_node_button.pack(side=tk.LEFT, padx=5)
        self.uninstall_node_button = ttk.Button(nodes_buttons_container, text="卸载节点", style="Tab.TButton", command=self._queue_node_uninstall)
        self.uninstall_node_button.pack(side=tk.LEFT, padx=5)
        self.update_all_nodes_button = ttk.Button(nodes_buttons_container, text="更新全部", style="TabAccent.TButton", command=self._queue_all_nodes_update)
        self.update_all_nodes_button.pack(side=tk.LEFT, padx=5)

        # Hint Label
        ttk.Label(self.nodes_frame, text="列表默认显示本地 custom_nodes 目录下的全部节点。输入内容后点击“搜索”显示匹配的本地/在线节点。", style='Hint.TLabel').grid(row=1, column=0, sticky=tk.W, padx=5, pady=(0, 5), columnspan=2)

        # Nodes List (REQ: Updated Columns)
        self.nodes_tree = ttk.Treeview(self.nodes_frame, columns=("name", "status", "local_id", "repo_info", "repo_url"), show="headings", style='Treeview')
        self.nodes_tree.heading("name", text="节点名称"); self.nodes_tree.column("name", width=200, stretch=tk.YES)
        self.nodes_tree.heading("status", text="状态"); self.nodes_tree.column("status", width=80, stretch=tk.NO, anchor=tk.CENTER)
        self.nodes_tree.heading("local_id", text="本地ID"); self.nodes_tree.column("local_id", width=100, stretch=tk.NO, anchor=tk.CENTER) # 8-char ID
        self.nodes_tree.heading("repo_info", text="仓库信息"); self.nodes_tree.column("repo_info", width=180, stretch=tk.NO) # Remote commit + date
        self.nodes_tree.heading("repo_url", text="仓库地址"); self.nodes_tree.column("repo_url", width=300, stretch=tk.YES)
        self.nodes_tree.grid(row=2, column=0, sticky="nsew")
        self.nodes_scrollbar = ttk.Scrollbar(self.nodes_frame, orient=tk.VERTICAL, command=self.nodes_tree.yview)
        self.nodes_tree.configure(yscrollcommand=self.nodes_scrollbar.set)
        self.nodes_scrollbar.grid(row=2, column=1, sticky="ns")
        try: # Tag configuration for status coloring
            self.nodes_tree.tag_configure('installed', foreground=FG_INFO)
            self.nodes_tree.tag_configure('not_installed', foreground=FG_MUTED)
        except tk.TclError: pass
        self.nodes_tree.bind("<<TreeviewSelect>>", lambda event: self._update_ui_state())


        # --- Logs Tab (REQ: New structure with sub-tabs) ---
        self.logs_tab_frame = ttk.Frame(self.notebook, padding="5", style='Logs.TFrame') # Main frame for the Logs tab
        self.logs_tab_frame.columnconfigure(0, weight=1)
        self.logs_tab_frame.rowconfigure(0, weight=1)
        self.notebook.add(self.logs_tab_frame, text=' 日志 / Logs ')

        # Sub-notebook for Launcher and ComfyUI logs
        self.logs_notebook = ttk.Notebook(self.logs_tab_frame, style='TNotebook') # Store reference
        self.logs_notebook.grid(row=0, column=0, sticky="nsew")
        self.logs_notebook.enable_traversal()

        # ComLauncher Log Sub-tab
        launcher_log_frame = ttk.Frame(self.logs_notebook, style='Logs.TFrame', padding=0)
        launcher_log_frame.columnconfigure(0, weight=1)
        launcher_log_frame.rowconfigure(0, weight=1)
        self.logs_notebook.add(launcher_log_frame, text=' ComLauncher日志 / Launcher Logs ')
        self.launcher_log_text = scrolledtext.ScrolledText(launcher_log_frame, wrap=tk.WORD, state=tk.DISABLED, font=(FONT_FAMILY_MONO, FONT_SIZE_MONO), bg=TEXT_AREA_BG, fg=FG_STDOUT, relief=tk.FLAT, borderwidth=1, bd=1, highlightthickness=1, highlightbackground=BORDER_COLOR, insertbackground="white")
        self.launcher_log_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        setup_text_tags(self.launcher_log_text) # Apply color tags

        # ComfyUI Log Sub-tab (Uses the original main_output_text)
        comfyui_log_frame = ttk.Frame(self.logs_notebook, style='Logs.TFrame', padding=0)
        comfyui_log_frame.columnconfigure(0, weight=1)
        comfyui_log_frame.rowconfigure(0, weight=1)
        self.logs_notebook.add(comfyui_log_frame, text=' ComfyUI日志 / ComfyUI Logs ')
        self.main_output_text = scrolledtext.ScrolledText(comfyui_log_frame, wrap=tk.WORD, state=tk.DISABLED, font=(FONT_FAMILY_MONO, FONT_SIZE_MONO), bg=TEXT_AREA_BG, fg=FG_STDOUT, relief=tk.FLAT, borderwidth=1, bd=1, highlightthickness=1, highlightbackground=BORDER_COLOR, insertbackground="white")
        self.main_output_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        setup_text_tags(self.main_output_text) # Apply color tags


        # --- Analysis Tab (REQ: Layout confirmed, functionality updated) ---
        self.analysis_frame = ttk.Frame(self.notebook, padding="15", style='Analysis.TFrame')
        self.analysis_frame.columnconfigure(0, weight=1)
        # MOD4: Configure row 1 (where error_analysis_text is) to expand
        self.analysis_frame.rowconfigure(1, weight=1) # Row 1 contains the text area now
        self.notebook.add(self.analysis_frame, text=' 分析 / Analysis ')

        analysis_current_row = 0
        # API Configuration Controls Frame (takes minimal space at top)
        api_control_group = ttk.Frame(self.analysis_frame, style='Analysis.TFrame')
        api_control_group.grid(row=analysis_current_row, column=0, sticky="new", padx=frame_padx, pady=widget_pady) # Stick to top-ew
        api_control_group.columnconfigure(1, weight=1) # Make entry column expand

        # Row 1 inside control group: API Endpoint
        ttk.Label(api_control_group, text="API 接口:", width=label_min_width, anchor=tk.W).grid(row=0, column=0, sticky=tk.W, padx=widget_padx, pady=(0, widget_pady))
        self.api_endpoint_entry = ttk.Entry(api_control_group, textvariable=self.error_api_endpoint_var)
        self.api_endpoint_entry.grid(row=0, column=1, sticky="ew", padx=widget_padx, pady=(0, widget_pady))

        # Row 2 inside control group: API Key and Buttons
        ttk.Label(api_control_group, text="API 密匙:", width=label_min_width, anchor=tk.W).grid(row=1, column=0, sticky=tk.W, padx=widget_padx, pady=widget_pady)
        key_button_frame = ttk.Frame(api_control_group, style='Analysis.TFrame')
        key_button_frame.grid(row=1, column=1, sticky="ew", padx=widget_padx, pady=widget_pady)
        key_button_frame.columnconfigure(0, weight=1) # Key entry expands
        self.api_key_entry = ttk.Entry(key_button_frame, textvariable=self.error_api_key_var, show="*")
        self.api_key_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.diagnose_button = ttk.Button(key_button_frame, text="诊断", style="Tab.TButton", command=self.run_diagnosis)
        self.diagnose_button.grid(row=0, column=1, padx=(0, 5))
        self.fix_button = ttk.Button(key_button_frame, text="修复", style="Tab.TButton", command=self.run_fix)
        self.fix_button.grid(row=0, column=2)

        analysis_current_row += 1

        # Output Text Area (CMD code display box) - Now in row 1, configured to expand
        self.error_analysis_text = scrolledtext.ScrolledText(self.analysis_frame, wrap=tk.WORD, state=tk.DISABLED, font=(FONT_FAMILY_MONO, FONT_SIZE_MONO), bg=TEXT_AREA_BG, fg=FG_STDOUT, relief=tk.FLAT, borderwidth=1, bd=1, highlightthickness=1, highlightbackground=BORDER_COLOR, insertbackground="white")
        self.error_analysis_text.grid(row=analysis_current_row, column=0, sticky="nsew", padx=frame_padx, pady=(5, 0)) # Grid in next row
        setup_text_tags(self.error_analysis_text) # Apply tags including 'api_output' and 'cmd'


        # Default to Settings tab initially
        self.notebook.select(self.settings_frame)


    # --- Text/Output Methods (MOD5: Force scroll to bottom remains unchanged) ---
    def insert_output(self, text_widget, line, tag="stdout"):
        """Inserts text into a widget with tags, handles auto-scroll."""
        if not text_widget or not text_widget.winfo_exists():
            return
        try:
            text_widget.config(state=tk.NORMAL)
            # Ensure tag exists before inserting
            if tag not in text_widget.tag_names():
                tag = "stdout" # Fallback tag
            text_widget.insert(tk.END, line, (tag,))
            # MOD5: Always scroll to the end after inserting text
            text_widget.see(tk.END)
            text_widget.config(state=tk.DISABLED)
        except tk.TclError as e:
             print(f"[Launcher ERROR] TclError inserting output: {e}")
        except Exception as e:
             print(f"[Launcher ERROR] Unexpected error inserting output: {e}")


    def log_to_gui(self, source, message, level="info", target_override=None):
        """
        Adds a message to the appropriate output queue based on the source.
        source: Module/origin (e.g., "Launcher", "ComfyUI", "Git", "Update", "Fix", "ErrorAnalysis")
        message: The log message string.
        level: Log level ("info", "warn", "error", "cmd", "api_output", "stdout", "stderr") used for tagging.
        target_override: Force message to a specific widget queue ("Launcher" or "ComfyUI").
        """
        if not message.endswith('\n'):
            message += '\n'

        # Determine the target queue and widget
        target_queue = self.launcher_log_queue # Default to Launcher log
        # Route ErrorAnalysis logs to launcher queue unless specifically stdout/stderr
        if source == "ComfyUI" or target_override == "ComfyUI":
            target_queue = self.comfyui_output_queue
        elif source == "ErrorAnalysis" and level not in ["stdout", "stderr"]: # Route API output etc. to launcher queue
             target_queue = self.launcher_log_queue

        # Determine the tag based on level and source
        tag = level # Use level directly as the primary tag indicator
        if level == "stdout" and source != "ComfyUI": # Non-ComfyUI stdout -> treat as info
             tag = "info"
        elif level == "stderr": # Always use stderr tag for errors
             tag = "stderr"
        # Allow specific tags like 'cmd', 'api_output'
        elif level in ["cmd", "api_output", "warn", "error", "info"]:
             tag = level # Keep specific level tags

        # Construct the log line prefix for context
        log_prefix = f"[{source}] " if source else ""

        # Put the formatted message and tag into the queue
        try:
             target_queue.put((log_prefix + message, tag))
        except Exception as e:
             print(f"[Launcher CRITICAL] Failed to put log message in queue: {e}")


    def process_output_queues(self):
        """Processes messages from BOTH log queues and updates text widgets."""
        # MOD6: No change needed here. Launcher logs go to launcher_log_text,
        # ComfyUI logs go to main_output_text. The clear only happens on launch.
        processed_count = 0
        max_lines_per_update = 50 # Process up to 50 lines per interval

        # Process Launcher Log Queue
        try:
            while not self.launcher_log_queue.empty() and processed_count < max_lines_per_update:
                line, tag = self.launcher_log_queue.get_nowait()
                # Route Analysis API/CMD output to error_analysis_text
                # MOD4: Route ErrorAnalysis source logs (not just specific tags) to analysis text
                # Check if the source marker (e.g., "[ErrorAnalysis] ") is present in the line
                is_error_analysis_log = False
                if line.startswith("[ErrorAnalysis]"):
                    is_error_analysis_log = True
                # Alternative check if prefix might vary
                # source_marker = f"[{'ErrorAnalysis'}] "
                # if source_marker in line:
                #    is_error_analysis_log = True

                if is_error_analysis_log:
                     # Optionally remove the source marker if needed from the line itself
                     # line = line.replace(f"[{'ErrorAnalysis'}] ", "") # Example removal
                     self.insert_output(self.error_analysis_text, line, tag)
                else:
                     self.insert_output(self.launcher_log_text, line, tag)
                processed_count += 1
        except queue.Empty:
            pass
        except Exception as e:
             print(f"[Launcher ERROR] Error processing launcher log queue: {e}")
             traceback.print_exc()


        # Process ComfyUI Log Queue
        try:
            while not self.comfyui_output_queue.empty() and processed_count < max_lines_per_update:
                line, tag = self.comfyui_output_queue.get_nowait()
                # Handle special marker
                if line.strip() == _COMFYUI_READY_MARKER_.strip():
                    print("[Launcher INFO] Received ComfyUI ready marker.")
                    self._trigger_comfyui_browser_opening()
                else:
                    # Route ComfyUI logs to main_output_text
                    self.insert_output(self.main_output_text, line, tag)
                processed_count += 1
        except queue.Empty:
            pass
        except Exception as e:
             print(f"[Launcher ERROR] Error processing comfyui log queue: {e}")
             traceback.print_exc()

        # Schedule the next check
        self.root.after(UPDATE_INTERVAL_MS, self.process_output_queues)

    def stream_output(self, process_stream, stream_name_prefix):
        """
        Reads lines from a process stream and puts them into the appropriate queue.
        stream_name_prefix: e.g., "[ComfyUI]", "[ComfyUI ERR]", "[Git stdout]", "[Fix stderr]"
        """
        is_comfyui_stream = stream_name_prefix.startswith("[ComfyUI")
        is_stderr = "ERR" in stream_name_prefix or "stderr" in stream_name_prefix

        # Determine target queue based on prefix
        target_queue = self.comfyui_output_queue if is_comfyui_stream else self.launcher_log_queue

        # Determine log level/tag
        if is_stderr:
             log_level = "stderr"
        elif is_comfyui_stream:
             log_level = "stdout" # ComfyUI stdout
        else:
             log_level = "info" # Default for other stdout (Git, Fix)

        api_port = self.config.get("comfyui_api_port", DEFAULT_COMFYUI_API_PORT)
        # More robust ready string detection
        ready_strings = [
            f"To see the GUI go to: http://127.0.0.1:{api_port}",
            f"Uvicorn running on http://127.0.0.1:{api_port}"
        ]
        # Custom marker for simpler detection if needed
        custom_ready_marker = "### ComfyUI Ready ###"

        try:
            for line in iter(process_stream.readline, ''):
                if self.stop_event.is_set():
                    print(f"[Launcher INFO] {stream_name_prefix} stream reader received stop event.")
                    break

                if line:
                    # Put the raw line into the queue with prefix and level
                    target_queue.put((stream_name_prefix + " " + line, log_level))

                    # Check for ComfyUI ready marker ONLY if it's a ComfyUI stream
                    # and we haven't sent the internal marker yet.
                    if is_comfyui_stream and not self.comfyui_ready_marker_sent:
                        if any(rs in line for rs in ready_strings) or custom_ready_marker in line:
                             print(f"[Launcher INFO] {stream_name_prefix} stream detected ready string. Queuing marker.")
                             # Queue the special internal marker
                             target_queue.put((_COMFYUI_READY_MARKER_, "info")) # Use info tag for marker
                             self.comfyui_ready_marker_sent = True

            print(f"[Launcher INFO] {stream_name_prefix} stream reader thread finished.")

        except ValueError:
             print(f"[Launcher INFO] {stream_name_prefix} stream closed unexpectedly (ValueError).")
        except Exception as e:
            print(f"[Launcher ERROR] Error reading {stream_name_prefix} stream: {e}", exc_info=True)
        finally:
            try:
                process_stream.close()
            except Exception:
                pass


    # --- Service Management ---
    def _is_comfyui_running(self):
        """Checks if the managed ComfyUI process is currently running."""
        return self.comfyui_process is not None and self.comfyui_process.poll() is None

    def _is_update_task_running(self):
        """Checks if a background update task is currently running."""
        return self._update_task_running

    def _validate_paths_for_execution(self, check_comfyui=True, check_git=False, show_error=True):
        """Validates essential paths before attempting to start services or git operations."""
        # Ensure derived paths are up-to-date based on current config
        self.update_derived_paths()

        paths_ok = True
        missing_files = []
        missing_dirs = []

        if check_comfyui:
            if not self.comfyui_install_dir or not os.path.isdir(self.comfyui_install_dir):
                missing_dirs.append(f"ComfyUI 安装目录 ({self.comfyui_install_dir or '未配置'})")
                paths_ok = False
            if not self.comfyui_portable_python or not os.path.isfile(self.comfyui_portable_python):
                missing_files.append(f"ComfyUI Python ({self.comfyui_portable_python or '未配置'})")
                paths_ok = False
            # Check main.py only if install dir seems ok
            elif self.comfyui_install_dir and os.path.isdir(self.comfyui_install_dir) and not os.path.isfile(self.comfyui_main_script):
                 missing_files.append(f"ComfyUI 主脚本 ({self.comfyui_main_script or '无法派生'})")
                 paths_ok = False

        if check_git:
             if not self.git_exe_path or not os.path.isfile(self.git_exe_path):
                  missing_files.append(f"Git 可执行文件 ({self.git_exe_path or '未配置'})")
                  paths_ok = False

        if not paths_ok and show_error:
            error_message = "启动服务或执行操作失败，缺少必需的文件或目录。\n请在“设置”中配置路径。\n\n"
            if missing_files:
                error_message += "缺少文件:\n" + "\n".join(f"- {f}" for f in missing_files) + "\n\n"
            if missing_dirs:
                error_message += "缺少目录:\n" + "\n".join(f"- {d}" for d in missing_dirs)
            messagebox.showerror("路径配置错误 / Path Configuration Error", error_message.strip(), parent=self.root)

        return paths_ok

    def start_comfyui_service_thread(self):
        """Starts ComfyUI service in a separate thread."""
        if self._is_comfyui_running():
            self.log_to_gui("Launcher", "ComfyUI 后台已在运行。", "warn")
            return
        if self.comfyui_externally_detected:
             self.log_to_gui("Launcher", f"检测到外部 ComfyUI 已在端口 {self.comfyui_api_port} 运行。请先停止外部实例。", "warn")
             return
        # MOD2: Allow starting even if update task is running (unless it's actively starting/stopping)
        # if self._is_update_task_running():
        #      self.log_to_gui("Launcher", "更新任务正在进行中，请稍候。", "warn")
        #      return
        if not self._validate_paths_for_execution(check_comfyui=True, check_git=False):
            return # Validation failed, error shown by validate function

        self.stop_event.clear()
        self.comfyui_externally_detected = False
        self.backend_browser_triggered_for_session = False
        self.comfyui_ready_marker_sent = False

        self.root.after(0, self._update_ui_state) # Update UI before starting thread

        self.progress_bar.start(10)
        # if not self.progress_bar.winfo_ismapped(): self.progress_bar.grid() # Ensure visible
        self.status_label.config(text="状态: 启动 ComfyUI 后台...")
        self.clear_output_widgets() # Clear previous logs
        # REQ: Switch to the "Logs" tab, then the "ComfyUI日志" sub-tab
        try:
             self.notebook.select(self.logs_tab_frame)
             # Find the ComfyUI log sub-tab index (assuming it's the second tab)
             comfyui_log_sub_tab_index = 1 # 0 = Launcher, 1 = ComfyUI
             if hasattr(self, 'logs_notebook') and self.logs_notebook.winfo_exists():
                 self.logs_notebook.select(comfyui_log_sub_tab_index)
        except Exception as e:
             print(f"[Launcher WARNING] Failed to switch to ComfyUI log tab: {e}")


        thread = threading.Thread(target=self._start_comfyui_service, daemon=True)
        thread.start()

    def _start_comfyui_service(self):
        """Internal method to start the ComfyUI service subprocess."""
        if self._is_comfyui_running(): # Double check within thread
            return

        port_to_check = int(self.config.get("comfyui_api_port", DEFAULT_COMFYUI_API_PORT))
        check_url = f"http://127.0.0.1:{port_to_check}/queue"
        is_already_running = False

        # Check if port is already in use before launching
        try:
            print(f"[Launcher INFO] Checking if ComfyUI is running on {check_url} before launch...")
            response = requests.get(check_url, timeout=1.0)
            if response.status_code == 200:
                is_already_running = True
                self.log_to_gui("ComfyUI", f"检测到 ComfyUI 已在端口 {port_to_check} 运行，跳过启动。", "info")
                print(f"[Launcher INFO] ComfyUI detected running on port {port_to_check}. Skipping launch.")
                self.comfyui_externally_detected = True
                self.root.after(0, self._update_ui_state)
                self.comfyui_process = None
                # Trigger browser opening for the detected instance
                self.root.after(0, self._trigger_comfyui_browser_opening) # Use root.after for thread safety
                return # Stop execution here
            else:
                 print(f"[Launcher WARNING] Port check received unexpected status {response.status_code} from {check_url}. Proceeding with launch.")
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            print(f"[Launcher INFO] Port check timed out or connection refused for {check_url}. Port {port_to_check} likely free. Proceeding with launch.")
        except Exception as e:
            print(f"[Launcher ERROR] Port check failed unexpectedly for {check_url}: {e}. Proceeding with launch.")

        # Ensure flags are reset if we proceed with launch
        self.backend_browser_triggered_for_session = False
        self.comfyui_ready_marker_sent = False
        self.comfyui_externally_detected = False

        try:
            self.log_to_gui("ComfyUI", f"启动 ComfyUI 后台于 {self.comfyui_install_dir}...", "info")
            # Ensure args are current
            self.update_derived_paths()
            base_cmd = [self.comfyui_portable_python, "-s", "-u", self.comfyui_main_script]
            comfyui_cmd_list = base_cmd + self.comfyui_base_args

            cmd_log_list = [shlex.quote(arg) for arg in comfyui_cmd_list]
            cmd_log_str = ' '.join(cmd_log_list)
            self.log_to_gui("ComfyUI", f"最终参数 / Final Arguments: {' '.join(self.comfyui_base_args)}", "info")
            self.log_to_gui("ComfyUI", f"完整命令 / Full Command: {cmd_log_str}", "cmd")

            comfy_env = os.environ.copy()
            comfy_env['PYTHONIOENCODING'] = 'utf-8' # Force UTF-8
            git_dir_in_path = os.path.dirname(self.git_exe_path) if self.git_exe_path and os.path.isdir(os.path.dirname(self.git_exe_path)) else ""
            if git_dir_in_path:
                 comfy_env['PATH'] = git_dir_in_path + os.pathsep + comfy_env.get('PATH', '')

            creationflags = 0
            startupinfo = None
            if os.name == 'nt':
                creationflags = subprocess.CREATE_NO_WINDOW

            self.comfyui_process = subprocess.Popen(
                comfyui_cmd_list,
                cwd=self.comfyui_install_dir,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                bufsize=0, # Unbuffered
                creationflags=creationflags, startupinfo=startupinfo,
                env=comfy_env, text=True, encoding='utf-8', errors='replace'
            )
            self.log_to_gui("ComfyUI", f"Backend PID: {self.comfyui_process.pid}", "info")

            # Start threads to read stdout and stderr
            self.comfyui_reader_thread_stdout = threading.Thread(target=self.stream_output, args=(self.comfyui_process.stdout, "[ComfyUI]"), daemon=True)
            self.comfyui_reader_thread_stderr = threading.Thread(target=self.stream_output, args=(self.comfyui_process.stderr, "[ComfyUI ERR]"), daemon=True)
            self.comfyui_reader_thread_stdout.start()
            self.comfyui_reader_thread_stderr.start()

            # Check if process terminated quickly after start
            time.sleep(2)
            if not self._is_comfyui_running():
                exit_code = self.comfyui_process.poll() if self.comfyui_process else 'N/A'
                error_reason = f"ComfyUI 后台进程意外终止，退出码 {exit_code}。"
                # Attempt to capture immediate output (might be empty if already read by threads)
                try:
                    stdout_output, stderr_output = self.comfyui_process.communicate(timeout=0.5) # Short timeout
                    if stdout_output: error_reason += f"\n\nStdout:\n{stdout_output.strip()}"
                    if stderr_output: error_reason += f"\n\nStderr:\n{stderr_output.strip()}"
                except subprocess.TimeoutExpired: pass # Output likely being handled by threads
                except Exception as read_err: print(f"[Launcher WARNING] Error reading immediate output: {read_err}")
                # Check if port is the likely issue
                try:
                    with socket.create_connection(("127.0.0.1", port_to_check), timeout=0.5): pass
                    error_reason += f"\n\n可能原因：端口 {port_to_check} 似乎已被占用。"
                except (ConnectionRefusedError, socket.timeout): pass # Port likely free
                except Exception: pass # Other port check error
                raise Exception(error_reason)

            self.log_to_gui("ComfyUI", "ComfyUI 后台服务已启动。", "info")
            self.root.after(0, self._update_ui_state)

        except FileNotFoundError:
             error_msg = f"启动 ComfyUI 后台失败: 找不到指定的 Python 或主脚本文件。\nPython: {self.comfyui_portable_python}\nScript: {self.comfyui_main_script}"
             print(f"[Launcher CRITICAL] {error_msg}")
             self.log_to_gui("ComfyUI", error_msg, "error")
             self.root.after(0, lambda msg=error_msg: messagebox.showerror("ComfyUI 启动错误", msg, parent=self.root))
             self.comfyui_process = None
             self.root.after(0, self.reset_ui_on_error)
        except Exception as e:
            error_msg = f"启动 ComfyUI 后台失败: {e}"
            print(f"[Launcher CRITICAL] {error_msg}", exc_info=True) # Print traceback for debug
            self.log_to_gui("ComfyUI", error_msg, "error")
            self.root.after(0, lambda msg=str(e): messagebox.showerror("ComfyUI 启动错误", f"启动 ComfyUI 后台时发生错误:\n{msg}", parent=self.root))
            self.comfyui_process = None
            self.root.after(0, self.reset_ui_on_error)


    def _stop_comfyui_service(self):
        """Internal method to stop the managed ComfyUI service subprocess."""
        self.comfyui_externally_detected = False # Assume stopping means we lose track

        if not self._is_comfyui_running():
            self.log_to_gui("Launcher", "ComfyUI 后台未由此启动器管理或未运行。", "warn")
            self.root.after(0, self._update_ui_state)
            return

        self.log_to_gui("Launcher", "停止 ComfyUI 后台...", "info")
        self.root.after(0, self._update_ui_state) # Update UI before stopping

        self.status_label.config(text="状态: 停止 ComfyUI 后台...")
        self.progress_bar.start(10)
        # if not self.progress_bar.winfo_ismapped(): self.progress_bar.grid() # Ensure visible
        try:
            self.stop_event.set() # Signal stream readers
            time.sleep(0.1)
            self.log_to_gui("ComfyUI", f"终止进程 PID: {self.comfyui_process.pid}...", "info")
            self.comfyui_process.terminate()
            try:
                self.comfyui_process.wait(timeout=10) # Wait up to 10 seconds
                self.log_to_gui("ComfyUI", "ComfyUI 后台已终止。", "info")
            except subprocess.TimeoutExpired:
                print("[Launcher WARNING] ComfyUI process did not terminate gracefully, killing.")
                self.log_to_gui("ComfyUI", "强制终止 ComfyUI 后台...", "warn")
                self.comfyui_process.kill()
                self.comfyui_process.wait(timeout=5) # Wait briefly for kill
                self.log_to_gui("ComfyUI", "ComfyUI 后台已强制终止。", "info")
        except Exception as e:
            error_msg = f"停止 ComfyUI 后台出错: {e}"
            print(f"[Launcher ERROR] {error_msg}")
            self.log_to_gui("ComfyUI", error_msg, "stderr")
        finally:
            self.comfyui_process = None
            self.stop_event.clear()
            self.backend_browser_triggered_for_session = False
            self.comfyui_ready_marker_sent = False
            self.root.after(0, self._update_ui_state) # Update UI state after stopping


    def start_all_services_thread(self):
        """Alias for starting ComfyUI, as it's the only managed service."""
        self.start_comfyui_service_thread()


    def stop_all_services(self):
        """Stops ComfyUI service and signals update worker to stop."""
        if not self._is_comfyui_running() and not self.comfyui_externally_detected and not self._is_update_task_running():
             print("[Launcher INFO] Stop all: No managed process active or detected.")
             self._update_ui_state()
             return

        self.log_to_gui("Launcher", "请求停止所有服务...", "info")
        self.root.after(0, self._update_ui_state) # Update UI before stopping
        self.status_label.config(text="状态: 停止所有服务...")
        self.progress_bar.start(10)
        # if not self.progress_bar.winfo_ismapped(): self.progress_bar.grid() # Ensure visible

        if self._is_comfyui_running():
             self._stop_comfyui_service() # Handles its own UI updates within
        elif self.comfyui_externally_detected:
            self.comfyui_externally_detected = False
            self.log_to_gui("Launcher", "检测到外部 ComfyUI，未尝试停止。", "info")

        if self._is_update_task_running():
             self.log_to_gui("Launcher", "请求停止当前更新任务...", "info")
             self.stop_event.set() # Signal worker thread

        # Final UI update is handled by _stop_comfyui_service or worker thread completion
        # Or call it here after a short delay to catch the final state
        self.root.after(100, self._update_ui_state)


    # --- Git Execution Helper ---
    def _run_git_command(self, command_list, cwd, timeout=300, log_output=True):
        """Runs a git command, logs output, and returns stdout, stderr, return code."""
        git_exe = self.git_exe_path_var.get()
        if not git_exe or not os.path.isfile(git_exe):
             err_msg = f"Git 可执行文件路径未配置或无效: {git_exe}"
             if log_output: self.log_to_gui("Git", err_msg, "error")
             return "", err_msg, 127

        full_cmd = [git_exe] + command_list
        git_env = os.environ.copy()
        git_env['PYTHONIOENCODING'] = 'utf-8'
        # Prevent git from asking for credentials interactively
        git_env['GIT_TERMINAL_PROMPT'] = '0'

        if not os.path.isdir(cwd):
             err_msg = f"Git 命令工作目录不存在或无效: {cwd}"
             if log_output: self.log_to_gui("Git", err_msg, "error")
             return "", err_msg, 1

        try:
            cmd_log_list = [shlex.quote(arg) for arg in full_cmd]
            cmd_log_str = ' '.join(cmd_log_list)
            if log_output:
                 # Log with 'cmd' level to potentially route differently if needed
                 self.log_to_gui("Git", f"执行: {cmd_log_str}", "cmd")
                 self.log_to_gui("Git", f"工作目录: {cwd}", "cmd")

            process = subprocess.Popen(
                full_cmd,
                cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding='utf-8', errors='replace',
                startupinfo=None, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                env=git_env
            )

            stdout_full = ""
            stderr_full = ""
            try:
                stdout_full, stderr_full = process.communicate(timeout=timeout)
                returncode = process.returncode
                # Log captured output if requested
                if log_output:
                    if stdout_full: self.log_to_gui("Git", stdout_full, "stdout") # Log git stdout
                    if stderr_full: self.log_to_gui("Git", stderr_full, "stderr") # Log git stderr
            except subprocess.TimeoutExpired:
                if log_output: self.log_to_gui("Git", f"Git 命令超时 ({timeout} 秒), 进程被终止。", "error")
                try: process.kill()
                except OSError: pass
                returncode = 124 # Standard timeout exit code
                stdout_full, stderr_full = "", "命令执行超时 / Command timed out"

            if log_output and returncode != 0:
                 self.log_to_gui("Git", f"Git 命令返回非零退出码 {returncode}。", "warn")

            return stdout_full, stderr_full, returncode

        except FileNotFoundError:
            error_msg = f"Git 可执行文件未找到: {git_exe}"
            if log_output: self.log_to_gui("Git", error_msg, "error")
            return "", error_msg, 127
        except Exception as e:
            error_msg = f"执行 Git 命令时发生意外错误: {e}\n命令: {' '.join(full_cmd)}"
            if log_output: self.log_to_gui("Git", error_msg, "error")
            return "", error_msg, 1


    # --- Update Task Worker Thread ---
    def _update_task_worker(self):
        """Worker thread that processes update tasks from the queue."""
        while True:
            task_func, task_args, task_kwargs = None, None, None # Define outside try
            try:
                task_func, task_args, task_kwargs = self.update_task_queue.get(timeout=1) # Use timeout
                if self.stop_event.is_set(): # Check if stopped while waiting
                    self.log_to_gui("Launcher", f"更新任务 '{task_func.__name__ if task_func else 'Unknown'}' 从队列中移除，因为收到停止信号。", "warn")
                    self.update_task_queue.task_done()
                    continue # Skip processing this task

                self._update_task_running = True
                self.root.after(0, self._update_ui_state)
                self.log_to_gui("Launcher", f"执行更新任务: {task_func.__name__}", "info")

                try:
                    task_func(*task_args, **task_kwargs)
                except threading.ThreadExit: # Handle explicit stop signal within task
                     self.log_to_gui("Launcher", f"更新任务 '{task_func.__name__}' 被取消。", "warn")
                except Exception as e:
                    print(f"[Launcher ERROR] Update task '{task_func.__name__}' failed: {e}", exc_info=True)
                    self.log_to_gui("Launcher", f"更新任务 '{task_func.__name__}' 执行失败: {e}", "error")
                    # Show error in GUI thread
                    self.root.after(0, lambda name=task_func.__name__, msg=str(e): messagebox.showerror("更新任务失败", f"任务 '{name}' 执行失败:\n{msg}", parent=self.root))

                finally:
                    self.update_task_queue.task_done()
                    self._update_task_running = False
                    self.stop_event.clear() # Reset stop event for the next task
                    self.log_to_gui("Launcher", f"更新任务 '{task_func.__name__}' 完成。", "info")
                    self.root.after(0, self._update_ui_state)

            except queue.Empty:
                # Timeout occurred, loop continues to check stop_event or wait again
                if self.stop_event.is_set():
                    # print("[Launcher DEBUG] Update worker detected stop event during idle.")
                    # Potentially break the loop if no more tasks are expected? Or just continue waiting.
                    pass # Continue waiting for tasks or external close signal
                continue
            except Exception as e:
                # Catch errors in the worker loop itself
                print(f"[Launcher CRITICAL] Error in update task worker loop: {e}", exc_info=True)
                # Ensure state is reset if loop fails catastrophically
                self._update_task_running = False
                self.stop_event.clear()
                if task_func: # If a task was retrieved before error
                    try: self.update_task_queue.task_done()
                    except ValueError: pass # Ignore if task_done called multiple times
                self.root.after(0, self._update_ui_state) # Try to update UI state
                time.sleep(1) # Prevent tight loop on unexpected errors


    # --- Queueing Methods for UI actions ---
    def _queue_main_body_refresh(self):
        """Queues the main body version refresh task."""
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中...", "warn"); return
        if not self._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=True):
             return

        self.log_to_gui("Launcher", "将刷新本体版本任务添加到队列...", "info")
        self.update_task_queue.put((self.refresh_main_body_versions, [], {}))
        self.root.after(0, self._update_ui_state)

    def _queue_main_body_activation(self):
        """Queues the main body version activation task."""
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中...", "warn"); return

        selected_item = self.main_body_tree.focus()
        if not selected_item:
            messagebox.showwarning("未选择版本", "请从列表中选择一个要激活的本体版本。", parent=self.root)
            return

        version_data = self.main_body_tree.item(selected_item, 'values')
        if not version_data or len(version_data) < 4:
             self.log_to_gui("Update", "无法获取选中的本体版本数据。", "error")
             return

        # REQ: Use full commit ID for activation, which is stored in remote_main_body_versions
        selected_commit_id_short = version_data[1] # Short ID for display/lookup
        selected_version_display = version_data[0]
        full_commit_id = None

        # Find the full commit ID from the stored data based on the short ID
        for ver_data in self.remote_main_body_versions:
            # Match start for branches/tags (short ID is from commit_id[:8])
            # Check if commit_id exists and is a string before calling startswith
            commit_id_str = ver_data.get("commit_id")
            if isinstance(commit_id_str, str) and commit_id_str.startswith(selected_commit_id_short):
                 full_commit_id = ver_data["commit_id"]
                 break

        if not full_commit_id:
             # Fallback: Try to resolve using git rev-parse (requires Git)
             self.log_to_gui("Update", f"无法在缓存中找到 '{selected_commit_id_short}' 的完整ID，尝试 Git 解析...", "warn")
             comfyui_dir = self.comfyui_dir_var.get()
             if comfyui_dir and os.path.isdir(os.path.join(comfyui_dir, ".git")):
                 stdout, _, rc = self._run_git_command(["rev-parse", selected_commit_id_short], cwd=comfyui_dir, timeout=10, log_output=False)
                 if rc == 0 and stdout:
                     full_commit_id = stdout.strip()
                     self.log_to_gui("Update", f"Git 解析到完整 ID: {full_commit_id}", "info")
                 else:
                     self.log_to_gui("Update", f"无法解析提交ID '{selected_commit_id_short}' 的完整ID。", "error")
                     messagebox.showerror("激活失败", f"无法解析要激活的提交ID '{selected_commit_id_short}'。", parent=self.root)
                     return
             else:
                  self.log_to_gui("Update", "ComfyUI 目录不是 Git 仓库，无法解析提交ID。", "error")
                  messagebox.showerror("激活失败", "ComfyUI 目录不是 Git 仓库，无法解析提交ID。", parent=self.root)
                  return

        # Validate paths
        if not self._validate_paths_for_execution(check_comfyui=True, check_git=True, show_error=True):
             return
        comfyui_dir = self.comfyui_dir_var.get()
        if not os.path.isdir(os.path.join(comfyui_dir, ".git")):
             messagebox.showerror("Git 仓库错误", f"ComfyUI 安装目录不是一个有效的 Git 仓库:\n{comfyui_dir}", parent=self.root)
             return

        confirm = messagebox.askyesno("确认激活", f"确定要下载并覆盖安装本体版本 '{selected_version_display}' (提交ID: {full_commit_id[:8]}) 吗？\n此操作会修改 '{comfyui_dir}' 目录。\n\n警告: 可能导致节点不兼容！", parent=self.root)
        if not confirm: return

        self.log_to_gui("Launcher", f"将激活本体版本 '{full_commit_id[:8]}' 任务添加到队列...", "info")
        self.update_task_queue.put((self._activate_main_body_version_task, [comfyui_dir, full_commit_id], {})) # Pass full ID
        self.root.after(0, self._update_ui_state)

    def _queue_node_list_refresh(self):
        """Queues the node list refresh task."""
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中...", "warn"); return
        # Git path validation happens inside refresh task
        self.log_to_gui("Launcher", "将刷新节点列表任务添加到队列...", "info")
        self.update_task_queue.put((self.refresh_node_list, [], {}))
        self.root.after(0, self._update_ui_state)

    # REQ: Modified logic for "切换版本" button (Removed confirmation)
    def _queue_node_switch_or_show_history(self):
        """Handles click on '切换版本' button: shows history modal for installed git nodes, queues install for others."""
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中...", "warn"); return

        selected_item = self.nodes_tree.focus()
        if not selected_item:
            messagebox.showwarning("未选择节点", "请从列表中选择一个要操作的节点。", parent=self.root)
            return

        node_data = self.nodes_tree.item(selected_item, 'values')
        if not node_data or len(node_data) < 5:
             self.log_to_gui("Update", "无法获取选中的节点数据。", "error"); return

        node_name = node_data[0]
        node_status = node_data[1]
        repo_info = node_data[3] # Remote info string
        repo_url = node_data[4] # Repo URL

        # Validate paths first
        if not self._validate_paths_for_execution(check_comfyui=True, check_git=True, show_error=True):
             return
        if not self.comfyui_nodes_dir or not os.path.isdir(self.comfyui_nodes_dir):
             messagebox.showerror("目录错误", f"ComfyUI custom_nodes 目录未找到或无效:\n{self.comfyui_nodes_dir}", parent=self.root)
             return
        if not repo_url or repo_url in ("本地安装，无Git信息", "无法获取远程 URL", "本地安装", "N/A", "无远程仓库"):
             messagebox.showerror("节点信息缺失", f"节点 '{node_name}' 无有效的仓库地址，无法进行版本切换或安装。", parent=self.root)
             return

        node_install_path = os.path.normpath(os.path.join(self.comfyui_nodes_dir, node_name))
        is_installed_and_git = os.path.isdir(node_install_path) and os.path.isdir(os.path.join(node_install_path, ".git"))

        if is_installed_and_git:
            # Node is installed and is a Git repo -> Show History Modal
            # MOD2: Removed confirmation dialog here
             self.log_to_gui("Launcher", f"将获取节点 '{node_name}' 版本历史任务添加到队列...", "info")
             self.update_task_queue.put((self._node_history_fetch_task, [node_name, node_install_path], {}))
        else:
            # Node is not installed or not a Git repo -> Install (Clone)
             target_ref_for_install = "main" # Default branch
             # Try to parse target ref from repo_info if available and not installed
             if node_status == "未安装" and repo_info and not repo_info.startswith("信息获取失败"):
                 # Simple split, assumes format "target (status)" or "在线目标: target"
                 if "在线目标:" in repo_info:
                      potential_ref = repo_info.split("在线目标:", 1)[-1].strip()
                 else:
                      parts = repo_info.split('(')
                      potential_ref = parts[0].strip()

                 # Avoid using placeholders as refs
                 if potential_ref and potential_ref not in ("未知远程", "N/A", "在线目标:", "在线目标"):
                     target_ref_for_install = potential_ref

             confirm_msg = f"确定要安装节点 '{node_name}' 吗？\n" \
                           f"仓库地址: {repo_url}\n" \
                           f"目标引用/分支: {target_ref_for_install}\n" \
                           f"目标目录: {node_install_path}\n\n" \
                           f"确认前请确保 ComfyUI 已停止运行。"
             confirm = messagebox.askyesno("确认安装", confirm_msg, parent=self.root)
             if not confirm: return

             self.log_to_gui("Launcher", f"将安装节点 '{node_name}' (目标引用: {target_ref_for_install}) 任务添加到队列...", "info")
             self.update_task_queue.put((self._install_node_task, [node_name, node_install_path, repo_url, target_ref_for_install], {}))

        self.root.after(0, self._update_ui_state) # Update UI state immediately


    def _queue_all_nodes_update(self):
        """Queues the task to update all installed git nodes."""
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中...", "warn"); return
        if not self._validate_paths_for_execution(check_comfyui=True, check_git=True, show_error=True):
             return
        if not self.comfyui_nodes_dir or not os.path.isdir(self.comfyui_nodes_dir):
             messagebox.showerror("目录错误", f"ComfyUI custom_nodes 目录未找到或无效:\n{self.comfyui_nodes_dir}", parent=self.root)
             return

        nodes_to_update = [
            node for node in self.local_nodes_only
            if node.get("is_git") and node.get("repo_url") and node.get("repo_url") not in ("本地安装，无Git信息", "无法获取远程 URL", "本地安装", "N/A", "无远程仓库") and node.get("remote_branch") and node.get("remote_branch") != "N/A" # Ensure remote branch is known
        ]
        if not nodes_to_update:
             messagebox.showinfo("无节点可更新", "没有找到可更新的已安装 Git 节点（具有有效的远程跟踪分支）。", parent=self.root)
             return

        confirm = messagebox.askyesno("确认更新全部", f"确定要尝试更新 {len(nodes_to_update)} 个已安装节点吗？\n此操作将执行 Git pull。\n\n警告：可能丢失本地修改！\n确认前请确保 ComfyUI 已停止运行。", parent=self.root)
        if not confirm: return

        self.log_to_gui("Launcher", f"将更新全部节点任务添加到队列 (共 {len(nodes_to_update)} 个)...", "info")
        self.update_task_queue.put((self._update_all_nodes_task, [nodes_to_update], {}))
        self.root.after(0, self._update_ui_state)

    def _queue_node_uninstall(self):
        """Queues the node uninstall task."""
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中...", "warn"); return

        selected_item = self.nodes_tree.focus()
        if not selected_item:
            messagebox.showwarning("未选择节点", "请从列表中选择一个要卸载的节点。", parent=self.root)
            return
        node_data = self.nodes_tree.item(selected_item, 'values')
        if not node_data or len(node_data) < 5:
             self.log_to_gui("Update", "无法获取选中的节点数据。", "error"); return

        node_name = node_data[0]
        node_status = node_data[1]

        if node_status != "已安装":
             messagebox.showwarning("节点未安装", f"节点 '{node_name}' 未安装。", parent=self.root)
             return

        # Path validation
        if not self.comfyui_nodes_dir or not os.path.isdir(self.comfyui_nodes_dir):
             messagebox.showerror("目录错误", f"ComfyUI custom_nodes 目录未找到或无效:\n{self.comfyui_nodes_dir}", parent=self.root)
             return
        node_install_path = os.path.normpath(os.path.join(self.comfyui_nodes_dir, node_name))
        if not os.path.isdir(node_install_path):
             messagebox.showerror("目录错误", f"节点目录不存在或无效:\n{node_install_path}", parent=self.root)
             self.root.after(0, self._queue_node_list_refresh) # Refresh list if directory is missing
             return

        confirm = messagebox.askyesno(
             "确认卸载节点",
             f"确定要永久删除节点 '{node_name}' 及其目录 '{node_install_path}' 吗？\n此操作不可撤销。\n\n确认前请确保 ComfyUI 已停止运行。",
             parent=self.root)
        if not confirm: return

        self.log_to_gui("Launcher", f"将卸载节点 '{node_name}' 任务添加到队列...", "info")
        self.update_task_queue.put((self._node_uninstall_task, [node_name, node_install_path], {}))
        self.root.after(0, self._update_ui_state)


    # --- Initial Data Loading Task ---
    def start_initial_data_load(self):
         """Starts the initial data loading tasks in a background thread."""
         if self._is_update_task_running():
              print("[Launcher INFO] Initial data load skipped, an update task is already running.")
              return

         self.log_to_gui("Launcher", "开始加载更新管理数据...", "info")
         self.update_task_queue.put((self._run_initial_background_tasks, [], {}))
         self.root.after(0, self._update_ui_state) # Show busy state


    def _run_initial_background_tasks(self):
         """Executes the initial data loading tasks. Runs in worker thread."""
         self.log_to_gui("Launcher", "执行后台数据加载 (本体版本和节点列表)...", "info")
         git_path_ok = self._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=False)
         if not git_path_ok:
             self.log_to_gui("Launcher", "Git 路径无效，数据加载将受限。", "warn")

         # Refresh main body versions first
         self.refresh_main_body_versions()

         if self.stop_event.is_set():
              self.log_to_gui("Launcher", "后台数据加载任务已取消 (停止信号)。", "warn"); return

         # Then refresh node list
         self.refresh_node_list()

         if not self.stop_event.is_set():
             self.log_to_gui("Launcher", "后台数据加载完成。", "info")


    # --- Update Management Tasks (Executed in Worker Thread) ---

    # MOD2: Use robust date parsing and custom sort key
    def refresh_main_body_versions(self):
        """Fetches and displays ComfyUI main body versions using Git. Runs in worker thread."""
        if self.stop_event.is_set():
             return
        self.log_to_gui("Update", "刷新本体版本列表...", "info")

        main_repo_url = self.main_repo_url_var.get()
        comfyui_dir = self.comfyui_dir_var.get()
        git_path_ok = self._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=False)
        is_git_repo = git_path_ok and comfyui_dir and os.path.isdir(comfyui_dir) and os.path.isdir(os.path.join(comfyui_dir, ".git"))

        # Clear existing list in GUI thread
        self.root.after(0, lambda: [self.main_body_tree.delete(item) for item in self.main_body_tree.get_children()])
        self.remote_main_body_versions = [] # Clear stored data

        # Get Current Local Version
        local_version_display = "未知 / Unknown"
        if is_git_repo:
             stdout_id_short, _, rc_short = self._run_git_command(["rev-parse", "--short=8", "HEAD"], cwd=comfyui_dir, timeout=10, log_output=False)
             if rc_short == 0 and stdout_id_short:
                 local_version_display = f"本地 Commit: {stdout_id_short.strip()}"
             else:
                 stdout_desc, _, rc_desc = self._run_git_command(["describe", "--all", "--long", "--always"], cwd=comfyui_dir, timeout=10, log_output=False)
                 if rc_desc == 0 and stdout_desc:
                     local_version_display = f"本地: {stdout_desc.strip()}"
                 else:
                      local_version_display = "读取本地版本失败"
                      self.log_to_gui("Update", "无法获取本地本体版本信息。", "warn")
        else:
             local_version_display = "非 Git 仓库或路径无效"

        self.root.after(0, lambda lv=local_version_display: self.current_main_body_version_var.set(lv))

        if self.stop_event.is_set(): return

        # Fetch Remote Versions
        all_versions = []
        if is_git_repo and main_repo_url:
             self.log_to_gui("Update", f"尝试从 {main_repo_url} 刷新远程版本列表...", "info")
             stdout_get_url, _, rc_get_url = self._run_git_command(["remote", "get-url", "origin"], cwd=comfyui_dir, timeout=10)
             current_url = stdout_get_url.strip() if rc_get_url == 0 else None
             if not current_url or current_url != main_repo_url:
                  action = "set-url" if current_url else "add"
                  self.log_to_gui("Update", f"远程 origin URL 不匹配或缺失，尝试 git remote {action} origin...", "warn")
                  _, stderr_set, rc_set = self._run_git_command(["remote", action, "origin", main_repo_url], cwd=comfyui_dir, timeout=15)
                  if rc_set != 0: self.log_to_gui("Update", f"设置/添加远程 origin 失败: {stderr_set.strip()}", "error")

             if self.stop_event.is_set(): return

             self.log_to_gui("Update", "执行 Git fetch origin...", "info")
             _, stderr_fetch, rc_fetch = self._run_git_command(["fetch", "origin", "--prune", "--tags", "-f"], cwd=comfyui_dir, timeout=180)
             if rc_fetch != 0:
                  self.log_to_gui("Update", f"Git fetch 失败: {stderr_fetch.strip()}", "error")
                  self.root.after(0, lambda: self.main_body_tree.insert("", tk.END, values=("获取失败", "", "", "无法获取远程版本信息")))
                  return

             if self.stop_event.is_set(): return

             # Get remote branches
             # Use iso-strict for better parsing, include subject
             branches_output, _, _ = self._run_git_command(
                  ["for-each-ref", "refs/remotes/origin/", "--sort=-committerdate", "--format=%(refname:short) %(objectname) %(committerdate:iso-strict) %(contents:subject)"],
                  cwd=comfyui_dir, timeout=60 )
             for line in branches_output.splitlines():
                  parts = line.split(' ', 3)
                  if len(parts) >= 3: # Subject might be empty
                       refname, commit_id, date_iso = parts[0].replace("origin/", ""), parts[1], parts[2]
                       description = parts[3].strip() if len(parts) == 4 else "N/A"
                       if "HEAD->" not in refname:
                            all_versions.append({"type": "branch", "name": refname, "commit_id": commit_id, "date_iso": date_iso, "description": description})

             if self.stop_event.is_set(): return

             # Get tags
             # Use iso-strict for better parsing, include subject
             tags_output, _, _ = self._run_git_command(
                  ["for-each-ref", "refs/tags/", "--sort=-taggerdate", "--format=%(refname:short) %(objectname) %(taggerdate:iso-strict) %(contents:subject)"],
                  cwd=comfyui_dir, timeout=60 )
             for line in tags_output.splitlines():
                  parts = line.split(' ', 3)
                  if len(parts) >= 3: # Subject might be empty
                       refname, commit_id, date_iso = parts[0].replace("refs/tags/", ""), parts[1], parts[2]
                       description = parts[3].strip() if len(parts) == 4 else "N/A"
                       all_versions.append({"type": "tag", "name": refname, "commit_id": commit_id, "date_iso": date_iso, "description": description})

             # MOD2: Sort using the custom comparison function
             all_versions.sort(key=cmp_to_key(_compare_versions_for_sort))

        else:
             self.log_to_gui("Update", "无法获取远程版本信息 (非Git仓库或缺少URL)。", "warn")
             self.root.after(0, lambda: self.main_body_tree.insert("", tk.END, values=("无远程信息", "", "", "")))

        self.remote_main_body_versions = all_versions

        if not all_versions and is_git_repo and main_repo_url:
             self.log_to_gui("Update", "未从远程仓库获取到版本信息。", "warn")
             self.root.after(0, lambda: self.main_body_tree.insert("", tk.END, values=("无远程版本", "", "", "")))
        else:
             for ver_data in all_versions:
                 if self.stop_event.is_set(): break
                 version_display = f"{ver_data['type']} / {ver_data['name']}"
                 commit_display = ver_data.get("commit_id", "N/A")[:8]
                 # MOD2: Improved date display logic
                 date_obj = _parse_iso_date_for_sort(ver_data.get('date_iso'))
                 if date_obj:
                     try:
                         # Display date only, maybe add time if needed later
                         date_display = date_obj.strftime('%Y-%m-%d')
                     except ValueError: # Handle potential strftime errors for unusual dates
                         date_display = "日期格式错误"
                 else:
                     date_display = "日期解析失败" # Clearer message for failed parsing

                 description_display = ver_data.get("description", "N/A")
                 self.root.after(0, lambda v=(version_display, commit_display, date_display, description_display): self.main_body_tree.insert("", tk.END, values=v))

        self.log_to_gui("Update", f"本体版本列表刷新完成。", "info")


    def _activate_main_body_version_task(self, comfyui_dir, target_commit_id):
        """Task to execute git commands for activating main body version. Runs in worker thread."""
        if self.stop_event.is_set(): return
        self.log_to_gui("Update", f"正在激活本体版本 (提交ID: {target_commit_id[:8]})...", "info")

        try:
            # 1. Fetch latest changes (includes tags)
            self.log_to_gui("Update", "执行 Git fetch origin...", "info")
            _, stderr_fetch, rc_fetch = self._run_git_command(["fetch", "origin", "--prune", "--tags", "-f"], cwd=comfyui_dir, timeout=180)
            if rc_fetch != 0: raise Exception(f"Git fetch 失败: {stderr_fetch.strip()}")
            if self.stop_event.is_set(): raise threading.ThreadExit

            # 2. Reset local changes and checkout target commit
            stdout_status, _, _ = self._run_git_command(["status", "--porcelain"], cwd=comfyui_dir, timeout=10)
            if stdout_status.strip():
                 self.log_to_gui("Update", "检测到本体目录存在未提交的本地修改，将通过 reset --hard 覆盖。", "warn")

            self.log_to_gui("Update", f"执行 Git reset --hard {target_commit_id[:8]}...", "info")
            _, stderr_reset, rc_reset = self._run_git_command(["reset", "--hard", target_commit_id], cwd=comfyui_dir, timeout=60)
            if rc_reset != 0: raise Exception(f"Git reset --hard 失败: {stderr_reset.strip()}")
            if self.stop_event.is_set(): raise threading.ThreadExit

            # 3. Update submodules
            if os.path.exists(os.path.join(comfyui_dir, ".gitmodules")):
                 self.log_to_gui("Update", "执行 Git submodule update...", "info")
                 _, stderr_sub, rc_sub = self._run_git_command(["submodule", "update", "--init", "--recursive", "--force"], cwd=comfyui_dir, timeout=180)
                 if rc_sub != 0: self.log_to_gui("Update", f"Git submodule update 失败: {stderr_sub.strip()}", "warn") # Warn only
            if self.stop_event.is_set(): raise threading.ThreadExit

            # 4. Re-install Python dependencies
            python_exe = self.python_exe_var.get()
            requirements_path = os.path.join(comfyui_dir, "requirements.txt")
            if python_exe and os.path.isfile(python_exe) and os.path.isfile(requirements_path):
                 self.log_to_gui("Update", "执行 pip 安装依赖...", "info")
                 # Construct pip command carefully
                 pip_cmd_base = [python_exe, "-m", "pip", "install", "-r", requirements_path, "--upgrade"]
                 # Add extra index URLs common for ComfyUI
                 pip_cmd_extras = ["--extra-index-url", "https://download.pytorch.org/whl/cu118",
                                   "--extra-index-url", "https://download.pytorch.org/whl/cu121"]
                                # Add other indices if needed, e.g., rocm:
                                # "--extra-index-url", "https://download.pytorch.org/whl/rocm5.7"]
                 pip_cmd = pip_cmd_base + pip_cmd_extras

                 # Handle --user flag only if not in a virtual environment and not Windows
                 is_venv = sys.prefix != sys.base_prefix
                 if platform.system() != "Windows" and not is_venv:
                      pip_cmd.append("--user")
                      self.log_to_gui("Update", "非虚拟环境，使用 --user 选项安装依赖。", "warn")

                 _, stderr_pip, rc_pip = self._run_git_command(pip_cmd, cwd=comfyui_dir, timeout=600) # Longer timeout for pip
                 if rc_pip != 0:
                      self.log_to_gui("Update", f"Pip 安装依赖失败: {stderr_pip.strip()}", "error")
                      self.root.after(0, lambda: messagebox.showwarning("依赖安装失败", "Python 依赖安装失败，新版本可能无法正常工作。\n请查看日志获取详情。", parent=self.root))
                 else:
                      self.log_to_gui("Update", "Pip 安装依赖完成。", "info")
            else:
                 self.log_to_gui("Update", "Python 或 requirements.txt 无效，跳过依赖安装。", "warn")

            # Success
            self.log_to_gui("Update", f"本体版本激活流程完成 (提交ID: {target_commit_id[:8]})。", "info")
            self.root.after(0, lambda: messagebox.showinfo("激活完成", f"本体版本已激活到提交: {target_commit_id[:8]}", parent=self.root))

        except threading.ThreadExit:
             self.log_to_gui("Update", "本体版本激活任务已取消。", "warn")
        except Exception as e:
            error_msg = f"本体版本激活流程失败: {e}"
            self.log_to_gui("Update", error_msg, "error")
            self.root.after(0, lambda msg=str(e): messagebox.showerror("激活失败", msg, parent=self.root))
        finally:
            # Refresh main body list in GUI thread to show updated local version
            self.root.after(0, self._queue_main_body_refresh)


    # REQ: Refresh Node List (Updated logic for local/remote/search)
    def refresh_node_list(self):
        """Fetches and displays custom node list (local scan + online config), applying filter. Runs in worker thread."""
        # MOD5: No changes needed here based on analysis of the stuck progress bar issue.
        # The logic for task completion and UI state update appears correct.
        if self.stop_event.is_set(): return
        self.log_to_gui("Update", "刷新节点列表...", "info")

        node_config_url = self.node_config_url_var.get()
        comfyui_nodes_dir = self.comfyui_nodes_dir
        search_term_value = ""
        try:
            if hasattr(self, 'nodes_search_entry') and self.nodes_search_entry.winfo_exists():
                search_term_value = self.nodes_search_entry.get().strip().lower()
        except tk.TclError: pass # Handle widget not existing yet

        git_path_ok = self._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=False)
        is_nodes_dir_valid = comfyui_nodes_dir and os.path.isdir(comfyui_nodes_dir)

        # Clear existing list in GUI thread
        self.root.after(0, lambda: [self.nodes_tree.delete(item) for item in self.nodes_tree.get_children()])
        self.local_nodes_only = [] # Reset local node cache

        # --- Scan Local custom_nodes directory ---
        if is_nodes_dir_valid:
             self.log_to_gui("Update", f"扫描本地 custom_nodes 目录: {comfyui_nodes_dir}...", "info")
             try:
                  item_names = sorted(os.listdir(comfyui_nodes_dir))
                  for item_name in item_names:
                       if self.stop_event.is_set(): raise threading.ThreadExit

                       item_path = os.path.join(comfyui_nodes_dir, item_name)
                       if os.path.isdir(item_path):
                            node_info = {"name": item_name, "status": "已安装", "local_id": "N/A", "local_commit_full": None, "repo_info": "N/A", "repo_url": "本地安装", "is_git": False, "remote_branch": None}

                            if git_path_ok and os.path.isdir(os.path.join(item_path, ".git")):
                                 node_info["is_git"] = True

                                 # Get Local Short ID (8 chars) and Full ID
                                 stdout_id_short, _, rc_id_short = self._run_git_command(["rev-parse", "--short=8", "HEAD"], cwd=item_path, timeout=5, log_output=False)
                                 node_info["local_id"] = stdout_id_short.strip() if rc_id_short == 0 and stdout_id_short else "获取失败"
                                 stdout_id_full, _, rc_id_full = self._run_git_command(["rev-parse", "HEAD"], cwd=item_path, timeout=5, log_output=False)
                                 node_info["local_commit_full"] = stdout_id_full.strip() if rc_id_full == 0 and stdout_id_full else None


                                 # Get Remote URL
                                 stdout_url, _, rc_url = self._run_git_command(["remote", "get-url", "origin"], cwd=item_path, timeout=5, log_output=False)
                                 node_info["repo_url"] = stdout_url.strip() if rc_url == 0 and stdout_url else "无远程仓库"

                                 # Get Upstream Branch and Remote Info
                                 local_branch_stdout, _, rc_local_branch = self._run_git_command(["symbolic-ref", "--short", "HEAD"], cwd=item_path, timeout=5, log_output=False)
                                 upstream_ref = None
                                 if rc_local_branch == 0 and local_branch_stdout:
                                     local_branch_name = local_branch_stdout.strip()
                                     upstream_stdout, _, rc_upstream = self._run_git_command(["for-each-ref", "--format=%(upstream:short)", f"refs/heads/{local_branch_name}"], cwd=item_path, timeout=5, log_output=False)
                                     if rc_upstream == 0 and upstream_stdout:
                                         upstream_ref = upstream_stdout.strip()

                                 repo_info_display = "无远程跟踪"
                                 if upstream_ref and upstream_ref.startswith("origin/"):
                                     remote_branch_name = upstream_ref.replace("origin/", "")
                                     node_info["remote_branch"] = remote_branch_name # Store for update all

                                     log_cmd = ["log", "-1", "--format=%H %ci", upstream_ref] # Use ISO date
                                     stdout_log, _, rc_log = self._run_git_command(log_cmd, cwd=item_path, timeout=10, log_output=False)
                                     if rc_log == 0 and stdout_log:
                                          log_parts = stdout_log.strip().split(' ', 1)
                                          if len(log_parts) == 2:
                                               full_commit_id_remote, date_iso = log_parts[0], log_parts[1]
                                               remote_commit_id_short = full_commit_id_remote[:8]
                                               date_obj = _parse_iso_date_for_sort(date_iso)
                                               remote_commit_date = date_obj.strftime('%Y-%m-%d') if date_obj else "未知日期"
                                               repo_info_display = f"{remote_commit_id_short} ({remote_commit_date})"
                                          else: repo_info_display = f"{remote_branch_name} (日志解析失败)"
                                     else: repo_info_display = f"{remote_branch_name} (信息获取失败)"
                                 elif upstream_ref: # Tracks something else?
                                      repo_info_display = f"跟踪: {upstream_ref}"

                                 node_info["repo_info"] = repo_info_display

                            self.local_nodes_only.append(node_info)

             except threading.ThreadExit: return
             except Exception as e:
                  self.log_to_gui("Update", f"扫描本地 custom_nodes 目录时出错: {e}", "error", target_override="Launcher")
                  self.root.after(0, lambda: self.nodes_tree.insert("", tk.END, values=("扫描失败", "错误", "N/A", "扫描本地目录时出错", "N/A")))
        else: # Nodes dir not valid
             self.log_to_gui("Update", f"ComfyUI custom_nodes 目录无效，跳过本地扫描。", "warn")
             self.root.after(0, lambda: self.nodes_tree.insert("", tk.END, values=("本地目录无效", "错误", "N/A", "", "")))

        if self.stop_event.is_set(): return

        # --- Fetching Online Config Data ---
        online_nodes_config = []
        if node_config_url:
            online_nodes_config = self._fetch_online_node_config() # Runs in this worker thread
        else:
            self.log_to_gui("Update", "节点配置地址未设置，跳过在线配置获取。", "warn")

        if self.stop_event.is_set(): return

        # --- Combine local and online data ---
        local_node_dict_lower = {node['name'].lower(): node for node in self.local_nodes_only}
        combined_nodes_dict = {node['name'].lower(): node for node in self.local_nodes_only} # Start with local

        for online_node in online_nodes_config:
             if self.stop_event.is_set(): break
             try:
                 node_name = online_node.get('title') or online_node.get('name')
                 if not node_name: continue
                 node_name_lower = node_name.lower()
                 repo_url = online_node.get('files', [None])[0]
                 if not repo_url or not repo_url.endswith(".git"): continue

                 target_ref = online_node.get('reference') or online_node.get('branch') or 'main'

                 if node_name_lower not in local_node_dict_lower:
                     online_repo_info_display = f"在线目标: {target_ref}"
                     combined_nodes_dict[node_name_lower] = {
                         "name": node_name, "status": "未安装", "local_id": "N/A", "local_commit_full": None,
                         "repo_info": online_repo_info_display, "repo_url": repo_url,
                         "is_git": True
                     }
             except Exception as e:
                 print(f"[Launcher WARNING] Error processing online node entry: {online_node}. Error: {e}")
                 self.log_to_gui("Update", f"处理在线节点条目时出错: {e}", "warn")

        # Convert combined dict back to list and sort
        self.all_known_nodes = sorted(list(combined_nodes_dict.values()), key=lambda x: x.get('name', '').lower())

        if self.stop_event.is_set(): return

        # --- Apply Filtering Logic ---
        filtered_nodes = []
        if search_term_value == "": # Empty search -> show local only
            filtered_nodes = sorted(self.local_nodes_only, key=lambda x: x.get('name', '').lower())
        else: # Search term present -> filter combined list
            filtered_nodes = [
                node for node in self.all_known_nodes
                if search_term_value in node.get('name', '').lower() or \
                   search_term_value in node.get('repo_url', '').lower()
            ]
            filtered_nodes.sort(key=lambda x: x.get('name', '').lower())

        # --- Populate Treeview ---
        if not filtered_nodes:
              display_message = "未找到匹配的节点" if search_term_value else "未找到本地节点"
              self.root.after(0, lambda msg=display_message: self.nodes_tree.insert("", tk.END, values=("", msg, "", "", "")))
        else:
            for node_data in filtered_nodes:
                 if self.stop_event.is_set(): break
                 tags = ('installed',) if node_data.get('status') == '已安装' else ('not_installed',)
                 self.root.after(0, lambda v=(
                      node_data.get("name", "N/A"),
                      node_data.get("status", "未知"),
                      node_data.get("local_id", "N/A"), # Display short ID
                      node_data.get("repo_info", "N/A"),
                      node_data.get("repo_url", "N/A")
                 ), t=tags: self.nodes_tree.insert("", tk.END, values=v, tags=t))

        self.log_to_gui("Update", f"节点列表刷新完成。已显示 {len(filtered_nodes)} 个节点。", "info")


    def _fetch_online_node_config(self):
         """Fetches and parses the online custom node list config."""
         node_config_url = self.node_config_url_var.get()
         if not node_config_url: return []

         self.log_to_gui("Update", f"尝试从 {node_config_url} 获取节点配置...", "info")
         try:
              response = requests.get(node_config_url, timeout=20) # Increased timeout
              response.raise_for_status()
              config_data = response.json()

              if isinstance(config_data, list) and all(isinstance(item, dict) for item in config_data):
                   self.log_to_gui("Update", f"已获取在线节点配置 (共 {len(config_data)} 条)。", "info")
                   return config_data
              elif isinstance(config_data, dict) and 'custom_nodes' in config_data and isinstance(config_data['custom_nodes'], list):
                   self.log_to_gui("Update", f"已获取在线节点配置 (Manager格式，共 {len(config_data['custom_nodes'])} 条)。", "info")
                   return config_data['custom_nodes']
              else:
                   self.log_to_gui("Update", f"在线节点配置格式无法识别。", "error")
                   return []

         except requests.exceptions.Timeout:
              self.log_to_gui("Update", f"获取在线节点配置超时: {node_config_url}", "error")
              return []
         except requests.exceptions.RequestException as e:
              self.log_to_gui("Update", f"获取在线节点配置失败: {e}", "error")
              return []
         except json.JSONDecodeError as e:
              self.log_to_gui("Update", f"在线节点配置解析失败 (非JSON): {e}", "error")
              return []
         except Exception as e:
              self.log_to_gui("Update", f"处理在线节点配置时发生意外错误: {e}", "error")
              return []


    def _update_all_nodes_task(self, nodes_to_process):
        """Task to iterate and update all specified installed nodes. Runs in worker thread."""
        if self.stop_event.is_set(): return
        self.log_to_gui("Update", f"开始更新全部节点 ({len(nodes_to_process)} 个)...", "info")
        updated_count = 0
        failed_nodes = []

        for index, node_info in enumerate(nodes_to_process):
             if self.stop_event.is_set(): break

             node_name = node_info.get("name", "未知节点")
             node_install_path = os.path.normpath(os.path.join(self.comfyui_nodes_dir, node_name))
             repo_url = node_info.get("repo_url")
             remote_branch = node_info.get("remote_branch") # Branch name from refresh scan

             self.log_to_gui("Update", f"[{index+1}/{len(nodes_to_process)}] 正在处理节点 '{node_name}'...", "info")

             if not os.path.isdir(node_install_path) or not os.path.exists(os.path.join(node_install_path, ".git")):
                  self.log_to_gui("Update", f"跳过 '{node_name}': 非 Git 仓库或目录无效。", "warn")
                  failed_nodes.append(f"{node_name} (非Git仓库)")
                  continue
             if not remote_branch:
                 self.log_to_gui("Update", f"跳过 '{node_name}': 未能确定远程跟踪分支。", "warn")
                 failed_nodes.append(f"{node_name} (无跟踪分支)")
                 continue
             if not repo_url or repo_url in ("本地安装，无Git信息", "无法获取远程 URL", "本地安装", "N/A", "无远程仓库"):
                 self.log_to_gui("Update", f"跳过 '{node_name}': 缺少有效的远程 URL。", "warn")
                 failed_nodes.append(f"{node_name} (无远程URL)")
                 continue

             try:
                 stdout_get_url, _, rc_get_url = self._run_git_command(["remote", "get-url", "origin"], cwd=node_install_path, timeout=10)
                 current_url = stdout_get_url.strip() if rc_get_url == 0 else None
                 if not current_url or current_url != repo_url:
                      action = "set-url" if current_url else "add"
                      self.log_to_gui("Update", f"节点 '{node_name}': 远程 URL 不匹配/缺失，尝试 git remote {action} origin...", "warn")
                      _, stderr_set, rc_set = self._run_git_command(["remote", action, "origin", repo_url], cwd=node_install_path, timeout=15)
                      if rc_set != 0: self.log_to_gui("Update", f"节点 '{node_name}': 设置/添加远程 URL 失败: {stderr_set.strip()}", "warn")
                      else: self.log_to_gui("Update", f"节点 '{node_name}': 远程 URL 已更新。", "info")

                 if self.stop_event.is_set(): raise threading.ThreadExit

                 stdout_status, _, _ = self._run_git_command(["status", "--porcelain"], cwd=node_install_path, timeout=10)
                 if stdout_status.strip():
                      self.log_to_gui("Update", f"跳过 '{node_name}': 存在本地修改。", "warn")
                      failed_nodes.append(f"{node_name} (存在本地修改)")
                      continue

                 self.log_to_gui("Update", f"[{index+1}/{len(nodes_to_process)}] 执行 Git fetch origin {remote_branch}...", "info")
                 _, stderr_fetch, rc_fetch = self._run_git_command(["fetch", "origin", remote_branch], cwd=node_install_path, timeout=60)
                 if rc_fetch != 0:
                      self.log_to_gui("Update", f"Git fetch 失败 for '{node_name}': {stderr_fetch.strip()}", "error")
                      failed_nodes.append(f"{node_name} (Fetch失败)")
                      continue

                 if self.stop_event.is_set(): raise threading.ThreadExit

                 local_commit, _, _ = self._run_git_command(["rev-parse", "HEAD"], cwd=node_install_path, timeout=5, log_output=False)
                 remote_commit, _, _ = self._run_git_command(["rev-parse", f"origin/{remote_branch}"], cwd=node_install_path, timeout=5, log_output=False)

                 if local_commit and remote_commit and local_commit.strip() == remote_commit.strip():
                     self.log_to_gui("Update", f"节点 '{node_name}' 已是最新版本。", "info")
                     continue

                 self.log_to_gui("Update", f"[{index+1}/{len(nodes_to_process)}] 执行 Git reset --hard origin/{remote_branch} for '{node_name}'...", "info")
                 _, stderr_reset, returncode_reset = self._run_git_command(["reset", "--hard", f"origin/{remote_branch}"], cwd=node_install_path, timeout=60)
                 if returncode_reset != 0:
                       self.log_to_gui("Update", f"Git reset --hard 失败 for '{node_name}': {stderr_reset.strip()}", "error")
                       failed_nodes.append(f"{node_name} (Reset失败)")
                       continue

                 self.log_to_gui("Update", f"Git reset 完成 for '{node_name}'.", "info")

                 if self.stop_event.is_set(): raise threading.ThreadExit

                 if os.path.exists(os.path.join(node_install_path, ".gitmodules")):
                      self.log_to_gui("Update", f"执行 Git submodule update for '{node_name}'...", "info")
                      _, stderr_sub, rc_sub = self._run_git_command(["submodule", "update", "--init", "--recursive", "--force"], cwd=node_install_path, timeout=180)
                      if rc_sub != 0: self.log_to_gui("Update", f"Git submodule update 失败 for '{node_name}': {stderr_sub.strip()}", "warn")
                 python_exe = self.python_exe_var.get()
                 requirements_path = os.path.join(node_install_path, "requirements.txt")
                 if python_exe and os.path.isfile(python_exe) and os.path.isfile(requirements_path):
                      self.log_to_gui("Update", f"执行 pip 安装节点依赖 for '{node_name}'...", "info")
                      pip_cmd_base = [python_exe, "-m", "pip", "install", "-r", requirements_path, "--upgrade"]
                      pip_cmd_extras = ["--extra-index-url", "https://download.pytorch.org/whl/cu118", "--extra-index-url", "https://download.pytorch.org/whl/cu121"]
                      pip_cmd = pip_cmd_base + pip_cmd_extras
                      is_venv = sys.prefix != sys.base_prefix
                      if platform.system() != "Windows" and not is_venv: pip_cmd.append("--user")

                      _, stderr_pip, rc_pip = self._run_git_command(pip_cmd, cwd=node_install_path, timeout=180)
                      if rc_pip != 0:
                           self.log_to_gui("Update", f"Pip 安装节点依赖失败 for '{node_name}': {stderr_pip.strip()}", "error")
                           failed_nodes.append(f"{node_name} (依赖安装失败)")
                      else:
                           self.log_to_gui("Update", f"Pip 安装节点依赖完成 for '{node_name}'.", "info")

                 updated_count += 1
                 self.log_to_gui("Update", f"节点 '{node_name}' 更新成功。", "info")

             except threading.ThreadExit:
                 self.log_to_gui("Update", f"更新节点 '{node_name}' 时收到停止信号。", "warn")
                 failed_nodes.append(f"{node_name} (已取消)")
                 break
             except Exception as e:
                 self.log_to_gui(f"Update", f"更新节点 '{node_name}' 时发生意外错误: {e}", "error")
                 failed_nodes.append(f"{node_name} (发生错误)")

        # --- Update All Task Summary ---
        self.log_to_gui("Update", f"更新全部节点流程完成。", "info")
        final_message = f"全部节点更新流程完成。\n成功更新: {updated_count} 个。"
        if failed_nodes:
             final_message += f"\n\n失败/跳过节点 ({len(failed_nodes)} 个):\n- " + "\n- ".join(failed_nodes)
             self.root.after(0, lambda msg=final_message: messagebox.showwarning("更新全部完成 (有失败/跳过)", msg, parent=self.root))
        else:
             self.root.after(0, lambda msg=final_message: messagebox.showinfo("更新全部完成", msg, parent=self.root))

        self.root.after(0, self._queue_node_list_refresh)


    def _node_uninstall_task(self, node_name, node_install_path):
         """Task to uninstall a node by deleting its directory. Runs in worker thread."""
         if self.stop_event.is_set(): return
         self.log_to_gui("Update", f"正在卸载节点 '{node_name}' (删除目录: {node_install_path})...", "info")

         try:
              if not os.path.isdir(node_install_path):
                   self.log_to_gui("Update", f"节点目录 '{node_install_path}' 不存在，无需卸载。", "warn")
                   self.root.after(0, lambda name=node_name: messagebox.showwarning("卸载失败", f"节点目录 '{name}' 不存在。", parent=self.root))
                   return

              if self.stop_event.is_set(): raise threading.ThreadExit

              shutil.rmtree(node_install_path)
              self.log_to_gui("Update", f"节点目录 '{node_install_path}' 已删除。", "info")
              self.log_to_gui("Update", f"节点 '{node_name}' 卸载流程完成。", "info")
              self.root.after(0, lambda name=node_name: messagebox.showinfo("卸载完成", f"节点 '{name}' 已成功卸载。", parent=self.root))

         except threading.ThreadExit:
              self.log_to_gui("Update", f"节点 '{node_name}' 卸载任务已取消。", "warn")
         except Exception as e:
             error_msg = f"节点 '{node_name}' 卸载失败: {e}"
             self.log_to_gui("Update", error_msg, "error")
             self.root.after(0, lambda msg=error_msg: messagebox.showerror("卸载失败", msg, parent=self.root))
         finally:
             self.root.after(0, self._queue_node_list_refresh)


    def _install_node_task(self, node_name, node_install_path, repo_url, target_ref):
        """Task to execute git commands for INSTALLING a node (cloning). Runs in worker thread."""
        if self.stop_event.is_set(): return
        self.log_to_gui("Update", f"开始安装节点 '{node_name}'...", "info")
        self.log_to_gui("Update", f"  仓库: {repo_url}", "info")
        self.log_to_gui("Update", f"  目标引用: {target_ref}", "info")
        self.log_to_gui("Update", f"  目标目录: {node_install_path}", "info")

        try:
            comfyui_nodes_dir = self.comfyui_nodes_dir
            if not os.path.exists(comfyui_nodes_dir):
                 self.log_to_gui("Update", f"创建 custom_nodes 目录: {comfyui_nodes_dir}", "info")
                 os.makedirs(comfyui_nodes_dir, exist_ok=True)

            if os.path.exists(node_install_path):
                 if os.path.isdir(node_install_path) and len(os.listdir(node_install_path)) > 0:
                      raise Exception(f"节点安装目录已存在且不为空: {node_install_path}")
                 elif not os.path.isdir(node_install_path):
                      raise Exception(f"目标路径已存在但不是目录: {node_install_path}")
                 else:
                      try: os.rmdir(node_install_path)
                      except OSError as e: raise Exception(f"无法移除已存在的空目录 {node_install_path}: {e}")

            if self.stop_event.is_set(): raise threading.ThreadExit

            self.log_to_gui("Update", f"执行 Git clone...", "info")
            clone_cmd = ["clone", "--progress"]
            is_likely_commit_hash = len(target_ref) >= 7 and all(c in '0123456789abcdefABCDEF' for c in target_ref)
            if target_ref and target_ref != 'main' and target_ref != 'master' and not is_likely_commit_hash:
                 clone_cmd.extend(["--branch", target_ref])
            clone_cmd.extend([repo_url, node_install_path])

            # Use _run_git_command for consistent handling and logging
            stdout_clone, stderr_clone, returncode = self._run_git_command(clone_cmd, cwd=comfyui_nodes_dir, timeout=300, log_output=True) # Log output here

            # process = subprocess.Popen(
            #     [self.git_exe_path_var.get()] + clone_cmd, cwd=comfyui_nodes_dir,
            #     stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace',
            #     startupinfo=None, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0, env=os.environ.copy()
            # )
            # # Stream stderr for progress
            # stderr_thread = threading.Thread(target=self.stream_output, args=(process.stderr, "[Git stderr]"), daemon=True)
            # stderr_thread.start()
            # stdout_full, _ = process.communicate(timeout=300) # Capture stdout at the end
            # stderr_thread.join(timeout=5) # Wait briefly for stderr thread
            # returncode = process.returncode
            # if stdout_full: self.log_to_gui("Git", stdout_full, "stdout") # Log captured stdout


            if returncode != 0:
                 if os.path.exists(node_install_path):
                      try: shutil.rmtree(node_install_path); self.log_to_gui("Update", f"已移除失败的节点目录: {node_install_path}", "info")
                      except Exception as rm_err: self.log_to_gui("Update", f"移除失败的节点目录 '{node_install_path}' 失败: {rm_err}", "error")
                 # Error already logged by _run_git_command if log_output=True
                 raise Exception(f"Git clone 失败 (退出码 {returncode})")

            self.log_to_gui("Update", "Git clone 完成。", "info")

            if is_likely_commit_hash:
                 self.log_to_gui("Update", f"执行 Git checkout {target_ref}...", "info")
                 _, stderr_checkout, rc_checkout = self._run_git_command(["checkout", target_ref], cwd=node_install_path, timeout=60)
                 if rc_checkout != 0: raise Exception(f"Git checkout 失败: {stderr_checkout.strip()}")

            if self.stop_event.is_set(): raise threading.ThreadExit

            if os.path.exists(os.path.join(node_install_path, ".gitmodules")):
                 self.log_to_gui("Update", f"执行 Git submodule update for '{node_name}'...", "info")
                 _, stderr_sub, rc_sub = self._run_git_command(["submodule", "update", "--init", "--recursive", "--force"], cwd=node_install_path, timeout=180)
                 if rc_sub != 0: self.log_to_gui("Update", f"Git submodule update 失败: {stderr_sub.strip()}", "warn")

            if self.stop_event.is_set(): raise threading.ThreadExit

            python_exe = self.python_exe_var.get()
            requirements_path = os.path.join(node_install_path, "requirements.txt")
            if python_exe and os.path.isfile(python_exe) and os.path.isfile(requirements_path):
                 self.log_to_gui("Update", f"执行 pip 安装节点依赖 for '{node_name}'...", "info")
                 pip_cmd_base = [python_exe, "-m", "pip", "install", "-r", requirements_path, "--upgrade"]
                 pip_cmd_extras = ["--extra-index-url", "https://download.pytorch.org/whl/cu118", "--extra-index-url", "https://download.pytorch.org/whl/cu121"]
                 pip_cmd = pip_cmd_base + pip_cmd_extras
                 is_venv = sys.prefix != sys.base_prefix
                 if platform.system() != "Windows" and not is_venv: pip_cmd.append("--user")
                 _, stderr_pip, rc_pip = self._run_git_command(pip_cmd, cwd=node_install_path, timeout=180)
                 if rc_pip != 0:
                      self.log_to_gui("Update", f"Pip 安装节点依赖失败: {stderr_pip.strip()}", "error")
                      self.root.after(0, lambda name=node_name: messagebox.showwarning("依赖安装失败", f"节点 '{name}' 的 Python 依赖安装失败。", parent=self.root))
                 else:
                      self.log_to_gui("Update", f"Pip 安装节点依赖完成 for '{node_name}'.", "info")

            self.log_to_gui("Update", f"节点 '{node_name}' 安装流程完成。", "info")
            self.root.after(0, lambda name=node_name: messagebox.showinfo("安装完成", f"节点 '{name}' 已成功安装。", parent=self.root))

        except threading.ThreadExit:
             self.log_to_gui("Update", f"节点 '{node_name}' 安装任务已取消。", "warn")
        except Exception as e:
            error_msg = f"节点 '{node_name}' 安装失败: {e}"
            self.log_to_gui("Update", error_msg, "error")
            self.root.after(0, lambda msg=error_msg: messagebox.showerror("安装失败", msg, parent=self.root))
        finally:
            self.root.after(0, self._queue_node_list_refresh)


    # MOD3: Fetch node history, including current local commit
    def _node_history_fetch_task(self, node_name, node_install_path):
         """Task to fetch git history and current commit for a node. Runs in worker thread."""
         if self.stop_event.is_set(): return
         self.log_to_gui("Update", f"正在获取节点 '{node_name}' 的版本历史...", "info")

         history_data = []
         current_local_commit = None # MOD3: Variable to store current commit
         try:
             if not os.path.isdir(node_install_path) or not os.path.exists(os.path.join(node_install_path, ".git")):
                  raise Exception(f"节点目录不是有效的 Git 仓库: {node_install_path}")

             # Get current local commit ID (full)
             local_commit_stdout, _, rc_local = self._run_git_command(["rev-parse", "HEAD"], cwd=node_install_path, timeout=5, log_output=False)
             if rc_local == 0 and local_commit_stdout:
                 current_local_commit = local_commit_stdout.strip()
                 self.log_to_gui("Update", f"当前本地 Commit ID: {current_local_commit[:8]}", "info")
             else:
                 self.log_to_gui("Update", f"无法获取节点 '{node_name}' 的当前 Commit ID。", "warn")


             found_node_info = next((node for node in self.local_nodes_only if node.get("name") == node_name), None)
             repo_url = found_node_info.get("repo_url") if found_node_info else None
             if repo_url and repo_url not in ("本地安装，无Git信息", "无法获取远程 URL", "本地安装", "N/A", "无远程仓库"):
                 stdout_url, _, rc_url = self._run_git_command(["remote", "get-url", "origin"], cwd=node_install_path, timeout=10, log_output=False)
                 current_origin_url = stdout_url.strip() if rc_url == 0 else ""
                 if not current_origin_url or current_origin_url != repo_url:
                     action = "set-url" if current_origin_url else "add"
                     self.log_to_gui("Update", f"节点 '{node_name}': 远程 URL 不匹配/缺失，尝试 git remote {action} origin...", "warn")
                     _, stderr_set, rc_set = self._run_git_command(["remote", action, "origin", repo_url], cwd=node_install_path, timeout=10)
                     if rc_set != 0: self.log_to_gui("Update", f"节点 '{node_name}': 设置/添加远程 URL 失败: {stderr_set.strip()}", "warn") # Warn only
             elif not repo_url:
                 self.log_to_gui("Update", f"节点 '{node_name}': 无法从缓存或 Git 获取有效远程 URL，历史列表可能不完整。", "warn")


             if self.stop_event.is_set(): raise threading.ThreadExit

             # Fetch latest info
             self.log_to_gui("Update", f"执行 Git fetch origin for '{node_name}'...", "info")
             _, stderr_fetch, rc_fetch = self._run_git_command(["fetch", "origin", "--prune", "--tags", "-f"], cwd=node_install_path, timeout=60)
             if rc_fetch != 0:
                  self.log_to_gui("Update", f"Git fetch 失败 for '{node_name}': {stderr_fetch.strip()}", "error")
                  self.log_to_gui("Update", "无法从远程获取最新历史，列表可能不完整。", "warn")

             if self.stop_event.is_set(): return

             # Get branches (remote) - Use %(committerdate:iso-strict) for consistency
             branches_output, _, _ = self._run_git_command(
                  ["for-each-ref", "refs/remotes/origin/", "--sort=-committerdate", "--format=%(refname:short) %(objectname) %(committerdate:iso-strict)"],
                  cwd=node_install_path, timeout=30 )
             for line in branches_output.splitlines():
                  parts = line.split(' ', 2)
                  if len(parts) == 3:
                      refname, commit_id, date_iso = parts[0].replace("origin/", ""), parts[1], parts[2]
                      if "HEAD->" not in refname:
                           history_data.append({"type": "branch", "name": refname, "commit_id": commit_id, "date_iso": date_iso})

             if self.stop_event.is_set(): return

             # Get tags - Use %(taggerdate:iso-strict) for consistency
             tags_output, _, _ = self._run_git_command(
                  ["for-each-ref", "refs/tags/", "--sort=-taggerdate", "--format=%(refname:short) %(objectname) %(taggerdate:iso-strict)"],
                  cwd=node_install_path, timeout=30 )
             for line in tags_output.splitlines():
                  parts = line.split(' ', 2)
                  if len(parts) == 3:
                       refname, commit_id, date_iso = parts[0].replace("refs/tags/", ""), parts[1], parts[2]
                       history_data.append({"type": "tag", "name": refname, "commit_id": commit_id, "date_iso": date_iso})

             # Add local HEAD if it wasn't already listed and we found it
             if current_local_commit:
                 is_already_listed = any(item['commit_id'] == current_local_commit for item in history_data)
                 if not is_already_listed:
                     head_date_stdout, _, rc_head_date = self._run_git_command(["log", "-1", "--format=%ci", "HEAD"], cwd=node_install_path, timeout=5, log_output=False)
                     head_date_iso = None
                     if rc_head_date == 0 and head_date_stdout:
                        # Try to format git's date output to iso-strict like
                        try:
                             head_date_dt = datetime.strptime(head_date_stdout.strip(), '%Y-%m-%d %H:%M:%S %z')
                             head_date_iso = head_date_dt.isoformat()
                        except ValueError: pass
                     if not head_date_iso: head_date_iso = datetime.now(timezone.utc).isoformat() # Fallback

                     history_data.append({"type": "commit", "name": "当前本地 HEAD", "commit_id": current_local_commit, "date_iso": head_date_iso})

             # MOD3: Sort history using custom comparison (date then version/name)
             history_data.sort(key=cmp_to_key(_compare_versions_for_sort))

             self._node_history_modal_data = history_data
             self._node_history_modal_node_name = node_name
             self._node_history_modal_path = node_install_path
             self._node_history_modal_current_commit = current_local_commit # MOD3: Store current commit

             self.log_to_gui("Update", f"节点 '{node_name}' 版本历史获取完成。", "info")
             self.root.after(0, self._show_node_history_modal) # Show modal in GUI thread

         except threading.ThreadExit:
              self.log_to_gui("Update", f"节点 '{node_name}' 历史获取任务已取消。", "warn")
              self._cleanup_modal_state()
         except Exception as e:
             error_msg = f"获取节点 '{node_name}' 版本历史失败: {e}"
             self.log_to_gui("Update", error_msg, "error")
             self._cleanup_modal_state()
             self.root.after(0, lambda msg=error_msg: messagebox.showerror("获取历史失败", msg, parent=self.root))


    # MOD3: Show Node History Modal with Improved Styling
    def _show_node_history_modal(self):
        """Creates and displays the node version history modal with status and improved styling."""
        if not self._node_history_modal_data:
            self.log_to_gui("Update", f"没有节点 '{self._node_history_modal_node_name}' 的历史版本数据可显示。", "warn")
            self._cleanup_modal_state()
            return

        node_name = self._node_history_modal_node_name
        history_data = self._node_history_modal_data
        current_commit = self._node_history_modal_current_commit

        modal_window = Toplevel(self.root)
        modal_window.title(f"版本切换 - {node_name}")
        modal_window.transient(self.root)
        modal_window.grab_set()
        # MOD3: Adjusted size for better layout
        modal_window.geometry("800x550") # Increased width
        modal_window.configure(bg=BG_COLOR)
        modal_window.rowconfigure(0, weight=1); modal_window.columnconfigure(0, weight=1)
        modal_window.protocol("WM_DELETE_WINDOW", lambda win=modal_window: self._cleanup_modal_state(win))

        # Use a single frame to hold header and canvas/scrollbar for items
        main_modal_frame = ttk.Frame(modal_window, style='Modal.TFrame', padding=10)
        main_modal_frame.grid(row=0, column=0, sticky="nsew")
        main_modal_frame.rowconfigure(1, weight=1) # Allow canvas row to expand
        main_modal_frame.columnconfigure(0, weight=1) # Allow canvas col to expand


        # --- Header Row --- MOD3: Styled and weighted columns
        header_frame = ttk.Frame(main_modal_frame, style='Modal.TFrame', padding=(0, 5, 0, 8)) # Add bottom padding
        header_frame.grid(row=0, column=0, sticky="ew")
        # Column configuration for alignment (adjust minsize/weight as needed)
        header_frame.columnconfigure(0, weight=3, minsize=200) # Version Name (more weight)
        header_frame.columnconfigure(1, weight=0, minsize=60)  # Status (fixed width)
        header_frame.columnconfigure(2, weight=1, minsize=100) # Commit ID
        header_frame.columnconfigure(3, weight=1, minsize=120) # Date
        header_frame.columnconfigure(4, weight=0, minsize=70)  # Button (fixed width)

        # Use specific style for header labels
        ttk.Label(header_frame, text="版本", style='ModalHeader.TLabel', anchor=tk.W).grid(row=0, column=0, sticky='w', padx=5)
        ttk.Label(header_frame, text="状态", style='ModalHeader.TLabel', anchor=tk.CENTER).grid(row=0, column=1, sticky='ew', padx=5)
        ttk.Label(header_frame, text="提交ID", style='ModalHeader.TLabel', anchor=tk.W).grid(row=0, column=2, sticky='w', padx=5)
        ttk.Label(header_frame, text="更新日期", style='ModalHeader.TLabel', anchor=tk.W).grid(row=0, column=3, sticky='w', padx=5)
        ttk.Label(header_frame, text="操作", style='ModalHeader.TLabel', anchor=tk.CENTER).grid(row=0, column=4, sticky='ew', padx=(5,10)) # Added right padding


        # --- Scrollable Item List ---
        canvas = tk.Canvas(main_modal_frame, bg=BG_COLOR, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(main_modal_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Modal.TFrame')

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Make the frame inside the canvas expand horizontally
        scrollable_frame.bind('<Configure>', lambda e: canvas.itemconfigure(canvas_window, width=e.width))

        canvas.grid(row=1, column=0, sticky="nsew"); scrollbar.grid(row=1, column=1, sticky="ns")

        # Configure columns of the scrollable frame to match header
        scrollable_frame.columnconfigure(0, weight=3, minsize=200); scrollable_frame.columnconfigure(1, weight=0, minsize=60)
        scrollable_frame.columnconfigure(2, weight=1, minsize=100); scrollable_frame.columnconfigure(3, weight=1, minsize=120)
        scrollable_frame.columnconfigure(4, weight=0, minsize=70)

        # Populate with history items
        row_bg1, row_bg2 = BG_COLOR, "#3a3a3a"
        self.style.configure('row0.Modal.TFrame', background=row_bg1)
        self.style.configure('row1.Modal.TFrame', background=row_bg2)

        for i, item_data in enumerate(history_data):
             bg = row_bg1 if i % 2 == 0 else row_bg2
             style_name = f'row{i%2}.Modal.TFrame'


             # Create a frame for each row within the scrollable_frame
             row_frame = ttk.Frame(scrollable_frame, style=style_name, padding=(0, 3)) # Reduced vertical padding
             row_frame.grid(row=i, column=0, sticky="ew") # Use row 'i', column 0

             # Configure columns for this specific row_frame to match header
             row_frame.columnconfigure(0, weight=3, minsize=200); row_frame.columnconfigure(1, weight=0, minsize=60)
             row_frame.columnconfigure(2, weight=1, minsize=100); row_frame.columnconfigure(3, weight=1, minsize=120)
             row_frame.columnconfigure(4, weight=0, minsize=70)

             try:
                 date_str = item_data['date_iso']
                 date_obj = _parse_iso_date_for_sort(date_str)
                 if date_obj:
                     date_display = date_obj.strftime('%Y-%m-%d')
                 else:
                     date_display = "日期解析失败" if date_str else "无日期信息"
             except: date_display = "日期错误"

             commit_id = item_data.get("commit_id", "N/A")
             version_name = item_data.get("name", "N/A")
             version_type = item_data.get("type", "未知")
             version_display = f"{version_type} / {version_name}"

             # Determine status
             status_text = ""
             status_style = "TLabel" # Default label style
             if current_commit and commit_id == current_commit:
                  status_text = "当前"
                  status_style = "Highlight.TLabel" # Use highlight style

             # MOD3: Add labels and button to row_frame with correct sticky and padding
             # Use background=bg for labels inside colored frames if style doesn't handle it
             ttk.Label(row_frame, text=version_display, anchor=tk.W, background=bg, wraplength=180).grid(row=0, column=0, sticky='w', padx=5, pady=1)
             status_label_widget = ttk.Label(row_frame, text=status_text, style=status_style, anchor=tk.CENTER, background=bg)
             status_label_widget.grid(row=0, column=1, sticky='ew', padx=5, pady=1)
             # Manually set background for Highlight.TLabel if needed, depending on theme interaction
             if status_style == "Highlight.TLabel": status_label_widget.configure(background=bg)

             ttk.Label(row_frame, text=commit_id[:8], anchor=tk.W, background=bg).grid(row=0, column=2, sticky='w', padx=5, pady=1)
             ttk.Label(row_frame, text=date_display, anchor=tk.W, background=bg).grid(row=0, column=3, sticky='w', padx=5, pady=1)

             switch_btn = ttk.Button(row_frame, text="切换", style="Modal.TButton", width=6,
                                     command=lambda c_id=commit_id, win=modal_window: self._on_modal_switch_confirm(win, c_id))
             switch_btn.grid(row=0, column=4, sticky='e', padx=(5, 10), pady=1) # Added right padding

             if status_text == "当前":
                  switch_btn.config(state=tk.DISABLED)

        # Mousewheel scrolling needs to be bound to the canvas and the frame inside
        def _on_mousewheel(event):
             scroll_amount = 0
             if platform.system() == "Windows": scroll_amount = int(-1*(event.delta/120))
             elif platform.system() == "Darwin": scroll_amount = int(-1 * event.delta)
             else: # Linux
                 if event.num == 4: scroll_amount = -1
                 elif event.num == 5: scroll_amount = 1
             canvas.yview_scroll(scroll_amount, "units")

        # Bind mousewheel to canvas and its children
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        scrollable_frame.bind_all("<MouseWheel>", _on_mousewheel)
        # Also bind to the row frames to ensure capture
        for child in scrollable_frame.winfo_children():
             if isinstance(child, ttk.Frame): # Bind to row frames
                 child.bind_all("<MouseWheel>", _on_mousewheel)
                 for grandchild in child.winfo_children(): # Bind to widgets within rows
                     grandchild.bind_all("<MouseWheel>", _on_mousewheel)


        modal_window.wait_window()


    def _cleanup_modal_state(self, modal_window=None):
         """Cleans up modal-related instance variables and destroys the window."""
         self._node_history_modal_data = []
         self._node_history_modal_node_name = ""
         self._node_history_modal_path = ""
         self._node_history_modal_current_commit = "" # MOD3: Clear current commit too
         try:
             if modal_window and modal_window.winfo_exists():
                  # Unbind mousewheel specifically from this canvas and children
                  # This might be overly broad, but safer than missing bindings
                  modal_window.unbind_all("<MouseWheel>")
                  modal_window.destroy()
         except tk.TclError: pass


    def _on_modal_switch_confirm(self, modal_window, target_commit_id):
        """Handles the confirmation and queues the switch task from the modal."""
        node_name = self._node_history_modal_node_name
        node_install_path = self._node_history_modal_path

        if not node_name or not node_install_path or not target_commit_id:
            messagebox.showerror("切换失败", "无法确定节点信息或目标版本。", parent=modal_window)
            self._cleanup_modal_state(modal_window)
            return

        if not os.path.isdir(node_install_path) or not os.path.exists(os.path.join(node_install_path, ".git")):
             messagebox.showerror("切换失败", f"节点目录 '{node_install_path}' 不是有效的 Git 仓库。", parent=modal_window)
             self._cleanup_modal_state(modal_window)
             return

        # MOD3: Skip confirmation, directly queue the task
        self.log_to_gui("Launcher", f"将节点 '{node_name}' 切换到版本 {target_commit_id[:8]} 任务添加到队列...", "info")
        self.update_task_queue.put((self._switch_node_to_ref_task, [node_name, node_install_path, target_commit_id], {}))

        self._cleanup_modal_state(modal_window) # Close modal
        self.root.after(0, self._update_ui_state)


    def _switch_node_to_ref_task(self, node_name, node_install_path, target_ref):
         """Task to switch an installed node to a specific git reference. Runs in worker thread."""
         if self.stop_event.is_set(): return
         self.log_to_gui("Update", f"正在将节点 '{node_name}' 切换到版本 (引用: {target_ref[:8]})...", "info")

         try:
             if not os.path.isdir(node_install_path) or not os.path.exists(os.path.join(node_install_path, ".git")):
                  raise Exception(f"节点目录不是有效的 Git 仓库: {node_install_path}")

             stdout_status, _, _ = self._run_git_command(["status", "--porcelain"], cwd=node_install_path, timeout=10)
             if stdout_status.strip():
                  self.log_to_gui("Update", f"节点 '{node_name}' 存在未提交的本地修改，将通过 checkout --force 覆盖。", "warn")

             if self.stop_event.is_set(): raise threading.ThreadExit

             self.log_to_gui("Update", f"执行 Git checkout --force {target_ref[:8]}...", "info")
             _, stderr_checkout, rc_checkout = self._run_git_command(["checkout", "--force", target_ref], cwd=node_install_path, timeout=60)
             if rc_checkout != 0: raise Exception(f"Git checkout 失败: {stderr_checkout.strip()}")

             if self.stop_event.is_set(): raise threading.ThreadExit

             if os.path.exists(os.path.join(node_install_path, ".gitmodules")):
                 self.log_to_gui("Update", f"执行 Git submodule update...", "info")
                 _, stderr_sub, rc_sub = self._run_git_command(["submodule", "update", "--init", "--recursive", "--force"], cwd=node_install_path, timeout=180)
                 if rc_sub != 0: self.log_to_gui("Update", f"Git submodule update 失败: {stderr_sub.strip()}", "warn") # Warn only

             if self.stop_event.is_set(): raise threading.ThreadExit

             python_exe = self.python_exe_var.get()
             requirements_path = os.path.join(node_install_path, "requirements.txt")
             if python_exe and os.path.isfile(python_exe) and os.path.isfile(requirements_path):
                  self.log_to_gui("Update", f"执行 pip 安装节点依赖...", "info")
                  pip_cmd_base = [python_exe, "-m", "pip", "install", "-r", requirements_path, "--upgrade"]
                  pip_cmd_extras = ["--extra-index-url", "https://download.pytorch.org/whl/cu118", "--extra-index-url", "https://download.pytorch.org/whl/cu121"]
                  pip_cmd = pip_cmd_base + pip_cmd_extras
                  is_venv = sys.prefix != sys.base_prefix
                  if platform.system() != "Windows" and not is_venv: pip_cmd.append("--user")
                  _, stderr_pip, rc_pip = self._run_git_command(pip_cmd, cwd=node_install_path, timeout=180)
                  if rc_pip != 0:
                       self.log_to_gui("Update", f"Pip 安装节点依赖失败: {stderr_pip.strip()}", "error")
                       self.root.after(0, lambda name=node_name: messagebox.showwarning("依赖安装失败", f"节点 '{name}' 的 Python 依赖可能安装失败。", parent=self.root))
                  else:
                       self.log_to_gui("Update", f"Pip 安装节点依赖完成。", "info")

             self.log_to_gui("Update", f"节点 '{node_name}' 已成功切换到版本 (引用: {target_ref[:8]})。", "info")
             self.root.after(0, lambda name=node_name, ref=target_ref[:8]: messagebox.showinfo("切换完成", f"节点 '{name}' 已成功切换到版本: {ref}", parent=self.root))

         except threading.ThreadExit:
              self.log_to_gui("Update", f"节点 '{node_name}' 切换版本任务已取消。", "warn")
         except Exception as e:
             error_msg = f"节点 '{node_name}' 切换版本失败: {e}"
             self.log_to_gui("Update", error_msg, "error")
             self.root.after(0, lambda msg=error_msg: messagebox.showerror("切换失败", msg, parent=self.root))
         finally:
             self.root.after(0, self._queue_node_list_refresh)


    # --- Error Analysis Methods (MOD4: Real API Call Implementation) ---

    def run_diagnosis(self):
        """Captures logs, combines them, and sends them to the configured API for analysis."""
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中...", "warn"); return

        api_endpoint = self.error_api_endpoint_var.get().strip()
        api_key = self.error_api_key_var.get().strip()

        launcher_logs, comfyui_logs = "", ""
        try:
            if hasattr(self, 'launcher_log_text') and self.launcher_log_text.winfo_exists():
                 launcher_logs = self.launcher_log_text.get("1.0", tk.END).strip()
            if hasattr(self, 'main_output_text') and self.main_output_text.winfo_exists():
                 comfyui_logs = self.main_output_text.get("1.0", tk.END).strip()
        except tk.TclError as e:
             self.log_to_gui("ErrorAnalysis", f"读取日志时出错: {e}", "error")
             return

        if not api_endpoint:
             messagebox.showwarning("配置缺失", "请在“API 接口”中配置诊断 API 地址。", parent=self.root)
             return
        # Allow diagnosis even if logs are empty, API might handle it
        # if not launcher_logs and not comfyui_logs:
        #      messagebox.showwarning("日志为空", "未能获取任何日志进行分析。", parent=self.root)
        #      return

        # MOD4: Format payload specifically for Gemini API structure
        formatted_log_payload = f"""@@@@@@@@@设定：
你是一位严谨且高效的AI代码工程师和网页设计师，专注于为用户提供精确、可执行的前端及后端代码方案，并精通 ComfyUI 的集成。你的回复始终优先使用中文。@@ComfyUI 集成: 精通 ComfyUI 的 API (/prompt, /upload/image, /ws 等) 调用及数据格式，能够设计和实现前端与 ComfyUI 工作流的对接方案（例如参数注入、结果获取），当ComfyUI 运行出错后可以提供解决方案。

以下为我的运行日志：
@@@@@@@@@ComLauncher后台日志
{launcher_logs if launcher_logs else "（无）"}

@@@@@@@@@ComfyUI日志
{comfyui_logs if comfyui_logs else "（无）"}
"""
        # Gemini API payload structure
        gemini_payload = {
             "contents": [{
                 "parts": [{"text": formatted_log_payload}]
             }]
             # Optional: Add generationConfig here if needed
             # "generationConfig": { ... }
        }


        self.log_to_gui("ErrorAnalysis", f"准备发送日志到诊断 API: {api_endpoint}...", "info")
        try: # Clear previous analysis output
            self.error_analysis_text.config(state=tk.NORMAL)
            self.error_analysis_text.delete('1.0', tk.END)
            self.error_analysis_text.config(state=tk.DISABLED)
        except tk.TclError: pass

        self._update_ui_state() # Disable buttons

        # Queue the diagnosis task, passing the structured payload
        self.update_task_queue.put((self._run_diagnosis_task, [api_endpoint, api_key, gemini_payload], {}))


    # MOD4: Real API Diagnosis Task with Gemini Fix
    def _run_diagnosis_task(self, api_endpoint, api_key, gemini_payload):
        """Task to send logs to the configured API (Gemini) and display the analysis. Runs in worker thread."""
        if self.stop_event.is_set():
             return
        self.log_to_gui("ErrorAnalysis", f"--- 开始诊断 ---", "info")
        self.log_to_gui("ErrorAnalysis", f"API 端点 (原始): {api_endpoint}", "info")

        analysis_result = "未能获取分析结果。" # Default result

        # --- MOD4: Gemini API Endpoint and Key Handling ---
        # Ensure endpoint includes the action (:generateContent)
        if not api_endpoint.endswith((":generateContent", ":streamGenerateContent")):
            # Extract base model path if possible, or append default action
            if "/models/" in api_endpoint:
                base_model_path = api_endpoint
                # Remove trailing slash if present before adding action
                if base_model_path.endswith('/'):
                    base_model_path = base_model_path[:-1]
                # Check if model name looks valid before appending action
                model_part = base_model_path.split('/models/')[-1]
                if model_part and not ':' in model_part: # Avoid double action
                     api_endpoint_corrected = f"{base_model_path}:generateContent"
                     self.log_to_gui("ErrorAnalysis", f"修正 API 端点为: {api_endpoint_corrected}", "warn")
                else:
                    api_endpoint_corrected = api_endpoint # Use as is if format seems complex/correct
                    self.log_to_gui("ErrorAnalysis", f"API 端点格式可能已包含操作，按原样使用: {api_endpoint_corrected}", "info")
            else:
                 # Cannot reliably determine model path, append default action cautiously
                 api_endpoint_corrected = f"{api_endpoint}:generateContent"
                 self.log_to_gui("ErrorAnalysis", f"无法识别端点格式，尝试附加 ':generateContent': {api_endpoint_corrected}", "warn")
        else:
             api_endpoint_corrected = api_endpoint # Endpoint already includes action

        # Prepare parameters (API key)
        params = {}
        if api_key:
            params['key'] = api_key
        else:
            self.log_to_gui("ErrorAnalysis", "API 密钥未配置。", "warn")
            analysis_result = "错误：API 密钥未配置，无法进行诊断。"
            # Display result and finish early
            self.log_to_gui("ErrorAnalysis", analysis_result, "error")
            self.log_to_gui("ErrorAnalysis", f"--- 诊断结束 (配置错误) ---", "info")
            self.root.after(0, self._update_ui_state) # Re-enable buttons
            return # Stop the task here


        try:
            # Construct headers (Gemini uses standard Content-Type)
            headers = {
                "Content-Type": "application/json",
            }

            # Payload is passed in as `gemini_payload`

            self.log_to_gui("ErrorAnalysis", f"发送 POST 请求到: {api_endpoint_corrected}", "info")

            response = requests.post(api_endpoint_corrected, headers=headers, params=params, json=gemini_payload, timeout=120)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            # Parse the Gemini response
            response_data = response.json()
            try:
                 # Navigate the typical Gemini response structure
                 candidates = response_data.get('candidates', [])
                 if candidates:
                     content = candidates[0].get('content', {})
                     parts = content.get('parts', [])
                     if parts:
                         analysis_result = parts[0].get('text', "API 响应中未找到文本内容。")
                     else:
                         analysis_result = "API 响应 'parts' 为空或缺失。"
                 else:
                     # Check for safety ratings / blocks
                     prompt_feedback = response_data.get('promptFeedback', {})
                     block_reason = prompt_feedback.get('blockReason')
                     if block_reason:
                          analysis_result = f"API 请求被阻止: {block_reason}\n详情: {prompt_feedback.get('safetyRatings', 'N/A')}"
                     else:
                          analysis_result = "API 响应 'candidates' 为空或缺失。"

            except (KeyError, IndexError, TypeError) as e:
                 print(f"[Launcher ERROR] Could not parse Gemini API response structure: {e}")
                 analysis_result = f"API 响应解析失败。\n原始响应: {json.dumps(response_data, indent=2, ensure_ascii=False)}"

            self.log_to_gui("ErrorAnalysis", "成功获取 API 分析结果。", "info")

        except requests.exceptions.Timeout:
             error_msg = "API 请求超时。"
             self.log_to_gui("ErrorAnalysis", error_msg, "error")
             analysis_result = error_msg
        except requests.exceptions.HTTPError as e:
             # MOD4: Provide clearer error message for common HTTP errors
             status_code = e.response.status_code
             error_details = "N/A"
             try:
                 # Try to parse JSON error details from Gemini
                 error_json = e.response.json()
                 error_details = error_json.get("error", {}).get("message", e.response.text[:500])
             except json.JSONDecodeError:
                 error_details = e.response.text[:500] # Limit details length if not JSON

             if status_code == 404:
                 error_msg = f"[ErrorAnalysis]API 请求错误 404 (Not Found): 无法找到指定的 API 端点或模型。\n请确认 API 接口地址 ({api_endpoint_corrected}) 和模型名称是否正确。\n详情: {error_details}"
             elif status_code == 400:
                 error_msg = f"[ErrorAnalysis]API 请求错误 400 (Bad Request): 请求格式错误或 API 密钥无效/缺失。\n请检查 API 密钥及请求内容。\n详情: {error_details}"
             elif status_code == 403:
                  error_msg = f"[ErrorAnalysis]API 请求错误 403 (Forbidden): 权限不足或 API 密钥无效。\n请检查 API 密钥权限。\n详情: {error_details}"
             elif status_code == 429:
                  error_msg = f"[ErrorAnalysis]API 请求错误 429 (Too Many Requests): 超出配额限制。\n请稍后再试或检查您的 API 配额。\n详情: {error_details}"
             else:
                 error_msg = f"[ErrorAnalysis]API 请求失败 (HTTP {status_code})。\n详情: {error_details}"

             print(f"[Launcher ERROR] {error_msg}")
             self.log_to_gui("ErrorAnalysis", f"API 请求失败 (HTTP {status_code})", "error") # Log summary error
             analysis_result = error_msg # Use the detailed error message for display
        except requests.exceptions.RequestException as e:
             error_msg = f"[ErrorAnalysis]API 请求错误: 网络或连接问题。\n请检查网络连接和 API 端点 ({api_endpoint_corrected})。\n详情: {e}"
             print(f"[Launcher ERROR] {error_msg}")
             self.log_to_gui("ErrorAnalysis", error_msg, "error")
             analysis_result = error_msg # Display detailed message
        except json.JSONDecodeError as e:
             error_msg = f"[ErrorAnalysis]API 响应错误: 无法解析响应 (非有效 JSON)。\n来自: {api_endpoint_corrected}\n错误: {e}"
             response_text_preview = response.text[:500] if 'response' in locals() else "N/A"
             print(f"[Launcher ERROR] {error_msg}. Response Preview: {response_text_preview}") # Log part of the invalid response
             self.log_to_gui("ErrorAnalysis", error_msg, "error")
             analysis_result = error_msg
        except Exception as e:
            error_msg = f"[ErrorAnalysis]API 请求错误: 发生意外错误。\n详情: {e}"
            print(f"[Launcher ERROR] {error_msg}", exc_info=True)
            self.log_to_gui("ErrorAnalysis", error_msg, "error")
            analysis_result = error_msg # Display detailed message
        finally:
             # Display the final result (could be success or error message)
             self.log_to_gui("ErrorAnalysis", analysis_result, "api_output")
             self.log_to_gui("ErrorAnalysis", f"--- 诊断结束 ---", "info")
             self.root.after(0, self._update_ui_state) # Re-enable buttons


    def run_fix(self):
        """(Simulates) executing commands from the error analysis output."""
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中...", "warn"); return

        analysis_output = ""
        try:
            if hasattr(self, 'error_analysis_text') and self.error_analysis_text.winfo_exists():
                 analysis_output = self.error_analysis_text.get("1.0", tk.END).strip()
        except tk.TclError: pass

        if not analysis_output:
             messagebox.showwarning("无输出", "错误分析输出为空，无法执行修复。", parent=self.root)
             return

        # REQ: Extract commands for simulation
        lines = analysis_output.splitlines()
        commands_to_simulate = []
        capture_commands = False
        for line in lines:
            line_clean = line.strip()
            # Look for a specific header indicating commands
            if "建议执行的修复操作" in line_clean or "建议执行的命令" in line_clean or "```bash" in line_clean: # Added ```bash marker
                 capture_commands = True
                 continue
            if "```" in line_clean and capture_commands: # End marker
                 capture_commands = False
                 continue

            if capture_commands:
                 # Skip empty lines or lines clearly not commands
                 if not line_clean: continue
                 # Basic check for command-like structure (e.g., starts with git, pip, cd)
                 # Also handle placeholders like {git_exe}
                 potential_cmd = line_clean.lstrip('#').lstrip('$').strip() # Remove leading # or $ if present
                 if potential_cmd and any(potential_cmd.lower().startswith(cmd) for cmd in ["cd ", "git ", "pip ", "{git_exe}", "{python_exe}", "rm ", "mv ", "mkdir "]):
                      commands_to_simulate.append(potential_cmd) # Store the potential command line

        if not commands_to_simulate:
             self.log_to_gui("ErrorAnalysis", "在诊断输出中未检测到建议的修复命令。", "warn")
             messagebox.showinfo("无修复命令", "在诊断输出中未找到建议执行的修复命令。", parent=self.root)
             return

        confirm_msg = f"检测到以下 {len(commands_to_simulate)} 条建议修复命令：\n\n" + "\n".join(f"- {cmd}" for cmd in commands_to_simulate) + "\n\n将模拟执行这些命令并在下方显示过程。\n注意：这不会实际修改您的文件系统。\n\n是否开始模拟修复？"
        confirm = messagebox.askyesno("确认模拟修复", confirm_msg, parent=self.root)
        if not confirm: return

        # Clear analysis text before showing simulation? Or append? Let's append.
        self.log_to_gui("ErrorAnalysis", "\n--- 开始模拟修复流程 ---", "info")
        self._update_ui_state() # Disable buttons

        # Queue the simulation task
        self.update_task_queue.put((self._run_fix_simulation_task, [commands_to_simulate], {}))


    def _run_fix_simulation_task(self, commands_to_simulate):
        """Task to simulate executing a list of commands. Runs in worker thread."""
        if self.stop_event.is_set(): return
        self.log_to_gui("ErrorAnalysis", "准备模拟执行修复命令...", "info")

        # Format paths once for replacement
        comfyui_nodes_dir_fmt = self.comfyui_nodes_dir if self.comfyui_nodes_dir else "[custom_nodes 目录未设置]"
        git_exe_fmt = self.git_exe_path if self.git_exe_path else "[Git路径未设置]"
        python_exe_fmt = self.comfyui_portable_python if self.comfyui_portable_python else "[Python路径未设置]"
        comfyui_dir_fmt = self.comfyui_install_dir if self.comfyui_install_dir else "[ComfyUI目录未设置]"

        simulated_cwd = comfyui_dir_fmt # Assume starting CWD

        for index, cmd_template in enumerate(commands_to_simulate):
             if self.stop_event.is_set(): break

             # Replace placeholders in the command template
             cmd_string = cmd_template.replace("{comfyui_nodes_dir}", comfyui_nodes_dir_fmt)\
                                      .replace("{git_exe}", git_exe_fmt)\
                                      .replace("{python_exe}", python_exe_fmt)\
                                      .replace("{comfyui_dir}", comfyui_dir_fmt)

             self.log_to_gui("ErrorAnalysis", f"\n[{index+1}/{len(commands_to_simulate)}] 模拟执行 (CWD: {simulated_cwd}):", "cmd")
             self.log_to_gui("ErrorAnalysis", f"$ {cmd_string}", "cmd")

             # Simulate command effect
             time.sleep(0.5) # Short delay for visual effect
             if self.stop_event.is_set(): break

             simulated_output = "(模拟输出)"
             if cmd_string.lower().startswith("cd "):
                 try:
                     new_dir = cmd_string[3:].strip()
                     # Basic simulation of path joining/resolution relative to current simulated CWD
                     if os.path.isabs(new_dir): # Absolute path
                         simulated_cwd = new_dir
                     elif simulated_cwd.startswith("["): # If current CWD is unset placeholder
                          simulated_cwd = f"{simulated_cwd}/{new_dir}" # Append path crudely
                     else: # Relative path
                         simulated_cwd = os.path.normpath(os.path.join(simulated_cwd, new_dir))
                     simulated_output = f"(模拟: 工作目录切换到 {simulated_cwd})"
                 except Exception as e:
                     simulated_output = f"(模拟: 无法解析 cd 路径: {e})"
                 self.log_to_gui("ErrorAnalysis", simulated_output, "info")

             elif "git pull" in cmd_string.lower():
                  simulated_output = "(模拟输出)\n模拟: 拉取远程更改...\n模拟: Already up to date." # Or simulate changes
                  self.log_to_gui("ErrorAnalysis", simulated_output, "stdout")
             elif "pip install" in cmd_string.lower():
                  simulated_output = "(模拟输出)\n模拟: 检查依赖...\n模拟: Requirement already satisfied." # Or simulate install
                  self.log_to_gui("ErrorAnalysis", simulated_output, "stdout")
             elif "git clone" in cmd_string.lower():
                  simulated_output = "(模拟输出)\n模拟: 克隆仓库...\n模拟: 克隆完成。"
                  self.log_to_gui("ErrorAnalysis", simulated_output, "stdout")
             else: # Default simulation for other commands
                  self.log_to_gui("ErrorAnalysis", "(模拟: 命令执行完成)", "stdout")


        if self.stop_event.is_set():
             self.log_to_gui("ErrorAnalysis", "\n--- 模拟修复流程被取消 ---", "warn")
        else:
             self.log_to_gui("ErrorAnalysis", "\n--- 模拟修复流程结束 ---", "info")

        # UI update handled by worker finally block


    # --- UI State and Helpers ---
    def _update_ui_state(self):
        """Central function to update all button states and status label."""
        # Use root.after to ensure this runs in the main GUI thread
        self.root.after(0, self._do_update_ui_state)

    def _do_update_ui_state(self):
        """The actual UI update logic, called by root.after."""
        if not self.root or not self.root.winfo_exists(): return # Exit if root destroyed

        comfy_running_internally = self._is_comfyui_running()
        comfy_detected_externally = self.comfyui_externally_detected
        update_task_running = self._is_update_task_running()
        is_starting_stopping = False
        try: # Check progress bar state safely
            if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists():
                 is_running = self.progress_bar.winfo_ismapped() and self.progress_bar.cget('mode') == 'indeterminate'
                 # Use status label text as a secondary indicator for starting/stopping phase
                 label_text = self.status_label.cget("text") if hasattr(self, 'status_label') else ""
                 is_starting_stopping = is_running or "启动" in label_text or "停止" in label_text

        except tk.TclError: pass

        status_text = ""; main_stop_style = "Stop.TButton"
        run_comfyui_enabled = tk.NORMAL; stop_all_enabled = tk.DISABLED # Defaults

        # Determine Status and Global Button States
        if update_task_running:
            status_text = "状态: 更新/维护任务进行中..."
            # MOD2: Run button *can* be enabled during update tasks, unless actively starting/stopping ComfyUI
            # run_comfyui_enabled = tk.DISABLED # Keep disabled *if* update task is running? Reverted for safety.
            comfy_can_run_paths = self._validate_paths_for_execution(check_comfyui=True, check_git=False, show_error=False)
            run_comfyui_enabled = tk.DISABLED # Still disable run if an update is active
            stop_all_enabled = tk.NORMAL # Allow stopping update task
            main_stop_style = "StopRunning.TButton"
        elif is_starting_stopping:
             try: status_text = self.status_label.cget("text") # Keep existing status during transitions
             except: status_text = "状态: 处理中..."
             run_comfyui_enabled = tk.DISABLED
             stop_all_enabled = tk.NORMAL
             main_stop_style = "StopRunning.TButton"
        elif comfy_detected_externally:
            status_text = f"状态: 外部 ComfyUI 运行中 (端口 {self.comfyui_api_port})"
            run_comfyui_enabled = tk.DISABLED
            stop_all_enabled = tk.DISABLED # Cannot stop external
        elif comfy_running_internally:
            status_text = "状态: ComfyUI 后台运行中"
            main_stop_style = "StopRunning.TButton"
            run_comfyui_enabled = tk.DISABLED
            stop_all_enabled = tk.NORMAL
        else: # Idle state
            status_text = "状态: 服务已停止"
            comfy_can_run_paths = self._validate_paths_for_execution(check_comfyui=True, check_git=False, show_error=False)
             # MOD2: Run button enabled if paths are valid and NOT starting/stopping/running
            run_comfyui_enabled = tk.NORMAL if comfy_can_run_paths else tk.DISABLED
            stop_all_enabled = tk.DISABLED

        # Update Progress Bar
        try:
            if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists():
                # MOD5: Progress bar active if update task running OR comfyui is starting/stopping
                should_run = update_task_running or is_starting_stopping
                is_currently_running = self.progress_bar.winfo_ismapped() and self.progress_bar.cget('mode') == 'indeterminate'

                if should_run and not is_currently_running:
                    self.progress_bar.start(10)
                    if not self.progress_bar.winfo_ismapped(): self.progress_bar.grid() # Ensure visible
                elif not should_run and is_currently_running:
                    self.progress_bar.stop()
                    # self.progress_bar.grid_remove() # Optionally hide it completely when stopped
                # Ensure visibility matches state if hiding
                # if should_run and not self.progress_bar.winfo_ismapped():
                #      self.progress_bar.grid()
                # elif not should_run and self.progress_bar.winfo_ismapped() and not is_currently_running:
                #      self.progress_bar.grid_remove()

        except tk.TclError: pass

        # Update Status Label
        try:
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                 self.status_label.config(text=status_text)
        except tk.TclError: pass

        # Update Global Run/Stop Buttons
        try:
            if hasattr(self, 'run_all_button') and self.run_all_button.winfo_exists():
                 # Final check: Disable run button if actively starting/stopping
                 final_run_state = tk.DISABLED if is_starting_stopping else run_comfyui_enabled
                 self.run_all_button.config(state=final_run_state)
            if hasattr(self, 'stop_all_button') and self.stop_all_button.winfo_exists():
                 self.stop_all_button.config(state=stop_all_enabled, style=main_stop_style)
        except tk.TclError: pass

        # Update Management Tab Buttons
        git_path_ok = self._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=False)
        # Base state: Enabled only if git is OK AND no other major task is running
        base_update_enabled = tk.NORMAL if git_path_ok and not update_task_running and not is_starting_stopping else tk.DISABLED

        try:
            # Main Body Tab
            if hasattr(self, 'refresh_main_body_button') and self.refresh_main_body_button.winfo_exists():
                 self.refresh_main_body_button.config(state=base_update_enabled)
            if hasattr(self, 'activate_main_body_button') and self.activate_main_body_button.winfo_exists():
                 item_selected_main = bool(self.main_body_tree.focus()) if hasattr(self, 'main_body_tree') and self.main_body_tree.winfo_exists() else False
                 comfy_dir_is_repo = self.comfyui_install_dir and os.path.isdir(os.path.join(self.comfyui_install_dir, ".git"))
                 self.activate_main_body_button.config(state=base_update_enabled if item_selected_main and comfy_dir_is_repo else tk.DISABLED)

            # Nodes Tab
            item_selected_nodes = bool(self.nodes_tree.focus()) if hasattr(self, 'nodes_tree') and self.nodes_tree.winfo_exists() else False
            node_is_installed = False; node_is_git = False; node_has_url = False
            if item_selected_nodes and hasattr(self, 'nodes_tree'):
                 try:
                      node_data = self.nodes_tree.item(self.nodes_tree.focus(), 'values')
                      if node_data and len(node_data) >= 5:
                           node_status = node_data; repo_url = node_data
                           node_is_installed = (node_status == "已安装")
                           node_has_url = repo_url and repo_url not in ("本地安装，无Git信息", "无法获取远程 URL", "本地安装", "N/A", "无远程仓库")
                           node_name_selected = node_data
                           # Check local_nodes_only cache for is_git status
                           found_node_info = next((n for n in self.local_nodes_only if n.get("name") == node_name_selected), None)
                           if found_node_info:
                               node_is_git = found_node_info.get("is_git", False)
                           else: # If not in local cache, might be a remote-only entry, check path if needed
                                node_install_path = os.path.normpath(os.path.join(self.comfyui_nodes_dir, node_name_selected)) if self.comfyui_nodes_dir else ""
                                node_is_git = node_install_path and os.path.isdir(os.path.join(node_install_path, ".git"))

                 except Exception as e: print(f"[Launcher DEBUG] Error getting node state: {e}")

            if hasattr(self, 'nodes_search_entry') and self.nodes_search_entry.winfo_exists(): self.nodes_search_entry.config(state=tk.NORMAL if not update_task_running and not is_starting_stopping else tk.DISABLED)
            if hasattr(self, 'search_nodes_button') and self.search_nodes_button.winfo_exists(): self.search_nodes_button.config(state=tk.NORMAL if not update_task_running and not is_starting_stopping else tk.DISABLED)
            if hasattr(self, 'refresh_nodes_button') and self.refresh_nodes_button.winfo_exists(): self.refresh_nodes_button.config(state=base_update_enabled)

            # Switch/Install Button Logic:
            # Enable if an item is selected AND
            # ( (it's installed, is a git repo, has a URL) OR (it's not installed, has a URL) )
            # AND base_update_enabled is True
            can_switch = node_is_installed and node_is_git and node_has_url
            can_install = not node_is_installed and node_has_url
            switch_install_final_state = base_update_enabled if item_selected_nodes and (can_switch or can_install) else tk.DISABLED
            if hasattr(self, 'switch_install_node_button') and self.switch_install_node_button.winfo_exists():
                 self.switch_install_node_button.config(state=switch_install_final_state)

            # Uninstall Button Logic:
            # Enable if an item is selected AND it's installed AND no task running
            uninstall_final_state = tk.NORMAL if item_selected_nodes and node_is_installed and not update_task_running and not is_starting_stopping else tk.DISABLED
            if hasattr(self, 'uninstall_node_button') and self.uninstall_node_button.winfo_exists():
                 self.uninstall_node_button.config(state=uninstall_final_state)

            if hasattr(self, 'update_all_nodes_button') and self.update_all_nodes_button.winfo_exists(): self.update_all_nodes_button.config(state=base_update_enabled)

            # Analysis Tab Buttons
            api_endpoint_set = bool(self.error_api_endpoint_var.get().strip())
            diagnose_enabled = tk.NORMAL if api_endpoint_set and not update_task_running and not is_starting_stopping else tk.DISABLED
            if hasattr(self, 'diagnose_button') and self.diagnose_button.winfo_exists():
                 self.diagnose_button.config(state=diagnose_enabled)
            analysis_has_content = False
            try:
                if hasattr(self, 'error_analysis_text') and self.error_analysis_text.winfo_exists():
                    analysis_has_content = bool(self.error_analysis_text.get("1.0", "1.end").strip())
            except tk.TclError: pass
            # Fix button enabled if diagnose enabled and analysis has content
            fix_enabled = diagnose_enabled if analysis_has_content else tk.DISABLED
            if hasattr(self, 'fix_button') and self.fix_button.winfo_exists():
                 self.fix_button.config(state=fix_enabled)

        except tk.TclError as e: print(f"[Launcher WARNING] Error updating UI state (widget might not exist): {e}")
        except AttributeError as e: print(f"[Launcher WARNING] Error updating UI state (attribute missing): {e}")
        except Exception as e: print(f"[Launcher ERROR] Unexpected error updating UI state: {e}")


    def reset_ui_on_error(self):
        """Resets UI state after a service encounters an error."""
        print("[Launcher INFO] Resetting UI on error.")
        try:
            if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists() and self.progress_bar.winfo_ismapped():
                self.progress_bar.stop()
                # self.progress_bar.grid_remove() # Optional: Hide
        except tk.TclError: pass

        if self.comfyui_process and self.comfyui_process.poll() is not None:
            self.comfyui_process = None
        self.stop_event.clear()
        self.backend_browser_triggered_for_session = False
        self.comfyui_ready_marker_sent = False
        self.comfyui_externally_detected = False
        self._update_task_running = False # Ensure task flag is clear

        self._update_ui_state()


    def _trigger_comfyui_browser_opening(self):
        """Opens the ComfyUI URL in a web browser when ComfyUI is ready."""
        comfy_is_active = self._is_comfyui_running() or self.comfyui_externally_detected
        if comfy_is_active and not self.backend_browser_triggered_for_session:
            self.backend_browser_triggered_for_session = True
            self.root.after(100, self._open_frontend_browser) # Slight delay
        elif not comfy_is_active: print("[Launcher DEBUG] Browser trigger skipped - ComfyUI stopped.")
        # else: print("[Launcher DEBUG] Browser trigger skipped - Already triggered.")

    def _open_frontend_browser_from_settings(self):
        """Opens the ComfyUI URL configured in settings."""
        try:
            port = int(self.comfyui_api_port_var.get())
            if not (1 <= port <= 65535): raise ValueError("Invalid port")
            comfyui_url = f"http://127.0.0.1:{port}"
            self._open_url_in_browser(comfyui_url)
        except ValueError:
             messagebox.showerror("端口无效", "设置中的端口号无效。", parent=self.root)
        except Exception as e:
             messagebox.showerror("打开失败", f"无法打开浏览器: {e}", parent=self.root)

    def _open_frontend_browser(self):
        """Opens the ComfyUI backend URL derived from config."""
        self.update_derived_paths()
        comfyui_url = f"http://127.0.0.1:{self.comfyui_api_port}"
        self._open_url_in_browser(comfyui_url)

    def _open_url_in_browser(self, url):
        """Opens the given URL in the default web browser."""
        print(f"[Launcher INFO] Opening URL: {url}")
        try:
            webbrowser.open_new_tab(url)
        except Exception as e:
             print(f"[Launcher ERROR] Error opening browser tab for {url}: {e}")
             self.log_to_gui("Launcher", f"无法在浏览器中打开网址: {url}\n错误: {e}", "warn")


    def clear_output_widgets(self):
        """Clears the text in the output ScrolledText widgets."""
        widgets_to_clear = []
        if hasattr(self, 'main_output_text'): widgets_to_clear.append(self.main_output_text)
        if hasattr(self, 'launcher_log_text'): widgets_to_clear.append(self.launcher_log_text)
        if hasattr(self, 'error_analysis_text'): widgets_to_clear.append(self.error_analysis_text)

        for widget in widgets_to_clear:
            try:
                if widget and widget.winfo_exists():
                    widget.config(state=tk.NORMAL)
                    widget.delete('1.0', tk.END)
                    widget.config(state=tk.DISABLED)
            except tk.TclError: pass

    # MOD1: New method to handle 'git pull pause'
    def _run_git_pull_pause(self):
        """Runs 'git pull' in a new terminal window and pauses."""
        git_exe = self.git_exe_path_var.get()
        if not git_exe or not os.path.isfile(git_exe):
            messagebox.showerror("Git 未找到", f"未找到或未配置 Git 可执行文件:\n{git_exe}", parent=self.root)
            self.log_to_gui("Launcher", f"Git pull 失败: Git 路径无效 '{git_exe}'", "error")
            return

        # Get the directory of the launcher script (assuming it's in the repo root)
        launcher_dir = BASE_DIR
        if not os.path.isdir(os.path.join(launcher_dir, ".git")):
            messagebox.showerror("非 Git 仓库", f"当前目录不是一个有效的 Git 仓库:\n{launcher_dir}", parent=self.root)
            self.log_to_gui("Launcher", f"Git pull 失败: '{launcher_dir}' 不是 Git 仓库", "error")
            return

        self.log_to_gui("Launcher", f"准备执行 'git pull' 于目录: {launcher_dir}", "info")

        try:
            # Construct the command based on OS
            if platform.system() == "Windows":
                # Use cmd.exe to run git pull and then pause
                command = f'start cmd /k "cd /d "{launcher_dir}" && "{git_exe}" pull && pause"'
                subprocess.Popen(command, shell=True, creationflags=subprocess.CREATE_NEW_CONSOLE)
            elif platform.system() == "Darwin": # macOS
                 # Use AppleScript to open Terminal, run command, and keep window open
                 # Note: Requires Terminal.app permissions if run sandboxed
                 script = f'''
                 tell application "Terminal"
                     activate
                     do script "cd {shlex.quote(launcher_dir)}; {shlex.quote(git_exe)} pull; echo \\"按 Enter 关闭窗口...\\"; read"
                 end tell
                 '''
                 subprocess.run(['osascript', '-e', script], check=True)
            else: # Linux and other Unix-like
                # Use common terminals like gnome-terminal, konsole, xterm
                terminal_emulator = "xterm" # Default fallback
                if os.environ.get("XDG_CURRENT_DESKTOP") == "GNOME": terminal_emulator = "gnome-terminal"
                elif os.environ.get("XDG_CURRENT_DESKTOP") == "KDE": terminal_emulator = "konsole"
                # Command to run in the terminal: cd, git pull, then bash to keep window open
                cmd_in_terminal = f'cd {shlex.quote(launcher_dir)} && {shlex.quote(git_exe)} pull && echo "按 Enter 关闭窗口..." && read && exit'
                command = [terminal_emulator, "-e", f"bash -c '{cmd_in_terminal}'"]
                subprocess.Popen(command)

            self.log_to_gui("Launcher", "'git pull' 命令已在新终端窗口启动。", "info")

        except FileNotFoundError as e:
             messagebox.showerror("启动终端失败", f"无法找到终端命令:\n{e}\n请检查您的系统配置。", parent=self.root)
             self.log_to_gui("Launcher", f"启动终端失败: {e}", "error")
        except Exception as e:
            messagebox.showerror("执行失败", f"执行 'git pull' 时发生错误:\n{e}", parent=self.root)
            self.log_to_gui("Launcher", f"执行 'git pull' 失败: {e}", "error")


    def on_closing(self):
        """Handles the application closing event."""
        print("[Launcher INFO] Closing application requested.")
        if self._is_comfyui_running() or self._is_update_task_running():
             confirm_stop = messagebox.askyesno("进程运行中", "有后台进程（ComfyUI 或更新任务）正在运行。\n是否在退出前停止？", parent=self.root)
             if confirm_stop:
                 self.log_to_gui("Launcher", "正在停止后台进程...", "info")
                 self.stop_all_services()
                 wait_timeout = 15 # seconds
                 start_time = time.time()
                 while (self._is_comfyui_running() or self._is_update_task_running()) and (time.time() - start_time < wait_timeout):
                     try:
                         if self.root and self.root.winfo_exists():
                              self.root.update() # Process Tkinter events while waiting
                     except tk.TclError: # Handle root window being destroyed early
                          break
                     time.sleep(0.1)

                 if self._is_comfyui_running() or self._is_update_task_running():
                      print("[Launcher WARNING] Processes did not stop gracefully within timeout, forcing exit.")
                      self.log_to_gui("Launcher", "未能完全停止后台进程，强制退出。", "warn")
                      if self.comfyui_process and self.comfyui_process.poll() is None:
                           try: self.comfyui_process.kill()
                           except Exception: pass
                 else:
                      self.log_to_gui("Launcher", "后台进程已停止。", "info")

                 try: # Destroy root window safely
                      if self.root and self.root.winfo_exists():
                          self.root.destroy()
                 except tk.TclError: pass
             else:
                  print("[Launcher INFO] User chose not to stop processes, attempting direct termination.")
                  self.stop_event.set() # Signal threads
                  if self.comfyui_process and self.comfyui_process.poll() is None:
                       try: self.comfyui_process.terminate()
                       except Exception: pass
                  try: # Destroy root window safely
                      if self.root and self.root.winfo_exists():
                          self.root.destroy()
                  except tk.TclError: pass
        else:
             try: # Destroy root window safely
                 if self.root and self.root.winfo_exists():
                     self.root.destroy()
             except tk.TclError: pass


# --- Main Execution ---
if __name__ == "__main__":
    root = None # Define root outside try
    try:
        # Fix blurry fonts on Windows high DPI displays
        if platform.system() == "Windows":
            try:
                from ctypes import windll
                windll.shcore.SetProcessDpiAwareness(1) # Try setting DPI awareness
            except Exception as e:
                print(f"[Launcher WARNING] Failed to set DPI awareness: {e}")

        root = tk.Tk()
        app = ComLauncherApp(root)
        root.mainloop()
    except Exception as e:
        print(f"[Launcher CRITICAL] Unhandled exception during application startup or runtime: {e}", exc_info=True)
        try:
             if root and isinstance(root, tk.Tk) and root.winfo_exists():
                  messagebox.showerror("致命错误 / Fatal Error", f"应用程序遇到致命错误并需要关闭：\n{e}\n请检查控制台或日志文件获取详情。", parent=root)
                  root.destroy()
             else:
                  print("无法在 GUI 中显示错误信息，请查看控制台。")
        except Exception as mb_err:
            print(f"无法显示错误对话框：{mb_err}")
        sys.exit(1) # Exit with error code