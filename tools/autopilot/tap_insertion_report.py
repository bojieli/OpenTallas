#!/usr/bin/env python3 -I
"""tap_insertion_report.py -- WAVE-FLOW-R2 11-17 (COORD lever 6): per-die summary of the OT_TAP_INSERTION lines kits print after CTS (die_plan/tap_insertion.tcl).

    OT_TAP_INSERTION tap=<name> sinks=<n> ins_ps=<max> skew_ps=<n>

Advisory data for deciding which oversized taps to split: measured insertion, not sink counts.  --update reads the CTS logs of the autopilot jobs' kits (one ssh per host,
each kit's newest 4_1_cts.log) and writes autopilot/tap_insertion.json (per die: kits, taps, the oversized ones, insertion / skew distribution); failure_breakdown prints it.

    tap_insertion_report.py --update [--state STATE.json] [--out tap_insertion.json]     scan + write
    tap_insertion_report.py --print [--out tap_insertion.json]                             one summary line per die
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

LINE_RE = re.compile(r"^OT_TAP_INSERTION tap=(\S+) sinks=(\d+) ins_ps=(-?[0-9.]+) skew_ps=(-?[0-9.]+)\s*$")
OVERSIZED_SINKS = 1650                      # the oversized-tap size COORD quotes (KV 47 of 52 taps over 1,650 sinks)
LOG_GLOB = "run/logs/asap7/*/base/4_1_cts.log"
MARK = "@@KIT "


def parse_lines(text):
    """-> [(tap, sinks, ins_ps, skew_ps)] from kit log text"""
    out = []
    for ln in (text or "").splitlines():
        m = LINE_RE.match(ln.strip())
        if m:
            out.append((m.group(1), int(m.group(2)), float(m.group(3)), float(m.group(4))))
    return out


def kits_from_state(state):
    """newest job per (die, type): [(die, type, host, kit path)]; kit = 'host:/abs/path'"""
    best = {}
    for j in (state.get("jobs") or {}).values():
        kit = str(j.get("kit") or "")
        if ":" not in kit or not kit.split(":", 1)[1].startswith("/") or not j.get("die") or not j.get("type"):
            continue
        t = float(j.get("finished") or j.get("updated") or j.get("started") or 0)
        k = (j["die"], j["type"])
        if k not in best or t > best[k][0]:
            best[k] = (t, kit)
    return sorted((d, ty, kit.split(":", 1)[0], kit.split(":", 1)[1]) for (d, ty), (t, kit) in best.items())


def scan_host(host, kits, run=None):
    """one ssh per host: print the OT_TAP_INSERTION lines of each kit's CTS log, each block headed by '@@KIT <path>'.  -> {kit: text}"""
    script = "for k in " + " ".join(shlex.quote(k) for k in kits) + "; do f=$(ls -t $k/" + LOG_GLOB + " 2>/dev/null | head -1); " \
             "[ -n \"$f\" ] && grep -q '^OT_TAP_INSERTION tap=' \"$f\" 2>/dev/null && { echo \"" + MARK + "$k\"; grep -h '^OT_TAP_INSERTION tap=' \"$f\"; }; done"
    if run is None:
        argv = ["bash", "-c", script] if host in ("localhost", "hub", "") else ["ssh", "-n", "-o", "ControlPath=none", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", host, script]
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=300)
        except (OSError, subprocess.TimeoutExpired):
            return {}
        out = r.stdout
    else:
        out = run(host, script)
    res, cur = {}, None
    for ln in out.splitlines():
        if ln.startswith(MARK):
            cur = ln[len(MARK):].strip()
            res[cur] = []
        elif cur is not None:
            res[cur].append(ln)
    return {k: "\n".join(v) for k, v in res.items()}


def summarize(rows):
    """rows: [(die, type, tap, sinks, ins_ps, skew_ps)] -> {die: summary}"""
    out = {}
    for die in sorted({r[0] for r in rows}):
        rs = [r for r in rows if r[0] == die]
        ins = sorted(r[4] for r in rs)
        skew = sorted(r[5] for r in rs)
        big = [r for r in rs if r[3] > OVERSIZED_SINKS]
        pct = lambda v, p: v[min(len(v) - 1, int(p * len(v)))] if v else None
        out[die] = dict(types=len({r[1] for r in rs}), taps=len(rs), oversized_taps=len(big), oversized_sinks=OVERSIZED_SINKS,
                        ins_ps_max=ins[-1], ins_ps_p50=pct(ins, 0.5), ins_ps_p90=pct(ins, 0.9), skew_ps_max=skew[-1], skew_ps_p90=pct(skew, 0.9),
                        oversized_ins_ps_max=max((r[4] for r in big), default=None), oversized_skew_ps_max=max((r[5] for r in big), default=None),
                        worst=[dict(type=r[1], tap=r[2], sinks=r[3], ins_ps=r[4], skew_ps=r[5]) for r in sorted(rs, key=lambda r: -r[5])[:5]])
    return out


def update(state, out_path, scan=scan_host, now=time.time):
    kits = kits_from_state(state)
    by_host = {}
    for die, ty, host, path in kits:
        by_host.setdefault(host, []).append((die, ty, path))
    rows = []
    for host, items in sorted(by_host.items()):
        got = scan(host, [p for _, _, p in items])
        for die, ty, path in items:
            for tap, sinks, ins, skew in parse_lines(got.get(path, "")):
                rows.append((die, ty, tap, sinks, ins, skew))
    doc = dict(time=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now())), kits_scanned=len(kits), dies=summarize(rows),
               rule="advisory: measured per-tap insertion after CTS (OT_TAP_INSERTION), not a gate")
    Path(out_path).write_text(json.dumps(doc, indent=1, sort_keys=True))
    return doc


def lines(doc):
    """one TOOLS-style line per die for failure_breakdown"""
    out = []
    for die, s in sorted((doc.get("dies") or {}).items()):
        out.append(f"TAP-INSERTION {die}: {s['taps']} taps in {s['types']} types, {s['oversized_taps']} over {s['oversized_sinks']} sinks; insertion max {s['ins_ps_max']:.0f} ps "
                   f"(p50 {s['ins_ps_p50']:.0f}, p90 {s['ins_ps_p90']:.0f}), skew max {s['skew_ps_max']:.0f} ps; oversized taps: ins max "
                   + ("-" if s["oversized_ins_ps_max"] is None else f"{s['oversized_ins_ps_max']:.0f}") + " ps, skew max "
                   + ("-" if s["oversized_skew_ps_max"] is None else f"{s['oversized_skew_ps_max']:.0f}") + " ps")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--update", action="store_true")
    ap.add_argument("--print", dest="show", action="store_true")
    ap.add_argument("--state", default=os.path.expanduser("~/coord/autopilot/state.json"))
    ap.add_argument("--out", default=os.path.expanduser("~/coord/autopilot/tap_insertion.json"))
    a = ap.parse_args(argv)
    if a.update:
        doc = update(json.loads(Path(a.state).read_text()), a.out)
    else:
        doc = json.loads(Path(a.out).read_text())
    if a.show or a.update:
        print("\n".join(lines(doc)) or "TAP-INSERTION: no kit has printed OT_TAP_INSERTION yet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
