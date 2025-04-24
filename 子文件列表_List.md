@@@@文件夹架构：
```
ComLauncher/
├─ templates/ 
│   ├─ icon.ico 
│   ├─ icon.png 
├─ launcher.py 
├─ launcher_config.json 
├─ README.md 
├─ requirements.txt 
├─ run_requirements.bat 
├─ 运行_launcher.bat 
```

@@@@文件内容：


@@@@ File: requirements.txt (Relative Path: requirements.txt
```
# This file lists the minimum required Python packages to run the launcher.py script.
# Based on launcher.py Ver. 3.0.0
# python -m venv venv （如无，手动添加venv环境）

requests```


@@@@ File: launcher_config.json (Relative Path: launcher_config.json
```
{
    "comfyui_dir": "D:\\Program\\ComfyUI_Program\\ComfyUI",
    "python_exe": "D:\\Program\\ComfyUI_Program\\python_embeded\\python.exe",
    "comfyui_workflows_dir": "D:\\Program\\ComfyUI_Program\\ComfyUI\\user\\default\\workflows",
    "comfyui_api_port": "8188",
    "vram_mode": "高负载(8GB以上)",
    "ckpt_precision": "半精度(FP16)",
    "clip_precision": "FP8 (E4M3FN)",
    "unet_precision": "FP8 (E4M3FN)",
    "vae_precision": "半精度(FP16)",
    "cuda_malloc": "启用",
    "ipex_optimization": "启用",
    "xformers_acceleration": "启用",
    "git_exe_path": "D:\\Program\\ComfyUI_Program\\ComfyUI\\git\\cmd\\git.exe",
    "main_repo_url": "https://gitee.com/AIGODLIKE/ComfyUI.git",
    "node_config_url": "https://raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main/custom-node-list.json",
    "error_api_endpoint": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash",
    "error_api_key": ""
}```


@@@@ File: launcher.py (Relative Path: launcher.py
```
# -*- coding: utf-8 -*-
# File: launcher.py
# Version: Kerry, Ver. 2.4.0 (Threaded Updates, Enhanced Node List, Update All)

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, font as tkfont, filedialog
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
from datetime import datetime # Import datetime for date parsing
import shlex # Added for safe command splitting

# --- Configuration File ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "launcher_config.json")

# --- Default Values ---
DEFAULT_COMFYUI_INSTALL_DIR = "" # User must set this
DEFAULT_COMFYUI_PYTHON_EXE = "" # User must set this (can be portable or venv)
DEFAULT_COMFYUI_WORKFLOWS_DIR = "" # Will be derived if INSTALL_DIR is set, but allow override
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
# Default Git path (Windows specific example)
DEFAULT_GIT_EXE_PATH = r"D:\Program\ComfyUI_Program\ComfyUI\git\cmd\git.exe" if platform.system() == "Windows" else "/usr/bin/git" # Default Git path based on OS
DEFAULT_MAIN_REPO_URL = "https://gitee.com/AIGODLIKE/ComfyUI.git" # Default ComfyUI Main Repository
DEFAULT_NODE_CONFIG_URL = "https://raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main/custom-node-list.json" # Default Node Config URL
DEFAULT_ERROR_API_ENDPOINT = "" # Default Error Analysis API Endpoint
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
FG_STDOUT = "#e0e0e0"
FG_STDERR = "#ff6b6b"
FG_INFO = "#64d1b8"
FONT_FAMILY_UI = "Segoe UI"
FONT_FAMILY_MONO = "Consolas"
FONT_SIZE_NORMAL = 10
FONT_SIZE_MONO = 9
FONT_WEIGHT_BOLD = "bold"
VERSION_INFO = "ComLauncher, Ver. 2.4.0" # Updated version info for ComLauncher


# Special marker for queue
_COMFYUI_READY_MARKER_ = "_COMFYUI_IS_READY_FOR_BROWSER_\n"

# --- Text/Output Methods (Standalone function) ---
def setup_text_tags(text_widget):
    """Configures text tags for ScrolledText widget coloring."""
    if not text_widget or not text_widget.winfo_exists():
        return
    text_widget.tag_config("stdout", foreground=FG_STDOUT)
    text_widget.tag_config("stderr", foreground=FG_STDERR)
    text_widget.tag_config("info", foreground=FG_INFO, font=(FONT_FAMILY_MONO, FONT_SIZE_MONO, 'italic'))
    text_widget.tag_config("warn", foreground="#ffd700")
    text_widget.tag_config("error", foreground=FG_STDERR, font=(FONT_FAMILY_MONO, FONT_SIZE_MONO, 'bold'))
    text_widget.tag_config("api_output", foreground="#cccccc") # Tag for API analysis output
    text_widget.tag_config("cmd", foreground="#a0a0a0", font=(FONT_FAMILY_MONO, FONT_SIZE_MONO, 'bold')) # Tag for commands

class ComLauncherApp:
    """Main class for the Tkinter application (ComLauncher)."""
    def __init__(self, root):
        """ Initializes the application. """
        self.root = root
        self.root.title("ComLauncher") # Changed program name
        self.root.geometry("1000x750")
        self.root.configure(bg=BG_COLOR)
        self.root.minsize(800, 600)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        # Process and state variables
        self.comfyui_process = None
        self.comfyui_output_queue = queue.Queue() # Only one output queue for ComfyUI logs
        self.update_task_queue = queue.Queue() # Queue for background update tasks (Git operations)
        self.stop_event = threading.Event()
        self.backend_browser_triggered_for_session = False
        self.comfyui_ready_marker_sent = False
        self.comfyui_externally_detected = False # Keep detection logic
        self._update_task_running = False # Flag to indicate if an update task is running

        # Configuration variables
        self.comfyui_dir_var = tk.StringVar()
        self.python_exe_var = tk.StringVar()
        self.comfyui_workflows_dir_var = tk.StringVar()
        self.comfyui_api_port_var = tk.StringVar()

        # Performance variables
        self.vram_mode_var = tk.StringVar()
        self.ckpt_precision_var = tk.StringVar()
        self.clip_precision_var = tk.StringVar()
        self.unet_precision_var = tk.StringVar()
        self.vae_precision_var = tk.StringVar()
        self.cuda_malloc_var = tk.StringVar()
        self.ipex_optimization_var = tk.StringVar()
        self.xformers_acceleration_var = tk.StringVar()

        # New Configuration variables
        self.git_exe_path_var = tk.StringVar()
        self.main_repo_url_var = tk.StringVar()
        self.node_config_url_var = tk.StringVar()
        self.error_api_endpoint_var = tk.StringVar()
        self.error_api_key_var = tk.StringVar() # Sensitive data, handle carefully

        # Update Management specific variables
        self.current_main_body_version_var = tk.StringVar(value="未知 / Unknown") # Variable to hold current version
        self.all_known_nodes = [] # To hold the full list of detected nodes (local scan + online config)
        self.local_nodes_only = [] # To hold only the nodes found locally (for default view)
        self.remote_main_body_versions = [] # Store fetched remote versions for main body

        self.config = {}

        # Initialize
        self.load_config()
        self.update_derived_paths() # Calculate paths and args based on loaded config
        self.setup_styles()
        self.setup_ui()

        # Start background tasks
        self.root.after(UPDATE_INTERVAL_MS, self.process_output_queues)
        # Start a worker thread for update tasks (Git operations)
        self.update_worker_thread = threading.Thread(target=self._update_task_worker, daemon=True)
        self.update_worker_thread.start()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Set initial UI state and start initial background data loading
        self._update_ui_state()
        # REQUIREMENT 1: Start initial data loading in a background thread
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
            loaded_config = {}

        # Apply defaults and override with loaded config
        self.config = {
            "comfyui_dir": loaded_config.get("comfyui_dir", DEFAULT_COMFYUI_INSTALL_DIR),
            "python_exe": loaded_config.get("python_exe", DEFAULT_COMFYUI_PYTHON_EXE),
            # Derive default workflows path if comfyui_dir is set but workflows_dir isn't
            "comfyui_workflows_dir": loaded_config.get("comfyui_workflows_dir", os.path.normpath(os.path.join(loaded_config.get("comfyui_dir", DEFAULT_COMFYUI_INSTALL_DIR), r"user\default\workflows")) if loaded_config.get("comfyui_dir") else DEFAULT_COMFYUI_WORKFLOWS_DIR),
            "comfyui_api_port": loaded_config.get("comfyui_api_port", DEFAULT_COMFYUI_API_PORT),

            # Performance configs (ensure they are in the config, add if missing)
            "vram_mode": loaded_config.get("vram_mode", DEFAULT_VRAM_MODE),
            "ckpt_precision": loaded_config.get("ckpt_precision", DEFAULT_CKPT_PRECISION),
            "clip_precision": loaded_config.get("clip_precision", DEFAULT_CLIP_PRECISION),
            "unet_precision": loaded_config.get("unet_precision", DEFAULT_UNET_PRECISION),
            "vae_precision": loaded_config.get("vae_precision", DEFAULT_VAE_PRECISION),
            "cuda_malloc": loaded_config.get("cuda_malloc", DEFAULT_CUDA_MALLOC),
            "ipex_optimization": loaded_config.get("ipex_optimization", DEFAULT_IPEX_OPTIMIZATION),
            "xformers_acceleration": loaded_config.get("xformers_acceleration", DEFAULT_XFORMERS_ACCELERATION),

            # New configs
            "git_exe_path": loaded_config.get("git_exe_path", DEFAULT_GIT_EXE_PATH),
            "main_repo_url": loaded_config.get("main_repo_url", DEFAULT_MAIN_REPO_URL),
            "node_config_url": loaded_config.get("node_config_url", DEFAULT_NODE_CONFIG_URL),
            "error_api_endpoint": loaded_config.get("error_api_endpoint", DEFAULT_ERROR_API_ENDPOINT),
            "error_api_key": loaded_config.get("error_api_key", DEFAULT_ERROR_API_KEY), # Load key, but don't display it directly in UI later
        }

        # Set UI variables
        self.comfyui_dir_var.set(self.config["comfyui_dir"])
        self.python_exe_var.set(self.config["python_exe"])
        self.comfyui_workflows_dir_var.set(self.config["comfyui_workflows_dir"])
        self.comfyui_api_port_var.set(self.config["comfyui_api_port"])

        # Set performance variables
        self.vram_mode_var.set(self.config.get("vram_mode", DEFAULT_VRAM_MODE))
        self.ckpt_precision_var.set(self.config.get("ckpt_precision", DEFAULT_CKPT_PRECISION))
        self.clip_precision_var.set(self.config.get("clip_precision", DEFAULT_CLIP_PRECISION))
        self.unet_precision_var.set(self.config.get("unet_precision", DEFAULT_UNET_PRECISION))
        self.vae_precision_var.set(self.config.get("vae_precision", DEFAULT_VAE_PRECISION))
        self.cuda_malloc_var.set(self.config.get("cuda_malloc", DEFAULT_CUDA_MALLOC))
        self.ipex_optimization_var.set(self.config.get("ipex_optimization", DEFAULT_IPEX_OPTIMIZATION))
        self.xformers_acceleration_var.set(self.config.get("xformers_acceleration", DEFAULT_XFORMERS_ACCELERATION))

        # Set new variables
        self.git_exe_path_var.set(self.config.get("git_exe_path", DEFAULT_GIT_EXE_PATH))
        self.main_repo_url_var.set(self.config.get("main_repo_url", DEFAULT_MAIN_REPO_URL))
        self.node_config_url_var.set(self.config.get("node_config_url", DEFAULT_NODE_CONFIG_URL))
        self.error_api_endpoint_var.set(self.config.get("error_api_endpoint", DEFAULT_ERROR_API_ENDPOINT))
        self.error_api_key_var.set(self.config.get("error_api_key", DEFAULT_ERROR_API_KEY))


        # Save default config if file didn't exist or was empty/corrupt
        if not os.path.exists(CONFIG_FILE) or not loaded_config:
            print("[Launcher INFO] Attempting to save default configuration...")
            try: self.save_config_to_file(show_success=False)
            except Exception as e: print(f"[Launcher ERROR] Initial default config save failed: {e}")

    def save_settings(self):
        """Saves current settings from UI variables to the config dictionary and file."""
        print("--- Saving Settings ---")
        # Check if services are running (only ComfyUI now)
        if self._is_comfyui_running():
             if not messagebox.askyesno("服务运行中 / Service Running", "ComfyUI 服务当前正在运行。\n更改的设置需要重启服务才能生效。\n是否仍要保存？", parent=self.root):
                 return

        # Update config from UI variables
        self.config["comfyui_dir"] = self.comfyui_dir_var.get()
        self.config["python_exe"] = self.python_exe_var.get()
        self.config["comfyui_workflows_dir"] = self.comfyui_workflows_dir_var.get()
        self.config["comfyui_api_port"] = self.comfyui_api_port_var.get()

        # Performance settings
        self.config["vram_mode"] = self.vram_mode_var.get()
        self.config["ckpt_precision"] = self.ckpt_precision_var.get()
        self.config["clip_precision"] = self.clip_precision_var.get()
        self.config["unet_precision"] = self.unet_precision_var.get()
        self.config["vae_precision"] = self.vae_precision_var.get()
        self.config["cuda_malloc"] = self.cuda_malloc_var.get()
        self.config["ipex_optimization"] = self.ipex_optimization_var.get()
        self.config["xformers_acceleration"] = self.xformers_acceleration_var.get()

        # New settings
        self.config["git_exe_path"] = self.git_exe_path_var.get()
        self.config["main_repo_url"] = self.main_repo_url_var.get()
        self.config["node_config_url"] = self.node_config_url_var.get()
        self.config["error_api_endpoint"] = self.error_api_endpoint_var.get()
        self.config["error_api_key"] = self.error_api_key_var.get()


        port_valid = True
        try:
            comfy_port_str = self.config["comfyui_api_port"]
            comfy_port = int(comfy_port_str)
            if not (1 <= comfy_port <= 65535): raise ValueError("Port out of range")
        except ValueError as e:
            port_valid = False
            messagebox.showerror("端口错误 / Invalid Port", f"端口号必须是 1-65535 之间的数字。\n错误: {e}", parent=self.root)
        except Exception as e:
             port_valid = False
             messagebox.showerror("端口错误 / Invalid Port", f"端口配置无效。\n错误: {e}", parent=self.root)

        # Validate paths relevant to execution (ComfyUI and Git)
        paths_ok = self._validate_paths_for_execution(check_comfyui=True, check_git=True, show_error=False)


        if port_valid and paths_ok:
             self.save_config_to_file(show_success=True)
             self.update_derived_paths() # Recalculate derived paths and args
             print("[Launcher INFO] Settings saved and paths updated."); self._update_ui_state()
             self._setup_url_auto_save() # Re-setup auto-save in case config file was recreated or paths changed
        else:
             if not paths_ok:
                  self._validate_paths_for_execution(check_comfyui=True, check_git=True, show_error=True)


    def save_config_to_file(self, show_success=True):
        """Writes the self.config dictionary to the JSON file."""
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f: json.dump(self.config, f, indent=4, ensure_ascii=False)
            print(f"[Launcher INFO] Configuration saved to {CONFIG_FILE}")
            if show_success and self.root and self.root.winfo_exists(): messagebox.showinfo("设置已保存 / Settings Saved", "配置已成功保存。", parent=self.root)
        except Exception as e:
            print(f"[Launcher ERROR] Error saving config file: {e}")
            if self.root and self.root.winfo_exists(): messagebox.showerror("配置保存错误 / Config Save Error", f"无法将配置保存到文件：\n{e}", parent=self.root)

    # Auto-save for URL fields (updated for Req 4)
    def _setup_url_auto_save(self):
        """Sets up trace for auto-saving URL fields."""
        # Remove previous traces if any
        if hasattr(self, '_auto_save_job'):
            self.root.after_cancel(self._auto_save_job)
        if hasattr(self, '_url_trace_id_main_repo'):
            try: self.main_repo_url_var.trace_vdelete('write', self._url_trace_id_main_repo)
            except tk.TclError: pass # Ignore if trace doesn't exist
        if hasattr(self, '_url_trace_id_node_config'):
            try: self.node_config_url_var.trace_vdelete('write', self._url_trace_id_node_config)
            except tk.TclError: pass # Ignore if trace doesn't exist
        # Req 4: Remove previous traces for API fields
        if hasattr(self, '_api_trace_id_endpoint'):
             try: self.error_api_endpoint_var.trace_vdelete('write', self._api_trace_id_endpoint)
             except tk.TclError: pass
        if hasattr(self, '_api_trace_id_key'):
             try: self.error_api_key_var.trace_vdelete('write', self._api_trace_id_key)
             except tk.TclError: pass


        # Add new trace - store ids separately
        self._url_trace_id_main_repo = self.main_repo_url_var.trace_add('write', self._auto_save_urls)
        self._url_trace_id_node_config = self.node_config_url_var.trace_add('write', self._auto_save_urls)
        # Req 4: Add traces for API fields
        self._api_trace_id_endpoint = self.error_api_endpoint_var.trace_add('write', self._auto_save_urls)
        self._api_trace_id_key = self.error_api_key_var.trace_add('write', self._auto_save_urls)

        print("[Launcher INFO] URL and API auto-save traces set up.")

    def _auto_save_urls(self, *args):
        """Callback to auto-save URL and API fields."""
        # Use root.after to debounce rapid typing, saving only after a brief pause
        if hasattr(self, '_auto_save_job'):
            self.root.after_cancel(self._auto_save_job)
        self._auto_save_job = self.root.after(1000, self._perform_auto_save_urls) # Save 1 second after last change

    def _perform_auto_save_urls(self):
        """Performs the actual auto-save for URL and API fields."""
        print("[Launcher INFO] Config field changed, auto-saving config...")
        # Save all relevant fields
        self.config["main_repo_url"] = self.main_repo_url_var.get()
        self.config["node_config_url"] = self.node_config_url_var.get()
        # Req 4: Save API fields
        self.config["error_api_endpoint"] = self.error_api_endpoint_var.get()
        self.config["error_api_key"] = self.error_api_key_var.get()

        # Save without showing success message to avoid annoyance
        self.save_config_to_file(show_success=False)
        # self.root.after(0, self._update_ui_state) # Update UI state after saving (specifically for API button) - moved to save_settings

    def update_derived_paths(self):
        """Updates internal path variables and base arguments based on current config."""
        self.base_project_dir = os.path.dirname(os.path.abspath(__file__))
        self.comfyui_install_dir = self.config.get("comfyui_dir", "")
        self.comfyui_portable_python = self.config.get("python_exe", "")
        self.git_exe_path = self.config.get("git_exe_path", DEFAULT_GIT_EXE_PATH) # New git path

        configured_workflows_dir = self.config.get("comfyui_workflows_dir")
        if configured_workflows_dir:
             self.comfyui_workflows_dir = os.path.normpath(configured_workflows_dir)
        elif self.comfyui_install_dir and os.path.isdir(self.comfyui_install_dir):
             # Adjusted default workflows path to be inside user dir
             self.comfyui_workflows_dir = os.path.normpath(os.path.join(self.comfyui_install_dir, r"user\default\workflows"))
        else:
             self.comfyui_workflows_dir = ""

        self.comfyui_nodes_dir = os.path.normpath(os.path.join(self.comfyui_install_dir, "custom_nodes")) if self.comfyui_install_dir and os.path.isdir(self.comfyui_install_dir) else ""
        self.comfyui_models_dir = os.path.normpath(os.path.join(self.comfyui_install_dir, "models")) if self.comfyui_install_dir and os.path.isdir(self.comfyui_install_dir) else ""
        self.comfyui_lora_dir = os.path.normpath(os.path.join(self.comfyui_install_dir, r"models\loras")) if self.comfyui_install_dir and os.path.isdir(self.comfyui_install_dir) else ""
        self.comfyui_input_dir = os.path.normpath(os.path.join(self.comfyui_install_dir, "input")) if self.comfyui_install_dir and os.path.isdir(self.comfyui_install_dir) else ""
        self.comfyui_output_dir = os.path.normpath(os.path.join(self.comfyui_install_dir, "output")) if self.comfyui_install_dir and os.path.isdir(self.comfyui_install_dir) else ""

        self.comfyui_main_script = os.path.normpath(os.path.join(self.comfyui_install_dir, "main.py")) if self.comfyui_install_dir and os.path.isdir(self.comfyui_install_dir) else ""
        self.comfyui_api_port = self.config.get("comfyui_api_port", DEFAULT_COMFYUI_API_PORT)

        self.comfyui_base_args = [
            "--listen", "127.0.0.1", f"--port={self.comfyui_api_port}",
        ]

        # Add performance arguments based on selected options
        vram_mode = self.vram_mode_var.get()
        # Adjusted VRAM args based on common ComfyUI usage
        if vram_mode == "全负载(10GB以上)":
            # Default (no specific arg often means full) or --cuda-device if needed
            pass # No specific argument needed
        elif vram_mode == "高负载(8GB以上)":
            self.comfyui_base_args.append("--highvram")
        elif vram_mode == "中负载(4GB以上)":
            # Mapping "中负载" to "--lowvram" for VRAM reduction
            self.comfyui_base_args.append("--lowvram")
        elif vram_mode == "低负载(2GB以上)":
            self.comfyui_base_args.append("--lowvram")


        ckpt_prec = self.ckpt_precision_var.get()
        if ckpt_prec == "半精度(FP16)":
            self.comfyui_base_args.append("--force-fp16")

        clip_prec = self.clip_precision_var.get()
        if clip_prec == "半精度(FP16)":
            self.comfyui_base_args.append("--fp16-text-enc")
        elif clip_prec == "FP8 (E4M3FN)":
            self.comfyui_base_args.append("--fp8_e4m3fn-text-enc")
        elif clip_prec == "FP8 (E5M2)":
            self.comfyui_base_args.append("--fp8_e5m2-text-enc")


        unet_prec = self.unet_precision_var.get()
        if unet_prec == "半精度(BF16)":
            self.comfyui_base_args.append("--bf16-model")
        elif unet_prec == "半精度(FP16)":
            self.comfyui_base_args.append("--fp16-model")
        elif unet_prec == "FP8 (E4M3FN)":
            self.comfyui_base_args.append("--fp8_e4m3fn-unet")
        elif unet_prec == "FP8 (E5M2)":
            self.comfyui_base_args.append("--fp8_e5m2-unet")

        vae_prec = self.vae_precision_var.get()
        if vae_prec == "半精度(FP16)":
            self.comfyui_base_args.append("--fp16-vae")
        elif vae_prec == "半精度(BF16)":
            self.comfyui_base_args.append("--bf16-vae")


        if self.cuda_malloc_var.get() == "禁用":
            self.comfyui_base_args.append("--disable-cuda-malloc")

        if self.ipex_optimization_var.get() == "禁用":
            self.comfyui_base_args.append("--disable-ipex")

        if self.xformers_acceleration_var.get() == "禁用":
            self.comfyui_base_args.append("--disable-xformers")


        print(f"--- Paths Updated ---")
        print(f" ComfyUI Install Dir: {self.comfyui_install_dir}")
        print(f" ComfyUI Workflows Dir: {self.comfyui_workflows_dir}")
        print(f" ComfyUI Python Exe: {self.comfyui_portable_python}")
        print(f" Git Exe Path: {self.git_exe_path}") # New
        print(f" ComfyUI API Port: {self.comfyui_api_port}")
        print(f" ComfyUI Base Args: {' '.join(self.comfyui_base_args)}")

        # Set up auto-save trace after paths are updated and variables are set
        self._setup_url_auto_save()


    # Function to open folders (Keep)
    def open_folder(self, path):
        """Opens a given folder path using the default file explorer."""
        if not path or not os.path.isdir(path):
            messagebox.showwarning("路径无效 / Invalid Path", f"指定的文件夹不存在或无效:\n{path}", parent=self.root)
            print(f"[Launcher WARNING] Attempted to open invalid path: {path}")
            return
        try:
            # Use start for Windows, open for macOS, xdg-open for Linux
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin": # macOS
                subprocess.run(['open', path], check=True)
            else: # Linux and other Unix-like systems
                subprocess.run(['xdg-open', path], check=True)

            print(f"[Launcher INFO] Opened folder: {path}")
        except Exception as e:
            messagebox.showerror("打开文件夹失败 / Failed to Open Folder", f"无法打开文件夹:\n{path}\n错误: {e}", parent=self.root)
            print(f"[Launcher ERROR] Failed to open folder {path}: {e}")


    # Function to browse directory (Keep)
    def browse_directory(self, var_to_set, initial_dir=""):
        """Opens a directory selection dialog."""
        effective_initial_dir = initial_dir if os.path.isdir(initial_dir) else self.base_project_dir
        directory = filedialog.askdirectory(title="选择目录 / Select Directory", initialdir=effective_initial_dir, parent=self.root)
        if directory:
             normalized_path = os.path.normpath(directory)
             var_to_set.set(normalized_path)
             # Auto-update workflows dir if ComfyUI dir is set and workflows dir was default
             if var_to_set == self.comfyui_dir_var:
                  # Check if the current workflows UI value is empty OR matches the old derived default
                  # Get value from config before it's updated by save_settings
                  old_comfyui_dir_before_browse = self.config.get("comfyui_dir", "")
                  old_derived_default = os.path.normpath(os.path.join(old_comfyui_dir_before_browse, r"user\default\workflows")) if old_comfyui_dir_before_browse else ""
                  current_workflows_ui_val = self.comfyui_workflows_dir_var.get()

                  # Only update workflows_dir_var if user hadn't explicitly set it differently AND
                  # it was previously the default derived path or was empty.
                  if not current_workflows_ui_val or os.path.normpath(current_workflows_ui_val) == old_derived_default:
                       new_derived_default = os.path.normpath(os.path.join(normalized_path, r"user\default\workflows"))
                       self.comfyui_workflows_dir_var.set(new_derived_default)
             # Note: Derived paths internal variables are updated when saving settings


    # Function to browse file (Keep)
    def browse_file(self, var_to_set, filetypes, initial_dir=""):
        """Opens a file selection dialog."""
        effective_initial_dir = initial_dir if os.path.isdir(initial_dir) else self.base_project_dir
        filepath = filedialog.askopenfilename(title="选择文件 / Select File", filetypes=filetypes, initialdir=effective_initial_dir, parent=self.root)
        if filepath: var_to_set.set(os.path.normpath(filepath))

    # --- Styling Setup (Keep) ---
    def setup_styles(self):
        """Configures the ttk styles for the application."""
        self.style = ttk.Style(self.root)
        try: self.style.theme_use('clam')
        except tk.TclError: print("[Launcher WARNING] 'clam' theme not available, using default theme.")
        neutral_button_bg="#555555"; neutral_button_fg=FG_COLOR; n_active_bg="#6e6e6e"; n_pressed_bg="#7f7f7f"; n_disabled_bg="#4a5a6a"; n_disabled_fg=FG_MUTED
        self.style.configure('.', background=BG_COLOR, foreground=FG_COLOR, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL), bordercolor=BORDER_COLOR); self.style.map('.', background=[('active', '#4f4f4f'), ('disabled', '#404040')], foreground=[('disabled', FG_MUTED)])
        self.style.configure('TFrame', background=BG_COLOR); self.style.configure('Control.TFrame', background=CONTROL_FRAME_BG); self.style.configure('TabControl.TFrame', background=TAB_CONTROL_FRAME_BG);
        self.style.configure('Settings.TFrame', background=BG_COLOR); # Keep for Settings tab
        self.style.configure('ComfyuiBackend.TFrame', background=BG_COLOR); # New style for Comfyui Backend tab
        self.style.configure('ErrorAnalysis.TFrame', background=BG_COLOR); # New style for Error Analysis tab

        self.style.configure('TLabelframe', background=BG_COLOR, foreground=FG_COLOR, bordercolor=BORDER_COLOR, relief=tk.GROOVE); self.style.configure('TLabelframe.Label', background=BG_COLOR, foreground=FG_COLOR, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL, 'italic'))
        self.style.configure('TLabel', background=BG_COLOR, foreground=FG_COLOR); self.style.configure('Status.TLabel', background=CONTROL_FRAME_BG, foreground=FG_MUTED, padding=(5, 3)); self.style.configure('Version.TLabel', background=BG_COLOR, foreground=FG_MUTED, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL - 1))
        # Updated Hint Label style for slightly smaller text
        self.style.configure('Hint.TLabel', background=BG_COLOR, foreground=FG_MUTED, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL - 1), padding=(0, 0, 0, 0)) # Reduced padding


        main_pady=(10, 6); main_fnt=(FONT_FAMILY_UI, FONT_SIZE_NORMAL); main_fnt_bld=(FONT_FAMILY_UI, FONT_SIZE_NORMAL, FONT_WEIGHT_BOLD)
        self.style.configure('TButton', padding=(10, 6), anchor=tk.CENTER, font=main_fnt, borderwidth=0, relief=tk.FLAT, background=neutral_button_bg, foreground=neutral_button_fg); self.style.map('TButton', background=[('active', n_active_bg), ('pressed', n_pressed_bg), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])
        self.style.configure("Accent.TButton", padding=main_pady, font=main_fnt_bld, background=ACCENT_COLOR, foreground="white"); self.style.map("Accent.TButton", background=[('pressed', ACCENT_ACTIVE), ('active', '#006ae0'), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])
        self.style.configure("Stop.TButton", padding=main_pady, font=main_fnt, background=STOP_COLOR, foreground=FG_COLOR); self.style.map("Stop.TButton", background=[('pressed', STOP_ACTIVE), ('active', '#6e6e6e'), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])
        self.style.configure("StopRunning.TButton", padding=main_pady, font=main_fnt, background=STOP_RUNNING_BG, foreground=STOP_RUNNING_FG); self.style.map("StopRunning.TButton", background=[('pressed', STOP_RUNNING_ACTIVE_BG), ('active', STOP_RUNNING_ACTIVE_BG), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])
        tab_pady=(6, 4); tab_fnt=(FONT_FAMILY_UI, FONT_SIZE_NORMAL - 1); tab_neutral_bg=neutral_button_bg; tab_n_active_bg=n_active_bg; tab_n_pressed_bg=n_pressed_bg
        self.style.configure("TabAccent.TButton", padding=tab_pady, font=tab_fnt, background=tab_neutral_bg, foreground=neutral_button_fg); self.style.map("TabAccent.TButton", background=[('pressed', tab_n_pressed_bg), ('active', tab_n_active_bg), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])
        self.style.configure("TabStop.TButton", padding=tab_pady, font=tab_fnt, background=tab_neutral_bg, foreground=neutral_button_fg); self.style.map("TabStop.TButton", background=[('pressed', tab_n_pressed_bg), ('active', tab_n_active_bg), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])
        self.style.configure("TabStopRunning.TButton", padding=tab_pady, font=tab_fnt, background=tab_neutral_bg, foreground=neutral_button_fg); self.style.map("TabStopRunning.TButton", background=[('pressed', tab_n_pressed_bg), ('active', tab_n_active_bg), ('disabled', n_disabled_bg)], foreground=[('disabled', n_disabled_fg)])
        self.style.configure('TCheckbutton', background=BG_COLOR, foreground=FG_COLOR, font=main_fnt); self.style.map('TCheckbutton', background=[('active', BG_COLOR)], indicatorcolor=[('selected', ACCENT_COLOR), ('pressed', ACCENT_ACTIVE), ('!selected', FG_MUTED)], foreground=[('disabled', FG_MUTED)])
        self.style.configure('TCombobox', fieldbackground=TEXT_AREA_BG, background=TEXT_AREA_BG, foreground=FG_COLOR, arrowcolor=FG_COLOR, bordercolor=BORDER_COLOR, insertcolor=FG_COLOR, padding=(5, 4), font=main_fnt); self.style.map('TCombobox', fieldbackground=[('readonly', TEXT_AREA_BG), ('disabled', CONTROL_FRAME_BG)], foreground=[('disabled', FG_MUTED), ('readonly', FG_COLOR)], arrowcolor=[('disabled', FG_MUTED)], selectbackground=[('!focus', ACCENT_COLOR), ('focus', ACCENT_ACTIVE)], selectforeground=[('!focus', 'white'), ('focus', 'white')])
        try:
            self.root.option_add('*TCombobox*Listbox.background', TEXT_AREA_BG); self.root.option_add('*TCombobox*Listbox.foreground', FG_COLOR); self.root.option_add('*TCombobox*Listbox.selectBackground', ACCENT_ACTIVE); self.root.option_add('*TCombobox*Listbox.selectForeground', 'white'); self.root.option_add('*TCombobox*Listbox.font', (FONT_FAMILY_UI, FONT_SIZE_NORMAL)); self.root.option_add('*TCombobox*Listbox.borderWidth', 1); self.root.option_add('*TCombobox*Listbox.relief', 'solid')
        except tk.TclError as e: print(f"[Launcher WARNING] Could not set Combobox Listbox styles: {e}")
        self.style.configure('TNotebook', background=BG_COLOR, borderwidth=0, tabmargins=[5, 5, 5, 0]); self.style.configure('TNotebook.Tab', padding=[15, 8], background=BG_COLOR, foreground=FG_MUTED, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL), borderwidth=0); self.style.map('TNotebook.Tab', background=[('selected', '#4a4a4a'), ('active', '#3a3a3a')], foreground=[('selected', 'white'), ('active', FG_COLOR)], focuscolor=self.style.lookup('TNotebook.Tab', 'background'))
        self.style.configure('Horizontal.TProgressbar', thickness=6, background=ACCENT_COLOR, troughcolor=CONTROL_FRAME_BG, borderwidth=0)
        self.style.configure('TEntry', fieldbackground=TEXT_AREA_BG, foreground=FG_COLOR, insertcolor='white', bordercolor=BORDER_COLOR, borderwidth=1, padding=(5,4)); self.style.map('TEntry', fieldbackground=[('focus', TEXT_AREA_BG)], bordercolor=[('focus', ACCENT_COLOR)], lightcolor=[('focus', ACCENT_COLOR)])
        self.style.configure('Treeview', background=TEXT_AREA_BG, foreground=FG_STDOUT, fieldbackground=TEXT_AREA_BG, rowheight=22); self.style.configure('Treeview.Heading', font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL, 'bold'), background=CONTROL_FRAME_BG, foreground=FG_COLOR); self.style.map('Treeview', background=[('selected', ACCENT_ACTIVE)], foreground=[('selected', 'white')])


    # --- UI Setup ---
    def setup_ui(self):
        """Builds the main UI structure."""
        # Top Control Frame
        control_frame = ttk.Frame(self.root, padding=(10, 10, 10, 5), style='Control.TFrame'); control_frame.grid(row=0, column=0, sticky="ew"); control_frame.columnconfigure(1, weight=1)
        self.status_label = ttk.Label(control_frame, text="状态: 初始化...", style='Status.TLabel', anchor=tk.W); self.status_label.grid(row=0, column=0, sticky="w", padx=(0, 10)) # Set initial status
        ttk.Label(control_frame, text="", style='Status.TLabel').grid(row=0, column=1, sticky="ew") # Spacer
        self.progress_bar = ttk.Progressbar(control_frame, mode='indeterminate', length=350, style='Horizontal.TProgressbar'); self.progress_bar.grid(row=0, column=2, padx=10); self.progress_bar.stop()
        self.stop_all_button = ttk.Button(control_frame, text="停止", command=self.stop_all_services, style="Stop.TButton", width=12); self.stop_all_button.grid(row=0, column=3, padx=(0, 5))
        # Rename the run button text to "运行 ComfyUI" as it only starts backend now
        self.run_all_button = ttk.Button(control_frame, text="运行 ComfyUI", command=self.start_comfyui_service_thread, style="Accent.TButton", width=12); self.run_all_button.grid(row=0, column=4, padx=(0, 0))


        # Main Notebook (Tabs: 设置, 更新管理, Comfyui后台, 错误分析)
        self.notebook = ttk.Notebook(self.root, style='TNotebook'); self.notebook.grid(row=1, column=0, sticky="nsew", padx=5, pady=(0, 5)); self.notebook.enable_traversal()

        # --- Settings Tab ---
        self.settings_frame = ttk.Frame(self.notebook, padding="15", style='Settings.TFrame'); self.settings_frame.columnconfigure(0, weight=1); self.notebook.add(self.settings_frame, text=' 设置 / Settings ')
        current_row = 0; frame_padx = 5; frame_pady = (0, 10); widget_pady = 3; widget_padx = 5; label_min_width = 25

        # Folder Access Buttons (Keep existing layout and functionality)
        folder_button_frame = ttk.Frame(self.settings_frame, style='Settings.TFrame'); folder_button_frame.grid(row=current_row, column=0, sticky="ew", padx=frame_padx, pady=(0, widget_pady)); folder_button_frame.columnconfigure((0,1,2,3,4,5), weight=1); button_pady_reduced = 1;
        ttk.Button(folder_button_frame, text="Workflows", style='TButton', command=lambda: self.open_folder(self.comfyui_workflows_dir)).grid(row=0, column=0, padx=3, pady=button_pady_reduced, sticky='ew')
        ttk.Button(folder_button_frame, text="Nodes", style='TButton', command=lambda: self.open_folder(self.comfyui_nodes_dir)).grid(row=0, column=1, padx=3, pady=button_pady_reduced, sticky='ew')
        ttk.Button(folder_button_frame, text="Models", style='TButton', command=lambda: self.open_folder(self.comfyui_models_dir)).grid(row=0, column=2, padx=3, pady=button_pady_reduced, sticky='ew')
        ttk.Button(folder_button_frame, text="Lora", style='TButton', command=lambda: self.open_folder(self.comfyui_lora_dir)).grid(row=0, column=3, padx=3, pady=button_pady_reduced, sticky='ew')
        ttk.Button(folder_button_frame, text="Input", style='TButton', command=lambda: self.open_folder(self.comfyui_input_dir)).grid(row=0, column=4, padx=3, pady=button_pady_reduced, sticky='ew')
        ttk.Button(folder_button_frame, text="Output", style='TButton', command=lambda: self.open_folder(self.comfyui_output_dir)).grid(row=0, column=5, padx=3, pady=button_pady_reduced, sticky='ew')
        current_row += 1

        # Basic Settings Group (Updated Layout - Added Git Path, Updated Label)
        basic_group = ttk.LabelFrame(self.settings_frame, text=" 基本路径与端口 / Basic Paths & Ports ", padding=(10, 5)); basic_group.grid(row=current_row, column=0, sticky="ew", padx=frame_padx, pady=frame_pady);
        basic_group.columnconfigure(1, weight=1) # Column for entry/frames
        basic_row = 0 # Reset basic_row counter

        # ComfyUI Install Dir (Keep)
        ttk.Label(basic_group, text="ComfyUI 安装目录:", width=label_min_width, anchor=tk.W).grid(row=basic_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx); dir_entry = ttk.Entry(basic_group, textvariable=self.comfyui_dir_var); dir_entry.grid(row=basic_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); dir_btn = ttk.Button(basic_group, text="浏览", width=8, command=lambda: self.browse_directory(self.comfyui_dir_var, initial_dir=self.comfyui_dir_var.get()), style='TButton'); dir_btn.grid(row=basic_row, column=2, sticky=tk.E, pady=widget_pady, padx=(0, widget_padx)); basic_row += 1
        # ComfyUI Workflows Dir (Keep)
        ttk.Label(basic_group, text="ComfyUI 工作流目录:", width=label_min_width, anchor=tk.W).grid(row=basic_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx); workflows_dir_entry = ttk.Entry(basic_group, textvariable=self.comfyui_workflows_dir_var); workflows_dir_entry.grid(row=basic_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); workflows_dir_btn = ttk.Button(basic_group, text="浏览", width=8, command=lambda: self.browse_directory(self.comfyui_workflows_dir_var, initial_dir=self.comfyui_workflows_dir_var.get()), style='TButton'); workflows_dir_btn.grid(row=basic_row, column=2, sticky=tk.E, pady=widget_pady, padx=(0, widget_padx)); basic_row += 1
        # ComfyUI Python Exe (Keep)
        ttk.Label(basic_group, text="ComfyUI Python 路径:", width=label_min_width, anchor=tk.W).grid(row=basic_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx); py_entry = ttk.Entry(basic_group, textvariable=self.python_exe_var); py_entry.grid(row=basic_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); py_btn = ttk.Button(basic_group, text="浏览", width=8, command=lambda: self.browse_file(self.python_exe_var, [("Python Executable", "python.exe"), ("All Files", "*.*")], initial_dir=os.path.dirname(self.python_exe_var.get()) if self.python_exe_var.get() else ""), style='TButton'); py_btn.grid(row=basic_row, column=2, sticky=tk.E, pady=widget_pady, padx=(0, widget_padx)); basic_row += 1
        # New: Git Exe Path
        ttk.Label(basic_group, text="Git 可执行文件路径:", width=label_min_width, anchor=tk.W).grid(row=basic_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx); git_entry = ttk.Entry(basic_group, textvariable=self.git_exe_path_var); git_entry.grid(row=basic_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); git_btn = ttk.Button(basic_group, text="浏览", width=8, command=lambda: self.browse_file(self.git_exe_path_var, [("Git Executable", "git.exe"), ("All Files", "*.*")], initial_dir=os.path.dirname(self.git_exe_path_var.get()) if self.git_exe_path_var.get() else ""), style='TButton'); git_btn.grid(row=basic_row, column=2, sticky=tk.E, pady=widget_pady, padx=(0, widget_padx)); basic_row += 1

        # ComfyUI API Port - Adjusted layout
        ttk.Label(basic_group, text="ComfyUI 监听与共享端口:", width=label_min_width+8, anchor=tk.W).grid(row=basic_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        comfyui_port_entry = ttk.Entry(basic_group, textvariable=self.comfyui_api_port_var);
        comfyui_port_entry.grid(row=basic_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx);
        basic_row += 1


        current_row += 1


        # Performance Group (Updated with dropdowns - Removed '自动')
        perf_group = ttk.LabelFrame(self.settings_frame, text=" 性能与显存优化 / Performance & VRAM Optimization ", padding=(10, 5)); perf_group.grid(row=current_row, column=0, sticky="ew", padx=frame_padx, pady=frame_pady); perf_group.columnconfigure(1, weight=1); perf_row = 0
        # VRAM Mode
        ttk.Label(perf_group, text="显存优化:", width=label_min_width, anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx);
        vram_modes = ["全负载(10GB以上)", "高负载(8GB以上)", "中负载(4GB以上)", "低负载(2GB以上)"] # Removed "自动"
        vram_mode_combo = ttk.Combobox(perf_group, textvariable=self.vram_mode_var, values=vram_modes, state="readonly"); vram_mode_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); self.vram_mode_var.set(self.config.get("vram_mode", DEFAULT_VRAM_MODE)); perf_row += 1
        # CKPT Precision
        ttk.Label(perf_group, text="CKPT模型精度:", width=label_min_width, anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx);
        ckpt_precisions = ["全精度(FP32)", "半精度(FP16)"] # Removed "自动"
        ckpt_precision_combo = ttk.Combobox(perf_group, textvariable=self.ckpt_precision_var, values=ckpt_precisions, state="readonly"); ckpt_precision_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); self.ckpt_precision_var.set(self.config.get("ckpt_precision", DEFAULT_CKPT_PRECISION)); perf_row += 1
        # CLIP Precision
        ttk.Label(perf_group, text="CLIP编码精度:", width=label_min_width, anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx);
        clip_precisions = ["全精度(FP32)", "半精度(FP16)", "FP8 (E4M3FN)", "FP8 (E5M2)"] # Removed "自动"
        clip_precision_combo = ttk.Combobox(perf_group, textvariable=self.clip_precision_var, values=clip_precisions, state="readonly"); clip_precision_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); self.clip_precision_var.set(self.config.get("clip_precision", DEFAULT_CLIP_PRECISION)); perf_row += 1
        # UNET Precision
        ttk.Label(perf_group, text="UNET模型精度:", width=label_min_width, anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx);
        unet_precisions = ["半精度(BF16)", "半精度(FP16)", "FP8 (E4M3FN)", "FP8 (E5M2)"] # Removed "自动"
        unet_precision_combo = ttk.Combobox(perf_group, textvariable=self.unet_precision_var, values=unet_precisions, state="readonly"); unet_precision_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); self.unet_precision_var.set(self.config.get("unet_precision", DEFAULT_UNET_PRECISION)); perf_row += 1
        # VAE Precision
        ttk.Label(perf_group, text="VAE模型精度:", width=label_min_width, anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx);
        vae_precisions = ["全精度(FP32)", "半精度(FP16)", "半精度(BF16)"] # Removed "自动"
        vae_precision_combo = ttk.Combobox(perf_group, textvariable=self.vae_precision_var, values=vae_precisions, state="readonly"); vae_precision_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); self.vae_precision_var.set(self.config.get("vae_precision", DEFAULT_VAE_PRECISION)); perf_row += 1
        # CUDA Malloc (Keep)
        ttk.Label(perf_group, text="CUDA智能内存分配:", width=label_min_width, anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx);
        cuda_malloc_options = ["启用", "禁用"]
        cuda_malloc_combo = ttk.Combobox(perf_group, textvariable=self.cuda_malloc_var, values=cuda_malloc_options, state="readonly"); cuda_malloc_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); self.cuda_malloc_var.set(self.config.get("cuda_malloc", DEFAULT_CUDA_MALLOC)); perf_row += 1
         # IPEX Optimization (Keep)
        ttk.Label(perf_group, text="IPEX优化:", width=label_min_width, anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx);
        ipex_options = ["启用", "禁用"]
        ipex_combo = ttk.Combobox(perf_group, textvariable=self.ipex_optimization_var, values=ipex_options, state="readonly"); ipex_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); self.ipex_optimization_var.set(self.config.get("ipex_optimization", DEFAULT_IPEX_OPTIMIZATION)); perf_row += 1
         # xformers Acceleration (Keep)
        ttk.Label(perf_group, text="xformers加速:", width=label_min_width, anchor=tk.W).grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx);
        xformers_options = ["启用", "禁用"]
        xformers_combo = ttk.Combobox(perf_group, textvariable=self.xformers_acceleration_var, values=xformers_options, state="readonly"); xformers_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); self.xformers_acceleration_var.set(self.config.get("xformers_acceleration", DEFAULT_XFORMERS_ACCELERATION)); perf_row += 1

        current_row += 1
        # Spacer and Bottom Row - Ensure this pushes the bottom frame down
        self.settings_frame.rowconfigure(current_row, weight=1); current_row += 1
        bottom_frame = ttk.Frame(self.settings_frame, style='Settings.TFrame'); bottom_frame.grid(row=current_row, column=0, sticky="sew", pady=(15, 0)); bottom_frame.columnconfigure(1, weight=1)
        save_btn = ttk.Button(bottom_frame, text="保存设置", style="TButton", command=self.save_settings); save_btn.grid(row=0, column=0, sticky="sw", padx=(frame_padx, 0))
        version_label = ttk.Label(bottom_frame, text=VERSION_INFO, style="Version.TLabel"); version_label.grid(row=0, column=2, sticky="se", padx=(0, frame_padx))

        # --- Update Management Tab ---
        self.update_frame = ttk.Frame(self.notebook, padding="15", style='TFrame'); self.update_frame.columnconfigure(0, weight=1); self.update_frame.rowconfigure(1, weight=1) # Make bottom area (Node Management) expandable
        self.notebook.add(self.update_frame, text=' 更新管理 / Update Management ')

        update_current_row = 0
        # Repository Address Area
        repo_address_group = ttk.LabelFrame(self.update_frame, text=" 仓库地址 / Repository Address ", padding=(10, 5)); repo_address_group.grid(row=update_current_row, column=0, sticky="ew", padx=frame_padx, pady=frame_pady);
        repo_address_group.columnconfigure(1, weight=1) # Make entry column expandable
        repo_row = 0
        # Main Repo URL
        ttk.Label(repo_address_group, text="本体仓库地址:", width=label_min_width, anchor=tk.W).grid(row=repo_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx);
        main_repo_entry = ttk.Entry(repo_address_group, textvariable=self.main_repo_url_var);
        main_repo_entry.grid(row=repo_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); repo_row += 1
        # Node Config URL
        ttk.Label(repo_address_group, text="节点配置地址:", width=label_min_width, anchor=tk.W).grid(row=repo_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx);
        node_config_entry = ttk.Entry(repo_address_group, textvariable=self.node_config_url_var);
        node_config_entry.grid(row=repo_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx); repo_row += 1

        update_current_row += 1

        # Version & Node Management Area
        version_node_management_group = ttk.LabelFrame(self.update_frame, text=" 版本与节点管理 / Version & Node Management ", padding=(10, 5)); version_node_management_group.grid(row=update_current_row, column=0, sticky="nsew", padx=frame_padx, pady=frame_pady);
        version_node_management_group.columnconfigure(0, weight=1); version_node_management_group.rowconfigure(0, weight=1) # Make the notebook expandable

        # Sub-notebook for 本体 and 节点
        node_notebook = ttk.Notebook(version_node_management_group, style='TNotebook'); node_notebook.grid(row=0, column=0, sticky="nsew"); node_notebook.enable_traversal()

        # --- 本体 Sub-tab ---
        self.main_body_frame = ttk.Frame(node_notebook, style='TFrame', padding=5);
        self.main_body_frame.columnconfigure(0, weight=1);
        self.main_body_frame.columnconfigure(1, weight=0) # Column for scrollbar
        self.main_body_frame.rowconfigure(1, weight=1) # Row for Treeview expands

        node_notebook.add(self.main_body_frame, text=' 本体 / Main Body ')

        # Main Body Controls (Current Version, Refresh, Activate)
        main_body_control_frame = ttk.Frame(self.main_body_frame, style='TabControl.TFrame', padding=(5, 5));
        main_body_control_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5), columnspan=2); # Span across Treeview and scrollbar columns
        main_body_control_frame.columnconfigure(1, weight=1) # Spacer column to push buttons right

        # Current Version Label on the left
        ttk.Label(main_body_control_frame, text="当前本体版本:", style='TLabel').grid(row=0, column=0, sticky=tk.W, padx=(0, 5));
        self.current_main_body_version_label = ttk.Label(main_body_control_frame, textvariable=self.current_main_body_version_var, style='TLabel', anchor=tk.W, font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL, FONT_WEIGHT_BOLD));
        self.current_main_body_version_label.grid(row=0, column=0, sticky=tk.W, padx=(90, 5)); # Adjust padx to make space for "当前本体版本:"
        # Spacer in column 1 to push buttons
        ttk.Label(main_body_control_frame, text="", style='TLabel').grid(row=0, column=1, sticky="ew")
        # Refresh and Activate buttons on the right
        self.refresh_main_body_button = ttk.Button(main_body_control_frame, text="刷新版本", style="TabAccent.TButton", command=self._queue_main_body_refresh); # Call the queueing method
        self.refresh_main_body_button.grid(row=0, column=2, padx=(0, 5))
        self.activate_main_body_button = ttk.Button(main_body_control_frame, text="激活选中版本", style="TabAccent.TButton", command=self._queue_main_body_activation); # Call the queueing method
        self.activate_main_body_button.grid(row=0, column=3)

        # REQUIREMENT 2: Main Body Versions List (Treeview) with Scrollbar and Accurate Data
        # Updated columns for Requirement 2 "本体标签页"
        self.main_body_tree = ttk.Treeview(self.main_body_frame, columns=("version", "commit_id", "date", "description"), show="headings", style='Treeview')
        self.main_body_tree.heading("version", text="版本");
        self.main_body_tree.heading("commit_id", text="提交ID");
        self.main_body_tree.heading("date", text="日期");
        self.main_body_tree.heading("description", text="描述")
        self.main_body_tree.column("version", width=150, stretch=tk.NO); # Increased width
        self.main_body_tree.column("commit_id", width=100, stretch=tk.NO);
        self.main_body_tree.column("date", width=120, stretch=tk.NO);
        self.main_body_tree.column("description", width=300, stretch=tk.YES);
        self.main_body_tree.grid(row=1, column=0, sticky="nsew") # Treeview in column 0 of main_body_frame

        # Add vertical scrollbar for main_body_tree
        self.main_body_scrollbar = ttk.Scrollbar(self.main_body_frame, orient=tk.VERTICAL, command=self.main_body_tree.yview)
        self.main_body_tree.configure(yscrollcommand=self.main_body_scrollbar.set)
        self.main_body_scrollbar.grid(row=1, column=1, sticky="ns") # Scrollbar in column 1 of main_body_frame
        # Bind selection event to update activate button state
        self.main_body_tree.bind("<<TreeviewSelect>>", lambda event: self._update_ui_state())
        # --- END REQUIREMENT 2 (Layout part) ---

        # --- 节点 Sub-tab ---
        self.nodes_frame = ttk.Frame(node_notebook, style='TFrame', padding=5);
        self.nodes_frame.columnconfigure(0, weight=1);
        self.nodes_frame.columnconfigure(1, weight=0) # Column for scrollbar
        self.nodes_frame.rowconfigure(2, weight=1) # Row 2 (treeview) expands

        node_notebook.add(self.nodes_frame, text=' 节点 / Nodes ')

        # Nodes Search and Control
        nodes_control_frame = ttk.Frame(self.nodes_frame, style='TabControl.TFrame', padding=(5, 5));
        nodes_control_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5), columnspan=2); # Span across Treeview and scrollbar columns
        ttk.Label(nodes_control_frame, text="搜索:", style='TLabel').pack(side=tk.LEFT, padx=(0, 5))
        self.nodes_search_entry = ttk.Entry(nodes_control_frame, width=40);
        self.nodes_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10)) # Make search entry expand

        self.refresh_nodes_button = ttk.Button(nodes_control_frame, text="刷新节点列表", style="TabAccent.TButton", command=self._queue_node_list_refresh) # Call the queueing method
        self.refresh_nodes_button.pack(side=tk.LEFT, padx=5)
        self.switch_install_node_button = ttk.Button(nodes_control_frame, text="切换/安装选中版本", style="TabAccent.TButton", command=self._queue_node_switch_install) # Call the queueing method
        self.switch_install_node_button.pack(side=tk.LEFT, padx=5)
        # REQUIREMENT 5: Add "更新全部" button
        self.update_all_nodes_button = ttk.Button(nodes_control_frame, text="更新全部", style="TabAccent.TButton", command=self._queue_all_nodes_update) # Call the queueing method
        self.update_all_nodes_button.pack(side=tk.LEFT, padx=5)


        # Hint Label - Updated text
        ttk.Label(self.nodes_frame, text="列表默认显示本地 custom_nodes 目录下的全部节点。搜索时显示匹配的本地/在线节点。", style='Hint.TLabel').grid(row=1, column=0, sticky=tk.W, padx=5, pady=(0, 5), columnspan=2) # Span hint across columns


        # REQUIREMENT 4: Nodes List (Treeview) with Scrollbar and new column formatting
        # Updated columns and headings for Requirement 4 "节点标签页"
        # Changed "local_version" to "本地ID" and "version" to "仓库ID"
        self.nodes_tree = ttk.Treeview(self.nodes_frame, columns=("name", "status", "local_id", "repo_info", "repo_url"), show="headings", style='Treeview')
        self.nodes_tree.heading("name", text="节点名称");
        self.nodes_tree.heading("status", text="状态");
        self.nodes_tree.heading("local_id", text="本地ID"); # Renamed
        self.nodes_tree.heading("repo_info", text="仓库信息"); # Renamed and content changed (Remote ID + Date for installed, Branch for uninstalled)
        self.nodes_tree.heading("repo_url", text="仓库地址")
        # Adjust column widths slightly
        self.nodes_tree.column("name", width=200, stretch=tk.YES); # Allow name to take more space
        self.nodes_tree.column("status", width=80, stretch=tk.NO);
        self.nodes_tree.column("local_id", width=100, stretch=tk.NO); # Width for local ID (commit hash)
        self.nodes_tree.column("repo_info", width=180, stretch=tk.NO); # Increased width for remote info
        self.nodes_tree.column("repo_url", width=300, stretch=tk.YES) # Repo URL can also expand

        self.nodes_tree.grid(row=2, column=0, sticky="nsew") # Treeview in column 0 of nodes_frame

        # Add vertical scrollbar for nodes_tree
        self.nodes_scrollbar = ttk.Scrollbar(self.nodes_frame, orient=tk.VERTICAL, command=self.nodes_tree.yview)
        self.nodes_tree.configure(yscrollcommand=self.nodes_scrollbar.set)
        self.nodes_scrollbar.grid(row=2, column=1, sticky="ns") # Scrollbar in column 1 of nodes_frame

        # Configure Treeview tags for status coloring (add to setup_styles potentially) - Already present
        try:
            self.nodes_tree.tag_configure('installed', foreground=FG_INFO) # Greenish
            self.nodes_tree.tag_configure('not_installed', foreground=FG_MUTED) # Grayish
        except tk.TclError: pass # Ignore if tag config fails

        # Bind search entry to trigger refresh
        self.nodes_search_entry.bind("<KeyRelease>", lambda event: self.refresh_node_list())
        # Bind selection event to update switch/install button state
        self.nodes_tree.bind("<<TreeviewSelect>>", lambda event: self._update_ui_state())
        # --- END REQUIREMENT 4 & 5 (Layout part) ---


        # --- Comfyui Backend Tab (Confirmed layout) ---
        # Confirming existing layout: This layout already fills the space.
        self.main_frame = ttk.Frame(self.notebook, style='ComfyuiBackend.TFrame', padding=0);
        self.main_frame.columnconfigure(0, weight=1);
        self.main_frame.rowconfigure(0, weight=1) # Row 0 expands vertically

        # Rename the tab text
        self.notebook.add(self.main_frame, text=' Comfyui后台 / Comfyui Backend ')

        self.main_output_text = scrolledtext.ScrolledText(self.main_frame, wrap=tk.WORD, state=tk.DISABLED, font=(FONT_FAMILY_MONO, FONT_SIZE_MONO), bg=TEXT_AREA_BG, fg=FG_STDOUT, relief=tk.FLAT, borderwidth=1, bd=1, highlightthickness=1, highlightbackground=BORDER_COLOR, insertbackground="white");
        # Place in row 0, column 0 and make it stick to all sides
        self.main_output_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1);
        setup_text_tags(self.main_output_text)


        # --- Error Analysis Tab ---
        self.error_analysis_frame = ttk.Frame(self.notebook, padding="15", style='ErrorAnalysis.TFrame');
        self.error_analysis_frame.columnconfigure(0, weight=1); self.error_analysis_frame.rowconfigure(2, weight=1) # Row for the output text expands
        self.notebook.add(self.error_analysis_frame, text=' 错误分析 / Error Analysis ')

        error_current_row = 0
        # API Configuration Row 1 (Endpoint)
        api_endpoint_frame = ttk.Frame(self.error_analysis_frame, style='ErrorAnalysis.TFrame'); api_endpoint_frame.grid(row=error_current_row, column=0, sticky="ew", padx=frame_padx, pady=widget_pady); api_endpoint_frame.columnconfigure(1, weight=1)
        ttk.Label(api_endpoint_frame, text="API 接口:", width=label_min_width, anchor=tk.W).grid(row=0, column=0, sticky=tk.W, padx=(0, widget_padx));
        self.api_endpoint_entry = ttk.Entry(api_endpoint_frame, textvariable=self.error_api_endpoint_var); self.api_endpoint_entry.grid(row=0, column=1, sticky="ew")
        error_current_row += 1

        # API Configuration Row 2 (Key, Diagnose, Fix Buttons)
        api_control_frame = ttk.Frame(self.error_analysis_frame, style='ErrorAnalysis.TFrame'); api_control_frame.grid(row=error_current_row, column=0, sticky="ew", padx=frame_padx, pady=widget_pady); api_control_frame.columnconfigure(1, weight=1) # Spacer column to push buttons right

        ttk.Label(api_control_frame, text="API 密匙:", width=label_min_width, anchor=tk.W).grid(row=0, column=0, sticky=tk.W, padx=(0, widget_padx));
        # Use show="*" to mask the key
        self.api_key_entry = ttk.Entry(api_control_frame, textvariable=self.error_api_key_var, show="*");
        self.api_key_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10)) # Use sticky="ew" and weight=1

        # Buttons aligned to the right within the control frame
        self.diagnose_button = ttk.Button(api_control_frame, text="诊断", style="TButton", command=self.run_diagnosis);
        self.diagnose_button.grid(row=0, column=2, padx=(0, 5))
        self.fix_button = ttk.Button(api_control_frame, text="修复", style="TButton", command=self.run_fix);
        self.fix_button.grid(row=0, column=3)

        error_current_row += 1

        # Output Text Area (cmd code display box)
        self.error_analysis_text = scrolledtext.ScrolledText(self.error_analysis_frame, wrap=tk.WORD, state=tk.DISABLED, font=(FONT_FAMILY_MONO, FONT_SIZE_MONO), bg=TEXT_AREA_BG, fg=FG_STDOUT, relief=tk.FLAT, borderwidth=1, bd=1, highlightthickness=1, highlightbackground=BORDER_COLOR, insertbackground="white");
        self.error_analysis_text.grid(row=error_current_row, column=0, sticky="nsew", padx=1, pady=1);
        setup_text_tags(self.error_analysis_text) # Apply tags including 'api_output' and 'cmd'

        # Default to Settings tab initially (or Backend as requested visually?)
        # Let's default to Settings as it's the first tab and needs configuration.
        self.notebook.select(self.settings_frame)


    # --- Text/Output Methods (Keep and adapt) ---
    def insert_output(self, text_widget, line, source_tag="stdout"):
        """Inserts text into a widget with tags, handles auto-scroll."""
        if not text_widget or not text_widget.winfo_exists(): return
        text_widget.config(state=tk.NORMAL);
        tag = "stdout"
        if "[Launcher]" in source_tag:
             tag = "info"
        elif "ERR" in source_tag.upper() or "ERROR" in line.upper() or "Traceback" in line or "Failed" in line or "Exception" in line:
             tag = "stderr"
        elif "WARN" in source_tag.upper() or "WARNING" in line.upper():
             tag = "warn"
        elif "CRITICAL" in source_tag.upper():
             tag = "error"
        # New tags for error analysis output
        elif source_tag == "api_output":
             tag = "api_output"
        elif source_tag == "cmd":
             tag = "cmd"


        text_widget.insert(tk.END, line, (tag,));
        if text_widget.yview()[1] > 0.95:
             text_widget.see(tk.END)
        text_widget.config(state=tk.DISABLED)

    def log_to_gui(self, target, message, tag="info"):
         """Adds a message to the appropriate output queue."""
         if not message.endswith('\n'): message += '\n'
         # Route all standard output (ComfyUI, Launcher, Git) to main_output_text queue
         if target in ("ComfyUI", "Launcher", "Git", "Update"): # Added Update tag
             queue = self.comfyui_output_queue
             queue.put((f"[{target} {tag.upper()}]", message)) # Put message in queue
         elif target == "ErrorAnalysis": # New target for error analysis log - goes to separate widget
             # Directly insert into error analysis text area (using root.after for thread safety)
             self.root.after(0, lambda: self.insert_output(self.error_analysis_text, message, tag)) # Use error_analysis_text widget
         else: # Fallback for any other target (shouldn't happen)
             queue = self.comfyui_output_queue
             queue.put((f"[{target} {tag.upper()}]", message)) # Put message in queue


    def process_output_queues(self,):
        """Processes messages from the output queue and updates text widgets."""
        processed_comfy = 0
        max_lines_per_update = 50

        try:
            while not self.comfyui_output_queue.empty() and processed_comfy < max_lines_per_update:
                source, line = self.comfyui_output_queue.get_nowait()
                if line.strip() == _COMFYUI_READY_MARKER_.strip():
                    print(f"[Launcher INFO] Received ComfyUI ready marker.")
                    self._trigger_comfyui_browser_opening() # Call renamed trigger method
                else:
                    # Route all from comfyui_output_queue to main_output_text
                    self.insert_output(self.main_output_text, line, source)
                processed_comfy += 1
        except queue.Empty:
            pass

        self.root.after(UPDATE_INTERVAL_MS, self.process_output_queues)


    # stream_output function remains the same, only processes ComfyUI stream now
    def stream_output(self, process_stream, output_queue, stream_name):
        """Reads lines from a process stream and puts them into a queue."""
        # Only handle ComfyUI ready marker for the ComfyUI stream
        is_comfyui_stream = (stream_name == "[ComfyUI]") or (stream_name == "[ComfyUI ERR]")
        # marker_sent = False if is_comfyui_stream else True # Only check marker for ComfyUI streams - this is managed by self.comfyui_ready_marker_sent now

        api_port = self.config.get("comfyui_api_port", DEFAULT_COMFYUI_API_PORT)
        ready_str1 = f"Set up connection listening on:" # Match exact strings from ComfyUI startup
        ready_str2 = f"To see the GUI go to: http://127.0.0.1:{api_port}"
        ready_str3 = f"Uvicorn running on http://127.0.0.1:{api_port}"
        ready_strings = [ready_str1, ready_str2, ready_str3]

        try:
            # Use process_stream.read(1) in a loop or process_stream.readline if output is line buffered
            # Popen with text=True and encoding should make readline work reliably.
            # Alternatively, manually read byte by byte if needed for unusual streams,
            # but for standard console output, readline is better.
            # Using iter(process_stream.readline, b'') with text=True in Popen expects '' not b''
            for line in iter(process_stream.readline, ''): # Read lines until empty string is returned (pipe closed)
                if self.stop_event.is_set():
                    print(f"[Launcher INFO] {stream_name} stream reader received stop event.")
                    break

                if line:
                    output_queue.put((stream_name, line))
                    # Check for ComfyUI ready marker ONLY if it's a ComfyUI stream
                    # and we haven't sent the marker for this session yet.
                    if is_comfyui_stream and not self.comfyui_ready_marker_sent:
                        # Also check if the line contains "###" which can be a custom marker
                        if any(rs in line for rs in ready_strings) or "###" in line:
                             print(f"[Launcher INFO] {stream_name} stream detected ready string or custom marker. Queuing marker.")
                             output_queue.put(("[ComfyUI]", _COMFYUI_READY_MARKER_)); # Put marker with base comfyui source tag
                             self.comfyui_ready_marker_sent = True # Set the instance flag

            print(f"[Launcher INFO] {stream_name} stream reader thread finished due to end of stream or stop event.")

        except ValueError:
             # This might happen if pipe is closed abruptly
             print(f"[Launcher INFO] {stream_name} stream closed unexpectedly (ValueError).")
        except Exception as e:
            print(f"[Launcher ERROR] Error reading {stream_name} stream: {e}", exc_info=True)
        finally:
            try: process_stream.close()
            except Exception: pass


    # --- Service Management ---
    def _is_comfyui_running(self):
        """Checks if the managed ComfyUI process is currently running."""
        return self.comfyui_process is not None and self.comfyui_process.poll() is None

    def _is_update_task_running(self):
        """Checks if a background update task is currently running."""
        return self._update_task_running

    def _validate_paths_for_execution(self, check_comfyui=True, check_git=False, show_error=True):
        """Validates essential paths before attempting to start services or git operations."""
        paths_ok = True
        missing_files = []
        missing_dirs = []

        if check_comfyui:
            # Validate ComfyUI install directory
            if not self.comfyui_install_dir or not os.path.isdir(self.comfyui_install_dir):
                missing_dirs.append(f"ComfyUI 安装目录 ({self.comfyui_install_dir if self.comfyui_install_dir else '未配置'})")
                paths_ok = False
            # Validate Python executable path
            if not self.comfyui_portable_python or not os.path.isfile(self.comfyui_portable_python):
                missing_files.append(f"ComfyUI Python ({self.comfyui_portable_python if self.comfyui_portable_python else '未配置'})")
                paths_ok = False
            # Validate ComfyUI main script path (only if install dir is set and looks plausible)
            elif self.comfyui_install_dir and os.path.isdir(self.comfyui_install_dir) and not os.path.isfile(self.comfyui_main_script):
                 missing_files.append(f"ComfyUI 主脚本 ({self.comfyui_main_script})")
                 paths_ok = False

            # Workflows dir validation is less critical for starting, skip strict check here
            # if not self.comfyui_workflows_dir or not os.path.isdir(self.comfyui_workflows_dir):
            #      missing_dirs.append(f"ComfyUI 工作流目录 ({self.comfyui_workflows_dir})")
            #      paths_ok = False # Don't fail startup just for this? Maybe only warn.

        if check_git:
            # Validate Git executable path
             if not self.git_exe_path or not os.path.isfile(self.git_exe_path):
                  missing_files.append(f"Git 可执行文件 ({self.git_exe_path if self.git_exe_path else '未配置'})")
                  paths_ok = False

        if not paths_ok and show_error:
            error_message = "启动服务或执行操作失败，缺少必需的文件或目录。\n请在“设置”中配置路径。\n\n"
            if missing_files:
                error_message += "缺少文件:\n" + "\n".join(missing_files) + "\n\n"
            if missing_dirs:
                error_message += "缺少目录:\n" + "\n".join(missing_dirs)
            messagebox.showerror("路径配置错误 / Path Configuration Error", error_message.strip(), parent=self.root) # strip trailing newlines

        return paths_ok

    def start_comfyui_service_thread(self):
        """Starts ComfyUI service in a separate thread."""
        if self._is_comfyui_running():
            self.log_to_gui("ComfyUI", "ComfyUI 后台已在运行 / ComfyUI backend is already running", "warn"); return
        # Check if external ComfyUI is detected
        if self.comfyui_externally_detected:
             self.log_to_gui("ComfyUI", f"检测到外部 ComfyUI 已在端口 {self.comfyui_api_port} 运行。请先停止外部实例。/ External ComfyUI detected running on port {self.comfyui_api_port}. Please stop the external instance first.", "warn"); return
        # Check if an update task is running
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中，请稍候。/ An update task is in progress, please wait.", "warn"); return

        # Validate ComfyUI paths before starting
        if not self._validate_paths_for_execution(check_comfyui=True, check_git=False):
            return

        self.stop_event.clear();
        self.comfyui_externally_detected = False; # Ensure this is False when starting managed process
        self.backend_browser_triggered_for_session = False; # Reset browser flag
        self.comfyui_ready_marker_sent = False; # Reset marker flag

        # Update button state using _update_ui_state
        self.root.after(0, self._update_ui_state) # Disable buttons before thread starts

        self.progress_bar.start(10); self.status_label.config(text="状态: 启动 ComfyUI 后台... / Status: Starting ComfyUI Backend...");
        self.clear_output_widgets(); # Clear outputs when starting new session
        self.notebook.select(self.main_frame) # Switch to ComfyUI Backend tab

        thread = threading.Thread(target=self._start_comfyui_service, daemon=True); thread.start()


    def _start_comfyui_service(self):
        """Internal method to start the ComfyUI service subprocess."""
        if self._is_comfyui_running(): return

        port_to_check = int(self.config.get("comfyui_api_port", DEFAULT_COMFYUI_API_PORT))
        check_url = f"http://127.0.0.1:{port_to_check}/queue" # Standard ComfyUI API endpoint to check
        is_already_running = False
        try:
            print(f"[Launcher INFO] Checking if ComfyUI is running on {check_url} before launch...")
            # Use a smaller timeout
            response = requests.get(check_url, timeout=1.0) # Reduced timeout to 1 second
            if response.status_code == 200:
                is_already_running = True
                self.log_to_gui("ComfyUI", f"检测到 ComfyUI 已在端口 {port_to_check} 运行，跳过启动。/ ComfyUI detected running on port {port_to_check}, skipping launch.", "info")
                print(f"[Launcher INFO] ComfyUI detected running on port {port_to_check}. Skipping launch.")
                self.comfyui_externally_detected = True
                self.root.after(0, self._update_ui_state) # Update UI state to reflect detection
                self.comfyui_process = None # Ensure process handle is None if external is detected
                self._trigger_comfyui_browser_opening() # Open browser if external is detected
                return
            else:
                 print(f"[Launcher WARNING] Port check received unexpected status {response.status_code} from {check_url}. Proceeding with launch.")
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            print(f"[Launcher INFO] Port check timed out or connection refused for {check_url}. Port {port_to_check} likely free or service not ready. Proceeding with launch.")
        except Exception as e:
            print(f"[Launcher ERROR] Port check failed unexpectedly for {check_url}: {e}. Proceeding with launch.")


        # Ensure flags are reset if we proceed with launch
        self.backend_browser_triggered_for_session = False
        self.comfyui_ready_marker_sent = False
        self.comfyui_externally_detected = False


        try:
            self.log_to_gui("ComfyUI", f"启动 ComfyUI 后台于 {self.comfyui_install_dir}... / Starting ComfyUI Backend in {self.comfyui_install_dir}...")
            base_cmd = [self.comfyui_portable_python, "-s", "-u", self.comfyui_main_script];
            # Re-calculate base args here to ensure they are up-to-date with config
            self.update_derived_paths() # Re-calculate arguments based on current config

            comfyui_cmd_list = base_cmd + self.comfyui_base_args # Use updated args
            # Log command with quotes around executable and script paths for clarity
            cmd_log_list = [f'"{comfyui_cmd_list[0]}"', "-s", "-u", f'"{comfyui_cmd_list[2]}"'] + comfyui_cmd_list[3:]
            cmd_log_str = ' '.join(cmd_log_list)

            self.log_to_gui("ComfyUI", f"最终参数 / Final Arguments: {' '.join(self.comfyui_base_args)}")
            self.log_to_gui("ComfyUI", f"完整命令 / Full Command: {cmd_log_str}")

            comfy_env = os.environ.copy()
            # Fix UnicodeEncodeError by forcing UTF-8 output encoding / 通过强制 UTF-8 输出编码修复 UnicodeEncodeError
            comfy_env['PYTHONIOENCODING'] = 'utf-8'
            # Ensure PATH includes the Git directory if set, for subprocess calls that might need git
            git_dir_in_path = os.path.dirname(self.git_exe_path) if self.git_exe_path and os.path.isdir(os.path.dirname(self.git_exe_path)) else "" # Check if directory exists
            if git_dir_in_path:
                 comfy_env['PATH'] = git_dir_in_path + os.pathsep + comfy_env.get('PATH', '')
                 print(f"[Launcher INFO] Appending Git dir to PATH: {git_dir_in_path}")
            else:
                 print(f"[Launcher INFO] Git dir not added to PATH (path empty or invalid): {git_dir_in_path}")


            creationflags = 0; startupinfo = None
            if os.name == 'nt':
                # CREATE_NO_WINDOW hides the console window
                # Use CREATE_NEW_CONSOLE if you want a separate console window for debugging subprocess output directly
                # creationflags = subprocess.CREATE_NEW_CONSOLE
                creationflags = subprocess.CREATE_NO_WINDOW
                # startupinfo = subprocess.STARTUPINFO()
                # startupinfo.dwFlags |= subprocess.STARTF_USESTDHANDLES # Only needed if not using PIPE or CREATE_NO_WINDOW


            self.comfyui_process = subprocess.Popen(comfyui_cmd_list, cwd=self.comfyui_install_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0, creationflags=creationflags, startupinfo=startupinfo, env=comfy_env, text=True, encoding='utf-8', errors='replace')
            self.log_to_gui("ComfyUI", f"Backend PID: {self.comfyui_process.pid}")

            # Using threads with daemon=True ensures they close when the main app closes
            self.comfyui_reader_thread_stdout = threading.Thread(target=self.stream_output, args=(self.comfyui_process.stdout, self.comfyui_output_queue, "[ComfyUI]"), daemon=True); self.comfyui_reader_thread_stdout.start()
            self.comfyui_reader_thread_stderr = threading.Thread(target=self.stream_output, args=(self.comfyui_process.stderr, self.comfyui_output_queue, "[ComfyUI ERR]"), daemon=True); self.comfyui_reader_thread_stderr.start()

            # Give the process a moment to start and potentially fail immediately
            time.sleep(2);
            if not self._is_comfyui_running():
                exit_code = self.comfyui_process.poll() if self.comfyui_process else 'N/A'
                error_reason = f"ComfyUI 后台进程意外终止，退出码 {exit_code}。/ ComfyUI backend process terminated unexpectedly with exit code {exit_code}."
                # Attempt to capture immediate stderr output
                stderr_output = ""
                stdout_output = ""
                try:
                    # Use communicate with a short timeout to drain pipes if the process exited quickly
                    # This is better than just reading.
                    stdout_output, stderr_output = self.comfyui_process.communicate(timeout=1)
                    stdout_output = stdout_output.strip()
                    stderr_output = stderr_output.strip()

                    if stdout_output: error_reason += f"\n\nStdout Output:\n{stdout_output}"
                except subprocess.TimeoutExpired:
                    print("[Launcher WARNING] Could not capture immediate output from terminated ComfyUI process.")
                except Exception as read_err:
                     print(f"[Launcher WARNING] Error reading output from terminated ComfyUI process: {read_err}")

                if stderr_output: error_reason += f"\n\nStderr Output:\n{stderr_output}"

                # Check if port might be the issue
                try:
                    # Check if the port is actively listening after process exit
                    # If it is, something else is using it. If not, the process likely failed before binding.
                    s = socket.create_connection(("127.0.0.1", port_to_check), timeout=0.5)
                    s.close()
                    error_reason += f"\n\n可能原因：端口 {port_to_check} 似乎已被占用。/ Possible reason: Port {port_to_check} appears to be already in use."
                except (ConnectionRefusedError, socket.timeout):
                    pass # Port is likely free or the process didn't bind yet / Port check failed
                except Exception as port_check_err:
                    print(f"[Launcher WARNING] Error checking port {port_to_check} after ComfyUI termination: {port_check_err}")


                raise Exception(error_reason) # Raise the collected error


            self.log_to_gui("ComfyUI", "ComfyUI 后台服务已启动 / ComfyUI backend service started");
            # Browser opening is triggered by the ready marker from the stream_output thread
            self.root.after(0, self._update_ui_state) # Update UI state

        except FileNotFoundError:
             error_msg = f"启动 ComfyUI 后台失败: 找不到指定的 Python 或 Git 文件。/ Failed to start ComfyUI Backend: Specified Python or Git executable not found.";
             print(f"[Launcher CRITICAL] {error_msg}");
             self.log_to_gui("ComfyUI", error_msg, "error");
             self.root.after(0, lambda: messagebox.showerror("ComfyUI 后台错误 / ComfyUI Backend Error", f"启动 ComfyUI 后台失败:\n找不到指定的 Python 或 Git 文件。\n请检查设置中的路径配置。", parent=self.root));
             self.comfyui_process = None; # Ensure process handle is cleared on error
             self.root.after(0, self.reset_ui_on_error); # Reset UI state
        except Exception as e:
            error_msg = f"启动 ComfyUI 后台失败: {e} / Failed to start ComfyUI Backend: {e}";
            print(f"[Launcher CRITICAL] {error_msg}");
            self.log_to_gui("ComfyUI", error_msg, "error");
            self.root.after(0, lambda msg=str(e): messagebox.showerror("ComfyUI 后台错误 / ComfyUI Backend Error", f"启动 ComfyUI 后台失败:\n{msg}", parent=self.root));
            self.comfyui_process = None; # Ensure process handle is cleared on error
            self.root.after(0, self.reset_ui_on_error); # Reset UI state


    def _stop_comfyui_service(self):
        """Internal method to stop the ComfyUI service subprocess."""
        # Consider if we want to stop externally detected ComfyUI - probably not managed
        self.comfyui_externally_detected = False; # Assume stopping means we lose track of any external process

        if not self._is_comfyui_running():
            self.log_to_gui("ComfyUI", "ComfyUI 后台未由此启动器管理或未运行 / ComfyUI backend is not managed by this launcher or not running", "warn");
            self.root.after(0, self._update_ui_state); # Update UI even if nothing stops
            return

        self.log_to_gui("ComfyUI", "停止 ComfyUI 后台... / Stopping ComfyUI Backend...")
        # Update button state using _update_ui_state
        self.root.after(0, self._update_ui_state) # Disable buttons before stopping

        self.status_label.config(text="状态: 停止 ComfyUI 后台... / Status: Stopping ComfyUI Backend..."); self.progress_bar.start(10);
        try:
            # Signal stop to stream readers and then terminate process
            self.stop_event.set();
            time.sleep(0.1); # Give threads a moment to react
            # Use terminate first for graceful shutdown
            self.comfyui_process.terminate()
            try:
                self.comfyui_process.wait(timeout=10); # Give it more time to terminate
                self.log_to_gui("ComfyUI", "ComfyUI 后台已终止 / ComfyUI backend terminated")
            except subprocess.TimeoutExpired:
                print("[Launcher WARNING] ComfyUI process did not terminate gracefully within timeout, killing.")
                self.log_to_gui("ComfyUI", "强制终止 ComfyUI 后台... / Forcibly terminating ComfyUI Backend...", "warn");
                self.comfyui_process.kill(); # Use kill if terminate times out
                self.log_to_gui("ComfyUI", "ComfyUI 后台已强制终止 / ComfyUI backend forcibly terminated")
        except Exception as e:
            error_msg = f"停止 ComfyUI 后台出错: {e} / Error stopping ComfyUI backend: {e}"; print(f"[Launcher ERROR] {error_msg}"); self.log_to_gui("ComfyUI", error_msg, "stderr")
        finally:
            self.comfyui_process = None; # Clear process handle
            self.stop_event.clear(); # Reset stop event
            self.backend_browser_triggered_for_session = False; # Reset browser flag
            self.comfyui_ready_marker_sent = False; # Reset marker flag
            self.root.after(0, self._update_ui_state) # Update UI state


    def start_all_services_thread(self):
        """Starts all necessary services (only ComfyUI now) in a separate thread."""
        # Check if ComfyUI is already running (either managed or external)
        if self._is_comfyui_running() or self.comfyui_externally_detected:
            messagebox.showinfo("服务已运行 / Service Running", "ComfyUI 后台已在运行或已被检测到。/ ComfyUI backend is already running or detected.", parent=self.root); return
         # Check if an update task is running
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中，请稍候。/ An update task is in progress, please wait.", "warn"); return

        # Validate ComfyUI paths before starting
        if not self._validate_paths_for_execution(check_comfyui=True, check_git=False):
            return

        # Update button state using _update_ui_state
        self.root.after(0, self._update_ui_state) # Disable buttons before thread starts

        self.progress_bar.start(10); self.status_label.config(text="状态: 启动 ComfyUI 后台... / Status: Starting ComfyUI Backend...");
        self.clear_output_widgets(); # Clear outputs when starting new session
        self.notebook.select(self.main_frame); # Switch to ComfyUI Backend tab

        thread = threading.Thread(target=self._start_comfyui_service, daemon=True); thread.start()

    # Renamed _run_all_services to _run_comfyui_service as only ComfyUI is started
    # This method is slightly misleading now as _start_comfyui_service is the main one
    # Retained for compatibility but _start_comfyui_service does the actual work
    # This method is no longer called, removed it from the UI command.
    # def _run_comfyui_service(self):
    #     """Internal method to start ComfyUI service. (Helper, actual start is in _start_comfyui_service)."""
    #     self._start_comfyui_service()
    #     # Wait briefly for the process to start and potentially trigger the ready marker
    #     time.sleep(1) # Give it a moment
    #     # Update UI state after attempting to start ComfyUI
    #     self.log_to_gui("Launcher", "ComfyUI 后台启动流程完成 / ComfyUI backend startup procedure complete", "info")
    #     self.root.after(0, self._update_ui_state)


    def stop_all_services(self):
        """Stops ComfyUI service if it is running."""
        # If ComfyUI is not running (managed or external), just update state
        if not self._is_comfyui_running() and not self.comfyui_externally_detected and not self._is_update_task_running():
             print("[Launcher INFO] Stop all: No managed process active or detected.")
             self._update_ui_state();
             return

        # If managed ComfyUI is running, stop it
        if self._is_comfyui_running():
             self.log_to_gui("Launcher", "停止所有服务 (仅 ComfyUI 后台)... / Stopping all services (ComfyUI Backend only)...", "info")
             # Update button state using _update_ui_state
             self.root.after(0, self._update_ui_state) # Disable buttons before stopping
             self.status_label.config(text="状态: 停止 ComfyUI 后台... / Status: Stopping ComfyUI Backend...")
             self.progress_bar.start(10)
             self._stop_comfyui_service()
        # If ComfyUI was detected externally but not managed, just update state to clear detection flag
        elif self.comfyui_externally_detected:
            self.comfyui_externally_detected = False
            self.log_to_gui("ComfyUI", "检测到外部 ComfyUI，未尝试停止。/ External ComfyUI detected, not attempting to stop.", "info")
            self._update_ui_state()

        # If an update task is running, signal it to stop
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "停止当前更新任务... / Stopping current update task...", "info")
             # Stopping update tasks is handled within the _update_task_worker loop if stop_event is checked.
             # Setting the stop event will signal the worker thread to stop processing.
             self.stop_event.set()
             self.root.after(0, self._update_ui_state) # Update UI state


    # --- Git Execution Helper ---
    def _run_git_command(self, command_list, cwd, timeout=300): # Increased default timeout
        """Runs a git command and returns stdout, stderr, and return code."""
        git_exe = self.git_exe_path_var.get()
        if not git_exe or not os.path.isfile(git_exe):
             err_msg = f"Git 可执行文件路径未配置或无效: {git_exe}"
             # log_to_gui is used within refresh functions, so we don't log here to avoid double logging on error
             # self.log_to_gui("Git", err_msg, "error")
             return "", err_msg, 127 # Indicate error if git path is bad

        # Prepend the git executable to the command list
        full_cmd = [git_exe] + command_list

        # Use a copy of the environment and ensure PYTHONIOENCODING is set for subprocesses launched by git
        git_env = os.environ.copy()
        git_env['PYTHONIOENCODING'] = 'utf-8'


        try:
            # Log the command being executed
            # Safely quote arguments containing spaces or special characters
            cmd_log_list = [shlex.quote(arg) for arg in full_cmd]
            cmd_log_str = ' '.join(cmd_log_list)

            self.log_to_gui("Git", f"执行: {cmd_log_str}", "cmd")
            self.log_to_gui("Git", f"工作目录: {cwd}", "cmd")

            # Run the command
            # Use separate threads for reading pipes to prevent deadlock on Windows
            process = subprocess.Popen(
                full_cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                # bufsize=0, # Not needed with separate threads and text=True
                text=True, # Decode stdout/stderr as text
                encoding='utf-8', # Explicitly use utf-8 for decoding
                errors='replace', # Replace characters that can't be decoded
                startupinfo=None,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                env=git_env # Use the modified environment
            )

            # Use the single ComfyUI output queue for all subprocess output
            # Prefix with "[Git stdout]" or "[Git stderr]"
            stdout_thread = threading.Thread(target=self.stream_output, args=(process.stdout, self.comfyui_output_queue, "[Git stdout]"), daemon=True)
            stderr_thread = threading.Thread(target=self.stream_output, args=(process.stderr, self.comfyui_output_queue, "[Git stderr]"), daemon=True)

            stdout_thread.start()
            stderr_thread.start()

            # Wait for the process to complete with timeout
            try:
                returncode = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.log_to_gui("Git", f"Git 命令超时 ({timeout} 秒), 进程被终止。", "error")
                try: process.kill()
                except OSError: pass # Ignore if already terminated
                returncode = 124 # Timeout code

            # Wait for the reader threads to finish (they should finish quickly after process ends)
            stdout_thread.join(timeout=5) # Give readers a moment
            stderr_thread.join(timeout=5)

            # No need to collect output from queues here, stream_output sends it to the main queue.
            # We only need the return code and potential lingering error message from stderr pipe if threads didn't catch it all.
            # For simplicity and reliability, we'll just return empty strings for stdout/stderr here
            # and rely on the queue processing for displaying output.
            # However, the calling functions might need the output string for logic (e.g., parsing commit IDs).
            # Let's re-evaluate: returning the collected output is necessary for parsing.
            # The stream_output is for *displaying* to the GUI. The caller needs the *string* result.

            # Let's re-implement output collection while still streaming to GUI queue
            stdout_output_list = []
            stderr_output_list = []

            # Re-run the command, but capture output instead of streaming directly
            # This means the _run_git_command needs to change, or we need a different helper for logic vs display.
            # Let's modify this helper to capture and return, and rely on log_to_gui for display.

            # --- Revised _run_git_command to capture and log ---
            process = subprocess.Popen(
                full_cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, encoding='utf-8', errors='replace',
                startupinfo=None,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                env=git_env
            )

            stdout_buffer = []
            stderr_buffer = []

            # Read stdout and stderr line by line and log to GUI, also buffer
            def read_pipe(pipe, buffer, source_name):
                 try:
                      for line in iter(pipe.readline, ''):
                           self.log_to_gui("Git", line.strip(), source_name) # Log to GUI (strip newline for log_to_gui)
                           buffer.append(line) # Append with newline for accurate reconstruction
                 except Exception as e:
                      print(f"[Launcher ERROR] Error reading pipe from {source_name} (capture): {e}")
                 finally:
                      try: pipe.close()
                      except Exception: pass

            stdout_thread = threading.Thread(target=read_pipe, args=(process.stdout, stdout_buffer, "[Git stdout]"), daemon=True)
            stderr_thread = threading.Thread(target=read_pipe, args=(process.stderr, stderr_buffer, "[Git stderr]"), daemon=True)

            stdout_thread.start()
            stderr_thread.start()

            # Wait for process completion
            try:
                returncode = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.log_to_gui("Git", f"Git 命令超时 ({timeout} 秒), 进程被终止。", "error")
                try: process.kill()
                except OSError: pass
                returncode = 124

            # Wait for reader threads to finish consuming output
            stdout_thread.join(timeout=5)
            stderr_thread.join(timeout=5)

            stdout_output = "".join(stdout_buffer)
            stderr_output = "".join(stderr_buffer)

            if returncode != 0:
                 self.log_to_gui("Git", f"Git 命令返回非零退出码 {returncode}.", "error")
                 # Detailed error output is already logged by the read_pipe threads
                 # if stderr_output: self.log_to_gui("Git", f"stderr:\n{stderr_output.strip()}", "stderr")
                 # if stdout_output: self.log_to_gui("Git", f"stdout:\n{stdout_output.strip()}", "stdout")


            return stdout_output, stderr_output, returncode

        except FileNotFoundError:
            error_msg = f"Git 可执行文件未找到: {git_exe}"
            self.log_to_gui("Git", error_msg, "error")
            return "", error_msg, 127 # Standard Linux exit code for command not found
        except Exception as e:
            error_msg = f"执行 Git 命令时发生意外错误: {e}\n命令: {' '.join(full_cmd)}" # Use full_cmd here
            self.log_to_gui("Git", error_msg, "error")
            return "", error_msg, 1 # Generic error code

    # --- Update Task Worker Thread ---
    def _update_task_worker(self):
        """Worker thread that processes update tasks from the queue."""
        while True:
            try:
                # Get a task from the queue, block indefinitely until one is available
                task_func, task_args, task_kwargs = self.update_task_queue.get()
                self._update_task_running = True # Set flag
                self.root.after(0, self._update_ui_state) # Update UI state to show busy/disabled buttons

                try:
                    # Execute the task function
                    task_func(*task_args, **task_kwargs)
                except Exception as e:
                    print(f"[Launcher ERROR] Update task failed: {e}", exc_info=True)
                    self.log_to_gui("Launcher", f"更新任务执行失败: {e}", "error")
                    self.root.after(0, lambda msg=str(e): messagebox.showerror("更新任务失败 / Update Task Failed", f"更新任务执行失败:\n{msg}", parent=self.root))

                finally:
                    self.update_task_queue.task_done() # Mark task as done
                    self._update_task_running = False # Clear flag
                    self.stop_event.clear() # Reset stop event for the next task
                    self.root.after(0, self._update_ui_state) # Update UI state to idle/enabled buttons


            except queue.Empty:
                # This should not happen with a blocking get(), but as a fallback
                time.sleep(0.1)
            except Exception as e:
                print(f"[Launcher CRITICAL] Error in update task worker loop: {e}", exc_info=True)
                time.sleep(1) # Prevent tight loop on unexpected errors


    # --- Queueing Methods for UI actions ---
    def _queue_main_body_refresh(self):
        """Queues the main body version refresh task."""
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中，无法刷新本体版本。", "warn"); return
        self.log_to_gui("Launcher", "将刷新本体版本任务添加到队列...", "info")
        self.update_task_queue.put((self.refresh_main_body_versions, [], {})) # Add task to queue
        self.root.after(0, self._update_ui_state) # Update UI state immediately


    def _queue_main_body_activation(self):
        """Queues the main body version activation task."""
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中，无法激活本体版本。", "warn"); return

        selected_item = self.main_body_tree.focus()
        if not selected_item:
            messagebox.showwarning("未选择版本 / No Version Selected", "请从列表中选择一个要激活的本体版本。", parent=self.root)
            return

        version_data = self.main_body_tree.item(selected_item, 'values')
        if not version_data or len(version_data) < 4:
             self.log_to_gui("Update", "无法获取选中的本体版本数据。", "error")
             messagebox.showerror("数据错误", "无法获取选中的本体版本数据，请刷新列表。", parent=self.root)
             return

        selected_version_name = version_data[0] # e.g., tag@v1.2.3, branch@main
        selected_commit_id_short = version_data[1] # Short commit ID displayed

        # We need the full commit ID for checkout. Find it from stored remote_main_body_versions
        full_commit_id = None
        for ver in self.remote_main_body_versions:
            # Check if the displayed short ID matches the beginning of the full ID
            if ver["commit_id"].startswith(selected_commit_id_short):
                 full_commit_id = ver["commit_id"]
                 break

        if not full_commit_id:
             # Fallback: try to get the full ID from the short one using git rev-parse
             comfyui_dir = self.comfyui_dir_var.get()
             if comfyui_dir and os.path.isdir(comfyui_dir) and os.path.isdir(os.path.join(comfyui_dir, ".git")) and self._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=False):
                  stdout, stderr, returncode = self._run_git_command(["rev-parse", selected_commit_id_short], cwd=comfyui_dir, timeout=5)
                  if returncode == 0 and stdout:
                       full_commit_id = stdout.strip()
                       self.log_to_gui("Update", f"通过 git rev-parse 获取到完整提交 ID: {full_commit_id[:8]}", "info")
                  else:
                       self.log_to_gui("Update", f"无法解析选中的版本 '{selected_version_name}' 的完整提交 ID (git rev-parse 失败): {stderr if stderr else '未知错误'}", "error")
                       messagebox.showerror("版本错误 / Version Error", f"无法解析选中的版本 '{selected_version_name}' 的完整提交 ID。", parent=self.root)
                       self._update_ui_state()
                       return
             else:
                  self.log_to_gui("Update", "无法解析选中的本体版本，Git或目录路径配置无效。", "error")
                  messagebox.showerror("配置或Git错误", "无法解析选中的本体版本，请检查Git路径和ComfyUI目录配置。", parent=self.root)
                  self._update_ui_state()
                  return


        main_repo_url = self.main_repo_url_var.get()
        comfyui_dir = self.comfyui_dir_var.get()

        # Validate paths before proceeding
        if not self._validate_paths_for_execution(check_comfyui=True, check_git=True, show_error=True):
             self.log_to_gui("Update", "无法激活本体版本: 路径配置无效。/ Cannot activate main body version: Path configuration invalid.", "error")
             return
        # Check if the ComfyUI dir is a git repo
        if not os.path.isdir(comfyui_dir) or not os.path.isdir(os.path.join(comfyui_dir, ".git")):
             self.log_to_gui("Update", f"'{comfyui_dir}' 不是一个 Git 仓库，无法激活版本。", "error")
             messagebox.showerror("Git 仓库错误 / Git Repository Error", f"ComfyUI 安装目录不是一个有效的 Git 仓库:\n{comfyui_dir}\n请确保该目录是 Git 克隆的。", parent=self.root)
             self._update_ui_state()
             return


        confirm = messagebox.askyesno("确认激活 / Confirm Activation", f"确定要下载并覆盖安装本体版本 '{selected_version_name}' (提交ID: {full_commit_id[:8]}) 吗？\n此操作会修改 '{comfyui_dir}' 目录。\n\n警告: 激活不同版本可能导致当前节点不兼容，请谨慎操作！", parent=self.root)
        if not confirm: return

        self.log_to_gui("Launcher", f"将激活本体版本 '{selected_version_name}' (提交ID: {full_commit_id[:8]}) 任务添加到队列...", "info")
        # Queue the activation task
        self.update_task_queue.put((self._activate_main_body_version_task, [comfyui_dir, full_commit_id], {}))
        self.root.after(0, self._update_ui_state) # Update UI state immediately


    def _queue_node_list_refresh(self):
        """Queues the node list refresh task."""
        # No need to check if update task is running for simple list refresh (unless it involves network/git)
        # The current implementation does involve git, so we should queue it.
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中，无法刷新节点列表。", "warn"); return
        self.log_to_gui("Launcher", "将刷新节点列表任务添加到队列...", "info")
        self.update_task_queue.put((self.refresh_node_list, [], {})) # Add task to queue
        self.root.after(0, self._update_ui_state) # Update UI state immediately


    def _queue_node_switch_install(self):
        """Queues the node switch/install task."""
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中，无法切换/安装节点。", "warn"); return

        selected_item = self.nodes_tree.focus()
        if not selected_item:
            messagebox.showwarning("未选择节点 / No Node Selected", "请从列表中选择一个要切换/安装的节点。", parent=self.root)
            return

        # Get data from the 5-column treeview item
        # Columns: ("name", "status", "local_id", "repo_info", "repo_url")
        node_data = self.nodes_tree.item(selected_item, 'values')
        if not node_data or len(node_data) < 5:
             self.log_to_gui("Update", "无法获取选中的节点数据。", "error")
             messagebox.showerror("数据错误", "无法获取选中的节点数据，请刷新列表。", parent=self.root)
             return

        node_name = node_data[0]
        node_status = node_data[1]
        local_id = node_data[2] # Local commit ID string from treeview
        repo_info = node_data[3] # Remote info string from treeview
        repo_url = node_data[4] # Repo URL from treeview

        git_exe = self.git_exe_path_var.get()
        comfyui_nodes_dir = self.comfyui_nodes_dir

        # Validate paths before proceeding
        if not self._validate_paths_for_execution(check_comfyui=True, check_git=True, show_error=True):
             self.log_to_gui("Update", "无法切换/安装节点版本: 路径配置无效。/ Cannot switch/install node version: Path configuration invalid.", "error")
             return
        # Ensure nodes directory exists before attempting git operations within it
        if not comfyui_nodes_dir or not os.path.isdir(comfyui_nodes_dir):
             self.log_to_gui("Update", f"无法切换/安装节点: ComfyUI custom_nodes 目录未找到或无效 ({comfyui_nodes_dir})。", "error")
             messagebox.showerror("目录错误 / Directory Error", f"ComfyUI custom_nodes 目录未找到或无效:\n{comfyui_nodes_dir}\n请检查设置中的 ComfyUI 安装目录。", parent=self.root)
             return

        # Cannot install/switch if no valid repo URL is known
        if not repo_url or repo_url in ("本地安装，无Git信息", "无法获取远程 URL", "本地安装"):
             self.log_to_gui("Update", f"无法切换/安装节点 '{node_name}': 该节点无有效的仓库地址信息。/ Cannot switch/install node '{node_name}': This node has no valid repository URL information.", "error")
             messagebox.showerror("节点信息缺失 / Missing Node Info", f"节点 '{node_name}' 无有效的仓库地址，无法进行版本切换或安装。", parent=self.root)
             return

        # Determine the node's expected installation path based on repo URL
        repo_name_from_url = repo_url.split('/')[-1]
        if repo_name_from_url.lower().endswith('.git'):
             repo_name_from_url = repo_name_from_url[:-4]
        node_install_path = os.path.normpath(os.path.join(comfyui_nodes_dir, repo_name_from_url))

        # Determine target version based on what's displayed in the "仓库信息" column (Remote Info)
        # For installed nodes, repo_info is "branch_name (YYYY-MM-DD)". We need the branch name.
        # For uninstalled nodes, repo_info is just the branch name from the online config.
        # Take the part before the date if present, otherwise the whole string.
        target_ref = repo_info.split(' ')[0].strip()
        if target_ref in ("未知远程", "N/A", "信息获取失败"):
             # Fallback to a default branch if remote info is not useful
             target_ref = "main" # Or "master"
             self.log_to_gui("Update", f"无法解析远程版本信息 '{repo_info}'，使用默认目标分支 '{target_ref}'。", "warn")

        action = "安装" if node_status != "已安装" else "切换版本到"
        confirm_msg = f"确定要对节点 '{node_name}' 执行 '{action}' 操作吗？\n" \
                      f"仓库地址: {repo_url}\n" \
                      f"目标版本/分支: {target_ref}\n" \
                      f"操作目录: {node_install_path}\n\n"

        if node_status != "已安装":
             confirm_msg += "此操作将在 custom_nodes 目录下克隆仓库。"
        else:
             confirm_msg += "此操作将修改节点目录内容。\n警告：切换版本可能需要重新安装依赖，且可能丢失本地修改！\n建议在切换前备份节点目录。\n确认前请确保 ComfyUI 已停止运行。"

        confirm = messagebox.askyesno("确认操作 / Confirm Action", confirm_msg, parent=self.root)
        if not confirm: return

        self.log_to_gui("Launcher", f"将对节点 '{node_name}' 执行 '{action}' (目标引用: {target_ref}) 任务添加到队列...", "info")
        # Queue the switch/install task
        self.update_task_queue.put((self._switch_install_node_task, [node_name, node_status, node_install_path, repo_url, target_ref], {}))
        self.root.after(0, self._update_ui_state) # Update UI state immediately

    # REQUIREMENT 5: Queue All Nodes Update Task
    def _queue_all_nodes_update(self):
        """Queues the task to update all installed nodes."""
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中，无法更新全部节点。", "warn"); return

        # Validate paths before proceeding
        if not self._validate_paths_for_execution(check_comfyui=True, check_git=True, show_error=True):
             self.log_to_gui("Update", "无法更新全部节点: 路径配置无效。", "error")
             return
        # Ensure nodes directory exists
        comfyui_nodes_dir = self.comfyui_nodes_dir
        if not comfyui_nodes_dir or not os.path.isdir(comfyui_nodes_dir):
             self.log_to_gui("Update", f"无法更新全部节点: ComfyUI custom_nodes 目录未找到或无效 ({comfyui_nodes_dir})。", "error")
             messagebox.showerror("目录错误 / Directory Error", f"ComfyUI custom_nodes 目录未找到或无效:\n{comfyui_nodes_dir}\n请检查设置中的 ComfyUI 安装目录。", parent=self.root)
             return

        # Filter for only installed git nodes that have a remote URL
        nodes_to_update = [
            node for node in self.local_nodes_only
            if node.get("is_git") and node.get("repo_url") and "无法获取远程 URL" not in node.get("repo_url")
        ]

        if not nodes_to_update:
             self.log_to_gui("Update", "没有找到可更新的已安装 Git 节点。", "info")
             messagebox.showinfo("无节点可更新 / No Nodes to Update", "没有找到可更新的已安装 Git 节点。", parent=self.root)
             return

        confirm = messagebox.askyesno("确认更新全部 / Confirm Update All", f"确定要尝试更新以下 {len(nodes_to_update)} 个已安装节点吗？\n此操作将对每个节点目录执行 Git pull 等操作。\n\n警告：更新可能需要重新安装依赖，且可能丢失本地修改！\n确认前请确保 ComfyUI 已停止运行。", parent=self.root)
        if not confirm: return

        self.log_to_gui("Launcher", f"将更新全部节点任务添加到队列 (共 {len(nodes_to_update)} 个)...", "info")
        # Queue the update all task, passing the list of nodes to process
        self.update_task_queue.put((self._update_all_nodes_task, [nodes_to_update], {}))
        self.root.after(0, self._update_ui_state) # Update UI state immediately


    # --- Initial Data Loading Task ---
    # REQUIREMENT 1: Function to run initial data loading in background
    def start_initial_data_load(self):
         """Starts the initial data loading tasks (main body versions, nodes) in a background thread."""
         if self._is_update_task_running():
              print("[Launcher INFO] Initial data load skipped, an update task is already running.")
              return

         self.log_to_gui("Launcher", "开始加载更新管理数据...", "info")
         self.update_task_queue.put((self._run_initial_background_tasks, [], {}))
         self.root.after(0, self._update_ui_state) # Update UI to show busy state


    def _run_initial_background_tasks(self):
         """Executes the initial data loading tasks."""
         self.log_to_gui("Launcher", "执行后台数据加载 (本体版本和节点列表)...", "info")
         # Ensure Git path is valid before attempting Git operations
         if not self._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=False):
             self.log_to_gui("Launcher", "Git 路径无效，跳过本体版本和节点列表加载。", "error")
             # Still attempt node list refresh to at least show local non-git nodes
             # self.root.after(0, self.refresh_node_list) # Refresh node list (will only show non-git)
             # But the main_body_versions won't be refreshed accurately.
             self.root.after(0, self._update_ui_state) # Update UI state after failed validation attempt
             return


         # Refresh main body versions first
         self.refresh_main_body_versions() # This is now running in the worker thread

         # Then refresh node list
         self.refresh_node_list() # This is also running in the worker thread

         self.log_to_gui("Launcher", "后台数据加载完成。", "info")
         self.root.after(0, self._update_ui_state) # Update UI state when done


    # REQUIREMENT 2: Accurate Main Body Versions (Modified to run in task queue)
    def refresh_main_body_versions(self):
        """Fetches and displays ComfyUI main body versions using Git. Runs in worker thread."""
        # Check for stop event
        if self.stop_event.is_set():
             self.log_to_gui("Update", "本体版本刷新任务已取消。", "warn"); return

        main_repo_url = self.main_repo_url_var.get()
        comfyui_dir = self.comfyui_dir_var.get()

        # Validation is already done in _queue_main_body_refresh
        # if not self._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=False): ... return
        # if not comfyui_dir or not os.path.isdir(comfyui_dir) or not os.path.isdir(os.path.join(comfyui_dir, ".git")): ... return
        # if not main_repo_url: ... return

        self.log_to_gui("Update", f"尝试从 {main_repo_url} 刷新本体版本列表... / Attempting to refresh main body version list from {main_repo_url}...", "info")
        # Clear existing list in the GUI thread
        self.root.after(0, lambda: [self.main_body_tree.delete(item) for item in self.main_body_tree.get_children()])


        # --- Get Current Local Version ---
        stdout, stderr, returncode = self._run_git_command(["describe", "--all", "--long", "--always"], cwd=comfyui_dir, timeout=10)
        if returncode == 0 and stdout:
             local_version_info = stdout.strip()
             self.root.after(0, lambda: self.current_main_body_version_var.set(f"本地: {local_version_info}"))
        else:
             # Fallback to short commit hash if describe fails
             stdout, stderr, returncode = self._run_git_command(["rev-parse", "HEAD"], cwd=comfyui_dir, timeout=10)
             if returncode == 0 and stdout:
                 self.root.after(0, lambda: self.current_main_body_version_var.set(f"本地 Commit: {stdout.strip()[:8]}"))
             else:
                 self.root.after(0, lambda: self.current_main_body_version_var.set("读取本地版本失败"))
                 self.log_to_gui("Update", f"无法获取本地本体版本信息: {stderr if stderr else '未知错误'}", "warn")

        # Check for stop event after getting local version
        if self.stop_event.is_set():
             self.log_to_gui("Update", "本体版本刷新任务已取消。", "warn"); return

        # --- Fetch Remote Versions ---
        # Fetch latest info first
        self.log_to_gui("Update", "执行 Git fetch origin 获取远程信息...", "info")
        stdout, stderr, returncode = self._run_git_command(["fetch", "origin"], cwd=comfyui_dir, timeout=180) # Increased timeout
        if returncode != 0:
             self.log_to_gui("Update", f"Git fetch 失败: {stderr if stderr else '未知错误'}", "error")
             self.log_to_gui("Update", "无法获取远程本体版本列表。", "error")
             # self.root.after(0, self._update_ui_state) # Update state via finally
             return
        self.log_to_gui("Update", "Git fetch 完成。", "info")

        # Check for stop event after fetch
        if self.stop_event.is_set():
             self.log_to_gui("Update", "本体版本刷新任务已取消。", "warn"); return


        # Get list of remote branches with commit info
        # Format: '%(refname:short) %(objectname) %(committerdate:iso) %(contents:subject)'
        branches_output, branch_err, branch_rc = self._run_git_command(
             ["for-each-ref", "refs/remotes/origin/", "--sort=-committerdate", "--format=%(refname:short) %(objectname) %(committerdate:iso) %(contents:subject)"],
             cwd=comfyui_dir, timeout=60
        )
        # Get list of tags with commit info
        # Format: '%(refname:short) %(objectname) %(taggerdate:iso) %(contents:subject)'
        tags_output, tag_err, tag_rc = self._run_git_command(
             ["for-each-ref", "refs/tags/", "--sort=-taggerdate", "--format=%(refname:short) %(objectname) %(taggerdate:iso) %(contents:subject)"],
             cwd=comfyui_dir, timeout=60
        )

        all_versions = []
        # Process branches
        if branch_rc == 0 and branches_output:
             for line in branches_output.splitlines():
                 parts = line.split(' ', 3) # Split into refname, commit_id, date, subject
                 if len(parts) == 4:
                     refname = parts[0].replace("origin/", "") # Remove origin/ prefix
                     commit_id = parts[1]
                     date_iso = parts[2]
                     description = parts[3].strip()
                     # Exclude the default "origin/HEAD -> origin/master" entry
                     if "->" not in refname:
                          all_versions.append({"type": "branch", "name": refname, "commit_id": commit_id, "date_iso": date_iso, "description": description})
         # Process tags
        if tag_rc == 0 and tags_output:
             for line in tags_output.splitlines():
                 parts = line.split(' ', 3) # Split into refname, commit_id, date, subject
                 if len(parts) == 4:
                     refname = parts[0] # Tag name includes refs/tags/
                     commit_id = parts[1] # Object name is the commit ID the tag points to
                     date_iso = parts[2]
                     description = parts[3].strip()
                     # Clean up tag name if it includes refs/tags/
                     if refname.startswith("refs/tags/"): refname = refname[len("refs/tags/"):]

                     all_versions.append({"type": "tag", "name": refname, "commit_id": commit_id, "date_iso": date_iso, "description": description})

        # Sort versions, prioritize tags (newer tags first), then newer branches
        # Using date as the primary sort key descending, type 'tag' comes before 'branch' for same date
        all_versions.sort(key=lambda x: (x['date_iso'], x['type'] != 'tag'), reverse=True)


        self.remote_main_body_versions = all_versions # Store for node version lookup

        if not all_versions:
             self.log_to_gui("Update", "未从远程仓库获取到版本信息。", "warn")
             self.root.after(0, lambda: self.main_body_tree.insert("", tk.END, values=("无可用版本", "", "", "无法获取远程版本信息")))
        else:
             for ver_data in all_versions:
                 # Check for stop event during insertion
                 if self.stop_event.is_set():
                      self.log_to_gui("Update", "本体版本列表填充任务已取消。", "warn"); break # Stop inserting

                 version_display = f"{ver_data['type']}@{ver_data['name']}" # e.g., tag@v1.2.3, branch@main
                 commit_display = ver_data["commit_id"][:8]
                 # Format date to YYYY-MM-DD, handle potential parsing errors
                 try:
                      date_obj = datetime.fromisoformat(ver_data['date_iso'].split(' ')[0]) # Only take date part before time/timezone
                      date_display = date_obj.strftime('%Y-%m-%d')
                 except ValueError:
                      date_display = "无效日期"
                 description_display = ver_data["description"]

                 # Insert into Treeview in the GUI thread
                 self.root.after(0, lambda v=(version_display, commit_display, date_display, description_display): self.main_body_tree.insert("", tk.END, values=v))

        self.log_to_gui("Update", f"本体版本列表刷新完成 (共 {len(all_versions)} 条)。/ Main body version list refreshed ({len(all_versions)} items).", "info")
        # UI state update is handled by the worker thread's finally block

    # REQUIREMENT 3: Activate Main Body Version (Modified to run in task queue)
    def activate_main_body_version(self):
        """Activates the selected ComfyUI main body version. Queued for worker thread."""
        # Validation and queueing are done in _queue_main_body_activation
        pass # The actual logic is now in _queue_main_body_activation


    def _activate_main_body_version_task(self, comfyui_dir, target_commit_id):
        """Task to execute git commands for activating main body version. Runs in worker thread."""
        # Check for stop event
        if self.stop_event.is_set():
             self.log_to_gui("Update", "本体版本激活任务已取消。", "warn"); return

        self.log_to_gui("Update", f"正在激活本体版本 (提交ID: {target_commit_id[:8]})... / Activating main body version (Commit ID: {target_commit_id[:8]})...", "info")

        try:
            # 1. Ensure tracking remote is correct (Optional but good practice)
            # Check current origin URL
            stdout, stderr, returncode = self._run_git_command(["remote", "get-url", "origin"], cwd=comfyui_dir, timeout=10)
            current_origin_url = stdout.strip() if returncode == 0 else ""
            configured_origin_url = self.main_repo_url_var.get().strip()

            if returncode != 0 or current_origin_url != configured_origin_url:
                 if returncode != 0: self.log_to_gui("Update", f"无法获取当前远程 origin URL: {stderr if stderr else '未知错误'}", "warn")
                 self.log_to_gui("Update", f"远程 origin URL 不匹配或无法获取 ({current_origin_url} vs {configured_origin_url})，尝试设置...", "warn")
                 # Check if origin remote exists first
                 stdout, stderr, returncode = self._run_git_command(["remote", "get-url", "origin"], cwd=comfyui_dir, timeout=5)
                 if returncode == 0: # origin exists, just set URL
                      stdout, stderr, returncode = self._run_git_command(["remote", "set-url", "origin", configured_origin_url], cwd=comfyui_dir, timeout=10)
                 else: # origin does not exist, add it
                      stdout, stderr, returncode = self._run_git_command(["remote", "add", "origin", configured_origin_url], cwd=comfyui_dir, timeout=10)

                 if returncode != 0:
                      self.log_to_gui("Update", f"设置远程 URL 失败: {stderr if stderr else '未知错误'}", "error")
                      # This is a critical failure for fetching/updating
                      raise Exception("设置远程 URL 失败")
                 self.log_to_gui("Update", "远程 origin URL 已更新/添加。", "info")

            # Check for stop event
            if self.stop_event.is_set(): raise threading.ThreadExit # Use a custom exception or flag check

            # 2. Fetch latest changes
            self.log_to_gui("Update", "执行 Git fetch origin...", "info")
            stdout, stderr, returncode = self._run_git_command(["fetch", "origin"], cwd=comfyui_dir, timeout=180) # Increased timeout
            if returncode != 0:
                 self.log_to_gui("Update", f"Git fetch 失败: {stderr if stderr else '未知错误'}", "error")
                 raise Exception("Git fetch 失败")
            self.log_to_gui("Update", "Git fetch 完成。", "info")

            # Check for stop event
            if self.stop_event.is_set(): raise threading.ThreadExit

            # 3. Reset local changes and checkout target commit
            self.log_to_gui("Update", f"执行 Git reset --hard {target_commit_id[:8]}...", "info")
            stdout, stderr, returncode = self._run_git_command(["reset", "--hard", target_commit_id], cwd=comfyui_dir, timeout=60)
            if returncode != 0:
                 self.log_to_gui("Update", f"Git reset --hard 失败: {stderr if stderr else '未知错误'}", "error")
                 raise Exception("Git reset --hard 失败")
            self.log_to_gui("Update", "Git reset --hard 完成。", "info")

            # Check for stop event
            if self.stop_event.is_set(): raise threading.ThreadExit

            # 4. Clean untracked files (Optional, but often needed after hard reset)
            # self.log_to_gui("Update", "执行 Git clean -fdx...", "info")
            # stdout, stderr, returncode = self._run_git_command(["clean", "-fdx"], cwd=comfyui_dir)
            # if returncode != 0:
            #      self.log_to_gui("Update", f"Git clean -fdx 失败: {stderr if stderr else '未知错误'}", "warn") # Warn, don't necessarily fail activation
            # else:
            #      self.log_to_gui("Update", "Git clean -fdx 完成。", "info")

            # Check for stop event
            if self.stop_event.is_set(): raise threading.ThreadExit

            # 5. Update submodules
            # Check if .gitmodules exists first
            if os.path.exists(os.path.join(comfyui_dir, ".gitmodules")):
                 self.log_to_gui("Update", "执行 Git submodule update...", "info")
                 stdout, stderr, returncode = self._run_git_command(["submodule", "update", "--init", "--recursive"], cwd=comfyui_dir, timeout=180) # Increased timeout
                 if returncode != 0:
                      self.log_to_gui("Update", f"Git submodule update 失败: {stderr if stderr else '未知错误'}", "error")
                      # Continue but log error - submodule failure might not be fatal for *some* versions
                      # raise Exception("Git submodule update 失败") # Decide if this should be a hard fail
                 else:
                      self.log_to_gui("Update", "Git submodule update 完成。", "info")
            else:
                 self.log_to_gui("Update", "未找到 .gitmodules 文件，跳过 submodule update。", "info")

            # Check for stop event
            if self.stop_event.is_set(): raise threading.ThreadExit

            # 6. Re-install Python dependencies (Check requirements.txt change? Or always run?)
            python_exe = self.python_exe_var.get()
            requirements_path = os.path.join(comfyui_dir, "requirements.txt")
            if python_exe and os.path.isfile(python_exe) and os.path.isfile(requirements_path):
                 self.log_to_gui("Update", "执行 pip 安装依赖...", "info")
                 # Using --upgrade to ensure dependencies match the new requirements.txt
                 pip_cmd = [
                     python_exe, "-m", "pip", "install", "-r", requirements_path, "--upgrade",
                 ]
                 # Add extra index URLs if they are commonly needed (like PyTorch)
                 # Note: This is specific to PyTorch/CUDA. Might need to be configurable.
                 # Check platform and potentially installed torch/cuda versions
                 # For simplicity, include common URLs, user can edit if needed.
                 pip_cmd.extend(["--extra-index-url", "https://download.pytorch.org/whl/cu118", "--extra-index-url", "https://download.pytorch.org/whl/cu121", "--extra-index-url", "https://download.pytorch.org/whl/rocm5.7"])


                 stdout, stderr, returncode = self._run_git_command( # Using _run_git_command for pip, as it handles logging
                      pip_cmd,
                      cwd=comfyui_dir, timeout=600 # Allow more time for pip install
                 )
                 if returncode != 0:
                      self.log_to_gui("Update", f"Pip 安装依赖失败: {stderr if stderr else '未知错误'}", "error")
                      self.root.after(0, lambda: messagebox.showwarning("依赖安装失败 / Dependency Install Failed", "Python 依赖安装失败，新版本可能无法正常工作。\n请查看后台日志获取详情。", parent=self.root))
                 else:
                      self.log_to_gui("Update", "Pip 安装依赖完成。", "info")
            else:
                 self.log_to_gui("Update", "Python 或 requirements.txt 文件无效，跳过依赖安装。", "info")


            # Success message
            self.log_to_gui("Update", f"本体版本激活流程完成 (提交ID: {target_commit_id[:8]})。", "info")
            self.root.after(0, lambda: messagebox.showinfo("激活完成 / Activation Complete", f"本体版本已激活到提交: {target_commit_id[:8]}", parent=self.root))

        except threading.ThreadExit:
             self.log_to_gui("Update", "本体版本激活任务已取消。", "warn")
        except Exception as e:
            error_msg = f"本体版本激活流程失败: {e}"
            self.log_to_gui("Update", error_msg, "error")
            self.root.after(0, lambda: messagebox.showerror("激活失败 / Activation Failed", error_msg, parent=self.root))
        finally:
            # Always refresh list and update UI state after task finishes
            self.root.after(0, self.refresh_main_body_versions) # Refresh to show activated version
            # UI state update is handled by the worker thread's finally block


    # REQUIREMENT 4: Nodes List Scanning, Git Info, and "本地ID"/"仓库信息" Formatting (Modified to run in task queue)
    def refresh_node_list(self):
        """Fetches and displays custom node list (local scan + online config), applying filter. Runs in worker thread."""
        # Check for stop event
        if self.stop_event.is_set():
             self.log_to_gui("Update", "节点列表刷新任务已取消。", "warn"); return

        node_config_url = self.node_config_url_var.get()
        comfyui_nodes_dir = self.comfyui_nodes_dir
        # Get search term from UI variable in GUI thread
        search_term = self.root.after(0, lambda: self.nodes_search_entry.get().strip().lower()) # Get value via after
        # Need to wait for the result of after call if used outside GUI thread.
        # A better approach is to get the value before queuing or pass it as arg.
        search_term_value = self.nodes_search_entry.get().strip().lower() # Get directly as this runs in worker

        git_path_ok = self._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=False)

        # --- Scan Local custom_nodes directory ---
        self.local_nodes_only = [] # Reset the list of local nodes
        if comfyui_nodes_dir and os.path.isdir(comfyui_nodes_dir):
             self.log_to_gui("Update", f"扫描本地 custom_nodes 目录: {comfyui_nodes_dir}...", "info")
             # Check for stop event before listing directory
             if self.stop_event.is_set(): raise threading.ThreadExit

             try:
                  for item_name in os.listdir(comfyui_nodes_dir):
                       # Check for stop event during directory listing
                       if self.stop_event.is_set(): raise threading.ThreadExit

                       item_path = os.path.join(comfyui_nodes_dir, item_name)
                       if os.path.isdir(item_path):
                            node_info = {"name": item_name, "status": "已安装"}
                            # Try to get Git info if Git executable is available and it's a git repo
                            if git_path_ok and os.path.isdir(os.path.join(item_path, ".git")):
                                 node_info["is_git"] = True
                                 # REQUIREMENT 4: Get Local ID (short commit hash)
                                 stdout, stderr, returncode = self._run_git_command(["rev-parse", "--short", "HEAD"], cwd=item_path, timeout=5)
                                 node_info["local_id"] = stdout.strip() if returncode == 0 and stdout else "无法获取本地ID"
                                 if returncode != 0:
                                      self.log_to_gui("Update", f"无法获取节点 '{item_name}' 的本地Commit ID: {stderr if stderr else '未知错误'}", "warn")


                                 # REQUIREMENT 4: Get Remote Info ("仓库信息": Remote ID + Date or branch name)
                                 repo_info_display = "无远程跟踪分支" # Default if no upstream
                                 remote_branch_name = None
                                 remote_commit_id_short = "N/A"
                                 remote_commit_date = "N/A"
                                 repo_url_str = "无法获取远程 URL"

                                 # Try to get the upstream tracking branch
                                 stdout, stderr, returncode = self._run_git_command(["rev-parse", "--abbrev-ref", "@{u}"], cwd=item_path, timeout=5)
                                 if returncode == 0 and stdout:
                                      upstream_ref = stdout.strip() # e.g., origin/main
                                      remote_branch_name = upstream_ref.replace("origin/", "") # Get just the branch name

                                      # Get remote branch HEAD commit ID and Date
                                      log_cmd = ["log", "-1", "--format=%H %ci", upstream_ref]
                                      stdout_log, stderr_log, returncode_log = self._run_git_command(log_cmd, cwd=item_path, timeout=10)

                                      if returncode_log == 0 and stdout_log:
                                           log_parts = stdout_log.strip().split(' ', 1)
                                           if len(log_parts) == 2:
                                                full_commit_id = log_parts[0]
                                                date_iso = log_parts[1]
                                                remote_commit_id_short = full_commit_id[:8]
                                                try:
                                                     date_obj = datetime.fromisoformat(date_iso.split(' ')[0]) # Get date part
                                                     remote_commit_date = date_obj.strftime('%Y-%m-%d')
                                                except ValueError:
                                                     self.log_to_gui("Update", f"节点 '{item_name}' 远程分支 '{remote_branch_name}' 日期解析失败: {date_iso}", "warn")
                                                     remote_commit_date = "无效日期"

                                                # Format: commit_id (date)
                                                repo_info_display = f"{remote_commit_id_short} ({remote_commit_date})"
                                           else:
                                                self.log_to_gui("Update", f"无法解析节点 '{item_name}' 远程分支 '{remote_branch_name}' 的日志格式: {stdout_log.strip()}", "warn")
                                                repo_info_display = f"{remote_branch_name} (日志解析失败)"

                                      else:
                                           self.log_to_gui("Update", f"无法获取节点 '{item_name}' 远程分支 '{remote_branch_name}' 的最新提交信息: {stderr_log if stderr_log else '未知错误'}", "warn")
                                           repo_info_display = f"{remote_branch_name} (信息获取失败)"

                                 elif "no upstream configured" not in stderr and "no upstream branch" not in stderr and returncode != 0:
                                      self.log_to_gui("Update", f"无法获取节点 '{item_name}' 的远程跟踪分支信息: {stderr if stderr else '未知错误'}", "warn")
                                      repo_info_display = "信息获取失败"

                                 # Get Remote URL
                                 stdout, stderr, returncode = self._run_git_command(["remote", "get-url", "origin"], cwd=item_path, timeout=5)
                                 repo_url_str = stdout.strip() if returncode == 0 and stdout else "无法获取远程 URL"
                                 if returncode != 0 and "no such remote" not in stderr.lower():
                                     self.log_to_gui("Update", f"无法获取节点 '{item_name}' 的远程URL: {stderr if stderr else '未知错误'}", "warn")


                                 node_info["repo_info"] = repo_info_display
                                 node_info["repo_url"] = repo_url_str
                                 # Also store remote commit ID and date separately for Update All logic
                                 node_info["remote_commit_id"] = full_commit_id if 'full_commit_id' in locals() else None
                                 node_info["remote_commit_date"] = remote_commit_date


                            else:
                                 node_info["is_git"] = False
                                 node_info["local_id"] = "N/A" # Non-git nodes have no local ID
                                 node_info["repo_info"] = "N/A" # Non-git nodes have no remote info
                                 node_info["repo_url"] = "本地安装，无Git信息"

                            self.local_nodes_only.append(node_info)
                  self.log_to_gui("Update", f"本地 custom_nodes 目录扫描完成，找到 {len(self.local_nodes_only)} 个节点。", "info")

             except threading.ThreadExit:
                  self.log_to_gui("Update", "节点列表扫描任务已取消。", "warn"); return
             except Exception as e:
                  self.log_to_gui("Update", f"扫描本地 custom_nodes 目录时出错: {e}", "error")


        else:
             self.log_to_gui("Update", f"ComfyUI custom_nodes 目录未找到或无效 ({comfyui_nodes_dir})，跳过本地节点扫描。", "warn")

        # Check for stop event
        if self.stop_event.is_set():
             self.log_to_gui("Update", "节点列表刷新任务已取消。", "warn"); return

        # --- Simulate Fetching Online Config Data ---
        # In a real implementation, use requests.get(node_config_url) and parse JSON
        # This data is mainly used for the combined list when searching
        # TODO: Implement actual fetching of online node config
        simulated_online_nodes_config = self._fetch_online_node_config() # Call helper to get the config

        # Check for stop event
        if self.stop_event.is_set():
             self.log_to_gui("Update", "节点列表刷新任务已取消。", "warn"); return


        # --- Combine local and online data for searching ---
        # Use a dictionary for quick lookup of local nodes by name (case-insensitive)
        local_node_dict_lower = {node['name'].lower(): node for node in self.local_nodes_only}

        self.all_known_nodes = list(self.local_nodes_only) # Start the combined list with local nodes

        for online_node in simulated_online_nodes_config:
             node_name = online_node.get('name', '未知节点')
             node_name_lower = node_name.lower()
             repo_url = online_node.get('repo', 'N/A')
             version = online_node.get('branch', 'main') # Use branch as default version placeholder
             description = online_node.get('description', '无描述')


             if node_name_lower not in local_node_dict_lower:
                  # Node is in online config but not found locally, add it as "未安装"
                  # For "仓库信息", just show the recommended branch/version + (未安装)
                  online_repo_info_display = f"{version} (未安装)"

                  self.all_known_nodes.append({
                      "name": node_name,
                      "status": "未安装",
                      "local_id": "N/A", # Uninstalled nodes have no local ID
                      "repo_info": online_repo_info_display, # Display branch/version from online config + status
                      "repo_url": repo_url,
                      "is_git": True # Assume online nodes are git repos for filtering logic
                  })
             # If node_name_lower is in local_node_dict_lower, it's already added from local scan.
             # The local scan provides the authoritative info for installed nodes.

        # Sort the combined list by name for consistent searching
        self.all_known_nodes.sort(key=lambda x: x['name'].lower())

        # Check for stop event
        if self.stop_event.is_set():
             self.log_to_gui("Update", "节点列表刷新任务已取消。", "warn"); return

        # --- Apply Filtering Logic and Populate Treeview ---
        filtered_nodes = []
        # Get the search term again in case it changed while fetching online data
        search_term_after_fetch = self.nodes_search_entry.get().strip().lower()

        # Clear existing list in the GUI thread before populating
        self.root.after(0, lambda: [self.nodes_tree.delete(item) for item in self.nodes_tree.get_children()])


        if search_term_after_fetch == "":
            # If search is empty, show ONLY nodes from the local scan list (all local nodes)
            filtered_nodes = list(self.local_nodes_only)
            # Sort the default local list by name too
            filtered_nodes.sort(key=lambda x: x['name'].lower())
        else:
            # If search has text, filter the combined list (all_known_nodes) by name match
            filtered_nodes = [node for node in self.all_known_nodes if search_term_after_fetch in node.get('name', '').lower()]
            # Keep search results sorted by name
            filtered_nodes.sort(key=lambda x: x.get('name', '').lower())


        # Populate the Treeview with filtered data (using 5 columns)
        for node_data in filtered_nodes:
             # Check for stop event during insertion
             if self.stop_event.is_set():
                  self.log_to_gui("Update", "节点列表填充任务已取消。", "warn"); break # Stop inserting

             # Add tag for status visual hint
             tags = ('installed',) if node_data.get('status') == '已安装' else ('not_installed',)
             # Insert into Treeview in the GUI thread
             self.root.after(0, lambda v=(
                  node_data.get("name", "N/A"),
                  node_data.get("status", "未知"),
                  node_data.get("local_id", "N/A"),      # Data for the "本地ID" column
                  node_data.get("repo_info", "N/A"),    # Data for the "仓库信息" column
                  node_data.get("repo_url", "N/A")
             ), t=tags: self.nodes_tree.insert("", tk.END, values=v, tags=t))


        self.log_to_gui("Update", f"节点列表刷新完成。已显示 {len(filtered_nodes)} 个节点。", "info")
        # UI state update is handled by the worker thread's finally block

    # Helper to fetch online node config (Placeholder)
    def _fetch_online_node_config(self):
         """Fetches the online custom node list config."""
         node_config_url = self.node_config_url_var.get()
         if not node_config_url:
              self.log_to_gui("Update", "节点配置地址未设置，跳过在线配置获取。", "warn")
              return []
         # In a real implementation, use requests.get(node_config_url)
         try:
              self.log_to_gui("Update", f"尝试从 {node_config_url} 获取节点配置...", "info")
              # response = requests.get(node_config_url, timeout=15) # Add timeout
              # response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
              # config_data = response.json()
              # print(f"[Launcher INFO] Got online node config: {config_data}") # Log the data received

              # --- Simulated Data for testing ---
              simulated_online_nodes_config = [
                  {"name": "ComfyUI-Manager", "repo": "https://github.com/ltdrdata/ComfyUI-Manager.git", "branch": "main", "description": "ComfyUI Manager"},
                  {"name": "ComfyUI-AnimateDiff-Evolved", "repo": "https://github.com/Kosinkadink/ComfyUI-AnimateDiff-Evolved", "branch": "master", "description": "Animation nodes"},
                  {"name": "ComfyUI-Impact-Pack", "repo": "https://github.com/ltdrdata/ComfyUI-Impact-Pack", "branch": "main", "description": "Impact Pack nodes"},
                  {"name": "SaltAux", "repo": "https://github.com/Saltlaboratory/SaltAux", "branch": "main", "description": "SaltAux nodes"},
                  {"name": "WASasquatch_Suite", "repo": "https://github.com/WASasquatch/WASasquatch_Suite", "branch": "main", "description": "WASasquatch nodes"},
                  {"name": "ComfyUI-Custom-Scripts", "repo": "https://github.com/pythongosssss/ComfyUI-Custom-Scripts", "branch": "main", "description": "Custom Scripts nodes"},
                  {"name": "Efficient-Nodes", "repo": "https://github.com/jokergoo/ComfyUI-Jokergoo-Nodes", "branch": "main", "description": "Efficient nodes"},
                  {"name": "Aigodlike-Nodes", "repo": "https://gitee.com/AIGODLIKE/Aigodlike-ComfyUI-Nodes.git", "branch": "dev", "description": "Aigodlike nodes"},
                  {"name": "Fooocus-Nodes-Another", "repo": "https://github.com/another/Fooocus-Nodes", "branch": "main", "description": "Another Fooocus nodes"},
                  {"name": "Example-Node-1", "repo": "https://github.com/example/Example-Node-1.git", "branch": "main", "description": "Example node 1"},
                  {"name": "Example-Node-2", "repo": "https://github.com/example/Example-Node-2.git", "branch": "main", "description": "Example node 2"},
                  {"name": "Example-Node-3", "repo": "https://github.com/example/Example-Node-3.git", "branch": "main", "description": "Example node 3"},
              ]
              # Simulate adding more online nodes for testing search and scroll
              for i in range(20):
                   simulated_online_nodes_config.append({
                       "name": f"Simulated-Node-{i+1}",
                       "repo": f"https://github.com/simulated/Node-{i+1}.git",
                       "branch": "main",
                       "description": f"Simulated node number {i+1}"
                   })
              self.log_to_gui("Update", f"已获取模拟在线节点配置 (共 {len(simulated_online_nodes_config)} 条)。", "info")
              return simulated_online_nodes_config # Return simulated data
              # --- End Simulated Data ---


         except requests.exceptions.RequestException as e:
              self.log_to_gui("Update", f"获取在线节点配置失败: {e}", "error")
              # Decide if this should show an error box or just log
              # self.root.after(0, lambda msg=str(e): messagebox.showerror("获取节点配置失败", f"无法从 {node_config_url} 获取在线节点配置:\n{msg}", parent=self.root))
              return [] # Return empty list on failure
         except Exception as e:
              self.log_to_gui("Update", f"处理在线节点配置时发生意外错误: {e}", "error")
              return []

    # REQUIREMENT 5: Implement Update All Nodes Task
    def _update_all_nodes_task(self, nodes_to_process):
        """Task to iterate and update all specified installed nodes. Runs in worker thread."""
        self.log_to_gui("Update", f"开始更新全部节点 ({len(nodes_to_process)} 个)...", "info")

        updated_count = 0
        failed_nodes = []

        for index, node_info in enumerate(nodes_to_process):
             # Check for stop event before processing each node
             if self.stop_event.is_set():
                  self.log_to_gui("Update", f"更新全部节点任务已取消。", "warn"); break # Stop processing

             node_name = node_info.get("name", "未知节点")
             node_install_path = os.path.normpath(os.path.join(self.comfyui_nodes_dir, node_name)) # Derive path from name
             repo_url = node_info.get("repo_url", "N/A")
             local_id = node_info.get("local_id", "N/A")
             remote_branch = node_info.get("repo_info", "N/A").split(' ')[0].strip() # Get branch name from repo_info string


             self.log_to_gui("Update", f"[{index+1}/{len(nodes_to_process)}] 正在处理节点 '{node_name}'...", "info")

             if not os.path.isdir(node_install_path) or not os.path.exists(os.path.join(node_install_path, ".git")):
                  self.log_to_gui("Update", f"节点目录 '{node_name}' 不是有效的 Git 仓库 ({node_install_path})，跳过更新。", "warn")
                  failed_nodes.append(f"{node_name} (非Git仓库)")
                  continue

             # Ensure tracking remote is correct (Optional check)
             stdout, stderr, returncode = self._run_git_command(["remote", "get-url", "origin"], cwd=node_install_path, timeout=10)
             current_origin_url = stdout.strip() if returncode == 0 else ""
             if returncode != 0 or current_origin_url != repo_url:
                  if returncode != 0: self.log_to_gui("Update", f"无法获取节点 '{node_name}' 的当前远程 origin URL: {stderr if stderr else '未知错误'}", "warn")
                  self.log_to_gui("Update", f"节点 '{node_name}' 的远程 origin URL 不匹配或无法获取 ({current_origin_url} vs {repo_url})，尝试设置...", "warn")
                  stdout, stderr, returncode = self._run_git_command(["remote", "set-url", "origin", repo_url], cwd=node_install_path, timeout=10)
                  if returncode != 0:
                      self.log_to_gui("Update", f"设置节点 '{node_name}' 的远程 URL 失败: {stderr if stderr else '未知错误'}", "error")
                      # Continue but log error - maybe pull will still work if remote exists but URL changed?
                  else:
                       self.log_to_gui("Update", f"节点 '{node_name}' 的远程 origin URL 已更新。", "info")

             # Check for stop event
             if self.stop_event.is_set():
                  self.log_to_gui("Update", f"更新全部节点任务已取消。", "warn"); break

             # Check if there are local changes that would be overwritten by pull/reset
             stdout, stderr, returncode = self._run_git_command(["status", "--porcelain"], cwd=node_install_path, timeout=10)
             if returncode == 0 and stdout.strip():
                  self.log_to_gui("Update", f"节点 '{node_name}' 存在本地修改，跳过更新。", "warn")
                  failed_nodes.append(f"{node_name} (存在本地修改)")
                  continue

             # Check for stop event
             if self.stop_event.is_set():
                  self.log_to_gui("Update", f"更新全部节点任务已取消。", "warn"); break

             # Fetch latest from origin
             self.log_to_gui("Update", f"[{index+1}/{len(nodes_to_process)}] 执行 Git fetch origin for '{node_name}'...", "info")
             stdout, stderr, returncode = self._run_git_command(["fetch", "origin"], cwd=node_install_path, timeout=60)
             if returncode != 0:
                  self.log_to_gui("Update", f"Git fetch 失败 for '{node_name}': {stderr if stderr else '未知错误'}", "error")
                  failed_nodes.append(f"{node_name} (Fetch失败)")
                  continue
             self.log_to_gui("Update", f"Git fetch 完成 for '{node_name}'.", "info")

             # Check for stop event
             if self.stop_event.is_set():
                  self.log_to_gui("Update", f"更新全部节点任务已取消。", "warn"); break

             # Get local HEAD commit ID
             stdout_local, stderr_local, returncode_local = self._run_git_command(["rev-parse", "HEAD"], cwd=node_install_path, timeout=5)
             local_commit_id = stdout_local.strip() if returncode_local == 0 and stdout_local else None

             # Get remote tracking branch HEAD commit ID
             stdout_remote, stderr_remote, returncode_remote = self._run_git_command(["rev-parse", f"origin/{remote_branch}"], cwd=node_install_path, timeout=5)
             remote_commit_id = stdout_remote.strip() if returncode_remote == 0 and stdout_remote else None

             if local_commit_id and remote_commit_id and local_commit_id != remote_commit_id:
                  self.log_to_gui("Update", f"节点 '{node_name}' 有新版本可用 ({local_id[:8]} -> {remote_commit_id[:8]})。", "info")
                  # Perform git pull
                  self.log_to_gui("Update", f"[{index+1}/{len(nodes_to_process)}] 执行 Git pull origin {remote_branch} for '{node_name}'...", "info")
                  stdout, stderr, returncode = self._run_git_command(["pull", "origin", remote_branch], cwd=node_install_path, timeout=180) # Allow more time
                  if returncode != 0:
                       self.log_to_gui("Update", f"Git pull 失败 for '{node_name}': {stderr if stderr else '未知错误'}", "error")
                       failed_nodes.append(f"{node_name} (Pull失败)")
                       continue
                  self.log_to_gui("Update", f"Git pull 完成 for '{node_name}'.", "info")

                  # Check for stop event
                  if self.stop_event.is_set():
                       self.log_to_gui("Update", f"更新全部节点任务已取消。", "warn"); break

                  # Update submodules after pull
                  if os.path.exists(os.path.join(node_install_path, ".gitmodules")):
                      self.log_to_gui("Update", f"[{index+1}/{len(nodes_to_process)}] 执行 Git submodule update for '{node_name}'...", "info")
                      stdout, stderr, returncode = self._run_git_command(["submodule", "update", "--init", "--recursive"], cwd=node_install_path, timeout=180)
                      if returncode != 0:
                           self.log_to_gui("Update", f"Git submodule update 失败 for '{node_name}': {stderr if stderr else '未知错误'}", "warn")
                      else:
                           self.log_to_gui("Update", f"Git submodule update 完成 for '{node_name}'.", "info")
                  else:
                       self.log_to_gui("Update", f"'{node_name}' 目录未找到 .gitmodules 文件，跳过 submodule update。", "info")

                  # Check for stop event
                  if self.stop_event.is_set():
                       self.log_to_gui("Update", f"更新全部节点任务已取消。", "warn"); break

                  # Re-install Node-specific Python dependencies (if requirements.txt exists)
                  python_exe = self.python_exe_var.get()
                  requirements_path = os.path.join(node_install_path, "requirements.txt")
                  if python_exe and os.path.isfile(python_exe) and os.path.isfile(requirements_path):
                       self.log_to_gui("Update", f"[{index+1}/{len(nodes_to_process)}] 执行 pip 安装节点依赖 for '{node_name}'...", "info")
                       pip_cmd = [python_exe, "-m", "pip", "install", "-r", requirements_path, "--upgrade"]
                       pip_cmd.extend(["--extra-index-url", "https://download.pytorch.org/whl/cu118", "--extra-index-url", "https://download.pytorch.org/whl/cu121", "--extra-index-url", "https://download.pytorch.org/whl/rocm5.7"])

                       stdout, stderr, returncode = self._run_git_command(
                            pip_cmd,
                            cwd=node_install_path, timeout=180 # Allow more time
                       )
                       if returncode != 0:
                            self.log_to_gui("Update", f"Pip 安装节点依赖失败 for '{node_name}': {stderr if stderr else '未知错误'}", "error")
                            self.root.after(0, lambda name=node_name: messagebox.showwarning("节点依赖安装失败 / Node Dependency Install Failed", f"节点 '{name}' 的 Python 依赖安装失败，请手动检查。\n请查看后台日志获取详情。", parent=self.root))
                       else:
                            self.log_to_gui("Update", f"Pip 安装节点依赖完成 for '{node_name}'.", "info")
                  else:
                       self.log_to_gui("Update", f"节点 '{node_name}' 未找到 requirements.txt 或 Python 无效，跳过依赖安装。", "info")

                  updated_count += 1
                  self.log_to_gui("Update", f"节点 '{node_name}' 更新成功。", "info")
             elif local_commit_id and remote_commit_id and local_commit_id == remote_commit_id:
                  self.log_to_gui("Update", f"节点 '{node_name}' 已是最新版本。", "info")
             elif not local_commit_id:
                  self.log_to_gui("Update", f"无法获取节点 '{node_name}' 的本地Commit ID，跳过更新检查。", "warn")
                  failed_nodes.append(f"{node_name} (本地ID获取失败)")
             elif not remote_commit_id:
                  self.log_to_gui("Update", f"无法获取节点 '{node_name}' 的远程Commit ID ({remote_branch})，跳过更新检查。", "warn")
                  failed_nodes.append(f"{node_name} (远程信息获取失败)")


        self.log_to_gui("Update", f"更新全部节点流程完成。已更新 {updated_count} 个节点。", "info")
        final_message = f"全部节点更新流程完成。\n成功更新: {updated_count} 个"
        if failed_nodes:
             final_message += f"\n失败/跳过节点 ({len(failed_nodes)} 个):\n" + "\n".join(failed_nodes)
             self.root.after(0, lambda msg=final_message: messagebox.showwarning("更新全部完成 (有失败) / Update All Complete (with Failures)", msg, parent=self.root))
        else:
             self.root.after(0, lambda msg=final_message: messagebox.showinfo("更新全部完成 / Update All Complete", msg, parent=self.root))

        # Always refresh node list after update all attempt finishes
        self.root.after(0, self.refresh_node_list)
        # UI state update is handled by the worker thread's finally block


    def switch_install_node_version(self):
        """Installs or Switches the version of the selected node. Queued for worker thread."""
        # Validation and queueing are done in _queue_node_switch_install
        pass # The actual logic is now in _queue_node_switch_install

    def _switch_install_node_task(self, node_name, node_status, node_install_path, repo_url, target_ref):
        """Task to execute git commands for installing/switching node version. Runs in worker thread."""
        # Check for stop event
        if self.stop_event.is_set():
             self.log_to_gui("Update", f"节点 '{node_name}' 操作任务已取消。", "warn"); return

        action = "安装" if node_status != "已安装" else "切换版本到"
        self.log_to_gui("Update", f"正在对节点 '{node_name}' 执行 '{action}' (目标引用: {target_ref})...", "info")

        try:
            git_exe = self.git_exe_path_var.get()
            comfyui_nodes_dir = self.comfyui_nodes_dir

            if node_status != "已安装":
                 # --- Install (Clone) ---
                 # Ensure the parent directory for cloning exists
                 if not os.path.exists(comfyui_nodes_dir):
                      self.log_to_gui("Update", f"创建节点目录: {comfyui_nodes_dir}", "info")
                      os.makedirs(comfyui_nodes_dir, exist_ok=True) # Real command

                 self.log_to_gui("Update", f"执行 Git clone {repo_url} {node_install_path}...", "info")
                 # Optionally clone a specific branch initially
                 clone_cmd = ["clone"]
                 # Check if target_ref is a branch using ls-remote
                 is_branch = False
                 stdout_check, stderr_check, returncode_check = self._run_git_command(["ls-remote", "--heads", repo_url, target_ref], cwd=comfyui_nodes_dir, timeout=10)
                 if returncode_check == 0 and stdout_check.strip(): is_branch = True
                 elif returncode_check != 0 and "not found" not in stderr_check.lower():
                      self.log_to_gui("Update", f"检查目标引用 '{target_ref}' 是否为远程分支失败: {stderr_check if stderr_check else '未知错误'}", "warn")


                 if is_branch:
                     clone_cmd.extend(["--branch", target_ref]) # Clone specific branch
                 clone_cmd.extend([repo_url, node_install_path])

                 stdout, stderr, returncode = self._run_git_command(clone_cmd, cwd=comfyui_nodes_dir, timeout=300) # Allow more time for clone
                 if returncode != 0:
                      self.log_to_gui("Update", f"Git clone 失败: {stderr if stderr else '未知错误'}", "error")
                      # Attempt to remove the partially created directory
                      if os.path.exists(node_install_path):
                           try:
                                import shutil
                                shutil.rmtree(node_install_path)
                                self.log_to_gui("Update", f"已移除失败的节点目录: {node_install_path}", "info")
                           except Exception as rm_err:
                                self.log_to_gui("Update", f"移除失败的节点目录 '{node_install_path}' 失败: {rm_err}", "error")
                      raise Exception("Git clone 失败")
                 self.log_to_gui("Update", "Git clone 完成。", "info")

                 # After cloning, we are usually already on the target branch if --branch was used.
                 # If cloning a tag/commit, HEAD might be detached. No need to explicitly checkout after clone unless cloning specific commit/tag.
                 # The check below is mostly redundant if --branch was used, but safe.
                 if not is_branch: # If cloned a tag or specific commit
                      self.log_to_gui("Update", f"执行 Git checkout {target_ref}...", "info")
                      stdout, stderr, returncode = self._run_git_command(["checkout", target_ref], cwd=node_install_path, timeout=60)
                      if returncode != 0:
                           self.log_to_gui("Update", f"Git checkout 失败: {stderr if stderr else '未知错误'}", "error")
                           raise Exception(f"Git checkout {target_ref} 失败")
                      self.log_to_gui("Update", f"Git checkout {target_ref} 完成。", "info")


            else: # Already installed, switch version
                 # --- Switch Version (Fetch & Checkout/Pull) ---
                 if not os.path.isdir(node_install_path) or not os.path.exists(os.path.join(node_install_path, ".git")):
                      self.log_to_gui("Update", f"节点目录不是有效的 Git 仓库 ({node_install_path})，无法更新。", "error")
                      raise Exception(f"节点目录不是有效的 Git 仓库: {node_install_path}")

                 # Check for stop event
                 if self.stop_event.is_set(): raise threading.ThreadExit

                 # Ensure tracking remote is correct (Optional check)
                 stdout, stderr, returncode = self._run_git_command(["remote", "get-url", "origin"], cwd=node_install_path, timeout=10)
                 current_origin_url = stdout.strip() if returncode == 0 else ""
                 if returncode != 0 or current_origin_url != repo_url:
                     if returncode != 0: self.log_to_gui("Update", f"无法获取节点 '{node_name}' 的当前远程 origin URL: {stderr if stderr else '未知错误'}", "warn")
                     self.log_to_gui("Update", f"节点 '{node_name}' 的远程 origin URL 不匹配或无法获取 ({current_origin_url} vs {repo_url})，尝试设置...", "warn")
                     stdout, stderr, returncode = self._run_git_command(["remote", "set-url", "origin", repo_url], cwd=node_install_path, timeout=10)
                     if returncode != 0:
                         self.log_to_gui("Update", f"设置节点 '{node_name}' 的远程 URL 失败: {stderr if stderr else '未知错误'}", "error")
                         # Not critical error? Continue but log.
                     else:
                          self.log_to_gui("Update", f"节点 '{node_name}' 的远程 origin URL 已更新。", "info")

                 # Check for stop event
                 if self.stop_event.is_set(): raise threading.ThreadExit

                 # Fetch latest from origin
                 self.log_to_gui("Update", f"执行 Git fetch origin for '{node_name}'...", "info")
                 stdout, stderr, returncode = self._run_git_command(["fetch", "origin"], cwd=node_install_path, timeout=60) # Increased timeout
                 if returncode != 0:
                      self.log_to_gui("Update", f"Git fetch 失败 for '{node_name}': {stderr if stderr else '未知错误'}", "error")
                      raise Exception(f"Git fetch 失败 for '{node_name}'")
                 self.log_to_gui("Update", f"Git fetch 完成 for '{node_name}'.", "info")

                 # Check for stop event
                 if self.stop_event.is_set(): raise threading.ThreadExit

                 # Determine if target_ref is a branch or commit/tag and use appropriate command (checkout/pull)
                 # Try git checkout first, as it works for both branches and tags/commits
                 self.log_to_gui("Update", f"执行 Git checkout {target_ref} for '{node_name}'...", "info")
                 stdout, stderr, returncode = self._run_git_command(["checkout", target_ref], cwd=node_install_path, timeout=60)
                 if returncode != 0:
                      self.log_to_gui("Update", f"Git checkout 失败 for '{node_name}': {stderr if stderr else '未知错误'}", "error")
                      # If checkout fails, it might be a branch that needs pulling (if HEAD was detached etc.)
                      # Try git pull as a fallback if checkout failed for a reference that exists remotely as a branch
                      check_branch_cmd = ["ls-remote", "--heads", "origin", target_ref]
                      stdout_check, stderr_check, returncode_check = self._run_git_command(check_branch_cmd, cwd=node_install_path, timeout=5)
                      if returncode_check == 0 and stdout_check.strip(): # It's a remote branch
                          self.log_to_gui("Update", f"'{target_ref}' 被识别为远程分支，尝试执行 Git pull...", "info")
                          # Try git pull origin target_ref
                          stdout, stderr, returncode = self._run_git_command(["pull", "origin", target_ref], cwd=node_install_path, timeout=120) # Allow more time
                          if returncode != 0:
                               self.log_to_gui("Update", f"Git pull 失败 for '{node_name}': {stderr if stderr else '未知错误'}", "error")
                               raise Exception(f"Git pull 失败 for '{node_name}'")
                          self.log_to_gui("Update", f"Git pull 完成 for '{node_name}'.", "info")
                      else:
                           # It's neither a branch nor a tag/commit that checkout could handle
                           self.log_to_gui("Update", f"无法识别或切换到引用 '{target_ref}' for '{node_name}': {stderr if stderr else '未知错误'}", "error")
                           raise Exception(f"无法识别或切换到引用 '{target_ref}' for '{node_name}'")
                 self.log_to_gui("Update", f"Git checkout {target_ref} 完成 for '{node_name}'.", "info")


            # Check for stop event
            if self.stop_event.is_set(): raise threading.ThreadExit

            # --- Update submodules (for both install and switch if it's a git repo) ---
            if os.path.isdir(node_install_path) and os.path.exists(os.path.join(node_install_path, ".git")):
                 if os.path.exists(os.path.join(node_install_path, ".gitmodules")):
                     self.log_to_gui("Update", f"执行 Git submodule update for '{node_name}'...", "info")
                     stdout, stderr, returncode = self._run_git_command(["submodule", "update", "--init", "--recursive"], cwd=node_install_path, timeout=180) # Increased timeout
                     if returncode != 0:
                          self.log_to_gui("Update", f"Git submodule update 失败 for '{node_name}': {stderr if stderr else '未知错误'}", "error")
                          # Not critical error? Continue but log.
                     else:
                          self.log_to_gui("Update", f"Git submodule update 完成 for '{node_name}'.", "info")
                 else:
                      self.log_to_gui("Update", f"'{node_name}' 目录未找到 .gitmodules 文件，跳过 submodule update。", "info")
            else:
                 self.log_to_gui("Update", f"跳过 submodule update，'{node_name}' 目录不是有效的 Git 仓库。", "warn")

            # Check for stop event
            if self.stop_event.is_set(): raise threading.ThreadExit


            # --- Re-install Node-specific Python dependencies (if requirements.txt exists) ---
            python_exe = self.python_exe_var.get()
            requirements_path = os.path.join(node_install_path, "requirements.txt")
            if python_exe and os.path.isfile(python_exe) and os.path.isdir(node_install_path) and os.path.isfile(requirements_path):
                 self.log_to_gui("Update", f"执行 pip 安装节点依赖 for '{node_name}'...", "info")
                 # Using --upgrade to ensure dependencies match the new requirements.txt
                 pip_cmd = [python_exe, "-m", "pip", "install", "-r", requirements_path, "--upgrade"]
                 # Add extra index URLs
                 pip_cmd.extend(["--extra-index-url", "https://download.pytorch.org/whl/cu118", "--extra-index-url", "https://download.pytorch.org/whl/cu121", "--extra-index-url", "https://download.pytorch.org/whl/rocm5.7"])

                 stdout, stderr, returncode = self._run_git_command(
                      pip_cmd,
                      cwd=node_install_path, timeout=180 # Allow more time
                 )
                 if returncode != 0:
                      self.log_to_gui("Update", f"Pip 安装节点依赖失败 for '{node_name}': {stderr if stderr else '未知错误'}", "error")
                      self.root.after(0, lambda name=node_name: messagebox.showwarning("节点依赖安装失败 / Node Dependency Install Failed", f"节点 '{name}' 的 Python 依赖安装失败，请手动检查。\n请查看后台日志获取详情。", parent=self.root))
                 else:
                      self.log_to_gui("Update", f"Pip 安装节点依赖完成 for '{node_name}'.", "info")
            else:
                 if os.path.isdir(node_install_path) and os.path.exists(os.path.join(node_install_path, ".git")): # Only warn if it's a git repo that *might* have had deps
                      self.log_to_gui("Update", f"节点 '{node_name}' 未找到 requirements.txt 或 Python 无效，跳过依赖安装。", "info")


            # Success message
            self.log_to_gui("Update", f"节点 '{node_name}' '{action}' 流程完成。", "info")
            self.root.after(0, lambda name=node_name, act=action: messagebox.showinfo("操作完成 / Operation Complete", f"节点 '{name}' 已成功执行 '{act}' 操作。", parent=self.root))

        except threading.ThreadExit:
             self.log_to_gui("Update", f"节点 '{node_name}' 操作任务已取消。", "warn")
        except Exception as e:
            error_msg = f"节点 '{node_name}' '{action}' 流程失败: {e}"
            self.log_to_gui("Update", error_msg, "error")
            self.root.after(0, lambda msg=error_msg: messagebox.showerror("操作失败 / Operation Failed", msg, parent=self.root))
        finally:
            # Always refresh list and update UI state after task finishes
            self.root.after(0, self.refresh_node_list)
            # UI state update is handled by the worker thread's finally block


    # --- Error Analysis Methods ---

    def run_diagnosis(self):
        """Captures ComfyUI logs and sends them to the configured API for analysis."""
        # No need to queue this, it's usually a quick network call and UI update
        # However, if the API call is long, it might block the UI.
        # Let's run the API call in a separate thread, but keep the log capture in the main thread.
        # Check if an update task is running
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中，无法运行诊断。", "warn"); return


        api_endpoint = self.error_api_endpoint_var.get().strip()
        api_key = self.error_api_key_var.get().strip() # Get key for potential use in API call
        comfyui_logs = self.main_output_text.get("1.0", tk.END).strip() # Get all text from ComfyUI log widget

        if not api_endpoint:
             self.log_to_gui("ErrorAnalysis", "无法运行诊断: API 接口地址未配置。", "error")
             messagebox.showwarning("配置缺失 / Missing Configuration", "请在“API 接口”中配置诊断 API 地址。", parent=self.root)
             return
        # Add optional API key check here if required by the specific API (e.g., Gemini)
        # For example:
        # if "gemini.google" in api_endpoint.lower() and not api_key:
        #      self.log_to_gui("ErrorAnalysis", "无法运行诊断: API 密匙未配置。", "error")
        #      messagebox.showwarning("配置缺失 / Missing Configuration", "请在“API 密匙”中配置诊断 API 密匙。", parent=self.root)
        #      return


        if not comfyui_logs:
             self.log_to_gui("ErrorAnalysis", "ComfyUI 后台日志为空，无法进行诊断。", "warn")
             messagebox.showwarning("日志为空 / Logs Empty", "ComfyUI 后台没有日志输出，无法进行诊断。", parent=self.root)
             return

        self.log_to_gui("ErrorAnalysis", f"正在连接诊断 API ({api_endpoint}) 并上传日志...", "info")
        # Clear previous analysis output
        self.error_analysis_text.config(state=tk.NORMAL); self.error_analysis_text.delete('1.0', tk.END); self.error_analysis_text.config(state=tk.DISABLED)

        # Disable Diagnose and Fix buttons while processing
        self._update_ui_state() # Update UI to show buttons disabled

        # Run the API call in a separate thread
        threading.Thread(target=self._run_diagnosis_task, args=(api_endpoint, api_key, comfyui_logs), daemon=True).start()


    def _run_diagnosis_task(self, api_endpoint, api_key, comfyui_logs):
        """Task to send logs to API and display analysis."""
        try:
            # TODO: Implement actual API call logic (using requests library):
            # 1. Prepare the data payload (usually JSON) containing the logs.
            # 2. Add API key to request headers or body as required by the API.
            # 3. Send a POST request to the api_endpoint.
            # 4. Handle network errors, timeout, and HTTP response codes.
            # 5. Parse the API response. Extract analysis results and suggested fixes/commands.
            # 6. Display the analysis result and suggested commands in self.error_analysis_text (using root.after for thread safety).

            # Example simulation of API interaction and response
            self.log_to_gui("ErrorAnalysis", "--- 开始诊断输出 (模拟) ---", "api_output")
            self.log_to_gui("ErrorAnalysis", "分析 ComfyUI 日志...", "api_output")

            # Simulate analyzing logs and finding an error + suggestion
            simulated_analysis = """
检测到可能的错误：
Python 解释器路径配置不正确或 ComfyUI 依赖未完全安装。
Traceback 中显示 'No module named xformers' 或 'No module named comfy_extras' 等模块导入错误。这通常意味着 Python 环境不正确、依赖缺失或节点未安装。

诊断建议：
1. 检查 ComfyUI Python 路径是否正确。
2. 如果是依赖错误 (例如 xformers, torch)，尝试重新安装 ComfyUI 依赖。
3. 如果是节点模块错误 (例如 comfy_extras)，检查 custom_nodes 目录下对应的节点是否安装且完整。

建议执行的命令 (请谨慎使用)：
# 进入 ComfyUI 安装目录
cd "{comfyui_dir}"
# 安装 ComfyUI 主要依赖 (根据你的环境可能需要调整 extra-index-url)
"{python_exe}" -m pip install -r requirements.txt --upgrade --extra-index-url https://download.pytorch.org/whl/cu118 --extra-index-url https://download.pytorch.org/whl/cu121 --extra-index-url https://download.pytorch.org/whl/rocm5.7
# 如果遇到 xformers 错误，尝试安装特定版本 (可能需要根据你的GPU和Python版本调整)
# "{python_exe}" -m pip install xformers==0.0.20.dev513
# 如果是节点依赖问题，进入节点目录安装 (例如 comfy_extras 目录)
# cd "{comfyui_dir}/custom_nodes/comfy_extras"
# "{python_exe}" -m pip install -r requirements.txt --upgrade
        """
            # Replace placeholders with actual paths for display
            comfyui_dir = self.comfyui_dir_var.get()
            python_exe = self.python_exe_var.get()
            git_exe = self.git_exe_path_var.get()
            simulated_analysis = simulated_analysis.format(comfyui_dir=comfyui_dir, python_exe=python_exe, git_exe=git_exe)


            # Simulate delay
            time.sleep(3)

            # Display results in GUI thread
            self.root.after(0, lambda: self.log_to_gui("ErrorAnalysis", simulated_analysis, "api_output"))
            self.root.after(0, lambda: self.log_to_gui("ErrorAnalysis", "--- 诊断输出结束 (模拟) ---", "api_output"))
            self.root.after(0, lambda: self.log_to_gui("ErrorAnalysis", "诊断完成 (模拟)。/ Diagnosis complete (simulated).", "info"))

        except Exception as e:
            error_msg = f"诊断 API 调用失败: {e}"
            self.log_to_gui("ErrorAnalysis", error_msg, "error")
            self.root.after(0, lambda msg=str(e): messagebox.showerror("诊断失败 / Diagnosis Failed", f"调用诊断 API 失败:\n{msg}", parent=self.root))

        finally:
             # Always re-enable Diagnose and Fix buttons after task finishes (in GUI thread)
             self.root.after(0, self._update_ui_state)


    def run_fix(self):
        """Executes commands from the error analysis output to fix errors. Queued for worker thread."""
        # Check if an update task is running
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中，无法执行修复。", "warn"); return

        # Get analysis output from UI widget in GUI thread
        analysis_output = self.error_analysis_text.get("1.0", tk.END).strip() # Use error_analysis_text widget

        if not analysis_output:
             self.log_to_gui("ErrorAnalysis", "错误分析输出为空，无法执行修复命令。", "warn")
             messagebox.showwarning("无输出 / No Output", "错误分析输出为空，无法执行修复命令。", parent=self.root)
             return

        comfyui_dir = self.comfyui_dir_var.get()
        python_exe = self.python_exe_var.get()
        git_exe = self.git_exe_path_var.get()

        # Validate paths before proceeding
        if not self._validate_paths_for_execution(check_comfyui=True, check_git=True, show_error=True):
             self.log_to_gui("ErrorAnalysis", "无法执行修复命令: 路径配置无效。", "error")
             return

        # Extract commands from the analysis output
        lines = analysis_output.splitlines()
        commands_to_execute = []
        # Use the actual comfyui_dir as the starting point for tracking CWD
        current_cwd = comfyui_dir

        for line in lines:
             line = line.strip()
             # Simple detection for command-like lines (starts with recognizable executable/command)
             # Use case-insensitive check for 'cd'
             # Also check if the line starts with the configured python_exe or git_exe (quoted or not)
             line_lower = line.lower()
             python_exe_lower = python_exe.lower().strip('"')
             git_exe_lower = git_exe.lower().strip('"')

             is_cd_command = line_lower.startswith(('cd ', '"cd '))
             is_python_command = line_lower.startswith(python_exe_lower) or line_lower.startswith(f'"{python_exe_lower}"')
             is_git_command = line_lower.startswith(git_exe_lower) or line_lower.startswith(f'"{git_exe_lower}"')

             if is_cd_command or is_python_command or is_git_command:
                  # Remove comment marker if present
                  if line.startswith("# "): line = line[2:].strip()
                  if line.startswith("#"): continue # Skip pure comment lines

                  # Replace placeholders if any left (e.g., {comfyui_dir})
                  # Make sure to handle potential quotes in paths
                  processed_line = line.replace("{comfyui_dir}", shlex.quote(comfyui_dir))\
                                       .replace("{python_exe}", shlex.quote(python_exe))\
                                       .replace("{git_exe}", shlex.quote(git_exe))

                  commands_to_execute.append({"cmd": processed_line, "cwd": current_cwd})
                  # Simulate tracking directory changes (very basic)
                  if is_cd_command:
                       # Extract directory path, handling quotes
                       new_dir_part = processed_line[len('cd '):].strip()
                       try:
                            new_dir_parts = shlex.split(new_dir_part)
                            if new_dir_parts:
                                new_dir = new_dir_parts[0] # Take the first part after cd
                            else:
                                new_dir = "" # Empty cd command?
                       except Exception:
                            new_dir = new_dir_part # Fallback if shlex fails

                       # Join relative paths with the current simulated cwd, handle absolute paths
                       if os.path.isabs(new_dir):
                            current_cwd = os.path.normpath(new_dir)
                       else:
                            # Check if current_cwd is valid before joining
                            if os.path.isdir(current_cwd): # Check if the simulated current_cwd exists on filesystem
                                current_cwd = os.path.normpath(os.path.join(current_cwd, new_dir))
                            else:
                                 self.log_to_gui("ErrorAnalysis", f"模拟工作目录无效或不存在: {current_cwd}，无法执行相对 cd 到 {new_dir}", "error")
                                 # Fallback to ComfyUI root if current simulated cwd is invalid
                                 current_cwd = comfyui_dir


        if not commands_to_execute:
             self.log_to_gui("ErrorAnalysis", "在诊断输出中未检测到可执行的修复命令。", "warn")
             messagebox.showwarning("无修复命令 / No Fix Commands", "在诊断输出中未找到可执行的修复命令。", parent=self.root)
             return

        confirm = messagebox.askyesno(
             "确认执行修复命令 / Confirm Execute Fix Commands",
             f"确定要执行以下 {len(commands_to_execute)} 条修复命令吗？\n这将修改您的文件和环境。\n\n确认前请确保 ComfyUI 已停止运行。",
             parent=self.root
        )
        if not confirm: return


        # Disable Diagnose and Fix buttons while processing
        self._update_ui_state()

        # Queue the command execution task
        self.update_task_queue.put((self._run_fix_task, [commands_to_execute], {}))


    def _run_fix_task(self, commands_to_execute):
        """Task to execute a list of commands for fixing errors. Runs in worker thread."""
        self.log_to_gui("ErrorAnalysis", "--- 开始执行修复命令 ---", "info")

        # Use the actual comfyui_dir as the starting point for command execution CWD
        current_cwd = self.comfyui_dir_var.get()

        def execute_next_command(index):
            # This function should ideally not be in the worker thread calling root.after.
            # The worker thread should execute commands sequentially directly.
            # The GUI thread will then process the log messages via process_output_queues.
            pass # This structure is wrong for a worker thread

        # Correct approach: Loop and execute commands sequentially in the worker thread
        command_index = 0
        while command_index < len(commands_to_execute):
            # Check for stop event before executing each command
            if self.stop_event.is_set():
                 self.log_to_gui("ErrorAnalysis", "修复命令执行任务已取消。", "warn"); break

            cmd_info = commands_to_execute[command_index]
            cmd_string = cmd_info["cmd"]
            original_cmd_cwd_simulated = cmd_info["cwd"] # The simulated CWD from parsing

            # Update the actual CWD based on previous simulated 'cd' commands
            # The parsing loop above already calculated the simulated `current_cwd` step by step.
            # We need to re-calculate the CWD for the *current* command based on the sequence
            # up to this command. Or, just use the last calculated `current_cwd` from the loop.
            # Let's recalculate CWD sequentially within the execution loop for safety.
            current_execution_cwd = self.comfyui_dir_var.get() # Always start from base
            for i in range(command_index + 1): # Re-evaluate CWD up to the current command
                 prev_cmd_info = commands_to_execute[i]
                 prev_cmd_string = prev_cmd_info["cmd"]
                 if prev_cmd_string.lower().startswith(('cd ', '"cd ')):
                      # Extract directory path, handling quotes
                      new_dir_part = prev_cmd_string[len('cd '):].strip()
                      try:
                           new_dir_parts = shlex.split(new_dir_part)
                           if new_dir_parts:
                               new_dir = new_dir_parts[0]
                           else:
                               new_dir = ""
                      except Exception:
                           new_dir = new_dir_part

                      # Update current_execution_cwd (handle absolute paths)
                      if os.path.isabs(new_dir):
                           current_execution_cwd = os.path.normpath(new_dir)
                      else:
                           current_execution_cwd = os.path.normpath(os.path.join(current_execution_cwd, new_dir))

            # Skip simulated 'cd' commands during execution; CWD is handled internally
            if cmd_string.lower().startswith(('cd ', '"cd ')):
                 self.log_to_gui("ErrorAnalysis", f"模拟改变目录到: {current_execution_cwd}", "cmd")
                 command_index += 1 # Move to the next command
                 continue # Skip execution for cd

            # Log the command being executed in the error analysis output
            self.log_to_gui("ErrorAnalysis", f"执行命令 {command_index+1}/{len(commands_to_execute)} (工作目录: {current_execution_cwd}):", "cmd")
            self.log_to_gui("ErrorAnalysis", cmd_string, "cmd")

            # Execute the actual command
            cmd_parts = shlex.split(cmd_string) # Safely split the command string into parts

            stdout, stderr, returncode = "", "", 1 # Default failure
            command_failed = False

            try:
                 # Determine if it's a git command or a python/pip command
                 is_git_command = cmd_parts[0].lower().strip('"') == git_exe.lower().strip('"') if cmd_parts else False
                 is_python_command = cmd_parts[0].lower().strip('"') == python_exe.lower().strip('"') if cmd_parts else False

                 # Need to ensure cwd exists for subprocess before running
                 if not os.path.isdir(current_execution_cwd):
                      error_msg = f"执行命令失败: 工作目录 '{current_execution_cwd}' 不存在或无效。"
                      self.log_to_gui("ErrorAnalysis", error_msg, "error")
                      stdout, stderr, returncode = "", error_msg, 1
                      command_failed = True
                 else:
                      # Use subprocess.Popen with piping to capture and log output
                      process = subprocess.Popen(
                          cmd_parts,
                          cwd=current_execution_cwd, # Use the calculated CWD
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          text=True, encoding='utf-8', errors='replace',
                          startupinfo=None,
                          creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                          env=os.environ.copy() # Use a copy of the environment
                      )

                      # Threads to read pipes and log to GUI
                      stdout_thread = threading.Thread(target=self.stream_output, args=(process.stdout, self.comfyui_output_queue, "[Fix stdout]"), daemon=True)
                      stderr_thread = threading.Thread(target=self.stream_output, args=(process.stderr, self.comfyui_output_queue, "[Fix stderr]"), daemon=True)

                      stdout_thread.start()
                      stderr_thread.start()

                      # Wait for the command to finish with timeout
                      command_timeout = 300 # Default timeout for fix commands
                      if is_git_command or is_python_command and "install" in cmd_string.lower():
                           command_timeout = 600 # Longer timeout for installs/clones

                      try:
                           returncode = process.wait(timeout=command_timeout)
                      except subprocess.TimeoutExpired:
                          self.log_to_gui("ErrorAnalysis", f"命令超时 ({command_timeout} 秒), 进程被终止。", "error")
                          try: process.kill()
                          except OSError: pass
                          returncode = 124

                      # Wait for reader threads to finish
                      stdout_thread.join(timeout=5)
                      stderr_thread.join(timeout=5)

                      if returncode != 0: command_failed = True


            except FileNotFoundError:
                 error_msg = f"命令未找到: {cmd_parts[0]}"
                 self.log_to_gui("ErrorAnalysis", error_msg, "error")
                 stdout, stderr, returncode = "", error_msg, 127
                 command_failed = True
            except Exception as e:
                 error_msg = f"执行命令时发生意外错误: {e}\n命令: {cmd_string}"
                 self.log_to_gui("ErrorAnalysis", error_msg, "error")
                 stdout, stderr, returncode = "", error_msg, 1
                 command_failed = True

            # After execution, check for failure and ask user if needed (in GUI thread)
            if not command_failed:
                 self.log_to_gui("ErrorAnalysis", "命令执行完成。", "info")
                 command_index += 1 # Move to the next command
            else:
                 # On failure, ask user if they want to continue (needs GUI thread)
                 self.root.after(0, lambda cmd=cmd_string, idx=command_index: self._ask_continue_fix(cmd, idx))
                 return # Stop the worker loop, GUI thread will handle continuation


        # If loop completes without failure or user cancellation
        self.log_to_gui("ErrorAnalysis", "--- 修复命令执行完成 ---", "info")
        self.root.after(0, lambda: messagebox.showinfo("修复完成 / Fix Complete", "修复命令执行流程完成。", parent=self.root))
        # Re-enable buttons in GUI thread
        self.root.after(0, self._update_ui_state)


    def _ask_continue_fix(self, failed_cmd_string, failed_index):
         """Asks user in GUI thread if they want to continue fix task after a failure."""
         continue_fix = messagebox.askyesno(
             "命令执行失败 / Command Execution Failed",
             f"执行命令失败:\n{failed_cmd_string}\n\n是否继续执行下一条命令?",
             parent=self.root
         )
         if continue_fix:
              self.log_to_gui("ErrorAnalysis", "用户选择继续执行。", "info")
              # Queue the task to continue from the next command
              self.update_task_queue.put((self._run_fix_task_from_index, [commands_to_execute, failed_index + 1], {}))
         else:
              self.log_to_gui("ErrorAnalysis", "用户取消后续修复命令执行。", "info")
              # Re-enable buttons in GUI thread
              self.root.after(0, self._update_ui_state)

    # Helper task to continue fix from a specific index
    def _run_fix_task_from_index(self, commands_to_execute, start_index):
        """Continues the fix task from a specified index."""
        self.log_to_gui("ErrorAnalysis", f"从命令 {start_index+1} 开始继续执行修复流程...", "info")
        # Call the main task function, letting it handle the loop from the start_index
        self._run_fix_task(commands_to_execute[start_index:]) # Pass the remaining commands


    # --- UI State and Helpers ---
    def _update_ui_state(self):
        """Central function to update all button states and status label."""
        comfy_running_internally = self._is_comfyui_running()
        comfy_detected_externally = getattr(self, 'comfyui_externally_detected', False)
        update_task_running = self._is_update_task_running()


        status_text = ""; main_stop_style = "Stop.TButton";
        run_comfyui_button_enabled = tk.NORMAL; stop_all_button_enabled = tk.NORMAL;
        should_stop_progress = True

        is_any_starting_or_stopping = False
        try:
             if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists():
                # Consider progress bar active if it's indeterminate and mapped (visible)
                is_any_starting_or_stopping = self.progress_bar.cget('mode') == 'indeterminate' and self.progress_bar.winfo_ismapped()
        except tk.TclError:
             pass

        # State Logic based on ComfyUI status and Update task status
        if update_task_running:
             status_text = "状态: 更新/维护任务进行中... / Status: Update/Maintenance Task In Progress..."
             should_stop_progress = False # Keep progress bar running
             run_comfyui_button_enabled = tk.DISABLED # Disable ComfyUI start
             # Allow stopping update task? Yes, by stopping "all services"
             stop_all_button_enabled = tk.NORMAL # Enable stop button
             main_stop_style = "StopRunning.TButton" # Use running style for stop

        elif comfy_detected_externally and not comfy_running_internally:
             status_text = f"状态: 外部 ComfyUI 运行中 (端口 {self.comfyui_api_port})"
             stop_all_button_enabled = tk.DISABLED # Cannot stop external process
             run_comfyui_button_enabled = tk.DISABLED # Cannot start another if external detected
             should_stop_progress = True # Progress bar should stop

        elif comfy_running_internally: # Managed ComfyUI is running
            status_text = "状态: ComfyUI 后台运行中 / Status: ComfyUI Backend Running"
            main_stop_style = "StopRunning.TButton"
            run_comfyui_button_enabled = tk.DISABLED # Cannot start another
            stop_all_button_enabled = tk.NORMAL # Can stop managed process
            should_stop_progress = True # Progress bar should stop if service is stable running

        else: # ComfyUI is not running (neither managed nor external detected), AND no update task is running
             if is_any_starting_or_stopping:
                 # This state should ideally not be reached if update_task_running covers background tasks.
                 # This might indicate ComfyUI is starting/stopping but not yet fully up/down.
                 # Keep the previous status text if it indicates starting/stopping ComfyUI.
                 current_status = "状态: 处理中..."
                 try:
                     if hasattr(self, 'status_label') and self.status_label.winfo_exists():
                         current_status = self.status_label.cget("text")
                         if "启动 ComfyUI" in current_status or "停止 ComfyUI" in current_status or "Starting ComfyUI" in current_status or "Stopping ComfyUI" in current_status:
                              status_text = current_status
                         else:
                              status_text = "状态: 处理中..."
                 except tk.TclError: pass

                 should_stop_progress = False # Keep progress bar running
                 run_comfyui_button_enabled = tk.DISABLED # Disable buttons while processing
                 # Enable stop button here to allow cancelling ComfyUI start/stop
                 stop_all_button_enabled = tk.NORMAL # Enable stop during ComfyUI start/stop
                 main_stop_style = "StopRunning.TButton" # Use running style for stop while starting/stopping ComfyUI


             else:
                 # Nothing is running or starting/stopping
                 status_text = "状态: 服务已停止 / Status: Service Stopped"
                 should_stop_progress = True # Progress bar should be stopped
                 stop_all_button_enabled = tk.DISABLED # No service to stop


        if should_stop_progress:
            try:
                if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists() and self.progress_bar.winfo_ismapped():
                     self.progress_bar.stop()
                     # Hide progress bar when stopped
                     # self.progress_bar.grid_forget() # Optional: Hide it completely
            except tk.TclError: pass
        else:
             try:
                  if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists():
                       # Ensure it's shown and starting
                       # self.progress_bar.grid(row=0, column=2, padx=10) # Ensure it's visible
                       if self.progress_bar.cget('mode') != 'indeterminate' or not self.progress_bar.winfo_ismapped():
                           self.progress_bar.start(10)
             except tk.TclError: pass


        try:
            if hasattr(self, 'status_label') and self.status_label.winfo_exists(): self.status_label.config(text=status_text)

            # Update global Run button state (now "运行 ComfyUI")
            # Disable if any process is running or starting/stopping OR if ComfyUI paths are bad
            comfy_can_run_paths = self._validate_paths_for_execution(check_comfyui=True, check_git=False, show_error=False)
            final_run_state = tk.NORMAL if not comfy_running_internally and not comfy_detected_externally and not update_task_running and not is_any_starting_or_stopping and comfy_can_run_paths else tk.DISABLED
            if hasattr(self, 'run_all_button') and self.run_all_button.winfo_exists():
                self.run_all_button.config(state=final_run_state, style="Accent.TButton")

            # Update global Stop button state
            # Enable if managed ComfyUI is running OR if any update task is running OR if ComfyUI is starting/stopping
            final_stop_state = tk.NORMAL if comfy_running_internally or update_task_running or is_any_starting_or_stopping else tk.DISABLED
            if hasattr(self, 'stop_all_button') and self.stop_all_button.winfo_exists():
                 self.stop_all_button.config(state=final_stop_state, style=main_stop_style)


            # Update Update Management tab buttons
            # Enable Update buttons if Git path is valid AND no update task is running AND ComfyUI is not starting/stopping
            git_path_ok = self._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=False)
            update_buttons_enabled = tk.NORMAL if git_path_ok and not update_task_running and not is_any_starting_or_stopping else tk.DISABLED

            if hasattr(self, 'refresh_main_body_button') and self.refresh_main_body_button.winfo_exists():
                 self.refresh_main_body_button.config(state=update_buttons_enabled)
            if hasattr(self, 'activate_main_body_button') and self.activate_main_body_button.winfo_exists():
                 # Also check if an item is selected in the main body treeview for activate button
                 item_selected_in_main_body_tree = bool(self.main_body_tree.focus())
                 self.activate_main_body_button.config(state=update_buttons_enabled if item_selected_in_main_body_tree else tk.DISABLED)

            if hasattr(self, 'nodes_control_frame'): # Check if the frame exists
                 # Enable refresh/install/update all buttons if git path ok and no update task is running and no comfyui starting/stopping
                 nodes_buttons_enabled = update_buttons_enabled # Same condition as other update buttons

                 if hasattr(self, 'nodes_search_entry') and self.nodes_search_entry.winfo_exists():
                      self.nodes_search_entry.config(state=tk.NORMAL if git_path_ok else tk.DISABLED) # Search entry only needs git path


                 if hasattr(self, 'refresh_nodes_button') and self.refresh_nodes_button.winfo_exists():
                      self.refresh_nodes_button.config(state=nodes_buttons_enabled)
                 if hasattr(self, 'switch_install_node_button') and self.switch_install_node_button.winfo_exists():
                      # Also check if an item is selected in the nodes treeview for switch/install button
                      item_selected_in_nodes_tree = bool(self.nodes_tree.focus())
                      self.switch_install_node_button.config(state=nodes_buttons_enabled if item_selected_in_nodes_tree else tk.DISABLED)
                 if hasattr(self, 'update_all_nodes_button') and self.update_all_nodes_button.winfo_exists():
                      # Update All only needs git path and no update task running
                      self.update_all_nodes_button.config(state=update_buttons_enabled)


            # Update Error Analysis tab buttons (Req 4: Enabled based on API endpoint)
            # Enable Diagnose button if API endpoint is set AND no update task is running AND ComfyUI is not starting/stopping
            api_endpoint_set = bool(self.error_api_endpoint_var.get().strip())
            diagnose_enabled = tk.NORMAL if api_endpoint_set and not update_task_running and not is_any_starting_or_stopping else tk.DISABLED
            if hasattr(self, 'diagnose_button') and self.diagnose_button.winfo_exists():
                 self.diagnose_button.config(state=diagnose_enabled)

            # Fix button state is enabled *only* by run_diagnosis logic if commands are found.
            # It must be disabled if there's no API endpoint, or diagnose is disabled, or any process is running (start/stop/fix itself).
            # Get the current state first before potentially disabling it
            current_fix_state = self.fix_button.cget('state') if hasattr(self, 'fix_button') and self.fix_button.winfo_exists() else tk.DISABLED

            if hasattr(self, 'fix_button') and self.fix_button.winfo_exists():
                 if not api_endpoint_set or not diagnose_enabled == tk.NORMAL or update_task_running or is_any_starting_or_stopping:
                      self.fix_button.config(state=tk.DISABLED)
                 else:
                      # If conditions are met, restore the state that run_diagnosis might have set
                      self.fix_button.config(state=current_fix_state)


        except tk.TclError as e: print(f"[Launcher WARNING] Error updating UI state (widget might not exist): {e}")
        except AttributeError as e: print(f"[Launcher WARNING] Error updating UI state (attribute missing): {e}")

    def reset_ui_on_error(self):
        """Resets UI state after a service encounters an error."""
        print("[Launcher INFO] Resetting UI on error.")
        try:
            if hasattr(self, 'progress_bar') and self.progress_bar.winfo_exists() and self.progress_bar.winfo_ismapped():
                self.progress_bar.stop()
        except tk.TclError: pass

        # Check only ComfyUI process
        if self.comfyui_process and self.comfyui_process.poll() is not None:
            print("[Launcher INFO] ComfyUI process found terminated after error.")
            self.comfyui_process = None

        self.stop_event.clear();
        self.backend_browser_triggered_for_session = False;
        self.comfyui_ready_marker_sent = False;
        self.comfyui_externally_detected = False; # Clear external detection on error
        self._update_task_running = False; # Ensure update task flag is cleared

        self._update_ui_state()


    # Renamed _trigger_backend_browser_opening to _trigger_comfyui_browser_opening
    def _trigger_comfyui_browser_opening(self):
        """Opens the ComfyUI URL in a web browser when ComfyUI is ready."""
        comfy_is_active = self._is_comfyui_running() or self.comfyui_externally_detected
        if comfy_is_active and not self.backend_browser_triggered_for_session:
            self.backend_browser_triggered_for_session = True
            # The actual browser opening logic is in _open_frontend_browser
            self.root.after(100, self._open_frontend_browser) # Add slight delay to ensure port is fully open
        elif not comfy_is_active: print("[Launcher DEBUG] ComfyUI browser trigger skipped - ComfyUI stopped or not detected.")
        else: print("[Launcher DEBUG] ComfyUI browser trigger skipped - Already triggered for this session.")


    def _open_frontend_browser(self):
        """Opens the ComfyUI backend URL in a web browser (formerly frontend)."""
        # This method is now triggered by the ComfyUI ready marker
        comfyui_url = f"http://127.0.0.1:{self.config.get('comfyui_api_port', DEFAULT_COMFYUI_API_PORT)}"
        print(f"[Launcher INFO] Opening ComfyUI URL: {comfyui_url}")
        try:
             webbrowser.open_new_tab(comfyui_url)
        except Exception as e:
             print(f"[Launcher ERROR] Error opening ComfyUI browser tab: {e}")
             self.log_to_gui("ComfyUI", f"无法在浏览器中打开ComfyUI网址: {comfyui_url}\n错误: {e}", "warn")


    def clear_output_widgets(self):
        """Clears the text in the output ScrolledText widgets."""
        # Only clear main_output_text and error_analysis_text now
        for widget in [self.main_output_text, self.error_analysis_text]: # Corrected widget name
            try:
                if widget and widget.winfo_exists():
                    widget.config(state=tk.NORMAL);
                    widget.delete('1.0', tk.END);
                    widget.config(state=tk.DISABLED)
            except tk.TclError: pass


    def on_closing(self):
        """Handles the application closing event."""
        print("[Launcher INFO] Closing application requested.")
        # Check if any process (ComfyUI or Update task) is running
        if self._is_comfyui_running() or self._is_update_task_running():
             # Ask user if they want to stop services/tasks
             confirm_stop = messagebox.askyesno("进程运行中 / Processes Running", "有后台进程（ComfyUI 或更新任务）正在运行。\n是否在退出前停止？", parent=self.root)

             if confirm_stop:
                 self.stop_all_services() # This sets stop_event and tries to terminate ComfyUI process

                 # Wait for processes to stop with a timeout
                 wait_timeout = 20 # seconds
                 start_time = time.time()
                 while (self._is_comfyui_running() or self._is_update_task_running()) and (time.time() - start_time < wait_timeout):
                     time.sleep(0.1) # Wait briefly

                 if self._is_comfyui_running() or self._is_update_task_running():
                      print("[Launcher WARNING] Processes did not stop gracefully within timeout, forcing exit.")
                      # Force stop remaining if any
                      if self._is_comfyui_running():
                           try: self.comfyui_process.kill()
                           except Exception: pass
                      # If update task is still running, it might be stuck, cannot forcefully kill a thread easily
                      self.log_to_gui("Launcher", "未能完全停止所有后台进程，强制退出中。", "error")

                 self.root.destroy() # Destroy the main window

             else:
                  print("[Launcher INFO] User chose not to stop processes gracefully, attempting direct termination.")
                  if self._is_comfyui_running():
                      try: self.comfyui_process.terminate()
                      except Exception: pass
                  self.stop_event.set(); # Signal reader threads and update worker to stop
                  self.root.destroy()
        else:
             # No processes running, just destroy the window
             self.root.destroy()


# --- Main Execution ---
if __name__ == "__main__":
    # Removed Flask specific checks
    # Basic check for Python executable (though ComfyUI Python is configured)
    # and maybe git executable if we want to be strict early
    # Let's rely on the in-app path validation for ComfyUI/Git paths.
    # Just check if Tkinter works.

    try:
        root = tk.Tk()
        app = ComLauncherApp(root)
        root.mainloop()
    except Exception as e:
        # Catch any unexpected errors during app initialization or mainloop
        print(f"[Launcher CRITICAL] Unhandled exception during application startup or runtime: {e}", exc_info=True)
        # Try to show an error message box if root is still available
        try:
             if 'root' in locals() and root and root.winfo_exists():
                  messagebox.showerror("致命错误 / Fatal Error", f"应用程序遇到致命错误：\n{e}\n请检查日志。", parent=root)
                  root.destroy()
             else:
                  # If root is not available, print to console/stderr
                  print("无法在GUI中显示错误信息。")
        except Exception as mb_err:
             print(f"无法显示错误对话框：{mb_err}")
        sys.exit(1) # Exit with a non-zero code```


@@@@ File: run_requirements.bat (Relative Path: run_requirements.bat
```
@echo off

set "python_exec=python.exe"
set "requirements_txt=%~dp0\requirements.txt"
set "venv_folder=%~dp0\venv"

rem 检测是否存在venv文件夹
if not exist "%venv_folder%" (
    echo Creating virtual environment...
    %python_exec% -m venv "%venv_folder%"
    echo Virtual environment created successfully.
) else (
    echo Virtual environment already exists.
)

echo Installing with ComfyUI Portable
echo .
echo Install requirement.txt...
for /f "delims=" %%i in (%requirements_txt%) do (
    %python_exec% -s -m pip install "%%i"
)

echo .
echo Install Finish!
pause

rem Then, install the correct PyTorch version / 然后，安装正确的 PyTorch 版本
rem (Example for CUDA 11.8, replace with user's correct command)
rem (CUDA 11.8 示例，替换为用户正确的命令)
rem pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
rem (CUDA 12.4示例，替换为用户正确的命令)
rem pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
rem (CUDA 12.6示例，替换为用户正确的命令)
rem pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126    ```


@@@@ File: 运行_launcher.bat (Relative Path: 运行_launcher.bat
```
@echo off

REM --- Get the directory where this batch script is located ---
REM --- 获取此批处理脚本所在的目录 ---
SET "SCRIPT_DIR=%~dp0"

REM --- Construct the full paths ---
REM --- 构建完整路径 ---
SET "PYTHONW_EXE=%SCRIPT_DIR%venv\Scripts\pythonw.exe"
SET "LAUNCHER_PY=%SCRIPT_DIR%launcher.py"

REM --- Check if files exist (optional but good practice) ---
REM --- 检查文件是否存在（可选，但建议） ---
IF NOT EXIST "%PYTHONW_EXE%" (
    ECHO Error: PythonW not found at "%PYTHONW_EXE%"
    PAUSE
    EXIT /B 1
)
IF NOT EXIST "%LAUNCHER_PY%" (
    ECHO Error: Launcher script not found at "%LAUNCHER_PY%"
    PAUSE
    EXIT /B 1
)

REM --- Run the launcher script using pythonw.exe ---
REM --- 使用 pythonw.exe 运行启动器脚本 ---
REM --- The START command helps ensure the batch file can exit immediately. ---
REM --- START 命令有助于确保批处理文件可以立即退出。 ---
REM --- The "" is a placeholder for the window title (required by START). ---
REM --- "" 是窗口标题的占位符（START 命令需要）。 ---
START "" "%PYTHONW_EXE%" "%LAUNCHER_PY%"

REM --- Exit the batch script ---
REM --- 退出批处理脚本 ---
EXIT /B 0```


@@@@ File: README.md (Relative Path: README.md
```
@@@@功能说明：
ComfyUI启动器


@@@@文件夹架构：
ComLauncher/
├─ templates/                       # 模板文件（主要是 HTML 模板）
│  └─ icon.ico                     # ico 文件
├─ README.md                        # 项目说明文件
├─ launcher.py                      # 启动器脚本
├─ launcher_config.json             # 启动器配置文件
├─ requirements.txt                 # 依赖项清单
├─ run_requirements.bat             # Windows 依赖安装脚本（BAT 格式）
└─ 运行_launcher.bat             # Windows 启动器脚本（BAT 格式）

@@@@@当前launcher.py节点代码：
@@@@@后端comfyui日志：

@@@@以下为修改日志：
##20250423
基于launcher.py修改要求：
程序名称为ComLauncher；
参考铁锅炖comfyui界面设定和秋叶comfyui界面设定，重写当前launcher.py。
@@@@@要求1：
删除“前端”标签及相关内容，标签按照顺序修改为：设置、更新管理、Comfyui后台、错误分析；
@@@@标签页面详细信息如下：
@@设置标签页：完全保留现有布局和功能内容。在基本路径与端口界面，增加git路径，默认为：D:\Program\ComfyUI_Program\ComfyUI\git\cmd\git.exe。当本程序任意有需求git调用时，从中调用
基本路径中 api接口改为comfyui界面的监听和远程共享接口，意思是当我设定为8188，则comfyui从127.0.0.1：8188打开，当设定为8189，则comfyui从127.0.0.1：8189打开
性能显存优化，中删除所有“自动”相关选项。

@@更新管理标签页：
自上而下为两个区域：
标签页内顶部为：仓库地址、节点管理
@仓库地址区域有：
本体仓库地址，默认为：https://gitee.com/AIGODLIKE/ComfyUI.git
节点配置地址，默认为：https://raw.githubusercontent.com/ltdrdata/ComfyUI-Manager/main/custom-node-list.json
仓库地址及节点配置地址修改后默认保存。

@节点管理区域有设两个标签页面：本体、节点
本体标签页要求：标签页为列表。通过上述本体仓库地址加载的列表，点击更新时加载当前地址栏填写的对应地址。匹配当前comfyui版本，并可选择列表中的版本激活，点击激活后则下载当前版本并覆盖安装（参考第一张照片视觉效果）；
节点标签页要求：标签页内顶部有搜索框，搜索框以下为列表。列表默认为本地已安装节点及读取对应的github配置地址，点击更新时加载当前地址栏填写的对应地址。列表显示，并配有版本切换选项。搜索框可以搜索匹配节点配置地址，并结合本地已安装节点显示是否已安装，可选择列表中的版本切换（对于未在本地文件则为对应版本下载），点击切换后则下载当前版本并覆盖安装（参考第二张照片视觉效果）；
节点标签页内，列表默认为本地已安装nodes节点列表及读取对应的github配置地址，并配有版本切换选项。

@@Comfyui后台标签页：为现有“后端_comfyui”标签，完全保留现状布局和功能内容，删除标签页内顶部的“运行”和“停止”
@@错误分析标签页：
标签页内，参考“后端_comfyui”标签布局，标签页内顶部为“API接口”填入框，换行显示“API密匙”填入框（“API密匙”填入框默认为空，当填入api后可运行，但是文字显示为*号），“诊断”按钮，“修复”按钮；余下为cmd代码显示框。诊断按钮在填入“API接口”后可运行。
API接口系统设定为“你是一位严谨且高效的AI代码工程师和网页设计师，专注于为用户提供精确、可执行的前端及后端代码方案，并精通 ComfyUI 的集成。你的回复始终优先使用中文。@@ComfyUI 集成: 精通 ComfyUI 的 API (/prompt, /upload/image, /ws 等) 调用及数据格式，能够设计和实现前端与 ComfyUI 工作流的对接方案（例如参数注入、结果获取），当ComfyUI 运行出错后可以提供解决方案。”

运行逻辑（以API接口为google gemini2.5为例）：
点击诊断按钮后，将“Comfyui后台”标签页中的所有信息传入对接API接口，API接口分析后将修改意见输出，并显示在本标签页内的cmd代码显示框内。
点击修复按钮后，将筛选诊断结果，并在当前cmd代码显示框内逐步运行，以修复错误。
##20250424-1
@@@@@要求1：调整更新管理标签页，本体标签页：列表可展示二十条以上版本内容，当下拉滑块后，可继续加载全部版本信息
@@@@@要求2：调整更新管理标签页，节点标签页：列表默认显示为当前ComfyUI\custom_nodes内全部节点。要求全部展示，显示不足可以下拉滑块显示。当其搜索框有文字执行搜索后，才显示已安装和未安装的节点。
@@@@@要求3：调整comfyui后台标签页：调整当前标签页的cmd显示框占满标签页内部
##20250424-2
@@@@@要求1：调整更新管理标签页，本体标签页：列表可展示二十条以上版本内容，且内容为准确信息。当下拉滑块后，可继续加载全部版本信息
@@@@@要求2：调整更新管理标签页，节点标签页：保持默认全部显示为当前ComfyUI\custom_nodes内全部节点。列表中对应各个节点，读取其git仓库地址。
@@@@@要求3：调整更新管理标签页，节点标签页：列表保持默认全部显示为当前ComfyUI\custom_nodes内全部节点。在“状态”与“版本”之前增加“本地版本”显示。其中“本地版本”为本地版本号，“版本”为git仓库当前版本号
##20250424-3
@@@@@要求1：调整更新管理标签页，本体标签页：列表可展示版本内容占满本页，另配有下拉滑块，当列表下拉时，刷新继续加载本本信息，内容为准确信息。
@@@@@要求2：调整更新管理标签页，节点标签页：列表“本地版本”：仅显示其提交ID。如“heads/main-0-gda254b7”显示为“gda254b7”
@@@@@要求3：调整更新管理标签页，节点标签页：列表“版本”：显示其仓库地址当前的提交ID和更新日期
@@@@@要求4：错误分析标签页：“API接口”填入框及“API密匙”填入框填入信息后配置自动保存且“诊断”按钮可运行。
@@@@@另附当前代码后台日志：
##20250424-4
在以下当前代码基础上迭代修改：
@@@@@要求1：
优化启动速度。将更新管理页签的耗时 Git操作（获取本体和节点列表）在单独的线程中执行，避免阻塞主界面（其中，对于本地节点列表的显示可以优先加载）。且主界面”运行“任务不必等git操作完成。
@@@@@要求2：
调整更新管理标签页，本体标签页：列表可展示版本内容占满本页，另配有下拉滑块，当列表下拉时，继续加载本体信息，否则不加载。加载的本体信息内容为准确信息。
@@@@@要求3：
调整更新管理标签页，本体标签页：选中版本后，点击“激活选中版本”则更新当前comfyui本体为对应版本。
@@@@@要求4：
调整更新管理标签页，节点标签页：列表默认显示为当前ComfyUI\custom_nodes内全部节点。要求全部展示，显示不足可以下拉滑块显示。当其搜索框有文字执行搜索后，才显示已安装和未安装的节点。列表“本地版本”名称改为“本地ID”：仅完整显示其提交ID；列表“版本”改为"仓库ID"：显示其仓库地址当前的完整提交ID和更新日期。
@@@@@要求5：
调整更新管理标签页，节点标签页："切换/安装选择版本"更名为"切换版本"，在"切换版本"右侧，增加"卸载节点"和"更新全部"按钮，点击后可匹配仓库提交ID更新当前本地节点。点击切换版本后，单独线程获取该节点的过往版本ID、对应的描述信息以及更新日期，以单独弹窗显示，窗口名称为"切换版本"。该窗口内，选择对应版本后则更新节点。

@@@@@当前代码：

@@@@@另附当前代码后台日志：

```

