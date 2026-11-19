#!/usr/bin/env python3
"""kit_scan.py -- PRECHECK-1119 early kit scans (FABLE-CLOSURE-STRATEGY 11-19): run on a gen host over its kit runs,
each scan once per kit, as soon as the stage it reads exists.  An estimator: it posts, never stops a kit.

  kit_scan.py --kit KIT_DIR [--post]                    one kit (KIT_DIR/work/config.mk)
  kit_scan.py --roots /srv/opentallas-scratch2/claude/ot-jobs [--post] [--max-age-h 12]   one pass over new kits

FOLD    after synthesis (1_2_yosys.v): declared register bits vs netlist flops per class (fold_scan.py).
PLACED  after placement (3_place.odb, in the ORFS container, placed_hops_or.py): every register -> register leg
        whose launch -> capture Manhattan distance exceeds CBC reach (405 um), grouped by register class pair; and the
        in-tap skew from placement geometry is computed but NOT posted (it does not predict the CTS number:
        R2 <= 0.07 on 413 taps, skew_calib.py 11-19).
CTS     after CTS (4_1_cts.log OT_TAP_INSERTION skew_ps, taps >= 100 sinks): the measured in-tap skew, worst tap and the
        taps >= 100 ps.  CBC bands: < 60 ps 58 of 111 kits closed, >= 100 ps 0 of 23.
State: ~/.local/state/precheck-kit-scan/<kit>.<scan>.json (a scan that wrote its state is not repeated).
"""
import argparse
import collections
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "die_plan"))
import cbc_rules as CBC  # noqa: E402
sys.path.pop(0)
sys.path.insert(0, str(HERE))
import fold_scan as FS  # noqa: E402

MIN_TAP_SINKS = 32      # a tap with fewer sinks is a core / edge tap: its spread is not a tree skew
OT_HEAVY = "/srv/opentallas-scratch2/claude/rt/current/tools/fleet/ot-heavy"
STATE = Path(os.path.expanduser("~/.local/state/precheck-kit-scan"))
IMAGE = os.environ.get("OT_ORFS_IMAGE", "openroad/orfs:asap7lock")
CLS = re.compile(r"\[\d+\]")
TAPLINE = re.compile(r"OT_TAP_INSERTION tap=(\S+) sinks=(\d+) ins_ps=([-\d.]+) skew_ps=([-\d.]+)")


def reg_class(name):
    s = re.sub(r"\\?\[\d+\\?\]", "", name.lstrip("\\"))
    s = re.sub(r"\$_\w+_$", "", s)
    s = re.sub(r"^u_bound\.", "", s)
    s = re.sub(r"src_[0-9a-f]{8,}", "src_H", s)
    s = re.sub(r"_\d+_", "_N_", s)
    s = re.sub(r"\d+$", "N", s)
    return s[-70:]


def kit_type(kit):
    m = re.match(r"^(.+?)-(route|place|cts|grt|kit|sign|signoff|flow|full)-", Path(kit).name)
    return m.group(1) if m else Path(kit).name


def stage_file(kit, name):
    c = sorted(Path(kit, "work/run/results").glob(f"*/*/base/{name}"))
    return c[0] if c else None


def taps_of(kit):
    try:
        b = json.loads(Path(kit, "work/budget.json").read_text())
    except (OSError, ValueError):
        return [], None
    ck = b.get("clock") or {}
    taps = ck.get("taps_snapped") or ck.get("taps") or []
    return [(t["name"], float(t["xy"][0]), float(t["xy"][1])) for t in taps if t.get("xy")], ck.get("tap_max_sinks")


def assign_taps(taps, regs, cap, radius):
    """{tap: [distances]} nearest tap, then the clock_taps.tcl cap pass: the farthest sinks of an over-cap tap move to the
    nearest tap with room within radius"""
    member = collections.defaultdict(list)
    for x, y in regs:
        best = min(taps, key=lambda t: abs(t[1] - x) + abs(t[2] - y))
        member[best[0]].append((abs(best[1] - x) + abs(best[2] - y), x, y))
    pos = {t[0]: (t[1], t[2]) for t in taps}
    for n in sorted(member, key=lambda k: -len(member[k])):
        if len(member[n]) <= cap:
            continue
        member[n].sort()
        keep, extra = member[n][:cap], member[n][cap:]
        member[n] = keep
        for _d, x, y in extra:
            cands = sorted((abs(pos[t][0] - x) + abs(pos[t][1] - y), t) for t in pos if t != n and len(member[t]) < cap)
            if cands and cands[0][0] <= radius + abs(pos[n][0] - x) + abs(pos[n][1] - y):
                d, t = cands[0]
                member[t].append((d, x, y))
            else:
                member[n].append((abs(pos[n][0] - x) + abs(pos[n][1] - y), x, y))
    return {n: sorted(d for d, _x, _y in v) for n, v in member.items()}


def skew_estimate(dists, ps_per_um=CBC.TAP_SKEW_PS_PER_UM):
    if len(dists) < 4:
        return 0.0
    lo = dists[int(0.02 * (len(dists) - 1))]
    hi = dists[int(0.98 * (len(dists) - 1))]
    return round(ps_per_um * (hi - lo), 1)


def run_placed(kit, odb, out_json, mem_gb=14):
    o = out_json.parent
    cmd = ["docker", "run", "--rm", "--name", f"phscan-{os.getpid()}", "--cpus=1", f"--memory={mem_gb}g", f"--memory-swap={mem_gb}g",
           "-e", "OT_ODB=/k/" + odb.name, "-e", "OT_OUT=/o/" + out_json.name, "-e", f"OT_REACH_UM={CBC.REACH_UM_PER_HOP}",
           "-v", f"{odb.parent}:/k:ro", "-v", f"{o}:/o", "-v", f"{HERE}:/s:ro", IMAGE, "bash", "-lc",
           "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -python -exit /s/placed_hops_or.py > /o/%s.log 2>&1; "
           "rc=$?; chown %d:%d /o/%s /o/%s.log 2>/dev/null; exit $rc" % (out_json.stem, os.getuid(), os.getgid(), out_json.name, out_json.stem)]
    if os.path.exists(OT_HEAVY):         # host memory admission (owner r709 rails): queue like any heavy job
        cmd = [OT_HEAVY, "--mem", str(mem_gb), "--tag", f"phscan-{kit_type(kit)}", "--max-wait", "3600", "--"] + cmd
    return subprocess.run(cmd, capture_output=True, text=True, timeout=10800).returncode


def summarise_placed(kit, ph, reach=CBC.REACH_UM_PER_HOP):
    legs = [r for r in ph.get("legs", []) if r[0] > reach]
    pairs = collections.defaultdict(lambda: [0, 0.0, None])
    for st, acc, a, b, pin, la, lb in legs:
        k = (reg_class(a), reg_class(b))
        p = pairs[k]
        p[0] += 1
        if st > p[1]:
            p[1], p[2] = st, (a, b, la, lb)
    top = sorted(pairs.items(), key=lambda kv: -kv[1][0])
    taps, cap = taps_of(kit)
    skew = {}
    if taps and ph.get("regs"):
        mem = assign_taps(taps, [tuple(r) for r in ph["regs"]], int(min(cap or CBC.TAP_MAX_SINKS, CBC.TAP_MAX_SINKS)), CBC.TAP_RADIUS_UM)
        skew = {n: (skew_estimate(d), len(d)) for n, d in mem.items() if len(d) >= MIN_TAP_SINKS}
    worst = max((v[0] for v in skew.values()), default=None)
    return dict(legs_over=len(legs), pairs=[[a, b, n, round(w, 1), ex] for (a, b), (n, w, ex) in top[:40]],
                skew_worst_ps=worst, taps_over_pass=sorted([n for n, v in skew.items() if v[0] >= CBC.TAP_SKEW_PASS_PS]),
                taps_over_fail=sorted([n for n, v in skew.items() if v[0] >= CBC.TAP_SKEW_FAIL_PS]),
                skew=skew, n_regs=ph.get("n_regs"))


def post(text):
    subprocess.run(["timeout", "600", "ssh", "-n", "-o", "ControlPath=none", "intel2",
                    "bash ~/coord/bin/post.sh PRECHECK-1119 '" + text.replace("'", "'\"'\"'") + "'"], capture_output=True, text=True)


def kit_die(kit):
    try:
        return json.loads(Path(kit, "work/budget.json").read_text()).get("die") or "?"
    except (OSError, ValueError):
        return "?"


def scan_kit(kit, do_post=False, mem_gb=14):
    kit = Path(kit)
    STATE.mkdir(parents=True, exist_ok=True)
    tn = kit_type(kit)
    msgs = []
    sf = STATE / f"{kit.name}.fold.json"
    if not sf.exists() and stage_file(kit, "1_2_yosys.v"):
        r = FS.scan(kit / "work")
        sf.write_text(json.dumps(r, indent=1))
        if r.get("folds"):
            msgs.append(f"FOLD {r['lost']} register bits merged by synthesis: " + "; ".join(f"{c} {b} -> {n}" for c, b, n in r["folds"][:4]))
    sp = STATE / f"{kit.name}.placed.json"
    odb = stage_file(kit, "3_place.odb")
    if not sp.exists() and odb:
        raw = STATE / f"{kit.name}.placed_raw.json"
        rc = run_placed(kit, odb, raw, mem_gb)
        if rc == 0 and raw.exists():
            s = summarise_placed(kit, json.loads(raw.read_text()))
            s["rc"] = 0
            sp.write_text(json.dumps(s, indent=1))
            if s["legs_over"]:
                msgs.append(f"PLACED {s['legs_over']} legs > {CBC.REACH_UM_PER_HOP:.0f} um: " + "; ".join(
                    f"{a} -> {b} x{n} (max {w} um)" for a, b, n, w, _ex in s["pairs"][:4]))
            # the placement-geometry skew estimate is NOT posted: fitted 11-19 on 14 kits / 413 taps against the measured
            # OT_TAP_INSERTION skew_ps, R2 <= 0.07 and 2-3 of 14 kits in the right 60 / 100 ps band (leaf median 121 ps vs
            # col 37-52 ps at the same distance spread).  The measured CTS number (scan "cts" below) is posted instead.
        else:
            sp.write_text(json.dumps(dict(rc=rc)))
    sc = STATE / f"{kit.name}.cts.json"
    cts = sorted(Path(kit, "work/run/logs").glob("*/*/base/4_1_cts.log"))
    if not sc.exists() and cts:
        taps = {}
        for m in TAPLINE.finditer(cts[0].read_text(errors="replace")):
            taps[m.group(1)] = (int(m.group(2)), float(m.group(4)))
        big = {t: v for t, v in taps.items() if v[0] >= 100}
        if big:
            worst = max(big.items(), key=lambda kv: kv[1][1])
            over = sorted(t for t, v in big.items() if v[1] >= CBC.TAP_SKEW_FAIL_PS)
            sc.write_text(json.dumps(dict(worst_tap=worst[0], worst_ps=worst[1][1], taps=len(big), over_fail=over,
                                          over_pass=sorted(t for t, v in big.items() if v[1] >= CBC.TAP_SKEW_PASS_PS)), indent=1))
            if worst[1][1] >= CBC.TAP_SKEW_PASS_PS:
                msgs.append(f"CTS IN-TAP SKEW worst {worst[0]} {worst[1][1]:.0f} ps; {len(over)} of {len(big)} taps >= "
                            f"{CBC.TAP_SKEW_FAIL_PS:.0f} ps (< 60 ps: 58 of 111 kits closed; >= 100 ps: 0 of 23)")
    if msgs:
        print(f"KIT-SCAN {tn} ({kit.name}): " + " | ".join(msgs))
    if sf.exists() or sp.exists() or sc.exists():
        f = json.loads(sf.read_text()) if sf.exists() else {}
        p = json.loads(sp.read_text()) if sp.exists() else {}
        c = json.loads(sc.read_text()) if sc.exists() else {}
        return [dict(die=kit_die(kit), type=tn, kit=kit.name, fold=f.get("lost", 0), legs=p.get("legs_over"),
                     worst_pair=(p.get("pairs") or [[None, None, 0, 0]])[0][:4], skew=c.get("worst_ps"),
                     skew60=len(c.get("over_pass") or []), skew100=len(c.get("over_fail") or []))] if msgs else []
    return []


PENDING = STATE / "pending.jsonl"
LAST = STATE / "last_post"


def hourly_digest(rows, now=None):
    """one short line per die from the rows scanned since the last post"""
    by = collections.defaultdict(list)
    for r in rows:
        by[r["die"]].append(r)
    out = []
    for die, rs in sorted(by.items()):
        fold = [r for r in rs if r.get("fold")]
        legs = [r for r in rs if r.get("legs")]
        sk = [r for r in rs if (r.get("skew100") or 0) > 0]
        w = max(legs, key=lambda r: r["legs"], default=None)
        out.append(f"{die}: {len(rs)} kits; FOLD {len(fold)}" + (f" ({', '.join(sorted({r['type'] for r in fold})[:3])})" if fold else "")
                   + f"; legs>405 in {len(legs)}" + (f" (worst {w['type']} {w['legs']}: {w['worst_pair'][0]} -> {w['worst_pair'][1]} "
                                                     f"{w['worst_pair'][3]} um)" if w else "")
                   + f"; tap skew>=100 ps in {len(sk)}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kit", default="")
    ap.add_argument("--roots", default="")
    ap.add_argument("--max-age-h", type=float, default=12)
    ap.add_argument("--post", action="store_true")
    ap.add_argument("--mem-gb", type=int, default=14)
    a = ap.parse_args(argv)
    kits = [a.kit] if a.kit else []
    now = time.time()
    for root in [r for r in a.roots.split(",") if r]:
        for d in sorted(Path(root).glob("*/work/config.mk")):
            k = d.parent.parent
            if now - k.stat().st_mtime <= a.max_age_h * 3600:
                kits.append(str(k))
    STATE.mkdir(parents=True, exist_ok=True)
    with open(PENDING, "a") as fh:
        for k in kits:
            try:
                for r in scan_kit(k, a.post, a.mem_gb):
                    fh.write(json.dumps(r) + "\n")
            except Exception as e:  # noqa: BLE001 -- an estimator never stops the pass
                print(f"KIT-SCAN {k}: {type(e).__name__}: {e}")
    # COORD 11-19: stay light -- one short post per hour (per die line), from what was scanned since the last one
    last = float(LAST.read_text()) if LAST.exists() else 0.0
    if a.post and time.time() - last >= 3600 and PENDING.exists() and PENDING.stat().st_size:
        import socket
        rows = [json.loads(x) for x in PENDING.read_text().splitlines() if x.strip()]
        post(f"KIT-SCAN hourly [PRECHECK-1119 -> COORD, die owners] {socket.gethostname()}: " + " || ".join(hourly_digest(rows))
             + f". Estimator; detail {STATE}.")
        LAST.write_text(str(time.time()))
        PENDING.write_text("")
    return 0


if __name__ == "__main__":
    sys.exit(main())
