# /rec检查喵/

小米 / 红米 刷机报错检查助手 —— 粘贴日志或丢一张截图 → 自动判定平台与模式 →
从内置知识库检索出排查步骤与验证方法。覆盖 **MediaTek（MTK）/ 高通（Qualcomm）
/ fastboot / recovery / AVB** 常见报错。

- GUI：主交付物用 **tkinter**（标准库，全平台可用）；另保留 Toga 版供 x64 与 Android
- 知识库：dsh-kb Obsidian 库（`kb/`），编译成 `kb.json` 后打进应用
- 运行方式：**完全离线**，日志与图片都不会离开本机
- 测试：`python -m pytest`（74 项通过）
- 日志：`%LOCALAPPDATA%/rec检查喵/logs/app.log`

> 名称写法：窗口标题与显示名是 `/rec检查喵/`（前后斜杠是刻意的命令风写法）。
> 可执行文件名是 `rec检查喵.exe` —— Windows 文件名不能包含 `/`。

> ⚠️ **两个必须先看的现实问题**
> 1. **知识库内容没有真实素材支撑**：18 条页面的 `sources` 全为空，`kb/raw/` 里
>    没有一份现场日志。内容是按通用经验整理的，动手前请先读每页的「待确认」。
> 2. **APK 从未成功构建过**：本机缺 JDK 17 / git / 磁盘，CI 配置也从未运行。
>    详见 [4.7 APK 的真实状态](#47-apk-的真实状态)。

---

## 一、功能

| 能力 | 说明 |
|---|---|
| 平台判定 | 按日志里的特征串判定 MTK / 高通 / fastboot / recovery / AVB，并给出置信度与判定依据 |
| 模式识别 | BROM、Preloader、EDL/9008、fastbootd、Recovery 等 |
| 信息抽取 | 抽出 `ERROR 4032`、`STATUS_BROM_*`、`FAILED (remote: ...)` 等错误码，以及机型代号线索 |
| 方案检索 | 关键词加权 + 文档频率加权排序，返回最多 5 条方案（症状→原因→步骤→验证） |
| **文字识别（OCR）** | 截图/照片里的报错文字直接读出来，喂给文字检索 —— 能分辨 `ERROR 4032` 和 `ERROR 4004`（见一之二） |
| **画面识别** | 判断画面类型（Recovery 菜单 / fastboot 界面 / 报错弹窗等），OCR 失效时作为补充 |
| 二次元界面 | 深蓝+白配色、圆角卡片、内置形象「鲸鱼娘」、喵系文案 |
| 上下滚动 | 内容比窗口高时整页可滚动（滚轮 / PageUp·PageDown / Home·End），放得下时滚动条自动隐藏 |
| 设置页 | 界面里直接填 API 地址 / Key / 模型，带「测试连接」 |
| 日志 | 写入用户目录，出问题时可直接把日志文件发出来 |

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

## 一之二、图片识别（先读文字，再认画面）

丢一张截图进来，应用**先做文字识别（OCR）**，把读到的文字喂给现有的文字检索引擎，
**再**用画面匹配作为补充。

**为什么文字优先**：画面匹配只能判断"这看起来像 MTK 报错弹窗"，读不出具体是
`ERROR 4032` 还是 `ERROR 4004`。而 OCR 能把那行字直接读出来，交给文字检索 —— 精度
完全不同。实测 5 类典型日志全部命中正确条目：

| 图上文字 | OCR 读出的关键词 | 命中条目 |
|---|---|---|
| `BROM ERROR : S_FT_ENABLE_DRAM_FAIL (4032)` | BROM / ERROR / DRAM / **4032** | SP Flash Tool 4032/4004/4008 |
| `Writing boot FAILED (remote: not allowed in locked state)` | FAILED / remote / locked | fastboot flash 失败 |
| `E:failed to mount /data` | failed / mount / data | Recovery 数据分区 |
| `ERROR: Sahara Fail` | ERROR / Sahara / Fail | 高通 Sahara/Firehose |
| `dm-verity corruption` | verity / corruption | AVB / dm-verity |

**画面匹配仍然保留**，因为它在两种情况下更有用：OCR 读不出东西（照片太糊），
或者 OCR 读到了词但知识库没有对应条目 —— 这时画面类型就是唯一的线索。

### 用真实网图测试（发现并修掉一个真缺陷）

我下载了 4 张真实图片（Bing 图片搜索，来自 CSDN / 什么值得买 / 知乎 / onfix 等站点）
跑完整流程。**结论：OCR 读得很准，但暴露了一个严重缺陷 —— 没有报错的画面也会被
塞一份刷机方案。**

| 图片内容（OCR 读出） | 修复前 | 分数 | 含报错特征 |
|---|---|---|---|
| 真实 fastboot 界面（机型/序列号/Secure Boot 等） | ❌ 给了 `qualcomm-secure-boot-nop-sig-tag` | 72.7 | 无 |
| 只有 `FASTBOOT` 字样 | ❌ 给了 `avb-verified-boot-corruption` | **10.6** | 无 |
| `Android 14 0/30`（升级进度） | ❌ 给了 `recovery-cant-load-android-system` | **16.6** | 无 |
| 乱码 `0n0 0 ǀ 0` | ✅ 正确拒绝 | — | 无 |

三张**完全没有报错**的图，被给出了看起来很确定的"对应解决方案"，其中一张的匹配分
只有 **10.6**（纯噪声）。**给没有故障的画面套用刷机步骤，是这个应用最危险的失败
模式** —— 用户可能据此清掉数据甚至刷坏机器。

**修复**：加两道闸门（`report.py` + `ocr.py`）：

1. **报错特征闸门** `looks_like_error()`：文字里必须出现报错语言（ERROR / FAILED /
   无法 / 失败 / 损坏 / 校验失败…）或 4 位错误码，才认为画面在报错。普通的 UI 标签
   （比如 fastboot 界面上的 `Secure Boot`）不算。
2. **分数下限** `MIN_IMAGE_MATCH_SCORE = 30`：低于此分不当作结论。

没通过闸门时，**不给方案**，而是明确说"图中没有发现报错信息"，并把最接近的条目
降级为**标注为"仅供参考"的建议**。

修复后同一批图片：**4/4 全部正确拒绝**；而真实报错截图仍然全部命中
（`ERROR 4032`、`E:failed to mount /data`、`ERROR: Sahara Fail`、`dm-verity corruption`
等 6 例全中）。回归测试见 `tests/test_ocr.py::test_no_fault_screen_gets_no_solution`。

> 测试图片来自第三方网站，**只用于本地验证，没有打进应用、也没有提交进仓库**
> （见 `.gitignore` 的 `.rec_test/`）。它们不是本项目可再分发的素材。

### OCR 后端（按优先级自动选择）

| 后端 | 可用条件 | 质量 | 能否进 apk |
|---|---|---|---|
| **Windows OCR** | Windows + `winsdk` | 好（长句可完全正确） | ✖（Windows 专属） |
| Tesseract | 装了 `tesseract` 二进制 + `pytesseract` | 好，支持中文 | ✖（C++ 程序，Chaquopy 不支持） |
| RapidOCR | 装了 `rapidocr_onnxruntime` | 好 | ✖（Chaquopy 无 onnxruntime） |
| 内置模板匹配 | 总是可用 | 数字好、整句弱 | ✔ |

> **内置后端的能力边界（实测，不掩饰）**：字形模板在**多字号**下数字准确率 99.6%、
> 4 位错误码整串 99.5%、全字符集 96.7%；但**端到端整句识别很弱**（实测 2/16），
> 因为逐字归一化会抹掉相对大小，`a`↔`b`、`3`↔`J`、`2`↔`Z` 会混。它是 apk 的兜底，
> 不是通用 OCR。
>
> 我曾尝试"词表匹配"（拿 KB 关键词当词表做整词比对），实测命中率 28% 且会
> **凭空报出词表里的词**（如把没有 qdl 的句子报成 qdl）。会自信编造内容的模块比
> 没有更糟，所以**没有采用**。

**启用更好的 OCR**（桌面端，可选）：

```powershell
.\.venv\Scripts\python.exe -m pip install winsdk     # Windows 内置 OCR（推荐）
# 或
.\.venv\Scripts\python.exe -m pip install pytesseract  # 还需另装 tesseract 程序
```

装好后重新构建，`tools/build_exe.py` 会自动把它打进 exe（`spec_common.ocr_hidden_imports`
负责收集），冻结自检会验证 OCR 在打包后仍然可用。

### OCR 后处理：形近字归一化

OCR 的经典错误是形近字混淆。实测 Windows OCR 把 `failed` 读成 `fai1ed`、
`allowed` 读成 `a110wed`。这些如果不处理，关键词检索就匹配不上。所以检索前会做
一次归一化（`normalize_confusions`）：

```
fai1ed to mount /data  ->  failed to mount /data
a110wed in locked state ->  allowed in locked state
ERROR 4032             ->  ERROR 4032      ← 纯数字 token 原样保留，绝不改写错误码
```

**画面匹配的准确率（合成图，仅供参考）**：`tools/benchmark_recognition.py` 测得
默认阈值 0.70/0.02 下接受率 54.2%、接受即正确 100%。两级检索（廉价 hash 预筛 →
只对前 4 个类别的 2 张参考图做精确 ZNCC）把纯 Python 路径从 140 ms/张降到 42 ms/张。

> ⚠️ 这个数字来自**合成图**，参考图与测试图同源，不代表真机准确率。现在 OCR 承担了
> 主要识别工作，画面匹配只是补充，所以这个限制的影响比之前小。

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

## 一之四、联网查询（默认关闭）

知识库覆盖有限，少见报错查不到。联网查询补上这一环：**先搜索 → 抓取正文 → 让模型只依据
抓到的材料整理方案**，并强制标注来源。

### 四条硬规则（这是模块存在的意义）

1. **默认关闭**。本应用承诺日志和截图不离开本机；不显式开启、不在弹窗里确认，什么都不会发出去。
2. **一定要给出解决方案**。联网查询先用网上资料，**再用模型自身的知识补全**，
   两处来源都明确标注：网页来的标 `[1]`、`[2]`（可点开核对），模型自己知道的标 `[自身知识]`
   （不可核对，会提醒你自行验证）。**不会用"资料不足"当结论收尾。**
3. **发送前脱敏**。序列号 / IMEI / 手机号 / 邮箱 / MAC / 用户名路径都会被替换成占位符。
   实测：`Serial number: HO70390000000355` → `<serial>`，而 `ERROR 4032` 原样保留。
4. **不可用就静默降级**。没配置、没网络、接口报错，都只返回失败对象，离线功能完全不受影响。

> **设计变更记录**：最初我把它做成"没有来源就不作答"，结果搜不到时用户什么也拿不到 ——
> 而这恰恰是最需要答案的时候。现在改成"搜索是补充、不是闸门"：搜到就用来源并标注，
> 搜不到就用模型知识并**明说没有来源**。安全底线保留在提示词里：不许编造文件名/命令/链接，
> 不确定就写不确定，涉及清数据/刷机/解锁/降级的操作必须写明风险并给出更安全的先行动作。

**实测效果**（`error: Antirollback check error`，当时 360 正被限流、只有 1 条来源）：

```
ok=True  grounded=True  自身知识=True  来源=1  tokens=4908

## 最可能的原因
设备当前防回滚版本号高于要刷入的包，脚本判定"降级触发安全机制"而中止 [1]。
脚本逻辑：用 fastboot getvar anti 读设备值，与 images\anti_version.txt 比较 [1]。
次要因素：解压路径含中文/空格导致读不到 anti_version.txt [1]

## 排查步骤
1. 先把包解压到纯英文短路径重刷（最安全，先做）[1]
2. 确认是不是真的在降级 [自身知识]
3. 确认设备 anti 版本 [1]
4. 改用同版本或更高的官方包 [1]
5. 仅当以上都不行、且你理解风险时：改 flash_all.bat 绕过校验 [1]（列了具体几行）
6. 分阶段刷机降低变砖风险 [1]
```

注意第 5 步——**有风险的操作排在最后**，并写了具体改哪几行；第 2 步用自身知识补充并标注。

### 配置：用界面设置，不用手改文件

主界面点 **「设置」** 打开设置页，直接填：

| 字段 | 说明 |
|---|---|
| 启用联网查询 | 勾选框，**默认不勾** |
| API 地址 | OpenAI 兼容接口，通常以 `/v1` 结尾，如 `https://api.deepseek.com/v1` |
| API Key | 默认掩码显示（`●`），旁边有「显示」开关 |
| 模型名 | 如 `deepseek-chat` / `gpt-4o-mini` / `qwen2.5:7b`（本地 ollama） |

还有 **「测试连接」** 按钮：它会**真的发一次极小请求**，把失败原因说清楚，而不是让你在
第一次真正查询时才发现地址写错。实测四种情况：

```
地址写错 / 服务端不接受  -> 按服务端返回提示
Key 写错               -> 认证失败（401）：API Key 可能不对。<服务端原文>
端口不通               -> 连不上：[WinError 10061] 由于目标计算机积极拒绝…
正确                   -> 连接成功：模型回复「可用」（65 tokens）
```

保存后「联网查询」按钮立刻变为可用，不需要重启。

**配置文件位置**（按优先级，不可写时自动回退）：

```
%LOCALAPPDATA%\rec检查喵\ai.json
%TEMP%\rec检查喵\ai.json
程序所在目录\ai.json
```

回退是必要的：本机实测 `%LOCALAPPDATA%` 对 Python 进程不可写，没有回退链的话设置页
会**保存失败却不告诉你**。现在 `save()` 返回实际写入路径，全部失败则抛错并在设置页
显示 `❌ 保存失败：…`。

Key 只存在这个本机文件里（权限设为仅本人可读），**不写日志、不随程序分发**。

### 也支持环境变量

`RECNEKO_AI_BASE_URL` / `RECNEKO_AI_API_KEY` / `RECNEKO_AI_MODEL` / `RECNEKO_AI_ENABLED`
（**优先级高于配置文件**，方便临时覆盖或 CI 使用）。

### 实测：本机环境的联网能力

| 能力 | 结果 |
|---|---|
| AI 接口（OpenAI 兼容） | ✅ 可用，实测调用成功并计费 |
| **GitHub API 检索** | ✅ 可用，报错原文最准 |
| **CSDN** | ✅ **可用，走它自己的 JSON 接口**（搜索页是 JS 壳）—— 实测 30 条结果，「通过SP_Flash_Tool线刷失败解决方法」等 |
| **360 搜索（so.com）** | ✅ 可用，多词查询正确，作为通用网页后端 |
| **酷安** | ⚠️ 站内搜索不可用（网页 404 / API 403），**经 360 索引可达** —— 实测搜到「小米官方线刷工具 miflash 报错的解决方法」，正文含 `can not found file flash_all_lock.bat` |
| **百度贴吧** | ⚠️ 直连 403，**经 360 索引可达** —— 实测搜到「【MTK常见错误指令】SP Flash Tool mtk手机各错误的含义及解决【刷机吧】」 |
| **知乎** | ⚠️ 直连 403 / API 400，**经 360 索引可达**（收录较少） |
| **B 站** | ✅ 搜索 API 可用，但**必须先拿 `buvid3` cookie**（否则 HTTP 412）；只能读标题与简介，读不了视频内容 |
| XDA | ❌ 直连 403（Cloudflare），且 360 几乎没收录。后端已实现（先试直连、失败退站内搜索），但本机拿不到 |
| Bing 文本检索 | ❌ **不可用** —— 多词查询被截断成第一个词（查 `SP Flash Tool ERROR 4032` 返回"SP Group"） |
| 百度 / DuckDuckGo / Google / Ecosia / Brave | ❌ 验证码 / 不可达 / 只是 Bing 代理 |

> **为什么最初只有 GitHub**：第一版写完时它是唯一实测能用的后端。后来逐个重测才发现
> 360 能用、CSDN 有自己的接口、B 站补个 cookie 就能用、酷安和贴吧可以借 360 的索引绕过去。

**后端与默认开关**（设置页里可勾选，带简短说明）：

| 后端 | 默认 | 说明 | 通道 |
|---|---|---|---|
| `github` | ✅ | 报错原文最准 | GitHub API |
| `csdn` | ✅ | 技术博客多 | **CSDN 自己的 API** |
| `web360` | ✅ | 通用网页，覆盖面最广 | 360 |
| `coolapk` | ✅ | 酷安，小米社区经验 | 360 索引 |
| `tieba` | ✅ | 刷机吧 / MTK吧 | 360 索引 |
| `zhihu` | ✅ | 偏原理 | 360 索引 |
| `bilibili` | ✅ | 只有标题简介 | B站 API |
| `xda` | ⬜ | 常被墙 | 直连→360 |
| `bing` | ⬜ | 多词查询不准 | Bing |

**结果按后端交错合并**，不是一个后端吃满名额 —— 否则加了后端也等于没加（GitHub 会占满全部
6 个位置）。任一后端抛异常也不会拖垮整次查询。

### 只保留和安卓刷机有关的结果（三层过滤）

最初的结果里混了大量无关内容。实测 `SP Flash Tool 4032` 返回过：

```
github.com/mkdocs/mkdocs/issues/4032        ← 只是数字 4032 相同
github.com/zed-industries/zed/issues/35948  ← 无关
[视频] 天际线2更新以后的红绿灯新模组 traffic tool essentials   ← 只是含 "tool"
[视频] 拆包Flash游戏导出素材，反编译以及网站下载              ← "flash" 当成动画工具了
```

三层过滤，逐层收紧：

| 层 | 时机 | 规则 |
|---|---|---|
| **1. 主题过滤** | 搜索后、展示前 | 标题/摘要必须含**明确的刷机术语**（`刷机`/`线刷`/`救砖`/`fastboot`/`bootloader`/`twrp`/`brom`/`9008`/`sahara`/`qfil`/`miflash`/`sp flash tool`/`mtk`/`小米`…），或含报错短语本身。**"flash" 单独不算**——它匹配 Flash 游戏和 Adobe Flash |
| **2. 正文过滤** | 抓取后、送模型前 | 正文必须**真正包含报错短语**（或其中连续 3 词以上），否则丢弃 |
| **3. 引用过滤** | 模型返回后 | 回答里没有 `[编号]` 引用就**不采纳** |

再加一层**查询语境**：短语后面附加刷机领域词（`"ERROR 4032" 刷机 MTK`），
因为裸短语会把搜索引擎带偏。但**语境词不参与"正文必须包含"的判断** —— 没有哪个页面会
把 `Antirollback check error 刷机` 连在一起写，带上它会把正确来源全部否掉（实测踩过）。

修复前后对比（同一查询 `Antirollback check error`）：

```
修复前:  [1] Add durable break-glass approvals          ← 无关
        [4] [视频] error and uncertainty                ← 无关
        [5] [codex] ASAP security fixes for proofs      ← 无关
        [7] [视频] 测试error408                          ← 无关

修复后:  [1] (csdn)     小米线刷「Antirollback check error」问题解决方案   ← 完全对口
        [2] (bilibili) [视频] miflash线刷常见报错
        [3] (csdn)     Erasing boot FAILED刷机报错？Fastboot与MiFlash排查全攻略
        [4] (bilibili) [视频] 小米手机刷机问题大全及解决办法 | miflash报错
        [5] (csdn)     保姆级教程：用MiFlash和Fastboot给Redmi K50刷入Pixel Experience GSI
        [7] (csdn)     小米Note 3救砖实战：详解高通9008模式原理与MIUI降级操作
```

**后端是并行查询的**：7 个后端串行要 10-20 秒（等于每个站点延迟之和），并行后约等于最慢的
那一个（实测 8 条结果 1.4-7 秒）。

### ⚠️ 360 的频率限制（重要）

酷安 / 贴吧 / 知乎 / XDA **都走 360 的索引**（它们自己的搜索接口要么 403 要么 404）。
360 对自动化查询有频率限制，触发后返回「**访问异常页面**」+ 验证码，而不是结果。

我测试时反复查询把它触发了，**这一点必须说清楚**：

- 触发后这几个后端会**静默返回空**，看起来就像"这个报错没搜到" —— 这会误导人
- 所以加了**识别**：检测到验证码页就记下时间，并在联网查询的失败说明里写明
  「搜索引擎触发了频率限制，Coolapk / 贴吧 / 知乎 依赖它的索引，过几分钟再试」
- 请求之间加了 0.7 秒最小间隔并**串行化**，减少触发概率
- **CSDN 和 GitHub、B站 不受影响**（各有自己的接口）

正常使用（偶尔查一次）不容易触发；连续快速查询会。

**搜索引擎自带页面会被过滤**：360 会把自家的 AI 回答页（`ai.so.com`）和翻译页
（`fanyi.so.com`）当作结果塞进来；它们没有作者、无法引用、抓取也只能拿到 360 的外壳，直接丢掉。

**来源相关性过滤**在这里更关键：中文页面里无关内容不少，只有**正文真正包含报错短语**的才会
送给模型。实测"搜到 8 条、最终采用 1 条"是常态。

GitHub 的 issue/PR 走 API 抓正文（`github.com` 的 HTML 在本环境被拒，`api.github.com` 可以），
并且**连同评论一起抓**，因为解决办法通常写在评论里而不是正文。

### 一个必须防的坑：循环引用

第一次跑就踩到了：检索报错串会命中**本项目自己的 issue**（因为那个 issue 引用了这些报错
原文），于是新写的 KB 条目会把"自己的 issue"当作权威来源引用。已加 `SOURCE_BLOCKLIST`
硬性排除。

## 一之五、用联网查询补齐知识库

`tools/research_kb.py`：对一批缺失报错联网检索，把**抓到的正文原文**存进
`kb/raw/web/` 作为不可变证据，再生成 wiki 条目，`sources:` 指向该 raw 文件。

```powershell
python tools/research_kb.py --list              # 看目标
python tools/research_kb.py --all --dry-run     # 只检索不写
python tools/research_kb.py --only antirollback # 单条
```

**拒绝写入的规则**：没搜到来源 → 跳过；抓不到正文 → 跳过；模型没引用来源 → 跳过。
宁可留空，不可编造。

### 本次实际结果（8 条目标）

| 报错 | 结果 | 来源数 |
|---|---|---|
| `Antirollback check error` | ✅ 写入 | 1 |
| `Missmatching image and device error` | ✅ 写入 | 3 |
| `FAILED (data transfer failure (Too many links))` | ✅ 写入 | 6 |
| `Error reading sparse file` | ✅ 写入 | 5 |
| `can not found file flash_all_lock.bat` | ✅ 写入 | 1 |
| `press any key to shutdown` | ✅ 写入 | 3 |
| `Not catch checkpoint / flash is not done` | ✅ 写入 | 1 |
| `Length cannot be less than zero` | ⛔ **跳过**（没搜到来源，拒绝编造） | 0 |

**知识库覆盖：8/16 → 15/16**（第 16 条按规则留空）。

> ⚠️ **来源质量参差**。有的来源非常对口（如 `"Too many links" fastboot` 命中的 TWRP
> 线程），有的只是沾边（某个音频 issue 的评论里提到了 antirollback）。所有新条目顶部
> 都有醒目警告：内容来自联网检索 + 模型整理，**未经人工/官方核实**，动手前先读「待确认」
> 并自行核对来源。**我没有逐条人工核实这些内容**，这一点必须说清楚。

## 一之六、检索缺陷修复（先修这个再加内容）

加条目之前先修了检索本身，否则条目越多，"自信地答错"的机会越多。依据是本项目
issue #5 的实测。

| 缺陷 | 修复 |
|---|---|
| IDF 无上限 + 无停用词 → `"the the the"` 拿 **228.6** 分，反超真实关键词 `BROM`（38.6） | 加停用词表（**只含虚词**）+ `MAX_IDF=4.0` + 重复放大 `min(count,3)`→`min(count,2)` |
| **文字检索一道闸门都没有**（图片识别有三道）→ 没覆盖的报错也照常输出 5 条不相关"方案" | 加 `MIN_RELEVANCE` 相关度闸门 + 明确的「没有找到足够相关的条目」分支 |
| `_explain` 把查询词标成「命中关键词」（如 `命中关键词: and`） | 区分「命中关键词」与「文本重合」 |
| 关键词匹配对 `ERROR 2004` / `ERROR: 2004` 标点不敏感 → **照抄真实报错反而分更低** | 加 `loose()`，与 `scanner.py` 的口径对齐 |
| OCR 把 `dm-verity` 读成 `d m-verity`，复合关键词失配 | 加 `squash()` 无分隔符比对（长度 ≥6 才启用） |

**注意**：停用词表**故意不含** `error` / `failed` / `device` 这类领域词。issue 的建议里
包含了它们，但我实测发现去掉后 `Download Fail: Sahara Fail: ...` 不再命中 Sahara 页
（71.8 → 39.2 且排序错误），所以只保留真正的虚词。

### 阈值是量出来的，不是拍的

`MIN_RELEVANCE = 26.0`，来自实测间隔：

```
应命中（19 例，含 OCR 变体）: 34.6 ~ 189.1
不应命中（11 例，未覆盖 + 垃圾）:  0.0 ~  17.2
```

阈值落在 17.2 与 34.6 之间的空隙里。**这个阈值依赖语料规模**（打分用了 IDF），
**批量加条目后必须重新标定** —— `tests/test_kb.py::test_relevance_threshold_sits_in_a_real_gap`
断言的是"间隔存在"而不是具体数值，所以漂移会**报错**而不是悄悄退化成错答案。

> 本次就发生了：加完 7 条后分数整体下移，42.0 的阈值把真阳性也挡掉了，重新标定为 26.0。

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
│  ├─ launcher.py               # PyInstaller 入口（绝对导入；日志/GUI 选择/数据路径）
│  └─ mirecovery/
│     ├─ tkapp.py               # tkinter 界面（主交付物）
│     ├─ app.py                 # Toga 界面（x64 桌面 / Android）
│     ├─ theme.py               # 配色、字体、形象资源路径
│     ├─ kb.py                  # 知识库加载 + 检索引擎
│     ├─ scanner.py             # 日志分析（平台/模式/错误码）
│     ├─ imagefeatures.py       # 图片特征提取（dHash/ZNCC/直方图）
│     ├─ recognize.py           # 画面识别 + 置信度/拒绝策略
│     ├─ ocr.py                 # 文字识别（Windows OCR / Tesseract / RapidOCR / 内置模板）
│     ├─ report.py              # 报告渲染 + 图片全流程（OCR 优先，画面补充）
│     ├─ logsetup.py            # 日志 + 崩溃捕获（含目录回退）
│     ├─ _buildcfg.py           # 构建期 GUI 选择（由 build_exe.py 生成）
│     ├─ data/kb.json           # 构建产物，打进 exe/apk
│     ├─ data/image_refs.json   # 参考图特征库
│     ├─ data/ocr_templates.json # OCR 字形模板（多字号，构建期生成）
│     └─ resources/             # 形象原图 + icon.png/ico + window_icon.png
├─ tests/                       # pytest 测试套件（95 项）
│  ├─ test_scanner.py           #   平台判定（含裸错误码回归）
│  ├─ test_kb.py                #   加载权威性、检索、死链/来源校验
│  ├─ test_recognize.py         #   版本校验、空白拒绝、精度、预筛一致性
│  ├─ test_ocr.py               #   OCR 后端选择、多字号模板、形近字归一化、端到端命中
│  ├─ test_report_and_entrypoints.py  # 报告渲染 + 打包契约
│  └─ test_gui.py               #   tkinter 界面（无显示时跳过）
├─ tools/
│  ├─ spec_common.py            # 四个 spec 共用的数据/隐藏导入/排除清单
│  ├─ build_kb.py               # wiki → kb.json + index.md，含校验
│  ├─ build_ocr_templates.py    # 多字号渲染 OCR 字形模板
│  ├─ build_exe.py              # 一键构建全部 Windows 交付物 + 生成使用说明
│  ├─ build_references.py       # 参考图 → image_refs.json（含真实照片合并）
│  ├─ make_reference_images.py  # 生成合成参考图 + 拍照干扰测试图
│  ├─ benchmark_recognition.py  # 图片识别基准 + 阈值扫描
│  ├─ frozen_selftest.py        # 冻结自检：验证 exe 内各资源可用
│  ├─ make_icon.py              # 由原图生成图标（可移植，支持 --source）
│  ├─ sync_kb.py / .ps1         # 把 kb/ 同步进 ~/.dsh/kb
│  ├─ render_index.py           # 生成 index.md / log.md 行（供 ps1 调用）
│  └─ ci_prepare.py             # CI 打包前的准备步骤
├─ MiRecoveryHelper-tk.spec         # tkinter 单文件 exe（主交付物）
├─ MiRecoveryHelper-tk.onedir.spec  # tkinter 目录版（不依赖 %TEMP%）
├─ MiRecoveryHelper.spec            # Toga 单文件 exe（仅 x64）
├─ MiRecoveryHelper.selftest.spec   # 冻结自检（console）
├─ pyproject.toml               # Briefcase 配置 + pytest 配置
└─ .github/workflows/build.yml  # CI：exe + apk（★ 从未运行过，见 4.7）
```

## 二之二、测试

```powershell
.\.venv\Scripts\python.exe tools\run_tests.py     # 全部（推荐，95 项）
.\.venv\Scripts\python.exe -m pytest -q           # 库 / OCR 部分
.\.venv\Scripts\python.exe -m pytest tests\test_gui.py
```

> **为什么用 `run_tests.py` 而不是直接 `pytest`**：在同一个进程里同时跑 tkinter
> 测试和 OCR 测试，会在**所有用例通过之后**、解释器退出时崩掉（`0xC0000005`）。
> 可复现：`test_gui + test_ocr + test_recognize + test_report` 崩；去掉 GUI 或去掉
> 后面几个就不崩。推测是 Tk 以单线程套间初始化 COM，而 Windows OCR（WinRT）另有
> 套间模型，两者一起析构会出事。
>
> 这是**测试进程**的问题，不是应用的问题：冻结自检在同一个进程里既建 Tk 窗口又做
> OCR，退出码 0；GUI 应用本身运行正常。`run_tests.py` 把 GUI 测试放到独立进程，
> 让套件可靠，同时不掩盖问题。

测试覆盖的是**契约与回归**，不只是"能跑"：

- 打包契约：入口脚本不得用相对导入（否则 exe 启动即崩）；spec 必须共用
  `spec_common`（此前三份 spec 复制配置、漂移两次）；spec 必须声明版本信息；
  不得再用 `os.environ` 这种对产物无效的写法。
- 数据质量：死链、缺 keywords、`sources` 为空。
- 识别安全：接受即必须正确；空白/纯色图必须拒绝；参考库版本不匹配必须拒绝；
  预筛不得改变结论。
- OCR：后端优先级、多字号模板（防止退回单字号导致准确率暴跌）、形近字归一化、
  数字 token 不被改写、端到端命中正确条目。
- 已知缺口用 `xfail(strict=True)` 标注（目前是"知识库无 sources"），补上真实素材
  后会变成 XPASS 并提醒你移除标记。

## 二之三、日志

运行时会写日志（轮转，3 × 1 MB）：

| 平台 | 位置 |
|---|---|
| Windows | `%LOCALAPPDATA%\rec检查喵\logs\app.log` |
| Linux | `~/.local/state/rec检查喵/logs/app.log` |
| macOS | `~/Library/Logs/rec检查喵/app.log` |

首选目录不可写时会依次回退到 `%TEMP%` 和程序所在目录，并把实际路径写进启动失败
提示框。启动失败时还会把完整 traceback 记入日志 —— 之前没有日志，用户只能靠截图
或手抄 traceback 反馈问题。

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

### 4.3 本机未能构建 APK 的原因

APK 是在 CI 里构建的，**本机没有产出 apk**，原因是环境缺三样硬性前置：

| 缺什么 | 影响 |
|---|---|
| JDK 17 | Briefcase 构建 Android 必须有 `java`/`javac`，本机 `java` 不存在 |
| git | `briefcase create` 强制要求 git，本机未安装 |
| 磁盘空间 | Android SDK + NDK + Gradle 需约 10 GB；本机 C: 仅剩约 1 GB，D: 0.1 GB |

exe 路线不受影响，已在本机实际构建并通过冻结自检。

### 4.7 APK 的真实状态

**必须说清楚：APK 从来没有成功构建过，一次都没有。**

- 本机：上面三样前置都缺，装不了（磁盘也不够）。
- CI：`.github/workflows/build.yml` 里的 `android-apk` job **从未运行过**。我无法
  在这里推送仓库、也没有 GitHub 凭据，所以那份 YAML 是**未经验证**的配置。

它已经尽量做对了能做的部分：pin 了 Briefcase 版本、缓存 SDK/NDK/Gradle、
产物存在性检查、失败即报错。但"配置看起来合理"不等于"能出包"—— 首次推送
大概率需要调试（Android SDK 版本、NDK 版本、Chaquopy 与 Python 版本匹配等）。

**要真正拿到 apk，需要以下之一：**

1. 一台有 JDK 17 + git + 约 15 GB 空闲磁盘的机器，然后：
   ```bash
   python -m pip install "briefcase==0.4.5"
   python tools/build_kb.py
   python tools/make_icon.py
   python tools/build_references.py
   briefcase create android
   briefcase build android
   briefcase package android --no-input
   ```
2. 或把仓库推到 GitHub，用 Actions 跑 `android-apk` job 并接受首次可能要修。

**如果你只要桌面版，这个缺口不影响使用**；如果 apk 是硬需求，请按上面任一方式
拿到真实产物，不要把这个仓库里的 CI 当成"已经能出 apk"。

### 4.4 打包踩坑记录（改配置前值得一读）

- **PyInstaller 的入口脚本不能是包内的 `__main__.py`**：它以 `__main__` 执行且
  **没有父包**，`from .app import run` 会直接崩在启动阶段。必须用 `src/launcher.py`
  这类绝对导入的入口。这个错误**导入测试和冻结自检都抓不到**，所以
  `tests/test_report_and_entrypoints.py` 用 `runpy` 复现了 PyInstaller 的执行方式。
- **spec 里写 `os.environ[...]` 对产物无效**：那只是构建进程的环境变量。要影响
  运行时得让值随包一起走（本仓库用生成的 `mirecovery/_buildcfg.py`）。
- **两个 spec 输出同名文件会互相覆盖**：曾经 Toga 版把 tkinter 主交付物覆盖掉，
  而"构建成功"的日志完全看不出来。现在每个 spec 自己命名，构建脚本最后再断言
  主交付物仍然存在。
- **手写的 `使用说明.txt` 会过期**：它曾指向 `MiRecoveryHelper\MiRecoveryHelper.exe`，
  而两个名字都已改。现在由 `build_exe.py` 按实际产物名生成。
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

## 七、v2.2.0 新增：文字识别（OCR）

图片识别从"只认画面类型"升级为"**先读文字，再认画面**"。动机很直接：画面匹配
只能判断"这像 MTK 报错弹窗"，读不出是 `ERROR 4032` 还是 `ERROR 4004`；而 OCR 能
把那行字读出来交给文字检索。实测 5 类典型日志全部命中正确条目（见一之二的表格）。

新增文件：`src/mirecovery/ocr.py`、`tools/build_ocr_templates.py`、
`src/mirecovery/data/ocr_templates.json`、`tests/test_ocr.py`。

### 过程与实测（含两次失败）

1. **先做了纯 Pillow 的模板匹配**（因为 apk 用 Chaquopy，既没有 Tesseract 也没有
   onnxruntime，只能用 Pillow）。第一版把每个字形渲染成**单一字号**的 16×24 模板，
   实测：全字符集 68.7%、数字 91.5%、**4 位错误码整串只有 70.2%**。
2. **定位到根因**：归一化按字形自身墨迹外框缩放，导致字形比例随字号变化 ——
   同一个 `0` 在 64px 与 22px 下相关度只有 **0.759**，而错误字形 `4` 反而拿到 0.943。
   **多字号模板**修好了它：数字 **99.6%**、4 位码 **99.5%**、全字符集 **96.7%**。
3. **但端到端整句仍然只有 2/16**：逐字归一化会抹掉相对大小，`a`↔`b`、`3`↔`J`、
   `2`↔`Z` 混淆。所以内置后端只适合**数字/错误码**，不适合整句。
4. **试了"词表匹配"**（拿知识库关键词当词表做整词比对），实测命中率 **28%**，而且会
   **凭空报出词表里的词**（把不含 qdl 的句子报成 qdl）。会自信编造内容的模块比没有
   更糟，**已删除，没有采用**。
5. **改用 Windows 自带 OCR**（`winsdk`，离线、无需外部程序、与 PowerToys 文字提取
   同一个引擎）：长句可完全正确。发现它**对小图直接返回空**（1× 时 48 个样本有 28 个
   空），加 3× 放大后为 0 个空 —— 所以内置了自动放大。
6. **加形近字归一化**：Windows OCR 会把 `failed` 读成 `fai1ed`、`allowed` 读成
   `a110wed`，直接检索匹配不上。归一化后能匹配，且**纯数字 token 原样保留**，
   绝不改写错误码。

### 后端优先级与限制

| 后端 | 条件 | 质量 | apk |
|---|---|---|---|
| Windows OCR | Windows + `winsdk` | 好 | ✖ |
| Tesseract | `tesseract` + `pytesseract` | 好，支持中文 | ✖ |
| RapidOCR | `rapidocr_onnxruntime` | 好 | ✖ |
| 内置模板 | 总是可用 | 数字好、整句弱 | ✔ |

中文 OCR 在本机**不可用**：引擎报告 `zh-Hans-CN`，但实际识别返回空 —— 推测未安装
中文 OCR 语言包。**未经验证的能力我不写进承诺**。

代价：`winsdk` 让 exe 从 18.0 MB 涨到 **29.5 MB**。

## 八、v2.1.0 修复清单

一次审计发现并修复的问题。每条都附了**实测证据**或回归测试，不是"看着改了"。

### 功能缺陷

| 问题 | 证据 | 修复 |
|---|---|---|
| 裸错误码不触发平台判定：`ERROR 4032` → `platform=unknown`，报告自相矛盾地说"未能判定平台"却给出 MTK 方案 | 实测 5 个错误码全部 unknown | 给 MTK 补数字错误码特征；`tests/test_scanner.py` 加 7 例回归 |
| `KB.load(显式路径)` 读到损坏文件时**静默回退内置库** | 传损坏文件返回 18 条（= 内置库），无任何报错 | 显式路径改为权威：失败即抛 `KBLoadError`；`strict=False` 才回退 |
| 参考库 `feature_version` 完全不校验 | 伪造 v1 库仍被正常加载并给出结论 | 加载时校验版本，不匹配则跳过并给出提示 |
| `_VECTOR_CACHE` 用 `id()` 做键 + 无上限 | `id()` 回收后会复用 → 可能取到别的图的向量；缓存只增不减 | 向量 memo 挂到 `Thumb` 自身，随对象回收 |
| 排除 numpy 使交付版识别慢 7.5× | 实测 19 ms（有 numpy）vs 140 ms（无） | 两级检索（廉价预筛 → 精确 ZNCC）+ `int.bit_count()`：**140 → 42 ms**，精度不变 |
| GUI 提示文字是可编辑内容，污染检索 | 提示文字+真实日志 → signals 多 8 条噪声，置信度 1.0 → 0.63 | 改为真正的 placeholder（灰色、`_get_log()` 排除） |
| 大图识别冻结界面 | 4000×3000 提取耗时 1.83 s，且跑在 UI 线程 | 后台线程 + 队列轮询（`after` 不能跨线程调用）+ JPEG `draft()` 降采样 |
| `rgb_hist` 权重实际是配置值的 3 倍 | `intersection` 对 3 通道拼接直方图可返回 3.0，`similarity` 因此饱和 | 加 `multi_channel_intersection` 归一化；阈值重新扫描定为 0.70 |
| 跨平台命中被硬截断 | `platform_matches + others[:1]` 可能丢掉更相关的跨平台条目 | 改为重排序（平台作 tie-breaker）而非过滤 |

### 数据与内容

| 问题 | 证据 | 修复 |
|---|---|---|
| 3 处 `[[fastboot-unlock-failed]]` 死链 | 该页不存在（真名 `fastboot-unlock-token-verify-failed`） | 修正 4 处；`build_kb.py` 增加死链校验，**有死链即构建失败** |
| 18/18 条目 `sources` 为空，`raw/` 无素材 | 实测 18/18 | 无法凭空修复：`build_kb.py` 现在逐条告警，`Entry` 携带 `sources`，测试用 `xfail(strict=True)` 持续暴露 |
| 无 keywords 的页面无法检索 | — | 已在校验中覆盖（当前 0 条） |

### 打包与交付

| 问题 | 修复 |
|---|---|
| exe **无版本信息**（`VS_VERSION_INFO` 不存在） | `spec_common.version_file()` 生成并写入，版本随 `__version__` |
| `使用说明.txt` 与实际布局不符（指向 `MiRecoveryHelper\...`，实际是 `rec检查喵\`） | 改由 `build_exe.py` 按实际产物名生成 |
| 目录版内层 exe 名与品牌不一致 | 统一为 `rec检查喵.exe` |
| spec 里 `os.environ["MIRECOVERY_GUI"]` 是空操作 | 改为生成 `mirecovery/_buildcfg.py`，值随包一起走 |
| 三份 spec 复制配置，已漂移两次（漏 `image_refs.json`、漏 `tkinter`） | 抽出 `tools/spec_common.py`，四个 spec 共用 |
| Toga 版覆盖 tkinter 主交付物 | 每个 spec 自己命名；构建结束断言主交付物存在 |
| 自检跑的是 `buildcfg=toga`（测错配置） | 自检移到 Toga 构建**之前**；构建结束把 `_buildcfg` 复位 |

### 工程化

| 问题 | 修复 |
|---|---|
| **没有任何测试框架**，只有 4 个手跑脚本 | 迁移为 `tests/`（pytest，74 项），删除重复脚本与遗留调试文件 |
| **完全没有日志**，用户遇错只能贴 traceback | 加 `logsetup.py`：轮转文件日志 + 全局异常捕获 + 目录回退链 + 启动失败提示日志路径 |
| `make_icon.py` 硬编码某台机器的绝对路径 | 改为默认读仓库内原图，支持 `--source` / `RECNEKO_ART_SOURCE` |
| `kb.json` 的 `version` 只是当天日期 | 改为 `日期+内容哈希`，两次同日构建可区分 |
| `report.py` 类型标注松散（`tuple[object, str]`） | 改为 `tuple[Entry \| None, str]` |
| 用 Pillow 已弃用的 `getdata()`（Pillow 14 将移除） | 统一走 `pixel_values()`，优先 `get_flattened_data()` |
| 工具链锁死 Windows 路径 | `build_exe.py` 自行探测解释器；`make_icon.py` 可移植 |

### 仍未解决（不掩饰）

1. **知识库内容无据** —— 18 条全部 `sources: []`。需要真实日志才能修，我造不出来。
2. **图片识别只用合成图验证** —— 参考图与基准图同源，真实准确率未知。需要真机截图。
3. **APK 从未产出** —— 见 4.7。
4. **第三方美术授权** —— 形象图源自社区开源资产库，对外分发前需自行确认授权；
   `build_exe.py --no-art` 可产出不含该图的版本。

## 九、许可

MIT，见 [LICENSE](LICENSE)。

> 第三方角色形象不在此许可范围内，详见 4.7 与「一之三」的版权提醒。
