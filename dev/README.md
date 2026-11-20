# dev/ - tests and evaluations of intro-ledger (not part of the Skill runtime)

| file | what |
|---|---|
| `test_all.py` | 38 regression tests (stdlib `unittest`); `python3 dev/test_all.py [-v]` |
| `eval_support.py` | behaviour of the statement-to-source check under controlled word loss, wrong-source, changed-number and overstating-word perturbations on the real abstracts below |
| `make_examples.py` | regenerates `submission/examples/*/out` and `run.txt` from real runs |
| `make_docx.py` | builds a small .docx for tests of inputs |
| `fixtures/arxiv_landslide.json` | 20 public arXiv records on landslide detection / susceptibility (id, year, title, authors, abstract). arXiv metadata is released under CC0; fetched through the public arXiv API |

All own-paper material, drafts and the Chinese example are invented.
