### ComLauncher Program Description
**ComLauncher**

*   A simplified integrated interface designed to facilitate ComfyUI management, enabling quick access to ComfyUI settings, updates, node management, background log viewing, and online API diagnosis with (simulated) fixes. Interface features reference existing ComfyUI launcher designs (Paying tribute to the open-source community Iron Pot Stew AIGODLIKE and Mr. Qiu Ye aaaki).

#### 1. Folder Structure

```
ComLauncher/
├─ templates/                       # Template files (mainly icon)
│  └─ icon.ico                     # ico file
├─ ui_modules/                        # UI modules directory
│  ├─ settings.py                   # Settings tab UI and logic
│  ├─ management.py                 # Management tab UI and logic
│  ├─ logs.py                       # Logs tab UI and logic
│  ├─ analysis.py                   # Analysis tab UI and logic
│  ├─ launcher_config.json          # Launcher configuration file
│  ├─ ComLauncher.org               # Launcher log file
│  ├─ main_body_versions.json       # Main body version persistence (cached data)
│  └─ nodes_list.json               # Node list persistence (cached data)
├─ ComLauncher.exe                      # Main launcher executable
├─ launcher.py                      # Main launcher script
├─ README.md                        # Project README file
└─ requirements.txt                 # Python dependencies list
```

#### 2. Usage Instructions

1.  **First Launch:** Place the program files in a folder and run `ComLauncher.exe`.
2.  **Configure Basic Settings:** Switch to the "Settings" tab and fill in your ComfyUI installation directory, the path to the Python executable used to run ComfyUI, and the path to the Git executable. These are prerequisites for the program to function and perform management operations. You can also adjust performance options here.
3.  **Run ComfyUI:** Return to the top of the main interface and click the "Run ComfyUI" button. The program will check the configuration and then start the ComfyUI backend service.
4.  **Open ComfyUI Interface:** After ComfyUI has successfully started (confirm on the "Logs" tab), click the "Open" button next to the port number on the "Settings" tab, or manually access `http://127.0.0.1:YOUR_PORT_NUMBER` (default is 8188) in your browser.
5.  **Stop ComfyUI:** Click the "Stop" button on the top control bar.
6.  **Manage Versions and Nodes:** Switch to the "Management" tab. Refresh the main body version list or node list as needed. Select an item from the list and click the corresponding button to activate, install, update, or uninstall. **IMPORTANT: Before performing main body or node update/install/uninstall operations, ComfyUI must be stopped.**
7.  **Diagnose Errors:** If ComfyUI encounters an error during operation, you can view detailed information on the "Logs" tab. Then switch to the "Analysis" tab, configure the AI interface and key (if not already set), and click the "Diagnose" button. The program will send the logs to the AI for analysis, and the results will be displayed in the area below. The AI may provide fix suggestions and commands; you can click "Fix" to **simulate** running these commands. **Note that this is ONLY a simulation and will NOT actually modify files.** You need to manually perform the actual operations based on the simulation results in a terminal.
8.  **Exit Program:** Simply close the window. The program will attempt to stop the ComfyUI service before exiting and save logs and configuration.

#### 3. Interface Overview

After launching, the program interface is concise and intuitive, mainly divided into a top control bar and four main tab areas below.

*   **Top Control Bar:** Displays the program's current status (e.g., Running, Stopped), and buttons to start and stop ComfyUI entirely.
*   **Tab Area:**
    *   **设置 / Settings:** Configure basic settings like ComfyUI path, Python path, Git executable path, etc., as well as various performance optimization options, and includes shortcuts to open common ComfyUI subfolders.
    *   **管理 / Management:** Responsible for managing versions and installations of the ComfyUI main body and custom_nodes.
    *   **日志 / Logs:** Separately displays detailed running logs for ComLauncher and ComfyUI.
    *   **分析 / Analysis:** Used to configure the AI service interface and key. Combines logs with "User Request" input, sends for AI diagnosis, and simulates executing fix suggestions.

#### 4. Detailed Interface

**Interface and Operation Logic (in order):**

1.  **设置 / Settings** All changes in settings are automatically saved to `launcher_config.json` file.
    *   **Layout and Content:**
    *   **Basic Paths and Ports:**
        *   "ComfyUI Installation Directory" input field, "ComfyUI Listen and Shared Port" input field.
        *   "ComfyUI Listen and Shared Port" input field (default 8188), and "Open" button to open this address in a browser.
        *   "Git Executable Path" input field, the program calls this path when Git operations are needed.
    *   **Performance and VRAM Optimization:** Used to configure command-line arguments used when starting ComfyUI.
    *   **Folder Shortcuts Area:** Provides buttons that can quickly open the following folders within the ComfyUI installation directory: `workflows`, `custom_nodes` (Nodes), `models`, `loras`, `input`, `output`.

2.  **管理 / Management**
    *   **Layout:**
    *   **Repository Address Area:**
        *   "Main Repository Address" input field, "Node Configuration Address" input field.
    *   **Node Management Area:**
        *   **本体 / Main Body Tab:**
            *   Displays the historical version list of the ComfyUI main body obtained from the "Main Repository Address".
            *   After selecting a version from the list, clicking the "Activate Selected Version" button downloads and overwrites the installation with the chosen ComfyUI main body version.
        *   **节点 / Nodes Tab:**
            *   Contains a search box, "Search" button, "Refresh List" button, "Switch Version" button, "Uninstall Node" button, "Update All" button.
            *   The default list displays all installed nodes within the current `ComfyUI Installation Directory\custom_nodes`. The list includes node name, status, local ID, repository info, and repository URL.
            *   "Switch Version" button: Clicking it opens a separate window displaying the node's historical version list. The "Version Switch" window contains version, commit ID, update date, and a corresponding "Switch" button.
            *   "Update All" button: Clicking it updates the current local nodes based on their tracked remote branch.
            *   "Refresh List" button: Used to refresh the displayed node list.
            *   After entering text in the search box and clicking the "Search" button, the list will display installed and uninstalled nodes that match the search criteria and the "Node Configuration Address".
            *   Time-consuming Git operations like reading node Git repository addresses and fetching repository ID/update dates should be executed in separate threads, so as not to block the main interface and ComfyUI startup.

3.  **日志 / Logs**
    *   Includes two sub-tabs: "ComLauncher Logs" and "ComfyUI Logs".
        *   **ComLauncher Logs Tab:** Independently displays all running logs of the ComLauncher program.
        *   **ComfyUI Logs Tab:** Independently displays all running logs of the ComfyUI process.

4.  **分析 / Analysis**
    *   **Layout:**
    *   **Top Area:**
        *   "API Endpoint" input field, "API Key" input field, used to configure the access address and key for the AI diagnosis service.
        *   "Diagnose" button: Clicking it triggers the log sending and analysis task.
        *   "Fix" button: Clicking it simulates executing the suggested fix commands from the analysis result.
        *   "User Request" text box: Used to input the specific problem description you encountered, assisting the AI's understanding.
    *   **Bottom Area:** CMD code display box, used to display diagnosis results and the simulated fix process.
    *   **Function Logic:**
        *   After clicking the "Diagnose" button (requires "API Endpoint" and "API Key" to be filled):
            *   Merge the contents of "ComLauncher Logs", "ComfyUI Logs", and "User Request" according to the specified format (see reference below).
            *   Connect via the configured API endpoint to send the merged logs to an external AI service (e.g., send to Gemini 2.5 API and receive feedback).
            *   After receiving the AI service response, extract and display the returned analysis results and fix suggestions.
        *   After clicking the "Fix" button:
            *   Parse the fix suggestions from the CMD code display box and **simulate** displaying the specific operations. This will not actually execute any system commands or modify files. (You can perform manual operations based on the simulated suggestions).
    *   **Log Merging Format Reference:**

        ```
        @@@@@@@@@Setting:
        You are a rigorous and efficient AI code engineer and web designer, focused on providing users with accurate and executable frontend and backend code solutions, and proficient in ComfyUI integration. Your replies always prioritize Chinese.@@Core Capabilities:@@ComfyUI Integration: Proficient in ComfyUI's API (/prompt, /upload/image, /ws, etc.) calls and data formats, capable of designing and implementing frontend integration solutions with ComfyUI workflows (e.g., parameter injection, result retrieval). When ComfyUI encounters errors, you can provide solutions. If either "ComLauncher Logs" or "ComfyUI Logs" is empty, skip the analysis of the empty log and only analyze the content of the other part.
        The following are user requests and running logs:
        @@@@@@@@@User Request:
        (Detailed user request input)

        @@@@@@@@@ComLauncher Background Logs
        (Detailed log content)

        @@@@@@@@@ComfyUI Logs
        (Detailed log content)
        ```



### ComLauncher 程序说明
    **ComLauncher**
    *   **一个便于管理ComfyUI的简化集成界面，用于快捷管理 ComfyUI 的设置、更新、节点管理、后台日志查看以及API联网诊断与（模拟）修复。界面功能借鉴了现有 ComfyUI 启动器设计（向铁锅炖AIGODLIKE开源社区、秋叶aaaki大佬致敬）。

#### 1. 文件夹架构
	
```
ComLauncher/
├─ templates/                       # 模板文件（主要是 HTML 模板）
│  └─ icon.ico                     # ico 文件
├─ ui_modules/                        # 界面目录
│  ├─ settings.py                   # 设置标签页UI与逻辑
│  ├─ management.py                 # 管理标签页UI与逻辑
│  ├─ logs.py                       # 日志标签页UI与逻辑
│  ├─ analysis.py                   # 分析标签页UI与逻辑
│  ├─ launcher_config.json          # 启动器配置文件
│  ├─ ComLauncher.org               # 启动器日志文件
│  ├─ main_body_versions.json       # 本体版本持久化
│  └─ nodes_list.json               # 节点列表持久化
├─ ComLauncher.exe                      # 主启动器程序
├─ launcher.py                      # 主启动器脚本
├─ README.md                        # 项目说明文件
└─ requirements.txt                 # 依赖项清单
```

#### 2. 使用说明

1.  **首次启动:** 将程序文件放到一个文件夹里，运行 `ComLauncher.exe`。
2.  **配置基础设置:** 切换到“设置”选项卡，填写你的 ComfyUI 安装目录、用于运行 ComfyUI 的 Python 程序路径、以及 Git 程序路径。这些是程序正常运行和进行管理操作的前提。你也可以在这里调整性能选项。
3.  **运行 ComfyUI:** 回到主界面顶部，点击“运行 ComfyUI”按钮。程序会检查配置，然后启动 ComfyUI 后台服务。
4.  **打开 ComfyUI 界面:** 在 ComfyUI 成功启动后（查看“日志”标签页确认），点击“设置”标签页端口号旁边的“打开”按钮，或手动在浏览器中访问 `http://127.0.0.1:你的端口号` (默认是 8188)。
5.  **停止 ComfyUI:** 点击主界面顶部的“停止”按钮。
6.  **管理版本和节点:** 切换到“管理”选项卡。根据需要刷新本体版本列表或节点列表。选择列表中的项，然后点击相应的按钮进行激活、安装、更新或卸载操作。**重要：进行本体或节点更新/安装/卸载等操作前，必须先停止 ComfyUI。**
7.  **诊断错误:** 如果 ComfyUI 运行出错，可以在“日志”标签页查看详细信息。然后切换到“分析”标签页，配置好 AI 接口和密匙（如果未配置），点击“诊断”按钮。程序会发送日志给 AI 进行分析，结果会显示在下方区域。AI 可能会给出修复建议和命令，你可以点击“修复”来**模拟**运行这些命令，**注意这只是模拟，不会真正修改文件**，你需要手动根据模拟结果在终端执行实际操作。
8.  **退出程序:** 直接关闭窗口即可。程序会在退出前尝试停止 ComfyUI 服务，并保存日志和配置。

#### 3. 界面概览

启动后，程序界面简洁直观，主要分为顶部控制条和下方四个选项卡区域。

*   **顶部控制条:** 显示程序当前状态（如运行中、已停止），以及用于整体启动和停止 ComfyUI 的按钮。。
*   **选项卡区域:**
    *   **设置 / Settings:** 配置 ComfyUI 路径、Python 路径、Git 程序路径等基础设置，以及各种性能相关的优化选项，并配有快捷方式便于打开 ComfyUI 的常用子文件夹。
    *   **管理 / Management:** 负责 ComfyUI 本体和 custom_nodes 节点的版本与安装管理。
    *   **日志 / Logs:** 分别显示 ComLauncher 和 ComfyUI 的详细运行日志。
    *   **分析 / Analysis:** 用于配置 AI 服务的接口和密匙。将日志结合“用户诉求”输入，发送 AI 诊断并模拟执行修复建议。

#### 4. 详细界面
	
**界面及运行逻辑 (按顺序)：**

1.  **设置** 所有设置的改动会自动保存到 launcher_config.json 文件
    *   **布局和内容：**
    *   **基本路径与端口：**
        *   指定 "ComfyUI 安装目录" 输入框、 "ComfyUI 监听与共享端口" 输入框。
        *   "ComfyUI 监听与共享端口" 输入框（默认8188）、 "打开" 按钮，用于在浏览器中打开该地址。
        *   指定  "Git 路径" 输入框，程序在需要 Git 操作时调用此路径。
    *   **性能显存优化：** 用于配置 ComfyUI 启动时使用的命令行参数。
    *   **文件夹快捷区域：** 提供按钮,点击可快速打开 ComfyUI 安装目录下的 workflows, custom_nodes, models, loras, input, output 文件夹。：

2.  **管理**
    *   **布局：**
    *   **仓库地址区域：**
        *   "本体仓库地址" 输入框 、"节点配置地址" 输入框
    *   **节点管理区域：**
        *   **本体标签页：**
            *   显示从 "本体仓库地址" 获取的 ComfyUI 本体历史版本列表。
            *   选中列表中的版本后，点击 "激活选中版本" 按钮，下载并覆盖安装选定的 ComfyUI 本体版本。
        *   **节点标签页：**
            *   有搜索框、 "搜索" 按钮、"刷新列表" 按钮、"切换版本" 按钮、"卸载节点" 按钮、"更新全部" 按钮。
            *   默认列表显示当前 `ComfyUI 安装目录\custom_nodes` 内的全部已安装节点。列表包含节点名称、状态、本地ID、仓库ID、仓库地址信息。
			*   "切换版本" 按钮：点击后在单独弹窗显示该节点的历史版本列表。"版本切换" 弹窗内包含版本、提交 ID、更新日期及对应的 "切换" 按钮。
			*   "更新全部" 按钮：点击后根据 "仓库ID" 更新当前本地节点。
            *   "刷新列表" 按钮，用于刷新节点列表显示。
            *   在搜索框输入文字并点击 "搜索" 按钮后，列表将显示已安装和未安装的、与搜索条件及 "节点配置地址" 匹配的节点。
            *   读取节点 Git 仓库地址和获取仓库 ID/更新日期等耗时 Git 操作应在单独线程中执行，不阻塞主界面和 ComfyUI 的启动。

3.  **日志**
    *   ** 包含两个子标签页："ComLauncher日志" 和 "ComfyUI日志"。
        *   ComLauncher日志标签页：独立显示 ComLauncher 启动器程序的全部运行日志。
        *   ComfyUI日志标签页：独立显示 ComfyUI 进程的全部运行日志。

4.  **分析**
    *   **布局：**
    *   **顶部区域：**
        *   "API接口" 输入框、"API密匙" 输入框 ，用于配置 AI 诊断服务的访问地址和密钥。
        *   "诊断" 按钮 ：点击后触发日志发送和分析任务。
        *   "修复" 按钮：点击后模拟执行分析结果中建议的修复命令。
        *   “用户诉求”文本框：用于输入你遇到的具体问题描述，辅助 AI 理解。
    *   **下方区域：** CMD 代码显示框，用于显示诊断结果和模拟修复过程。
    *   **功能逻辑：**
        *   点击 "诊断" 按钮后 (需填写 "API接口" 和 "API密匙")：
            *   将“ComLauncher日志”、“ComfyUI日志”以及“用户诉求”的内容按照特定格式（详见下方参考）合并，
            *   通过配置的 API 接口联网，发送给外部 AI 服务(例如发送至 Gemini 2.5 API并反馈结果)。
            *   接收到 AI 服务的响应后，提取并显示返回的分析结果和修复建议。
        *   点击 "修复" 按钮后：
            *   解析 CMD 代码显示框中的修复建议，并"模拟"显示具体操作，不会真正执行任何系统命令或修改文件。（可根据模拟建议手动操作）。
    *   **日志合并后格式参考：**
	
            *   @@@@@@@@@设定：
	 	 	 	 你是一位严谨且高效的AI代码工程师和网页设计师，专注于为用户提供精确、可执行的前端及后端代码方案，并精通 ComfyUI 的集成。你的回复始终优先使用中文。@@ComfyUI 集成: 精通 ComfyUI 的 API (/prompt, /upload/image, /ws 等) 调用及数据格式，能够设计和实现前端与 ComfyUI 工作流的对接方案（例如参数注入、结果获取），当ComfyUI 运行出错后可以提供解决方案。
				 当“ComLauncher日志”或“ComfyUI日志”其中有日志为空时则跳过空日志的分析，只分析另一部分日志内容。
				 以下为用户诉求和运行日志：
            *   @@@@@@@@@用户诉求：
				 （详细输入的用户诉求）
				 
            *   @@@@@@@@@ComLauncher后台日志
	 	 	 	 （详细日志内容）

            *   @@@@@@@@@ComfyUI日志
	 	 	 	 （详细日志内容）
				 
#### 5. 技术日志

**未来功能：**

##远期待增加功能：X.X.X：忘记之前的一切，版本号更新：在当前版本代码基础上，严格保持现有布局、代码结构和功能，增加以下修改：

@@@@@修改1：
根目录增加"环境维护标签页",包含以下标签页信息：
环境信息："Win版本"、"CPU"、"显卡"、"内存"、"python版本"、"diffusers"、"ffmpeg"、"torch"、"xformers"、"pip版本"、"transformers"；
PyTorch与xFormers：推荐并罗列适合当前系统的PyTorch与xFormers版本列表；
环境修复：重新安装已有依赖项；
安装组件：输入pip包名称和版本，安装；
更新组件：使用review自动检测并更新所有依赖项。
@@@@@修改2：
语言设置
"ui_modules"文件夹中增加单独的”language“文件，功能为在"launcher.py"设置界面增加选项："语言/Language"栏，下拉列表有"简体中文、English",默认为简体中文，在选中后自动保存并在下次启动时生效
对应所有界面上的文字、日志等内容，均切换"语言/Language栏"后按照其选中的语言显示。其中“文件夹快捷方式"部分不做调整，仍保留全英文显示，

**修改日志：**

##待修改：2.6.3：在当前版本代码基础上，严格保持现有布局、代码结构和功能，增加以下修改：

@@@修改1：

@@@以下为当前版本代码：

##2.6.2：节点列表增加暂存功能；节点双击可切换版本；代码拆分成模块；
在当前版本代码基础上，视觉上严格保持2.5.11布局和功能，增加以下修改：

@@@@@修改原则：在当前2.6.1版本代码基础上，视觉上严格保持2.5.11版布局和功能。对于本次未产生调整的代码文件，仅展示文件名称，其代码省略
将上述代码更新到2.6.1后，报错如下，请修复：
@@@@@错误1：设置界面原有的"文件夹快捷方式"样式（框）及"基本路径与端口"栏内"浏览"和"打开"样式（框）丢失，这是不对的，请补充回来
@@@@@错误2：launcher打开后即可显示"运行"，不受其他任何的影响。而不是停在"停止"和进度条循环上
@@@@@错误3："管理"标签页>>"节点"标签内，列表加载后"搜索"栏各项都为无法运行，请按照2.5.11的原有逻辑修正
@@@@@修改4：增加功能："管理"标签页>>"节点"标签内，对列表内节点双击也可触发"切换版本"操作然后弹窗

##2.6.1：在当前版本代码基础上，严格保持现有布局、代码结构和功能，增加以下修改：

@@@@@修改1：
1.简化代码并将launcher代码拆分，满足功能和现有视觉布局前提下，尽量将不同的标签页内容拆分成单独的.py文件，由launcher.py去加载，便于后期单独修改标签页内容或者增加新的标签页而不影响其他区域的代码（拆分的.py文件默认为当前根目录下的"ui_modules"文件夹中，并以标签页的“英文.py”命名）；
2.实现：在launcher.py所在目录运行python launcher.py即可运行
3.将配置文件"launcher_config.json"及生成的日志文件"ComLauncher.org"也调整到当前根目录下的"ui_modules"文件夹中。
4.对于"本体"和"节点"的列表，增加列表存储功能：每次运行时获取当前列表信息，并分别存储为单独的列表文件（位于根目录下的"ui_modules"文件夹中），启动后后台仍执行原有获取列表动作，但前台标签将直接显示已保存的列表文件,待后台加载成功后覆盖保存列表文件并在前台标签列表刷新显示。
@@@@@以下为当前版本代码：

##2.5.11：正常显示弹窗列表。

@@@@@修改1：
修复"版本切换"弹窗列表样式问题：修改列表项的布局逻辑，确保抬头栏和所属信息纵向上对齐。

##2.5.10：在当前版本代码基础上，严格保持现有布局、代码结构和功能，增加以下修改：

@@@@@修改1：
不改变其他页面，仅调整管理标签页》节点标签页》"版本切换"弹窗：按照以下要求重新设计"版本切换"弹窗界面:
"版本切换"定义为新的窗口；在节点标签页选中节点并点击"版本切换"后弹出本窗口
窗口内容：该节点的全部历史版本列表，抬头栏包含"版本"、"状态"、"提交ID"、"更新日期"信息及"操作"栏，"操作"栏下为对应版本的 "切换" 按钮；"切换" 按钮和历史版本信息一一对应，点击 "切换"后按照对应版本更新节点；
窗口布局：严格参考"节点"标签页的列表样式；列表占满窗口，配有下拉滑块； 
单独线程获取点击“切换版本”对应的节点的过往版本ID、对应的描述信息以及更新日期，对于其他节点未点击“切换版本”按钮，则不获取其全部历史版本信息，以优化启动速度。

##2.5.9：在当前版本代码基础上，严格保持现有布局、代码结构和功能，增加以下修改：

@@@@@修改2：
优化“分析”标签页布局：“API接口”填入框及“API密匙”填入框的拉长，填入框的左侧边界更加靠近“API接口”文字及“API密匙”文字；
将”用户诉求“及”用户诉求“输入框视觉效果同调整后的“API接口”填入框及“API密匙”填入框一致；调整视觉效果后，单独调整”用户诉求“输入框高度为可输入6行文字的高度，在调整输入框高度后，将输入框内部默认字号降低1号。

##2.5.8：在代码基础上，严格保持现有布局、代码结构和功能，增加以下修改：

@@@@@修改1：
调整管理标签页，本体标签页：部分版本的日期解析失败，请修复，修复后如果列表中仍存在日期解析失败部分，对日期解析失败部分以版本号排序显示。排序示意“0.2.31、0.2.22、0.2.15、0.2.3、0.2.2、0.2.1”（注意示意顺序0.2.31顺序优于0.2.22优于0.2.9）；
@@@@@修改3：
优化“分析”标签页布局：“API接口”填入框及“API密匙”填入框的拉长，填入框的左侧边界更加靠近“API接口”文字及“API密匙”文字；
@@@@@修改4：
在当前程序关闭时，自动将“ComLauncher日志”和“ComfyUI日志”合并后的日志保存在当前目录下“ComLauncher.org”
合并后日志格式示意：
"""
@@@@@@@@@ComLauncher日志
{launcher_logs if launcher_logs else "（无）"}

@@@@@@@@@ComfyUI日志
{comfyui_logs if comfyui_logs else "（无）"}
"""

##2.5.7：在代码基础上，严格保持现有布局、代码结构和功能，增加以下修改：

@@@@@修改2：
调整分析标签页：当判定当前窗口“API接口”填入框及“API密匙”填入框有信息后，“诊断”按钮即可运行，“诊断”按钮状态不受其他元素的干扰。
@@@@@修改3：
错误修正：当前”comlauncher日志“无更新或后台无动作时，进度条停止滚动。
@@@@@修改4：
在“分析”标签页，“API接口”填入框及“API密匙”填入框下，增加一栏，为“用户诉求”填入框，“用户诉求”填入框显示为一行，但是允许用户填入多行信息，字符不受限制。并将“用户诉求”填入api的系统设定中。

"""@@@@@@@@@设定：
你是一位严谨且高效的AI代码工程师和网页设计师，专注于为用户提供精确、可执行的前端及后端代码方案，并精通 ComfyUI 的集成。你的回复始终优先使用中文。@@ComfyUI 集成: 精通 ComfyUI 的 API (/prompt, /upload/image, /ws 等) 调用及数据格式，能够设计和实现前端与 ComfyUI 工作流的对接方案（例如参数注入、结果获取），当ComfyUI 运行出错后可以提供解决方案。
当“ComLauncher日志”或“ComfyUI日志”其中有日志为空时则跳过空日志的分析，只分析另一部分日志内容。
以下为用户诉求和运行日志：
@@@@@@@@@用户诉求：
“用户诉求”
@@@@@@@@@ComLauncher日志
{launcher_logs if launcher_logs else "（无）"}

@@@@@@@@@ComfyUI日志
{comfyui_logs if comfyui_logs else "（无）"}
"""

##2.5.6：在代码基础上，严格保持现有布局、代码结构和功能，增加以下修改：

@@@@@修改1：
布局微调：版本号位置不变，将“设置”、“管理”、“日志”、“分析”标签栏位置上移，同版本号位置处于同一高度。
@@@@@修改2：
调整顶部“运行comfyui”状态，窗口打开即判定可以运行直至comfyui运行都会保持可运行状态，不受其他加载项的干扰；运行过程中，只有当开始运行comfyui后，“运行comfyui”才会显示为不可运行状态，不受“停止”干扰。
@@@@@修改4：
调整分析标签页：报错“[ErrorAnalysis]API 请求错误404.请检查 API 端点、密钥和网络连接,详情:”请修正
当前API接口为“https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-04-17”
可兼容其他API接口。
@@@@@修改6：
错误修正：”comlauncher日志“标签页，”comlauncher日志“不受“comfyui日志”干扰，在“comfyui日志”出现后在保留基础上继续记录comlauncher日志情况。

##2.5.5：在代码基础上，严格保持现有布局、代码结构和功能，增加以下修改：

@@@@@修改2：
调整顶部“运行comfyui”状态，窗口打开即判定可以运行直至comfyui运行都会保持可运行状态，不受其他加载项的干扰；

##2.5.4：在代码基础上，严格保持现有布局、代码结构和功能，增加以下修改,版本号更新2.5.4

@@@@@修改1：
布局微调：将版本号位置调整至“设置”、“管理”标签页同高位置，水平位置不变，仍在最右侧；

##2.5.3：在基础上，严格保持原有功能，增加以下修改,版本号更新2.5.3

@@@@@修改1：
调整管理标签页，本体标签页：日期信息显示准确完整。
@@@@@修改2：
调整管理标签页，节点标签页：取消点击切换版本后的“确认”弹窗，直接在点击”切换版本“后弹出”版本切换“弹窗
@@@@@修改4：
调整分析标签页：除了API填写区域外，cmd窗口占满视口。
提出将api接口及api密匙提交联网，在线连接API以分析诊断的实施方式（重点实现功能）。
@@@@@修改5：
调整日志标签页：标签页内两个标签页窗口打开后均默认将滑块滑至最低部（即当日志有变化时，滑块定位到最新的日志位置）

##2.5.2（回退重生2.5.2，原2.5.1以后版本获取节点信息错误、API错误、经常语法错误）

在以上基础上迭代修改，版本号更新2.5.2，输出完整修改后代码：
@@@@@@修改1：
调整更新管理标签页，节点标签页：取消点击”切换版本“后的confirm确认弹窗，直接在点击”切换版本“后弹出”版本切换“弹窗；"版本切换"弹窗内有该节点的历史版本列表和对应”切换“按钮，内容占满弹窗窗口
@@@@@@修改2：
调整更新管理标签页，节点标签页：列表“本地ID”通常按照git获取配置自动显示8位，不必完整显示；
@@@@@@修改3：
调整更新管理标签页，节点标签页："刷新节点列表"按钮更名为"刷新列表"
@@@@@@修改4：
当前后台无动作时，总窗口顶部进度滑块无动作。
@@@@@@修改5：
调整设置标签页:文件夹快捷区域，文件夹快捷按键、nodes、models、lora、input、output。其地址为获取“ComfyUI 安装目录”地址后对应的为\custom_nodes、\models、\lora、\input、\output地址，如：假设“ComfyUI 安装目录”填写为“D:\Program\ComfyUI”，则点击“models”按钮则打开“D:\Program\ComfyUI\models”文件夹，其他文件夹快捷同理；workflows文件夹除外，workflows文件夹为加载“ComfyUI 安装目录”下的\user\default\workflows目录。
@@@@@@修改6：
调整设置标签页:“基本路径与端口”标签页：删除“ComfyUI 工作流目录”及对应输入框，相应调整布局；
“ComfyUI 监听与共享端口”输入框右侧，增加“打开”按钮，视觉样式同上面的“浏览”按钮。
@@@@@@修改1：调整逻辑：界面打开后，“运行comfyui”即判定可以运行。不受其他加载项的干扰；
@@@@@@修改2：修改标签页，“comfyui后台”，拆分为“后台”标签和“comfyui”标签页：其中：
“后台”标签页：参考原来“comfyui后台”标签页显示效果显示当前程序后台全部日志，
“comfyui”标签页：参考原来“comfyui后台”标签页显示效果显示COMFYUI后台全部日志，
@@@@@@修改3：联网诊断：“错误分析”标签页，当运行“诊断”后，将上述的“后台”标签日志和“comfyui”标签页日志合并，并以
如下“日志合并后格式参考”格式发送给真实的API运行诊断及后续修复处理。
@@@@@@修改4：错误分析标签页内，诊断按钮在填入“API接口”后可运行。点击诊断按钮后，通过“API接口”和“api密匙”实现联网将合并后的日志发送给带密匙的API接口，然后反馈信息；在点击诊断按钮后，根据反馈信息模拟修复（诊断为真实的联网反馈，修复为模拟修复）。
@@@@日志合并后格式参考：

"""
@@@@@@@@@设定：
你是一位严谨且高效的AI代码工程师和网页设计师，专注于为用户提供精确、可执行的前端及后端代码方案，并精通 ComfyUI 的集成。你的回复始终优先使用中文。@@ComfyUI 集成: 精通 ComfyUI 的 API (/prompt, /upload/image, /ws 等) 调用及数据格式，能够设计和实现前端与 ComfyUI 工作流的对接方案（例如参数注入、结果获取），当ComfyUI 运行出错后可以提供解决方案。

以下为我的运行日志：
@@@@@@@@@ComLauncher后台日志
xxxxxxxx（详细日志内容）

@@@@@@@@@ComfyUI日志
xxxxxxxx（详细日志内容）
"""

##2.5.1

@@@@@要求5：
调整更新管理标签页，节点标签页："切换/安装选择版本"更名为"切换版本"，在"切换版本"右侧，增加"卸载节点"和"更新全部"按钮，点击后可匹配仓库提交ID更新当前本地节点。点击切换版本后，单独线程获取该节点的过往版本ID、对应的描述信息以及更新日期，以单独弹窗显示，窗口名称为"切换版本"。该窗口内，选择对应版本后则更新节点。
@@@@@要求6：
调整更新管理标签页，节点标签页：调整”搜索“和搜索框顺序，左侧为搜索框，右侧为”搜索“，且”搜索“为可执行的按钮。当其搜索框有文字，点击搜索后，显示已安装和未安装的节点。
@@@@@修正要求7：
迭代更新：调整更新管理标签页，节点标签页："切换版本"按钮赋予功能：点击后，单独弹窗"版本切换"；"版本切换"弹窗内有该节点的版本列表和对应”切换“按钮，内容占满弹窗，另配有下拉滑块，（当列表下拉时，继续加载本体信息，否则不加载。加载的本体信息内容为准确信息。）
列表内，主要显示内容为该节点的各个版本以"版本"、“提交ID”和“更新日期”，然后各个版本配有“切换”按钮。点击后按照选择版本更新节点
单独线程获取该节点的过往版本ID、对应的描述信息以及更新日期，以优化启动速度。

##20250425-1：以此开始以版本号2.5.1格式迭代记录日志

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
调整更新管理标签页，节点标签页：列表默认显示为当前ComfyUI\custom_nodes内全部节点。要求全部展示，显示不足可以下拉滑块显示。当其搜索框有文字执行搜索后，才显示已安装和未安装的节点。列表“本地版本”名称改为“本地ID”通常为8位的数字及字符，完整显示其提交ID；列表“版本”改为"仓库ID"：显示其仓库地址当前的完整提交ID和更新日期。

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

##过往日志省略。。。。。。