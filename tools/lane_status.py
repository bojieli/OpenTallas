#!/usr/bin/env python3
"""lane_status.py (FLOW-PROC-B, FABLE-FLOW-0800 class b): schema + helpers for lanes/LANE-STATUS.tsv.

Schema, tab separated, one row per lane (the LAST row of a lane wins in post_redirect.py, so a duplicate is an error here):
  lane  status  successor  updated  note
  lane       [A-Za-z0-9][A-Za-z0-9._-]*
  status     exactly live | stood-down | done
  successor  a lane name, or the word none (a stood-down lane with nobody to inherit); empty for live/done
  updated    YYYY-MM-DD
  note       free text (time, reason, handoff path); column 5, may be absent in old rows
bin/stand-down.sh is the only writer of stood-down rows.  Modes:
  lane_status.py --check [FILE]            exit 1 and print every bad row
  lane_status.py --repair FILE             print the repaired table on stdout (prose moved into the note column, duplicates collapsed)
  lane_status.py --set FILE LANE SUCCESSOR [NOTE]   print FILE with LANE's row replaced/added as stood-down (today, PST), schema-checked; exit 1 on a bad result
  lane_status.py --running LANE            running ot-run/ot-push records of LANE on THIS host whose pid is alive (JSON lines)
"""
import json
import os
import re
import sys

LANE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
DATE = re.compile(r"^\d{4}-\d\d-\d\d$")
STATUSES = ("live", "stood-down", "done")
HDR = "lane\tstatus\tsuccessor\tupdated\tnote"


def check_row(f):
    """-> list of problems for one split row"""
    p = []
    if len(f) < 4 or len(f) > 5:
        return ["%d columns (want 4 or 5)" % len(f)]
    lane, st, succ, upd = f[:4]
    if not LANE.match(lane):
        p.append("lane %r" % lane)
    if st not in STATUSES:
        p.append("status %r not live|stood-down|done" % st)
    if st == "stood-down" and not (LANE.match(succ) or succ == "none"):
        p.append("successor %r not a lane name or none" % succ)
    if st == "stood-down" and succ == lane:
        p.append("successor is the lane itself")
    if st != "stood-down" and succ and not LANE.match(succ):
        p.append("successor %r" % succ)
    if not DATE.match(upd):
        p.append("updated %r not YYYY-MM-DD" % upd)
    return p


def check_text(text):
    bad, seen = [], {}
    for i, ln in enumerate(text.splitlines(), 1):
        if not ln.strip() or ln.startswith("#") or ln.startswith("lane\t"):
            continue
        f = ln.split("\t")
        pr = check_row(f)
        if f[0] in seen:
            pr.append("duplicate of line %d" % seen[f[0]])
        seen.setdefault(f[0], i)
        if pr:
            bad.append((i, "; ".join(pr), ln))
    return bad


def repair_text(text):
    rows = {}
    for ln in text.splitlines():
        if not ln.strip() or ln.startswith("#") or ln.startswith("lane\t"):
            continue
        f = ln.split("\t")
        if len(f) == 3 and re.match(r"^\d{4}-\d\d-\d\d\b", f[1]):    # lane, date[ time], successor: the status cell was lost
            f = [f[0], "stood-down", f[2], f[1]]
        while len(f) < 4:
            f.append("")
        lane, st, succ, upd = f[:4]
        note = f[4] if len(f) > 4 else ""
        extra = []
        m = re.match(r"^(stood-down|live|done)\b\s*(.*)$", st)
        if m:                                                 # "stood-down 2026-11-21 07:xx PST (context)"
            st = m.group(1)
            if m.group(2):
                extra.append(m.group(2))
        m = re.match(r"^(\d{4}-\d\d-\d\d)\b\s*(.*)$", upd)
        if m:
            upd = m.group(1)
            if m.group(2):
                extra.insert(0, m.group(2))
        elif not DATE.match(upd) and upd:
            extra.insert(0, upd)
            upd = ""
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)\s*(.*)$", succ)
        if m:
            succ = m.group(1)
            if m.group(2):
                extra.append(m.group(2).strip("() "))
        elif succ.strip():
            extra.append(succ)
            succ = "none"
        if st == "stood-down" and not succ:
            succ = "none"
        if st in ("live",) and succ == "none":
            succ = ""
        if not DATE.match(upd):                               # time-only or empty: keep the text, date the repair
            upd_note = upd
            upd = os.environ.get("LS_REPAIR_DATE", "")
            if upd_note:
                extra.insert(0, upd_note)
        n = " | ".join(x for x in ([note] if note else []) + extra if x)
        rows[lane] = [lane, st, succ, upd, n]                 # last row wins, as post_redirect.py reads it
    return HDR + "\n" + "".join("\t".join(r).rstrip("\t") + "\n" for r in rows.values())


def running(lane, d=None):
    d = d or os.environ.get("OT_STATUS_DIR") or os.path.join(os.path.expanduser("~"), ".local", "state", "ot-status")
    out = []
    try:
        names = os.listdir(d)
    except OSError:
        return out
    for fn in names:
        if not fn.endswith(".json") or fn.startswith("."):
            continue
        try:
            r = json.load(open(os.path.join(d, fn)))
        except (OSError, ValueError):
            continue
        if r.get("state") != "running" or r.get("lane", "").casefold() != lane.casefold():
            continue
        pid = r.get("pid")
        if not pid or not os.path.exists("/proc/%s" % pid):
            continue
        try:
            s = open("/proc/%s/stat" % pid).read()
            st = int(s[s.rindex(")") + 2:].split()[19])
        except (OSError, ValueError, IndexError):
            continue
        if r.get("pid_start") is not None and st != r["pid_start"]:
            continue
        out.append({k: r.get(k) for k in ("name", "unit", "host", "pid", "lane", "log")})
    return out


def main(a):
    if len(a) >= 2 and a[0] == "--check":
        path = a[1] if len(a) > 1 else "lanes/LANE-STATUS.tsv"
        bad = check_text(open(path).read())
        for i, why, ln in bad:
            print("LANE-STATUS.tsv line %d: %s: %s" % (i, why, ln[:100]))
        return 1 if bad else 0
    if len(a) == 2 and a[0] == "--repair":
        sys.stdout.write(repair_text(open(a[1]).read()))
        return 0
    if len(a) in (4, 5) and a[0] == "--set":
        text = open(a[1]).read()
        lane, succ = a[2], a[3]
        note = a[4].replace("\t", " ").replace("\n", " ") if len(a) == 5 else ""
        import time
        os.environ["TZ"] = "America/Los_Angeles"
        time.tzset()
        row = [lane, "stood-down", succ, time.strftime("%Y-%m-%d"), (time.strftime("%H:%M PST") + (" | " + note if note else ""))]
        if check_row(row):
            print("bad new row: " + "; ".join(check_row(row)), file=sys.stderr)
            return 1
        out, done = [], False
        for ln in text.splitlines():
            if ln.split("\t")[0] == lane:
                if not done:
                    out.append("\t".join(row))
                done = True
                continue
            out.append(ln)
        if not done:
            out.append("\t".join(row))
        res = "\n".join(out) + "\n"
        bad = check_text(res)
        if bad:
            for i, why, ln in bad[:5]:
                print("result row %d: %s: %s" % (i, why, ln[:80]), file=sys.stderr)
            return 1
        sys.stdout.write(res)
        return 0
    if len(a) == 2 and a[0] == "--running":
        for r in running(a[1]):
            print(json.dumps(r))
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
