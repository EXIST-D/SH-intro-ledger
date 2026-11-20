# intro-ledger · 引言与相关工作写作（立得住 · 分得清 · 说得实 · 对得上）

面向「写作08｜引言与相关工作写作」：**文字由模型写，「站不站得住」由脚本核对**。作者自己的材料（草稿、结果、图表、数字）和文献库（摘要或原文）被读成一本「证据账」；模型写出的初稿逐句与账对照：每条转述他人工作的陈述对照所引文献的文本，每个研究空白对照它所引文献的局限，每条贡献对照作者自己的章节、图表和数字；再检出空洞开头、逐篇摘要拼接、无依据的“尚无研究”、未引用的近期工作和元数据缺口。通过检查后生成论文文本（md / docx / tex）、参考文献、证据表和 `result.json`。

> 文中数字都来自开发自测（20 篇公开 arXiv 摘要 + 自造稿件），**不是平台成绩**；没有跑过 DeepSeek 官方 Harness，也没有做过「不加载 Skill 的基础 Agent」对照，因此不宣称相对基线的提升。

## 对应题面的四个问题
| 题面问题 | 做法 | 自查手段 |
|---|---|---|
| 立得住 | 背景必须落在具体研究脉络与未解决问题上：检出“近年来…受到广泛关注 / 随着…的发展 / 起着重要作用 / 众所周知”等空转句（首句为错误）、只讲重要性的段落、无引用的断言、没有任何具体问题的背景 | `filler`、`importance_only`、`unbound_claim`、`no_concrete_problem` |
| 分得清 | 相关工作按问题 / 路线 / 数据分组（账本里写分组、维度、比较轴）；检出连续三句各摘要一篇而不比较、整段不含比较措辞、不分组；一句多引时**每个子句只对照自己那个标记所引的文献** | `sequential_summary`、`no_comparison`、`ungrouped`、逐子句 `evidence_table` |
| 说得实 | 研究空白必须从已引文献的局限推出：账本里的 `claim … kind: limitation` 必须附**逐字引文**（不在原文里就被拒绝），空白与这些局限的词汇重合被检；纯作者判断须写明“我们认为”；“尚无研究”要求限定范围并列入人工确认 | `gap_not_derived`、`limitation_not_in_source`、`absence_claim` |
| 对得上 | 每条贡献绑定作者自己材料里的证据锚点（章节 / 图 / 表 / 数字 / 逐字句），贡献里的数字必须出现在自己的结果里，“最优 / 显著 / 首次”没有对比证据就是错误；引用元数据来自文献库，`--online` 再用 Crossref / arXiv 核对 | `contribution_without_evidence`、`contribution_number_not_in_own_material`、`overclaim`、`unknown_key`、`build --online` |

## 目录
```
SKILL.md                         Agent 入口：何时用、九个步骤、账本块、写作规则、异常处理
README.md                        本文件
scripts/iw.py                    命令行：run / show / ingest / check / build
scripts/evidence.py              证据层：来源候选句、逐字引文核对、IDF 加权支持度、读取作者自己的材料、锚点解析、摘要补全（arXiv / Crossref / OpenAlex）
scripts/lint.py                  初稿解析（部分 / 段落 / 句子 / 标签 / 引文键）与词表（空话、比较、绝对化、判断标记）
scripts/docxw.py                 标准库写 .docx
scripts/bib.py, fmt.py, cite.py, dedupe.py, verify.py   文献库解析、GB/T 7714-2015 / APA 7 / IEEE / Vancouver 格式化、重复条目、结构与在线核验
scripts/segment.py, nlib.py, parse_pdf.py   读取 md / txt / tex / docx / pdf、分句、数字与线索词
references/                      初稿与账本格式、全部检查项与实测、写作指南与常见失败模式
examples/                        真实运行：9 篇公开 arXiv 记录 + 虚构的作者论文；中文内联 JSON 案例
GITHUB_URL.txt                   作品的 GitHub 公开链接
dev/ （仅仓库）                  38 个回归测试、支持度评测、示例生成脚本、20 篇 arXiv 摘要的测试数据
```

## 依赖与安装
- Python 3.9+，只用标准库（已在系统 Python 3.9.6 上跑通）。PDF 输入需要环境里有 `pymupdf`、`pdfplumber` 或 `pypdf` 之一；`--online` 需要能访问 arxiv.org、api.crossref.org、api.openalex.org（只发送 DOI / arXiv 号 / 标题，不发送稿件；没有网络时两次失败即停并如实说明）。
- 输入：`/input/case.json` + `task.md`（语言、字数、引文格式从中读取），作者材料（`.docx .md .tex .txt .pdf` 或 case 里的文本字段），文献库（`.bib .ris .enw .json` CSL、CNKI / NoteExpress 导出、case 里内联的记录列表），可选的来源文献原文。

## 使用步骤
```bash
python3 scripts/iw.py run --case /input/case.json --out out --online      # 证据简报 out/brief.md
python3 scripts/iw.py ingest out/.work ledger.txt                         # claim / group / gap / contribution / meta（逐字引文与锚点在此核验）
python3 scripts/iw.py check  out/.work draft.md                           # 逐句核对 + 结构检查
python3 scripts/iw.py build  out/.work draft.md --out out --style gbt7714 # 论文文本 + 参考文献 + 证据表 + result.json
```
初稿用 Markdown，引用写成 `[@key]`，用不占位的标签 `<!--gap:G1-->`、`<!--contrib:C1-->` 把空白与贡献句绑定到账本；格式见 `references/draft-and-ledger.md`。

## 输出
`intro.md` / `intro.docx` / `intro.tex`（键保留为 `\cite`）、`references.<style>.txt/.bib/.ris`、`evidence_table.csv/json`（每个被引子句：状态、重合度、数字是否出现、最接近的原文段落；空白→被引局限；贡献→自己的证据）、`traceability.md`、`review_checklist.md`、`result.json`（按 `output_contract` 的字段填充，推导不出的置 `null` 并列在 `_meta.unfilled_fields`；有错误未解决时 `status` 为 `partial`）。

## 实测（开发自测，不是平台成绩）
| 项 | 结果 |
|---|---|
| 回归测试 | `python3 dev/test_all.py`：38 个测试通过：逐字引文核对、数字（含紧邻汉字的数字）、锚点各形式、初稿部分 / 标签 / 子句解析、植入缺陷（空话、数字、未知键、无依据的空白、绝对化、虚报贡献…）全部被检出、好稿无错误、账本拒绝非逐字引文、中文内联案例、来源文档匹配、离线 / arXiv 核验（含模拟服务） |
| 支持度检查（20 篇真实 arXiv 摘要，模拟转述） | 忠实陈述：词汇替换 0 / 20 / 40 / 60% 时判为“支持”的比例 100 / 100 / 92 / 58%；把**另一篇同主题摘要**的句子挂到本篇上：92% 判为不支持、98% 至少告警；改动一个数字：25 例检出 23；加入“always”等强化词：178 例检出 160。模拟转述只替换词，不是真实模型改写，**真实改写的同义替换会让检查偏向告警**；阈值在同一批数据上定，无基线对照 |
| 在线核验 | arXiv 记录：正确 → verified；改年份与题名 → mismatch（指出差异）；无网络 2 次失败即停（均有测试）。Crossref 路径沿用写作04 的实测：正确 DOI verified、改年份 mismatch、伪造 DOI not_found |
| 示例 | `examples/landslide`：第一稿 5 个错误 / 6 个警告 → 修订稿 0 个错误、1 个警告（近期文献未引）；`examples/zh`：中文内联案例 |

## 限制（如实写在这里）
- 支持度是**词汇重合**（IDF 加权）的筛查，不理解语义：忠实但换了说法的句子可能被判“弱”，措辞相近但意思相反的句子可能被判“支持”（否定词与限定强度只做强化词与数字的核对）；`evidence_table.csv` 给出最接近的原文段落供人工确认。
- 只能核对材料里有的文本：只有题名的条目只能“引来说明存在”，不能支持具体结论；没有作者自己的材料时贡献无法核对；不会去检索新文献，也无法证明“尚无研究”。
- 不判断分组是否“合理”，只检查是否分组、是否比较、成员是否被引用；不检查文笔与期刊格式；中文分句与词汇重合用字二元组，对专业术语较多的文本更可靠。
- 没有 Word / LibreOffice 渲染验证 `.docx`，只验证了 XML 可解析；PDF 读取依赖环境里的 PDF 库。

## 方法说明
1. **证据层**：每个来源的文本 = 题名 + 摘要（+ 原文）；候选证据句按线索词分为问题 / 路线 / 数据 / 结果 / 局限；账本里的每条 `claim` 的逐字引文必须在来源里（忽略大小写、空白、连字符、标点；`...` 可跳词），陈述里的数字必须在来源里。
2. **对照**：句子（或带自己标记的子句）与来源句 / 相邻两句的 IDF 加权内容词重合；IDF 在文献库 + 自己材料上计算，所以领域公共词（如“landslide”）权重低。
3. **空白与贡献**：空白句与被引文献的局限句重合（或账本 `from`）才算推导成立；贡献句的数字必须在自己材料中，锚点逐个解析。
4. **写作与核对分离**：脚本从不替你写句子，也不静默改写；`build` 只做标记转换（编号按首次出现，著者-年用叙述式 / 括号式）、标签清理、格式化参考文献，并把未解决的问题列入 `review_checklist.md` 与 `result.json`。

## 复现
`python3 dev/test_all.py`；`python3 dev/eval_support.py`；`python3 dev/make_examples.py`（用真实命令重新生成示例）。
