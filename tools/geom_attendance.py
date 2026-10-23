#!/usr/bin/env python3
"""GEOM attendance audit (OWNER RULE 2026-10-23: "Do not leave elements no one attended").

Lists every open element on the four release dies (fleet-viz /api/elements rows whose dies include s81, qwen_compute,
qwen_kvsys or hbm and whose category is neither closed* nor superseded) plus every top the coordinator's visual review
marked BAD (COORD_VERDICTS.tsv), with
  last failure      latest failed closure-loop job of the block (status, time), else the fleet-viz latest failure;
  review            none | requested | PASS | FAIL  (lanes/GEOM-REVIEW.md REQ / VERDICT lines + verdict JSONs);
  live              y when a closure-loop job of the block is not terminal, fleet-viz live > 0, or a local ot-run
                    process names one of the element's kits;
  owner             RELEASE_TREE.md line naming the element (or one of its kits), else the newest lane NEXT line,
                    else the fleet-viz owner;
  hours             since the last action (loop job update, fleet-viz latest, lane file touched with the element in its
                    last 60 lines, GEOM-REVIEW REQ/VERDICT);
  UNATTENDED        a failure, no live job, no review in flight (none / FAIL) and no action in < 2 h.
Writes <coord>/ATTENDANCE.md, rewrites the "AWAITING REDESIGN" section of lanes/GEOM-REVIEW.md (COORD BAD tops with no
REQ yet: "AWAITING REDESIGN <element> <owner>") and prints the UNATTENDED lines (for the coordinator's hourly check).
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import glob
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "closure_loop"))
import geom_review_gate as G  # noqa: E402

COORD = Path(os.environ.get("GEOM_REVIEW_COORD", "/home/ubuntu/claude-takeover-20261007"))
LANES = COORD / "lanes"
DIES = ("s81", "qwen_compute", "qwen_kvsys", "hbm")
LIVE_STATES = {"QUEUED", "RUNNING", "READY", "BENCH", "WAITING", "INGESTED", "PENDING", "ECO", "ROUTE", "SUBMITTED",
               "SMOKE_OK"}
TERMINAL = {"CLOSED", "CANCELLED", "REFUSED", "INVALID"}
REQ_RE = re.compile(r"^\s*-?\s*(?:\[[^\]]*\]\s*)?REQ\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)", re.M)
VER_RE = re.compile(r"^\s*-?\s*(?:\[[^\]]*\]\s*)?VERDICT\s+(\S+)\s+(\S+)\s+(PASS-CONDITIONAL|PASS|FAIL)(?![\w-])", re.M)
STALE_H = 2.0
STAMP_RE = re.compile(r"\[(\d\d-\d\d) (\d\d:\d\d)\]")
STEWARDS = (("STEWARD-S81", ("dsdv_", "dsfd_", "ot_s81", "s81", "col_h")), ("STEWARD-QK", ("qfd_", "qkd_", "ot_coll_", "ot_qwen")),
            ("STEWARD-HBM", ("ot_hbm", "hfd_", "ot_hgi", "ot_hfd", "ot_hidx", "hnx_", "hdie", "ot_hdie")))


def steward(e: str, dies: str) -> str:
    for st, pre in STEWARDS:
        if e.startswith(pre):
            return st
    return {"s81": "STEWARD-S81", "qwen_compute": "STEWARD-QK", "qwen_kvsys": "STEWARD-QK", "hbm": "STEWARD-HBM"}.get(
        dies.split(",")[0], "COORD")


def now() -> float:
    return time.time()


def api(url=G.ELEMENTS_URL):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read())["rows"]


def open_on_dies(rows):
    out = {}
    for x in rows:
        dies = {d.get("design") for d in (x.get("dies") or []) if isinstance(d, dict)}
        cat = str(x.get("category") or "")
        if dies & set(DIES) and not cat.startswith("closed") and cat != "superseded":
            out[x["element"]] = x
    return out


def coord_rows(path=G.COORD_VERDICTS):
    """top -> [(row element, verdict, reason)] for every COORD row"""
    out = {}
    try:
        lines = Path(path).read_text().splitlines()[1:]
    except OSError:
        return out
    for ln in lines:
        f = ln.split("\t")
        if len(f) >= 3:
            out.setdefault(f[0].split("__")[0], []).append((f[0], f[2], f[6] if len(f) > 6 else ""))
    return out


def loop_index(state=G.STATE):
    """block -> [job summary] from the closure-loop job states"""
    idx = {}
    for p in glob.glob(str(state / "jobs" / "*.json")):
        try:
            j = json.loads(Path(p).read_text())
        except (OSError, ValueError):
            continue
        s = j.get("spec") or {}
        b = s.get("block")
        if not b:
            continue
        idx.setdefault(b, []).append({"name": j.get("name"), "status": j.get("status"), "t": G._ts(j.get("updated")),
                                      "reason": str(j.get("reason") or "")[:160], "kit": G.spec_kit(s)})
    return idx


def review_state(text: str, verdicts):
    """element -> (state, detail, t): the LAST REQ / VERDICT line of the element in lanes/GEOM-REVIEW.md (file order);
    verdict JSONs only for elements the lane does not mention"""
    st = {}
    for v in sorted(verdicts, key=lambda v: v["at"]):
        if v.get("element"):
            st[v["element"]] = (v["verdict"], f"{v['verdict']} {v.get('kit')}", v["at"])
    mt = G.LANE.stat().st_mtime if G.LANE.exists() else 0.0
    ev = [(m.start(), m.group(1), "requested", f"REQ {m.group(2)} by {m.group(5)}") for m in REQ_RE.finditer(text)]
    ev += [(m.start(), m.group(1), m.group(3), f"{m.group(3)} {m.group(2)}") for m in VER_RE.finditer(text)]
    for pos, e, state, det in sorted(ev):
        # GEOM-REVIEW stamps its VERDICT lines "[MM-DD HH:MM]"; REQ lines carry no reliable time (lane mtime)
        line = text[pos:text.find("\n", pos) if text.find("\n", pos) >= 0 else len(text)]
        m = STAMP_RE.search(line)
        t = mt
        if m:
            try:
                t = dt.datetime.strptime(f"{dt.date.today().year}-{m.group(1)} {m.group(2)}", "%Y-%m-%d %H:%M").timestamp()
            except ValueError:
                pass
        st[e] = (state, det, t)
    return st


def lane_texts():
    out = []
    for p in sorted(glob.glob(str(LANES / "*.md"))):
        if p.endswith("GEOM-REVIEW.md"):
            continue
        try:
            out.append((Path(p).stem, Path(p).stat().st_mtime, Path(p).read_text(errors="replace").splitlines()))
        except OSError:
            continue
    return out


def owner_of(names, tree_lines, lanes, api_owner):
    for ln in tree_lines:
        if any(n in ln for n in names):
            f = [x.strip() for x in ln.split("·")]
            if len(f) >= 2:
                return f"{f[1]} (tree {f[0].split(']')[-1].split()[0] if ']' in f[0] else ''})".strip()
    best = None
    for stem, mt, lines in lanes:
        for ln in lines:
            if "NEXT" in ln and any(n in ln for n in names):
                tag = re.search(r"\[([A-Za-z0-9_.-]+)[ \]]", ln)
                if best is None or mt > best[0]:
                    best = (mt, tag.group(1) if tag else stem)
    if best:
        return f"{best[1]} (lane NEXT)"
    return f"{api_owner} (viz)" if api_owner else "-"


def lane_touch(names, lanes):
    t = 0.0
    for stem, mt, lines in lanes:
        # lines written by GEOM-REVIEW (verdict broadcasts, notices) are not an owner action
        if any(n in ln for ln in lines[-60:] if "GEOM-REVIEW" not in ln for n in names):
            t = max(t, mt)
    return t


def ps_args():
    try:
        return subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return ""


def build(rows, cmap, lidx, verdicts, lane_text, tree_lines, lanes, psout):
    opened = open_on_dies(rows)
    byname = {x["element"]: x for x in rows}
    bad_tops = {t for t, v in cmap.items() if any(r[1] in G.BAD for r in v)}
    elements = sorted(set(opened) | bad_tops)
    rstate = review_state(lane_text, verdicts)
    out = []
    for e in elements:
        row = byname.get(e) or {}
        cat = str(row.get("category") or "")
        if e not in opened and (cat.startswith("closed") or cat == "superseded"):
            continue            # COORD BAD but since closed / superseded: not open work
        jobs = lidx.get(e, [])
        kits = {Path(j["kit"]).name for j in jobs if j.get("kit")}
        kits |= {r[0].split("__", 1)[1] for r in cmap.get(e, []) if "__" in r[0]}
        names = [e] + sorted(kits)
        fails = [j for j in jobs if G.is_fail_state(j["status"] or "")]
        closed_t = max((j["t"] for j in jobs if j["status"] == "CLOSED"), default=0.0)
        lf = max(fails, key=lambda j: j["t"]) if fails else None
        coordbad = [r for r in cmap.get(e, []) if r[1] in G.BAD]
        failure = None
        if lf and lf["t"] > closed_t:
            failure = f"{lf['status']} {dt.datetime.fromtimestamp(lf['t']).strftime('%m-%d %H:%M')} {lf['name']}"
        elif int(row.get("failed") or 0) > 0:
            lat = row.get("latest") or {}
            failure = f"viz failed={row.get('failed')} latest {lat.get('status')} {lat.get('job')}"
        if coordbad:
            failure = (failure + " + " if failure else "") + f"COORD {coordbad[0][1]} {coordbad[0][0]}"
        live_loop = [j for j in jobs if j["status"] in LIVE_STATES or (j["status"] not in TERMINAL and
                                                                      not G.is_fail_state(j["status"] or ""))]
        live_ps = [k for k in kits if k and re.search(rf"(ref_gate_|/){re.escape(k)}(_|-|/|\.)", psout)]
        live = bool(live_loop or int(row.get("live") or 0) > 0 or live_ps)
        livewhat = (live_loop[0]["name"] if live_loop else (f"ot-run {live_ps[0]}" if live_ps else
                                                             ("viz live" if live else "")))
        rs = rstate.get(e, ("none", "", 0.0))
        lat_t = float((row.get("latest") or {}).get("t") or 0)
        last = max([j["t"] for j in jobs] + [lat_t, lane_touch(names, lanes), rs[2] if rs[0] != "none" else 0.0]
                   + ([now()] if live else []))
        hours = (now() - last) / 3600 if last else 999.0
        owner = owner_of(names, tree_lines, lanes, row.get("owner"))
        unatt = bool(failure) and not live and rs[0] in ("none", "FAIL") and hours >= STALE_H
        dies = ",".join(sorted({d.get("design") for d in (row.get("dies") or []) if isinstance(d, dict)})) or "-"
        if owner == "-" or "(viz)" in owner:
            owner = f"{steward(e, dies)} (steward; {owner})"
        out.append(dict(element=e, dies=dies, category=cat or "-", failure=failure or "-", review=rs[0],
                        review_detail=rs[1], live="y" if live else "n", live_what=livewhat, owner=owner,
                        hours=round(hours, 1), unattended=unatt, coord_bad=bool(coordbad), kits=sorted(kits)))
    return out


def awaiting(recs):
    return [r for r in recs if r["coord_bad"] and r["review"] == "none"]


def write_md(recs, path):
    ts = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
    un = [r for r in recs if r["unattended"]]
    L = [f"# ATTENDANCE (tools/geom_attendance.py, {ts})",
         "OWNER 10-23: no element left unattended. UNATTENDED = failure + no live job + no review in flight + no action "
         f"in < {STALE_H:g} h.  Review queue: lanes/GEOM-REVIEW.md.", "",
         f"## UNATTENDED ({len(un)})"]
    L += [f"- UNATTENDED {r['element']} [{r['dies']}] owner {r['owner']} | {r['failure']} | review {r['review']} | "
          f"idle {r['hours']} h" for r in un] or ["- none"]
    aw = awaiting(recs)
    L += ["", f"## AWAITING REDESIGN (COORD BAD, no REQ yet: {len(aw)})"]
    L += [f"- AWAITING REDESIGN {r['element']} {r['owner']}" for r in aw] or ["- none"]
    L += ["", f"## ALL ({len(recs)})", "| element | dies | category | last failure | review | live | owner | h since action |",
          "|---|---|---|---|---|---|---|---|"]
    for r in sorted(recs, key=lambda r: (not r["unattended"], r["review"] != "none", -r["hours"])):
        L.append(f"| {r['element']} | {r['dies']} | {r['category']} | {r['failure']} | {r['review']} {r['review_detail']} | "
                 f"{r['live']} {r['live_what']} | {r['owner']} | {r['hours']} |")
    Path(path).write_text("\n".join(L) + "\n")
    return un, aw


def update_lane(aw, lane=None):
    lane = Path(lane or G.LANE)
    if not lane.exists():
        return
    ts = dt.datetime.now().strftime("%m-%d %H:%M")
    with open(str(lane) + ".lock", "a") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        text = lane.read_text()
        head = "## AWAITING REDESIGN"
        i = text.find(head)
        if i < 0:
            return
        j = text.find("\n## ", i + 1)
        j = len(text) if j < 0 else j
        body = [text[i:].split("\n", 1)[0], f"(regenerated {ts} by tools/geom_attendance.py; a steward's REQ removes the line)"]
        body += [f"- AWAITING REDESIGN {r['element']} {r['owner']}" for r in aw] or ["- none"]
        lane.write_text(text[:i] + "\n".join(body) + "\n" + text[j:])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(COORD / "ATTENDANCE.md"))
    ap.add_argument("--json", help="also write the records as JSON")
    ap.add_argument("--no-lane", action="store_true", help="do not rewrite the AWAITING section of GEOM-REVIEW.md")
    a = ap.parse_args(argv)
    rows = api()
    try:
        tree = (COORD / "RELEASE_TREE.md").read_text().splitlines()
    except OSError:
        tree = []
    try:
        lane_text = G.LANE.read_text()
    except OSError:
        lane_text = ""
    recs = build(rows, coord_rows(), loop_index(), G.load_verdicts(), lane_text, tree, lane_texts(), ps_args())
    un, aw = write_md(recs, a.out)
    if a.json:
        Path(a.json).write_text(json.dumps(recs, indent=1) + "\n")
    if not a.no_lane:
        update_lane(aw)
    for r in un:
        print(f"UNATTENDED {r['element']} [{r['dies']}] owner {r['owner']} | {r['failure']} | review {r['review']} | "
              f"idle {r['hours']} h")
    print(f"# {len(recs)} elements, {len(un)} UNATTENDED, {len(aw)} AWAITING REDESIGN -> {a.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
