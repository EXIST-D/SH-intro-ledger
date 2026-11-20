# Draft format and ledger blocks

## Draft (`draft.md`)
Markdown. Headings name the parts (`## 1 Introduction`, `## 2 Related Work`, `## Research gap and contributions`, or Chinese 引言 / 相关工作 / 研究空白 / 本文贡献); several parts may share one heading. Paragraphs are separated by blank lines.

| Element | Syntax | Meaning |
|---|---|---|
| citation | `[@key]`, `[@a; @b]`, `[@key, p. 3]`; LaTeX `\cite{a,b}` also read | keys are the library keys printed by `run` / `show`; renumbered (or turned into author-year) by `build` |
| part tag | `<!--part:background\|related\|gap\|contribution\|organization-->` first in a paragraph | the part of the introduction the paragraph belongs to; otherwise the heading, then wording cues decide |
| group tag | `<!--group:G1-->` first in a related-work paragraph | the ledger group the paragraph presents |
| gap tag | `<!--gap:G1-->` right after the sentence that states ledger gap G1 | binds the sentence to its derivation |
| contribution tag | `<!--contrib:C1-->` right after the statement (a tag ends a statement even inside a longer sentence, so `A <!--contrib:C1-->; B <!--contrib:C2-->.` is two statements) | binds the statement to its evidence anchors |

Tags and citation markers disappear from `intro.md` / `.docx`; `intro.tex` keeps the keys as `\cite{}`.

## Ledger blocks (`ingest W FILE|-`)
A block starts with `=== kind target` followed by `key: value` lines (a value may continue on the next lines). Re-ingesting the same block replaces it. Exit code 2 when something was rejected; the reason is printed.

| Block | Keys | Verified by `ingest` |
|---|---|---|
| `=== claim KEY` | `kind` (problem route data result limitation scope), `text` (your wording), `quote` (verbatim from the source text) | the quote occurs in the source (case, spacing, hyphenation and punctuation ignored; `...` may skip words; at least 12 letters); every number in `text` occurs in the source |
| `=== group G1` | `title`, `dimension`, `members`, `axes`, `takeaway` | all members are library keys, at least two |
| `=== gap G1` | `type` (limitation conflict uncovered judgement), `statement`, `from` (claim ids `key:kind` or library keys) | a non-judgement gap needs `from`; claim ids must exist; a bare key needs a limitation statement in its text |
| `=== contribution C1` | `statement`, `evidence` (anchors separated by ` \| ` or lines), `addresses` (gap ids), `scope` | every anchor is resolved against the own material (below) |
| `=== meta KEY` | `title year authors doi container volume issue pages publisher abstract` | corrects a record (marks it corrected); an abstract added here becomes citable text |

Anchors: `Table 2`, `Fig. 3` / `Figure 3` (a caption line or a reference in the text), `图3`, `表2`, `Sec: Method` (a heading), `N: 0.812` (a number occurring in the own material), `Q: "verbatim sentence"` (occurs in the own material).

## Inputs
`run --case /input/case.json` reads: `task.md` (language, length "约800字" / "800 words", style GB/T / APA / IEEE / Vancouver), file paths named in the case, every file in the case folder (up to 3 levels), long text fields (own material), and lists of records with `title` + (`abstract` | `authors` | `doi`) as inline library entries. Files: library `.bib .bibtex .ris .enw .nbib .json` (CSL) and CNKI / NoteExpress `.txt`; own material `.docx .md .tex .txt .pdf`; source documents (PDF / text of cited papers) through `--source` or a folder / key named literature / references / sources, matched to records by title. `--own`, `--lib`, `--source` override the classification.
