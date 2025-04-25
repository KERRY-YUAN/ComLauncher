# -*- coding: utf-8 -*-
# File: launcher.py
# Version: Kerry, Ver. 2.5.0 (Threaded Updates, Enhanced Node List, Update All, Node Uninstall/Switch History)

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, font as tkfont, filedialog, Toplevel # Import Toplevel for modal window
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
import shutil # Added for directory removal (uninstall)

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
# REQUIREMENT 4: Updated Default Node Config URL
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
# Updated version info for ComLauncher
VERSION_INFO = "ComLauncher, Ver. 2.5.0"


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
        # Store fetched node history for the modal
        self._node_history_modal_data = []
        self._node_history_modal_node_name = ""


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
        # New Treeview styles for Node History Modal
        self.style.configure('NodeHistory.Treeview', background=TEXT_AREA_BG, foreground=FG_STDOUT, fieldbackground=TEXT_AREA_BG, rowheight=22);
        self.style.configure('NodeHistory.Treeview.Heading', font=(FONT_FAMILY_UI, FONT_SIZE_NORMAL, 'bold'), background=CONTROL_FRAME_BG, foreground=FG_COLOR);
        self.style.map('NodeHistory.Treeview', background=[('selected', ACCENT_ACTIVE)], foreground=[('selected', 'white')])


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
        self.update_frame = ttk.Frame(self.notebook, padding="15", style='TFrame'); self.update_frame.columnconfigure(0, weight=1); self.update_frame.rowconfigure(1, weight=1) # Make bottom area (Version & Node Management) expandable
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
        # REQUIREMENT 5: Renamed "切换/安装选择版本" to "切换版本"
        self.switch_install_node_button = ttk.Button(nodes_control_frame, text="切换版本", style="TabAccent.TButton", command=self._queue_node_switch_install); # Call the queueing method
        self.switch_install_node_button.pack(side=tk.LEFT, padx=5)
        # REQUIREMENT 5: Add "卸载节点" button
        self.uninstall_node_button = ttk.Button(nodes_control_frame, text="卸载节点", style="TabAccent.TButton", command=self._queue_node_uninstall) # Call the queueing method
        self.uninstall_node_button.pack(side=tk.LEFT, padx=5)
        # REQUIREMENT 5: Add "更新全部" button
        self.update_all_nodes_button = ttk.Button(nodes_control_frame, text="更新全部", style="TabAccent.TButton", command=self._queue_all_nodes_update) # Call the queueing method
        self.update_all_nodes_button.pack(side=tk.LEFT, padx=5)


        # Hint Label - Updated text (Requirement 4)
        ttk.Label(self.nodes_frame, text="列表默认显示本地 custom_nodes 目录下的全部节点。搜索时显示匹配的本地/在线节点。", style='Hint.TLabel').grid(row=1, column=0, sticky=tk.W, padx=5, pady=(0, 5), columnspan=2) # Span hint across columns


        # REQUIREMENT 4: Nodes List (Treeview) with Scrollbar and new column formatting
        # Updated columns and headings for Requirement 4 "节点标签页"
        # Changed "local_version" to "本地ID" and "version" to "仓库ID"
        self.nodes_tree = ttk.Treeview(self.nodes_frame, columns=("name", "status", "local_id", "repo_info", "repo_url"), show="headings", style='Treeview')
        self.nodes_tree.heading("name", text="节点名称");
        self.nodes_tree.heading("status", text="状态");
        # REQUIREMENT 4: Renamed heading
        self.nodes_tree.heading("local_id", text="本地ID");
        # REQUIREMENT 4: Renamed heading and content changed
        self.nodes_tree.heading("repo_info", text="仓库信息");
        self.nodes_tree.heading("repo_url", text="仓库地址")
        # Adjust column widths slightly
        self.nodes_tree.column("name", width=200, stretch=tk.YES); # Allow name to take more space
        self.nodes_tree.column("status", width=80, stretch=tk.NO);
        # REQUIREMENT 4: Width for local ID (short commit hash)
        self.nodes_tree.column("local_id", width=100, stretch=tk.NO);
        # REQUIREMENT 4: Increased width for remote info
        self.nodes_tree.column("repo_info", width=180, stretch=tk.NO);
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

        # Bind search entry to trigger refresh (Requirement 4)
        self.nodes_search_entry.bind("<KeyRelease>", lambda event: self._queue_node_list_refresh()) # Queue refresh task
        # Bind selection event to update switch/install and uninstall button states (Requirement 5)
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
        # Added tags for Git outputs
        elif "[Git stdout]" in source_tag:
             tag = "stdout"
        elif "[Git stderr]" in source_tag:
             tag = "stderr"
        # Added tags for Fix script outputs
        elif "[Fix stdout]" in source_tag:
             tag = "stdout"
        elif "[Fix stderr]" in source_tag:
             tag = "stderr"


        text_widget.insert(tk.END, line, (tag,));
        if text_widget.yview()[1] > 0.95:
             text_widget.see(tk.END)
        text_widget.config(state=tk.DISABLED)

    def log_to_gui(self, target, message, tag="info"):
         """Adds a message to the appropriate output queue."""
         if not message.endswith('\n'): message += '\n'
         # Route all standard output (ComfyUI, Launcher, Git, Fix) to main_output_text queue
         if target in ("ComfyUI", "Launcher", "Git", "Update", "Fix"): # Added Fix tag
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
        # marker_sent is managed by self.comfyui_ready_marker_sent now

        api_port = self.config.get("comfyui_api_port", DEFAULT_COMFYUI_API_PORT)
        ready_str1 = f"Set up connection listening on:" # Match exact strings from ComfyUI startup
        ready_str2 = f"To see the GUI go to: http://127.0.0.1:{api_port}"
        ready_str3 = f"Uvicorn running on http://127.0.0.1:{api_port}"
        ready_strings = [ready_str1, ready_str2, ready_str3]

        try:
            for line in iter(process_stream.readline, ''): # Read lines until empty string is returned (pipe closed)
                if self.stop_event.is_set():
                    # This loop handles multiple stream sources (ComfyUI, Git, Fix).
                    # The stop_event should signal all reader threads.
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
        # The flag is set/cleared by the _update_task_worker
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
            # Use shlex.quote for robust quoting
            cmd_log_list = [shlex.quote(arg) for arg in comfyui_cmd_list]
            cmd_log_str = ' '.join(cmd_log_list)


            self.log_to_gui("ComfyUI", f"最终参数 / Final Arguments: {' '.join(self.comfyui_base_args)}")
            self.log_to_gui("ComfyUI", f"完整命令 / Full Command: {cmd_log_str}", "cmd")

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
             self.log_to_gui("Git", err_msg, "error") # Log Git path error
             return "", err_msg, 127 # Indicate error if git path is bad

        # Prepend the git executable to the command list
        full_cmd = [git_exe] + command_list

        # Use a copy of the environment and ensure PYTHONIOENCODING is set for subprocesses launched by git
        git_env = os.environ.copy()
        git_env['PYTHONIOENCODING'] = 'utf-8'

        # Ensure cwd exists
        if not os.path.isdir(cwd):
             err_msg = f"Git 命令工作目录不存在或无效: {cwd}"
             self.log_to_gui("Git", err_msg, "error")
             return "", err_msg, 1 # Generic error code

        try:
            # Log the command being executed
            # Safely quote arguments containing spaces or special characters
            cmd_log_list = [shlex.quote(arg) for arg in full_cmd]
            cmd_log_str = ' '.join(cmd_log_list)

            self.log_to_gui("Git", f"执行: {cmd_log_str}", "cmd")
            self.log_to_gui("Git", f"工作目录: {cwd}", "cmd")


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
            def read_pipe_and_buffer(pipe, buffer, source_name):
                 try:
                      for line in iter(pipe.readline, ''):
                           self.log_to_gui("Git", line.strip(), source_name) # Log to GUI (strip newline for log_to_gui)
                           buffer.append(line) # Append with newline for accurate reconstruction
                 except Exception as e:
                      print(f"[Launcher ERROR] Error reading pipe from {source_name} (capture): {e}")
                 finally:
                      try: pipe.close()
                      except Exception: pass

            stdout_thread = threading.Thread(target=read_pipe_and_buffer, args=(process.stdout, stdout_buffer, "[Git stdout]"), daemon=True)
            stderr_thread = threading.Thread(target=read_pipe_and_buffer, args=(process.stderr, stderr_buffer, "[Git stderr]"), daemon=True)

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
            # This case is handled by the initial git_exe path check
            # Kept here as a safeguard
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
                self.log_to_gui("Launcher", f"执行更新任务: {task_func.__name__}", "info")


                try:
                    # Execute the task function
                    task_func(*task_args, **task_kwargs)
                except threading.ThreadExit:
                     # Handle specific ThreadExit exception for graceful stop
                     self.log_to_gui("Launcher", f"更新任务 '{task_func.__name__}' 被取消。", "warn")
                except Exception as e:
                    print(f"[Launcher ERROR] Update task '{task_func.__name__}' failed: {e}", exc_info=True)
                    self.log_to_gui("Launcher", f"更新任务 '{task_func.__name__}' 执行失败: {e}", "error")
                    # Show error box in GUI thread
                    self.root.after(0, lambda msg=str(e): messagebox.showerror("更新任务失败 / Update Task Failed", f"更新任务执行失败:\n{msg}", parent=self.root))

                finally:
                    self.update_task_queue.task_done() # Mark task as done
                    self._update_task_running = False # Clear flag
                    self.stop_event.clear() # Reset stop event for the next task
                    self.log_to_gui("Launcher", f"更新任务 '{task_func.__name__}' 完成。", "info")
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
        # Validate Git path before queuing Git tasks
        if not self._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=True):
             self.log_to_gui("Update", "无法刷新本体版本: Git 路径配置无效。", "error")
             return

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
             self._update_ui_state() # Ensure UI state updates on error
             return

        # Get the displayed short ID from the Treeview (column index 1)
        selected_commit_id_short = version_data[1]
        selected_version_display = version_data[0] # Version type@name


        # Find the full commit ID from the stored remote_main_body_versions
        full_commit_id = None
        for ver in self.remote_main_body_versions:
            if ver["commit_id"].startswith(selected_commit_id_short):
                 full_commit_id = ver["commit_id"]
                 break

        if not full_commit_id:
             # Fallback: If for some reason the short ID isn't found in stored data,
             # try to get the full ID from the short one using git rev-parse HEAD
             comfyui_dir = self.comfyui_dir_var.get()
             if comfyui_dir and os.path.isdir(comfyui_dir) and os.path.isdir(os.path.join(comfyui_dir, ".git")) and self._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=False):
                  # Need to run this check in the worker thread potentially? No, just validate paths here.
                  # Getting the full ID from short via git is a quick operation usually, could do it here or queue.
                  # Let's queue it as part of the activation task to keep UI responsive during path validation too.
                  # Or, better, just queue the task with the *short* ID and let the task resolve the full ID.
                  # This makes the queuing part faster.

                  # Re-design: Pass short ID and let the task resolve full ID if needed.
                  pass # Full ID resolution moved to task

        # Validate paths before proceeding with the task
        if not self._validate_paths_for_execution(check_comfyui=True, check_git=True, show_error=True):
             self.log_to_gui("Update", "无法激活本体版本: 路径配置无效。", "error")
             return
        # Check if the ComfyUI dir is a git repo
        comfyui_dir = self.comfyui_dir_var.get()
        if not os.path.isdir(comfyui_dir) or not os.path.isdir(os.path.join(comfyui_dir, ".git")):
             self.log_to_gui("Update", f"'{comfyui_dir}' 不是一个 Git 仓库，无法激活版本。", "error")
             messagebox.showerror("Git 仓库错误 / Git Repository Error", f"ComfyUI 安装目录不是一个有效的 Git 仓库:\n{comfyui_dir}\n请确保该目录是 Git 克隆的。", parent=self.root)
             self._update_ui_state() # Ensure UI updates after error
             return

        # Confirm activation
        confirm = messagebox.askyesno("确认激活 / Confirm Activation", f"确定要下载并覆盖安装本体版本 '{selected_version_display}' (提交ID: {selected_commit_id_short}) 吗？\n此操作会修改 '{comfyui_dir}' 目录。\n\n警告: 激活不同版本可能导致当前节点不兼容，请谨慎操作！", parent=self.root)
        if not confirm: return

        self.log_to_gui("Launcher", f"将激活本体版本 '{selected_version_display}' (提交ID: {selected_commit_id_short}) 任务添加到队列...", "info")
        # Queue the activation task, passing the short commit ID
        self.update_task_queue.put((self._activate_main_body_version_task, [comfyui_dir, selected_commit_id_short], {}))
        self.root.after(0, self._update_ui_state) # Update UI state immediately


    def _queue_node_list_refresh(self):
        """Queues the node list refresh task."""
        # We need git path to get remote info, but local scan works without it.
        # Let's queue the task and let the task handle partial refresh if git is missing.
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中，无法刷新节点列表。", "warn"); return

        self.log_to_gui("Launcher", "将刷新节点列表任务添加到队列...", "info")
        self.update_task_queue.put((self.refresh_node_list, [], {})) # Add task to queue
        self.root.after(0, self._update_ui_state) # Update UI state immediately


    def _queue_node_switch_install(self):
        """Queues the node switch/install task or node history fetch task."""
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中，无法切换/安装节点。", "warn"); return

        selected_item = self.nodes_tree.focus()
        if not selected_item:
            messagebox.showwarning("未选择节点 / No Node Selected", "请从列表中选择一个要操作的节点。", parent=self.root)
            return

        # Get data from the 5-column treeview item
        # Columns: ("name", "status", "local_id", "repo_info", "repo_url")
        node_data = self.nodes_tree.item(selected_item, 'values')
        if not node_data or len(node_data) < 5:
             self.log_to_gui("Update", "无法获取选中的节点数据。", "error")
             messagebox.showerror("数据错误", "无法获取选中的节点数据，请刷新列表。", parent=self.root)
             self._update_ui_state() # Ensure UI updates on error
             return

        node_name = node_data[0]
        node_status = node_data[1]
        # local_id = node_data[2] # Short local commit ID
        repo_info = node_data[3] # Remote info string
        repo_url = node_data[4] # Repo URL

        comfyui_nodes_dir = self.comfyui_nodes_dir

        # Validate paths before proceeding
        if not self._validate_paths_for_execution(check_comfyui=True, check_git=True, show_error=True):
             self.log_to_gui("Update", "无法切换/安装节点: 路径配置无效。", "error")
             return
        # Ensure nodes directory exists before attempting git operations within it
        if not comfyui_nodes_dir or not os.path.isdir(comfyui_nodes_dir):
             self.log_to_gui("Update", f"无法切换/安装节点: ComfyUI custom_nodes 目录未找到或无效 ({comfyui_nodes_dir})。", "error")
             messagebox.showerror("目录错误 / Directory Error", f"ComfyUI custom_nodes 目录未找到或无效:\n{comfyui_nodes_dir}\n请检查设置中的 ComfyUI 安装目录。", parent=self.root)
             self._update_ui_state() # Ensure UI updates on error
             return

        # Cannot install/switch if no valid repo URL is known
        if not repo_url or repo_url in ("本地安装，无Git信息", "无法获取远程 URL", "本地安装", "N/A"):
             self.log_to_gui("Update", f"无法切换/安装节点 '{node_name}': 该节点无有效的仓库地址信息。", "error")
             messagebox.showerror("节点信息缺失 / Missing Node Info", f"节点 '{node_name}' 无有效的仓库地址，无法进行版本切换或安装。", parent=self.root)
             self._update_ui_state() # Ensure UI updates on error
             return

        # Determine the node's expected installation path based on repo URL
        # This derivation needs to be consistent with how _refresh_node_list finds installed nodes.
        # It's usually the last segment of the repo URL without .git
        repo_name_from_url = repo_url.split('/')[-1]
        if repo_name_from_url.lower().endswith('.git'):
             repo_name_from_url = repo_name_from_url[:-4]
        node_install_path = os.path.normpath(os.path.join(comfyui_nodes_dir, repo_name_from_url))

        # Check if the node directory exists and is a git repo to determine status precisely
        # Relying on the treeview status is generally fine, but double-checking here is safer.
        is_installed_and_git = os.path.isdir(node_install_path) and os.path.isdir(os.path.join(node_install_path, ".git"))

        if not is_installed_and_git:
             # --- Node is not installed or not a git repo (e.g. manually copied) ---
             # Treat as an installation scenario (clone)
             action = "安装"
             # Determine the target branch/version for installation from the online config info (repo_info)
             # This is the part before " (未安装)" or " (信息获取失败)"
             target_ref_for_install = repo_info.split(' ')[0].strip()
             if target_ref_for_install in ("未知远程", "N/A", "信息获取失败", "未安装"):
                 # Fallback to a default branch if online info is not useful
                 target_ref_for_install = "main" # Or "master"
                 self.log_to_gui("Update", f"无法解析安装目标引用 '{repo_info}'，使用默认目标分支 '{target_ref_for_install}' 进行克隆。", "warn")

             confirm_msg = f"确定要安装节点 '{node_name}' 吗？\n" \
                           f"仓库地址: {repo_url}\n" \
                           f"克隆分支: {target_ref_for_install}\n" \
                           f"目标目录: {node_install_path}\n\n" \
                           f"此操作将在 custom_nodes 目录下克隆仓库。\n确认前请确保 ComfyUI 已停止运行。"

             confirm = messagebox.askyesno("确认安装 / Confirm Installation", confirm_msg, parent=self.root)
             if not confirm: return

             self.log_to_gui("Launcher", f"将安装节点 '{node_name}' (目标引用: {target_ref_for_install}) 任务添加到队列...", "info")
             # Queue the installation task (_switch_install_node_task handles both clone and checkout/pull)
             # Pass the target ref to the task
             self.update_task_queue.put((self._switch_install_node_task, [node_name, node_install_path, repo_url, target_ref_for_install], {}))

        else:
             # --- Node is installed and is a Git repo ---
             # Show the version history modal (Requirement 5)
             action = "切换版本"
             confirm_msg = f"确定要获取节点 '{node_name}' 的版本历史并切换吗？\n\n此操作将获取仓库 '{repo_url}' 的版本信息。"
             confirm = messagebox.askyesno("确认切换版本 / Confirm Switch Version", confirm_msg, parent=self.root)
             if not confirm: return

             self.log_to_gui("Launcher", f"将获取节点 '{node_name}' 版本历史任务添加到队列...", "info")
             # Queue the task to fetch history, which will then show the modal
             self.update_task_queue.put((self._queue_node_history_fetch, [node_name, node_install_path], {}))


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
        # Use the self.local_nodes_only list which contains detailed info from the last refresh
        nodes_to_update = [
            node for node in self.local_nodes_only
            if node.get("is_git") and node.get("repo_url") and node.get("repo_url") not in ("本地安装，无Git信息", "无法获取远程 URL", "本地安装", "N/A")
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

    # REQUIREMENT 5: Queue Uninstall Node Task
    def _queue_node_uninstall(self):
        """Queues the node uninstall task."""
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中，无法卸载节点。", "warn"); return

        selected_item = self.nodes_tree.focus()
        if not selected_item:
            messagebox.showwarning("未选择节点 / No Node Selected", "请从列表中选择一个要卸载的节点。", parent=self.root)
            return

        node_data = self.nodes_tree.item(selected_item, 'values')
        if not node_data or len(node_data) < 5:
             self.log_to_gui("Update", "无法获取选中的节点数据。", "error")
             messagebox.showerror("数据错误", "无法获取选中的节点数据，请刷新列表。", parent=self.root)
             self._update_ui_state() # Ensure UI updates on error
             return

        node_name = node_data[0]
        node_status = node_data[1]

        # Can only uninstall "已安装" nodes
        if node_status != "已安装":
             self.log_to_gui("Update", f"节点 '{node_name}' 未安装，无需卸载。", "warn")
             messagebox.showwarning("节点未安装 / Node Not Installed", f"节点 '{node_name}' 未安装。", parent=self.root)
             return

        comfyui_nodes_dir = self.comfyui_nodes_dir
        node_install_path = os.path.normpath(os.path.join(comfyui_nodes_dir, node_name)) # Derive path

        # Validate path
        if not os.path.isdir(node_install_path):
             self.log_to_gui("Update", f"节点目录不存在或无效: {node_install_path}", "error")
             messagebox.showerror("目录错误 / Directory Error", f"节点目录不存在或无效:\n{node_install_path}", parent=self.root)
             self._update_ui_state()
             return

        confirm = messagebox.askyesno(
             "确认卸载节点 / Confirm Uninstall Node",
             f"确定要永久删除节点 '{node_name}' 及其目录 '{node_install_path}' 吗？\n此操作不可撤销。\n\n确认前请确保 ComfyUI 已停止运行。",
             parent=self.root
        )
        if not confirm: return

        self.log_to_gui("Launcher", f"将卸载节点 '{node_name}' 任务添加到队列...", "info")
        # Queue the uninstall task
        self.update_task_queue.put((self._node_uninstall_task, [node_name, node_install_path], {}))
        self.root.after(0, self._update_ui_state) # Update UI state immediately


    # --- Initial Data Loading Task (Requirement 1) ---
    def start_initial_data_load(self):
         """Starts the initial data loading tasks (main body versions, nodes) in a background thread."""
         if self._is_update_task_running():
              print("[Launcher INFO] Initial data load skipped, an update task is already running.")
              return

         self.log_to_gui("Launcher", "开始加载更新管理数据...", "info")
         # Queue the initial background task runner
         self.update_task_queue.put((self._run_initial_background_tasks, [], {}))
         self.root.after(0, self._update_ui_state) # Update UI to show busy state


    def _run_initial_background_tasks(self):
         """Executes the initial data loading tasks. Runs in worker thread."""
         self.log_to_gui("Launcher", "执行后台数据加载 (本体版本和节点列表)...", "info")
         # Ensure Git path is valid before attempting Git operations
         git_path_ok = self._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=False)

         if not git_path_ok:
             self.log_to_gui("Launcher", "Git 路径无效，本体版本列表加载将受限。", "warn")
             # Node list refresh will still run and show local non-git nodes.
             pass # Continue to node list refresh


         # Refresh main body versions first (will only work fully if git_path_ok)
         self.refresh_main_body_versions() # This is now running in the worker thread

         # Check for stop event after main body refresh
         if self.stop_event.is_set():
              self.log_to_gui("Launcher", "后台数据加载任务已取消。", "warn"); return


         # Then refresh node list (will work partially or fully based on git_path_ok)
         self.refresh_node_list() # This is also running in the worker thread

         self.log_to_gui("Launcher", "后台数据加载完成。", "info")
         # UI state update is handled by the worker thread's finally block


    # REQUIREMENT 2: Accurate Main Body Versions (Modified to run in task queue)
    def refresh_main_body_versions(self):
        """Fetches and displays ComfyUI main body versions using Git. Runs in worker thread."""
        # Check for stop event
        if self.stop_event.is_set():
             self.log_to_gui("Update", "本体版本刷新任务已取消。", "warn"); return

        main_repo_url = self.main_repo_url_var.get()
        comfyui_dir = self.comfyui_dir_var.get()
        git_path_ok = self._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=False)

        # Clear existing list in the GUI thread
        self.root.after(0, lambda: [self.main_body_tree.delete(item) for item in self.main_body_tree.get_children()])
        self.remote_main_body_versions = [] # Clear stored data


        # --- Get Current Local Version ---
        local_version_display = "读取本地版本失败"
        if git_path_ok and comfyui_dir and os.path.isdir(comfyui_dir) and os.path.isdir(os.path.join(comfyui_dir, ".git")):
             stdout, stderr, returncode = self._run_git_command(["describe", "--all", "--long", "--always"], cwd=comfyui_dir, timeout=10)
             if returncode == 0 and stdout:
                  local_version_display = f"本地: {stdout.strip()}"
             else:
                  # Fallback to short commit hash if describe fails
                  stdout, stderr, returncode = self._run_git_command(["rev-parse", "HEAD"], cwd=comfyui_dir, timeout=10)
                  if returncode == 0 and stdout:
                      local_version_display = f"本地 Commit: {stdout.strip()[:8]}"
                  else:
                      self.log_to_gui("Update", f"无法获取本地本体版本信息: {stderr if stderr else '未知错误'}", "warn")
        else:
             if not git_path_ok: self.log_to_gui("Update", "Git 路径无效，无法获取本地本体版本信息。", "warn")
             elif not comfyui_dir or not os.path.isdir(comfyui_dir): self.log_to_gui("Update", f"ComfyUI 目录无效 ({comfyui_dir if comfyui_dir else '未配置'})，无法获取本地本体版本信息。", "warn")
             elif comfyui_dir and not os.path.isdir(os.path.join(comfyui_dir, ".git")): self.log_to_gui("Update", f"ComfyUI 目录 '{comfyui_dir}' 不是 Git 仓库，无法获取本地本体版本信息。", "warn")

        # Update current version label in GUI thread
        self.root.after(0, lambda lv=local_version_display: self.current_main_body_version_var.set(lv))


        # Check for stop event after getting local version
        if self.stop_event.is_set():
             self.log_to_gui("Update", "本体版本刷新任务已取消。", "warn"); return

        # --- Fetch Remote Versions (Only if Git path and repo are valid) ---
        all_versions = []
        if git_path_ok and comfyui_dir and os.path.isdir(comfyui_dir) and os.path.isdir(os.path.join(comfyui_dir, ".git")) and main_repo_url:

             self.log_to_gui("Update", f"尝试从 {main_repo_url} 刷新本体版本列表... / Attempting to refresh main body version list from {main_repo_url}...", "info")

             # Fetch latest info first
             self.log_to_gui("Update", "执行 Git fetch origin 获取远程信息...", "info")
             stdout, stderr, returncode = self._run_git_command(["fetch", "origin"], cwd=comfyui_dir, timeout=180) # Increased timeout
             if returncode != 0:
                  self.log_to_gui("Update", f"Git fetch 失败: {stderr if stderr else '未知错误'}", "error")
                  self.log_to_gui("Update", "无法获取远程本体版本列表。", "error")
                  # Add an entry to the treeview indicating failure
                  self.root.after(0, lambda: self.main_body_tree.insert("", tk.END, values=("获取失败", "", "", "无法获取远程版本信息，请检查Git路径和仓库地址。")))
                  return # Stop here if fetch failed
             self.log_to_gui("Update", "Git fetch 完成。", "info")

             # Check for stop event after fetch
             if self.stop_event.is_set():
                  self.log_to_gui("Update", "本体版本刷新任务已取消。", "warn"); return

             # Get list of remote branches with commit info
             # Format: '%(refname:short) %(objectname) %(committerdate:iso-strict) %(contents:subject)'
             branches_output, branch_err, branch_rc = self._run_git_command(
                  ["for-each-ref", "refs/remotes/origin/", "--sort=-committerdate", "--format=%(refname:short) %(objectname) %(committerdate:iso-strict) %(contents:subject)"],
                  cwd=comfyui_dir, timeout=60
             )
             # Get list of tags with commit info
             # Format: '%(refname:short) %(objectname) %(taggerdate:iso-strict) %(contents:subject)'
             tags_output, tag_err, tag_rc = self._run_git_command(
                  ["for-each-ref", "refs/tags/", "--sort=-taggerdate", "--format=%(refname:short) %(objectname) %(taggerdate:iso-strict) %(contents:subject)"],
                  cwd=comfyui_dir, timeout=60
             )

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
             elif branch_rc != 0:
                  self.log_to_gui("Update", f"获取远程分支列表失败: {branch_err if branch_err else '未知错误'}", "warn")

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
             elif tag_rc != 0:
                  self.log_to_gui("Update", f"获取远程标签列表失败: {tag_err if tag_err else '未知错误'}", "warn")

             # Sort versions, prioritize tags (newer tags first), then newer branches
             # Using date as the primary sort key descending, type 'tag' comes before 'branch' for same date
             all_versions.sort(key=lambda x: (x['date_iso'], x['type'] != 'tag'), reverse=True)

        else:
             if not main_repo_url: self.log_to_gui("Update", "本体仓库地址未设置，无法获取远程版本信息。", "warn")
             elif not git_path_ok: self.log_to_gui("Update", "Git 路径无效，无法获取远程本体版本信息。", "warn")
             elif not comfyui_dir or not os.path.isdir(comfyui_dir): self.log_to_gui("Update", f"ComfyUI 目录无效 ({comfyui_dir if comfyui_dir else '未配置'})，无法获取远程本体版本信息。", "warn")
             elif comfyui_dir and not os.path.isdir(os.path.join(comfyui_dir, ".git")): self.log_to_gui("Update", f"ComfyUI 目录 '{comfyui_dir}' 不是 Git 仓库，无法获取远程本体版本信息。", "warn")

             # Add an entry to the treeview indicating limited/no remote info
             self.root.after(0, lambda: self.main_body_tree.insert("", tk.END, values=("无远程版本信息", "", "", "请检查Git路径和仓库地址配置")))


        self.remote_main_body_versions = all_versions # Store for node version lookup

        if not all_versions and (git_path_ok and comfyui_dir and os.path.isdir(comfyui_dir) and os.path.isdir(os.path.join(comfyui_dir, ".git")) and main_repo_url):
             # Only log warning if git/repo is configured but no versions found
             self.log_to_gui("Update", "未从远程仓库获取到版本信息。", "warn")
             # Add an entry to the treeview indicating no versions found
             self.root.after(0, lambda: self.main_body_tree.insert("", tk.END, values=("无可用远程版本", "", "", "远程仓库未找到版本信息")))

        else:
             for ver_data in all_versions:
                 # Check for stop event during insertion
                 if self.stop_event.is_set():
                      self.log_to_gui("Update", "本体版本列表填充任务已取消。", "warn"); break # Stop inserting

                 version_display = f"{ver_data['type']}@{ver_data['name']}" # e.g., tag@v1.2.3, branch@main
                 commit_display = ver_data["commit_id"][:8]
                 # Format date to YYYY-MM-DD, handle potential parsing errors
                 try:
                      # Use fromisoformat for ISO 8601 date/time/timezone string
                      date_obj = datetime.fromisoformat(ver_data['date_iso'])
                      date_display = date_obj.strftime('%Y-%m-%d')
                 except ValueError:
                      self.log_to_gui("Update", f"本体版本日期解析失败: {ver_data['date_iso']}", "warn")
                      date_display = "无效日期"
                 description_display = ver_data["description"]

                 # Insert into Treeview in the GUI thread
                 self.root.after(0, lambda v=(version_display, commit_display, date_display, description_display): self.main_body_tree.insert("", tk.END, values=v))

        self.log_to_gui("Update", f"本体版本列表刷新完成 (共 {len(all_versions)} 条远程版本)。/ Main body version list refreshed ({len(all_versions)} remote items).", "info")
        # UI state update is handled by the worker thread's finally block

    # REQUIREMENT 3: Activate Main Body Version (Modified to run in task queue)
    # The queuing method _queue_main_body_activation is the entry point now.
    # The actual activation logic is in _activate_main_body_version_task
    def activate_main_body_version(self):
        """Activates the selected ComfyUI main body version. Queued for worker thread."""
        pass # Logic moved to _queue_main_body_activation


    def _activate_main_body_version_task(self, comfyui_dir, target_commit_id_short):
        """Task to execute git commands for activating main body version. Runs in worker thread."""
        # Check for stop event
        if self.stop_event.is_set():
             self.log_to_gui("Update", "本体版本激活任务已取消。", "warn"); return

        # Resolve full commit ID from short ID if necessary (safer to do in task)
        full_commit_id = None
        # First, check stored data
        for ver in self.remote_main_body_versions:
             if ver["commit_id"].startswith(target_commit_id_short):
                  full_commit_id = ver["commit_id"]
                  break

        # If not found in stored data, try git rev-parse (might be a local commit, or fetch missed it)
        if not full_commit_id:
             self.log_to_gui("Update", f"无法在缓存数据中找到短提交ID '{target_commit_id_short}'，尝试通过 git rev-parse 解析...", "info")
             stdout, stderr, returncode = self._run_git_command(["rev-parse", target_commit_id_short], cwd=comfyui_dir, timeout=5)
             if returncode == 0 and stdout:
                  full_commit_id = stdout.strip()
                  self.log_to_gui("Update", f"git rev-parse 解析到完整提交 ID: {full_commit_id[:8]}", "info")
             else:
                  self.log_to_gui("Update", f"无法解析提交ID '{target_commit_id_short}' 的完整ID: {stderr if stderr else '未知错误'}", "error")
                  # Show error box in GUI thread
                  self.root.after(0, lambda: messagebox.showerror("激活失败 / Activation Failed", f"无法解析要激活的提交ID '{target_commit_id_short}'。", parent=self.root))
                  return # Cannot proceed without a full commit ID


        self.log_to_gui("Update", f"正在激活本体版本 (提交ID: {full_commit_id[:8]})... / Activating main body version (Commit ID: {full_commit_id[:8]})...", "info")

        try:
            # 1. Ensure tracking remote is correct (Optional but good practice)
            # Check current origin URL
            # Use try-except for remote get-url as it might not exist
            current_origin_url = ""
            try:
                 stdout, stderr, returncode = self._run_git_command(["remote", "get-url", "origin"], cwd=comfyui_dir, timeout=10)
                 if returncode == 0: current_origin_url = stdout.strip()
                 else: self.log_to_gui("Update", f"无法获取当前远程 origin URL: {stderr.strip() if stderr else '未知错误'}", "warn")
            except Exception as e: self.log_to_gui("Update", f"获取当前远程 origin URL 异常: {e}", "warn")

            configured_origin_url = self.main_repo_url_var.get().strip()

            if not current_origin_url or current_origin_url != configured_origin_url:
                 self.log_to_gui("Update", f"远程 origin URL 不匹配或无法获取 ({current_origin_url} vs {configured_origin_url})，尝试设置...", "warn")
                 # Check if origin remote exists first
                 stdout, stderr, returncode = self._run_git_command(["remote", "get-url", "origin"], cwd=comfyui_dir, timeout=5)
                 if returncode == 0: # origin exists, just set URL
                      self.log_to_gui("Update", f"执行 git remote set-url origin {configured_origin_url}...", "info")
                      stdout, stderr, returncode = self._run_git_command(["remote", "set-url", "origin", configured_origin_url], cwd=comfyui_dir, timeout=10)
                 else: # origin does not exist, add it
                      self.log_to_gui("Update", f"执行 git remote add origin {configured_origin_url}...", "info")
                      stdout, stderr, returncode = self._run_git_command(["remote", "add", "origin", configured_origin_url], cwd=comfyui_dir, timeout=10)

                 if returncode != 0:
                      self.log_to_gui("Update", f"设置远程 URL 失败: {stderr if stderr else '未知错误'}", "error")
                      raise Exception("设置远程 URL 失败")
                 self.log_to_gui("Update", "远程 origin URL 已更新/添加。", "info")

            # Check for stop event
            if self.stop_event.is_set(): raise threading.ThreadExit # Use ThreadExit to signal cancel

            # 2. Fetch latest changes to ensure target commit is available locally
            self.log_to_gui("Update", "执行 Git fetch origin...", "info")
            stdout, stderr, returncode = self._run_git_command(["fetch", "origin"], cwd=comfyui_dir, timeout=180) # Increased timeout
            if returncode != 0:
                 self.log_to_gui("Update", f"Git fetch 失败: {stderr if stderr else '未知错误'}", "error")
                 raise Exception("Git fetch 失败")
            self.log_to_gui("Update", "Git fetch 完成。", "info")

            # Check for stop event
            if self.stop_event.is_set(): raise threading.ThreadExit

            # 3. Reset local changes and checkout target commit
            # Check if there are local changes before hard reset (optional, but good practice)
            stdout_status, stderr_status, returncode_status = self._run_git_command(["status", "--porcelain"], cwd=comfyui_dir, timeout=10)
            if returncode_status == 0 and stdout_status.strip():
                 self.log_to_gui("Update", "检测到本体目录存在未提交的本地修改。", "warn")
                 # Decide whether to block or proceed with warning
                 # For reset --hard, it will discard local changes. User was warned in messagebox. Proceed.


            self.log_to_gui("Update", f"执行 Git reset --hard {full_commit_id[:8]}...", "info")
            stdout, stderr, returncode = self._run_git_command(["reset", "--hard", full_commit_id], cwd=comfyui_dir, timeout=60)
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
                 stdout, stderr, returncode = self._run_git_command(["submodule", "update", "--init", "--recursive", "--force"], cwd=comfyui_dir, timeout=180) # Added --force for robustness
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
                 # Use --break-system-packages if needed for system python (warn user?)
                 if platform.system() != "Windows": # Assume venv is less common on Windows portable
                      # Check if running in a venv by comparing python_exe with sys.executable
                      # Simple check: if sys.prefix is not sys.base_prefix, it's likely a venv
                      if sys.prefix == sys.base_prefix:
                           # Not in a venv, might need --break-system-packages or --user
                           # Prompt user or assume --user? --user is safer usually.
                           pip_cmd.append("--user")
                           self.log_to_gui("Update", "未检测到Python虚拟环境，使用 --user 选项安装依赖。", "warn")
                      # else: In a venv, no extra flags needed


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
            self.log_to_gui("Update", f"本体版本激活流程完成 (提交ID: {full_commit_id[:8]})。", "info")
            self.root.after(0, lambda: messagebox.showinfo("激活完成 / Activation Complete", f"本体版本已激活到提交: {full_commit_id[:8]}", parent=self.root))

        except threading.ThreadExit:
             self.log_to_gui("Update", "本体版本激活任务已取消。", "warn")
        except Exception as e:
            error_msg = f"本体版本激活流程失败: {e}"
            self.log_to_gui("Update", error_msg, "error")
            self.root.after(0, lambda msg=str(e): messagebox.showerror("激活失败 / Activation Failed", msg, parent=self.root))
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

        # Get search term from UI variable (safe to access directly in worker thread)
        search_term_value = self.nodes_search_entry.get().strip().lower() if hasattr(self, 'nodes_search_entry') and self.nodes_search_entry.winfo_exists() else ""


        git_path_ok = self._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=False)
        is_comfyui_nodes_dir_valid = comfyui_nodes_dir and os.path.isdir(comfyui_nodes_dir)


        # --- Scan Local custom_nodes directory ---
        self.local_nodes_only = [] # Reset the list of local nodes
        if is_comfyui_nodes_dir_valid:
             self.log_to_gui("Update", f"扫描本地 custom_nodes 目录: {comfyui_nodes_dir}...", "info")
             # Check for stop event before listing directory
             if self.stop_event.is_set(): raise threading.ThreadExit

             try:
                  # List items and sort by name
                  item_names = sorted(os.listdir(comfyui_nodes_dir))
                  for item_name in item_names:
                       # Check for stop event during directory listing
                       if self.stop_event.is_set(): raise threading.ThreadExit

                       item_path = os.path.join(comfyui_nodes_dir, item_name)
                       if os.path.isdir(item_path):
                            node_info = {"name": item_name, "status": "已安装"}
                            node_info["local_id"] = "N/A" # Default for non-git or error
                            node_info["repo_info"] = "N/A" # Default for non-git or error
                            node_info["repo_url"] = "本地安装" # Default
                            node_info["is_git"] = False # Default

                            # Try to get Git info if Git executable is available and it's a git repo
                            if git_path_ok and os.path.isdir(os.path.join(item_path, ".git")):
                                 node_info["is_git"] = True

                                 # REQUIREMENT 4: Get Local ID (short commit hash)
                                 stdout_id, stderr_id, returncode_id = self._run_git_command(["rev-parse", "--short", "HEAD"], cwd=item_path, timeout=5)
                                 if returncode_id == 0 and stdout_id:
                                      node_info["local_id"] = stdout_id.strip()
                                 else:
                                      self.log_to_gui("Update", f"无法获取节点 '{item_name}' 的本地Commit ID: {stderr_id.strip() if stderr_id else '未知错误'}", "warn")

                                 # REQUIREMENT 4: Get Remote Info ("仓库信息": Remote ID + Date or branch name)
                                 repo_info_display = "无远程跟踪分支" # Default if no upstream
                                 remote_branch_name = "N/A"
                                 remote_commit_id_short = "N/A"
                                 remote_commit_date = "N/A"
                                 repo_url_str = "无法获取远程 URL"

                                 # Try to get the upstream tracking branch
                                 stdout_upstream, stderr_upstream, returncode_upstream = self._run_git_command(["rev-parse", "--abbrev-ref", "@{u}"], cwd=item_path, timeout=5)
                                 if returncode_upstream == 0 and stdout_upstream:
                                      upstream_ref = stdout_upstream.strip() # e.g., origin/main
                                      # Handle cases like HEAD is already on the upstream
                                      if upstream_ref == "HEAD":
                                           repo_info_display = "HEAD (无跟踪分支)"
                                      elif upstream_ref.startswith("origin/"):
                                           remote_branch_name = upstream_ref.replace("origin/", "") # Get just the branch name

                                           # Get remote branch HEAD commit ID and Date
                                           log_cmd = ["log", "-1", "--format=%H %ci", upstream_ref]
                                           stdout_log, stderr_log, returncode_log = self._run_git_command(log_cmd, cwd=item_path, timeout=10)

                                           if returncode_log == 0 and stdout_log:
                                                log_parts = stdout_log.strip().split(' ', 1)
                                                if len(log_parts) == 2:
                                                     full_commit_id_remote = log_parts[0] # Full remote commit ID
                                                     date_iso = log_parts[1]
                                                     remote_commit_id_short = full_commit_id_remote[:8]
                                                     try:
                                                          # Use fromisoformat for ISO 8601
                                                          date_obj = datetime.fromisoformat(date_iso)
                                                          remote_commit_date = date_obj.strftime('%Y-%m-%d')
                                                     except ValueError:
                                                          self.log_to_gui("Update", f"节点 '{item_name}' 远程分支 '{remote_branch_name}' 日期解析失败: {date_iso}", "warn")
                                                          remote_commit_date = "无效日期"

                                                     # Format: commit_id (date)
                                                     repo_info_display = f"{remote_commit_id_short} ({remote_commit_date})"
                                                     # Store full remote commit ID and branch for update logic
                                                     node_info["remote_commit_id"] = full_commit_id_remote
                                                     node_info["remote_branch"] = remote_branch_name

                                                else:
                                                     self.log_to_gui("Update", f"无法解析节点 '{item_name}' 远程分支 '{remote_branch_name}' 的日志格式: {stdout_log.strip()}", "warn")
                                                     repo_info_display = f"{remote_branch_name} (日志解析失败)"

                                           else:
                                                self.log_to_gui("Update", f"无法获取节点 '{item_name}' 远程分支 '{remote_branch_name}' 的最新提交信息: {stderr_log.strip() if stderr_log else '未知错误'}", "warn")
                                                repo_info_display = f"{remote_branch_name} (信息获取失败)"

                                      # Handle other upstream types like tags if necessary, but common is origin/branch
                                      else:
                                          self.log_to_gui("Update", f"节点 '{item_name}' 远程跟踪分支 '{upstream_ref}' 格式未知。", "warn")
                                          repo_info_display = f"跟踪: {upstream_ref} (未知格式)"


                                 elif "no upstream configured" not in (stderr_upstream.lower() if stderr_upstream else "") and \
                                      "no upstream branch" not in (stderr_upstream.lower() if stderr_upstream else "") and \
                                      returncode_upstream != 0:
                                      self.log_to_gui("Update", f"无法获取节点 '{item_name}' 的远程跟踪分支信息: {stderr_upstream.strip() if stderr_upstream else '未知错误'}", "warn")
                                      repo_info_display = "信息获取失败"

                                 # Get Remote URL
                                 stdout_url, stderr_url, returncode_url = self._run_git_command(["remote", "get-url", "origin"], cwd=item_path, timeout=5)
                                 if returncode_url == 0 and stdout_url:
                                      repo_url_str = stdout_url.strip()
                                 elif returncode_url != 0 and "no such remote" not in (stderr_url.lower() if stderr_url else ""):
                                     self.log_to_gui("Update", f"无法获取节点 '{item_name}' 的远程URL: {stderr_url.strip() if stderr_url else '未知错误'}", "warn")


                                 node_info["repo_info"] = repo_info_display
                                 node_info["repo_url"] = repo_url_str


                            else: # Not a git repo or git path invalid
                                 node_info["local_id"] = "N/A" # Non-git nodes have no local ID
                                 node_info["repo_info"] = "N/A" # Non-git nodes have no remote info
                                 node_info["repo_url"] = "本地安装"

                            self.local_nodes_only.append(node_info)

                  self.log_to_gui("Update", f"本地 custom_nodes 目录扫描完成，找到 {len(self.local_nodes_only)} 个节点。", "info")

             except threading.ThreadExit:
                  self.log_to_gui("Update", "节点列表扫描任务已取消。", "warn"); return
             except Exception as e:
                  self.log_to_gui("Update", f"扫描本地 custom_nodes 目录时出错: {e}", "error")
                  # Add entry indicating local scan failure
                  self.root.after(0, lambda: self.nodes_tree.insert("", tk.END, values=("扫描失败", "错误", "N/A", "扫描本地目录时出错", "N/A")))


        else:
             if not is_comfyui_nodes_dir_valid:
                 self.log_to_gui("Update", f"ComfyUI custom_nodes 目录未找到或无效 ({comfyui_nodes_dir if comfyui_nodes_dir else '未配置'})，跳过本地节点扫描。", "warn")
                 # Add entry indicating directory not found
                 self.root.after(0, lambda: self.nodes_tree.insert("", tk.END, values=("本地目录无效", "错误", "N/A", "custom_nodes 目录不存在或无效", "N/A")))
             # If git_path_ok is false, the git info part inside the loop won't run, but local scan still happens.
             # The warning about git path is logged separately.


        # Check for stop event
        if self.stop_event.is_set():
             self.log_to_gui("Update", "节点列表刷新任务已取消。", "warn"); return

        # --- Fetching Online Config Data ---
        simulated_online_nodes_config = []
        if node_config_url:
            simulated_online_nodes_config = self._fetch_online_node_config() # Call helper to get the config
        else:
            self.log_to_gui("Update", "节点配置地址未设置，跳过在线配置获取。", "warn")


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
             # Use branch or version from config, fallback to main
             version_ref = online_node.get('branch') or online_node.get('version') or 'main'
             description = online_node.get('description', '无描述')

             if node_name_lower not in local_node_dict_lower:
                  # Node is in online config but not found locally, add it as "未安装"
                  # For "仓库信息", just show the recommended branch/version + (未安装)
                  online_repo_info_display = f"{version_ref} (未安装)"

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
        self.all_known_nodes.sort(key=lambda x: x.get('name', '').lower())

        # Check for stop event
        if self.stop_event.is_set():
             self.log_to_gui("Update", "节点列表刷新任务已取消。", "warn"); return

        # --- Apply Filtering Logic and Populate Treeview ---
        filtered_nodes = []

        if search_term_value == "":
            # If search is empty, show ONLY nodes from the local scan list (all local nodes)
            filtered_nodes = list(self.local_nodes_only)
            # Sort the default local list by name too
            filtered_nodes.sort(key=lambda x: x.get('name', '').lower())
        else:
            # If search has text, filter the combined list (all_known_nodes) by name match
            filtered_nodes = [node for node in self.all_known_nodes if search_term_value in node.get('name', '').lower()]
            # Keep search results sorted by name
            filtered_nodes.sort(key=lambda x: x.get('name', '').lower())


        # Populate the Treeview with filtered data (using 5 columns)
        # Clear before populating (already done above)
        # self.root.after(0, lambda: [self.nodes_tree.delete(item) for item in self.nodes_tree.get_children()])

        if not filtered_nodes and (search_term_value != "" or (search_term_value == "" and not is_comfyui_nodes_dir_valid)):
             # If search is active and no results, or if search is empty but nodes dir is invalid
              display_message = "未找到匹配的节点" if search_term_value != "" else "无法加载本地节点列表"
              self.root.after(0, lambda msg=display_message: self.nodes_tree.insert("", tk.END, values=("", msg, "", "", "")))


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

    # Helper to fetch online node config (Placeholder) - Runs in worker thread
    def _fetch_online_node_config(self):
         """Fetches the online custom node list config."""
         node_config_url = self.node_config_url_var.get()
         if not node_config_url:
              self.log_to_gui("Update", "节点配置地址未设置，跳过在线配置获取。", "warn")
              return []

         self.log_to_gui("Update", f"尝试从 {node_config_url} 获取节点配置...", "info")
         try:
              response = requests.get(node_config_url, timeout=15) # Add timeout
              response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
              config_data = response.json()
              # Basic validation of the structure
              if not isinstance(config_data, list):
                   self.log_to_gui("Update", f"在线节点配置格式错误：根不是列表。", "error")
                   return []
              # Check if stop event was set while waiting for request
              if self.stop_event.is_set():
                   self.log_to_gui("Update", "获取在线节点配置任务已取消。", "warn"); return []

              self.log_to_gui("Update", f"已获取在线节点配置 (共 {len(config_data)} 条)。", "info")
              return config_data

         except requests.exceptions.RequestException as e:
              self.log_to_gui("Update", f"获取在线节点配置失败: {e}", "error")
              # Decide if this should show an error box or just log
              # self.root.after(0, lambda msg=str(e): messagebox.showerror("获取节点配置失败", f"无法从 {node_config_url} 获取在线节点配置:\n{msg}", parent=self.root))
              return [] # Return empty list on failure
         except json.JSONDecodeError:
              self.log_to_gui("Update", f"在线节点配置解析失败：不是有效的 JSON。", "error")
              # self.root.after(0, lambda: messagebox.showerror("解析节点配置失败", "在线节点配置不是有效的 JSON 格式。", parent=self.root))
              return []
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
             comfyui_nodes_dir = self.comfyui_nodes_dir # Get nodes dir again in case config changed
             node_install_path = os.path.normpath(os.path.join(comfyui_nodes_dir, node_name)) # Derive path from name
             repo_url = node_info.get("repo_url", "N/A")
             local_id = node_info.get("local_id", "N/A")
             # Get remote branch name from the detailed info captured during refresh_node_list
             remote_branch = node_info.get("remote_branch") # Use the stored branch name if available
             if not remote_branch:
                  # Fallback: try to parse from repo_info string, or default
                  remote_branch = node_info.get("repo_info", "N/A").split(' ')[0].strip() # Get branch name from repo_info string
                  if remote_branch in ("未知远程", "N/A", "信息获取失败", "无远程跟踪分支"):
                      # Further fallback - maybe the node's default branch is 'main'?
                      remote_branch = "main"
                      self.log_to_gui("Update", f"无法确定节点 '{node_name}' 的远程跟踪分支，使用默认分支 '{remote_branch}' 进行更新。", "warn")

             # Ensure remote_branch is not empty/invalid before pull
             if not remote_branch or remote_branch in ("未知远程", "N/A", "信息获取失败", "无远程跟踪分支"):
                 self.log_to_gui("Update", f"节点 '{node_name}' 远程跟踪分支信息无效 ({remote_branch})，跳过更新。", "warn")
                 failed_nodes.append(f"{node_name} (远程分支无效)")
                 continue


             self.log_to_gui("Update", f"[{index+1}/{len(nodes_to_process)}] 正在处理节点 '{node_name}'...", "info")

             # Double check if directory is still a git repo
             if not os.path.isdir(node_install_path) or not os.path.exists(os.path.join(node_install_path, ".git")):
                  self.log_to_gui("Update", f"节点目录 '{node_name}' 不是有效的 Git 仓库 ({node_install_path})，跳过更新。", "warn")
                  failed_nodes.append(f"{node_name} (非Git仓库)")
                  continue

             # Ensure tracking remote is correct (Optional check)
             stdout, stderr, returncode = self._run_git_command(["remote", "get-url", "origin"], cwd=node_install_path, timeout=10)
             current_origin_url = stdout.strip() if returncode == 0 else ""
             if returncode != 0 or current_origin_url != repo_url:
                  if returncode != 0: self.log_to_gui("Update", f"无法获取节点 '{node_name}' 的当前远程 origin URL: {stderr.strip() if stderr else '未知错误'}", "warn")
                  # Check if repo_url is valid before attempting to set
                  if repo_url in ("本地安装，无Git信息", "无法获取远程 URL", "本地安装", "N/A"):
                       self.log_to_gui("Update", f"节点 '{node_name}' 缺少有效的远程 URL ({repo_url})，无法更新远程地址。", "warn")
                       # Continue, but note that remote operations might fail if URL is wrong/missing
                  else:
                       self.log_to_gui("Update", f"节点 '{node_name}' 的远程 origin URL 不匹配或无法获取 ({current_origin_url} vs {repo_url})，尝试设置...", "warn")
                       # Check if origin remote exists first
                       stdout_remote_check, stderr_remote_check, returncode_remote_check = self._run_git_command(["remote", "get-url", "origin"], cwd=node_install_path, timeout=5)
                       if returncode_remote_check == 0: # origin exists, just set URL
                            self.log_to_gui("Update", f"执行 git remote set-url origin {repo_url} for '{node_name}'...", "info")
                            stdout_set, stderr_set, returncode_set = self._run_git_command(["remote", "set-url", "origin", repo_url], cwd=node_install_path, timeout=10)
                            if returncode_set != 0:
                                 self.log_to_gui("Update", f"设置节点 '{node_name}' 的远程 URL 失败: {stderr_set.strip() if stderr_set else '未知错误'}", "error")
                                 # Continue but log error - maybe pull will still work if remote exists but URL changed?
                            else:
                                self.log_to_gui("Update", f"节点 '{node_name}' 的远程 origin URL 已更新。", "info")
                       else: # origin does not exist, add it
                            self.log_to_gui("Update", f"执行 git remote add origin {repo_url} for '{node_name}'...", "info")
                            stdout_add, stderr_add, returncode_add = self._run_git_command(["remote", "add", "origin", repo_url], cwd=node_install_path, timeout=10)
                            if returncode_add != 0:
                                 self.log_to_gui("Update", f"添加节点 '{node_name}' 的远程 URL 失败: {stderr_add.strip() if stderr_add else '未知错误'}", "error")
                                 # Continue but log error
                            else:
                                 self.log_to_gui("Update", f"节点 '{node_name}' 的远程 origin URL 已添加。", "info")


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
                  self.log_to_gui("Update", f"Git fetch 失败 for '{node_name}': {stderr.strip() if stderr else '未知错误'}", "error")
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
             # Ensure the remote branch exists locally after fetch
             stdout_remote, stderr_remote, returncode_remote = self._run_git_command(["rev-parse", f"origin/{remote_branch}"], cwd=node_install_path, timeout=5)
             remote_commit_id = stdout_remote.strip() if returncode_remote == 0 and stdout_remote else None

             if local_commit_id and remote_commit_id and local_commit_id != remote_commit_id:
                  self.log_to_gui("Update", f"节点 '{node_name}' 有新版本可用 ({local_id[:8]} -> {remote_commit_id[:8]})。", "info")
                  # Perform git pull (attempts merge, safer than reset if no local changes)
                  # Use pull --ff-only if you want to avoid merge commits on fast-forwardable branches
                  self.log_to_gui("Update", f"[{index+1}/{len(nodes_to_process)}] 执行 Git pull origin {remote_branch} for '{node_name}'...", "info")
                  stdout, stderr, returncode = self._run_git_command(["pull", "origin", remote_branch], cwd=node_install_path, timeout=180) # Allow more time
                  if returncode != 0:
                       self.log_to_gui("Update", f"Git pull 失败 for '{node_name}': {stderr.strip() if stderr else '未知错误'}", "error")
                       failed_nodes.append(f"{node_name} (Pull失败)")
                       continue
                  self.log_to_gui("Update", f"Git pull 完成 for '{node_name}'.", "info")

                  # Check for stop event
                  if self.stop_event.is_set():
                       self.log_to_gui("Update", f"更新全部节点任务已取消。", "warn"); break

                  # Update submodules after pull
                  if os.path.exists(os.path.join(node_install_path, ".gitmodules")):
                      self.log_to_gui("Update", f"[{index+1}/{len(nodes_to_process)}] 执行 Git submodule update for '{node_name}'...", "info")
                      stdout, stderr, returncode = self._run_git_command(["submodule", "update", "--init", "--recursive", "--force"], cwd=node_install_path, timeout=180) # Added --force
                      if returncode != 0:
                           self.log_to_gui("Update", f"Git submodule update 失败 for '{node_name}': {stderr.strip() if stderr else '未知错误'}", "warn")
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
                  if python_exe and os.path.isfile(python_exe) and os.path.isdir(node_install_path) and os.path.isfile(requirements_path):
                       self.log_to_gui("Update", f"[{index+1}/{len(nodes_to_process)}] 执行 pip 安装节点依赖 for '{node_name}'...", "info")
                       pip_cmd = [python_exe, "-m", "pip", "install", "-r", requirements_path, "--upgrade"]
                       # Add --user if not in venv (check similar to main body)
                       if platform.system() != "Windows" and sys.prefix == sys.base_prefix:
                            pip_cmd.append("--user")
                            self.log_to_gui("Update", f"节点 '{node_name}': 未检测到Python虚拟环境，使用 --user 选项安装依赖。", "warn")

                       pip_cmd.extend(["--extra-index-url", "https://download.pytorch.org/whl/cu118", "--extra-index-url", "https://download.pytorch.org/whl/cu121", "--extra-index-url", "https://download.pytorch.org/whl/rocm5.7"])

                       stdout, stderr, returncode = self._run_git_command(
                            pip_cmd,
                            cwd=node_install_path, timeout=180 # Allow more time
                       )
                       if returncode != 0:
                            self.log_to_gui("Update", f"Pip 安装节点依赖失败 for '{node_name}': {stderr.strip() if stderr else '未知错误'}", "error")
                            self.root.after(0, lambda name=node_name: messagebox.showwarning("节点依赖安装失败 / Node Dependency Install Failed", f"节点 '{name}' 的 Python 依赖安装失败，请手动检查。\n请查看后台日志获取详情。", parent=self.root))
                       else:
                            self.log_to_gui("Update", f"Pip 安装节点依赖完成 for '{node_name}'.", "info")
                  else:
                       if os.path.isdir(node_install_path) and os.path.exists(os.path.join(node_install_path, ".git")): # Only warn if it's a git repo that *might* have had deps
                            self.log_to_gui("Update", f"节点 '{node_name}' 未找到 requirements.txt 或 Python 无效，跳过依赖安装。", "info")

                  updated_count += 1
                  self.log_to_gui("Update", f"节点 '{node_name}' 更新成功。", "info")
             elif local_commit_id and remote_commit_id and local_commit_id == remote_commit_id:
                  self.log_to_gui("Update", f"节点 '{node_name}' 已是最新版本。", "info")
             elif not local_commit_id:
                  self.log_to_gui("Update", f"无法获取节点 '{node_name}' 的本地Commit ID，跳过更新检查。", "warn")
                  failed_nodes.append(f"{node_name} (本地ID获取失败)")
             elif not remote_commit_id:
                  self.log_to_gui("Update", f"无法获取节点 '{node_name}' 的远程Commit ID (origin/{remote_branch})，跳过更新检查。", "warn")
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

    # REQUIREMENT 5: Implement Node Uninstall Task
    def _node_uninstall_task(self, node_name, node_install_path):
         """Task to uninstall a node by deleting its directory. Runs in worker thread."""
         # Check for stop event
         if self.stop_event.is_set():
              self.log_to_gui("Update", f"节点 '{node_name}' 卸载任务已取消。", "warn"); return

         self.log_to_gui("Update", f"正在卸载节点 '{node_name}' (删除目录: {node_install_path})...", "info")

         try:
              # Double check if the directory exists before attempting deletion
              if not os.path.isdir(node_install_path):
                   self.log_to_gui("Update", f"节点目录 '{node_install_path}' 不存在，无需卸载。", "warn")
                   self.root.after(0, lambda name=node_name: messagebox.showwarning("卸载失败", f"节点目录 '{name}' 不存在。", parent=self.root))
                   return # Exit task if directory is already gone

              # Check for stop event just before deletion
              if self.stop_event.is_set(): raise threading.ThreadExit

              # Perform directory deletion
              shutil.rmtree(node_install_path)
              self.log_to_gui("Update", f"节点目录 '{node_install_path}' 删除成功。", "info")

              # Success message
              self.log_to_gui("Update", f"节点 '{node_name}' 卸载流程完成。", "info")
              self.root.after(0, lambda name=node_name: messagebox.showinfo("卸载完成 / Uninstall Complete", f"节点 '{name}' 已成功卸载。", parent=self.root))

         except threading.ThreadExit:
              self.log_to_gui("Update", f"节点 '{node_name}' 卸载任务已取消。", "warn")
              # If cancellation happened during deletion, the directory might be in an inconsistent state.
              self.root.after(0, lambda name=node_name: messagebox.showwarning("卸载被中断", f"节点 '{name}' 的卸载任务被中断，目录可能未完全清除。", parent=self.root))
         except Exception as e:
             error_msg = f"节点 '{node_name}' 卸载失败: {e}"
             self.log_to_gui("Update", error_msg, "error")
             self.root.after(0, lambda msg=error_msg: messagebox.showerror("卸载失败 / Uninstall Failed", msg, parent=self.root))
         finally:
             # Always refresh list and update UI state after task finishes
             self.root.after(0, self.refresh_node_list)
             # UI state update is handled by the worker thread's finally block


    # REQUIREMENT 5: Node Switch/Install and History Modal Logic
    # _switch_install_node_task is now used for INSTALLATION and potentially simple CHECKOUT/PULL if called directly.
    # The MODAL logic for switching versions uses a different task flow.

    # Renamed to be more specific: this handles INSTALLATION (clone)
    # For installed nodes, _queue_node_switch_install calls _queue_node_history_fetch instead.
    def _switch_install_node_task(self, node_name, node_install_path, repo_url, target_ref):
        """Task to execute git commands for INSTALLING a node (cloning). Runs in worker thread."""
        # Check for stop event
        if self.stop_event.is_set():
             self.log_to_gui("Update", f"节点 '{node_name}' 安装任务已取消。", "warn"); return

        action = "安装" # This task is specifically for installation via clone
        self.log_to_gui("Update", f"正在对节点 '{node_name}' 执行 '{action}' (目标引用: {target_ref})...", "info")

        try:
            comfyui_nodes_dir = self.comfyui_nodes_dir # Get nodes dir again

            # --- Install (Clone) ---
            # Ensure the parent directory for cloning exists
            if not os.path.exists(comfyui_nodes_dir):
                 self.log_to_gui("Update", f"创建节点目录: {comfyui_nodes_dir}", "info")
                 # Use root.after for potential message box if creation fails, but os.makedirs handles exist_ok
                 os.makedirs(comfyui_nodes_dir, exist_ok=True) # Real command

            # Check if the directory already exists and is not empty (might be a manual copy or failed previous attempt)
            if os.path.exists(node_install_path) and (os.path.isdir(node_install_path) and len(os.listdir(node_install_path)) > 0 or not os.path.isdir(node_install_path)):
                 self.log_to_gui("Update", f"节点安装目录 '{node_install_path}' 已存在且不为空，请先手动移除或卸载。", "error")
                 # Show error box in GUI thread
                 self.root.after(0, lambda name=node_name, path=node_install_path: messagebox.showerror("安装失败", f"节点安装目录已存在且不为空:\n{path}\n请先手动移除或使用卸载功能。", parent=self.root))
                 return # Cannot clone if directory exists and isn't empty

            self.log_to_gui("Update", f"执行 Git clone {repo_url} {node_install_path}...", "info")
            clone_cmd = ["clone"]
            # Optionally clone a specific branch initially if target_ref is a branch
            # It's safer to just clone and then checkout the specific ref.
            # git clone <repo_url> <install_path>
            clone_cmd.extend([repo_url, node_install_path])

            stdout, stderr, returncode = self._run_git_command(clone_cmd, cwd=comfyui_nodes_dir, timeout=300) # Allow more time for clone
            if returncode != 0:
                 self.log_to_gui("Update", f"Git clone 失败: {stderr.strip() if stderr else '未知错误'}", "error")
                 # Attempt to remove the partially created directory
                 if os.path.exists(node_install_path):
                      try:
                           # Use root.after for confirmation dialog? No, auto-clean is fine here.
                           shutil.rmtree(node_install_path)
                           self.log_to_gui("Update", f"已移除失败的节点目录: {node_install_path}", "info")
                      except Exception as rm_err:
                           self.log_to_gui("Update", f"移除失败的节点目录 '{node_install_path}' 失败: {rm_err}", "error")
                 raise Exception("Git clone 失败")
            self.log_to_gui("Update", "Git clone 完成。", "info")

            # Check for stop event
            if self.stop_event.is_set(): raise threading.ThreadExit

            # After cloning, checkout the target ref if it's not the default branch (or if we didn't use --branch)
            # It's safer to always checkout the specified target_ref after cloning.
            self.log_to_gui("Update", f"执行 Git checkout {target_ref}...", "info")
            stdout, stderr, returncode = self._run_git_command(["checkout", target_ref], cwd=node_install_path, timeout=60)
            if returncode != 0:
                 self.log_to_gui("Update", f"Git checkout 失败: {stderr.strip() if stderr else '未知错误'}", "error")
                 # This might leave the repo in a bad state.
                 raise Exception(f"Git checkout {target_ref} 失败")
            self.log_to_gui("Update", f"Git checkout {target_ref} 完成。", "info")


            # Check for stop event
            if self.stop_event.is_set(): raise threading.ThreadExit

            # --- Update submodules (if it's a git repo) ---
            if os.path.isdir(node_install_path) and os.path.exists(os.path.join(node_install_path, ".git")):
                 if os.path.exists(os.path.join(node_install_path, ".gitmodules")):
                     self.log_to_gui("Update", f"执行 Git submodule update for '{node_name}'...", "info")
                     stdout, stderr, returncode = self._run_git_command(["submodule", "update", "--init", "--recursive", "--force"], cwd=node_install_path, timeout=180) # Added --force
                     if returncode != 0:
                          self.log_to_gui("Update", f"Git submodule update 失败 for '{node_name}': {stderr.strip() if stderr else '未知错误'}", "error")
                          # Log error but don't necessarily fail the install
                     else:
                          self.log_to_gui("Update", f"Git submodule update 完成 for '{node_name}'.", "info")
                 else:
                      self.log_to_gui("Update", f"'{node_name}' 目录未找到 .gitmodules 文件，跳过 submodule update。", "info")
            else:
                 self.log_to_gui("Update", f"跳过 submodule update，'{node_name}' 目录不是有效的 Git 仓库。", "warn")


            # Check for stop event
            if self.stop_event.is_set(): raise threading.ThreadExit


            # --- Install Node-specific Python dependencies (if requirements.txt exists) ---
            python_exe = self.python_exe_var.get()
            requirements_path = os.path.join(node_install_path, "requirements.txt")
            if python_exe and os.path.isfile(python_exe) and os.path.isdir(node_install_path) and os.path.isfile(requirements_path):
                 self.log_to_gui("Update", f"执行 pip 安装节点依赖 for '{node_name}'...", "info")
                 pip_cmd = [python_exe, "-m", "pip", "install", "-r", requirements_path, "--upgrade"]
                 # Add --user if not in venv (check similar to main body)
                 if platform.system() != "Windows" and sys.prefix == sys.base_prefix:
                      pip_cmd.append("--user")
                      self.log_to_gui("Update", f"节点 '{node_name}': 未检测到Python虚拟环境，使用 --user 选项安装依赖。", "warn")

                 pip_cmd.extend(["--extra-index-url", "https://download.pytorch.org/whl/cu118", "--extra-index-url", "https://download.pytorch.org/whl/cu121", "--extra-index-url", "https://download.pytorch.org/whl/rocm5.7"])


                 stdout, stderr, returncode = self._run_git_command(
                      pip_cmd,
                      cwd=node_install_path, timeout=180 # Allow more time
                 )
                 if returncode != 0:
                      self.log_to_gui("Update", f"Pip 安装节点依赖失败 for '{node_name}': {stderr.strip() if stderr else '未知错误'}", "error")
                      self.root.after(0, lambda name=node_name: messagebox.showwarning("节点依赖安装失败 / Node Dependency Install Failed", f"节点 '{name}' 的 Python 依赖安装失败，请手动检查。\n请查看后台日志获取详情。", parent=self.root))
                 else:
                      self.log_to_gui("Update", f"Pip 安装节点依赖完成 for '{node_name}'.", "info")
            else:
                 if os.path.isdir(node_install_path) and os.path.exists(os.path.join(node_install_path, ".git")): # Only log info if it's a potentially valid node
                      self.log_to_gui("Update", f"节点 '{node_name}' 未找到 requirements.txt 或 Python 无效，跳过依赖安装。", "info")


            # Success message
            self.log_to_gui("Update", f"节点 '{node_name}' '{action}' 流程完成。", "info")
            self.root.after(0, lambda name=node_name, act=action: messagebox.showinfo("操作完成 / Operation Complete", f"节点 '{name}' 已成功执行 '{act}' 操作。", parent=self.root))

        except threading.ThreadExit:
             self.log_to_gui("Update", f"节点 '{node_name}' 安装任务已取消。", "warn")
        except Exception as e:
            error_msg = f"节点 '{node_name}' '{action}' 流程失败: {e}"
            self.log_to_gui("Update", error_msg, "error")
            self.root.after(0, lambda msg=error_msg: messagebox.showerror("操作失败 / Operation Failed", msg, parent=self.root))
        finally:
            # Always refresh list and update UI state after task finishes
            self.root.after(0, self.refresh_node_list)
            # UI state update is handled by the worker thread's finally block

    # REQUIREMENT 5: Task to fetch node history
    def _queue_node_history_fetch(self, node_name, node_install_path):
        """Queues the task to fetch history for an installed node."""
        self.log_to_gui("Launcher", f"将获取节点 '{node_name}' 版本历史任务添加到队列...", "info")
        # Pass necessary info to the task
        self.update_task_queue.put((self._node_history_fetch_task, [node_name, node_install_path], {}))
        # UI state update is handled by the queueing method's finally block

    # REQUIREMENT 5: Task to fetch node history (Runs in worker thread)
    def _node_history_fetch_task(self, node_name, node_install_path):
         """Task to fetch git history (branches and tags) for a node. Runs in worker thread."""
         self.log_to_gui("Update", f"正在获取节点 '{node_name}' 的版本历史...", "info")

         # Check for stop event
         if self.stop_event.is_set():
              self.log_to_gui("Update", f"节点 '{node_name}' 历史获取任务已取消。", "warn"); return

         history_data = [] # List to store history entries

         try:
             # Ensure it's a valid git repo
             if not os.path.isdir(node_install_path) or not os.path.exists(os.path.join(node_install_path, ".git")):
                  self.log_to_gui("Update", f"节点目录 '{node_install_path}' 不是有效的 Git 仓库，无法获取历史。", "error")
                  raise Exception(f"节点目录不是有效的 Git 仓库: {node_install_path}")

             # Ensure tracking remote is correct (Optional but good practice) - similar logic to main body activation
             # Can skip setting if it fails, just log warning. Fetch below might fail if remote is bad.
             repo_url = "无法获取远程 URL"
             # Try to find the repo_url from the stored local_nodes_only data
             found_node_info = next((node for node in self.local_nodes_only if os.path.normpath(os.path.join(self.comfyui_nodes_dir, node.get("name", ""))) == os.path.normpath(node_install_path)), None)
             if found_node_info and found_node_info.get("repo_url") not in ("本地安装，无Git信息", "无法获取远程 URL", "本地安装", "N/A"):
                  repo_url = found_node_info.get("repo_url")
                  # Check current remote URL and set if needed, same logic as main body activate
                  try:
                       stdout_url, stderr_url, returncode_url = self._run_git_command(["remote", "get-url", "origin"], cwd=node_install_path, timeout=10)
                       current_origin_url = stdout_url.strip() if returncode_url == 0 else ""
                       if not current_origin_url or current_origin_url != repo_url:
                            self.log_to_gui("Update", f"节点 '{node_name}': 远程 origin URL 不匹配或无法获取 ({current_origin_url} vs {repo_url})，尝试设置...", "warn")
                            stdout_set, stderr_set, returncode_set = self._run_git_command(["remote", "set-url", "origin", repo_url], cwd=node_install_path, timeout=10)
                            if returncode_set != 0:
                                 self.log_to_gui("Update", f"节点 '{node_name}': 设置远程 URL 失败: {stderr_set.strip() if stderr_set else '未知错误'}", "warn")
                            else:
                                self.log_to_gui("Update", f"节点 '{node_name}': 远程 origin URL 已更新。", "info")
                  except Exception as e:
                       self.log_to_gui("Update", f"节点 '{node_name}': 获取/设置远程 origin URL 异常: {e}", "warn")
             else:
                  self.log_to_gui("Update", f"节点 '{node_name}': 未在本地节点列表中找到或无有效远程 URL ({repo_url})，跳过远程 URL 检查/设置。", "warn")


             # Check for stop event
             if self.stop_event.is_set(): raise threading.ThreadExit

             # Fetch latest info from origin first
             self.log_to_gui("Update", f"执行 Git fetch origin for '{node_name}'...", "info")
             stdout, stderr, returncode = self._run_git_command(["fetch", "origin"], cwd=node_install_path, timeout=60)
             if returncode != 0:
                  self.log_to_gui("Update", f"Git fetch 失败 for '{node_name}': {stderr.strip() if stderr else '未知错误'}", "error")
                  # Don't raise exception, allow listing local refs if fetch fails
                  self.log_to_gui("Update", "无法从远程获取最新历史，列表可能不完整。", "warn")


             # Check for stop event after fetch
             if self.stop_event.is_set():
                  self.log_to_gui("Update", f"节点 '{node_name}' 历史获取任务已取消。", "warn"); return

             # Get list of relevant refs (remote branches and tags) with commit info
             # Format: '%(refname:short) %(objectname) %(committerdate:iso-strict) %(contents:subject)'
             # Get branches (remote)
             branches_output, branch_err, branch_rc = self._run_git_command(
                  ["for-each-ref", "refs/remotes/origin/", "--sort=-committerdate", "--format=%(refname:short) %(objectname) %(committerdate:iso-strict) %(contents:subject)"],
                  cwd=node_install_path, timeout=30
             )
             if branch_rc == 0 and branches_output:
                  for line in branches_output.splitlines():
                      parts = line.split(' ', 3)
                      if len(parts) == 4:
                          refname = parts[0].replace("origin/", "")
                          commit_id = parts[1]
                          date_iso = parts[2]
                          description = parts[3].strip()
                          if "->" not in refname: # Exclude origin/HEAD
                              history_data.append({"type": "branch", "name": refname, "commit_id": commit_id, "date_iso": date_iso, "description": description})
             elif branch_rc != 0:
                  self.log_to_gui("Update", f"获取节点 '{node_name}' 远程分支列表失败: {branch_err.strip() if branch_err else '未知错误'}", "warn")


             # Check for stop event
             if self.stop_event.is_set():
                  self.log_to_gui("Update", f"节点 '{node_name}' 历史获取任务已取消。", "warn"); return

             # Get tags
             tags_output, tag_err, tag_rc = self._run_git_command(
                  ["for-each-ref", "refs/tags/", "--sort=-taggerdate", "--format=%(refname:short) %(objectname) %(taggerdate:iso-strict) %(contents:subject)"],
                  cwd=node_install_path, timeout=30
             )
             if tag_rc == 0 and tags_output:
                  for line in tags_output.splitlines():
                      parts = line.split(' ', 3)
                      if len(parts) == 4:
                          refname = parts[0].replace("refs/tags/", "")
                          commit_id = parts[1] # Object name the tag points to
                          date_iso = parts[2]
                          description = parts[3].strip()
                          history_data.append({"type": "tag", "name": refname, "commit_id": commit_id, "date_iso": date_iso, "description": description})
             elif tag_rc != 0:
                  self.log_to_gui("Update", f"获取节点 '{node_name}' 标签列表失败: {tag_err.strip() if tag_err else '未知错误'}", "warn")


             # Sort history data by date (newest first)
             history_data.sort(key=lambda x: x['date_iso'], reverse=True)

             self._node_history_modal_data = history_data # Store data for the modal
             self._node_history_modal_node_name = node_name # Store node name

             self.log_to_gui("Update", f"节点 '{node_name}' 版本历史获取完成 (共 {len(history_data)} 条)。", "info")

             # Show the modal in the GUI thread
             self.root.after(0, self._show_node_history_modal)


         except threading.ThreadExit:
              self.log_to_gui("Update", f"节点 '{node_name}' 历史获取任务已取消。", "warn")
              self._node_history_modal_data = [] # Clear data if cancelled
              self._node_history_modal_node_name = ""
              # No need to show modal if cancelled
         except Exception as e:
             error_msg = f"获取节点 '{node_name}' 版本历史失败: {e}"
             self.log_to_gui("Update", error_msg, "error")
             self._node_history_modal_data = [] # Clear data on error
             self._node_history_modal_node_name = ""
             # Show error box in GUI thread
             self.root.after(0, lambda msg=error_msg: messagebox.showerror("获取历史失败 / Failed to Get History", msg, parent=self.root))
         finally:
              # UI state update is handled by the worker thread's finally block
              pass # No specific action needed here, modal/error is shown by after calls.


    # REQUIREMENT 5: Show Node History Modal (Runs in GUI thread)
    def _show_node_history_modal(self):
         """Creates and displays the node version history modal."""
         if not self._node_history_modal_data:
              self.log_to_gui("Update", f"没有节点 '{self._node_history_modal_node_name}' 的历史版本数据。", "warn")
              messagebox.showwarning("无版本历史", f"未能获取节点 '{self._node_history_modal_node_name}' 的版本历史。", parent=self.root)
              self._node_history_modal_node_name = "" # Clear state
              return

         node_name = self._node_history_modal_node_name

         modal_window = Toplevel(self.root)
         modal_window.title(f"切换版本 - {node_name}")
         modal_window.transient(self.root) # Keep modal on top of main window
         modal_window.grab_set() # Modal
         modal_window.geometry("700x500")
         modal_window.configure(bg=BG_COLOR)
         modal_window.columnconfigure(0, weight=1)
         modal_window.rowconfigure(0, weight=1)
         modal_window.protocol("WM_DELETE_WINDOW", modal_window.destroy) # Close modal on window close button


         frame = ttk.Frame(modal_window, style='TFrame', padding=10)
         frame.grid(row=0, column=0, sticky="nsew")
         frame.columnconfigure(0, weight=1)
         frame.rowconfigure(0, weight=1) # Treeview row


         # Treeview for history
         history_tree = ttk.Treeview(frame, columns=("type", "name", "commit_id", "date", "description"), show="headings", style='NodeHistory.Treeview') # Use dedicated style
         history_tree.heading("type", text="类型");
         history_tree.heading("name", text="名称");
         history_tree.heading("commit_id", text="提交ID");
         history_tree.heading("date", text="日期");
         history_tree.heading("description", text="描述")

         history_tree.column("type", width=60, stretch=tk.NO);
         history_tree.column("name", width=120, stretch=tk.NO);
         history_tree.column("commit_id", width=80, stretch=tk.NO); # Short ID display
         history_tree.column("date", width=100, stretch=tk.NO);
         history_tree.column("description", width=200, stretch=tk.YES);

         history_tree.grid(row=0, column=0, sticky="nsew")

         # Scrollbar for history tree
         history_scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=history_tree.yview)
         history_tree.configure(yscrollcommand=history_scrollbar.set)
         history_scrollbar.grid(row=0, column=1, sticky="ns")

         # Populate the treeview with stored history data
         for item_data in self._node_history_modal_data:
              try:
                   # Format date to YYYY-MM-DD
                   date_obj = datetime.fromisoformat(item_data['date_iso'])
                   date_display = date_obj.strftime('%Y-%m-%d')
              except ValueError:
                   date_display = "无效日期"

              history_tree.insert("", tk.END, values=(
                   item_data.get("type", "未知"),
                   item_data.get("name", "N/A"),
                   item_data.get("commit_id", "N/A")[:8], # Display short commit ID
                   date_display,
                   item_data.get("description", "无描述")
              ), iid=item_data.get("commit_id")) # Use full commit ID as iid for easy retrieval

         # Button frame at the bottom
         button_frame = ttk.Frame(modal_window, style='TFrame', padding=(0, 5))
         button_frame.grid(row=1, column=0, sticky="ew")
         button_frame.columnconfigure(0, weight=1) # Spacer column
         switch_button = ttk.Button(button_frame, text="确定切换到此版本", style="Accent.TButton",
                                    command=lambda: self._on_modal_switch_confirm(modal_window, history_tree, node_name))
         switch_button.grid(row=0, column=1, padx=(0, 5))
         cancel_button = ttk.Button(button_frame, text="取消", style="TButton", command=modal_window.destroy)
         cancel_button.grid(row=0, column=2)

         # Bind selection event to enable/disable the switch button
         def update_switch_button_state(event):
             selected_item = history_tree.focus()
             switch_button.config(state=tk.NORMAL if selected_item else tk.DISABLED)

         history_tree.bind("<<TreeviewSelect>>", update_switch_button_state)
         switch_button.config(state=tk.DISABLED) # Initially disabled

         # Clear the temporary stored data after showing modal
         self._node_history_modal_data = []
         # node_name is stored locally within this function scope now


    # REQUIREMENT 5: Handle Modal Switch Confirmation (Runs in GUI thread)
    def _on_modal_switch_confirm(self, modal_window, history_tree, node_name):
         """Handles the confirmation button click in the node history modal."""
         selected_item = history_tree.focus()
         if not selected_item:
             messagebox.showwarning("未选择版本", "请从列表中选择一个要切换的版本。", parent=modal_window)
             return

         # The iid of the treeview item is the full commit ID
         target_commit_id = history_tree.item(selected_item, 'iid')

         # Get the node's installation path
         comfyui_nodes_dir = self.comfyui_nodes_dir # Get nodes dir again
         # Find the node info from the stored local_nodes_only list to get the correct directory name
         found_node_info = next((node for node in self.local_nodes_only if node.get("name") == node_name), None)

         if not found_node_info:
              self.log_to_gui("Update", f"节点 '{node_name}' 未在本地节点列表中找到，无法执行切换。", "error")
              messagebox.showerror("切换失败", f"无法找到节点 '{node_name}' 的本地信息。", parent=modal_window)
              modal_window.destroy()
              return

         # Derive the node installation path based on the name found in local_nodes_only
         node_install_path = os.path.normpath(os.path.join(comfyui_nodes_dir, found_node_info.get("name")))

         if not os.path.isdir(node_install_path) or not os.path.exists(os.path.join(node_install_path, ".git")):
              self.log_to_gui("Update", f"节点目录 '{node_install_path}' 不是有效的 Git 仓库，无法切换版本。", "error")
              messagebox.showerror("切换失败", f"节点目录 '{node_install_path}' 不是有效的 Git 仓库。", parent=modal_window)
              modal_window.destroy()
              return


         # Confirm switch
         confirm = messagebox.askyesno("确认切换版本", f"确定要将节点 '{node_name}' 切换到版本 (提交ID: {target_commit_id[:8]}) 吗？\n此操作会修改节点目录内容。\n\n警告：切换版本可能需要重新安装依赖，且可能丢失本地修改！\n建议在切换前备份节点目录。\n确认前请确保 ComfyUI 已停止运行。", parent=modal_window)
         if not confirm: return


         self.log_to_gui("Launcher", f"将节点 '{node_name}' 切换到版本 (提交ID: {target_commit_id[:8]}) 任务添加到队列...", "info")
         # Queue the task to switch to the specific commit ID
         # Use a dedicated task or modify the existing _switch_install_node_task
         # Let's create a dedicated task for switching to a specific commit/tag/branch.
         self.update_task_queue.put((self._switch_node_to_ref_task, [node_name, node_install_path, target_commit_id], {}))

         modal_window.destroy() # Close the modal after queuing the task
         self.root.after(0, self._update_ui_state) # Update UI state


    # REQUIREMENT 5: Task to switch node to a specific ref (commit/tag/branch)
    def _switch_node_to_ref_task(self, node_name, node_install_path, target_ref):
         """Task to switch an installed node to a specific git reference (commit/tag/branch). Runs in worker thread."""
         # Check for stop event
         if self.stop_event.is_set():
              self.log_to_gui("Update", f"节点 '{node_name}' 切换版本任务已取消。", "warn"); return

         self.log_to_gui("Update", f"正在将节点 '{node_name}' 切换到版本 (引用: {target_ref[:8]})...", "info") # Use short ref for log

         try:
             # Ensure it's a valid git repo
             if not os.path.isdir(node_install_path) or not os.path.exists(os.path.join(node_install_path, ".git")):
                  self.log_to_gui("Update", f"节点目录 '{node_install_path}' 不是有效的 Git 仓库，无法切换版本。", "error")
                  raise Exception(f"节点目录不是有效的 Git 仓库: {node_install_path}")

             # Check if there are local changes that would be overwritten by checkout/reset
             stdout_status, stderr_status, returncode_status = self._run_git_command(["status", "--porcelain"], cwd=node_install_path, timeout=10)
             if returncode_status == 0 and stdout_status.strip():
                  # This check should ideally be done in the GUI thread before queuing if blocking is desired.
                  # Since it's in the worker, we just log a warning. The checkout might fail or require --force.
                  self.log_to_gui("Update", f"节点 '{node_name}' 存在未提交的本地修改，切换版本可能会覆盖。", "warn")
                  # Proceed, relying on `git checkout` behavior or adding --force


             # Check for stop event
             if self.stop_event.is_set(): raise threading.ThreadExit

             # Perform git checkout to the target reference
             # Use --force to potentially discard local changes (user was warned)
             self.log_to_gui("Update", f"执行 Git checkout --force {target_ref[:8]} for '{node_name}'...", "info")
             stdout, stderr, returncode = self._run_git_command(["checkout", "--force", target_ref], cwd=node_install_path, timeout=60)
             if returncode != 0:
                  self.log_to_gui("Update", f"Git checkout 失败 for '{node_name}': {stderr.strip() if stderr else '未知错误'}", "error")
                  # Add specific checks for common errors like 'pathspec did not match any file(s) known to git'
                  if "did not match any file(s) known to git" in (stderr.lower() if stderr else ""):
                       error_detail = "目标引用不存在或已损坏。"
                  elif "could not switch to" in (stderr.lower() if stderr else ""):
                       error_detail = "无法切换分支，可能存在冲突或本地未跟踪文件阻止。"
                  else:
                       error_detail = "未知 Git 错误。"

                  raise Exception(f"Git checkout {target_ref[:8]} 失败: {error_detail}")

             self.log_to_gui("Update", f"Git checkout {target_ref[:8]} 完成 for '{node_name}'.", "info")


             # Check for stop event
             if self.stop_event.is_set(): raise threading.ThreadExit

             # --- Update submodules ---
             if os.path.exists(os.path.join(node_install_path, ".gitmodules")):
                 self.log_to_gui("Update", f"执行 Git submodule update for '{node_name}'...", "info")
                 stdout, stderr, returncode = self._run_git_command(["submodule", "update", "--init", "--recursive", "--force"], cwd=node_install_path, timeout=180) # Added --force
                 if returncode != 0:
                      self.log_to_gui("Update", f"Git submodule update 失败 for '{node_name}': {stderr.strip() if stderr else '未知错误'}", "error")
                      # Not critical error? Continue but log.
                 else:
                      self.log_to_gui("Update", f"Git submodule update 完成 for '{node_name}'.", "info")
             else:
                  self.log_to_gui("Update", f"'{node_name}' 目录未找到 .gitmodules 文件，跳过 submodule update。", "info")

             # Check for stop event
             if self.stop_event.is_set(): raise threading.ThreadExit


             # --- Re-install Node-specific Python dependencies (if requirements.txt exists) ---
             python_exe = self.python_exe_var.get()
             requirements_path = os.path.join(node_install_path, "requirements.txt")
             if python_exe and os.path.isfile(python_exe) and os.path.isdir(node_install_path) and os.path.isfile(requirements_path):
                  self.log_to_gui("Update", f"执行 pip 安装节点依赖 for '{node_name}'...", "info")
                  pip_cmd = [python_exe, "-m", "pip", "install", "-r", requirements_path, "--upgrade"]
                  # Add --user if not in venv (check similar to main body)
                  if platform.system() != "Windows" and sys.prefix == sys.base_prefix:
                       pip_cmd.append("--user")
                       self.log_to_gui("Update", f"节点 '{node_name}': 未检测到Python虚拟环境，使用 --user 选项安装依赖。", "warn")

                  pip_cmd.extend(["--extra-index-url", "https://download.pytorch.org/whl/cu118", "--extra-index-url", "https://download.pytorch.org/whl/cu121", "--extra-index-url", "https://download.pytorch.org/whl/rocm5.7"])


                  stdout, stderr, returncode = self._run_git_command(
                       pip_cmd,
                       cwd=node_install_path, timeout=180 # Allow more time
                  )
                  if returncode != 0:
                       self.log_to_gui("Update", f"Pip 安装节点依赖失败 for '{node_name}': {stderr.strip() if stderr else '未知错误'}", "error")
                       self.root.after(0, lambda name=node_name: messagebox.showwarning("节点依赖安装失败 / Node Dependency Install Failed", f"节点 '{name}' 的 Python 依赖安装失败，请手动检查。\n请查看后台日志获取详情。", parent=self.root))
                  else:
                       self.log_to_gui("Update", f"Pip 安装节点依赖完成 for '{node_name}'.", "info")
             else:
                  if os.path.isdir(node_install_path) and os.path.exists(os.path.join(node_install_path, ".git")): # Only log info if it's a potentially valid node
                       self.log_to_gui("Update", f"节点 '{node_name}' 未找到 requirements.txt 或 Python 无效，跳过依赖安装。", "info")


             # Success message
             self.log_to_gui("Update", f"节点 '{node_name}' 已成功切换到版本 (引用: {target_ref[:8]})。", "info")
             self.root.after(0, lambda name=node_name, ref=target_ref[:8]: messagebox.showinfo("切换完成 / Switch Complete", f"节点 '{name}' 已成功切换到版本: {ref}", parent=self.root))


         except threading.ThreadExit:
              self.log_to_gui("Update", f"节点 '{node_name}' 切换版本任务已取消。", "warn")
         except Exception as e:
             error_msg = f"节点 '{node_name}' 切换版本失败: {e}"
             self.log_to_gui("Update", error_msg, "error")
             self.root.after(0, lambda msg=error_msg: messagebox.showerror("切换失败 / Switch Failed", msg, parent=self.root))
         finally:
             # Always refresh list and update UI state after task finishes
             self.root.after(0, self.refresh_node_list)
             # UI state update is handled by the worker thread's finally block


    # --- Error Analysis Methods ---

    def run_diagnosis(self):
        """Captures ComfyUI logs and sends them to the configured API for analysis."""
        # Check if an update task is running
        if self._is_update_task_running():
             self.log_to_gui("Launcher", "更新任务正在进行中，无法运行诊断。", "warn"); return

        # Check if ComfyUI is running - optional, but diagnosis is most useful with running logs
        # if not self._is_comfyui_running() and not self.comfyui_externally_detected:
        #      messagebox.showwarning("ComfyUI未运行", "ComfyUI 后台未运行，诊断结果可能不准确或无日志。", parent=self.root)
        #      # Decide if we should still proceed or return. Let's proceed to allow analyzing old logs.


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
        """Task to send logs to API and display analysis. Runs in worker thread."""
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
        sys.exit(1) # Exit with a non-zero code