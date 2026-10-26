#!/usr/bin/env python3
"""Related-pair die STA with the real (routed) die clock -- METHODOLOGY 12.4a v4.3 freeze-gate form.

    die_sta_related.py PROOF_DIR --plan die_plan.json --out OUT [--corner TT --corner FF]
                       [--clock-tool WT/tools/die_plan]   # re-run the CLOCK-128 fold report on a COPY if needed

PROOF_DIR is a die clock proof (die_clock_mesh.py build/post/report) holding tap_arrivals_<C>.json, the CLOCK-128 fold
export: per tap port the PROPAGATED late/early arrival on routed RC + the late-early range of every last-common tree
node (die root 'h', region roots).  When the files are missing and --clock-tool is given, PROOF_DIR is copied to
OUT/proof_copy and `die_clock_mesh.py report` runs on the copy (caller's env: PYTHONPATH, OT_PROOF_* as the proof was
built); the proof dir itself is never written.

Pair set = COMPLETE (NUMBER-CHECK 10-26 06:47), no spatial pruning:
  intra   every ordered tap pair (a != b) inside one partition
  seam    every (src-part tap, dst-part tap) cross product of each port-connected partition pair, both in one clock region
  landed  the same cross products when the two partitions sit in different clock regions (landed / forwarded hops)
Ports touching the die IO or a partition without taps are counted as uncovered (die links leave the die: PHY timing).

CPPR (12.4b): credit = min(range at the last common tree node, launch late-early, capture late-early); the last
common node is the region root for same-region pairs, the die root 'h' otherwise.  Mesh-node credit is never taken.

Block interface model per partition (pin register under the tap): core clock latency + clk->q / setup / hold.
  'kit'             a partition kit JSON (--kit part_or_type=kit.json with core_latency_ps{TT,FF}, clkq_max/min, setup, hold)
  'declared-budget' 12.3 common core latency (plan clock.common_latency_ps, default 250 TT; the same value at FF unless
                    --core-latency-ff is given) on both sides of the pair, plus pin-register arcs characterised here by
                    OpenSTA on the ASAP7 DFFHQNx1 liberty at the corner's max tap slew.  The common latency cancels in
                    every pair; --core-tol-ps (default 20 = 12.8b +-20 TT) is reported as a sensitivity (launch late +tol,
                    capture early -tol), never folded into the gate number.
Data path per pair = register to register, zero logic (the structural hold worst case, 12.4a); setup adds the declared
seam wire (--seam-wire-um at --wire-ff-per-um on the launch Q net), hold uses no wire.  Intra-partition setup without a
kit is therefore "slack left for logic", not a path slack.

  setup slack = T - unc_setup - (L_late + clkq_max + wire) + (C_early - setup) + credit
  hold  slack = (L_early + clkq_min) - (C_late + hold) - unc_hold + credit
Landed hops are timed as the plan defines them (die_clock_mesh report): the region-to-region clock damage against the
landing window (--landing-window-ps, default T/2) -> margin = window - damage; their single-cycle slacks are INFO.

Output OUT/die_sta_related.json (+ worst pairs per class); prints one line per class and corner.
"""
import argparse
import itertools
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

PERIOD_PS = 833.333
UNC_SETUP_PS = 60.0
UNC_HOLD_PS = 25.0
SIGNOFF = {"TT": "setup", "FF": "hold"}
IMAGE = os.environ.get("OT_ORFS_IMAGE", "openroad/orfs:asap7lock")
REG_CELL = "DFFHQNx1_ASAP7_75t_R"
DIE_PART = "die"

REG_TCL = r"""
set C $::env(C)
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_${C}_nldm_220123.lib
read_verilog /w/reg.v
link_design t
create_clock -name clk -period %(period)s [get_ports clk]
set_clock_transition $::env(SLEW) [get_clocks clk]
set_input_delay 0 -clock clk [get_ports d]
set_output_delay 0 -clock clk [get_ports q]
set_input_transition 20 [get_ports d]
foreach {tag ld} [list w $::env(LOAD) n 0] {
  set_load $ld [get_nets n1]
  foreach pd {max min} {
    puts "REGCHAR $tag $pd"
    report_checks -from [get_pins a/CLK] -to [get_pins b/D] -path_delay $pd -digits 3
  }
}
"""
REG_V = """module t(clk, d, q);
input clk; input d; output q; wire n1;
%(c)s a (.CLK(clk), .D(d), .QN(n1));
%(c)s b (.CLK(clk), .D(n1), .QN(q));
endmodule
"""


def characterise(out, corner, slew, load_ff, mem="4g"):
    """pin-register arcs from OpenSTA on the ASAP7 liberty: clk->q max (with the seam wire load) / min (no wire),
    setup, hold.  Cached in OUT/regchar/<corner>.json."""
    d = out / "regchar"
    d.mkdir(parents=True, exist_ok=True)
    cache = d / f"{corner}.json"
    key = dict(corner=corner, slew_ps=round(slew, 3), load_ff=round(load_ff, 4), cell=REG_CELL, image=IMAGE)
    if cache.exists():
        c = json.loads(cache.read_text())
        if c.get("key") == key:
            return c
    (d / "reg.v").write_text(REG_V % dict(c=REG_CELL))
    (d / "reg.tcl").write_text(REG_TCL % dict(period=PERIOD_PS))
    dk = ["docker"] if os.access("/var/run/docker.sock", os.W_OK) else ["sudo", "docker"]
    cmd = dk + ["run", "--rm", "--memory", mem, "-e", f"C={corner}", "-e", f"SLEW={slew:.3f}", "-e", f"LOAD={load_ff:.4f}",
                "-v", f"{d.resolve()}:/w", IMAGE, "bash", "-c",
                "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; "
                "S=$(ls /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/sta 2>/dev/null || which sta); "
                "$S -no_splash -exit /w/reg.tcl"]
    txt = subprocess.run(cmd, check=True, capture_output=True, text=True).stdout
    (d / f"{corner}.log").write_text(txt)
    res = {}
    for blk in txt.split("REGCHAR ")[1:]:
        tag, pd = blk.split()[:2]
        arr = float(re.search(r"([-\d.]+)\s+data arrival time", blk).group(1))
        lib = float(re.search(r"([-\d.]+)\s+[-\d.]+\s+library (setup|hold) time", blk).group(1))
        res[f"{tag}_{pd}"] = dict(clkq_ps=arr, lib_ps=lib)
    c = dict(key=key, clkq_max_wire_ps=res["w_max"]["clkq_ps"], clkq_min_nowire_ps=res["n_min"]["clkq_ps"],
             setup_ps=-res["w_max"]["lib_ps"], hold_ps=res["n_min"]["lib_ps"],
             note="OpenSTA %s, ideal clock at max tap slew; setup = -(library setup term), hold = library hold" % REG_CELL)
    cache.write_text(json.dumps(c, indent=1) + "\n")
    return c


def load_taps(d, corner):
    t = json.loads((d / f"tap_arrivals_{corner}.json").read_text())
    taps = {r["port"]: r for r in t["taps"]}
    return t, taps


def credit(rng, node, la, ea, lc, ec):
    c = node
    while c not in rng and len(c) > 1:
        c = c[:-1]
    return min(max(0.0, rng.get(c, 0.0)), max(0.0, la - ea), max(0.0, lc - ec))


def build_pairs(plan, taps):
    """complete pair sets from the plan ports and the tap table (one corner's rows; ports are corner independent)."""
    by_part = defaultdict(list)
    for p, r in taps.items():
        by_part[r["part"]].append(p)
    for v in by_part.values():
        v.sort()
    intra, seam, landed, straddle = [], [], [], []
    for part, tl in by_part.items():
        for a, b in itertools.permutations(tl, 2):
            (intra if taps[a]["cppr_node"] == taps[b]["cppr_node"] else straddle).append((a, b, part))
    conn, uncovered = defaultdict(int), defaultdict(int)
    for pr in plan["ports"]:
        s, t = pr["src"]["part"], pr["dst"]["part"]
        if s == t:
            continue
        if s not in by_part or t not in by_part:
            uncovered["die_io" if DIE_PART in (s, t) else "no_taps"] += int(pr.get("width", 1))
            continue
        conn[(s, t)] += int(pr.get("width", 1))
    for (s, t), bits in conn.items():
        for a in by_part[s]:
            for b in by_part[t]:
                (seam if taps[a]["cppr_node"] == taps[b]["cppr_node"] else landed).append((a, b, f"{s}->{t}"))
    return dict(intra=intra, intra_cross_region=straddle, seam=seam, landed=landed), dict(
        partitions_with_taps=len(by_part), connected_part_pairs=len(conn), uncovered_bits=dict(uncovered))


def nearest_pairs(d, plan_path, tool, taps):
    """INFO subset (decision-5 seam rule): per port bit the src-part tap / dst-part tap nearest the pin, i.e. the tap the
    pin register sits under -- the clock tool's own DC.seam_pairs.  Needs the tool dir importable (--clock-tool)."""
    if tool:
        sys.path.insert(0, str(Path(tool)))
    try:
        import die_clock as DC
        import schema as S
    except Exception as e:  # noqa: BLE001
        print(f"nearest-tap INFO classes skipped ({e})", file=sys.stderr)
        return {}
    M = json.loads((d / "mesh.json").read_text())
    tb = defaultdict(list)
    for t in M["taps"]:
        if t["port"] in taps:
            tb[t["part"]].append(dict(port=t["port"], part=t["part"], xy=t["xy"]))
    seam, landed = [], []
    for (a_, b_, pid) in DC.seam_pairs(S.Plan(S.load(plan_path)), tb):
        (seam if taps[a_]["cppr_node"] == taps[b_]["cppr_node"] else landed).append((a_, b_, pid))
    return {"seam_nearest_INFO": seam, "landed_nearest_INFO": landed}


def time_class(pairs, taps, rng, reg, lat_tol, period, unc_s, unc_h, landed=False, window=None):
    ws, wh, sk, rows = None, None, 0.0, []
    nneg_s = nneg_h = 0
    mds = mdh = float('-inf')
    for a, b, tag in pairs:
        A, B = taps[a], taps[b]
        la, ea, lc, ec = A["late_ps"], A["early_ps"], B["late_ps"], B["early_ps"]
        node = A["cppr_node"] if A["cppr_node"] == B["cppr_node"] else "h"
        cr = credit(rng, node, la, ea, lc, ec)
        dmg_s, dmg_h = la - ec - cr, lc - ea - cr
        s = period - unc_s - (la + reg["clkq_max_wire_ps"]) + (ec - reg["setup_ps"]) + cr
        h = (ea + reg["clkq_min_nowire_ps"]) - (lc + reg["hold_ps"]) - unc_h + cr
        nneg_s += s < 0
        nneg_h += h < 0
        sk = max(sk, dmg_s, dmg_h)
        if ws is None or s < ws[0]:
            ws = (s, a, b, tag, dmg_s, cr)
        if wh is None or h < wh[0]:
            wh = (h, a, b, tag, dmg_h, cr)
        rows.append((max(dmg_s, dmg_h), a, b))
        mds, mdh = max(mds, dmg_s), max(mdh, dmg_h)
    if ws is None:
        return dict(pairs=0)
    out = dict(pairs=len(pairs),
               worst_setup_slack_ps=round(ws[0], 2), setup_neg_pairs=int(nneg_s),
               worst_setup=dict(launch=ws[1], capture=ws[2], where=ws[3], clock_damage_ps=round(ws[4], 2),
                                cppr_ps=round(ws[5], 2)),
               worst_hold_slack_ps=round(wh[0], 2), hold_neg_pairs=int(nneg_h),
               worst_hold=dict(launch=wh[1], capture=wh[2], where=wh[3], clock_damage_ps=round(wh[4], 2),
                               cppr_ps=round(wh[5], 2)),
               skew_diag_max_ps=round(sk, 2), skew_diag_over_80=sum(1 for r in rows if r[0] > 80.0),
               sens_core_tol=dict(tol_ps=lat_tol, worst_setup_slack_ps=round(ws[0] - 2 * lat_tol, 2),
                                  worst_hold_slack_ps=round(wh[0] - 2 * lat_tol, 2)),
               worst_skew=[[round(v, 2), a, b] for v, a, b in sorted(rows, reverse=True)[:5]])
    if landed:
        out["plan_landing"] = dict(window_ps=round(window, 2), setup_margin_ps=round(window - mds, 2),
                                   hold_margin_ps=round(window - mdh, 2),
                                   damage_max_ps=round(max(r[0] for r in rows), 2),
                                   verdict="PASS" if max(r[0] for r in rows) <= window else "FAIL",
                                   note="plan-defined landed/forwarded hop: region-to-region clock damage vs landing "
                                        "window; single-cycle slacks above are INFO for landed pairs")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("proof")
    ap.add_argument("--plan", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--corner", action="append")
    ap.add_argument("--clock-tool", help="tools/die_plan dir holding die_clock_mesh.py (fold report on a copy)")
    ap.add_argument("--period-ps", type=float, default=PERIOD_PS)
    ap.add_argument("--core-latency-ff", type=float, help="declared FF core latency (default = TT value, cancels)")
    ap.add_argument("--core-tol-ps", type=float, default=20.0)
    ap.add_argument("--seam-wire-um", type=float, default=40.0)
    ap.add_argument("--wire-ff-per-um", type=float, default=0.15)
    ap.add_argument("--landing-window-ps", type=float)
    ap.add_argument("--kit", action="append", default=[], help="part_or_type=kit.json (interface model); none yet for QC")
    a = ap.parse_args(argv)
    corners = a.corner or ["TT", "FF"]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    d = Path(a.proof)
    if not all((d / f"tap_arrivals_{c}.json").exists() for c in corners):
        if not a.clock_tool:
            raise SystemExit(f"{d}: no tap_arrivals_<C>.json; pass --clock-tool to run the fold report on a copy")
        cp = out / "proof_copy"
        if cp.exists():
            shutil.rmtree(cp)
        shutil.copytree(d, cp, symlinks=True)
        r = subprocess.run([sys.executable, str(Path(a.clock_tool) / "die_clock_mesh.py"), "report", str(cp),
                            "--plan", a.plan], capture_output=True, text=True)
        (out / "fold_report.log").write_text(r.stdout + r.stderr)
        if r.returncode:
            raise SystemExit(f"fold report failed, see {out / 'fold_report.log'}")
        d = cp
    plan = json.loads(Path(a.plan).read_text())
    if a.kit:
        raise SystemExit("kit interface models: not implemented (no QC partition kit exists yet); add the reader here")
    period = a.period_ps
    window = a.landing_window_ps if a.landing_window_ps else period / 2
    lat_tt = float(plan.get("clock", {}).get("common_latency_ps", 250.0))
    lat = dict(TT=lat_tt, FF=a.core_latency_ff if a.core_latency_ff is not None else lat_tt)
    res = dict(proof=str(Path(a.proof).resolve()), timed_dir=str(d.resolve()), plan=str(Path(a.plan).resolve()),
               period_ps=period, unc_setup_ps=UNC_SETUP_PS, unc_hold_ps=UNC_HOLD_PS, gate="METHODOLOGY 12.4a v4.3: TT setup "
               ">= 0 and FF hold >= 0 on every related pair; CPPR at last common tree node (12.4b); skew = DIAGNOSTIC",
               block_model=dict(label="declared-budget", core_latency_ps=lat, cancels="same declared latency both sides",
                                core_tol_sensitivity_ps=a.core_tol_ps, register=REG_CELL,
                                seam_wire=dict(um=a.seam_wire_um, ff_per_um=a.wire_ff_per_um, applied="setup only"),
                                kits_found=0),
               corners={})
    cov = None
    for c in corners:
        meta, taps = load_taps(d, c)
        rng = meta["cppr_node_range_ps"]
        slew = max(r["slew_ps"] for r in taps.values())
        reg = characterise(out, c, slew, a.seam_wire_um * a.wire_ff_per_um)
        pairs, cov = build_pairs(plan, taps)
        pairs.update(nearest_pairs(d, a.plan, a.clock_tool, taps))
        cr = dict(basis=meta.get("basis"), tap_slew_max_ps=round(slew, 2), register=reg, classes={})
        for k, pl in pairs.items():
            cr["classes"][k] = time_class(pl, taps, rng, reg, a.core_tol_ps, period, UNC_SETUP_PS, UNC_HOLD_PS,
                                          landed=k.startswith("landed"), window=window)
            cr["classes"][k]["label"] = "declared-budget" + (" / INFO subset" if k.endswith("INFO") else "")
        res["corners"][c] = cr
    res["coverage"] = cov
    gate = {}
    for k in ("intra", "seam"):
        s = res["corners"].get("TT", {}).get("classes", {}).get(k, {})
        h = res["corners"].get("FF", {}).get("classes", {}).get(k, {})
        gate[k] = dict(tt_setup_ps=s.get("worst_setup_slack_ps"), ff_hold_ps=h.get("worst_hold_slack_ps"),
                       verdict="PASS" if (s.get("worst_setup_slack_ps", -1) >= 0 and h.get("worst_hold_slack_ps", -1) >= 0)
                       else "FAIL")
    lt = res["corners"].get("TT", {}).get("classes", {}).get("landed", {}).get("plan_landing", {})
    lf = res["corners"].get("FF", {}).get("classes", {}).get("landed", {}).get("plan_landing", {})
    gate["landed"] = dict(tt_setup_margin_ps=lt.get("setup_margin_ps"), ff_hold_margin_ps=lf.get("hold_margin_ps"),
                          verdict="PASS" if lt.get("verdict") == "PASS" and lf.get("verdict") == "PASS" else "FAIL")
    res["summary"] = dict(gate, status="UNCHECKED (NUMBER-CHECK pending)", label="declared-budget (no QC kit)")
    (out / "die_sta_related.json").write_text(json.dumps(res, indent=1) + "\n")
    for c, cr in res["corners"].items():
        for k, v in cr["classes"].items():
            if v.get("pairs"):
                print(f"{d.name} {c} {k:18s} pairs {v['pairs']:7d} setup {v['worst_setup_slack_ps']:8.2f} "
                      f"(neg {v['setup_neg_pairs']}) hold {v['worst_hold_slack_ps']:8.2f} (neg {v['hold_neg_pairs']}) "
                      f"skew {v['skew_diag_max_ps']:7.2f}" + (f" landing {v['plan_landing']}" if "plan_landing" in v else ""))
    print("SUMMARY", json.dumps(res["summary"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
