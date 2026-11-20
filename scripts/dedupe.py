#!/usr/bin/env python3
"""dedupe.py - find duplicate bibliographic entries and say WHY two entries are the same work.

Rules (each pair gets the list of rules that fired, a decision and a confidence):
  doi           same DOI                                                     -> same (certain)
  arxiv         same arXiv id (version ignored)                              -> same (certain)
  isbn          same ISBN and same edition                                   -> same (certain)
  title+author  identical normalised title, same first author, years within 1 -> same (high)
  version_pair  identical / near-identical title, same first author, one entry is a preprint (or years differ by 2-3, conference vs journal) -> same work, canonical = published version
  fuzzy         title similarity >= 0.90, same first author, years within 1, pages not contradicting -> same (medium); 0.80-0.90 -> candidate
  bilingual     one Chinese and one Latin title: same year, volume and first page and (first author pinyin == Latin family name or same DOI/ISSN) -> same (high); only year + pages + volume -> candidate
  venue         same container, volume, issue, pages, year and first author, titles similar (>= 0.7) -> same (high)
Guards (never merged): different DOIs with different titles; same title but disjoint author lists; same author names with unrelated titles (homonyms).
Nothing is merged by this module: it returns clusters + evidence; the caller applies decisions.
"""
from __future__ import annotations

import difflib
import re
import unicodedata

import bib

PINYIN = {"王": "wang", "李": "li", "张": "zhang", "刘": "liu", "陈": "chen", "杨": "yang", "黄": "huang", "赵": "zhao", "吴": "wu", "周": "zhou", "徐": "xu", "孙": "sun", "马": "ma", "朱": "zhu", "胡": "hu", "郭": "guo", "何": "he", "高": "gao", "林": "lin", "罗": "luo",
          "郑": "zheng", "梁": "liang", "谢": "xie", "宋": "song", "唐": "tang", "许": "xu", "韩": "han", "冯": "feng", "邓": "deng", "曹": "cao", "彭": "peng", "曾": "zeng", "肖": "xiao", "田": "tian", "董": "dong", "袁": "yuan", "潘": "pan", "于": "yu", "蒋": "jiang",
          "蔡": "cai", "余": "yu", "杜": "du", "叶": "ye", "程": "cheng", "苏": "su", "魏": "wei", "吕": "lv", "丁": "ding", "任": "ren", "沈": "shen", "姚": "yao", "卢": "lu", "姜": "jiang", "崔": "cui", "钟": "zhong", "谭": "tan", "陆": "lu", "汪": "wang", "范": "fan",
          "金": "jin", "石": "shi", "廖": "liao", "贾": "jia", "夏": "xia", "韦": "wei", "付": "fu", "方": "fang", "白": "bai", "邹": "zou", "孟": "meng", "熊": "xiong", "秦": "qin", "邱": "qiu", "江": "jiang", "尹": "yin", "薛": "xue", "闫": "yan", "段": "duan", "雷": "lei",
          "侯": "hou", "龙": "long", "史": "shi", "陶": "tao", "黎": "li", "贺": "he", "顾": "gu", "毛": "mao", "郝": "hao", "龚": "gong", "邵": "shao", "万": "wan", "钱": "qian", "严": "yan", "覃": "qin", "武": "wu", "戴": "dai", "莫": "mo", "孔": "kong", "向": "xiang",
          "汤": "tang", "常": "chang", "温": "wen", "康": "kang", "施": "shi", "文": "wen", "牛": "niu", "樊": "fan", "葛": "ge", "邢": "xing", "安": "an", "齐": "qi", "易": "yi", "乔": "qiao", "伍": "wu", "庞": "pang", "颜": "yan", "倪": "ni", "庄": "zhuang", "聂": "nie",
          "章": "zhang", "鲁": "lu", "岳": "yue", "翟": "zhai", "殷": "yin", "詹": "zhan", "申": "shen", "欧阳": "ouyang", "司马": "sima", "上官": "shangguan", "诸葛": "zhuge", "东方": "dongfang", "单": "shan", "柯": "ke", "库": "ku", "牟": "mou", "柏": "bai", "卫": "wei", "管": "guan"}
STOPW = {"a", "an", "the", "of", "in", "on", "for", "and", "to", "with", "by", "from", "at", "as", "is", "are", "via", "using", "its", "their"}
PREPRINT = re.compile(r"arxiv|biorxiv|medrxiv|chemrxiv|ssrn|preprint|working paper|eprint|researchsquare", re.I)


def norm_title(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^\w一-鿿]+", " ", s)
    return " ".join(w for w in s.split() if w not in STOPW)


def title_sim(a, b):
    na, nb = norm_title(a), norm_title(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ta, tb = set(na.split()), set(nb.split())
    jac = len(ta & tb) / len(ta | tb)
    return max(jac, difflib.SequenceMatcher(None, na, nb).ratio() * 0.98)


def fam(r, i=0):
    if len(r["authors"]) <= i:
        return ""
    a = r["authors"][i]
    f = a["family"] or a["literal"]
    return re.sub(r"[^\w一-鿿]", "", unicodedata.normalize("NFKD", f).lower()) if not bib.CJK.search(f) else f


def fam_eq(x, y):
    if not x or not y:
        return False
    if x == y:
        return True
    xa, ya = re.sub(r"[^a-z]", "", x), re.sub(r"[^a-z]", "", y)
    return len(xa) >= 4 and len(ya) >= 4 and difflib.SequenceMatcher(None, xa, ya).ratio() >= 0.85


def fam_set(r):
    return [fam(r, i) for i in range(len(r["authors"])) if fam(r, i)]


def author_jaccard(a, b):
    sa, sb = fam_set(a), fam_set(b)
    if not sa or not sb:
        return None
    inter = sum(1 for x in sa if any(fam_eq(x, y) for y in sb))
    return inter / max(len(sa), len(sb))


def pinyin_family(r):
    if not r["authors"]:
        return ""
    f = r["authors"][0]["family"]
    return PINYIN.get(f, "")


def first_page(r):
    m = re.match(r"([A-Za-z]?\d+)", r["pages"] or "")
    return m.group(1) if m else ""


def author_overlap(a, b):
    fa, fb = fam_set(a), fam_set(b)
    if not fa or not fb:
        return None
    return sum(1 for x in fa if any(fam_eq(x, y) for y in fb)) / min(len(fa), len(fb))


def years_close(a, b, tol=1):
    try:
        return abs(int(a["year"]) - int(b["year"])) <= tol
    except (TypeError, ValueError):
        return None


def arxiv_core(x):
    return re.sub(r"v\d+$", "", (x or "").lower())


def compare(a, b):
    """-> dict(decision same|candidate|different, confidence, rules[], reasons[], work_pair bool, guards[])"""
    rules, why, guards = [], [], []
    same = False
    conf = ""
    work_pair = False
    ts = title_sim(a["title"], b["title"])
    ao = author_overlap(a, b)
    f1 = fam_eq(fam(a), fam(b))
    aj = author_jaccard(a, b)
    ntok = len(norm_title(a["title"]).split())
    generic = ntok <= 4
    authors_ok = aj is None or aj >= (0.7 if generic else 0.5) or (len(a["authors"]) <= 1 or len(b["authors"]) <= 1) and not generic
    yc1, yc3 = years_close(a, b, 1), years_close(a, b, 3)
    zh_a, zh_b = bool(bib.CJK.search(a["title"])), bool(bib.CJK.search(b["title"]))
    if a["doi"] and b["doi"]:
        if a["doi"] == b["doi"]:
            return {"decision": "same", "confidence": "certain", "rules": ["doi"], "reasons": ["same DOI " + a["doi"]], "work_pair": False, "guards": [], "title_sim": round(ts, 2)}
        if ts < 0.8:
            return {"decision": "different", "confidence": "high", "rules": [], "reasons": [], "work_pair": False, "guards": ["different DOIs and different titles"], "title_sim": round(ts, 2)}
        guards.append("different DOIs but similar titles (preprint / published?)")
    if a["arxiv"] and b["arxiv"] and arxiv_core(a["arxiv"]) == arxiv_core(b["arxiv"]):
        return {"decision": "same", "confidence": "certain", "rules": ["arxiv"], "reasons": ["same arXiv id " + arxiv_core(a["arxiv"])], "work_pair": False, "guards": [], "title_sim": round(ts, 2)}
    if a["isbn"] and b["isbn"] and re.sub(r"\D", "", a["isbn"]) == re.sub(r"\D", "", b["isbn"]) and (a["edition"] or "") == (b["edition"] or ""):
        return {"decision": "same", "confidence": "certain", "rules": ["isbn"], "reasons": ["same ISBN and edition"], "work_pair": False, "guards": [], "title_sim": round(ts, 2)}
    # same title but disjoint authors: never merge
    if ts >= 0.9 and ao is not None and ao == 0 and not (zh_a != zh_b):
        return {"decision": "different", "confidence": "high", "rules": [], "reasons": [], "work_pair": False, "guards": ["same title but no common author family name (homonymous title)"], "title_sim": round(ts, 2)}
    # bilingual pair
    if zh_a != zh_b and a["year"] and a["year"] == b["year"]:
        zh, la = (a, b) if zh_a else (b, a)
        vol_eq = zh["volume"] and zh["volume"] == la["volume"]
        pg_eq = first_page(zh) and first_page(zh) == first_page(la)
        py = pinyin_family(zh)
        py_eq = py and py == fam(la)
        if vol_eq and pg_eq and (py_eq or (zh["issue"] and zh["issue"] == la["issue"])):
            rules.append("bilingual")
            why.append("Chinese / Latin titles, same year %s, volume %s, first page %s, %s" % (a["year"], zh["volume"], first_page(zh), ("first author %s = %s" % (zh["authors"][0]["family"], py)) if py_eq else "same issue"))
            same, conf = True, "high"
        elif (vol_eq and pg_eq) or (pg_eq and py_eq):
            rules.append("bilingual")
            why.append("Chinese / Latin titles with matching year and %s: confirm" % ("volume + first page" if vol_eq else "first page + author pinyin"))
            return {"decision": "candidate", "confidence": "medium", "rules": rules, "reasons": why, "work_pair": False, "guards": guards, "title_sim": round(ts, 2)}
    prea, preb = bool(PREPRINT.search(a["container"] or "") or a["type"] == "preprint" or a["arxiv"] and not a["doi"]), bool(PREPRINT.search(b["container"] or "") or b["type"] == "preprint" or b["arxiv"] and not b["doi"])
    # identical title + first author
    if not same and ts >= 0.98 and (f1 or (ao is not None and ao >= 0.5)) and yc1 and authors_ok and (not generic or a["year"] == b["year"]):
        rules.append("title+author")
        why.append("identical normalised title, same first author (%s), years %s / %s" % (fam(a), a["year"], b["year"]))
        same, conf = True, "high"
    if same and prea != preb and not work_pair:
        rules.append("version_pair")
        why.append("one entry is a preprint (arXiv / working paper) and the other a published version: one work, canonical = the published version")
        work_pair = True
    if not same and ts >= 0.88 and (f1 or (ao is not None and ao >= 0.5)) and authors_ok and not generic and yc3 and ((prea != preb) or (a["type"] != b["type"] and {a["type"], b["type"]} <= {"journal", "conference", "preprint"})):
        rules.append("version_pair")
        why.append("near-identical title (%.2f), same first author, %s vs %s versions (years %s / %s): one work" % (ts, "preprint" if prea else a["type"], "preprint" if preb else b["type"], a["year"], b["year"]))
        same, conf, work_pair = True, "high", True
    if not same and ts >= 0.9 and (f1 or (ao is not None and ao >= 0.6)) and authors_ok and yc1 and not (a["pages"] and b["pages"] and a["pages"] != b["pages"]):
        rules.append("fuzzy")
        why.append("title similarity %.2f, same first author, years %s / %s" % (ts, a["year"], b["year"]))
        same, conf = True, "medium"
    if not same and ts >= 0.8 and (f1 or (ao is not None and ao >= 0.5)) and yc3:
        rules.append("fuzzy")
        why.append("title similarity %.2f with same first author, years %s / %s: confirm" % (ts, a["year"], b["year"]))
        return {"decision": "candidate", "confidence": "medium", "rules": rules, "reasons": why, "work_pair": False, "guards": guards, "title_sim": round(ts, 2)}
    if not same and a["container"] and norm_title(a["container"]) == norm_title(b["container"]) and a["volume"] and a["volume"] == b["volume"] and a["pages"] and a["pages"] == b["pages"] and a["year"] == b["year"] and f1 and ts >= 0.7 and authors_ok:
        rules.append("venue")
        why.append("same journal, volume, pages, year and first author, titles similar (%.2f)" % ts)
        same, conf = True, "high"
    if same:
        return {"decision": "same", "confidence": conf, "rules": rules, "reasons": why, "work_pair": work_pair, "guards": guards, "title_sim": round(ts, 2)}
    return {"decision": "different", "confidence": "high" if ts < 0.6 else "medium", "rules": [], "reasons": [], "work_pair": False, "guards": guards, "title_sim": round(ts, 2)}


def blocks(recs):
    """candidate pairs by blocking on normalised title tokens / first author / DOI to avoid O(n^2) on big libraries"""
    idx = {}
    for i, r in enumerate(recs):
        keys = {"d:" + r["doi"]} if r["doi"] else set()
        if r["arxiv"]:
            keys.add("x:" + arxiv_core(r["arxiv"]))
        nt = norm_title(r["title"]).split()
        keys.add("n:" + " ".join(nt))
        if len(nt) >= 3:
            keys.add("h:" + " ".join(nt[:3]))
        keys |= {"t:" + w for w in nt if len(w) > 7}
        if fam(r) and r["year"]:
            keys.add("a:%s:%s" % (fam(r), r["year"][:3]))
        if bib.CJK.search(r["title"]) and r["year"]:
            keys.add("y:%s:%s:%s" % (r["year"], r["volume"], first_page(r)))
        elif r["year"] and r["volume"]:
            keys.add("y:%s:%s:%s" % (r["year"], r["volume"], first_page(r)))
        for k in keys:
            idx.setdefault(k, []).append(i)
    pairs = set()
    for k, ids in idx.items():
        if len(ids) > 60:
            continue
        for x in range(len(ids)):
            for y in range(x + 1, len(ids)):
                pairs.add((ids[x], ids[y]))
    return pairs


FIELDS = ("type", "authors", "title", "container", "year", "volume", "issue", "pages", "publisher", "place", "doi", "url", "isbn", "issn", "edition", "abstract", "number", "date")


def completeness(r):
    return sum(1 for k in FIELDS if r.get(k)) + (2 if r["doi"] else 0) + (1 if r["type"] in ("journal", "conference") else 0) - (2 if r["type"] == "preprint" else 0) + (1 if r["source"] != "text" else 0)


def merge_records(recs, canon_id=None):
    """-> (merged record, details{filled[], conflicts[], dropped[]}); canonical = published > most complete > library"""
    recs = sorted(recs, key=lambda r: (-(r["type"] != "preprint"), -completeness(r)))
    base = dict(next((r for r in recs if r["id"] == canon_id), recs[0]))
    base["authors"] = list(base["authors"])
    filled, conflicts = [], []
    for o in recs:
        if o["id"] == base["id"]:
            continue
        for k in FIELDS:
            if k == "type":
                continue
            ov, bv = o.get(k), base.get(k)
            if k == "authors":
                if not bv and ov:
                    base[k] = list(ov)
                    filled.append((k, o["id"]))
                continue
            if ov and not bv:
                base[k] = ov
                filled.append((k, o["id"]))
            elif ov and bv and norm_title(str(ov)) != norm_title(str(bv)) and k not in ("abstract", "url", "title", "container", "publisher", "place"):
                conflicts.append({"field": k, "kept": bv, "other": ov, "from": o["id"]})
            elif ov and bv and k in ("title",) and norm_title(ov) != norm_title(bv) and bool(bib.CJK.search(ov)) == bool(bib.CJK.search(bv)):
                conflicts.append({"field": k, "kept": bv, "other": ov, "from": o["id"]})
        if o["arxiv"] and not base["arxiv"]:
            base["arxiv"] = o["arxiv"]
            filled.append(("arxiv", o["id"]))
    base["merged_from"] = [r["id"] for r in recs if r["id"] != base["id"]]
    base["alt_titles"] = sorted({r["title"] for r in recs if r["title"] and r["title"] != base["title"]})
    return base, {"filled": filled, "conflicts": conflicts}


def clusters(recs, prefer_zh=None):
    """union-find over 'same' pairs -> ([cluster dicts], [candidate pairs], [guarded pairs]); prefer_zh: for a Chinese + Latin pair keep the entry in the manuscript's language as canonical (the other fills missing fields such as the DOI)"""
    n = len(recs)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    same_pairs, cands, guarded = [], [], []
    for i, j in sorted(blocks(recs)):
        c = compare(recs[i], recs[j])
        if c["decision"] == "same":
            parent[find(i)] = find(j)
            same_pairs.append((i, j, c))
        elif c["decision"] == "candidate":
            cands.append({"a": recs[i]["id"], "b": recs[j]["id"], **c})
        elif c["guards"]:
            guarded.append({"a": recs[i]["id"], "b": recs[j]["id"], **c})
    groups = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    out = []
    for g in groups.values():
        if len(g) < 2:
            continue
        ev = [{"a": recs[i]["id"], "b": recs[j]["id"], "rules": c["rules"], "reasons": c["reasons"], "confidence": c["confidence"], "work_pair": c["work_pair"]} for i, j, c in same_pairs if i in g and j in g]
        members = [recs[i] for i in g]
        canon = None
        if prefer_zh is not None:
            same_lang = [r for r in members if bool(bib.CJK.search(r["title"])) == prefer_zh]
            if same_lang and len(same_lang) < len(members):
                canon = sorted(same_lang, key=lambda r: (-(r["type"] != "preprint"), -completeness(r)))[0]["id"]
        merged, det = merge_records(members, canon)
        order = {"certain": 3, "high": 2, "medium": 1}
        out.append({"members": [r["id"] for r in members], "canonical": merged["id"], "confidence": min((e["confidence"] for e in ev), key=lambda c: order[c]), "evidence": ev, "fills": det["filled"], "conflicts": det["conflicts"], "work_pair": any(e["work_pair"] for e in ev)})
    return out, cands, guarded
