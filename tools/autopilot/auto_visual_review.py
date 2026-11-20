#!/usr/bin/env python3
"""auto_visual_review.py: automatic reviewer for WAIT-VISUAL (review-before-route) rows.

OWNER 11-13: visual review improves layouts and never blocks; the only blocking facts are functional.  ROUTE-RELEASE-1300
11-20 (COORD): 55 rows sat in WAIT-VISUAL with no reviewer.  This module reads the exact placed kit (placed_scan / auto_geom /
detailed-place log + report) and decides:

  ACCEPT        placement legal (no cells on macros, no placement failure, no macro overlap) and the worst setup estimate
                is better than SETUP_FLOOR_PS (-300) -> the wave writes an ISSUES-ACCEPT GEOM VERDICT line (exact kit=...)
  SLEW-LIMITED  the worst setup path has a pin slew above SLEW_LIMIT_PS (1000, FABLE-CLOSURE-1315): the WNS is untrustworthy,
                not "can't sign" -> no verdict, listed for CORE-LIB-LIMITS-1330 (regen with e7ebced0c4e)
  SETUP         worst setup <= -300 ps with trusted slews: cannot sign -> no verdict, listed for the die owner
  ILLEGAL       cells on macros / placement failures / macro overlap (functional) -> no verdict, die owner
  NODATA        a needed file is missing or unreadable -> nothing written, retried later

It never writes BAD / ISSUES (those would send the row to WAIT-FORM): a row that does not pass simply stays held and is listed
in lanes/AUTO-REVIEW-HELD.tsv with its reason.  The remote read is a few greps on the kit host, not heavy work.
"""
import json
import re
import subprocess
import time
from pathlib import Path

SETUP_FLOOR_PS = -300.0
SLEW_LIMIT_PS = 1000.0
HELD_TSV = "AUTO-REVIEW-HELD.tsv"

# runs on the kit host: python3 -I - <kit dir> < REMOTE_SCRIPT ; prints one JSON line
REMOTE_SCRIPT = r'''
import sys, json, os, re, glob
kit = sys.argv[1].rstrip("/")
X = kit.rsplit("/gen/", 1)[0]
out = {}
def rd(p):
    try:
        return open(p, errors="replace").read()
    except OSError:
        return None
try:
    j = json.load(open(os.path.join(X, "geom", "auto_geom.json")))
    line = j.get("line", "")
    m = re.search(r"cells_on_macros=(\w+)\(([^)]*)\)", line)
    out["cells_on_macros"] = None if not m else (0 if m.group(1) == "ok" else m.group(2))
    rules = {r.get("rule"): r for r in j.get("rules", [])}
    if m is None and rules:                      # a rule that is not listed was not violated (auto_geom lists failing / warned rules)
        r = rules.get("cells_on_macros")
        out["cells_on_macros"] = 0 if r is None or r.get("status") == "PASS" else r.get("value")
    out["clock_on_macro"] = (re.search(r"clock_on_macro=(\w+)\(([^)]*)\)", line) or [None, None, None])[2]
    m = re.search(r"comb_loops=(\w+)\(([^)]*)\)", line)
    out["comb_loops"] = None if not m else (0 if m.group(1) == "ok" else m.group(2))
    m = re.search(r"grt=(\w+)\(([^)]*)\)", line)
    out["grt"] = None if not m else m.group(2)
except Exception as e:
    out["geom_err"] = str(e)[:80]
try:
    j = json.load(open(os.path.join(X, "geom", "placed_scan.json")))
    gs = j.get("groups", [])
    out["scan"] = dict(over_reach=j.get("groups_over_reach"), need_station=j.get("groups_need_station"),
                       bits_over_cycle=j.get("bits_over_cycle"),
                       max_um=max([g.get("max_um", 0) for g in gs]) if gs else 0)
except Exception as e:
    out["scan_err"] = str(e)[:80]
run = os.path.join(kit, "run")
for key, pat in (("dp", "3_5_place_dp.log"), ("macro", "2_2_floorplan_macro.log")):
    f = glob.glob(os.path.join(run, "logs/asap7/*/base", pat))
    t = rd(f[0]) if f else None
    if t is None:
        out[key] = None
        continue
    out[key] = [l.strip()[:160] for l in t.splitlines()
                if re.search(r"(?<!non)overlap|illegal|unplaced|Total Placement Failures", l, re.I)][:6]
f = glob.glob(os.path.join(run, "reports/asap7/*/base/3_detailed_place.rpt"))
out["rpt"] = rd(f[0]) if f else None
print(json.dumps(out))
'''

_PIN_EDGE = re.compile(r"^\s*(?P<nums>[-\d.\s]+?)\s+[\^v]\s+\S")


def parse_report(text):
    """-> dict(wns, worst_slew, paths) from a 3_detailed_place.rpt.  wns = the 'worst slack max' value; worst_slew = the largest
    pin slew on the lowest-slack path of the 'report_checks -path_delay max' section (None when no path is readable)."""
    if not text:
        return dict(wns=None, worst_slew=None, paths=0)
    wns = None
    m = re.search(r"report_worst_slack[\s=-]*worst slack max\s+(-?[\d.]+)", text)
    if m:
        wns = float(m.group(1))
    else:
        m = re.search(r"report_wns[\s=-]*wns max\s+(-?[\d.]+)", text)
        if m:
            wns = float(m.group(1))
    start = text.find("report_checks -path_delay max\n")
    sect = ""
    if start >= 0:
        end = text.find("\ndetailed place ", start + 10)
        sect = text[start:end if end > 0 else len(text)]
    best = None                          # (slack, max slew)
    paths = 0
    cur = []
    for ln in sect.splitlines() + ["Startpoint: END"]:
        if ln.startswith("Startpoint:"):
            if cur:
                slack = None
                slew = 0.0
                for c in cur:
                    ms = re.search(r"(-?[\d.]+)\s+slack \((?:MET|VIOLATED)\)", c)
                    if ms:
                        slack = float(ms.group(1))
                    mp = _PIN_EDGE.match(c)
                    if mp:
                        nums = mp.group("nums").split()
                        if len(nums) in (3, 5):
                            try:
                                slew = max(slew, float(nums[-3]))
                            except ValueError:
                                pass
                if slack is not None:
                    paths += 1
                    if best is None or slack < best[0]:
                        best = (slack, slew)
            cur = [ln]
        else:
            cur.append(ln)
    return dict(wns=wns, worst_slew=best[1] if best else None, path_slack=best[0] if best else None, paths=paths)


def decide(info):
    """info = remote JSON (rpt text included) -> (CLASS, reason, facts dict)"""
    rep = parse_report(info.get("rpt"))
    facts = dict(wns=rep["wns"], worst_slew=rep["worst_slew"], **(info.get("scan") or {}))
    if info.get("rpt") is None or rep["wns"] is None or info.get("dp") is None or info.get("cells_on_macros") is None:
        return "NODATA", "placed report / auto_geom / place log not readable", facts
    illegal = []
    if info.get("cells_on_macros") not in (0, "0"):
        illegal.append(f"cells_on_macros {info['cells_on_macros']}")
    for l in (info.get("dp") or []) + (info.get("macro") or []):
        if re.search(r"Found 0 overlaps", l):
            continue
        if (re.search(r"Total Placement Failures:\s+[1-9]", l) or re.search(r"Found [1-9]\d* overlaps", l)
                or (re.search(r"(?<!non)overlap|illegal|unplaced", l, re.I) and "OT_" not in l and "Found" not in l)):
            illegal.append(l[:80])
    if illegal:
        return "ILLEGAL", "; ".join(illegal[:3]), facts
    if rep["wns"] > SETUP_FLOOR_PS:
        return "ACCEPT", f"placement legal, post-place setup estimate wns {rep['wns']:.0f} ps", facts
    if rep["worst_slew"] is not None and rep["worst_slew"] > SLEW_LIMIT_PS:
        return ("SLEW-LIMITED",
                f"wns {rep['wns']:.0f} ps but worst-path slew {rep['worst_slew']:.0f} ps > {SLEW_LIMIT_PS:.0f}: untrustworthy; "
                "slew-limited -> regen with e7ebced0c4e (CORE-LIB-LIMITS-1330)", facts)
    return "SETUP", f"post-place setup wns {rep['wns']:.0f} ps worse than {SETUP_FLOOR_PS:.0f}: cannot sign", facts


def remote_info(kit_loc, timeout=120):
    """kit_loc 'host:/path' -> remote JSON dict or None"""
    host, _, path = kit_loc.partition(":")
    if not host or not path.startswith("/"):
        return None
    try:
        p = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "-o", "ControlPath=none", host,
                            "python3", "-I", "-", path], input=REMOTE_SCRIPT, capture_output=True, text=True, timeout=timeout)
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (OSError, subprocess.TimeoutExpired, ValueError, IndexError):
        return None


def verdict_line(rec, kit_loc, reason, facts, now=None):
    ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(now))
    scan = ""
    if facts.get("bits_over_cycle") is not None:
        scan = f"; {facts.get('over_reach')} hop groups over 405 um, {facts.get('bits_over_cycle')} bits over one cycle"
    return (f"- {ts} PST GEOM VERDICT [AUTO-VISUAL-REVIEW viewed auto_geom.json + placed_scan.json + place log/report] "
            f"{rec['die']}/{rec['item']} attempt_{int(rec.get('attempt') or 0)}: ISSUES-ACCEPT (advisory; owner 11-13 visual review "
            f"never blocks) kit={kit_loc} . {reason}{scan}. Layout smells are improvements for the die owner, not route blockers.")


def auto_review_pass(cfg, st, review_before_route, review_kit_location, hold_text="WAIT-VISUAL", max_rows=8, log=None,
                     info_fn=None, coord=None, commit=True):
    """One wave tick: review up to max_rows WAIT-VISUAL rows that have no verdict and were not judged yet.
    ACCEPT -> append an ISSUES-ACCEPT line to lanes/GEOM-REVIEW.md; else list in lanes/AUTO-REVIEW-HELD.tsv.  Returns counts."""
    coord = Path(coord) if coord else Path.home() / "coord"
    done = st.setdefault("auto_review", {})
    todo = []
    for rec in (st.get("items") or {}).values():
        if rec.get("status") != "ROUTE-HELD" or not str(rec.get("route_hold") or "").startswith(hold_text):
            continue
        if not review_before_route(cfg, rec):
            continue
        kit = review_kit_location(rec)
        key = f"{rec['die']}|{rec['item']}|{rec.get('attempt')}|{kit}"
        if not kit or key in done:
            continue
        todo.append((key, rec, kit))
    counts = dict(ACCEPT=0, SLEW_LIMITED=0, SETUP=0, ILLEGAL=0, NODATA=0)
    lines, held = [], []
    for key, rec, kit in todo[:max_rows]:
        info = (info_fn or remote_info)(kit)
        if info is None:
            counts["NODATA"] += 1
            continue
        cls, reason, facts = decide(info)
        if cls == "NODATA":
            counts["NODATA"] += 1
            continue
        counts[cls.replace("-", "_")] += 1
        done[key] = dict(cls=cls, t=int(time.time()), reason=reason[:200])
        if cls == "ACCEPT":
            lines.append(verdict_line(rec, kit, reason, facts))
        else:
            held.append("\t".join([rec["die"], rec["item"], str(rec.get("attempt")), cls, reason,
                                   "" if facts.get("wns") is None else f"{facts['wns']:.0f}",
                                   "" if facts.get("worst_slew") is None else f"{facts['worst_slew']:.0f}", kit]))
    if commit and (lines or held):
        _publish(coord, lines, held)
    if log and (lines or held):
        log(f"KIT-WAVE AUTO-VISUAL-REVIEW accepted {len(lines)} held {len(held)} {counts}")
    return counts


def _publish(coord, lines, held):
    files = []
    if lines:
        with open(coord / "lanes" / "GEOM-REVIEW.md", "a") as f:
            f.write("\n".join(lines) + "\n")
        files.append("lanes/GEOM-REVIEW.md")
    if held:
        p = coord / "lanes" / HELD_TSV
        head = "die\ttype\tattempt\tclass\treason\twns_ps\tworst_slew_ps\tkit\n"
        rows = {}
        for ln in (p.read_text().splitlines()[1:] if p.exists() else []):
            rows["\t".join(ln.split("\t")[:3])] = ln
        for ln in held:                  # one row per die/type/attempt: a re-review replaces it
            rows["\t".join(ln.split("\t")[:3])] = ln
        p.write_text(head + "\n".join(rows[k] for k in sorted(rows)) + "\n")
        files.append(f"lanes/{HELD_TSV}")
    try:
        subprocess.run([str(coord / "bin" / "coord-commit.sh"), "KIT-WAVE AUTO-VISUAL-REVIEW", *files],
                       capture_output=True, timeout=180, cwd=str(coord))
    except (OSError, subprocess.TimeoutExpired):
        pass
