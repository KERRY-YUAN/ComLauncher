# -*- coding: utf-8 -*-
# File: ui_modules/analysis.py
# Version: Kerry, Ver. 2.6.1 - Analysis Tab Module (Fixed Attribute Errors)

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, font as tkfont
import json
import requests
import traceback
# Note: Styling constants, setup_text_tags are accessed via app_instance

class AnalysisTab:
    """Handles the UI and logic for the Analysis tab."""
    def __init__(self, parent_frame, app_instance):
        """
        Initializes the Analysis tab UI elements.

        Args:
            parent_frame: The ttk.Frame widget that serves as the parent for this tab's content.
            app_instance: The main ComLauncherApp instance to access shared resources.
        """
        self.app = app_instance
        self.frame = parent_frame

        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(3, weight=1)

        self.api_endpoint_entry = None
        self.api_key_entry = None
        self.user_request_text = None
        self.error_analysis_text = None
        self.diagnose_button = None
        self.fix_button = None

        self._setup_ui()


    def _setup_ui(self):
        """Builds the UI elements for the Analysis tab."""
        current_row = 0
        frame_padx = 5
        widget_pady = 3
        widget_padx = 5

        ttk.Label(self.frame, text="API 接口:", anchor=tk.W).grid(row=current_row, column=0, sticky=tk.W, padx=widget_padx, pady=(0, widget_pady))
        self.api_endpoint_entry = ttk.Entry(self.frame, textvariable=self.app.error_api_endpoint_var)
        self.api_endpoint_entry.grid(row=current_row, column=1, sticky="ew", padx=widget_padx, pady=(0, widget_pady))
        current_row += 1

        ttk.Label(self.frame, text="API 密匙:", anchor=tk.W).grid(row=current_row, column=0, sticky=tk.W, padx=widget_padx, pady=widget_pady)
        key_button_frame = ttk.Frame(self.frame, style='Analysis.TFrame')
        key_button_frame.grid(row=current_row, column=1, sticky="ew", padx=widget_padx, pady=widget_pady)
        key_button_frame.columnconfigure(0, weight=1)

        self.api_key_entry = ttk.Entry(key_button_frame, textvariable=self.app.error_api_key_var, show="*")
        self.api_key_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.diagnose_button = ttk.Button(key_button_frame, text="诊断", style="Tab.TButton", command=self.run_diagnosis)
        self.diagnose_button.grid(row=0, column=1, padx=(0, 5))
        self.fix_button = ttk.Button(key_button_frame, text="修复", style="Tab.TButton", command=self.run_fix)
        self.fix_button.grid(row=0, column=2)
        current_row += 1

        ttk.Label(self.frame, text="用户诉求:", anchor=tk.W).grid(row=current_row, column=0, sticky=tk.W, padx=widget_padx, pady=widget_pady)
        user_request_font = tkfont.Font(family=self.app.FONT_FAMILY_UI, size=self.app.FONT_SIZE_NORMAL - 1) # Use self.app
        self.user_request_text = scrolledtext.ScrolledText(self.frame, wrap=tk.WORD, height=6,
                                                           font=user_request_font,
                                                           bg=self.app.TEXT_AREA_BG, fg=self.app.FG_COLOR, relief=tk.FLAT, # Use self.app
                                                           borderwidth=1, bd=1, highlightthickness=1,
                                                           highlightbackground=self.app.BORDER_COLOR, insertbackground="white") # Use self.app
        self.user_request_text.grid(row=current_row, column=1, sticky="ew", padx=widget_padx, pady=(0, widget_pady))
        self.user_request_text.bind("<KeyRelease>", lambda event: self.app._update_ui_state())
        current_row += 1

        self.error_analysis_text = scrolledtext.ScrolledText(self.frame, wrap=tk.WORD, state=tk.DISABLED, font=(self.app.FONT_FAMILY_MONO, self.app.FONT_SIZE_MONO), bg=self.app.TEXT_AREA_BG, fg=self.app.FG_STDOUT, relief=tk.FLAT, borderwidth=1, bd=1, highlightthickness=1, highlightbackground=self.app.BORDER_COLOR, insertbackground="white") # Use self.app
        self.error_analysis_text.grid(row=current_row, column=0, columnspan=2, sticky="nsew", padx=frame_padx, pady=(5, 0))
        self.app.setup_text_tags(self.error_analysis_text)


    # --- Analysis Methods (Executed in Worker Thread via Queue) ---

    def run_diagnosis(self):
        """Captures logs, combines them, and sends them to the configured API for analysis."""
        # Access module state via self.app.modules
        is_modal_open_status = self.app.modules.get('management') and hasattr(self.app.modules['management'], 'is_modal_open') and self.app.modules['management'].is_modal_open()

        if self.app._is_update_task_running() or is_modal_open_status:
             self.app.log_to_gui("Analysis", "任务进行中，无法诊断。", "warn")
             messagebox.showwarning("操作进行中", "更新或维护任务正在进行中，或节点版本历史弹窗已打开。", parent=self.app.root)
             return

        api_endpoint = self.app.error_api_endpoint_var.get().strip()
        api_key = self.app.error_api_key_var.get().strip()

        if not api_endpoint:
             messagebox.showwarning("配置缺失", "请在“API 接口”中配置诊断 API 地址。", parent=self.app.root)
             self.app.log_to_gui("Analysis", "诊断取消: API 接口未配置。", "warn")
             return
        if not api_key:
             messagebox.showwarning("配置缺失", "请在“API 密匙”中配置诊断 API 密钥。", parent=self.app.root)
             self.app.log_to_gui("Analysis", "诊断取消: API 密钥未配置。", "warn")
             return

        launcher_logs, comfyui_logs, user_request = "", "", ""
        try:
            if hasattr(self.app, 'launcher_log_text') and self.app.launcher_log_text and self.app.launcher_log_text.winfo_exists():
                 raw_launcher_logs = self.app.launcher_log_text.get("1.0", tk.END).strip()
                 launcher_logs = "\n".join([
                      line[22:] if line.startswith('[') and len(line) > 21 and line[20:21] == ']' else line
                      for line in raw_launcher_logs.splitlines()
                 ])

            if hasattr(self.app, 'main_output_text') and self.app.main_output_text and self.app.main_output_text.winfo_exists():
                 raw_comfyui_logs = self.app.main_output_text.get("1.0", tk.END).strip()
                 comfyui_logs = "\n".join([
                      line[line.find(']') + 2:] if line.startswith('[ComfyUI') and ']' in line else line
                      for line in raw_comfyui_logs.splitlines()
                 ])

            if hasattr(self, 'user_request_text') and self.user_request_text.winfo_exists():
                 user_request = self.user_request_text.get("1.0", tk.END).strip()

        except tk.TclError as e:
             self.app.log_to_gui("Analysis", f"读取日志或用户诉求时出错: {e}", "error")
             return

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
        gemini_payload = {
             "contents": [{
                 "parts": [{"text": formatted_log_payload}]
             }]
        }

        self.app.log_to_gui("Analysis", f"准备发送日志到诊断 API: {api_endpoint}...", "info")
        try:
            if hasattr(self, 'error_analysis_text') and self.error_analysis_text.winfo_exists():
                 self.error_analysis_text.config(state=tk.NORMAL)
                 self.error_analysis_text.delete('1.0', tk.END)
                 self.error_analysis_text.config(state=tk.DISABLED)
        except tk.TclError:
            pass

        self.app.update_task_queue.put((self._run_diagnosis_task, [api_endpoint, api_key, gemini_payload], {}))


    # Executed in worker thread via run_diagnosis
    def _run_diagnosis_task(self, api_endpoint, api_key, gemini_payload):
        """Task to send logs to the configured API (Gemini) and display the analysis. Runs in worker thread."""
        if self.app.stop_event_set():
             self.app.log_to_gui("Analysis", f"诊断任务已取消 (停止信号)。", "warn")
             return
        self.app.log_to_gui("Analysis", f"--- 开始诊断 ---", "info")
        self.app.log_to_gui("Analysis", f"API 端点 (原始): {api_endpoint}", "info")
        self.app.log_to_gui("Analysis", f"API 密钥: {'已配置' if api_key else '未配置'}", "info")

        analysis_result = "未能获取分析结果。"

        if not api_key:
            self.app.log_to_gui("Analysis", "API 密钥未配置，无法进行诊断。", "error")
            analysis_result = "错误：API 密钥未配置，无法进行诊断。"
            # Display error in GUI thread
            self.app.root.after(0, lambda res=analysis_result: self._display_analysis_result(res))
            self.app.log_to_gui("Analysis", f"--- 诊断结束 (配置错误) ---", "info")
            return

        api_endpoint_corrected = api_endpoint.strip()
        if api_endpoint_corrected.endswith('/'):
             api_endpoint_corrected = api_endpoint_corrected[:-1]

        if "/models/" in api_endpoint_corrected and ":" not in api_endpoint_corrected.split("/")[-1]:
             api_endpoint_corrected = f"{api_endpoint_corrected}:generateContent"
             self.app.log_to_gui("Analysis", f"修正 API 端点为 (附加 :generateContent): {api_endpoint_corrected}", "info")
        elif not api_endpoint_corrected.endswith((":generateContent", ":streamGenerateContent")):
             self.app.log_to_gui("Analysis", f"API 端点格式 '{api_endpoint_corrected}' 无法识别，按原样使用。请确保端点包含 ':generateContent' 或 ':streamGenerateContent'。", "warn")


        params = {'key': api_key}

        try:
            headers = {"Content-Type": "application/json"}
            self.app.log_to_gui("Analysis", f"发送 POST 请求到: {api_endpoint_corrected}", "info")

            response = requests.post(api_endpoint_corrected, headers=headers, params=params, json=gemini_payload, timeout=120)
            self.app.log_to_gui("Analysis", f"API 响应状态码: {response.status_code}", "info")
            response.raise_for_status()

            response_data = response.json()
            try:
                 candidates = response_data.get('candidates', [])
                 if candidates:
                     content = candidates[0].get('content', {})
                     parts = content.get('parts', [])
                     if parts:
                         analysis_result = parts[0].get('text', "API 响应中未找到文本内容。")
                     else:
                         analysis_result = "API 响应 'parts' 为空或缺失。"
                 else:
                     prompt_feedback = response_data.get('promptFeedback', {})
                     block_reason = prompt_feedback.get('blockReason')
                     if block_reason:
                          analysis_result = f"API 请求被阻止: {block_reason}\n详情: {prompt_feedback.get('safetyRatings', 'N/A')}"
                     else:
                          analysis_result = "API 响应 'candidates' 为空或缺失。"

            except (KeyError, IndexError, TypeError) as e:
                 print(f"[Analysis Module ERROR] Could not parse Gemini API response structure: {e}")
                 analysis_result = f"API 响应解析失败。\n错误: {e}\n原始响应: {json.dumps(response_data, indent=2, ensure_ascii=False)}"

            self.app.log_to_gui("Analysis", "成功获取 API 分析结果。", "info")

        except requests.exceptions.Timeout:
             error_msg = "[ErrorAnalysis]API 请求超时。请检查网络或增加超时时间。"
             self.app.log_to_gui("Analysis", error_msg, "error")
             analysis_result = error_msg
        except requests.exceptions.HTTPError as e:
             status_code = e.response.status_code
             error_details = "N/A"
             try:
                 error_json = e.response.json()
                 error_details = error_json.get("error", {}).get("message", e.response.text[:500])
             except json.JSONDecodeError:
                 error_details = e.response.text[:500] if hasattr(e.response, 'text') else "N/A"

             if status_code == 401:
                  error_msg = f"[ErrorAnalysis]API 请求错误 401 (Unauthorized): API 密钥无效或认证失败。\n请检查 API 密钥设置。\n详情: {error_details}"
             elif status_code == 403:
                  error_msg = f"[ErrorAnalysis]API 请求错误 403 (Forbidden): 权限不足或模型不可用。\n请检查 API 密钥权限及模型选择。\n详情: {error_details}"
             elif status_code == 404:
                 error_msg = f"[ErrorAnalysis]API 请求错误 404 (Not Found): 无法找到指定的 API 端点或模型。\n请确认 API 接口地址 ({api_endpoint_corrected}) 和模型名称是否正确。\n详情: {error_details}"
             elif status_code == 400:
                 error_msg = f"[ErrorAnalysis]API 请求错误 400 (Bad Request): 请求格式错误或 API 密钥无效/缺失。\n请检查 API 密钥及请求内容。\n详情: {error_details}"
             elif status_code == 429:
                  error_msg = f"[ErrorAnalysis]API 请求错误 429 (Too Many Requests): 超出配额限制。\n请稍后再试或检查您的 API 配额。\n详情: {error_details}"
             else:
                 error_msg = f"[ErrorAnalysis]API 请求失败 (HTTP {status_code})。\n详情: {error_details}"

             print(f"[Analysis Module ERROR] {error_msg}")
             self.app.log_to_gui("Analysis", error_msg, "error")
             analysis_result = error_msg
        except requests.exceptions.RequestException as e:
             error_msg = f"[ErrorAnalysis]API 请求错误: 网络或连接问题。\n请检查网络连接和 API 端点 ({api_endpoint_corrected})。\n详情: {e}"
             print(f"[Analysis Module ERROR] {error_msg}")
             self.app.log_to_gui("Analysis", error_msg, "error")
             analysis_result = error_msg
        except json.JSONDecodeError as e:
             error_msg = f"[ErrorAnalysis]API 响应错误: 无法解析响应 (非有效 JSON)。\n来自: {api_endpoint_corrected}\n错误: {e}"
             response_text_preview = response.text[:500] if 'response' in locals() and hasattr(response, 'text') else "N/A"
             print(f"[Analysis Module ERROR] {error_msg}. Response Preview: {response_text_preview}")
             self.app.log_to_gui("Analysis", error_msg, "error")
             analysis_result = error_msg
        except Exception as e:
            error_msg = f"[ErrorAnalysis]API 请求错误: 发生意外错误。\n详情: {e}"
            print(f"[Analysis Module ERROR] {error_msg}", exc_info=True)
            self.app.log_to_gui("Analysis", error_msg, "error")
            analysis_result = error_msg
        finally:
             self.app.root.after(0, lambda res=analysis_result: self._display_analysis_result(res))
             self.app.log_to_gui("Analysis", f"--- 诊断结束 ---", "info")


    # Run in GUI thread
    def _display_analysis_result(self, result_text):
         """Inserts the final analysis result into the error_analysis_text widget."""
         if not hasattr(self, 'error_analysis_text') or not self.error_analysis_text.winfo_exists():
              self.app.log_to_gui("Analysis", "Cannot display analysis result, widget not found.", "warn")
              return
         try:
             self.error_analysis_text.config(state=tk.NORMAL)
             self.app.insert_output(self.error_analysis_text, result_text, tag="api_output")
             self.error_analysis_text.config(state=tk.DISABLED)
             self.app._update_ui_state()
         except tk.TclError as e:
             self.app.log_to_gui("Analysis", f"TclError displaying analysis result: {e}", "error")


    # Executed in worker thread via run_fix
    def _run_fix_simulation_task(self, commands_to_simulate):
        """Task to simulate executing a list of commands. Runs in worker thread."""
        if self.app.stop_event_set():
            self.app.log_to_gui("Analysis", "模拟修复任务已取消 (停止信号)。", "warn")
            return
        self.app.log_to_gui("Analysis", "准备模拟执行修复命令...", "info")

        comfyui_nodes_dir_fmt = self.app.comfyui_nodes_dir if self.app.comfyui_nodes_dir else "[custom_nodes 目录未设置]"
        git_exe_fmt = self.app.git_exe_path if self.app.git_exe_path else "[Git路径未设置]"
        python_exe_fmt = self.app.comfyui_portable_python if self.app.comfyui_portable_python else "[Python路径未设置]"
        comfyui_dir_fmt = self.app.comfyui_install_dir if self.app.comfyui_install_dir else "[ComfyUI目录未设置]"

        simulated_cwd = comfyui_dir_fmt

        for index, cmd_template in enumerate(commands_to_simulate):
             if self.app.stop_event_set():
                 break

             cmd_string = cmd_template
             comfyui_nodes_dir_val = self.app.comfyui_nodes_dir if self.app.comfyui_nodes_dir and os.path.isdir(self.app.comfyui_nodes_dir) else "[custom_nodes 目录未设置]"
             git_exe_val = self.app.git_exe_path_var.get() if self.app.git_exe_path_var.get() and os.path.isfile(self.app.git_exe_path_var.get()) else "[Git路径未设置]"
             python_exe_val = self.app.python_exe_var.get() if self.app.python_exe_var.get() and os.path.isfile(self.app.python_exe_var.get()) else "[Python路径未设置]"
             comfyui_dir_val = self.app.comfyui_install_dir if self.app.comfyui_install_dir and os.path.isdir(self.app.comfyui_install_dir) else "[ComfyUI目录未设置]"

             cmd_string = cmd_string.replace("{comfyui_nodes_dir}", comfyui_nodes_dir_val, 1)
             cmd_string = cmd_string.replace("{git_exe}", git_exe_val, 1)
             cmd_string = cmd_string.replace("{python_exe}", python_exe_val, 1)
             cmd_string = cmd_string.replace("{comfyui_dir}", comfyui_dir_val, 1)

             self.app.log_to_gui("Analysis", f"\n[{index+1}/{len(commands_to_simulate)}] 模拟执行 (CWD: {simulated_cwd}):", "cmd")
             self.app.log_to_gui("Analysis", f"$ {cmd_string}", "cmd")

             time.sleep(0.5)
             if self.app.stop_event_set():
                 break

             simulated_output = "(模拟输出)"
             cmd_lower = cmd_string.lower().strip()

             if cmd_lower.startswith("cd "):
                 try:
                     new_dir = cmd_string[3:].strip()
                     new_dir = new_dir.replace("{comfyui_nodes_dir}", comfyui_nodes_dir_val)\
                                      .replace("{comfyui_dir}", comfyui_dir_val)

                     if os.path.isabs(new_dir):
                         simulated_cwd = new_dir
                     elif simulated_cwd.startswith("["):
                          simulated_cwd = f"{simulated_cwd}/{new_dir}"
                     else:
                         simulated_cwd = os.path.normpath(os.path.join(simulated_cwd, new_dir))
                     simulated_output = f"(模拟: 工作目录切换到 {simulated_cwd})"
                 except Exception as e:
                     simulated_output = f"(模拟: 无法解析 cd 路径: {e})"
                 self.app.log_to_gui("Analysis", simulated_output, "info")

             elif "git pull" in cmd_lower:
                  simulated_output = "(模拟输出)\n模拟: 拉取远程更改...\n模拟: Already up to date."
                  self.app.log_to_gui("Analysis", simulated_output, "stdout")
             elif "pip install" in cmd_lower or "python -m pip install" in cmd_lower:
                  simulated_output = "(模拟输出)\n模拟: 检查依赖...\n模拟: Requirement already satisfied."
                  self.app.log_to_gui("Analysis", simulated_output, "stdout")
             elif "git clone" in cmd_lower:
                  simulated_output = "(模拟输出)\n模拟: 克隆仓库...\n模拟: 克隆完成。\n模拟: 尝试执行 Git checkout main..."
                  self.app.log_to_gui("Analysis", simulated_output, "stdout")
             elif "git checkout" in cmd_lower:
                  simulated_output = "(模拟输出)\n模拟: 切换分支/提交...\n模拟: Checkout complete."
                  self.app.log_to_gui("Analysis", simulated_output, "stdout")
             elif "git reset" in cmd_lower:
                  simulated_output = "(模拟输出)\n模拟: 重置仓库状态...\n模拟: Reset complete."
                  self.app.log_to_gui("Analysis", simulated_output, "stdout")
             elif "git submodule update" in cmd_lower:
                  simulated_output = "(模拟输出)\n模拟: 更新子模块..."
                  self.app.log_to_gui("Analysis", simulated_output, "stdout")
             elif cmd_lower.startswith("rm ") or cmd_lower.startswith("del "):
                  simulated_output = "(模拟输出)\n模拟: 删除文件/目录..."
                  self.app.log_to_gui("Analysis", simulated_output, "stdout")
             else:
                  self.app.log_to_gui("Analysis", "(模拟: 命令执行完成)", "stdout")


        if self.app.stop_event_set():
             self.app.log_to_gui("Analysis", "\n--- 模拟修复流程被取消 ---", "warn")
        else:
             self.app.log_to_gui("Analysis", "\n--- 模拟修复流程结束 ---", "info")


    def run_fix(self):
        """(Simulates) executing commands from the error analysis output."""
        is_modal_open_status = self.app.modules.get('management') and hasattr(self.app.modules['management'], 'is_modal_open') and self.app.modules['management'].is_modal_open()
        if self.app._is_update_task_running() or is_modal_open_status:
             self.app.log_to_gui("Analysis", "任务进行中，无法模拟修复。", "warn")
             messagebox.showwarning("操作进行中", "更新或维护任务正在进行中，或节点版本历史弹窗已打开。", parent=self.app.root)
             return

        analysis_output = ""
        try:
            if hasattr(self, 'error_analysis_text') and self.error_analysis_text.winfo_exists():
                 analysis_output = self.error_analysis_text.get("1.0", tk.END).strip()
        except tk.TclError:
            pass

        if not analysis_output:
             messagebox.showwarning("无输出", "错误分析输出为空，无法执行模拟修复。", parent=self.app.root)
             return

        lines = analysis_output.splitlines()
        commands_to_simulate = []
        capture_commands = False
        for line in lines:
            line_clean = line.strip()
            if "建议执行的修复操作" in line_clean or "建议执行的命令" in line_clean:
                 capture_commands = True
                 continue
            elif line_clean.lower().startswith("```"):
                 if capture_commands:
                      capture_commands = False
                 else:
                      capture_commands = True
                 continue

            if capture_commands:
                 if not line_clean:
                     continue
                 potential_cmd = line_clean.lstrip('#').lstrip('$').strip()
                 if potential_cmd and any(potential_cmd.lower().startswith(cmd) for cmd in ["cd ", "git ", "pip ", "{git_exe}", "{python_exe}", "rm ", "del ", "mv ", "move ", "mkdir ", "conda ", "python "]):
                      commands_to_simulate.append(potential_cmd)

        if not commands_to_simulate:
             self.app.log_to_gui("Analysis", "在诊断输出中未检测到建议的修复命令。", "warn")
             messagebox.showinfo("无修复命令", "在诊断输出中未找到建议执行的修复命令。", parent=self.app.root)
             return

        confirm_msg = f"检测到以下 {len(commands_to_simulate)} 条建议修复命令：\n\n" + "\n".join(f"- {cmd}" for cmd in commands_to_simulate) + "\n\n将模拟执行这些命令并在下方显示过程。\n注意：这不会实际修改您的文件系统。\n\n是否开始模拟修复？"
        confirm = messagebox.askyesno("确认模拟修复", confirm_msg, parent=self.app.root)
        if not confirm:
            return

        self.app.log_to_gui("Analysis", "\n--- 开始模拟修复流程 ---", "info")
        self.app.update_task_queue.put((self._run_fix_simulation_task, [commands_to_simulate], {}))


    # Helper method for launcher.py to check if there's content in the analysis output
    def has_analysis_output_content(self):
         """Returns True if the analysis output text widget has content."""
         if hasattr(self, 'error_analysis_text') and self.error_analysis_text and self.error_analysis_text.winfo_exists():
             try:
                 return bool(self.error_analysis_text.get("1.0", "end-1c").strip())
             except tk.TclError:
                 pass
         return False

    # Helper method for launcher.py to check if user request text widget is enabled
    def is_user_request_enabled(self):
         """Returns True if the user request text widget is in the 'normal' state."""
         if hasattr(self, 'user_request_text') and self.user_request_text and self.user_request_text.winfo_exists():
             try:
                 return self.user_request_text.cget('state') == tk.NORMAL
             except tk.TclError:
                 pass
         return False

    # Helper method for launcher.py to set user request text widget state
    def set_user_request_state(self, state):
         """Sets the state of the user request text widget."""
         if hasattr(self, 'user_request_text') and self.user_request_text and self.user_request_text.winfo_exists():
             try:
                 self.user_request_text.config(state=state)
             except tk.TclError:
                 pass


# Function to be called by launcher.py to setup this tab
def setup_analysis_tab(parent_frame, app_instance):
    """Entry point for the Analysis tab module."""
    return AnalysisTab(parent_frame, app_instance)