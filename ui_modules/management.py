# -*- coding: utf-8 -*-
# File: ui_modules/management.py
# Version: Kerry, Ver. 2.6.1 - Management Tab Module (Fixed Attribute Errors)

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
        self.current_main_body_version_label = None
        self.refresh_main_body_button = None
        self.activate_main_body_button = None
        self.search_nodes_button = None
        self.refresh_nodes_button = None
        self.switch_install_node_button = None
        self.uninstall_node_button = None
        self.update_all_nodes_button = None

        # Persistence file paths relative to ui_modules directory
        self.MAIN_BODY_VERSIONS_FILE = os.path.join(self.app.base_project_dir, "ui_modules", "main_body_versions.json")
        self.NODES_LIST_FILE = os.path.join(self.app.base_project_dir, "ui_modules", "nodes_list.json")

        self._setup_ui()
        self._load_state()

    def _setup_ui(self):
        """Builds the UI elements for the Management tab."""
        current_row = 0
        frame_padx = 5
        frame_pady = (0, 10)
        widget_pady = 3
        widget_padx = 5

        repo_address_group = ttk.LabelFrame(self.frame, text=" 仓库地址 / Repository Address ", padding=(10, 5))
        repo_address_group.grid(row=current_row, column=0, sticky="ew", padx=frame_padx, pady=frame_pady)
        repo_address_group.columnconfigure(1, weight=1)
        repo_row = 0
        ttk.Label(repo_address_group, text="本体仓库地址:", anchor=tk.W).grid(row=repo_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        main_repo_entry = ttk.Entry(repo_address_group, textvariable=self.app.main_repo_url_var)
        main_repo_entry.grid(row=repo_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx)
        repo_row += 1
        ttk.Label(repo_address_group, text="节点配置地址:", anchor=tk.W).grid(row=repo_row, column=0, sticky=tk.W, pady=widget_pady, padx=widget_padx)
        node_config_entry = ttk.Entry(repo_address_group, textvariable=self.app.node_config_url_var)
        node_config_entry.grid(row=repo_row, column=1, sticky="ew", pady=widget_pady, padx=widget_padx)
        repo_row += 1

        current_row += 1

        version_node_management_group = ttk.LabelFrame(self.frame, text=" 版本与节点管理 / Version & Node Management ", padding=(10, 5))
        version_node_management_group.grid(row=current_row, column=0, sticky="nsew", padx=frame_padx, pady=frame_pady)
        version_node_management_group.columnconfigure(0, weight=1)
        version_node_management_group.rowconfigure(0, weight=1)

        node_notebook = ttk.Notebook(version_node_management_group, style='TNotebook')
        node_notebook.grid(row=0, column=0, sticky="nsew")
        node_notebook.enable_traversal()

        # --- 本体 Sub-tab ---
        self.main_body_frame = ttk.Frame(node_notebook, style='TFrame', padding=5)
        self.main_body_frame.columnconfigure(0, weight=1)
        self.main_body_frame.rowconfigure(1, weight=1)
        node_notebook.add(self.main_body_frame, text=' 本体 / Main Body ')

        main_body_control_frame = ttk.Frame(self.main_body_frame, style='TabControl.TFrame', padding=(5, 5))
        main_body_control_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5), columnspan=2)
        main_body_control_frame.columnconfigure(1, weight=1)

        ttk.Label(main_body_control_frame, text="当前本体版本:", style='TLabel').grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.current_main_body_version_label = ttk.Label(main_body_control_frame, textvariable=self.app.current_main_body_version_var, style='TLabel', anchor=tk.W, font=(self.app.FONT_FAMILY_UI, self.app.FONT_SIZE_NORMAL, self.app.FONT_WEIGHT_BOLD)) # Use self.app
        self.current_main_body_version_label.grid(row=0, column=0, sticky=tk.W, padx=(90, 5))
        ttk.Label(main_body_control_frame, text="", style='TLabel').grid(row=0, column=1, sticky="ew")

        self.refresh_main_body_button = ttk.Button(main_body_control_frame, text="刷新版本", style="Tab.TButton", command=self.app._queue_main_body_refresh)
        self.refresh_main_body_button.grid(row=0, column=2, padx=(0, 5))
        self.activate_main_body_button = ttk.Button(main_body_control_frame, text="激活选中版本", style="TabAccent.TButton", command=self.app._queue_main_body_activation)
        self.activate_main_body_button.grid(row=0, column=3)

        self.main_body_tree = ttk.Treeview(self.main_body_frame, columns=("version", "commit_id", "date", "description"), show="headings", style='Treeview')
        self.main_body_tree.heading("version", text="版本"); self.main_body_tree.column("version", width=150, stretch=tk.NO)
        self.main_body_tree.heading("commit_id", text="提交ID"); self.main_body_tree.column("commit_id", width=100, stretch=tk.NO, anchor=tk.CENTER)
        self.main_body_tree.heading("date", text="日期"); self.main_body_tree.column("date", width=120, stretch=tk.NO, anchor=tk.CENTER)
        self.main_body_tree.heading("description", text="描述"); self.main_body_tree.column("description", width=300, stretch=tk.YES)
        self.main_body_tree.grid(row=1, column=0, sticky="nsew")
        self.main_body_scrollbar = ttk.Scrollbar(self.main_body_frame, orient=tk.VERTICAL, command=self.main_body_tree.yview)
        self.main_body_tree.configure(yscrollcommand=self.main_body_scrollbar.set)
        self.main_body_scrollbar.grid(row=1, column=1, sticky="ns")
        self.main_body_tree.bind("<<TreeviewSelect>>", lambda event: self.app._update_ui_state())
        try: # Use app constants for tag configuration
             self.main_body_tree.tag_configure('highlight', foreground=self.app.FG_HIGHLIGHT, font=(self.app.FONT_FAMILY_UI, self.app.FONT_SIZE_NORMAL, self.app.FONT_WEIGHT_BOLD))
             self.main_body_tree.tag_configure('persisted', foreground=self.app.FG_MUTED)
        except tk.TclError:
             pass


        # --- 节点 Sub-tab ---
        self.nodes_frame = ttk.Frame(node_notebook, style='TFrame', padding=5)
        self.nodes_frame.columnconfigure(0, weight=1)
        self.nodes_frame.rowconfigure(2, weight=1)
        node_notebook.add(self.nodes_frame, text=' 节点 / Nodes ')

        nodes_control_frame = ttk.Frame(self.nodes_frame, style='TabControl.TFrame', padding=(5, 5))
        nodes_control_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5), columnspan=2)

        search_frame = ttk.Frame(nodes_control_frame, style='TabControl.TFrame')
        search_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.nodes_search_entry = ttk.Entry(search_frame, width=40)
        self.nodes_search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_nodes_button = ttk.Button(search_frame, text="搜索", style="Tab.TButton", command=self.app._queue_node_list_refresh)
        self.search_nodes_button.pack(side=tk.LEFT, padx=(5, 0))

        nodes_buttons_container = ttk.Frame(nodes_control_frame, style='TabControl.TFrame')
        nodes_buttons_container.pack(side=tk.RIGHT)
        self.refresh_nodes_button = ttk.Button(nodes_buttons_container, text="刷新列表", style="Tab.TButton", command=self.app._queue_node_list_refresh)
        self.refresh_nodes_button.pack(side=tk.LEFT, padx=(0, 5))
        self.switch_install_node_button = ttk.Button(nodes_buttons_container, text="切换版本", style="Tab.TButton", command=self.app._queue_node_switch_or_show_history)
        self.switch_install_node_button.pack(side=tk.LEFT, padx=5)
        self.uninstall_node_button = ttk.Button(nodes_buttons_container, text="卸载节点", style="Tab.TButton", command=self.app._queue_node_uninstall)
        self.uninstall_node_button.pack(side=tk.LEFT, padx=5)
        self.update_all_nodes_button = ttk.Button(nodes_buttons_container, text="更新全部", style="TabAccent.TButton", command=self.app._queue_all_nodes_update)
        self.update_all_nodes_button.pack(side=tk.LEFT, padx=5)

        ttk.Label(self.nodes_frame, text="列表默认显示本地 custom_nodes 目录下的全部节点。输入内容后点击“搜索”显示匹配的本地/在线节点。", style='Hint.TLabel').grid(row=1, column=0, sticky=tk.W, padx=5, pady=(0, 5), columnspan=2)

        self.nodes_tree = ttk.Treeview(self.nodes_frame, columns=("name", "status", "local_id", "repo_info", "repo_url"), show="headings", style='Treeview')
        self.nodes_tree.heading("name", text="节点名称"); self.nodes_tree.column("name", width=200, stretch=tk.YES)
        self.nodes_tree.heading("status", text="状态"); self.nodes_tree.column("status", width=80, stretch=tk.NO, anchor=tk.CENTER)
        self.nodes_tree.heading("local_id", text="本地ID"); self.nodes_tree.column("local_id", width=100, stretch=tk.NO, anchor=tk.CENTER)
        self.nodes_tree.heading("repo_info", text="仓库信息"); self.nodes_tree.column("repo_info", width=180, stretch=tk.NO)
        self.nodes_tree.heading("repo_url", text="仓库地址"); self.nodes_tree.column("repo_url", width=300, stretch=tk.YES)
        self.nodes_tree.grid(row=2, column=0, sticky="nsew")
        self.nodes_scrollbar = ttk.Scrollbar(self.nodes_frame, orient=tk.VERTICAL, command=self.nodes_tree.yview)
        self.nodes_tree.configure(yscrollcommand=self.nodes_scrollbar.set)
        self.nodes_scrollbar.grid(row=2, column=1, sticky="ns")
        try: # Use app constants for tag configuration
            self.nodes_tree.tag_configure('installed', foreground=self.app.FG_INFO)
            self.nodes_tree.tag_configure('not_installed', foreground=self.app.FG_MUTED)
            self.nodes_tree.tag_configure('persisted', foreground=self.app.FG_MUTED)
        except tk.TclError:
            pass
        self.nodes_tree.bind("<<TreeviewSelect>>", lambda event: self.app._update_ui_state())
        self.nodes_search_entry.bind("<KeyRelease>", lambda event: self.app._update_ui_state())


    # --- Persistence Handling ---
    def _load_state(self):
        """Loads main body versions and node list from persistence files."""
        self.app.log_to_gui("Management", "尝试加载持久化数据...", "info")
        try:
            os.makedirs(os.path.dirname(self.MAIN_BODY_VERSIONS_FILE), exist_ok=True)
            os.makedirs(os.path.dirname(self.NODES_LIST_FILE), exist_ok=True)

            if os.path.exists(self.MAIN_BODY_VERSIONS_FILE):
                with open(self.MAIN_BODY_VERSIONS_FILE, 'r', encoding='utf-8') as f:
                    self.remote_main_body_versions = json.load(f)
                self.app.log_to_gui("Management", f"从 {self.MAIN_BODY_VERSIONS_FILE} 加载了 {len(self.remote_main_body_versions)} 条本体版本数据。", "info")
                self.app.root.after(0, lambda list_to_populate=self.remote_main_body_versions: self._populate_main_body_treeview(list_to_populate, persisted=True))
            else:
                self.app.log_to_gui("Management", f"本体版本持久化文件 {self.MAIN_BODY_VERSIONS_FILE} 未找到。", "warn")
                self.remote_main_body_versions = []
                self.app.root.after(0, lambda list_to_populate=[]: self._populate_main_body_treeview(list_to_populate, persisted=True))


            if os.path.exists(self.NODES_LIST_FILE):
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

                search_term_value = ""
                try:
                    if self.nodes_search_entry and self.nodes_search_entry.winfo_exists():
                        search_term_value = self.nodes_search_entry.get().strip().lower()
                except tk.TclError:
                    pass

                filtered_nodes = sorted(self.local_nodes_only, key=lambda x: x.get('name', '').lower()) if search_term_value == "" else sorted([
                    node for node in self.all_known_nodes
                    if search_term_value in node.get('name', '').lower() or \
                       search_term_value in node.get('repo_url', '').lower() or \
                       search_term_value in node.get('status', '').lower()
                ], key=lambda x: x.get('name', '').lower())
                self.app.root.after(0, lambda list_to_populate=filtered_nodes: self._populate_nodes_treeview(list_to_populate, persisted=True))
            else:
                self.app.log_to_gui("Management", f"节点列表持久化文件 {self.NODES_LIST_FILE} 未找到。", "warn")
                self.local_nodes_only = []
                self.all_known_nodes = []
                self.app.root.after(0, lambda list_to_populate=[]: self._populate_nodes_treeview(list_to_populate, persisted=True))


        except (json.JSONDecodeError, IOError, OSError) as e:
            self.app.log_to_gui("Management", f"加载持久化文件时出错: {e}", "error")
            self.remote_main_body_versions = []
            self.local_nodes_only = []
            self.all_known_nodes = []
            self.app.root.after(0, lambda: [
                 self._populate_main_body_treeview([], persisted=True),
                 self._populate_nodes_treeview([], persisted=True)
            ])
        except Exception as e:
            self.app.log_to_gui("Management", f"加载持久化数据时发生意外错误: {e}", "error")
            self.remote_main_body_versions = []
            self.local_nodes_only = []
            self.all_known_nodes = []
            self.app.root.after(0, lambda: [
                 self._populate_main_body_treeview([], persisted=True),
                 self._populate_nodes_treeview([], persisted=True)
            ])


    def _save_state(self):
        """Saves the current main body versions and node lists to persistence files."""
        try:
            os.makedirs(os.path.dirname(self.MAIN_BODY_VERSIONS_FILE), exist_ok=True)

            with open(self.MAIN_BODY_VERSIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.remote_main_body_versions, f, indent=4, ensure_ascii=False)
            self.app.log_to_gui("Management", f"本体版本数据已保存到 {self.MAIN_BODY_VERSIONS_FILE}", "info")

            os.makedirs(os.path.dirname(self.NODES_LIST_FILE), exist_ok=True)
            nodes_save_data = {
                 'local_nodes_only': self.local_nodes_only,
                 'all_known_nodes': self.all_known_nodes
            }
            with open(self.NODES_LIST_FILE, 'w', encoding='utf-8') as f:
                json.dump(nodes_save_data, f, indent=4, ensure_ascii=False)
            self.app.log_to_gui("Management", f"节点列表数据已保存到 {self.NODES_LIST_FILE}", "info")

        except Exception as e:
            self.app.log_to_gui("Management", f"保存持久化文件时出错: {e}", "error")


    # --- Treeview Population Helpers (Run in GUI thread via app.root.after) ---
    def _populate_main_body_treeview(self, versions_list, persisted=False):
         """Populates the main body Treeview from a list of version data."""
         if not self.main_body_tree or not self.main_body_tree.winfo_exists():
              return
         try:
              self.main_body_tree.delete(*self.main_body_tree.get_children())

              if not versions_list:
                   display_message = "未获取到本体版本信息" if not persisted else "从持久化文件加载失败或无数据"
                   self.main_body_tree.insert("", tk.END, values=("", display_message, "", ""))
                   return

              current_local_commit = self.app._get_current_local_main_body_commit()

              for ver_data in versions_list:
                  ver_data.setdefault('type', '未知')
                  ver_data.setdefault('name', 'N/A')
                  ver_data.setdefault('commit_id', 'N/A')
                  ver_data.setdefault('date_iso', '')
                  ver_data.setdefault('description', 'N/A')

                  version_display = f"{ver_data['type']} / {ver_data['name']}"
                  commit_display = ver_data.get("commit_id", "N/A")[:8]

                  date_obj = self.app._parse_iso_date_for_sort(ver_data['date_iso'])
                  date_display = date_obj.strftime('%Y-%m-%d') if date_obj else ("解析失败" if ver_data['date_iso'] else "无日期")

                  description_display = ver_data['description']

                  tags = ()
                  if current_local_commit and ver_data.get('commit_id') == current_local_commit:
                       tags += ('highlight',)
                  if persisted:
                       tags += ('persisted',)


                  self.main_body_tree.insert("", tk.END, values=(version_display, commit_display, date_display, description_display), tags=tags)

              self.app.log_to_gui("Management", f"本体版本列表已在 GUI 中显示 ({len(versions_list)} 条)。", "info")

         except tk.TclError as e:
             self.app.log_to_gui("Management", f"TclError populating main body treeview: {e}", "error")
         except Exception as e:
             self.app.log_to_gui("Management", f"意外错误 populating main body treeview: {e}", "error")


    def _populate_nodes_treeview(self, nodes_list, persisted=False):
         """Populates the nodes Treeview from a list of node data."""
         if not self.nodes_tree or not self.nodes_tree.winfo_exists():
              return
         try:
              self.nodes_tree.delete(*self.nodes_tree.get_children())

              if not nodes_list:
                  display_message = "未找到匹配的节点" if (self.nodes_search_entry and self.nodes_search_entry.winfo_exists() and self.nodes_search_entry.get().strip()) else ("未找到本地节点" if not persisted else "从持久化文件加载失败或无数据")
                  self.nodes_tree.insert("", tk.END, values=("", display_message, "", "", ""))
                  return

              for node_data in nodes_list:
                  node_data.setdefault("name", "N/A")
                  node_data.setdefault("status", "未知")
                  node_data.setdefault("local_id", "N/A")
                  node_data.setdefault("repo_info", "N/A")
                  node_data.setdefault("repo_url", "N/A")
                  node_data.setdefault("is_git", False)
                  node_data.setdefault("local_commit_full", None)
                  node_data.setdefault("remote_branch", None)


                  tags = ()
                  if node_data.get('status') == '已安装':
                      tags += ('installed',)
                  else:
                      tags += ('not_installed',)
                  if persisted:
                      tags += ('persisted',)


                  self.nodes_tree.insert("", tk.END, values=(
                       node_data.get("name", "N/A"),
                       node_data.get("status", "未知"),
                       node_data.get("local_id", "N/A"),
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
        if self.app.stop_event_set():
             self.app.log_to_gui("Management", "本体版本刷新任务已取消 (停止信号)。", "warn")
             return
        self.app.log_to_gui("Management", "刷新本体版本列表...", "info")

        main_repo_url = self.app.main_repo_url_var.get()
        comfyui_dir = self.app.comfyui_dir_var.get()
        git_path_ok = self.app._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=False)
        is_git_repo = git_path_ok and comfyui_dir and os.path.isdir(comfyui_dir) and os.path.isdir(os.path.join(comfyui_dir, ".git"))

        local_version_display = "未知 / Unknown"
        current_local_commit = None
        if is_git_repo:
             stdout_id_full, _, rc_full = self.app._run_git_command(["rev-parse", "HEAD"], cwd=comfyui_dir, timeout=10, log_output=False)
             if rc_full == 0 and stdout_id_full:
                  current_local_commit = stdout_id_full.strip()
                  stdout_id_short = current_local_commit[:8]
                  local_version_display = f"本地 Commit: {stdout_id_short}"

                  stdout_sym_ref, _, rc_sym_ref = self.app._run_git_command(["symbolic-ref", "-q", "--short", "HEAD"], cwd=comfyui_dir, timeout=5, log_output=False)
                  if rc_sym_ref == 0 and stdout_sym_ref:
                       local_version_display = f"本地 Branch: {stdout_sym_ref.strip()} ({stdout_id_short})"
                  else:
                       stdout_desc, _, rc_desc = self.app._run_git_command(["describe", "--all", "--long", "--always"], cwd=comfyui_dir, timeout=10, log_output=False)
                       if rc_desc == 0 and stdout_desc:
                            local_version_display = f"本地: {stdout_desc.strip()}"

             else:
                  local_version_display = "读取本地版本失败"
                  self.app.log_to_gui("Management", "无法获取本地本体版本信息。", "warn")
        else:
             local_version_display = "非 Git 仓库或路径无效"

        self.app.root.after(0, lambda lv=local_version_display: self.app.current_main_body_version_var.set(lv))

        if self.app.stop_event_set():
            self.app.log_to_gui("Management", "本体版本刷新任务已取消 (停止信号)。", "warn")
            return

        all_versions = []
        if is_git_repo and main_repo_url:
             self.app.log_to_gui("Management", f"尝试从 {main_repo_url} 刷新远程版本列表...", "info")
             stdout_get_url, _, rc_get_url = self.app._run_git_command(["remote", "get-url", "origin"], cwd=comfyui_dir, timeout=10, log_output=False)
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

             if self.app.stop_event_set():
                 self.app.log_to_gui("Management", "本体版本刷新任务已取消 (停止信号)。", "warn")
                 return

             self.app.log_to_gui("Management", "执行 Git fetch origin --prune --tags -f...", "info")
             _, stderr_fetch, rc_fetch = self.app._run_git_command(["fetch", "origin", "--prune", "--tags", "-f"], cwd=comfyui_dir, timeout=180)
             if rc_fetch != 0:
                  self.app.log_to_gui("Management", f"Git fetch 失败: {stderr_fetch.strip()}", "error")
                  self.app.root.after(0, lambda: self._populate_main_body_treeview([{"name":"获取失败", "commit_id":"", "date_iso":"", "description":"无法获取远程版本信息"}]))
                  return

             if self.app.stop_event_set():
                 self.app.log_to_gui("Management", "本体版本刷新任务已取消 (停止信号)。", "warn")
                 return

             branches_output, _, _ = self.app._run_git_command(
                  ["for-each-ref", "refs/remotes/origin/", "--sort=-committerdate", "--format=%(refname:short) %(objectname) %(committerdate:iso-strict) %(contents:subject)"],
                  cwd=comfyui_dir, timeout=60 )
             for line in branches_output.splitlines():
                  parts = line.split(' ', 3)
                  if len(parts) >= 3:
                       refname, commit_id, date_iso = parts[0].replace("origin/", ""), parts[1], parts[2]
                       description = parts[3].strip() if len(parts) == 4 else ""
                       if "HEAD->" not in refname:
                            all_versions.append({"type": "branch", "name": refname, "commit_id": commit_id, "date_iso": date_iso, "description": description})
                  elif len(parts) == 2:
                        refname, commit_id = parts[0].replace("origin/", ""), parts[1]
                        if "HEAD->" not in refname:
                             all_versions.append({"type": "branch", "name": refname, "commit_id": commit_id, "date_iso": "", "description": ""})


             if self.app.stop_event_set():
                 self.app.log_to_gui("Management", "本体版本刷新任务已取消 (停止信号)。", "warn")
                 return

             tags_output, _, _ = self.app._run_git_command(
                  ["for-each-ref", "refs/tags/", "--sort=-taggerdate", "--format=%(refname:short) %(objectname) %(taggerdate:iso-strict) %(contents:subject)"],
                  cwd=comfyui_dir, timeout=60 )
             for line in tags_output.splitlines():
                  parts = line.split(' ', 3)
                  if len(parts) >= 3:
                       refname, commit_id, date_iso = parts[0].replace("refs/tags/", ""), parts[1], parts[2]
                       description = parts[3].strip() if len(parts) == 4 else ""
                       all_versions.append({"type": "tag", "name": refname, "commit_id": commit_id, "date_iso": date_iso, "description": description})
                  elif len(parts) == 2:
                       refname, commit_id = parts[0].replace("refs/tags/", ""), parts[1]
                       all_versions.append({"type": "tag", "name": refname, "commit_id": commit_id, "date_iso": "", "description": ""})

             if current_local_commit:
                 is_local_listed = any(v.get('commit_id', '') == current_local_commit for v in all_versions)
                 if not is_local_listed:
                     self.app.log_to_gui("Management", "获取当前本地 Commit 信息...", "info")
                     head_date_stdout, _, rc_head_date = self.app._run_git_command(["log", "-1", "--format=%ci", "HEAD"], cwd=comfyui_dir, timeout=5, log_output=False)
                     head_subject_stdout, _, rc_head_subject = self.app._run_git_command(["log", "-1", "--format=%s", "HEAD"], cwd=comfyui_dir, timeout=5, log_output=False)

                     head_date_iso = head_date_stdout.strip() if rc_head_date == 0 else None
                     head_description = head_subject_stdout.strip() if rc_head_subject == 0 else "当前工作目录"

                     date_obj = self.app._parse_iso_date_for_sort(head_date_iso)
                     final_date_iso = date_obj.isoformat() if date_obj else datetime.now(timezone.utc).isoformat()

                     head_sym_ref_out, _, rc_head_sym_ref = self.app._run_git_command(["symbolic-ref", "-q", "--short", "HEAD"], cwd=comfyui_dir, timeout=2, log_output=False)
                     head_type = "commit (HEAD)" if rc_head_sym_ref != 0 else "branch (local)"
                     head_name = head_sym_ref_out.strip() if head_type == "branch (local)" else f"Detached at {current_local_commit[:8]}"

                     all_versions.append({"type": head_type, "name": head_name, "commit_id": current_local_commit, "date_iso": final_date_iso, "description": head_description})
                     self.app.log_to_gui("Management", f"添加当前本地 HEAD ({current_local_commit[:8]}) 到列表。", "info")


             all_versions.sort(key=cmp_to_key(self.app._compare_versions_for_sort))

        else:
             self.app.log_to_gui("Management", "无法获取远程版本信息 (非Git仓库或缺少URL)。", "warn")
             self.app.root.after(0, lambda: self._populate_main_body_treeview([{"name":"无远程信息", "commit_id":"", "date_iso":"", "description":""}]))
             self.remote_main_body_versions = []
             self.app.log_to_gui("Management", "本体版本列表刷新完成 (无远程信息)。", "info")
             self._save_state()
             return

        self.remote_main_body_versions = all_versions
        self._save_state()

        self.app.root.after(0, lambda list_to_populate=all_versions: self._populate_main_body_treeview(list_to_populate))

        self.app.log_to_gui("Management", f"本体版本列表刷新完成。找到 {len(all_versions)} 条记录。", "info")


    # Called by app._queue_main_body_activation
    def _activate_main_body_version_task(self, comfyui_dir, target_ref):
        """Task to execute git commands for activating main body version. Runs in worker thread."""
        if self.app.stop_event_set():
            self.app.log_to_gui("Management", "本体版本激活任务已取消 (停止信号)。", "warn")
            return
        self.app.log_to_gui("Management", f"正在激活本体版本 (引用: {target_ref[:8]})...", "info")

        try:
            if self.app.stop_event_set():
                raise threading.ThreadExit

            stdout_status, _, _ = self.app._run_git_command(["status", "--porcelain"], cwd=comfyui_dir, timeout=10, log_output=False)
            if stdout_status.strip():
                 self.app.log_to_gui("Management", "检测到本体目录存在未提交的本地修改，将通过 reset --hard 覆盖。", "warn")
                 self.app.log_to_gui("Management", "执行 Git reset --hard...", "info")
                 _, stderr_reset, rc_reset = self.app._run_git_command(["reset", "--hard"], cwd=comfyui_dir, timeout=30)
                 if rc_reset != 0:
                     self.app.log_to_gui("Management", f"Git reset --hard 失败: {stderr_reset.strip()}", "warn")

            self.app.log_to_gui("Management", f"执行 Git checkout --force {target_ref[:8]}...", "info")
            _, stderr_checkout, rc_checkout = self.app._run_git_command(["checkout", "--force", target_ref], cwd=comfyui_dir, timeout=60)
            if rc_checkout != 0:
                raise Exception(f"Git checkout --force 失败: {stderr_checkout.strip()}")

            self.app.log_to_gui("Management", f"Git checkout 完成 (引用: {target_ref[:8]}).", "info")

            if self.app.stop_event_set():
                raise threading.ThreadExit

            if os.path.exists(os.path.join(comfyui_dir, ".gitmodules")):
                 self.app.log_to_gui("Management", "执行 Git submodule update...", "info")
                 _, stderr_sub, rc_sub = self.app._run_git_command(["submodule", "update", "--init", "--recursive", "--force"], cwd=comfyui_dir, timeout=180)
                 if rc_sub != 0:
                     self.app.log_to_gui("Management", f"Git submodule update 失败: {stderr_sub.strip()}", "warn")

            if self.app.stop_event_set():
                raise threading.ThreadExit

            # --- Continue from here ---
            python_exe = self.app.python_exe_var.get()
            requirements_path = os.path.join(comfyui_dir, "requirements.txt")
            if python_exe and os.path.isfile(python_exe) and os.path.isfile(requirements_path):
                 self.app.log_to_gui("Management", "执行 pip 安装依赖...", "info")
                 pip_cmd_base = [python_exe, "-m", "pip", "install", "-r", requirements_path, "--upgrade"]
                 pip_cmd_extras = []
                 pip_cmd_extras.extend(["--extra-index-url", "https://download.pytorch.org/whl/cu118", "--extra-index-url", "https://download.pytorch.org/whl/cu121"])

                 pip_cmd = pip_cmd_base + pip_cmd_extras
                 is_venv = sys.prefix != sys.base_prefix
                 # Check if python_exe is within a venv/portable path, NOT if the *launcher* is in a venv
                 # A simple check: if the python_exe path contains "venv" or "envs" or is not within the base python install
                 # A more robust check is difficult without knowing the specific python distribution.
                 # Let's stick to the sys.prefix check as a simple heuristic, assuming the user sets the path correctly.
                 if platform.system() != "Windows" and not is_venv: # if NOT Windows AND NOT in a VENV (sys.prefix != sys.base_prefix)
                      # Check if the python_exe path itself is not within the *system* base prefix
                      # This is a slightly better heuristic for detecting non-system installs on Linux/macOS
                      try:
                           # Check if python_exe is a sub-path of sys.base_prefix
                           relative_path = os.path.relpath(python_exe, sys.base_prefix)
                           if relative_path.startswith('..') or os.path.isabs(relative_path): # Not within base prefix
                                # Might be a user-installed python or portable env outside the system venv check
                                # Revert to the simpler sys.base_prefix check for --user
                                if sys.base_prefix == sys.prefix: # Check if we are in the system's base environment
                                     pip_cmd.append("--user")
                                     self.app.log_to_gui("Management", "非虚拟环境 (系统安装)，使用 --user 选项安装依赖。", "warn")
                                else:
                                     # We are in a venv or equivalent, do not use --user
                                     pass # Already handled by the `not is_venv` check
                           # Else: python_exe is inside sys.base_prefix, likely part of a venv/system install, don't use --user
                      except ValueError: # Path mismatch (e.g., different drive on Windows, unlikely on Linux/macOS)
                           # Assume not in a venv if relpath fails
                           if sys.base_prefix == sys.prefix:
                                pip_cmd.append("--user")
                                self.app.log_to_gui("Management", "无法确定Python环境，假定非虚拟环境并使用 --user。", "warn")


                 pip_cmd.extend(["--no-cache-dir"]) # Added --no-cache-dir

                 _, stderr_pip, rc_pip = self.app._run_git_command(pip_cmd, cwd=comfyui_dir, timeout=600) # Longer timeout for pip
                 if rc_pip != 0:
                      self.app.log_to_gui("Management", f"Pip 安装依赖失败: {stderr_pip.strip()}", "error")
                      self.app.root.after(0, lambda: messagebox.showwarning("依赖安装失败", "Python 依赖安装失败，新版本可能无法正常工作。\n请查看日志获取详情。", parent=self.app.root))
                 else:
                      self.app.log_to_gui("Management", "Pip 安装依赖完成。", "info")
            else:
                 self.app.log_to_gui("Management", "Python 或 requirements.txt 无效，跳过依赖安装。", "warn")

            # Success
            self.app.log_to_gui("Management", f"本体版本激活流程完成 (引用: {target_ref[:8]})。", "info")
            self.app.root.after(0, lambda ref=target_ref[:8]: messagebox.showinfo("激活完成", f"本体版本已激活到: {ref}", parent=self.app.root))

        except threading.ThreadExit:
             self.app.log_to_gui("Management", "本体版本激活任务已取消。", "warn")
        except Exception as e:
            error_msg = f"本体版本激活流程失败: {e}"
            self.app.log_to_gui("Management", error_msg, "error")
            self.app.root.after(0, lambda msg=str(e): messagebox.showerror("激活失败", msg, parent=self.app.root))
        finally:
            # Always refresh the list after attempting activation
            self.app._queue_main_body_refresh()


    # Called by app._run_initial_background_tasks and app._queue_node_list_refresh
    def refresh_node_list(self):
        """Fetches and displays custom node list (local scan + online config), applying filter. Runs in worker thread."""
        if self.app.stop_event_set():
            self.app.log_to_gui("Management", "节点列表刷新任务已取消 (停止信号)。", "warn")
            return
        self.app.log_to_gui("Management", "刷新节点列表...", "info")

        node_config_url = self.app.node_config_url_var.get()
        comfyui_nodes_dir = self.app.comfyui_nodes_dir
        search_term_value = ""
        try:
            if hasattr(self, 'nodes_search_entry') and self.nodes_search_entry.winfo_exists():
                search_term_value = self.nodes_search_entry.get().strip().lower()
        except tk.TclError:
            pass

        git_path_ok = self.app._validate_paths_for_execution(check_comfyui=False, check_git=True, show_error=False)
        is_nodes_dir_valid = comfyui_nodes_dir and os.path.isdir(comfyui_nodes_dir)

        local_nodes = []
        if is_nodes_dir_valid:
             self.app.log_to_gui("Management", f"扫描本地 custom_nodes 目录: {comfyui_nodes_dir}...", "info")
             try:
                  item_names = sorted([d for d in os.listdir(comfyui_nodes_dir) if os.path.isdir(os.path.join(comfyui_nodes_dir, d))])
                  for item_name in item_names:
                       if self.app.stop_event_set():
                           raise threading.ThreadExit

                       item_path = os.path.join(comfyui_nodes_dir, item_name)
                       node_info = {"name": item_name, "status": "已安装", "local_id": "N/A", "local_commit_full": None, "repo_info": "本地安装", "repo_url": "本地安装", "is_git": False, "remote_branch": None}

                       if git_path_ok and os.path.isdir(os.path.join(item_path, ".git")):
                            node_info["is_git"] = True

                            stdout_id_full, _, rc_id_full = self.app._run_git_command(["rev-parse", "HEAD"], cwd=item_path, timeout=5, log_output=False)
                            node_info["local_commit_full"] = stdout_id_full.strip() if rc_id_full == 0 and stdout_id_full else None
                            node_info["local_id"] = node_info["local_commit_full"][:8] if node_info["local_commit_full"] else "获取失败"

                            stdout_url, _, rc_url = self.app._run_git_command(["config", "--get", "remote.origin.url"], cwd=item_path, timeout=5, log_output=False)
                            node_info["repo_url"] = stdout_url.strip() if rc_url == 0 and stdout_url and stdout_url.strip().endswith(".git") else "无远程仓库"

                            upstream_stdout, _, rc_upstream = self.app._run_git_command(["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd=item_path, timeout=5, log_output=False)
                            upstream_ref = upstream_stdout.strip() if rc_upstream == 0 and upstream_stdout else None

                            repo_info_display = "无远程跟踪"
                            if upstream_ref and upstream_ref.startswith("origin/"):
                                remote_branch_name = upstream_ref.replace("origin/", "")
                                node_info["remote_branch"] = remote_branch_name

                                log_cmd = ["log", "-1", "--format=%H %ci %s", upstream_ref]
                                stdout_log, _, rc_log = self.app._run_git_command(log_cmd, cwd=item_path, timeout=10, log_output=False)
                                if rc_log == 0 and stdout_log:
                                     log_parts = stdout_log.strip().split(' ', 2)
                                     if len(log_parts) >= 2:
                                          full_commit_id_remote = log_parts[0]
                                          date_iso = log_parts[1]
                                          subject = log_parts[2].strip() if len(log_parts) == 3 else ""

                                          remote_commit_id_short = full_commit_id_remote[:8]
                                          date_obj = self.app._parse_iso_date_for_sort(date_iso)
                                          remote_commit_date = date_obj.strftime('%Y-%m-%d') if date_obj else "未知日期"
                                          repo_info_display = f"{remote_branch_name} {remote_commit_id_short} ({remote_commit_date})"
                                     else:
                                          repo_info_display = f"{remote_branch_name} (日志解析失败)"
                                else:
                                     repo_info_display = f"{remote_branch_name} (信息获取失败)"
                            elif upstream_ref:
                                 repo_info_display = f"跟踪: {upstream_ref}"

                            node_info["repo_info"] = repo_info_display

                       local_nodes.append(node_info)

             except threading.ThreadExit:
                 self.app.log_to_gui("Management", "节点列表扫描任务已取消 (停止信号)。", "warn")
                 return
             except Exception as e:
                  self.app.log_to_gui("Management", f"扫描本地 custom_nodes 目录时出错: {e}", "error", target_override="Launcher")
                  self.app.root.after(0, lambda: self._populate_nodes_treeview([{"name":"扫描失败", "status":"错误", "local_id":"N/A", "repo_info":"扫描本地目录时出错", "repo_url":"N/A"}]))

        else:
             self.app.log_to_gui("Management", f"ComfyUI custom_nodes 目录无效，跳过本地扫描。", "warn")

        if self.app.stop_event_set():
             self.app.log_to_gui("Management", "节点列表刷新任务已取消 (停止信号)。", "warn")
             return

        online_nodes_config = []
        if node_config_url:
            online_nodes_config = self._fetch_online_node_config()
        else:
            self.app.log_to_gui("Management", "节点配置地址未设置，跳过在线配置获取。", "warn")

        if self.app.stop_event_set():
             self.app.log_to_gui("Management", "节点列表刷新任务已取消 (停止信号)。", "warn")
             return

        local_node_dict_lower = {node['name'].lower(): node for node in local_nodes}
        combined_nodes_dict = {node['name'].lower(): node for node in local_nodes}

        for online_node in online_nodes_config:
             if self.app.stop_event_set():
                 break
             try:
                 node_name = online_node.get('title') or online_node.get('name')
                 if not node_name:
                     continue
                 node_name_lower = node_name.lower()
                 repo_url = None
                 files = online_node.get('files', [])
                 if isinstance(files, list):
                      for file_entry in files:
                           if isinstance(file_entry, str) and file_entry.strip().endswith(".git"):
                                repo_url = file_entry.strip()
                                break
                 if not repo_url:
                     continue

                 target_ref = online_node.get('reference') or online_node.get('branch') or 'main'

                 if node_name_lower not in local_node_dict_lower:
                     online_repo_info_display = f"在线目标: {target_ref}"
                     combined_nodes_dict[node_name_lower] = {
                         "name": node_name, "status": "未安装", "local_id": "N/A", "local_commit_full": None,
                         "repo_info": online_repo_info_display, "repo_url": repo_url,
                         "is_git": True,
                         "remote_branch": target_ref
                     }
             except Exception as e:
                 self.app.log_to_gui("Management", f"处理在线节点条目时出错: {e}", "warn")


        self.local_nodes_only = sorted(local_nodes, key=lambda x: x.get('name', '').lower())
        self.all_known_nodes = sorted(list(combined_nodes_dict.values()), key=lambda x: x.get('name', '').lower())

        if self.app.stop_event_set():
             self.app.log_to_gui("Management", "节点列表刷新任务已取消 (停止信号)。", "warn")
             return

        filtered_nodes = []
        search_term_value = ""
        try:
            if hasattr(self, 'nodes_search_entry') and self.nodes_search_entry.winfo_exists():
                search_term_value = self.nodes_search_entry.get().strip().lower()
        except tk.TclError:
            pass

        if search_term_value == "":
            filtered_nodes = sorted(self.local_nodes_only, key=lambda x: x.get('name', '').lower())
        else:
            filtered_nodes = [
                node for node in self.all_known_nodes
                if search_term_value in node.get('name', '').lower() or \
                   search_term_value in node.get('repo_url', '').lower() or \
                   search_term_value in node.get('status', '').lower()
            ]
            filtered_nodes.sort(key=lambda x: x.get('name', '').lower())

        self._save_state()

        self.app.root.after(0, lambda list_to_populate=filtered_nodes: self._populate_nodes_treeview(list_to_populate))

        self.app.log_to_gui("Management", f"节点列表刷新完成。已显示 {len(filtered_nodes)} 个节点。", "info")


    def _fetch_online_node_config(self):
         """Fetches and parses the online custom node list config. Runs in worker thread."""
         node_config_url = self.app.node_config_url_var.get()
         if not node_config_url:
             return []

         self.app.log_to_gui("Management", f"尝试从 {node_config_url} 获取节点配置...", "info")
         try:
              response = requests.get(node_config_url, timeout=20)
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
        if self.app.stop_event_set():
            self.app.log_to_gui("Management", f"节点 '{node_name}' 安装任务已取消 (停止信号)。", "warn")
            return
        self.app.log_to_gui("Management", f"开始安装节点 '{node_name}'...", "info")
        self.app.log_to_gui("Management", f"  仓库: {repo_url}", "info")
        self.app.log_to_gui("Management", f"  目标引用: {target_ref}", "info")
        self.app.log_to_gui("Management", f"  目标目录: {node_install_path}", "info")

        try:
            comfyui_nodes_dir = self.app.comfyui_nodes_dir
            if not comfyui_nodes_dir:
                 raise Exception("ComfyUI custom_nodes 目录未设置或无效。")

            if not os.path.exists(comfyui_nodes_dir):
                 self.app.log_to_gui("Management", f"创建 custom_nodes 目录: {comfyui_nodes_dir}", "info")
                 os.makedirs(comfyui_nodes_dir, exist_ok=True)

            if os.path.exists(node_install_path):
                 if os.path.isdir(node_install_path) and len(os.listdir(node_install_path)) > 0:
                      raise Exception(f"节点安装目录已存在且不为空: {node_install_path}")
                 elif not os.path.isdir(node_install_path):
                      raise Exception(f"目标路径已存在但不是目录: {node_install_path}")
                 else:
                      try:
                           self.app.log_to_gui("Management", f"移除已存在的空目录: {node_install_path}", "info")
                           os.rmdir(node_install_path)
                      except OSError as e:
                           raise Exception(f"无法移除已存在的空目录 {node_install_path}: {e}")

            if self.app.stop_event_set():
                raise threading.ThreadExit

            self.app.log_to_gui("Management", f"执行 Git clone {repo_url} {node_install_path}...", "info")
            clone_cmd = ["clone", "--progress"]
            is_likely_commit_hash = len(target_ref) >= 7 and all(c in '0123456789abcdefABCDEF' for c in target_ref.lower())

            if target_ref and not is_likely_commit_hash:
                 clone_cmd.extend(["--branch", target_ref])

            clone_cmd.extend([repo_url, node_install_path])

            stdout_clone, stderr_clone, returncode = self.app._run_git_command(clone_cmd, cwd=comfyui_nodes_dir, timeout=300, log_output=True)

            if returncode != 0:
                 if os.path.exists(node_install_path):
                      try:
                           self.app.log_to_gui("Management", f"Git clone 失败，尝试移除失败目录: {node_install_path}", "warn")
                           shutil.rmtree(node_install_path)
                           self.app.log_to_gui("Management", f"已移除失败的节点目录: {node_install_path}", "info")
                      except Exception as rm_err:
                           self.app.log_to_gui("Management", f"移除失败的节点目录 '{node_install_path}' 失败: {rm_err}", "error")
                 raise Exception(f"Git clone 失败 (退出码 {returncode})")

            self.app.log_to_gui("Management", "Git clone 完成。", "info")

            if target_ref:
                 self.app.log_to_gui("Management", f"尝试执行 Git checkout {target_ref}...", "info")
                 _, stderr_checkout, rc_checkout = self.app._run_git_command(["checkout", "--force", target_ref], cwd=node_install_path, timeout=60)
                 if rc_checkout != 0:
                      self.app.log_to_gui("Management", f"Git checkout {target_ref[:8]} 失败: {stderr_checkout.strip()}", "warn")
                      self.app.root.after(0, lambda name=node_name, ref=target_ref[:8]: messagebox.showwarning("版本切换警告", f"节点 '{name}' 安装后尝试切换到版本 {ref} 失败。\n请查看日志。", parent=self.app.root))
                 else:
                      self.app.log_to_gui("Management", f"Git checkout {target_ref[:8]} 完成。", "info")


            if self.app.stop_event_set():
                raise threading.ThreadExit

            if os.path.exists(os.path.join(node_install_path, ".gitmodules")):
                 self.app.log_to_gui("Management", f"执行 Git submodule update for '{node_name}'...", "info")
                 _, stderr_sub, rc_sub = self.app._run_git_command(["submodule", "update", "--init", "--recursive", "--force"], cwd=node_install_path, timeout=180)
                 if rc_sub != 0:
                     self.app.log_to_gui("Management", f"Git submodule update 失败: {stderr_sub.strip()}", "warn")

            if self.app.stop_event_set():
                raise threading.ThreadExit

            python_exe = self.app.python_exe_var.get()
            requirements_path = os.path.join(node_install_path, "requirements.txt")
            if python_exe and os.path.isfile(python_exe) and os.path.isfile(requirements_path):
                 self.app.log_to_gui("Management", f"执行 pip 安装节点依赖 for '{node_name}'...", "info")
                 pip_cmd_base = [python_exe, "-m", "pip", "install", "-r", requirements_path, "--upgrade"]
                 pip_cmd_extras = ["--extra-index-url", "https://download.pytorch.org/whl/cu118", "--extra-index-url", "https://download.pytorch.org/whl/cu121"]
                 pip_cmd = pip_cmd_base + pip_cmd_extras
                 is_venv = sys.prefix != sys.base_prefix
                 if platform.system() != "Windows" and not is_venv:
                       try:
                            relative_path = os.path.relpath(python_exe, sys.base_prefix)
                            if relative_path.startswith('..') or os.path.isabs(relative_path):
                                 if sys.base_prefix == sys.prefix:
                                      pip_cmd.append("--user")
                                      self.app.log_to_gui("Management", "无法确定节点依赖Python环境，假定非虚拟环境并使用 --user。", "warn")
                       except ValueError:
                            if sys.base_prefix == sys.prefix:
                                 pip_cmd.append("--user")
                                 self.app.log_to_gui("Management", "无法确定节点依赖Python环境，假定非虚拟环境并使用 --user。", "warn")

                 pip_cmd.extend(["--no-cache-dir"])

                 _, stderr_pip, rc_pip = self.app._run_git_command(pip_cmd, cwd=node_install_path, timeout=180)
                 if rc_pip != 0:
                      self.app.log_to_gui("Management", f"Pip 安装节点依赖失败: {stderr_pip.strip()}", "error")
                      self.app.root.after(0, lambda name=node_name: messagebox.showwarning("依赖安装失败", f"节点 '{name}' 的 Python 依赖可能安装失败。\n请查看日志。", parent=self.app.root))
                 else:
                      self.app.log_to_gui("Management", f"Pip 安装节点依赖完成 for '{node_name}'.", "info")

            self.app.log_to_gui("Management", f"节点 '{node_name}' 安装流程完成。", "info")
            self.app.root.after(0, lambda name=node_name: messagebox.showinfo("安装完成", f"节点 '{name}' 已成功安装。", parent=self.app.root))

        except threading.ThreadExit:
             self.app.log_to_gui("Management", f"节点 '{node_name}' 安装任务已取消。", "warn")
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
            self.app.root.after(0, lambda msg=error_msg: messagebox.showerror("安装失败", msg, parent=self.app.root))
        finally:
            self.app._queue_node_list_refresh()


    # Called by app._queue_node_uninstall
    def _node_uninstall_task(self, node_name, node_install_path):
         """Task to uninstall a node by deleting its directory. Runs in worker thread."""
         if self.app.stop_event_set():
             self.app.log_to_gui("Management", f"节点 '{node_name}' 卸载任务已取消 (停止信号)。", "warn")
             return
         self.app.log_to_gui("Management", f"正在卸载节点 '{node_name}' (删除目录: {node_install_path})...", "info")

         try:
              if not os.path.isdir(node_install_path):
                   self.app.log_to_gui("Management", f"节点目录 '{node_install_path}' 不存在，无需卸载。", "warn")
                   self.app.root.after(0, lambda name=node_name: messagebox.showwarning("卸载失败", f"节点目录 '{name}' 不存在。", parent=self.app.root))
                   return

              if self.app.stop_event_set():
                  raise threading.ThreadExit

              self.app.log_to_gui("Management", f"删除目录: {node_install_path}", "cmd")
              shutil.rmtree(node_install_path)
              self.app.log_to_gui("Management", f"节点目录 '{node_install_path}' 已删除。", "info")
              self.app.log_to_gui("Management", f"节点 '{node_name}' 卸载流程完成。", "info")
              self.app.root.after(0, lambda name=node_name: messagebox.showinfo("卸载完成", f"节点 '{name}' 已成功卸载。", parent=self.app.root))

         except threading.ThreadExit:
              self.app.log_to_gui("Management", f"节点 '{node_name}' 卸载任务已取消。", "warn")
         except Exception as e:
             error_msg = f"节点 '{node_name}' 卸载失败: {e}"
             self.app.log_to_gui("Management", error_msg, "error")
             self.app.root.after(0, lambda msg=error_msg: messagebox.showerror("卸载失败", msg, parent=self.app.root))
         finally:
             self.app._queue_node_list_refresh()


    # Called by app._queue_all_nodes_update
    def _update_all_nodes_task(self, nodes_to_process):
        """Task to iterate and update all specified installed nodes. Runs in worker thread."""
        if self.app.stop_event_set():
            self.app.log_to_gui("Management", "更新全部节点任务已取消 (停止信号)。", "warn")
            return
        self.app.log_to_gui("Management", f"开始更新全部节点 ({len(nodes_to_process)} 个)...", "info")
        updated_count = 0
        failed_nodes = []

        for index, node_info in enumerate(nodes_to_process):
             if self.app.stop_event_set():
                 break

             node_name = node_info.get("name", "未知节点")
             node_install_path = os.path.normpath(os.path.join(self.app.comfyui_nodes_dir, node_name))
             repo_url = node_info.get("repo_url")
             remote_branch = node_info.get("remote_branch")

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
                 stdout_get_url, _, rc_get_url = self.app._run_git_command(["remote", "get-url", "origin"], cwd=node_install_path, timeout=10, log_output=False)
                 current_url = stdout_get_url.strip() if rc_get_url == 0 else None
                 if not current_url:
                      self.app.log_to_gui("Management", f"节点 '{node_name}': 远程 'origin' 不存在，尝试添加...", "info")
                      _, stderr_add, rc_add = self.app._run_git_command(["remote", "add", "origin", repo_url], cwd=node_install_path, timeout=15)
                      if rc_add != 0:
                          self.app.log_to_gui("Management", f"节点 '{node_name}': 添加远程 'origin' 失败: {stderr_add.strip()}", "warn")
                 elif current_url != repo_url:
                      self.app.log_to_gui("Management", f"节点 '{node_name}': 远程 'origin' URL 不匹配 ({current_url}), 尝试设置新 URL...", "warn")
                      _, stderr_set, rc_set = self.app._run_git_command(["remote", "set-url", "origin", repo_url], cwd=node_install_path, timeout=15)
                      if rc_set != 0:
                          self.app.log_to_gui("Management", f"节点 '{node_name}': 设置远程 'origin' URL 失败: {stderr_set.strip()}", "warn")
                      else:
                          self.app.log_to_gui("Management", f"节点 '{node_name}': 远程 URL 已更新。", "info")


                 if self.app.stop_event_set():
                     raise threading.ThreadExit

                 stdout_status, _, _ = self.app._run_git_command(["status", "--porcelain"], cwd=node_install_path, timeout=10, log_output=False)
                 if stdout_status.strip():
                      self.app.log_to_gui("Management", f"跳过 '{node_name}': 存在未提交的本地修改。", "warn")
                      failed_nodes.append(f"{node_name} (存在本地修改)")
                      continue

                 self.app.log_to_gui("Management", f"[{index+1}/{len(nodes_to_process)}] 执行 Git fetch origin {remote_branch}...", "info")
                 _, stderr_fetch, rc_fetch = self.app._run_git_command(["fetch", "origin", remote_branch], cwd=node_install_path, timeout=60)
                 if rc_fetch != 0:
                      self.app.log_to_gui("Management", f"Git fetch 失败 for '{node_name}': {stderr_fetch.strip()}", "error")
                      failed_nodes.append(f"{node_name} (Fetch失败)")
                      continue

                 if self.app.stop_event_set():
                     raise threading.ThreadExit

                 local_commit_full, _, _ = self.app._run_git_command(["rev-parse", "HEAD"], cwd=node_install_path, timeout=5, log_output=False)
                 remote_commit_full, _, _ = self.app._run_git_command(["rev-parse", f"origin/{remote_branch}"], cwd=node_install_path, timeout=5, log_output=False)

                 if local_commit_full and remote_commit_full and local_commit_full.strip() == remote_commit_full.strip():
                     self.app.log_to_gui("Management", f"节点 '{node_name}' 已是最新版本。", "info")
                     continue

                 self.app.log_to_gui("Management", f"[{index+1}/{len(nodes_to_process)}] 执行 Git checkout --force origin/{remote_branch} for '{node_name}'...", "info")
                 _, stderr_checkout, returncode_checkout = self.app._run_git_command(["checkout", "--force", f"origin/{remote_branch}"], cwd=node_install_path, timeout=60)
                 if returncode_checkout != 0:
                       self.app.log_to_gui("Management", f"Git checkout --force 失败 for '{node_name}': {stderr_checkout.strip()}", "error")
                       failed_nodes.append(f"{node_name} (Checkout失败)")
                       continue
                 self.app.log_to_gui("Management", f"Git checkout 完成 for '{node_name}'.", "info")

                 local_branch_exists_stdout, _, rc_local_branch = self.app._run_git_command(["rev-parse", "--verify", "--quiet", remote_branch], cwd=node_install_path, timeout=5, log_output=False)
                 if rc_local_branch == 0:
                      self.app.log_to_gui("Management", f"节点 '{node_name}': 本地分支 '{remote_branch}' 存在，尝试切换回本地分支...", "info")
                      _, stderr_checkout_local, rc_checkout_local = self.app._run_git_command(["checkout", remote_branch], cwd=node_install_path, timeout=30)
                      if rc_checkout_local != 0:
                           self.app.log_to_gui("Management", f"节点 '{node_name}': 切换回本地分支 '{remote_branch}' 失败: {stderr_checkout_local.strip()}", "warn")
                      else:
                           self.app.log_to_gui("Management", f"节点 '{node_name}': 已切换回本地分支 '{remote_branch}'.", "info")
                 else:
                      self.app.log_to_gui("Management", f"节点 '{node_name}': 未找到本地分支 '{remote_branch}', 保持在 detached HEAD 状态。", "info")


                 if self.app.stop_event_set():
                     raise threading.ThreadExit

                 if os.path.exists(os.path.join(node_install_path, ".gitmodules")):
                      self.app.log_to_gui("Management", f"执行 Git submodule update for '{node_name}'...", "info")
                      _, stderr_sub, rc_sub = self.app._run_git_command(["submodule", "update", "--init", "--recursive", "--force"], cwd=node_install_path, timeout=180)
                      if rc_sub != 0:
                          self.app.log_to_gui("Management", f"Git submodule update 失败: {stderr_sub.strip()}", "warn")
                 python_exe = self.app.python_exe_var.get()
                 requirements_path = os.path.join(node_install_path, "requirements.txt")
                 if python_exe and os.path.isfile(python_exe) and os.path.isfile(requirements_path):
                      self.app.log_to_gui("Management", f"执行 pip 安装节点依赖 for '{node_name}'...", "info")
                      pip_cmd_base = [python_exe, "-m", "pip", "install", "-r", requirements_path, "--upgrade"]
                      pip_cmd_extras = ["--extra-index-url", "https://download.pytorch.org/whl/cu118", "--extra-index-url", "https://download.pytorch.org/whl/cu121"]
                      pip_cmd = pip_cmd_base + pip_cmd_extras
                      is_venv = sys.prefix != sys.base_prefix
                      if platform.system() != "Windows" and not is_venv:
                           try:
                                relative_path = os.path.relpath(python_exe, sys.base_prefix)
                                if relative_path.startswith('..') or os.path.isabs(relative_path):
                                     if sys.base_prefix == sys.prefix:
                                          pip_cmd.append("--user")
                                          self.app.log_to_gui("Management", "无法确定节点依赖Python环境，假定非虚拟环境并使用 --user。", "warn")
                           except ValueError:
                                if sys.base_prefix == sys.prefix:
                                     pip_cmd.append("--user")
                                     self.app.log_to_gui("Management", "无法确定节点依赖Python环境，假定非虚拟环境并使用 --user。", "warn")

                      pip_cmd.extend(["--no-cache-dir"])

                      _, stderr_pip, rc_pip = self.app._run_git_command(pip_cmd, cwd=node_install_path, timeout=180)
                      if rc_pip != 0:
                           self.app.log_to_gui("Management", f"Pip 安装节点依赖失败: {stderr_pip.strip()}", "error")
                           failed_nodes.append(f"{node_name} (依赖安装失败)")
                      else:
                           self.app.log_to_gui("Management", f"Pip 安装节点依赖完成 for '{node_name}'.", "info")

                 updated_count += 1
                 self.app.log_to_gui("Management", f"节点 '{node_name}' 更新成功。", "info")

             except threading.ThreadExit:
                 self.app.log_to_gui("Management", f"更新节点 '{node_name}' 时收到停止信号。", "warn")
                 failed_nodes.append(f"{node_name} (已取消)")
                 break
             except Exception as e:
                 self.app.log_to_gui(f"Management", f"更新节点 '{node_name}' 时发生意外错误: {e}", "error")
                 failed_nodes.append(f"{node_name} (发生错误)")

        self.app.log_to_gui("Management", f"更新全部节点流程完成。", "info")
        final_message = f"全部节点更新流程完成。\n成功更新: {updated_count} 个。"
        if failed_nodes:
             final_message += f"\n\n失败/跳过节点 ({len(failed_nodes)} 个):\n- " + "\n- ".join(failed_nodes)
             self.app.root.after(0, lambda msg=final_message: messagebox.showwarning("更新全部完成 (有失败/跳过)", msg, parent=self.app.root))
        else:
             self.app.root.after(0, lambda msg=final_message: messagebox.showinfo("更新全部完成", msg, parent=self.app.root))

        self.app._queue_node_list_refresh()


    # Called by app._queue_node_switch_or_show_history (for history scenario)
    def _node_history_fetch_task(self, node_name, node_install_path):
         """Task to fetch git history and current commit for a node. Runs in worker thread."""
         if self.app.stop_event_set():
             self.app.log_to_gui("Management", f"节点 '{node_name}' 版本历史获取任务已取消 (停止信号)。", "warn")
             self.app.root.after(0, self._cleanup_modal_state)
             return

         self.app.log_to_gui("Management", f"正在获取节点 '{node_name}' 的版本历史...", "info")

         history_data = []
         current_local_commit = None
         try:
             if not os.path.isdir(node_install_path) or not os.path.exists(os.path.join(node_install_path, ".git")):
                  raise Exception(f"节点目录不是有效的 Git 仓库: {node_install_path}")

             local_commit_stdout, _, rc_local = self.app._run_git_command(["rev-parse", "HEAD"], cwd=node_install_path, timeout=5, log_output=False)
             if rc_local == 0 and local_commit_stdout:
                 current_local_commit = local_commit_stdout.strip()
                 self.app.log_to_gui("Management", f"当前本地 Commit ID: {current_local_commit[:8]}", "info")
             else:
                 self.app.log_to_gui("Management", f"无法获取节点 '{node_name}' 的当前 Commit ID。", "warn")


             found_node_info = next((node for node in self.local_nodes_only if node.get("name") == node_name), None)
             repo_url = found_node_info.get("repo_url") if found_node_info else None

             if not repo_url or repo_url in ("本地安装，无Git信息", "无法获取远程 URL", "本地安装", "N/A", "无远程仓库"):
                 stdout_config_url, _, rc_config_url = self.app._run_git_command(["config", "--get", "remote.origin.url"], cwd=node_install_path, timeout=5, log_output=False)
                 if rc_config_url == 0 and stdout_config_url and stdout_config_url.strip().endswith(".git"):
                      repo_url = stdout_config_url.strip()
                      self.app.log_to_gui("Management", f"从本地 Git config 获取到远程 URL: {repo_url}", "info")
                 else:
                      self.app.log_to_gui("Management", f"节点 '{node_name}': 无法获取有效的远程 URL，历史列表可能不完整。", "warn")


             if repo_url and repo_url not in ("本地安装", "N/A"):
                 stdout_get_url, _, rc_get_url = self.app._run_git_command(["remote", "get-url", "origin"], cwd=node_install_path, timeout=10, log_output=False)
                 current_origin_url = stdout_get_url.strip() if rc_get_url == 0 else ""

                 if not current_origin_url:
                      self.app.log_to_gui("Management", f"节点 '{node_name}': 远程 'origin' 不存在，尝试添加 URL '{repo_url}'...", "info")
                      _, stderr_add, rc_add = self.app._run_git_command(["remote", "add", "origin", repo_url], cwd=node_install_path, timeout=10)
                      if rc_add != 0:
                          self.app.log_to_gui("Management", f"节点 '{node_name}': 添加远程 'origin' 失败: {stderr_add.strip()}", "warn")
                 elif current_origin_url != repo_url:
                     self.app.log_to_gui("Management", f"节点 '{node_name}': 远程 'origin' URL 不匹配 ({current_origin_url}), 尝试设置新 URL '{repo_url}'...", "warn")
                     _, stderr_set, rc_set = self.app._run_git_command(["remote", "set-url", "origin", repo_url], cwd=node_install_path, timeout=10)
                     if rc_set != 0:
                         self.app.log_to_gui("Management", f"节点 '{node_name}': 设置远程 URL 失败: {stderr_set.strip()}", "warn")
                     else:
                         self.app.log_to_gui("Management", f"节点 '{node_name}': 远程 URL 已更新。", "info")

                 if self.app.stop_event_set():
                     raise threading.ThreadExit
                 self.app.log_to_gui("Management", f"执行 Git fetch origin --prune --tags -f for '{node_name}'...", "info")
                 _, stderr_fetch, rc_fetch = self.app._run_git_command(["fetch", "origin", "--prune", "--tags", "-f"], cwd=node_install_path, timeout=90)
                 if rc_fetch != 0:
                      self.app.log_to_gui("Management", f"Git fetch 失败 for '{node_name}': {stderr_fetch.strip()}", "error")
                      self.app.log_to_gui("Management", "无法从远程获取最新历史，列表可能不完整。", "warn")
             else:
                  self.app.log_to_gui("Management", f"节点 '{node_name}': 无有效远程 URL，仅显示本地历史。", "warn")


             if self.app.stop_event_set():
                 raise threading.ThreadExit

             log_cmd = ["for-each-ref", "refs/", "--sort=-committerdate", "--format=%(refname) %(objectname) %(committerdate:iso-strict) %(contents:subject)"]
             history_output, _, rc_history = self.app._run_git_command(log_cmd, cwd=node_install_path, timeout=60)

             if rc_history != 0:
                  self.app.log_to_gui("Management", f"获取 Git 历史失败: {history_output.strip()}", "error")
                  self.app.log_to_gui("Management", "无法获取节点历史。", "error")
             else:
                  processed_commits = set()
                  for line in history_output.splitlines():
                       parts = line.split(' ', 3)
                       if len(parts) >= 3:
                           refname, commit_id, date_iso = parts[0], parts[1], parts[2]
                           description = parts[3].strip() if len(parts) == 4 else ""

                           if commit_id in processed_commits:
                                continue

                           ref_type = "commit"
                           display_name = commit_id[:8]

                           if refname == "HEAD":
                                head_sym_ref_out, _, _ = self.app._run_git_command(["symbolic-ref", "-q", "--short", "HEAD"], cwd=node_install_path, timeout=2, log_output=False)
                                if head_sym_ref_out:
                                    ref_type = "branch (HEAD)"
                                    display_name = head_sym_ref_out.strip()
                                else:
                                    ref_type = "commit (HEAD)"

                                description = f"HEAD - {description}"
                           elif refname.startswith("refs/heads/"):
                                ref_type = "branch"
                                display_name = refname.replace("refs/heads/", "")
                           elif refname.startswith("refs/remotes/origin/"):
                                ref_type = "branch (remote)"
                                display_name = refname.replace("refs/remotes/origin/", "")
                                if "HEAD" in display_name:
                                     continue
                           elif refname.startswith("refs/tags/"):
                                ref_type = "tag"
                                display_name = refname.replace("refs/tags/", "")
                                description = f"TAG - {description}"

                           history_data.append({"type": ref_type, "name": display_name, "commit_id": commit_id, "date_iso": date_iso, "description": description})
                           processed_commits.add(commit_id)

             history_data.sort(key=cmp_to_key(self.app._compare_versions_for_sort))

             if current_local_commit and current_local_commit not in processed_commits:
                  self.app.log_to_gui("Management", "获取当前本地 Commit 信息...", "info")
                  head_date_stdout, _, rc_head_date = self.app._run_git_command(["log", "-1", "--format=%ci", "HEAD"], cwd=node_install_path, timeout=5, log_output=False)
                  head_subject_stdout, _, rc_head_subject = self.app._run_git_command(["log", "-1", "--format=%s", "HEAD"], cwd=node_install_path, timeout=5, log_output=False)
                  head_date_iso = head_date_stdout.strip() if rc_head_date == 0 else None
                  head_description = head_subject_stdout.strip() if rc_head_subject == 0 else "当前工作目录"
                  date_obj = self.app._parse_iso_date_for_sort(head_date_iso)
                  final_date_iso = date_obj.isoformat() if date_obj else datetime.now(timezone.utc).isoformat()

                  head_sym_ref_out, _, rc_head_sym_ref = self.app._run_git_command(["symbolic-ref", "-q", "--short", "HEAD"], cwd=node_install_path, timeout=2, log_output=False)
                  head_type = "commit (HEAD)" if rc_head_sym_ref != 0 else "branch (local)"
                  head_name = head_sym_ref_out.strip() if head_type == "branch (local)" else f"Detached at {current_local_commit[:8]}"

                  history_data.append({"type": head_type, "name": head_name, "commit_id": current_local_commit, "date_iso": final_date_iso, "description": head_description})
                  self.app.log_to_gui("Management", f"添加当前本地 HEAD ({current_local_commit[:8]}) 到列表。", "info")

                  history_data.sort(key=cmp_to_key(self.app._compare_versions_for_sort))


             self._node_history_modal_versions_data = history_data
             self._node_history_modal_node_name = node_name
             self._node_history_modal_node_path = node_install_path
             self._node_history_modal_current_commit = current_local_commit

             self.app.log_to_gui("Management", f"节点 '{node_name}' 版本历史获取完成。找到 {len(history_data)} 条记录。", "info")
             self.app.root.after(0, self._show_node_history_modal)

         except threading.ThreadExit:
              self.app.log_to_gui("Management", f"节点 '{node_name}' 历史获取任务已取消。", "warn")
              self.app.root.after(0, self._cleanup_modal_state)
         except Exception as e:
             error_msg = f"获取节点 '{node_name}' 版本历史失败: {e}"
             self.app.log_to_gui("Management", error_msg, "error")
             self.app.root.after(0, self._cleanup_modal_state)
             self.app.root.after(0, lambda msg=error_msg: messagebox.showerror("获取历史失败", msg, parent=self.app.root))


    # Called by _node_history_fetch_task
    def _show_node_history_modal(self):
        """Creates and displays the node version history modal with improved styling."""
        if self._node_history_modal_window and self._node_history_modal_window.winfo_exists():
             self.app.log_to_gui("Management", "Attempted to open node history modal, but one is already open.", "warn")
             return

        if not self._node_history_modal_versions_data:
            self.app.log_to_gui("Management", f"没有节点 '{self._node_history_modal_node_name}' 的历史版本数据可显示。", "warn")
            self._cleanup_modal_state()
            return

        node_name = self._node_history_modal_node_name
        history_data = self._node_history_modal_versions_data
        current_commit = self._node_history_modal_current_commit

        modal_window = Toplevel(self.app.root)
        self.app.root.eval(f'tk::PlaceWindow {str(modal_window)} center')
        modal_window.title(f"版本切换 - {node_name}")
        modal_window.transient(self.app.root)
        modal_window.grab_set()
        modal_window.geometry("850x550")
        modal_window.configure(bg=self.app.BG_COLOR)
        modal_window.rowconfigure(0, weight=1); modal_window.columnconfigure(0, weight=1)
        modal_window.protocol("WM_DELETE_WINDOW", lambda win=modal_window: self._cleanup_modal_state(win))
        self._node_history_modal_window = modal_window

        main_modal_frame = ttk.Frame(modal_window, style='Modal.TFrame', padding=10)
        main_modal_frame.grid(row=0, column=0, sticky="nsew")
        main_modal_frame.rowconfigure(1, weight=1); main_modal_frame.columnconfigure(0, weight=1)

        header_frame = ttk.Frame(main_modal_frame, style='TabControl.TFrame', padding=(0, 5, 0, 8))
        header_frame.grid(row=0, column=0, columnspan=2, sticky="ew")
        header_frame.columnconfigure(0, weight=4, minsize=250); header_frame.columnconfigure(1, weight=1, minsize=80); header_frame.columnconfigure(2, weight=1, minsize=100); header_frame.columnconfigure(3, weight=1, minsize=110); header_frame.columnconfigure(4, weight=0, minsize=80)

        ttk.Label(header_frame, text="版本", style='ModalHeader.TLabel', anchor=tk.W).grid(row=0, column=0, sticky='w', padx=5)
        ttk.Label(header_frame, text="状态", style='ModalHeader.TLabel', anchor=tk.CENTER).grid(row=0, column=1, sticky='ew', padx=5)
        ttk.Label(header_frame, text="提交ID", style='ModalHeader.TLabel', anchor=tk.W).grid(row=0, column=2, sticky='w', padx=5)
        ttk.Label(header_frame, text="更新日期", style='ModalHeader.TLabel', anchor=tk.W).grid(row=0, column=3, sticky='w', padx=5)
        ttk.Label(header_frame, text="操作", style='ModalHeader.TLabel', anchor=tk.CENTER).grid(row=0, column=4, sticky='ew', padx=(5,10))

        canvas = tk.Canvas(main_modal_frame, bg=self.app.TEXT_AREA_BG, highlightthickness=1, highlightbackground=self.app.BORDER_COLOR, borderwidth=0)
        scrollbar = ttk.Scrollbar(main_modal_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Modal.TFrame')

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=1, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=1, sticky="ns")
        canvas.bind('<Configure>', lambda e: canvas.itemconfigure(canvas_window, width=e.width))

        scrollable_frame.columnconfigure(0, weight=4, minsize=250); scrollable_frame.columnconfigure(1, weight=1, minsize=80); scrollable_frame.columnconfigure(2, weight=1, minsize=100); scrollable_frame.columnconfigure(3, weight=1, minsize=110); scrollable_frame.columnconfigure(4, weight=0, minsize=80)

        for i, item_data in enumerate(history_data):
             item_data.setdefault('type', '未知'); item_data.setdefault('name', 'N/A'); item_data.setdefault('commit_id', 'N/A'); item_data.setdefault('date_iso', ''); item_data.setdefault('description', 'N/A')

             row_frame_style = f'ModalRow{"Odd" if i % 2 == 0 else "Even"}.TFrame'
             label_style = f'ModalRow{"Odd" if i % 2 == 0 else "Even"}.TLabel'
             highlight_style = f'ModalRow{"Odd" if i % 2 == 0 else "Even"}Highlight.TLabel'

             row_frame = ttk.Frame(scrollable_frame, style=row_frame_style, padding=(0, 3))
             row_frame.grid(row=i, column=0, columnspan=5, sticky="ew", padx=0, pady=0)
             row_frame.columnconfigure(0, weight=4, minsize=250); row_frame.columnconfigure(1, weight=1, minsize=80); row_frame.columnconfigure(2, weight=1, minsize=100); row_frame.columnconfigure(3, weight=1, minsize=110); row_frame.columnconfigure(4, weight=0, minsize=80)

             try:
                 date_str = item_data['date_iso']
                 date_obj = self.app._parse_iso_date_for_sort(date_str)
                 date_display = date_obj.strftime('%Y-%m-%d') if date_obj else ("解析失败" if date_str else "无日期")
             except Exception:
                 date_display = "日期错误"

             commit_id = item_data['commit_id']
             version_name = item_data['name']
             version_type = item_data['type']
             version_display = f"{version_type} / {version_name}"

             status_text = ""
             status_label_actual_style = label_style
             if current_commit and commit_id == current_commit:
                  status_text = "当前"
                  status_label_actual_style = highlight_style

             ttk.Label(row_frame, text=version_display, style=label_style, anchor=tk.W, wraplength=240).grid(row=0, column=0, sticky='w', padx=(5,0), pady=1)
             ttk.Label(row_frame, text=status_text, style=status_label_actual_style, anchor=tk.CENTER).grid(row=0, column=1, sticky='ew', padx=5, pady=1)
             ttk.Label(row_frame, text=commit_id[:8], style=label_style, anchor=tk.W).grid(row=0, column=2, sticky='w', padx=5, pady=1)
             ttk.Label(row_frame, text=date_display, style=label_style, anchor=tk.W).grid(row=0, column=3, sticky='w', padx=5, pady=1)

             switch_btn = ttk.Button(row_frame, text="切换", style="Modal.TButton", width=6,
                                     command=lambda c_id=commit_id, win=modal_window, name=node_name: self._on_modal_switch_confirm(win, name, c_id))
             switch_btn.grid(row=0, column=4, sticky='e', padx=(5, 10), pady=1)

             if status_text == "当前":
                  switch_btn.config(state=tk.DISABLED)

        def _on_mousewheel(event):
             scroll_amount = 0
             if platform.system() == "Windows":
                 scroll_amount = int(-1*(event.delta/120))
             elif platform.system() == "Darwin":
                 scroll_amount = int(-1 * event.delta)
             else:
                 if event.num == 4:
                     scroll_amount = -1
                 elif event.num == 5:
                     scroll_amount = 1
             if canvas and canvas.winfo_exists():
                canvas.yview_scroll(scroll_amount, "units")

        if canvas and canvas.winfo_exists():
            canvas.bind("<MouseWheel>", _on_mousewheel)
            if scrollable_frame and scrollable_frame.winfo_exists():
                 scrollable_frame.bind("<MouseWheel>", _on_mousewheel)


    # Called by modal closing protocol and task cancellations
    def _cleanup_modal_state(self, modal_window=None):
         """Cleans up modal-related instance variables and destroys the window."""
         self.app.log_to_gui("Management", "Cleaning up modal state...", "info")
         self._node_history_modal_versions_data = []
         self._node_history_modal_node_name = ""
         self._node_history_modal_node_path = ""
         self._node_history_modal_current_commit = ""

         window_to_destroy = modal_window if modal_window else self._node_history_modal_window
         if window_to_destroy and self.app.window_to_exists(window_to_destroy):
             try:
                  window_to_destroy.destroy()
                  self.app.log_to_gui("Management", "Modal window destroyed.", "info")
             except tk.TclError:
                 self.app.log_to_gui("Management", "Modal window already destroyed (TclError during destroy).", "info")
                 pass
             except Exception as e:
                 self.app.log_to_gui("Management", f"Error during modal window destruction: {e}", "error")

         self._node_history_modal_window = None
         self.app.log_to_gui("Management", "Modal state variables cleared.", "info")
         self.app._update_ui_state()


    # Called by modal switch button command
    def _on_modal_switch_confirm(self, modal_window, node_name, target_ref):
        """Handles the confirmation and queues the switch task from the modal."""
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

        if self.app._is_comfyui_running() or self.app.comfyui_externally_detected:
             messagebox.showwarning("服务运行中", "请先停止 ComfyUI 后台服务，再进行节点版本切换。", parent=modal_window)
             return

        confirm = messagebox.askyesno(
            "确认切换版本",
            f"确定要将节点 '{modal_node_name}' 切换到版本 (引用: {target_ref[:8]})吗？\n\n警告: 此操作会覆盖节点目录下的本地修改，并可能导致与其他节点不兼容！\n确认前请确保 ComfyUI 已停止运行。",
            parent=modal_window
        )
        if not confirm:
            return

        self.app.log_to_gui("Management", f"将节点 '{modal_node_name}' 切换到版本 {target_ref[:8]} 任务添加到队列...", "info")
        self.app.update_task_queue.put((self._switch_node_to_ref_task, [modal_node_name, modal_node_path, target_ref], {}))

        self._cleanup_modal_state(modal_window)
        self.app._update_ui_state()


    # Called by _on_modal_switch_confirm
    def _switch_node_to_ref_task(self, node_name, node_install_path, target_ref):
         """Task to switch an installed node to a specific git reference. Runs in worker thread."""
         if self.app.stop_event_set():
             self.app.log_to_gui("Management", f"节点 '{node_name}' 切换版本任务已取消 (停止信号)。", "warn")
             return
         self.app.log_to_gui("Management", f"正在将节点 '{node_name}' 切换到版本 (引用: {target_ref[:8]})...", "info")

         try:
             if not os.path.isdir(node_install_path) or not os.path.exists(os.path.join(node_install_path, ".git")):
                  raise Exception(f"节点目录不是有效的 Git 仓库: {node_install_path}")

             stdout_status, _, _ = self.app._run_git_command(["status", "--porcelain"], cwd=node_install_path, timeout=10, log_output=False)
             if stdout_status.strip():
                  self.app.log_to_gui("Management", f"节点 '{node_name}' 存在未提交的本地修改，将通过 checkout --force 覆盖。", "warn")

             if self.app.stop_event_set():
                 raise threading.ThreadExit

             self.app.log_to_gui("Management", f"执行 Git checkout --force {target_ref[:8]}...", "info")
             _, stderr_checkout, rc_checkout = self.app._run_git_command(["checkout", "--force", target_ref], cwd=node_install_path, timeout=60)
             if rc_checkout != 0:
                 raise Exception(f"Git checkout 失败: {stderr_checkout.strip()}")

             self.app.log_to_gui("Management", f"Git checkout 完成 (引用: {target_ref[:8]}).", "info")

             if self.app.stop_event_set():
                 raise threading.ThreadExit

             if os.path.exists(os.path.join(node_install_path, ".gitmodules")):
                 self.app.log_to_gui("Management", f"执行 Git submodule update for '{node_name}'...", "info")
                 _, stderr_sub, rc_sub = self.app._run_git_command(["submodule", "update", "--init", "--recursive", "--force"], cwd=node_install_path, timeout=180)
                 if rc_sub != 0:
                     self.app.log_to_gui("Management", f"Git submodule update 失败: {stderr_sub.strip()}", "warn")

             if self.app.stop_event_set():
                 raise threading.ThreadExit

             python_exe = self.app.python_exe_var.get()
             requirements_path = os.path.join(node_install_path, "requirements.txt")
             if python_exe and os.path.isfile(python_exe) and os.path.isfile(requirements_path):
                  self.app.log_to_gui("Management", f"执行 pip 安装节点依赖 for '{node_name}'...", "info")
                  pip_cmd_base = [python_exe, "-m", "pip", "install", "-r", requirements_path, "--upgrade"]
                  pip_cmd_extras = ["--extra-index-url", "https://download.pytorch.org/whl/cu118", "--extra-index-url", "https://download.pytorch.org/whl/cu121"]
                  pip_cmd = pip_cmd_base + pip_cmd_extras
                  is_venv = sys.prefix != sys.base_prefix
                  if platform.system() != "Windows" and not is_venv:
                       try:
                           relative_path = os.path.relpath(python_exe, sys.base_prefix)
                           if relative_path.startswith('..') or os.path.isabs(relative_path):
                                if sys.base_prefix == sys.prefix:
                                     pip_cmd.append("--user")
                                     self.app.log_to_gui("Management", "无法确定节点依赖Python环境，假定非虚拟环境并使用 --user。", "warn")
                       except ValueError:
                            if sys.base_prefix == sys.prefix:
                                 pip_cmd.append("--user")
                                 self.app.log_to_gui("Management", "无法确定节点依赖Python环境，假定非虚拟环境并使用 --user。", "warn")

                  pip_cmd.extend(["--no-cache-dir"])

                  _, stderr_pip, rc_pip = self.app._run_git_command(pip_cmd, cwd=node_install_path, timeout=180)
                  if rc_pip != 0:
                       self.app.log_to_gui("Management", f"Pip 安装节点依赖失败: {stderr_pip.strip()}", "error")
                       self.app.root.after(0, lambda name=node_name: messagebox.showwarning("依赖安装失败", f"节点 '{name}' 的 Python 依赖可能安装失败。\n请查看日志。", parent=self.app.root))
                  else:
                       self.app.log_to_gui("Management", f"Pip 安装节点依赖完成.", "info")

             self.app.log_to_gui("Management", f"节点 '{node_name}' 已成功切换到版本 (引用: {target_ref[:8]})。", "info")
             self.app.root.after(0, lambda name=node_name, ref=target_ref[:8]: messagebox.showinfo("切换完成", f"节点 '{name}' 已成功切换到版本: {ref}", parent=self.app.root))

         except threading.ThreadExit:
              self.app.log_to_gui("Management", f"节点 '{node_name}' 切换版本任务已取消。", "warn")
         except Exception as e:
             error_msg = f"节点 '{node_name}' 切换版本失败: {e}"
             self.app.log_to_gui("Management", error_msg, "error")
             self.app.root.after(0, lambda msg=error_msg: messagebox.showerror("切换失败", msg, parent=self.app.root))
         finally:
             self.app._queue_node_list_refresh()


    # Helper methods for launcher.py to get state
    def get_selected_main_body_item_data(self):
         """Returns the item data for the currently selected main body version."""
         if self.main_body_tree and self.main_body_tree.winfo_exists():
              selected_item = self.main_body_tree.focus()
              if selected_item:
                   return self.main_body_tree.item(selected_item, 'values')
         return None

    def get_selected_node_item_data(self):
         """Returns the item data for the currently selected node."""
         if self.nodes_tree and self.nodes_tree.winfo_exists():
              selected_item = self.nodes_tree.focus()
              if selected_item:
                   return self.nodes_tree.item(selected_item, 'values')
         return None

    def get_nodes_search_term(self):
         """Returns the current text in the node search entry."""
         if self.nodes_search_entry and self.nodes_search_entry.winfo_exists():
              return self.nodes_search_entry.get().strip()
         return ""

    def is_modal_open(self):
         """Returns True if the node history modal is currently open."""
         # Check for the instance variable and if the window still exists
         return self._node_history_modal_window is not None and self.app.window_to_exists(self._node_history_modal_window)


# Function to be called by launcher.py to setup this tab
def setup_management_tab(parent_frame, app_instance):
    """Entry point for the Management tab module."""
    # Create and return the instance of the ManagementTab class
    return ManagementTab(parent_frame, app_instance)