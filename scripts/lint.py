#!/usr/bin/env python3
"""lint.py - reading a drafted introduction / related work, and the lexicons its checks use.

A draft is Markdown: headings, paragraphs, citations as pandoc keys `[@smith2020; @lee2019]` (or \\cite{}), optional tags that cost nothing in the final text:
  <!--part:background|related|gap|contribution|organization-->   first thing in a paragraph: which part of the introduction it is
  <!--group:G1-->   in a related-work paragraph: which group of the ledger it presents
  <!--gap:G1-->     right after the sentence that states ledger gap G1
  <!--contrib:C1--> right after the sentence that states ledger contribution C1
`parse_draft` returns parts -> paragraphs -> sentences with their keys and tags; the roles come from the tags, else from the headings, else from cues.
"""
from __future__ import annotations

import re

import nlib

TAG = re.compile(r"<!--\s*(part|group|gap|contrib)\s*:\s*([\w\-./ ]+?)\s*-->")
PANDOC = re.compile(r"\[((?:[^\[\]@;]*?)-?@[\w:.#$%&\-+?<>~/]+(?:[^\[\]@;]*)(?:\s*;\s*[^\[\]@;]*?-?@[\w:.#$%&\-+?<>~/]+[^\[\]@;]*)*)\]")
LATEXC = re.compile(r"\\(?:cite|citep|citet|parencite|textcite|autocite)[a-zA-Z]*\*?(?:\[[^\]]*\])*\{([^}]*)\}")
KEYRE = re.compile(r"-?@([\w:.#$%&\-+?<>~/]+)")

# ------------------------------------------------------------------------------------------------ lexicons
FILLER_EN = [
    r"in recent years,? .{0,60}(?:has|have) (?:attracted|received|drawn|gained) (?:increasing|growing|considerable|great|much|widespread|significant)? ?(?:attention|interest)",
    r"(?:has|have) (?:attracted|received|drawn|gained) (?:increasing|growing|considerable|great|much|widespread|significant) (?:attention|interest)",
    r"with the (?:rapid )?(?:development|advance|advances|progress|rise|growth) of",
    r"plays? (?:a |an )?(?:very |increasingly |more and more )?(?:important|crucial|vital|key|significant|essential|pivotal) (?:role|part)",
    r"is (?:of )?(?:great|vital|crucial|critical|paramount|significant) (?:importance|significance)",
    r"(?:has become|have become|is becoming|are becoming) (?:a )?(?:hot|popular|prevalent|ubiquitous|important|critical|key) (?:topic|issue|problem|research)",
    r"(?:more and more|an increasing number of|a growing number of) (?:researchers|scholars|studies|works)",
    r"in the era of big data", r"it is well known that", r"it is widely (?:known|accepted|recognized|recognised)",
    r"(?:a )?wide (?:range|variety) of (?:applications|fields|areas)",
    r"has been (?:extensively|widely|intensively) (?:studied|researched|investigated|used|applied)",
]
FILLER_ZH = [
    r"近年来.{0,30}(?:受到|引起|得到).{0,6}(?:广泛|越来越多|高度|普遍)?.{0,4}(?:关注|重视)", r"随着.{1,30}(?:的)?(?:快速|飞速|不断|迅速)?(?:发展|进步|普及|提高)", r"(?:起着|发挥着|具有)(?:十分|非常|越来越|极其)?(?:重要|关键)的(?:作用|意义)",
    r"(?:已成为|成为了?)(?:当前|目前)?(?:研究)?(?:热点|焦点|热门)", r"(?:越来越多|众多|大量)的(?:学者|研究者|研究)", r"众所周知", r"(?:被)?广泛(?:应用|使用|研究)于", r"具有(?:重要|广阔|重大)的(?:理论|研究|应用|现实)?(?:意义|价值|前景)",
]
IMPORTANCE_EN = re.compile(r"\b(important|importance|significant|crucial|vital|essential|widely used|popular|increasingly|growing|attention|interest|hot topic|key role)\b", re.I)
IMPORTANCE_ZH = re.compile(r"重要|关键|意义|价值|关注|热点|广泛|越来越|日益")
COMPARE_EN = re.compile(r"\b(whereas|while|in contrast|by contrast|on the other hand|compared (?:with|to)|unlike|both|similarly|likewise|differ(?:s|ent)?|trade-?off|in comparison|rather than|instead of|however|but|"
                        r"the former|the latter|at the cost of|more (?:accurate|efficient|robust) than|whereas|share|common|except)\b", re.I)
COMPARE_ZH = re.compile(r"相比|相较|而|不同于|与之相反|相反|另一方面|前者|后者|共同|均|都|但是|然而|则|代价|权衡|优于|劣于")
ABSENCE_EN = re.compile(r"\b(no (?:study|work|research|paper|method|approach|one)|none of (?:the|these)|nobody|never been|has not been|have not been|hasn't been|haven't been|to the best of our knowledge|no existing|not (?:yet )?been (?:studied|explored|investigated|addressed)|"
                        r"remains? (?:unexplored|unaddressed|open)|first (?:to|study|work))\b", re.I)
ABSENCE_ZH = re.compile(r"尚无|没有(?:任何)?(?:研究|工作|方法)|尚未(?:被)?(?:研究|探索|解决)|鲜有|未见|首次|据我们所知|空白")
JUDGE_EN = re.compile(r"\b(we (?:argue|believe|contend|posit|hypothesi[sz]e|conjecture|think)|in our (?:view|opinion)|our (?:judg(?:e)?ment|assessment) is|we (?:judge|consider)|it seems to us|arguably)\b", re.I)
JUDGE_ZH = re.compile(r"我们认为|本文认为|笔者认为|据我们判断|我们判断|在我们看来|本文判断")
FIRST_EN = re.compile(r"\b(we|our|this (?:paper|work|study|article|thesis)|in this (?:paper|work|study))\b", re.I)
FIRST_ZH = re.compile(r"本文|我们|本研究|笔者|本工作")
GAP_EN = re.compile(r"\b(however|nevertheless|yet|but|remain(?:s)? (?:unclear|open|challenging|limited|unresolved)|(?:is|are) (?:still )?(?:limited|lacking|missing|insufficient)|lack(?:s)?|fail(?:s)? to|"
                    r"little (?:is known|attention)|gap|unresolved|unaddressed|open (?:question|problem))\b", re.I)
GAP_ZH = re.compile(r"然而|但是|尚未|仍然|不足|缺乏|局限|空白|未能|有待|难以|仍存在")
CONTRIB_EN = re.compile(r"\b(our (?:main |key |major )?contributions?|the (?:main |key )?contributions? (?:of this|are)|we (?:propose|introduce|present|develop|show|demonstrate|release|build|provide|contribute)|this (?:paper|work) (?:proposes|presents|introduces))\b", re.I)
CONTRIB_ZH = re.compile(r"本文的(?:主要)?(?:贡献|创新)|主要贡献|本文(?:提出|设计|构建|给出|提供)|我们(?:提出|设计|构建|给出|提供|证明|发现)")
ORG_EN = re.compile(r"\b(the rest of (?:this|the) paper|paper is organi[sz]ed|section \d+ (?:reviews|describes|presents)|organi[sz]ation of)\b", re.I)
ORG_ZH = re.compile(r"论文(?:的)?(?:其余|结构|组织)|本文(?:其余|余下)|第[二三四五六七八九\d]节")
ROLE_HEAD = [
    ("related", re.compile(r"related work|literature|prior work|previous work|state of the art|相关工作|研究现状|文献综述|国内外")),
    ("gap", re.compile(r"research gap|gap|limitations? of (?:existing|prior)|problem statement|motivation|研究空白|问题提出|研究不足|研究动机")),
    ("contribution", re.compile(r"contribution|our (?:work|approach)|this (?:paper|work)|贡献|本文工作|研究内容")),
    ("organization", re.compile(r"organi[sz]ation|outline|paper structure|论文结构|章节安排")),
    ("background", re.compile(r"background|introduction|overview|context|研究背景|背景|引言|绪论")),
]
OVERCLAIM_C = re.compile(r"\b(state-of-the-art|sota|first|novel|best|superior|outperform(?:s|ed)?|significantly|substantially|breakthrough|unprecedented|optimal|robust|universal|generali[sz]es? (?:to|across)|all|any|every|always|never)\b", re.I)
OVERCLAIM_ZH = re.compile(r"首次|首个|最先进|最优|最好|显著|大幅|突破|通用|普适|完全|所有|任何|均优于")
STRONG_SRC = re.compile(r"\b(prove[sd]?|demonstrat(?:e|es|ed|ing)|confirm(?:s|ed)?|establish(?:es|ed)?|always|never|entirely|completely|clearly|conclusively|dramatically|substantially|eliminate[sd]?|solve[sd]?|guarantee[sd]?|"
                        r"state-of-the-art|sota|outperform(?:s|ed)?|superior|significantly|best|optimal)\b", re.I)


def is_zh(text):
    return nlib.cjk_ratio(text) > 0.3


def filler_hits(sentence):
    pats = FILLER_ZH if is_zh(sentence) else FILLER_EN
    return [p for p in pats if re.search(p, sentence, re.I)]


# ------------------------------------------------------------------------------------------------ the draft
def keys_in(text):
    keys = []
    for m in PANDOC.finditer(text):
        keys += [k.rstrip(".,;:") for k in KEYRE.findall(m.group(1))]
    for m in LATEXC.finditer(text):
        keys += [k.strip() for k in m.group(1).split(",") if k.strip()]
    return list(dict.fromkeys(keys))


def strip_markup(text):
    t = PANDOC.sub("", text)
    t = LATEXC.sub("", t)
    t = TAG.sub("", t)
    return re.sub(r"\s+([,.;:。，；：])", r"\1", re.sub(r"\s+", " ", t)).strip()


def role_of_heading(title):
    """the part a heading names; a heading naming several parts ('Research gap and contributions') decides nothing: the paragraphs' own cues do"""
    hits = [role for role, rx in ROLE_HEAD if rx.search(title) and role != "background"]
    if len(hits) > 1:
        return None
    if hits:
        return hits[0]
    return "background" if ROLE_HEAD[-1][1].search(title) else None


def split_with_tags(par):
    """sentences of a paragraph; a tag that follows a sentence's final stop belongs to that sentence; a gap / contribution tag ends its statement even inside a longer sentence"""
    raw = nlib.split_sentences(par)
    out = []
    for s in raw:
        if out and re.match(r"^\s*(?:<!--.*?-->\s*)+$", s):
            out[-1] += " " + s
            continue
        parts, pos = [], 0
        for m in TAG.finditer(s):
            if m.group(1) in ("gap", "contrib"):
                parts.append(s[pos:m.end()])
                pos = m.end()
        rest = s[pos:]
        if parts:
            if re.sub(r"[\s。.；;，,]", "", rest):
                parts.append(rest)
            else:
                parts[-1] += rest
        else:
            parts = [s]
        out += parts
    return out


def parse_draft(text):
    """-> {"parts": [{"title","role","paragraphs": [...]}], "paragraphs": [...], "sentences": [...]} ; ids P1.. / D001..."""
    parts, cur = [], {"title": "", "role": None, "paragraphs": []}
    parts.append(cur)
    pid, sid = 0, 0
    allp, alls = [], []
    for block in re.split(r"\n\s*\n", text.strip()):
        b = block.strip()
        if not b:
            continue
        mh = re.match(r"^(#{1,6})\s+(.+?)\s*#*$", b)
        if mh and "\n" not in b:
            title = mh.group(2).strip()
            cur = {"title": title, "role": role_of_heading(title), "paragraphs": [], "level": len(mh.group(1))}
            parts.append(cur)
            continue
        if b.startswith(("```", "|", "---")) or re.match(r"^\s*(?:Keywords?|关键词)\s*[:：]", b):
            continue
        pid += 1
        flat = re.sub(r"\s*\n\s*", " ", b)
        ptags = {}
        for m in TAG.finditer(flat):
            ptags.setdefault(m.group(1), []).append(m.group(2).strip())
        par = {"id": "P%d" % pid, "text": flat, "part_tag": (ptags.get("part") or [None])[0], "group": (ptags.get("group") or [None])[0], "section": cur["title"], "sentences": []}
        for s in split_with_tags(flat):
            sid += 1
            tags = {k: v for k, v in ((m.group(1), m.group(2).strip()) for m in TAG.finditer(s)) if k in ("gap", "contrib")}
            sen = {"id": "D%03d" % sid, "par": par["id"], "text": s, "plain": strip_markup(s), "keys": keys_in(s), "gap": tags.get("gap"), "contrib": tags.get("contrib")}
            par["sentences"].append(sen)
            alls.append(sen)
        cur["paragraphs"].append(par)
        allp.append(par)
    parts = [p for p in parts if p["paragraphs"]]
    assign_roles(parts)
    return {"parts": parts, "paragraphs": allp, "sentences": alls}


def para_cues(par):
    z = is_zh(par["text"])
    t = " ".join(s["plain"] for s in par["sentences"])
    n = max(1, len(par["sentences"]))
    return {
        "gap": len(GAP_ZH.findall(t) if z else GAP_EN.findall(t)) / n,
        "contrib": len(CONTRIB_ZH.findall(t) if z else CONTRIB_EN.findall(t)) / n,
        "org": bool((ORG_ZH if z else ORG_EN).search(t)),
        "cites": sum(len(s["keys"]) for s in par["sentences"]),
        "sents": n,
    }


def assign_roles(parts):
    """paragraph role: tag > heading > cues > position (first paragraph background)"""
    first = True
    for part in parts:
        for par in part["paragraphs"]:
            cues = para_cues(par)
            par["cues"] = cues
            if par["part_tag"]:
                role = par["part_tag"].lower()
            elif part["role"]:
                role = part["role"]
            elif any(s["gap"] for s in par["sentences"]):
                role = "gap"
            elif any(s["contrib"] for s in par["sentences"]) or cues["contrib"] >= 0.3:
                role = "contribution"
            elif cues["org"]:
                role = "organization"
            elif cues["gap"] >= 0.5 and cues["cites"] >= 1:
                role = "gap"
            elif par["group"] or (cues["cites"] >= 3 and not first):
                role = "related"
            else:
                role = "background" if first or not par.get("prev") else "related"
            par["role"] = role
            first = False
    # an unlabelled paragraph that follows related paragraphs and has no cues stays related
    prev = None
    for part in parts:
        for par in part["paragraphs"]:
            if par["role"] == "background" and prev == "related" and not (part["role"] == "background" or par["part_tag"]):
                par["role"] = "related"
            prev = par["role"]
    for part in parts:
        for par in part["paragraphs"]:
            for s in par["sentences"]:
                s["role"] = par["role"]
            if part["role"] is None and part["paragraphs"]:
                pass
    return parts


def sentence_kind(s, role):
    """own / gap / contribution / cited / plain: what a sentence is doing"""
    z = is_zh(s["plain"])
    if s.get("contrib") or (role == "contribution" and (CONTRIB_ZH if z else CONTRIB_EN).search(s["plain"])):
        return "contribution"
    if s.get("gap"):
        return "gap"
    if s["keys"]:
        return "cited"
    if (FIRST_ZH if z else FIRST_EN).search(s["plain"]):
        return "own"
    return "plain"
