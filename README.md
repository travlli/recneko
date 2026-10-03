# /rec检查喵/

小米 / 红米 刷机报错检查助手 —— 粘贴日志或丢一张截图 → 自动判定平台与模式 →
从内置知识库检索出排查步骤与验证方法。覆盖 **MediaTek（MTK）/ 高通（Qualcomm）
/ fastboot / recovery / AVB** 常见报错。

界面为二次元风（樱花粉 + DeepSeek 蓝），内置原创吉祥物「大肥鱼喵」。

- GUI：主交付物用 **tkinter**（标准库，全平台可用）；另保留 Toga 版供 x64 与 Android
- 知识库：dsh-kb Obsidian 库（`kb/`），编译成 `kb.json` 后打进应用
- 运行方式：**完全离线**，日志与图片都不会离开本机

> 名称写法：窗口标题与显示名是 `/rec检查喵/`（前后斜杠是刻意的命令风写法）。
> 可执行文件名是 `rec检查喵.exe` —— Windows 文件名不能包含 `/`。

---

## 一、功能

| 能力 | 说明 |
|---|---|
| 平台判定 | 按日志里的特征串判定 MTK / 高通 / fastboot / recovery / AVB，并给出置信度与判定依据 |
| 模式识别 | BROM、Preloader、EDL/9008、fastbootd、Recovery 等 |
| 信息抽取 | 抽出 `ERROR 4032`、`STATUS_BROM_*`、`FAILED (remote: ...)` 等错误码，以及机型代号线索 |
| 方案检索 | 关键词加权 + 文档频率加权排序，返回最多 5 条方案（症状→原因→步骤→验证） |
| **图片识别** | 选一张报错截图/照片，判断画面属于哪种报错，直接带出对应方案（纯 Pillow，exe/apk 都能用） |
| 二次元界面 | 樱花粉+蓝配色、圆角卡片、内置吉祥物「大肥鱼喵」、喵系文案 |

知识库现有 **18 条** howto 条目（MTK 6 / 高通 6 / fastboot 3 / recovery 2 / AVB 1）。

## 一之三、形象与图标（使用用户提供的原图）

应用内展示的、以及打包进 exe 的图标，都用**用户提供的原图**，不做裁剪、抠图、
调色或重绘：

| 资源 | 说明 |
|---|---|
| `src/mirecovery/resources/character_sheet.jpg` | 原图入库（Q 版三头身鲸鱼娘，462×501，按原始编码转存） |
| `src/mirecovery/resources/icon.png` | 图标：原图**居中** + 四周补原图四角底色（不裁画面） |
| `src/mirecovery/resources/icon.ico` | 多尺寸 Windows 图标（同上方式生成） |
| `src/mirecovery/resources/window_icon.png` | 64px 标题栏图标 |

为什么图标要补边：Windows 图标必须是正方形，而原图是竖构图。补边是加背景，
没有改动画面内容本身；`tools/make_icon.py` 里有完整说明。

```powershell
.\.venv\Scripts\python.exe tools\make_icon.py
```

> 换图只需把新图片路径加到 `tools/make_icon.py` 的 `SOURCE_CANDIDATES` 开头，
> 或直接把图片放到 `resources/character_sheet.jpg` 再运行脚本。
>
> 历史：早期版本用 Pillow 图元程序化绘制过原创形象（`mascot.png`），也用过成熟
> 比例三视图设定图（`character_sheet.png`），均已按用户要求替换为当前原图。

### ⚠️ 版权提醒

这张图是**第三方作品**（形象设定源自社区开源资产库
[鲸鱼娘开源资产库](https://treapgogo.github.io/deepseek-whale-girl/)，该库明示
不代表深度求索官方立场并欢迎二创）。它不是本仓库原创，直接打进要对外分发的
exe / apk 可能涉及他人著作权。**如果计划商用或公开分发，请先自行确认授权。**
本仓库只做技术处理，不改变这一事实。

## 一之二、图片识别

**它做什么**：识别画面**类型**（Recovery 主菜单 / 数据损坏提示 / 挂载失败刷屏 /
fastboot 界面 / EDL 黑屏 / SP Flash Tool 弹窗 / MiFlash 报错 / sideload 失败），
然后打开对应知识库条目。

**它不做什么**：读不出图里的**文字**。所以它无法分辨截图写的是 `ERROR 4032`
还是 `ERROR 4004`。要精确定位错误码，请把文字粘进日志框。

**技术选型**：Android 端由 ChaquoPy 构建，只支持有限的一组预编译包 —— 有
`numpy`/`Pillow`/`opencv`，但**没有 Tesseract（C++ 二进制）、没有 onnxruntime**，
所以 PaddleOCR / RapidOCR / tesseract 都进不了 apk。最终选了纯 Pillow 的
**画面匹配**：`dHash` + 零归一化互相关（ZNCC）缩略图 + 边缘分布 + 颜色直方图，
加权相似度 + 最近邻分类。

> 踩坑记录：最初用「平均绝对差」做相似度，在 80% 是纯黑背景的屏幕上完全失效 ——
> 任意两张黑底截图都拿到 ~0.90 分。换成 ZNCC（对亮度/对比度不变，且忽略平坦区域）
> 后分数才有区分度。

**判定策略（关键）**：只有**相似度足够高**且**明显领先第二名**时才给结论；否则
如实回答「无法确定，请粘文字」。宁可少答，不可答错 —— 指错刷机方向比不回答更糟。
结构值过低的空白/全黑/过曝图直接拒绝，不会硬凑答案。

**准确率（务必看清前提）**：`tools/benchmark_recognition.py` 在**合成图**
（参考与测试都是程序绘制，测试图额外加了缩放/透视/旋转/光照/模糊/噪点/JPEG 干扰）上测得：

| min_score | 接受率 | 接受中正确率 | 错误接受 |
|---|---|---|---|
| 0.75 | 60.4% | 93.1% | 2 |
| **0.78（当前默认）** | **54.2%** | **100.0%** | **0** |
| 0.85 | 47.9% | 100.0% | 0 |

即：**愿意回答的那一半里，全部答对**。

> ⚠️ **这个数字来自合成图，不代表真机准确率。** 我没有真机截图可用，合成参考图
> 与真实屏幕（字体、系统版本、UI 布局）必然有差异。要让它真正可用，必须放真实照片。

**加入真实照片**（每类 2~5 张即可，拍照/截图都行，任意分辨率与旋转）：

```
kb/image_refs/user/<类别>/*.png|jpg
```

类别名用 `tools/build_references.py` 里 `LABELS` 的键（如 `recovery-menu`、
`spflash-error-dialog`）。放好后重建特征库并用真实图重新标定阈值：

```powershell
.\.venv\Scripts\python.exe tools\build_references.py
.\.venv\Scripts\python.exe tools\benchmark_recognition.py --sweep
```

真实参考图会与合成图合并使用，并在报告里标注来源。

## 二、目录结构

```
mi-recovery-helper/
├─ kb/                          # 知识库（dsh-kb Obsidian 库，权威数据源）
│  ├─ schema.md                 # 本库约定（含 platform 字段扩展）
│  ├─ index.md                  # 由 tools/build_kb.py 自动生成
│  ├─ raw/                      # 原始素材（不可变，等你丢现场日志进来）
│  ├─ wiki/howtos/*.md          # 18 篇排错条目
│  └─ image_refs/               # 图片识别参考集
│     ├─ synthetic/<类别>/      #   程序绘制的示意图（make_reference_images.py 生成）
│     ├─ user/<类别>/           #   ★ 你放真机照片的地方（现在为空）
│     └─ benchmark/<类别>/      #   加了拍照干扰的测试图（仅评测用）
├─ src/
│  ├─ launcher.py               # PyInstaller 入口（绝对导入，见 4.5）
│  └─ mirecovery/
│  ├─ app.py                    # Toga GUI
│  ├─ kb.py                     # 知识库加载 + 检索引擎
│  ├─ scanner.py                # 日志分析（平台/模式/错误码）
│  ├─ imagefeatures.py          # 图片特征提取（dHash/ZNCC/直方图）
│  ├─ recognize.py              # 画面识别 + 置信度/拒绝策略
│  ├─ report.py                 # 报告渲染
│  ├─ data/kb.json              # 构建产物，打进 exe/apk
│  └─ resources/icon.{png,ico}
├─ tools/
│  ├─ build_kb.py               # wiki → kb.json + index.md
│  ├─ smoke_test.py             # 文字检索 8 用例 + 图片识别检查（无需 GUI）
│  ├─ verify_gui.py             # Toga API/样式/事件流程无头验证
│  ├─ verify_entrypoints.py     # 校验打包入口（防相对导入崩溃）
│  ├─ make_reference_images.py  # 生成合成参考图 + 拍照干扰测试图
│  ├─ build_references.py       # 参考图 → image_refs.json（含真实照片合并）
│  ├─ benchmark_recognition.py  # 图片识别基准 + 阈值扫描
│  ├─ frozen_selftest.py        # 冻结自检：验证 exe 内知识库/参考库可用
│  ├─ sync_kb.py                # 把 kb/ 同步进 ~/.dsh/kb（纯 Python）
│  ├─ sync_kb.ps1               # 同上，PowerShell 版（本机受限环境用这个）
│  ├─ render_index.py           # 生成 index.md / log.md 行（供 ps1 调用）
│  ├─ make_icon.py              # 生成图标
│  └─ ci_prepare.py             # CI 打包前的准备步骤
├─ MiRecoveryHelper.spec        # PyInstaller 单文件 exe 配置
├─ MiRecoveryHelper.selftest.spec  # PyInstaller 冻结自检配置
├─ pyproject.toml               # Briefcase 配置（Windows MSI / Android APK）
└─ .github/workflows/build.yml  # CI：一键产出 exe + apk
```

## 三、本地开发

```powershell
# 1. 建虚拟环境并安装依赖
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: "toga>=0.4.0" "cffi>=1.17"

# 2. 生成知识库数据
.\.venv\Scripts\python.exe tools\build_kb.py

# 3. 跑冒烟测试（验证检索正确性，不需要 GUI）
.\.venv\Scripts\python.exe tools\smoke_test.py

# 4. 启动 GUI
.\.venv\Scripts\python.exe -m mirecovery
```

> Windows 上 Toga 依赖 `pythonnet` → `cffi`。若不加 `--only-binary=:all:`，pip 会在
> 没有编译器的环境下反复尝试源码构建 cffi，表现为「安装卡住」（实际是依赖回溯）。

## 四、构建交付物

### 4.1 推荐：GitHub Actions 一键出 exe + apk

把本目录推到 GitHub，`.github/workflows/build.yml` 会自动产出：

| 产物 | 来源 | 说明 |
|---|---|---|
| `MiRecoveryHelper.exe` | PyInstaller | Windows 免安装单文件 |
| `MiRecoveryHelper-*.apk` | Briefcase | Android 安装包 |
| `*.msi` | Briefcase | Windows 安装包（可选，失败不影响其它产物） |

在仓库 **Actions → Build EXE + APK → Run workflow** 手动触发，或推送 tag（`v*`）。
产物在该次运行页面的 **Artifacts** 区域下载。

CI 里包含一个**冻结自检**步骤（`MiRecoveryHelper.selftest.spec`）：它会打出一个小
控制台程序并真的运行，验证打包后的 exe 仍能读到内嵌知识库 —— 这是唯一只在打包
后才会暴露的故障点。

### 4.2 本地构建

```powershell
# 一次产出全部 Windows 交付物（两种 exe + 便携压缩包 + 冻结自检）
.\.venv\Scripts\python.exe tools\build_exe.py
```

或分别构建：

```powershell
# ① 单文件 exe（免安装，但每次启动要解压到 %TEMP%）
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm MiRecoveryHelper.spec
# 产物：dist\MiRecoveryHelper.exe

# ② 目录版（推荐：不解压、启动快、不怕磁盘紧张）
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm MiRecoveryHelper.onedir.spec
# 产物：dist\MiRecoveryHelper\MiRecoveryHelper.exe
```

```bash
# APK（需要 git + JDK 17；Briefcase 会自动下载 Android SDK / NDK）
python -m pip install briefcase
python tools/build_kb.py
briefcase create android
briefcase build android
briefcase package android --no-input
# 产物：dist/*.apk
```

### 4.5 报错「Could not create temporary directory!」怎么办

单文件 exe 每次启动都要把整个运行时解压到 `%TEMP%`，这个报错说明**临时目录写不进去
或空间不够**（本机实测：C 盘只剩 0.9 GB 时必现）。三种解法，按推荐顺序：

| 解法 | 做法 | 说明 |
|---|---|---|
| **改用目录版**（推荐） | 跑 `MiRecoveryHelper\MiRecoveryHelper.exe` | onedir 布局不解压任何东西，**完全不依赖临时目录**，启动也更快。代价是它是个文件夹（已提供 zip） |
| 腾出空间 / 改 TEMP | 清理磁盘，或把 `TEMP`/`TMP` 指到空间充足的分区后再启动 | 单文件版需要临时目录至少有几十 MB 可写空间 |
| 排除干扰 | 关掉杀毒软件的实时防护 / 沙箱拦截 | 部分安全软件会拦 PyInstaller 的自解压行为 |

诊断命令（在 CMD 或 PowerShell 里）：

```powershell
echo $env:TEMP          # 看临时目录指向哪
Test-Path $env:TEMP     # 必须为 True
Get-PSDrive C           # 看剩余空间
```

> 本机出这个错时 C 盘只剩 **0.98 GB**；换到工作区内可写目录后单文件版能正常启动，
> 目录版则**任何情况都不受影响**。这也是同时提供两种构建的原因。

### 4.6 ARM64 电脑：Toga 桌面界面不可用，主交付物改用 tkinter

**现象**（在 ARM64 Windows 上启动 Toga 版必然出现，与打包方式无关）：

```
RuntimeError: Failed to resolve Python.Runtime.Loader.Initialize from
...\pythonnet\runtime\Python.Runtime.dll
```

**根因**：Toga 的 Windows 后端 `toga-winforms` 依赖 `pythonnet`，而 pythonnet
在 PyPI 上只提供 **x86 / x64** 的运行时 DLL，**没有 ARM64 版本**。ARM64 上的
解释器是 ARM64，加载该 DLL 必然失败。实测佐证：

| 项目 | 实测值 |
|---|---|
| Python 解释器 | 3.12.14，`platform.machine()` = **ARM64** |
| `pythonnet/runtime/Python.Runtime.dll` | PE machine = **0x014C (x86)** |
| 打包后的 `python312.dll` | PE machine = 0x8664 (x64) |
| 直接 `Assembly.LoadFrom` 该 DLL | `HRESULT 0x80131515`（加载被拒） |

备选方案同样不通：`toga-webview2` 在 PyPI 上**不存在**，`pywebview` **也依赖
pythonnet**。

**解法**：界面改用 **tkinter**（Python 标准库自带，Tk 8.6，完全不碰 .NET）。
业务逻辑一行未改 —— `kb.py` / `scanner.py` / `imagefeatures.py` /
`recognize.py` / `report.py` 全部复用。

| 文件 | 作用 |
|---|---|
| `src/mirecovery/tkapp.py` | tkinter 界面（主交付物） |
| `src/mirecovery/app.py` | Toga 界面（保留：x64 桌面 + Android 构建仍用它） |
| `src/launcher.py` | 探测 Toga 是否可用，不可用则自动回退 tkinter；可用 `MIRECOVERY_GUI=tk\|toga` 强制 |
| `MiRecoveryHelper-tk*.spec` | tkinter 版打包（排除整个 Toga/.NET 栈） |

构建产物：

```powershell
python tools\build_exe.py          # 全部产物 + 冻结自检
python tools\build_exe.py --tk-only
```

| 产物 | 说明 |
|---|---|
| `MiRecoveryHelper.exe` | tkinter 单文件版（主交付物，无 .NET 依赖） |
| `MiRecoveryHelper/` + `-portable.zip` | tkinter 目录版，不依赖 %TEMP% |
| `MiRecoveryHelper-toga.exe` | Toga 版，**仅 x64 可用** |

> Android 侧不受影响：`toga-android` 不经过 WinForms/pythonnet，Briefcase 构建照旧。

### 4.3 本机未能构建 APK 的原因（重要）

APK 是在 CI 里构建的，**本机没有产出 apk**，原因是环境缺三样东西，都属硬性前置：

| 缺什么 | 影响 |
|---|---|
| JDK 17 | Briefcase 构建 Android 必须有 `java`/`javac`，本机 `java` 不存在 |
| git | `briefcase create` 强制要求 git，本机未安装 |
| 磁盘空间 | Android SDK + NDK + Gradle 需约 10 GB；本机 C: 仅剩 2.4 GB，D: 0.1 GB |

exe 路线不受影响，已在本机实际构建并通过冻结自检。

### 4.4 打包踩坑记录（改配置前值得一读）

- **Briefcase 读的是 `[tool.briefcase]`，不是 `[briefcase]`**。写在 `[briefcase]`
  下会被完全忽略，报错却是「Global configuration is incomplete」。
- **许可字段必须是 app 级**（`[tool.briefcase.app.<name>]`）：`license` 要是合法
  SPDX 表达式，且需配 `license-files`，否则报「does not contain a valid PEP 639
  license definition」。
- **Briefcase 主目录不可写时会直接失败**：本机 `%LOCALAPPDATA%\BeeWare` 写不进去，
  需用 `BRIEFCASE_HOME` 指到可写目录（CI 上无此问题）。
- **Windows 上 Toga 依赖 `pythonnet` → `cffi`**：不加 `--only-binary=cffi` 时 pip
  会尝试源码构建 cffi（本机无编译器），表现为「安装卡住」（实际是依赖回溯）。
- **PyInstaller 入口不能用包内的 `__main__.py`**：PyInstaller 把入口脚本当作
  `__main__` 执行且**没有父包**，`from .app import run` 会直接崩在启动阶段：

  ```
  ImportError: attempted relative import with no known parent package
  ```

  正确做法是用 `src/launcher.py`（绝对导入 `from mirecovery.app import run`）作为
  spec 入口。注意这个错误**导入测试和冻结自检都抓不到** —— 它们当包成员导入模块，
  不会以 `__main__` 方式执行。`tools/verify_entrypoints.py` 专门复现 PyInstaller
  的执行方式（用 `runpy` 以 `__name__='__main__'` 跑入口脚本），已接入 CI。

## 五、维护知识库

知识库是**数据源**，改完必须重新编译，应用才能检索到：

```powershell
# 改 kb/wiki/howtos/*.md 之后
.\.venv\Scripts\python.exe tools\build_kb.py     # 重新生成 kb.json + index.md
.\.venv\Scripts\python.exe tools\smoke_test.py   # 回归验证
```

把知识库发布到 dsh-kb 界面（`~/.dsh/kb`）：

```powershell
# 本机受限环境下 Python 子进程写不进该目录，用 PowerShell 版：
powershell -ExecutionPolicy Bypass -File tools\sync_kb.ps1
powershell -ExecutionPolicy Bypass -File tools\sync_kb.ps1 -DryRun   # 先看会写什么
```

```bash
# 环境正常时也可以用纯 Python 版：
python tools/sync_kb.py
```

同步会复制 `wiki/**/*.md` 与 `schema.md`，重新生成 `index.md`，并向 `log.md`
追加一行；**不会触碰 `raw/`**（schema 规定 raw 不可变）。

### 新增条目须知

- 文件名 kebab-case；frontmatter 必填 `title / tags / keywords / author / created / updated`
  **外加本库扩展字段 `platform`**（`mtk`/`qualcomm`/`fastboot`/`recovery`/`avb`）
- `keywords` 决定检索命中率：**请把报错原文照抄进去**（如 `ERROR 4032`、
  `Sahara Fail`、`not allowed in locked state`），不要只写中文概括
- 正文用 `## 症状 / ## 原因 / ## 步骤 / ## 验证`，不确定的写 `## 待确认`，**不要编**

## 六、内容准确性说明（重要）

现有 18 篇条目的作者是 `deepseek-agent`，是**依据通用维修经验撰写**的，
不是从真实工单里提炼的。撰写时刻意做了保守处理：

- 只写能确定的报错符号名，拿不准的（如 `ERROR 4008/2004/2005/3004` 的官方符号名、
  各机型 firehose programmer 文件名、`vbmeta_system` 是否存在）一律进「待确认」小节；
- 不编造工具版本号、固件版本号、分区名；
- 平台/机型差异大的地方明确标注依赖具体机型。

**请把现场日志丢进 `kb/raw/`**，用真实素材校正这些条目后再用于实际救火。
`raw/` 按 schema 不可变，素材放进去只增不改。

## 七、许可

MIT，见 [LICENSE](LICENSE)。
