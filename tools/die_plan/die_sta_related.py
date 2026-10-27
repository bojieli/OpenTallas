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
KIT HOLD CONTRACT (INFRA-FIRST-R3b, always reported next to the zero-logic numbers): what the plan-declared kit SDC
already guarantees, so the die only has to deliver its tap arrivals inside the declared window.
  seam   receiver input min delay in_min (legacy -insertion_tol, or clock.seam_hold) + sender output min out_min
         (gen_phys.sdc / seam_hold): the two kit checks sum to   die seam hold slack >= W_seam - damage_hold,
         W_seam = seam_hold.seam_ps if declared, else insertion_tol_ps - HOLD_OUT_MIN (0)  (gen_phys.seam_hold).
  intra  die intra hold slack >= W_intra - damage_hold, W_intra = the plan's clock.tap_window.window_ps (gen_phys
         emits set_clock_latency -source -early -W / -late 0 on every tap port: the kit times cross-tap pairs with the
         full W, same-tap pairs keep CRPR), else 0 (every tap on ONE ideal clock guarantees nothing).
         --intra-window-ps = labelled WHAT-IF override.
  The bound is exact for a kit pair signed with zero slack and conservative otherwise; it never uses kit numbers.
Landed hops are timed as the plan defines them (die_clock_mesh report): the region-to-region clock damage against the
landing window (--landing-window-ps, default T/2) -> margin = window - damage; their single-cycle slacks are INFO.

REAL VIEWS (CLOCK-KV-R16, opt-in; without them the output is unchanged):
  --core-view MODULE=VIEWDIR  a signed hard core's own view (VIEWDIR/<MODULE>_{tt,ff}.lib ETM + <MODULE>.core.json).
      Every plan hard-core instance of MODULE is mapped to the nearest tap of its partition (core centre, die frame).
      That tap gets a second endpoint model next to the declared pin register: the ETM boundary arcs, which already
      hold the core's own clock insertion (clk->out at the seam-wire load; input setup/hold constraints), referenced
      to the core clock pin = tap arrival + --core-part-delay-ps (the partition tap->core-pin wire, unbuilt = budget).
  --kit PART_OR_TYPE=kit.json  a partition interface model replacing the declared register on every tap of that
      partition (or type): {"corners": {"TT": {"lat_min_ps", "lat_max_ps", "clkq_max_ps", "clkq_min_ps", "setup_ps",
      "hold_ps"}, "FF": {...}}}.
  With any real view the declared side carries the 12.3 common latency explicitly (TT clock.insertion_ps, FF
  clock.insertion_ff_ps or 0.81 x TT) because it no longer cancels against a real core latency.  Every pair is
  timed over all endpoint-model combinations; the class keeps the worst over all, and 'real_view' reports the worst
  over the combinations that use at least one real model, plus real/total pair and instance counts.

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


def endpoint_slacks(A, B, la, ea, lc, ec, cr, period, unc_s, unc_h, models_a, models_b):
    """[(setup, hold, real, ma, mb)] over every launch model x capture model (REAL VIEWS).  Model: name, real,
    lat_late, lat_early (clock pin latency below the tap), clkq_max/min (launch arcs), setup/hold (capture arcs)."""
    out = []
    for ma in models_a:
        al = la + ma["lat_late"] + ma["clkq_max"]
        ae = ea + ma["lat_early"] + ma["clkq_min"]
        for mb in models_b:
            s = (ec + mb["lat_early"] + period - mb["setup"]) - al - unc_s + cr
            h = ae - (lc + mb["lat_late"] + mb["hold"]) - unc_h + cr
            out.append((s, h, ma["real"] or mb["real"], ma["name"], mb["name"], ma["real"] and mb["real"]))
    return out


def time_class(pairs, taps, rng, reg, lat_tol, period, unc_s, unc_h, landed=False, window=None, hold_window=None,
               ocv=None, views=None):
    """ocv: optional callable (a_port, b_port, check) -> clock OCV pessimism ps on the non-common clock (CLK-AOCV,
    opt-in --clock-ocv); None = unchanged (no clock derate in this gate).
    views: optional {port: [endpoint models]} (REAL VIEWS, opt-in); None = the declared register on every tap."""
    ws, wh, sk, rows = None, None, 0.0, []
    rv = dict(pairs=0, ws=None, wh=None, nneg_s=0, nneg_h=0, both=0, bs=None, bh=None, bneg_s=0, bneg_h=0,
              dmg=[]) if views is not None else None
    ocv_max = {"setup": 0.0, "hold": 0.0}
    nneg_s = nneg_h = 0
    mds = mdh = float('-inf')
    for a, b, tag in pairs:
        A, B = taps[a], taps[b]
        la, ea, lc, ec = A["late_ps"], A["early_ps"], B["late_ps"], B["early_ps"]
        node = A["cppr_node"] if A["cppr_node"] == B["cppr_node"] else "h"
        cr = credit(rng, node, la, ea, lc, ec)
        dmg_s, dmg_h = la - ec - cr, lc - ea - cr
        if views is None:
            s = period - unc_s - (la + reg["clkq_max_wire_ps"]) + (ec - reg["setup_ps"]) + cr
            h = (ea + reg["clkq_min_nowire_ps"]) - (lc + reg["hold_ps"]) - unc_h + cr
        else:
            ma, mb = views[a], views[b]
            combos = endpoint_slacks(A, B, la, ea, lc, ec, cr, period, unc_s, unc_h, ma, mb)
            s, h = min(c[0] for c in combos), min(c[1] for c in combos)
            rc = [c for c in combos if c[2]]
            if rc:
                po = (ocv(a, b, "setup"), ocv(a, b, "hold")) if ocv is not None else (0.0, 0.0)
                rs = min(rc, key=lambda c: c[0])
                rh = min(rc, key=lambda c: c[1])
                rv["pairs"] += 1
                rv["both"] += any(m["real"] for m in ma) and any(m["real"] for m in mb)
                rv["nneg_s"] += rs[0] - po[0] < 0
                rv["nneg_h"] += rh[1] - po[1] < 0
                if rv["ws"] is None or rs[0] - po[0] < rv["ws"][0]:
                    rv["ws"] = (rs[0] - po[0], a, b, tag, rs[3], rs[4])
                if rv["wh"] is None or rh[1] - po[1] < rv["wh"][0]:
                    rv["wh"] = (rh[1] - po[1], a, b, tag, rh[3], rh[4], round(lc - ea - cr, 2))
                bc = [c for c in combos if c[5]]
                if bc:
                    bs_ = min(bc, key=lambda c: c[0])
                    bh_ = min(bc, key=lambda c: c[1])
                    rv["bneg_s"] += bs_[0] - po[0] < 0
                    rv["bneg_h"] += bh_[1] - po[1] < 0
                    if rv["bs"] is None or bs_[0] - po[0] < rv["bs"][0]:
                        rv["bs"] = (bs_[0] - po[0], a, b, tag, bs_[3], bs_[4], round(la - ec - cr, 2))
                    if rv["bh"] is None or bh_[1] - po[1] < rv["bh"][0]:
                        rv["bh"] = (bh_[1] - po[1], a, b, tag, bh_[3], bh_[4], round(lc - ea - cr, 2))
        if ocv is not None:
            ps_, ph_ = ocv(a, b, "setup"), ocv(a, b, "hold")
            s, h = s - ps_, h - ph_
            ocv_max["setup"], ocv_max["hold"] = max(ocv_max["setup"], ps_), max(ocv_max["hold"], ph_)
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
    if rv is not None:
        out["real_view"] = dict(pairs_with_real_endpoint=rv["pairs"], pairs_both_real=int(rv["both"]),
                                pairs_total=len(pairs), setup_neg_pairs=int(rv["nneg_s"]), hold_neg_pairs=int(rv["nneg_h"]))
        if rv["ws"]:
            out["real_view"].update(
                worst_setup_slack_ps=round(rv["ws"][0], 2), worst_hold_slack_ps=round(rv["wh"][0], 2),
                worst_setup=dict(zip(("launch", "capture", "where", "launch_model", "capture_model"), rv["ws"][1:])),
                worst_hold=dict(zip(("launch", "capture", "where", "launch_model", "capture_model", "clock_damage_ps"),
                                    rv["wh"][1:])))
        if rv["bs"]:
            k_ = ("launch", "capture", "where", "launch_model", "capture_model", "clock_damage_ps")
            out["real_view"]["both_real"] = dict(
                setup_neg_pairs=int(rv["bneg_s"]), hold_neg_pairs=int(rv["bneg_h"]),
                worst_setup_slack_ps=round(rv["bs"][0], 2), worst_hold_slack_ps=round(rv["bh"][0], 2),
                worst_setup=dict(zip(k_, rv["bs"][1:])), worst_hold=dict(zip(k_, rv["bh"][1:])))
    if ocv is not None:
        out["clock_ocv_pessimism_max_ps"] = {k: round(v, 2) for k, v in ocv_max.items()}
    if hold_window is not None:
        hd = []
        for a, b, tag in pairs:
            A, B = taps[a], taps[b]
            node = A["cppr_node"] if A["cppr_node"] == B["cppr_node"] else "h"
            cr = credit(rng, node, A["late_ps"], A["early_ps"], B["late_ps"], B["early_ps"])
            hd.append((B["late_ps"] - A["early_ps"] - cr, a, b, tag))
        hd.sort(reverse=True)
        w = float(hold_window["ps"])
        out["kit_contract_hold"] = dict(
            window_ps=w, basis=hold_window["basis"], worst_hold_bound_ps=round(w - hd[0][0], 2),
            neg_pairs=sum(1 for v in hd if v[0] > w), window_needed_ps=round(max(0.0, hd[0][0]), 2),
            worst=dict(launch=hd[0][1], capture=hd[0][2], where=hd[0][3], damage_ps=round(hd[0][0], 2)),
            damage_pctl_ps={q: round(hd[min(len(hd) - 1, int(len(hd) * (1 - q / 100.0)))][0], 2) for q in (50, 99, 99.9)},
            verdict="PASS" if hd[0][0] <= w else "FAIL")
    if landed:
        out["plan_landing"] = dict(window_ps=round(window, 2), setup_margin_ps=round(window - mds, 2),
                                   hold_margin_ps=round(window - mdh, 2),
                                   damage_max_ps=round(max(r[0] for r in rows), 2),
                                   verdict="PASS" if max(r[0] for r in rows) <= window else "FAIL",
                                   note="plan-defined landed/forwarded hop: region-to-region clock damage vs landing "
                                        "window; single-cycle slacks above are INFO for landed pairs")
    return out


def clock_ocv_fn(mode, droop, meta, taps, core_lat, table_path=None, margins_path=None, cell_share=None):
    """CLK-AOCV (METHODOLOGY 12.4a b1, DRAFT, opt-in): per pair clock OCV pessimism on the branches below the last
    common node.  Needs per-tap 'stages_from_root' + 'xy_um' and per-node meta 'node_stages' / 'node_xy_um' plus the
    node arrivals 'node_late_ps' / 'node_early_ps' in tap_arrivals_<C>.json (CLOCK-128-R7 --aocv-fold export names;
    CLOCK-128-R8); refuses when they are missing.
    Branch = tap arrival - node arrival (+ declared core latency, class-B stages), cell share from the table (class A
    die stage) unless cell_share is given.  mode 'flat' = die_ci_margins.json cell/net derates, 'table' = clk_aocv.
    droop 'stated' = +5.1 % late on the late branch always; 'shared' = 0 when both taps share a region (cppr_node
    != 'h' and equal), else +5.1 %."""
    import clk_aocv as CA
    here = Path(__file__).resolve().parent
    T = CA.load(table_path or here / "clk_aocv_table.json")
    m = json.loads(Path(margins_path or here / "die_ci_margins.json").read_text())
    need = [k for k in ("node_stages", "node_xy_um", "node_late_ps", "node_early_ps") if k not in meta]
    tneed = sum(1 for r in taps.values() if "stages_from_root" not in r or "xy_um" not in r)
    if need or tneed:
        raise SystemExit(f"--clock-ocv {mode}: tap_arrivals lacks {need} / {tneed} taps without stages_from_root+xy_um "
                         "(CLOCK-128 fold export must add them)")
    corner = meta.get("corner", "TT")
    B = T["classes"]["B"][corner]
    fc = cell_share if cell_share is not None else T["classes"]["A"][corner]["cell_share"]
    nB = max(1, round(core_lat / B["mu_stage_ps"]))

    def branch(r, node, late):
        arr = (r["late_ps"] if late else r["early_ps"]) - float(meta["node_late_ps" if late else "node_early_ps"][node])
        return dict(cell_ps=fc * arr + B["cell_share"] * core_lat, net_ps=(1 - fc) * arr + (1 - B["cell_share"]) * core_lat,
                    stages={"A": int(r["stages_from_root"]) - int(meta["node_stages"][node]), "B": nB})

    def fn(a, b, check):
        A_, B_ = taps[a], taps[b]
        node = A_["cppr_node"] if A_["cppr_node"] == B_["cppr_node"] else "h"
        same = node != "h"
        nxy = meta["node_xy_um"][node]
        pts = [A_["xy_um"], B_["xy_um"], nxy]
        d = ((max(p[0] for p in pts) - min(p[0] for p in pts)) ** 2 + (max(p[1] for p in pts) - min(p[1] for p in pts)) ** 2) ** 0.5
        # setup: launch a late, capture b early; hold: capture b late, launch a early
        ba = branch(A_, node, check == "setup")
        bb = branch(B_, node, check != "setup")
        if mode == "flat":
            return CA.flat_pessimism(m, ba, bb, check, same, droop == "shared")
        return CA.branch_pessimism(T, corner, ba, bb, d, same if droop == "shared" else False, check)
    return fn


# ---------------------------------------------------------------- REAL VIEWS (CLOCK-KV-R16, opt-in)
def _vals(txt):
    return [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", txt)]


def _interp(index, values, x):
    """1-D table at x (linear, clamped extrapolation-free at the ends); a non 1-D table -> None."""
    if not index or len(index) != len(values):
        return None
    if x <= index[0]:
        return values[0]
    for i in range(1, len(index)):
        if x <= index[i]:
            f = (x - index[i - 1]) / (index[i] - index[i - 1])
            return values[i - 1] + f * (values[i] - values[i - 1])
    return values[-1]


def parse_etm(lib_path, load_ff):
    """worst boundary arcs of a hard-core ETM (OpenROAD write_timing_model Liberty) against its main clock pin (the
    pin with min/max_clock_tree_path).  out_max/out_min = max/min clk->out (cell_rise|fall) over every output at
    load_ff; in_setup/in_hold = max setup/hold constraint over every input.  Arcs already include the core's own
    clock insertion.  Tables that are not 1-D in load use their max (setup side) / min (hold side) entry."""
    txt = Path(lib_path).read_text()
    pin, ttype, rel, grp, idx = None, None, None, None, None
    clk_tree, arcs, other = {}, dict(out=[], setup=[], hold=[]), set()
    for line in txt.splitlines():
        s = line.strip()
        m = re.match(r'pin\("([^"]+)"\)', s)
        if m:
            pin = m.group(1)
            continue
        if s.startswith("timing()"):
            ttype, rel = None, None
            continue
        m = re.match(r"timing_type\s*:\s*(\w+)", s)
        if m:
            ttype = m.group(1)
            continue
        m = re.match(r'related_pin\s*:\s*"([^"]+)"', s)
        if m:
            rel = m.group(1)
            continue
        m = re.match(r"(cell_rise|cell_fall|rise_constraint|fall_constraint)\b", s)
        if m:
            grp, idx = m.group(1), None
            continue
        if s.startswith("index_1"):
            idx = _vals(s.split("(", 1)[1])
            continue
        if s.startswith("values(") and grp:
            v = _vals(s[len("values("):])
            if ttype in ("min_clock_tree_path", "max_clock_tree_path"):
                clk_tree.setdefault(pin, {})[ttype] = max(v) if ttype.startswith("max") else min(v)
            elif ttype == "rising_edge" and grp.startswith("cell_"):
                x = _interp(idx, v, load_ff)
                arcs["out"].append((pin, rel, x if x is not None else max(v), x if x is not None else min(v)))
            elif ttype in ("setup_rising", "hold_rising") and grp.endswith("constraint"):
                arcs["setup" if ttype.startswith("setup") else "hold"].append((pin, rel, max(v)))
            elif ttype:
                other.add(ttype)
            grp = None
    if len(clk_tree) != 1:
        raise SystemExit(f"{lib_path}: expected one main clock pin with clock_tree_path arcs, found {sorted(clk_tree)}")
    ck = next(iter(clk_tree))
    bad = sorted({r for k in arcs for _, r, *_ in arcs[k] if r != ck})
    if bad:
        raise SystemExit(f"{lib_path}: boundary arcs related to non-main clocks {bad}")
    if not arcs["out"] or not arcs["setup"] or not arcs["hold"]:
        raise SystemExit(f"{lib_path}: missing boundary arcs (out {len(arcs['out'])} setup {len(arcs['setup'])} "
                         f"hold {len(arcs['hold'])})")
    om = max(arcs["out"], key=lambda r: r[2])
    on = min(arcs["out"], key=lambda r: r[3])
    su = max(arcs["setup"], key=lambda r: r[2])
    ho = max(arcs["hold"], key=lambda r: r[2])
    return dict(lib=str(lib_path), clock_pin=ck, load_ff=load_ff, clock_tree_path_ps=clk_tree[ck],
                out_max_ps=round(om[2], 3), out_max_pin=om[0], out_min_ps=round(on[3], 3), out_min_pin=on[0],
                in_setup_ps=round(su[2], 3), in_setup_pin=su[0], in_hold_ps=round(ho[2], 3), in_hold_pin=ho[0],
                arcs=dict(out=len(arcs["out"]), setup=len(arcs["setup"]), hold=len(arcs["hold"])),
                other_timing_types=sorted(other))


def core_view_model(module, view_dir, corner, load_ff, part_delay_ps):
    vd = Path(view_dir)
    etm = parse_etm(vd / f"{module}_{corner.lower()}.lib", load_ff)
    cj = vd / f"{module}.core.json"
    prov = vd / "provenance.json"
    meta = {}
    if cj.exists():
        meta["clock_latency_measured"] = json.loads(cj.read_text()).get("clock_latency_measured")
    if prov.exists():
        p = json.loads(prov.read_text())
        meta.update(verdict=p.get("verdict"), pins_sha256=p.get("kit", {}).get("pins_sha256"),
                    pins_file=p.get("kit", {}).get("pins_file"))
    return dict(name=f"core:{module}", real=True, lat_late=part_delay_ps, lat_early=part_delay_ps,
                clkq_max=etm["out_max_ps"], clkq_min=etm["out_min_ps"], setup=etm["in_setup_ps"],
                hold=etm["in_hold_ps"], etm=etm, meta=meta)


def kit_model(spec, corner, name):
    c = spec["corners"][corner]
    return dict(name=f"kit:{name}", real=True, lat_late=float(c["lat_max_ps"]), lat_early=float(c["lat_min_ps"]),
                clkq_max=float(c["clkq_max_ps"]), clkq_min=float(c["clkq_min_ps"]), setup=float(c["setup_ps"]),
                hold=float(c["hold_ps"]))


def budget_model(reg, lat):
    return dict(name="budget", real=False, lat_late=lat, lat_early=lat, clkq_max=reg["clkq_max_wire_ps"],
                clkq_min=reg["clkq_min_nowire_ps"], setup=reg["setup_ps"], hold=reg["hold_ps"])


def map_cores_to_taps(plan, taps):
    """{(part, inst): (module, port, distance_um, pins_file)} every plan hard-core instance -> nearest tap of its
    partition (core outline centre, die frame via schema.Plan.to_die)."""
    import schema as S
    P = S.Plan(plan)
    by_part = defaultdict(list)
    for p, r in taps.items():
        by_part[r["part"]].append((p, r["xy_um"]))
    out = {}
    for n, p in P.parts.items():
        for h in P.types[p["type"]].get("hard_cores", []) or []:
            cx = float(h["origin_um"][0]) + float(h["outline_um"][0]) / 2
            cy = float(h["origin_um"][1]) + float(h["outline_um"][1]) / 2
            X, Y = P.to_die(n, (cx, cy))
            tl = by_part.get(n)
            if not tl:
                out[(n, h["inst"])] = (h["module"], None, None, h.get("pins_file"))
                continue
            port, xy = min(tl, key=lambda t: (t[1][0] - X) ** 2 + (t[1][1] - Y) ** 2)
            out[(n, h["inst"])] = (h["module"], port, round(((xy[0] - X) ** 2 + (xy[1] - Y) ** 2) ** 0.5, 2),
                                   h.get("pins_file"))
    return out


def build_views(plan, taps, corner, reg, lat, core_views, kits, load_ff, part_delay_ps):
    """{port: [models]} + coverage record.  core_views {module: dir}; kits {part_or_type: spec}."""
    budget = budget_model(reg, lat)
    views = {p: [budget] for p in taps}
    cmodels = {m: core_view_model(m, d, corner, load_ff, part_delay_ps) for m, d in core_views.items()}
    cmap = map_cores_to_taps(plan, taps) if core_views else {}
    real_inst, real_taps = defaultdict(int), set()
    for (n, inst), (mod, port, dist, pins) in cmap.items():
        if mod in cmodels and port:
            if cmodels[mod] not in views[port]:
                views[port] = views[port] + [cmodels[mod]]
            real_inst[mod] += 1
            real_taps.add(port)
    ptype = {x["name"]: x["type"] for x in plan["partitions"]}
    kit_parts = set()
    for p, r in taps.items():
        key = r["part"] if r["part"] in kits else ptype.get(r["part"]) if ptype.get(r["part"]) in kits else None
        if key:
            views[p] = [kit_model(kits[key], corner, key)]
            real_taps.add(p)
            kit_parts.add(r["part"])
    tot = defaultdict(int)
    for (_, _), (mod, *_r) in cmap.items():
        tot[mod] += 1
    cov = dict(core_instances_total=sum(tot.values()) if cmap else None,
               core_instances_real=sum(real_inst.values()), real_by_module=dict(real_inst),
               taps_total=len(taps), taps_with_real_model=len(real_taps), kit_partitions=sorted(kit_parts),
               core_models={m: dict(c["etm"], meta=c["meta"], part_delay_ps=part_delay_ps) for m, c in cmodels.items()},
               map_distance_max_um=max([v[2] for v in cmap.values() if v[2] is not None] or [0.0]),
               map_distance_real_um=sorted(v[2] for v in cmap.values() if v[0] in cmodels and v[2] is not None)[::32])
    return views, cov


def kit_windows(pc, intra_override=None):
    """{intra, seam, seam_nearest_INFO: {ps, basis}}: the kit hold windows the plan clock block declares."""
    if pc.get("seam_hold"):
        wseam = dict(ps=float(pc["seam_hold"]["seam_ps"]), basis="plan clock.seam_hold.seam_ps (gen_phys.seam_hold)")
    else:
        wseam = dict(ps=float(pc.get("insertion_tol_ps", 40.0)) - 0.0,
                     basis="legacy: receiver in_min -insertion_tol, sender out_min 0 (gen_phys.seam_hold)")
    if pc.get("io_hold"):
        wseam["basis"] += f"; plan has clock.io_hold ({pc['io_hold']}) -> per-port, not modelled: bound is conservative"
    if intra_override is not None:
        wintra = dict(ps=intra_override, basis=f"WHAT-IF --intra-window-ps {intra_override:g} (not the plan)")
    elif pc.get("tap_window"):
        wintra = dict(ps=float(pc["tap_window"]["window_ps"]), basis="plan clock.tap_window.window_ps (gen_phys."
                      "tap_window_ps: kit SDC source -early -W / -late 0 on every tap port, CRPR credits same-tap)")
    else:
        wintra = dict(ps=0.0, basis="kit SDC: all taps of a partition on one ideal clock (no plan clock.tap_window)")
    hwin = dict(intra=wintra,
                seam=wseam, seam_nearest_INFO=wseam)
    return hwin


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
    ap.add_argument("--intra-window-ps", type=float,
                    help="WHAT-IF override of the intra-partition kit window (default: the plan's clock.tap_window."
                         "window_ps, else 0 = the one-ideal-clock kit SDC)")
    ap.add_argument("--kit", action="append", default=[], help="part_or_type=kit.json partition interface model "
                    "(REAL VIEWS, opt-in; see docstring)")
    ap.add_argument("--core-view", action="append", default=[], help="MODULE=VIEWDIR signed hard-core view "
                    "(<MODULE>_{tt,ff}.lib ETM + core.json); REAL VIEWS, opt-in")
    ap.add_argument("--core-part-delay-ps", type=float, default=0.0,
                    help="partition tap -> core clock pin delay (unbuilt partition = budget; default 0)")
    ap.add_argument("--clock-ocv", choices=("none", "flat", "table"), default="none",
                    help="CLK-AOCV opt-in (12.4a b1 DRAFT, not a gate until OWNER review): clock OCV on the non-common "
                         "branches; default none = unchanged output")
    ap.add_argument("--clock-droop", choices=("stated", "shared"),
                    help="clock droop with --clock-ocv: stated +5.1 %% always, or shared (0 in one region); default "
                         "shared for table, stated for flat")
    ap.add_argument("--clock-aocv-table", help="clock_aocv block (default tools/die_plan/clk_aocv_table.json)")
    ap.add_argument("--clock-ocv-cell-share", type=float, help="cell share of the die branch (default: table class A)")
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
    kits = {}
    for k in a.kit:
        n, f = k.split("=", 1)
        kits[n] = json.loads(Path(f).read_text())
    core_views = dict(k.split("=", 1) for k in a.core_view)
    real = bool(kits or core_views)
    period = a.period_ps
    window = a.landing_window_ps if a.landing_window_ps else period / 2
    lat_tt = float(plan.get("clock", {}).get("common_latency_ps", 250.0))
    pc = plan.get("clock", {})
    hwin = kit_windows(pc, a.intra_window_ps)
    lat = dict(TT=lat_tt, FF=a.core_latency_ff if a.core_latency_ff is not None else lat_tt)
    res = dict(proof=str(Path(a.proof).resolve()), timed_dir=str(d.resolve()), plan=str(Path(a.plan).resolve()),
               period_ps=period, unc_setup_ps=UNC_SETUP_PS, unc_hold_ps=UNC_HOLD_PS, gate="METHODOLOGY 12.4a v4.3: TT setup "
               ">= 0 and FF hold >= 0 on every related pair; CPPR at last common tree node (12.4b); skew = DIAGNOSTIC",
               block_model=dict(label="declared-budget", core_latency_ps=lat, cancels="same declared latency both sides",
                                core_tol_sensitivity_ps=a.core_tol_ps, register=REG_CELL,
                                seam_wire=dict(um=a.seam_wire_um, ff_per_um=a.wire_ff_per_um, applied="setup only"),
                                kits_found=len(kits), core_views_found=len(core_views)),
               corners={})
    if real:
        import schema as S_
        res["block_model"]["label"] = "real-view (%d core views, %d kits) + declared-budget rest" % (len(core_views), len(kits))
        res["block_model"]["declared_latency_ps"] = {c: S_.common_latency_ps(S_.Plan(plan), c) for c in ("TT", "FF")}
        res["block_model"]["core_part_delay_ps"] = a.core_part_delay_ps
    cov = None
    for c in corners:
        meta, taps = load_taps(d, c)
        rng = meta["cppr_node_range_ps"]
        slew = max(r["slew_ps"] for r in taps.values())
        reg = characterise(out, c, slew, a.seam_wire_um * a.wire_ff_per_um)
        pairs, cov = build_pairs(plan, taps)
        views = None
        if real:
            import schema as S_
            views, rcov = build_views(plan, taps, c, reg, S_.common_latency_ps(S_.Plan(plan), c), core_views, kits,
                                      a.seam_wire_um * a.wire_ff_per_um, a.core_part_delay_ps)
            cr_real = rcov
        pairs.update(nearest_pairs(d, a.plan, a.clock_tool, taps))
        cr = dict(basis=meta.get("basis"), tap_slew_max_ps=round(slew, 2), register=reg, classes={})
        if real:
            cr["real_view_coverage"] = cr_real
        ocv = None
        if a.clock_ocv != "none":
            droop = a.clock_droop or ("shared" if a.clock_ocv == "table" else "stated")
            ocv = clock_ocv_fn(a.clock_ocv, droop, dict(meta, corner=c), taps, lat[c], a.clock_aocv_table,
                               cell_share=a.clock_ocv_cell_share)
            cr["clock_ocv"] = dict(mode=a.clock_ocv, droop=droop, status="DRAFT 12.4a b1, UNCHECKED, not a gate")
        for k, pl in pairs.items():
            cr["classes"][k] = time_class(pl, taps, rng, reg, a.core_tol_ps, period, UNC_SETUP_PS, UNC_HOLD_PS,
                                          landed=k.startswith("landed"), window=window,
                                          hold_window=hwin.get(k) if c == "FF" else None, ocv=ocv, views=views)
            cr["classes"][k]["label"] = ("real-view+budget" if real else "declared-budget") + (
                " / INFO subset" if k.endswith("INFO") else "")
        res["corners"][c] = cr
    res["coverage"] = cov
    gate = {}
    for k in ("intra", "seam"):
        s = res["corners"].get("TT", {}).get("classes", {}).get(k, {})
        h = res["corners"].get("FF", {}).get("classes", {}).get(k, {})
        gate[k] = dict(tt_setup_ps=s.get("worst_setup_slack_ps"), ff_hold_ps=h.get("worst_hold_slack_ps"),
                       verdict="PASS" if (s.get("worst_setup_slack_ps", -1) >= 0 and h.get("worst_hold_slack_ps", -1) >= 0)
                       else "FAIL")
    for k in ("intra", "seam"):
        kc = res["corners"].get("FF", {}).get("classes", {}).get(k, {}).get("kit_contract_hold")
        if kc:
            gate[k]["ff_hold_kit_contract_ps"] = kc["worst_hold_bound_ps"]
            gate[k]["kit_contract_window_ps"] = kc["window_ps"]
            gate[k]["kit_contract_window_needed_ps"] = kc["window_needed_ps"]
            gate[k]["kit_contract_verdict"] = kc["verdict"]
    lt = res["corners"].get("TT", {}).get("classes", {}).get("landed", {}).get("plan_landing", {})
    lf = res["corners"].get("FF", {}).get("classes", {}).get("landed", {}).get("plan_landing", {})
    gate["landed"] = dict(tt_setup_margin_ps=lt.get("setup_margin_ps"), ff_hold_margin_ps=lf.get("hold_margin_ps"),
                          verdict="PASS" if lt.get("verdict") == "PASS" and lf.get("verdict") == "PASS" else "FAIL")
    res["summary"] = dict(gate, status="UNCHECKED (NUMBER-CHECK pending)",
                          label=res["block_model"]["label"] if real else "declared-budget (no QC kit)")
    if real:
        for k in ("intra", "seam"):
            rs = res["corners"].get("TT", {}).get("classes", {}).get(k, {}).get("real_view", {})
            rh = res["corners"].get("FF", {}).get("classes", {}).get(k, {}).get("real_view", {})
            gate[k]["real_view"] = dict(pairs=f"{rs.get('pairs_with_real_endpoint', 0)}/{rs.get('pairs_total', 0)}",
                                        tt_setup_ps=rs.get("worst_setup_slack_ps"), ff_hold_ps=rh.get("worst_hold_slack_ps"))
        res["summary"].update(gate)
    (out / "die_sta_related.json").write_text(json.dumps(res, indent=1) + "\n")
    for c, cr in res["corners"].items():
        for k, v in cr["classes"].items():
            if v.get("pairs"):
                print(f"{d.name} {c} {k:18s} pairs {v['pairs']:7d} setup {v['worst_setup_slack_ps']:8.2f} "
                      f"(neg {v['setup_neg_pairs']}) hold {v['worst_hold_slack_ps']:8.2f} (neg {v['hold_neg_pairs']}) "
                      f"skew {v['skew_diag_max_ps']:7.2f}" + (f" kit-contract hold {v['kit_contract_hold']['worst_hold_bound_ps']:.2f}"
                      f" (W {v['kit_contract_hold']['window_ps']:g}, need {v['kit_contract_hold']['window_needed_ps']:.2f},"
                      f" neg {v['kit_contract_hold']['neg_pairs']})" if "kit_contract_hold" in v else "") + (f" landing {v['plan_landing']}" if "plan_landing" in v else "")
                      + (f" | REAL {v['real_view']['pairs_with_real_endpoint']} pairs setup "
                         f"{v['real_view'].get('worst_setup_slack_ps')} (neg {v['real_view']['setup_neg_pairs']}) hold "
                         f"{v['real_view'].get('worst_hold_slack_ps')} (neg {v['real_view']['hold_neg_pairs']})"
                         + (f" | BOTH-REAL {v['real_view']['pairs_both_real']} setup "
                            f"{v['real_view']['both_real']['worst_setup_slack_ps']} hold "
                            f"{v['real_view']['both_real']['worst_hold_slack_ps']} (neg "
                            f"{v['real_view']['both_real']['hold_neg_pairs']})" if "both_real" in v["real_view"] else "")
                         if v.get("real_view", {}).get("pairs_with_real_endpoint") else ""))
    print("SUMMARY", json.dumps(res["summary"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
