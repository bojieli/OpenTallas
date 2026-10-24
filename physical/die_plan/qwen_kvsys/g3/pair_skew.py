#!/usr/bin/env python3
"""Related launch/capture flop-pair clock skew WITH CPPR credit: summary, gate and session wrappers.

OWNER DECISION 2026-10-23: the clock CTS gate is the related launch/capture flop-pair skew with CPPR credit <= 80 ps at
TT and FF, for intra-partition pairs and seam pairs (pairs across neighbouring partitions).  Sign-off is
propagated-clock STA closing (setup TT, hold FF).  The max-min spread over (face) flops is REPORTED only, never a gate.

Measurement: tools/die_plan/pair_skew.tcl (sourced in an OpenSTA / OpenROAD session; writes the TSV this tool reads).
pair skew = effective capture clock arrival - launch clock arrival, CPPR credited (setup: Cmin + crpr - Lmax; hold:
Cmax - crpr - Lmin), worst path per register endpoint, reg->reg setup and hold checks only.

    pair_skew.py summarize TT.tsv [FF.tsv ...] [--seam-map map.json] [--parts-sep /] [--json out.json]
    pair_skew.py gate TT.tsv FF.tsv [--limit 80] [--seam-map ...] [--json out.json]     # exit 1 on FAIL
    pair_skew.py kit-tcl --odb /k/4_cts.odb --sdc /k/4_cts.sdc [--spef F] [--pair-skew /t/pair_skew.tcl] > s.tcl
    pair_skew.py die-tcl                                                         # the hook for gen_phys.sta_die_tcl

Classification: a pair is INTRA when launch and capture lie in the same top-level hierarchy instance (the first
path component before --parts-sep), SEAM otherwise.  A TSV whose header says "H scope kit" (kit-tcl wrapper) is one
partition: every pair is intra.  --seam-map JSON {instance: partition_label} merges instances into one partition label.
"""
import argparse
import json
import math
import sys
from pathlib import Path

LIMIT_PS = 80.0
CHECK = {"max": "setup", "min": "hold"}


def read_tsv(path):
    """{"header": {k: v}, "pairs": [(dly, launch, capture, skew, slack, crpr)], "ck": [(inst, ps, face)]}"""
    hdr, pairs, ck = {}, [], []
    for line in Path(path).read_text().splitlines():
        f = line.split("\t")
        if not f or not f[0]:
            continue
        if f[0] == "H" and len(f) >= 3:
            hdr[f[1]] = f[2]
        elif f[0] == "P" and len(f) >= 6:
            crpr = float(f[6]) if len(f) > 6 and f[6] not in ("", "NA") else None
            pairs.append((f[1], f[2], f[3], float(f[4]), float(f[5]) if f[5] not in ("", "NA") else None, crpr))
        elif f[0] == "C" and len(f) >= 3:
            ck.append((f[1], float(f[2]), len(f) > 3 and f[3] == "1"))
    return dict(header=hdr, pairs=pairs, ck=ck)


def top_of(inst, sep="/", seam_map=None):
    t = inst.split(sep, 1)[0] if sep in inst else "@top"
    return (seam_map or {}).get(t, t)


def pct(vals, q):
    """nearest-rank percentile (q in 0..100) of a non-empty list"""
    v = sorted(vals)
    return v[max(0, math.ceil(q / 100.0 * len(v)) - 1)]


def _stats(rows):
    if not rows:
        return None
    w = max(rows, key=lambda r: abs(r[3]))
    ab = [abs(r[3]) for r in rows]
    return dict(n=len(rows), worst_abs_ps=round(abs(w[3]), 2), worst_signed_ps=round(w[3], 2),
                p99_abs_ps=round(pct(ab, 99), 2), worst_launch=w[1], worst_capture=w[2])


def _spread(vals):
    if not vals:
        return None
    return dict(n=len(vals), min_ps=round(min(vals), 2), max_ps=round(max(vals), 2),
                spread_ps=round(max(vals) - min(vals), 2), p1_ps=round(pct(vals, 1), 2),
                p99_ps=round(pct(vals, 99), 2), p1_p99_ps=round(pct(vals, 99) - pct(vals, 1), 2))


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def summarize(data, sep="/", seam_map=None):
    """one corner: per class (intra / seam) and per check (setup / hold) count, worst |skew|, worst signed, p99 |skew|;
    per-seam (partition pair) worst; CK spread of all register clock pins and of the face flops (information only)."""
    hdr = data["header"]
    kit = hdr.get("scope") == "kit"
    cls = {"intra": {"setup": [], "hold": []}, "seam": {"setup": [], "hold": []}}
    seams = {}
    for r in data["pairs"]:
        chk = CHECK.get(r[0], r[0])
        a, b = ("@kit", "@kit") if kit else (top_of(r[1], sep, seam_map), top_of(r[2], sep, seam_map))
        c = "intra" if a == b else "seam"
        cls[c].setdefault(chk, []).append(r)
        if c == "seam":
            seams.setdefault("|".join(sorted((a, b))), []).append(r)
    out = dict(corner=hdr.get("corner"), scope="kit" if kit else "die",
               signoff={k: _num(hdr.get(k)) for k in ("wns_ps", "tns_ps", "whs_ps", "ths_ps")},
               classes={}, seams={}, verify={k: hdr[k] for k in ("verify_max", "verify_min") if k in hdr})
    for c, d in cls.items():
        st = {chk: _stats(rows) for chk, rows in d.items() if rows}
        if st:
            allr = [r for rows in d.values() for r in rows]
            st["all"] = _stats(allr)
            out["classes"][c] = st
    for k, rows in sorted(seams.items()):
        out["seams"][k] = _stats(rows)
    out["spread_all"] = _spread([x[1] for x in data["ck"]])
    out["spread_face"] = _spread([x[1] for x in data["ck"] if x[2]])
    return out


def gate(summaries, limit=LIMIT_PS):
    """PASS iff worst |pair skew| <= limit for every class present at every corner given; spread never counts.
    NO_DATA when no corner has a reg->reg pair."""
    fails, worst = [], {}
    any_pairs = False
    for s in summaries:
        cn = s.get("corner") or "?"
        for c, st in s["classes"].items():
            a = st["all"]
            any_pairs = True
            worst[f"{cn}_{c}"] = a["worst_abs_ps"]
            if a["worst_abs_ps"] > limit:
                fails.append(f"{cn} {c} pair skew {a['worst_signed_ps']:+.1f} ps ({a['worst_launch']} -> "
                             f"{a['worst_capture']}) > {limit:g}")
    verdict = "FAIL" if fails else ("PASS" if any_pairs else "NO_DATA")
    corners = [s.get("corner") for s in summaries]
    notes = [f"{c} not measured" for c in ("TT", "FF") if c not in corners]
    return dict(verdict=verdict, limit_ps=limit, worst_abs_ps=worst, fails=fails, notes=notes)


def one_line(summaries, g):
    parts = []
    for s in summaries:
        cs = []
        for c in ("intra", "seam"):
            st = s["classes"].get(c)
            if st:
                cs.append(f"{c} {st['all']['worst_abs_ps']:.1f}/p99 {st['all']['p99_abs_ps']:.1f}")
        sp = s.get("spread_face") or s.get("spread_all")
        so = s["signoff"]
        parts.append(f"{s.get('corner')}: " + ", ".join(cs or ["no pairs"])
                     + (f"; spread {sp['spread_ps']:.1f} (info)" if sp else "")
                     + f"; WNS {so.get('wns_ps')} WHS {so.get('whs_ps')}")
    return f"pair skew {g['verdict']} (limit {g['limit_ps']:g} ps, CPPR): " + " | ".join(parts)


# ------------------------------------------------------------------------------------------------ session wrappers
def kit_tcl(odb, sdc, spef=None, pair_skew="/t/pair_skew.tcl", platform="/OpenROAD-flow-scripts/flow/platforms/asap7"):
    """openroad session for one kit at env CORNER (TT|FF): RVT + LVT NLDM libs of the corner (no *FAKE* / *SRAM*),
    read_db + read_sdc, setRC, parasitics (SPEF, else GRT estimate when the odb has global routes, else placement),
    then pair_skew.tcl (env OT_PS_OUT, OT_PS_FACE, ...).  Scope kit: every pair is intra."""
    par = (f"read_spef {spef}" if spef else
           "if {[catch {estimate_parasitics -global_routing} e]} {\n"
           "  puts \"OT_PS_PARASITICS placement ($e)\"\n  estimate_parasitics -placement\n"
           "} else { puts \"OT_PS_PARASITICS global_routing\" }")
    return f"""# GENERATED by tools/die_plan/pair_skew.py kit-tcl: related flop-pair skew with CPPR (owner gate 10-23)
set C $::env(CORNER)
set P {platform}
foreach f [glob $P/lib/NLDM/*_RVT_${{C}}_*.lib* $P/lib/NLDM/*_LVT_${{C}}_*.lib*] {{
  if {{[string match *FAKE* $f] || [string match *SRAM* $f]}} continue
  read_liberty $f
}}
read_db {odb}
read_sdc {sdc}
source $P/setRC.tcl
{par}
set ::env(OT_PS_SCOPE) kit
source {pair_skew}
"""


DIE_HOOK = ('if {[info exists ::env(PAIRSKEW_OUT)]} { set ::env(OT_PS_OUT) $::env(PAIRSKEW_OUT); '
            'source [file join [file dirname [info script]] pair_skew.tcl] }')


def die_tcl():
    """the line gen_phys.sta_die_tcl appends LAST (after the report_checks: pair_skew.tcl zeroes the clock
    uncertainties), with pair_skew.tcl copied into the die dir (sta runs with -w /work)."""
    return DIE_HOOK + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for n in ("summarize", "gate"):
        s = sub.add_parser(n)
        s.add_argument("tsv", nargs="+")
        s.add_argument("--parts-sep", default="/")
        s.add_argument("--seam-map")
        s.add_argument("--limit", type=float, default=LIMIT_PS)
        s.add_argument("--json")
    k = sub.add_parser("kit-tcl")
    k.add_argument("--odb", required=True)
    k.add_argument("--sdc", required=True)
    k.add_argument("--spef")
    k.add_argument("--pair-skew", default="/t/pair_skew.tcl")
    k.add_argument("--platform", default="/OpenROAD-flow-scripts/flow/platforms/asap7")
    sub.add_parser("die-tcl")
    a = ap.parse_args(argv)
    if a.cmd == "kit-tcl":
        sys.stdout.write(kit_tcl(a.odb, a.sdc, a.spef, a.pair_skew, a.platform))
        return 0
    if a.cmd == "die-tcl":
        sys.stdout.write(die_tcl())
        return 0
    sm = json.loads(Path(a.seam_map).read_text()) if a.seam_map else None
    sums = [summarize(read_tsv(t), a.parts_sep, sm) for t in a.tsv]
    g = gate(sums, a.limit)
    res = dict(summaries=sums, gate=g, files=a.tsv)
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1) + "\n")
    if a.cmd == "summarize":
        for s in sums:
            print(f"== {s['corner']} ({s['scope']}) signoff {s['signoff']}")
            for c, st in s["classes"].items():
                for chk, x in st.items():
                    print(f"  {c:5s} {chk:5s} n={x['n']} worst|.|={x['worst_abs_ps']} signed={x['worst_signed_ps']} "
                          f"p99={x['p99_abs_ps']}  {x['worst_launch']} -> {x['worst_capture']}")
            for k2, x in s["seams"].items():
                print(f"  seam {k2}: n={x['n']} worst {x['worst_signed_ps']} p99 {x['p99_abs_ps']}")
            for nm in ("spread_all", "spread_face"):
                if s[nm]:
                    print(f"  {nm} (info): {s[nm]}")
            if s["verify"]:
                print(f"  verify (n, max |diff| ps): {s['verify']}")
    print(one_line(sums, g))
    return 1 if (a.cmd == "gate" and g["verdict"] == "FAIL") else 0


if __name__ == "__main__":
    sys.exit(main())
