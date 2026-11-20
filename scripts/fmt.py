#!/usr/bin/env python3
"""fmt.py - format normalised records in a target reference style (GB/T 7714-2015 numeric, APA 7, IEEE, Vancouver) and export BibTeX / RIS.

Plain text with Markdown italics (`*...*`) where the style italicises (APA, IEEE); `italic=False` removes them. GB/T 7714 punctuation can be ASCII (as in the standard's own examples) or full-width for Chinese entries (`punct`).
A field the record does not have is left out - never invented; the formatter reports which required fields were missing.
"""
from __future__ import annotations

import re

import bib

STYLES = ("gbt7714", "apa7", "ieee", "vancouver")
MONTHS = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "Jun.", "Jul.", "Aug.", "Sep.", "Oct.", "Nov.", "Dec."]
GB_MARK = {"journal": "J", "book": "M", "chapter": "M", "conference": "C", "thesis": "D", "report": "R", "standard": "S", "patent": "P", "web": "EB", "preprint": "EB", "newspaper": "N", "other": "Z"}
ZH_ETAL, EN_ETAL = "等", "et al"


def initials(given, dots=True, space=True):
    g = re.sub(r"[.\-]", " ", given or "").split()
    toks = []
    for p in g:
        if bib.CJK.search(p):
            toks.append(p)
        elif p.isupper() and len(p) <= 3:
            toks += list(p)
        else:
            toks.append(p[0].upper())
    sep = (". " if space else ".") if dots else (" " if space else "")
    return (sep.join(toks) + ("." if dots and toks else "")).strip()


def plain_i(s, italic):
    return "*%s*" % s if italic and s else s


def last_page(p):
    return p.split("-")[0] if p else ""


def ensure_dot(s):
    return s if not s or s.endswith((".", "?", "!", "。")) else s + "."


# ------------------------------------------------------------------------------------------------ GB/T 7714-2015
def gb_authors(r, fw):
    au = r["authors"]
    zh_entry = bib.CJK.search(r["title"] or "") is not None
    names = []
    for a in au[:3] if len(au) > 3 else au:
        if a.get("literal"):
            names.append(a["literal"])
        elif a.get("zh"):
            names.append(a["family"] + a["given"])
        else:
            names.append("%s %s" % (a["family"].upper(), initials(a["given"], dots=False, space=True)) if a["given"] else a["family"].upper())
    sep = "，" if (fw and zh_entry) else ", "
    s = sep.join(names)
    if len(au) > 3:
        s += sep + (ZH_ETAL if zh_entry else EN_ETAL)
    return s


def gb_people(lst, fw, zh_entry):
    names = []
    for a in lst[:3] if len(lst) > 3 else lst:
        names.append(a["literal"] if a.get("literal") else (a["family"] + a["given"] if a.get("zh") else ("%s %s" % (a["family"].upper(), initials(a["given"], dots=False, space=True)) if a["given"] else a["family"].upper())))
    sep = "，" if (fw and zh_entry) else ", "
    return sep.join(names) + (sep + (ZH_ETAL if zh_entry else EN_ETAL) if len(lst) > 3 else "")


def format_gbt(r, fw=False, italic=False):
    zh = bib.CJK.search(r["title"] or "") is not None
    P = (lambda ascii_, wide: wide if (fw and zh) else ascii_)
    comma, colon = P(", ", "，"), P(": ", "：")
    t = r["type"]
    online = bool(r["url"] and not r["doi"]) or (r["url"] and t in ("web", "preprint"))
    mark = GB_MARK.get(t, "Z") + ("/OL" if (r["url"] and not (t == "web")) or t == "web" else "")
    if t == "journal" and not r["url"]:
        mark = "J"
    au = gb_authors(r, fw)
    title = r["title"] + ((colon.strip() + " " + r["number"]) if r["number"] and t in ("standard", "report") else "")
    if r["volume"] and t in ("book", "chapter"):
        title += colon.strip() + (" " if not zh else "") + ("第%s卷" % r["volume"] if zh and r["volume"].isdigit() else ("Vol. %s" % r["volume"] if r["volume"].isdigit() else r["volume"]))
    head = (au + ". " if au else "") + title + "[" + mark + "]"
    pg = r["pages"]
    out = ""
    if t == "journal":
        vi = (r["volume"] or "") + ("(%s)" % r["issue"] if r["issue"] else "")
        out = "%s. %s%s%s" % (head, r["container"], comma + r["year"] if r["year"] else "", (comma + vi if vi else "") + (colon + pg if pg else "")) if True else ""
        yv = (r["year"] or "") + ((comma + vi) if r["volume"] else (("(%s)" % r["issue"]) if r["issue"] else ""))
        out = head + ". " + r["container"] + (comma + yv if yv else "") + (colon + pg if pg else "") + "."
    elif t in ("book", "report", "standard"):
        ed = (" " + (r["edition"] if re.search(r"\D", r["edition"] or "") else ("%s ed" % ordinal(r["edition"]) if not zh else "第%s版" % r["edition"]))) if r["edition"] and r["edition"] not in ("1", "1st", "first") else ""
        pub = (r["place"] + colon if r["place"] else "") + (r["publisher"] or "")
        tr = (" " + gb_people(r["translators"], fw, zh) + (", 译." if not (fw and zh) else "，译.")) if r["translators"] else ""
        out = head + "." + tr + (ed.rstrip(".") + "." if ed else "") + (" " + pub if pub else "") + (comma + r["year"] if r["year"] else "") + (colon + pg if pg else "") + "."
    elif t == "chapter":
        pub = (r["place"] + colon if r["place"] else "") + (r["publisher"] or "")
        ca = (gb_people(r["container_authors"] or r["editors"], fw, zh) + ". ") if (r["container_authors"] or r["editors"]) else ""
        out = head.replace("[M]", "[M]") + "//" + ca + (r["container"] or "") + "." + (" " + pub if pub else "") + (comma + r["year"] if r["year"] else "") + (colon + pg if pg else "") + "."
    elif t == "conference":
        pub = (r["place"] + colon if r["place"] else "") + (r["publisher"] or "")
        ca = (gb_people(r["container_authors"] or r["editors"], fw, zh) + ". ") if (r["container_authors"] or r["editors"]) else ""
        out = head + "//" + ca + (r["container"] or "") + "." + (" " + pub if pub else "") + (comma + r["year"] if r["year"] else "") + (colon + pg if pg else "") + "."
    elif t == "thesis":
        pub = (r["place"] + colon if r["place"] else "") + (r["publisher"] or "")
        out = head + "." + (" " + pub if pub else "") + (comma + r["year"] if r["year"] else "") + (colon + pg if pg else "") + "."
    elif t == "patent":
        out = head.replace("[P", ((colon.strip() + " " + r["number"]) if r["number"] else "") + "[P", 1) + "." + (" " + (r["date"] or r["year"]) if (r["date"] or r["year"]) else "") + "."
    elif t == "newspaper":
        out = head + "." + (" " + r["container"] if r["container"] else "") + ((comma + (r["date"] or r["year"])) if (r["date"] or r["year"]) else "") + (("(%s)" % pg) if pg else "") + "."
    elif t == "web":
        out = head + "." + ((" (%s)" % (r["date"] or r["year"])) if (r["date"] or r["year"]) else "") + (("[%s]" % r["accessed"]) if r["accessed"] else "") + "."
    elif t == "preprint":
        out = head + "." + (" arXiv:%s" % r["arxiv"] if r["arxiv"] else "") + (comma + r["year"] if r["year"] else "") + "."
    else:
        out = head + "." + (" " + r["container"] if r["container"] else "") + (comma + r["year"] if r["year"] else "") + (colon + pg if pg else "") + "."
    if r["accessed"] and t != "web":
        out = out.rstrip(".") + "[%s]." % r["accessed"]
    if r["url"]:
        out += " " + r["url"] + "."
    if r["doi"]:
        out += " DOI:" + r["doi"] + "."
    return re.sub(r"\s+", " ", out).replace("..", ".").replace(" .", ".").strip()


def ordinal(n):
    try:
        n = int(n)
    except (TypeError, ValueError):
        return str(n)
    return "%d%s" % (n, "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th"))


# ------------------------------------------------------------------------------------------------ APA 7
def apa_name(a):
    if a.get("literal"):
        return a["literal"]
    if a.get("zh"):
        return a["family"] + a["given"]
    g = initials(a["given"], dots=True, space=True)
    return ("%s, %s" % (a["family"], g)) if g else a["family"]


def apa_authors(au, role=""):
    names = [apa_name(a) for a in au]
    suffix = (" (Ed.)" if len(names) == 1 else " (Eds.)") if role == "editor" else ""
    if not names:
        return ""
    if len(names) == 1:
        return names[0] + suffix
    if len(names) <= 20:
        return ", ".join(names[:-1]) + (", & " if len(names) > 2 else ", & ") + names[-1] + suffix
    return ", ".join(names[:19]) + ", . . . " + names[-1] + suffix


def format_apa(r, italic=True):
    au = apa_authors(r["authors"], r.get("authors_role", ""))
    y = "(%s)" % (r["year"] or "n.d.")
    head = ((ensure_dot(au) + " ") if au else "") + y + "."
    t = r["type"]
    title = r["title"]
    pg = r["pages"].replace("-", "–")
    link = ("https://doi.org/" + r["doi"]) if r["doi"] else r["url"]
    if t == "journal":
        vi = (plain_i(r["volume"], italic) if r["volume"] else "") + ("(%s)" % r["issue"] if r["issue"] else "")
        body = "%s %s %s%s%s." % (head, ensure_dot(title), plain_i(r["container"], italic), (", " + vi) if vi else "", (", " + pg) if pg else "")
    elif t in ("book", "report", "standard"):
        ed = " (%s ed.)" % ordinal(r["edition"]) if r["edition"] and r["edition"] not in ("1", "1st") else ""
        body = "%s %s%s. %s" % (head, plain_i(title, italic), ed, ensure_dot(r["publisher"]) if r["publisher"] else "")
    elif t == "chapter":
        body = "%s %s In %s%s. %s" % (head, ensure_dot(title), plain_i(r["container"], italic), (" (pp. %s)" % pg) if pg else "", ensure_dot(r["publisher"]) if r["publisher"] else "")
    elif t == "conference":
        body = "%s %s In %s%s. %s" % (head, ensure_dot(title), plain_i(r["container"], italic), (" (pp. %s)" % pg) if pg else "", ensure_dot(r["publisher"]) if r["publisher"] else "")
    elif t == "thesis":
        body = "%s %s [%s]. %s" % (head, plain_i(title, italic), "Doctoral dissertation" if "PhD" in (r["note"] or "") else "Master's thesis", ensure_dot(r["publisher"]) if r["publisher"] else "")
    elif t == "preprint":
        body = "%s %s %s" % (head, plain_i(title, italic) + ".", ("arXiv. " + link if r["arxiv"] else ensure_dot(r["container"] or "Preprint")))
        link = "" if r["arxiv"] else link
        if r["arxiv"]:
            body = "%s %s arXiv. https://arxiv.org/abs/%s" % (head, plain_i(title, italic) + ".", r["arxiv"])
    else:
        body = "%s %s %s" % (head, plain_i(title, italic) + ".", ensure_dot(r["container"] or r["publisher"] or ""))
    if link and not (t == "preprint" and r["arxiv"]):
        body = body.rstrip() + " " + link
    return re.sub(r"\s+", " ", body).replace("..", ".").replace(" .", ".").strip()


# ------------------------------------------------------------------------------------------------ IEEE
def ieee_name(a):
    if a.get("literal"):
        return a["literal"]
    if a.get("zh"):
        return a["family"] + a["given"]
    g = initials(a["given"], dots=True, space=True)
    return ("%s %s" % (g, a["family"])).strip()


def format_ieee(r, italic=True):
    names = [ieee_name(a) for a in r["authors"]]
    if len(names) > 6:
        au = names[0] + " et al."
    elif len(names) > 2:
        au = ", ".join(names[:-1]) + ", and " + names[-1]
    else:
        au = " and ".join(names)
    if r.get("authors_role") == "editor" and au:
        au += ", Ed." if len(names) == 1 else ", Eds."
    t = r["type"]
    pg = r["pages"].replace("-", "–")
    pp = (("pp. " if "–" in pg else "p. ") + pg) if pg else ""
    year = r["year"]
    acc = ""
    ma = re.match(r"(\d{4})\D+(\d{1,2})\D+(\d{1,2})", r.get("accessed") or "")
    if ma and 1 <= int(ma.group(2)) <= 12:
        acc = "Accessed: %s %d, %s." % (["Jan.", "Feb.", "Mar.", "Apr.", "May", "Jun.", "Jul.", "Aug.", "Sep.", "Oct.", "Nov.", "Dec."][int(ma.group(2)) - 1], int(ma.group(3)), ma.group(1))
    online = ("[Online]. Available: " + r["url"]) if r["url"] else ""
    if r["doi"]:
        tail_doi = ", doi: " + r["doi"]
    elif online:
        tail_doi = ((", " if t in ("journal", "conference") else ". ") + acc + " " if acc else (", " if t in ("journal", "conference") else ". ")) + online
    else:
        tail_doi = ""
    if t == "journal":
        parts = [plain_i(r["container"], italic)] + (["vol. " + r["volume"]] if r["volume"] else []) + (["no. " + r["issue"]] if r["issue"] else []) + ([pp] if pp else []) + ([year] if year else [])
        out = '%s, "%s," %s%s.' % (au, r["title"], ", ".join(parts), tail_doi)
    elif t == "conference":
        parts = ["in " + plain_i(r["container"], italic)] + ([r["place"]] if r["place"] else []) + ([year] if year else []) + ([pp] if pp else [])
        out = '%s, "%s," %s%s.' % (au, r["title"], ", ".join(parts), tail_doi)
    elif t == "chapter":
        parts = ["in " + plain_i(r["container"], italic)] + ([r["place"] + ": " + r["publisher"]] if r["place"] and r["publisher"] else ([r["publisher"]] if r["publisher"] else [])) + ([year] if year else []) + ([pp] if pp else [])
        out = '%s, "%s," %s%s.' % (au, r["title"], ", ".join(parts), tail_doi)
    elif t in ("book", "report", "standard"):
        ed = ", %s ed." % ordinal(r["edition"]) if r["edition"] and r["edition"] not in ("1", "1st") else ""
        pub = (r["place"] + ": " if r["place"] else "") + (r["publisher"] or "")
        out = "%s, %s%s%s%s%s." % (au, plain_i(r["title"], italic), ed, (". " + pub) if pub else "", (", " + year) if year else "", tail_doi)
    elif t == "thesis":
        out = '%s, "%s," %s, %s, %s.' % (au, r["title"], "Ph.D. dissertation" if "PhD" in (r["note"] or "") else "M.S. thesis", r["publisher"] or "", year)
    elif t == "preprint":
        out = '%s, "%s," arXiv:%s, %s.' % (au, r["title"], r["arxiv"], year) if r["arxiv"] else '%s, "%s," %s, %s%s.' % (au, r["title"], r["container"] or "preprint", year, tail_doi)
    else:
        out = '%s, "%s," %s%s%s.' % (au, r["title"], r["container"] or r["publisher"] or "", (", " + year) if year else "", tail_doi)
    out = re.sub(r"\s+", " ", out).replace(" ,", ",").replace(",.", ".").replace(" .", ".").replace(",,", ",")
    return out.lstrip(", ")


# ------------------------------------------------------------------------------------------------ Vancouver
def format_vancouver(r, italic=False):
    names = []
    for a in r["authors"][:6]:
        names.append(a["literal"] if a.get("literal") else (a["family"] + a["given"] if a.get("zh") else ("%s %s" % (a["family"], initials(a["given"], dots=False, space=False)) if a["given"] else a["family"])))
    au = ", ".join(names) + (", et al" if len(r["authors"]) > 6 else "")
    t = r["type"]
    if t == "journal":
        vi = (r["volume"] or "") + ("(%s)" % r["issue"] if r["issue"] else "")
        out = "%s. %s. %s. %s;%s:%s." % (au, r["title"], r["container"], r["year"], vi, r["pages"]) if r["year"] else "%s. %s. %s." % (au, r["title"], r["container"])
        out = out.replace(";:", ";").replace(":.", ".").replace(";.", ".")
    elif t in ("book", "report", "standard"):
        out = "%s. %s. %s%s: %s; %s." % (au, r["title"], (r["edition"] + " ed. ") if r["edition"] else "", r["place"], r["publisher"], r["year"])
    else:
        out = "%s. %s. %s. %s." % (au, r["title"], r["container"] or r["publisher"], r["year"])
    if r["doi"]:
        out += " doi:" + r["doi"]
    return re.sub(r"\s+", " ", out).replace(" .", ".").replace("..", ".").replace(": ;", ";").strip()


def format_entry(r, style, **kw):
    style = style.lower()
    if style in ("gbt7714", "gb/t7714", "gbt", "gb"):
        return format_gbt(r, fw=kw.get("punct") == "fullwidth", italic=False)
    if style in ("apa7", "apa"):
        return format_apa(r, italic=kw.get("italic", True))
    if style == "ieee":
        return format_ieee(r, italic=kw.get("italic", True))
    if style in ("vancouver", "nlm"):
        return format_vancouver(r)
    raise SystemExit("unknown style %s (gbt7714, apa7, ieee, vancouver)" % style)


# ------------------------------------------------------------------------------------------------ exports
def to_bibtex(recs):
    out = []
    for r in recs:
        typ = {"journal": "article", "book": "book", "chapter": "incollection", "conference": "inproceedings", "thesis": "phdthesis" if "PhD" in (r["note"] or "") else "mastersthesis", "report": "techreport", "standard": "misc", "patent": "misc", "web": "misc", "preprint": "misc", "other": "misc"}[r["type"]]
        au = " and ".join(a["literal"] if a.get("literal") else ("%s, %s" % (a["family"], a["given"]) if a["given"] else a["family"]) for a in r["authors"])
        f = [("author", au), ("title", "{%s}" % r["title"] if r["title"] else ""), ("journal" if r["type"] == "journal" else "booktitle", r["container"]), ("year", r["year"]), ("volume", r["volume"]), ("number", r["issue"]), ("pages", r["pages"].replace("-", "--")),
             ("publisher", r["publisher"]), ("address", r["place"]), ("edition", r["edition"]), ("doi", r["doi"]), ("url", r["url"]), ("isbn", r["isbn"]), ("issn", r["issn"]), ("eprint", r["arxiv"]), ("archiveprefix", "arXiv" if r["arxiv"] else ""), ("language", {"zh": "chinese", "en": "english"}.get(r["language"], ""))]
        key = re.sub(r"[^\w:-]", "", r["id"]) or "ref"
        out.append("@%s{%s,\n%s\n}" % (typ, key, ",\n".join("  %s = {%s}" % (k, v) for k, v in f if v)))
    return "\n\n".join(out) + "\n"


def to_ris(recs):
    out = []
    for r in recs:
        ty = {"journal": "JOUR", "book": "BOOK", "chapter": "CHAP", "conference": "CONF", "thesis": "THES", "report": "RPRT", "standard": "STAND", "patent": "PAT", "web": "ELEC", "preprint": "UNPB", "other": "GEN"}[r["type"]]
        lines = ["TY  - " + ty] + ["AU  - " + (a["literal"] if a.get("literal") else ("%s, %s" % (a["family"], a["given"]) if a["given"] else a["family"])) for a in r["authors"]]
        sp, _, ep = r["pages"].partition("-")
        for tag, v in (("TI", r["title"]), ("JO" if r["type"] == "journal" else "T2", r["container"]), ("PY", r["year"]), ("VL", r["volume"]), ("IS", r["issue"]), ("SP", sp), ("EP", ep), ("PB", r["publisher"]), ("CY", r["place"]), ("DO", r["doi"]), ("UR", r["url"]), ("SN", r["isbn"] or r["issn"]), ("AB", r["abstract"])):
            if v:
                lines.append("%s  - %s" % (tag, v))
        lines += ["KW  - " + k for k in r["keywords"]] + ["ID  - " + r["id"], "ER  - "]
        out.append("\n".join(lines))
    return "\n\n".join(out) + "\n"
