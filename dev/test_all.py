#!/usr/bin/env python3
"""Regression tests for intro-ledger (stdlib unittest). Run: python3 dev/test_all.py [-v]
Library text: 20 real public arXiv abstracts (dev/fixtures/arxiv_landslide.json, metadata CC0); the author's own paper and all drafts are invented."""
import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
import warnings
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SUB = os.path.join(ROOT, "submission") if os.path.isdir(os.path.join(ROOT, "submission")) else ROOT
sys.path.insert(0, os.path.join(SUB, "scripts"))
import evidence as ev  # noqa: E402
import iw  # noqa: E402
import lint  # noqa: E402

warnings.simplefilter("ignore", ResourceWarning)
D = json.load(open(os.path.join(HERE, "fixtures", "arxiv_landslide.json"), encoding="utf-8"))

OWN = """# Cross-sensor landslide mapping with a lightweight transfer model

## Method
LiteSlide uses a shared encoder with sensor-specific stems. We pre-train on 9,800 labelled tiles from 14 regions and fine-tune with 200 tiles from the target region. The model has 4.1 million parameters.

## Experiments
Table 1 compares LiteSlide with three baselines on four held-out regions. LiteSlide reaches a mean F1 of 0.812, against 0.771 for the best baseline. In the SAR-only setting the F1 is 0.703. Figure 3 shows that performance drops by 0.04 when the number of fine-tuning tiles falls from 200 to 50.

Table 1. F1 of LiteSlide and three baselines on four held-out regions.

Figure 3. F1 as a function of the number of fine-tuning tiles.

## Limitations
The model was only tested on Sentinel imagery.
"""


def run(*args):
    buf = io.StringIO()
    code = 0
    with contextlib.redirect_stdout(buf):
        try:
            iw.main(list(args))
        except SystemExit as e:
            code = e.code or 0
    return code, buf.getvalue()


def bibtex(n=12):
    out = []
    for d in D[:n]:
        key = d["authors"][0].split()[-1].lower() + d["year"]
        out.append("@article{%s,\n author={%s},\n title={%s},\n journal={arXiv preprint arXiv:%s},\n year={%s},\n eprint={%s},\n archiveprefix={arXiv},\n abstract={%s}\n}\n" % (key, " and ".join(d["authors"][:4]), d["title"], d["id"].split("v")[0], d["year"], d["id"].split("v")[0], d["abstract"]))
    return "\n".join(out)


class Tmp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.own = self.write("own.md", OWN)
        self.lib = self.write("library.bib", bibtex())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def path(self, *p):
        return os.path.join(self.tmp, *p)

    def write(self, name, text):
        with open(self.path(name), "w", encoding="utf-8") as fh:
            fh.write(text)
        return self.path(name)

    def prep(self):
        code, t = run("run", "--own", self.own, "--lib", self.lib, "--out", self.path("out"))
        self.assertEqual(code, 0, t)
        return self.path("out", ".work")

    def check(self, draft, ledger=None, work=None):
        work = work or self.prep()
        if ledger:
            run("ingest", work, self.write("dec.txt", ledger))
        code, t = run("check", work, self.write("draft.md", draft))
        res = json.load(open(os.path.join(work, "check.json"), encoding="utf-8"))
        return work, res, {i["code"] for i in res["issues"]}


GOOD = """## 1 Introduction

<!--part:background-->
Landslide inventories after a triggering event are increasingly produced with deep learning on SAR data, which can provide measurements of affected areas independent of weather or lighting conditions [@boehm2022]. Optical CNNs reached an overall accuracy of 99.20% in the Hokkaido case [@nava2021].

<!--group:G1-->
Landslide4Sense provides 3,799 image patches fusing Sentinel-2 layers with elevation and slope [@ghorbanzadeh2022], whereas LMHLD contains 25,365 patches with different sizes to accommodate different landslide scales [@liu2025].

However, the effects of factor selection on the prediction accuracy of ML and DL models are unclear [@chen2023]. <!--gap:G1-->

Our contributions: we propose LiteSlide, a transfer model with 4.1 million parameters <!--contrib:C1-->; it reaches a mean F1 of 0.812 on four held-out regions <!--contrib:C2-->.
"""


class TestEvidence(unittest.TestCase):
    def test_quote_verification(self):
        t = "We find that additional satellite visits enhance detection per-\nformance, but that early detection is possible."
        self.assertTrue(ev.verify_quote("additional satellite visits enhance detection performance", t))
        self.assertTrue(ev.verify_quote("We find that ... early detection is possible", t))
        self.assertFalse(ev.verify_quote("additional satellite visits degrade detection performance", t))
        self.assertFalse(ev.verify_quote("too short", t))
        self.assertFalse(ev.verify_quote("early detection is possible ... We find that additional", t))  # order matters

    def test_numbers_next_to_cjk(self):
        self.assertEqual(ev.numbers_of("迁移学习可将F1从0.52提高到0.88"), ["0.52", "0.88"])
        self.assertEqual(ev.numbers_of("see Table 2 and Figure 3 [4]: 94.2% in 2019 (Smith, 2020)"), ["94.2", "2019"])
        self.assertIn("93.5", ev.numbers_in_text("总体精度达到93.5%。"))

    def test_support_separates_own_from_other_source(self):
        texts = [d["title"] + ". " + d["abstract"] for d in D]
        idf = ev.Idf(texts)
        s = "SAR can provide measurements of affected areas independent of weather or lighting conditions"
        own, _ = ev.best_support(s, texts[2], idf)
        other, _ = ev.best_support(s, texts[5], idf)
        self.assertGreater(own, 0.8)
        self.assertLess(other, 0.25)

    def test_anchor_forms(self):
        import tempfile as tf
        d = tf.mkdtemp()
        try:
            p = os.path.join(d, "own.md")
            open(p, "w", encoding="utf-8").write(OWN)
            own = ev.load_own(p, d)
        finally:
            pass
        self.assertTrue(ev.resolve_anchor("Table 1", own)[0])
        self.assertTrue(ev.resolve_anchor("Fig. 3", own)[0])
        self.assertFalse(ev.resolve_anchor("Fig. 9", own)[0])
        self.assertTrue(ev.resolve_anchor("N: 0.812", own)[0])
        self.assertFalse(ev.resolve_anchor("N: 0.912", own)[0])
        self.assertTrue(ev.resolve_anchor("Sec: Experiments", own)[0])
        self.assertTrue(ev.resolve_anchor('Q: "reaches a mean F1 of 0.812"', own)[0])
        self.assertFalse(ev.resolve_anchor('Q: "reaches a mean F1 of 0.912"', own)[0])
        self.assertEqual(sorted(own["figures"]), ["fig:3", "tab:1"])
        shutil.rmtree(d, ignore_errors=True)

    def test_candidates_skip_title_and_find_kinds(self):
        d = D[2]
        c = ev.candidates(d["title"] + ". " + d["abstract"])
        self.assertTrue(c and all(x["text"] != d["title"] + "." for x in c))
        self.assertIn("result", {x["kind"] for x in c})


class TestLint(unittest.TestCase):
    def test_parse_roles_and_tags(self):
        P = lint.parse_draft(GOOD)
        roles = [p["role"] for p in P["paragraphs"]]
        self.assertEqual(roles, ["background", "related", "gap", "contribution"])
        gap = [s for s in P["sentences"] if s["gap"]]
        self.assertEqual(len(gap), 1)
        self.assertEqual(sorted(s["contrib"] for s in P["sentences"] if s["contrib"]), ["C1", "C2"])
        self.assertEqual(P["paragraphs"][1]["group"], "G1")

    def test_heading_naming_two_parts_defers_to_cues(self):
        P = lint.parse_draft("## Research gap and contributions\n\nHowever, X is unclear [@a]. <!--gap:G1-->\n\nWe propose Y <!--contrib:C1-->.")
        self.assertEqual([p["role"] for p in P["paragraphs"]], ["gap", "contribution"])

    def test_filler_en_zh(self):
        self.assertTrue(lint.filler_hits("In recent years, landslide mapping has attracted increasing attention."))
        self.assertTrue(lint.filler_hits("With the rapid development of remote sensing, many tasks changed."))
        self.assertTrue(lint.filler_hits("近年来，滑坡识别受到了广泛关注。"))
        self.assertFalse(lint.filler_hits("Landslide4Sense provides 3,799 patches fusing Sentinel-2 layers."))

    def test_clauses_split_at_markers(self):
        cl = iw.clauses_of("Optical methods are sensitive to shadows [@a], while radar needs terrain data [@b; @c].")
        self.assertEqual([k for _, k in cl], [["a"], ["b", "c"]])
        one = iw.clauses_of("Ma et al. [@ma] built a transformer for forecasting.")
        self.assertEqual(len(one), 1)

    def test_tags_split_one_sentence_into_statements(self):
        P = lint.parse_draft("We propose A <!--contrib:C1-->; we show B <!--contrib:C2-->.")
        self.assertEqual([s["contrib"] for s in P["sentences"]], ["C1", "C2"])

    def test_keys_latex_and_pandoc(self):
        self.assertEqual(lint.keys_in("a [@x; @y, p. 3] b \\citep{z,w}"), ["x", "y", "z", "w"])


class TestCheck(Tmp):
    def test_good_draft_has_no_errors(self):
        work, res, codes = self.check(GOOD, "=== claim chen2023\nkind: limitation\ntext: the effect of factor selection on ML and DL accuracy is unclear\nquote: the effects of factor selection using various methods on the prediction accuracy of ML and DL models are unclear\n"
                                            "=== gap G1\ntype: limitation\nstatement: factor selection effects are unclear\nfrom: chen2023:limitation\n"
                                            "=== contribution C1\nstatement: LiteSlide with 4.1 million parameters\nevidence: Sec: Method | N: 4.1\n=== contribution C2\nstatement: mean F1 0.812\nevidence: Table 1 | N: 0.812\naddresses: G1\n")
        errs = [i for i in res["issues"] if i["severity"] == "error"]
        self.assertEqual(errs, [], errs)
        self.assertEqual({r["status"] for r in res["rows"] if r["keys"] and r["kind"] == "cited"} <= {"supported", "weak"}, True)

    def test_seeded_defects_are_found(self):
        bad = GOOD.replace("Landslide inventories after", "In recent years, landslide mapping has attracted increasing attention. Landslide inventories after")
        bad = bad.replace("99.20%", "97.10%")
        bad = bad.replace("[@liu2025]", "[@liu2025; @nobody2020]")
        bad = bad.replace("However, the effects of factor selection on the prediction accuracy of ML and DL models are unclear [@chen2023].", "However, no study has combined optical and SAR imagery and existing models are too slow.")
        bad = bad.replace("it reaches a mean F1 of 0.812", "it significantly outperforms all baselines with an F1 of 0.912")
        work, res, codes = self.check(bad)
        for want in ("filler", "number_not_in_source", "unknown_key", "gap_not_derived", "absence_claim", "contribution_number_not_in_own_material"):
            self.assertIn(want, codes, codes)

    def test_wrong_source_is_flagged(self):
        d = GOOD.replace("[@boehm2022]", "[@ma2023]")
        work, res, codes = self.check(d)
        self.assertTrue({"unsupported_statement", "weak_support"} & codes, codes)

    def test_limitation_must_be_in_the_source(self):
        d = GOOD.replace("However, the effects of factor selection on the prediction accuracy of ML and DL models are unclear [@chen2023].", "However, the model of Ma and Mei fails on small slopes and cannot transfer to new regions [@ma2023].")
        work, res, codes = self.check(d)
        self.assertIn("limitation_not_in_source", codes)

    def test_judgement_marker_is_accepted(self):
        d = GOOD.replace("However, the effects of factor selection on the prediction accuracy of ML and DL models are unclear [@chen2023].", "However, we argue that these models are hard to use operationally [@ma2023].")
        work, res, codes = self.check(d)
        self.assertNotIn("limitation_not_in_source", codes)

    def test_sequential_summary_and_ungrouped(self):
        d = GOOD.replace("<!--group:G1-->\nLandslide4Sense provides 3,799 image patches fusing Sentinel-2 layers with elevation and slope [@ghorbanzadeh2022], whereas LMHLD contains 25,365 patches with different sizes to accommodate different landslide scales [@liu2025].",
                         "Ma et al. built a transformer that forecasts landslides [@ma2023]. Ahmad et al. selected eight input channels [@ahmad2026]. Chen and Fan studied factor selection [@chen2023]. Oak et al. compared CNN models [@oak2024].")
        work, res, codes = self.check(d)
        self.assertIn("sequential_summary", codes)
        self.assertIn("ungrouped", codes)

    def test_title_only_entry_cannot_carry_a_specific_claim(self):
        lib = bibtex(12) + "\n@article{noabs2020, author={Doe, Jane}, title={Landslides and rain in some place}, journal={J}, year={2020}}\n"
        self.lib = self.write("library.bib", lib)
        d = GOOD.replace("[@nava2021]", "[@noabs2020]")
        work, res, codes = self.check(d)
        self.assertIn("unverifiable_claim", codes)

    def test_contribution_without_any_support_is_an_error(self):
        d = GOOD.replace("it reaches a mean F1 of 0.812 on four held-out regions", "we release a global archive of ten million Landsat scenes with expert labels")
        work, res, codes = self.check(d)
        self.assertIn("contribution_without_evidence", codes)

    def test_numeric_markers_are_refused_with_advice(self):
        work, res, codes = self.check("## Intro\n\nSAR works under cloud [1]. However, X is unclear [2].")
        self.assertIn("markers_without_keys", codes)

    def test_missing_parts(self):
        work, res, codes = self.check("## Intro\n\nLandslide inventories are produced with deep learning [@boehm2022].")
        self.assertIn("missing_part", codes)
        self.assertIn("no_gap_statement", codes)
        self.assertIn("no_contribution", codes)

    def test_check_is_deterministic(self):
        work, r1, _ = self.check(GOOD)
        code, t = run("check", work, self.path("draft.md"))
        r2 = json.load(open(os.path.join(work, "check.json"), encoding="utf-8"))
        self.assertEqual(r1["issues"], r2["issues"])


class TestIngest(Tmp):
    def test_quote_must_be_verbatim_and_numbers_must_match(self):
        work = self.prep()
        blocks = ("=== claim boehm2022\nkind: result\ntext: AUPRC above 0.7\nquote: achieving an Area under the Precision-Recall curve exceeding 0.7\n"
                  "=== claim boehm2022\nkind: limitation\ntext: invented\nquote: this sentence is not in the abstract at all of the paper\n"
                  "=== claim nava2021\nkind: result\ntext: accuracy 99.99%\nquote: achieving an overall accuracy of 99.20%\n"
                  "=== claim nowhere\nkind: result\ntext: x\nquote: y\n")
        code, t = run("ingest", work, self.write("b.txt", blocks))
        self.assertEqual(code, 2)
        self.assertIn("recorded: claim 1", t)
        self.assertIn("not verbatim", t)
        self.assertIn("not in the source", t)
        ops = json.load(open(os.path.join(work, "ops.json")))
        self.assertEqual([c["id"] for c in ops["claims"]], ["boehm2022:result"])

    def test_gap_needs_a_source_or_a_judgement_label(self):
        work = self.prep()
        code, t = run("ingest", work, self.write("b.txt", "=== gap G1\ntype: limitation\nstatement: x\n"))
        self.assertEqual(code, 2)
        self.assertIn("REJECTED", t)
        code, t = run("ingest", work, self.write("b.txt", "=== gap G2\ntype: judgement\nstatement: we argue x\n"))
        self.assertEqual(code, 0, t)

    def test_group_needs_two_known_works(self):
        work = self.prep()
        code, t = run("ingest", work, self.write("b.txt", "=== group G1\ntitle: t\nmembers: boehm2022\n"))
        self.assertEqual(code, 2)
        code, t = run("ingest", work, self.write("b.txt", "=== group G1\ntitle: t\nmembers: boehm2022, nava2021\n"))
        self.assertEqual(code, 0, t)

    def test_contribution_anchors_are_resolved(self):
        work = self.prep()
        run("ingest", work, self.write("b.txt", "=== contribution C1\nstatement: s\nevidence: Table 1 | Fig. 9 | N: 0.812\n"))
        ops = json.load(open(os.path.join(work, "ops.json")))
        self.assertEqual([a["ok"] for a in ops["contributions"][0]["anchors"]], [True, False, True])

    def test_ingest_is_idempotent(self):
        work = self.prep()
        b = self.write("b.txt", "=== claim boehm2022\nkind: result\ntext: x\nquote: achieving an Area under the Precision-Recall curve exceeding 0.7\n")
        run("ingest", work, b)
        run("ingest", work, b)
        self.assertEqual(len(json.load(open(os.path.join(work, "ops.json")))["claims"]), 1)


class TestBuild(Tmp):
    def build(self, draft=GOOD, *extra):
        work = self.prep()
        code, t = run("build", work, self.write("draft.md", draft), "--out", self.path("out"), *extra)
        return work, code, t

    def test_outputs_numeric(self):
        work, code, t = self.build()
        out = self.path("out")
        text = open(os.path.join(out, "intro.md"), encoding="utf-8").read()
        self.assertNotIn("<!--", text)
        self.assertNotIn("[@", text)
        self.assertRegex(text, r"conditions \[1\]\.")
        self.assertIn("## References", text)
        self.assertNotRegex(text, r"\s[.,;]")
        for f in ("intro.docx", "intro.tex", "references.bib", "references.ris", "evidence_table.csv", "evidence_table.json", "traceability.md", "review_checklist.md", "result.json"):
            self.assertTrue(os.path.isfile(os.path.join(out, f)), f)
        import xml.dom.minidom as md
        md.parseString(zipfile.ZipFile(os.path.join(out, "intro.docx")).read("word/document.xml"))
        tex = open(os.path.join(out, "intro.tex"), encoding="utf-8").read()
        self.assertIn("\\cite{boehm2022}", tex)
        self.assertIn("\\section{1 Introduction}", tex)

    def test_numbers_follow_first_appearance(self):
        work, code, t = self.build()
        refs = open(self.path("out", "references.ieee.txt"), encoding="utf-8").read().splitlines()
        self.assertTrue(refs[0].startswith("[1] V. Boehm"))
        self.assertTrue(refs[1].startswith("[2] L. Nava"))

    def test_apa_author_year_and_narrative(self):
        d = GOOD.replace("Optical CNNs reached", "Nava et al. [@nava2021] report that optical CNNs reached")
        work, code, t = self.build(d, "--style", "apa7")
        text = open(self.path("out", "intro.md"), encoding="utf-8").read()
        self.assertIn("(Boehm et al., 2022)", text)
        self.assertIn("Nava et al. (2021)", text)

    def test_status_reflects_open_errors(self):
        bad = GOOD.replace("99.20%", "97.10%")
        work, code, t = self.build(bad)
        res = json.load(open(self.path("out", "result.json")))
        self.assertEqual(res["status"], "partial")
        self.assertTrue(any(r["kind"] == "number_not_in_source" for r in res["boundaries"]["human_review"]))

    def test_contract_fields(self):
        case = self.write("case.json", json.dumps({"case_id": "c1", "output_contract": {"fields": ["case_id", "目标产物", "事实与来源映射", "版本与边界", "reviewer_score"]}}))
        code, t = run("run", "--case", case, "--own", self.own, "--lib", self.lib, "--out", self.path("out"))
        work = self.path("out", ".work")
        code, t = run("build", work, self.write("draft.md", GOOD), "--out", self.path("out"))
        res = json.load(open(self.path("out", "result.json")))
        self.assertEqual(res["case_id"], "c1")
        self.assertIn("text", res["目标产物"])
        self.assertIn("cited_sentences", res["事实与来源映射"])
        self.assertIn("open_issues", res["版本与边界"])
        self.assertIsNone(res["reviewer_score"])
        self.assertEqual(res["_meta"]["unfilled_fields"], ["reviewer_score"])
        self.assertEqual(code, 2)
        ans = self.write("ans.json", json.dumps({"reviewer_score": "set by the platform"}))
        code, t = run("build", work, self.path("draft.md"), "--out", self.path("out"), "--answers", ans)
        self.assertEqual(code, 0)


class TestInputs(Tmp):
    def test_inline_chinese_case(self):
        case = {"case_id": "zh", "task": "请撰写引言与相关工作，约800字，使用中文，参考文献按GB/T 7714-2015。",
                "research_summary": "## 研究内容\n本文提出轻量迁移模型LiteSlide，用于利用Sentinel-2光学影像和Sentinel-1雷达影像识别滑坡，参数量为410万。\n\n## 实验\n在四个留出区域上，LiteSlide的平均F1为0.812，最强基线为0.771。仅使用雷达数据时F1为0.703。",
                "references": [{"id": "zhang2020", "title": "基于深度卷积网络的光学影像滑坡自动识别", "authors": ["张伟", "李明"], "year": 2020, "venue": "地球信息科学学报",
                                "abstract": "针对滑坡灾后快速制图的需求，本文提出一种基于深度卷积网络的滑坡自动识别方法。方法在高分辨率光学影像上训练，在测试区总体精度达到93.5%。实验表明，该方法对阴影和裸地造成的误检较为敏感，且仅在单一地区验证，跨区域泛化能力尚未检验。"}]}
        cp = self.write("in/case.json", json.dumps(case, ensure_ascii=False)) if os.makedirs(self.path("in")) is None else None
        code, t = run("run", "--case", cp, "--out", self.path("out"))
        self.assertEqual(code, 0, t)
        self.assertIn("language: zh | length hint: 800 | style hint: gbt7714", t)
        draft = "## 引言\n\n光学影像上的深度卷积网络在测试区总体精度达到93.5%[@zhang2020]。\n\n然而，该方法仅在单一地区验证[@zhang2020]。<!--gap:G1-->\n\n本文提出参数量为410万的LiteSlide<!--contrib:C1-->，平均F1为0.912<!--contrib:C2-->。"
        work = self.path("out", ".work")
        code, t = run("check", work, self.write("d.md", draft))
        res = json.load(open(os.path.join(work, "check.json"), encoding="utf-8"))
        codes = {i["code"] for i in res["issues"]}
        self.assertIn("contribution_number_not_in_own_material", codes)
        self.assertNotIn("number_not_in_source", codes)
        self.assertEqual({g["status"] for g in res["gaps"]}, {"derived"})
        code, t = run("build", work, self.path("d.md"), "--out", self.path("out"))
        text = open(self.path("out", "intro.md"), encoding="utf-8").read()
        self.assertIn("[1]", text)
        self.assertIn("## 参考文献", text)
        self.assertIn("[J]", text)  # GB/T 7714 type mark

    def test_source_documents_are_matched_to_library_records(self):
        lib = self.write("lib.bib", "@article{boehm2022, author={Boehm, V.}, title={Deep Learning for Rapid Landslide Detection using Synthetic Aperture Radar (SAR) Datacubes}, year={2022}}\n")
        d = self.path("src")
        os.makedirs(d)
        self.write("src/paper1.md", "# Deep Learning for Rapid Landslide Detection using Synthetic Aperture Radar (SAR) Datacubes\n\nWe find that additional satellite visits enhance detection performance, but that early detection is possible when SAR data is combined with terrain information.\n")
        code, t = run("run", "--own", self.own, "--lib", lib, "--source", self.path("src", "paper1.md"), "--out", self.path("out"))
        self.assertEqual(code, 0, t)
        M = json.load(open(self.path("out", ".work", "materials.json"), encoding="utf-8"))
        self.assertEqual(M["sources"][0]["entry"], "boehm2022")
        self.assertIn("early detection is possible", M["texts"]["boehm2022"])

    def test_unreadable_library_does_not_stop(self):
        bad = self.write("bad.json", '[["x"], {"title": 1}]')
        code, t = run("run", "--own", self.own, "--lib", bad, "--lib", self.lib, "--out", self.path("out"))
        self.assertEqual(code, 0, t)

    def test_online_enrichment_fails_fast(self):
        import urllib.request
        orig = urllib.request.urlopen
        calls = []

        def boom(*a, **k):
            calls.append(1)
            raise OSError("network unreachable")
        urllib.request.urlopen = boom
        try:
            recs = [{"id": "r%d" % i, "doi": "10.1/x%d" % i, "arxiv": "", "abstract": ""} for i in range(6)]
            ev.enrich(recs, timeout=1)
        finally:
            urllib.request.urlopen = orig
        self.assertEqual(len(calls), 2)

    def test_arxiv_verification_with_mocked_service(self):
        import urllib.request
        import verify
        import bib
        atom = ('<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/2211.02869v1</id><published>2022-11-05T00:00:00Z</published>'
                '<title>Deep Learning for Rapid Landslide Detection using Synthetic Aperture Radar (SAR) Datacubes</title><summary>x</summary><author><name>Vanessa Boehm</name></author></entry></feed>')

        class R:
            def read(self):
                return atom.encode()

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        orig = urllib.request.urlopen
        urllib.request.urlopen = lambda *a, **k: R()
        ev.ARXIV.clear()
        try:
            def rec(title, year):
                r = bib.new_record("t")
                r.update({"id": "x" + year, "title": title, "year": year, "arxiv": "2211.02869", "type": "preprint", "container": "arXiv"})
                r["authors"] = bib.split_authors("Boehm, Vanessa")
                return bib.finish(r)
            good = rec("Deep Learning for Rapid Landslide Detection using Synthetic Aperture Radar (SAR) Datacubes", "2022")
            bad = rec("A different title about dams", "2015")
            res = verify.check_all([good, bad], online=True, timeout=1)
        finally:
            urllib.request.urlopen = orig
            ev.ARXIV.clear()
        self.assertEqual(res[good["id"]]["status"], "verified")
        self.assertEqual(res[bad["id"]]["status"], "mismatch")

    def test_bad_inputs_have_clear_messages(self):
        code, t = run("run", "--own", self.path("missing.md"), "--out", self.path("o"))
        self.assertNotEqual(code, 0)


if __name__ == "__main__":
    unittest.main(warnings="ignore")
