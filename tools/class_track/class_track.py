#!/usr/bin/env python3
"""class_track.py -- CLASS-TRACK cut tool (COORD/OWNER 11-25: track problem CLASSES, not items).

Report-only by default.  Per cut it turns each die's PRE advisory output on its live plan (plan_advisory.py --json and
derived_drop.py RSTREACH text) plus a hand-adjudicated carry table into one count per (die, class), compares against the
previous cut in lanes/CLASS-TREND.tsv and prints one line per die:

    <DIE> open=<classes with count>0> NEW=<classes first seen this cut> total=<sum of counts> (last <prev>, <delta>)

Convergence (OWNER): NEW ~ 0 and falling counts per cut.  Two cuts in a row without a fall on a die -> LOOP.
A class counts toward the fall comparison only when it was measured on the same basis at both cuts (basis column);
first exact measures and lead-count baselines are listed but excluded from the comparable delta.

    class_track.py cut  --label "2026-11-26 09:00 PST" --pre-dir DIR --carry carry.tsv --trend CLASS-TREND.tsv \
                        [--classes CLASSES.tsv] [--plans plans.tsv] [--write]
    class_track.py seed --label "2026-11-25 21:00 PST" --baseline baseline.tsv --trend CLASS-TREND.tsv
"""
import argparse
import csv
import json
import os
import re
import sys

DIES = ("S81", "HEAD", "QC", "KV", "FLEET")  # FLEET: fleet/process classes only (no plan); HBM parked, not tracked
DIEFILE = {"S81": "s81", "HEAD": "head", "QC": "qc", "KV": "kv"}
# class id -> (PRE tag, label).  RSTREACH is read from derived_drop text (rst_<die>.txt), the rest from plan_advisory json.
PRE_CLASSES = {
    "C-STREET": "ADV-FP-STREET",
    "C-LEG405": "ADV-LEG405-ZERO",
    "C-TAP-LOAD": "ADV-TAP-LOAD",
}
# PRE checks that report findings but have no class in CLASSES.tsv yet -> candidate NEW classes (first seen, no owner).
PRE_ONLY = {
    "C-FT-CROSSES-CORE": "ADV-FT-CROSSES-CORE",
    "C-RELAY-SEAT": "ADV-RELAY-SEAT",
    "C-OVERSIZE": "ADV-FP-OVERSIZE",
    "C-LAND-REACH": "ADV-LAND-REACH",
}
TREND_COLS = ["cut_local", "die", "class_id", "count", "basis", "source", "prev_count", "prev_basis", "move"]
EXACT = "exact"
CARRIED = set()      # (die, class) rows copied from the previous cut without a fresh measurement: shown, never counted as a fall or a rise
OWNER_OVERRIDE = {}  # (die, class) -> owner named by a carry row (lane-measured rows may name the right owner)
OWN_NOTE = re.compile(r"\d\d:\d\d PST CLASS-TRACK|^PRE |CLASS-TRACK PRE")  # a note this tool wrote itself (evidence paths may contain the CLASS-TRACK directory)
LANE_SHA = re.compile(r"\b[0-9a-f]{7,64}\b")


def _line_type(line, tag):
    """type name of a `WARN <tag> <type>: ...` line, or None for summary / not-checked / INFO / non-matching lines."""
    m = re.match(r"^(?:WARN|FAIL)\s+" + re.escape(tag) + r"\s+(\S+?):?\s", line + " ")
    if not m:
        return None
    t = m.group(1)
    if t in ("summary", "not", "plan"):
        return None
    return t


def types_for(lines, tag):
    out = set()
    for ln in lines:
        t = _line_type(ln, tag)
        if t:
            out.add(t)
    return out


def load_pre(pre_dir, die):
    f = os.path.join(pre_dir, DIEFILE[die] + ".json")
    if not os.path.exists(f):
        return None
    with open(f) as fh:
        return json.load(fh).get("advisories", [])


def load_rst(pre_dir, die):
    f = os.path.join(pre_dir, "rst_" + DIEFILE[die] + ".txt")
    if not os.path.exists(f):
        return None
    with open(f) as fh:
        return fh.read().splitlines()


def read_tsv(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def measure(pre_dir, carry_rows, plans):
    """-> {(die, class): (count, basis, source)}"""
    res = {}
    for die in DIES:
        if die not in DIEFILE:
            continue
        adv = load_pre(pre_dir, die)
        sha = plans.get(die, "")
        if adv is not None:
            for cid, tag in {**PRE_CLASSES, **PRE_ONLY}.items():
                res[(die, cid)] = (len(types_for(adv, tag)), EXACT, f"PRE {tag} types on live plan {sha}")
        rst = load_rst(pre_dir, die)
        if rst is not None:
            fails = types_for([x for x in rst if x.startswith("FAIL ")], "RSTREACH")
            warns = types_for([x for x in rst if x.startswith("WARN ")], "RSTREACH")
            res[(die, "C-RST-RELAY-REACH")] = (len(fails), EXACT, f"derived_drop RSTREACH FAIL types on live plan {sha} ({len(warns)} advisory WARN types)")
    for r in carry_rows:
        res[(r["die"], r["class_id"])] = (int(r["count"]), r["basis"], r["source"])
        if r.get("carried") == "1":
            CARRIED.add((r["die"], r["class_id"]))
        if r.get("owner"):
            OWNER_OVERRIDE[(r["die"], r["class_id"])] = r["owner"]
    return res


def last_cut(trend_rows):
    cuts = []
    for r in trend_rows:
        if r["cut_local"] not in cuts:
            cuts.append(r["cut_local"])
    return cuts


def prev_map(trend_rows):
    """latest row per (die, class) -> row; plus all classes ever seen per die."""
    latest, seen = {}, set()
    for r in trend_rows:
        latest[(r["die"], r["class_id"])] = r
        seen.add((r["die"], r["class_id"]))
    return latest, seen


def compare(meas, trend_rows, label):
    latest, seen = prev_map(trend_rows)
    known_ids = {c for (_, c) in seen}
    rows = []
    for (die, cid), (cnt, basis, src) in sorted(meas.items()):
        p = latest.get((die, cid))
        if p is None and cid in known_ids:  # a known class first counted on this die: it was 0 there at the last cut
            p = {"count": "0", "basis": basis}
        if (die, cid) in CARRIED and p is not None:
            move = "CARRIED"
            pc, pb = int(p["count"]), p["basis"]
        elif p is None:
            move = "NEW"
            pc, pb = "", ""
        else:
            pc, pb = int(p["count"]), p["basis"]
            if pb != basis:
                move = "FIRST-EXACT" if basis == EXACT else "BASIS-CHANGE"
            else:
                move = "DOWN" if cnt < pc else ("UP" if cnt > pc else "FLAT")
        rows.append({"cut_local": label, "die": die, "class_id": cid, "count": cnt, "basis": basis, "source": src,
                     "prev_count": pc, "prev_basis": pb, "move": move})
    return rows


def summarize(rows, trend_rows):
    """per die: open, NEW, total, prev_total (same classes as the previous cut), comparable cur/prev, delta."""
    latest, _ = prev_map(trend_rows)
    out = {}
    for die in DIES:
        mine = [r for r in rows if r["die"] == die]
        tracked = [r for r in mine if r["move"] != "NEW"]
        total = sum(int(r["count"]) for r in tracked)  # classes already on the ledger at the last cut
        new_items = sum(int(r["count"]) for r in mine if r["move"] == "NEW")
        prev_total = sum(int(p["count"]) for (d, c), p in latest.items() if d == die and p["move"] != "STREAK" and p["class_id"] != "*STREAK*")
        comp_cur = sum(int(r["count"]) for r in mine if r["move"] in ("UP", "DOWN", "FLAT"))
        comp_prev = sum(int(r["prev_count"]) for r in mine if r["move"] in ("UP", "DOWN", "FLAT"))
        out[die] = {
            "open": sum(1 for r in mine if int(r["count"]) > 0),
            "new": sum(1 for r in mine if r["move"] == "NEW"),
            "new_ids": [r["class_id"] for r in mine if r["move"] == "NEW"],
            "total": total, "prev_total": prev_total, "new_items": new_items,
            "comp_cur": comp_cur, "comp_prev": comp_prev,
            "fell": comp_cur < comp_prev,
            "first_exact": [r["class_id"] for r in mine if r["move"] in ("FIRST-EXACT", "BASIS-CHANGE")],
        }
    return out


def loop_check(summary, trend_rows, label):
    """LOOP when this cut and the previous cut both show no fall on the comparable basis (no NEW-free fall either)."""
    hist = {}
    for r in trend_rows:
        if r["move"] == "STREAK":
            hist[r["die"]] = int(r["count"])
    loops = {}
    for die, s in summary.items():
        streak = hist.get(die, 0)
        streak = 0 if s["fell"] else (streak if s["comp_cur"] + s["comp_prev"] == 0 else streak + 1)  # nothing re-measured: no evidence either way
        s["streak"] = streak
        loops[die] = streak >= 2
    return loops


def render(summary, loops, label):
    out = [f"CLASS-TRACK cut {label}"]
    for die in DIES:
        s = summary[die]
        d = s["total"] - s["prev_total"]
        cd = s["comp_cur"] - s["comp_prev"]
        out.append(f"{die} open={s['open']} NEW={s['new']} total={s['total']} (last {s['prev_total']}, {d:+d}) +{s['new_items']} items in NEW classes; "
                   f"comparable classes {s['comp_prev']}->{s['comp_cur']} ({cd:+d}); no-fall streak {s['streak']}"
                   + (f"; NEW ids {','.join(s['new_ids'])}" if s["new_ids"] else "")
                   + (f"; first exact {','.join(s['first_exact'])}" if s["first_exact"] else ""))
    bad = [d for d, v in loops.items() if v]
    out.append("LOOP: " + (",".join(bad) if bad else "none"))
    return "\n".join(out)


def write_trend(path, rows, summary, label):
    new_file = not os.path.exists(path)
    with open(path, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=TREND_COLS, delimiter="\t", lineterminator="\n")
        if new_file:
            w.writeheader()
        for r in rows:
            w.writerow(r)
        for die, s in summary.items():  # one STREAK marker row per die per cut (no-fall streak length)
            w.writerow({"cut_local": label, "die": die, "class_id": "*STREAK*", "count": s["streak"], "basis": "meta",
                        "source": "no-fall streak on comparable classes", "prev_count": "", "prev_basis": "", "move": "STREAK"})


def update_classes(path, rows, label, meta=None):
    """refresh mapped_count / cut_local / owner_measurement of existing CLASSES.tsv rows; append NEW classes."""
    cur = read_tsv(path)
    cols = list(cur[0].keys()) if cur else ["class_id", "die", "kind", "static_check", "owner", "cut_local", "mapped_count",
                                            "status", "owner_measurement"]
    idx = {(r["die"], r["class_id"]): r for r in cur}
    for r in rows:
        k = (r["die"], r["class_id"])
        note = f"{label} CLASS-TRACK {r['source']}: {r['count']} (last {r['prev_count'] if r['prev_count'] != '' else 'none'}, {r['move']})"
        if k in idx:
            old = idx[k].get("owner_measurement", "")
            lane_sha = bool(LANE_SHA.search(old)) and not OWN_NOTE.search(old)
            carry_sha = bool(LANE_SHA.search(r["source"])) and not OWN_NOTE.search(r["source"])
            # COORD 11-26 09:22: a lane-measured count with an evidence sha wins over the cut tool's own count: a row whose
            # owner_measurement carries a sha (and is not a CLASS-TRACK note) keeps its count and text unless this cut brings its own lane sha.
            if carry_sha:
                idx[k]["cut_local"], idx[k]["mapped_count"] = label, str(r["count"])
                idx[k]["owner_measurement"] = r["source"]
            elif not lane_sha:
                idx[k]["cut_local"], idx[k]["mapped_count"], idx[k]["owner_measurement"] = label, str(r["count"]), note
            if (k) in OWNER_OVERRIDE:
                idx[k]["owner"] = OWNER_OVERRIDE[k]
        else:
            m = (meta or {}).get(r["class_id"], {})
            idx[k] = {"class_id": r["class_id"], "die": r["die"], "kind": m.get("kind") or ("DESIGN" if r["class_id"].startswith("C-") else "PROCESS"),
                      "static_check": m.get("static_check") or r["source"], "owner": m.get("owner") or "UNOWNED (CLASS-TRACK first seen)",
                      "cut_local": label,
                      "mapped_count": str(r["count"]), "status": "NEW at first cut; needs an owner",
                      "owner_measurement": note}
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, delimiter="\t", lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for k in sorted(idx, key=lambda k: (k[1], DIES.index(k[0]) if k[0] in DIES else 9)):
            w.writerow(idx[k])


TAG = re.compile(r"\b[CP]-[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+\b")
STAMP = re.compile(r"^- (\d{4}-\d{2}-\d{2} \d{2}:\d{2})\b")


def scan_posts(posts_dir, since, known):
    """(lane, stamp, class_id) of the first post since `since` per unknown class id; only post lines start with a stamp."""
    first = {}
    for fn in sorted(os.listdir(posts_dir)):
        if not fn.endswith(".md"):
            continue
        with open(os.path.join(posts_dir, fn), errors="replace") as fh:
            for ln in fh:
                m = STAMP.match(ln)
                if not m or m.group(1) < since:
                    continue
                for cid in TAG.findall(ln):
                    if cid not in known and (cid not in first or m.group(1) < first[cid][1]):
                        first[cid] = (fn[:-3], m.group(1))
    return sorted((v[0], v[1], k) for k, v in first.items())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cut")
    c.add_argument("--label", required=True)
    c.add_argument("--pre-dir", required=True)
    c.add_argument("--carry", default="")
    c.add_argument("--trend", required=True)
    c.add_argument("--classes", default="")
    c.add_argument("--meta", default="", help="TSV class_id, owner, static_check, kind for classes first seen this cut")
    c.add_argument("--plans", default="", help="TSV die<TAB>plan_sha12 (for the source column)")
    c.add_argument("--write", action="store_true", help="append CLASS-TREND.tsv and refresh CLASSES.tsv (default: report only)")
    n = sub.add_parser("scan", help="class ids tagged in lane posts since a cut that CLASSES.tsv / the trend do not know")
    n.add_argument("--posts", required=True)
    n.add_argument("--since", required=True, help='"YYYY-MM-DD HH:MM" local')
    n.add_argument("--classes", required=True)
    n.add_argument("--trend", default="")
    pl = sub.add_parser("plans", help="print the live plan per die from autopilot/kit_wave.json (TSV: die plan tree asbuilt bind_out)")
    pl.add_argument("--kit-wave", required=True)
    s = sub.add_parser("seed")
    s.add_argument("--label", required=True)
    s.add_argument("--baseline", required=True)
    s.add_argument("--trend", required=True)
    a = ap.parse_args(argv)

    if a.cmd == "plans":
        dies = json.load(open(a.kit_wave))["dies"]
        print("die\tplan\ttree\tasbuilt\tbind_out")
        for die, key in (("S81", "s81"), ("HEAD", "s81_head"), ("QC", "qwen_compute"), ("KV", "qwen_kvsys")):
            d = dies.get(key) or {}
            kr = d.get("kit_rtl") or {}
            print("\t".join([die, d.get("plan") or "-", d.get("src") or "-", kr.get("asbuilt") or "-", kr.get("bind_out") or "-"]))
        return 0
    if a.cmd == "scan":
        for lane, ts, cid in scan_posts(a.posts, a.since, {r["class_id"] for r in read_tsv(a.classes)} |
                                        {r["class_id"] for r in read_tsv(a.trend)}):
            print(f"{cid}\t{lane}\t{ts}")
        return 0
    if a.cmd == "seed":
        rows = [{"cut_local": a.label, "die": r["die"], "class_id": r["class_id"], "count": r["count"], "basis": r["basis"],
                 "source": r["source"], "prev_count": "", "prev_basis": "", "move": "BASELINE"} for r in read_tsv(a.baseline)]
        if os.path.exists(a.trend) and read_tsv(a.trend):
            print("trend already has rows; refusing to seed", file=sys.stderr)
            return 2
        summary = {d: {"streak": 0} for d in DIES}
        write_trend(a.trend, rows, summary, a.label)
        print(f"seeded {len(rows)} rows at {a.label}")
        return 0

    plans = {r["die"]: r["plan_sha12"] for r in read_tsv(a.plans)} if a.plans else {}
    carry = read_tsv(a.carry) if a.carry else []
    trend = read_tsv(a.trend)
    meas = measure(a.pre_dir, carry, plans)
    rows = compare(meas, trend, a.label)
    summary = summarize(rows, trend)
    loops = loop_check(summary, trend, a.label)
    print(render(summary, loops, a.label))
    for die in [d for d, v in loops.items() if v]:
        print(f"LOOP-BREAKDOWN {die}: class prev->now move")
        for r in rows:
            if r["die"] == die and (int(r["count"]) > 0 or str(r["prev_count"]) not in ("", "0")):
                print(f"  {r['class_id']} {r['prev_count'] if r['prev_count'] != '' else '-'}->{r['count']} {r['move']}")
    if a.write:
        write_trend(a.trend, rows, summary, a.label)
        if a.classes:
            update_classes(a.classes, rows, a.label, {r['class_id']: r for r in read_tsv(a.meta)} if a.meta else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
