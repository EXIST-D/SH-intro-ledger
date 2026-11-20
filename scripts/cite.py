#!/usr/bin/env python3
"""cite.py - find the citation markers of a manuscript (numeric brackets, superscripts, author-year, LaTeX \\cite, pandoc [@key]), the reference list, and write markers back.

A marker (instance) is {par, start, end, raw, style, nums | keys | ay, form}. Positions are offsets in the paragraph text of the document model (segment.py), so a rewrite
replaces exactly the marker and nothing else. Marker styles: bracket `[1]`, `[1,2]`, `[1-3]`; sup `<sup>1,2</sup>` / `^1^` / unicode superscripts; authyear `(Smith, 2020; Lee et al., 2019)` / `Smith (2020)`;
latex `\\cite{a,b}`; pandoc `[@a; @b]`.
"""
from __future__ import annotations

import re

import bib
import nlib

SUPD = "⁰¹²³⁴⁵⁶⁷⁸⁹"
SUPMAP = {c: str(i) for i, c in enumerate(SUPD)}
SUPMAP.update({"⁻": "-", "⁼": "="})
RNG = r"\s*[-–—~‐−]\s*"
NUMLIST = r"\d{1,3}(?:%s\d{1,3})?(?:\s*[,，;；]\s*\d{1,3}(?:%s\d{1,3})?)*" % (RNG, RNG)
P_BRACKET = re.compile(r"[\[［]\s*(%s)\s*[\]］]" % NUMLIST)
P_SUPTAG = re.compile(r"<sup>\s*(%s)\s*</sup>" % NUMLIST)
P_SUPUNI = re.compile(r"[⁰¹²³⁴⁵⁶⁷⁸⁹][⁰¹²³⁴⁵⁶⁷⁸⁹,⁻]*")
P_CARET = re.compile(r"\^\[?(%s)\]?\^" % NUMLIST)
P_LATEX = re.compile(r"\\((?:cite|citep|citet|citealp|citeauthor|citeyear|parencite|textcite|autocite|footcite|nocite)[a-zA-Z]*)\*?((?:\[[^\]]*\])*)\{([^}]*)\}")
P_PANDOC = re.compile(r"\[((?:[^\[\]@;]*?)-?@[\w:.#$%&\-+?<>~/]+(?:[^\[\]@;]*)(?:\s*;\s*[^\[\]@;]*?-?@[\w:.#$%&\-+?<>~/]+[^\[\]@;]*)*)\]")
P_PAREN = re.compile(r"[(（]([^()（）]*?(?:19|20)\d{2}[a-z]?[^()（）]*?)[)）]")
AY_ITEM = re.compile(r"^\s*(?:see\s+|e\.g\.,?\s*|cf\.\s*|参见\s*)?([A-Z][\w'’-]+(?:\s+(?:et\s+al\.?|and|&)\s+[A-Z][\w'’-]+)?(?:\s+et\s+al\.?)?|[一-鿿]{2,4}(?:等)?)\s*[,，]?\s*((?:19|20)\d{2}[a-z]?)(?:\s*[,;，]\s*(?:p+\.?|页)\s*[\d\-–]+)?\s*$")
P_NARR = re.compile(r"([A-Z][\w'’-]+(?:\s+et\s+al\.?|\s+(?:and|&)\s+[A-Z][\w'’-]+)?|[一-鿿]{2,4}等?)\s*[(（]\s*((?:19|20)\d{2}[a-z]?(?:\s*[,;，]\s*(?:19|20)\d{2}[a-z]?)*)\s*[)）]")


def expand(spec):
    """'1-3, 5' -> [1,2,3,5] (invalid ranges are kept as their end points)"""
    out = []
    for part in re.split(r"[,，;；]", spec.replace("＝", "")):
        part = part.strip()
        m = re.fullmatch(r"(\d+)%s(\d+)" % RNG, part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            out += list(range(a, b + 1)) if 0 <= b - a <= 200 else [a, b]
        elif part.isdigit():
            out.append(int(part))
    return out


def sup_to_ascii(s):
    return "".join(SUPMAP.get(c, c) for c in s)


def compress(nums, rng="–", min_run=3, sep=","):
    """sorted unique numbers -> '1–3,5' (runs of >= min_run become a range)"""
    nums = sorted(set(nums))
    out, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        if j - i + 1 >= min_run:
            out.append("%d%s%d" % (nums[i], rng, nums[j]))
        else:
            out += [str(n) for n in nums[i:j + 1]]
        i = j + 1
    return sep.join(out)


def find_instances(text, par):
    """-> list of instances in one paragraph text (non-overlapping, left to right)"""
    found = []
    taken = []

    def free(a, b):
        return not any(a < y and x < b for x, y in taken)

    def add(m, style, **kw):
        if free(m.start(), m.end()):
            taken.append((m.start(), m.end()))
            found.append({"par": par, "start": m.start(), "end": m.end(), "raw": m.group(0), "style": style, **kw})
    for m in P_LATEX.finditer(text):
        add(m, "latex", keys=[k.strip() for k in m.group(3).split(",") if k.strip()], cmd=m.group(1))
    for m in P_PANDOC.finditer(text):
        keys = re.findall(r"-?@([\w:.#$%&\-+?<>~/]+)", m.group(1))
        add(m, "pandoc", keys=[k.rstrip(".,;:") for k in keys])
    for m in P_SUPTAG.finditer(text):
        add(m, "sup", nums=expand(m.group(1)), form={"tag": "html", "rng": rng_char(m.group(1)), "sep": sep_char(m.group(1))})
    for m in P_CARET.finditer(text):
        add(m, "sup", nums=expand(m.group(1)), form={"tag": "caret", "rng": rng_char(m.group(1)), "sep": sep_char(m.group(1))})
    for m in P_SUPUNI.finditer(text):
        s = sup_to_ascii(m.group(0))
        if re.fullmatch(r"\d+(?:[,\-]\d+)*", s):
            add(m, "sup", nums=expand(s), form={"tag": "unicode", "rng": "-", "sep": ","})
    for m in P_BRACKET.finditer(text):
        # a bracketed number list directly after '(' or inside a link / reference label is not a citation here
        add(m, "bracket", nums=expand(m.group(1)), form={"rng": rng_char(m.group(1)), "sep": sep_char(m.group(1)), "space": bool(re.search(r"[,，;；]\s", m.group(1))), "wide": m.group(0)[0] == "［"})
    for m in P_PAREN.finditer(text):
        items = [x for x in re.split(r"\s*;\s*|；", m.group(1)) if x.strip()]
        ay = []
        for it in items:
            mm = AY_ITEM.match(it)
            if not mm:
                ay = []
                break
            ay.append((mm.group(1).strip(), mm.group(2)))
        if ay:
            add(m, "authyear", ay=ay)
    for m in P_NARR.finditer(text):
        if free(m.start(), m.end()) and not re.match(r"(?:Figure|Fig|Table|Section|Eq|Equation)", m.group(1)):
            ys = re.findall(r"(?:19|20)\d{2}[a-z]?", m.group(2))
            add(m, "authyear", ay=[(m.group(1).strip(), y) for y in ys], narrative=True)
    return sorted(found, key=lambda x: x["start"])


def rng_char(s):
    m = re.search(r"\d(\s*)([-–—~‐−])(\s*)\d", s)
    return m.group(2) if m else "–"


def sep_char(s):
    m = re.search(r"\d(\s*)([,，;；])", s)
    return m.group(2) if m else ","


def render_marker(inst, nums, style=None, rng="–", sep=",", space=False, wide=False, min_run=3):
    """text of a numeric marker for the given numbers"""
    style = style or inst["style"]
    body = compress(nums, rng, min_run, sep + (" " if space else ""))
    if style == "bracket":
        return ("［%s］" if wide else "[%s]") % body
    form = inst.get("form", {}) if inst else {}
    tag = form.get("tag", "html")
    if tag == "unicode":
        return "".join({v: k for k, v in SUPMAP.items()}.get(c, c) for c in compress(nums, "-", min_run, ","))
    if tag == "caret":
        return "^%s^" % body
    return "<sup>%s</sup>" % body


# ------------------------------------------------------------------------------------------------ reference list
def parse_reflist(doc):
    """-> (entries, region) ; entries [{no, raw, par, record}] in list order; region = {"pars": [...], "numbered": bool, "label": 'bracket|dot|none|auto'}"""
    pars = [p for p in doc["paragraphs"] if p.get("in_refs") and p["kind"] == "frozen" and p.get("frozen_reason", "").startswith("reference")]
    if not pars:
        # a LaTeX thebibliography environment
        pars = [p for p in doc["paragraphs"] if "\\bibitem" in p["text"]]
    entries, label = [], "none"
    for p in pars:
        txt = p["text"]
        if "\\bibitem" in txt:
            for m in re.finditer(r"\\bibitem(?:\[[^\]]*\])?\{([^}]*)\}\s*(.*?)(?=\\bibitem|\\end\{thebibliography\}|$)", txt, re.S):
                entries.append({"raw": re.sub(r"\s+", " ", m.group(2)).strip(), "par": p["id"], "key": m.group(1)})
            label = "bibitem"
            continue
        lines = txt.split("\n")
        if len(lines) == 1 or not any(re.match(r"\s*(?:\[\d+\]|\(\d+\)|\d+[.)])\s+", l) for l in lines):
            if p.get("numbered") or len(lines) == 1:
                for l in lines:
                    if l.strip():
                        m = re.match(r"\s*(\[\d+\]|\(\d+\)|\d+[.)])\s*", l)
                        if m and label == "none":
                            label = "bracket" if m.group(1).startswith("[") else ("paren" if m.group(1).startswith("(") else "dot")
                        entries.append({"raw": re.sub(r"^\s*(?:\[\d+\]|\(\d+\)|\d+[.)])\s*", "", l).strip(), "par": p["id"], "auto": bool(p.get("numbered")) and not m, "no_label": m.group(1) if m else ""})
                if p.get("numbered") and label == "none":
                    label = "auto"
                continue
        cur = None
        for l in lines:
            m = re.match(r"\s*(\[\d+\]|\(\d+\)|\d+[.)])\s+(.*)$", l)
            if m:
                if cur:
                    entries.append(cur)
                if label == "none":
                    label = "bracket" if m.group(1).startswith("[") else ("paren" if m.group(1).startswith("(") else "dot")
                cur = {"raw": m.group(2).strip(), "par": p["id"], "no_label": m.group(1)}
            elif cur and l.strip() and not cur.get("no_label") and re.search(r"(?:1[5-9]|20)\d{2}", cur["raw"]) and re.match(r"\s*[A-Z\u4e00-\u9fff]", l):
                entries.append(cur)  # an unnumbered list written one entry per line
                cur = {"raw": l.strip(), "par": p["id"]}
            elif cur and l.strip():
                cur["raw"] += " " + l.strip()
            elif not cur and l.strip():
                cur = {"raw": l.strip(), "par": p["id"]}
        if cur:
            entries.append(cur)
    labels = []
    for e in entries:
        m = re.match(r"[\[(]?(\d+)", e.get("no_label", ""))
        labels.append(int(m.group(1)) if m else None)
    explicit = all(x is not None for x in labels) and len(set(labels)) == len(labels)
    for i, e in enumerate(entries, 1):
        e["no"] = labels[i - 1] if explicit and labels else i
        e["record"] = bib.parse_text_entry(e["raw"])
    region = {"pars": [p["id"] for p in pars], "label": label, "numbered": label != "none"}
    return entries, region


# ------------------------------------------------------------------------------------------------ author-year resolution
def norm_family(s):
    s = re.sub(r"\s+(?:et\s+al\.?|等).*$", "", s.strip())
    s = re.split(r"\s+(?:and|&)\s+", s)[0]
    return re.sub(r"[^\w一-鿿]", "", s).lower()


def resolve_ay(fam, year, recs):
    f = norm_family(fam)
    y = year[:4]
    suffix = year[4:]
    hits = [r for r in recs if r["authors"] and str(r["year"]) == y and norm_family(r["authors"][0]["family"] or r["authors"][0]["literal"]) == f]
    if len(hits) > 1 and suffix:
        hits = [r for r in hits if r.get("ay_suffix") == suffix] or hits
    return hits
