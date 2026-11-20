# Checks (`check` / `build`): what each one tests

Severity: **error** = fix before handing over (build still writes everything, `status` = `partial`); **warn** = fix or justify; **info** = shown with `--all`.

## Statements about other work (every clause is checked against the works its own marker cites)
| Code | Sev | Test |
|---|---|---|
| `unknown_key` | error | a cited key is not in the library |
| `unsupported_statement` | error | IDF-weighted share of the clause's content words found in its best source passage (one sentence or two adjacent ones) < 0.25 |
| `weak_support` | warn | the same share between 0.25 and 0.40 |
| `number_not_in_source` | error | a number the clause asserts (not own-voice) occurs nowhere in the cited text(s) |
| `number_from_other_passage` | warn | the number occurs in the source but not in the passage the clause matches |
| `overstated` | warn | strong wording (always, never, demonstrates, state-of-the-art, outperforms, significantly, best, solves ...) absent from the cited text |
| `limitation_not_in_source` | error | a clause that states a limitation of the cited work overlaps no limitation passage of it (< 0.22) and is not marked as judgement |
| `unverifiable_claim` | warn | a specific claim (number / result / limitation) about a work whose text is title only |
| `citation_padding` | warn | in a clause with 3+ keys, one key's text shares almost nothing with it (< 0.12) |

## Background
`filler` (error in the first sentence, else warn): lexicon of generic openings, English and Chinese ("attracted increasing attention", "with the development of", "plays an important role", "众所周知", "近年来…广泛关注" ...). `importance_only` (paragraph says only that the topic matters), `unbound_claim` (prior-work claim without a citation), `no_concrete_problem` (no problem / limitation sentence backed by a source or number), `thin_background_sources` (fewer than two distinct works).

## Related work
`sequential_summary` (three consecutive sentences each starting with one work and no contrast / comparison word), `no_comparison` (a 3+ sentence paragraph without any comparison wording), `ungrouped` (one paragraph, no group tags), `single_work_paragraph` (info), `group_member_not_cited`, `group_not_in_draft` (info).

## Gap
`no_gap_statement` (error), `gap_not_derived` (error: overlap with a limitation passage of the works cited in the paragraph < 0.15 and no ledger `from`), `gap_unmarked_judgement`, `absence_claim` (warn: "no study", "none of", "尚无", "首次" ...; downgraded to info when hedged and scoped), `gap_tag_unknown`, `ledger_gap_not_in_draft` (info).

## Contributions
`no_contribution` (error), `too_many_contributions` (> 6), `contribution_number_not_in_own_material` (error), `anchor_not_found` (error), `contribution_without_evidence` (error: no resolved anchor and wording match with the own material < 0.30), `overclaim` (error: strong wording without a Table / Fig / N: anchor), `priority_claim` (warn: "first", "to the best of our knowledge"; cannot be verified from the materials), `contribution_without_gap` (info), `contribution_tag_unknown`, `ledger_contribution_not_in_draft`.

## Structure, coverage, metadata
`missing_part` (error: background / related / gap / contribution), `length` (outside 70-140% of the task's length hint), `recent_work_not_cited` (library entries within two years of the newest, uncited), `uncited_library_entries` (info), `duplicate_entries_cited` (the same work under two keys), `metadata_missing` (warn when authors / title / year / venue lacking, else info), `metadata_structure` (year range, page order, ISBN / ISSN check digits ...).

## Measured behaviour (development data, not an evaluation of real model output)
`dev/eval_support.py`: 20 real arXiv abstracts on landslide detection (public metadata); simulated paraphrase = a share of each sentence's content words replaced by words absent from the abstract (so synonyms are never recognised):

| statement vs its own source | supported (>= 0.40) | weak | unsupported |
|---|---|---|---|
| 0% / 20% of content words replaced | 100% / 100% | 0 | 0 |
| 40% replaced | 92% | 5% | 1% |
| 60% replaced | 58% | 29% | 11% |
| a sentence of ANOTHER abstract of the same topic, cited to this one | 1% | 6% | 92% |

A changed number was detected in 23 of 25 cases (the two misses: the new number occurs in the matching passage); an added overstating word ("always", ...) in 160 of 178. Real paraphrases replace words by synonyms and reorder, so expect `weak` for faithful but loosely worded sentences: the check is a screen, `evidence_table.csv` shows the closest source passage for every cited clause so a person can confirm. It does not read meaning, only shared content words.
