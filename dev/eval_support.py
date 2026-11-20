#!/usr/bin/env python3
"""eval_support.py - how well does the statement-to-source check separate faithful statements from unfaithful ones?

Data: 20 real arXiv abstracts on landslide detection / susceptibility (public metadata, CC0) in dev/fixtures/arxiv_landslide.json.
Faithful statements are SIMULATED paraphrases: a sentence of an abstract with a share (0 / 20 / 40 / 60 %) of its content words replaced by words that do not occur in the abstract
(so synonyms are never recognised). Unfaithful statements: (a) a sentence of ANOTHER abstract of the same topic cited to this one, (b) a faithful statement with one number changed,
(c) a faithful statement with an overstating word added ("always", "significantly outperforms ...").
This is not an evaluation on real model paraphrases: it measures the check's behaviour under controlled word loss, no more.
Usage: python3 dev/eval_support.py
"""
import json
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, next(p for p in (os.path.join(HERE, "..", "submission", "scripts"), os.path.join(HERE, "..", "scripts")) if os.path.isdir(p)))
import evidence as ev  # noqa: E402
import lint  # noqa: E402
import nlib  # noqa: E402

SUP_OK, SUP_WEAK = 0.40, 0.25
D = json.load(open(os.path.join(HERE, "fixtures", "arxiv_landslide.json"), encoding="utf-8"))
texts = [d["title"] + ". " + d["abstract"] for d in D]
idf = ev.Idf(texts)
rng = random.Random(3)
vocab = sorted({w for t in texts for w in re.findall(r"[a-z]{5,}", t.lower())})


def paraphrase(sent, own_text, rate):
    own = set(re.findall(r"[a-z]{4,}", own_text.lower()))
    pool = [w for w in vocab if w not in own]
    out = []
    for w in sent.split():
        core = re.sub(r"[^A-Za-z]", "", w)
        if len(core) >= 5 and rng.random() < rate:
            out.append(rng.choice(pool))
        else:
            out.append(w)
    return " ".join(out)


def status(sc):
    return "supported" if sc >= SUP_OK else ("weak" if sc >= SUP_WEAK else "unsupported")


def perturb_number(s):
    m = re.search(r"(?<![\w.,:/\\-])\d+(?:\.\d+)?(?![\w.,:/\\%-]|\.\d)", s)  # a standalone number (not part of an identifier, URL, thousands group or scenario name)
    if not m:
        return None
    n = m.group(0)
    new = str(int(float(n)) + 7) if "." not in n else "%.2f" % (float(n) + 0.17)
    return s[:m.start()] + new + s[m.end():]


rows = {}
for rate in (0.0, 0.2, 0.4, 0.6):
    res = {"supported": 0, "weak": 0, "unsupported": 0}
    for i, d in enumerate(D):
        for s in ev.split_sents(d["abstract"]):
            if len(s.split()) < 10:
                continue
            res[status(ev.best_support(paraphrase(s, texts[i], rate), texts[i], idf)[0])] += 1
    rows["faithful, %d%% of content words replaced" % int(rate * 100)] = res
wrong = {"supported": 0, "weak": 0, "unsupported": 0}
num_det = [0, 0]
over_det = [0, 0]
for i, d in enumerate(D):
    for s in ev.split_sents(d["abstract"]):
        if len(s.split()) < 10:
            continue
        j = rng.choice([k for k in range(len(D)) if k != i])
        wrong[status(ev.best_support(s, texts[j], idf)[0])] += 1
        p = perturb_number(s)
        if p:
            sc_, passage = ev.best_support(p, texts[i], idf)
            miss = [x for x in ev.numbers_of(p) if x not in ev.numbers_in_text(texts[i])] or [x for x in ev.numbers_of(p) if x not in ev.numbers_in_text(passage)]
            num_det[1] += 1
            num_det[0] += bool(miss)
        q = "Moreover, this always " + s[0].lower() + s[1:]
        strong = [m.group(0).lower() for m in lint.STRONG_SRC.finditer(q) if m.group(0).lower() not in texts[i].lower()]
        over_det[1] += 1
        over_det[0] += bool(strong)
print("statement vs its own source (simulated paraphrase):")
for k, r in rows.items():
    n = sum(r.values())
    print("  %-46s n=%-4d supported %3d%%  weak %3d%%  unsupported %3d%%" % (k, n, 100 * r["supported"] // n, 100 * r["weak"] // n, 100 * r["unsupported"] // n))
n = sum(wrong.values())
print("statement from ANOTHER abstract of the same topic cited to this one: n=%d supported %d%%  weak %d%%  unsupported %d%%  (flagged weak or worse: %d%%)" % (n, 100 * wrong["supported"] // n, 100 * wrong["weak"] // n, 100 * wrong["unsupported"] // n, 100 * (wrong["weak"] + wrong["unsupported"]) // n))
print("number changed in a faithful statement: detected %d / %d (number absent from the source, or present only outside the matching passage)" % tuple(num_det))
print("overstating word added: detected %d / %d" % tuple(over_det))
