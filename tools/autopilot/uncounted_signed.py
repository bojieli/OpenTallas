#!/usr/bin/env python3
"""UNCOUNTED-SIGNED (FLOW-FLEET-R1 11-22, FABLE-FLOW-0000 F7): a SIGNED row that is not counted for more than 2 h is alerted, naming the gate it waits on.

slice_station__t52 waited 20.7 h as PENDING-LEC and QC slw_hc3__clccfc3e6b__pvcca9ff41 sat pending, and nobody was told: the count only shows totals.
Sources (read-only):
  * lanes/COUNT-REVOKED.tsv rows whose reason starts PENDING-<GATE> (PENDING-LEC -> gate LEC, PENDING-VISUAL -> visual, ...)
  * the release-tree cache: plans[*].pending_archive_types / pending_archive_cores -> gate "archive key" (no AGIdock archive / INDEX row), or
    "flow tag" when the record is SIGNED-NO-TAG (provenance)
  * the auto-export spool items set aside (spool/failed/*.reason, F9) that are not canary / test runs -> gate "export"
Not alerted (LEC-AUTOFILL 11-25): a PENDING row whose die/type the release-tree cache credits from another record (the revoked
sha was replaced, e.g. "replaces revoked c7ce90ba4af9"), and a set-aside spool item whose record the export ledger has since
marked done (rtx-pro verified after the set-aside; the stale spool/failed file is not a missing export).
Age = now - the earliest of (first seen by this tool, a time the record names: COUNT-REVOKED date, ns / s epoch in the path, spool file time).
Rows older than ALERT_H are written to lanes/UNCOUNTED-SIGNED.md; each new one gets ONE NEEDS-ACTION line in lanes/COORD-REVIEW-QUEUE.md
(state ~/.local/state/uncounted_signed.json), both through bin/coord-commit.sh.  --dry prints only.

    python3 -I tools/autopilot/uncounted_signed.py [--dry] [--coord ~/coord]
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
ALERT_H = float(os.environ.get("OT_UNCOUNTED_ALERT_H", "2"))
CACHE = HOME / ".local/state/fleet-viz/release_tree_plan_cache.json"
SPOOL_FAILED = HOME / ".local/state/ot-auto-export/spool/failed"
LEDGER = HOME / ".local/state/ot-auto-export/ledger.json"
STATE = HOME / ".local/state/uncounted_signed.json"
OUT = "lanes/UNCOUNTED-SIGNED.md"
QUEUE = "lanes/COORD-REVIEW-QUEUE.md"
GATE_WORDS = {"LEC": "LEC", "VISUAL": "visual", "EXPORT": "export", "ARCHIVE": "archive key", "DRC": "DRC", "STA": "STA"}
NOT_RECORD = re.compile(r"canary|/test[_-]|not a sign-off of record", re.I)


def _date_epoch(text):
    m = re.search(r"(\d{4}-\d{2}-\d{2})(?:[ T](\d{2}):(\d{2}))?", text or "")
    if not m:
        return None
    try:
        return time.mktime(time.strptime(m.group(1) + " " + (m.group(2) or "00") + ":" + (m.group(3) or "00"), "%Y-%m-%d %H:%M"))
    except ValueError:
        return None


def _path_epoch(text):
    m = re.search(r"(?<!\d)(1[78]\d{17})(?!\d)", text or "")         # ns epoch (signoff_eco_<ns>)
    if m:
        return int(m.group(1)) / 1e9
    m = re.search(r"(?<!\d)(1[78]\d{8})(?!\d)", text or "")          # s epoch
    return float(m.group(1)) if m else None


def credited_names(cache):
    """-> {(die, type)} the release-tree cache credits from a replacement record"""
    return {(c.get("die"), c.get("name")) for c in ((cache or {}).get("credited") or []) if isinstance(c, dict)}


def done_records(ledger):
    """-> record shas the export ledger marks done (rtx-pro verified, INDEX rows written)"""
    return {u.get("record") for u in ((ledger or {}).get("units") or {}).values()
            if isinstance(u, dict) and u.get("state") == "done" and u.get("record")}


def rows_from_revoked(text, credited=()):
    out = []
    for ln in (text or "").splitlines():
        if not ln.strip() or ln.startswith("#"):
            continue
        f = ln.split("\t")
        if len(f) < 4:
            continue
        m = re.match(r"\s*PENDING-([A-Z]+)", f[3])
        if not m:
            continue
        if (f[0], f[1]) in credited:
            continue                                  # counted from the replacement record
        gate = GATE_WORDS.get(m.group(1), m.group(1).lower())
        out.append(dict(die=f[0], name=f[1], gate=gate, evidence=f[3][:200], t=_date_epoch(f[4] if len(f) > 4 else "")))
    return out


def rows_from_cache(cache):
    out = []
    for plan, ent in sorted(((cache or {}).get("plans") or {}).items()):
        die = ent.get("die") or plan.split("/")[0]
        for key in ("pending_archive_types", "pending_archive_cores"):
            for name, ev in sorted((ent.get(key) or {}).items()):
                evs = ev if isinstance(ev, list) else [str(ev)]
                txt = " | ".join(map(str, evs))
                gate = "flow tag (record has no src_commit / flow_tag)" if all("SIGNED-NO-TAG" in str(e) for e in evs) and evs else \
                    "archive key (no AGIdock archive / INDEX row)"
                ts = [t for t in (_path_epoch(str(e)) for e in evs) if t]
                out.append(dict(die=die, name=name, gate=gate, evidence=txt[:200], t=min(ts) if ts else None))
    return out


def rows_from_spool(d=SPOOL_FAILED, done=()):
    out = []
    for r in sorted(glob.glob(str(Path(d) / "*.reason"))):
        try:
            why = json.loads(Path(r).read_text()).get("reason") or ""
        except (OSError, ValueError):
            why = Path(r).read_text(errors="replace")[:200] if os.path.exists(r) else ""
        if NOT_RECORD.search(why):
            continue
        j = r[:-len(".reason")]
        try:
            rec = json.loads(Path(j).read_text())
        except (OSError, ValueError):
            rec = {}
        if rec.get("record") and rec["record"] in done:
            continue                                  # exported and verified after it was set aside
        try:
            t = os.stat(j).st_mtime
        except OSError:
            t = None
        out.append(dict(die=rec.get("die") or "?", name=rec.get("name") or rec.get("element") or Path(j).stem, gate="export",
                        evidence=f"set aside: {why}"[:200], t=t))
    return out


# P-SIGNED-CANDIDATE-FALSE (FABLE-FLOW-0910 a5, COORD 11-27 ruling 4; no b4e3 prescreen source exists on main, so this is the ruled rule): a row is a REAL signed
# candidate only if (1) its sign-off verdict re-reads as SIGNED, (2) the record has an INDEX or AGIdock row by sha, and (3) the LEC verdict is EQ.  A row whose
# evidence names a readable sign-off / LEC artifact that fails (1) or (3) is a false candidate (diagnostic body, NOT SIGNED probe) and is dropped from the table;
# an unreadable artifact keeps the row (an alert is cheap, a lost one is not).  Gate (2) is what the table itself reports (gate "archive key"), so it is not a drop reason.
PATH_RE = re.compile(r"(/[\w@.+=,/-]+?/(?:signoff/)?signoff\.json)")


def prescreen(row, read=lambda p: Path(p).read_text()):
    """-> (keep, why)"""
    m = PATH_RE.search(row.get("evidence", "") or "")
    if not m:
        return True, "no readable sign-off artifact named"
    try:
        d = json.loads(read(m.group(1)))
    except (OSError, ValueError):
        return True, "sign-off artifact unreadable"
    verdict = str(d.get("verdict") or d.get("status") or "")
    if verdict and verdict != "SIGNED":
        return False, f"rejudged verdict {verdict}"
    lec = str(((d.get("checks") or {}).get("lec") or {}).get("verdict") or d.get("lec") or "") if isinstance(d.get("checks"), dict) or d.get("lec") else ""
    if lec and lec.upper() not in ("EQ", "EQUIVALENT"):
        return False, f"LEC {lec}"
    return True, "SIGNED"


def judge(rows, state, now, alert_h=ALERT_H):
    """-> (due rows with 'age_h', new keys).  state {'seen': {key: t}, 'alerted': {key: t}} is updated in place"""
    seen = state.setdefault("seen", {})
    alerted = state.setdefault("alerted", {})
    live = set()
    due, new = [], []
    for r in rows:
        k = f"{r['die']}|{r['name']}|{r['gate']}"
        live.add(k)
        seen.setdefault(k, now)
        t0 = min(x for x in (seen[k], r.get("t")) if x)
        age_h = (now - t0) / 3600.0
        if age_h >= alert_h:
            due.append(dict(r, key=k, age_h=round(age_h, 1)))
            if k not in alerted:
                alerted[k] = now
                new.append(k)
    for k in [k for k in seen if k not in live]:
        seen.pop(k, None)
        alerted.pop(k, None)                         # counted (or gone): a recurrence alerts again
    due.sort(key=lambda r: -r["age_h"])
    return due, new


def render(due, now):
    head = (f"# UNCOUNTED-SIGNED ({time.strftime('%Y-%m-%d %H:%M %Z', time.localtime(now))}; tools/autopilot/uncounted_signed.py, FABLE-FLOW-0000 F7)\n\n"
            f"SIGNED rows not counted for more than {ALERT_H:g} h, with the gate each waits on.\n\n")
    if not due:
        return head + "None.\n"
    lines = ["| die | type | missing gate | waiting | evidence |", "|---|---|---|---|---|"]
    lines += [f"| {r['die']} | {r['name']} | {r['gate']} | {r['age_h']:.1f} h | {r['evidence'].replace('|', '/')[:160]} |" for r in due]
    return head + "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--coord", default=str(HOME / "coord"))
    a = ap.parse_args(argv)
    coord = Path(a.coord)
    now = time.time()
    rows = []
    try:
        cache = json.loads(CACHE.read_text())
    except (OSError, ValueError):
        cache = {}
    try:
        rows += rows_from_revoked((coord / "lanes/COUNT-REVOKED.tsv").read_text(), credited_names(cache))
    except OSError:
        pass
    rows += rows_from_cache(cache)
    try:
        done = done_records(json.loads(LEDGER.read_text()))
    except (OSError, ValueError):
        done = set()
    rows += rows_from_spool(done=done)
    try:
        state = json.loads(STATE.read_text())
    except (OSError, ValueError):
        state = {}
    rows = [r for r in rows if prescreen(r)[0]]
    due, new = judge(rows, state, now)
    for r in due:
        print(f"UNCOUNTED-SIGNED {r['die']} {r['name']}: gate {r['gate']}, {r['age_h']:.1f} h ({r['evidence'][:120]})")
    print(f"UNCOUNTED-SIGNED {len(due)} row(s) over {ALERT_H:g} h, {len(new)} new")
    if a.dry:
        return 0
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state))
    (coord / OUT).write_text(render(due, now))
    files = [OUT]
    if new:
        stamp = time.strftime("%Y-%m-%d %H:%M %Z", time.localtime(now))
        with open(coord / QUEUE, "a") as f:
            for r in due:
                if r["key"] in new:
                    f.write(f"- {stamp} NEEDS-ACTION [UNCOUNTED-SIGNED -> COORD + {r['die']} owner] {r['die']}/{r['name']} signed but not counted "
                            f"for {r['age_h']:.1f} h: missing gate {r['gate']} ({r['evidence'][:160]}); table {OUT}\n")
        files.append(QUEUE)
    try:
        subprocess.run([str(coord / "bin/coord-commit.sh"), "uncounted-signed (auto)"] + files, timeout=280, capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        print("UNCOUNTED-SIGNED coord-commit timed out; the files are in the tree for the next commit", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
