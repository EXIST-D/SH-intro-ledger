#!/usr/bin/env python3
"""verify.py - does a reference exist, and are its fields right? Offline structural checks always; Crossref / arXiv lookups only when asked (`--online`) and reachable.

Status per entry: verified (an authoritative record agrees on title, year and first author) | mismatch (a record was found but fields differ: the differences are listed) |
not_found (no matching record: possibly fabricated or not indexed) | structural_problem (fails offline checks) | unchecked (offline). Offline checks never say 'verified'.
"""
from __future__ import annotations

import datetime
import json
import re
import urllib.error
import urllib.parse
import urllib.request

import bib
import dedupe


def isbn_ok(s):
    d = re.sub(r"[^\dXx]", "", s or "")
    if len(d) == 10:
        return sum((10 - i) * (10 if c in "xX" else int(c)) for i, c in enumerate(d)) % 11 == 0
    if len(d) == 13 and d.isdigit():
        return sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(d)) % 10 == 0
    return False


def issn_ok(s):
    d = re.sub(r"[^\dXx]", "", s or "")
    if len(d) != 8:
        return False
    return sum((8 - i) * (10 if c in "xX" else int(c)) for i, c in enumerate(d[:7])) % 11 == (11 - (10 if d[7] in "xX" else int(d[7]))) % 11 or (sum((8 - i) * int(c) for i, c in enumerate(d[:7])) + (10 if d[7] in "xX" else int(d[7]))) % 11 == 0


def structural(r):
    """list of problems found without any network"""
    p = []
    yr = datetime.date.today().year
    if r["year"] and not (1500 <= int(r["year"]) <= yr + 1):
        p.append("year %s is outside 1500-%d" % (r["year"], yr + 1))
    if r["pages"]:
        m = re.fullmatch(r"([A-Za-z]?\d+)-([A-Za-z]?\d+)", r["pages"])
        if m and m.group(1).isdigit() and m.group(2).isdigit() and int(m.group(2)) < int(m.group(1)):
            p.append("page range %s is decreasing" % r["pages"])
        if m and m.group(1).isdigit() and m.group(2).isdigit() and int(m.group(2)) - int(m.group(1)) > 400 and r["type"] in ("journal", "conference"):
            p.append("page range %s is unusually long for an article" % r["pages"])
    if r["doi"] and not re.fullmatch(r"10\.\d{4,9}/\S+", r["doi"]):
        p.append("malformed DOI")
    if r["isbn"] and not isbn_ok(r["isbn"]):
        p.append("ISBN %s fails its check digit" % r["isbn"])
    if r["issn"] and not issn_ok(r["issn"]):
        p.append("ISSN %s fails its check digit" % r["issn"])
    if r["arxiv"]:
        m = re.match(r"(\d{2})(\d{2})\.\d{4,5}", r["arxiv"])
        if m and not (1 <= int(m.group(2)) <= 12):
            p.append("arXiv id %s has an impossible month" % r["arxiv"])
        elif m and r["year"] and abs((2000 + int(m.group(1))) - int(r["year"])) > 4:
            p.append("arXiv id %s (year %d) does not fit year %s" % (r["arxiv"], 2000 + int(m.group(1)), r["year"]))
    if r["title"] and (r["title"].isupper() and len(r["title"]) > 25):
        p.append("title is all upper case")
    if r["title"] and re.search(r"\b(lorem ipsum|et al\b)", r["title"], re.I):
        p.append("title contains placeholder / 'et al' text")
    if any(re.search(r"\bet\s+al\b", (a.get("family", "") + a.get("given", "") + a.get("literal", "")), re.I) for a in r["authors"]):
        p.append("'et al' stored as an author name")
    if r["type"] == "journal" and r["volume"] and not re.fullmatch(r"[\dA-Za-z.\-]+", r["volume"]):
        p.append("volume '%s' looks wrong" % r["volume"])
    if not r["authors"] and r["type"] in ("journal", "conference", "book"):
        p.append("no author")
    if not r["title"]:
        p.append("no title")
    return p


def http_json(url, timeout=10):
    req = urllib.request.Request(url, headers={"User-Agent": "citation-ledger/1.0 (open-source reference checker)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def crossref_record(msg):
    r = bib.new_record("crossref")
    r["id"] = msg.get("DOI", "")
    r["title"] = (msg.get("title") or [""])[0]
    r["authors"] = [{"family": a.get("family", ""), "given": a.get("given", ""), "literal": a.get("name", ""), "zh": False} for a in msg.get("author", [])]
    r["container"] = (msg.get("container-title") or [""])[0]
    iss = (msg.get("issued") or {}).get("date-parts") or [[None]]
    r["year"] = str(iss[0][0]) if iss and iss[0] and iss[0][0] else ""
    r["volume"], r["issue"], r["pages"], r["publisher"], r["doi"] = msg.get("volume", ""), msg.get("issue", ""), msg.get("page", ""), msg.get("publisher", ""), msg.get("DOI", "")
    r["type"] = {"journal-article": "journal", "proceedings-article": "conference", "book": "book", "book-chapter": "chapter", "posted-content": "preprint", "dissertation": "thesis", "report": "report"}.get(msg.get("type", ""), "other")
    return bib.finish(r)


def lookup_arxiv(r, timeout=10):
    """record with an arXiv id and no DOI: compare title / first author / year with the arXiv API entry (one batched request for all ids, see evidence.arxiv_batch)"""
    import evidence
    try:
        got = evidence.arxiv_batch([r["arxiv"]], timeout).get(re.sub(r"v\d+$", "", r["arxiv"]))
    except (urllib.error.URLError, OSError, ValueError) as ex:
        return "unchecked", ["offline or service error: %s" % str(ex)[:80]], None
    if not got:
        return "not_found", ["arXiv has no record with id %s" % r["arxiv"]], None
    found = bib.new_record("arxiv")
    found["title"], found["year"] = got["title"], got["year"]
    found["authors"] = bib.split_authors(" and ".join(got["authors"][:3]))
    diffs = []
    ts = dedupe.title_sim(found["title"], r["title"])
    if ts < 0.85:
        diffs.append("title: arXiv has '%s' (similarity %.2f)" % (found["title"][:90], ts))
    if r["year"] and found["year"] and abs(int(r["year"]) - int(found["year"])) > 1:
        diffs.append("year: %s vs arXiv %s" % (r["year"], found["year"]))
    if r["authors"] and found["authors"] and not dedupe.fam_eq(dedupe.fam(r), dedupe.fam(found)):
        diffs.append("first author: %s vs arXiv %s" % (r["authors"][0]["family"], found["authors"][0]["family"]))
    return ("verified" if not diffs else "mismatch"), (diffs or ["arXiv record agrees on title, year and first author"]), found


def lookup(r, timeout=10):
    """-> (status, details, found_record|None). Needs network."""
    if r.get("arxiv") and not r.get("doi") and r.get("title"):
        return lookup_arxiv(r, timeout)
    if not r["doi"] and bib.CJK.search(r["title"] or ""):
        return "unchecked", ["Chinese-language title without a DOI: Crossref indexes few Chinese journals, so a miss would prove nothing; check CNKI / Wanfang by hand"], None
    if not r["doi"] and r["type"] in ("book", "thesis", "report", "standard", "patent", "web", "newspaper"):
        return "unchecked", ["%s without a DOI: not what Crossref indexes; check a library catalogue / the issuing body by hand" % r["type"]], None
    try:
        if r["doi"]:
            try:
                msg = http_json("https://api.crossref.org/works/" + urllib.parse.quote(r["doi"], safe="/"), timeout)["message"]
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return "not_found", ["DOI %s is not registered at Crossref (may be a DataCite / other agency DOI, or invented)" % r["doi"]], None
                raise
            found = crossref_record(msg)
        elif r["title"]:
            q = urllib.parse.urlencode({"query.bibliographic": "%s %s %s" % (r["title"], " ".join(a["family"] for a in r["authors"][:2]), r["year"]), "rows": 3})
            items = http_json("https://api.crossref.org/works?" + q, timeout)["message"]["items"]
            cands = [crossref_record(m) for m in items]
            cands = [c for c in cands if dedupe.title_sim(c["title"], r["title"]) >= 0.85]
            if not cands:
                return "not_found", ["no Crossref record with a title similar to '%s' (arXiv-only, book, thesis, or invented?)" % r["title"][:60]], None
            found = max(cands, key=lambda c: dedupe.title_sim(c["title"], r["title"]))
        else:
            return "unchecked", ["no DOI and no title to look up"], None
    except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
        return "unchecked", ["offline or service error: %s" % str(e)[:80]], None
    diffs = []
    ts = dedupe.title_sim(found["title"], r["title"])
    if ts < 0.85:
        diffs.append("title: record has '%s' (similarity %.2f)" % (found["title"][:90], ts))
    if r["year"] and found["year"] and r["year"] != found["year"]:
        diffs.append("year: %s vs record %s" % (r["year"], found["year"]))
    if r["authors"] and found["authors"] and not dedupe.fam_eq(dedupe.fam(r), dedupe.fam(found)):
        diffs.append("first author: %s vs record %s" % (r["authors"][0]["family"], found["authors"][0]["family"]))
    if r["pages"] and found["pages"] and r["pages"].split("-")[0] != found["pages"].replace("–", "-").split("-")[0]:
        diffs.append("pages: %s vs record %s" % (r["pages"], found["pages"]))
    if r["volume"] and found["volume"] and r["volume"] != found["volume"]:
        diffs.append("volume: %s vs record %s" % (r["volume"], found["volume"]))
    if r["container"] and found["container"] and dedupe.title_sim(r["container"], found["container"]) < 0.5 and not re.search(r"(?:\b[A-Z]{2,}\b|\.)", r["container"]):
        diffs.append("journal: '%s' vs record '%s'" % (r["container"], found["container"]))
    return ("verified" if not diffs else "mismatch"), (diffs or ["Crossref record agrees on title, year and first author"]), found


def check_all(recs, online=False, timeout=10, budget=240, max_failures=2):
    """online lookups stop after `max_failures` consecutive network failures or `budget` seconds (the rest stay 'unchecked'): a sandbox without network must not eat the run time"""
    import time
    out, fails, t0, gave_up = {}, 0, time.time(), ""
    if online:
        try:
            import evidence
            evidence.arxiv_batch([r["arxiv"] for r in recs if r.get("arxiv") and not r.get("doi")], timeout)
        except Exception:
            pass
    for r in recs:
        prob = structural(r)
        st, det, found = ("unchecked", ["offline: not looked up"], None)
        if online and not gave_up:
            st, det, found = lookup(r, timeout)
            fails = fails + 1 if (st == "unchecked" and det and det[0].startswith("offline or service error")) else 0
            if fails >= max_failures:
                gave_up = "network unreachable (%d consecutive failures): remaining entries not looked up" % fails
            elif time.time() - t0 > budget:
                gave_up = "time budget of %ds used: remaining entries not looked up" % budget
        elif online and gave_up:
            st, det = "unchecked", [gave_up]
        if prob and st in ("unchecked", "verified"):
            st = "structural_problem" if st == "unchecked" else st
        out[r["id"]] = {"status": st, "structural": prob, "details": det, "found_doi": (found or {}).get("doi") if found else None, "found": ({k: found[k] for k in ("title", "year", "container", "volume", "pages", "doi")} if found else None)}
    return out
