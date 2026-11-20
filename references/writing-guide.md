# Writing guide: paragraph recipes and the failure patterns the checks target

## Background (one to two paragraphs)
1. Thread: what the field does, narrowed to the task of this paper, with the numbers or settings that define it (cited).
2. Tension: where the thread stalls (a limitation, a trade-off, a conflict between findings), each side cited.
3. Handover: one sentence naming the open problem this paper takes (leads into the gap).
Bad: "In recent years, X has attracted increasing attention. X plays an important role in many fields." Good: "SAR can provide measurements independent of weather [A], yet optical images gave 99.20% overall accuracy where SAR CNNs reached beyond 94% [B]: choosing a sensor trades accuracy against availability."

## Related work (one paragraph per group)
topic sentence naming the dimension -> works compared on it (what each chose and what it cost) -> sentence on what the group leaves open.
Bad: "Smith et al. proposed A [1]. Lee et al. proposed B [2]. Wang et al. proposed C [3]." Good: "Methods differ in where they spend labels: A [1] and B [2] train per region, whereas C [3] pre-trains once and adapts, at the cost of a large model."
For each work state: setting (data, task), what it found (with its number), its condition or limit. Convert findings, not adjectives.

## Gap
"Three limitations stand out: L1 [A]; L2 [B]; L3 [C]. We argue that D is missing." Each Li quotes (ledger) a limitation of a cited work; the final sentence says what follows, marked as judgement if the sources do not state it.

## Contributions
Numbered statements, each = what was built / shown + the number or figure that backs it, in the paper's own words and scale. No contribution without an anchor. Map each to the gap it answers.

## Failure patterns of unassisted drafts and the check that catches each
| Pattern | Check |
|---|---|
| generic opening / importance-only paragraph | `filler`, `importance_only` |
| chain of one-sentence summaries | `sequential_summary`, `no_comparison`, `ungrouped` |
| number copied wrongly / invented | `number_not_in_source`, `number_from_other_passage` |
| sentence not in the cited paper | `unsupported_statement`, `weak_support`, `citation_padding` |
| "may" -> "does", "on this dataset" -> general | `overstated` |
| gap not from the cited literature | `gap_not_derived`, `limitation_not_in_source` |
| "no study has ..." | `absence_claim` |
| contribution not backed by results | `contribution_without_evidence`, `contribution_number_not_in_own_material`, `overclaim` |
| invented reference / wrong metadata | `unknown_key`, `metadata_*`, `build --online` |
| recent work ignored, one work under two keys | `recent_work_not_cited`, `duplicate_entries_cited` |
