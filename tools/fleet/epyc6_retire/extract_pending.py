#!/usr/bin/env python3
"""EPYC6-RETIRE: candidate paths on ot-epyc6 that open pending_results / RELEASE_TREE / lane-file lines still reference.
Prints JSON list of {path, src, line_no, lane, line} (raw candidate, before existence check on the host)."""
import glob, json, os, re, sys
T = "/home/ubuntu/claude-takeover-20261007"
PAT = re.compile(r"(/srv/opentallas-scratch2?/(?:claude|codex)/[^\s|,;:)\'\"`<>\]\[]+)")
EP8 = re.compile(r"epyc6|EPYC6|\bep6\b")
out = []
# EPYC6: also lane files (lanes/*.md): a lane line naming an ot-epyc6 path is kept like a pending line (EPYC8 procedure, reused 10-21)
LANE_FILES = sorted(os.path.relpath(p, T) for p in glob.glob(f"{T}/lanes/*.md") if "EPYC6-RETIRE" not in p)
for fn in ["pending_results.txt", "RELEASE_TREE.md"] + LANE_FILES:
    try:
        lines = open(f"{T}/{fn}", errors="replace").read().splitlines()
    except OSError:
        continue
    for i, l in enumerate(lines, 1):
        s = l.strip()
        if not EP8.search(s):
            continue
        if fn == "pending_results.txt" and re.match(r"^(DONE|\[?DONE|COLLECTED|SUPERSEDED|ARCHIVED-EPYC6|EPYC6-RETIRE)", s):
            continue
        if "EPYC6-RETIRE copy" in s:
            continue
        lane = s.rsplit("|", 1)[-1].strip()[:40] if "|" in s else ""
        # expand one-level brace groups (".../dv2f21g5r3s{1,2,3}") into the individual paths
        while True:
            mb = re.search(r"\{([^{}]*,[^{}]*)\}", s)
            if not mb:
                break
            pre, post = s[:mb.start()], s[mb.end():]
            tok0 = re.search(r"\S*$", pre).group(0)
            tok1 = re.match(r"\S*", post).group(0)
            exp = " ".join(tok0 + alt + tok1 for alt in mb.group(1).split(","))
            s = pre[:len(pre) - len(tok0)] + exp + post[len(tok1):]
        for m in PAT.finditer(s):
            p = m.group(1)
            p = re.split(r"[{*<$]", p)[0].rstrip("/.")
            if p.count("/") < 4:
                continue
            out.append(dict(path=p, src=fn, line_no=i, lane=lane, line=s[:300]))
json.dump(out, sys.stdout, indent=0)
