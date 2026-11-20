#!/usr/bin/env python3
"""iw.py - intro-ledger: write the introduction and related work of a paper so that every statement about other work, every research gap and every contribution is bound to evidence.

You write the prose and make the judgements; the ledger keeps what the prose rests on and checks it: each statement about a cited work against that work's text, each gap against
the limitations of the works it cites, each contribution against the author's own sections, figures, tables and numbers; plus filler, sequential summaries, unsupported
absence claims, coverage and metadata. `build` turns the checked draft into the paper text, the reference list and the evidence table.

  iw.py run [--case /input/case.json] --out OUT [--own F ...] [--lib F ...] [--source F ...] [--online]   prepare + brief (what the evidence is)
  iw.py show W [--entry KEY | --own]            full evidence of one source / the own material
  iw.py ingest W [FILE|-]                       claim / group / gap / contribution / meta blocks
  iw.py check W DRAFT.md                        lint + evidence checks, writes check.json and evidence_table.json
  iw.py build W DRAFT.md --out OUT [--style gbt7714|apa7|ieee|vancouver] [--case ...] [--answers answers.json]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
import unicodedata
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bib  # noqa: E402
import cite  # noqa: E402
import dedupe  # noqa: E402
import docxw  # noqa: E402
import evidence as ev  # noqa: E402
import fmt  # noqa: E402
import lint  # noqa: E402
import nlib  # noqa: E402
import verify  # noqa: E402

VERSION = "1.0.0"
SUP_OK, SUP_WEAK = 0.40, 0.25      # IDF-weighted share of a sentence's content found in its best source passage
LIM_OK = 0.22                      # limitation sentences need a limitation passage of the cited work
KINDS = ("problem", "route", "data", "result", "limitation", "scope")


# ------------------------------------------------------------------------------------------------ io
def jload(p, default=None):
    if not os.path.isfile(p):
        return default
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def jsave(p, obj):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def wtext(p, text):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(text)


def rtext(p):
    with open(p, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def find_key(obj, names):
    if isinstance(obj, dict):
        for k in names:
            if k in obj:
                return obj[k]
        for v in obj.values():
            r = find_key(v, names)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_key(v, names)
            if r is not None:
                return r
    return None


def load(work):
    M = jload(os.path.join(work, "materials.json"))
    if M is None:
        raise SystemExit("no materials.json in %s: run `run` / `prepare` first" % work)
    return M, jload(os.path.join(work, "ops.json"), empty_ops())


def empty_ops():
    return {"claims": [], "groups": [], "gaps": [], "contributions": [], "meta": []}


# ------------------------------------------------------------------------------------------------ discovery
LIB_EXT = (".bib", ".bibtex", ".ris", ".enw", ".nbib")
DOC_EXT = (".docx", ".md", ".markdown", ".tex", ".txt", ".pdf")
OWN_HINT = re.compile(r"own|our|my|manuscript|draft|paper|result|method|experiment|material|note|summary|abstract|stage|底稿|本文|稿|方法|结果|实验|材料|笔记|摘要|成果", re.I)
SRC_HINT = re.compile(r"librar|literature|reference|related|cited|source|prior|bib|refs|文献|参考|相关|引用|来源", re.I)
SKIP = {"task.md", "case.json", "readme.md", "readme.txt"}


def strings(obj, key=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from strings(v, k)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings(v, key)
    elif isinstance(obj, str):
        yield key, obj


def walk(roots, depth=3):
    out = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        base = root.rstrip(os.sep).count(os.sep)
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in sorted(dn) if not d.startswith(".") and d not in ("__pycache__", "output", "work")]
            if dp.count(os.sep) - base >= depth:
                dn[:] = []
            for f in sorted(fn):
                p = os.path.join(dp, f)
                if f.lower() not in SKIP and not f.startswith(".") and p not in out:
                    out.append(p)
    return out


def is_library(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in LIB_EXT:
        return True
    if ext in (".txt", ".json"):
        head = rtext(path)[:20000]
        if bib.sniff(head, os.path.basename(path)) != "text":
            return True
    return False


def json_entries(obj):
    """records given inline in the case file: lists of dicts with a title and (abstract | authors | doi)"""
    recs = []

    def walk_(o):
        if isinstance(o, list):
            if o and all(isinstance(x, dict) for x in o) and sum(1 for x in o if x.get("title")) >= max(1, len(o) // 2) and any(("abstract" in x or "authors" in x or "author" in x or "doi" in x or "DOI" in x) for x in o):
                for x in o:
                    if x.get("title"):
                        recs.append(x)
                return
            for v in o:
                walk_(v)
        elif isinstance(o, dict):
            for v in o.values():
                walk_(v)
    walk_(obj)
    out = []
    for x in recs:
        r = bib.new_record("case")
        r["title"] = str(x.get("title", ""))
        au = x.get("authors") or x.get("author") or []
        if isinstance(au, str):
            au = bib.split_authors(au)
        else:
            au = [a if isinstance(a, dict) else (bib.parse_name(str(a)) or {"family": str(a), "given": "", "literal": "", "zh": False}) for a in au]
            au = [{"family": a.get("family", ""), "given": a.get("given", ""), "literal": a.get("literal", ""), "zh": a.get("zh", False)} for a in au]
        r["authors"] = au
        r["year"] = str(x.get("year") or x.get("date") or x.get("published") or "")
        r["container"] = str(x.get("venue") or x.get("journal") or x.get("container") or x.get("source") or "")
        r["doi"] = str(x.get("doi") or x.get("DOI") or "")
        r["url"] = str(x.get("url") or "")
        r["abstract"] = str(x.get("abstract") or x.get("summary") or x.get("text") or "")
        r["type"] = "journal" if r["container"] else "other"
        r["id"] = str(x.get("id") or x.get("key") or x.get("citekey") or "")
        out.append(bib.finish(r))
    return out


def discover(a):
    case = jload(a.case) if a.case and os.path.isfile(a.case) else None
    base = os.path.dirname(os.path.abspath(a.case)) if a.case else "/input"
    walk_roots = list(dict.fromkeys([base, "/input"]))
    roots = walk_roots + [os.getcwd()]
    files = walk(walk_roots)
    named = []
    if case:
        for key, val in strings(case):
            if len(val) < 300 and re.search(r"\.(?:docx|tex|md|markdown|txt|pdf|bib|bibtex|ris|enw|nbib|json)\b", val, re.I):
                for root in roots + [""]:
                    p = os.path.join(root, val) if root and not os.path.isabs(val) else val
                    if os.path.isfile(p) and os.path.basename(p).lower() not in SKIP:
                        named.append((key, os.path.abspath(p)))
                        if os.path.abspath(p) not in files:
                            files.append(os.path.abspath(p))
                        break
    libs = [os.path.abspath(x) for x in (a.lib or [])]
    own = [os.path.abspath(x) for x in (a.own or [])]
    src = [os.path.abspath(x) for x in (a.source or [])]
    for f in a.lib or []:
        if not os.path.isfile(f):
            raise SystemExit("ERROR: library file not found: %s" % f)
    for f in (a.own or []) + (a.source or []):
        if not os.path.isfile(f):
            raise SystemExit("ERROR: file not found: %s" % f)
    keyof = {p: k for k, p in named}
    rest = [f for f in files if f not in libs + own + src]
    if not a.lib:
        libs += [f for f in rest if is_library(f)]
    rest = [f for f in rest if f not in libs and os.path.splitext(f)[1].lower() in DOC_EXT]
    if not a.source:
        src += [f for f in rest if SRC_HINT.search(keyof.get(f, "") + " " + "/".join(f.split(os.sep)[-3:])) and not OWN_HINT.search(keyof.get(f, ""))]
    rest = [f for f in rest if f not in src]
    inline_own = [v for k, v in strings(case or {}) if nlib.wcount(v) > 60 and not SRC_HINT.search(k)]
    if not own and inline_own and not any(OWN_HINT.search(keyof.get(f, "")) for f in rest):
        rest = [f for f in rest if f in keyof]  # the case carries the own material as text: only files it names are candidates
    if not own:
        nonpdf = [f for f in rest if not f.lower().endswith(".pdf")]
        pdfs = [f for f in rest if f.lower().endswith(".pdf")]
        own = nonpdf[:3] if nonpdf else pdfs[:1]
        src += [f for f in rest if f not in own]
    return own, libs, src, case, walk_roots


# ------------------------------------------------------------------------------------------------ materials
def uniq_ids(recs):
    seen = set()
    for r in recs:
        rid = r["id"] or "ref"
        if rid in seen:
            k = 2
            while "%s_%d" % (rid, k) in seen:
                k += 1
            rid = "%s_%d" % (rid, k)
        r["id"] = rid
        seen.add(rid)
    return recs


def make_keys(recs):
    """readable citation keys (family + year [+ letter]) for records without a BibTeX key"""
    seen = set()
    for r in recs:
        if r["id"] and not re.fullmatch(r"ref\d+", r["id"]):
            seen.add(r["id"])
    for r in recs:
        if r["id"] and not re.fullmatch(r"ref\d+", r["id"]):
            continue
        fam = (r["authors"][0]["family"] if r["authors"] else "") or (r["title"].split() or ["ref"])[0]
        fam = dedupe.PINYIN.get(fam, fam)
        fam = unicodedata.normalize("NFKD", nlib.norm(fam)).encode("ascii", "ignore").decode("ascii")
        base = re.sub(r"[^a-z0-9]", "", fam.lower()) or "ref"
        base = "%s%s" % (base, r["year"] or "")
        k, c = base, 1
        while k in seen:
            c += 1
            k = "%s%s" % (base, chr(96 + c) if c <= 26 else c)
        r["id"] = k
        seen.add(k)
    return recs


def match_source(text, name, recs):
    """which library record a source document is: title found in its first page, else filename similarity"""
    head = nlib.squash(text[:4000])
    best, bs = None, 0.0
    for r in recs:
        t = nlib.squash(r["title"])
        if len(t) > 15 and t in head:
            return r, 1.0
        s = dedupe.title_sim(re.sub(r"[_\-.]+", " ", os.path.splitext(name)[0]), r["title"])
        if s > bs:
            best, bs = r, s
    return (best, bs) if bs >= 0.6 else (None, bs)


def task_info(case, roots):
    text = ""
    for root in roots:
        p = os.path.join(root, "task.md")
        if os.path.isfile(p):
            text = rtext(p)
            break
    if case:
        for key, val in strings(case):
            if re.search(r"task|instruction|prompt|requirement|任务|要求|说明|description", key, re.I) and len(val) > 20:
                text += "\n" + val
    info = {"text": text.strip()[:6000], "lang": None, "length": None, "style": None, "venue": None}
    if re.search(r"中文|汉语|Chinese", text, re.I) and not re.search(r"English only|仅英文|用英文", text):
        info["lang"] = "zh"
    if re.search(r"用英文|英文撰写|in English|English version|英语", text, re.I):
        info["lang"] = "en"
    m = re.search(r"(\d{3,5})\s*(?:字|个字|words|词)", text)
    if m:
        info["length"] = int(m.group(1))
    for st, rx in (("gbt7714", r"GB/?T ?7714|国标"), ("apa7", r"\bAPA\b"), ("ieee", r"\bIEEE\b"), ("vancouver", r"Vancouver")):
        if re.search(rx, text, re.I):
            info["style"] = st
    return info


def cmd_run(a):
    os.makedirs(a.out, exist_ok=True)
    a.work = a.work or os.path.join(a.out, ".work")
    prepare(a)
    brief(a.work, a.out, full=True)


def prepare(a):
    os.makedirs(a.work, exist_ok=True)
    own_files, lib_files, src_files, case, roots = discover(a)
    own = None
    note = []
    for i, f in enumerate(own_files):
        o = ev.load_own(f, os.path.join(a.work, "own%d" % i))
        if o.get("note"):
            note.append(o["note"])
        if own is None:
            own = o
            own["files"] = [os.path.basename(f)]
        else:
            off = len(own["sentences"])
            for s in o["sentences"]:
                s["id"] = "O%03d" % (int(s["id"][1:]) + off)
            own["sentences"] += o["sentences"]
            own["figures"].update(o["figures"])
            own["sections"] += o["sections"]
            for n, ids in o["numbers"].items():
                own["numbers"].setdefault(n, []).extend("O%03d" % (int(x[1:]) + off) for x in ids)
            own["text"] += "\n" + o["text"]
            own["files"].append(os.path.basename(f))
    # case-embedded own text (summaries, notes) when no own file exists
    if own is None:
        blob = []
        for key, val in strings(case or {}):
            if nlib.wcount(val) > 60 and not SRC_HINT.search(key):
                blob.append("## %s\n\n%s" % (key, val))
        if blob:
            p = os.path.join(a.work, "case_text.md")
            wtext(p, "\n\n".join(blob))
            own = ev.load_own(p, os.path.join(a.work, "own_case"))
            own["files"] = ["case.json (text fields)"]
        else:
            own = {"files": [], "sections": [], "sentences": [], "figures": {}, "numbers": {}, "text": "", "format": "none", "file": ""}
    recs, lib_info = [], []
    for lp in lib_files:
        try:
            kind, rs = bib.parse_any(rtext(lp), os.path.basename(lp))
        except Exception as e:  # a damaged library file must not stop the run
            lib_info.append({"file": os.path.basename(lp), "format": "unreadable", "entries": 0, "error": "%s: %s" % (type(e).__name__, str(e)[:80])})
            print("WARNING: library file %s could not be parsed (%s): skipped" % (os.path.basename(lp), lib_info[-1]["error"]))
            continue
        for r in rs:
            r["lib_file"] = os.path.basename(lp)
        recs += rs
        lib_info.append({"file": os.path.basename(lp), "format": kind, "entries": len(rs)})
    inline = json_entries(case) if case else []
    if inline:
        recs += inline
        lib_info.append({"file": "case.json (inline records)", "format": "json", "entries": len(inline)})
    make_keys(recs)
    uniq_ids(recs)
    texts, sources = {}, []
    for sp in src_files:
        try:
            if sp.lower().endswith(".docx") or sp.lower().endswith(".pdf") or sp.lower().endswith((".md", ".tex", ".txt", ".markdown")):
                d = ev.load_own(sp, os.path.join(a.work, "src%d" % len(sources)))
        except SystemExit as e:
            print("WARNING: source %s skipped: %s" % (os.path.basename(sp), str(e)[:100]))
            continue
        except Exception as e:
            print("WARNING: source %s skipped (%s)" % (os.path.basename(sp), type(e).__name__))
            continue
        text = d["full_text"][:300000]
        r, sc = match_source(text, os.path.basename(sp), recs)
        if r is None:
            r = bib.new_record("source")
            first = next((s["text"] for s in d["sentences"][:3] if 8 < len(s["text"]) < 200), os.path.splitext(os.path.basename(sp))[0])
            r["title"], r["type"], r["id"] = first, "other", "doc_" + re.sub(r"[^A-Za-z0-9]+", "", os.path.splitext(os.path.basename(sp))[0])[:20]
            r["parse"] = {"confidence": 0.2, "missing": ["authors", "year", "venue: metadata unknown, taken from nothing"]}
            recs.append(r)
            note_meta = "no library record matched: metadata unknown"
        else:
            note_meta = "matched to library record (similarity %.2f)" % sc
        texts[r["id"]] = texts.get(r["id"], "") + "\n" + text
        r["has_source_text"] = True
        sources.append({"file": os.path.basename(sp), "entry": r["id"], "note": note_meta, "words": len(text.split())})
    uniq_ids(recs)
    enriched = {}
    if a.online:
        enriched = ev.enrich([r for r in recs if r["id"] not in texts], timeout=10)
    for r in recs:
        texts[r["id"]] = (r["title"] + ". " + (r.get("abstract") or "") + "\n" + texts.get(r["id"], "")).strip()
    entries = {r["id"]: r for r in recs}
    cands = {k: ev.candidates(t) for k, t in texts.items()}
    task = task_info(case, roots)
    lang = task["lang"] or nlib.detect_lang((own["text"] or " ".join(r["title"] for r in recs))[:3000])
    M = {"version": VERSION, "own": own, "entries": entries, "texts": texts, "candidates": cands, "sources": sources, "libs": lib_info, "task": task, "lang": lang, "enriched": enriched,
         "case_id": (find_key(case, ["case_id", "caseId"]) or find_key(case, ["id"])) if case else None, "case": case, "notes": note}
    jsave(os.path.join(a.work, "materials.json"), M)
    if not os.path.isfile(os.path.join(a.work, "ops.json")):
        jsave(os.path.join(a.work, "ops.json"), empty_ops())
    return M


def au_name(x):
    return x["literal"] or ((x["family"] + x["given"]) if x.get("zh") else x["family"])


def text_class(M, k):
    t = M["texts"].get(k, "")
    r = M["entries"][k]
    n = nlib.wcount(t) - nlib.wcount(r["title"])
    if r.get("has_source_text") and n > 400:
        return "full text"
    return "abstract" if n >= 40 else ("title only" if n < 8 else "short text")


def brief(work, out, full=False):
    M, ops = load(work)
    own, E = M["own"], M["entries"]
    L = []
    L.append("# Evidence brief (generated; the facts here are what the draft may rest on)\n")
    t = M["task"]
    L.append("## Task\n- language: %s | length hint: %s | style hint: %s\n%s\n" % (M["lang"], t["length"] or "none", t["style"] or "none", ("```\n" + t["text"][:1500] + "\n```") if t["text"] else "- no task.md found"))
    L.append("## Own material (%s)\n- sections: %s\n- figures/tables: %s" % (", ".join(own["files"]) or "NONE", "; ".join(own["sections"][:14]) or "(none)", "; ".join("%s: %s" % (v["label"], v["caption"][len(v["label"]):].lstrip(" .:：、-").strip()[:70]) for v in list(own["figures"].values())[:14]) or "(none)"))
    resl = [s for s in own["sentences"] if not ev.FIG.match(s["text"]) and re.search(r"result|experiment|evaluation|conclusion|discussion|结果|实验|结论|讨论|评估", s["section"], re.I) and re.search(r"\d", s["text"])]
    L.append("- result sentences with numbers (%d): " % len(resl))
    for s in resl[:12]:
        L.append("  - %s [%s] %s" % (s["id"], s["section"][:24], s["text"][:200]))
    L.append("\n## Library (%d entries; text: %s)" % (len(E), Counter(text_class(M, k) for k in E)))
    L.append("key | authors year | title | text | evidence candidates")
    for k, r in E.items():
        au = "; ".join(au_name(x) for x in r["authors"][:2]) + (" et al." if len(r["authors"]) > 2 else "")
        c = Counter(x["kind"] for x in M["candidates"].get(k, []))
        L.append("%s | %s %s | %s | %s | %s" % (k, au or "?", r["year"] or "?", r["title"][:70], text_class(M, k), ", ".join("%s %d" % kv for kv in c.items()) or "-"))
    if full:
        L.append("\n## Source evidence (verbatim sentences you may quote; `show --entry KEY` for all)")
        shown = 0
        for k in E:
            if shown >= (14 if len(E) > 14 else len(E)):
                L.append("... %d more entries: use `show W --entry KEY`" % (len(E) - shown))
                break
            L.append("### %s [%s]" % (k, text_class(M, k)))
            for c in M["candidates"].get(k, [])[:6]:
                L.append("- %s: %s" % (c["kind"], c["text"][:260]))
            shown += 1
    if M["sources"]:
        L.append("\n## Source documents\n" + "\n".join("- %s -> %s (%s, %d words)" % (s["file"], s["entry"], s["note"], s["words"]) for s in M["sources"]))
    issues = []
    if not own["sentences"]:
        issues.append("no own material was found: contributions cannot be bound to the author's results; ask for it or mark every contribution as unverifiable")
    if not E:
        issues.append("the library is empty: related work cannot be written from sources; do not invent references")
    no_text = [k for k in E if text_class(M, k) in ("title only", "short text")]
    if no_text:
        issues.append("%d entries have no abstract/text (%s): they can be cited for existence only, not for what they found; `run --online` tries to fetch abstracts by DOI / arXiv id" % (len(no_text), ", ".join(no_text[:8])))
    meta = [k for k, r in E.items() if r["parse"].get("missing")]
    if meta:
        L.append("\n## Metadata gaps\n" + "\n".join("- %s: missing %s" % (k, ", ".join(E[k]["parse"]["missing"])) for k in meta[:12]))
    if issues:
        L.append("\n## Material limits\n" + "\n".join("- " + x for x in issues))
    txt = "\n".join(L) + "\n"
    wtext(os.path.join(out, "brief.md"), txt)
    print(txt if full else "")
    print("[brief written to %s]" % os.path.join(out, "brief.md"))
    print("Next: write decisions (`ingest`: claim / group / gap / contribution blocks) and the draft (Markdown, citations as [@key]); then `check`, then `build`.")


def cmd_show(a):
    M, ops = load(a.work)
    if a.own or not a.entry:
        o = M["own"]
        print("own files: %s | sections: %s" % (o["files"], "; ".join(o["sections"])))
        for k, v in o["figures"].items():
            print("  %s %s" % (k, v["caption"][:160]))
        for s in o["sentences"][: a.limit]:
            print("%s [%s] %s" % (s["id"], s["section"][:20], s["text"][:220]))
        return
    for key in re.split(r"[,\s]+", a.entry):
        if key not in M["entries"]:
            print("unknown entry %s (keys: %s ...)" % (key, ", ".join(list(M["entries"])[:8])))
            continue
        r = M["entries"][key]
        print("## %s | %s | %s | %s %s | DOI %s | text: %s" % (key, "; ".join(au_name(x) for x in r["authors"][:4]), r["title"], r["container"], r["year"], r["doi"] or "-", text_class(M, key)))
        for c in M["candidates"].get(key, []):
            print("  [%s] %s" % (c["kind"], c["text"]))
        print("  claims in ledger: %s" % ([c["id"] + (" (verified)" if c["verified"] else "") for c in ops["claims"] if c["key"] == key] or "none"))
        if a.full:
            print(M["texts"][key][:6000])


# ------------------------------------------------------------------------------------------------ ingest
FIELD = re.compile(r"^\s*(?:[-*]\s*)?([A-Za-z_]+)\s*[:：]\s*(.*)$")


def parse_blocks(text):
    recs, cur, key = [], None, None
    for ln in text.splitlines():
        s = ln.rstrip()
        if re.match(r"^\s*```\w*\s*$", s):
            continue
        m = re.match(r"^\s*[#=*]{2,}\s*(claim|group|gap|contribution|contrib|meta)\b\s*(.*?)[*=#]*\s*$", s, re.I)
        if m:
            cur = {"kind": {"contrib": "contribution"}.get(m.group(1).lower(), m.group(1).lower()), "target": m.group(2).strip(), "f": {}}
            recs.append(cur)
            key = None
            continue
        if cur is None:
            continue
        mk = FIELD.match(s)
        if mk and mk.group(1).lower() in ("kind", "text", "quote", "title", "dimension", "members", "axes", "takeaway", "type", "statement", "from", "evidence", "addresses", "scope", "doi", "year", "authors", "container", "volume", "issue", "pages", "publisher", "abstract", "note"):
            key = mk.group(1).lower()
            cur["f"][key] = mk.group(2).strip()
        elif key and s.strip():
            cur["f"][key] += ("\n" if key == "evidence" else " ") + s.strip()
    return recs


def keys_list(v):
    return [k.strip().lstrip("@") for k in re.split(r"[,;]", v or "") if k.strip()]


def unquote(s):
    s = (s or "").strip()
    return re.sub(r"^[\"“'‘]+|[\"”'’]+$", "", s).strip()


def cmd_ingest(a):
    M, ops = load(a.work)
    text = sys.stdin.read() if (not a.file or a.file == "-") else rtext(a.file)
    blocks = parse_blocks(text)
    if not blocks:
        raise SystemExit("no blocks found: '=== claim KEY', '=== group G1', '=== gap G1', '=== contribution C1', '=== meta KEY' followed by key: value lines")
    own = M["own"]
    idf = ev.Idf(list(M["texts"].values()) + [own["text"]])
    n, msgs, bad = Counter(), [], 0
    for b in blocks:
        k, f, tgt = b["kind"], b["f"], b["target"]
        if k == "claim":
            key = tgt.strip().lstrip("@")
            kind = (f.get("kind") or "").lower()
            if key not in M["entries"] or kind not in KINDS:
                msgs.append("claim %s: unknown entry or kind '%s' (kinds: %s)" % (key, kind, ", ".join(KINDS)))
                bad += 1
                continue
            quote = unquote(f.get("quote"))
            src = M["texts"][key]
            if not quote or not ev.verify_quote(quote, src):
                msgs.append("claim %s/%s REJECTED: the quote is not verbatim in the source text (%s)%s" % (key, kind, text_class(M, key), "" if quote else ": no quote given"))
                bad += 1
                continue
            para = f.get("text") or quote
            miss = [x for x in ev.numbers_of(para) if x not in ev.numbers_in_text(src)]
            if miss:
                msgs.append("claim %s/%s REJECTED: number(s) %s in the statement are not in the source" % (key, kind, miss))
                bad += 1
                continue
            cid = "%s:%s" % (key, kind)
            ops["claims"] = [c for c in ops["claims"] if c["id"] != cid]
            ops["claims"].append({"id": cid, "key": key, "kind": kind, "text": para, "quote": quote, "verified": True})
            n["claim"] += 1
        elif k == "group":
            gid = tgt or f.get("title", "G?")
            members = keys_list(f.get("members"))
            unk = [x for x in members if x not in M["entries"]]
            if unk or len(members) < 2:
                msgs.append("group %s REJECTED: %s" % (gid, ("unknown entries %s" % unk) if unk else "a group needs at least two works to compare"))
                bad += 1
                continue
            ops["groups"] = [g for g in ops["groups"] if g["id"] != gid]
            ops["groups"].append({"id": gid, "title": f.get("title", ""), "dimension": f.get("dimension", ""), "members": members, "axes": f.get("axes", ""), "takeaway": f.get("takeaway", "")})
            n["group"] += 1
        elif k == "gap":
            gid = tgt or "G?"
            typ = (f.get("type") or "limitation").lower()
            src, probs = [], []
            for item in keys_list(f.get("from")):
                cid = item if ":" in item else None
                if cid:
                    c = next((c for c in ops["claims"] if c["id"] == cid), None)
                    if not c:
                        probs.append("claim %s not in the ledger (add `=== claim` first)" % cid)
                    else:
                        src.append(cid)
                elif item in M["entries"]:
                    lim = [c for c in ops["claims"] if c["key"] == item and c["kind"] == "limitation"]
                    auto = [c for c in M["candidates"].get(item, []) if c["kind"] == "limitation"]
                    if lim:
                        src += [c["id"] for c in lim]
                    elif auto:
                        src.append("%s:limitation(auto)" % item)
                    else:
                        probs.append("%s has no limitation statement in its text" % item)
                else:
                    probs.append("unknown entry %s" % item)
            if typ != "judgement" and not src:
                msgs.append("gap %s REJECTED: type '%s' needs `from:` claims or entries whose limitation it rests on (%s); use type: judgement for the author's own judgement" % (gid, typ, "; ".join(probs) or "none given"))
                bad += 1
                continue
            ops["gaps"] = [g for g in ops["gaps"] if g["id"] != gid]
            ops["gaps"].append({"id": gid, "type": typ, "statement": f.get("statement", ""), "from": src})
            for p in probs:
                msgs.append("gap %s: %s" % (gid, p))
            n["gap"] += 1
        elif k == "contribution":
            cid = tgt or "C?"
            anchors = [x.strip(" -*") for x in re.split(r"\n|\s\|\s", f.get("evidence", "")) if x.strip(" -*")]
            res = []
            for an in anchors:
                ok, detail = ev.resolve_anchor(an, own)
                res.append({"anchor": an, "ok": ok, "detail": detail})
            ops["contributions"] = [c for c in ops["contributions"] if c["id"] != cid]
            ops["contributions"].append({"id": cid, "statement": f.get("statement", ""), "anchors": res, "addresses": keys_list(f.get("addresses")), "scope": f.get("scope", "")})
            for r in res:
                if not r["ok"]:
                    msgs.append("contribution %s: anchor '%s' -> %s" % (cid, r["anchor"][:50], r["detail"]))
            if not res:
                msgs.append("contribution %s: no evidence anchors given (the check will try to match the own material by wording)" % cid)
            n["contribution"] += 1
        elif k == "meta":
            key = tgt.strip().lstrip("@")
            if key not in M["entries"]:
                msgs.append("meta %s: unknown entry" % key)
                bad += 1
                continue
            r = M["entries"][key]
            for fld in ("title", "year", "doi", "container", "volume", "issue", "pages", "publisher"):
                if f.get(fld):
                    r[fld] = f[fld]
            if f.get("authors"):
                r["authors"] = bib.split_authors(f["authors"])
            if f.get("abstract"):
                r["abstract"] = f["abstract"]
                M["texts"][key] = r["title"] + ". " + f["abstract"] + "\n" + M["texts"][key]
                M["candidates"][key] = ev.candidates(M["texts"][key])
            r["corrected"] = True
            ops["meta"].append({"entry": key, "fields": sorted(k2 for k2 in f if f[k2])})
            n["meta"] += 1
    jsave(os.path.join(a.work, "ops.json"), ops)
    jsave(os.path.join(a.work, "materials.json"), M)
    print("recorded: " + ", ".join("%s %d" % kv for kv in n.items()) + (" | rejected %d" % bad if bad else ""))
    for m in msgs[:25]:
        print("  " + m)
    sys.exit(2 if bad else 0)


# ------------------------------------------------------------------------------------------------ check
def clauses_of(text):
    """[(clause text, [keys])]: a sentence with several citation markers is split at the markers, each clause is checked against the works its own marker cites.
    A sentence that opens with a short narrative marker ("Ma et al. [@ma2023] built ...") stays one clause for that marker."""
    ms = list(lint.PANDOC.finditer(text)) + list(lint.LATEXC.finditer(text))
    ms.sort(key=lambda m: m.start())
    if len(ms) <= 1:
        return [(lint.strip_markup(text), lint.keys_in(text))]
    segs, prev = [], 0
    for m in ms:
        segs.append([text[prev:m.start()], lint.keys_in(m.group(0))])
        prev = m.end()
    tail = text[prev:]
    if len(segs[0][0].split()) < 5 and not CJKRE.search(segs[0][0]) and len(segs) > 1:
        segs[1][0] = segs[0][0] + " " + segs[1][0]
        segs[1][1] = segs[0][1] + segs[1][1]
        segs = segs[1:]
    if tail.strip(" .。;；,，") and segs:
        segs[-1][0] += tail
    out = [(lint.strip_markup(t), k) for t, k in segs]
    return [(t, k) for t, k in out if t]


CJKRE = re.compile(r"[㐀-鿿]")


def issue(out, code, sev, msg, sid=None, part=None, **kw):
    out.append({"code": code, "severity": sev, "sentence": sid, "part": part, "message": msg, **kw})


def run_check(M, ops, draft_text, task_len=None):
    D = lint.parse_draft(draft_text)
    E, own = M["entries"], M["own"]
    idf = ev.Idf(list(M["texts"].values()) + [own["text"]])
    iss, rows = [], []
    sents = D["sentences"]
    roles = {p["id"]: p["role"] for p in D["paragraphs"]}
    if not any(x["keys"] for x in sents):
        if re.search(r"\[\d+(?:\s*[,–-]\s*\d+)*\]", draft_text) or re.search(r"\([A-Z][A-Za-z\-]+(?: et al\.?)?,? (?:19|20)\d{2}[a-z]?\)", draft_text):
            issue(iss, "markers_without_keys", "error", "the draft cites with numbers or (Author, year) but not with library keys: write citations as [@key] so every statement can be bound to its source (build renumbers or converts them)", None, "structure")
    # parts present
    present = {p["role"] for p in D["paragraphs"]}
    for need, label in (("background", "research background"), ("related", "related work"), ("gap", "research gap"), ("contribution", "contributions")):
        if need not in present:
            issue(iss, "missing_part", "error", "no %s part found (headings, <!--part:%s--> tags or wording)" % (label, need), part=need)
    claims_by_key = defaultdict(list)
    for c in ops["claims"]:
        claims_by_key[c["key"]].append(c)

    def src_text(k):
        t = M["texts"].get(k, "")
        return t + "\n" + "\n".join(c["quote"] for c in claims_by_key.get(k, []))

    def has_text(k):
        return text_class(M, k) in ("abstract", "full text", "short text") and nlib.wcount(M["texts"].get(k, "")) - nlib.wcount(E[k]["title"]) >= 25 if k in E else False
    cited_all = []
    gap_sents, contrib_sents = [], []
    for s in sents:
        role = s["role"]
        kind = lint.sentence_kind(s, role)
        s["kind"] = kind
        z = lint.is_zh(s["plain"])
        for k in s["keys"]:
            cited_all.append(k)
            if k not in E:
                issue(iss, "unknown_key", "error", "cites '%s', which is not in the library (do not cite what the materials do not contain)" % k, s["id"], role)
        keys = [k for k in s["keys"] if k in E]
        if kind == "gap" or (role == "gap" and (lint.GAP_ZH if z else lint.GAP_EN).search(s["plain"])):
            gap_sents.append(s)
        if kind == "contribution":
            contrib_sents.append(s)
        row = {"sentence": s["id"], "part": role, "kind": kind, "text": s["plain"], "keys": s["keys"], "status": "no citation", "score": None, "evidence": "", "numbers_ok": None}
        # ---- sentences about cited work: every clause is checked against the works its own marker cites
        if keys and kind != "contribution":
            own_voice = bool((lint.FIRST_ZH if z else lint.FIRST_EN).search(s["plain"]))
            worst, rank = None, {"supported": 0, "weak": 1, "unverifiable": 1, "unsupported": 2, "number_mismatch": 3}
            det = []
            for ctext, ckeys in clauses_of(s["text"]):
                ckeys = [k for k in ckeys if k in E]
                if not ckeys:
                    continue
                avail = [k for k in ckeys if has_text(k)]
                best, passage, bkey, per = 0.0, "", None, {}
                for k in avail:
                    sc, p = ev.best_support(ctext, src_text(k), idf)
                    per[k] = sc
                    if sc > best:
                        best, passage, bkey = sc, p, k
                nums = ev.numbers_of(ctext)
                cl_kinds = nlib.classify_sentence(ctext)
                specific = bool(nums) or "result" in cl_kinds or "limitation" in cl_kinds
                tag = "" if len(clauses_of(s["text"])) == 1 else " [clause: \"%s\"]" % ctext[:60]
                if not avail:
                    st_ = "unverifiable"
                    if specific:
                        issue(iss, "unverifiable_claim", "warn", "makes a specific claim about %s but no text of the cited work is available (title only): cite for existence only or supply the abstract / PDF%s" % (", ".join(ckeys), tag), s["id"], role, keys=ckeys)
                else:
                    if best >= SUP_OK:
                        st_ = "supported"
                    elif best >= SUP_WEAK:
                        st_ = "weak"
                        issue(iss, "weak_support", "warn", "wording overlaps its source only weakly (%.2f): check it says what %s says. Closest passage: \"%s\"%s" % (best, bkey, passage[:140], tag), s["id"], role, keys=ckeys, score=round(best, 2))
                    else:
                        st_ = "unsupported"
                        issue(iss, "unsupported_statement", "error", "does not match the text of the work(s) it cites (best overlap %.2f with %s): rewrite from the source or cite another work. Closest passage: \"%s\"%s" % (best, bkey, passage[:140], tag), s["id"], role, keys=ckeys, score=round(best, 2))
                    union = set()
                    for k in avail:
                        union |= ev.numbers_in_text(src_text(k))
                    if nums and not own_voice:
                        miss = [x for x in nums if x not in union]
                        if miss:
                            row["numbers_ok"] = False
                            st_ = "number_mismatch"
                            issue(iss, "number_not_in_source", "error", "number(s) %s do not occur in the cited work(s) %s%s" % (miss, ", ".join(avail), tag), s["id"], role, keys=ckeys, numbers=miss)
                        else:
                            row["numbers_ok"] = row["numbers_ok"] is not False
                            far = [x for x in nums if x not in ev.numbers_in_text(passage)] if passage else []
                            if far and best >= SUP_WEAK:
                                issue(iss, "number_from_other_passage", "warn", "number(s) %s occur in the cited work but not in the passage this clause matches (\"%s\"): check the number belongs to this finding%s" % (far, passage[:100], tag), s["id"], role, keys=ckeys, numbers=far)
                    srcall = " ".join(src_text(k) for k in avail)
                    strong = sorted({m.group(0).lower() for m in lint.STRONG_SRC.finditer(ctext) if m.group(0).lower() not in srcall.lower()})
                    if strong and not own_voice:
                        issue(iss, "overstated", "warn", "strong wording %s is not found in the cited work(s): check it is not stronger than the source%s" % (strong, tag), s["id"], role, keys=ckeys)
                    if "limitation" in cl_kinds or (role == "gap" and (lint.GAP_ZH if z else lint.GAP_EN).search(ctext)):
                        limtxt = " ".join([c["text"] + " " + c["quote"] for k in avail for c in claims_by_key.get(k, []) if c["kind"] == "limitation"] + [c["text"] for k in avail for c in M["candidates"].get(k, []) if c["kind"] == "limitation"])
                        ls, lp = ev.best_support(ctext, limtxt, idf) if limtxt.strip() else (0.0, "")
                        row["limitation_score"] = round(ls, 2)
                        if ls < LIM_OK and not (lint.JUDGE_ZH if z else lint.JUDGE_EN).search(s["plain"]):
                            issue(iss, "limitation_not_in_source", "error", "states a limitation of the cited work(s) that their text does not show (best overlap with a limitation passage %.2f): quote a limitation, or mark it as your own judgement ('we argue ...')%s" % (ls, tag), s["id"], role, keys=ckeys)
                    if len(ckeys) >= 3:
                        for k, sc in per.items():
                            if sc < 0.12:
                                issue(iss, "citation_padding", "warn", "%s is cited here but its text shares almost nothing with the sentence (%.2f)" % (k, sc), s["id"], role, keys=[k])
                det.append({"clause": ctext[:120], "keys": ckeys, "status": st_, "score": round(best, 2) if avail else None, "evidence": passage[:300], "best_key": bkey})
                if worst is None or rank[st_] > rank[worst]:
                    worst = st_
                    row["score"], row["evidence"], row["best_key"] = (round(best, 2) if avail else None), passage[:300], bkey
            row["status"] = worst or "no citation"
            row["clauses"] = det
        elif role in ("related",) and not keys and kind in ("plain", "own") and not s["gap"] and len(s["plain"].split()) > 6 and not (lint.FIRST_ZH if z else lint.FIRST_EN).search(s["plain"]):
            pass
        rows.append(row)
    # ---- background
    bg = [p for p in D["paragraphs"] if p["role"] == "background"]
    first_sent = sents[0] if sents else None
    for i, p in enumerate(bg):
        allspecific = 0
        for s in p["sentences"]:
            hits = lint.filler_hits(s["plain"])
            if hits:
                firstp = (p is bg[0] and s is p["sentences"][0])
                issue(iss, "filler", "error" if firstp else "warn", "filler statement (%s...): replace it with the concrete research thread and the specific unresolved problem" % s["plain"][:60], s["id"], "background")
            z = lint.is_zh(s["plain"])
            if not s["keys"] and not (lint.FIRST_ZH if z else lint.FIRST_EN).search(s["plain"]):
                cl_ = nlib.classify_sentence(s["plain"])
                if ("result" in cl_ and re.search(r"\d", s["plain"])) or re.search(r"\b(?:has|have) been (?:shown|reported|demonstrated|proposed)|studies (?:have )?(?:show|shown|report)|研究表明|已有研究|有研究", s["plain"]):
                    issue(iss, "unbound_claim", "warn", "background claim without a citation: bind it to a source or mark it as the author's judgement", s["id"], "background")
            if (lint.IMPORTANCE_ZH if z else lint.IMPORTANCE_EN).search(s["plain"]) and not s["keys"] and not re.search(r"\d", s["plain"]):
                allspecific += 0
            else:
                allspecific += 1
        if allspecific == 0 and len(p["sentences"]) >= 2:
            issue(iss, "importance_only", "warn", "paragraph %s only says the topic is important / popular, with no concrete thread, number or source" % p["id"], p["sentences"][0]["id"], "background")
    if bg:
        txt = " ".join(s["plain"] for p in bg for s in p["sentences"])
        zz = lint.is_zh(txt)
        concrete = [s for p in bg for s in p["sentences"] if ((lint.GAP_ZH if zz else lint.GAP_EN).search(s["plain"]) or "limitation" in nlib.classify_sentence(s["plain"])) and (s["keys"] or re.search(r"\d", s["plain"]))]
        if not concrete and not any(p["role"] == "gap" for p in D["paragraphs"]):
            issue(iss, "no_concrete_problem", "warn", "the background never names a specific unresolved problem or constraint backed by a source or a number", None, "background")
        nk = len({k for p in bg for s in p["sentences"] for k in s["keys"]})
        if nk < 2:
            issue(iss, "thin_background_sources", "warn", "the background cites %d distinct work(s): ground the research thread in at least two" % nk, None, "background")
    # ---- related work
    rel = [p for p in D["paragraphs"] if p["role"] == "related"]
    ZH = lint.is_zh(draft_text)
    for p in rel:
        ks = [s for s in p["sentences"] if s["keys"]]
        run_, seq_start = 0, None
        for s in p["sentences"]:
            starts = bool(re.match(r"^\s*(?:\[@|[A-Z][\w\-]+(?:\s+et al\.?|\s+and\s+[A-Z][\w\-]+)?\s*(?:\[@|\(|,|\s+(?:[a-z]+ed|[a-z]+ied|built|found|showed|ran|made|took|gave|chose|wrote|saw|did|began|trained|used)\b))|^\s*[一-鿿]{2,4}(?:等)?(?:\[@|（|\()", s["text"]))
            comp = (lint.COMPARE_ZH if ZH else lint.COMPARE_EN).search(s["plain"])
            if s["keys"] and starts and not comp:
                run_ += 1
                seq_start = seq_start or s["id"]
                if run_ == 3:
                    issue(iss, "sequential_summary", "warn", "three consecutive sentences each summarise one work without comparing it to another (starts at %s): organise by problem / method / data dimension and say how the works differ" % seq_start, s["id"], "related")
            else:
                run_, seq_start = 0, None
        if len(p["sentences"]) >= 3 and not any((lint.COMPARE_ZH if ZH else lint.COMPARE_EN).search(s["plain"]) for s in p["sentences"]):
            issue(iss, "no_comparison", "warn", "paragraph %s lists works but never compares them (no contrast / shared-limitation wording)" % p["id"], p["sentences"][0]["id"], "related")
        if len({k for s in p["sentences"] for k in s["keys"]}) < 2 and len(p["sentences"]) >= 2:
            issue(iss, "single_work_paragraph", "info", "paragraph %s rests on fewer than two works: a group needs a comparison" % p["id"], p["sentences"][0]["id"], "related")
    if rel and len(rel) < 2 and not any(p["group"] for p in rel):
        issue(iss, "ungrouped", "warn", "related work is one paragraph: group it by problem, method route or data / evaluation setting", None, "related")
    tagged_groups = {p["group"] for p in rel if p["group"]}
    cited_keys = set(cited_all)
    for g in ops["groups"]:
        missing = [m for m in g["members"] if m not in cited_keys]
        if missing:
            issue(iss, "group_member_not_cited", "warn", "group %s ('%s') lists %s but the draft does not cite them" % (g["id"], g["title"], ", ".join(missing[:6])), None, "related")
        if g["id"] not in tagged_groups and tagged_groups:
            issue(iss, "group_not_in_draft", "info", "group %s has no paragraph tagged <!--group:%s-->" % (g["id"], g["id"]), None, "related")
    # ---- gap
    if not gap_sents:
        issue(iss, "no_gap_statement", "error", "no research-gap sentence found: state it (tag it <!--gap:G1-->) and derive it from cited limitations", None, "gap")
    table_gap = []
    for s in gap_sents:
        z = lint.is_zh(s["plain"])
        par = next(p for p in D["paragraphs"] if p["id"] == s["par"])
        keys = [k for k in s["keys"] if k in E]
        prev = [k for q in par["sentences"] for k in q["keys"] if k in E]
        pool = list(dict.fromkeys(keys + prev))
        led = next((g for g in ops["gaps"] if g["id"] == s.get("gap")), None)
        if s.get("gap") and not led:
            issue(iss, "gap_tag_unknown", "warn", "tag gap:%s is not in the ledger (add `=== gap %s`)" % (s["gap"], s["gap"]), s["id"], "gap")
        limtxt = []
        for k in pool:
            limtxt += [c["text"] + " " + c["quote"] for c in claims_by_key.get(k, []) if c["kind"] == "limitation"] + [c["text"] for c in M["candidates"].get(k, []) if c["kind"] == "limitation"]
        ls, lp = ev.best_support(s["plain"], " ".join(limtxt), idf) if limtxt else (0.0, "")
        judge = bool((lint.JUDGE_ZH if z else lint.JUDGE_EN).search(s["plain"]))
        absent = (lint.ABSENCE_ZH if z else lint.ABSENCE_EN).search(s["plain"])
        status = "derived" if (ls >= 0.15 or (led and led["from"])) and pool else ("judgement" if judge or (led and led["type"] == "judgement") else "unsupported")
        table_gap.append({"gap": s.get("gap"), "sentence": s["id"], "text": s["plain"], "cited": pool, "best_limitation_overlap": round(ls, 2), "limitation_passage": lp[:240], "ledger_from": led["from"] if led else [], "status": status})
        if status == "unsupported":
            issue(iss, "gap_not_derived", "error", "the gap is not derived from any limitation of the works it cites (overlap %.2f): cite the works whose limitation it is and quote it, or mark it as your judgement" % ls, s["id"], "gap")
        if led and led["type"] == "judgement" and not judge:
            issue(iss, "gap_unmarked_judgement", "warn", "ledger says this gap is your judgement; the sentence should say so ('we argue ...')", s["id"], "gap")
        if absent:
            hedged = re.search(r"to the best of our knowledge|据我们所知", s["plain"], re.I)
            scoped = re.search(r"\b(?:in|for|on|within|under)\b [^,.]{6,}|在.{3,}(?:中|下|上)|针对", s["plain"])
            issue(iss, "absence_claim", "warn" if not (hedged and scoped) else "info", "claims that nothing exists ('%s'): scope it (field, setting, period) and confirm by search; the materials cannot prove absence" % absent.group(0), s["id"], "gap")
    # ---- contributions
    if not contrib_sents:
        issue(iss, "no_contribution", "error", "no contribution statement found (tag each <!--contrib:C1-->)", None, "contribution")
    if len(contrib_sents) > 6:
        issue(iss, "too_many_contributions", "warn", "%d contribution sentences: compress to what the evidence supports" % len(contrib_sents), None, "contribution")
    table_c = []
    gap_texts = [g["plain"] for g in gap_sents]
    for s in contrib_sents:
        z = lint.is_zh(s["plain"])
        led = next((c for c in ops["contributions"] if c["id"] == s.get("contrib")), None)
        if s.get("contrib") and not led:
            issue(iss, "contribution_tag_unknown", "warn", "tag contrib:%s is not in the ledger (add `=== contribution %s` with evidence anchors)" % (s["contrib"], s["contrib"]), s["id"], "contribution")
        auto = ev.best_own(s["plain"], own, idf)
        best_sc = auto[0][0] if auto else 0.0
        nums = ev.numbers_of(s["plain"])
        miss = [x for x in nums if x not in own["numbers"] and x not in ev.numbers_in_text(" ".join(c["quote"] for c in ops["claims"]))]
        if own["sentences"] and miss:
            issue(iss, "contribution_number_not_in_own_material", "error", "number(s) %s do not occur in your own material: a contribution may only state numbers your results show" % miss, s["id"], "contribution", numbers=miss)
        anchors = led["anchors"] if led else []
        okanch = [x for x in anchors if x["ok"]]
        for x in anchors:
            if not x["ok"]:
                issue(iss, "anchor_not_found", "error", "evidence anchor '%s' does not resolve: %s" % (x["anchor"][:60], x["detail"]), s["id"], "contribution")
        if not okanch and (best_sc < 0.30 or not own["sentences"]):
            issue(iss, "contribution_without_evidence", "error", "no evidence in the own material backs this contribution (best wording match %.2f): add evidence anchors (Fig./Table/Sec/N:/Q:) or drop the claim" % best_sc, s["id"], "contribution")
        over = (lint.OVERCLAIM_ZH if z else lint.OVERCLAIM_C).findall(s["plain"])
        if over:
            comparative = any(re.match(r"^(?:Fig|Tab|图|表|N:|num)", x["anchor"], re.I) for x in okanch)
            if not comparative:
                issue(iss, "overclaim", "error", "strong wording %s without a table / figure / number anchor that shows the comparison" % sorted(set(o.lower() if isinstance(o, str) else o for o in over))[:4], s["id"], "contribution")
        if re.search(r"\bfirst\b|首次|首个|to the best of our knowledge|据我们所知", s["plain"], re.I):
            issue(iss, "priority_claim", "warn", "priority claim ('first'): the materials cannot prove it; keep it only if a search supports it, and list it for human confirmation", s["id"], "contribution")
        if gap_texts:
            gsc = max(ev.overlap(ev.toks(s["plain"]), set(ev.toks(g)), idf) for g in gap_texts)
        else:
            gsc = 0.0
        addressed = led["addresses"] if led else []
        if gap_texts and gsc < 0.10 and not addressed:
            issue(iss, "contribution_without_gap", "info", "no gap sentence shares wording with this contribution: say which gap it fills (`addresses:` in the ledger)", s["id"], "contribution")
        table_c.append({"contribution": s.get("contrib"), "sentence": s["id"], "text": s["plain"], "anchors": anchors, "auto_match": [{"score": round(x[0], 2), "own": x[1], "text": x[2][:200]} for x in auto], "numbers": nums, "numbers_missing": miss,
                        "addresses": addressed, "gap_overlap": round(gsc, 2), "status": "evidenced" if (okanch or best_sc >= 0.30) and not miss else "unsupported"})
    for g in ops["gaps"]:
        if not any(s.get("gap") == g["id"] for s in sents):
            issue(iss, "ledger_gap_not_in_draft", "info", "ledger gap %s is not tagged in the draft" % g["id"], None, "gap")
    for c in ops["contributions"]:
        if not any(s.get("contrib") == c["id"] for s in sents):
            issue(iss, "ledger_contribution_not_in_draft", "warn", "ledger contribution %s is not tagged in the draft: the draft may claim something the ledger does not evidence, or omit it" % c["id"], None, "contribution")
    # ---- library coverage, metadata, duplicates
    uncited = [k for k in E if k not in cited_keys]
    years = [int(r["year"]) for r in E.values() if r["year"].isdigit()]
    ymax = max(years) if years else 0
    recent = [k for k in uncited if E[k]["year"].isdigit() and int(E[k]["year"]) >= ymax - 2]
    if uncited:
        issue(iss, "uncited_library_entries", "info", "%d of %d library entries are not cited: %s" % (len(uncited), len(E), ", ".join(uncited[:10])), None, "coverage", keys=uncited)
    if recent:
        issue(iss, "recent_work_not_cited", "warn", "recent work in the library is not cited (%s): cover current progress or say why it is out of scope" % ", ".join(recent[:8]), None, "coverage", keys=recent)
    for k in sorted(set(cited_all)):
        if k in E:
            miss = E[k]["parse"].get("missing") or []
            core = [m for m in miss if m.split(":")[0] in ("authors", "title", "year", "container", "publisher")]
            if miss:
                issue(iss, "metadata_missing", "warn" if core else "info", "%s lacks %s: the reference cannot be formatted completely; complete it (`meta`) or report it" % (k, ", ".join(miss)), None, "metadata", keys=[k])
            for m in verify.structural(E[k]):
                issue(iss, "metadata_structure", "warn", "%s: %s" % (k, m), None, "metadata", keys=[k])
    cl_, cands, guarded = dedupe.clusters([E[k] for k in E if k in cited_keys])
    for c in cl_:
        issue(iss, "duplicate_entries_cited", "warn", "the same work is cited under %d keys (%s): merge them" % (len(c["members"]), ", ".join(c["members"])), None, "metadata", keys=c["members"])
    # ---- length
    words = sum(nlib.wcount(s["plain"]) for s in sents)
    if task_len and words:
        zh = ZH
        n = words if not zh else sum(len(re.findall(r"[㐀-鿿]", s["plain"])) for s in sents)
        if n < 0.7 * task_len or n > 1.4 * task_len:
            issue(iss, "length", "warn", "draft has about %d %s; the task asks for about %d" % (n, "characters" if zh else "words", task_len), None, "structure")
    sev = Counter(i["severity"] for i in iss)
    return {"issues": iss, "rows": rows, "gaps": table_gap, "contributions": table_c, "stats": {"sentences": len(sents), "paragraphs": len(D["paragraphs"]), "words": words, "cited_keys": len(cited_keys), "library": len(E), "severity": dict(sev),
                                                                                    "parts": sorted(present)}, "draft": D, "cited_all": cited_all}


def cmd_check(a):
    M, ops = load(a.work)
    res = run_check(M, ops, rtext(a.draft), M["task"].get("length"))
    out = {k: v for k, v in res.items() if k != "draft"}
    jsave(os.path.join(a.work, "check.json"), out)
    st = res["stats"]
    print("draft: %d sentences in %d paragraphs (%d words) | parts: %s | cited %d of %d library entries | issues: %s" % (st["sentences"], st["paragraphs"], st["words"], ", ".join(st["parts"]), st["cited_keys"], st["library"], st["severity"]))
    order = {"error": 0, "warn": 1, "info": 2}
    for i in sorted(res["issues"], key=lambda x: (order[x["severity"]], x["code"], x["sentence"] or "")):
        if i["severity"] == "info" and not a.all:
            continue
        print("  %-5s %-34s %s%s" % (i["severity"], i["code"], (i["sentence"] + " ") if i["sentence"] else "", i["message"][:230]))
    c = Counter(r["status"] for r in res["rows"] if r["keys"])
    print("cited sentences: %s" % dict(c))
    print("gaps: %s | contributions: %s" % (Counter(g["status"] for g in res["gaps"]) or "none", Counter(c["status"] for c in res["contributions"]) or "none"))
    if st["severity"].get("error"):
        print("Fix the errors in the draft (or in the ledger), then `check` again; `build` still writes everything and lists what is open.")


# ------------------------------------------------------------------------------------------------ build
def author_year(r, narrative=False):
    au = r["authors"]
    zh = bool(bib.CJK.search(r["title"] or ""))
    nm = lambda x: x["literal"] or (x["family"] if not x.get("zh") else x["family"] + x["given"])
    if not au:
        who = (r["container"] or r["title"])[:30]
    elif len(au) == 1:
        who = nm(au[0])
    elif len(au) == 2:
        who = nm(au[0]) + ((" 和 " if zh else (" and " if narrative else " & ")) + nm(au[1]))
    else:
        who = nm(au[0]) + (" 等" if zh else " et al.")
    y = r["year"] or "n.d."
    return ("%s (%s)" % (who, y)) if narrative else ("%s, %s" % (who, y))


def convert_markers(text, order_keys, E, style):
    """[@a; @b] -> [1,2] / (Smith, 2020; Lee et al., 2019)"""
    nums = {k: i + 1 for i, k in enumerate(order_keys)}

    def repl(m):
        keys = [k.rstrip(".,;:") for k in lint.KEYRE.findall(m.group(1))]
        keys = [k for k in keys if k in E]
        if not keys:
            return m.group(0)
        if style == "apa7":
            before = text[max(0, m.start() - 60):m.start()]
            if len(keys) == 1:
                fam = (E[keys[0]]["authors"][0]["family"] if E[keys[0]]["authors"] else "")
                if fam and re.search(re.escape(fam) + r"(?:\s+et al\.?|\s+(?:and|&)\s+[A-Z][\w\-]+)?\s*$", before):
                    return "(%s)" % (E[keys[0]]["year"] or "n.d.")
            zh = bool(bib.CJK.search(E[keys[0]]["title"] or ""))
            return ("（%s）" if zh else "(%s)") % ("；" if zh else "; ").join(author_year(E[k]) for k in sorted(keys, key=lambda k: ((E[k]["authors"][0]["family"] if E[k]["authors"] else "").lower(), E[k]["year"])))
        return "[%s]" % cite.compress([nums[k] for k in keys], "–", 3, ",")
    t = lint.PANDOC.sub(repl, text)
    t = lint.LATEXC.sub(lambda m: repl(type("M", (), {"group": lambda self, i=0: "@" + ",@".join(x.strip() for x in m.group(1).split(",")), "start": lambda self: m.start()})()), t)
    return t


def contract_fields(case):
    oc = find_key(case, ["output_contract", "outputContract", "output_schema", "outputs"]) if case else None
    fields = []

    def add(x):
        if isinstance(x, str) and x not in fields:
            fields.append(x)
    items = oc if isinstance(oc, list) else (oc.get("fields") or oc.get("required") or oc.get("properties") or oc.get("required_fields") or [k for k in oc if k not in ("type", "description", "title", "version", "schema", "$schema", "additionalProperties")]) if isinstance(oc, dict) else []
    if isinstance(items, dict):
        items = list(items)
    for it in items:
        add(it if isinstance(it, str) else (it.get("name") or it.get("field") or it.get("key")) if isinstance(it, dict) else None)
    return fields


def derive_field(name, ctx):
    n = name.lower()
    words = set(re.split(r"[^a-z]+", n))

    def has(ascii_words=(), cjk=()):
        return bool(words & set(ascii_words)) or any(x in n for x in cjk)
    if n in ("status", "run_status", "state", "outcome") or has(("status",), ("状态",)):
        return True, ctx["status"]
    if n in ("manuscript", "text", "draft", "introduction", "intro", "target", "product", "deliverable", "target_product") or has(("product", "manuscript", "deliverable", "target", "draft", "introduction"), ("产物", "稿", "引言")):
        return True, {"files": [f for f in ctx["files"] if f.startswith("intro")], "text": ctx["final_text"], "word_count": ctx["words"]}
    if n in ("background",) or has(("background",), ("背景",)):
        return True, ctx["parts"].get("background", "")
    if has(("related",), ("相关工作",)):
        return True, ctx["parts"].get("related", "")
    if has(("gap", "gaps"), ("空白",)):
        return True, {"text": ctx["parts"].get("gap", ""), "derivations": ctx["check"]["gaps"]}
    if has(("contribution", "contributions"), ("贡献",)):
        return True, {"text": ctx["parts"].get("contribution", ""), "evidence": ctx["check"]["contributions"]}
    if has(("references", "bibliography", "citations"), ("参考文献", "引用")):
        return True, {"style": ctx["style"], "entries": ctx["refs"], "files": [f for f in ctx["files"] if f.startswith("references")]}
    if has(("source", "sources", "evidence", "provenance", "mapping"), ("来源", "映射")):
        return True, {"cited_sentences": ctx["check"]["rows"], "gaps": ctx["check"]["gaps"], "contributions": ctx["check"]["contributions"], "claims": ctx["ops"]["claims"], "groups": ctx["ops"]["groups"]}
    if has(("boundary", "boundaries", "limits", "limitations", "uncertainty", "uncertainties", "caveats", "review"), ("边界", "版本", "不确定", "确认")):
        return True, {"open_issues": ctx["open"], "human_review": ctx["review"], "uncertainty": ctx["uncertainty"], "check_summary": ctx["check"]["stats"]}
    if has(("files", "artifacts"), ()):
        return True, ctx["files"]
    return False, None


def cmd_build(a):
    M, ops = load(a.work)
    E = M["entries"]
    draft_text = rtext(a.draft)
    check = run_check(M, ops, draft_text, M["task"].get("length"))
    style = a.style or M["task"].get("style") or ("gbt7714" if M["lang"] == "zh" else "ieee")
    cited = [k for k in dict.fromkeys(check["cited_all"]) if k in E]
    unknown = [k for k in dict.fromkeys(check["cited_all"]) if k not in E]
    os.makedirs(a.out, exist_ok=True)
    final_body = convert_markers(draft_text, cited, E, style)
    final_body = tidy(lint.TAG.sub("", final_body))
    numeric = style != "apa7"
    order = cited if numeric else sorted(cited, key=lambda k: ((E[k]["authors"][0]["family"] if E[k]["authors"] else "").lower(), E[k]["year"], E[k]["title"].lower()))
    refs = []
    for i, k in enumerate(order, 1):
        line = fmt.format_entry(E[k], style, punct=a.punct)
        refs.append(("[%d] " % i if numeric else "") + line)
    heading = "参考文献" if M["lang"] == "zh" else "References"
    final_text = final_body.rstrip() + "\n\n## %s\n\n%s\n" % (heading, "\n".join(refs))
    files = []
    wtext(os.path.join(a.out, "intro.md"), final_text)
    files.append("intro.md")
    # docx
    blocks = []
    for b in re.split(r"\n\s*\n", final_text.strip()):
        mh = re.match(r"^(#{1,6})\s+(.+?)\s*$", b.strip())
        if mh and "\n" not in b.strip():
            blocks.append(("h1" if len(mh.group(1)) <= 2 else "h2", mh.group(2)))
        elif b.strip().startswith("[") and re.match(r"^\[\d+\]", b.strip()) and "\n" in b.strip():
            blocks += [("ref", x) for x in b.strip().split("\n")]
        elif b.strip() and heading in final_text and b.strip() in "\n".join(refs):
            blocks += [("ref", x) for x in b.strip().split("\n")]
        else:
            blocks.append(("p", re.sub(r"\s*\n\s*", " ", b.strip())))
    docxw.make(blocks, os.path.join(a.out, "intro.docx"))
    files.append("intro.docx")
    # latex: keys stay \cite keys, bibliography is the generated bib file
    tex = tidy(lint.TAG.sub("", draft_text))
    tex = lint.PANDOC.sub(lambda m: "\\cite{%s}" % ",".join(k.rstrip(".,;:") for k in lint.KEYRE.findall(m.group(1)) if k.rstrip(".,;:") in E), tex)
    tex_lines = []
    for b in re.split(r"\n\s*\n", tex.strip()):
        mh = re.match(r"^(#{1,6})\s+(.+?)\s*$", b.strip())
        if mh and "\n" not in b.strip():
            tex_lines.append("\\%ssection{%s}" % ("sub" * max(0, len(mh.group(1)) - 2), mh.group(2)))
        else:
            tex_lines.append(re.sub(r"\s*\n\s*", " ", b.strip()).replace("%", "\\%").replace("&", "\\&"))
    wtext(os.path.join(a.out, "intro.tex"), "% generated by intro-ledger; compile inside your paper with \\bibliography{references}\n" + "\n\n".join(tex_lines) + "\n")
    files.append("intro.tex")
    cited_recs = [E[k] for k in order]
    wtext(os.path.join(a.out, "references.%s.txt" % style), "\n".join(refs) + "\n")
    wtext(os.path.join(a.out, "references.bib"), fmt.to_bibtex(cited_recs))
    wtext(os.path.join(a.out, "references.ris"), fmt.to_ris(cited_recs))
    files += ["references.%s.txt" % style, "references.bib", "references.ris"]
    # evidence table
    rows = check["rows"]
    with open(os.path.join(a.out, "evidence_table.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["sentence", "part", "kind", "keys", "status", "overlap", "numbers_ok", "text", "closest_source_passage"])
        for r in rows:
            if r["keys"] or r["kind"] in ("gap", "contribution"):
                w.writerow([r["sentence"], r["part"], r["kind"], ";".join(r["keys"]), r["status"], r["score"] if r["score"] is not None else "", r["numbers_ok"] if r["numbers_ok"] is not None else "", r["text"], r["evidence"]])
    jsave(os.path.join(a.out, "evidence_table.json"), {"cited_sentences": [r for r in rows if r["keys"]], "gaps": check["gaps"], "contributions": check["contributions"], "claims": ops["claims"], "groups": ops["groups"], "gap_ledger": ops["gaps"], "contribution_ledger": ops["contributions"],
                                                      "sources": {k: {"title": E[k]["title"], "authors": [x["family"] or x["literal"] for x in E[k]["authors"]], "year": E[k]["year"], "doi": E[k]["doi"], "text_available": text_class(M, k)} for k in order}})
    files += ["evidence_table.csv", "evidence_table.json"]
    parts = {}
    for p in check["draft"]["paragraphs"]:
        parts.setdefault(p["role"], []).append(strip_for_part(p["text"], convert_markers, cited, E, style))
    parts = {k: "\n\n".join(v) for k, v in parts.items()}
    # open issues, review list, uncertainty
    errs = [i for i in check["issues"] if i["severity"] == "error"]
    warns = [i for i in check["issues"] if i["severity"] == "warn"]
    review = []
    for i in errs + warns:
        review.append({"kind": i["code"], "sentence": i["sentence"], "detail": i["message"][:300]})
    for g in check["gaps"]:
        if g["status"] == "judgement":
            review.append({"kind": "gap_is_author_judgement", "sentence": g["sentence"], "detail": "this gap rests on the author's judgement, not on a cited limitation: confirm it"})
    for c in check["contributions"]:
        if c["status"] != "evidenced":
            review.append({"kind": "contribution_not_evidenced", "sentence": c["sentence"], "detail": c["text"][:140]})
    unc = []
    notext = [k for k in order if text_class(M, k) in ("title only", "short text")]
    if notext:
        unc.append({"kind": "cited_without_text", "detail": "cited without any abstract / text to check against: %s" % ", ".join(notext)})
    if unknown:
        unc.append({"kind": "unknown_keys_left", "detail": "cited keys not in the library: %s (left unchanged in the text)" % ", ".join(unknown)})
    unc.append({"kind": "lexical_checks_only", "detail": "statement-to-source support is a lexical overlap screen over the abstract / text provided; it cannot judge meaning. Read the evidence table for every claim you rely on."})
    if not M["own"]["sentences"]:
        unc.append({"kind": "no_own_material", "detail": "no own material was provided: contributions could not be checked against results"})
    ver = {}
    if a.online:
        ver = verify.check_all([E[k] for k in order], online=True, timeout=10)
        jsave(os.path.join(a.out, "verification.json"), ver)
        files.append("verification.json")
        for k, v in ver.items():
            if v["status"] in ("mismatch", "not_found"):
                review.append({"kind": "reference_" + v["status"], "sentence": None, "detail": "%s: %s" % (k, "; ".join(v["details"])[:200])})
        if all(v["status"] == "unchecked" for v in ver.values()):
            unc.append({"kind": "references_unchecked", "detail": "online verification could not run (no network): references are not checked against any bibliographic source"})
    else:
        unc.append({"kind": "references_not_verified", "detail": "references were not looked up online (build --online): only their structure was checked"})
    status = "success" if not errs and cited and not unknown else "partial"
    ctx = {"status": status, "final_text": final_text, "words": check["stats"]["words"], "parts": parts, "check": check, "refs": refs, "files": files, "ops": ops, "open": [{"code": i["code"], "severity": i["severity"], "sentence": i["sentence"], "message": i["message"]} for i in check["issues"] if i["severity"] != "info"], "review": review, "uncertainty": unc, "style": style}
    with open(os.path.join(a.out, "traceability.md"), "w", encoding="utf-8") as fh:
        fh.write("# Traceability (generated)\n\n## Gaps -> cited limitations\n")
        for g in check["gaps"]:
            fh.write("- %s (%s): \"%s\"\n  - cites: %s | overlap with a limitation passage %.2f | ledger from: %s\n  - closest limitation passage: %s\n" % (g["gap"] or "untagged", g["status"], g["text"][:160], ", ".join(g["cited"]) or "none", g["best_limitation_overlap"], ", ".join(g["ledger_from"]) or "-", g["limitation_passage"][:200] or "-"))
        fh.write("\n## Contributions -> own evidence\n")
        for c in check["contributions"]:
            fh.write("- %s (%s): \"%s\"\n" % (c["contribution"] or "untagged", c["status"], c["text"][:160]))
            for x in c["anchors"]:
                fh.write("  - anchor %s: %s (%s)\n" % (x["anchor"][:60], "ok" if x["ok"] else "NOT FOUND", x["detail"][:100]))
            for x in c["auto_match"][:1]:
                fh.write("  - closest own sentence %s (%.2f): %s\n" % (x["own"], x["score"], x["text"][:150]))
        fh.write("\n## Statements about cited work\n")
        for r in rows:
            if r["keys"] and r["kind"] == "cited":
                fh.write("- %s [%s] %s -> %s | overlap %s\n" % (r["sentence"], ", ".join(r["keys"]), r["text"][:110], r["status"], r["score"]))
    wtext(os.path.join(a.out, "review_checklist.md"), "# Review checklist\n\nMachine-assisted draft: nothing here is approved by the author.\n\n" + ("\n".join("- [ ] %s %s: %s" % (r["kind"], r["sentence"] or "", r["detail"]) for r in review) or "- no open item") +
          "\n\n## Always confirm by hand\n- that every paraphrase of another work says what that work says (the overlap check is lexical)\n- priority and absence claims ('first', 'no study')\n- references with status unchecked / not_found\n")
    files += ["traceability.md", "review_checklist.md"]
    case = M.get("case")
    fields = contract_fields(case)
    answers = jload(a.answers, {}) if a.answers else {}
    result = {"case_id": M.get("case_id")}
    unfilled = []
    for fld in fields:
        if fld == "case_id":
            continue
        if fld in answers:
            result[fld] = answers[fld]
            continue
        ok, v = derive_field(fld, ctx)
        result[fld] = v if ok else None
        if not ok:
            unfilled.append(fld)
    for nm in ("status", "manuscript", "references", "evidence", "boundaries", "files"):
        if nm not in result:
            result[nm] = {"status": status, "manuscript": derive_field("manuscript", ctx)[1], "references": derive_field("references", ctx)[1], "evidence": derive_field("evidence", ctx)[1],
                          "boundaries": derive_field("boundaries", ctx)[1], "files": files}[nm]
    for k, v in answers.items():
        result.setdefault(k, v)
    result["_meta"] = {"generator": "intro-ledger/iw.py %s" % VERSION, "contract_fields": fields, "unfilled_fields": unfilled, "contract_found": bool(fields), "files": files}
    jsave(os.path.join(a.out, "result.json"), result)
    st = check["stats"]
    print(json.dumps({"written": a.out, "status": status, "words": st["words"], "cited_works": len(cited), "issues": st["severity"], "style": style, "unfilled_contract_fields": unfilled, "contract_found": bool(fields)}, ensure_ascii=False))
    for e in errs[:10]:
        print("OPEN ERROR %s %s: %s" % (e["code"], e["sentence"] or "", e["message"][:160]))
    if unfilled:
        print("UNFILLED contract fields (put them in answers.json and re-run build --answers): " + ", ".join(unfilled))
    if a.case is not None and not fields:
        print("WARNING: no output_contract found in the case file: read /input/case.json and task.md and add the fields by hand via --answers")
    sys.exit(0 if (not unfilled or not fields) else 2)


def tidy(text):
    """what is left after removing tags and markers: no space before punctuation, no empty lines in a row, no leading blanks"""
    t = re.sub(r"[ \t]+([,.;:。，；：)])", r"\1", text)
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = re.sub(r"(?m)^[ \t]+|[ \t]+$", "", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip() + "\n"


def strip_for_part(text, conv, cited, E, style):
    return tidy(re.sub(r"\s+", " ", lint.TAG.sub("", conv(text, cited, E, style)))).strip()


# ------------------------------------------------------------------------------------------------ main
def main(argv=None):
    ap = argparse.ArgumentParser(prog="iw.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("run")
    p.set_defaults(fn=cmd_run)
    p.add_argument("--case")
    p.add_argument("--out", required=True)
    p.add_argument("--work")
    p.add_argument("--own", action="append")
    p.add_argument("--lib", action="append")
    p.add_argument("--source", action="append")
    p.add_argument("--online", action="store_true")
    p = sub.add_parser("show")
    p.set_defaults(fn=cmd_show)
    p.add_argument("work")
    p.add_argument("--entry")
    p.add_argument("--own", action="store_true")
    p.add_argument("--full", action="store_true")
    p.add_argument("--limit", type=int, default=60)
    p = sub.add_parser("ingest")
    p.set_defaults(fn=cmd_ingest)
    p.add_argument("work")
    p.add_argument("file", nargs="?")
    p = sub.add_parser("check")
    p.set_defaults(fn=cmd_check)
    p.add_argument("work")
    p.add_argument("draft")
    p.add_argument("--all", action="store_true")
    p = sub.add_parser("build")
    p.set_defaults(fn=cmd_build)
    p.add_argument("work")
    p.add_argument("draft")
    p.add_argument("--out", required=True)
    p.add_argument("--style", choices=fmt.STYLES)
    p.add_argument("--punct", choices=["ascii", "fullwidth"], default="ascii")
    p.add_argument("--case", default="")
    p.add_argument("--answers")
    p.add_argument("--online", action="store_true")
    a = ap.parse_args(argv)
    import zipfile
    import xml.etree.ElementTree as ET
    try:
        a.fn(a)
    except zipfile.BadZipFile:
        raise SystemExit("ERROR: the input is not a valid .docx (corrupt, truncated or not a Word file)")
    except ET.ParseError as e:
        raise SystemExit("ERROR: the Word document's XML cannot be read (%s)" % e)
    except FileNotFoundError as e:
        raise SystemExit("ERROR: file not found: %s" % e.filename)


if __name__ == "__main__":
    main()
