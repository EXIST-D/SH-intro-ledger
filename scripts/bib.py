#!/usr/bin/env python3
"""bib.py - bibliographic records: parse BibTeX / RIS / EndNote (refer) / RefWorks / NoteExpress-CNKI / CSL-JSON / plain-text reference lists into one normalised record.

Record (dict): id, type (journal | book | chapter | conference | thesis | report | standard | patent | web | preprint | other), authors[{family, given, literal, zh}], title, container (journal / book / proceedings title),
year, volume, issue, pages ("12-34"), publisher, place, doi, url, accessed, arxiv, isbn, issn, edition, language, abstract, keywords[], note, raw, source ("bibtex|ris|enw|refworks|noteexpress|csl|text"), parse{confidence, missing[]}.
Nothing is invented: a field that is not in the source stays empty and is listed in parse.missing.
"""
from __future__ import annotations

import html
import json
import re

CJK = re.compile(r"[㐀-鿿豈-﫿]")
TYPES = ("journal", "book", "chapter", "conference", "thesis", "report", "standard", "patent", "web", "preprint", "newspaper", "other")
MAP_BIBTEX = {"article": "journal", "book": "book", "inbook": "chapter", "incollection": "chapter", "inproceedings": "conference", "conference": "conference", "proceedings": "conference", "phdthesis": "thesis", "mastersthesis": "thesis",
              "techreport": "report", "report": "report", "online": "web", "electronic": "web", "misc": "other", "unpublished": "preprint", "standard": "standard", "patent": "patent", "booklet": "book", "manual": "report"}
MAP_RIS = {"JOUR": "journal", "JFULL": "journal", "BOOK": "book", "CHAP": "chapter", "CONF": "conference", "CPAPER": "conference", "THES": "thesis", "RPRT": "report", "STAND": "standard", "PAT": "patent", "ELEC": "web", "ICOMM": "web", "UNPB": "preprint",
           "GEN": "other", "MGZN": "journal", "NEWS": "other", "WEB": "web", "DATA": "other", "COMP": "other"}
MAP_TEXT_MARK = {"J": "journal", "M": "book", "C": "conference", "D": "thesis", "R": "report", "S": "standard", "P": "patent", "EB": "web", "N": "other", "A": "chapter", "G": "other", "Z": "other", "DB": "other", "CP": "other"}
LATEX_ACC = {"\\'a": "á", "\\'e": "é", "\\'i": "í", "\\'o": "ó", "\\'u": "ú", "\\`a": "à", "\\`e": "è", "\\\"a": "ä", "\\\"o": "ö", "\\\"u": "ü", "\\\"e": "ë", "\\~n": "ñ", "\\c c": "ç", "\\^o": "ô", "\\^e": "ê", "\\'c": "ć", "\\v c": "č", "\\v s": "š", "\\v z": "ž",
             "\\'A": "Á", "\\'E": "É", "\\\"A": "Ä", "\\\"O": "Ö", "\\\"U": "Ü", "\\ss": "ß", "\\o": "ø", "\\aa": "å", "\\ae": "æ", "\\l": "ł", "\\&": "&", "\\%": "%", "\\_": "_", "\\#": "#"}


def clean(s):
    if s is None:
        return ""
    s = html.unescape(str(s))
    for k, v in LATEX_ACC.items():
        s = s.replace("{" + k + "}", v).replace(k, v)
    s = re.sub(r"\{\\'\{?([aeiouAEIOU])\}?\}", lambda m: {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú", "A": "Á", "E": "É", "I": "Í", "O": "Ó", "U": "Ú"}[m.group(1)], s)
    s = re.sub(r"\\(?:textit|textbf|emph|textsc|mathrm|text)\{([^{}]*)\}", r"\1", s)
    s = s.replace("--", "–") if re.search(r"\d--\d", s) else s
    s = re.sub(r"[{}]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_doi(d):
    d = (d or "").strip()
    d = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", d, flags=re.I)
    d = re.sub(r"[\s.,;]+$", "", d)
    return d.lower() if re.match(r"10\.\d{4,9}/\S+", d) else ""


def norm_pages(p):
    p = clean(p).rstrip(".,;").replace("–", "-").replace("—", "-").replace("−", "-")
    p = re.sub(r"\s*-+\s*", "-", p)
    m = re.fullmatch(r"(\d+)-(\d+)", p)
    if m and len(m.group(2)) < len(m.group(1)) and int(m.group(2)) < int(m.group(1)):  # 1234-45 -> 1234-1245
        return "%s-%s" % (m.group(1), m.group(1)[:len(m.group(1)) - len(m.group(2))] + m.group(2))
    return p


# ------------------------------------------------------------------------------------------------ names
PARTICLES = {"van", "von", "de", "der", "den", "da", "di", "del", "della", "du", "la", "le", "bin", "al", "el", "ter", "ten", "dos", "das", "st", "mac", "mc"}
CORP = re.compile(r"\b(?:university|institute|committee|association|organization|organisation|ministry|bureau|commission|society|group|laboratory|council|department|center|centre|office|press|company|corporation|inc\.?|ltd\.?|consortium|collaboration|world health|大学|研究所|研究院|委员会|协会|学会|部|局|办公室|公司|中心|出版社|科学院|工作组|联盟)\b", re.I)


def parse_name(s):
    s = clean(s).strip(" ;,")
    if not s:
        return None
    if CJK.search(s):
        s2 = re.sub(r"\s+", "", s)
        if len(s2) <= 4 or re.fullmatch(r"[㐀-鿿·]+", s2):
            if CORP.search(s2) or len(s2) > 4:
                return {"family": "", "given": "", "literal": s2, "zh": True}
            fam = 2 if (s2[:2] in COMPOUND_ZH) else 1
            return {"family": s2[:fam], "given": s2[fam:], "literal": s2, "zh": True}
        return {"family": "", "given": "", "literal": s, "zh": True}
    if CORP.search(s) and "," not in s:
        return {"family": "", "given": "", "literal": s, "zh": False}
    if "," in s:
        fam, giv = [x.strip() for x in s.split(",", 1)]
    else:
        toks = s.split()
        if len(toks) == 1:
            return {"family": toks[0], "given": "", "literal": s, "zh": False}
        # trailing initials ("Smith JA", "KNUTH D E") vs leading ("J. A. Smith")
        k = len(toks)
        while k > 1 and re.fullmatch(r"[A-Z]{1,3}\.?|[A-Z]\.[A-Z]\.?", toks[k - 1]) and not (k == len(toks) and toks[0].lower() in PARTICLES):
            k -= 1
        if k < len(toks) and k >= 1 and not re.fullmatch(r"[A-Z]\.?|[A-Z]\.[A-Z]\.?", toks[0]) and re.fullmatch(r"[A-Z][\w'’-]*", toks[0]):
            fam, giv = " ".join(toks[:k]), " ".join(toks[k:])
        else:
            i = len(toks) - 1
            while i > 0 and toks[i - 1].lower() in PARTICLES:
                i -= 1
            fam, giv = " ".join(toks[i:]), " ".join(toks[:i])
    return {"family": fam, "given": giv, "literal": "", "zh": False}


COMPOUND_ZH = {"欧阳", "司马", "上官", "诸葛", "东方", "皇甫", "尉迟", "公孙", "慕容", "令狐", "司徒", "夏侯", "轩辕", "宇文", "长孙", "南宫", "端木", "闻人", "独孤", "西门"}


INIT_FIRST = re.compile(r"^(?:[A-Z]\.?\s*){1,3}(?:[A-Z][\w'’-]+|[a-z]+\s+[A-Z][\w'’-]+)(?:\s+[A-Z][\w'’-]+)?$")


def split_authors(s):
    s = clean(s).replace("，", ",").replace("、", ",").replace("；", ";")
    s = re.sub(r"\bet\s+al\.?|等\.?$", "", s).strip(" ,;")
    if not s:
        return []
    if CJK.search(s) and not re.search(r"[A-Za-z]{3}", s):
        return [x for x in (parse_name(p) for p in re.split(r"[,;]", s) if p.strip()) if x]
    toks = [p.strip() for p in re.split(r"\s*(?:;|,?\s*&\s|,?\s+and\s)\s*", s) if p.strip()]
    if len(toks) > 1:
        out = []
        for tk in toks:
            pp = [p.strip() for p in tk.split(",") if p.strip()]
            if len(pp) >= 4 and len(pp) % 2 == 0 and all(re.fullmatch(r"(?:[A-Z][a-z]?\.?[\s-]*){1,3}|[A-Z][a-z]+(?:\s+[A-Z]\.?)?", pp[i]) for i in range(1, len(pp), 2)):
                out += [parse_name(pp[i] + ", " + pp[i + 1]) for i in range(0, len(pp), 2)]
            elif tk.count(",") >= 1 and not re.search(r"[A-Za-z]+,\s*[A-Z]", tk) and re.search(r",\s*[A-Z][a-z]+\s+[A-Z]", tk):
                out += [parse_name(p) for p in tk.split(",") if p.strip()]
            elif tk.count(",") >= 2 and INIT_FIRST.match(tk.split(",")[0].strip()):
                out += [parse_name(p) for p in tk.split(",") if p.strip()]
            else:
                out.append(parse_name(tk))
        return [x for x in out if x]
    parts = [p.strip() for p in s.split(",") if p.strip()]
    if len(parts) > 1 and all(INIT_FIRST.match(p) for p in parts):
        return [x for x in (parse_name(p) for p in parts) if x]
    if len(parts) >= 2 and len(parts) % 2 == 0 and all(re.fullmatch(r"(?:[A-Z][a-z]?\.?\s*){1,3}|[A-Z][a-z]+(?:\s+[A-Z]\.?)?", parts[i]) and not parts[i].split()[0].lower() in PARTICLES for i in range(1, len(parts), 2)) and all(re.search(r"[a-z]{2}", parts[i]) or parts[i].isupper() for i in range(0, len(parts), 2)):
        return [x for x in (parse_name(parts[i] + ", " + parts[i + 1]) for i in range(0, len(parts), 2)) if x]
    return [x for x in (parse_name(p) for p in parts) if x]


def bib_authors(s):
    """BibTeX 'A and B and C' with 'Family, Given' or 'Given Family'"""
    parts = re.split(r"\s+and\s+", clean(s))
    out = []
    for p in parts:
        if p.strip().lower() in ("others", "et al", "et al."):
            continue
        n = parse_name(p)
        if n:
            out.append(n)
    return out


# ------------------------------------------------------------------------------------------------ record
def new_record(src, raw=""):
    return {"id": "", "type": "other", "authors": [], "title": "", "container": "", "year": "", "volume": "", "issue": "", "pages": "", "publisher": "", "place": "", "doi": "", "url": "", "accessed": "", "arxiv": "", "isbn": "", "issn": "",
            "edition": "", "language": "", "abstract": "", "keywords": [], "note": "", "number": "", "date": "", "translators": [], "editors": [], "container_authors": [], "authors_role": "", "raw": raw, "source": src, "parse": {}}


def finish(r):
    r["title"] = clean(r["title"]).rstrip(".")
    r["container"] = clean(r["container"])
    r["year"] = re.search(r"(?:1[5-9]|20)\d{2}", str(r["year"])).group(0) if re.search(r"(?:1[5-9]|20)\d{2}", str(r["year"])) else ""
    r["doi"] = norm_doi(r["doi"]) or norm_doi(r["url"])
    m = re.search(r"arxiv[:.\s/]*(\d{4}\.\d{4,5}(?:v\d+)?|[a-z-]+(?:\.[A-Z]{2})?/\d{7})", " ".join([r["arxiv"], r["url"], r["note"], r["container"]]), re.I)
    r["arxiv"] = m.group(1) if m else r["arxiv"]
    r["pages"] = norm_pages(r["pages"])
    r["language"] = r["language"] or ("zh" if CJK.search(r["title"]) else "en")
    if r["type"] in ("other", "journal") and r["arxiv"] and (not r["container"] or re.search(r"arxiv|biorxiv|medrxiv|preprint|ssrn", r["container"], re.I)):
        r["type"] = "preprint"
    need = ["authors", "title", "year"] + (["container"] if r["type"] in ("journal", "conference", "chapter") else []) + (["publisher"] if r["type"] in ("book", "report", "standard") else [])
    miss = [k for k in need if not r.get(k)]
    if r["type"] == "journal" and not (r["volume"] or r["pages"] or r["doi"]):
        miss.append("volume/pages/doi")
    r["parse"] = {"missing": miss, "confidence": round(max(0.2, 1.0 - 0.18 * len(miss)), 2) if r["source"] != "text" else r["parse"].get("confidence", 0.6)}
    return r


# ------------------------------------------------------------------------------------------------ BibTeX
def parse_bibtex(text):
    out, i, n = [], 0, len(text)
    strings = {"jan": "January", "feb": "February", "mar": "March", "apr": "April", "may": "May", "jun": "June", "jul": "July", "aug": "August", "sep": "September", "oct": "October", "nov": "November", "dec": "December"}
    while True:
        m = re.compile(r"@(\w+)\s*([({])").search(text, i)
        if not m:
            break
        typ, op = m.group(1).lower(), m.group(2)
        close = ")" if op == "(" else "}"
        j, depth = m.end(), 1
        while j < n and depth:
            c = text[j]
            if c == "\\":
                j += 2
                continue
            depth += (c == op) - (c == close) if op == "{" else (c == "(") - (c == ")")
            j += 1
        body = text[m.end():j - 1]
        i = j
        if typ in ("comment", "preamble"):
            continue
        if typ == "string":
            ms = re.match(r"\s*(\w+)\s*=\s*(.*)$", body, re.S)
            if ms:
                strings[ms.group(1).lower()] = clean(ms.group(2).strip().strip('{}"'))
            continue
        key, _, rest = body.partition(",")
        fields, k = {}, 0
        for mf in re.finditer(r"(\w[\w-]*)\s*=\s*", rest):
            if mf.start() < k:
                continue
            p = mf.end()
            val, k = read_value(rest, p, strings)
            fields[mf.group(1).lower()] = val
        r = new_record("bibtex", "@%s{%s,%s}" % (typ, key.strip(), rest)[:2000])
        r["id"] = key.strip()
        r["type"] = MAP_BIBTEX.get(typ, "other")
        f = lambda *ks: next((fields[x] for x in ks if fields.get(x)), "")
        r["authors"] = bib_authors(f("author", "editor"))
        r["authors_role"] = "editor" if not fields.get("author") and fields.get("editor") else ""
        if fields.get("author") and fields.get("editor"):
            r["editors"] = bib_authors(fields["editor"])
        r["title"] = f("title")
        r["container"] = f("journal", "journaltitle", "booktitle", "series") if r["type"] != "book" else f("series")
        r["year"] = f("year", "date")
        r["volume"], r["issue"], r["pages"] = f("volume"), f("number", "issue"), f("pages")
        r["publisher"] = f("publisher", "school", "institution", "organization")
        r["place"] = f("address", "location")
        r["doi"], r["url"], r["isbn"], r["issn"] = f("doi"), f("url"), f("isbn"), f("issn")
        r["edition"] = f("edition")
        r["language"] = {"chinese": "zh", "zh": "zh", "english": "en", "en": "en"}.get(f("language").lower(), "")
        r["abstract"] = clean(f("abstract"))
        r["keywords"] = [x.strip() for x in re.split(r"[;,]", clean(f("keywords"))) if x.strip()]
        r["note"] = f("note")
        if re.search(r"eprint|archiveprefix", " ".join(fields)) and fields.get("archiveprefix", "").lower() == "arxiv":
            r["arxiv"] = fields.get("eprint", "")
        if typ == "phdthesis":
            r["note"] = (r["note"] + " PhD thesis").strip()
        elif typ == "mastersthesis":
            r["note"] = (r["note"] + " Master thesis").strip()
        out.append(finish(r))
    return out


def read_value(s, p, strings):
    parts, n = [], len(s)
    while p < n:
        while p < n and s[p] in " \t\r\n":
            p += 1
        if p >= n:
            break
        c = s[p]
        if c == "{":
            d, q = 1, p + 1
            while q < n and d:
                if s[q] == "\\":
                    q += 2
                    continue
                d += (s[q] == "{") - (s[q] == "}")
                q += 1
            parts.append(s[p + 1:q - 1])
            p = q
        elif c == '"':
            q = p + 1
            while q < n and s[q] != '"':
                q += 2 if s[q] == "\\" else 1
            parts.append(s[p + 1:q])
            p = q + 1
        else:
            m = re.match(r"[\w.:-]+", s[p:])
            if not m:
                break
            w = m.group(0)
            parts.append(strings.get(w.lower(), w))
            p += len(w)
        while p < n and s[p] in " \t\r\n":
            p += 1
        if p < n and s[p] == "#":
            p += 1
            continue
        break
    while p < n and s[p] in " \t\r\n,":
        p += 1
    return "".join(parts), p


# ------------------------------------------------------------------------------------------------ RIS / EndNote / RefWorks / NoteExpress
def parse_ris(text):
    out, cur = [], None
    for ln in text.splitlines():
        m = re.match(r"^([A-Z][A-Z0-9])  - ?(.*)$", ln)
        if not m:
            if cur is not None and ln.strip() and cur["_last"] in ("AB", "N2", "TI", "T1", "N1"):
                cur["f"][cur["_last"]][-1] += " " + ln.strip()
            continue
        tag, val = m.group(1), m.group(2).strip()
        if tag == "TY":
            cur = {"f": {}, "_last": tag, "ty": val}
            continue
        if cur is None:
            continue
        if tag == "ER":
            out.append(ris_record(cur))
            cur = None
            continue
        cur["f"].setdefault(tag, []).append(val)
        cur["_last"] = tag
    if cur is not None and cur["f"]:
        out.append(ris_record(cur))
    return out


def ris_record(cur):
    f = cur["f"]
    g = lambda *ks: next((f[k][0] for k in ks if f.get(k)), "")
    r = new_record("ris", "\n".join("%s  - %s" % (k, v) for k, vs in f.items() for v in vs)[:2000])
    r["id"] = g("ID", "L1", "M3")
    r["type"] = MAP_RIS.get(cur["ty"], "other")
    r["authors"] = [parse_name(x) for x in (f.get("AU", []) + f.get("A1", []) + f.get("A2", [])[:0]) if x]
    r["title"] = g("TI", "T1", "CT")
    r["container"] = g("JO", "JF", "T2", "JA", "BT", "J2")
    r["year"] = g("PY", "Y1", "DA")
    r["volume"], r["issue"] = g("VL"), g("IS")
    r["pages"] = (g("SP") + ("-" + g("EP") if g("EP") else "")) if g("SP") else g("EP")
    r["publisher"], r["place"] = g("PB"), g("CY")
    r["doi"], r["url"] = g("DO"), g("UR", "L2")
    sn = g("SN")
    if re.fullmatch(r"[\d-]{9}[\dXx]|97[89][\d-]{10}", sn.replace(" ", "")):
        r["isbn" if len(re.sub(r"\D", "", sn)) >= 10 else "issn"] = sn
    else:
        r["issn"] = sn
    r["abstract"] = g("AB", "N2")
    r["keywords"] = f.get("KW", [])
    r["note"] = g("N1")
    r["language"] = {"chi": "zh", "zh": "zh", "eng": "en", "en": "en"}.get(g("LA").lower(), "")
    r["authors"] = [x for x in r["authors"] if x]
    return finish(r)


MAP_ENW = {"Journal Article": "journal", "Book": "book", "Book Section": "chapter", "Conference Paper": "conference", "Conference Proceedings": "conference", "Thesis": "thesis", "Report": "report", "Standard": "standard", "Patent": "patent",
           "Web Page": "web", "Electronic Article": "journal", "Generic": "other", "Magazine Article": "journal", "Newspaper Article": "other", "Journal": "journal", "Dissertation": "thesis", "Preprint": "preprint"}


def parse_enw(text):
    out, cur = [], None
    for ln in text.splitlines():
        m = re.match(r"^%(.) (.*)$", ln)
        if not m:
            if ln.strip() == "" and cur and cur["f"]:
                out.append(enw_record(cur))
                cur = None
            elif cur and ln.strip() and cur.get("_last"):
                cur["f"][cur["_last"]][-1] += " " + ln.strip()
            continue
        tag, val = m.group(1), m.group(2).strip()
        if tag == "0":
            if cur and cur["f"]:
                out.append(enw_record(cur))
            cur = {"f": {}, "ty": val}
            continue
        if cur is None:
            continue
        cur["f"].setdefault(tag, []).append(val)
        cur["_last"] = tag
    if cur and cur["f"]:
        out.append(enw_record(cur))
    return out


def enw_record(cur):
    f = cur["f"]
    g = lambda k: f[k][0] if f.get(k) else ""
    r = new_record("enw", "\n".join("%%%s %s" % (k, v) for k, vs in f.items() for v in vs)[:2000])
    r["type"] = MAP_ENW.get(cur["ty"], "other")
    r["authors"] = [x for x in (parse_name(a) for a in f.get("A", [])) if x]
    r["title"] = g("T")
    r["container"] = g("J") or g("B")
    r["year"], r["volume"], r["issue"], r["pages"] = g("D"), g("V"), g("N"), g("P")
    r["publisher"], r["place"] = g("I"), g("C")
    r["doi"] = g("R") if g("R").startswith("10.") or "doi" in g("R").lower() else ""
    r["url"], r["abstract"], r["edition"] = g("U"), g("X"), g("7")
    sn = g("@")
    r["isbn" if len(re.sub(r"\D", "", sn)) >= 10 else "issn"] = sn
    r["keywords"] = [k.strip() for k in re.split(r"[;,]", g("K")) if k.strip()]
    r["language"] = {"Chinese": "zh", "chi": "zh", "English": "en", "eng": "en"}.get(g("G"), "")
    return finish(r)


def parse_refworks(text):
    out, cur = [], None
    for ln in text.splitlines():
        m = re.match(r"^([A-Z][A-Z0-9]) (.*)$", ln)
        if ln.startswith("RT "):
            if cur and cur["f"]:
                out.append(refworks_record(cur))
            cur = {"f": {}, "ty": ln[3:].strip()}
            continue
        if cur is None or not m:
            continue
        cur["f"].setdefault(m.group(1), []).append(m.group(2).strip())
    if cur and cur["f"]:
        out.append(refworks_record(cur))
    return out


def refworks_record(cur):
    f = cur["f"]
    g = lambda *ks: next((f[k][0] for k in ks if f.get(k)), "")
    r = new_record("refworks", "\n".join("%s %s" % (k, v) for k, vs in f.items() for v in vs)[:2000])
    r["type"] = MAP_ENW.get(cur["ty"], "other")
    r["authors"] = [x for x in (parse_name(a) for a in f.get("A1", [])) if x]
    r["title"], r["container"] = g("T1"), g("JF", "JO", "T2")
    r["year"], r["volume"], r["issue"] = g("YR"), g("VO"), g("IS")
    r["pages"] = (g("SP") + ("-" + g("OP") if g("OP") else "")) if g("SP") else ""
    r["publisher"], r["place"], r["doi"], r["url"] = g("PB"), g("PP"), g("DO"), g("LK", "UL")
    r["abstract"] = g("AB")
    r["keywords"] = [k.strip() for k in re.split(r"[;,]", g("K1")) if k.strip()]
    r["isbn" if len(re.sub(r"\D", "", g("SN"))) >= 10 else "issn"] = g("SN")
    return finish(r)


def parse_noteexpress(text):
    out, cur = [], None
    for ln in text.splitlines():
        m = re.match(r"^\{([^}]+)\}\s*[:：]\s*(.*)$", ln)
        if not m:
            continue
        k, v = m.group(1).strip(), m.group(2).strip()
        if k == "Reference Type":
            if cur:
                out.append(ne_record(cur))
            cur = {"ty": v, "f": {}}
        elif cur is not None:
            cur["f"][k] = v
    if cur:
        out.append(ne_record(cur))
    return out


def ne_record(cur):
    f = cur["f"]
    g = lambda *ks: next((f[k] for k in ks if f.get(k)), "")
    r = new_record("noteexpress", "\n".join("{%s}: %s" % kv for kv in f.items())[:2000])
    r["type"] = MAP_ENW.get(cur["ty"], {"期刊论文": "journal", "图书": "book", "会议论文": "conference", "学位论文": "thesis", "标准": "standard", "专利": "patent", "报告": "report"}.get(cur["ty"], "other"))
    r["authors"] = [x for x in (parse_name(a) for a in re.split(r"[;；]", g("Author", "作者")) if a.strip()) if x]
    r["title"] = g("Title", "题名", "Title-Chinese")
    r["container"] = g("Journal", "Source", "刊名", "Secondary Title", "Book Title")
    r["year"], r["volume"], r["issue"], r["pages"] = g("Year", "年"), g("Volume", "卷"), g("Issue", "期"), g("Pages", "页码", "Start Page")
    r["publisher"], r["place"] = g("Publisher", "出版社"), g("Place Published", "出版地")
    r["doi"], r["url"], r["abstract"] = g("DOI"), g("URL"), g("Abstract", "摘要")
    r["keywords"] = [k.strip() for k in re.split(r"[;；,]", g("Keywords", "关键词")) if k.strip()]
    r["issn"] = g("ISBN/ISSN", "ISSN")
    r["note"] = g("Title-English") and "English title: " + g("Title-English") or ""
    return finish(r)


# ------------------------------------------------------------------------------------------------ CSL-JSON
def parse_csl(text):
    data = json.loads(text)
    if isinstance(data, dict):
        data = data.get("items") or data.get("references") or [data]
    out = []
    for it in data:
        r = new_record("csl", json.dumps(it, ensure_ascii=False)[:2000])
        r["id"] = str(it.get("id") or it.get("citation-key") or "")
        r["type"] = {"article-journal": "journal", "book": "book", "chapter": "chapter", "paper-conference": "conference", "thesis": "thesis", "report": "report", "standard": "standard", "patent": "patent", "webpage": "web", "post-weblog": "web",
                     "article": "preprint", "dataset": "other", "article-newspaper": "newspaper", "article-magazine": "journal", "legislation": "standard", "bill": "standard"}.get(it.get("type", ""), "other")
        for a in it.get("author", []):
            r["authors"].append({"family": a.get("family", ""), "given": a.get("given", ""), "literal": a.get("literal", ""), "zh": bool(CJK.search(a.get("family", "") + a.get("literal", "")))})
        for k, key in (("translators", "translator"), ("editors", "editor"), ("container_authors", "container-author")):
            for a in it.get(key, []):
                r[k].append({"family": a.get("family", ""), "given": a.get("given", ""), "literal": a.get("literal", ""), "zh": bool(CJK.search(a.get("family", "") + a.get("literal", "")))})
        if not r["authors"] and r["editors"]:
            r["authors"], r["authors_role"], r["editors"] = r["editors"], "editor", []
        r["title"], r["container"] = it.get("title", ""), it.get("container-title", "")
        dp = (it.get("issued") or {}).get("date-parts") or [[""]]
        r["year"] = str(dp[0][0]) if dp and dp[0] else ""
        r["volume"], r["issue"], r["pages"] = str(it.get("volume", "")), str(it.get("issue", "")), str(it.get("page", ""))
        r["publisher"], r["place"] = it.get("publisher", ""), it.get("publisher-place", "")
        r["doi"], r["url"], r["isbn"], r["issn"] = it.get("DOI", ""), it.get("URL", ""), it.get("ISBN", ""), it.get("ISSN", "")
        r["edition"], r["language"], r["abstract"] = str(it.get("edition", "")), it.get("language", "")[:2], it.get("abstract", "")
        r["note"] = it.get("note", "")
        r["number"] = str(it.get("number", ""))
        dp0 = (it.get("issued") or {}).get("date-parts") or [[]]
        r["date"] = "-".join("%02d" % int(x) if i else str(x) for i, x in enumerate(dp0[0])) if dp0 and dp0[0] and len(dp0[0]) > 1 else ""
        r["keywords"] = [k.strip() for k in re.split(r"[;,]", it.get("keyword", "")) if k.strip()]
        ac = (it.get("accessed") or {}).get("date-parts")
        r["accessed"] = "-".join("%02d" % int(x) if i else str(x) for i, x in enumerate(ac[0])) if ac and ac[0] else ""
        out.append(finish(r))
    return out


def to_csl(r):
    """normalised record -> CSL-JSON item (for citeproc oracles and for export)"""
    t = {"journal": "article-journal", "book": "book", "chapter": "chapter", "conference": "paper-conference", "thesis": "thesis", "report": "report", "standard": "standard", "patent": "patent", "web": "webpage", "preprint": "article", "newspaper": "article-newspaper", "other": "document"}[r["type"]]
    it = {"id": r["id"], "type": t, "title": r["title"]}
    au = []
    for a in r["authors"]:
        au.append({"literal": a["literal"]} if a.get("literal") else {"family": a["family"], "given": a["given"]})
    if au:
        it["editor" if r.get("authors_role") == "editor" else "author"] = au
    for k, key in (("translators", "translator"), ("editors", "editor"), ("container_authors", "container-author")):
        if r.get(k):
            it[key] = [{"literal": a["literal"]} if a.get("literal") else {"family": a["family"], "given": a["given"]} for a in r[k]]
    for k, ck in (("container", "container-title"), ("volume", "volume"), ("issue", "issue"), ("pages", "page"), ("publisher", "publisher"), ("place", "publisher-place"), ("doi", "DOI"), ("url", "URL"), ("isbn", "ISBN"), ("issn", "ISSN"), ("edition", "edition"), ("abstract", "abstract"), ("note", "note"), ("number", "number")):
        if r.get(k):
            it[ck] = r[k]
    if r["year"]:
        it["issued"] = {"date-parts": [[int(r["year"])]]}
    if r["language"]:
        it["language"] = {"zh": "zh-CN", "en": "en-US"}.get(r["language"], r["language"])
    return it


# ------------------------------------------------------------------------------------------------ plain-text reference entries
def parse_text_entry(s):
    """one formatted reference (GB/T 7714, APA, IEEE, Vancouver, Chicago-ish) -> record with a parse confidence. Heuristic: fields that are not recognised stay empty."""
    raw = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"^\s*(?:\[\d+\]|\(\d+\)|\d+[.)])\s*", "", raw)
    s = re.sub(r"(?<![\w*_])(\*{1,2}|_{1,2})(?=\S)(.+?)(?<=\S)\1(?![\w*_])", r"\2", s)  # Markdown emphasis from a previously formatted list
    r = new_record("text", raw)
    doi = re.search(r"\b(10\.\d{4,9}/[^\s,;]+[^\s,;.])", s)
    r["doi"] = doi.group(1) if doi else ""
    url = re.search(r"https?://[^\s]+", s)
    r["url"] = re.sub(r"[.,;]+$", "", url.group(0)) if url else ""
    ax = re.search(r"arXiv[:\s]*(\d{4}\.\d{4,5}(?:v\d+)?)", s, re.I)
    r["arxiv"] = ax.group(1) if ax else ""
    conf = 0.3
    body = re.sub(r"(?:DOI|doi)\s*[:：]?\s*10\.\S+|https?://\S+", "", s).strip()
    mark = re.search(r"\[(J|M|C|D|R|S|P|EB(?:/OL)?|N|A|G|Z|DB(?:/OL)?|CP(?:/OL)?|M/OL|J/OL)\]", body)
    if mark:  # GB/T 7714
        typ = MAP_TEXT_MARK.get(mark.group(1).split("/")[0], "other")
        r["type"] = typ
        head, tail = body[:mark.start()], body[mark.end():]
        parts = re.split(r"\.\s+(?=[^.]*$)", head, maxsplit=1)
        m2 = re.match(r"(.+?)\.\s+(.+)$", head)
        if m2:
            r["authors"] = split_authors(m2.group(1))
            r["title"] = m2.group(2)
        else:
            r["title"] = head
        tail = tail.lstrip(". ").strip()
        m3 = re.match(r"(?://\s*)?(.*?)[.,，]\s*((?:1[5-9]|20)\d{2})\s*(?:[,，:：]\s*(\d+)?\s*(?:\((\d+[\w-]*)\))?\s*[:：]\s*([\d+\-–]+))?", tail)
        if typ == "journal" and m3:
            r["container"], r["year"], r["volume"], r["issue"], r["pages"] = m3.group(1), m3.group(2), m3.group(3) or "", m3.group(4) or "", m3.group(5) or ""
            conf = 0.85
        elif typ in ("book", "thesis", "report", "standard", "patent") or "M" in mark.group(1):
            mm = re.match(r"(?:(\d+(?:st|nd|rd|th)?\s*ed\.?|第?\d+版)(?:[.,，]\s*|\s+))?(?:(.+?)[:：]\s*)?(.+?)[,，]\s*((?:1[5-9]|20)\d{2})(?:\s*[:：]\s*([\d\-–]+))?", tail)
            if mm:
                r["edition"], r["place"], r["publisher"], r["year"], r["pages"] = mm.group(1) or "", mm.group(2) or "", mm.group(3), mm.group(4), mm.group(5) or ""
                conf = 0.8
        elif typ == "conference":
            mm = re.match(r"(?://)?\s*(.+?)[.,，]\s*(?:(.+?)[:：]\s*)?(.+?)[,，]\s*((?:1[5-9]|20)\d{2})(?:[:：]\s*([\d+\-–]+))?", tail)
            if mm:
                r["container"], r["place"], r["publisher"], r["year"], r["pages"] = mm.group(1), mm.group(2) or "", mm.group(3), mm.group(4), mm.group(5) or ""
                conf = 0.7
        if not r["year"]:
            y = re.search(r"((?:1[5-9]|20)\d{2})", tail)
            r["year"] = y.group(1) if y else ""
            conf = max(conf, 0.5) if y else conf
        return finish(r) if r.__setitem__("parse", {"confidence": conf}) is None else r
    # APA / Chicago-like:  Authors (Year). Title. Journal, vol(issue), pages.
    m = re.match(r"(.+?)\s*\(((?:1[5-9]|20)\d{2}[a-z]?|n\.d\.)\)\.?\s*(.+)$", body)
    if m:
        r["authors"] = split_authors(m.group(1))
        r["year"] = m.group(2)
        rest = m.group(3)
        mt = re.match(r"(.+?[?!.])\s+(.+)$", rest)
        if mt:
            r["title"] = mt.group(1).rstrip(".")
            tail = mt.group(2)
            mj = re.match(r"\*?_?([^,*_]+?)\*?_?,\s*\*?(\d+)\*?(?:\((\d+[\w-]*)\))?(?:,\s*([\dA-Za-z.\-–]+))?", tail)
            if mj:
                r["type"], r["container"], r["volume"], r["issue"], r["pages"] = "journal", mj.group(1), mj.group(2), mj.group(3) or "", mj.group(4) or ""
                conf = 0.8
            else:
                mb = re.match(r"(?:In\s+(.+?)\s+\(pp\.\s*([\d\-–]+)\)\.\s*)?([^.]+)\.?", tail)
                if mb:
                    r["publisher"] = mb.group(3).strip()
                    r["container"] = mb.group(1) or ""
                    r["pages"] = mb.group(2) or ""
                    r["type"] = "chapter" if mb.group(1) else "book"
                    conf = 0.6
                    if re.search(r"arxiv|biorxiv|medrxiv|preprint|ssrn", r["publisher"] + " " + r["container"], re.I) or (r["arxiv"] and not r["publisher"].strip()):
                        r["type"], r["container"], r["publisher"] = "preprint", "arXiv" if r["arxiv"] else r["publisher"], ""
                        conf = 0.75
        return finish(r) if r.__setitem__("parse", {"confidence": conf}) is None else r
    # IEEE:  A. Author, B. Author, "Title," Journal, vol. x, no. y, pp. a-b, Mon. Year.
    m = re.match(r"(.+?),\s*[\"“](.+?)[,.]?[\"”]\s*,?\s*(.+)$", body)
    if m:
        r["authors"] = split_authors(re.sub(r"\band\b", ",", m.group(1)))
        r["title"] = m.group(2).rstrip(",")
        tail = m.group(3)
        y = re.search(r"((?:1[5-9]|20)\d{2})", tail)
        r["year"] = y.group(1) if y else ""
        mc = re.match(r"(?:in\s+)?([^,]+)", tail, re.I)
        r["container"] = mc.group(1).strip() if mc else ""
        for k, pat in (("volume", r"vol\.?\s*(\d+)"), ("issue", r"no\.?\s*(\d+[\w-]*)"), ("pages", r"pp?\.?\s*([\d\-–]+)")):
            mm = re.search(pat, tail)
            r[k] = mm.group(1) if mm else ""
        r["type"] = "conference" if re.search(r"proc|conf|symposium|workshop", r["container"], re.I) else "journal"
        conf = 0.75
        return finish(r) if r.__setitem__("parse", {"confidence": conf}) is None else r
    # Vancouver:  Author AB, Author CD. Title. Journal. Year;vol(issue):pages.
    m = re.match(r"(.+?)\.\s+(.+?)\.\s+(.+?)\.\s*((?:1[5-9]|20)\d{2})(?:\s+\w+)?\s*;\s*(\d+)(?:\((\d+[\w-]*)\))?\s*:\s*([\w\-–]+)", body)
    if m:
        r["authors"] = split_authors(m.group(1))
        r["title"], r["container"], r["year"], r["volume"], r["issue"], r["pages"], r["type"] = m.group(2), m.group(3), m.group(4), m.group(5), m.group(6) or "", m.group(7), "journal"
        return finish(r) if r.__setitem__("parse", {"confidence": 0.75}) is None else r
    y = re.search(r"((?:1[5-9]|20)\d{2})", body)
    r["year"] = y.group(1) if y else ""
    r["title"] = body[:120]
    r["parse"] = {"confidence": 0.2}
    r = finish(r)
    r["parse"]["confidence"] = 0.2
    r["parse"]["missing"] = sorted(set(r["parse"].get("missing", []) + ["unparsed: structure not recognised"]))
    return r


# ------------------------------------------------------------------------------------------------ dispatch
def sniff(text, name=""):
    ext = name.lower().rsplit(".", 1)[-1] if "." in name else ""
    t = text.lstrip("\ufeff \n\t")
    if ext in ("bib", "bibtex") or re.match(r"@\w+\s*[{(]", t):
        return "bibtex"
    if ext == "ris" or re.match(r"TY  - ", t) or re.search(r"(?m)^TY  - ", t):
        return "ris"
    if ext in ("enw", "txt") and re.search(r"(?m)^%0 ", t):
        return "enw"
    if re.search(r"(?m)^RT ", t) and re.search(r"(?m)^A1 ", t):
        return "refworks"
    if re.search(r"(?m)^\{Reference Type\}\s*[:：]", t):
        return "noteexpress"
    if t[:1] in "[{" and ext in ("json", ""):
        try:
            json.loads(t)
            return "csl"
        except ValueError:
            pass
    return "text"


def parse_text_list(text):
    """a pasted reference list: numbered entries ([1] ..., 1. ...) or one entry per paragraph / line"""
    ents = re.split(r"(?m)^\s*(?:\[\d+\]|\(\d+\)|\d+[.)])\s+", text)
    ents = [e.strip() for e in ents if e.strip()]
    if len(ents) <= 1:
        ents = [e.strip() for e in re.split(r"\n\s*\n|\n(?=[A-Z\u4e00-\u9fff])", text) if len(e.strip()) > 20]
    return [parse_text_entry(e) for e in ents]


def parse_any(text, name=""):
    kind = sniff(text, name)
    fn = {"bibtex": parse_bibtex, "ris": parse_ris, "enw": parse_enw, "refworks": parse_refworks, "noteexpress": parse_noteexpress, "csl": parse_csl, "text": parse_text_list}[kind]
    recs = fn(text)
    for i, r in enumerate(recs, 1):
        r["id"] = r["id"] or "ref%03d" % i
        r["authors"] = [a for a in r["authors"] if a]
    return kind, recs
