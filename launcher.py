# -*- coding: utf-8 -*-
# File: launcher.py
# Version: Kerry, Ver. 2.5.10 (MODs: V2.5.9 base + Node History Modal Fix)

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
DEFAULT_ERROR_API_ENDPOINT = "" # e.g., https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent - User MUST set this
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
# MOD Version Update: Version updated
VERSION_INFO = "Kerry, Ver. 2.5.10" # MOD: Version Updated

# Special marker for queue
_COMFYUI_READY_MARKER_ = "_COMFYUI_IS_READY_FOR_BROWSER_\n"

# --- Text/Output Methods (Standalone function) ---
def setup_text_tags(text_widget):
    """Configures text tags for ScrolledText widget coloring."""
    if not text_widget or not text_widget.winfo_exists():
        return
    try:
        # Define tags with specific foreground colors and font styles
        text_widget.tag_config("stdout", foreground=FG_STDOUT)
        text_widget.tag_config("stderr", foreground=FG_STDERR)
        text_widget.tag_config("info", foreground=FG_INFO, font=(FONT_FAMILY_MONO, FONT_SIZE_MONO, 'italic'))
        text_widget.tag_config("warn", foreground=FG_WARN)
        text_widget.tag_config("error", foreground=FG_STDERR, font=(FONT_FAMILY_MONO, FONT_SIZE_MONO, 'bold'))
        text_widget.tag_config("api_output", foreground=FG_API) # Tag for API analysis output
        text_widget.tag_config("cmd", foreground=FG_CMD, font=(FONT_FAMILY_MONO, FONT_SIZE_MONO, 'bold')) # Tag for commands
        text_widget.tag_config("highlight", foreground=FG_HIGHLIGHT, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL, 'bold')) # MOD: Added highlight tag
    except tk.TclError as e:
        print(f"[Launcher WARNING] Failed to configure text tags: {e}")


# --- Helper functions for Sorting (MOD1: Enhanced date/version parsing and comparison) ---
def _parse_iso_date_for_sort(date_str):
    """Safely parses ISO date string, returns datetime object or None."""
    if not date_str:
        return None
    try:
        # Handle potential 'Z' timezone suffix and various ISO formats
        cleaned_date_str = date_str
        if isinstance(date_str, str):
            if date_str.endswith('Z'):
                cleaned_date_str = date_str[:-1] + '+00:00'
        else: # Handle cases where date_str might not be a string initially
            return None

        # Try parsing with timezone offset first (common formats)
        try:
            # Handles formats like 'YYYY-MM-DDTHH:MM:SS+ZZ:ZZ' or 'YYYY-MM-DD HH:MM:SS+ZZZZ'
            return datetime.fromisoformat(cleaned_date_str.replace(' ', 'T'))
        except ValueError:
            # Fallback for formats like 'YYYY-MM-DD HH:MM:SS +ZZZZ' or 'YYYY-MM-DD HH:MM:SS' (assume UTC if no tz)
            try:
                # Attempt with timezone first (e.g., 'YYYY-MM-DD HH:MM:SS +ZZZZ')
                return datetime.strptime(cleaned_date_str, '%Y-%m-%d %H:%M:%S %z')
            except ValueError:
                try:
                    # Attempt without timezone, assume UTC (e.g., 'YYYY-MM-DD HH:MM:SS')
                    return datetime.strptime(cleaned_date_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
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
    # Clean common prefixes for robust parsing
    cleaned_version_str = version_str
    if isinstance(version_str, str): # Ensure it's a string before processing
        if '/' in cleaned_version_str: # e.g., "tag / v1.2" -> "v1.2"
            cleaned_version_str = cleaned_version_str.split('/')[-1].strip()
        if cleaned_version_str.startswith('v'):
            cleaned_version_str = cleaned_version_str[1:]
        # Handle potential "Local Commit:" or similar prefixes before version parsing
        if cleaned_version_str.startswith("本地"):
             cleaned_version_str = cleaned_version_str.split(":")[-1].strip()
    else: # If not a string, return as is for potential direct comparison or None
        return version_str

    if parse_version: # Use packaging.version if available
        try:
            return parse_version(cleaned_version_str)
        except InvalidVersion:
            # print(f"[Launcher DEBUG] InvalidVersion for '{version_str}' during sort.")
            # Fallback to string comparison for versions unparseable by packaging
            return cleaned_version_str
        except Exception as e:
            print(f"[Launcher ERROR] Unexpected version parsing error for '{version_str}': {e}")
            return cleaned_version_str # Fallback to string comparison
    else: # Basic fallback if packaging isn't installed (already tried numerical tuple)
        # If numerical tuple failed, try splitting by dot for potential numerical tuple sort
        parts = cleaned_version_str.split('.')
        if all(part.isdigit() for part in parts):
             try:
                  return tuple(map(int, parts))
             except ValueError: # Should not happen with isdigit check, but defensive
                  pass

        # If numerical tuple failed, return the cleaned string for basic lexical sort
        return cleaned_version_str

def _compare_versions_for_sort(item1, item2):
    """
    Custom comparison function for sorting main body versions or node histories.
    Prioritizes date (newest first), then version string (descending) for items without valid dates.
    """
    date1 = _parse_iso_date_for_sort(item1.get('date_iso'))
    date2 = _parse_iso_date_for_sort(item2.get('date_iso'))
    name1 = item1.get('name')
    name2 = item2.get('name')
    type1 = item1.get('type', '') # e.g., 'branch', 'tag', 'commit'
    type2 = item2.get('type', '')

    # Compare dates first (descending order - newest first)
    # Items with valid dates sort before items with no valid date (None)
    if date1 is not None and date2 is not None:
        if date1 > date2:
            return -1
        if date1 < date2:
            return 1
        # Dates are equal, proceed to version/type
    elif date1 is not None and date2 is None: # item1 has date, item2 doesn't -> item1 is newer (sorts first)
        return -1
    elif date1 is None and date2 is not None: # item2 has date, item1 doesn't -> item2 is newer (sorts first)
        return 1
    # Both have invalid/None dates, proceed to version comparison

    # Compare versions if dates are inconclusive (descending)
    version1 = _parse_version_string_for_sort(name1)
    version2 = _parse_version_string_for_sort(name2)

    # Prefer numerical tuple comparison if available for both
    is_tuple1 = isinstance(version1, tuple)
    is_tuple2 = isinstance(version2, tuple)

    if is_tuple1 and is_tuple2:
        if version1 > version2:
            return -1 # Descending numerical sort
        if version1 < version2:
            return 1
        # Tuples are equal, proceed to type/name
    elif version1 is not None and version2 is not None: # If packaging.Version or string
        try:
            # If they are both packaging.Version objects, compare directly
            if parse_version and isinstance(version1, parse_version("1.0").__class__) and isinstance(version2, parse_version("1.0").__class__):
                 if version1 > version2:
                      return -1
                 if version1 < version2:
                      return 1
            # Fallback to string comparison if versions are strings or incompatible types for direct comparison
            elif str(version1) > str(version2):
                 return -1
            elif str(version1) < str(version2):
                 return 1

        except TypeError: # Cannot compare different types (e.g., Version vs str, or different string formats)
             # Fallback to simple string comparison if typed comparison fails
             if str(name1) > str(name2):
                  return -1
             elif str(name1) < str(name2):
                  return 1
    elif version1 is not None and version2 is None: # Treat parseable version as higher priority
        return -1
    elif version1 is None and version2 is not None:
        return 1
    # Both version parseable fail, or types incompatible, proceed to type/name fallback

    # Fallback: Compare types (tags usually more important than branches/commits, but order not strictly defined by user - alphabetical?)
    # Let's try sorting by type descending (commit, branch, tag) then name descending if all else equal
    # Prioritize 'tag', then 'branch', then 'commit' - this makes tags appear first, then branches, then commits
    type_order = {'tag': 0, 'branch': 1, 'commit': 2, 'branch (remote)': 3, 'branch (HEAD)': 4, 'commit (HEAD)': 5, '未知': 10} # Lower value = higher priority
    type_comp = type_order.get(type1, 10) - type_order.get(type2, 10)
    if type_comp != 0:
        return type_comp # Sort by type priority

    # Final fallback: Lexicographical comparison of original names (descending)
    if name1 and name2:
        if name1 > name2:
            return -1
        if name1 < name2:
            return 1
    elif name1:
        return -1 # name1 exists, name2 doesn't
    elif name2:
        return 1  # name2 exists, name1 doesn't

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
        # MOD1: Configure rows for new layout: 0=Control, 1=Notebook+Version
        self.root.rowconfigure(0, weight=0) # Control bar row - no expand
        self.root.rowconfigure(1, weight=1) # Notebook+Version row - expand

        # Process and state variables
        self.comfyui_process = None
        # Separate Queues for Logs
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
        self.comfyui_api_port_var = tk.StringVar()
        self.git_exe_path_var = tk.StringVar()
        self.main_repo_url_var = tk.StringVar()
        self.node_config_url_var = tk.StringVar()
        self.error_api_endpoint_var = tk.StringVar()
        self.error_api_key_var = tk.StringVar()
        # MOD5: No StringVar for scrolledtext user_request field

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
        # MOD2: Variables to hold data for node history modal - RENAMED for clarity
        self._node_history_modal_versions_data = [] # List of dictionaries for history items
        self._node_history_modal_node_name = ""      # Name of the node the modal is for
        self._node_history_modal_node_path = ""      # Local path to the node's directory
        self._node_history_modal_current_commit = "" # MOD: Store current commit for modal status
        self._node_history_modal_window = None # MOD2: Reference to the modal window


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

    def save_config_to_file(self, show_success=True):
        """Writes the self.config dictionary to the JSON file."""
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            # Avoid logging every auto-save unless explicitly requested
            if show_success:
                print(f"[Launcher INFO] Configuration saved to {CONFIG_FILE}")
        except Exception as e:
            print(f"[Launcher ERROR] Error saving config file: {e}")
            if self.root and self.root.winfo_exists():
                messagebox.showerror("配置保存错误 / Config Save Error", f"无法将配置保存到文件：\n{e}", parent=self.root)

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
                        return # Skip saving if port is invalid

                # Update the internal config dictionary
                self.config[config_key_changed] = new_value
                # Update derived paths if a relevant path changed
                if config_key_changed in ["comfyui_dir", "python_exe", "git_exe_path", "comfyui_api_port"] or config_key_changed.startswith("vram_") or config_key_changed.endswith(("_precision", "_malloc", "_optimization", "_acceleration")):
                    self.update_derived_paths()
                # Save the entire config to file without showing success message
                self.save_config_to_file(show_success=False)
                # Update UI state if needed (e.g., API button enablement)
                self.root.after(0, self._update_ui_state) # MOD4 Fix: Ensure UI update happens
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
        elif vram_mode == "全负载(10GB以上)":
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


    # Function to open folders
    def open_folder(self, path):
        """Opens a given folder path using the default file explorer."""
        self.update_derived_paths()
        target_path = ""
        if path == 'nodes':
            target_path = self.comfyui_nodes_dir
        elif path == 'models':
            target_path = self.comfyui_models_dir
        elif path == 'lora':
            target_path = self.comfyui_lora_dir
        elif path == 'input':
            target_path = self.comfyui_input_dir
        elif path == 'output':
            target_path = self.comfyui_output_dir
        elif path == 'workflows':
            target_path = self.comfyui_workflows_dir
        else:
            target_path = path

        if not target_path:
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
                subprocess.run(['explorer', os.path.normpath(target_path)], check=False)
            elif platform.system() == "Darwin":
                subprocess.run(['open', target_path], check=True)
            else:
                subprocess.run(['xdg-open', target_path], check=True)
            print(f"[Launcher INFO] Opened folder: {target_path}")
        except FileNotFoundError as e:
             messagebox.showerror("打开文件夹失败 / Failed to Open Folder", f"无法找到文件浏览器命令:\n'{e.filename}'\n错误: {e}", parent=self.root)
             print(f"[Launcher ERROR] Failed to find file explorer command: {e}")
        except Exception as e:
            messagebox.showerror("打开文件夹失败 / Failed to Open Folder", f"无法打开文件夹:\n{target_path}\n错误: {e}", parent=self.root)
            print(f"[Launcher ERROR] Failed to open folder {target_path}: {e}")


    # Function to browse directory
    def browse_directory(self, var_to_set, initial_dir=""):
        """Opens a directory selection dialog."""
        current_val = var_to_set.get()
        effective_initial_dir = current_val if os.path.isdir(current_val) else self.base_project_dir
        directory = filedialog.askdirectory(title="选择目录 / Select Directory", initialdir=effective_initial_dir, parent=self.root)
        if directory:
             normalized_path = os.path.normpath(directory)
             var_to_set.set(normalized_path)

    # Function to browse file
    def browse_file(self, var_to_set, filetypes, initial_dir=""):
        """Opens a file selection dialog."""
        current_val = var_to_set.get()
        effective_initial_dir = os.path.dirname(current_val) if current_val and os.path.isfile(current_val) else self.base_project_dir
        filepath = filedialog.askopenfilename(title="选择文件 / Select File", filetypes=filetypes, initialdir=effective_initial_dir, parent=self.root)
        if filepath:
             var_to_set.set(os.path.normpath(filepath))

    # --- Styling Setup ---
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

        # MOD1 Node Modal List Styles (Based on Treeview Appearance)
        row_bg1, row_bg2 = TEXT_AREA_BG, "#282828" # Darker, slightly alternating backgrounds
        self.style.configure('ModalRowOdd.TFrame', background=row_bg1)
        self.style.configure('ModalRowEven.TFrame', background=row_bg2)


        # LabelFrame
        self.style.configure('TLabelframe', background=BG_COLOR, foreground=FG_COLOR, bordercolor=BORDER_COLOR, relief=tk.GROOVE)
        self.style.configure('TLabelframe.Label', background=BG_COLOR, foreground=FG_COLOR, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL, 'italic'))

        # Labels
        self.style.configure('TLabel', background=BG_COLOR, foreground=FG_COLOR)
        self.style.configure('Status.TLabel', background=CONTROL_FRAME_BG, foreground=FG_MUTED, padding=(5, 3))
        self.style.configure('Version.TLabel', background=BG_COLOR, foreground=FG_MUTED, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL - 1))
        self.style.configure('Hint.TLabel', background=BG_COLOR, foreground=FG_MUTED, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL - 1), padding=(0, 0, 0, 0))
        self.style.configure('Highlight.TLabel', background=BG_COLOR, foreground=FG_HIGHLIGHT, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL, 'bold')) # Style for highlighted status in modal
        self.style.configure('ModalHeader.TLabel', background=BG_COLOR, foreground=FG_COLOR, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL, 'bold')) # MOD1: Style for modal header text

        # MOD1: Styles for labels within modal list rows, inheriting background
        self.style.configure('ModalRowOdd.TLabel', background=row_bg1, foreground=FG_COLOR)
        self.style.configure('ModalRowEven.TLabel', background=row_bg2, foreground=FG_COLOR)
        self.style.configure('ModalRowOddHighlight.TLabel', background=row_bg1, foreground=FG_HIGHLIGHT, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL, 'bold'))
        self.style.configure('ModalRowEvenHighlight.TLabel', background=row_bg2, foreground=FG_HIGHLIGHT, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL, 'bold'))


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
        self.style.configure("Modal.TButton", padding=(4, 2), font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL-1), background=tab_neutral_bg, foreground=neutral_button_fg) # Modal buttons, slightly smaller padding
        self.style.map("Modal.TButton", background=[('pressed', tab_n_pressed_bg), ('active', tab_n_active_bg), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])
        # MOD1: Style for the new Version Button (using Tab.TButton style)
        self.style.configure("Version.TButton", padding=(2, 1), font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL - 1), background=BG_COLOR, foreground=FG_MUTED, relief=tk.FLAT, borderwidth=0) # Flat look
        self.style.map("Version.TButton", foreground=[('active', FG_COLOR), ('pressed', FG_COLOR)], background=[('active', "#3f3f3f"), ('pressed', "#4f4f4f")])


        # Other Widgets
        self.style.configure('TCheckbutton', background=BG_COLOR, foreground=FG_COLOR, font=main_fnt); self.style.map('TCheckbutton', background=[('active', BG_COLOR)], indicatorcolor=[('selected', ACCENT_COLOR), ('pressed', ACCENT_ACTIVE), ('!selected', FG_MUTED)], foreground=[('disabled', FG_MUTED)])
        self.style.configure('TCombobox', fieldbackground=TEXT_AREA_BG, background=TEXT_AREA_BG, foreground=FG_COLOR, arrowcolor=FG_COLOR, bordercolor=BORDER_COLOR, insertcolor=FG_COLOR, padding=(5, 4), font=main_fnt); self.style.map('TCombobox', fieldbackground=[('readonly', TEXT_AREA_BG), ('disabled', CONTROL_FRAME_BG)], foreground=[('disabled', FG_MUTED), ('readonly', FG_COLOR)], arrowcolor=[('disabled', FG_MUTED)], selectbackground=[('!focus', ACCENT_COLOR), ('focus', ACCENT_ACTIVE)], selectforeground=[('!focus', 'white'), ('focus', 'white')])
        try:
            self.root.option_add('*TCombobox*Listbox.background', TEXT_AREA_BG); self.root.option_add('*TCombobox*Listbox.foreground', FG_COLOR); self.root.option_add('*TCombobox*Listbox.selectBackground', ACCENT_ACTIVE); self.root.option_add('*TCombobox*Listbox.selectForeground', 'white'); self.root.option_add('*TCombobox*Listbox.font', (FONT_FAMILY_UI, FONT_SIZE_NORMAL)); self.root.option_add('*TCombobox*Listbox.borderWidth', 1); self.root.option_add('*TCombobox*Listbox.relief', 'solid')
        except tk.TclError as e:
            print(f"[Launcher WARNING] Could not set Combobox Listbox styles: {e}")
        self.style.configure('TNotebook', background=BG_COLOR, borderwidth=0, tabmargins=[5, 5, 5, 0]); self.style.configure('TNotebook.Tab', padding=[15, 8], background=BG_COLOR, foreground=FG_MUTED, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL), borderwidth=0); self.style.map('TNotebook.Tab', background=[('selected', '#4a4a4a'), ('active', '#3a3a3a')], foreground=[('selected', 'white'), ('active', FG_COLOR)], focuscolor=self.style.lookup('TNotebook.Tab', 'background'))
        self.style.configure('Horizontal.TProgressbar', thickness=6, background=ACCENT_COLOR, troughcolor=CONTROL_FRAME_BG, borderwidth=0)
        self.style.configure('TEntry', fieldbackground=TEXT_AREA_BG, foreground=FG_COLOR, insertcolor='white', bordercolor=BORDER_COLOR, borderwidth=1, padding=(5,4)); self.style.map('TEntry', fieldbackground=[('focus', TEXT_AREA_BG)], bordercolor=[('focus', ACCENT_COLOR)], lightcolor=[('focus', ACCENT_COLOR)])
        self.style.configure('Treeview', background=TEXT_AREA_BG, foreground=FG_STDOUT, fieldbackground=TEXT_AREA_BG, rowheight=22); self.style.configure('Treeview.Heading', font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL, 'bold'), background=CONTROL_FRAME_BG, foreground=FG_COLOR); self.style.map('Treeview', background=[('selected', ACCENT_ACTIVE)], foreground=[('selected', 'white')])
        # MOD1: Added style for Modal Canvas - This style is actually unused because tk.Canvas does not support the -style option.
        # The bg, highlightthickness, etc. parameters directly style the tk.Canvas.
        # self.style.configure('Modal.TCanvas', background=TEXT_AREA_BG, borderwidth=0, highlightthickness=0); # Keep style definition but it's ineffective for tk.Canvas


    # --- UI Setup ---
    def setup_ui(self):
        """Builds the main UI structure."""
        # Top Control Frame (Row 0)
        control_frame = ttk.Frame(self.root, padding=(10, 10, 10, 5), style='Control.TFrame')
        control_frame.grid(row=0, column=0, sticky="ew")
        control_frame.columnconfigure(1, weight=1) # Spacer column

        self.status_label = ttk.Label(control_frame, text="状态: 初始化...", style='Status.TLabel', anchor=tk.W)
        self.status_label.grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Label(control_frame, text="", style='Status.TLabel').grid(row=0, column=1, sticky="ew") # Spacer
        self.progress_bar = ttk.Progressbar(control_frame, mode='indeterminate', length=350, style='Horizontal.TProgressbar')
        self.progress_bar.grid(row=0, column=2, padx=10)
        self.progress_bar.stop() # Start stopped
        self.stop_all_button = ttk.Button(control_frame, text="停止", command=self.stop_all_services, style="Stop.TButton", width=12)
        self.stop_all_button.grid(row=0, column=3, padx=(0, 5))
        self.run_all_button = ttk.Button(control_frame, text="运行 ComfyUI", command=self.start_comfyui_service_thread, style="Accent.TButton", width=12)
        self.run_all_button.grid(row=0, column=4, padx=(0, 0))

        # --- MOD1: Container for Notebook and Version Info (Row 1) ---
        top_area_frame = ttk.Frame(self.root, style='TFrame') # Use base TFrame style
        top_area_frame.grid(row=1, column=0, sticky="nsew")
        top_area_frame.columnconfigure(0, weight=1) # Notebook area expands
        top_area_frame.rowconfigure(0, weight=1)   # Notebook area expands vertically

        # Main Notebook (Tabs: 设置, 管理, 日志, 分析)
        self.notebook = ttk.Notebook(top_area_frame, style='TNotebook')
        # Place Notebook in the main cell of the top area
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=(5, 5)) # Added top padding
        self.notebook.enable_traversal()

        # Version Info Frame (within top_area_frame, top-right)
        version_frame = ttk.Frame(top_area_frame, style='Version.TFrame', padding=(0, 0, 10, 0)) # Adjust padding
        # Place Version Frame in the same cell, but stick to top-right
        version_frame.grid(row=0, column=0, sticky="ne", padx=(0, 10), pady=(5,0)) # Added top/right padding for alignment
        # Make version button stick to the right within its frame
        version_frame.columnconfigure(0, weight=1)

        version_button = ttk.Button(version_frame,
                                    text=VERSION_INFO, # Uses the updated constant
                                    style="Version.TButton", # Use the new style
                                    command=self._run_git_pull_pause) # Call the update function
        # Grid button within version_frame, pushed right
        version_button.grid(row=0, column=1, sticky="e")

        # --- Settings Tab ---
        self.settings_frame = ttk.Frame(self.notebook, padding="15", style='Settings.TFrame')
        self.settings_frame.columnconfigure(0, weight=1)
        self.notebook.add(self.settings_frame, text=' 设置 / Settings ')
        current_row = 0; frame_padx = 5; frame_pady = (0, 10); widget_pady = 3; widget_padx = 5; label_min_width = 25

        # Folder Access Buttons
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

        # Basic Settings Group
        basic_group = ttk.LabelFrame(self.settings_frame, text=" 基本路径与端口 / Basic Paths & Ports ", padding=(10, 5))
        basic_group.grid(row=current_row, column=0, sticky="ew", padx=frame_padx, pady=frame_pady)
        basic_group.columnconfigure(1, weight=1) # Entry column expands
        basic_row = 0

        # ComfyUI Install Dir
        # ttk.Label(basic_group, text="ComfyUI 安装目录:", width=label_min_width, anchor=tk.W).grid(row=basic_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        ttk.Label(basic_group, text="ComfyUI 安装目录:", anchor=tk.W).grid(row=basic_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx) # Removed fixed width
        dir_entry = ttk.Entry(basic_group, textvariable=self.comfyui_dir_var)
        dir_entry.grid(row=basic_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx)
        dir_btn = ttk.Button(basic_group, text="浏览", width=6, style='Browse.TButton', command=lambda: self.browse_directory(self.comfyui_dir_var))
        dir_btn.grid(row=basic_row, column=2, sticky=tk.E, pady=widget_pady, padx=(0, widget_padx))
        basic_row += 1

        # ComfyUI Python Exe
        # ttk.Label(basic_group, text="ComfyUI Python 路径:", width=label_min_width, anchor=tk.W).grid(row=basic_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        ttk.Label(basic_group, text="ComfyUI Python 路径:", anchor=tk.W).grid(row=basic_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx) # Removed fixed width
        py_entry = ttk.Entry(basic_group, textvariable=self.python_exe_var)
        py_entry.grid(row=basic_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx)
        py_btn = ttk.Button(basic_group, text="浏览", width=6, style='Browse.TButton', command=lambda: self.browse_file(self.python_exe_var, [("Python Executable", "python.exe"), ("All Files", "*.*")]))
        py_btn.grid(row=basic_row, column=2, sticky=tk.E, pady=widget_pady, padx=(0, widget_padx))
        basic_row += 1

        # Git Exe Path
        # ttk.Label(basic_group, text="Git 可执行文件路径:", width=label_min_width, anchor=tk.W).grid(row=basic_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        ttk.Label(basic_group, text="Git 可执行文件路径:", anchor=tk.W).grid(row=basic_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx) # Removed fixed width
        git_entry = ttk.Entry(basic_group, textvariable=self.git_exe_path_var)
        git_entry.grid(row=basic_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx)
        git_btn = ttk.Button(basic_group, text="浏览", width=6, style='Browse.TButton', command=lambda: self.browse_file(self.git_exe_path_var, [("Git Executable", "git.exe"), ("All Files", "*.*")]))
        git_btn.grid(row=basic_row, column=2, sticky=tk.E, pady=widget_pady, padx=(0, widget_padx))
        basic_row += 1

        # ComfyUI API Port
        port_frame = ttk.Frame(basic_group) # Frame to hold port entry and button
        port_frame.grid(row=basic_row, column=1, columnspan=2, sticky="ew") # Span entry and button columns
        port_frame.columnconfigure(0, weight=1) # Entry expands

        # ttk.Label(basic_group, text="ComfyUI 监听与共享端口:", width=label_min_width, anchor=tk.W).grid(row=basic_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        ttk.Label(basic_group, text="ComfyUI 监听与共享端口:", anchor=tk.W).grid(row=basic_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx) # Removed fixed width
        comfyui_port_entry = ttk.Entry(port_frame, textvariable=self.comfyui_api_port_var, width=10) # Fixed width might be better here
        comfyui_port_entry.grid(row=0, column=0, sticky="w", pady=widget_pady, padx=widget_padx) # Align left, use west anchor
        port_open_btn = ttk.Button(port_frame, text="打开", width=6, style='Browse.TButton', command=self._open_frontend_browser_from_settings)
        port_open_btn.grid(row=0, column=1, sticky="w", pady=widget_pady, padx=(0, widget_padx)) # Place button next to entry

        basic_row += 1
        current_row += 1

        # Performance Group
        perf_group = ttk.LabelFrame(self.settings_frame, text=" 性能与显存优化 / Performance & VRAM Optimization ", padding=(10, 5))
        perf_group.grid(row=current_row, column=0, sticky="ew", padx=frame_padx, pady=frame_pady)
        perf_group.columnconfigure(1, weight=1); perf_row = 0

        # VRAM Mode
        ttk.Label(perf_group, text="显存优化:", anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx); # Removed fixed width
        vram_modes = ["全负载(10GB以上)", "高负载(8GB以上)", "中负载(4GB以上)", "低负载(2GB以上)"]
        vram_mode_combo = ttk.Combobox(perf_group, textvariable=self.vram_mode_var, values=vram_modes, state="readonly"); vram_mode_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); perf_row += 1
        # CKPT Precision
        ttk.Label(perf_group, text="CKPT模型精度:", anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx); # Removed fixed width
        ckpt_precisions = ["全精度(FP32)", "半精度(FP16)"]
        ckpt_precision_combo = ttk.Combobox(perf_group, textvariable=self.ckpt_precision_var, values=ckpt_precisions, state="readonly"); ckpt_precision_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); perf_row += 1
        # CLIP Precision
        ttk.Label(perf_group, text="CLIP编码精度:", anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx); # Removed fixed width
        clip_precisions = ["全精度(FP32)", "半精度(FP16)", "FP8 (E4M3FN)", "FP8 (E5M2)"]
        clip_precision_combo = ttk.Combobox(perf_group, textvariable=self.clip_precision_var, values=clip_precisions, state="readonly"); clip_precision_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); perf_row += 1
        # UNET Precision
        ttk.Label(perf_group, text="UNET模型精度:", anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx); # Removed fixed width
        unet_precisions = ["半精度(BF16)", "半精度(FP16)", "FP8 (E4M3FN)", "FP8 (E5M2)"]
        unet_precision_combo = ttk.Combobox(perf_group, textvariable=self.unet_precision_var, values=unet_precisions, state="readonly"); unet_precision_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); perf_row += 1
        # VAE Precision
        ttk.Label(perf_group, text="VAE模型精度:", anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx); # Removed fixed width
        vae_precisions = ["全精度(FP32)", "半精度(FP16)", "半精度(BF16)"]
        vae_precision_combo = ttk.Combobox(perf_group, textvariable=self.vae_precision_var, values=vae_precisions, state="readonly"); vae_precision_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); perf_row += 1
        # CUDA Malloc
        ttk.Label(perf_group, text="CUDA智能内存分配:", anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx); # Removed fixed width
        cuda_malloc_options = ["启用", "禁用"]
        cuda_malloc_combo = ttk.Combobox(perf_group, textvariable=self.cuda_malloc_var, values=cuda_malloc_options, state="readonly"); cuda_malloc_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); perf_row += 1
        # IPEX Optimization
        ttk.Label(perf_group, text="IPEX优化:", anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx); # Removed fixed width
        ipex_options = ["启用", "禁用"]
        ipex_combo = ttk.Combobox(perf_group, textvariable=self.ipex_optimization_var, values=ipex_options, state="readonly"); ipex_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); perf_row += 1
        # xformers Acceleration
        ttk.Label(perf_group, text="xformers加速:", anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx); # Removed fixed width
        xformers_options = ["启用", "禁用"]
        xformers_combo = ttk.Combobox(perf_group, textvariable=self.xformers_acceleration_var, values=xformers_options, state="readonly"); xformers_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); perf_row += 1

        current_row += 1
        self.settings_frame.rowconfigure(current_row, weight=1) # Spacer row

        # --- Management Tab ---
        self.update_frame = ttk.Frame(self.notebook, padding="15", style='TFrame')
        self.update_frame.columnconfigure(0, weight=1)
        self.update_frame.rowconfigure(1, weight=1) # Make bottom area (Node Management) expandable
        self.notebook.add(self.update_frame, text=' 管理 / Management ')

        update_current_row = 0
        # Repository Address Area
        repo_address_group = ttk.LabelFrame(self.update_frame, text=" 仓库地址 / Repository Address ", padding=(10, 5))
        repo_address_group.grid(row=update_current_row, column=0, sticky="ew", padx=frame_padx, pady=frame_pady)
        repo_address_group.columnconfigure(1, weight=1)
        repo_row = 0
        ttk.Label(repo_address_group, text="本体仓库地址:", anchor=tk.W).grid(row=repo_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx) # Removed fixed width
        main_repo_entry = ttk.Entry(repo_address_group, textvariable=self.main_repo_url_var)
        main_repo_entry.grid(row=repo_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); repo_row += 1
        ttk.Label(repo_address_group, text="节点配置地址:", anchor=tk.W).grid(row=repo_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx) # Removed fixed width
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

        # Main Body Versions List
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

        # Nodes Search and Control
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
        # MOD2: Command for the '切换版本' button modified to trigger history fetch or install
        self.switch_install_node_button = ttk.Button(nodes_buttons_container, text="切换版本", style="Tab.TButton", command=self._queue_node_switch_or_show_history) # Modified command
        self.switch_install_node_button.pack(side=tk.LEFT, padx=5)
        self.uninstall_node_button = ttk.Button(nodes_buttons_container, text="卸载节点", style="Tab.TButton", command=self._queue_node_uninstall)
        self.uninstall_node_button.pack(side=tk.LEFT, padx=5)
        self.update_all_nodes_button = ttk.Button(nodes_buttons_container, text="更新全部", style="TabAccent.TButton", command=self._queue_all_nodes_update)
        self.update_all_nodes_button.pack(side=tk.LEFT, padx=5)

        # Hint Label
        ttk.Label(self.nodes_frame, text="列表默认显示本地 custom_nodes 目录下的全部节点。输入内容后点击“搜索”显示匹配的本地/在线节点。", style='Hint.TLabel').grid(row=1, column=0, sticky=tk.W, padx=5, pady=(0, 5), columnspan=2)

        # Nodes List
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
        except tk.TclError:
            pass
        self.nodes_tree.bind("<<TreeviewSelect>>", lambda event: self._update_ui_state())


        # --- Logs Tab ---
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

        # ComfyUI Log Sub-tab
        comfyui_log_frame = ttk.Frame(self.logs_notebook, style='Logs.TFrame', padding=0)
        comfyui_log_frame.columnconfigure(0, weight=1)
        comfyui_log_frame.rowconfigure(0, weight=1)
        self.logs_notebook.add(comfyui_log_frame, text=' ComfyUI日志 / ComfyUI Logs ')
        self.main_output_text = scrolledtext.ScrolledText(comfyui_log_frame, wrap=tk.WORD, state=tk.DISABLED, font=(FONT_FAMILY_MONO, FONT_SIZE_MONO), bg=TEXT_AREA_BG, fg=FG_STDOUT, relief=tk.FLAT, borderwidth=1, bd=1, highlightthickness=1, highlightbackground=BORDER_COLOR, insertbackground="white")
        self.main_output_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        setup_text_tags(self.main_output_text) # Apply color tags


        # --- Analysis Tab (MOD2: Layout Optimization) ---
        self.analysis_frame = ttk.Frame(self.notebook, padding="15", style='Analysis.TFrame')
        # Configure column 1 to expand for entries and user request text area
        self.analysis_frame.columnconfigure(1, weight=1)
        # Configure row 3 to expand for the analysis output text area
        self.analysis_frame.rowconfigure(3, weight=1)
        self.notebook.add(self.analysis_frame, text=' 分析 / Analysis ')

        analysis_current_row = 0

        # Row 0: API Endpoint
        # MOD2: Remove fixed width, rely on column weights and padding
        ttk.Label(self.analysis_frame, text="API 接口:", anchor=tk.W).grid(row=analysis_current_row, column=0, sticky=tk.W, padx=widget_padx, pady=(0, widget_pady))
        self.api_endpoint_entry = ttk.Entry(self.analysis_frame, textvariable=self.error_api_endpoint_var)
        # MOD2: Place in column 1, make sticky EW
        self.api_endpoint_entry.grid(row=analysis_current_row, column=1, sticky="ew", padx=widget_padx, pady=(0, widget_pady))
        analysis_current_row += 1

        # Row 1: API Key and Buttons
        # MOD2: Remove fixed width, rely on column weights and padding
        ttk.Label(self.analysis_frame, text="API 密匙:", anchor=tk.W).grid(row=analysis_current_row, column=0, sticky=tk.W, padx=widget_padx, pady=widget_pady)
        key_button_frame = ttk.Frame(self.analysis_frame, style='Analysis.TFrame') # Frame to hold key entry and buttons
        # MOD2: Place in column 1, make sticky EW
        key_button_frame.grid(row=analysis_current_row, column=1, sticky="ew", padx=widget_padx, pady=widget_pady)
        key_button_frame.columnconfigure(0, weight=1) # Key entry expands within key_button_frame
        self.api_key_entry = ttk.Entry(key_button_frame, textvariable=self.error_api_key_var, show="*")
        self.api_key_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10)) # Sticky EW to fill column 0 of key_button_frame
        self.diagnose_button = ttk.Button(key_button_frame, text="诊断", style="Tab.TButton", command=self.run_diagnosis)
        self.diagnose_button.grid(row=0, column=1, padx=(0, 5)) # Grid in column 1 of key_button_frame
        self.fix_button = ttk.Button(key_button_frame, text="修复", style="Tab.TButton", command=self.run_fix)
        self.fix_button.grid(row=0, column=2) # Grid in column 2 of key_button_frame
        analysis_current_row += 1

        # Row 2: User Request Label and Input (MOD2: Side-by-side)
        # MOD2: Remove fixed width, rely on column weights and padding
        ttk.Label(self.analysis_frame, text="用户诉求:", anchor=tk.W).grid(row=analysis_current_row, column=0, sticky=tk.W, padx=widget_padx, pady=widget_pady)
        # MOD2: Create ScrolledText with specified height and reduced font size
        user_request_font = tkfont.Font(family=FONT_FAMILY_UI, size=FONT_SIZE_NORMAL - 1) # Define font with reduced size
        self.user_request_text = scrolledtext.ScrolledText(self.analysis_frame, wrap=tk.WORD, height=6, # MOD2: Set height to 6 lines
                                                           font=user_request_font, # MOD2: Apply reduced font size
                                                           bg=TEXT_AREA_BG, fg=FG_COLOR, relief=tk.FLAT,
                                                           borderwidth=1, bd=1, highlightthickness=1,
                                                           highlightbackground=BORDER_COLOR, insertbackground="white")
        # MOD2: Place in column 1, make sticky EW
        self.user_request_text.grid(row=analysis_current_row, column=1, sticky="ew", padx=widget_padx, pady=(0, widget_pady))
        self.user_request_text.bind("<KeyRelease>", lambda event: self._update_ui_state()) # MOD4: Ensure UI state updates on input
        analysis_current_row += 1 # Move to the next row for the analysis output (now row 3)

        # Row 3: Output Text Area (CMD code display box) - Now row 3
        self.error_analysis_text = scrolledtext.ScrolledText(self.analysis_frame, wrap=tk.WORD, state=tk.DISABLED, font=(FONT_FAMILY_MONO, FONT_SIZE_MONO), bg=TEXT_AREA_BG, fg=FG_STDOUT, relief=tk.FLAT, borderwidth=1, bd=1, highlightthickness=1, highlightbackground=BORDER_COLOR, insertbackground="white")
        # MOD2: Place in column 0 AND 1 (span), make sticky NSEW to fill expanding row/column
        self.error_analysis_text.grid(row=analysis_current_row, column=0, columnspan=2, sticky="nsew", padx=frame_padx, pady=(5, 0))
        setup_text_tags(self.error_analysis_text) # Apply tags including 'api_output' and 'cmd'


        # Default to Settings tab initially
        self.notebook.select(self.settings_frame)

        # MOD4: Bind changes in API entry fields to update the UI state immediately
        self.error_api_endpoint_var.trace_add('write', lambda *args: self.root.after(0, self._update_ui_state))
        self.error_api_key_var.trace_add('write', lambda *args: self.root.after(0, self._update_ui_state))


    # --- Text/Output Methods ---
    def insert_output(self, text_widget, line, tag="stdout"):
        """Inserts text into a widget with tags, handles auto-scroll."""
        if not text_widget or not text_widget.winfo_exists():
            return
        try:
            text_widget.config(state=tk.NORMAL)
            # Ensure tag exists before inserting
            if tag not in text_widget.tag_names():
                tag = "stdout" # Fallback tag
            # MOD6: Add timestamp prefix to Launcher logs only
            if text_widget == self.launcher_log_text:
                 timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                 line = f"[{timestamp}] {line}"

            text_widget.insert(tk.END, line, (tag,))
            # Always scroll to the end after inserting text
            text_widget.see(tk.END)
            # MOD2: Ensure ScrolledText widgets intended for user input remain normal
            if text_widget != self.user_request_text:
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
        if not isinstance(message, str): # Ensure message is a string
            message = str(message)

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
        else: # Fallback for unknown levels
             tag = "info"


        # Construct the log line prefix for context (handled in insert_output for timestamp)
        # For queueing, just include the source prefix if not ComfyUI
        log_prefix = f"[{source}] " if source and source != "ComfyUI" else ""
        # ComfyUI stream_output adds its own prefix

        # Put the formatted message and tag into the queue
        try:
             target_queue.put((log_prefix + message, tag))
        except Exception as e:
             print(f"[Launcher CRITICAL] Failed to put log message in queue: {e}")


    def process_output_queues(self):
        """Processes messages from BOTH log queues and updates text widgets."""
        processed_count = 0
        max_lines_per_update = 50 # Process up to 50 lines per interval

        # Process Launcher Log Queue
        try:
            while not self.launcher_log_queue.empty() and processed_count < max_lines_per_update:
                line, tag = self.launcher_log_queue.get_nowait()
                # Route Analysis API/CMD output to error_analysis_text
                # Check the _prefix_ added in log_to_gui, not just the raw line start
                is_error_analysis_log = line.startswith("[ErrorAnalysis]") # MOD5: Check prefix

                if is_error_analysis_log:
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
        log_level = "stderr" if is_stderr else ("stdout" if is_comfyui_stream else "info")

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
                    # Prefix is added here for streams, log_to_gui adds prefix for its own messages
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
        # MOD2: Allow starting even if update task is running (UI state handles button enablement)
        # if self._is_update_task_running(): # Check removed here, rely on UI state
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
        self.status_label.config(text="状态: 启动 ComfyUI 后台...")
        self.clear_output_widgets() # Clear previous logs (MOD6: Launcher log preserved)

        # Switch to the "Logs" tab, then the "ComfyUI日志" sub-tab
        try:
             self.notebook.select(self.logs_tab_frame)
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
                try:
                    stdout_output, stderr_output = self.comfyui_process.communicate(timeout=0.5) # Short timeout
                    if stdout_output:
                        error_reason += f"\n\nStdout:\n{stdout_output.strip()}"
                    if stderr_output:
                        error_reason += f"\n\nStderr:\n{stderr_output.strip()}"
                except subprocess.TimeoutExpired:
                    pass # Output likely being handled by threads
                except Exception as read_err:
                    print(f"[Launcher WARNING] Error reading immediate output: {read_err}")
                try:
                    with socket.create_connection(("127.0.0.1", port_to_check), timeout=0.5):
                        pass
                    error_reason += f"\n\n可能原因：端口 {port_to_check} 似乎已被占用。"
                except (ConnectionRefusedError, socket.timeout):
                    pass # Port likely free
                except Exception:
                    pass # Other port check error
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
        # MOD2: Also check if node history modal is open and try to close it
        if self._node_history_modal_window and self._node_history_modal_window.winfo_exists():
             self._cleanup_modal_state(self._node_history_modal_window)
             # Give modal a moment to close before proceeding with stop if needed
             self.root.update_idletasks() # Process pending events

        if not self._is_comfyui_running() and not self.comfyui_externally_detected and not self._is_update_task_running():
             print("[Launcher INFO] Stop all: No managed process active or detected.")
             self._update_ui_state()
             return

        self.log_to_gui("Launcher", "请求停止所有服务...", "info")
        self.root.after(0, self._update_ui_state) # Update UI before stopping
        self.status_label.config(text="状态: 停止所有服务...")
        self.progress_bar.start(10)

        if self._is_comfyui_running():
             self._stop_comfyui_service() # Handles its own UI updates within
        elif self.comfyui_externally_detected:
            self.comfyui_externally_detected = False
            self.log_to_gui("Launcher", "检测到外部 ComfyUI，未尝试停止。", "info")

        if self._is_update_task_running():
             self.log_to_gui("Launcher", "请求停止当前更新任务...", "info")
             self.stop_event.set() # Signal worker thread

        # Give worker a moment to react, then update UI
        self.root.after(100, self._update_ui_state)


    # --- Git Execution Helper ---
    def _run_git_command(self, command_list, cwd, timeout=300, log_output=True):
        """Runs a git command, logs output, and returns stdout, stderr, return code."""
        git_exe = self.git_exe_path_var.get()
        if not git_exe or not os.path.isfile(git_exe):
             err_msg = f"Git 可执行文件路径未配置或无效: {git_exe}"
             if log_output:
                 self.log_to_gui("Git", err_msg, "error", target_override="Launcher") # Log to launcher log
             return "", err_msg, 127

        full_cmd = [git_exe] + command_list
        git_env = os.environ.copy()
        git_env['PYTHONIOENCODING'] = 'utf-8'
        git_env['GIT_TERMINAL_PROMPT'] = '0'

        if not os.path.isdir(cwd):
             err_msg = f"Git 命令工作目录不存在或无效: {cwd}"
             if log_output:
                 self.log_to_gui("Git", err_msg, "error", target_override="Launcher") # Log to launcher log
             return "", err_msg, 1

        try:
            cmd_log_list = [shlex.quote(arg) for arg in full_cmd]
            cmd_log_str = ' '.join(cmd_log_list)
            if log_output:
                 self.log_to_gui("Git", f"执行: {cmd_log_str}", "cmd", target_override="Launcher") # Log to launcher log
                 self.log_to_gui("Git", f"工作目录: {cwd}", "cmd", target_override="Launcher") # Log to launcher log

            startupinfo = None
            creationflags = 0
            if os.name == 'nt':
                 creationflags = subprocess.CREATE_NO_WINDOW

            process = subprocess.Popen(
                full_cmd,
                cwd=cwd,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, encoding='utf-8', errors='replace',
                startupinfo=startupinfo, creationflags=creationflags,
                env=git_env
            )

            stdout_full = ""
            stderr_full = ""
            try:
                stdout_full, stderr_full = process.communicate(timeout=timeout)
                returncode = process.returncode
                if log_output:
                    if stdout_full:
                        self.log_to_gui("Git", stdout_full, "stdout", target_override="Launcher") # Log to launcher log
                    if stderr_full:
                        self.log_to_gui("Git", stderr_full, "stderr", target_override="Launcher") # Log to launcher log
            except subprocess.TimeoutExpired:
                if log_output:
                    self.log_to_gui("Git", f"Git 命令超时 ({timeout} 秒), 进程被终止。", "error", target_override="Launcher") # Log to launcher log
                try:
                    process.kill()
                except OSError:
                    pass
                returncode = 124 # Standard timeout exit code
                stdout_full, stderr_full = "", "命令执行超时 / Command timed out"

            if log_output and returncode != 0:
                 self.log_to_gui("Git", f"Git 命令返回非零退出码 {returncode}。", "warn", target_override="Launcher") # Log to launcher log

            return stdout_full, stderr_full, returncode

        except FileNotFoundError:
            error_msg = f"Git 可执行文件未找到: {git_exe}"
            if log_output:
                self.log_to_gui("Git", error_msg, "error", target_override="Launcher") # Log to launcher log
            return "", error_msg, 127
        except Exception as e:
            error_msg = f"执行 Git 命令时发生意外错误: {e}\n命令: {' '.join(full_cmd)}"
            if log_output:
                self.log_to_gui("Git", error_msg, "error", target_override="Launcher") # Log to launcher log
            return "", error_msg, 1


    # --- Update Task Worker Thread ---
    def _update_task_worker(self):
        """Worker thread that processes update tasks from the queue."""
        while True:
            task_func, task_args, task_kwargs = None, None, None # Define outside try
            try:
                # Use timeout=0.1 or small value so the loop can check stop_event frequently
                task_func, task_args, task_kwargs = self.update_task_queue.get(timeout=0.1)
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
                    # MOD5 Debug: Add print to confirm finally block execution
                    print(f"[Launcher DEBUG] Task '{task_func.__name__ if task_func else 'Unknown'}' finished, entering finally block.")
                    self.update_task_queue.task_done()
                    self._update_task_running = False
                    self.stop_event.clear() # Reset stop event for the next task
                    print(f"[Launcher DEBUG] _update_task_running set to False.") # MOD5 Debug
                    self.log_to_gui("Launcher", f"更新任务 '{task_func.__name__}' 完成。", "info")
                    self.root.after(0, self._update_ui_state)
                    print(f"[Launcher DEBUG] UI update scheduled after task completion.") # MOD5 Debug

            except queue.Empty:
                # When queue is empty and stop_event is set, exit the worker loop
                if self.stop_event.is_set():
                    print("[Launcher INFO] Update worker thread received stop signal and queue is empty, exiting.")
                    break
                # If queue is empty but stop_event is not set, just continue waiting (loop naturally handles timeout)
                continue
            except Exception as e:
                print(f"[Launcher CRITICAL] Error in update task worker loop: {e}", exc_info=True)
                self._update_task_running = False
                self.stop_event.clear()
                # Attempt to mark task done if it was retrieved, even if it failed
                try:
                    if task_func: # Check if task_func was successfully retrieved before error
                        self.update_task_queue.task_done()
                except ValueError:
                    pass # Task might not have been put correctly or state is inconsistent

                self.root.after(0, self._update_ui_state) # Try to update UI state
                # Avoid tight loop on persistent errors
                time.sleep(1)


    # --- Queueing Methods for UI actions ---
    def _queue_main_body_refresh(self):
        """Queues the main body version refresh task."""
        # MOD2: Check if modal is open
        if self._node_history_modal_window and self._node_history_modal_window.winfo_exists():
             messagebox.showwarning("操作进行中", "请先关闭节点版本历史弹窗。", parent=self.root)
             return
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中...", "warn")
             return
        if not self._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=True):
             return

        self.log_to_gui("Launcher", "将刷新本体版本任务添加到队列...", "info")
        self.update_task_queue.put((self.refresh_main_body_versions, [], {}))
        self.root.after(0, self._update_ui_state)

    def _queue_main_body_activation(self):
        """Queues the main body version activation task."""
        # MOD2: Check if modal is open
        if self._node_history_modal_window and self._node_history_modal_window.winfo_exists():
             messagebox.showwarning("操作进行中", "请先关闭节点版本历史弹窗。", parent=self.root)
             return
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中...", "warn")
             return

        selected_item = self.main_body_tree.focus()
        if not selected_item:
            messagebox.showwarning("未选择版本", "请从列表中选择一个要激活的本体版本。", parent=self.root)
            return

        version_data = self.main_body_tree.item(selected_item, 'values')
        if not version_data or len(version_data) < 4:
             self.log_to_gui("Update", "无法获取选中的本体版本数据。", "error")
             return

        selected_commit_id_short = version_data[1] # Short ID for display/lookup
        selected_version_display = version_data[0]
        full_commit_id = None

        # Find the full commit ID from the stored data
        for ver_data in self.remote_main_body_versions:
            commit_id_str = ver_data.get('commit_id')
            if isinstance(commit_id_str, str) and commit_id_str.startswith(selected_commit_id_short):
                 full_commit_id = ver_data["commit_id"]
                 break

        if not full_commit_id:
             # If not found in cached data, try getting full ID from treeview data (less reliable)
             # Or, rely on git checkout to resolve the short ID (git checkout works with short IDs)
             # Let's pass the short ID to the task and let Git resolve it.
             full_commit_id = selected_commit_id_short # Use short ID as the target ref for git

             self.log_to_gui("Update", f"无法在缓存中找到 '{selected_commit_id_short}' 的完整ID，将尝试使用短ID激活。", "warn")


        if not self._validate_paths_for_execution(check_comfyui=True, check_git=True, show_error=True):
             return
        comfyui_dir = self.comfyui_dir_var.get()
        if not comfyui_dir or not os.path.isdir(os.path.join(comfyui_dir, ".git")): # Re-check existence
             messagebox.showerror("Git 仓库错误", f"ComfyUI 安装目录不是一个有效的 Git 仓库:\n{comfyui_dir}", parent=self.root)
             return

        # MOD2: Check if ComfyUI is running before allowing main body activation
        if self._is_comfyui_running() or self.comfyui_externally_detected:
             messagebox.showwarning("服务运行中", "请先停止 ComfyUI 后台服务，再进行本体版本切换。", parent=self.root)
             return


        confirm = messagebox.askyesno("确认激活", f"确定要下载并覆盖安装本体版本 '{selected_version_display}' (提交ID: {full_commit_id[:8]}) 吗？\n此操作会修改 '{comfyui_dir}' 目录。\n\n警告: 可能导致节点不兼容！\n确认前请确保 ComfyUI 已停止运行。", parent=self.root) # Added warning about ComfyUI state
        if not confirm:
            return

        self.log_to_gui("Launcher", f"将激活本体版本 '{full_commit_id[:8]}' 任务添加到队列...", "info")
        self.update_task_queue.put((self._activate_main_body_version_task, [comfyui_dir, full_commit_id], {})) # Pass target ID
        self.root.after(0, self._update_ui_state)

    def _queue_node_list_refresh(self):
        """Queues the node list refresh task."""
        # MOD2: Check if modal is open
        if self._node_history_modal_window and self._node_history_modal_window.winfo_exists():
             messagebox.showwarning("操作进行中", "请先关闭节点版本历史弹窗。", parent=self.root)
             return
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中...", "warn")
             return
        self.log_to_gui("Launcher", "将刷新节点列表任务添加到队列...", "info")
        self.update_task_queue.put((self.refresh_node_list, [], {}))
        self.root.after(0, self._update_ui_state)

    # MOD2: Modified command for '切换版本' button
    def _queue_node_switch_or_show_history(self):
        """Handles click on '切换版本' button: shows history modal for installed git nodes, queues install for others."""
        # MOD2: Prevent multiple modals
        if self._node_history_modal_window and self._node_history_modal_window.winfo_exists():
             messagebox.showwarning("操作进行中", "节点版本历史弹窗已打开。", parent=self.root)
             return

        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中...", "warn")
             return

        selected_item = self.nodes_tree.focus()
        if not selected_item:
            messagebox.showwarning("未选择节点", "请从列表中选择一个要操作的节点。", parent=self.root)
            return

        node_data = self.nodes_tree.item(selected_item, 'values')
        if not node_data or len(node_data) < 5:
             self.log_to_gui("Update", "无法获取选中的节点数据。", "error")
             return

        node_name = node_data[0]
        node_status = node_data[1]
        repo_info = node_data[3] # Remote info string
        repo_url = node_data[4] # Repo URL

        if not self._validate_paths_for_execution(check_comfyui=True, check_git=True, show_error=True):
             return
        if not self.comfyui_nodes_dir or not os.path.isdir(self.comfyui_nodes_dir):
             messagebox.showerror("目录错误", f"ComfyUI custom_nodes 目录未找到或无效:\n{self.comfyui_nodes_dir}", parent=self.root)
             return

        node_install_path = os.path.normpath(os.path.join(self.comfyui_nodes_dir, node_name))
        # Check if installed AND is a git repository
        is_installed_and_git = os.path.isdir(node_install_path) and os.path.isdir(os.path.join(node_install_path, ".git"))

        # MOD2: Logic split - show history modal for installed git nodes, install for others
        if is_installed_and_git:
             # MOD2: Check if ComfyUI is running before allowing git operations on node
             if self._is_comfyui_running() or self.comfyui_externally_detected:
                  messagebox.showwarning("服务运行中", "请先停止 ComfyUI 后台服务，再进行节点版本切换。", parent=self.root)
                  return

             # --- MOD1: Defer history fetch ---
             self.log_to_gui("Launcher", f"将获取节点 '{node_name}' 版本历史任务添加到队列...", "info")
             # Pass node name and path to the fetch task
             self.update_task_queue.put((self._node_history_fetch_task, [node_name, node_install_path], {}))
             # The _node_history_fetch_task will call _show_node_history_modal upon completion
        else:
             if not repo_url or repo_url in ("本地安装，无Git信息", "无法获取远程 URL", "本地安装", "N/A", "无远程仓库"):
                 messagebox.showerror("节点信息缺失", f"节点 '{node_name}' 无有效的仓库地址，无法进行版本切换或安装。", parent=self.root)
                 return
             # MOD2: Check if ComfyUI is running before allowing git operations on node
             if self._is_comfyui_running() or self.comfyui_externally_detected:
                  messagebox.showwarning("服务运行中", "请先停止 ComfyUI 后台服务，再进行节点安装。", parent=self.root)
                  return

             target_ref_for_install = "main" # Default branch (can be overridden)
             # Try to infer target reference (branch/tag) from online config info if available
             found_online_node = next((n for n in self.all_known_nodes if n.get("name","").lower() == node_name.lower()), None)
             if found_online_node:
                  potential_ref = found_online_node.get("reference") or found_online_node.get("branch")
                  if potential_ref:
                       target_ref_for_install = potential_ref
                       self.log_to_gui("Update", f"从在线配置获取到目标引用: {target_ref_for_install}", "info")
             elif repo_info and not repo_info.startswith("信息获取失败"):
                 # Fallback to parsing the repo_info string if online config wasn't used or failed
                 if "在线目标:" in repo_info:
                      potential_ref = repo_info.split("在线目标:", 1)[-1].strip()
                      if potential_ref:
                          target_ref_for_install = potential_ref
                 # Attempt to parse branch name from repo_info like "branch (commit)"
                 elif '(' in repo_info and ')' in repo_info:
                     parts = repo_info.split('(')
                     potential_ref = parts[0].strip()
                     if potential_ref:
                         target_ref_for_install = potential_ref


             confirm_msg = f"确定要安装节点 '{node_name}' 吗？\n" \
                           f"仓库地址: {repo_url}\n" \
                           f"目标引用/分支: {target_ref_for_install}\n" \
                           f"目标目录: {node_install_path}\n\n" \
                           f"确认前请确保 ComfyUI 已停止运行。" # Reiterated warning
             confirm = messagebox.askyesno("确认安装", confirm_msg, parent=self.root)
             if not confirm:
                 return

             self.log_to_gui("Launcher", f"将安装节点 '{node_name}' (目标引用: {target_ref_for_install})任务添加到队列...", "info")
             self.update_task_queue.put((self._install_node_task, [node_name, node_install_path, repo_url, target_ref_for_install], {}))

        self.root.after(0, self._update_ui_state)


    def _queue_all_nodes_update(self):
        """Queues the task to update all installed git nodes."""
        # MOD2: Check if modal is open
        if self._node_history_modal_window and self._node_history_modal_window.winfo_exists():
             messagebox.showwarning("操作进行中", "请先关闭节点版本历史弹窗。", parent=self.root)
             return
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中...", "warn")
             return
        if not self._validate_paths_for_execution(check_comfyui=True, check_git=True, show_error=True):
             return
        if not self.comfyui_nodes_dir or not os.path.isdir(self.comfyui_nodes_dir):
             messagebox.showerror("目录错误", f"ComfyUI custom_nodes 目录未找到或无效:\n{self.comfyui_nodes_dir}", parent=self.root)
             return

        # MOD2: Check if ComfyUI is running before allowing git operations on nodes
        if self._is_comfyui_running() or self.comfyui_externally_detected:
             messagebox.showwarning("服务运行中", "请先停止 ComfyUI 后台服务，再进行全部节点更新。", parent=self.root)
             return


        # Filter for installed git nodes with a known remote branch
        nodes_to_update = [
            node for node in self.local_nodes_only
            if node.get("is_git") and node.get("repo_url") and node.get("repo_url") not in ("本地安装，无Git信息", "无法获取远程 URL", "本地安装", "N/A", "无远程仓库") and node.get("remote_branch") and node.get("remote_branch") != "N/A" # Ensure remote branch is known
        ]
        if not nodes_to_update:
             messagebox.showinfo("无节点可更新", "没有找到可更新的已安装 Git 节点（具有有效的远程跟踪分支）。", parent=self.root)
             return

        confirm = messagebox.askyesno("确认更新全部", f"确定要尝试更新 {len(nodes_to_update)} 个已安装节点吗？\n此操作将执行 Git pull。\n\n警告：可能丢失本地修改！\n确认前请确保 ComfyUI 已停止运行。", parent=self.root) # Reiterated warning
        if not confirm:
            return

        self.log_to_gui("Launcher", f"将更新全部节点任务添加到队列 (共 {len(nodes_to_update)} 个)...", "info")
        self.update_task_queue.put((self._update_all_nodes_task, [nodes_to_update], {}))
        self.root.after(0, self._update_ui_state)

    def _queue_node_uninstall(self):
        """Queues the node uninstall task."""
        # MOD2: Check if modal is open
        if self._node_history_modal_window and self._node_history_modal_window.winfo_exists():
             messagebox.showwarning("操作进行中", "请先关闭节点版本历史弹窗。", parent=self.root)
             return
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中...", "warn")
             return

        selected_item = self.nodes_tree.focus()
        if not selected_item:
            messagebox.showwarning("未选择节点", "请从列表中选择一个要卸载的节点。", parent=self.root)
            return
        node_data = self.nodes_tree.item(selected_item, 'values')
        if not node_data or len(node_data) < 5:
             self.log_to_gui("Update", "无法获取选中的节点数据。", "error")
             return

        node_name = node_data[0]
        node_status = node_data[1]

        if node_status != "已安装":
             messagebox.showwarning("节点未安装", f"节点 '{node_name}' 未安装。", parent=self.root)
             return

        if not self.comfyui_nodes_dir or not os.path.isdir(self.comfyui_nodes_dir):
             messagebox.showerror("目录错误", f"ComfyUI custom_nodes 目录未找到或无效:\n{self.comfyui_nodes_dir}", parent=self.root)
             return
        node_install_path = os.path.normpath(os.path.join(self.comfyui_nodes_dir, node_name))
        if not os.path.isdir(node_install_path):
             messagebox.showerror("目录错误", f"节点目录不存在或无效:\n{node_install_path}", parent=self.root)
             self.root.after(0, self._queue_node_list_refresh) # Refresh list if directory is missing
             return

        # MOD2: Check if ComfyUI is running before allowing uninstall
        if self._is_comfyui_running() or self.comfyui_externally_detected:
             messagebox.showwarning("服务运行中", "请先停止 ComfyUI 后台服务，再进行节点卸载。", parent=self.root)
             return


        confirm = messagebox.askyesno(
             "确认卸载节点",
             f"确定要永久删除节点 '{node_name}' 及其目录 '{node_install_path}' 吗？\n此操作不可撤销。\n\n确认前请确保 ComfyUI 已停止运行。", # Reiterated warning
             parent=self.root)
        if not confirm:
            return

        self.log_to_gui("Launcher", f"将卸载节点 '{node_name}' task添加到队列...", "info") # Corrected to 'task'
        self.update_task_queue.put((self._node_uninstall_task, [node_name, node_install_path], {}))
        self.root.after(0, self._update_ui_state)


    # --- Initial Data Loading Task ---
    def start_initial_data_load(self):
         """Starts the initial data loading tasks in a background thread."""
         if self._is_update_task_running():
              print("[Launcher INFO] Initial data load skipped, an update task is already running.")
              return
         # MOD2: Prevent initial load if modal is open (unlikely but defensive)
         if self._node_history_modal_window and self._node_history_modal_window.winfo_exists():
              print("[Launcher INFO] Initial data load skipped, modal window is open.")
              return


         self.log_to_gui("Launcher", "开始加载更新管理数据...", "info")
         self.update_task_queue.put((self._run_initial_background_tasks, [], {}))
         self.root.after(0, self._update_ui_state) # Show busy state


    def _run_initial_background_tasks(self):
         """Executes the initial data loading tasks. Runs in worker thread."""
         # Check for stop event at the very beginning
         if self.stop_event.is_set():
             self.log_to_gui("Launcher", "后台数据加载任务已取消 (停止信号)。", "warn")
             return

         self.log_to_gui("Launcher", "执行后台数据加载 (本体版本和节点列表)...", "info")
         git_path_ok = self._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=False)
         if not git_path_ok:
             self.log_to_gui("Launcher", "Git 路径无效，数据加载将受限。", "warn")

         # Refresh main body versions first
         self.refresh_main_body_versions()

         if self.stop_event.is_set():
              self.log_to_gui("Launcher", "后台数据加载任务已取消 (停止信号)。", "warn")
              return

         # Then refresh node list
         self.refresh_node_list()

         if not self.stop_event.is_set():
             self.log_to_gui("Launcher", "后台数据加载完成。", "info")


    # --- Update Management Tasks (Executed in Worker Thread) ---

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
        current_local_commit = None
        if is_git_repo:
             stdout_id_full, _, rc_full = self._run_git_command(["rev-parse", "HEAD"], cwd=comfyui_dir, timeout=10, log_output=False)
             if rc_full == 0 and stdout_id_full:
                  current_local_commit = stdout_id_full.strip() # Store full ID
                  stdout_id_short = current_local_commit[:8] # Display short ID
                  local_version_display = f"本地 Commit: {stdout_id_short}"

                  # Try to find a symbolic ref (branch/tag) if HEAD is not detached
                  stdout_sym_ref, _, rc_sym_ref = self._run_git_command(["symbolic-ref", "-q", "--short", "HEAD"], cwd=comfyui_dir, timeout=5, log_output=False)
                  if rc_sym_ref == 0 and stdout_sym_ref:
                       local_version_display = f"本地 Branch: {stdout_sym_ref.strip()} ({stdout_id_short})"
                  else: # If detached HEAD, try describe
                       stdout_desc, _, rc_desc = self._run_git_command(["describe", "--all", "--long", "--always"], cwd=comfyui_dir, timeout=10, log_output=False)
                       if rc_desc == 0 and stdout_desc:
                            local_version_display = f"本地: {stdout_desc.strip()}"

             else:
                  local_version_display = "读取本地版本失败"
                  self.log_to_gui("Update", "无法获取本地本体版本信息。", "warn")
        else:
             local_version_display = "非 Git 仓库或路径无效"

        self.root.after(0, lambda lv=local_version_display: self.current_main_body_version_var.set(lv))

        if self.stop_event.is_set():
            return

        # Fetch Remote Versions
        all_versions = []
        if is_git_repo and main_repo_url:
             self.log_to_gui("Update", f"尝试从 {main_repo_url} 刷新远程版本列表...", "info")
             # Ensure origin remote exists and points to the correct URL
             stdout_get_url, _, rc_get_url = self._run_git_command(["remote", "get-url", "origin"], cwd=comfyui_dir, timeout=10, log_output=False) # No logging here
             current_url = stdout_get_url.strip() if rc_get_url == 0 else None

             if not current_url:
                  self.log_to_gui("Update", f"远程 'origin' 不存在，尝试添加...", "info")
                  _, stderr_add, rc_add = self._run_git_command(["remote", "add", "origin", main_repo_url], cwd=comfyui_dir, timeout=15)
                  if rc_add != 0:
                      self.log_to_gui("Update", f"添加远程 'origin' 失败: {stderr_add.strip()}", "error")
             elif current_url != main_repo_url:
                  self.log_to_gui("Update", f"远程 'origin' URL 不匹配 ({current_url}), 尝试设置新 URL...", "warn")
                  _, stderr_set, rc_set = self._run_git_command(["remote", "set-url", "origin", main_repo_url], cwd=comfyui_dir, timeout=15)
                  if rc_set != 0:
                      self.log_to_gui("Update", f"设置远程 'origin' URL 失败: {stderr_set.strip()}", "error")

             if self.stop_event.is_set():
                 return

             self.log_to_gui("Update", "执行 Git fetch origin --prune --tags -f...", "info")
             _, stderr_fetch, rc_fetch = self._run_git_command(["fetch", "origin", "--prune", "--tags", "-f"], cwd=comfyui_dir, timeout=180)
             if rc_fetch != 0:
                  self.log_to_gui("Update", f"Git fetch 失败: {stderr_fetch.strip()}", "error")
                  self.root.after(0, lambda: self.main_body_tree.insert("", tk.END, values=("获取失败", "", "", "无法获取远程版本信息")))
                  return

             if self.stop_event.is_set():
                 return

             # Get remote branches and tags with commit hash, date, and subject
             # Using separate commands for clarity and easier parsing
             # Format: %(refname:short) %(objectname) %(committerdate:iso-strict) %(contents:subject)

             # Get remote branches
             self.log_to_gui("Update", "获取远程分支信息...", "info")
             # Added --no-merges to filter out merge commits from the log output used for description
             branches_output, _, _ = self._run_git_command(
                  ["for-each-ref", "refs/remotes/origin/", "--sort=-committerdate", "--format=%(refname:short) %(objectname) %(committerdate:iso-strict) %(contents:subject)"],
                  cwd=comfyui_dir, timeout=60 )
             for line in branches_output.splitlines():
                  parts = line.split(' ', 3) # Split into at most 4 parts
                  if len(parts) >= 3: # Subject might be empty or multi-word
                       refname, commit_id, date_iso = parts[0].replace("origin/", ""), parts[1], parts[2]
                       description = parts[3].strip() if len(parts) == 4 else ""
                       if "HEAD->" not in refname: # Exclude HEAD alias
                            all_versions.append({"type": "branch", "name": refname, "commit_id": commit_id, "date_iso": date_iso, "description": description})
                  elif len(parts) == 2: # Handle missing date/subject
                        refname, commit_id = parts[0].replace("origin/", ""), parts[1]
                        if "HEAD->" not in refname:
                             all_versions.append({"type": "branch", "name": refname, "commit_id": commit_id, "date_iso": "", "description": ""})
                  # Ignore lines with insufficient parts


             if self.stop_event.is_set():
                 return

             # Get tags
             self.log_to_gui("Update", "获取标签信息...", "info")
             tags_output, _, _ = self._run_git_command(
                  ["for-each-ref", "refs/tags/", "--sort=-taggerdate", "--format=%(refname:short) %(objectname) %(taggerdate:iso-strict) %(contents:subject)"],
                  cwd=comfyui_dir, timeout=60 )
             for line in tags_output.splitlines():
                  parts = line.split(' ', 3) # Split into at most 4 parts
                  if len(parts) >= 3: # Subject might be empty or multi-word
                       refname, commit_id, date_iso = parts[0].replace("refs/tags/", ""), parts[1], parts[2]
                       description = parts[3].strip() if len(parts) == 4 else ""
                       all_versions.append({"type": "tag", "name": refname, "commit_id": commit_id, "date_iso": date_iso, "description": description})
                  elif len(parts) == 2: # Handle missing date/subject
                       refname, commit_id = parts[0].replace("refs/tags/", ""), parts[1]
                       all_versions.append({"type": "tag", "name": refname, "commit_id": commit_id, "date_iso": "", "description": ""})
                  # Ignore lines with insufficient parts


             # Get current local commit if it's detached HEAD or doesn't match any remote branch/tag fetched
             if current_local_commit:
                 # Check if this exact commit hash is already in the list (from remote branches/tags)
                 is_local_listed = any(v.get('commit_id', '') == current_local_commit for v in all_versions)
                 if not is_local_listed:
                     self.log_to_gui("Update", "获取当前本地 Commit 信息...", "info")
                     # Get date and subject for current HEAD
                     head_date_stdout, _, rc_head_date = self._run_git_command(["log", "-1", "--format=%ci", "HEAD"], cwd=comfyui_dir, timeout=5, log_output=False)
                     head_subject_stdout, _, rc_head_subject = self._run_git_command(["log", "-1", "--format=%s", "HEAD"], cwd=comfyui_dir, timeout=5, log_output=False)

                     head_date_iso = head_date_stdout.strip() if rc_head_date == 0 else None
                     head_description = head_subject_stdout.strip() if rc_head_subject == 0 else "当前工作目录"

                     # Try to parse date, fallback to now if failed
                     date_obj = _parse_iso_date_for_sort(head_date_iso)
                     final_date_iso = date_obj.isoformat() if date_obj else datetime.now(timezone.utc).isoformat()

                     # Determine type (detached HEAD or local branch not tracking remote)
                     head_sym_ref_out, _, rc_head_sym_ref = self._run_git_command(["symbolic-ref", "-q", "--short", "HEAD"], cwd=comfyui_dir, timeout=2, log_output=False)
                     head_type = "commit (HEAD)" if rc_head_sym_ref != 0 else "branch (local)"
                     head_name = head_sym_ref_out.strip() if head_type == "branch (local)" else f"Detached at {current_local_commit[:8]}"


                     all_versions.append({"type": head_type, "name": head_name, "commit_id": current_local_commit, "date_iso": final_date_iso, "description": head_description})
                     self.log_to_gui("Update", f"添加当前本地 HEAD ({current_local_commit[:8]}) 到列表。", "info")
                 else:
                     self.log_to_gui("Update", "当前本地 Commit 与远程已同步或已在列表中。", "info")


             # Sort the combined list (MOD1: Using custom comparison)
             all_versions.sort(key=cmp_to_key(_compare_versions_for_sort))

        else:
             self.log_to_gui("Update", "无法获取远程版本信息 (非Git仓库或缺少URL)。", "warn")
             self.root.after(0, lambda: self.main_body_tree.insert("", tk.END, values=("无远程信息", "", "", "")))

        self.remote_main_body_versions = all_versions # Store for potential future use (like showing more detail?)

        # Populate the Treeview (MOD1: Handling "日期解析失败" and order)
        if not all_versions and is_git_repo and main_repo_url:
             self.log_to_gui("Update", "未从远程仓库获取到版本信息。", "warn")
             self.root.after(0, lambda: self.main_body_tree.insert("", tk.END, values=("无远程版本", "", "", "")))
        else:
             for ver_data in all_versions:
                 if self.stop_event.is_set():
                     break
                 # Ensure keys exist with default empty strings if missing
                 ver_data.setdefault('type', '未知')
                 ver_data.setdefault('name', 'N/A')
                 ver_data.setdefault('commit_id', 'N/A')
                 ver_data.setdefault('date_iso', '')
                 ver_data.setdefault('description', 'N/A')

                 version_display = f"{ver_data['type']} / {ver_data['name']}"
                 commit_display = ver_data.get("commit_id", "N/A")[:8] # Display short ID

                 date_obj = _parse_iso_date_for_sort(ver_data['date_iso'])
                 date_display = date_obj.strftime('%Y-%m-%d') if date_obj else ("解析失败" if ver_data['date_iso'] else "无日期") # Display "日期解析失败" or "无日期"

                 description_display = ver_data['description']

                 # Check if this version is the current local commit (using full ID)
                 tags = ('highlight',) if current_local_commit and ver_data.get('commit_id') == current_local_commit else ()


                 self.root.after(0, lambda v=(version_display, commit_display, date_display, description_display), t=tags: self.main_body_tree.insert("", tk.END, values=v, tags=t))


        self.log_to_gui("Update", f"本体版本列表刷新完成。", "info")


    def _activate_main_body_version_task(self, comfyui_dir, target_ref): # Renamed target_commit_id to target_ref
        """Task to execute git commands for activating main body version. Runs in worker thread."""
        if self.stop_event.is_set():
            return
        self.log_to_gui("Update", f"正在激活本体版本 (引用: {target_ref[:8]})...", "info") # Use short ref for logging

        try:
            # 1. Fetch latest changes if target_ref is not a full SHA or known local ref
            # A simple approach is to always try fetching the specific ref if it looks like a remote branch or tag
            # or if git checkout fails initially. A more robust way is to check if the ref is already local.
            # Let's assume `target_ref` *might* need a fetch first if it's a remote branch/tag name.
            # We can try 'git fetch origin <target_ref>' which is safe if it's already fetched.
            # However, `git checkout <ref>` itself can often work with remote branch names like `origin/main`
            # if `git fetch origin` has been run recently (which refresh_main_body_versions does).
            # Let's trust `git checkout` to handle refs that exist locally (either via fetch or already local).
            # If it fails, we'll report the error.

            if self.stop_event.is_set():
                raise threading.ThreadExit

            # 2. Reset local changes and checkout target commit/ref
            stdout_status, _, _ = self._run_git_command(["status", "--porcelain"], cwd=comfyui_dir, timeout=10, log_output=False) # No logging status unless needed
            if stdout_status.strip():
                 self.log_to_gui("Update", "检测到本体目录存在未提交的本地修改，将通过 reset --hard 覆盖。", "warn")

            # Use checkout --force to handle local changes and ensure the target ref is checked out
            self.log_to_gui("Update", f"执行 Git checkout --force {target_ref[:8]}...", "info")
            _, stderr_checkout, rc_checkout = self._run_git_command(["checkout", "--force", target_ref], cwd=comfyui_dir, timeout=60)
            if rc_checkout != 0:
                # If checkout fails, try reset --hard as a fallback? No, checkout is the standard way.
                # The most likely reason is the ref doesn't exist *locally* after fetch.
                # Maybe try one more fetch of the specific ref? Or just report error.
                # Given refresh_main_body_versions *just* ran fetch --prune --tags -f,
                # if the ref exists remotely, it should be local. Let's just fail clearly.
                raise Exception(f"Git checkout --force 失败: {stderr_checkout.strip()}")

            self.log_to_gui("Update", f"Git checkout 完成 (引用: {target_ref[:8]}).", "info")

            if self.stop_event.is_set():
                raise threading.ThreadExit

            # 3. Update submodules
            if os.path.exists(os.path.join(comfyui_dir, ".gitmodules")):
                 self.log_to_gui("Update", "执行 Git submodule update...", "info")
                 # Use --init and --recursive --force together
                 _, stderr_sub, rc_sub = self._run_git_command(["submodule", "update", "--init", "--recursive", "--force"], cwd=comfyui_dir, timeout=180)
                 if rc_sub != 0:
                     self.log_to_gui("Update", f"Git submodule update 失败: {stderr_sub.strip()}", "warn") # Warn only
            if self.stop_event.is_set():
                raise threading.ThreadExit

            # 4. Re-install Python dependencies
            python_exe = self.python_exe_var.get()
            requirements_path = os.path.join(comfyui_dir, "requirements.txt")
            if python_exe and os.path.isfile(python_exe) and os.path.isfile(requirements_path):
                 self.log_to_gui("Update", "执行 pip 安装依赖...", "info")
                 pip_cmd_base = [python_exe, "-m", "pip", "install", "-r", requirements_path, "--upgrade"]
                 # Conditional extra index URLs based on platform/needs (adjust if needed)
                 pip_cmd_extras = []
                 # Example: Add cu118 or cu121 index based on detected CUDA or user preference
                 # For simplicity, keep the current approach of adding both as extras
                 pip_cmd_extras.extend(["--extra-index-url", "https://download.pytorch.org/whl/cu118", "--extra-index-url", "https://download.pytorch.org/whl/cu121"])

                 pip_cmd = pip_cmd_base + pip_cmd_extras
                 is_venv = sys.prefix != sys.base_prefix
                 if platform.system() != "Windows" and not is_venv:
                      # Only add --user if not in a venv and not Windows (user installs are standard on Linux/macOS outside venv)
                      # On Windows, --user is generally not recommended for venv/portable envs
                      # Check if python_exe is within a venv/portable path.
                      # A simple check: if the python_exe is NOT inside sys.base_prefix
                      if sys.base_prefix != sys.prefix: # Are we NOT in the *system* base environment?
                           # Then we are likely in a venv or similar managed environment
                           pass # Don't add --user
                      else:
                           # Likely system installation on Linux/macOS
                           pip_cmd.append("--user")
                           self.log_to_gui("Update", "非虚拟环境 (系统安装)，使用 --user 选项安装依赖。", "warn")


                 # Added --no-cache-dir to save space, --compile could speed up subsequent imports
                 pip_cmd.extend(["--no-cache-dir"])

                 _, stderr_pip, rc_pip = self._run_git_command(pip_cmd, cwd=comfyui_dir, timeout=600) # Longer timeout for pip
                 if rc_pip != 0:
                      self.log_to_gui("Update", f"Pip 安装依赖失败: {stderr_pip.strip()}", "error")
                      self.root.after(0, lambda: messagebox.showwarning("依赖安装失败", "Python 依赖安装失败，新版本可能无法正常工作。\n请查看日志获取详情。", parent=self.root))
                 else:
                      self.log_to_gui("Update", "Pip 安装依赖完成。", "info")
            else:
                 self.log_to_gui("Update", "Python 或 requirements.txt 无效，跳过依赖安装。", "warn")

            # Success
            self.log_to_gui("Update", f"本体版本激活流程完成 (引用: {target_ref[:8]})。", "info")
            self.root.after(0, lambda ref=target_ref[:8]: messagebox.showinfo("激活完成", f"本体版本已激活到: {ref}", parent=self.root))

        except threading.ThreadExit:
             self.log_to_gui("Update", "本体版本激活任务已取消。", "warn")
        except Exception as e:
            error_msg = f"本体版本激活流程失败: {e}"
            self.log_to_gui("Update", error_msg, "error")
            self.root.after(0, lambda msg=str(e): messagebox.showerror("激活失败", msg, parent=self.root))
        finally:
            # Always refresh the list after attempting activation
            self.root.after(0, self._queue_main_body_refresh)


    def refresh_node_list(self):
        """Fetches and displays custom node list (local scan + online config), applying filter. Runs in worker thread."""
        if self.stop_event.is_set():
            return
        self.log_to_gui("Update", "刷新节点列表...", "info")

        node_config_url = self.node_config_url_var.get()
        comfyui_nodes_dir = self.comfyui_nodes_dir
        search_term_value = ""
        try:
            if hasattr(self, 'nodes_search_entry') and self.nodes_search_entry.winfo_exists():
                search_term_value = self.nodes_search_entry.get().strip().lower()
        except tk.TclError:
            pass # Handle widget not existing yet

        git_path_ok = self._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=False)
        is_nodes_dir_valid = comfyui_nodes_dir and os.path.isdir(comfyui_nodes_dir)

        # Clear existing list in GUI thread
        self.root.after(0, lambda: [self.nodes_tree.delete(item) for item in self.nodes_tree.get_children()])
        self.local_nodes_only = [] # Reset local node cache

        # --- Scan Local custom_nodes directory ---
        if is_nodes_dir_valid:
             self.log_to_gui("Update", f"扫描本地 custom_nodes 目录: {comfyui_nodes_dir}...", "info")
             try:
                  # List directories first for better processing
                  item_names = sorted([d for d in os.listdir(comfyui_nodes_dir) if os.path.isdir(os.path.join(comfyui_nodes_dir, d))])
                  for item_name in item_names:
                       if self.stop_event.is_set():
                           raise threading.ThreadExit

                       item_path = os.path.join(comfyui_nodes_dir, item_name)
                       node_info = {"name": item_name, "status": "已安装", "local_id": "N/A", "local_commit_full": None, "repo_info": "N/A", "repo_url": "本地安装", "is_git": False, "remote_branch": None}

                       if git_path_ok and os.path.isdir(os.path.join(item_path, ".git")):
                            node_info["is_git"] = True

                            # Get Local Short ID (8 chars) and Full ID
                            stdout_id_full, _, rc_id_full = self._run_git_command(["rev-parse", "HEAD"], cwd=item_path, timeout=5, log_output=False)
                            node_info["local_commit_full"] = stdout_id_full.strip() if rc_id_full == 0 and stdout_id_full else None
                            node_info["local_id"] = node_info["local_commit_full"][:8] if node_info["local_commit_full"] else "获取失败"


                            # Get Remote URL
                            stdout_url, _, rc_url = self._run_git_command(["config", "--get", "remote.origin.url"], cwd=item_path, timeout=5, log_output=False)
                            node_info["repo_url"] = stdout_url.strip() if rc_url == 0 and stdout_url and stdout_url.strip().endswith(".git") else "无远程仓库" # Ensure it looks like a URL

                            # Get Upstream Branch and Remote Info
                            # Use git rev-parse --abbrev-ref --symbolic-full-name @{u} to get tracking branch
                            upstream_stdout, _, rc_upstream = self._run_git_command(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd=item_path, timeout=5, log_output=False)
                            upstream_ref = upstream_stdout.strip() if rc_upstream == 0 and upstream_stdout else None

                            repo_info_display = "无远程跟踪"
                            if upstream_ref and upstream_ref.startswith("origin/"):
                                remote_branch_name = upstream_ref.replace("origin/", "")
                                node_info["remote_branch"] = remote_branch_name # Store for update all

                                # Get remote commit ID and date for the tracking branch
                                # Use git log --format to get commit hash (%H), committer date (%ci), and subject (%s)
                                log_cmd = ["log", "-1", "--format=%H %ci %s", upstream_ref] # Use ISO date, include subject
                                stdout_log, _, rc_log = self._run_git_command(log_cmd, cwd=item_path, timeout=10, log_output=False)
                                if rc_log == 0 and stdout_log:
                                     log_parts = stdout_log.strip().split(' ', 2) # Split into hash, date, rest (subject)
                                     if len(log_parts) >= 2: # Need at least hash and date
                                          full_commit_id_remote = log_parts[0]
                                          date_iso = log_parts[1]
                                          subject = log_parts[2].strip() if len(log_parts) == 3 else ""

                                          remote_commit_id_short = full_commit_id_remote[:8]
                                          date_obj = _parse_iso_date_for_sort(date_iso)
                                          remote_commit_date = date_obj.strftime('%Y-%m-%d') if date_obj else "未知日期"
                                          # Display branch, short commit, and date
                                          repo_info_display = f"{remote_branch_name} {remote_commit_id_short} ({remote_commit_date})"
                                          # Could add subject to tooltip later if needed
                                     else:
                                          repo_info_display = f"{remote_branch_name} (日志解析失败)"
                                else:
                                     repo_info_display = f"{remote_branch_name} (信息获取失败)"
                            elif upstream_ref: # Tracks something else?
                                 repo_info_display = f"跟踪: {upstream_ref}"

                            node_info["repo_info"] = repo_info_display

                       self.local_nodes_only.append(node_info)

             except threading.ThreadExit:
                 return
             except Exception as e:
                  self.log_to_gui("Update", f"扫描本地 custom_nodes 目录时出错: {e}", "error", target_override="Launcher")
                  self.root.after(0, lambda: self.nodes_tree.insert("", tk.END, values=("扫描失败", "错误", "N/A", "扫描本地目录时出错", "N/A")))
        else: # Nodes dir not valid
             self.log_to_gui("Update", f"ComfyUI custom_nodes 目录无效，跳过本地扫描。", "warn")
             self.root.after(0, lambda: self.nodes_tree.insert("", tk.END, values=("本地目录无效", "错误", "N/A", "", "")))

        if self.stop_event.is_set():
            return

        # --- Fetching Online Config Data ---
        online_nodes_config = []
        if node_config_url:
            online_nodes_config = self._fetch_online_node_config() # Runs in this worker thread
        else:
            self.log_to_gui("Update", "节点配置地址未设置，跳过在线配置获取。", "warn")

        if self.stop_event.is_set():
            return

        # --- Combine local and online data ---
        local_node_dict_lower = {node['name'].lower(): node for node in self.local_nodes_only}
        combined_nodes_dict = {node['name'].lower(): node for node in self.local_nodes_only} # Start with local

        for online_node in online_nodes_config:
             if self.stop_event.is_set():
                 break
             try:
                 node_name = online_node.get('title') or online_node.get('name')
                 if not node_name:
                     continue
                 node_name_lower = node_name.lower()
                 # Find the first git URL in files list
                 repo_url = None
                 files = online_node.get('files', [])
                 if isinstance(files, list):
                      for file_entry in files:
                           if isinstance(file_entry, str) and file_entry.endswith(".git"):
                                repo_url = file_entry
                                break
                 if not repo_url:
                     continue

                 target_ref = online_node.get('reference') or online_node.get('branch') or 'main'

                 if node_name_lower not in local_node_dict_lower:
                     # Only add online node if it's NOT already installed locally
                     online_repo_info_display = f"在线目标: {target_ref}"
                     combined_nodes_dict[node_name_lower] = {
                         "name": node_name, "status": "未安装", "local_id": "N/A", "local_commit_full": None,
                         "repo_info": online_repo_info_display, "repo_url": repo_url,
                         "is_git": True, # Assume online nodes are git repos
                         "remote_branch": target_ref # Store potential target ref
                     }
             except Exception as e:
                 print(f"[Launcher WARNING] Error processing online node entry: {online_node}. Error: {e}")
                 self.log_to_gui("Update", f"处理在线节点条目时出错: {e}", "warn")

        # Convert combined dict back to list and sort by name
        self.all_known_nodes = sorted(list(combined_nodes_dict.values()), key=lambda x: x.get('name', '').lower())

        if self.stop_event.is_set():
            return

        # --- Apply Filtering Logic ---
        filtered_nodes = []
        search_term_value = self.nodes_search_entry.get().strip().lower() # Re-get value in case it changed during fetch
        if search_term_value == "": # Empty search -> show local only
            filtered_nodes = sorted(self.local_nodes_only, key=lambda x: x.get('name', '').lower())
        else: # Search term present -> filter combined list
            filtered_nodes = [
                node for node in self.all_known_nodes
                if search_term_value in node.get('name', '').lower() or \
                   search_term_value in node.get('repo_url', '').lower() or \
                   search_term_value in node.get('status', '').lower()
            ]
            filtered_nodes.sort(key=lambda x: x.get('name', '').lower())

        # --- Populate Treeview ---
        if not filtered_nodes:
              display_message = "未找到匹配的节点" if search_term_value else "未找到本地节点"
              self.root.after(0, lambda msg=display_message: self.nodes_tree.insert("", tk.END, values=("", msg, "", "", "")))
        else:
            for node_data in filtered_nodes:
                 if self.stop_event.is_set():
                     break
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
         if not node_config_url:
             return []

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
        if self.stop_event.is_set():
            return
        self.log_to_gui("Update", f"开始更新全部节点 ({len(nodes_to_process)} 个)...", "info")
        updated_count = 0
        failed_nodes = []

        for index, node_info in enumerate(nodes_to_process):
             if self.stop_event.is_set():
                 break

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
                 # Ensure origin remote exists and points to the correct URL
                 stdout_get_url, _, rc_get_url = self._run_git_command(["remote", "get-url", "origin"], cwd=node_install_path, timeout=10, log_output=False)
                 current_url = stdout_get_url.strip() if rc_get_url == 0 else None
                 if not current_url:
                      self.log_to_gui("Update", f"节点 '{node_name}': 远程 'origin' 不存在，尝试添加...", "info")
                      _, stderr_add, rc_add = self._run_git_command(["remote", "add", "origin", repo_url], cwd=node_install_path, timeout=15)
                      if rc_add != 0:
                          self.log_to_gui("Update", f"节点 '{node_name}': 添加远程 'origin' 失败: {stderr_add.strip()}", "warn")
                 elif current_url != repo_url:
                      self.log_to_gui("Update", f"节点 '{node_name}': 远程 'origin' URL 不匹配 ({current_url}), 尝试设置新 URL...", "warn")
                      _, stderr_set, rc_set = self._run_git_command(["remote", "set-url", "origin", repo_url], cwd=node_install_path, timeout=15)
                      if rc_set != 0:
                          self.log_to_gui("Update", f"节点 '{node_name}': 设置远程 'origin' URL 失败: {stderr_set.strip()}", "warn")
                      else:
                          self.log_to_gui("Update", f"节点 '{node_name}': 远程 URL 已更新。", "info")


                 if self.stop_event.is_set():
                     raise threading.ThreadExit

                 stdout_status, _, _ = self._run_git_command(["status", "--porcelain"], cwd=node_install_path, timeout=10, log_output=False)
                 if stdout_status.strip():
                      self.log_to_gui("Update", f"跳过 '{node_name}': 存在未提交的本地修改。", "warn")
                      failed_nodes.append(f"{node_name} (存在本地修改)")
                      continue

                 # Fetch the remote branch specifically
                 self.log_to_gui("Update", f"[{index+1}/{len(nodes_to_process)}] 执行 Git fetch origin {remote_branch}...", "info")
                 _, stderr_fetch, rc_fetch = self._run_git_command(["fetch", "origin", remote_branch], cwd=node_install_path, timeout=60)
                 if rc_fetch != 0:
                      self.log_to_gui("Update", f"Git fetch 失败 for '{node_name}': {stderr_fetch.strip()}", "error")
                      failed_nodes.append(f"{node_name} (Fetch失败)")
                      continue

                 if self.stop_event.is_set():
                     raise threading.ThreadExit

                 # Compare local HEAD with remote tracking branch
                 local_commit_full, _, _ = self._run_git_command(["rev-parse", "HEAD"], cwd=node_install_path, timeout=5, log_output=False)
                 remote_commit_full, _, _ = self._run_git_command(["rev-parse", f"origin/{remote_branch}"], cwd=node_install_path, timeout=5, log_output=False)

                 if local_commit_full and remote_commit_full and local_commit_full.strip() == remote_commit_full.strip():
                     self.log_to_gui("Update", f"节点 '{node_name}' 已是最新版本。", "info")
                     continue

                 # Checkout the remote tracking branch, discarding local changes
                 self.log_to_gui("Update", f"[{index+1}/{len(nodes_to_process)}] 执行 Git checkout --force origin/{remote_branch} for '{node_name}'...", "info")
                 _, stderr_checkout, returncode_checkout = self._run_git_command(["checkout", "--force", f"origin/{remote_branch}"], cwd=node_install_path, timeout=60)
                 if returncode_checkout != 0:
                       self.log_to_gui("Update", f"Git checkout --force 失败 for '{node_name}': {stderr_checkout.strip()}", "error")
                       failed_nodes.append(f"{node_name} (Checkout失败)")
                       continue
                 self.log_to_gui("Update", f"Git checkout 完成 for '{node_name}'.", "info")

                 # At this point, HEAD is detached and points to origin/<branch>. To make it track the branch,
                 # we should optionally checkout the local branch again, or do a git pull.
                 # Git pull is effectively fetch + merge/rebase. Since we just did reset --hard,
                 # a simple `git pull origin <branch>` should work similarly to fetch + reset --hard.
                 # Let's stick to checkout as it explicitly puts the working tree into the desired state.
                 # To re-attach HEAD to the local branch if one exists with the same name as the remote tracking branch:
                 local_branch_exists_stdout, _, rc_local_branch = self._run_git_command(["rev-parse", "--verify", "--quiet", remote_branch], cwd=node_install_path, timeout=5, log_output=False)
                 if rc_local_branch == 0: # Local branch exists with the same name
                      self.log_to_gui("Update", f"节点 '{node_name}': 本地分支 '{remote_branch}' 存在，尝试切换回本地分支...", "info")
                      # Checkout the local branch, it should now point to the same commit as origin/<branch>
                      _, stderr_checkout_local, rc_checkout_local = self._run_git_command(["checkout", remote_branch], cwd=node_install_path, timeout=30)
                      if rc_checkout_local != 0:
                           self.log_to_gui("Update", f"节点 '{node_name}': 切换回本地分支 '{remote_branch}' 失败: {stderr_checkout_local.strip()}", "warn")
                      else:
                           self.log_to_gui("Update", f"节点 '{node_name}': 已切换回本地分支 '{remote_branch}'.", "info")
                 else:
                      self.log_to_gui("Update", f"节点 '{node_name}': 未找到本地分支 '{remote_branch}', 保持在 detached HEAD 状态。", "info")


                 if self.stop_event.is_set():
                     raise threading.ThreadExit

                 if os.path.exists(os.path.join(node_install_path, ".gitmodules")):
                      self.log_to_gui("Update", f"执行 Git submodule update for '{node_name}'...", "info")
                      _, stderr_sub, rc_sub = self._run_git_command(["submodule", "update", "--init", "--recursive", "--force"], cwd=node_install_path, timeout=180)
                      if rc_sub != 0:
                          self.log_to_gui("Update", f"Git submodule update 失败: {stderr_sub.strip()}", "warn")
                 python_exe = self.python_exe_var.get()
                 requirements_path = os.path.join(node_install_path, "requirements.txt")
                 if python_exe and os.path.isfile(python_exe) and os.path.isfile(requirements_path):
                      self.log_to_gui("Update", f"执行 pip 安装节点依赖 for '{node_name}'...", "info")
                      pip_cmd_base = [python_exe, "-m", "pip", "install", "-r", requirements_path, "--upgrade"]
                      pip_cmd_extras = ["--extra-index-url", "https://download.pytorch.org/whl/cu118", "--extra-index-url", "https://download.pytorch.org/whl/cu121"]
                      pip_cmd = pip_cmd_base + pip_cmd_extras
                      is_venv = sys.prefix != sys.base_prefix
                      if platform.system() != "Windows" and not is_venv:
                           if sys.base_prefix != sys.prefix:
                                pass
                           else:
                                pip_cmd.append("--user")

                      pip_cmd.extend(["--no-cache-dir"])

                      _, stderr_pip, rc_pip = self._run_git_command(pip_cmd, cwd=node_install_path, timeout=180)
                      if rc_pip != 0:
                           self.log_to_gui("Update", f"Pip 安装节点依赖失败: {stderr_pip.strip()}", "error")
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
         if self.stop_event.is_set():
             return
         self.log_to_gui("Update", f"正在卸载节点 '{node_name}' (删除目录: {node_install_path})...", "info")

         try:
              if not os.path.isdir(node_install_path):
                   self.log_to_gui("Update", f"节点目录 '{node_install_path}' 不存在，无需卸载。", "warn")
                   self.root.after(0, lambda name=node_name: messagebox.showwarning("卸载失败", f"节点目录 '{name}' 不存在。", parent=self.root))
                   return

              if self.stop_event.is_set():
                  raise threading.ThreadExit

              self.log_to_gui("Update", f"删除目录: {node_install_path}", "cmd") # Log the action
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
        if self.stop_event.is_set():
            return
        self.log_to_gui("Update", f"开始安装节点 '{node_name}'...", "info")
        self.log_to_gui("Update", f"  仓库: {repo_url}", "info")
        self.log_to_gui("Update", f"  目标引用: {target_ref}", "info")
        self.log_to_gui("Update", f"  目标目录: {node_install_path}", "info")

        try:
            comfyui_nodes_dir = self.comfyui_nodes_dir
            if not comfyui_nodes_dir: # Should be validated earlier, but defensive check
                 raise Exception("ComfyUI custom_nodes 目录未设置或无效。")

            if not os.path.exists(comfyui_nodes_dir):
                 self.log_to_gui("Update", f"创建 custom_nodes 目录: {comfyui_nodes_dir}", "info")
                 os.makedirs(comfyui_nodes_dir, exist_ok=True)

            if os.path.exists(node_install_path):
                 if os.path.isdir(node_install_path) and len(os.listdir(node_install_path)) > 0:
                      # If the directory exists and is not empty, maybe it's a failed partial clone?
                      # Offer to clean it up? Or just fail? Let's fail and let the user decide.
                      raise Exception(f"节点安装目录已存在且不为空: {node_install_path}")
                 elif not os.path.isdir(node_install_path):
                      # If it exists but is a file, we can't clone here.
                      raise Exception(f"目标路径已存在但不是目录: {node_install_path}")
                 else:
                      # If it exists and is an empty directory, try to remove it first (maybe from a previous failed attempt)
                      try:
                           self.log_to_gui("Update", f"移除已存在的空目录: {node_install_path}", "info")
                           os.rmdir(node_install_path)
                      except OSError as e:
                           # If rmdir fails for some reason (e.g., permissions), raise an error
                           raise Exception(f"无法移除已存在的空目录 {node_install_path}: {e}")

            if self.stop_event.is_set():
                raise threading.ThreadExit

            self.log_to_gui("Update", f"执行 Git clone {repo_url} {node_install_path}...", "info")
            clone_cmd = ["clone", "--progress"] # --progress gives output during clone
            # Check if target_ref looks like a commit hash (approx 7+ hex chars)
            is_likely_commit_hash = len(target_ref) >= 7 and all(c in '0123456789abcdefABCDEF' for c in target_ref.lower())

            # If target_ref is specified and is not a likely commit hash, try cloning the specific branch
            # Git clone -b <branch> only works for branches. Tags/Commits need checkout after clone.
            if target_ref and not is_likely_commit_hash:
                 # Add branch flag. If it's not a branch name, the clone will proceed with default branch,
                 # and the subsequent checkout step will handle tags or commits.
                 clone_cmd.extend(["--branch", target_ref])

            clone_cmd.extend([repo_url, node_install_path])

            # Run clone command from the custom_nodes directory, targeting node_install_path
            stdout_clone, stderr_clone, returncode = self._run_git_command(clone_cmd, cwd=comfyui_nodes_dir, timeout=300, log_output=True)

            if returncode != 0:
                 # Clean up potentially created partial directory on failure
                 if os.path.exists(node_install_path):
                      try:
                           self.log_to_gui("Update", f"Git clone 失败，尝试移除失败目录: {node_install_path}", "warn")
                           shutil.rmtree(node_install_path)
                           self.log_to_gui("Update", f"已移除失败的节点目录: {node_install_path}", "info")
                      except Exception as rm_err:
                           self.log_to_gui("Update", f"移除失败的节点目录 '{node_install_path}' 失败: {rm_err}", "error")
                 raise Exception(f"Git clone 失败 (退出码 {returncode})")

            self.log_to_gui("Update", "Git clone 完成。", "info")

            # If target_ref was specified, checkout the specific ref after cloning
            # This handles tags, commit hashes, and ensures the correct state if --branch failed or wasn't used.
            if target_ref:
                 self.log_to_gui("Update", f"尝试执行 Git checkout {target_ref}...", "info")
                 # Use --force to ensure checkout succeeds even if clone resulted in unexpected state (shouldn't happen but safe)
                 _, stderr_checkout, rc_checkout = self._run_git_command(["checkout", "--force", target_ref], cwd=node_install_path, timeout=60)
                 if rc_checkout != 0:
                      # Log warning, not fatal error, as the node is still installed, just maybe not the exact version.
                      self.log_to_gui("Update", f"Git checkout {target_ref[:8]} 失败: {stderr_checkout.strip()}", "warn")
                      self.root.after(0, lambda name=node_name, ref=target_ref[:8]: messagebox.showwarning("版本切换警告", f"节点 '{name}' 安装后尝试切换到版本 {ref} 失败。\n请查看日志。", parent=self.root))
                 else:
                      self.log_to_gui("Update", f"Git checkout {target_ref[:8]} 完成。", "info")


            if self.stop_event.is_set():
                raise threading.ThreadExit

            # Update submodules if .gitmodules exists
            if os.path.exists(os.path.join(node_install_path, ".gitmodules")):
                 self.log_to_gui("Update", f"执行 Git submodule update for '{node_name}'...", "info")
                 _, stderr_sub, rc_sub = self._run_git_command(["submodule", "update", "--init", "--recursive", "--force"], cwd=node_install_path, timeout=180)
                 if rc_sub != 0:
                     self.log_to_gui("Update", f"Git submodule update 失败: {stderr_sub.strip()}", "warn")

            if self.stop_event.is_set():
                raise threading.ThreadExit

            # Install Python dependencies if requirements.txt exists
            python_exe = self.python_exe_var.get()
            requirements_path = os.path.join(node_install_path, "requirements.txt")
            if python_exe and os.path.isfile(python_exe) and os.path.isfile(requirements_path):
                 self.log_to_gui("Update", f"执行 pip 安装节点依赖 for '{node_name}'...", "info")
                 pip_cmd_base = [python_exe, "-m", "pip", "install", "-r", requirements_path, "--upgrade"]
                 pip_cmd_extras = ["--extra-index-url", "https://download.pytorch.org/whl/cu118", "--extra-index-url", "https://download.pytorch.org/whl/cu121"]
                 pip_cmd = pip_cmd_base + pip_cmd_extras
                 is_venv = sys.prefix != sys.base_prefix
                 if platform.system() != "Windows" and not is_venv:
                       if sys.base_prefix != sys.prefix:
                           pass
                       else:
                           pip_cmd.append("--user")

                 pip_cmd.extend(["--no-cache-dir"])

                 _, stderr_pip, rc_pip = self._run_git_command(pip_cmd, cwd=node_install_path, timeout=180)
                 if rc_pip != 0:
                      self.log_to_gui("Update", f"Pip 安装节点依赖失败: {stderr_pip.strip()}", "error")
                      self.root.after(0, lambda name=node_name: messagebox.showwarning("依赖安装失败", f"节点 '{name}' 的 Python 依赖可能安装失败。\n请查看日志。", parent=self.root))
                 else:
                      self.log_to_gui("Update", f"Pip 安装节点依赖完成 for '{node_name}'.", "info")

            self.log_to_gui("Update", f"节点 '{node_name}' 安装流程完成。", "info")
            self.root.after(0, lambda name=node_name: messagebox.showinfo("安装完成", f"节点 '{name}' 已成功安装。", parent=self.root))

        except threading.ThreadExit:
             self.log_to_gui("Update", f"节点 '{node_name}' 安装任务已取消。", "warn")
             # Clean up partially created directory if it exists
             if os.path.exists(node_install_path):
                 try:
                      self.log_to_gui("Update", f"安装任务取消，尝试移除部分创建的目录: {node_install_path}", "warn")
                      shutil.rmtree(node_install_path)
                      self.log_to_gui("Update", f"已移除部分创建的目录: {node_install_path}", "info")
                 except Exception as rm_err:
                      self.log_to_gui("Update", f"移除部分创建的目录 '{node_install_path}' 失败: {rm_err}", "error")

        except Exception as e:
            error_msg = f"节点 '{node_name}' 安装失败: {e}"
            self.log_to_gui("Update", error_msg, "error")
            self.root.after(0, lambda msg=error_msg: messagebox.showerror("安装失败", msg, parent=self.root))
        finally:
            # Always refresh the list after attempting installation
            self.root.after(0, self._queue_node_list_refresh)


    # MOD2: Task to fetch git history for a node
    def _node_history_fetch_task(self, node_name, node_install_path):
         """Task to fetch git history and current commit for a node. Runs in worker thread."""
         if self.stop_event.is_set():
             return
         self.log_to_gui("Update", f"正在获取节点 '{node_name}' 的版本历史...", "info")

         history_data = []
         current_local_commit = None # Full ID
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
                 # Even if we can't get the current commit, try fetching history

             # Ensure origin remote exists and is correct before fetching history
             # Find the correct repo_url from cache if available, otherwise try reading from local git config
             found_node_info = next((node for node in self.local_nodes_only if node.get("name") == node_name), None)
             repo_url = found_node_info.get("repo_url") if found_node_info else None

             if not repo_url or repo_url in ("本地安装，无Git信息", "无法获取远程 URL", "本地安装", "N/A", "无远程仓库"):
                 # If URL not in cache, try reading from local git config
                 stdout_config_url, _, rc_config_url = self._run_git_command(["config", "--get", "remote.origin.url"], cwd=node_install_path, timeout=5, log_output=False)
                 if rc_config_url == 0 and stdout_config_url and stdout_config_url.strip().endswith(".git"):
                      repo_url = stdout_config_url.strip()
                      self.log_to_gui("Update", f"从本地 Git config 获取到远程 URL: {repo_url}", "info")
                 else:
                      self.log_to_gui("Update", f"节点 '{node_name}': 无法获取有效的远程 URL，历史列表可能不完整。", "warn")


             if repo_url and repo_url not in ("本地安装", "N/A"): # Only attempt fetch if a valid URL is found
                 stdout_get_url, _, rc_get_url = self._run_git_command(["remote", "get-url", "origin"], cwd=node_install_path, timeout=10, log_output=False)
                 current_origin_url = stdout_get_url.strip() if rc_get_url == 0 else ""

                 if not current_origin_url:
                      self.log_to_gui("Update", f"节点 '{node_name}': 远程 'origin' 不存在，尝试添加 URL '{repo_url}'...", "info")
                      _, stderr_add, rc_add = self._run_git_command(["remote", "add", "origin", repo_url], cwd=node_install_path, timeout=10)
                      if rc_add != 0:
                          self.log_to_gui("Update", f"节点 '{node_name}': 添加远程 'origin' 失败: {stderr_add.strip()}", "warn")
                 elif current_origin_url != repo_url:
                     self.log_to_gui("Update", f"节点 '{node_name}': 远程 'origin' URL 不匹配 ({current_origin_url}), 尝试设置新 URL '{repo_url}'...", "warn")
                     _, stderr_set, rc_set = self._run_git_command(["remote", "set-url", "origin", repo_url], cwd=node_install_path, timeout=10)
                     if rc_set != 0:
                         self.log_to_gui("Update", f"节点 '{node_name}': 设置远程 URL 失败: {stderr_set.strip()}", "warn")
                     else:
                         self.log_to_gui("Update", f"节点 '{node_name}': 远程 URL 已更新。", "info")

                 # After ensuring remote is set, fetch
                 if self.stop_event.is_set():
                     raise threading.ThreadExit
                 self.log_to_gui("Update", f"执行 Git fetch origin --prune --tags -f for '{node_name}'...", "info")
                 # Increase timeout slightly for fetch
                 _, stderr_fetch, rc_fetch = self._run_git_command(["fetch", "origin", "--prune", "--tags", "-f"], cwd=node_install_path, timeout=90)
                 if rc_fetch != 0:
                      self.log_to_gui("Update", f"Git fetch 失败 for '{node_name}': {stderr_fetch.strip()}", "error")
                      self.log_to_gui("Update", "无法从远程获取最新历史，列表可能不完整。", "warn")
             else:
                  self.log_to_gui("Update", f"节点 '{node_name}': 无有效远程 URL，仅显示本地历史。", "warn")


             if self.stop_event.is_set():
                 return

             # Get all local and fetched remote references (branches, tags, HEAD) with their commits and dates
             # Format: %(refname) %(objectname) %(committerdate:iso-strict) %(contents:subject)
             # Use full refname to distinguish local/remote/tags
             # Added %(contents:subject) to get commit message for description
             log_cmd = ["for-each-ref", "refs/", "--sort=-committerdate", "--format=%(refname) %(objectname) %(committerdate:iso-strict) %(contents:subject)"]
             history_output, _, rc_history = self._run_git_command(log_cmd, cwd=node_install_path, timeout=60)

             if rc_history != 0:
                  self.log_to_gui("Update", f"获取 Git 历史失败: {history_output.strip()}", "error")
                  self.log_to_gui("Update", "无法获取节点历史。", "error")
             else:
                  processed_commits = set() # To avoid duplicates for the same commit reachable by multiple refs
                  # Parse history output
                  for line in history_output.splitlines():
                       parts = line.split(' ', 3) # Split into refname, commit_id, date_iso, subject (optional)
                       if len(parts) >= 3:
                           refname, commit_id, date_iso = parts[0], parts[1], parts[2]
                           description = parts[3].strip() if len(parts) == 4 else ""

                           # Skip if we've already listed this commit hash
                           if commit_id in processed_commits:
                                continue

                           ref_type = "commit" # Default type
                           display_name = commit_id[:8] # Default display name is short commit ID

                           if refname == "HEAD":
                                # Find the symbolic ref for HEAD if possible to show local branch name
                                head_sym_ref_out, _, _ = self._run_git_command(["symbolic-ref", "-q", "--short", "HEAD"], cwd=node_install_path, timeout=2, log_output=False)
                                if head_sym_ref_out:
                                    ref_type = "branch (HEAD)"
                                    display_name = head_sym_ref_out.strip()
                                else: # Detached HEAD
                                    ref_type = "commit (HEAD)"
                                    # display_name remains commit_id[:8] or set below

                                description = f"HEAD - {description}" # Add HEAD marker to description
                           elif refname.startswith("refs/heads/"):
                                ref_type = "branch"
                                display_name = refname.replace("refs/heads/", "")
                           elif refname.startswith("refs/remotes/origin/"):
                                ref_type = "branch (remote)" # Indicate remote branch
                                display_name = refname.replace("refs/remotes/origin/", "")
                                if "HEAD" in display_name: # Skip remote HEAD alias more robustly
                                     continue
                           elif refname.startswith("refs/tags/"):
                                ref_type = "tag"
                                display_name = refname.replace("refs/tags/", "")
                                description = f"TAG - {description}" # Add TAG marker to description

                           history_data.append({"type": ref_type, "name": display_name, "commit_id": commit_id, "date_iso": date_iso, "description": description})
                           processed_commits.add(commit_id)

             # Sort the history data (MOD1: Using custom comparison)
             history_data.sort(key=cmp_to_key(_compare_versions_for_sort))

             # --- Add current local commit if not already in the list (e.g., local-only commits) ---
             if current_local_commit and current_local_commit not in processed_commits:
                  self.log_to_gui("Update", "获取当前本地 Commit 信息...", "info")
                  head_date_stdout, _, rc_head_date = self._run_git_command(["log", "-1", "--format=%ci", "HEAD"], cwd=node_install_path, timeout=5, log_output=False)
                  head_subject_stdout, _, rc_head_subject = self._run_git_command(["log", "-1", "--format=%s", "HEAD"], cwd=node_install_path, timeout=5, log_output=False)
                  head_date_iso = head_date_stdout.strip() if rc_head_date == 0 else None
                  head_description = head_subject_stdout.strip() if rc_head_subject == 0 else "当前工作目录"
                  date_obj = _parse_iso_date_for_sort(head_date_iso)
                  final_date_iso = date_obj.isoformat() if date_obj else datetime.now(timezone.utc).isoformat()

                  # Determine type (detached HEAD or local branch not tracking remote)
                  head_sym_ref_out, _, rc_head_sym_ref = self._run_git_command(["symbolic-ref", "-q", "--short", "HEAD"], cwd=node_install_path, timeout=2, log_output=False)
                  head_type = "commit (HEAD)" if rc_head_sym_ref != 0 else "branch (local)"
                  head_name = head_sym_ref_out.strip() if head_type == "branch (local)" else f"Detached at {current_local_commit[:8]}"

                  history_data.append({"type": head_type, "name": head_name, "commit_id": current_local_commit, "date_iso": final_date_iso, "description": head_description})
                  self.log_to_gui("Update", f"添加当前本地 HEAD ({current_local_commit[:8]}) 到列表。", "info")

                  # Re-sort to include the added local HEAD
                  history_data.sort(key=cmp_to_key(_compare_versions_for_sort))


             self._node_history_modal_versions_data = history_data # Store in the designated variable
             self._node_history_modal_node_name = node_name
             self._node_history_modal_node_path = node_install_path
             self._node_history_modal_current_commit = current_local_commit # Full local commit ID

             self.log_to_gui("Update", f"节点 '{node_name}' 版本历史获取完成。找到 {len(history_data)} 条记录。", "info")
             self.root.after(0, self._show_node_history_modal) # Show modal in GUI thread

         except threading.ThreadExit:
              self.log_to_gui("Update", f"节点 '{node_name}' 历史获取任务已取消。", "warn")
              self.root.after(0, self._cleanup_modal_state) # Clean up state in GUI thread
         except Exception as e:
             error_msg = f"获取节点 '{node_name}' 版本历史失败: {e}"
             self.log_to_gui("Update", error_msg, "error")
             self.root.after(0, self._cleanup_modal_state) # Clean up state in GUI thread
             self.root.after(0, lambda msg=error_msg: messagebox.showerror("获取历史失败", msg, parent=self.root))


    # MOD1: Show Node History Modal (Refactored Styling and Layout Fix)
    def _show_node_history_modal(self):
        """Creates and displays the node version history modal with improved styling resembling the Node list."""
        # Check if the modal is already open or if data is missing
        if self._node_history_modal_window and self._node_history_modal_window.winfo_exists():
             print("[Launcher WARNING] Attempted to open node history modal, but one is already open.")
             return # Do nothing if already open

        if not self._node_history_modal_versions_data:
            self.log_to_gui("Update", f"没有节点 '{self._node_history_modal_node_name}' 的历史版本数据可显示。", "warn")
            self._cleanup_modal_state() # Clean up state if no data
            return

        node_name = self._node_history_modal_node_name
        history_data = self._node_history_modal_versions_data # Use stored data
        current_commit = self._node_history_modal_current_commit # Full local commit ID

        modal_window = Toplevel(self.root)
        self.root.eval(f'tk::PlaceWindow {str(modal_window)} center') # Center the modal
        modal_window.title(f"版本切换 - {node_name}")
        modal_window.transient(self.root) # Set modal parent
        modal_window.grab_set() # Modal capture events
        modal_window.geometry("850x550") # Adjusted size
        modal_window.configure(bg=BG_COLOR)
        modal_window.rowconfigure(0, weight=1); modal_window.columnconfigure(0, weight=1)
        # MOD2: Use the cleanup function when modal is closed by window manager
        modal_window.protocol("WM_DELETE_WINDOW", lambda win=modal_window: self._cleanup_modal_state(win))
        self._node_history_modal_window = modal_window # Store reference


        # Use a single frame to hold header and canvas/scrollbar for items
        main_modal_frame = ttk.Frame(modal_window, style='Modal.TFrame', padding=10)
        main_modal_frame.grid(row=0, column=0, sticky="nsew")
        main_modal_frame.rowconfigure(1, weight=1) # Allow canvas row to expand
        main_modal_frame.columnconfigure(0, weight=1) # Allow canvas col to expand


        # --- Header Row --- Style and alignment confirmed/refined
        header_frame = ttk.Frame(main_modal_frame, style='TabControl.TFrame', padding=(0, 5, 0, 8)) # MOD1: Use TabControl BG for header
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew") # MOD1: Span both canvas and potential scrollbar column
        # MOD1: Adjusted column weights/minsizes for visual similarity to Nodes tab Treeview
        # Columns: Version (Name+Type), Status, Commit ID, Date, Action
        # Assign weights to distribute extra space proportionally
        header_frame.columnconfigure(0, weight=4, minsize=250) # Version Name (wider)
        header_frame.columnconfigure(1, weight=1, minsize=80)  # Status
        header_frame.columnconfigure(2, weight=1, minsize=100) # Commit ID
        header_frame.columnconfigure(3, weight=1, minsize=110) # Date
        header_frame.columnconfigure(4, weight=0, minsize=80)  # Button (fixed size)

        # MOD1: Use ModalHeader style, ensure alignment
        ttk.Label(header_frame, text="版本", style='ModalHeader.TLabel', anchor=tk.W).grid(row=0, column=0, sticky='w', padx=5)
        ttk.Label(header_frame, text="状态", style='ModalHeader.TLabel', anchor=tk.CENTER).grid(row=0, column=1, sticky='ew', padx=5)
        ttk.Label(header_frame, text="提交ID", style='ModalHeader.TLabel', anchor=tk.W).grid(row=0, column=2, sticky='w', padx=5)
        ttk.Label(header_frame, text="更新日期", style='ModalHeader.TLabel', anchor=tk.W).grid(row=0, column=3, sticky='w', padx=5)
        ttk.Label(header_frame, text="操作", style='ModalHeader.TLabel', anchor=tk.CENTER).grid(row=0, column=4, sticky='ew', padx=(5,10))


        # --- Scrollable Item List ---
        # FIX 1: Removed style='Modal.TCanvas' as tk.Canvas doesn't support it.
        canvas = tk.Canvas(main_modal_frame, bg=TEXT_AREA_BG, highlightthickness=1, highlightbackground=BORDER_COLOR, borderwidth=0) # Use bg directly
        scrollbar = ttk.Scrollbar(main_modal_frame, orient=tk.VERTICAL, command=canvas.yview)
        # scrollable_frame will contain the actual row frames
        scrollable_frame = ttk.Frame(canvas, style='Modal.TFrame')

        # Bind the scrollable frame's size changes to update the canvas scrollregion
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        # Create the window on the canvas that holds the scrollable frame
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw") # Remove width=1, let it determine size
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")

        # Bind canvas width changes to the scrollable frame's width
        # This ensures the scrollable_frame fills the canvas width horizontally
        canvas.bind('<Configure>', lambda e: canvas.itemconfigure(canvas_window, width=e.width))


        # Configure columns of the scrollable frame to match header
        # FIX 2: Configure columns *only* on the scrollable_frame.
        # These weights and minsizes will govern the width of the columns for ALL rows placed inside scrollable_frame.
        scrollable_frame.columnconfigure(0, weight=4, minsize=250) # Version Name
        scrollable_frame.columnconfigure(1, weight=1, minsize=80)  # Status
        scrollable_frame.columnconfigure(2, weight=1, minsize=100) # Commit ID
        scrollable_frame.columnconfigure(3, weight=1, minsize=110) # Date
        scrollable_frame.columnconfigure(4, weight=0, minsize=80)  # Button


        # Populate with history items using new styles
        for i, item_data in enumerate(history_data):
             # Ensure necessary keys exist with default empty strings if missing
             item_data.setdefault('type', '未知')
             item_data.setdefault('name', 'N/A')
             item_data.setdefault('commit_id', 'N/A')
             item_data.setdefault('date_iso', '')
             item_data.setdefault('description', 'N/A')


             # Determine styles for alternating backgrounds
             row_frame_style = f'ModalRow{"Odd" if i % 2 == 0 else "Even"}.TFrame'
             label_style = f'ModalRow{"Odd" if i % 2 == 0 else "Even"}.TLabel'
             highlight_style = f'ModalRow{"Odd" if i % 2 == 0 else "Even"}Highlight.TLabel'

             # Create a frame for this row to hold the background color and contain the widgets
             row_frame = ttk.Frame(scrollable_frame, style=row_frame_style, padding=(0, 3))
             # FIX 2: Grid row_frame into scrollable_frame, spanning ALL columns
             row_frame.grid(row=i, column=0, columnspan=5, sticky="ew", padx=0, pady=0)

             # FIX 2: DO NOT configure columns on row_frame itself.
             # row_frame.columnconfigure(...) <-- REMOVED

             try:
                 date_str = item_data['date_iso']
                 date_obj = _parse_iso_date_for_sort(date_str)
                 date_display = date_obj.strftime('%Y-%m-%d') if date_obj else ("解析失败" if date_str else "无日期")
             except Exception:
                 date_display = "日期错误"

             commit_id = item_data['commit_id']
             version_name = item_data['name']
             version_type = item_data['type']
             description = item_data['description']

             # Concatenate type and name for the first column (Version)
             version_display = f"{version_type} / {version_name}"

             status_text = ""
             status_label_actual_style = label_style # Default style
             # Compare full commit IDs for "当前" status
             if current_commit and commit_id == current_commit:
                  status_text = "当前"
                  status_label_actual_style = highlight_style # Use highlight style


             # Add labels and button, gridding them *into the row_frame*
             # FIX 2: Ensure widgets within row_frame are gridded into columns 0 through 4.
             # Their size and placement within these columns will be influenced by the
             # *parent* scrollable_frame's column configuration and their own sticky settings.
             version_label_widget = ttk.Label(row_frame, text=version_display, style=label_style, anchor=tk.W, wraplength=240) # Use fixed wrap for simplicity
             version_label_widget.grid(row=0, column=0, sticky='w', padx=5, pady=1)

             status_label_widget = ttk.Label(row_frame, text=status_text, style=status_label_actual_style, anchor=tk.CENTER)
             status_label_widget.grid(row=0, column=1, sticky='ew', padx=5, pady=1) # Sticky EW for centering

             ttk.Label(row_frame, text=commit_id[:8], style=label_style, anchor=tk.W).grid(row=0, column=2, sticky='w', padx=5, pady=1)
             ttk.Label(row_frame, text=date_display, style=label_style, anchor=tk.W).grid(row=0, column=3, sticky='w', padx=5, pady=1)
             # Adding a description label here if needed
             # ttk.Label(row_frame, text=description, style=label_style, anchor=tk.W, wraplength=300).grid(row=0, column=4, sticky='w', padx=5, pady=1) # Example if adding description col


             switch_btn = ttk.Button(row_frame, text="切换", style="Modal.TButton", width=6,
                                     command=lambda c_id=commit_id, win=modal_window, name=node_name: self._on_modal_switch_confirm(win, name, c_id)) # Pass node_name and modal_window
             switch_btn.grid(row=0, column=4, sticky='e', padx=(5, 10), pady=1) # Align button right

             if status_text == "当前":
                  switch_btn.config(state=tk.DISABLED)

        # Mousewheel scrolling
        def _on_mousewheel(event):
             scroll_amount = 0
             # Calculate scroll units based on OS/event type
             if platform.system() == "Windows":
                 # Windows event.delta is 120 per notch
                 scroll_amount = int(-1*(event.delta/120))
             elif platform.system() == "Darwin": # macOS uses event.delta directly
                 scroll_amount = int(-1 * event.delta) # Adjust sensitivity if needed
             else: # Linux, event.num indicates button 4 (up) or 5 (down)
                 if event.num == 4:
                     scroll_amount = -1
                 elif event.num == 5:
                     scroll_amount = 1
             # Check if canvas exists before scrolling
             if canvas and canvas.winfo_exists():
                canvas.yview_scroll(scroll_amount, "units")

        # Bind mousewheel to canvas and its children for broader coverage
        # Bind directly to the canvas first, which often covers the area
        if canvas and canvas.winfo_exists():
            canvas.bind("<MouseWheel>", _on_mousewheel)
            # Optionally bind to the scrollable frame *inside* the canvas
            if scrollable_frame and scrollable_frame.winfo_exists():
                 scrollable_frame.bind("<MouseWheel>", _on_mousewheel)
            # Binding to individual row frames/labels is usually not necessary and adds complexity


        # Keep the modal open until explicitly closed by the user (or WM_DELETE_WINDOW protocol)
        # modal_window.wait_window() # Removed, as WM_DELETE_WINDOW protocol handles cleanup


    # MOD2: Cleanup Modal State
    def _cleanup_modal_state(self, modal_window=None):
         """Cleans up modal-related instance variables and destroys the window."""
         print("[Launcher DEBUG] Cleaning up modal state...")
         # Clear internal state variables regardless of how the window is closed
         self._node_history_modal_versions_data = []
         self._node_history_modal_node_name = ""
         self._node_history_modal_node_path = ""
         self._node_history_modal_current_commit = ""

         # Destroy the window if it exists and is not already destroyed
         window_to_destroy = modal_window if modal_window else self._node_history_modal_window
         if window_to_destroy and self.window_to_exists(window_to_destroy): # Use self.window_to_exists
             try:
                  # Attempt to unbind mousewheel events if bound specifically during modal creation
                  # This is tricky. If bound to canvas and scrollable_frame, destroying the window
                  # should clean them up. Explicit unbinding is often not needed when destroying
                  # the parent widget, but can be added here if persistent issues occur.
                  # Example: if hasattr(window_to_destroy, '_canvas'): window_to_destroy._canvas.unbind("<MouseWheel>")

                  window_to_destroy.destroy()
                  print("[Launcher DEBUG] Modal window destroyed.")
             except tk.TclError:
                 # Window might already be destroyed if this is called multiple times
                 print("[Launcher DEBUG] Modal window already destroyed (TclError during destroy).")
                 pass
             except Exception as e:
                 print(f"[Launcher ERROR] Error during modal window destruction: {e}")

         # Always clear the reference after attempting destruction
         self._node_history_modal_window = None
         print("[Launcher DEBUG] Modal state variables cleared.")

         # Schedule a UI state update to re-enable buttons
         self.root.after(0, self._update_ui_state)
         print("[Launcher DEBUG] UI update scheduled after modal cleanup.")


    # Helper function to check if a window widget exists safely
    def window_to_exists(self, window): # Added self
        """Safely checks if a Tkinter widget exists."""
        try:
            return window and window.winfo_exists()
        except tk.TclError:
            return False
        except Exception:
            return False


    # MOD2: Handle Modal Switch Confirmation and Queue Task
    def _on_modal_switch_confirm(self, modal_window, node_name, target_ref): # Added node_name
        """Handles the confirmation and queues the switch task from the modal."""
        # Get node info from stored state variables (more reliable than relying on args from lambda)
        # Although lambda captures are fine, using the state vars reinforces the modal's state dependency.
        modal_node_name = self._node_history_modal_node_name
        modal_node_path = self._node_history_modal_node_path

        if not modal_node_name or not modal_node_path or not target_ref:
            messagebox.showerror("切换失败", "无法确定节点信息或目标版本。", parent=modal_window)
            self._cleanup_modal_state(modal_window)
            return

        if not os.path.isdir(modal_node_path) or not os.path.exists(os.path.join(modal_node_path, ".git")):
             messagebox.showerror("切换失败", f"节点目录 '{modal_node_path}' 不是有效的 Git 仓库。", parent=modal_window)
             self._cleanup_modal_state(modal_window)
             return

        # Check if ComfyUI is running before queuing the task
        if self._is_comfyui_running() or self.comfyui_externally_detected:
             messagebox.showwarning("服务运行中", "请先停止 ComfyUI 后台服务，再进行节点版本切换。", parent=modal_window)
             # Don't close the modal, let the user stop ComfyUI first
             return # Do not queue the task if ComfyUI is running

        confirm = messagebox.askyesno(
            "确认切换版本",
            f"确定要将节点 '{modal_node_name}' 切换到版本 (引用: {target_ref[:8]}) 吗？\n\n警告: 此操作会覆盖节点目录下的本地修改，并可能导致与其他节点不兼容！\n确认前请确保 ComfyUI 已停止运行。",
            parent=modal_window
        )
        if not confirm:
            return # User cancelled, leave modal open

        self.log_to_gui("Launcher", f"将节点 '{modal_node_name}' 切换到版本 {target_ref[:8]} 任务添加到队列...", "info")
        self.update_task_queue.put((self._switch_node_to_ref_task, [modal_node_name, modal_node_path, target_ref], {})) # Pass correct arguments

        self._cleanup_modal_state(modal_window) # Close modal after queuing task
        self.root.after(0, self._update_ui_state) # Update UI state to show task running


    # MOD2: Task to switch an installed node to a specific git reference
    def _switch_node_to_ref_task(self, node_name, node_install_path, target_ref):
         """Task to switch an installed node to a specific git reference. Runs in worker thread."""
         if self.stop_event.is_set():
             return
         self.log_to_gui("Update", f"正在将节点 '{node_name}' 切换到版本 (引用: {target_ref[:8]})...", "info")

         try:
             if not os.path.isdir(node_install_path) or not os.path.exists(os.path.join(node_install_path, ".git")):
                  raise Exception(f"节点目录不是有效的 Git 仓库: {node_install_path}")

             # Check for local changes and warn/force checkout
             stdout_status, _, _ = self._run_git_command(["status", "--porcelain"], cwd=node_install_path, timeout=10, log_output=False)
             if stdout_status.strip():
                  self.log_to_gui("Update", f"节点 '{node_name}' 存在未提交的本地修改，将通过 checkout --force 覆盖。", "warn")

             if self.stop_event.is_set():
                 raise threading.ThreadExit

             # Checkout the target reference (commit hash, tag, branch name, remote branch name)
             self.log_to_gui("Update", f"执行 Git checkout --force {target_ref[:8]}...", "info")
             # Use --force to discard local changes if any and handle detached HEAD gracefully
             _, stderr_checkout, rc_checkout = self._run_git_command(["checkout", "--force", target_ref], cwd=node_install_path, timeout=60)
             if rc_checkout != 0:
                 raise Exception(f"Git checkout 失败: {stderr_checkout.strip()}")

             self.log_to_gui("Update", f"Git checkout 完成 (引用: {target_ref[:8]}).", "info")

             if self.stop_event.is_set():
                 raise threading.ThreadExit

             # Update submodules if .gitmodules exists
             if os.path.exists(os.path.join(node_install_path, ".gitmodules")):
                 self.log_to_gui("Update", f"执行 Git submodule update for '{node_name}'...", "info")
                 _, stderr_sub, rc_sub = self._run_git_command(["submodule", "update", "--init", "--recursive", "--force"], cwd=node_install_path, timeout=180)
                 if rc_sub != 0:
                     self.log_to_gui("Update", f"Git submodule update 失败: {stderr_sub.strip()}", "warn")

             if self.stop_event.is_set():
                 raise threading.ThreadExit

             # Re-install Python dependencies if requirements.txt exists
             python_exe = self.python_exe_var.get()
             requirements_path = os.path.join(node_install_path, "requirements.txt")
             if python_exe and os.path.isfile(python_exe) and os.path.isfile(requirements_path):
                  self.log_to_gui("Update", f"执行 pip 安装节点依赖 for '{node_name}'...", "info")
                  pip_cmd_base = [python_exe, "-m", "pip", "install", "-r", requirements_path, "--upgrade"]
                  pip_cmd_extras = ["--extra-index-url", "https://download.pytorch.org/whl/cu118", "--extra-index-url", "https://download.pytorch.org/whl/cu121"]
                  pip_cmd = pip_cmd_base + pip_cmd_extras
                  is_venv = sys.prefix != sys.base_prefix
                  if platform.system() != "Windows" and not is_venv:
                       if sys.base_prefix != sys.prefix:
                           pass
                       else:
                           pip_cmd.append("--user")

                  pip_cmd.extend(["--no-cache-dir"])

                  _, stderr_pip, rc_pip = self._run_git_command(pip_cmd, cwd=node_install_path, timeout=180)
                  if rc_pip != 0:
                       self.log_to_gui("Update", f"Pip 安装节点依赖失败: {stderr_pip.strip()}", "error")
                       self.root.after(0, lambda name=node_name: messagebox.showwarning("依赖安装失败", f"节点 '{name}' 的 Python 依赖可能安装失败。\n请查看日志。", parent=self.root))
                  else:
                       self.log_to_gui("Update", f"Pip 安装节点依赖完成.", "info")

             self.log_to_gui("Update", f"节点 '{node_name}' 已成功切换到版本 (引用: {target_ref[:8]})。", "info")
             self.root.after(0, lambda name=node_name, ref=target_ref[:8]: messagebox.showinfo("切换完成", f"节点 '{name}' 已成功切换到版本: {ref}", parent=self.root))

         except threading.ThreadExit:
              self.log_to_gui("Update", f"节点 '{node_name}' 切换版本任务已取消。", "warn")
         except Exception as e:
             error_msg = f"节点 '{node_name}' 切换版本失败: {e}"
             self.log_to_gui("Update", error_msg, "error")
             self.root.after(0, lambda msg=error_msg: messagebox.showerror("切换失败", msg, parent=self.root))
         finally:
             # Always refresh node list after attempting a switch
             self.root.after(0, self._queue_node_list_refresh)


    # --- Error Analysis Methods (MOD4: API Call logic confirmed, MOD5: User Request Field) ---

    def run_diagnosis(self):
        """Captures logs, combines them, and sends them to the configured API for analysis."""
        # MOD2: Check if modal is open
        if self._node_history_modal_window and self._node_history_modal_window.winfo_exists():
             messagebox.showwarning("操作进行中", "请先关闭节点版本历史弹窗。", parent=self.root)
             return
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中...", "warn")
             return

        api_endpoint = self.error_api_endpoint_var.get().strip()
        api_key = self.error_api_key_var.get().strip()

        # MOD4 & MOD5: Check API endpoint and key before proceeding
        if not api_endpoint:
             messagebox.showwarning("配置缺失", "请在“API 接口”中配置诊断 API 地址。", parent=self.root)
             self.log_to_gui("ErrorAnalysis", "诊断取消: API 接口未配置。", "warn")
             return
        if not api_key:
             messagebox.showwarning("配置缺失", "请在“API 密匙”中配置诊断 API 密钥。", parent=self.root)
             self.log_to_gui("ErrorAnalysis", "诊断取消: API 密钥未配置。", "warn")
             return

        launcher_logs, comfyui_logs, user_request = "", "", ""
        try:
            if hasattr(self, 'launcher_log_text') and self.launcher_log_text.winfo_exists():
                 # Get Launcher logs, remove any initial timestamp/prefix added by insert_output for cleaner AI input
                 # Assumes timestamp format is [YYYY-MM-DD HH:MM:SS]
                 raw_launcher_logs = self.launcher_log_text.get("1.0", tk.END).strip()
                 launcher_logs = "\n".join([
                      line[22:] if line.startswith('[') and len(line) > 21 and line[20:21] == ']' else line
                      for line in raw_launcher_logs.splitlines()
                 ])


            if hasattr(self, 'main_output_text') and self.main_output_text.winfo_exists():
                 # Get ComfyUI logs, remove any initial prefix added by stream_output for cleaner AI input
                 # Assumes prefixes like "[ComfyUI]", "[ComfyUI ERR]"
                 raw_comfyui_logs = self.main_output_text.get("1.0", tk.END).strip()
                 comfyui_logs = "\n".join([
                      line[line.find(']') + 2:] if line.startswith('[ComfyUI') and ']' in line else line
                      for line in raw_comfyui_logs.splitlines()
                 ])

            # MOD5: Get user request text
            if hasattr(self, 'user_request_text') and self.user_request_text.winfo_exists():
                 user_request = self.user_request_text.get("1.0", tk.END).strip()


        except tk.TclError as e:
             self.log_to_gui("ErrorAnalysis", f"读取日志或用户诉求时出错: {e}", "error")
             return

        # MOD5: Format payload to include user request and handle empty logs as specified
        # Use the exact format specified by the user.
        # Include the system setting part specified by the user in the prompt.
        system_setting = """你是一位严谨且高效的AI代码工程师和网页设计师，专注于为用户提供精确、可执行的前端及后端代码方案，并精通 ComfyUI 的集成。你的回复始终优先使用中文。@@核心职能与能力:@@ComfyUI 集成: 精通 ComfyUI 的 API (/prompt, /upload/image, /ws 等) 调用及数据格式，能够设计和实现前端与 ComfyUI 工作流的对接方案（例如参数注入、结果获取），当ComfyUI 运行出错后可以提供解决方案。当“ComLauncher日志”或“ComfyUI日志”其中有日志为空时则跳过空日志的分析，只分析另一部分日志内容。"""

        formatted_log_payload = f"""{system_setting}
以下为用户诉求和运行日志：
@@@@@@@@@用户诉求：
{user_request if user_request else "（无）"}

@@@@@@@@@ComLauncher日志
{launcher_logs if launcher_logs else "（无）"}

@@@@@@@@@ComfyUI日志
{comfyui_logs if comfyui_logs else "（无）"}
"""
        # Gemini API payload structure (using text role, could also use parts list)
        gemini_payload = {
             "contents": [{
                 "parts": [{"text": formatted_log_payload}]
             }]
        }


        self.log_to_gui("ErrorAnalysis", f"准备发送日志到诊断 API: {api_endpoint}...", "info")
        try: # Clear previous analysis output
            if hasattr(self, 'error_analysis_text') and self.error_analysis_text.winfo_exists():
                 self.error_analysis_text.config(state=tk.NORMAL)
                 self.error_analysis_text.delete('1.0', tk.END)
                 self.error_analysis_text.config(state=tk.DISABLED)
        except tk.TclError:
            pass

        # No need to update UI state here, worker thread handles it
        # self._update_ui_state() # Disable buttons

        # Queue the diagnosis task, passing the structured payload
        self.update_task_queue.put((self._run_diagnosis_task, [api_endpoint, api_key, gemini_payload], {}))


    # MOD4: Real API Diagnosis Task with Gemini Fix (Logic confirmed, added logging)
    def _run_diagnosis_task(self, api_endpoint, api_key, gemini_payload):
        """Task to send logs to the configured API (Gemini) and display the analysis. Runs in worker thread."""
        if self.stop_event.is_set():
             return
        self.log_to_gui("ErrorAnalysis", f"--- 开始诊断 ---", "info")
        self.log_to_gui("ErrorAnalysis", f"API 端点 (原始): {api_endpoint}", "info")
        # MOD4: Log API Key presence (but not the key itself)
        self.log_to_gui("ErrorAnalysis", f"API 密钥: {'已配置' if api_key else '未配置'}", "info")

        analysis_result = "未能获取分析结果。" # Default result

        # MOD4: Check for API Key *before* making the call if it's missing
        if not api_key:
            self.log_to_gui("ErrorAnalysis", "API 密钥未配置，无法进行诊断。", "error")
            analysis_result = "错误：API 密钥未配置，无法进行诊断。"
            self.log_to_gui("ErrorAnalysis", analysis_result, "api_output") # Display error in output area
            self.log_to_gui("ErrorAnalysis", f"--- 诊断结束 (配置错误) ---", "info")
            # UI update happens in worker's finally block
            return # Stop the task here

        # --- Gemini API Endpoint Correction ---
        # Ensure endpoint format is correct for generateContent if a base model URL is provided
        # Look for the model name at the end of the URL structure /models/model-name
        api_endpoint_corrected = api_endpoint.strip()
        if api_endpoint_corrected.endswith('/'):
             api_endpoint_corrected = api_endpoint_corrected[:-1] # Remove trailing slash

        # Check if the URL ends with a model path like /models/model-name and doesn't have a method
        if "/models/" in api_endpoint_corrected and ":" not in api_endpoint_corrected.split("/")[-1]:
             api_endpoint_corrected = f"{api_endpoint_corrected}:generateContent"
             self.log_to_gui("ErrorAnalysis", f"修正 API 端点为 (附加 :generateContent): {api_endpoint_corrected}", "info")
        elif not api_endpoint_corrected.endswith((":generateContent", ":streamGenerateContent")):
             # If it doesn't look like a standard model path but also doesn't end with a method,
             # log a warning but use the URL as is. It might be a custom setup or different API.
             self.log_to_gui("ErrorAnalysis", f"API 端点格式 '{api_endpoint_corrected}' 无法识别，按原样使用。请确保端点包含 ':generateContent' 或 ':streamGenerateContent'。", "warn")


        # Prepare parameters (API key)
        params = {'key': api_key}

        try:
            headers = {"Content-Type": "application/json"}
            # MOD4: Log final request details (excluding key value)
            self.log_to_gui("ErrorAnalysis", f"发送 POST 请求到: {api_endpoint_corrected}", "info")
            # self.log_to_gui("ErrorAnalysis", f"Payload: {json.dumps(gemini_payload, indent=2, ensure_ascii=False)[:500]}...", "info") # Log truncated payload if needed

            response = requests.post(api_endpoint_corrected, headers=headers, params=params, json=gemini_payload, timeout=120)
            # MOD4: Log response status code
            self.log_to_gui("ErrorAnalysis", f"API 响应状态码: {response.status_code}", "info")
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            # Parse the Gemini response
            response_data = response.json()
            try:
                 candidates = response_data.get('candidates', [])
                 if candidates:
                     # Assuming the response is from a generateContent call with text output
                     content = candidates[0].get('content', {})
                     parts = content.get('parts', [])
                     if parts:
                         analysis_result = parts[0].get('text', "API 响应中未找到文本内容。")
                     else:
                         analysis_result = "API 响应 'parts' 为空或缺失。"
                 else:
                     # Handle cases where candidates list is empty (e.g., safety block)
                     prompt_feedback = response_data.get('promptFeedback', {})
                     block_reason = prompt_feedback.get('blockReason')
                     if block_reason:
                          analysis_result = f"API 请求被阻止: {block_reason}\n详情: {prompt_feedback.get('safetyRatings', 'N/A')}"
                     else:
                          analysis_result = "API 响应 'candidates' 为空或缺失。"

            except (KeyError, IndexError, TypeError) as e:
                 print(f"[Launcher ERROR] Could not parse Gemini API response structure: {e}")
                 analysis_result = f"API 响应解析失败。\n错误: {e}\n原始响应: {json.dumps(response_data, indent=2, ensure_ascii=False)}"

            self.log_to_gui("ErrorAnalysis", "成功获取 API 分析结果。", "info")

        except requests.exceptions.Timeout:
             error_msg = "[ErrorAnalysis]API 请求超时。请检查网络或增加超时时间。"
             self.log_to_gui("ErrorAnalysis", error_msg, "error")
             analysis_result = error_msg
        except requests.exceptions.HTTPError as e:
             status_code = e.response.status_code
             error_details = "N/A"
             try:
                 # Attempt to parse JSON error details from response body
                 error_json = e.response.json()
                 error_details = error_json.get("error", {}).get("message", e.response.text[:500])
             except json.JSONDecodeError:
                 # If not JSON, use raw response text preview
                 error_details = e.response.text[:500] if hasattr(e.response, 'text') else "N/A"

             if status_code == 401: # Often indicates invalid API key
                  error_msg = f"[ErrorAnalysis]API 请求错误 401 (Unauthorized): API 密钥无效或认证失败。\n请检查 API 密钥设置。\n详情: {error_details}"
             elif status_code == 403: # Often indicates permission issues or wrong model
                  error_msg = f"[ErrorAnalysis]API 请求错误 403 (Forbidden): 权限不足或模型不可用。\n请检查 API 密钥权限及模型选择。\n详情: {error_details}"
             elif status_code == 404: # Endpoint not found
                 error_msg = f"[ErrorAnalysis]API 请求错误 404 (Not Found): 无法找到指定的 API 端点或模型。\n请确认 API 接口地址 ({api_endpoint_corrected}) 和模型名称是否正确。\n详情: {error_details}"
             elif status_code == 400: # Bad Request
                 error_msg = f"[ErrorAnalysis]API 请求错误 400 (Bad Request): 请求格式错误或 API 密钥无效/缺失。\n请检查 API 密钥及请求内容。\n详情: {error_details}"
             elif status_code == 429: # Rate limited
                  error_msg = f"[ErrorAnalysis]API 请求错误 429 (Too Many Requests): 超出配额限制。\n请稍后再试或检查您的 API 配额。\n详情: {error_details}"
             else: # Other HTTP errors
                 error_msg = f"[ErrorAnalysis]API 请求失败 (HTTP {status_code})。\n详情: {error_details}"

             print(f"[Launcher ERROR] {error_msg}")
             self.log_to_gui("ErrorAnalysis", error_msg, "error") # Log formatted error
             analysis_result = error_msg
        except requests.exceptions.RequestException as e:
             error_msg = f"[ErrorAnalysis]API 请求错误: 网络或连接问题。\n请检查网络连接和 API 端点 ({api_endpoint_corrected})。\n详情: {e}"
             print(f"[Launcher ERROR] {error_msg}")
             self.log_to_gui("ErrorAnalysis", error_msg, "error")
             analysis_result = error_msg
        except json.JSONDecodeError as e:
             error_msg = f"[ErrorAnalysis]API 响应错误: 无法解析响应 (非有效 JSON)。\n来自: {api_endpoint_corrected}\n错误: {e}"
             response_text_preview = response.text[:500] if 'response' in locals() and hasattr(response, 'text') else "N/A"
             print(f"[Launcher ERROR] {error_msg}. Response Preview: {response_text_preview}")
             self.log_to_gui("ErrorAnalysis", error_msg, "error")
             analysis_result = error_msg
        except Exception as e:
            error_msg = f"[ErrorAnalysis]API 请求错误: 发生意外错误。\n详情: {e}"
            print(f"[Launcher ERROR] {error_msg}", exc_info=True)
            self.log_to_gui("ErrorAnalysis", error_msg, "error")
            analysis_result = error_msg
        finally:
             # Display the final result (either successful analysis or error message)
             self.root.after(0, lambda res=analysis_result: self._display_analysis_result(res))
             self.log_to_gui("ErrorAnalysis", f"--- 诊断结束 ---", "info")
             # UI update happens in worker's finally block

    # MOD4: Helper to display analysis result in the GUI thread
    def _display_analysis_result(self, result_text):
         """Inserts the final analysis result into the error_analysis_text widget."""
         if not hasattr(self, 'error_analysis_text') or not self.error_analysis_text.winfo_exists():
              print("[Launcher WARNING] Cannot display analysis result, widget not found.")
              return
         try:
             self.error_analysis_text.config(state=tk.NORMAL)
             # Keep previous content? Or replace? User request implies replacing.
             # self.error_analysis_text.delete('1.0', tk.END) # Already cleared before sending
             self.insert_output(self.error_analysis_text, result_text, tag="api_output") # Use api_output tag
             self.error_analysis_text.config(state=tk.DISABLED)
             # Trigger UI state update as the analysis output is now populated
             self.root.after(0, self._update_ui_state)
         except tk.TclError as e:
             print(f"[Launcher ERROR] TclError displaying analysis result: {e}")


    def run_fix(self):
        """(Simulates) executing commands from the error analysis output."""
        # MOD2: Check if modal is open
        if self._node_history_modal_window and self._node_history_modal_window.winfo_exists():
             messagebox.showwarning("操作进行中", "请先关闭节点版本历史弹窗。", parent=self.root)
             return
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中...", "warn")
             return

        analysis_output = ""
        try:
            if hasattr(self, 'error_analysis_text') and self.error_analysis_text.winfo_exists():
                 analysis_output = self.error_analysis_text.get("1.0", tk.END).strip()
        except tk.TclError:
            pass

        if not analysis_output:
             messagebox.showwarning("无输出", "错误分析输出为空，无法执行修复。", parent=self.root)
             return

        lines = analysis_output.splitlines()
        commands_to_simulate = []
        capture_commands = False
        for line in lines:
            line_clean = line.strip()
            # Look for common markers including code block start
            # Added case-insensitivity for code block markers
            if "建议执行的修复操作" in line_clean or "建议执行的命令" in line_clean:
                 capture_commands = True
                 continue
            elif line_clean.lower().startswith("```"):
                 if capture_commands: # End of a code block
                      capture_commands = False
                 else: # Start of a code block
                      capture_commands = True
                 continue # Skip the marker line itself


            if capture_commands:
                 if not line_clean:
                     continue
                 # Remove potential comment/prompt prefixes
                 potential_cmd = line_clean.lstrip('#').lstrip('$').strip()
                 # Basic check for common command starts, case-insensitive
                 if potential_cmd and any(potential_cmd.lower().startswith(cmd) for cmd in ["cd ", "git ", "pip ", "{git_exe}", "{python_exe}", "rm ", "del ", "mv ", "move ", "mkdir ", "conda ", "python "]):
                      commands_to_simulate.append(potential_cmd)

        if not commands_to_simulate:
             self.log_to_gui("ErrorAnalysis", "在诊断输出中未检测到建议的修复命令。", "warn")
             messagebox.showinfo("无修复命令", "在诊断输出中未找到建议执行的修复命令。", parent=self.root)
             return

        confirm_msg = f"检测到以下 {len(commands_to_simulate)} 条建议修复命令：\n\n" + "\n".join(f"- {cmd}" for cmd in commands_to_simulate) + "\n\n将模拟执行这些命令并在下方显示过程。\n注意：这不会实际修改您的文件系统。\n\n是否开始模拟修复？"
        confirm = messagebox.askyesno("确认模拟修复", confirm_msg, parent=self.root)
        if not confirm:
            return

        self.log_to_gui("ErrorAnalysis", "\n--- 开始模拟修复流程 ---", "info")
        # No need to update UI state here, worker thread handles it
        # self._update_ui_state() # Disable buttons

        # Queue the simulation task
        self.update_task_queue.put((self._run_fix_simulation_task, [commands_to_simulate], {}))


    def _run_fix_simulation_task(self, commands_to_simulate):
        """Task to simulate executing a list of commands. Runs in worker thread."""
        if self.stop_event.is_set():
            return
        self.log_to_gui("ErrorAnalysis", "准备模拟执行修复命令...", "info")

        # Use current values for paths
        comfyui_nodes_dir_fmt = self.comfyui_nodes_dir if self.comfyui_nodes_dir else "[custom_nodes 目录未设置]"
        git_exe_fmt = self.git_exe_path if self.git_exe_path else "[Git路径未设置]"
        python_exe_fmt = self.comfyui_portable_python if self.comfyui_portable_python else "[Python路径未设置]"
        comfyui_dir_fmt = self.comfyui_install_dir if self.comfyui_install_dir else "[ComfyUI目录未设置]"

        simulated_cwd = comfyui_dir_fmt # Start in ComfyUI directory

        for index, cmd_template in enumerate(commands_to_simulate):
             if self.stop_event.is_set():
                 break

             # Perform replacements case-insensitively and handle potential issues
             cmd_string = cmd_template
             # Use .get() on StringVars to get current values
             comfyui_nodes_dir_val = self.comfyui_nodes_dir if self.comfyui_nodes_dir else "[custom_nodes 目录未设置]"
             git_exe_val = self.git_exe_path_var.get() if self.git_exe_path_var.get() and os.path.isfile(self.git_exe_path_var.get()) else "[Git路径未设置]"
             python_exe_val = self.python_exe_var.get() if self.python_exe_var.get() and os.path.isfile(self.python_exe_var.get()) else "[Python路径未设置]"
             comfyui_dir_val = self.comfyui_install_dir if self.comfyui_install_dir and os.path.isdir(self.comfyui_install_dir) else "[ComfyUI目录未设置]"


             cmd_string = cmd_string.replace("{comfyui_nodes_dir}", comfyui_nodes_dir_val, 1) # Replace only once
             cmd_string = cmd_string.replace("{git_exe}", git_exe_val, 1)
             cmd_string = cmd_string.replace("{python_exe}", python_exe_val, 1)
             cmd_string = cmd_string.replace("{comfyui_dir}", comfyui_dir_val, 1)


             self.log_to_gui("ErrorAnalysis", f"\n[{index+1}/{len(commands_to_simulate)}] 模拟执行 (CWD: {simulated_cwd}):", "cmd")
             self.log_to_gui("ErrorAnalysis", f"$ {cmd_string}", "cmd")

             time.sleep(0.5) # Short delay
             if self.stop_event.is_set():
                 break

             simulated_output = "(模拟输出)"
             cmd_lower = cmd_string.lower().strip()

             if cmd_lower.startswith("cd "):
                 try:
                     new_dir = cmd_string[3:].strip()
                     # Handle potential variable replacements in cd path (already done above, but double-check)
                     new_dir = new_dir.replace("{comfyui_nodes_dir}", comfyui_nodes_dir_val)\
                                      .replace("{comfyui_dir}", comfyui_dir_val)

                     if os.path.isabs(new_dir):
                         simulated_cwd = new_dir
                     elif simulated_cwd.startswith("["): # If current cwd is a placeholder
                          simulated_cwd = f"{simulated_cwd}/{new_dir}" # Append to placeholder
                     else:
                         simulated_cwd = os.path.normpath(os.path.join(simulated_cwd, new_dir))
                     simulated_output = f"(模拟: 工作目录切换到 {simulated_cwd})"
                 except Exception as e:
                     simulated_output = f"(模拟: 无法解析 cd 路径: {e})"
                 self.log_to_gui("ErrorAnalysis", simulated_output, "info")

             elif "git pull" in cmd_lower:
                  simulated_output = "(模拟输出)\n模拟: 拉取远程更改...\n模拟: Already up to date."
                  self.log_to_gui("ErrorAnalysis", simulated_output, "stdout")
             elif "pip install" in cmd_lower or "python -m pip install" in cmd_lower:
                  simulated_output = "(模拟输出)\n模拟: 检查依赖...\n模拟: Requirement already satisfied."
                  self.log_to_gui("ErrorAnalysis", simulated_output, "stdout")
             elif "git clone" in cmd_lower:
                  simulated_output = "(模拟输出)\n模拟: 克隆仓库...\n模拟: 克隆完成。\n模拟: 尝试执行 Git checkout main..." # Simulate checkout after clone
                  self.log_to_gui("ErrorAnalysis", simulated_output, "stdout")
             elif "git checkout" in cmd_lower:
                  simulated_output = "(模拟输出)\n模拟: 切换分支/提交...\n模拟: Checkout complete."
                  self.log_to_gui("ErrorAnalysis", simulated_output, "stdout")
             elif "git reset" in cmd_lower:
                  simulated_output = "(模拟输出)\n模拟: 重置仓库状态...\n模拟: Reset complete."
                  self.log_to_gui("ErrorAnalysis", simulated_output, "stdout")
             elif "git submodule update" in cmd_lower:
                  simulated_output = "(模拟输出)\n模拟: 更新子模块..."
                  self.log_to_gui("ErrorAnalysis", simulated_output, "stdout")
             elif cmd_lower.startswith("rm ") or cmd_lower.startswith("del "):
                  simulated_output = "(模拟输出)\n模拟: 删除文件/目录..."
                  self.log_to_gui("ErrorAnalysis", simulated_output, "stdout")
             else:
                  self.log_to_gui("ErrorAnalysis", "(模拟: 命令执行完成)", "stdout")


        if self.stop_event.is_set():
             self.log_to_gui("ErrorAnalysis", "\n--- 模拟修复流程被取消 ---", "warn")
        else:
             self.log_to_gui("ErrorAnalysis", "\n--- 模拟修复流程结束 ---", "info")


    # --- UI State and Helpers ---
    def _update_ui_state(self):
        """Central function to update all button states and status label."""
        # Schedule the actual update to happen soon in the main GUI thread
        self.root.after(0, self._do_update_ui_state)

    def _do_update_ui_state(self):
        """The actual UI update logic, called by root.after."""
        # Ensure root window and necessary widgets exist before trying to configure them
        if not self.root or not self.root.winfo_exists():
             return

        comfy_running_internally = self._is_comfyui_running()
        comfy_detected_externally = self.comfyui_externally_detected
        update_task_running = self._is_update_task_running()
        is_starting_stopping_comfy = False # Flag for ComfyUI specific start/stop state
        is_progress_bar_running = False

        try: # Check progress bar state safely
            if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists():
                 is_progress_bar_running = self.progress_bar.winfo_ismapped() and self.progress_bar.cget('mode') == 'indeterminate'
                 label_text = self.status_label.cget("text") if hasattr(self, 'status_label') and self.status_label.winfo_exists() else ""
                 # Check if status label indicates ComfyUI specific start/stop
                 if any(status_text in label_text for status_text in ["启动 ComfyUI", "停止 ComfyUI", "停止所有服务"]):
                      is_starting_stopping_comfy = True

        except tk.TclError:
            is_progress_bar_running = False # Assume not running if widget gone
            is_starting_stopping_comfy = False

        status_text = "状态: 服务已停止" # Default status
        main_stop_style = "Stop.TButton"
        run_comfyui_enabled = tk.DISABLED # Defaults
        stop_all_enabled = tk.DISABLED

        # Determine Status and Global Button States
        comfy_can_run_paths = self._validate_paths_for_execution(check_comfyui=True, check_git=False, show_error=False)
        git_path_ok = self._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=False)

        if update_task_running:
            status_text = "状态: 更新/维护任务进行中..."
            stop_all_enabled = tk.NORMAL # Allow stopping update task
            main_stop_style = "StopRunning.TButton"
            # Run button disabled while any update task is running
            run_comfyui_enabled = tk.DISABLED
        elif is_starting_stopping_comfy: # Catches ComfyUI specific start/stop phases specifically
             try:
                 if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                      status_text = self.status_label.cget("text") # Keep existing status during transitions
                 else:
                      status_text = "状态: ComfyUI 启动/停止中..."
             except tk.TclError:
                 status_text = "状态: ComfyUI 启动/停止中..."
             run_comfyui_enabled = tk.DISABLED # Disabled while starting/stopping ComfyUI
             stop_all_enabled = tk.NORMAL
             main_stop_style = "StopRunning.TButton"
        elif comfy_detected_externally:
            status_text = f"状态: 外部 ComfyUI 运行中 (端口 {self.comfyui_api_port_var.get()})" # Use current port from var
            run_comfyui_enabled = tk.DISABLED
            stop_all_enabled = tk.DISABLED # Cannot stop external process
        elif comfy_running_internally:
            status_text = "状态: ComfyUI 后台运行中"
            main_stop_style = "StopRunning.TButton"
            run_comfyui_enabled = tk.DISABLED # Disabled once running
            stop_all_enabled = tk.NORMAL
        else: # Idle state (Neither ComfyUI running/detected/starting/stopping, nor update task running)
            status_text = "状态: 服务已停止"
            # Run button enabled only if paths are valid and nothing is currently running
            run_comfyui_enabled = tk.NORMAL if comfy_can_run_paths else tk.DISABLED
            stop_all_enabled = tk.DISABLED


        # Update Progress Bar (Active if update task running OR comfyui starting/stopping is indicated by label)
        try:
            if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists():
                # Progress bar should run if any background task is active (update_task_running)
                # OR if the status label indicates ComfyUI specific start/stop phase.
                should_run_progress = update_task_running or is_starting_stopping_comfy

                if should_run_progress and not is_progress_bar_running:
                    self.progress_bar.start(10)
                elif not should_run_progress and is_progress_bar_running:
                    self.progress_bar.stop()
        except tk.TclError:
            pass


        # Update Status Label
        try:
            if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                 self.status_label.config(text=status_text)
        except tk.TclError:
            pass

        # Update Global Run/Stop Buttons
        try:
            if hasattr(self, 'run_all_button') and self.run_all_button.winfo_exists():
                 self.run_all_button.config(state=run_comfyui_enabled)
            if hasattr(self, 'stop_all_button') and self.stop_all_button.winfo_exists():
                 self.stop_all_button.config(state=stop_all_enabled, style=main_stop_style)
        except tk.TclError:
            pass

        # --- Update Management Tab Buttons ---
        # Base state for *most* update buttons: Enabled if git OK AND no update/start/stop task running AND modal is closed
        modal_is_open = self._node_history_modal_window is not None and self._node_history_modal_window.winfo_exists()
        base_update_enabled = tk.NORMAL if git_path_ok and not update_task_running and not is_starting_stopping_comfy and not modal_is_open else tk.DISABLED

        try:
            # Main Body Tab
            if hasattr(self, 'refresh_main_body_button') and self.refresh_main_body_button.winfo_exists():
                 self.refresh_main_body_button.config(state=base_update_enabled)

            if hasattr(self, 'activate_main_body_button') and self.activate_main_body_button.winfo_exists():
                 item_selected_main = False
                 if hasattr(self, 'main_body_tree') and self.main_body_tree.winfo_exists():
                     item_selected_main = bool(self.main_body_tree.focus())

                 comfy_dir_is_repo = False
                 if self.comfyui_install_dir and os.path.isdir(self.comfyui_install_dir):
                      comfy_dir_is_repo = os.path.isdir(os.path.join(self.comfyui_install_dir, ".git"))

                 # Activate requires base enabled, item selected, ComfyUI dir is git repo AND ComfyUI not running/detected
                 activate_enabled_state = tk.DISABLED
                 if base_update_enabled == tk.NORMAL and item_selected_main and comfy_dir_is_repo and not comfy_running_internally and not comfy_detected_externally:
                      activate_enabled_state = tk.NORMAL

                 self.activate_main_body_button.config(state=activate_enabled_state)

            # Nodes Tab
            item_selected_nodes = False
            if hasattr(self, 'nodes_tree') and self.nodes_tree.winfo_exists():
                 item_selected_nodes = bool(self.nodes_tree.focus())

            node_is_installed = False; node_is_git = False; node_has_url = False
            if item_selected_nodes and hasattr(self, 'nodes_tree') and self.nodes_tree.winfo_exists() and self.comfyui_nodes_dir: # Check nodes_dir exists
                 try:
                      node_data = self.nodes_tree.item(self.nodes_tree.focus(), 'values')
                      if node_data and len(node_data) >= 5:
                           node_name_selected = node_data[0]; node_status = node_data[1]; repo_url = node_data[4]
                           node_is_installed = (node_status == "已安装")
                           node_has_url = bool(repo_url) and repo_url not in ("本地安装，无Git信息", "无法获取远程 URL", "本地安装", "N/A", "无远程仓库")
                           # Try finding in cached list first
                           found_node_info = next((n for n in self.local_nodes_only if n.get("name") == node_name_selected), None)
                           if found_node_info:
                               node_is_git = found_node_info.get("is_git", False)
                           else:
                                # Fallback check by path if not in local_nodes_only (shouldn't happen if list is fresh?)
                                node_install_path = os.path.normpath(os.path.join(self.comfyui_nodes_dir, node_name_selected))
                                node_is_git = os.path.isdir(node_install_path) and os.path.isdir(os.path.join(node_install_path, ".git"))

                 except Exception as e:
                     print(f"[Launcher DEBUG] Error getting node state: {e}") # Log error but continue

            # Search entry and button enabled if no update/start/stop task running AND modal is closed
            search_enabled = tk.NORMAL if not update_task_running and not is_starting_stopping_comfy and not modal_is_open else tk.DISABLED
            if hasattr(self, 'nodes_search_entry') and self.nodes_search_entry.winfo_exists():
                self.nodes_search_entry.config(state=search_enabled)
            if hasattr(self, 'search_nodes_button') and self.search_nodes_button.winfo_exists():
                self.search_nodes_button.config(state=search_enabled)
            if hasattr(self, 'refresh_nodes_button') and self.refresh_nodes_button.winfo_exists():
                self.refresh_nodes_button.config(state=base_update_enabled)

            # Switch/Install Button Logic:
            # Enabled if base enabled, item selected, ComfyUI not running, AND (can switch OR can install)
            can_switch = node_is_installed and node_is_git and node_has_url # Need git repo for history/switch
            can_install = not node_is_installed and node_has_url # Need remote URL to install
            switch_install_final_state = tk.DISABLED
            if base_update_enabled == tk.NORMAL and item_selected_nodes and (can_switch or can_install) and not comfy_running_internally and not comfy_detected_externally:
                switch_install_final_state = tk.NORMAL

            if hasattr(self, 'switch_install_node_button') and self.switch_install_node_button.winfo_exists():
                 # Text changes based on selection state
                 button_text = "切换版本" # Default
                 if item_selected_nodes: # Only change text if an item is actually selected
                      button_text = "切换版本" if node_is_installed and node_is_git else "安装节点" if node_has_url else "切换版本"

                 self.switch_install_node_button.config(state=switch_install_final_state, text=button_text)


            # Uninstall Button Logic:
            # Enabled if base enabled, item selected, installed, AND ComfyUI not running
            uninstall_final_state = tk.DISABLED
            if base_update_enabled == tk.NORMAL and item_selected_nodes and node_is_installed and not comfy_running_internally and not comfy_detected_externally:
                 uninstall_final_state = tk.NORMAL
            if hasattr(self, 'uninstall_node_button') and self.uninstall_node_button.winfo_exists():
                 self.uninstall_node_button.config(state=uninstall_final_state)

            # Update All Button Logic:
            # Enabled if base enabled AND ComfyUI not running
            update_all_final_state = tk.DISABLED
            if base_update_enabled == tk.NORMAL and not comfy_running_internally and not comfy_detected_externally:
                 update_all_final_state = tk.NORMAL
            if hasattr(self, 'update_all_nodes_button') and self.update_all_nodes_button.winfo_exists():
                 self.update_all_nodes_button.config(state=update_all_final_state)

            # Analysis Tab Buttons
            api_endpoint_set = bool(self.error_api_endpoint_var.get().strip())
            api_key_set = bool(self.error_api_key_var.get().strip()) # MOD4: Check key presence
            # Diagnose enabled if API endpoint AND key are set, AND no update/start/stop task running AND modal is closed
            diagnose_enabled_state = tk.DISABLED
            if api_endpoint_set and api_key_set and not update_task_running and not is_starting_stopping_comfy and not modal_is_open:
                 diagnose_enabled_state = tk.NORMAL

            if hasattr(self, 'diagnose_button') and self.diagnose_button.winfo_exists():
                 self.diagnose_button.config(state=diagnose_enabled_state)

            # Fix button is enabled if diagnose is enabled AND an update/fix task is NOT running, AND there is content in the analysis output AND modal is closed
            analysis_has_content = False
            try:
                if hasattr(self, 'error_analysis_text') and self.error_analysis_text.winfo_exists():
                    # Check if the text widget has any content other than the initial state
                    analysis_has_content = bool(self.error_analysis_text.get("1.0", "end-1c").strip()) # end-1c to ignore trailing newline
            except tk.TclError:
                pass

            fix_enabled_state = tk.DISABLED
            if diagnose_enabled_state == tk.NORMAL and analysis_has_content and not update_task_running and not is_starting_stopping_comfy and not modal_is_open:
                 fix_enabled_state = tk.NORMAL

            if hasattr(self, 'fix_button') and self.fix_button.winfo_exists():
                 self.fix_button.config(state=fix_enabled_state)

            # User request text area is enabled if no update/start/stop task running AND modal is closed
            user_request_enabled_state = tk.DISABLED
            if not update_task_running and not is_starting_stopping_comfy and not modal_is_open:
                user_request_enabled_state = tk.NORMAL
            if hasattr(self, 'user_request_text') and self.user_request_text.winfo_exists():
                 # Use 'normal' or 'disabled' state for ScrolledText
                 widget_state = tk.NORMAL if user_request_enabled_state == tk.NORMAL else tk.DISABLED
                 self.user_request_text.config(state=widget_state)


        except tk.TclError as e:
            print(f"[Launcher WARNING] Error updating UI state (widget might not exist): {e}")
        except AttributeError as e:
            print(f"[Launcher WARNING] Error updating UI state (attribute missing): {e}")
        except Exception as e:
            print(f"[Launcher ERROR] Unexpected error updating UI state: {e}")


    def reset_ui_on_error(self):
        """Resets UI state after a service encounters an error."""
        print("[Launcher INFO] Resetting UI on error.")
        try:
            # Stop progress bar if it's running
            if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists() and self.progress_bar.winfo_ismapped():
                self.progress_bar.stop()
        except tk.TclError:
            pass

        # Ensure internal state flags are reset
        if self.comfyui_process and self.comfyui_process.poll() is not None:
            self.comfyui_process = None
        self.stop_event.clear()
        self.backend_browser_triggered_for_session = False
        self.comfyui_ready_marker_sent = False
        # Keep external detection status as it might still be running outside
        # self.comfyui_externally_detected = False # Maybe don't reset this on *internal* error?

        self._update_task_running = False # Ensure task flag is clear

        # Attempt to cleanup modal if it's open (error might have happened during history fetch)
        if self._node_history_modal_window and self._node_history_modal_window.winfo_exists():
             self._cleanup_modal_state(self._node_history_modal_window)


        self.root.after(0, self._update_ui_state)


    def _trigger_comfyui_browser_opening(self):
        """Opens the ComfyUI URL in a web browser when ComfyUI is ready."""
        comfy_is_active = self._is_comfyui_running() or self.comfyui_externally_detected
        if comfy_is_active and not self.backend_browser_triggered_for_session:
            self.backend_browser_triggered_for_session = True
            self.root.after(100, self._open_frontend_browser) # Slight delay to ensure port is fully open
        elif not comfy_is_active:
             print("[Launcher DEBUG] Browser trigger skipped - ComfyUI stopped or not detected.")


    def _open_frontend_browser_from_settings(self):
        """Opens the ComfyUI URL configured in settings."""
        try:
            # Get the current port value from the StringVar
            port_str = self.comfyui_api_port_var.get()
            port = int(port_str)
            if not (1 <= port <= 65535):
                 raise ValueError("Port out of range 1-65535")
            comfyui_url = f"http://127.0.0.1:{port}"
            self._open_url_in_browser(comfyui_url)
        except ValueError:
             messagebox.showerror("端口无效", f"设置中的端口号无效: '{self.comfyui_api_port_var.get()}'。", parent=self.root)
             self.log_to_gui("Launcher", f"打开浏览器失败: 无效端口 '{self.comfyui_api_port_var.get()}'", "error")
        except Exception as e:
             messagebox.showerror("打开失败", f"无法打开浏览器:\n{e}", parent=self.root)
             self.log_to_gui("Launcher", f"打开浏览器失败: {e}", "error")


    def _open_frontend_browser(self):
        """Opens the ComfyUI backend URL derived from config."""
        # Ensure derived paths are up-to-date before getting the port
        self.update_derived_paths()
        try:
            # Use the derived port (from config, updated by update_derived_paths)
            port = int(self.comfyui_api_port)
            if not (1 <= port <= 65535):
                 raise ValueError("Invalid derived port")
            comfyui_url = f"http://127.0.0.1:{port}"
            self._open_url_in_browser(comfyui_url)
        except ValueError:
             print(f"[Launcher ERROR] Invalid derived API port during auto-open: {self.comfyui_api_port}. Skipping browser open.")
        except Exception as e:
             print(f"[Launcher ERROR] Error opening browser tab for ComfyUI URL: {e}")


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
        # MOD6: Only clear ComfyUI and Analysis logs, preserve Launcher logs
        widgets_to_clear = []
        if hasattr(self, 'main_output_text'):
            widgets_to_clear.append(self.main_output_text) # ComfyUI Log
        # if hasattr(self, 'launcher_log_text'): widgets_to_clear.append(self.launcher_log_text) # Launcher Log - REMOVED as per MOD6
        if hasattr(self, 'error_analysis_text'):
            widgets_to_clear.append(self.error_analysis_text) # Analysis Log
        # MOD5: Also clear User Request text box
        if hasattr(self, 'user_request_text'):
            widgets_to_clear.append(self.user_request_text)

        self.log_to_gui("Launcher", "清空 ComfyUI 日志、用户诉求和分析区域...", "info") # Update log message

        for widget in widgets_to_clear:
            try:
                if widget and widget.winfo_exists():
                    widget.config(state=tk.NORMAL)
                    widget.delete('1.0', tk.END)
                    # Set state back - Analysis/ComfyUI logs disabled, User request normal
                    is_output_log = widget == self.error_analysis_text or widget == self.main_output_text
                    widget.config(state=tk.DISABLED if is_output_log else tk.NORMAL)
            except tk.TclError:
                pass


    # Method to handle 'git pull pause' for the launcher itself
    def _run_git_pull_pause(self):
        """Runs 'git pull' for the launcher's own repository in a new terminal window and pauses."""
        git_exe = self.git_exe_path_var.get()
        if not git_exe or not os.path.isfile(git_exe):
            messagebox.showerror("Git 未找到", f"未找到或未配置 Git 可执行文件:\n{git_exe}\n请在“设置”中配置。", parent=self.root)
            self.log_to_gui("Launcher", f"Git pull 失败: Git 路径无效 '{git_exe}'", "error")
            return

        # Use the base directory of the currently running script
        launcher_dir = BASE_DIR
        if not os.path.isdir(os.path.join(launcher_dir, ".git")):
            messagebox.showerror("非 Git 仓库", f"当前启动器目录不是一个有效的 Git 仓库:\n{launcher_dir}\n无法执行 Git pull。", parent=self.root)
            self.log_to_gui("Launcher", f"Git pull 失败: '{launcher_dir}' 不是 Git 仓库", "error")
            return

        self.log_to_gui("Launcher", f"准备执行 'git pull' 于目录: {launcher_dir}", "info")

        try:
            # Construct the command based on OS to run in a new terminal and pause
            command_parts = []
            if platform.system() == "Windows":
                # Use start cmd /k for a new window that stays open
                # Quote paths with spaces
                quoted_launcher_dir = shlex.quote(launcher_dir)
                quoted_git_exe = shlex.quote(git_exe)
                # Use && to chain commands. pause > nul waits for keypress without output.
                cmd_string = f'cd /d {quoted_launcher_dir} && {quoted_git_exe} pull --prune && echo. && echo 操作完成，按任意键关闭此窗口... && pause > nul'
                # Use CREATE_NEW_CONSOLE to ensure it's a separate window
                subprocess.Popen(['cmd', '/c', f'start cmd /k "{cmd_string}"'], creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.DETACHED_PROCESS)

            elif platform.system() == "Darwin": # macOS
                 script = f'''
                 tell application "Terminal"
                     activate
                     do script "cd {shlex.quote(launcher_dir)}; {shlex.quote(git_exe)} pull --prune; echo \\"操作完成，按 Enter 关闭窗口...\\"; read; exit"
                 end tell
                 '''
                 # Run AppleScript via osascript
                 subprocess.run(['osascript', '-e', script], check=True)

            else: # Linux and other Unix-like
                terminal_emulator = "xterm" # Default fallback
                # Attempt to find a more common terminal emulator
                for term in ["gnome-terminal", "konsole", "xfce4-terminal", "lxterminal", "urxvt"]:
                     if shutil.which(term):
                          terminal_emulator = term
                          break
                quoted_launcher_dir = shlex.quote(launcher_dir)
                quoted_git_exe = shlex.quote(git_exe)
                # Use -e to execute a command string in the terminal
                # Chain commands with &&, use read for pause, then exit
                cmd_in_terminal = f'bash -c "cd {quoted_launcher_dir} && {quoted_git_exe} pull --prune && echo \\"操作完成，按 Enter 关闭窗口...\\" && read && exit"'
                command_parts = [terminal_emulator, "-e", cmd_in_terminal]
                subprocess.Popen(command_parts)

            self.log_to_gui("Launcher", "'git pull' 命令已在新终端窗口启动。", "info")

        except FileNotFoundError as e:
             terminal_name = "cmd" if platform.system() == "Windows" else (terminal_emulator if platform.system() != "Darwin" else "Terminal (AppleScript)")
             messagebox.showerror("启动终端失败", f"无法找到终端命令 ({terminal_name}):\n{e}\n请检查您的系统配置或安装必要的终端。", parent=self.root)
             self.log_to_gui("Launcher", f"启动终端失败: {e}", "error")
        except Exception as e:
            messagebox.showerror("执行失败", f"执行 'git pull' 时发生错误:\n{e}", parent=self.root)
            self.log_to_gui("Launcher", f"执行 'git pull' 失败: {e}", "error")


    # MOD4: Implement saving logs on close
    def on_closing(self):
        """Handles the application closing event, stops services, saves logs, and destroys window."""
        print("[Launcher INFO] Closing application requested.")

        # --- MOD4: Save Logs Before Closing ---
        self.log_to_gui("Launcher", "正在保存日志...", "info")
        launcher_logs_content = ""
        comfyui_logs_content = ""

        try:
            if hasattr(self, 'launcher_log_text') and self.launcher_log_text.winfo_exists():
                 # Get all text from Launcher log
                 launcher_logs_content = self.launcher_log_text.get("1.0", tk.END).strip()
            if hasattr(self, 'main_output_text') and self.main_output_text.winfo_exists():
                 # Get all text from ComfyUI log
                 comfyui_logs_content = self.main_output_text.get("1.0", tk.END).strip()

            # Format the combined log content as specified
            combined_log_content = f"""
@@@@@@@@@ComLauncher日志
{launcher_logs_content if launcher_logs_content else "（无）"}

@@@@@@@@@ComfyUI日志
{comfyui_logs_content if comfyui_logs_content else "（无）"}
"""
            # Ensure log file is in the base directory
            log_file_path = os.path.join(BASE_DIR, "ComLauncher.org")
            with open(log_file_path, 'w', encoding='utf-8') as f:
                 f.write(combined_log_content.strip()) # Strip leading/trailing whitespace from the formatted block
            print(f"[Launcher INFO] Logs saved to {log_file_path}")
        except Exception as e:
            print(f"[Launcher ERROR] Failed to save logs on closing: {e}")
            # Do not show a messagebox here, just log the error


        # --- Stop Services ---
        # Check if any managed process is running
        process_running = self._is_comfyui_running()
        task_running = self._is_update_task_running()

        if process_running or task_running:
             confirm_stop = messagebox.askyesno("进程运行中", "有后台进程（ComfyUI 或更新任务）正在运行。\n是否在退出前停止？", parent=self.root)
             if confirm_stop:
                 self.log_to_gui("Launcher", "正在停止后台进程...", "info")
                 self.stop_all_services() # This signals threads and handles ComfyUI process
                 wait_timeout = 15 # seconds
                 start_time = time.time()
                 # Wait for processes/tasks to signal completion (by clearing flags)
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
                      # Attempt to kill subprocesses if they are still alive
                      if self.comfyui_process and self.comfyui_process.poll() is None:
                           try:
                               self.comfyui_process.kill()
                           except Exception:
                               pass
                      # The worker thread should ideally respond to stop_event, but if not, it's daemon and will exit with app

                 # Processes should be stopped by now, or will be killed on exit.
                 # Now safe to destroy the GUI.
                 try:
                      if self.root and self.root.winfo_exists():
                          self.root.destroy()
                 except tk.TclError:
                     pass # Ignore if already destroyed

             else:
                  # User chose not to stop, signal threads to stop if possible, then destroy GUI
                  print("[Launcher INFO] User chose not to stop processes, attempting direct termination.")
                  self.stop_event.set() # Signal worker thread
                  if self.comfyui_process and self.comfyui_process.poll() is None:
                       try:
                           self.comfyui_process.terminate() # Try graceful termination first
                       except Exception:
                           pass
                  # GUI will be destroyed below

        # --- Destroy GUI ---
        # Ensure the GUI is destroyed whether or not processes were running/stopped
        try:
             if self.root and self.root.winfo_exists():
                 self.root.destroy()
        except tk.TclError:
            pass


# --- Main Execution ---
if __name__ == "__main__":
    root = None # Define root outside try for error handling
    app = None # Define app outside try
    try:
        # Fix blurry fonts on Windows high DPI displays
        if platform.system() == "Windows":
            try:
                # Check if SetProcessDpiAwareness is available (Windows 8.1+)
                # and if the process is not already DPI aware (e.g., via manifest)
                # If SetProcessDpiAwareness(2) (Per Monitor V2) is preferred, use that.
                # For simplicity, SetProcessDpiAwareness(1) (System) is common.
                # Check if DPI awareness is already set to avoid errors
                from ctypes import windll, POINTER, c_void_p, c_uint, Structure, byref

                try:
                    # Try using SetProcessDpiAwareness first (more modern approach)
                    SetProcessDpiAwareness = windll.shcore.SetProcessDpiAwareness
                    # Try setting awareness (System)
                    # Returns HRESULT, 0 usually means success. E_ACCESSDENIED can happen if already set.
                    # S_OK = 0, E_ACCESSDENIED = -2147024891 (or 0x80070005)
                    hresult = SetProcessDpiAwareness(1) # DPI_AWARENESS.MDT_SYSTEM_AWARE
                    print(f"[Launcher DEBUG] SetProcessDpiAwareness(1) HRESULT: {hresult}")
                    if hresult != 0 and hresult != -2147024891: # Log non-success other than ACCESSDENIED
                         print(f"[Launcher WARNING] SetProcessDpiAwareness returned unexpected HRESULT: {hresult}")

                except (AttributeError, ImportError):
                    # Fallback for older Windows or if shcore.dll not found
                    try:
                        windll.user32.SetProcessDPIAware()
                        print("[Launcher INFO] Using SetProcessDPIAware()")
                    except (AttributeError, ImportError):
                        print("[Launcher WARNING] No DPI awareness function found.")

                except Exception as e:
                    print(f"[Launcher WARNING] Failed to set DPI awareness: {e}")

            except Exception as e:
                print(f"[Launcher WARNING] Error during Windows DPI setup: {e}")


        root = tk.Tk()
        app = ComLauncherApp(root)
        root.mainloop()

    except Exception as e:
        # Unhandled exception during application startup or runtime
        print(f"[Launcher CRITICAL] Unhandled exception during application startup or runtime: {e}", exc_info=True)

        # Attempt to save logs even on crash
        try:
            launcher_logs_content = ""
            comfyui_logs_content = ""
            # Try to get logs from app instance if created
            if app:
                 try:
                     if hasattr(app, 'launcher_log_text') and app.launcher_log_text.winfo_exists():
                         launcher_logs_content = app.launcher_log_text.get("1.0", tk.END).strip()
                     if hasattr(app, 'main_output_text') and app.main_output_text.winfo_exists():
                         comfyui_logs_content = app.main_output_text.get("1.0", tk.END).strip()
                 except tk.TclError:
                     print("[Launcher CRITICAL] Error getting logs from widgets during crash handling.")
            # If app wasn't created or logs not available, indicate empty
            combined_log_content = f"""
@@@@@@@@@ComLauncher日志
{launcher_logs_content if launcher_logs_content else "（无）"}

@@@@@@@@@ComfyUI日志
{comfyui_logs_content if comfyui_logs_content else "（无）"}

@@@@@@@@@致命错误信息
{traceback.format_exc()} # Include traceback
"""
            log_file_path = os.path.join(BASE_DIR, "ComLauncher_crash.log") # Use a different name for crash logs
            with open(log_file_path, 'w', encoding='utf-8') as f:
                 f.write(combined_log_content.strip())
            print(f"[Launcher CRITICAL] Crash logs saved to {log_file_path}")
        except Exception as log_err:
             print(f"[Launcher CRITICAL] Failed to save crash logs: {log_err}")

        # Attempt to show error message box
        try:
             # Ensure a root window exists to host the messagebox
             if not root or not isinstance(root, tk.Tk) or not root.winfo_exists():
                  # Create a temporary root if the main one failed or was destroyed
                  temp_root = tk.Tk()
                  temp_root.withdraw() # Hide the temporary window
                  messagebox.showerror("致命错误 / Fatal Error", f"应用程序遇到致命错误并需要关闭：\n{e}\n错误详情已保存到 ComLauncher_crash.log 文件。", parent=temp_root)
                  temp_root.destroy() # Clean up temporary root
             else:
                  messagebox.showerror("致命错误 / Fatal Error", f"应用程序遇到致命错误并需要关闭：\n{e}\n错误详情已保存到 ComLauncher_crash.log 文件。", parent=root)

        except Exception as mb_err:
            print(f"[Launcher CRITICAL] Unable to display fatal error dialog: {mb_err}")
        finally:
             # Ensure application exits
             sys.exit(1) # Exit with error code 1