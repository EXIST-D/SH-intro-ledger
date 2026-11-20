#!/usr/bin/env python3
"""evidence.py - the evidence layer of intro-ledger: what each source says, what the own paper shows, and how to compare a sentence with them.

Everything here is lexical and checkable (no model): IDF-weighted content overlap between a sentence and a source's sentences, verbatim quote verification,
number extraction, candidate evidence sentences (result / limitation / data / method cues), reading of the author's own material (sections, figures, tables,
numbers) and optional abstract enrichment from public APIs (arXiv, Crossref, OpenAlex) when a record has an identifier but no text.
"""
from __future__ import annotations

import json
import math
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

import nlib
import segment

CJK = re.compile(r"[㐀-鿿]")


# ------------------------------------------------------------------------------------------------ tokens and overlap
def toks(text):
    """content tokens: stemmed Latin words, Chinese character bigrams"""
    t = nlib.norm(text)
    out = []
    for part in re.split(r"([㐀-鿿]+)", t):
        if not part:
            continue
        if CJK.match(part):
            out += [part[i:i + 2] for i in range(len(part) - 1)] or [part]
        else:
            out += nlib.tokens(part)
    return out


class Idf:
    """inverse document frequency over a list of texts (the library plus the own paper): words every entry shares ("landslide", "deep learning" in a landslide review) weigh little"""

    def __init__(self, texts):
        self.n = max(1, len(texts))
        self.df = Counter()
        for t in texts:
            self.df.update(set(toks(t)))

    def w(self, tok):
        return math.log(1.0 + self.n / (1.0 + self.df.get(tok, 0)))


def split_sents(text):
    out = []
    for para in re.split(r"\n\s*\n|\n(?=\s*(?:[-*]|\d+[.)])\s)", text or ""):
        para = re.sub(r"\s+", " ", para).strip()
        if para:
            out += nlib.split_sentences(para)
    return [s for s in out if len(s) > 2]


def overlap(stoks, dset, idf):
    """share of the sentence's IDF mass found in the document tokens"""
    ws = {t: idf.w(t) for t in set(stoks)}
    tot = sum(ws.values())
    if not tot:
        return 0.0
    return sum(w for t, w in ws.items() if t in dset) / tot


def best_support(sentence, source_text, idf, window=2):
    """-> (score 0..1, best source passage). The passage is one source sentence or two adjacent ones (a paraphrase often merges two)."""
    st = toks(strip_cites(sentence))
    if not st or not source_text:
        return 0.0, ""
    ss = split_sents(source_text)
    best, passage = 0.0, ""
    for i in range(len(ss)):
        for w in range(1, window + 1):
            if i + w > len(ss):
                break
            p = " ".join(ss[i:i + w])
            sc = overlap(st, set(toks(p)), idf)
            if sc > best + 1e-9:
                best, passage = sc, p
    return best, passage


def strip_cites(s):
    s = re.sub(r"\[@[^\]]*\]|\\cite\w*\{[^}]*\}|\[\d+(?:[,–-]\s*\d+)*\]", " ", s)
    s = re.sub(r"<!--.*?-->", " ", s)
    return re.sub(r"\s+", " ", s).strip()


NUM = re.compile(r"(?<![A-Za-z0-9_.])[-−–+±]?\d{1,3}(?:,\d{3})+(?:\.\d+)?|(?<![A-Za-z0-9_.])[-−–+±]?\d+(?:\.\d+)?(?:[eE][-+−]?\d+)?")  # a CJK character before a number is not a word character here


def _nums(t):
    out = []
    for x in NUM.findall(t):
        v = nlib.norm_num(x)
        if v not in ("", "-", "+"):
            out.append(v)
    return out


def numbers_of(sentence):
    """numbers a sentence asserts (years inside citations, figure / table numbers and list numbers excluded)"""
    t = nlib.norm(strip_cites(sentence))
    t = re.sub(r"\b10\s*\^\s*[-+]?\s*(?=\d)|\b10[-+](?=\d)", "10 ", t)
    t = nlib.REF_RE.sub(" ", t)
    t = re.sub(r"\([A-Z][A-Za-z'\-]+(?: et al\.?)?(?:,| and [A-Z][a-z]+,?)? ?\d{4}[a-z]?\)", " ", t)
    t = re.sub(r"(?:图|表|第)\s*\d+(?:\.\d+)?", " ", t)
    return _nums(t)


def numbers_in_text(text):
    t = nlib.norm(text)
    t = re.sub(r"\b10\s*\^\s*[-+]?\s*(?=\d)|\b10[-+](?=\d)", "10 ", t)
    t = nlib.CITE_RE.sub(" ", t)
    out = _nums(t)
    for x in list(out):
        m = re.fullmatch(r"10(\d{1,2})", x)
        if m:
            out += ["10", m.group(1).lstrip("0") or "0"]
    return set(out)


# ------------------------------------------------------------------------------------------------ quotes
def split_quote(q):
    parts = [p for p in re.split(r"\s*(?:\[\s*\.\.\.\s*\]|\.\.\.|…)\s*", nlib.norm(q)) if p.strip(" .,;:\"'")]
    return parts


def verify_quote(quote, text):
    """True when every segment of the quote (segments are separated by ... or […]) occurs, in order, in the text, ignoring case, spacing, hyphenation and punctuation"""
    parts = split_quote(quote)
    if not parts or sum(len(nlib.squash(p)) for p in parts) < 12:
        return False
    hay, pos = nlib.squash(text), 0
    for p in parts:
        k = hay.find(nlib.squash(p), pos)
        if k < 0:
            return False
        pos = k + len(nlib.squash(p))
    return True


# ------------------------------------------------------------------------------------------------ candidates in sources
KIND_ORDER = ("problem", "route", "data", "result", "limitation")
PROBLEM = re.compile(r"\b(we (?:address|tackle|study|investigate|focus on|aim)|this (?:paper|work|study) (?:addresses|focuses|aims|investigates)|the (?:problem|task|challenge) (?:of|is)|aim(?:s)? to|"
                     r"is (?:a )?(?:key|major|critical|challenging) (?:problem|task|challenge))\b", re.I)
ROUTE = re.compile(r"\b(?:we|this (?:paper|work|study|letter|article)|here,? we|in this (?:paper|work|study|letter|article),? we) (?:\w+ )?(?:propose|introduce|present|develop|design|build|construct|employ|adopt|apply|use|train|leverage|combine|integrate|investigate|study|compare|evaluate|apply)[a-z]*\b|"
                   r"\b(?:is|are) (?:proposed|introduced|presented|developed|designed|constructed)\b|\bwe (?:propose|introduce|present|develop)\b", re.I)
RESULT_Q = re.compile(r"\b(we (?:find|found|observe[d]?|show|demonstrate|report)|results? (?:show|demonstrate|indicate|reveal|suggest|confirm)|findings? (?:show|indicate|suggest)|demonstrate that|shown to|proved? (?:to be|effective)|outperform\w*|better than|compared (?:with|to))\b", re.I)


def candidates(text, limit=3):
    """evidence sentences of a source, by kind (problem / route / data / result / limitation); each {kind, text, numbers}. The title sentence is skipped."""
    out, seen = [], set()
    ss = split_sents(text)
    if ss and len(ss[0].split()) < 30 and len(ss) > 1:
        ss = ss[1:]  # the title line that readers put in front of the abstract
    for kind in KIND_ORDER:
        n = 0
        for s in ss:
            if len(s.split()) < 6 and not CJK.search(s):
                continue
            kinds = nlib.classify_sentence(s)
            hit = False
            if kind == "problem":
                hit = bool(PROBLEM.search(s) or "problem" in kinds or re.search(r"\b(?:challenging|remains? (?:a )?(?:challenge|difficult|unclear)|lack of|is (?:difficult|hard)|unclear)\b", s, re.I))
            elif kind == "route":
                hit = bool(ROUTE.search(s)) or ("contribution" in kinds and not re.search(r"\d", s))
            elif kind == "data":
                hit = "data" in kinds
            elif kind == "result":
                hit = "result" in kinds or bool(RESULT_Q.search(s))
            elif kind == "limitation":
                hit = "limitation" in kinds
            if hit and s not in seen:
                seen.add(s)
                out.append({"kind": kind, "text": s, "numbers": sorted(numbers_in_text(s))[:6]})
                n += 1
                if n >= limit:
                    break
    return out


# ------------------------------------------------------------------------------------------------ own material
FIG = re.compile(r"^\s*(?:(Fig(?:ure)?s?\.?)|(Tab(?:le)?s?\.?)|(图)|(表))\s*([A-Z]?\d+(?:\.\d+)?)\s*[.:：、\s-]*(.*)$", re.I | re.S)


def anchor_key(kind, num):
    return "%s:%s" % ("fig" if kind == "fig" else "tab", num.upper())


def load_own(path, work):
    """read the author's own material (draft, results, notes): sections, sentences, figure/table captions, numbers -> dict"""
    if path.lower().endswith((".md", ".markdown", ".txt")):
        # a heading glued to its paragraph without a blank line would not be read as a heading
        os.makedirs(work, exist_ok=True)
        with open(path, encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
        norm_path = os.path.join(work, "norm_" + os.path.basename(path))
        with open(norm_path, "w", encoding="utf-8") as fh:
            fh.write(re.sub(r"(?m)^(#{1,6} .+)\n(?=[^\n#])", r"\1\n\n", raw))
        doc = segment.build(norm_path, work)
        doc["file"] = os.path.basename(path)
    else:
        doc = segment.build(path, work)
    sections, sents, figs, nums, allp = [], [], {}, {}, []
    cur = "(start)"
    for p in doc["paragraphs"]:
        txt = p["text"].strip()
        if not txt:
            continue
        allp.append(txt)
        if p["kind"] == "heading":
            cur = re.sub(r"^\s*[\d.]+\s*", "", txt)
            sections.append(cur)
            continue
        m = FIG.match(txt)
        if m and (m.group(1) or m.group(2) or m.group(3) or m.group(4)) and len(txt) < 400:
            kind = "fig" if (m.group(1) or m.group(3)) else "tab"
            figs[anchor_key(kind, m.group(5))] = {"label": txt[:m.end(5)].strip(), "caption": txt, "section": cur}
        for s in split_sents(txt):
            sid = "O%03d" % (len(sents) + 1)
            sents.append({"id": sid, "section": cur, "text": s})
            for n in numbers_in_text(s):
                nums.setdefault(n, []).append(sid)
    text = "\n".join(s["text"] for s in sents)
    return {"file": doc["file"], "format": doc["format"], "sections": sections, "sentences": sents, "figures": figs, "numbers": nums, "text": text, "full_text": "\n\n".join(allp), "note": doc.get("note")}


def resolve_anchor(anchor, own):
    """one evidence anchor of a contribution -> (ok, detail).  Forms: Fig. 3 / Figure 3 / Table 2 / 图3 / 表2 ; Sec: Results ; N: 94.2 ; Q: "verbatim quote from the own material" """
    a = anchor.strip()
    m = re.match(r"^(?:Q|quote)\s*[:：]\s*[\"“]?(.+?)[\"”]?\s*$", a, re.I | re.S)
    if m:
        ok = verify_quote(m.group(1), own["text"])
        return ok, "quote found in own material" if ok else "quote NOT found verbatim in own material"
    m = re.match(r"^(?:N|num|number)\s*[:：]\s*(.+)$", a, re.I)
    if m:
        ns = nlib.numbers_ev(m.group(1))
        miss = [n for n in ns if n not in own["numbers"]]
        return (bool(ns) and not miss), ("numbers %s found in own material" % ns) if not miss and ns else ("numbers not in own material: %s" % (miss or m.group(1)))
    m = re.match(r"^(?:Sec(?:tion)?|S|节|章节)\s*[:：]\s*(.+)$", a, re.I)
    if m:
        want = m.group(1).strip().lower()
        hit = [s for s in own["sections"] if want in s.lower() or s.lower() in want]
        return bool(hit), ("section '%s' exists" % hit[0]) if hit else "no section named '%s' (sections: %s)" % (m.group(1), "; ".join(own["sections"][:8]))
    m = FIG.match(a + " ")
    if m:
        kind = "fig" if (m.group(1) or m.group(3)) else "tab"
        key = anchor_key(kind, m.group(5))
        if key in own["figures"]:
            return True, "%s found: %s" % (own["figures"][key]["label"], own["figures"][key]["caption"][:90])
        refs = [s for s in own["sentences"] if re.search(r"(?<![A-Za-z0-9])(?:Fig(?:ure)?s?\.?|Tab(?:le)?s?\.?|图|表)\s*%s(?![0-9])" % re.escape(m.group(5)), s["text"], re.I)]
        return bool(refs), ("%s is referred to in the text (%s) but has no caption line" % (a, refs[0]["id"])) if refs else "%s not found in the own material" % a
    return False, "anchor form not recognised (use Fig. N, Table N, Sec: name, N: number, Q: \"quote\")"


def best_own(sentence, own, idf, k=2):
    """own-material sentences / captions that best match a contribution sentence -> [(score, id, text)]"""
    st = toks(strip_cites(sentence))
    res = []
    for s in own["sentences"]:
        sc = overlap(st, set(toks(s["text"])), idf)
        if sc > 0:
            res.append((sc, s["id"], s["text"]))
    res.sort(reverse=True)
    return res[:k]


# ------------------------------------------------------------------------------------------------ online enrichment (optional)
def _get(url, timeout):
    req = urllib.request.Request(url, headers={"User-Agent": "intro-ledger/1.0 (open-source writing checker)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


ARXIV = {}


def arxiv_batch(ids, timeout=15):
    """one request for all arXiv ids (the API asks for few, spaced requests; a 429 is retried once after a pause) -> {id: {title, year, authors, abstract}}; results are cached"""
    import time
    import xml.etree.ElementTree as ET
    want = [re.sub(r"v\d+$", "", i) for i in dict.fromkeys(ids) if i]
    todo = [i for i in want if i not in ARXIV]
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for start in range(0, len(todo), 50):
        chunk = todo[start:start + 50]
        url = "https://export.arxiv.org/api/query?max_results=%d&id_list=%s" % (len(chunk), ",".join(urllib.parse.quote(i) for i in chunk))
        for attempt in (0, 1):
            try:
                root = ET.fromstring(_get(url, timeout))
                break
            except urllib.error.HTTPError as ex:
                if ex.code == 429 and attempt == 0:
                    time.sleep(4)
                    continue
                raise
        for e in root.findall("a:entry", ns):
            eid = re.sub(r"v\d+$", "", (e.find("a:id", ns).text or "").split("/abs/")[-1])
            title = re.sub(r"\s+", " ", e.find("a:title", ns).text or "").strip()
            if title.lower().startswith("error"):
                continue
            ARXIV[eid] = {"title": title, "year": (e.find("a:published", ns).text or "")[:4], "authors": [a.find("a:name", ns).text for a in e.findall("a:author", ns)],
                          "abstract": re.sub(r"\s+", " ", (e.find("a:summary", ns).text or "")).strip()}
        time.sleep(1)
    return {i: ARXIV.get(i) for i in want}


def fetch_abstract(rec, timeout=10):
    """-> (abstract, source) from arXiv (arXiv id), Crossref (DOI), OpenAlex (DOI); ('', reason) when nothing is found. Only the identifier is sent."""
    try:
        if rec.get("arxiv"):
            got = arxiv_batch([rec["arxiv"]], timeout).get(re.sub(r"v\d+$", "", rec["arxiv"]))
            if got and got["abstract"]:
                return got["abstract"], "arXiv"
        if rec.get("doi"):
            try:
                j = json.loads(_get("https://api.crossref.org/works/" + urllib.parse.quote(rec["doi"], safe="/"), timeout))["message"]
                ab = re.sub(r"<[^>]+>", " ", j.get("abstract", ""))
                ab = re.sub(r"^\s*Abstract\s*", "", re.sub(r"\s+", " ", ab)).strip()
                if len(ab.split()) >= 20:
                    return ab, "Crossref"
            except urllib.error.HTTPError:
                pass
            j = json.loads(_get("https://api.openalex.org/works/https://doi.org/" + urllib.parse.quote(rec["doi"], safe="/") + "?select=abstract_inverted_index", timeout))
            inv = j.get("abstract_inverted_index") or {}
            if inv:
                words = {}
                for w, pos in inv.items():
                    for p in pos:
                        words[p] = w
                return " ".join(words[i] for i in sorted(words)), "OpenAlex"
        return "", "no identifier or no abstract at the source"
    except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
        return "", "offline or service error: %s" % str(e)[:60]


def enrich(recs, timeout=10, budget=120, max_failures=2):
    """fill missing abstracts; stops after consecutive network failures or the time budget. -> {id: (source|reason)}"""
    import time
    t0, fails, res, gave_up = time.time(), 0, {}, ""
    try:
        arxiv_batch([r["arxiv"] for r in recs if r.get("arxiv") and len((r.get("abstract") or "").split()) < 30], timeout)
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        pass
    for r in recs:
        if len((r.get("abstract") or "").split()) >= 30 or not (r.get("doi") or r.get("arxiv")):
            continue
        if gave_up:
            res[r["id"]] = gave_up
            continue
        ab, src = fetch_abstract(r, timeout)
        if ab:
            r["abstract"], r["abstract_source"] = ab, src
            fails = 0
            res[r["id"]] = src
        else:
            res[r["id"]] = src
            fails = fails + 1 if src.startswith("offline") else 0
            if fails >= max_failures:
                gave_up = "network unreachable: not looked up"
            elif time.time() - t0 > budget:
                gave_up = "time budget used: not looked up"
    return res
