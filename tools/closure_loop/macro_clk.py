#!/usr/bin/env python3
"""MACRO-CLK check (macro-clk-1010, 2026-10-10): SRAM-macro clock distribution after CTS.

Failure class (ds-1010 s81b-coll_lane_ww lcrph / lcrpw / lcr0ctl, HBM SM tile_eg g363): TritonCTS builds the macro
clock sinks as their own tree; with its default macro clustering the H-tree stops with NO leaf buffers and 10 SRAM
clock pins hang on a few long nets: macro clk slew 165-260 ps, macro clock ~60 ps after the register tree, SRAM
wd_in / addr hold -65..-175 ps that hold repair cannot converge on (EARLY_FAIL_HOLD at CTS).

Two sources, both cheap:
  1. the CTS log (TritonCTS CTS-0098..0102 per clock net; a net X with a sibling X_regs is X's MACRO tree) and the
     wrapper's OT_MACRO_CTS line (physical/common_flow/macro_cts_cluster.tcl: was macro clustering on?);
  2. the calibrate stage's calib.json "macro_clk" verdict (ck_insertion.py: per macro clock pin slew and FF lateness).
signature() says whether a job shows the single-shallow-leaf macro clock, and whether its CTS already had clustering.
The closure loop flags it after CTS (calibration ingest) and auto-react class f requeues a hold-stalled job whose CTS
ran without the clustering default (the default now reaches every snapshot through hold_corners_patch.py).
"""
import re

LOG_GREP = r"CTS-009[89]|CTS-010[0-2]|OT_MACRO_CTS|clock_tree_synthesis"
SHALLOW_MIN_SINKS = 3        # 3+ macro sinks on 0 leaf buffers, or more than 2 per leaf (the default clusters 4)
SHALLOW_MIN_WIRE_UM = 150.0  # average sink wire of a leaf-less macro tree (ds-1010 lane: 383-437 um)


def scan_cmd(run):
    """remote shell: every CTS log of a job run dir, headed '==== <path>', grepped to the CTS tree summary lines"""
    return (f"for f in $(find {run} -path '*/src' -prune -o -name '4_1_cts*.log' -print 2>/dev/null | sort); do "
            f"echo \"==== $f\"; grep -E '{LOG_GREP}' \"$f\" | head -400; done")


def parse_cts_logs(text):
    """[{log, trees: {net: {sinks, leaf, wire, depth}}, macro_nets: [...], clustered: bool|None, cts_args}]"""
    out, cur, net = [], None, None
    for line in text.splitlines():
        if line.startswith("==== "):
            cur = dict(log=line[5:].strip(), trees={}, clustered=None, cts_args=None)
            out.append(cur)
            net = None
            continue
        if cur is None:
            continue
        m = re.search(r'CTS-0098\]\s+Clock net "([^"]+)"', line)
        if m:
            net = m.group(1)
            cur["trees"][net] = {}
            continue
        if net is not None:
            for code, key, rx in (("0099", "sinks", r"Sinks\s+(\d+)"), ("0100", "leaf", r"Leaf buffers\s+(\d+)"),
                                  ("0101", "wire", r"Average sink wire length\s+([\d.]+)"),
                                  ("0102", "depth", r"Path depth\s+(\d+)\s*-\s*(\d+)")):
                if f"CTS-{code}]" in line:
                    mm = re.search(rx, line)
                    if mm:
                        cur["trees"][net][key] = int(mm.group(2)) if key == "depth" else \
                            (float(mm.group(1)) if key == "wire" else int(mm.group(1)))
        if "OT_MACRO_CTS" in line:
            if re.search(r"OT_MACRO_CTS \d+ clocked macros|OT_MACRO_CTS kept", line):
                cur["clustered"] = True
            elif cur["clustered"] is None and re.search(r"OT_MACRO_CTS (off|skipped)", line):
                cur["clustered"] = False
        m = re.match(r"\s*(?:log_cmd\s+)?clock_tree_synthesis\s+(.*)$", line)
        if m and not line.lstrip().startswith("Took"):
            cur["cts_args"] = m.group(1).strip()
            if "-macro_clustering_size" in cur["cts_args"]:
                cur["clustered"] = True
    for c in out:
        c["macro_nets"] = sorted(n for n in c["trees"] if f"{n}_regs" in c["trees"])
        if c["clustered"] is None and c["cts_args"] is not None:
            c["clustered"] = False
    return out


def shallow_trees(cts):
    """the under-buffered macro trees of one parsed log: [(net, sinks, leaf buffers, avg sink wire)]"""
    res = []
    for n in cts["macro_nets"]:
        t = cts["trees"][n]
        # leaf-less, or more than 2 macros per leaf buffer (TritonCTS default: up to 4 per cluster, diameter = region)
        if t.get("sinks", 0) >= SHALLOW_MIN_SINKS and t.get("sinks", 0) > 2 * t.get("leaf", 0) \
                and t.get("wire", 0.0) >= SHALLOW_MIN_WIRE_UM:
            res.append((n, t["sinks"], t.get("leaf", 0), t.get("wire", 0.0)))
    return res


def signature(logs, calib_macro=None):
    """{"hit": bool, "clustered": bool|None, "why": str, "logs": n} for one job.

    hit: a CTS log shows a leaf-less macro tree, or the calibrate measurement flagged a macro clock-pin outlier.
    clustered: True when every CTS log with macro trees already ran the clustering default (a hit then is structural,
    not this flow defect); None when no log said."""
    why, hit, cl = [], False, []
    for c in logs:
        if c["macro_nets"]:
            cl.append(c["clustered"])
        sh = shallow_trees(c)
        if sh:
            hit = True
            tag = c["log"].rsplit("/", 1)[-1]
            why.append(f"{tag}: " + ", ".join(f"{n} {s} macros on {lf} leaf buffers ({w:.0f} um avg wire)"
                                              for n, s, lf, w in sh[:3]))
    if calib_macro and calib_macro.get("flag"):
        hit = True
        o = calib_macro.get("outliers") or []
        why.append(f"calibrate: {len(o)}/{calib_macro.get('n')} macro clock pins outliers ({o[0]['why'] if o else ''})")
    clustered = None if not cl or any(x is None for x in cl) else all(cl)
    return dict(hit=hit, clustered=clustered, why="; ".join(why)[:400], logs=len(logs))


def calib_flag_text(calib_macro):
    """one event line for a calibrate macro_clk verdict, or None when clean / not measured"""
    if not calib_macro or not calib_macro.get("flag"):
        return None
    o = calib_macro["outliers"]
    return (f"MACRO-CLK flag after CTS: {len(o)}/{calib_macro['n']} macro clock pins out of bounds (slew > "
            f"{calib_macro['slew_ps']:.0f} ps or FF > {calib_macro['late_ps']:.0f} ps after the register mean): "
            + "; ".join(f"{x['pin']} {x['why']}" for x in o[:3]))[:500]
