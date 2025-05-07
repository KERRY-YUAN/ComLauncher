# -*- coding: utf-8 -*-
# File: ui_modules/management.py
# Version: Kerry, Ver. 2.6.2 - Management Tab Module (Fixed Bugs + Node Double Click)

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, Toplevel, font as tkfont # Import Toplevel for modal window
import os
import threading
import queue
import time
import json
import shlex
import shutil
import platform
import sys
from datetime import datetime, timezone
from functools import cmp_to_key
import requests # Import requests for _fetch_online_node_config

# Attempt to import packaging for version parsing, allow fallback
try:
    from packaging.version import parse as parse_version, InvalidVersion
except ImportError:
    print("[Management Module WARNING] 'packaging' library not found. Version sorting fallback will be basic string comparison.")
    parse_version = None
    InvalidVersion = Exception

# Note: Styling constants, setup_text_tags, and sorting helpers
# are now accessed via the app_instance.
# _parse_iso_date_for_sort, _parse_version_string_for_sort, _compare_versions_for_sort
# are methods of the main ComLauncherApp and will be called via self.app.method_name

class ManagementTab:
    """Handles the UI and logic for the Management tab (Updates and Nodes)."""
    def __init__(self, parent_frame, app_instance):
        """
        Initializes the Management tab UI elements.

        Args:
            parent_frame: The ttk.Frame widget that serves as the parent for this tab's content.
            app_instance: The main ComLauncherApp instance to access shared resources.
        """
        self.app = app_instance
        self.frame = parent_frame

        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(1, weight=1)

        self.all_known_nodes = []
        self.local_nodes_only = []
        self.remote_main_body_versions = []

        # Modal state variables (kept within this module instance)
        self._node_history_modal_versions_data = []
        self._node_history_modal_node_name = ""
        self._node_history_modal_node_path = ""
        self._node_history_modal_current_commit = ""
        self._node_history_modal_window = None

        # UI widget references needed for state updates/logic from launcher
        self.main_body_tree = None
        self.nodes_tree = None
        self.nodes_search_entry = None
        # Removed current_main_body_version_label as it's on the app instance
        self.refresh_main_body_button = None
        self.activate_main_body_button = None
        self.search_nodes_button = None
        self.refresh_nodes_button = None
        self.switch_install_node_button = None
        self.uninstall_node_button = None
        self.update_all_nodes_button = None

        # Persistence file paths relative to ui_modules directory (Correct path)
        self.MAIN_BODY_VERSIONS_FILE = os.path.join(self.app.base_project_dir, "ui_modules", "main_body_versions.json")
        self.NODES_LIST_FILE = os.path.join(self.app.base_project_dir, "ui_modules", "nodes_list.json")

        self._setup_ui()
        self._load_state() # Load persisted data on initialization


    def _setup_ui(self):
        """Builds the UI elements for the Management tab."""
        current_row = 0
        frame_padx = 5
        frame_pady = (0, 10) # Added bottom padding to groups
        widget_pady = 3
        widget_padx = 5

        # --- Repository Address Area ---
        repo_address_group = ttk.LabelFrame(self.frame, text=" 仓库地址 / Repository Address ", padding=(10, 5))
        repo_address_group.grid(row=current_row, column=0, sticky="ew", padx=frame_padx, pady=frame_pady)
        repo_address_group.columnconfigure(1, weight=1)
        repo_row = 0
        ttk.Label(repo_address_group, text="本体仓库地址:", anchor=tk.W).grid(row=repo_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        # Bind textvariable to app_instance's StringVar
        main_repo_entry = ttk.Entry(repo_address_group, textvariable=self.app.main_repo_url_var)
        main_repo_entry.grid(row=repo_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx)
        repo_row += 1
        ttk.Label(repo_address_group, text="节点配置地址:", anchor=tk.W).grid(row=repo_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        # Bind textvariable to app_instance's StringVar
        node_config_entry = ttk.Entry(repo_address_group, textvariable=self.app.node_config_url_var)
        node_config_entry.grid(row=repo_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx)
        repo_row += 1

        current_row += 1

        # --- Version & Node Management Area ---
        version_node_management_group = ttk.LabelFrame(self.frame, text=" 版本与节点管理 / Version & Node Management ", padding=(10, 5))
        version_node_management_group.grid(row=current_row, column=0, sticky="nsew", padx=frame_padx, pady=frame_pady)
        version_node_management_group.columnconfigure(0, weight=1)
        version_node_management_group.rowconfigure(0, weight=1)

        # Sub-notebook for 本体 and 节点
        node_notebook = ttk.Notebook(version_node_management_group, style='TNotebook')
        node_notebook.grid(row=0, column=0, sticky="nsew")
        node_notebook.enable_traversal()

        # --- 本体 Sub-tab ---
        self.main_body_frame = ttk.Frame(node_notebook, style='TFrame', padding=5)
        self.main_body_frame.columnconfigure(0, weight=1)
        self.main_body_frame.rowconfigure(1, weight=1) # Treeview expands
        node_notebook.add(self.main_body_frame, text=' 本体 / Main Body ')

        main_body_control_frame = ttk.Frame(self.main_body_frame, style='TabControl.TFrame', padding=(5, 5))
        main_body_control_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5), columnspan=2) # Span scrollbar too
        main_body_control_frame.columnconfigure(1, weight=1) # Spacer

        ttk.Label(main_body_control_frame, text="当前本体版本:", style='TLabel').grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        # Bind textvariable to app_instance's StringVar
        self.current_main_body_version_label = ttk.Label(main_body_control_frame, textvariable=self.app.current_main_body_version_var, style='TLabel', anchor=tk.W, font=(self.app.FONT_FAMILY_UI, self.app.FONT_SIZE_NORMAL, self.app.FONT_WEIGHT_BOLD)) # Use self.app
        self.current_main_body_version_label.grid(row=0, column=0, sticky=tk.W, padx=(90, 5))
        ttk.Label(main_body_control_frame, text="", style='TLabel').grid(row=0, column=1, sticky="ew") # Spacer

        # Bind commands to app_instance methods
        self.refresh_main_body_button = ttk.Button(main_body_control_frame, text="刷新版本", style="Tab.TButton", command=self.app._queue_main_body_refresh)
        self.refresh_main_body_button.grid(row=0, column=2, padx=(0, 5))
        self.activate_main_body_button = ttk.Button(main_body_control_frame, text="激活选中版本", style="TabAccent.TButton", command=self.app._queue_main_body_activation)
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
        self.main_body_tree.bind("<<TreeviewSelect>>", lambda event: self.app._update_ui_state())
        try: # Use app constants for tag configuration
             self.main_body_tree.tag_configure('highlight', foreground=self.app.FG_HIGHLIGHT, font=(self.app.FONT_FAMILY_UI, self.app.FONT_SIZE_NORMAL, self.app.FONT_WEIGHT_BOLD))
             self.main_body_tree.tag_configure('persisted', foreground=self.app.FG_MUTED) # Tag for items loaded from persistence
        except tk.TclError:
             pass


        # --- 节点 Sub-tab ---
        self.nodes_frame = ttk.Frame(node_notebook, style='TFrame', padding=5)
        self.nodes_frame.columnconfigure(0, weight=1)
        self.nodes_frame.rowconfigure(2, weight=1) # Treeview expands
        node_notebook.add(self.nodes_frame, text=' 节点 / Nodes ')

        # Nodes Search and Control
        nodes_control_frame = ttk.Frame(self.nodes_frame, style='TabControl.TFrame', padding=(5, 5))
        nodes_control_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5), columnspan=2) # Span scrollbar too

        # Search box and button on the left
        search_frame = ttk.Frame(nodes_control_frame, style='TabControl.TFrame')
        search_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.nodes_search_entry = ttk.Entry(search_frame, width=40)
        self.nodes_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        # Bind commands to app_instance methods
        self.search_nodes_button = ttk.Button(search_frame, text="搜索", style="Tab.TButton", command=self.app._queue_node_list_refresh)
        self.search_nodes_button.pack(side=tk.LEFT, padx=(5, 0))

        # Other buttons on the right
        nodes_buttons_container = ttk.Frame(nodes_control_frame, style='TabControl.TFrame')
        nodes_buttons_container.pack(side=tk.RIGHT)
        self.refresh_nodes_button = ttk.Button(nodes_buttons_container, text="刷新列表", style="Tab.TButton", command=self.app._queue_node_list_refresh)
        self.refresh_nodes_button.pack(side=tk.LEFT, padx=(0, 5))
        # MOD2: Command for the '切换版本' button modified to trigger history fetch or install (calls app_instance)
        self.switch_install_node_button = ttk.Button(nodes_buttons_container, text="切换版本", style="Tab.TButton", command=self.app._queue_node_switch_or_show_history) # Modified command
        self.switch_install_node_button.pack(side=tk.LEFT, padx=5)
        self.uninstall_node_button = ttk.Button(nodes_buttons_container, text="卸载节点", style="Tab.TButton", command=self.app._queue_node_uninstall)
        self.uninstall_node_button.pack(side=tk.LEFT, padx=5)
        self.update_all_nodes_button = ttk.Button(nodes_buttons_container, text="更新全部", style="TabAccent.TButton", command=self.app._queue_all_nodes_update)
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
        try: # Use app constants for tag configuration
            self.nodes_tree.tag_configure('installed', foreground=self.app.FG_INFO)
            self.nodes_tree.tag_configure('not_installed', foreground=self.app.FG_MUTED)
            self.nodes_tree.tag_configure('persisted', foreground=self.app.FG_MUTED) # Tag for items loaded from persistence
        except tk.TclError:
            pass
        self.nodes_tree.bind("<<TreeviewSelect>>", lambda event: self.app._update_ui_state())
        # MOD4: Bind double-click to trigger the same action as the button
        self.nodes_tree.bind("<Double-1>", lambda event: self.app._queue_node_switch_or_show_history())
        self.nodes_search_entry.bind("<KeyRelease>", lambda event: self.app._update_ui_state())


    # --- Persistence Handling ---
    def _load_state(self):
        """Loads main body versions and node list from persistence files."""
        self.app.log_to_gui("Management", "尝试加载持久化数据...", "info")
        try:
            os.makedirs(os.path.dirname(self.MAIN_BODY_VERSIONS_FILE), exist_ok=True)
            os.makedirs(os.path.dirname(self.NODES_LIST_FILE), exist_ok=True)

            # Load Main Body Versions
            if os.path.exists(self.MAIN_BODY_VERSIONS_FILE):
                try:
                    with open(self.MAIN_BODY_VERSIONS_FILE, 'r', encoding='utf-8') as f:
                        self.remote_main_body_versions = json.load(f)
                    self.app.log_to_gui("Management", f"从 {self.MAIN_BODY_VERSIONS_FILE} 加载了 {len(self.remote_main_body_versions)} 条本体版本数据。", "info")
                    # Populate Treeview immediately in the GUI thread
                    self.app.root.after(0, lambda list_to_populate=self.remote_main_body_versions: self._populate_main_body_treeview(list_to_populate, persisted=True))
                except (json.JSONDecodeError, IOError, OSError) as e:
                    self.app.log_to_gui("Management", f"加载本体版本持久化文件时出错: {e}", "error")
                    self.remote_main_body_versions = [] # Clear on error
                    self.app.root.after(0, lambda list_to_populate=[]: self._populate_main_body_treeview(list_to_populate, persisted=True))
            else:
                self.app.log_to_gui("Management", f"本体版本持久化文件 {self.MAIN_BODY_VERSIONS_FILE} 未找到。", "warn")
                self.remote_main_body_versions = []
                self.app.root.after(0, lambda list_to_populate=[]: self._populate_main_body_treeview(list_to_populate, persisted=True))


            # Load Nodes List
            if os.path.exists(self.NODES_LIST_FILE):
                try:
                    with open(self.NODES_LIST_FILE, 'r', encoding='utf-8') as f:
                        loaded_data = json.load(f)
                        if isinstance(loaded_data, dict):
                             self.local_nodes_only = loaded_data.get('local_nodes_only', [])
                             self.all_known_nodes = loaded_data.get('all_known_nodes', [])
                        else:
                             self.app.log_to_gui("Management", f"节点列表持久化文件 {self.NODES_LIST_FILE} 格式无效，无法加载。", "warn")
                             self.local_nodes_only = []
                             self.all_known_nodes = []

                    self.app.log_to_gui("Management", f"从 {self.NODES_LIST_FILE} 加载了 {len(self.local_nodes_only)} 条本地节点和 {len(self.all_known_nodes)} 条全部节点数据。", "info")

                    # Populate Treeview immediately in the GUI thread based on initial search term (usually empty)
                    search_term_value = ""
                    try:
                        if self.nodes_search_entry and self.nodes_search_entry.winfo_exists():
                            search_term_value = self.nodes_search_entry.get().strip().lower()
                    except tk.TclError:
                        pass

                    # Apply initial filter (empty search shows local only)
                    filtered_nodes = sorted(self.local_nodes_only, key=lambda x: x.get('name', '').lower()) if search_term_value == "" else sorted([
                        node for node in self.all_known_nodes
                        if search_term_value in node.get('name', '').lower() or \
                           search_term_value in node.get('repo_url', '').lower() or \
                           search_term_value in node.get('status', '').lower()
                    ], key=lambda x: x.get('name', '').lower())
                    self.app.root.after(0, lambda list_to_populate=filtered_nodes: self._populate_nodes_treeview(list_to_populate, persisted=True))

                except (json.JSONDecodeError, IOError, OSError) as e:
                     self.app.log_to_gui("Management", f"加载节点列表持久化文件时出错: {e}", "error")
                     self.local_nodes_only = [] # Clear on error
                     self.all_known_nodes = []   # Clear on error
                     self.app.root.after(0, lambda list_to_populate=[]: self._populate_nodes_treeview(list_to_populate, persisted=True))

            else:
                self.app.log_to_gui("Management", f"节点列表持久化文件 {self.NODES_LIST_FILE} 未找到。", "warn")
                self.local_nodes_only = []
                self.all_known_nodes = []
                self.app.root.after(0, lambda list_to_populate=[]: self._populate_nodes_treeview(list_to_populate, persisted=True))

        except Exception as e:
            self.app.log_to_gui("Management", f"加载持久化数据时发生意外错误: {e}", "error")
            # Clear data and populate empty treeviews on unexpected error
            self.remote_main_body_versions = []
            self.local_nodes_only = []
            self.all_known_nodes = []
            self.app.root.after(0, lambda: [
                 self._populate_main_body_treeview([], persisted=True),
                 self._populate_nodes_treeview([], persisted=True)
            ])

        # Trigger a UI state update after initial data loading (Bug 3 Fix)
        self.app.root.after(0, self.app._update_ui_state)
        self.app.log_to_gui("Management", "持久化数据加载完成，触发 UI 状态更新。", "info")


    def _save_state(self):
        """Saves the current main body versions and node lists to persistence files."""
        try:
            # Ensure the ui_modules directory exists
            os.makedirs(os.path.dirname(self.MAIN_BODY_VERSIONS_FILE), exist_ok=True)

            # Save Main Body Versions
            with open(self.MAIN_BODY_VERSIONS_FILE, 'w', encoding='utf-8') as f:
                # Ensure list is serializable (contains only basic types)
                json.dump(self.remote_main_body_versions, f, indent=4, ensure_ascii=False)
            self.app.log_to_gui("Management", f"本体版本数据已保存到 {self.MAIN_BODY_VERSIONS_FILE}", "info")

            # Save Nodes List
            os.makedirs(os.path.dirname(self.NODES_LIST_FILE), exist_ok=True)
            nodes_save_data = {
                 'local_nodes_only': self.local_nodes_only,
                 'all_known_nodes': self.all_known_nodes
            }
            with open(self.NODES_LIST_FILE, 'w', encoding='utf-8') as f:
                # Ensure list is serializable
                json.dump(nodes_save_data, f, indent=4, ensure_ascii=False)
            self.app.log_to_gui("Management", f"节点列表数据已保存到 {self.NODES_LIST_FILE}", "info")

        except Exception as e:
            self.app.log_to_gui("Management", f"保存持久化文件时出错: {e}", "error")


    # --- Treeview Population Helpers (Run in GUI thread via app.root.after) ---
    def _populate_main_body_treeview(self, versions_list, persisted=False):
         """Populates the main body Treeview from a list of version data."""
         # Safely check if the Treeview widget exists
         if not self.main_body_tree or not self.main_body_tree.winfo_exists():
              return
         try:
              # Delete existing items safely
              for item in self.main_body_tree.get_children():
                  self.main_body_tree.delete(item)

              if not versions_list:
                   display_message = "未获取到本体版本信息" if not persisted else "从持久化文件加载失败或无数据"
                   self.main_body_tree.insert("", tk.END, values=("", display_message, "", ""))
                   return

              # Get current local commit ID safely via app instance method
              current_local_commit = self.app._get_current_local_main_body_commit()

              for ver_data in versions_list:
                  # Ensure keys exist with default empty strings if missing
                  ver_data.setdefault('type', '未知')
                  ver_data.setdefault('name', 'N/A')
                  ver_data.setdefault('commit_id', 'N/A')
                  ver_data.setdefault('date_iso', '')
                  ver_data.setdefault('description', 'N/A')

                  version_display = f"{ver_data['type']} / {ver_data['name']}"
                  commit_display = ver_data.get("commit_id", "N/A")[:8] # Display short ID

                  # Parse date safely via app instance method
                  date_obj = self.app._parse_iso_date_for_sort(ver_data['date_iso'])
                  date_display = date_obj.strftime('%Y-%m-%d') if date_obj else ("解析失败" if ver_data['date_iso'] else "无日期") # Display "日期解析失败" or "无日期"

                  description_display = ver_data['description']

                  # Check if this version is the current local commit (using full ID)
                  tags = ()
                  if current_local_commit and ver_data.get('commit_id') == current_local_commit:
                       tags += ('highlight',)
                  # Add tag for items loaded from persistence
                  if persisted:
                       tags += ('persisted',)


                  # Insert item into Treeview
                  self.main_body_tree.insert("", tk.END, values=(version_display, commit_display, date_display, description_display), tags=tags)

              self.app.log_to_gui("Management", f"本体版本列表已在 GUI 中显示 ({len(versions_list)} 条)。", "info")

         except tk.TclError as e:
             self.app.log_to_gui("Management", f"TclError populating main body treeview: {e}", "error")
         except Exception as e:
             self.app.log_to_gui("Management", f"意外错误 populating main body treeview: {e}", "error")


    def _populate_nodes_treeview(self, nodes_list, persisted=False):
         """Populates the nodes Treeview from a list of node data."""
         # Safely check if the Treeview widget exists
         if not self.nodes_tree or not self.nodes_tree.winfo_exists():
              return
         try:
              # Delete existing items safely
              for item in self.nodes_tree.get_children():
                  self.nodes_tree.delete(item)

              if not nodes_list:
                  # Safely get search term
                  search_term_value = ""
                  try:
                      if self.nodes_search_entry and self.nodes_search_entry.winfo_exists():
                           search_term_value = self.nodes_search_entry.get().strip()
                  except tk.TclError:
                      pass
                  # Display message based on search term or persistence state
                  display_message = "未找到匹配的节点" if search_term_value else ("未找到本地节点" if not persisted else "从持久化文件加载失败或无数据")
                  self.nodes_tree.insert("", tk.END, values=("", display_message, "", "", ""))
                  return

              for node_data in nodes_list:
                  # Ensure keys exist with default empty strings if missing
                  node_data.setdefault("name", "N/A")
                  node_data.setdefault("status", "未知")
                  node_data.setdefault("local_id", "N/A")
                  node_data.setdefault("repo_info", "N/A")
                  node_data.setdefault("repo_url", "N/A")
                  # Internal fields used during scanning/fetching, not displayed directly in columns
                  node_data.setdefault("is_git", False)
                  node_data.setdefault("local_commit_full", None)
                  node_data.setdefault("remote_branch", None)


                  tags = ()
                  if node_data.get('status') == '已安装':
                      tags += ('installed',)
                  else:
                      tags += ('not_installed',)
                  # Add tag for items loaded from persistence
                  if persisted:
                      tags += ('persisted',)

                  # Insert item into Treeview
                  self.nodes_tree.insert("", tk.END, values=(
                       node_data.get("name", "N/A"),
                       node_data.get("status", "未知"),
                       node_data.get("local_id", "N/A"), # Display short ID
                       node_data.get("repo_info", "N/A"),
                       node_data.get("repo_url", "N/A")
                  ), tags=tags)

              self.app.log_to_gui("Management", f"节点列表已在 GUI中显示 ({len(nodes_list)} 条)。", "info")

         except tk.TclError as e:
             self.app.log_to_gui("Management", f"TclError populating nodes treeview: {e}", "error")
         except Exception as e:
             self.app.log_to_gui("Management", f"意外错误 populating nodes treeview: {e}", "error")


    # --- Git Execution Helper (Accessed via app._run_git_command) ---
    # Moved to launcher.py

    # --- Update Task Implementations (Executed in Worker Thread) ---

    # Called by app._run_initial_background_tasks and app._queue_main_body_refresh
    def refresh_main_body_versions(self):
        """Fetches and displays ComfyUI main body versions using Git. Runs in worker thread."""
        if self.app.stop_event_set(): # Use the getter method
             self.app.log_to_gui("Management", "本体版本刷新任务已取消 (停止信号)。", "warn")
             return
        self.app.log_to_gui("Management", "刷新本体版本列表...", "info")

        main_repo_url = self.app.main_repo_url_var.get()
        comfyui_dir = self.app.comfyui_dir_var.get()
        # Validate paths using app instance method
        git_path_ok = self.app._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=False)
        is_git_repo = git_path_ok and comfyui_dir and os.path.isdir(comfyui_dir) and os.path.isdir(os.path.join(comfyui_dir, ".git"))

        # Clear existing list in GUI thread before starting fetch
        self.app.root.after(0, lambda: [self.main_body_tree.delete(item) for item in self.main_body_tree.get_children()])
        self.remote_main_body_versions = [] # Clear stored data

        # Get Current Local Version
        local_version_display = "未知 / Unknown"
        current_local_commit = None
        if is_git_repo:
             # Use app instance method for git command
             stdout_id_full, _, rc_full = self.app._run_git_command(["rev-parse", "HEAD"], cwd=comfyui_dir, timeout=10, log_output=False)
             if rc_full == 0 and stdout_id_full:
                  current_local_commit = stdout_id_full.strip() # Store full ID
                  stdout_id_short = current_local_commit[:8] # Display short ID
                  local_version_display = f"本地 Commit: {stdout_id_short}"

                  # Try to find a symbolic ref (branch/tag) if HEAD is not detached
                  stdout_sym_ref, _, rc_sym_ref = self.app._run_git_command(["symbolic-ref", "-q", "--short", "HEAD"], cwd=comfyui_dir, timeout=5, log_output=False)
                  if rc_sym_ref == 0 and stdout_sym_ref:
                       local_version_display = f"本地 Branch: {stdout_sym_ref.strip()} ({stdout_id_short})"
                  else: # If detached HEAD, try describe
                       stdout_desc, _, rc_desc = self.app._run_git_command(["describe", "--all", "--long", "--always"], cwd=comfyui_dir, timeout=10, log_output=False)
                       if rc_desc == 0 and stdout_desc:
                            local_version_display = f"本地: {stdout_desc.strip()}"

             else:
                  local_version_display = "读取本地版本失败"
                  self.app.log_to_gui("Management", "无法获取本地本体版本信息。", "warn")
        else:
             local_version_display = "非 Git 仓库或路径无效"

        # Update the StringVar on the app instance in the GUI thread
        self.app.root.after(0, lambda lv=local_version_display: self.app.current_main_body_version_var.set(lv))

        if self.app.stop_event_set(): # Use the getter method
            self.app.log_to_gui("Management", "本体版本刷新任务已取消 (停止信号)。", "warn")
            return

        # Fetch Remote Versions
        all_versions = []
        if is_git_repo and main_repo_url:
             self.app.log_to_gui("Management", f"尝试从 {main_repo_url} 刷新远程版本列表...", "info")
             # Ensure origin remote exists and points to the correct URL
             stdout_get_url, _, rc_get_url = self.app._run_git_command(["remote", "get-url", "origin"], cwd=comfyui_dir, timeout=10, log_output=False) # No logging here
             current_url = stdout_get_url.strip() if rc_get_url == 0 else None

             if not current_url:
                  self.app.log_to_gui("Management", f"远程 'origin' 不存在，尝试添加...", "info")
                  _, stderr_add, rc_add = self.app._run_git_command(["remote", "add", "origin", main_repo_url], cwd=comfyui_dir, timeout=15)
                  if rc_add != 0:
                      self.app.log_to_gui("Management", f"添加远程 'origin' 失败: {stderr_add.strip()}", "error")
             elif current_url != main_repo_url:
                  self.app.log_to_gui("Management", f"远程 'origin' URL 不匹配 ({current_url}), 尝试设置新 URL...", "warn")
                  _, stderr_set, rc_set = self.app._run_git_command(["remote", "set-url", "origin", main_repo_url], cwd=comfyui_dir, timeout=15)
                  if rc_set != 0:
                      self.app.log_to_gui("Management", f"设置远程 'origin' URL 失败: {stderr_set.strip()}", "error")

             if self.app.stop_event_set(): # Use the getter method
                 self.app.log_to_gui("Management", "本体版本刷新任务已取消 (停止信号)。", "warn")
                 return

             self.app.log_to_gui("Management", "执行 Git fetch origin --prune --tags -f...", "info")
             _, stderr_fetch, rc_fetch = self.app._run_git_command(["fetch", "origin", "--prune", "--tags", "-f"], cwd=comfyui_dir, timeout=180)
             if rc_fetch != 0:
                  self.app.log_to_gui("Management", f"Git fetch 失败: {stderr_fetch.strip()}", "error")
                  # Populate Treeview with error message in GUI thread
                  self.app.root.after(0, lambda: self._populate_main_body_treeview([{"name":"获取失败", "commit_id":"", "date_iso":"", "description":"无法获取远程版本信息"}]))
                  self.remote_main_body_versions = [] # Clear stored data on error
                  self._save_state() # Save empty or error state
                  return

             if self.app.stop_event_set(): # Use the getter method
                 self.app.log_to_gui("Management", "本体版本刷新任务已取消 (停止信号)。", "warn")
                 return

             # Get remote branches and tags with commit hash, date, and subject
             # Using separate commands for clarity and easier parsing
             # Format: %(refname:short) %(objectname) %(committerdate:iso-strict) %(contents:subject)

             # Get remote branches
             self.app.log_to_gui("Management", "获取远程分支信息...", "info")
             # Use app instance method
             branches_output, _, _ = self.app._run_git_command(
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


             if self.app.stop_event_set(): # Use the getter method
                 self.app.log_to_gui("Management", "本体版本刷新任务已取消 (停止信号)。", "warn")
                 return

             # Get tags
             self.app.log_to_gui("Management", "获取标签信息...", "info")
             # Use app instance method
             tags_output, _, _ = self.app._run_git_command(
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
                     self.app.log_to_gui("Management", "获取当前本地 Commit 信息...", "info")
                     # Use app instance method
                     head_date_stdout, _, rc_head_date = self.app._run_git_command(["log", "-1", "--format=%ci", "HEAD"], cwd=comfyui_dir, timeout=5, log_output=False)
                     head_subject_stdout, _, rc_head_subject = self.app._run_git_command(["log", "-1", "--format=%s", "HEAD"], cwd=comfyui_dir, timeout=5, log_output=False)

                     head_date_iso = head_date_stdout.strip() if rc_head_date == 0 else None
                     head_description = head_subject_stdout.strip() if rc_head_subject == 0 else "当前工作目录"

                     # Try to parse date, fallback to now if failed using app instance method
                     date_obj = self.app._parse_iso_date_for_sort(head_date_iso)
                     final_date_iso = date_obj.isoformat() if date_obj else datetime.now(timezone.utc).isoformat()

                     # Determine type (detached HEAD or local branch not tracking remote)
                     head_sym_ref_out, _, rc_head_sym_ref = self.app._run_git_command(["symbolic-ref", "-q", "--short", "HEAD"], cwd=comfyui_dir, timeout=2, log_output=False)
                     head_type = "commit (HEAD)" if rc_head_sym_ref != 0 else "branch (local)"
                     head_name = head_sym_ref_out.strip() if head_type == "branch (local)" else f"Detached at {current_local_commit[:8]}"


                     all_versions.append({"type": head_type, "name": head_name, "commit_id": current_local_commit, "date_iso": final_date_iso, "description": head_description})
                     self.app.log_to_gui("Management", f"添加当前本地 HEAD ({current_local_commit[:8]}) 到列表。", "info")

                 else:
                     self.app.log_to_gui("Management", "当前本地 Commit 与远程已同步或已在列表中。", "info")


             # Sort the combined list (MOD1: Using custom comparison via app instance method)
             all_versions.sort(key=cmp_to_key(self.app._compare_versions_for_sort))

        else:
             self.app.log_to_gui("Management", "无法获取远程版本信息 (非Git仓库或缺少URL)。", "warn")
             # Populate Treeview with info message in GUI thread
             self.app.root.after(0, lambda: self._populate_main_body_treeview([{"name":"无远程信息", "commit_id":"", "date_iso":"", "description":""}]))
             self.remote_main_body_versions = [] # Ensure list is empty if no remote info
             self._save_state() # Save empty state
             self.app.log_to_gui("Management", "本体版本列表刷新完成 (无远程信息)。", "info")
             return # Exit the task if no remote info


        self.remote_main_body_versions = all_versions # Store fetched data
        self._save_state() # Save the fetched data

        # Populate the Treeview in the GUI thread
        self.app.root.after(0, lambda list_to_populate=all_versions: self._populate_main_body_treeview(list_to_populate))

        self.app.log_to_gui("Management", f"本体版本列表刷新完成。找到 {len(all_versions)} 条记录。", "info")


    # Called by app._queue_main_body_activation
    def _activate_main_body_version_task(self, comfyui_dir, target_ref): # Renamed target_commit_id to target_ref
        """Task to execute git commands for activating main body version. Runs in worker thread."""
        if self.app.stop_event_set(): # Use the getter method
            self.app.log_to_gui("Management", "本体版本激活任务已取消 (停止信号)。", "warn")
            return
        self.app.log_to_gui("Management", f"正在激活本体版本 (引用: {target_ref[:8]})...", "info") # Use short ref for logging

        try:
            # 1. Check for stop event
            if self.app.stop_event_set():
                raise threading.ThreadExit

            # 2. Check for local changes and reset hard
            stdout_status, _, _ = self.app._run_git_command(["status", "--porcelain"], cwd=comfyui_dir, timeout=10, log_output=False) # No logging status unless needed
            if stdout_status.strip():
                 self.app.log_to_gui("Management", "检测到本体目录存在未提交的本地修改，将通过 reset --hard 覆盖。", "warn")
                 self.app.log_to_gui("Management", "执行 Git reset --hard...", "info")
                 # Use app instance method
                 _, stderr_reset, rc_reset = self.app._run_git_command(["reset", "--hard"], cwd=comfyui_dir, timeout=30)
                 if rc_reset != 0:
                     # This might be a problem, but checkout --force might still work. Log warning.
                     self.app.log_to_gui("Management", f"Git reset --hard 失败: {stderr_reset.strip()}", "warn")


            if self.app.stop_event_set():
                raise threading.ThreadExit

            # 3. Checkout target commit/ref
            # Use checkout --force to handle local changes and ensure the target ref is checked out
            self.app.log_to_gui("Management", f"执行 Git checkout --force {target_ref[:8]}...", "info")
            # Use app instance method for git command
            _, stderr_checkout, rc_checkout = self.app._run_git_command(["checkout", "--force", target_ref], cwd=comfyui_dir, timeout=60)
            if rc_checkout != 0:
                # If checkout fails, the most likely reason is the ref doesn't exist *locally* after fetch.
                # Report error and exit the task.
                raise Exception(f"Git checkout --force 失败: {stderr_checkout.strip()}")

            self.app.log_to_gui("Management", f"Git checkout 完成 (引用: {target_ref[:8]}).", "info")

            if self.app.stop_event_set():
                raise threading.ThreadExit

            # 4. Update submodules
            if os.path.exists(os.path.join(comfyui_dir, ".gitmodules")):
                 self.app.log_to_gui("Management", "执行 Git submodule update...", "info")
                 # Use --init and --recursive --force together
                 # Use app instance method for git command
                 _, stderr_sub, rc_sub = self.app._run_git_command(["submodule", "update", "--init", "--recursive", "--force"], cwd=comfyui_dir, timeout=180)
                 if rc_sub != 0:
                     self.app.log_to_gui("Management", f"Git submodule update 失败: {stderr_sub.strip()}", "warn") # Warn only

            if self.app.stop_event_set():
                raise threading.ThreadExit

            # 5. Re-install Python dependencies
            python_exe = self.app.python_exe_var.get()
            requirements_path = os.path.join(comfyui_dir, "requirements.txt")
            if python_exe and os.path.isfile(python_exe) and os.path.isfile(requirements_path):
                 self.app.log_to_gui("Management", "执行 pip 安装依赖...", "info")
                 pip_cmd_base = [python_exe, "-m", "pip", "install", "-r", requirements_path, "--upgrade"]
                 # Conditional extra index URLs based on platform/needs (adjust if needed)
                 pip_cmd_extras = []
                 # Example: Add cu118 or cu121 index based on detected CUDA or user preference
                 # For simplicity, keep the current approach of adding both as extras
                 pip_cmd_extras.extend(["--extra-index-url", "https://download.pytorch.org/whl/cu118", "--extra-index-url", "https://download.pytorch.org/whl/cu121"])

                 pip_cmd = pip_cmd_base + pip_cmd_extras
                 is_venv = sys.prefix != sys.base_prefix # Check if the LAUNCHER's python is in a venv
                 # Check if the target python_exe itself is NOT within the launcher's base prefix (heuristic for standalone/portable env)
                 try:
                      # os.path.relpath can raise ValueError if paths are on different drives on Windows
                      relative_path_to_base = os.path.relpath(python_exe, sys.base_prefix)
                      is_outside_launcher_base = relative_path_to_base.startswith('..') or os.path.isabs(relative_path_to_base)
                 except ValueError: # Assume it's outside on path error
                      is_outside_launcher_base = True

                 # Add --user only if on Linux/macOS AND (the launcher is NOT in a venv AND the target python is NOT in the launcher's base path)
                 if platform.system() != "Windows" and not is_venv and is_outside_launcher_base:
                      # This heuristic tries to guess if the target python is a 'user' install vs a system/venv install
                      # It's imperfect but safer than always adding --user.
                      self.app.log_to_gui("Management", "目标Python路径可能非系统或虚拟环境安装，使用 --user 选项安装依赖。", "warn")
                      pip_cmd.append("--user")


                 # Added --no-cache-dir to save space, --compile could speed up subsequent imports
                 pip_cmd.extend(["--no-cache-dir"])

                 # Use app instance method for running pip command
                 _, stderr_pip, rc_pip = self.app._run_git_command(pip_cmd, cwd=comfyui_dir, timeout=600) # Longer timeout for pip
                 if rc_pip != 0:
                      self.app.log_to_gui("Management", f"Pip 安装依赖失败: {stderr_pip.strip()}", "error")
                      # Show warning in GUI thread
                      self.app.root.after(0, lambda: messagebox.showwarning("依赖安装失败", "Python 依赖安装失败，新版本可能无法正常工作。\n请查看日志获取详情。", parent=self.app.root))
                 else:
                      self.app.log_to_gui("Management", "Pip 安装依赖完成。", "info")
            else:
                 self.app.log_to_gui("Management", "Python 可执行文件或 requirements.txt 无效，跳过依赖安装。", "warn")

            # Success
            self.app.log_to_gui("Management", f"本体版本激活流程完成 (引用: {target_ref[:8]})。", "info")
            # Show success message in GUI thread
            self.app.root.after(0, lambda ref=target_ref[:8]: messagebox.showinfo("激活完成", f"本体版本已激活到: {ref}", parent=self.app.root))

        except threading.ThreadExit:
             self.app.log_to_gui("Management", "本体版本激活任务已取消。", "warn")
        except Exception as e:
            error_msg = f"本体版本激活流程失败: {e}"
            self.app.log_to_gui("Management", error_msg, "error")
            # Show error message in GUI thread
            self.app.root.after(0, lambda msg=str(e): messagebox.showerror("激活失败", msg, parent=self.app.root))
        finally:
            # Always refresh the list after attempting activation by queuing the refresh task
            self.app._queue_main_body_refresh()


    # Called by app._run_initial_background_tasks and app._queue_node_list_refresh
    def refresh_node_list(self):
        """Fetches and displays custom node list (local scan + online config), applying filter. Runs in worker thread."""
        if self.app.stop_event_set(): # Use the getter method
            self.app.log_to_gui("Management", "节点列表刷新任务已取消 (停止信号)。", "warn")
            # Repopulate with current cached data if available
            # Safely access nodes_tree before attempting to populate
            if hasattr(self, 'nodes_tree') and self.nodes_tree and self.nodes_tree.winfo_exists():
                 self.app.root.after(0, lambda list_to_populate=sorted(self.local_nodes_only, key=lambda x: x.get('name', '').lower()): self._populate_nodes_treeview(list_to_populate))
            return
        self.app.log_to_gui("Management", "刷新节点列表...", "info")

        node_config_url = self.app.node_config_url_var.get()
        comfyui_nodes_dir = self.app.comfyui_nodes_dir
        # Safely get the current search term from the GUI thread before starting the task
        search_term_value = ""
        try:
            # Use app.root.after to get GUI state if needed, but binding KeyRelease
            # and requeueing refresh might mean the state is picked up implicitly.
            # Let's try getting it directly here, as the event handler queues the task.
            # A safer approach might be to pass the search term in the queue call, but let's check this first.
            if hasattr(self, 'nodes_search_entry') and self.nodes_search_entry and self.nodes_search_entry.winfo_exists():
                 search_term_value = self.nodes_search_entry.get().strip().lower()
        except tk.TclError:
            pass # Widget might have been destroyed, use empty string
        self.app.log_to_gui("Management", f"当前搜索词: '{search_term_value}'", "info")


        # Validate paths using app instance method (show error only if check_comfyui is true)
        git_path_ok = self.app._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=False)
        is_nodes_dir_valid = comfyui_nodes_dir and os.path.isdir(comfyui_nodes_dir)

        # Clear existing list in GUI thread before starting refresh
        # Safely access nodes_tree before clearing
        if hasattr(self, 'nodes_tree') and self.nodes_tree and self.nodes_tree.winfo_exists():
             self.app.root.after(0, lambda: [self.nodes_tree.delete(item) for item in self.nodes_tree.get_children()])

        self.local_nodes_only = [] # Reset local node cache

        # --- Scan Local custom_nodes directory ---
        local_nodes = []
        if is_nodes_dir_valid:
             self.app.log_to_gui("Management", f"扫描本地 custom_nodes 目录: {comfyui_nodes_dir}...", "info")
             try:
                  # List directories first for better processing
                  item_names = sorted([d for d in os.listdir(comfyui_nodes_dir) if os.path.isdir(os.path.join(comfyui_nodes_dir, d))])
                  for item_name in item_names:
                       if self.app.stop_event_set(): # Use the getter method
                           raise threading.ThreadExit

                       item_path = os.path.join(comfyui_nodes_dir, item_name)
                       node_info = {"name": item_name, "status": "已安装", "local_id": "N/A", "local_commit_full": None, "repo_info": "本地安装", "repo_url": "本地安装", "is_git": False, "remote_branch": None}

                       if git_path_ok and os.path.isdir(os.path.join(item_path, ".git")):
                            node_info["is_git"] = True

                            # Get Local Short ID (8 chars) and Full ID using app instance method
                            stdout_id_full, _, rc_id_full = self.app._run_git_command(["rev-parse", "HEAD"], cwd=item_path, timeout=5, log_output=False)
                            node_info["local_commit_full"] = stdout_id_full.strip() if rc_id_full == 0 and stdout_id_full else None
                            node_info["local_id"] = node_info["local_commit_full"][:8] if node_info["local_commit_full"] else "获取失败"


                            # Get Remote URL using app instance method
                            stdout_url, _, rc_url = self.app._run_git_command(["config", "--get", "remote.origin.url"], cwd=item_path, timeout=5, log_output=False)
                            node_info["repo_url"] = stdout_url.strip() if rc_url == 0 and stdout_url and stdout_url.strip().endswith(".git") else "无远程仓库" # Ensure it looks like a URL

                            # Get Upstream Branch and Remote Info using app instance method
                            # Use git rev-parse --abbrev-ref --symbolic-full-name @{u} to get tracking branch
                            upstream_stdout, _, rc_upstream = self.app._run_git_command(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd=item_path, timeout=5, log_output=False)
                            upstream_ref = upstream_stdout.strip() if rc_upstream == 0 and upstream_stdout else None

                            repo_info_display = "无远程跟踪"
                            if upstream_ref and upstream_ref.startswith("origin/"):
                                remote_branch_name = upstream_ref.replace("origin/", "")
                                node_info["remote_branch"] = remote_branch_name # Store for update all

                                # Get remote commit ID and date for the tracking branch using app instance method
                                # Use git log --format to get commit hash (%H), committer date (%ci), and subject (%s)
                                log_cmd = ["log", "-1", "--format=%H %ci %s", upstream_ref] # Use ISO date, include subject
                                stdout_log, _, rc_log = self.app._run_git_command(log_cmd, cwd=item_path, timeout=10, log_output=False)
                                if rc_log == 0 and stdout_log:
                                     log_parts = stdout_log.strip().split(' ', 2) # Split into hash, date, rest (subject)
                                     if len(log_parts) >= 2: # Need at least hash and date
                                          full_commit_id_remote = log_parts[0]
                                          date_iso = log_parts[1]
                                          subject = log_parts[2].strip() if len(log_parts) == 3 else ""

                                          remote_commit_id_short = full_commit_id_remote[:8]
                                          # Parse date safely using app instance method
                                          date_obj = self.app._parse_iso_date_for_sort(date_iso)
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

                       local_nodes.append(node_info)

             except threading.ThreadExit:
                 self.app.log_to_gui("Management", "节点列表扫描任务已取消 (停止信号)。", "warn")
                 # Repopulate with current cached data if available
                 # Safely access nodes_tree before attempting to populate
                 if hasattr(self, 'nodes_tree') and self.nodes_tree and self.nodes_tree.winfo_exists():
                      self.app.root.after(0, lambda list_to_populate=sorted(self.local_nodes_only, key=lambda x: x.get('name', '').lower()): self._populate_nodes_treeview(list_to_populate))
                 return
             except Exception as e:
                  self.app.log_to_gui("Management", f"扫描本地 custom_nodes 目录时出错: {e}", "error", target_override="Launcher")
                  # Populate Treeview with error message in GUI thread
                  self.app.root.after(0, lambda: self._populate_nodes_treeview([{"name":"扫描失败", "status":"错误", "local_id":"N/A", "repo_info":"扫描本地目录时出错", "repo_url":"N/A"}]))
        else: # Nodes dir not valid
             self.app.log_to_gui("Management", f"ComfyUI custom_nodes 目录无效，跳过本地扫描。", "warn")
             # Populate Treeview with info message in GUI thread
             self.app.root.after(0, lambda: self._populate_nodes_treeview([{"name":"本地目录无效", "status":"错误", "local_id":"N/A", "repo_info":"", "repo_url":""}]))


        if self.app.stop_event_set(): # Use the getter method
             self.app.log_to_gui("Management", "节点列表刷新任务已取消 (停止信号)。", "warn")
             # Repopulate with current cached data if available
             if hasattr(self, 'nodes_tree') and self.nodes_tree and self.nodes_tree.winfo_exists():
                  self.app.root.after(0, lambda list_to_populate=sorted(self.local_nodes_only, key=lambda x: x.get('name', '').lower()): self._populate_nodes_treeview(list_to_populate))
             return

        # --- Fetching Online Config Data ---
        online_nodes_config = []
        if node_config_url:
            online_nodes_config = self._fetch_online_node_config() # Runs in this worker thread
        else:
            self.app.log_to_gui("Management", "节点配置地址未设置，跳过在线配置获取。", "warn")

        if self.app.stop_event_set(): # Use the getter method
            self.app.log_to_gui("Management", "节点列表刷新任务已取消 (停止信号)。", "warn")
            # Repopulate with current cached data if available
            if hasattr(self, 'nodes_tree') and self.nodes_tree and self.nodes_tree.winfo_exists():
                 self.app.root.after(0, lambda list_to_populate=sorted(self.local_nodes_only, key=lambda x: x.get('name', '').lower()): self._populate_nodes_treeview(list_to_populate))
            return

        # --- Combine local and online data ---
        local_node_dict_lower = {node['name'].lower(): node for node in local_nodes}
        combined_nodes_dict = {node['name'].lower(): node for node in local_nodes} # Start with local

        for online_node in online_nodes_config:
             if self.app.stop_event_set(): # Use the getter method
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
                           # Check if the file_entry is a dictionary with a 'url' key ending in .git
                           if isinstance(file_entry, dict) and file_entry.get('url', '').strip().endswith(".git"):
                                repo_url = file_entry['url'].strip()
                                break
                           # Fallback for old format where files list contained just urls (strings)
                           elif isinstance(file_entry, str) and file_entry.strip().endswith(".git"):
                                repo_url = file_entry.strip()
                                break

                 if not repo_url:
                     continue

                 target_ref = online_node.get('reference') or online_node.get('branch') or 'main'

                 if node_name_lower not in local_node_dict_lower:
                     # Only add online node if it's NOT already installed locally
                     online_repo_info_display = f"在线目标: {target_ref}"
                     combined_nodes_dict[node_name_lower] = {
                         "name": online_node.get('title') or online_node.get('name', '未知名称'), # Use title preferentially for display
                         "status": "未安装",
                         "local_id": "N/A",
                         "local_commit_full": None,
                         "repo_info": online_repo_info_display,
                         "repo_url": repo_url,
                         "is_git": True, # Assume online nodes are git repos
                         "remote_branch": target_ref # Store potential target ref
                     }
             except Exception as e:
                 print(f"[Management Module WARNING] Error processing online node entry: {online_node}. Error: {e}")
                 self.app.log_to_gui("Management", f"处理在线节点条目时出错: {e}", "warn")

        # Convert combined dict back to list and sort by name
        self.local_nodes_only = sorted(local_nodes, key=lambda x: x.get('name', '').lower()) # Store the scanned local list
        self.all_known_nodes = sorted(list(combined_nodes_dict.values()), key=lambda x: x.get('name', '').lower()) # Store the combined list


        if self.app.stop_event_set(): # Use the getter method
            self.app.log_to_gui("Management", "节点列表刷新任务已取消 (停止信号)。", "warn")
            # Repopulate with current cached data if available
            if hasattr(self, 'nodes_tree') and self.nodes_tree and self.nodes_tree.winfo_exists():
                 self.app.root.after(0, lambda list_to_populate=sorted(self.local_nodes_only, key=lambda x: x.get('name', '').lower()): self._populate_nodes_treeview(list_to_populate))
            return

        # --- Apply Filtering Logic ---
        filtered_nodes = []
        search_term_value = ""
        try:
            # Re-get value in case it changed during fetch (still in worker thread)
            if hasattr(self, 'nodes_search_entry') and self.nodes_search_entry and self.nodes_search_entry.winfo_exists():
                 search_term_value = self.nodes_search_entry.get().strip().lower()
        except tk.TclError:
            pass

        if search_term_value == "": # Empty search -> show local only
            filtered_nodes = sorted(self.local_nodes_only, key=lambda x: x.get('name', '').lower())
        else: # Search term present -> filter combined list
            filtered_nodes = [
                node for node in self.all_known_nodes
                if search_term_value in node.get('name', '').lower() or \
                   search_term_value in node.get('repo_url', '').lower() or \
                   search_term_value in node.get('status', '').lower()
            ]
            filtered_nodes.sort(key=lambda x: x.get('name', '').lower()) # Sort filtered results by name

        # --- Save State ---
        self._save_state() # Save the fetched and combined data

        # --- Populate Treeview ---
        # Populate the Treeview in the GUI thread
        self.app.root.after(0, lambda list_to_populate=filtered_nodes: self._populate_nodes_treeview(list_to_populate))

        self.app.log_to_gui("Management", f"节点列表刷新完成。已显示 {len(filtered_nodes)} 个节点。", "info")


    # Called by refresh_node_list
    def _fetch_online_node_config(self):
         """Fetches and parses the online custom node list config. Runs in worker thread."""
         node_config_url = self.app.node_config_url_var.get()
         if not node_config_url:
             return []

         self.app.log_to_gui("Management", f"尝试从 {node_config_url} 获取节点配置...", "info")
         try:
              response = requests.get(node_config_url, timeout=20) # Increased timeout
              response.raise_for_status()
              config_data = response.json()

              if isinstance(config_data, list) and all(isinstance(item, dict) for item in config_data):
                   self.app.log_to_gui("Management", f"已获取在线节点配置 (共 {len(config_data)} 条)。", "info")
                   return config_data
              elif isinstance(config_data, dict) and 'custom_nodes' in config_data and isinstance(config_data['custom_nodes'], list):
                   self.app.log_to_gui("Management", f"已获取在线节点配置 (Manager格式，共 {len(config_data['custom_nodes'])} 条)。", "info")
                   return config_data['custom_nodes']
              else:
                   self.app.log_to_gui("Management", f"在线节点配置格式无法识别。", "error")
                   return []

         except requests.exceptions.Timeout:
              self.app.log_to_gui("Management", f"获取在线节点配置超时: {node_config_url}", "error")
              return []
         except requests.exceptions.RequestException as e:
              self.app.log_to_gui("Management", f"获取在线节点配置失败: {e}", "error")
              return []
         except json.JSONDecodeError as e:
              self.app.log_to_gui("Management", f"在线节点配置解析失败 (非JSON): {e}", "error")
              return []
         except Exception as e:
              self.app.log_to_gui("Management", f"处理在线节点配置时发生意外错误: {e}", "error")
              return []


    # Called by app._queue_node_switch_or_show_history (for install scenario)
    def _install_node_task(self, node_name, node_install_path, repo_url, target_ref):
        """Task to execute git commands for INSTALLING a node (cloning). Runs in worker thread."""
        if self.app.stop_event_set(): # Use the getter method
            self.app.log_to_gui("Management", f"节点 '{node_name}' 安装任务已取消 (停止信号)。", "warn")
            return
        self.app.log_to_gui("Management", f"开始安装节点 '{node_name}'...", "info")
        self.app.log_to_gui("Management", f"  仓库: {repo_url}", "info")
        self.app.log_to_gui("Management", f"  目标引用: {target_ref}", "info")
        self.app.log_to_gui("Management", f"  目标目录: {node_install_path}", "info")

        try:
            comfyui_nodes_dir = self.app.comfyui_nodes_dir
            if not comfyui_nodes_dir: # Should be validated earlier, but defensive check
                 raise Exception("ComfyUI custom_nodes 目录未设置或无效。")

            if not os.path.exists(comfyui_nodes_dir):
                 self.app.log_to_gui("Management", f"创建 custom_nodes 目录: {comfyui_nodes_dir}", "info")
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
                           self.app.log_to_gui("Management", f"移除已存在的空目录: {node_install_path}", "info")
                           os.rmdir(node_install_path)
                      except OSError as e:
                           # If rmdir fails for some reason (e.g., permissions), raise an error
                           raise Exception(f"无法移除已存在的空目录 {node_install_path}: {e}")

            if self.app.stop_event_set(): # Use the getter method
                raise threading.ThreadExit

            self.app.log_to_gui("Management", f"执行 Git clone {repo_url} {node_install_path}...", "info")
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
            # Use app instance method
            stdout_clone, stderr_clone, returncode = self.app._run_git_command(clone_cmd, cwd=comfyui_nodes_dir, timeout=300, log_output=True)

            if returncode != 0:
                 # Clean up potentially created partial directory on failure
                 if os.path.exists(node_install_path):
                      try:
                           self.app.log_to_gui("Management", f"Git clone 失败，尝试移除失败目录: {node_install_path}", "warn")
                           shutil.rmtree(node_install_path)
                           self.app.log_to_gui("Management", f"已移除失败的节点目录: {node_install_path}", "info")
                      except Exception as rm_err:
                           self.app.log_to_gui("Management", f"移除失败的节点目录 '{node_install_path}' 失败: {rm_err}", "error")
                 raise Exception(f"Git clone 失败 (退出码 {returncode})")

            self.app.log_to_gui("Management", "Git clone 完成。", "info")

            # If target_ref was specified, checkout the specific ref after cloning
            # This handles tags, commit hashes, and ensures the correct state if --branch failed or wasn't used.
            if target_ref:
                 self.app.log_to_gui("Management", f"尝试执行 Git checkout {target_ref}...", "info")
                 # Use --force to ensure checkout succeeds even if clone resulted in unexpected state (shouldn't happen but safe)
                 # Use app instance method
                 _, stderr_checkout, rc_checkout = self.app._run_git_command(["checkout", "--force", target_ref], cwd=node_install_path, timeout=60)
                 if rc_checkout != 0:
                      # Log warning, not fatal error, as the node is still installed, just maybe not the exact version.
                      self.app.log_to_gui("Management", f"Git checkout {target_ref[:8]} 失败: {stderr_checkout.strip()}", "warn")
                      # Show warning in GUI thread
                      self.app.root.after(0, lambda name=node_name, ref=target_ref[:8]: messagebox.showwarning("版本切换警告", f"节点 '{name}' 安装后尝试切换到版本 {ref} 失败。\n请查看日志。", parent=self.app.root))
                 else:
                      self.app.log_to_gui("Management", f"Git checkout {target_ref[:8]} 完成。", "info")


            if self.app.stop_event_set(): # Use the getter method
                raise threading.ThreadExit

            # Update submodules if .gitmodules exists
            if os.path.exists(os.path.join(node_install_path, ".gitmodules")):
                 self.app.log_to_gui("Management", f"执行 Git submodule update for '{node_name}'...", "info")
                 # Use app instance method
                 _, stderr_sub, rc_sub = self.app._run_git_command(["submodule", "update", "--init", "--recursive", "--force"], cwd=node_install_path, timeout=180)
                 if rc_sub != 0:
                     self.app.log_to_gui("Management", f"Git submodule update 失败: {stderr_sub.strip()}", "warn")

            if self.app.stop_event_set(): # Use the getter method
                raise threading.ThreadExit

            # Install Python dependencies if requirements.txt exists
            python_exe = self.app.python_exe_var.get()
            requirements_path = os.path.join(node_install_path, "requirements.txt")
            if python_exe and os.path.isfile(python_exe) and os.path.isfile(requirements_path):
                 self.app.log_to_gui("Management", f"执行 pip 安装节点依赖 for '{node_name}'...", "info")
                 pip_cmd_base = [python_exe, "-m", "pip", "install", "-r", requirements_path, "--upgrade"]
                 pip_cmd_extras = ["--extra-index-url", "https://download.pytorch.org/whl/cu118", "--extra-index-url", "https://download.pytorch.org/whl/cu121"]
                 pip_cmd = pip_cmd_base + pip_cmd_extras
                 is_venv = sys.prefix != sys.base_prefix
                 # Check if the target python_exe is NOT within the launcher's base prefix (heuristic for standalone/portable env)
                 try:
                      relative_path_to_base = os.path.relpath(python_exe, sys.base_prefix)
                      is_outside_launcher_base = relative_path_to_base.startswith('..') or os.path.isabs(relative_path_to_base)
                 except ValueError: # Assume it's outside on path error
                      is_outside_launcher_base = True

                 # Add --user only if on Linux/macOS AND (the launcher is NOT in a venv AND the target python is NOT in the launcher's base path)
                 if platform.system() != "Windows" and not is_venv and is_outside_launcher_base:
                       self.app.log_to_gui("Management", "目标Python路径可能非系统或虚拟环境安装，使用 --user 选项安装依赖。", "warn")
                       pip_cmd.append("--user")

                 pip_cmd.extend(["--no-cache-dir"]) # Added --no-cache-dir

                 # Use app instance method
                 _, stderr_pip, rc_pip = self.app._run_git_command(pip_cmd, cwd=node_install_path, timeout=180)
                 if rc_pip != 0:
                      self.app.log_to_gui("Management", f"Pip 安装节点依赖失败: {stderr_pip.strip()}", "error")
                      # Show warning in GUI thread
                      self.app.root.after(0, lambda name=node_name: messagebox.showwarning("依赖安装失败", f"节点 '{name}' 的 Python 依赖可能安装失败。\n请查看日志。", parent=self.app.root))
                 else:
                      self.app.log_to_gui("Management", f"Pip 安装节点依赖完成 for '{node_name}'.", "info")

            self.app.log_to_gui("Management", f"节点 '{node_name}' 安装流程完成。", "info")
            # Show success message in GUI thread
            self.app.root.after(0, lambda name=node_name: messagebox.showinfo("安装完成", f"节点 '{name}' 已成功安装。", parent=self.app.root))

        except threading.ThreadExit:
             self.app.log_to_gui("Management", f"节点 '{node_name}' 安装任务已取消。", "warn")
             # Clean up partially created directory if it exists
             if os.path.exists(node_install_path):
                 try:
                      self.app.log_to_gui("Management", f"安装任务取消，尝试移除部分创建的目录: {node_install_path}", "warn")
                      shutil.rmtree(node_install_path)
                      self.app.log_to_gui("Management", f"已移除部分创建的目录: {node_install_path}", "info")
                 except Exception as rm_err:
                      self.app.log_to_gui("Management", f"移除部分创建的目录 '{node_install_path}' 失败: {rm_err}", "error")

        except Exception as e:
            error_msg = f"节点 '{node_name}' 安装失败: {e}"
            self.app.log_to_gui("Management", error_msg, "error")
            # Show error message in GUI thread
            self.app.root.after(0, lambda msg=error_msg: messagebox.showerror("安装失败", msg, parent=self.app.root))
        finally:
            # Always refresh the list after attempting installation by queuing the refresh task
            self.app._queue_node_list_refresh()


    # Called by app._queue_node_uninstall
    def _node_uninstall_task(self, node_name, node_install_path):
         """Task to uninstall a node by deleting its directory. Runs in worker thread."""
         if self.app.stop_event_set(): # Use the getter method
             self.app.log_to_gui("Management", f"节点 '{node_name}' 卸载任务已取消 (停止信号)。", "warn")
             return
         self.app.log_to_gui("Management", f"正在卸载节点 '{node_name}' (删除目录: {node_install_path})...", "info")

         try:
              if not os.path.isdir(node_install_path):
                   self.app.log_to_gui("Management", f"节点目录 '{node_install_path}' 不存在，无需卸载。", "warn")
                   # Show warning in GUI thread
                   self.app.root.after(0, lambda name=node_name: messagebox.showwarning("卸载失败", f"节点目录 '{name}' 不存在。", parent=self.app.root))
                   return

              if self.app.stop_event_set(): # Use the getter method
                  raise threading.ThreadExit

              self.app.log_to_gui("Management", f"删除目录: {node_install_path}", "cmd") # Log the action
              shutil.rmtree(node_install_path)
              self.app.log_to_gui("Management", f"节点目录 '{node_install_path}' 已删除。", "info")
              self.app.log_to_gui("Management", f"节点 '{node_name}' 卸载流程完成。", "info")
              # Show success message in GUI thread
              self.app.root.after(0, lambda name=node_name: messagebox.showinfo("卸载完成", f"节点 '{name}' 已成功卸载。", parent=self.app.root))

         except threading.ThreadExit:
              self.app.log_to_gui("Management", f"节点 '{node_name}' 卸载任务已取消。", "warn")
         except Exception as e:
             error_msg = f"节点 '{node_name}' 卸载失败: {e}"
             self.app.log_to_gui("Management", error_msg, "error")
             # Show error message in GUI thread
             self.app.root.after(0, lambda msg=error_msg: messagebox.showerror("卸载失败", msg, parent=self.app.root))
         finally:
             # Always refresh the list after attempting uninstall by queuing the refresh task
             self.app._queue_node_list_refresh()


    # Called by app._queue_all_nodes_update
    def _update_all_nodes_task(self, nodes_to_process):
        """Task to iterate and update all specified installed nodes. Runs in worker thread."""
        if self.app.stop_event_set(): # Use the getter method
            self.app.log_to_gui("Management", "更新全部节点任务已取消 (停止信号)。", "warn")
            return
        self.app.log_to_gui("Management", f"开始更新全部节点 ({len(nodes_to_process)} 个)...", "info")
        updated_count = 0
        failed_nodes = []

        for index, node_info in enumerate(nodes_to_process):
             if self.app.stop_event_set(): # Use the getter method
                 break

             node_name = node_info.get("name", "未知节点")
             # Safely access nodes_dir via app instance
             node_install_path = os.path.normpath(os.path.join(self.app.comfyui_nodes_dir, node_name))
             repo_url = node_info.get("repo_url")
             remote_branch = node_info.get("remote_branch") # Branch name from refresh scan

             self.app.log_to_gui("Management", f"[{index+1}/{len(nodes_to_process)}] 正在处理节点 '{node_name}'...", "info")

             if not os.path.isdir(node_install_path) or not os.path.exists(os.path.join(node_install_path, ".git")):
                  self.app.log_to_gui("Management", f"跳过 '{node_name}': 非 Git 仓库或目录无效。", "warn")
                  failed_nodes.append(f"{node_name} (非Git仓库)")
                  continue
             if not remote_branch:
                 self.app.log_to_gui("Management", f"跳过 '{node_name}': 未能确定远程跟踪分支。", "warn")
                 failed_nodes.append(f"{node_name} (无跟踪分支)")
                 continue
             if not repo_url or repo_url in ("本地安装，无Git信息", "无法获取远程 URL", "本地安装", "N/A", "无远程仓库"):
                 self.app.log_to_gui("Management", f"跳过 '{node_name}': 缺少有效的远程 URL。", "warn")
                 failed_nodes.append(f"{node_name} (无远程URL)")
                 continue

             try:
                 # Ensure origin remote exists and points to the correct URL using app instance method
                 stdout_get_url, _, rc_get_url = self.app._run_git_command(["remote", "get-url", "origin"], cwd=node_install_path, timeout=10, log_output=False)
                 current_url = stdout_get_url.strip() if rc_get_url == 0 else None
                 if not current_url:
                      self.app.log_to_gui("Management", f"节点 '{node_name}': 远程 'origin' 不存在，尝试添加...", "info")
                      # Use app instance method
                      _, stderr_add, rc_add = self.app._run_git_command(["remote", "add", "origin", repo_url], cwd=node_install_path, timeout=15)
                      if rc_add != 0:
                          self.app.log_to_gui("Management", f"节点 '{node_name}': 添加远程 'origin' 失败: {stderr_add.strip()}", "warn")
                 elif current_url != repo_url:
                      self.app.log_to_gui("Management", f"节点 '{node_name}': 远程 'origin' URL 不匹配 ({current_url}), 尝试设置新 URL...", "warn")
                      # Use app instance method
                      _, stderr_set, rc_set = self.app._run_git_command(["remote", "set-url", "origin", repo_url], cwd=node_install_path, timeout=15)
                      if rc_set != 0:
                          self.app.log_to_gui("Management", f"节点 '{node_name}': 设置远程 'origin' URL 失败: {stderr_set.strip()}", "warn")
                      else:
                          self.app.log_to_gui("Management", f"节点 '{node_name}': 远程 URL 已更新。", "info")


                 if self.app.stop_event_set(): # Use the getter method
                     raise threading.ThreadExit

                 # Check for local changes using app instance method
                 stdout_status, _, _ = self.app._run_git_command(["status", "--porcelain"], cwd=node_install_path, timeout=10, log_output=False)
                 if stdout_status.strip():
                      self.app.log_to_gui("Management", f"跳过 '{node_name}': 存在未提交的本地修改。", "warn")
                      failed_nodes.append(f"{node_name} (存在本地修改)")
                      continue

                 # Fetch the remote branch specifically using app instance method
                 self.app.log_to_gui("Management", f"[{index+1}/{len(nodes_to_process)}] 执行 Git fetch origin {remote_branch}...", "info")
                 # Increase timeout slightly for fetch
                 _, stderr_fetch, rc_fetch = self.app._run_git_command(["fetch", "origin", remote_branch], cwd=node_install_path, timeout=60)
                 if rc_fetch != 0:
                      self.app.log_to_gui("Management", f"Git fetch 失败 for '{node_name}': {stderr_fetch.strip()}", "error")
                      failed_nodes.append(f"{node_name} (Fetch失败)")
                      continue

                 if self.app.stop_event_set(): # Use the getter method
                     raise threading.ThreadExit

                 # Compare local HEAD with remote tracking branch using app instance method
                 local_commit_full, _, _ = self.app._run_git_command(["rev-parse", "HEAD"], cwd=node_install_path, timeout=5, log_output=False)
                 remote_commit_full, _, _ = self.app._run_git_command(["rev-parse", f"origin/{remote_branch}"], cwd=node_install_path, timeout=5, log_output=False)

                 if local_commit_full and remote_commit_full and local_commit_full.strip() == remote_commit_full.strip():
                     self.app.log_to_gui("Management", f"节点 '{node_name}' 已是最新版本。", "info")
                     continue

                 # Checkout the remote tracking branch, discarding local changes using app instance method
                 self.app.log_to_gui("Management", f"[{index+1}/{len(nodes_to_process)}] 执行 Git checkout --force origin/{remote_branch} for '{node_name}'...", "info")
                 _, stderr_checkout, returncode_checkout = self.app._run_git_command(["checkout", "--force", f"origin/{remote_branch}"], cwd=node_install_path, timeout=60)
                 if returncode_checkout != 0:
                       self.app.log_to_gui("Management", f"Git checkout --force 失败 for '{node_name}': {stderr_checkout.strip()}", "error")
                       failed_nodes.append(f"{node_name} (Checkout失败)")
                       continue
                 self.app.log_to_gui("Management", f"Git checkout 完成 for '{node_name}'.", "info")

                 # At this point, HEAD is detached and points to origin/<branch>. To make it track the branch,
                 # we should optionally checkout the local branch again, or do a git pull.
                 # Git pull is effectively fetch + merge/rebase. Since we just did reset --hard,
                 # a simple `git pull origin <branch>` should work similarly to fetch + reset --hard.
                 # Let's stick to checkout as it explicitly puts the working tree into the desired state.
                 # To re-attach HEAD to the local branch if one exists with the same name as the remote tracking branch:
                 local_branch_exists_stdout, _, rc_local_branch = self.app._run_git_command(["rev-parse", "--verify", "--quiet", remote_branch], cwd=node_install_path, timeout=5, log_output=False)
                 if rc_local_branch == 0: # Local branch exists with the same name
                      self.app.log_to_gui("Management", f"节点 '{node_name}': 本地分支 '{remote_branch}' 存在，尝试切换回本地分支...", "info")
                      # Checkout the local branch, it should now point to the same commit as origin/<branch>
                      # Use app instance method
                      _, stderr_checkout_local, rc_checkout_local = self.app._run_git_command(["checkout", remote_branch], cwd=node_install_path, timeout=30)
                      if rc_checkout_local != 0:
                           self.app.log_to_gui("Management", f"节点 '{node_name}': 切换回本地分支 '{remote_branch}' 失败: {stderr_checkout_local.strip()}", "warn")
                      else:
                           self.app.log_to_gui("Management", f"节点 '{node_name}': 已切换回本地分支 '{remote_branch}'.", "info")
                 else:
                      self.app.log_to_gui("Management", f"节点 '{node_name}': 未找到本地分支 '{remote_branch}', 保持在 detached HEAD 状态。", "info")


                 if self.app.stop_event_set(): # Use the getter method
                     raise threading.ThreadExit

                 if os.path.exists(os.path.join(node_install_path, ".gitmodules")):
                      self.app.log_to_gui("Management", f"执行 Git submodule update for '{node_name}'...", "info")
                      # Use app instance method
                      _, stderr_sub, rc_sub = self.app._run_git_command(["submodule", "update", "--init", "--recursive", "--force"], cwd=node_install_path, timeout=180)
                      if rc_sub != 0:
                          self.app.log_to_gui("Management", f"Git submodule update 失败: {stderr_sub.strip()}", "warn")

                 if self.app.stop_event_set(): # Use the getter method
                     raise threading.ThreadExit

                 # Re-install Python dependencies if requirements.txt exists
                 python_exe = self.app.python_exe_var.get()
                 requirements_path = os.path.join(node_install_path, "requirements.txt")
                 if python_exe and os.path.isfile(python_exe) and os.path.isfile(requirements_path):
                      self.app.log_to_gui("Management", f"执行 pip 安装节点依赖 for '{node_name}'...", "info")
                      pip_cmd_base = [python_exe, "-m", "pip", "install", "-r", requirements_path, "--upgrade"]
                      pip_cmd_extras = ["--extra-index-url", "https://download.pytorch.org/whl/cu118", "--extra-index-url", "https://download.pytorch.org/whl/cu121"]
                      pip_cmd = pip_cmd_base + pip_cmd_extras
                      is_venv = sys.prefix != sys.base_prefix
                      # Check if the target python_exe is NOT within the launcher's base prefix (heuristic for standalone/portable env)
                      try:
                          relative_path_to_base = os.path.relpath(python_exe, sys.base_prefix)
                          is_outside_launcher_base = relative_path_to_base.startswith('..') or os.path.isabs(relative_path_to_base)
                      except ValueError:
                          is_outside_launcher_base = True

                      if platform.system() != "Windows" and not is_venv and is_outside_launcher_base:
                           self.app.log_to_gui("Management", "目标Python路径可能非系统或虚拟环境安装，使用 --user 选项安装依赖。", "warn")
                           pip_cmd.append("--user")

                      pip_cmd.extend(["--no-cache-dir"])

                      # Use app instance method
                      _, stderr_pip, rc_pip = self.app._run_git_command(pip_cmd, cwd=node_install_path, timeout=180)
                      if rc_pip != 0:
                           self.app.log_to_gui("Management", f"Pip 安装节点依赖失败: {stderr_pip.strip()}", "error")
                           failed_nodes.append(f"{node_name} (依赖安装失败)")
                           # Show warning in GUI thread
                           self.app.root.after(0, lambda name=node_name: messagebox.showwarning("依赖安装失败", f"节点 '{name}' 的 Python 依赖可能安装失败。\n请查看日志。", parent=self.app.root))
                      else:
                           self.app.log_to_gui("Management", f"Pip 安装节点依赖完成.", "info")

                 updated_count += 1
                 self.app.log_to_gui("Management", f"节点 '{node_name}' 更新成功。", "info")

             except threading.ThreadExit:
                 self.app.log_to_gui("Management", f"更新节点 '{node_name}' 时收到停止信号。", "warn")
                 failed_nodes.append(f"{node_name} (已取消)")
                 break # Stop processing remaining nodes if task is cancelled
             except Exception as e:
                 self.app.log_to_gui(f"Management", f"更新节点 '{node_name}' 时发生意外错误: {e}", "error")
                 failed_nodes.append(f"{node_name} (发生错误)")

        # --- Update All Task Summary ---
        self.app.log_to_gui("Management", f"更新全部节点流程完成。", "info")
        final_message = f"全部节点更新流程完成。\n成功更新: {updated_count} 个。"
        if failed_nodes:
             final_message += f"\n\n失败/跳过节点 ({len(failed_nodes)} 个):\n- " + "\n- ".join(failed_nodes)
             # Show summary in GUI thread
             self.app.root.after(0, lambda msg=final_message: messagebox.showwarning("更新全部完成 (有失败/跳过)", msg, parent=self.app.root))
        else:
             # Show success in GUI thread
             self.app.root.after(0, lambda msg=final_message: messagebox.showinfo("更新全部完成", msg, parent=self.app.root))

        # Always refresh node list after attempting update all
        self.app._queue_node_list_refresh()


    # Called by app._queue_node_switch_or_show_history (for history scenario)
    def _node_history_fetch_task(self, node_name, node_install_path):
         """Task to fetch git history and current commit for a node. Runs in worker thread."""
         if self.app.stop_event_set(): # Use the getter method
             self.app.log_to_gui("Management", f"节点 '{node_name}' 版本历史获取任务已取消 (停止信号)。", "warn")
             # Clean up modal state in GUI thread on cancellation
             self.app.root.after(0, self._cleanup_modal_state)
             return

         self.app.log_to_gui("Management", f"正在获取节点 '{node_name}' 的版本历史...", "info")

         history_data = []
         current_local_commit = None # Full ID
         try:
             if not os.path.isdir(node_install_path) or not os.path.exists(os.path.join(node_install_path, ".git")):
                  raise Exception(f"节点目录不是有效的 Git 仓库: {node_install_path}")

             # Get current local commit ID (full) using app instance method
             local_commit_stdout, _, rc_local = self.app._run_git_command(["rev-parse", "HEAD"], cwd=node_install_path, timeout=5, log_output=False)
             if rc_local == 0 and local_commit_stdout:
                 current_local_commit = local_commit_stdout.strip()
                 self.app.log_to_gui("Management", f"当前本地 Commit ID: {current_local_commit[:8]}", "info")
             else:
                 self.app.log_to_gui("Management", f"无法获取节点 '{node_name}' 的当前 Commit ID。", "warn")
                 # Even if we can't get the current commit, try fetching history

             # Ensure origin remote exists and is correct before fetching history
             # Find the correct repo_url from cached list (local_nodes_only) if available, otherwise try reading from local git config
             found_node_info = next((node for node in self.local_nodes_only if node.get("name") == node_name), None)
             repo_url = found_node_info.get("repo_url") if found_node_info else None

             if not repo_url or repo_url in ("本地安装，无Git信息", "无法获取远程 URL", "本地安装", "N/A", "无远程仓库"):
                 # If URL not in cache, try reading from local git config using app instance method
                 stdout_config_url, _, rc_config_url = self.app._run_git_command(["config", "--get", "remote.origin.url"], cwd=node_install_path, timeout=5, log_output=False)
                 if rc_config_url == 0 and stdout_config_url and stdout_config_url.strip().endswith(".git"):
                      repo_url = stdout_config_url.strip()
                      self.app.log_to_gui("Management", f"从本地 Git config 获取到远程 URL: {repo_url}", "info")
                 else:
                      self.app.log_to_gui("Management", f"节点 '{node_name}': 无法获取有效的远程 URL，历史列表可能不完整。", "warn")


             if repo_url and repo_url not in ("本地安装", "N/A"): # Only attempt fetch if a valid URL is found
                 # Use app instance method
                 stdout_get_url, _, rc_get_url = self.app._run_git_command(["remote", "get-url", "origin"], cwd=node_install_path, timeout=10, log_output=False)
                 current_origin_url = stdout_get_url.strip() if rc_get_url == 0 else ""

                 if not current_origin_url:
                      self.app.log_to_gui("Management", f"节点 '{node_name}': 远程 'origin' 不存在，尝试添加 URL '{repo_url}'...", "info")
                      # Use app instance method
                      _, stderr_add, rc_add = self.app._run_git_command(["remote", "add", "origin", repo_url], cwd=node_install_path, timeout=10)
                      if rc_add != 0:
                          self.app.log_to_gui("Management", f"节点 '{node_name}': 添加远程 'origin' 失败: {stderr_add.strip()}", "warn")
                 elif current_origin_url != repo_url:
                     self.app.log_to_gui("Management", f"节点 '{node_name}': 远程 'origin' URL 不匹配 ({current_origin_url}), 尝试设置新 URL '{repo_url}'...", "warn")
                     # Use app instance method
                     _, stderr_set, rc_set = self.app._run_git_command(["remote", "set-url", "origin", repo_url], cwd=node_install_path, timeout=10)
                     if rc_set != 0:
                         self.app.log_to_gui("Management", f"节点 '{node_name}': 设置远程 URL 失败: {stderr_set.strip()}", "warn")
                     else:
                         self.app.log_to_gui("Management", f"节点 '{node_name}': 远程 URL 已更新。", "info")

                 # After ensuring remote is set, fetch
                 if self.app.stop_event_set(): # Use the getter method
                     raise threading.ThreadExit
                 self.app.log_to_gui("Management", f"执行 Git fetch origin --prune --tags -f for '{node_name}'...", "info")
                 # Increase timeout slightly for fetch
                 # Use app instance method
                 _, stderr_fetch, rc_fetch = self.app._run_git_command(["fetch", "origin", "--prune", "--tags", "-f"], cwd=node_install_path, timeout=90)
                 if rc_fetch != 0:
                      self.app.log_to_gui("Management", f"Git fetch 失败 for '{node_name}': {stderr_fetch.strip()}", "error")
                      self.app.log_to_gui("Management", "无法从远程获取最新历史，列表可能不完整。", "warn")
             else:
                  self.app.log_to_gui("Management", f"节点 '{node_name}': 无有效远程 URL，仅显示本地历史。", "warn")


             if self.app.stop_event_set(): # Use the getter method
                 self.app.log_to_gui("Management", f"节点 '{node_name}' 版本历史获取任务已取消 (停止信号)。", "warn")
                 # Clean up modal state in GUI thread on cancellation
                 self.app.root.after(0, self._cleanup_modal_state)
                 return

             # Get all local and fetched remote references (branches, tags, HEAD) with their commits and dates
             # Format: %(refname) %(objectname) %(committerdate:iso-strict) %(contents:subject)
             # Use full refname to distinguish local/remote/tags
             # Added %(contents:subject) to get commit message for description
             log_cmd = ["for-each-ref", "refs/", "--sort=-committerdate", "--format=%(refname) %(objectname) %(committerdate:iso-strict) %(contents:subject)"]
             # Use app instance method
             history_output, _, rc_history = self.app._run_git_command(log_cmd, cwd=node_install_path, timeout=60)

             if rc_history != 0:
                  self.app.log_to_gui("Management", f"获取 Git 历史失败: {history_output.strip()}", "error")
                  self.app.log_to_gui("Management", "无法获取节点历史。", "error")
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
                                # Find the symbolic ref for HEAD if possible to show local branch name using app instance method
                                head_sym_ref_out, _, _ = self.app._run_git_command(["symbolic-ref", "-q", "--short", "HEAD"], cwd=node_install_path, timeout=2, log_output=False)
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

             # Sort the history data (MOD1: Using custom comparison via app instance method)
             history_data.sort(key=cmp_to_key(self.app._compare_versions_for_sort))

             # --- Add current local commit if not already in the list (e.g., local-only commits) ---
             if current_local_commit and current_local_commit not in processed_commits:
                  self.app.log_to_gui("Management", "获取当前本地 Commit 信息...", "info")
                  # Use app instance methods
                  head_date_stdout, _, rc_head_date = self.app._run_git_command(["log", "-1", "--format=%ci", "HEAD"], cwd=node_install_path, timeout=5, log_output=False)
                  head_subject_stdout, _, rc_head_subject = self.app._run_git_command(["log", "-1", "--format=%s", "HEAD"], cwd=node_install_path, timeout=5, log_output=False)
                  head_date_iso = head_date_stdout.strip() if rc_head_date == 0 else None
                  head_description = head_subject_stdout.strip() if rc_head_subject == 0 else "当前工作目录"
                  # Parse date safely via app instance method
                  date_obj = self.app._parse_iso_date_for_sort(head_date_iso)
                  final_date_iso = date_obj.isoformat() if date_obj else datetime.now(timezone.utc).isoformat()

                  # Determine type (detached HEAD or local branch not tracking remote) using app instance method
                  head_sym_ref_out, _, rc_head_sym_ref = self.app._run_git_command(["symbolic-ref", "-q", "--short", "HEAD"], cwd=node_install_path, timeout=2, log_output=False)
                  head_type = "commit (HEAD)" if rc_head_sym_ref != 0 else "branch (local)"
                  head_name = head_sym_ref_out.strip() if head_type == "branch (local)" else f"Detached at {current_local_commit[:8]}"

                  history_data.append({"type": head_type, "name": head_name, "commit_id": current_local_commit, "date_iso": final_date_iso, "description": head_description})
                  self.app.log_to_gui("Management", f"添加当前本地 HEAD ({current_local_commit[:8]}) 到列表。", "info")

                  # Re-sort to include the added local HEAD using app instance method
                  history_data.sort(key=cmp_to_key(self.app._compare_versions_for_sort))


             self._node_history_modal_versions_data = history_data # Store in the designated variable
             self._node_history_modal_node_name = node_name
             self._node_history_modal_node_path = node_install_path
             self._node_history_modal_current_commit = current_local_commit # Full local commit ID

             self.app.log_to_gui("Management", f"节点 '{node_name}' 版本历史获取完成。找到 {len(history_data)} 条记录。", "info")
             # Show modal in GUI thread
             self.app.root.after(0, self._show_node_history_modal)

         except threading.ThreadExit:
              self.app.log_to_gui("Management", f"节点 '{node_name}' 历史获取任务已取消。", "warn")
              # Clean up state in GUI thread on cancellation
              self.app.root.after(0, self._cleanup_modal_state)
         except Exception as e:
             error_msg = f"获取节点 '{node_name}' 版本历史失败: {e}"
             self.app.log_to_gui("Management", error_msg, "error")
             # Clean up state and show error in GUI thread
             self.app.root.after(0, self._cleanup_modal_state)
             self.app.root.after(0, lambda msg=error_msg: messagebox.showerror("获取历史失败", msg, parent=self.app.root))


    # Called by _node_history_fetch_task
    def _show_node_history_modal(self):
        """Creates and displays the node version history modal with improved styling resembling the Node list."""
        # Check if the modal is already open or if data is missing
        # Use the getter method
        if self.is_modal_open():
             self.app.log_to_gui("Management", "Attempted to open node history modal, but one is already open.", "warn")
             return # Do nothing if already open

        if not self._node_history_modal_versions_data:
            self.app.log_to_gui("Management", f"没有节点 '{self._node_history_modal_node_name}' 的历史版本数据可显示。", "warn")
            self._cleanup_modal_state() # Clean up state if no data
            return

        node_name = self._node_history_modal_node_name
        history_data = self._node_history_modal_versions_data # Use stored data
        current_commit = self._node_history_modal_current_commit # Full local commit ID

        modal_window = Toplevel(self.app.root)
        self.app.root.eval(f'tk::PlaceWindow {str(modal_window)} center') # Center the modal
        modal_window.title(f"版本切换 - {node_name}")
        modal_window.transient(self.app.root) # Set modal parent
        modal_window.grab_set() # Modal capture events
        modal_window.geometry("850x550") # Adjusted size
        # Use app instance constant
        modal_window.configure(bg=self.app.BG_COLOR)
        modal_window.rowconfigure(0, weight=1); modal_window.columnconfigure(0, weight=1)
        # MOD2: Use the cleanup function when modal is closed by window manager
        modal_window.protocol("WM_DELETE_WINDOW", lambda win=modal_window: self._cleanup_modal_state(win))
        self._node_history_modal_window = modal_window # Store reference


        # Use a single frame to hold header and canvas/scrollbar for items
        # Use app instance constant
        main_modal_frame = ttk.Frame(modal_window, style='Modal.TFrame', padding=10)
        main_modal_frame.grid(row=0, column=0, sticky="nsew")
        main_modal_frame.rowconfigure(1, weight=1) # Allow canvas row to expand
        main_modal_frame.columnconfigure(0, weight=1) # Allow canvas col to expand


        # --- Header Row --- Style and alignment confirmed/refined
        # Use app instance constant
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
        # Use app instance constants
        canvas = tk.Canvas(main_modal_frame, bg=self.app.TEXT_AREA_BG, highlightthickness=1, highlightbackground=self.app.BORDER_COLOR, borderwidth=0) # Use bg directly
        scrollbar = ttk.Scrollbar(main_modal_frame, orient=tk.VERTICAL, command=canvas.yview)
        # scrollable_frame will contain the actual row frames
        # Use app instance constant
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
             row_frame = ttk.Frame(scrollable_frame, style=row_frame_style, padding=(0, 3)) # Keep padding here
             # FIX 2: Grid row_frame into scrollable_frame, spanning ALL columns
             row_frame.grid(row=i, column=0, columnspan=5, sticky="ew", padx=0, pady=0) # No padx/pady on the row_frame itself

             # FIX 2: DO NOT configure columns on row_frame itself.
             # row_frame.columnconfigure(...) <-- REMOVED
             # MODIFICATION: Configure columns on row_frame to match the header
             row_frame.columnconfigure(0, weight=4, minsize=250) # Version Name
             row_frame.columnconfigure(1, weight=1, minsize=80)  # Status
             row_frame.columnconfigure(2, weight=1, minsize=100) # Commit ID
             row_frame.columnconfigure(3, weight=1, minsize=110) # Date
             row_frame.columnconfigure(4, weight=0, minsize=80)  # Button


             try:
                 date_str = item_data['date_iso']
                 # Parse date safely via app instance method
                 date_obj = self.app._parse_iso_date_for_sort(date_str)
                 date_display = date_obj.strftime('%Y-%m-%d') if date_obj else ("解析失败" if date_str else "无日期")
             except Exception:
                 date_display = "日期错误"

             commit_id = item_data['commit_id']
             version_name = item_data['name']
             version_type = item_data['type']
             # description = item_data['description'] # Description is not displayed in columns in the screenshot

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
             # MODIFICATION: Grid into row_frame's columns
             # Use app instance constant for font
             version_label_widget = ttk.Label(row_frame, text=version_display, style=label_style, anchor=tk.W, wraplength=240) # Use fixed wrap for simplicity
             # MODIFICATION: Grid into row_frame, column 0
             version_label_widget.grid(row=0, column=0, sticky='w', padx=(5,0), pady=1) # Use padx for internal horizontal spacing

             status_label_widget = ttk.Label(row_frame, text=status_text, style=status_label_actual_style, anchor=tk.CENTER)
             # MODIFICATION: Grid into row_frame, column 1
             status_label_widget.grid(row=0, column=1, sticky='ew', padx=5, pady=1) # Sticky EW for centering

             # MODIFICATION: Grid into row_frame, column 2
             ttk.Label(row_frame, text=commit_id[:8], style=label_style, anchor=tk.W).grid(row=0, column=2, sticky='w', padx=5, pady=1)
             # MODIFICATION: Grid into row_frame, column 3
             ttk.Label(row_frame, text=date_display, style=label_style, anchor=tk.W).grid(row=0, column=3, sticky='w', padx=5, pady=1)
             # Adding a description label here if needed
             # ttk.Label(row_frame, text=description, style=label_style, anchor=tk.W, wraplength=300).grid(row=0, column=4, sticky='w', padx=5, pady=1) # Example if adding description col


             switch_btn = ttk.Button(row_frame, text="切换", style="Modal.TButton", width=6,
                                     command=lambda c_id=commit_id, win=modal_window, name=node_name: self._on_modal_switch_confirm(win, name, c_id)) # Pass node_name and modal_window
             # MODIFICATION: Grid into row_frame, column 4
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


    # Called by modal closing protocol and task cancellations
    def _cleanup_modal_state(self, modal_window=None):
         """Cleans up modal-related instance variables and destroys the window."""
         self.app.log_to_gui("Management", "Cleaning up modal state...", "info")
         self._node_history_modal_versions_data = []
         self._node_history_modal_node_name = ""
         self._node_history_modal_node_path = ""
         self._node_history_modal_current_commit = ""

         # Destroy the window if it exists and is not already destroyed
         window_to_destroy = modal_window if modal_window else self._node_history_modal_window
         # Use the safe checker method from app instance
         if window_to_destroy and self.app.window_to_exists(window_to_destroy):
             try:
                  # Attempt to unbind mousewheel events if bound specifically during modal creation
                  # This is tricky. If bound to canvas and scrollable_frame, destroying the window
                  # should clean them up. Explicit unbinding is often not needed when destroying
                  # the parent widget, but can be added here if persistent issues occur.
                  # Example: if hasattr(window_to_destroy, '_canvas'): window_to_destroy._canvas.unbind("<MouseWheel>")

                  window_to_destroy.destroy()
                  self.app.log_to_gui("Management", "Modal window destroyed.", "info")
             except tk.TclError:
                 # Window might already be destroyed if this is called multiple times
                 self.app.log_to_gui("Management", "Modal window already destroyed (TclError during destroy).", "info")
                 pass
             except Exception as e:
                 self.app.log_to_gui("Management", f"Error during modal window destruction: {e}", "error")

         # Always clear the reference after attempting destruction
         self._node_history_modal_window = None
         self.app.log_to_gui("Management", "Modal state variables cleared.", "info")

         # Schedule a UI state update to re-enable buttons (Bug 3 Fix)
         self.app.root.after(0, self.app._update_ui_state)
         self.app.log_to_gui("Management", "UI update scheduled after modal cleanup.", "info")


    # Called by modal switch button command
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

        # Check if ComfyUI is running before queuing the task using app instance method
        if self.app._is_comfyui_running() or self.app.comfyui_externally_detected:
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

        self.app.log_to_gui("Management", f"将节点 '{modal_node_name}' 切换到版本 {target_ref[:8]} 任务添加到队列...", "info")
        # Queue the switch task method of this module instance
        self.app.update_task_queue.put((self._switch_node_to_ref_task, [modal_node_name, modal_node_path, target_ref], {})) # Pass correct arguments

        self._cleanup_modal_state(modal_window) # Close modal after queuing task
        self.app._update_ui_state() # Update UI state to show task running


    # Called by _on_modal_switch_confirm
    def _switch_node_to_ref_task(self, node_name, node_install_path, target_ref):
         """Task to switch an installed node to a specific git reference. Runs in worker thread."""
         if self.app.stop_event_set(): # Use the getter method
             self.app.log_to_gui("Management", f"节点 '{node_name}' 切换版本任务已取消 (停止信号)。", "warn")
             return
         self.app.log_to_gui("Management", f"正在将节点 '{node_name}' 切换到版本 (引用: {target_ref[:8]})...", "info")

         try:
             if not os.path.isdir(node_install_path) or not os.path.exists(os.path.join(node_install_path, ".git")):
                  raise Exception(f"节点目录不是有效的 Git 仓库: {node_install_path}")

             # Check for local changes and warn/force checkout using app instance method
             stdout_status, _, _ = self.app._run_git_command(["status", "--porcelain"], cwd=node_install_path, timeout=10, log_output=False)
             if stdout_status.strip():
                  self.app.log_to_gui("Management", f"节点 '{node_name}' 存在未提交的本地修改，将通过 checkout --force 覆盖。", "warn")

             if self.app.stop_event_set(): # Use the getter method
                 raise threading.ThreadExit

             # Checkout the target reference (commit hash, tag, branch name, remote branch name)
             self.app.log_to_gui("Management", f"执行 Git checkout --force {target_ref[:8]}...", "info")
             # Use --force to discard local changes if any and handle detached HEAD gracefully
             # Use app instance method
             _, stderr_checkout, rc_checkout = self.app._run_git_command(["checkout", "--force", target_ref], cwd=node_install_path, timeout=60)
             if rc_checkout != 0:
                 raise Exception(f"Git checkout 失败: {stderr_checkout.strip()}")

             self.app.log_to_gui("Management", f"Git checkout 完成 (引用: {target_ref[:8]}).", "info")

             if self.app.stop_event_set(): # Use the getter method
                 raise threading.ThreadExit

             # Update submodules if .gitmodules exists using app instance method
             if os.path.exists(os.path.join(node_install_path, ".gitmodules")):
                 self.app.log_to_gui("Management", f"执行 Git submodule update for '{node_name}'...", "info")
                 # Use app instance method
                 _, stderr_sub, rc_sub = self.app._run_git_command(["submodule", "update", "--init", "--recursive", "--force"], cwd=node_install_path, timeout=180)
                 if rc_sub != 0:
                     self.app.log_to_gui("Management", f"Git submodule update 失败: {stderr_sub.strip()}", "warn")

             if self.app.stop_event_set(): # Use the getter method
                 raise threading.ThreadExit

             # Re-install Python dependencies if requirements.txt exists
             python_exe = self.app.python_exe_var.get()
             requirements_path = os.path.join(node_install_path, "requirements.txt")
             if python_exe and os.path.isfile(python_exe) and os.path.isfile(requirements_path):
                  self.app.log_to_gui("Management", f"执行 pip 安装节点依赖 for '{node_name}'...", "info")
                  pip_cmd_base = [python_exe, "-m", "pip", "install", "-r", requirements_path, "--upgrade"]
                  pip_cmd_extras = ["--extra-index-url", "https://download.pytorch.org/whl/cu118", "--extra-index-url", "https://download.pytorch.org/whl/cu121"]
                  pip_cmd = pip_cmd_base + pip_cmd_extras
                  is_venv = sys.prefix != sys.base_prefix
                  # Check if the target python_exe is NOT within the launcher's base prefix (heuristic for standalone/portable env)
                  try:
                      relative_path_to_base = os.path.relpath(python_exe, sys.base_prefix)
                      is_outside_launcher_base = relative_path_to_base.startswith('..') or os.path.isabs(relative_path_to_base)
                  except ValueError:
                      is_outside_launcher_base = True

                  if platform.system() != "Windows" and not is_venv and is_outside_launcher_base:
                       self.app.log_to_gui("Management", "目标Python路径可能非系统或虚拟环境安装，使用 --user 选项安装依赖。", "warn")
                       pip_cmd.append("--user")

                  pip_cmd.extend(["--no-cache-dir"])

                  # Use app instance method
                  _, stderr_pip, rc_pip = self.app._run_git_command(pip_cmd, cwd=node_install_path, timeout=180)
                  if rc_pip != 0:
                       self.app.log_to_gui("Management", f"Pip 安装节点依赖失败: {stderr_pip.strip()}", "error")
                       # Show warning in GUI thread
                       self.app.root.after(0, lambda name=node_name: messagebox.showwarning("依赖安装失败", f"节点 '{name}' 的 Python 依赖可能安装失败。\n请查看日志。", parent=self.app.root))
                  else:
                       self.app.log_to_gui("Management", f"Pip 安装节点依赖完成.", "info")

             self.app.log_to_gui("Management", f"节点 '{node_name}' 已成功切换到版本 (引用: {target_ref[:8]})。", "info")
             # Show success message in GUI thread
             self.app.root.after(0, lambda name=node_name, ref=target_ref[:8]: messagebox.showinfo("切换完成", f"节点 '{name}' 已成功切换到版本: {ref}", parent=self.app.root))

         except threading.ThreadExit:
              self.app.log_to_gui("Management", f"节点 '{node_name}' 切换版本任务已取消。", "warn")
         except Exception as e:
             error_msg = f"节点 '{node_name}' 切换版本失败: {e}"
             self.app.log_to_gui("Management", error_msg, "error")
             # Show error message in GUI thread
             self.app.root.after(0, lambda msg=error_msg: messagebox.showerror("切换失败", msg, parent=self.app.root))
         finally:
             # Always refresh node list after attempting a switch by queuing the refresh task
             self.app._queue_node_list_refresh()


    # Helper methods for launcher.py to get state
    def get_selected_main_body_item_data(self):
         """Returns the item data for the currently selected main body version."""
         # Safely check if the Treeview widget exists
         if hasattr(self, 'main_body_tree') and self.main_body_tree and self.main_body_tree.winfo_exists():
              selected_item = self.main_body_tree.focus()
              if selected_item:
                   return self.main_body_tree.item(selected_item, 'values')
         return None

    def get_selected_node_item_data(self):
         """Returns the item data for the currently selected node."""
         # Safely check if the Treeview widget exists
         if hasattr(self, 'nodes_tree') and self.nodes_tree and self.nodes_tree.winfo_exists():
              selected_item = self.nodes_tree.focus()
              if selected_item:
                   return self.nodes_tree.item(selected_item, 'values')
         return None

    def get_nodes_search_term(self):
         """Returns the current text in the node search entry."""
         # Safely check if the Entry widget exists
         if hasattr(self, 'nodes_search_entry') and self.nodes_search_entry and self.nodes_search_entry.winfo_exists():
              return self.nodes_search_entry.get().strip()
         return ""

    def is_modal_open(self):
         """Returns True if the node history modal is currently open."""
         # Check for the instance variable and if the window still exists using the safe checker method from app instance
         return self._node_history_modal_window is not None and self.app.window_to_exists(self._node_history_modal_window)


# Function to be called by launcher.py to setup this tab
def setup_management_tab(parent_frame, app_instance):
    """Entry point for the Management tab module."""
    # Create and return the instance of the ManagementTab class
    return ManagementTab(parent_frame, app_instance)