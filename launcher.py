# -*- coding: utf-8 -*-
# File: launcher.py
# Version: Kerry, Ver. 2.6.2 (Fixed Bugs + Node Double Click)

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, font as tkfont, filedialog, Toplevel
import subprocess
import os
import threading
import queue
import time
import json
import webbrowser
import requests
import socket
import platform
import sys
from datetime import datetime, timezone
import shlex
import shutil
import traceback
from functools import cmp_to_key

# Attempt to import packaging for version parsing, but allow fallback
try:
    from packaging.version import parse as parse_version, InvalidVersion
except ImportError:
    print("[Launcher WARNING] 'packaging' library not found. Version sorting fallback will be basic string comparison.")
    parse_version = None
    InvalidVersion = Exception # Define for except block

# Import UI modules
# Using absolute imports from the project root for clarity
# Ensure ui_modules directory is in sys.path if running from a different location
# (This is usually handled correctly when running python launcher.py from the project root)
try:
    from ui_modules import settings, management, logs, analysis
except ImportError as e:
    print(f"[Launcher CRITICAL] Failed to import UI modules: {e}")
    print("Please ensure the 'ui_modules' directory exists in the same directory as launcher.py")
    print("and contains settings.py, management.py, logs.py, and analysis.py.")
    sys.exit(1) # Exit if modules can't be imported

# --- Configuration File ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Updated CONFIG_FILE path to ui_modules directory
CONFIG_FILE = os.path.join(BASE_DIR, "ui_modules", "launcher_config.json")
# Updated LOG_FILE path to ui_modules directory - used only in on_closing
LOG_FILE = os.path.join(BASE_DIR, "ui_modules", "ComLauncher.org")
ICON_PATH = os.path.join(BASE_DIR, "templates", "icon.ico") # Path to icon

# --- Default Values ---
DEFAULT_COMFYUI_INSTALL_DIR = ""
DEFAULT_COMFYUI_PYTHON_EXE = ""
DEFAULT_COMFYUI_API_PORT = "8188"

# --- Performance Settings Defaults ---
DEFAULT_VRAM_MODE = "高负载(8GB以上)"
DEFAULT_CKPT_PRECISION = "半精度(FP16)"
DEFAULT_VAE_PRECISION = "半精度(FP16)"
DEFAULT_CLIP_PRECISION = "FP8 (E4M3FN)"
DEFAULT_UNET_PRECISION = "FP8 (E5M2)"
DEFAULT_CUDA_MALLOC = "启用"
DEFAULT_IPEX_OPTIMIZATION = "启用"
DEFAULT_XFORMERS_ACCELERATION = "启用"

# --- New Configuration Defaults ---
DEFAULT_GIT_EXE_PATH = r"D:\Program\ComfyUI_Program\ComfyUI\git\cmd\git.exe" if platform.system() == "Windows" else "/usr/bin/git" # Default Git path based on OS
DEFAULT_MAIN_REPO_URL = "https://gitee.com/AIGODLIKE/ComfyUI.git" # Default ComfyUI Main Repository
DEFAULT_NODE_CONFIG_URL = "https://raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main/custom-node-list.json" # Default Node Config URL
DEFAULT_ERROR_API_ENDPOINT = ""
DEFAULT_ERROR_API_KEY = ""

# MOD: Version Updated
VERSION_INFO = "Kerry, Ver. 2.6.2"

# Special marker for queue
_COMFYUI_READY_MARKER_ = "_COMFYUI_IS_READY_FOR_BROWSER_\n"


class ComLauncherApp:
    """Main class for the Tkinter application (ComLauncher)."""
    def __init__(self, root):
        """ Initializes the application. """
        self.root = root
        self.root.title("ComLauncher")
        try:
            if os.path.exists(ICON_PATH):
                self.root.iconbitmap(ICON_PATH)
            else:
                print(f"[Launcher WARNING] Icon file not found at {ICON_PATH}, using default.")
        except tk.TclError as e:
            print(f"[Launcher WARNING] Failed to set window icon: {e}")
        except Exception as e:
            print(f"[Launcher ERROR] Unexpected error setting window icon: {e}")

        self.root.geometry("1000x750")
        # MOD: Moved styling constants inside the class
        self.BG_COLOR = "#2d2d2d"
        self.CONTROL_FRAME_BG = "#353535"
        self.TAB_CONTROL_FRAME_BG = "#3c3c3c"
        self.TEXT_AREA_BG = "#1e1e1e"
        self.FG_COLOR = "#e0e0e0"
        self.FG_MUTED = "#9e9e9e"
        self.ACCENT_COLOR = "#007aff"
        self.ACCENT_ACTIVE = "#005ecb"
        self.STOP_COLOR = "#5a5a5a"
        self.STOP_ACTIVE = "#ff453a"
        self.STOP_RUNNING_BG = "#b71c1c"
        self.STOP_RUNNING_ACTIVE_BG = "#d32f2f"
        self.STOP_RUNNING_FG = "#ffffff"
        self.BORDER_COLOR = "#484848"
        self.FG_STDOUT = "#e0e0e0"
        self.FG_STDERR = "#ff6b6b"
        self.FG_INFO = "#64d1b8"
        self.FG_WARN = "#ffd700"
        self.FG_CMD = "#a0a0a0"
        self.FG_API = "#cccccc"
        self.FG_HIGHLIGHT = "#00e676"
        self.FONT_FAMILY_UI = "Segoe UI"
        self.FONT_FAMILY_MONO = "Consolas"
        self.FONT_SIZE_NORMAL = 10
        self.FONT_SIZE_MONO = 9
        self.FONT_WEIGHT_BOLD = "bold"
        self.UPDATE_INTERVAL_MS = 100 # Also a constant

        self.root.configure(bg=self.BG_COLOR)
        self.root.minsize(800, 600)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=0) # Control bar row - no expand
        self.root.rowconfigure(1, weight=1) # Notebook row - expand

        # Process and state variables
        self.comfyui_process = None
        self.comfyui_output_queue = queue.Queue()
        self.launcher_log_queue = queue.Queue()
        self.update_task_queue = queue.Queue()
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

        # Performance variables
        self.vram_mode_var = tk.StringVar()
        self.ckpt_precision_var = tk.StringVar()
        self.vae_precision_var = tk.StringVar()
        self.clip_precision_var = tk.StringVar()
        self.unet_precision_var = tk.StringVar()
        self.cuda_malloc_var = tk.StringVar()
        self.ipex_optimization_var = tk.StringVar()
        self.xformers_acceleration_var = tk.StringVar()

        # Update Management specific variables (now in management module, but need StringVar for label)
        self.current_main_body_version_var = tk.StringVar(value="未知 / Unknown") # Used by ManagementTab

        # Log text widget references (now in logs module, stored here for queue processing)
        self.launcher_log_text = None
        self.main_output_text = None
        # Logs notebook reference (now in logs module, stored here for tab switching)
        self.logs_notebook = None

        # Base project dir for file dialogs and persistence files
        self.base_project_dir = BASE_DIR

        # Store module instances
        self.modules = {}

        # Internal derived paths (updated from config variables)
        self.comfyui_install_dir = ""
        self.comfyui_portable_python = ""
        self.git_exe_path = ""
        self.comfyui_api_port = ""
        self.comfyui_nodes_dir = ""
        self.comfyui_models_dir = ""
        self.comfyui_lora_dir = ""
        self.comfyui_input_dir = ""
        self.comfyui_output_dir = ""
        self.comfyui_workflows_dir = ""
        self.comfyui_main_script = ""
        self.comfyui_base_args = []

        self.config = {} # Internal dictionary for config values

        # Initialize
        self.load_config()
        self.update_derived_paths()
        self.setup_styles()
        self.setup_ui() # This will create module instances and UI elements
        self._setup_auto_save()

        # Start background tasks
        self.root.after(self.UPDATE_INTERVAL_MS, self.process_output_queues) # Use instance constant
        self.update_worker_thread = threading.Thread(target=self._update_task_worker, daemon=True)
        self.update_worker_thread.start()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Set initial UI state and start initial background data loading *after* UI is ready
        self.root.after(0, self._update_ui_state)
        # Delay the initial data load slightly to ensure UI is fully initialized and updated first (Fix for Bug 2 & 3)
        self.root.after(500, self.start_initial_data_load)


    # --- Configuration Handling (Remains in launcher.py) ---
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
            loaded_config = {}

        comfyui_dir_loaded = loaded_config.get("comfyui_dir", DEFAULT_COMFYUI_INSTALL_DIR)

        self.config = {
            "comfyui_dir": comfyui_dir_loaded,
            "python_exe": loaded_config.get("python_exe", DEFAULT_COMFYUI_PYTHON_EXE),
            "comfyui_api_port": loaded_config.get("comfyui_api_port", DEFAULT_COMFYUI_API_PORT),
            "vram_mode": loaded_config.get("vram_mode", DEFAULT_VRAM_MODE),
            "ckpt_precision": loaded_config.get("ckpt_precision", DEFAULT_CKPT_PRECISION),
            "vae_precision": loaded_config.get("vae_precision", DEFAULT_VAE_PRECISION),
            "clip_precision": loaded_config.get("clip_precision", DEFAULT_CLIP_PRECISION),
            "unet_precision": loaded_config.get("unet_precision", DEFAULT_UNET_PRECISION),
            "cuda_malloc": loaded_config.get("cuda_malloc", DEFAULT_CUDA_MALLOC),
            "ipex_optimization": loaded_config.get("ipex_optimization", DEFAULT_IPEX_OPTIMIZATION),
            "xformers_acceleration": loaded_config.get("xformers_acceleration", DEFAULT_XFORMERS_ACCELERATION),
            "git_exe_path": loaded_config.get("git_exe_path", DEFAULT_GIT_EXE_PATH),
            "main_repo_url": loaded_config.get("main_repo_url", DEFAULT_MAIN_REPO_URL),
            "node_config_url": loaded_config.get("node_config_url", DEFAULT_NODE_CONFIG_URL),
            "error_api_endpoint": loaded_config.get("error_api_endpoint", DEFAULT_ERROR_API_ENDPOINT),
            "error_api_key": loaded_config.get("error_api_key", DEFAULT_ERROR_API_KEY),
        }

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
            if show_success:
                print(f"[Launcher INFO] Configuration saved to {CONFIG_FILE}")
        except Exception as e:
            print(f"[Launcher ERROR] Error saving config file: {e}")
            if self.root and self.root.winfo_exists():
                messagebox.showerror("配置保存错误 / Config Save Error", f"无法将配置保存到文件：\n{e}", parent=self.root)

    def _setup_auto_save(self):
        """Sets up trace for auto-saving specific configuration fields."""
        print("[Launcher INFO] Setting up auto-save traces...")
        vars_to_trace = {
            "comfyui_dir": self.comfyui_dir_var, "python_exe": self.python_exe_var,
            "comfyui_api_port": self.comfyui_api_port_var, "git_exe_path": self.git_exe_path_var,
            "main_repo_url": self.main_repo_url_var, "node_config_url": self.node_config_url_var,
            "error_api_endpoint": self.error_api_endpoint_var, "error_api_key": self.error_api_key_var,
            "vram_mode": self.vram_mode_var, "ckpt_precision": self.ckpt_precision_var,
            "clip_precision": self.clip_precision_var, "unet_precision": self.unet_precision_var,
            "vae_precision": self.vae_precision_var, "cuda_malloc": self.cuda_malloc_var,
            "ipex_optimization": self.ipex_optimization_var, "xformers_acceleration": self.xformers_acceleration_var,
        }

        for var_name, var_instance in vars_to_trace.items():
            trace_id_key = f'_trace_id_{var_name}'
            if hasattr(self, trace_id_key):
                try:
                    trace_id = getattr(self, trace_id_key)
                    if trace_id:
                        var_instance.trace_vdelete('write', trace_id)
                except (tk.TclError, AttributeError):
                    pass
                finally:
                    setattr(self, trace_id_key, None)

        for var_name, var_instance in vars_to_trace.items():
            try:
                trace_id = var_instance.trace_add('write', lambda *args, key=var_name: self._schedule_auto_save(key))
                setattr(self, f'_trace_id_{var_name}', trace_id)
            except Exception as e:
                print(f"[Launcher ERROR] Failed to set trace for {var_name}: {e}")

        print("[Launcher INFO] Auto-save traces set up.")

    def _schedule_auto_save(self, config_key_changed):
        """Schedules the auto-save action after a brief delay."""
        if hasattr(self, '_auto_save_job') and self._auto_save_job is not None:
            self.root.after_cancel(self._auto_save_job)
            self._auto_save_job = None
        self._auto_save_job = self.root.after(1000, lambda key=config_key_changed: self._perform_auto_save(key))

    def _perform_auto_save(self, config_key_changed):
        """Performs the actual auto-save for changed configuration fields."""
        self._auto_save_job = None
        print(f"[Launcher INFO] Config field '{config_key_changed}' changed, auto-saving config...")

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
                if config_key_changed == "comfyui_api_port":
                    try:
                        port_int = int(new_value)
                        if not (1 <= port_int <= 65535):
                            raise ValueError("Port out of range 1-65535")
                    except ValueError as e:
                        print(f"[Launcher WARNING] Invalid port value '{new_value}' entered, auto-save skipped for port. Error: {e}")
                        return

                self.config[config_key_changed] = new_value
                if config_key_changed in ["comfyui_dir", "python_exe", "git_exe_path", "comfyui_api_port"] or config_key_changed.startswith("vram_") or config_key_changed.endswith(("_precision", "_malloc", "_optimization", "_acceleration")):
                    self.update_derived_paths()

                self.save_config_to_file(show_success=False)
                self.root.after(0, self._update_ui_state)
            except Exception as e:
                print(f"[Launcher ERROR] Failed to get value or save during auto-save for '{config_key_changed}': {e}")
        else:
            print(f"[Launcher WARNING] Auto-save triggered for unknown key: '{config_key_changed}'")

    def update_derived_paths(self):
        """Updates internal path variables and base arguments based on current config."""
        self.comfyui_install_dir = self.config.get("comfyui_dir", "")
        self.comfyui_portable_python = self.config.get("python_exe", "")
        self.git_exe_path = self.config.get("git_exe_path", DEFAULT_GIT_EXE_PATH)
        self.comfyui_api_port = self.config.get("comfyui_api_port", DEFAULT_COMFYUI_API_PORT)

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

        self.comfyui_base_args = [
            "--listen", "127.0.0.1", f"--port={self.comfyui_api_port}",
        ]

        vram_mode = self.config.get("vram_mode", DEFAULT_VRAM_MODE)
        if vram_mode == "高负载(8GB以上)":
            self.comfyui_base_args.append("--highvram")
        elif vram_mode == "中负载(4GB以上)":
            self.comfyui_base_args.append("--lowvram")
        elif vram_mode == "低负载(2GB以上)":
            self.comfyui_base_args.append("--lowvram")
        elif vram_mode == "全负载(10GB以上)":
             self.comfyui_base_args.append("--highvram")


        ckpt_prec = self.config.get("ckpt_precision", DEFAULT_CKPT_PRECISION)
        if ckpt_prec == "半精度(FP16)":
            self.comfyui_base_args.append("--force-fp16")

        vae_prec = self.config.get("vae_precision", DEFAULT_VAE_PRECISION)
        if vae_prec == "半精度(FP16)":
            self.comfyui_base_args.append("--fp16-vae")
        elif vae_prec == "半精度(BF16)":
            self.comfyui_base_args.append("--bf16-vae")

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

        # Corrected logic for --disable-cuda-malloc
        if self.config.get("cuda_malloc", DEFAULT_CUDA_MALLOC) == "禁用":
            self.comfyui_base_args.append("--disable-cuda-malloc")

        if self.config.get("ipex_optimization", DEFAULT_IPEX_OPTIMIZATION) == "禁用":
            self.comfyui_base_args.append("--disable-ipex")

        if self.config.get("xformers_acceleration", DEFAULT_XFORMERS_ACCELERATION) == "禁用":
            self.comfyui_base_args.append("--disable-xformers")


    # Function to open folders (Remains in launcher.py as a core utility)
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

    # Function to browse directory (Remains in launcher.py)
    def browse_directory(self, var_to_set, initial_dir=""):
        """Opens a directory selection dialog."""
        current_val = var_to_set.get()
        effective_initial_dir = current_val if os.path.isdir(current_val) else self.base_project_dir
        directory = filedialog.askdirectory(title="选择目录 / Select Directory", initialdir=effective_initial_dir, parent=self.root)
        if directory:
             normalized_path = os.path.normpath(directory)
             var_to_set.set(normalized_path)

    # Function to browse file (Remains in launcher.py)
    def browse_file(self, var_to_set, filetypes, initial_dir=""):
        """Opens a file selection dialog."""
        current_val = var_to_set.get()
        effective_initial_dir = os.path.dirname(current_val) if current_val and os.path.isfile(current_val) else self.base_project_dir
        filepath = filedialog.askopenfilename(title="选择文件 / Select File", filetypes=filetypes, initialdir=effective_initial_dir, parent=self.root)
        if filepath:
             var_to_set.set(os.path.normpath(filepath))

    # --- Styling Setup (Remains in launcher.py) ---
    def setup_styles(self):
        """Configures the ttk styles for the application."""
        self.style = ttk.Style(self.root)
        try:
            self.style.theme_use('clam')
        except tk.TclError:
            print("[Launcher WARNING] 'clam' theme not available, using default theme.")

        # Use instance constants here
        neutral_button_bg=self.BG_COLOR; neutral_button_fg=self.FG_COLOR; n_active_bg="#6e6e6e"; n_pressed_bg="#7f7f7f"; n_disabled_bg="#4a5a6a"; n_disabled_fg=self.FG_MUTED

        self.style.configure('.', background=self.BG_COLOR, foreground=self.FG_COLOR, font=(self.FONT_FAMILY_UI, self.FONT_SIZE_NORMAL), bordercolor=self.BORDER_COLOR)
        self.style.map('.', background=[('active', '#4f4f4f'), ('disabled', '#404040')], foreground=[('disabled', self.FG_MUTED)])

        self.style.configure('TFrame', background=self.BG_COLOR)
        self.style.configure('Control.TFrame', background=self.CONTROL_FRAME_BG)
        self.style.configure('TabControl.TFrame', background=self.TAB_CONTROL_FRAME_BG)
        self.style.configure('Settings.TFrame', background=self.BG_COLOR)
        self.style.configure('Logs.TFrame', background=self.BG_COLOR)
        self.style.configure('Analysis.TFrame', background=self.BG_COLOR)
        self.style.configure('Modal.TFrame', background=self.BG_COLOR)
        self.style.configure('Version.TFrame', background=self.BG_COLOR)

        # MOD1: Styles for modal row backgrounds
        row_bg1, row_bg2 = self.TEXT_AREA_BG, "#282828"
        self.style.configure('ModalRowOdd.TFrame', background=row_bg1)
        self.style.configure('ModalRowEven.TFrame', background=row_bg2)


        self.style.configure('TLabelframe', background=self.BG_COLOR, foreground=self.FG_COLOR, bordercolor=self.BORDER_COLOR, relief=tk.GROOVE)
        # MOD1: Added style for Folder LabelFrame in Settings
        self.style.configure('Folder.TLabelframe', background=self.BG_COLOR, foreground=self.FG_COLOR, bordercolor=self.BORDER_COLOR, relief=tk.GROOVE)
        self.style.configure('TLabelframe.Label', background=self.BG_COLOR, foreground=self.FG_COLOR, font=(self.FONT_FAMILY_UI, self.FONT_SIZE_NORMAL, 'italic'))

        self.style.configure('TLabel', background=self.BG_COLOR, foreground=self.FG_COLOR)
        self.style.configure('Status.TLabel', background=self.CONTROL_FRAME_BG, foreground=self.FG_MUTED, padding=(5, 3))
        self.style.configure('Version.TLabel', background=self.BG_COLOR, foreground=self.FG_MUTED, font=(self.FONT_FAMILY_UI, self.FONT_SIZE_NORMAL - 1))
        self.style.configure('Hint.TLabel', background=self.BG_COLOR, foreground=self.FG_MUTED, font=(self.FONT_FAMILY_UI, self.FONT_SIZE_NORMAL - 1), padding=(0, 0, 0, 0))
        self.style.configure('Highlight.TLabel', background=self.BG_COLOR, foreground=self.FG_HIGHLIGHT, font=(self.FONT_FAMILY_UI, self.FONT_SIZE_NORMAL, self.FONT_WEIGHT_BOLD))
        self.style.configure('ModalHeader.TLabel', background=self.BG_COLOR, foreground=self.FG_COLOR, font=(self.FONT_FAMILY_UI, self.FONT_SIZE_NORMAL, self.FONT_WEIGHT_BOLD))

        # MOD1: Styles for labels within modal rows
        self.style.configure('ModalRowOdd.TLabel', background=row_bg1, foreground=self.FG_COLOR)
        self.style.configure('ModalRowEven.TLabel', background=row_bg2, foreground=self.FG_COLOR)
        self.style.configure('ModalRowOddHighlight.TLabel', background=row_bg1, foreground=self.FG_HIGHLIGHT, font=(self.FONT_FAMILY_UI, self.FONT_SIZE_NORMAL, self.FONT_WEIGHT_BOLD))
        self.style.configure('ModalRowEvenHighlight.TLabel', background=row_bg2, foreground=self.FG_HIGHLIGHT, font=(self.FONT_FAMILY_UI, self.FONT_SIZE_NORMAL, self.FONT_WEIGHT_BOLD))


        main_pady=(10, 6); main_fnt=(self.FONT_FAMILY_UI, self.FONT_SIZE_NORMAL); main_fnt_bld=(self.FONT_FAMILY_UI, self.FONT_SIZE_NORMAL, self.FONT_WEIGHT_BOLD)
        self.style.configure('TButton', padding=main_pady, anchor=tk.CENTER, font=main_fnt, borderwidth=0, relief=tk.FLAT, background=neutral_button_bg, foreground=neutral_button_fg)
        self.style.map('TButton', background=[('active', n_active_bg), ('pressed', n_pressed_bg), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])
        self.style.configure("Accent.TButton", padding=main_pady, font=main_fnt_bld, background=self.ACCENT_COLOR, foreground="white")
        self.style.map("Accent.TButton", background=[('pressed', self.ACCENT_ACTIVE), ('active', '#006ae0'), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])
        self.style.configure("Stop.TButton", padding=main_pady, font=main_fnt, background=self.STOP_COLOR, foreground=self.FG_COLOR)
        self.style.map("Stop.TButton", background=[('pressed', self.STOP_ACTIVE), ('active', '#6e6e6e'), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])
        self.style.configure("StopRunning.TButton", padding=main_pady, font=main_fnt, background=self.STOP_RUNNING_BG, foreground=self.STOP_RUNNING_FG)
        self.style.map("StopRunning.TButton", background=[('pressed', self.STOP_RUNNING_ACTIVE_BG), ('active', self.STOP_RUNNING_ACTIVE_BG), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])

        tab_pady=(6, 4); tab_fnt=(self.FONT_FAMILY_UI, self.FONT_SIZE_NORMAL - 1); tab_neutral_bg=neutral_button_bg; tab_n_active_bg=n_active_bg; tab_n_pressed_bg=n_pressed_bg
        self.style.configure("Tab.TButton", padding=tab_pady, font=tab_fnt, background=tab_neutral_bg, foreground=neutral_button_fg)
        self.style.map("Tab.TButton", background=[('pressed', tab_n_pressed_bg), ('active', tab_n_active_bg), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])
        self.style.configure("TabAccent.TButton", padding=tab_pady, font=tab_fnt, background=self.ACCENT_COLOR, foreground="white")
        self.style.map("TabAccent.TButton", background=[('pressed', self.ACCENT_ACTIVE), ('active', '#006ae0'), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])

        # MOD1: Modified Browse.TButton style to have a border for visual "box" effect (Bug 1)
        self.style.configure("Browse.TButton", padding=(4, 2), font=tab_fnt, background=tab_neutral_bg, foreground=neutral_button_fg, borderwidth=1, relief='solid')
        self.style.map("Browse.TButton", background=[('pressed', tab_n_pressed_bg), ('active', tab_n_active_bg), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])

        self.style.configure("Modal.TButton", padding=(4, 2), font=(self.FONT_FAMILY_UI, self.FONT_SIZE_NORMAL-1), background=tab_neutral_bg, foreground=neutral_button_fg)
        self.style.map("Modal.TButton", background=[('pressed', tab_n_pressed_bg), ('active', tab_n_active_bg), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])
        self.style.configure("Version.TButton", padding=(2, 1), font=(self.FONT_FAMILY_UI, self.FONT_SIZE_NORMAL - 1), background=self.BG_COLOR, foreground=self.FG_MUTED, relief=tk.FLAT, borderwidth=0)
        self.style.map("Version.TButton", foreground=[('active', self.FG_COLOR), ('pressed', self.FG_COLOR)], background=[('active', "#3f3f3f"), ('pressed', "#4f4f4f")])

        self.style.configure('TCheckbutton', background=self.BG_COLOR, foreground=self.FG_COLOR, font=main_fnt); self.style.map('TCheckbutton', background=[('active', self.BG_COLOR)], indicatorcolor=[('selected', self.ACCENT_COLOR), ('pressed', self.ACCENT_ACTIVE), ('!selected', self.FG_MUTED)], foreground=[('disabled', self.FG_MUTED)])
        self.style.configure('TCombobox', fieldbackground=self.TEXT_AREA_BG, background=self.TEXT_AREA_BG, foreground=self.FG_COLOR, arrowcolor=self.FG_COLOR, bordercolor=self.BORDER_COLOR, insertcolor=self.FG_COLOR, padding=(5, 4), font=main_fnt); self.style.map('TCombobox', fieldbackground=[('readonly', self.TEXT_AREA_BG), ('disabled', self.CONTROL_FRAME_BG)], foreground=[('disabled', self.FG_MUTED), ('readonly', self.FG_COLOR)], arrowcolor=[('disabled', self.FG_MUTED)], selectbackground=[('!focus', self.ACCENT_COLOR), ('focus', self.ACCENT_ACTIVE)], selectforeground=[('!focus', 'white'), ('focus', 'white')])
        try:
            self.root.option_add('*TCombobox*Listbox.background', self.TEXT_AREA_BG); self.root.option_add('*TCombobox*Listbox.foreground', self.FG_COLOR); self.root.option_add('*TCombobox*Listbox.selectBackground', self.ACCENT_ACTIVE); self.root.option_add('*TCombobox*Listbox.selectForeground', 'white'); self.root.option_add('*TCombobox*Listbox.font', (self.FONT_FAMILY_UI, self.FONT_SIZE_NORMAL)); self.root.option_add('*TCombobox*Listbox.borderWidth', 1); self.root.option_add('*TCombobox*Listbox.relief', 'solid')
        except tk.TclError as e:
            print(f"[Launcher WARNING] Could not set Combobox Listbox styles: {e}")
        self.style.configure('TNotebook', background=self.BG_COLOR, borderwidth=0, tabmargins=[5, 5, 5, 0]); self.style.configure('TNotebook.Tab', padding=[15, 8], background=self.BG_COLOR, foreground=self.FG_MUTED, font=(self.FONT_FAMILY_UI, self.FONT_SIZE_NORMAL), borderwidth=0); self.style.map('TNotebook.Tab', background=[('selected', '#4a4a4a'), ('active', '#3a3a3a')], foreground=[('selected', 'white'), ('active', self.FG_COLOR)], focuscolor=self.style.lookup('TNotebook.Tab', 'background'))
        self.style.configure('Horizontal.TProgressbar', thickness=6, background=self.ACCENT_COLOR, troughcolor=self.CONTROL_FRAME_BG, borderwidth=0)
        self.style.configure('TEntry', fieldbackground=self.TEXT_AREA_BG, foreground=self.FG_COLOR, insertcolor='white', bordercolor=self.BORDER_COLOR, borderwidth=1, padding=(5,4)); self.style.map('TEntry', fieldbackground=[('focus', self.TEXT_AREA_BG)], bordercolor=[('focus', self.ACCENT_COLOR)], lightcolor=[('focus', self.ACCENT_COLOR)])
        self.style.configure('Treeview', background=self.TEXT_AREA_BG, foreground=self.FG_STDOUT, fieldbackground=self.TEXT_AREA_BG, rowheight=22); self.style.configure('Treeview.Heading', font=(self.FONT_FAMILY_UI, self.FONT_SIZE_NORMAL, self.FONT_WEIGHT_BOLD), background=self.CONTROL_FRAME_BG, foreground=self.FG_COLOR); self.style.map('Treeview', background=[('selected', self.ACCENT_ACTIVE)], foreground=[('selected', 'white')])

    # --- UI Setup (Remains in launcher.py, delegates tab creation) ---
    def setup_ui(self):
        """Builds the main UI structure and delegates tab setup to modules."""
        control_frame = ttk.Frame(self.root, padding=(10, 10, 10, 5), style='Control.TFrame')
        control_frame.grid(row=0, column=0, sticky="ew")
        control_frame.columnconfigure(1, weight=1)

        self.status_label = ttk.Label(control_frame, text="状态: 初始化...", style='Status.TLabel', anchor=tk.W)
        self.status_label.grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Label(control_frame, text="", style='Status.TLabel').grid(row=0, column=1, sticky="ew")
        self.progress_bar = ttk.Progressbar(control_frame, mode='indeterminate', length=350, style='Horizontal.TProgressbar')
        self.progress_bar.grid(row=0, column=2, padx=10)
        self.progress_bar.stop()
        self.stop_all_button = ttk.Button(control_frame, text="停止", command=self.stop_all_services, style="Stop.TButton", width=12)
        self.stop_all_button.grid(row=0, column=3, padx=(0, 5))
        self.run_all_button = ttk.Button(control_frame, text="运行 ComfyUI", command=self.start_comfyui_service_thread, style="Accent.TButton", width=12)
        self.run_all_button.grid(row=0, column=4, padx=(0, 0))

        top_area_frame = ttk.Frame(self.root, style='TFrame')
        top_area_frame.grid(row=1, column=0, sticky="nsew")
        top_area_frame.columnconfigure(0, weight=1)
        top_area_frame.rowconfigure(0, weight=1)

        self.notebook = ttk.Notebook(top_area_frame, style='TNotebook')
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=(5, 5))
        self.notebook.enable_traversal()

        version_frame = ttk.Frame(top_area_frame, style='Version.TFrame', padding=(0, 0, 10, 0))
        version_frame.grid(row=0, column=0, sticky="ne", padx=(0, 10), pady=(5,0))
        version_frame.columnconfigure(0, weight=1)

        version_button = ttk.Button(version_frame, text=VERSION_INFO, style="Version.TButton", command=self._run_git_pull_pause)
        version_button.grid(row=0, column=1, sticky="e")

        # --- Delegate Tab Setup to Modules ---
        # Pass the app instance to the module's setup function
        self.settings_frame = ttk.Frame(self.notebook, padding="15", style='Settings.TFrame')
        self.modules['settings'] = settings.setup_settings_tab(self.settings_frame, self)
        self.notebook.add(self.settings_frame, text=' 设置 / Settings ')

        self.update_frame = ttk.Frame(self.notebook, padding="15", style='TFrame')
        # Pass the app instance to the module's setup function
        self.modules['management'] = management.setup_management_tab(self.update_frame, self)
        self.notebook.add(self.update_frame, text=' 管理 / Management ')

        self.logs_tab_frame = ttk.Frame(self.notebook, padding="5", style='Logs.TFrame')
        # Pass the app instance to the module's setup function
        self.modules['logs'] = logs.setup_logs_tab(self.logs_tab_frame, self)
        # The logs module sets self.launcher_log_text, self.main_output_text, self.logs_notebook on the app instance
        self.notebook.add(self.logs_tab_frame, text=' 日志 / Logs ')

        self.analysis_frame = ttk.Frame(self.notebook, padding="15", style='Analysis.TFrame')
        # Pass the app instance to the module's setup function
        self.modules['analysis'] = analysis.setup_analysis_tab(self.analysis_frame, self)
        self.notebook.add(self.analysis_frame, text=' 分析 / Analysis ')


        # Default to Settings tab initially
        self.notebook.select(self.settings_frame)

        # Trace API entry fields to update UI state (enabled/disabled diagnose button)
        self.error_api_endpoint_var.trace_add('write', lambda *args: self.root.after(0, self._update_ui_state))
        self.error_api_key_var.trace_add('write', lambda *args: self.root.after(0, self._update_ui_state))


    # --- Text/Output Methods (Remains in launcher.py) ---
    def setup_text_tags(self, text_widget):
        """Configures text tags for ScrolledText widget coloring."""
        if not text_widget or not text_widget.winfo_exists():
            return
        try:
            text_widget.tag_config("stdout", foreground=self.FG_STDOUT)
            text_widget.tag_config("stderr", foreground=self.FG_STDERR)
            text_widget.tag_config("info", foreground=self.FG_INFO, font=(self.FONT_FAMILY_MONO, self.FONT_SIZE_MONO, 'italic'))
            text_widget.tag_config("warn", foreground=self.FG_WARN)
            text_widget.tag_config("error", foreground=self.FG_STDERR, font=(self.FONT_FAMILY_MONO, self.FONT_SIZE_MONO, 'bold'))
            text_widget.tag_config("api_output", foreground=self.FG_API)
            text_widget.tag_config("cmd", foreground=self.FG_CMD, font=(self.FONT_FAMILY_MONO, self.FONT_SIZE_MONO, 'bold'))
            # Use root.after for tag_config that might involve styling that needs theme lookup
            self.root.after(0, lambda: text_widget.tag_config("highlight", foreground=self.FG_HIGHLIGHT, font=(self.FONT_FAMILY_UI, self.FONT_SIZE_NORMAL, self.FONT_WEIGHT_BOLD)))
            # Add tag for persisted items in Treeviews
            self.root.after(0, lambda: text_widget.tag_config("persisted", foreground=self.FG_MUTED))

        except tk.TclError as e:
            print(f"[Launcher WARNING] Failed to configure text tags: {e}")

    def insert_output(self, text_widget, line, tag="stdout"):
        """Inserts text into a widget with tags, handles auto-scroll."""
        if not text_widget or not text_widget.winfo_exists():
            return
        try:
            text_widget.config(state=tk.NORMAL)
            # Ensure tag exists before inserting
            if tag not in text_widget.tag_names():
                tag = "stdout"

            # Add timestamp prefix to Launcher logs only (MOD6)
            if text_widget == self.launcher_log_text:
                 timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                 line = f"[{timestamp}] {line}"

            text_widget.insert(tk.END, line, (tag,))
            # Always scroll to the end after inserting text
            text_widget.see(tk.END)
            # MOD5: Ensure ScrolledText widgets intended for user input remain normal
            # Access user_request_text safely via the analysis module instance
            is_user_request = self.modules.get('analysis') and hasattr(self.modules['analysis'], 'user_request_text') and self.modules['analysis'].user_request_text and text_widget == self.modules['analysis'].user_request_text
            if not is_user_request:
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
        # Route ErrorAnalysis logs to launcher queue unless specifically stdout/stderr (handled by process_output_queues)
        if source == "ComfyUI" or target_override == "ComfyUI":
            target_queue = self.comfyui_output_queue
        # Note: Routing Analysis/ErrorAnalysis messages to the correct text area
        # is now handled in process_output_queues by checking the prefix.


        # Determine the tag based on level and source
        tag = level # Use level directly as the primary tag indicator
        if level == "stdout" and source not in ["ComfyUI", "Git"]: # Non-ComfyUI/Git stdout -> treat as info
             tag = "info"
        elif level == "stderr": # Always use stderr tag for errors
             tag = "stderr"
        # Allow specific tags like 'cmd', 'api_output'
        elif level in ["cmd", "api_output", "warn", "error", "info"]:
             tag = level # Keep specific level tags
        else: # Fallback for unknown levels
             tag = "info"

        # Construct the log line prefix for context (handled in insert_output for timestamp for Launcher logs)
        # For queueing, just include the source prefix if not ComfyUI
        log_prefix = f"[{source}] " if source and source != "ComfyUI" else ""

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
                # Check for specific prefixes added in log_to_gui
                is_analysis_log = line.strip().startswith("[ErrorAnalysis]") or line.strip().startswith("[Analysis]")

                # Safely access the analysis text widget via the module instance
                analysis_text_widget = None
                if self.modules.get('analysis') and hasattr(self.modules['analysis'], 'error_analysis_text'):
                     analysis_text_widget = self.modules['analysis'].error_analysis_text

                if is_analysis_log and analysis_text_widget and analysis_text_widget.winfo_exists():
                     self.insert_output(analysis_text_widget, line, tag)
                elif self.launcher_log_text and self.launcher_log_text.winfo_exists():
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
                elif self.main_output_text and self.main_output_text.winfo_exists(): # Safely access widget
                    # Route ComfyUI logs to main_output_text
                    self.insert_output(self.main_output_text, line, tag)
                processed_count += 1
        except queue.Empty:
            pass
        except Exception as e:
             print(f"[Launcher ERROR] Error processing comfyui log queue: {e}")
             traceback.print_exc()

        # Schedule the next check
        self.root.after(self.UPDATE_INTERVAL_MS, self.process_output_queues)

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
                if self.stop_event_set(): # Use the getter method
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

    def clear_output_widgets(self):
        """Clears the text in the output ScrolledText widgets."""
        # Only clear ComfyUI and Analysis logs, preserve Launcher logs (MOD6)
        widgets_to_clear = []
        if self.main_output_text:
            widgets_to_clear.append(self.main_output_text) # ComfyUI Log

        # Safely access analysis text widgets via the module instance
        analysis_module = self.modules.get('analysis')
        if analysis_module:
            if hasattr(analysis_module, 'error_analysis_text') and analysis_module.error_analysis_text:
                 widgets_to_clear.append(analysis_module.error_analysis_text) # Analysis Log
            if hasattr(analysis_module, 'user_request_text') and analysis_module.user_request_text:
                 widgets_to_clear.append(analysis_module.user_request_text) # User Request

        self.log_to_gui("Launcher", "清空 ComfyUI 日志、用户诉求和分析区域...", "info")

        for widget in widgets_to_clear:
            try:
                if widget and widget.winfo_exists():
                    widget.config(state=tk.NORMAL)
                    widget.delete('1.0', tk.END)
                    # Set state back - Analysis/ComfyUI logs disabled, User request normal
                    # Safely check if widget is the user request text widget
                    is_user_request = analysis_module and hasattr(analysis_module, 'user_request_text') and widget == analysis_module.user_request_text
                    widget.config(state=tk.DISABLED if not is_user_request else tk.NORMAL)
            except tk.TclError:
                pass


    # --- Service Management (Remains in launcher.py) ---
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
             self.log_to_gui("Launcher", f"检测到外部 ComfyUI 已在端口 {self.comfyui_api_port_var.get()} 运行。请先停止外部实例。", "warn")
             return
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中，请稍候。", "warn")
             return
        # Check if management modal is open via the module instance
        if self.modules.get('management') and hasattr(self.modules['management'], 'is_modal_open') and self.modules['management'].is_modal_open():
             self.log_to_gui("Launcher", "节点版本历史弹窗已打开，请先关闭。", "warn")
             messagebox.showwarning("操作进行中", "请先关闭节点版本历史弹窗。", parent=self.root)
             return


        if not self._validate_paths_for_execution(check_comfyui=True, check_git=False):
            return # Validation failed, error shown by validate function

        self.stop_event.clear()
        self.comfyui_externally_detected = False
        self.backend_browser_triggered_for_session = False
        self.comfyui_ready_marker_sent = False

        self.root.after(0, self._update_ui_state) # Update UI before starting thread

        # Start progress bar and update status label only when initiating ComfyUI launch
        try:
             if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists():
                 self.progress_bar.start(10)
             if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                 self.status_label.config(text="状态: 启动 ComfyUI 后台...")
        except tk.TclError:
             pass

        self.clear_output_widgets() # Clear previous logs (MOD6: Launcher log preserved)

        # Switch to the "Logs" tab, then the "ComfyUI日志" sub-tab
        try:
             logs_tab_index = -1
             # Find the index of the Logs tab dynamically
             for i in range(self.notebook.index("end")):
                  if self.notebook.tab(i, "text").strip().startswith("日志"):
                       logs_tab_index = i
                       break

             if logs_tab_index != -1:
                  self.notebook.select(logs_tab_index)
                  # ComfyUI log sub-tab index is 1 (0 = Launcher, 1 = ComfyUI)
                  comfyui_log_sub_tab_index = 1
                  # Safely access the logs notebook via the module instance
                  if hasattr(self, 'logs_notebook') and self.logs_notebook and self.logs_notebook.winfo_exists():
                      self.logs_notebook.select(comfyui_log_sub_tab_index)
             else:
                  print("[Launcher WARNING] Could not find Logs tab to switch to.")
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
                # Attempt to check port *after* process exit, it might indicate port conflict was the cause
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

        try:
             if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                 self.status_label.config(text="状态: 停止 ComfyUI 后台...")
             if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists():
                  self.progress_bar.start(10)
        except tk.TclError:
             pass

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
        # Check if management modal is open and try to close it via the module instance
        if self.modules.get('management') and hasattr(self.modules['management'], 'is_modal_open') and self.modules['management'].is_modal_open():
             # Call cleanup method if it exists
             if hasattr(self.modules['management'], '_cleanup_modal_state'):
                 self.modules['management']._cleanup_modal_state()
             # Give modal a moment to close before proceeding with stop if needed
             self.root.update_idletasks() # Process pending events


        process_running = self._is_comfyui_running()
        task_running = self._is_update_task_running()
        comfy_externally_detected = self.comfyui_externally_detected


        if not process_running and not comfy_externally_detected and not task_running:
             print("[Launcher INFO] Stop all: No managed process active or detected.")
             self._update_ui_state()
             return

        self.log_to_gui("Launcher", "请求停止所有服务...", "info")
        self.root.after(0, self._update_ui_state) # Update UI before stopping
        try:
             if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                 self.status_label.config(text="状态: 停止所有服务...")
             if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists():
                  self.progress_bar.start(10) # Keep progress bar running during stop process
        except tk.TclError:
             pass

        if process_running:
             self._stop_comfyui_service() # Handles its own UI updates within
        elif comfy_externally_detected:
            self.comfyui_externally_detected = False
            self.log_to_gui("Launcher", "检测到外部 ComfyUI，未尝试停止。", "info")


        if task_running:
             self.log_to_gui("Launcher", "请求停止当前更新任务...", "info")
             self.stop_event.set() # Signal worker thread

        # Give worker a moment to react, then update UI
        # The _update_task_worker's finally block will also trigger _update_ui_state
        # So an extra delay here is primarily for the ComfyUI stop process visual feedback
        self.root.after(500, self._update_ui_state)


    # --- Git Execution Helper (Remains in launcher.py) ---
    def _run_git_command(self, command_list, cwd, timeout=300, log_output=True):
        """Runs a git command, logs output, and returns stdout, stderr, return code."""
        git_exe = self.git_exe_path_var.get()
        if not git_exe or not os.path.isfile(git_exe):
             err_msg = f"Git 可执行文件路径未配置或无效: {git_exe}"
             if log_output:
                 self.log_to_gui("Git", err_msg, "error", target_override="Launcher")
             return "", err_msg, 127

        full_cmd = [git_exe] + command_list
        git_env = os.environ.copy()
        git_env['PYTHONIOENCODING'] = 'utf-8'
        git_env['GIT_TERMINAL_PROMPT'] = '0' # Prevent interactive prompts

        if not os.path.isdir(cwd):
             err_msg = f"Git 命令工作目录不存在或无效: {cwd}"
             if log_output:
                 self.log_to_gui("Git", err_msg, "error", target_override="Launcher")
             return "", err_msg, 1

        try:
            cmd_log_list = [shlex.quote(arg) for arg in full_cmd]
            cmd_log_str = ' '.join(cmd_log_list)
            if log_output:
                 self.log_to_gui("Git", f"执行: {cmd_log_str}", "cmd", target_override="Launcher")
                 self.log_to_gui("Git", f"工作目录: {cwd}", "cmd", target_override="Launcher")

            startupinfo = None
            creationflags = 0
            if os.name == 'nt':
                 creationflags = subprocess.CREATE_NO_WINDOW # Prevent window popping up

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
                        self.log_to_gui("Git", stdout_full, "stdout", target_override="Launcher")
                    if stderr_full:
                        self.log_to_gui("Git", stderr_full, "stderr", target_override="Launcher")
            except subprocess.TimeoutExpired:
                if log_output:
                    self.log_to_gui("Git", f"Git 命令超时 ({timeout} 秒), 进程被终止。", "error", target_override="Launcher")
                try:
                    process.kill()
                except OSError:
                    pass
                returncode = 124 # Standard timeout exit code
                stdout_full, stderr_full = "", "命令执行超时 / Command timed out"

            if log_output and returncode != 0:
                 self.log_to_gui("Git", f"Git 命令返回非零退出码 {returncode}。", "warn", target_override="Launcher")

            return stdout_full, stderr_full, returncode

        except FileNotFoundError:
            error_msg = f"Git 可执行文件未找到: {git_exe}"
            if log_output:
                self.log_to_gui("Git", error_msg, "error", target_override="Launcher")
            return "", error_msg, 127
        except Exception as e:
            error_msg = f"执行 Git 命令时发生意外错误: {e}\n命令: {' '.join(full_cmd)}"
            if log_output:
                self.log_to_gui("Git", error_msg, "error", target_override="Launcher")
            return "", error_msg, 1


    # --- Git Utility Methods (Needed by Management Tab, Placed in Launcher) ---

    def _get_current_local_main_body_commit(self):
        """Gets the full commit ID of the current HEAD for the main ComfyUI repo."""
        comfyui_dir = self.comfyui_dir_var.get()
        if not comfyui_dir or not os.path.isdir(comfyui_dir) or not os.path.isdir(os.path.join(comfyui_dir, ".git")):
             return None
        try:
             stdout_id_full, _, rc_full = self._run_git_command(["rev-parse", "HEAD"], cwd=comfyui_dir, timeout=5, log_output=False)
             if rc_full == 0 and stdout_id_full:
                  return stdout_id_full.strip()
        except Exception as e:
             print(f"[Launcher ERROR] Failed to get current main body commit: {e}")
             self.log_to_gui("Launcher", f"获取当前本体 Commit ID 失败: {e}", "error")
             return None
        return None


    # Helper functions for Sorting (Remains in launcher.py)
    def _parse_iso_date_for_sort(self, date_str):
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
                    # Attempt with timezone first (e.g., 'YYYY-MM-DD HH:MM:SS %z')
                    return datetime.strptime(cleaned_date_str, '%Y-%m-%d %H:%M:%S %z')
                except ValueError:
                    try:
                        # Attempt without timezone, assume UTC (e.g., 'YYYY-MM-DD HH:MM:SS')
                        # Added more formats just in case
                        formats_to_try = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d', '%Y-%m-%d %H:%M:%S.%f%z', '%Y-%m-%dT%H:%M:%S.%f%z']
                        for fmt in formats_to_try:
                             try:
                                  dt_obj = datetime.strptime(cleaned_date_str, fmt)
                                  # Assume UTC if timezone is not present
                                  return dt_obj if dt_obj.tzinfo is not None else dt_obj.replace(tzinfo=timezone.utc)
                             except ValueError:
                                  continue # Try next format
                        return None # Indicate parsing failure for all formats
                    except ValueError:
                         # print(f"[Launcher DEBUG] Could not parse date '{date_str}' for sorting.")
                         return None # Indicate parsing failure
        except Exception as e:
            print(f"[Launcher ERROR] Unexpected date parsing error for '{date_str}': {e}")
            return None

    def _parse_version_string_for_sort(self, version_str):
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

    def _compare_versions_for_sort(self, item1, item2):
        """
        Custom comparison function for sorting main body versions or node histories.
        Prioritizes date (newest first), then version string (descending) for items without valid dates.
        """
        date1 = self._parse_iso_date_for_sort(item1.get('date_iso'))
        date2 = self._parse_iso_date_for_sort(item2.get('date_iso'))
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
        version1 = self._parse_version_string_for_sort(name1)
        version2 = self._parse_version_string_for_sort(name2)

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
                # Handle potential Nonetype in str() if version parsing failed but isn't None
                elif str(version1 if version1 is not None else '') > str(version2 if version2 is not None else ''):
                     return -1
                elif str(version1 if version1 is not None else '') < str(version2 if version2 is not None else ''):
                     return 1

            except TypeError: # Cannot compare different types (e.g., Version vs str, or different string formats)
                 # Fallback to simple string comparison if typed comparison fails
                 if str(name1 if name1 is not None else '') > str(name2 if name2 is not None else ''):
                      return -1
                 elif str(name1 if name1 is not None else '') < str(name2 if name2 is not None else ''):
                      return 1
        elif version1 is not None and version2 is None: # Treat parseable version as higher priority
            return -1
        elif version1 is None and version2 is not None:
            return 1
        # Both version parseable fail, or types incompatible, proceed to type/name fallback

        # Fallback: Compare types (tags usually more important than branches/commits, but order not strictly defined by user - alphabetical?)
        # Prioritize 'tag', then 'branch', then 'commit' - this makes tags appear first, then branches, then commits
        # Added 'branch (local)', 'branch (HEAD)', 'commit (HEAD)' with lower priority than remote
        type_order = {'tag': 0, 'branch': 1, 'branch (remote)': 2, 'branch (local)': 3, 'branch (HEAD)': 4, 'commit': 5, 'commit (HEAD)': 6, '未知': 10} # Lower value = higher priority
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


    # Helper function to check if a window widget exists safely (Remains in launcher.py)
    def window_to_exists(self, window):
        """Safely checks if a Tkinter widget exists."""
        try:
            return window and window.winfo_exists()
        except tk.TclError:
            return False
        except Exception:
            return False

    # Getter method for stop_event state (Utility for modules)
    def stop_event_set(self):
        """Getter method for stop_event.is_set()."""
        return self.stop_event.is_set()


    # --- Update Task Worker Thread (Remains in launcher.py) ---
    def _update_task_worker(self):
        """Worker thread that processes update tasks from the queue."""
        while True:
            task_func, task_args, task_kwargs = None, None, None # Define outside try
            try:
                # Use timeout=0.1 or small value so the loop can check stop_event frequently
                task_func, task_args, task_kwargs = self.update_task_queue.get(timeout=0.1)
                if self.stop_event_set(): # Check if stopped while waiting
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
                    # print(f"[Launcher DEBUG] Task '{task_func.__name__ if task_func else 'Unknown'}' finished, entering finally block.")
                    self.update_task_queue.task_done()
                    self._update_task_running = False
                    self.stop_event.clear() # Reset stop event for the next task
                    # print(f"[Launcher DEBUG] _update_task_running set to False.")
                    self.log_to_gui("Launcher", f"更新任务 '{task_func.__name__}' 完成。", "info")
                    self.root.after(0, self._update_ui_state) # Schedule UI update after task completion
                    # print(f"[Launcher DEBUG] UI update scheduled after task completion.")

            except queue.Empty:
                # When queue is empty and stop_event is set, exit the worker loop
                if self.stop_event_set(): # Use the getter method
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


    # --- Queueing Methods for UI actions (Remains in launcher.py, calls module methods) ---
    def _queue_main_body_refresh(self):
        """Queues the main body version refresh task (calls management module)."""
        # Access modal state via the management module instance
        if self.modules.get('management') and hasattr(self.modules['management'], 'is_modal_open') and self.modules['management'].is_modal_open():
             messagebox.showwarning("操作进行中", "请先关闭节点版本历史弹窗。", parent=self.root)
             return
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中...", "warn")
             return
        if not self._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=True):
             return

        self.log_to_gui("Launcher", "将刷新本体版本任务添加到队列...", "info")
        # Queue the task method of the management module instance
        if self.modules.get('management'):
            # Ensure the method exists before queuing
            if hasattr(self.modules['management'], 'refresh_main_body_versions'):
                 self.update_task_queue.put((self.modules['management'].refresh_main_body_versions, [], {}))
            else:
                 self.log_to_gui("Launcher", "Management module refresh_main_body_versions method not found.", "error")
                 messagebox.showerror("模块错误", "节点管理模块部分功能缺失，请检查文件。", parent=self.root)
        else:
            self.log_to_gui("Launcher", "Management module not loaded, cannot queue refresh.", "error")
            messagebox.showerror("模块错误", "节点管理模块未加载，无法进行更新管理。", parent=self.root)
        self.root.after(0, self._update_ui_state)

    def _queue_main_body_activation(self):
        """Queues the main body version activation task (calls management module)."""
        if self.modules.get('management') and hasattr(self.modules['management'], 'is_modal_open') and self.modules['management'].is_modal_open():
             messagebox.showwarning("操作进行中", "请先关闭节点版本历史弹窗。", parent=self.root)
             return
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中...", "warn")
             return

        # Access management module and its methods/attributes safely
        mgmt_module = self.modules.get('management')
        if not mgmt_module:
             self.log_to_gui("Launcher", "Management module not loaded, cannot queue activation.", "error")
             messagebox.showerror("模块错误", "节点管理模块未加载，无法进行更新管理。", parent=self.root)
             return

        # Access selected item data via management module
        selected_item_data = None
        if hasattr(mgmt_module, 'get_selected_main_body_item_data'):
             selected_item_data = mgmt_module.get_selected_main_body_item_data()

        if not selected_item_data or len(selected_item_data) < 4:
            messagebox.showwarning("未选择版本", "请从列表中选择一个要激活的本体版本。", parent=self.root)
            return

        selected_version_display = selected_item_data[0]
        selected_commit_id_short = selected_item_data[1] # Short ID from treeview

        full_commit_id = None
        # Access cached data via management module
        if hasattr(mgmt_module, 'remote_main_body_versions'):
             for ver_data in mgmt_module.remote_main_body_versions:
                 commit_id_str = ver_data.get('commit_id')
                 # Match using the displayed short ID for robustness
                 if isinstance(commit_id_str, str) and commit_id_str.startswith(selected_commit_id_short):
                      full_commit_id = ver_data["commit_id"]
                      break

        if not full_commit_id:
             # Fallback: Use the short ID directly. Git checkout usually works with short IDs.
             full_commit_id = selected_commit_id_short
             self.log_to_gui("Launcher", f"无法在缓存中找到 '{selected_commit_id_short}' 的完整ID，将尝试使用短ID激活。", "warn")


        if not self._validate_paths_for_execution(check_comfyui=True, check_git=True, show_error=True):
             return
        comfyui_dir = self.comfyui_dir_var.get()
        if not comfyui_dir or not os.path.isdir(os.path.join(comfyui_dir, ".git")):
             messagebox.showerror("Git 仓库错误", f"ComfyUI 安装目录不是一个有效的 Git 仓库:\n{comfyui_dir}", parent=self.root)
             return

        if self._is_comfyui_running() or self.comfyui_externally_detected:
             messagebox.showwarning("服务运行中", "请先停止 ComfyUI 后台服务，再进行本体版本切换。", parent=self.root)
             return


        confirm = messagebox.askyesno("确认激活", f"确定要下载并覆盖安装本体版本 '{selected_version_display}' (提交ID: {full_commit_id[:8]}) 吗？\n此操作会修改 '{comfyui_dir}' 目录。\n\n警告: 可能导致节点不兼容！\n确认前请确保 ComfyUI 已停止运行。", parent=self.root)
        if not confirm:
            return

        self.log_to_gui("Launcher", f"将激活本体版本 '{full_commit_id[:8]}' 任务添加到队列...", "info")
        # Queue the task method of the management module instance
        if hasattr(mgmt_module, '_activate_main_body_version_task'):
            self.update_task_queue.put((mgmt_module._activate_main_body_version_task, [comfyui_dir, full_commit_id], {}))
        else:
            self.log_to_gui("Launcher", "Management module _activate_main_body_version_task method not found.", "error")
            messagebox.showerror("模块错误", "节点管理模块部分功能缺失，无法执行激活。", parent=self.root)

        self.root.after(0, self._update_ui_state)

    def _queue_node_list_refresh(self):
        """Queues the node list refresh task (calls management module)."""
        if self.modules.get('management') and hasattr(self.modules['management'], 'is_modal_open') and self.modules['management'].is_modal_open():
             messagebox.showwarning("操作进行中", "请先关闭节点版本历史弹窗。", parent=self.root)
             return
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中...", "warn")
             return
        # Note: Path validation moved inside the refresh_node_list task itself for flexibility

        self.log_to_gui("Launcher", "将刷新节点列表任务添加到队列...", "info")
        # Queue the task method of the management module instance
        if self.modules.get('management'):
             if hasattr(self.modules['management'], 'refresh_node_list'):
                 self.update_task_queue.put((self.modules['management'].refresh_node_list, [], {}))
             else:
                 self.log_to_gui("Launcher", "Management module refresh_node_list method not found.", "error")
                 messagebox.showerror("模块错误", "节点管理模块部分功能缺失，无法执行刷新。", parent=self.root)
        else:
            self.log_to_gui("Launcher", "Management module not loaded, cannot queue node list refresh.", "error")
            messagebox.showerror("模块错误", "节点管理模块未加载，无法进行更新管理。", parent=self.root)
        self.root.after(0, self._update_ui_state)

    def _queue_node_switch_or_show_history(self):
        """Handles click on '切换版本' button or node double-click: shows history modal for installed git nodes, queues install for others (calls management module)."""
        # Access management module and its methods/attributes safely
        mgmt_module = self.modules.get('management')
        if not mgmt_module:
             self.log_to_gui("Launcher", "Management module not loaded, cannot queue node operation.", "error")
             messagebox.showerror("模块错误", "节点管理模块未加载，无法进行更新管理。", parent=self.root)
             return

        if hasattr(mgmt_module, 'is_modal_open') and mgmt_module.is_modal_open():
             messagebox.showwarning("操作进行中", "节点版本历史弹窗已打开。", parent=self.root)
             return

        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中...", "warn")
             return

        # Access selected item data via management module
        selected_item_data = None
        if hasattr(mgmt_module, 'get_selected_node_item_data'):
             selected_item_data = mgmt_module.get_selected_node_item_data()

        if not selected_item_data or len(selected_item_data) < 5:
            messagebox.showwarning("未选择节点", "请从列表中选择一个要操作的节点。", parent=self.root)
            return

        node_name = selected_item_data[0]
        node_status = selected_item_data[1]
        repo_info = selected_item_data[3] # Remote info string
        repo_url = selected_item_data[4] # Repo URL

        if not self._validate_paths_for_execution(check_comfyui=True, check_git=True, show_error=True):
             return
        if not self.comfyui_nodes_dir or not os.path.isdir(self.comfyui_nodes_dir):
             messagebox.showerror("目录错误", f"ComfyUI custom_nodes 目录未找到或无效:\n{self.comfyui_nodes_dir}", parent=self.root)
             return

        node_install_path = os.path.normpath(os.path.join(self.comfyui_nodes_dir, node_name))
        # Check if installed AND is a git repository
        is_installed_and_git = os.path.isdir(node_install_path) and os.path.isdir(os.path.join(node_install_path, ".git"))


        if is_installed_and_git:
             # MOD2: Check if ComfyUI is running before allowing git operations on node
             if self._is_comfyui_running() or self.comfyui_externally_detected:
                  messagebox.showwarning("服务运行中", "请先停止 ComfyUI 后台服务，再进行节点版本切换。", parent=self.root)
                  return

             # --- MOD1: Defer history fetch ---
             self.log_to_gui("Launcher", f"将获取节点 '{node_name}' 版本历史任务添加到队列...", "info")
             # Pass node name and path to the fetch task method of the management module
             if hasattr(mgmt_module, '_node_history_fetch_task'):
                 self.update_task_queue.put((mgmt_module._node_history_fetch_task, [node_name, node_install_path], {}))
             else:
                 self.log_to_gui("Launcher", "Management module _node_history_fetch_task method not found.", "error")
                 messagebox.showerror("模块错误", "节点管理模块部分功能缺失，无法获取历史版本。", parent=self.root)

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
             # Access cached data via management module
             found_online_node = None
             if hasattr(mgmt_module, 'all_known_nodes'):
                  found_online_node = next((n for n in mgmt_module.all_known_nodes if n.get("name","").lower() == node_name.lower()), None)

             if found_online_node:
                  potential_ref = found_online_node.get("reference") or found_online_node.get("branch")
                  if potential_ref:
                       target_ref_for_install = potential_ref
                       self.log_to_gui("Management", f"从在线配置获取到目标引用: {target_ref_for_install}", "info")
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
             # Queue the install task method of the management module
             if hasattr(mgmt_module, '_install_node_task'):
                 self.update_task_queue.put((mgmt_module._install_node_task, [node_name, node_install_path, repo_url, target_ref_for_install], {}))
             else:
                 self.log_to_gui("Launcher", "Management module _install_node_task method not found.", "error")
                 messagebox.showerror("模块错误", "节点管理模块部分功能缺失，无法执行安装。", parent=self.root)


        self.root.after(0, self._update_ui_state)


    def _queue_all_nodes_update(self):
        """Queues the task to update all installed git nodes (calls management module)."""
        if self.modules.get('management') and hasattr(self.modules['management'], 'is_modal_open') and self.modules['management'].is_modal_open():
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

        if self._is_comfyui_running() or self.comfyui_externally_detected:
             messagebox.showwarning("服务运行中", "请先停止 ComfyUI 后台服务，再进行全部节点更新。", parent=self.root)
             return

        # Access management module and its local_nodes_only attribute safely
        mgmt_module = self.modules.get('management')
        nodes_to_update = []
        if mgmt_module and hasattr(mgmt_module, 'local_nodes_only'):
             nodes_to_update = [
                 node for node in mgmt_module.local_nodes_only
                 if node.get("is_git") and node.get("repo_url") and node.get("repo_url") not in ("本地安装，无Git信息", "无法获取远程 URL", "本地安装", "N/A", "无远程仓库") and node.get("remote_branch") and node.get("remote_branch") != "N/A"
             ]
        else:
             self.log_to_gui("Launcher", "Management module not loaded or local_nodes_only attribute missing, cannot get node list for update.", "error")
             messagebox.showerror("模块错误", "无法加载节点管理模块，无法更新全部节点。", parent=self.root)
             return


        if not nodes_to_update:
             messagebox.showinfo("无节点可更新", "没有找到可更新的已安装 Git 节点（具有有效的远程跟踪分支）。", parent=self.root)
             return

        confirm = messagebox.askyesno("确认更新全部", f"确定要尝试更新 {len(nodes_to_update)} 个已安装节点吗？\n此操作将执行 Git pull。\n\n警告：可能丢失本地修改！\n确认前请确保 ComfyUI 已停止运行。", parent=self.root)
        if not confirm:
            return

        self.log_to_gui("Launcher", f"将更新全部节点任务添加到队列 (共 {len(nodes_to_update)} 个)...", "info")
        # Queue the update task method of the management module
        if hasattr(mgmt_module, '_update_all_nodes_task'):
            self.update_task_queue.put((mgmt_module._update_all_nodes_task, [nodes_to_update], {}))
        else:
             self.log_to_gui("Launcher", "Management module _update_all_nodes_task method not found.", "error")
             messagebox.showerror("模块错误", "节点管理模块部分功能缺失，无法执行更新全部。", parent=self.root)

        self.root.after(0, self._update_ui_state)

    def _queue_node_uninstall(self):
        """Queues the node uninstall task (calls management module)."""
        if self.modules.get('management') and hasattr(self.modules['management'], 'is_modal_open') and self.modules['management'].is_modal_open():
             messagebox.showwarning("操作进行中", "请先关闭节点版本历史弹窗。", parent=self.root)
             return
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中...", "warn")
             return

        # Access management module and its selected item data method safely
        mgmt_module = self.modules.get('management')
        if not mgmt_module:
             self.log_to_gui("Launcher", "Management module not loaded, cannot queue uninstall.", "error")
             messagebox.showerror("模块错误", "节点管理模块未加载，无法进行更新管理。", parent=self.root)
             return

        selected_item_data = None
        if hasattr(mgmt_module, 'get_selected_node_item_data'):
             selected_item_data = mgmt_module.get_selected_node_item_data()

        if not selected_item_data or len(selected_item_data) < 5:
            messagebox.showwarning("未选择节点", "请从列表中选择一个要卸载的节点。", parent=self.root)
            return

        node_name = selected_item_data[0]
        node_status = selected_item_data[1]

        if node_status != "已安装":
             messagebox.showwarning("节点未安装", f"节点 '{node_name}' 未安装。", parent=self.root)
             return

        if not self.comfyui_nodes_dir or not os.path.isdir(self.comfyui_nodes_dir):
             messagebox.showerror("目录错误", f"ComfyUI custom_nodes 目录未找到或无效:\n{self.comfyui_nodes_dir}", parent=self.root)
             return
        node_install_path = os.path.normpath(os.path.join(self.comfyui_nodes_dir, node_name))
        if not os.path.isdir(node_install_path):
             messagebox.showerror("目录错误", f"指定的节点目录不存在或无效:\n{node_install_path}", parent=self.root)
             self.root.after(0, self._queue_node_list_refresh) # Refresh list if directory is missing
             return

        if self._is_comfyui_running() or self.comfyui_externally_detected:
             messagebox.showwarning("服务运行中", "请先停止 ComfyUI 后台服务，再进行节点卸载。", parent=self.root)
             return


        confirm = messagebox.askyesno(
             "确认卸载节点",
             f"确定要永久删除节点 '{node_name}' 及其目录 '{node_install_path}' 吗？\n此操作不可撤销。\n\n确认前请确保 ComfyUI 已停止运行。",
             parent=self.root)
        if not confirm:
            return

        self.log_to_gui("Launcher", f"将卸载节点 '{node_name}' task添加到队列...", "info") # Corrected to 'task'
        # Queue the uninstall task method of the management module
        if hasattr(mgmt_module, '_node_uninstall_task'):
            self.update_task_queue.put((mgmt_module._node_uninstall_task, [node_name, node_install_path], {}))
        else:
             self.log_to_gui("Launcher", "Management module _node_uninstall_task method not found.", "error")
             messagebox.showerror("模块错误", "节点管理模块部分功能缺失，无法执行卸载。", parent=self.root)

        self.root.after(0, self._update_ui_state)


    # --- Initial Data Loading Task (Remains in launcher.py) ---
    def start_initial_data_load(self):
         """Starts the initial data loading tasks in a background thread."""
         if self._is_update_task_running():
              print("[Launcher INFO] Initial data load skipped, an update task is already running.")
              return
         # Check if management modal is open via the module
         if self.modules.get('management') and hasattr(self.modules['management'], 'is_modal_open') and self.modules['management'].is_modal_open():
              print("[Launcher INFO] Initial data load skipped, modal window is open.")
              return

         self.log_to_gui("Launcher", "开始加载更新管理数据...", "info")
         # Access management module safely before queuing its wrapper task
         mgmt_module = self.modules.get('management')
         if mgmt_module:
              # Queue a wrapper task that calls module methods
              # Pass the module instance itself to the wrapper task
              self.update_task_queue.put((self._run_initial_background_tasks, [mgmt_module], {}))
         else:
              self.log_to_gui("Launcher", "Management module not loaded, cannot perform initial data load.", "error")
              messagebox.showerror("模块错误", "节点管理模块未加载，跳过初始数据加载。", parent=self.root)

         self.root.after(0, self._update_ui_state)


    def _run_initial_background_tasks(self, mgmt_module_instance):
         """Executes the initial data loading tasks by calling module methods. Runs in worker thread."""
         # Note: mgmt_module_instance is passed as an argument here
         if self.stop_event_set(): # Use the getter method
             self.log_to_gui("Launcher", "后台数据加载任务已取消 (停止信号)。", "warn")
             return

         self.log_to_gui("Launcher", "执行后台数据加载 (本体版本和节点列表)...", "info")
         git_path_ok = self._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=False)
         if not git_path_ok:
             self.log_to_gui("Launcher", "Git 路径无效，数据加载将受限。", "warn")

         # Call refresh methods on the passed management module instance
         if hasattr(mgmt_module_instance, 'refresh_main_body_versions'):
             mgmt_module_instance.refresh_main_body_versions()
         else:
              self.log_to_gui("Launcher", "Management module refresh_main_body_versions method not found during initial load.", "error")

         if self.stop_event_set(): # Use the getter method
              self.log_to_gui("Launcher", "后台数据加载任务已取消 (停止信号)。", "warn")
              return

         if hasattr(mgmt_module_instance, 'refresh_node_list'):
              mgmt_module_instance.refresh_node_list()
         else:
              self.log_to_gui("Launcher", "Management module refresh_node_list method not found during initial load.", "error")


         if not self.stop_event_set(): # Use the getter method
             self.log_to_gui("Launcher", "后台数据加载完成。", "info")


    # --- Update Management Tasks (Moved to management.py) ---
    # ... (methods like refresh_main_body_versions, _activate_main_body_version_task,
    # refresh_node_list, _install_node_task, _node_uninstall_task,
    # _update_all_nodes_task, _node_history_fetch_task, _show_node_history_modal,
    # _cleanup_modal_state, _on_modal_switch_confirm, _switch_node_to_ref_task
    # are now implemented in ui_modules/management.py)


    # --- Error Analysis Methods (Moved to analysis.py) ---
    # ... (methods like run_diagnosis, _run_diagnosis_task, _display_analysis_result,
    # run_fix, _run_fix_simulation_task, has_analysis_output_content,
    # is_user_request_enabled, set_user_request_state
    # are now implemented in ui_modules/analysis.py)


    # --- UI State and Helpers (Remains in launcher.py, interacts with modules) ---
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
        # Check modal state via management module instance safely
        modal_is_open = self.modules.get('management') and hasattr(self.modules['management'], 'is_modal_open') and self.modules['management'].is_modal_open()


        try: # Check progress bar state safely
            if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists():
                 is_progress_bar_running = self.progress_bar.winfo_ismapped() and self.progress_bar.cget('mode') == 'indeterminate'
                 label_text = self.status_label.cget("text") if hasattr(self, 'status_label') and self.status_label.winfo_exists() else ""
                 # Check if status label indicates any task is starting/stopping/running (includes both ComfyUI and other tasks)
                 # The condition `update_task_running` already covers the "任务进行中..." state.
                 # Let's refine the condition for starting/stopping ComfyUI specifically.
                 # Check if the status explicitly says "启动 ComfyUI" or "停止 ComfyUI" or "停止所有服务" (which includes ComfyUI stop).
                 if any(status_text in label_text for status_text in ["启动 ComfyUI", "停止 ComfyUI", "停止所有服务"]):
                      is_starting_stopping_comfy = True
                 # If update_task_running is True, the status is already set to "任务进行中...",
                 # so the check above is mainly for the brief transition state of ComfyUI.

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

        # Prioritize task state > ComfyUI running state > idle state
        if update_task_running or is_starting_stopping_comfy:
            # Status is set by the task/start/stop method itself during the process
            # status_text = "状态: 任务进行中..." # Keep the specific status set earlier
            stop_all_enabled = tk.NORMAL # Allow stopping update task or ComfyUI process
            main_stop_style = "StopRunning.TButton"
            # Run button disabled while any task or ComfyUI is starting/stopping/running
            run_comfyui_enabled = tk.DISABLED
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
            # Run button enabled only if paths are valid and nothing is currently running/modal is closed (Bug 2)
            run_comfyui_enabled = tk.NORMAL if comfy_can_run_paths and not modal_is_open else tk.DISABLED
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
                 # Only update status text if not currently indicating a task/transition state
                 if not (update_task_running or is_starting_stopping_comfy):
                     self.status_label.config(text=status_text)
                 # Otherwise, the status text was set by the task/start/stop method, leave it as is.
            # Update current main body version label regardless of state
            mgmt_module = self.modules.get('management')
            if mgmt_module and hasattr(mgmt_module, 'current_main_body_version_label') and mgmt_module.current_main_body_version_label and mgmt_module.current_main_body_version_label.winfo_exists():
                 # The text variable (self.current_main_body_version_var) is updated by the refresh task,
                 # the label just needs to be potentially repainted, which Tkinter handles.
                 # No explicit config needed here.
                 pass # Keep this for clarity, the label update is implicit via textvariable

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
        # Base state for *most* update buttons: Enabled if git OK AND no task/start/stop running AND modal is closed
        base_update_enabled = tk.NORMAL if git_path_ok and not update_task_running and not is_starting_stopping_comfy and not modal_is_open else tk.DISABLED

        # Access management module safely
        mgmt_module = self.modules.get('management')
        if mgmt_module:
            try:
                # Main Body Tab
                if hasattr(mgmt_module, 'refresh_main_body_button') and mgmt_module.refresh_main_body_button and mgmt_module.refresh_main_body_button.winfo_exists():
                     mgmt_module.refresh_main_body_button.config(state=base_update_enabled)

                if hasattr(mgmt_module, 'activate_main_body_button') and mgmt_module.activate_main_body_button and mgmt_module.activate_main_body_button.winfo_exists():
                     # Safely check if treeview exists before querying selection
                     item_selected_main = hasattr(mgmt_module, 'main_body_tree') and mgmt_module.main_body_tree and mgmt_module.main_body_tree.winfo_exists() and bool(mgmt_module.main_body_tree.focus())

                     comfy_dir_is_repo = False
                     if self.comfyui_install_dir and os.path.isdir(self.comfyui_install_dir):
                          comfy_dir_is_repo = os.path.isdir(os.path.join(self.comfyui_install_dir, ".git"))

                     # Activate requires base enabled, item selected, ComfyUI dir is git repo AND ComfyUI not running/detected
                     activate_enabled_state = tk.DISABLED
                     if base_update_enabled == tk.NORMAL and item_selected_main and comfy_dir_is_repo and not comfy_running_internally and not comfy_detected_externally:
                          activate_enabled_state = tk.NORMAL

                     mgmt_module.activate_main_body_button.config(state=activate_enabled_state)

                # Nodes Tab
                item_selected_nodes = hasattr(mgmt_module, 'nodes_tree') and mgmt_module.nodes_tree and mgmt_module.nodes_tree.winfo_exists() and bool(mgmt_module.nodes_tree.focus())

                node_is_installed = False; node_is_git = False; node_has_url = False
                # Safely access nodes_tree and nodes_dir before trying to get item data
                if item_selected_nodes and hasattr(mgmt_module, 'nodes_tree') and mgmt_module.nodes_tree and mgmt_module.nodes_tree.winfo_exists() and self.comfyui_nodes_dir and os.path.isdir(self.comfyui_nodes_dir):
                     try:
                          node_data = mgmt_module.nodes_tree.item(mgmt_module.nodes_tree.focus(), 'values')
                          if node_data and len(node_data) >= 5:
                               node_name_selected = node_data[0]; node_status = node_data[1]; repo_url = node_data[4]
                               node_is_installed = (node_status == "已安装")
                               node_has_url = bool(repo_url) and repo_url not in ("本地安装，无Git信息", "无法获取远程 URL", "本地安装", "N/A", "无远程仓库")
                               # Try finding in cached local list first
                               found_node_info = hasattr(mgmt_module, 'local_nodes_only') and next((n for n in mgmt_module.local_nodes_only if n.get("name") == node_name_selected), None)
                               if found_node_info:
                                   node_is_git = found_node_info.get("is_git", False)
                               else:
                                    # Fallback check by path if not in local_nodes_only (shouldn't happen if list is fresh?)
                                    node_install_path = os.path.normpath(os.path.join(self.comfyui_nodes_dir, node_name_selected))
                                    node_is_git = os.path.isdir(node_install_path) and os.path.isdir(os.path.join(node_install_path, ".git"))

                     except Exception as e:
                         print(f"[Launcher DEBUG] Error getting node state: {e}") # Log error but continue


                # Search entry and button enabled if no task/start/stop running AND modal is closed (Bug 3 Fix check)
                search_enabled = tk.NORMAL if not update_task_running and not is_starting_stopping_comfy and not modal_is_open else tk.DISABLED
                if hasattr(mgmt_module, 'nodes_search_entry') and mgmt_module.nodes_search_entry and mgmt_module.nodes_search_entry.winfo_exists():
                    mgmt_module.nodes_search_entry.config(state=search_enabled)
                if hasattr(mgmt_module, 'search_nodes_button') and mgmt_module.search_nodes_button and mgmt_module.search_nodes_button.winfo_exists():
                    mgmt_module.search_nodes_button.config(state=search_enabled)
                if hasattr(mgmt_module, 'refresh_nodes_button') and mgmt_module.refresh_nodes_button and mgmt_module.refresh_nodes_button.winfo_exists():
                    mgmt_module.refresh_nodes_button.config(state=base_update_enabled)

                # Switch/Install Button Logic:
                # Enabled if base enabled, item selected, ComfyUI not running, AND (can switch OR can install)
                can_switch = node_is_installed and node_is_git and node_has_url # Need git repo for history/switch
                can_install = not node_is_installed and node_has_url # Need remote URL to install
                switch_install_final_state = tk.DISABLED
                if base_update_enabled == tk.NORMAL and item_selected_nodes and (can_switch or can_install) and not comfy_running_internally and not comfy_detected_externally:
                    switch_install_final_state = tk.NORMAL

                if hasattr(mgmt_module, 'switch_install_node_button') and mgmt_module.switch_install_node_button and mgmt_module.switch_install_node_button.winfo_exists():
                     # Text changes based on selection state
                     button_text = "切换版本" # Default if nothing selected or unknown
                     if item_selected_nodes: # Only change text if an item is actually selected
                          button_text = "切换版本" if node_is_installed and node_is_git else "安装节点" if node_has_url else "切换版本" # Default if no URL
                     mgmt_module.switch_install_node_button.config(state=switch_install_final_state, text=button_text)


                # Uninstall Button Logic:
                # Enabled if base enabled, item selected, installed, AND ComfyUI not running
                uninstall_final_state = tk.DISABLED
                if base_update_enabled == tk.NORMAL and item_selected_nodes and node_is_installed and not comfy_running_internally and not comfy_detected_externally:
                     uninstall_final_state = tk.NORMAL
                if hasattr(mgmt_module, 'uninstall_node_button') and mgmt_module.uninstall_node_button and mgmt_module.uninstall_node_button.winfo_exists():
                     mgmt_module.uninstall_node_button.config(state=uninstall_final_state)

                # Update All Button Logic:
                # Enabled if base enabled AND ComfyUI not running
                update_all_final_state = tk.DISABLED
                if base_update_enabled == tk.NORMAL and not comfy_running_internally and not comfy_detected_externally:
                     update_all_final_state = tk.NORMAL
                if hasattr(mgmt_module, 'update_all_nodes_button') and mgmt_module.update_all_nodes_button and mgmt_module.update_all_nodes_button.winfo_exists():
                     mgmt_module.update_all_nodes_button.config(state=update_all_final_state)

            except tk.TclError as e:
                 print(f"[Launcher WARNING] Error updating Management UI state: {e}")
            except AttributeError as e:
                 print(f"[Launcher WARNING] Error updating Management UI state (attribute missing in module): {e}")
            except Exception as e:
                 print(f"[Launcher ERROR] Unexpected error updating Management UI state: {e}")
        else:
             # If management module is not loaded, disable all its buttons (defensive)
             for mod_name in ['management']:
                  if self.modules.get(mod_name):
                       mod_instance = self.modules[mod_name]
                       for attr_name in ['refresh_main_body_button', 'activate_main_body_button',
                                         'nodes_search_entry', 'search_nodes_button', 'refresh_nodes_button',
                                         'switch_install_node_button', 'uninstall_node_button', 'update_all_nodes_button']:
                            if hasattr(mod_instance, attr_name):
                                 widget = getattr(mod_instance, attr_name)
                                 if widget and widget.winfo_exists():
                                      try:
                                           widget.config(state=tk.DISABLED)
                                      except tk.TclError:
                                           pass # Widget might have been destroyed


        # --- Analysis Tab Buttons ---
        # Access analysis module safely
        analysis_module = self.modules.get('analysis')
        if analysis_module:
             try:
                  api_endpoint_set = bool(self.error_api_endpoint_var.get().strip())
                  api_key_set = bool(self.error_api_key_var.get().strip()) # MOD4: Check key presence
                  # Diagnose enabled if API endpoint AND key are set, AND no task/start/stop running AND modal is closed (Bug 3 Fix check)
                  diagnose_enabled_state = tk.DISABLED
                  if api_endpoint_set and api_key_set and not update_task_running and not is_starting_stopping_comfy and not modal_is_open:
                       diagnose_enabled_state = tk.NORMAL

                  if hasattr(analysis_module, 'diagnose_button') and analysis_module.diagnose_button and analysis_module.diagnose_button.winfo_exists():
                       analysis_module.diagnose_button.config(state=diagnose_enabled_state)

                  # Check if analysis output has content via the module's helper method
                  analysis_has_content = hasattr(analysis_module, 'has_analysis_output_content') and analysis_module.has_analysis_output_content()

                  # Fix button is enabled if diagnose is enabled AND an update/fix task is NOT running, AND there is content in the analysis output AND modal is closed
                  fix_enabled_state = tk.DISABLED
                  if diagnose_enabled_state == tk.NORMAL and analysis_has_content and not update_task_running and not is_starting_stopping_comfy and not modal_is_open:
                       fix_enabled_state = tk.NORMAL

                  if hasattr(analysis_module, 'fix_button') and analysis_module.fix_button and analysis_module.fix_button.winfo_exists():
                       analysis_module.fix_button.config(state=fix_enabled_state)

                  # User request text area is enabled if no task/start/stop running AND modal is closed (Bug 3 Fix check)
                  user_request_enabled_state = tk.DISABLED
                  if not update_task_running and not is_starting_stopping_comfy and not modal_is_open:
                       user_request_enabled_state = tk.NORMAL

                  # Set the state of the user request text widget via the module's helper method
                  if hasattr(analysis_module, 'set_user_request_state'):
                      widget_state = tk.NORMAL if user_request_enabled_state == tk.NORMAL else tk.DISABLED
                      analysis_module.set_user_request_state(widget_state)

             except tk.TclError as e:
                  print(f"[Launcher WARNING] Error updating Analysis UI state: {e}")
             except AttributeError as e:
                  print(f"[Launcher WARNING] Error updating Analysis UI state (attribute missing in module): {e}")
             except Exception as e:
                  print(f"[Launcher ERROR] Unexpected error updating Analysis UI state: {e}")
        else:
             # If analysis module is not loaded, disable its buttons/widgets (defensive)
             for mod_name in ['analysis']:
                   if self.modules.get(mod_name):
                       mod_instance = self.modules[mod_name]
                       for attr_name in ['diagnose_button', 'fix_button', 'user_request_text']:
                             if hasattr(mod_instance, attr_name):
                                  widget = getattr(mod_instance, attr_name)
                                  if widget and widget.winfo_exists():
                                       try:
                                            # ScrolledText uses 'normal'/'disabled'
                                            widget_state = tk.DISABLED if attr_name != 'user_request_text' else tk.DISABLED
                                            widget.config(state=widget_state)
                                       except tk.TclError:
                                            pass # Widget might have been destroyed


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

        # Attempt to cleanup modal if it's open via the management module
        if self.modules.get('management') and hasattr(self.modules['management'], 'is_modal_open') and self.modules['management'].is_modal_open():
             if hasattr(self.modules['management'], '_cleanup_modal_state'):
                 self.modules['management']._cleanup_modal_state()


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


    def _run_git_pull_pause(self):
        """Runs 'git pull' for the launcher's own repository in a new terminal window and pauses."""
        git_exe = self.git_exe_path_var.get()
        if not git_exe or not os.path.isfile(git_exe):
            messagebox.showerror("Git 未找到", f"未找到或未配置 Git 可执行文件:\n{git_exe}\n请在“设置”中配置。", parent=self.root)
            self.log_to_gui("Launcher", f"Git pull failed: Git path invalid '{git_exe}'", "error")
            return

        # Use the base directory of the currently running script
        launcher_dir = self.base_project_dir
        if not os.path.isdir(os.path.join(launcher_dir, ".git")):
            messagebox.showerror("非 Git 仓库", f"当前启动器目录不是一个有效的 Git 仓库:\n{launcher_dir}\n无法执行 Git pull。", parent=self.root)
            self.log_to_gui("Launcher", f"Git pull failed: '{launcher_dir}' is not Git repo", "error")
            return

        self.log_to_gui("Launcher", f"准备执行 'git pull' 于目录: {launcher_dir}", "info")

        try:
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
                for term in ["gnome-terminal", "konsole", "xfce4-terminal", "lxterminal", "urxvt", "alacritty", "kitty", "st", "terminator"]:
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
            self.log_to_gui("Launcher", f"执行 'git pull' failed: {e}", "error")


    # MOD4: Implement saving logs on close
    def on_closing(self):
        """Handles the application closing event, stops services, saves logs, and destroys window."""
        print("[Launcher INFO] Closing application requested.")

        # --- Save Logs Before Closing ---
        self.log_to_gui("Launcher", "正在保存日志...", "info")
        launcher_logs_content = ""
        comfyui_logs_content = ""

        try:
            # Safely access the log text widgets via instance variables
            if hasattr(self, 'launcher_log_text') and self.launcher_log_text and self.launcher_log_text.winfo_exists():
                 # Get all text from Launcher log
                 launcher_logs_content = self.launcher_log_text.get("1.0", tk.END).strip()
            if hasattr(self, 'main_output_text') and self.main_output_text and self.main_output_text.winfo_exists():
                 # Get all text from ComfyUI log
                 comfyui_logs_content = self.main_output_text.get("1.0", tk.END).strip()

            # Format the combined log content as specified (Corrected header)
            combined_log_content = f"""
@@@@@@@@@ComLauncher后台日志
{launcher_logs_content if launcher_logs_content else "（无）"}

@@@@@@@@@ComfyUI日志
{comfyui_logs_content if comfyui_logs_content else "（无）"}
"""
            # Ensure log file is in the ui_modules directory (Correct path used)
            try:
                 os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
                 with open(LOG_FILE, 'w', encoding='utf-8') as f:
                      f.write(combined_log_content.strip()) # Strip leading/trailing whitespace from the formatted block
                 print(f"[Launcher INFO] Logs saved to {LOG_FILE}")
            except Exception as e:
                 print(f"[Launcher ERROR] Failed to save logs to {LOG_FILE}: {e}")

        except Exception as e:
            print(f"[Launcher ERROR] Failed to retrieve logs on closing: {e}")
            # Do not show a messagebox here, just log the error


        # --- Stop Services ---
        # Check if any managed process is running
        process_running = self._is_comfyui_running()
        task_running = self._is_update_task_running()
        # Also check for externally detected ComfyUI, although we can't stop it,
        # the user might want to know something is still active.
        comfy_externally_detected = self.comfyui_externally_detected


        if process_running or comfy_externally_detected or task_running:
             # Use self.root as parent for the messagebox
             confirm_stop = messagebox.askyesno("进程运行中", "有后台进程（ComfyUI 或更新任务）正在运行。\n是否在退出前停止？", parent=self.root)
             if confirm_stop:
                 self.log_to_gui("Launcher", "正在停止后台进程...", "info")
                 self.stop_all_services() # This signals threads and handles ComfyUI process
                 wait_timeout = 15 # seconds
                 start_time = time.time()
                 # Wait for processes/tasks to signal completion (by clearing flags)
                 # Use getter methods and check the process poll state
                 while (self._is_comfyui_running() or self._is_update_task_running()) and (time.time() - start_time < wait_timeout):
                     try:
                         if self.root and self.root.winfo_exists():
                              self.root.update() # Process Tkinter events while waiting
                     except tk.TclError: # Handle root window being destroyed early
                          break # Exit wait loop if GUI is gone
                     time.sleep(0.1) # Small delay

                 if self._is_comfyui_running() or self._is_update_task_running():
                      print("[Launcher WARNING] Processes did not stop gracefully within timeout, forcing exit.")
                      self.log_to_gui("Launcher", "未能完全停止后台进程，强制退出。", "warn")
                      # Attempt to kill subprocesses if they are still alive
                      if self.comfyui_process and self.comfyui_process.poll() is None:
                           try:
                               self.comfyui_process.kill()
                           except Exception:
                               pass # Ignore errors on kill
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
                           pass # Ignore errors on terminate
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
                from ctypes import windll
                # SetProcessDpiAwareness is Windows 8.1+
                # SetProcessDPIAware is older Windows
                try:
                    # Try setting DPI awareness for the process
                    # PROCESS_DPI_AWARENESS.PROCESS_SYSTEM_DPI_AWARE (1) or PROCESS_PER_MONITOR_DPI_AWARE (2)
                    # Setting it to 1 (System) is usually sufficient for Tkinter to scale correctly
                    windll.shcore.SetProcessDpiAwareness(1)
                    # print("[Launcher INFO] Using SetProcessDpiAwareness(1)") # Debug print
                except (AttributeError, OSError): # OSError can be raised if the function isn't found
                     try:
                         windll.user32.SetProcessDPIAware()
                         # print("[Launcher INFO] Using SetProcessDPIAware()") # Debug print
                     except (AttributeError, OSError):
                         print("[Launcher WARNING] No DPI awareness function found.")
                except Exception as e:
                     print(f"[Launcher WARNING] Failed to set DPI awareness: {e}")

            except Exception as e:
                print(f"[Launcher WARNING] Error during Windows DPI setup: {e}")


        root = tk.Tk()
        app = ComLauncherApp(root)
        root.mainloop()

    except Exception as e:
        # --- Error Handling for Fatal Crash ---
        # Log the error and traceback
        print(f"[Launcher CRITICAL] Unhandled exception during application startup or runtime: {e}")
        # Use traceback.print_exc() to print the full traceback to stderr
        traceback.print_exc()

        # Attempt to save logs even on crash
        try:
            launcher_logs_content = ""
            comfyui_logs_content = ""
            if app: # If app instance was created
                 try:
                     # Safely access log widgets via the app instance
                     if hasattr(app, 'launcher_log_text') and app.launcher_log_text and app.launcher_log_text.winfo_exists():
                         launcher_logs_content = app.launcher_log_text.get("1.0", tk.END).strip()
                     if hasattr(app, 'main_output_text') and app.main_output_text and app.main_output_text.winfo_exists():
                         comfyui_logs_content = app.main_output_text.get("1.0", tk.END).strip()
                 except tk.TclError:
                     print("[Launcher CRITICAL] Error getting logs from widgets during crash handling.")

            # Format the combined log content (Corrected header)
            combined_log_content = f"""
@@@@@@@@@ComLauncher后台日志
{launcher_logs_content if launcher_logs_content else "（无）"}

@@@@@@@@@ComfyUI日志
{comfyui_logs_content if comfyui_logs_content else "（无）"}

@@@@@@@@@致命错误信息
{traceback.format_exc()} # Include traceback
"""
            # Save crash log file to the base directory
            crash_log_file_path = os.path.join(BASE_DIR, "ComLauncher_crash.log")
            try:
                 with open(crash_log_file_path, 'w', encoding='utf-8') as f:
                      f.write(combined_log_content.strip())
                 print(f"[Launcher CRITICAL] Crash logs saved to {crash_log_file_path}")
            except Exception as log_err:
                 print(f"[Launcher CRITICAL] Failed to save crash logs to {crash_log_file_path}: {log_err}")

        except Exception as log_err:
             print(f"[Launcher CRITICAL] Unable to prepare crash log content: {log_err}")

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
             sys.exit(1) # Exit with error code 1