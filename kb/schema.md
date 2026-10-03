---
title: KB 约定（schema）
updated: 2026-10-02
---

# KB 约定

本目录是团队知识库。人机共写：人往 raw/ 丢素材，agent 按 schema 加工成文、维护 index。

## 目录

- `raw/` 原始素材，**不可变**：任何情况下不得修改或删除（log/现场证据要回溯）
- `wiki/howtos/` 操作手册：症状 → 原因 → 步骤 → 验证
- `wiki/decisions/` 决策记录：背景 → 选项 → 结论 → 后果
- `wiki/postmortems/` 复盘：时间线 → 根因 → 改进项
- `wiki/notes/` 读书摘记/成书笔记：教材、书籍、长文等不成 howto/decision/postmortem 形态的素材
- `index.md` 目录：每篇成文必须挂进对应小节
- `log.md` 操作流水：每次加工追加一行

## 页面规范

- 文件名 kebab-case 英文；frontmatter 必填：`title / tags / keywords / author / created / updated`
- `keywords`: 3~8 个检索关键词（metadata 区块的一部分，人查库与 agent 回溯都靠它）
- `sources`: [raw/...] 原始素材位置；有分片/章节等属性时加 `source-note: 类型｜范围｜分片`（如 `书籍分片｜第一集 18~26 章｜3/49`）
- 读到产出文件时：从 frontmatter `sources` 回溯原始素材位置，需要细节直接回读原文
- 互链用 `[[页面名]]`；**矛盾必须显式化**：新内容与已有条目矛盾时，两个页面都要标注「⚠️ 与 [[对方]] 矛盾」并说明适用环境差异（客户环境经常不同，救火时拿错方案是要出事的）
- 不确定的内容写进页面末尾「待确认」小节，不要编

## 加工流程（两步）

1. **分析**：读 raw 素材，列出关键实体/步骤，对照 wiki 已有条目找出关联与矛盾
2. **生成**：写/更新 wiki 页面 → index.md 挂链接 → log.md 追加一行；raw 原样保留并在 sources 里引用

## 并发与身份

- index.md/log.md **先读后写**：写入前重新读最新文件再追加，写完确认自己的行还在（其他会话可能同时入库）
- author：宿主有登录身份就用；否则本会话第一次写入前问一次，之后记住

## log.md 行格式

```
- YYYY-MM-DD HH:mm <author> <新增|更新|标注矛盾> <wiki 路径> ← <raw 路径>
```

## 自动蒸馏（v0.2+）

- 插件内置自动蒸馏：新入 raw/ 的素材自动入队，由 kb-bot 会话按本 schema 逐个加工（串行）
- log.md 中 author 为 `kb-bot` 的行来自自动队列；交互会话不必重复加工已入队素材（以队列为准）
- 队列台账在 `~/.dsh/dsh-kb/queue.json`（插件运行时状态，不在本库内）
- kb-bot 加工的页面 author 一律 `kb-bot`；人工纠错照常更新页面并把 author 写自己

## 本库的额外约定（小米/红米 Recovery 排错）

- 本库是 **mi-recovery-helper 应用的数据源**：页面在 `wiki/howtos/` 写好后，必须运行
  `python tools/build_kb.py` 重新生成 `src/mirecovery/data/kb.json`，应用才能检索到。
- frontmatter 除 schema 必填项外，本库统一增加 `platform` 字段，取值：
  `mtk` / `qualcomm` / `fastboot` / `recovery` / `avb` / `meta`。
  应用用它做平台判定后的优先级排序，请务必填写。
- `keywords` 是本库检索质量的关键：请把**报错原文**（如 `ERROR 4032`、
  `Sahara Fail`、`not allowed in locked state`）按原样写进去，不要只写中文概括。
- 素材入口：`raw/` 放现场日志、聊天记录、截图说明；加工时在 `sources` 里引用。
