#!/usr/bin/env python3
"""make_examples.py - regenerate submission/examples/*/out and run.txt from the real tool (nothing typed by hand).
landslide/: the library is 9 real public arXiv records (metadata CC0); the own paper (LiteSlide) and everything written about it are INVENTED. zh/: everything is invented."""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SUB = os.path.join(ROOT, "submission") if os.path.isdir(os.path.join(ROOT, "submission")) else ROOT
EX = os.path.join(SUB, "examples")
IW = os.path.join(SUB, "scripts", "iw.py")
KEEP = {"landslide": ("intro.md", "intro.tex", "references.ieee.txt", "evidence_table.csv", "traceability.md", "review_checklist.md", "result.json", "brief.md"),
        "zh": ("intro.md", "references.gbt7714.txt", "evidence_table.csv", "traceability.md", "review_checklist.md")}


def scrub(text, *paths):
    for p in sorted(set(x for x in paths if x), key=len, reverse=True):
        text = text.replace(p, "<dir>")
    text = re.sub(r"/(?:Users|home|var/folders|private)/[^\s\"',)]*", "<dir>", text)
    return re.sub(r"<dir>/tmp\w+", "<work>", text)


def sh(cwd, args, log, cut=None):
    r = subprocess.run([sys.executable, IW] + args, capture_output=True, text=True, cwd=cwd)
    out = r.stdout + r.stderr
    if cut:
        lines = out.splitlines()
        out = "\n".join(lines[:cut] + (["... (%d more lines; the full brief is in out/brief.md)" % (len(lines) - cut)] if len(lines) > cut else []))
    log.write(scrub("$ iw.py " + " ".join(args) + "\n" + out + "\n\n", EX, tempfile.gettempdir()))
    return r


def tidy_out(out, name):
    for f in os.listdir(out):
        p = os.path.join(out, f)
        if f not in KEEP[name]:
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)


def main():
    # ---- landslide: first draft (defects) -> check -> final draft -> build
    d = os.path.join(EX, "landslide")
    out = os.path.join(d, "out")
    shutil.rmtree(out, ignore_errors=True)
    work = tempfile.mkdtemp()
    log = open(os.path.join(tempfile.gettempdir(), "run_ls.txt"), "w", encoding="utf-8")
    sh(d, ["run", "--own", "own.md", "--lib", "library.bib", "--out", "out", "--work", work], log, cut=40)
    sh(d, ["ingest", work, "decisions.txt"], log)
    sh(d, ["check", work, "draft_v1.md"], log)
    sh(d, ["check", work, "draft.md", "--all"], log)
    sh(d, ["build", work, "draft.md", "--out", "out"], log)
    log.close()
    tidy_out(out, "landslide")
    shutil.move(os.path.join(tempfile.gettempdir(), "run_ls.txt"), os.path.join(d, "run.txt"))
    shutil.rmtree(work, ignore_errors=True)
    # ---- zh
    d = os.path.join(EX, "zh")
    out = os.path.join(d, "out")
    shutil.rmtree(out, ignore_errors=True)
    work = tempfile.mkdtemp()
    log = open(os.path.join(tempfile.gettempdir(), "run_zh.txt"), "w", encoding="utf-8")
    sh(d, ["run", "--case", "case.json", "--out", "out", "--work", work], log, cut=30)
    sh(d, ["ingest", work, "decisions.txt"], log)
    sh(d, ["check", work, "draft.md"], log)
    sh(d, ["build", work, "draft.md", "--out", "out", "--style", "gbt7714"], log)
    log.close()
    tidy_out(out, "zh")
    shutil.move(os.path.join(tempfile.gettempdir(), "run_zh.txt"), os.path.join(d, "run.txt"))
    shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    main()
