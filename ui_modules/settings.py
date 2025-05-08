# -*- coding: utf-8 -*-
# File: ui_modules/settings.py
# Settings Tab Module (Fixed Styles)

import tkinter as tk
from tkinter import ttk, filedialog
import os

# Note: Styling constants and setup_text_tags are accessed via app_instance

class SettingsTab:
    """Handles the UI and basic logic for the Settings tab."""
    def __init__(self, parent_frame, app_instance):
        """
        Initializes the Settings tab UI elements.

        Args:
            parent_frame: The ttk.Frame widget that serves as the parent for this tab's content.
            app_instance: The main ComLauncherApp instance to access shared resources.
        """
        self.app = app_instance # Store reference to the main application instance
        self.frame = parent_frame

        self.frame.columnconfigure(0, weight=1)
        current_row = 0
        frame_padx = 5
        frame_pady = (0, 10) # Added bottom padding to groups
        widget_pady = 3
        widget_padx = 5
        # Removed fixed label_min_width

        # --- Folder Access Buttons (Bug 1 Fix: Wrap in LabelFrame and configure column weight) ---
        # Use app instance constant for style
        folder_group = ttk.LabelFrame(self.frame, text=" 文件夹快捷方式 / Folder Shortcuts ", padding=(10, 5), style='Folder.TLabelframe') # Added LabelFrame and style
        folder_group.grid(row=current_row, column=0, sticky="ew", padx=frame_padx, pady=frame_pady) # Grid the LabelFrame

        # FIX: Configure the column within the folder_group LabelFrame to expand
        folder_group.columnconfigure(0, weight=1) # Allow the single column containing folder_button_frame to expand

        # Use app instance constant for style
        folder_button_frame = ttk.Frame(folder_group, style='Settings.TFrame') # Put the button frame inside the LabelFrame
        # The button frame should now expand within the LabelFrame's column 0
        folder_button_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0) # No internal padding needed here

        # Configure columns within the button frame to have equal weight, making buttons expand
        folder_button_frame.columnconfigure((0, 1, 2, 3, 4, 5), weight=1) # Equal weight for buttons within the frame
        button_pady_reduced = 1
        button_padx_reduced = 3

        # Bind commands to methods on the app_instance
        # Buttons now use the modified Browse.TButton style for borders (defined in launcher.py)
        # Use sticky='ew' to make buttons fill their grid cells horizontally
        ttk.Button(folder_button_frame, text="Workflows", style='Browse.TButton', command=lambda: self.app.open_folder('workflows')).grid(row=0, column=0, padx=button_padx_reduced, pady=button_pady_reduced, sticky='ew')
        ttk.Button(folder_button_frame, text="Nodes", style='Browse.TButton', command=lambda: self.app.open_folder('nodes')).grid(row=0, column=1, padx=button_padx_reduced, pady=button_pady_reduced, sticky='ew')
        ttk.Button(folder_button_frame, text="Models", style='Browse.TButton', command=lambda: self.app.open_folder('models')).grid(row=0, column=2, padx=button_padx_reduced, pady=button_pady_reduced, sticky='ew')
        ttk.Button(folder_button_frame, text="Lora", style='Browse.TButton', command=lambda: self.app.open_folder('lora')).grid(row=0, column=3, padx=button_padx_reduced, pady=button_pady_reduced, sticky='ew')
        ttk.Button(folder_button_frame, text="Input", style='Browse.TButton', command=lambda: self.app.open_folder('input')).grid(row=0, column=4, padx=button_padx_reduced, pady=button_pady_reduced, sticky='ew')
        ttk.Button(folder_button_frame, text="Output", style='Browse.TButton', command=lambda: self.app.open_folder('output')).grid(row=0, column=5, padx=button_padx_reduced, pady=button_pady_reduced, sticky='ew')

        current_row += 1 # Increment row after adding the folder group


        # --- Basic Settings Group (Remains LabelFrame) ---
        basic_group = ttk.LabelFrame(self.frame, text=" 基本路径与端口 / Basic Paths & Ports ", padding=(10, 5))
        basic_group.grid(row=current_row, column=0, sticky="ew", padx=frame_padx, pady=frame_pady)
        basic_group.columnconfigure(1, weight=1) # Entry column expands
        basic_row = 0

        # ComfyUI Install Dir
        # Use app instance constant for style
        ttk.Label(basic_group, text="ComfyUI 安装目录:", anchor=tk.W, style='TLabel').grid(row=basic_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        # Use app instance constant for style
        dir_entry = ttk.Entry(basic_group, textvariable=self.app.comfyui_dir_var, style='TEntry')
        dir_entry.grid(row=basic_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx)
        # Bind browse command to app_instance method, using the modified Browse.TButton style
        dir_btn = ttk.Button(basic_group, text="浏览", width=6, style='Browse.TButton', command=lambda: self.app.browse_directory(self.app.comfyui_dir_var))
        dir_btn.grid(row=basic_row, column=2, sticky=tk.E, pady=widget_pady, padx=(0, widget_padx))
        basic_row += 1

        # ComfyUI Python Exe
        # Use app instance constant for style
        ttk.Label(basic_group, text="ComfyUI Python 路径:", anchor=tk.W, style='TLabel').grid(row=basic_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        # Use app instance constant for style
        py_entry = ttk.Entry(basic_group, textvariable=self.app.python_exe_var, style='TEntry')
        py_entry.grid(row=basic_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx)
        # Bind browse command to app_instance method, using the modified Browse.TButton style
        py_btn = ttk.Button(basic_group, text="浏览", width=6, style='Browse.TButton', command=lambda: self.app.browse_file(self.app.python_exe_var, [("Python Executable", "python.exe"), ("All Files", "*.*")]))
        py_btn.grid(row=basic_row, column=2, sticky=tk.E, pady=widget_pady, padx=(0, widget_padx))
        basic_row += 1

        # Git Exe Path
        # Use app instance constant for style
        ttk.Label(basic_group, text="Git 可执行文件路径:", anchor=tk.W, style='TLabel').grid(row=basic_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        # Use app instance constant for style
        git_entry = ttk.Entry(basic_group, textvariable=self.app.git_exe_path_var, style='TEntry')
        git_entry.grid(row=basic_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx)
        # Bind browse command to app_instance method, using the modified Browse.TButton style
        git_btn = ttk.Button(basic_group, text="浏览", width=6, style='Browse.TButton', command=lambda: self.app.browse_file(self.app.git_exe_path_var, [("Git Executable", "git.exe"), ("All Files", "*.*")]))
        git_btn.grid(row=basic_row, column=2, sticky=tk.E, pady=widget_pady, padx=(0, widget_padx))
        basic_row += 1

        # ComfyUI API Port
        port_frame = ttk.Frame(basic_group) # Frame to hold port entry and button
        port_frame.grid(row=basic_row, column=1, columnspan=2, sticky="ew") # Span entry and button columns
        port_frame.columnconfigure(0, weight=1) # Entry expands

        # Use app instance constant for style
        ttk.Label(basic_group, text="ComfyUI 监听与共享端口:", anchor=tk.W, style='TLabel').grid(row=basic_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        # Use app instance constant for style
        comfyui_port_entry = ttk.Entry(port_frame, textvariable=self.app.comfyui_api_port_var, width=10, style='TEntry') # Fixed width might be better here
        comfyui_port_entry.grid(row=0, column=0, sticky="w", pady=widget_pady, padx=widget_padx) # Align left, use west anchor
        # Bind open browser command to app_instance method, using the modified Browse.TButton style
        port_open_btn = ttk.Button(port_frame, text="打开", width=6, style='Browse.TButton', command=self.app._open_frontend_browser_from_settings)
        port_open_btn.grid(row=0, column=1, sticky="w", pady=widget_pady, padx=(0, widget_padx)) # Place button next to entry

        basic_row += 1
        current_row += 1

        # --- Performance Group ---
        perf_group = ttk.LabelFrame(self.frame, text=" 性能与显存优化 / Performance & VRAM Optimization ", padding=(10, 5))
        perf_group.grid(row=current_row, column=0, sticky="ew", padx=frame_padx, pady=frame_pady)
        perf_group.columnconfigure(1, weight=1)
        perf_row = 0

        # VRAM Mode
        # Use app instance constant for style
        ttk.Label(perf_group, text="显存优化:", anchor=tk.W, style='TLabel').grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        vram_modes = ["全负载(10GB以上)", "高负载(8GB以上)", "中负载(4GB以上)", "低负载(2GB以上)"]
        # Use app instance constant for style and textvariable
        vram_mode_combo = ttk.Combobox(perf_group, textvariable=self.app.vram_mode_var, values=vram_modes, style='TCombobox', state="readonly")
        vram_mode_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx)
        perf_row += 1

        # CKPT Precision
        # Use app instance constant for style
        ttk.Label(perf_group, text="CKPT模型精度:", anchor=tk.W, style='TLabel').grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        ckpt_precisions = ["全精度(FP32)", "半精度(FP16)"]
        # Use app instance constant for style and textvariable
        ckpt_precision_combo = ttk.Combobox(perf_group, textvariable=self.app.ckpt_precision_var, values=ckpt_precisions, style='TCombobox', state="readonly")
        ckpt_precision_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx)
        perf_row += 1

        # VAE Precision
        # Use app instance constant for style
        ttk.Label(perf_group, text="VAE模型精度:", anchor=tk.W, style='TLabel').grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        vae_precisions = ["全精度(FP32)", "半精度(FP16)", "半精度(BF16)"]
        # Use app instance constant for style and textvariable
        vae_precision_combo = ttk.Combobox(perf_group, textvariable=self.app.vae_precision_var, values=vae_precisions, style='TCombobox', state="readonly")
        vae_precision_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx)
        perf_row += 1


        # CLIP Precision
        # Use app instance constant for style
        ttk.Label(perf_group, text="CLIP编码精度:", anchor=tk.W, style='TLabel').grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        clip_precisions = ["全精度(FP32)", "半精度(FP16)", "FP8 (E4M3FN)", "FP8 (E5M2)"]
        # Use app instance constant for style and textvariable
        clip_precision_combo = ttk.Combobox(perf_group, textvariable=self.app.clip_precision_var, values=clip_precisions, style='TCombobox', state="readonly")
        clip_precision_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx)
        perf_row += 1

        # UNET Precision
        # Use app instance constant for style
        ttk.Label(perf_group, text="UNET模型精度:", anchor=tk.W, style='TLabel').grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        unet_precisions = ["半精度(BF16)", "半精度(FP16)", "FP8 (E4M3FN)", "FP8 (E5M2)"]
        # Use app instance constant for style and textvariable
        unet_precision_combo = ttk.Combobox(perf_group, textvariable=self.app.unet_precision_var, values=unet_precisions, style='TCombobox', state="readonly")
        unet_precision_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx)
        perf_row += 1

        # CUDA Malloc
        # Use app instance constant for style
        ttk.Label(perf_group, text="CUDA智能内存分配:", anchor=tk.W, style='TLabel').grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        cuda_malloc_options = ["启用", "禁用"]
        # Use app instance constant for style and textvariable
        cuda_malloc_combo = ttk.Combobox(perf_group, textvariable=self.app.cuda_malloc_var, values=cuda_malloc_options, style='TCombobox', state="readonly")
        cuda_malloc_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx)
        perf_row += 1

        # IPEX Optimization
        # Use app instance constant for style
        ttk.Label(perf_group, text="IPEX优化:", anchor=tk.W, style='TLabel').grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        ipex_options = ["启用", "禁用"]
        # Use app instance constant for style and textvariable
        ipex_combo = ttk.Combobox(perf_group, textvariable=self.app.ipex_optimization_var, values=ipex_options, style='TCombobox', state="readonly")
        ipex_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx)
        perf_row += 1

        # xformers Acceleration
        # Use app instance constant for style
        ttk.Label(perf_group, text="xformers加速:", anchor=tk.W, style='TLabel').grid(row=perf_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        xformers_options = ["启用", "禁用"]
        # Use app instance constant for style and textvariable
        xformers_combo = ttk.Combobox(perf_group, textvariable=self.app.xformers_acceleration_var, values=xformers_options, style='TCombobox', state="readonly")
        xformers_combo.grid(row=perf_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx)
        perf_row += 1

        current_row += 1
        self.frame.rowconfigure(current_row, weight=1) # Spacer row


# Function to be called by launcher.py to setup this tab
def setup_settings_tab(parent_frame, app_instance):
    """Entry point for the Settings tab module."""
    return SettingsTab(parent_frame, app_instance) # Return instance if needed, or just call init