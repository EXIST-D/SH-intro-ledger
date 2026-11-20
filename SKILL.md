---
name: intro-ledger
description: Write the introduction and related work of a research paper (English or Chinese) so that every statement about other work, every research gap and every contribution is bound to evidence. Reads the author's own material (draft, results, figures, tables) and the literature library (BibTeX, RIS, EndNote, CNKI, CSL-JSON, inline JSON, abstracts or source PDFs), then checks your draft - each statement against the text of the work it cites, each gap against the limitations of the works it cites, each contribution against the author's own sections, figures, tables and numbers - and flags filler openings, paper-by-paper summaries, unsupported "no study" claims, uncited recent work and weak metadata. Builds the paper text (md / docx / tex), the reference list (GB/T 7714-2015, APA 7, IEEE, Vancouver), an evidence table and result.json. Use for "write the introduction", "organise related work", "derive the research gap", "state the contributions", "add citations", "check my introduction". Python 3.9+ standard library only.
---

# intro-ledger

You write; the ledger keeps what the writing rests on and checks it. Basic assistants fail the same ways: an opening that says the topic is "attracting increasing attention", related work as a chain of one-sentence summaries, numbers that drift from the cited paper, a research gap that is not derived from anything cited, contributions that claim more than the results show. `scripts/iw.py` makes each of these checkable, so you can fix them before the text is handed over.

Not for: finding new literature (it never adds a reference that is not in the materials), peer review, methods / experiments sections.

```bash
S=/skills/weekly-skill/scripts/iw.py      # or the scripts/ folder next to this SKILL.md
```
Budget (64 requests, 900 s): `run` (1), your ledger + draft (1-2 writes), `check` (1-3), `build` (1). Do not retype what the scripts print.

## Procedure

1. **Read the task** (`/input/task.md`, `/input/case.json`): language, length, citation style, venue, what is asked (whole introduction, only related work, only contributions ...). The task wording beats every default below.
2. **Gather evidence in one call:**
   ```bash
   python3 $S run --case /input/case.json --out /app/output --online
   ```
   (or `run --own own.md --lib refs.bib [--source paper.pdf ...] --out /app/output`). It classifies the files, reads the own material (sections, figures / tables, numbers), the library (abstracts; with `--online`, missing abstracts are fetched by DOI / arXiv id from arXiv, Crossref or OpenAlex: only the identifier is sent), matches source documents to records, and prints `brief.md`: task, own results, library table with text availability, and verbatim evidence sentences per source (problem / route / data / result / limitation). **Read it all**; `show W --entry KEY --full` prints one source's text, `show W --own` the own material.
3. **Plan before you write.** From the brief decide (a) the research thread of the background and the concrete unresolved problem, (b) 2-4 groups for related work with a comparison dimension each, (c) the gap: which cited limitations it comes from, (d) the contributions: which figure / table / number backs each. Write this as ledger blocks (below) — the ingest step verifies every quote and anchor and rejects what is not in the materials.
4. **Record the ledger** (optional but it is what makes the result checkable; syntax in `references/draft-and-ledger.md`):
   ```
   === claim chen2023
   kind: limitation            # problem | route | data | result | limitation | scope
   text: how factor selection changes ML / DL accuracy is unclear            # your wording
   quote: "the effects of factor selection ... on the prediction accuracy of ML and DL models are unclear"   # VERBATIM from the source
   === group G1
   title: Input modality
   dimension: sensor input
   members: nava2021, boehm2022, ganerd2023
   takeaway: optical is more accurate, SAR works under cloud, fusion helps
   === gap G1
   type: limitation            # limitation | conflict | uncovered | judgement
   statement: SAR needs expert pre-processing, global models overfit, input-selection effects are unclear
   from: boehm2022:limitation, ganerd2023:limitation, chen2023:limitation
   === contribution C1
   statement: a lightweight transfer model with 4.1 million parameters
   evidence: Sec: Method | N: 4.1 | Table 1 | Fig. 3 | Q: "verbatim sentence from the own material"
   addresses: G1
   ```
   `python3 $S ingest /app/output/.work ledger.txt` (rejections are printed with the reason: a quote that is not verbatim, a number the source does not contain, an unknown key, an anchor that does not exist).
5. **Write the draft** (Markdown, `draft.md`): headings per part; citations as `[@key]` or `[@a; @b]` using library keys only; tags that cost nothing in the final text: `<!--part:background-->` first in a paragraph, `<!--group:G1-->` first in a related-work paragraph, `<!--gap:G1-->` right after the gap sentence, `<!--contrib:C1-->` right after each contribution. Rules of writing are below.
6. **Check and repair:** `python3 $S check /app/output/.work draft.md` prints errors (fix them), warnings (fix or justify) and the evidence status of every cited sentence (`supported | weak | unsupported | number_mismatch | unverifiable`). Rewrite from the source, not from memory; re-run until no error is left. `--all` also shows info items.
7. **Build:** `python3 $S build /app/output/.work draft.md --out /app/output [--style gbt7714|apa7|ieee|vancouver] [--online]` writes `intro.md`, `intro.docx`, `intro.tex` (keys kept as `\cite`), `references.<style>.txt/.bib/.ris`, `evidence_table.csv/json`, `traceability.md`, `review_checklist.md`, `result.json`. `--online` verifies the cited references (Crossref / arXiv) and lists mismatches. Default style: the task's, else IEEE (Chinese: GB/T 7714-2015).
8. **Fill the contract.** `result.json` takes its fields from the case's `output_contract`; those it can derive are filled (manuscript / sources / boundaries ...), others are `null` and listed in `_meta.unfilled_fields` and on the console as `UNFILLED`. Put your own content for them in `answers.json` (`{"field": value}`) and run `build ... --answers answers.json`. Never leave a field out, never invent its content.
9. **Before you stop:** no `OPEN ERROR` line (or each one explained in `answers.json` / the review list); every priority claim ("first") and absence claim ("no study") confirmed or removed; `status` is `partial` whenever the checks still show errors — say so in your final message instead of calling the text finished.

## Rules of writing that decide quality

- **Background that stands.** Open with the concrete research thread and the specific problem that is still unsolved, each bound to a source or a number. Never open with "in recent years X has attracted increasing attention", "with the development of", "plays an important role", "近年来…受到广泛关注" (`filler` is an error in the first sentence). A paragraph that only says the topic is important is flagged.
- **Related work that separates.** Group by problem, method route or data / evaluation setting; give each group a topic sentence naming the dimension, compare the works on it (whereas, in contrast, both, at the cost of ...), and end with what the group leaves open. Three sentences in a row that each summarise one work are flagged (`sequential_summary`). Every statement about a work carries its own marker; with several markers in one sentence each clause is checked against its own source.
- **Paraphrase safely.** Keep the numbers, scope, conditions and hedges of the source; do not turn "may" into "does" or "improves on this dataset" into "improves". A number you write must occur in the work you cite for it (and in the passage you paraphrase). Cite a title-only entry for existence ("X has been applied to Y"), never for a finding.
- **A gap that is derived.** State the gap from limitations of works you cited in the same paragraph, quote them in the ledger (`claim … kind: limitation`), and say how the gap follows. A gap that is your own judgement is allowed if the sentence says so ("we argue that ...", "我们认为"). "No study has ..." needs a scope (field, setting, period) and a search; the materials cannot prove absence, so it is listed for confirmation.
- **Contributions that match.** One sentence per contribution, each tagged and anchored to the own material (Sec / Fig / Table / N: number / Q: quote). Numbers in a contribution must occur in the own material; "state-of-the-art", "outperforms", "significantly", "robust", "first" need an anchor that shows the comparison (a table, figure or number) and are otherwise errors; priority claims always go to human confirmation. Say what each contribution answers (`addresses: G1`).
- **Coverage.** Cite what the library holds and the task makes relevant: recent work that stays uncited is flagged; groups list their members; the same work under two keys is flagged. Do not cite what is not in the library; if a needed source is missing, write it into the review list as a material gap.
- **Language and form.** Write in the task's language; keep terminology constant; Chinese: use full-width punctuation and GB/T 7714-2015 numbering; numeric citations are renumbered by first appearance at build time.

## Exceptions

| Situation | Do |
|---|---|
| No own material (results / draft) | contributions cannot be checked: state them only as the task gives them, mark every one `contribution_not_evidenced`, say so in the final message |
| Library empty or title-only entries | related work cannot rest on findings: write only what the own material and the task state, cite for existence only, list the gap in the review list; try `run --online` for abstracts |
| Source PDFs supplied | pass them as `--source`; they are matched to library records by title, and `quote:` may then come from the full text; without `pymupdf`/`pdfplumber`/`pypdf` PDF reading fails with a message: use abstracts instead |
| Case lists records inline in `case.json` | read automatically (title, authors, year, venue, doi, abstract) |
| Citation style unknown / venue format unknown | default to IEEE (zh: GB/T 7714-2015), say which style was used |
| Key in the draft not in the library (`unknown_key`) | replace it with a library key or remove the sentence; never create a reference |
| Quote rejected | copy the sentence from `brief.md` / `show --entry KEY --full` exactly; `...` may skip words |
| Check says `weak` for a faithful paraphrase | the check is lexical (shared content words, IDF-weighted); keep the technical terms of the source in your sentence or justify the warning in the review list |
| No network | `--online` gives up after two failures and says so; references stay `unchecked` and are reported as such |

More: `references/draft-and-ledger.md` (formats), `references/checks.md` (every check, thresholds, measured behaviour), `references/writing-guide.md` (paragraph recipes, failure patterns), `examples/` (a real run: library of 9 public arXiv records, invented own paper; a Chinese case). Example outputs are examples, not results of any evaluation case.
