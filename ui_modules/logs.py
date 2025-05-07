# -*- coding: utf-8 -*-
# File: ui_modules/logs.py
# Version: Kerry, Ver. 2.6.1 - Logs Tab Module

import tkinter as tk
from tkinter import ttk, scrolledtext
# setup_text_tags is accessed via app_instance

class LogsTab:
    """Handles the UI for the Logs tab."""
    def __init__(self, parent_frame, app_instance):
        """
        Initializes the Logs tab UI elements.

        Args:
            parent_frame: The ttk.Frame widget that serves as the parent for this tab's content.
            app_instance: The main ComLauncherApp instance to access shared resources.
        """
        self.app = app_instance # Store reference to the main application instance
        self.frame = parent_frame

        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)

        self._setup_ui() # Build the UI for this tab

    def _setup_ui(self):
        """Builds the UI elements for the Logs tab."""
        # Sub-notebook for Launcher and ComfyUI logs
        self.logs_notebook = ttk.Notebook(self.frame, style='TNotebook')
        self.logs_notebook.grid(row=0, column=0, sticky="nsew")
        self.logs_notebook.enable_traversal()

        # ComLauncher Log Sub-tab
        launcher_log_frame = ttk.Frame(self.logs_notebook, style='Logs.TFrame', padding=0)
        launcher_log_frame.columnconfigure(0, weight=1); launcher_log_frame.rowconfigure(0, weight=1)
        self.logs_notebook.add(launcher_log_frame, text=' ComLauncher日志 / Launcher Logs ')
        # Pass widget references back to app_instance for log processing
        self.app.launcher_log_text = scrolledtext.ScrolledText(launcher_log_frame, wrap=tk.WORD, state=tk.DISABLED, font=(self.app.FONT_FAMILY_MONO, self.app.FONT_SIZE_MONO), bg=self.app.TEXT_AREA_BG, fg=self.app.FG_STDOUT, relief=tk.FLAT, borderwidth=1, bd=1, highlightthickness=1, highlightbackground=self.app.BORDER_COLOR, insertbackground="white")
        self.app.launcher_log_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.app.setup_text_tags(self.app.launcher_log_text) # Apply color tags using app's method

        # ComfyUI Log Sub-tab
        comfyui_log_frame = ttk.Frame(self.logs_notebook, style='Logs.TFrame', padding=0)
        comfyui_log_frame.columnconfigure(0, weight=1); comfyui_log_frame.rowconfigure(0, weight=1)
        self.logs_notebook.add(comfyui_log_frame, text=' ComfyUI日志 / ComfyUI Logs ')
        # Pass widget references back to app_instance for log processing
        self.app.main_output_text = scrolledtext.ScrolledText(comfyui_log_frame, wrap=tk.WORD, state=tk.DISABLED, font=(self.app.FONT_FAMILY_MONO, self.app.FONT_SIZE_MONO), bg=self.app.TEXT_AREA_BG, fg=self.app.FG_STDOUT, relief=tk.FLAT, borderwidth=1, bd=1, highlightthickness=1, highlightbackground=self.app.BORDER_COLOR, insertbackground="white")
        self.app.main_output_text.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.app.setup_text_tags(self.app.main_output_text) # Apply color tags using app's method

        # Store notebook reference in app_instance for switching tabs
        self.app.logs_notebook = self.logs_notebook


# Function to be called by launcher.py to setup this tab
def setup_logs_tab(parent_frame, app_instance):
    """Entry point for the Logs tab module."""
    return LogsTab(parent_frame, app_instance) # Return instance (optional)