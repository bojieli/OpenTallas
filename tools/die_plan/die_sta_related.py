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
  DIAGNOSTIC ONLY since OWNER 12.19 (FLOW-HOLD-1): the die hold gate is judged on real signed views (below).
HOLD ON REAL VIEWS ONLY (OWNER 12.19, FLOW-HOLD-1): every pair class carries 'hold_measured': a pair is MEASURED only
  when both endpoint blocks have a signed real view (partition --kit, or the --core-view of an early core tap); a pair
  through a declared register / missing core view / unsigned view is UNMEASURED (reason: missing view <block>), not a
  hold failure.  Summary per class: ff_hold_margin_ps (measured pairs only), hold_pairs_measured/unmeasured,
  missing_views, hold_status PASS (0 unmeasured, all measured >= 0) / BLOCKED(kits) / FAIL; the all-pair number is
  ff_hold_all_pairs_diag_ps (DIAGNOSTIC).  Setup unchanged.
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

EARLY CORE TAPS (FLOW-ONEMODEL-3, COORD 10-28; plans with clock.core_taps 'early'; others byte-unchanged): an early
  core tap t_<part>__clk_c<k> feeds only its core's clock pin(s) and is delivered core_tap_early_ps before the plain
  taps on purpose, so its endpoint carries the core's OWN insertion instead of the common latency.  --core-insertion
  view (gate default): the signed --core-view model of its core (pin-matched as above; the core is not also mapped to
  the nearest tap); a core tap with no matching view keeps the common latency, is listed missing and the intra/seam
  verdicts FAIL (closed).  --core-insertion declared (PLANNING ONLY): no-view taps use the plan's per-tap insertion
  (insertion_ps / insertion_ff_ps) on the declared register, labelled 'declared'; a passing result reads 'DECLARED',
  never PASS.  Plain taps then carry the common latency explicitly (TT clock.insertion_ps, FF insertion_ff_ps).  The
  kit contract measures each core tap at arrival + its kit-SDC earliness (-source -early_ps), so a planned early tap is
  damage-free and a LATE core pin is charged.
DROOP REGION (CLOCK-KV-R17, COORD RULING CLOCK-KV-R16 (2), METHODOLOGY 12.4a b1): with --clock-droop shared the clock
  is charged droop only between taps in DIFFERENT mesh/PDN regions.  --droop-region mesh (default) = the region is the
  mesh/PDN region: every tap of the proof's mesh.json (one continuous die mesh) is in ONE region unless --droop-regions
  FILE (JSON {port: region}, e.g. from PDNSim) says otherwise; taps without a mesh region fall back to the tree rule.
  --droop-region tree = the old (buggy) behaviour that tied the droop region to the last common tree node; kept only to
  reproduce pre-R17 numbers.
SIGNED MESH = COMMON POINT (CLOCK-KV-R17, opt-in, METHODOLOGY 12.4a b exception / 12.8e): --mesh-signoff
  TT=mc_TT.json,FF=mc_FF.json (kv_r17/mesh_mc17.py variation sim: per mesh-load nominal + MC arrivals, routed nominal,
  gradient shift vectors).  Every tap whose mesh load (array stub input; with --mesh-band sim also the leaf-fed band
  root input) is in the sign-off is re-referenced to the mesh: late/early := M0 + (tap - routed load late/early),
  cppr_node 'm' (credit 0: the same M0 on both sides), AOCV charged only below the load point (node 'm' stages = mesh
  driver output, no node position: distance = launch/capture bbox).  Each 'm' pair then carries the explicit signed
  uncertainty U(a,b) = max(worst |d'| over the samples, |mean d'| + 3 sigma) + |gradient shift vector difference|
  (worst direction), where d' = the two load arrivals' difference in a sample PLUS the routed-vs-sim gap difference
  (gap_a - gap_b, folded into every sample; PD11 ruling 3, 10-27 -- before, |gap_a - gap_b| was added after max|d|,
  which over-counted when the gap and the sample difference had opposite signs).  The record reports the die-wide
  bound (max U) and per-pair percentiles (p50/p90/p99/max) over every mesh pair the STA evaluated.
  --mesh-band tree (default, strict): the leaf-fed band taps are NOT through the mesh; any pair with one keeps its
  absolute arrivals and CPPR at the die root 'h' (12.4b).  --mesh-band sim: band-root inputs are sign-off pseudo loads
  (same per-sample tree offsets as the drivers above them) -> 'm' too (INFO / ruling needed).
  Pair classes (intra / seam / landed) are always built on the tree cppr nodes, before the re-reference.

DATA DROOP (METHODOLOGY 12.4a b2, OWNER 10-27 ~18:1x; tools/die_plan/data_droop.py): --data-droop class (DEFAULT)
  charges every pair's SETUP a late data derate at the 35 mV budget: logic class (flop clk->Q, core ETM clk->out minus
  the core's own clock insertion, core ETM input path) +10 % TT / +8 % FF, wire class (repeated M8/M9 stages a
  model declares as wire_max_ps / wire_in_ps) +5 % / +4 %; planned HB4 hold-buffer cells (data cells) get the logic
  fraction on their TT setup charge.  HOLD IS NEVER CREDITED (no early data term).  The clock keeps the shared-droop
  rule above.  --data-droop flat = the old stated +5.1 % (die_ci ir) on every data cell (control); --data-droop none
  = no data term (byte-identical pre-b2 output).  The record carries summary.data_droop {mode, fractions, worst TT
  setup penalty}.

COUNT-ALIGNED CROSSINGS (--count-align, CA-OCV-1): the CA interval = STA phase (OpenSTA late/early + CPPR) + exactly
  ONE clock variation term, the same per-pair callable the related-pair classes get (--clock-ocv table/flat with the
  --clock-droop rule, + --mesh-signoff U, or --pair-unc): d_lo -= ocv(setup), d_hi += ocv(hold).  The exported tap
  late/early carry no derate (their spread is the liberty pin-cap range), so this is not a double count.  Without a
  variation model the CA record says clock_variation 'none' and a WARNING is printed (12.14a needs OCV + droop).
Output OUT/die_sta_related.json (+ worst pairs per class); prints one line per class and corner.
"""
import argparse
import itertools
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data_droop as DD  # noqa: E402

# CLOCK-KV-R18: default clock AOCV table = the OWNER-approved 0.21 %/mm gate table (METHODOLOGY 12.4a b1, 10-26 18:4x).
# clk_aocv_table.json keeps the 0.42 %/mm DRAFT (global-variation bound); R16 gate numbers used it by mistake.
APPROVED_AOCV_TABLE = "clk_aocv_table_g021.json"
APPROVED_G_PER_MM = 0.0021

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


CPPR_LCA = False   # PATH-S81-PD6 opt-in --cppr-lca (default off = unchanged output)


def pair_node(A, B):
    """last common clock node of a pair.  Default: the shared cppr_node (region root) else the die root 'h'.
    --cppr-lca (opt-in, PATH-S81-PD6): taps carry 'tree_path' (root 'h' + one child-index char per tree level, so a
    prefix is an ancestor); the node is the longest common prefix = the true last common tree node (12.4b), which for
    cross-region pairs is the H-tree node above both region roots instead of the die root."""
    if A.get("clock_source_root") or B.get("clock_source_root"):
        return "__source__"  # actual tree input precedes the root output cell: no common cell credit
    if A["cppr_node"] == "m" and B["cppr_node"] == "m":
        return "m"     # both taps re-referenced to the signed mesh (--mesh-signoff)
    if CPPR_LCA and "tree_path" in A and "tree_path" in B:
        x, y = A["tree_path"], B["tree_path"]
        n = 0
        while n < min(len(x), len(y)) and x[n] == y[n]:
            n += 1
        return x[:max(1, n)]
    return A["cppr_node"] if A["cppr_node"] == B["cppr_node"] else "h"


def arr4(A, B, node):
    """launch late/early, capture late/early for this pair's common node: a mesh-re-referenced tap keeps its absolute
    arrival for every pair whose common point is not the signed mesh 'm' (die root or, with --cppr-lca, a tree node above it) (--mesh-signoff, CLOCK-KV-R17)."""
    if node != "m":
        return (A.get("abs_late_ps", A["late_ps"]), A.get("abs_early_ps", A["early_ps"]),
                B.get("abs_late_ps", B["late_ps"]), B.get("abs_early_ps", B["early_ps"]))
    return A["late_ps"], A["early_ps"], B["late_ps"], B["early_ps"]


def count_align_ss_info(landed, taps, bind, period, reg=None, scale=1.27, need_ps=100.0, start_wire=None, cppr_range=None,
                        key="part", ocv=None, ocv_label=None, start_data_delay=None):
    """MESO-RECONCILE (COORD 22:31 HEAD (3)): SS corner row of the count-aligned crossings, INFORMATION ONLY (AGENTS.md /
    METHODOLOGY 6.1: SS never gates).  No die clock proof carries SS tap arrivals, so the TT taps (and the pin-register
    clk->Q) are scaled by the SS/TT delay ratio `scale` (default 1.27 = ASAP7 logic SS/TT derate used by uarch_model;
    clock buffers/wires assumed to scale alike, UNCHECKED) and the same rows (lag, slot->read, guard, start skew) are
    evaluated against the fixed TT/FF-planned K/DEPTH/origins at the same 833 ps period.  A die with real
    tap_arrivals_SS.json runs --corner SS instead (then the SS row is real)."""
    keys = TAP_TIME_KEYS
    st = {k: dict(v, **{f: float(v[f]) * scale for f in keys if f in v}) for k, v in taps.items()}
    rg = None if reg is None else dict(reg, clkq_max_wire_ps=float(reg["clkq_max_wire_ps"]) * scale,
                                       clkq_min_nowire_ps=float(reg["clkq_min_nowire_ps"]) * scale)
    r = count_align_landed(landed, st, bind, period, rg, need_ps, start_wire,
                           None if cppr_range is None else {k: float(v) * scale for k, v in cppr_range.items()},
                           key=key, ocv=None if ocv is None else (lambda x, y, c: scale * ocv(x, y, c)),
                           ocv_label=ocv_label and f"{ocv_label} x {scale}",
                           **({"start_data_delay": start_data_delay} if start_data_delay is not None else {}))
    r.update(info_only=True, ss_scale=scale, basis="TT taps x SS/TT scale (no SS clock proof)", gates=False)
    return r


# METHODOLOGY 12.15 b (OWNER 10-27 23:2x): die STA gates scale clock-network arrivals by the measured OpenSTA-vs-ngspice
# factor (ASAP7 BUFx24 spice calibration: x1.0485 TT, x1.0552 FF); data-path derates unchanged.  Opt-in --clock-cal spice.
# Source: OSS-CLOCK-2 data/asap7_bufx24_spice_cal.json "spice_scale" (opentools/mscts/data/, claude/oss-clock-2-1027@285ba72636).
SPICE_CLOCK_CAL = {"TT": 1.0485, "FF": 1.0552}
TAP_TIME_KEYS = ("late_ps", "early_ps", "abs_late_ps", "abs_early_ps", "fall_late_ps", "fall_early_ps", "abs_fall_late_ps",
                 "abs_fall_early_ps")


NODE_TIME_KEYS = ("node_late_ps", "node_early_ps", "node_fall_late_ps", "node_fall_early_ps")


EARLY_TAP_KEYS = ("early_ps", "abs_early_ps", "fall_early_ps", "abs_fall_early_ps")
EARLY_NODE_KEYS = ("node_early_ps", "node_fall_early_ps")


def scale_clock(meta, taps, f, f_early=None):
    """clock arrivals x f (tap late/early incl. mesh-absolute, the CPPR node ranges and the tree NODE arrivals);
    returns new (meta, taps).  DIE-QC-5: node_late_ps / node_early_ps are clock-network arrivals too.  The clock OCV
    branch is tap - node arrival (clock_ocv_fn), so scaling the taps but not the nodes put f-1 of the whole upstream
    insertion into every branch (QC K2: FF intra OCV pessimism 77.45 vs 56.20 ps on a pre-scaled proof); a proof whose
    arr files were scaled before export (scale_arr.py) must give the same answer as --clock-cal spice."""
    if f_early is not None and f_early != f:
        return _scale_clock_edge(meta, taps, f, f_early)
    if f == 1.0:
        return meta, taps
    t = {k: dict(v, **{x: float(v[x]) * f for x in TAP_TIME_KEYS if x in v}) for k, v in taps.items()}
    m = dict(meta, cppr_node_range_ps={k: float(v) * f for k, v in (meta.get("cppr_node_range_ps") or {}).items()},
             clock_cal_factor=f)
    for nk in NODE_TIME_KEYS:
        if isinstance(meta.get(nk), dict):
            m[nk] = {k: (None if v is None else float(v) * f) for k, v in meta[nk].items()}
    return m, t


def _scale_clock_edge(meta, taps, f, fe):
    """--clock-cal spice_edge (CLK-INV-CAL-2): late keys x f (spice / STA max analysis), early keys x fe (spice / STA
    min analysis).  OpenSTA's min analysis loads every pin with the LOW end of its liberty capacitance_range, so the
    no-derate STA early/late gap of a clock tree is a load-model difference, not variation; the spice MC AOCV table
    (clock_variation) is the variation.  Early is capped at late per key (never earlier than late after calibration
    is only clipped, never reordered); the CPPR node range is re-derived from the scaled node arrivals where both exist."""
    def pair(late, early):
        lv, ev = float(late) * f, float(early) * fe
        return lv, min(ev, lv)
    t = {}
    for k, v in taps.items():
        w = dict(v)
        for lk, ek in (("late_ps", "early_ps"), ("abs_late_ps", "abs_early_ps"), ("fall_late_ps", "fall_early_ps"),
                       ("abs_fall_late_ps", "abs_fall_early_ps")):
            if lk in v and ek in v:
                w[lk], w[ek] = pair(v[lk], v[ek])
            elif lk in v:
                w[lk] = float(v[lk]) * f
            elif ek in v:
                w[ek] = float(v[ek]) * fe
        t[k] = w
    m = dict(meta, clock_cal_factor=f, clock_cal_factor_early=fe)
    for lk, ek in (("node_late_ps", "node_early_ps"), ("node_fall_late_ps", "node_fall_early_ps")):
        L, E = meta.get(lk), meta.get(ek)
        if isinstance(L, dict):
            m[lk] = {k: (None if v is None else float(v) * f) for k, v in L.items()}
        if isinstance(E, dict):
            m[ek] = {k: (None if v is None else
                         (min(float(v) * fe, m[lk][k]) if isinstance(L, dict) and L.get(k) is not None
                          else float(v) * fe)) for k, v in E.items()}
    nl, ne = m.get("node_late_ps") or {}, m.get("node_early_ps") or {}
    rng = {}
    for k, v in (meta.get("cppr_node_range_ps") or {}).items():
        rng[k] = (round(max(0.0, nl[k] - ne[k]), 4) if nl.get(k) is not None and ne.get(k) is not None
                  else float(v) * fe)
    m["cppr_node_range_ps"] = rng
    return m, t


# CLK-INV-CAL-1 (COORD 09:16: the inverter tree die_trial --clock-cell inv / inv2 is the release clock on all dies): the
# ONE shared model keyed by the die clock cell.  'buf' (BUFx24) = SPICE_CLOCK_CAL + AOCV class A, unchanged.  'inv'
# (CKINVDCx16, inv and inv2 trees alike: a branch counts every inverter as one stage) = SPICE_CLOCK_CAL_INV + AOCV class
# 'Ainv' of the approved table, both from the BUFx24 methods repeated on the inverter (tools/die_plan/clk_inv_cal.py,
# results/clk_inv_cal_1_1028/README.md).  Auto-detected from the proof's clock netlist (detect_clock_cell).
# Measured 10-28 (ngspice r3 xAct3D CKINVDCx16 vs OpenSTA NLDM on the same SPEF ladders, 48-stage comb trees, affine
# slope over both sink edges): NDR rep 250 TT 0.9207 / FF 0.9380, NDR rep 150 TT 0.9324 / FF 0.9371 (1x rep 250 TT
# 0.9333 / FF 0.9515, not a clock form).  Gate value = the larger NDR slope per corner (keeps more of the arrival, so
# more OCV, than the smaller one).  BUFx24 control on the same bench: 1.0537 / 1.0640 vs SPICE_CLOCK_CAL 1.0485 / 1.0552.
SPICE_CLOCK_CAL_INV = {"TT": 0.9324, "FF": 0.9380}
# CLK-INV-CAL-2 (opt-in --clock-cal spice_edge): spice / OpenSTA MIN-analysis slope on the same benches (sta_arr_min).
# OpenSTA min analysis takes the low end of the liberty capacitance_range (CKINVDCx16 A 6.68-9.54 fF rise, 6.64-9.53 fall),
# so STA early sits ~12 % under STA late on a no-derate inverter tree, while ngspice gives ONE delay: spice = 0.93 x late
# = 1.02-1.07 x early.  Measured: NDR250 TT 1.0241 / FF 1.0487, NDR150 TT 1.0550 / FF 1.0704 (1x250 1.0501 / 1.0761).
# Gate value = the SMALLER NDR slope per corner (keeps more early/late gap, the hold-safe side).  BUFx24 keeps one
# factor (its pin-cap range is 1.76-2.35 fF on a 24x driver: 1.2 % gap) -> spice_edge == spice for buf.
SPICE_CLOCK_CAL_INV_EARLY = {"TT": 1.0241, "FF": 1.0487}
# MODEL-REFIT-BUF (opt-in --clock-cal spice_buf_edge; COORD 10-28 after MODEL-CORR-1): BUFx24 factors per root edge
# (rise / fall) and per analysis (late = STA max, early = STA min), from the MODEL-CORR-1 golden raw rows
# (tools/die_plan/model_corr_golden.json: ngspice r3 xAct3D BUFx24 vs OpenSTA NLDM, NDR450 50-stage chain, 1x450
# 20-stage chain, 1-2 mm NDR legs; taps 3-50 stages).  The one-factor spice mode (SPICE_CLOCK_CAL, a rise fit) puts the
# falling edge 2.5-4.3 % LATE of spice (late AND early: early above spice is hold-optimistic) and the BUF duty (fall -
# rise) 12-145 ps over spice.  Bounding fit, not a slope: late factor = MAX spice / STA-late over all rows of that
# edge (model late >= spice), early factor = MIN spice / STA-early (model early <= spice), so every bench row keeps
# late >= spice >= early.  Rise late keeps SPICE_CLOCK_CAL (it already bounds: max 1.0472 TT / 1.0551 FF).
# Inverter dies: identical to spice_edge.  Default stays spice until NUMBER-CHECK confirms.
SPICE_CLOCK_CAL_BUF_EDGE = {"TT": dict(rise_late=1.0485, rise_early=1.0524, fall_late=1.0226, fall_early=1.0224),
                            "FF": dict(rise_late=1.0552, rise_early=1.0593, fall_late=1.0256, fall_early=1.0297)}
# MODEL-REFIT-2 (opt-in --clock-cal spice_cell; COORD 10-28 22:47 after the routed HEAD h16 path): ONE factor set per
# clock MASTER, per root edge and per analysis, because the BUFx24 factor over-reads OpenSTA on BUFx4 delay cells (raw
# OpenSTA ~= spice there; spice_buf_edge early up to 5.6 % LATE of spice = hold-optimistic on the h16 taps).  Bounding fit
# over the MODEL-CORR golden rows of each master (chains incl. the MODEL-REFIT-2 BUFx4 / BUFx6f ramp benches) and over
# the routed rows (a mixed path is bounded by the largest late / smallest early factor of its masters):
# late = MAX spice / STA-late, early = MIN spice / STA-early, rounded outward (model_corr.py fit).  A tap's arrival
# holds the delay of every master between the root and the tap, so a tap with masters S takes late = max over S and
# early = min over S (stage-wise bound: sum f_i d_i lies in [min f, max f] x sum d_i).  Masters per tap: tap key
# 'clock_masters', else meta 'clock_masters' (the die's clock-path master census), else the die clock cell's master;
# a master without a factor fails closed.  Default stays spice / spice_edge until NUMBER-CHECK confirms.
# BTAB-F3 (10-29): BUFx10/12/12f/16f from measured 2/60-um chain references;
# see results/buf_master_cal_1029. Existing factors and default modes remain unchanged.
SPICE_CLOCK_CAL_CELL = {
    "BUFx24_ASAP7_75t_R": {
        "TT": dict(rise_late=1.0473, rise_early=1.0222, fall_late=1.0227, fall_early=1.0206),
        "FF": dict(rise_late=1.0552, rise_early=1.0073, fall_late=1.0257, fall_early=1.0025),
    },
    "BUFx4_ASAP7_75t_R": {
        "TT": dict(rise_late=1.0443, rise_early=1.0164, fall_late=1.0388, fall_early=1.0018),
        "FF": dict(rise_late=1.0263, rise_early=0.9972, fall_late=1.024, fall_early=0.9877),
    },
    "BUFx6f_ASAP7_75t_R": {
        "TT": dict(rise_late=1.0243, rise_early=1.0463, fall_late=1.0218, fall_early=1.0417),
        "FF": dict(rise_late=1.0101, rise_early=1.0301, fall_late=1.0056, fall_early=1.025),
    },
    "BUFx8_ASAP7_75t_R": {
        "TT": dict(rise_late=1.0408, rise_early=1.0528, fall_late=1.0332, fall_early=1.0437),
        "FF": dict(rise_late=1.0236, rise_early=1.0347, fall_late=1.0189, fall_early=1.0305),
    },
    "CKINVDCx16_ASAP7_75t_R": {
        "TT": dict(rise_late=0.9483, rise_early=1.0269, fall_late=0.9528, fall_early=1.0274),
        "FF": dict(rise_late=0.9611, rise_early=1.0515, fall_late=0.9623, fall_early=1.052),
    },
    "BUFx10_ASAP7_75t_R": {
        "TT": dict(rise_late=1.0399, rise_early=1.0139, fall_late=1.0295, fall_early=1.0018),
        "FF": dict(rise_late=1.0241, rise_early=1.0003, fall_late=1.019, fall_early=0.9975),
    },
    "BUFx12_ASAP7_75t_R": {
        "TT": dict(rise_late=1.0425, rise_early=1.0196, fall_late=1.0328, fall_early=1.0126),
        "FF": dict(rise_late=1.0278, rise_early=1.0074, fall_late=1.0218, fall_early=1.0074),
    },
    "BUFx12f_ASAP7_75t_R": {
        "TT": dict(rise_late=1.0246, rise_early=1.0366, fall_late=1.0227, fall_early=1.0297),
        "FF": dict(rise_late=1.0112, rise_early=1.0178, fall_late=1.0065, fall_early=1.0112),
    },
    "BUFx16f_ASAP7_75t_R": {
        "TT": dict(rise_late=1.0275, rise_early=1.0088, fall_late=1.0259, fall_early=1.0024),
        "FF": dict(rise_late=1.0112, rise_early=0.9983, fall_late=1.0094, fall_early=0.9955),
    },
}
CLOCK_CALS = ("none", "spice", "spice_edge", "spice_buf_edge", "spice_cell")
CLOCK_CELL_MASTERS = {"buf": ("BUFx24_ASAP7_75t_R",), "inv": ("CKINVDCx16_ASAP7_75t_R",)}
CLOCK_CELL_AOCV_CLASS = {"buf": "A", "inv": "Ainv"}
CLOCK_CELLS = ("auto", "buf", "inv", "inv2")


def spice_cal_factor(corner, clock_cell="buf"):
    """12.15b clock spice factor of the die clock cell ('buf' = SPICE_CLOCK_CAL; SS uses the TT factor)."""
    t = SPICE_CLOCK_CAL_INV if clock_cell == "inv" else SPICE_CLOCK_CAL
    return t.get(corner, t["TT"])


def buf_edge_factors(corner):
    """MODEL-REFIT-BUF per-edge BUFx24 factors (SS uses TT, as spice_cal_factor)."""
    return dict(SPICE_CLOCK_CAL_BUF_EDGE.get(corner, SPICE_CLOCK_CAL_BUF_EDGE["TT"]))


def _scale_clock_buf_edge(meta, taps, fe4):
    """--clock-cal spice_buf_edge on a BUFx24 tree: rise keys (late_ps / early_ps / abs_* / node_late / node_early)
    x rise_late / rise_early, fall keys (fall_* / abs_fall_* / node_fall_*) x fall_late / fall_early.  Early is capped
    at late per key (as _scale_clock_edge); the CPPR node range is re-derived from the scaled rise node arrivals, else
    scaled by the smaller rise factor (less CPPR credit = the pessimistic side)."""
    fr, fre, ff, ffe = fe4["rise_late"], fe4["rise_early"], fe4["fall_late"], fe4["fall_early"]
    pairs = ((("late_ps", "early_ps"), fr, fre), (("abs_late_ps", "abs_early_ps"), fr, fre),
             (("fall_late_ps", "fall_early_ps"), ff, ffe), (("abs_fall_late_ps", "abs_fall_early_ps"), ff, ffe))
    t = {}
    for k, v in taps.items():
        w = dict(v)
        for (lk, ek), fl, fe in pairs:
            if lk in v:
                w[lk] = float(v[lk]) * fl
            if ek in v:
                w[ek] = float(v[ek]) * fe
                if lk in v:
                    w[ek] = min(w[ek], w[lk])
        t[k] = w
    m = dict(meta, clock_cal_factor=fr, clock_cal_factor_early=fre, clock_cal_factor_fall=ff,
             clock_cal_factor_fall_early=ffe)
    for (lk, ek), fl, fe in ((("node_late_ps", "node_early_ps"), fr, fre),
                             (("node_fall_late_ps", "node_fall_early_ps"), ff, ffe)):
        L, E = meta.get(lk), meta.get(ek)
        if isinstance(L, dict):
            m[lk] = {k: (None if v is None else float(v) * fl) for k, v in L.items()}
        if isinstance(E, dict):
            m[ek] = {k: (None if v is None else
                         (min(float(v) * fe, m[lk][k]) if isinstance(L, dict) and L.get(k) is not None
                          else float(v) * fe)) for k, v in E.items()}
    nl, ne = m.get("node_late_ps") or {}, m.get("node_early_ps") or {}
    rng = {}
    for k, v in (meta.get("cppr_node_range_ps") or {}).items():
        rng[k] = (round(max(0.0, nl[k] - ne[k]), 4) if nl.get(k) is not None and ne.get(k) is not None
                  else float(v) * min(fr, fre))
    m["cppr_node_range_ps"] = rng
    return m, t


class ClockMasterUncalibrated(SystemExit):
    pass


def cell_cal_factors(corner, masters):
    """MODEL-REFIT-2 bound of a set of clock masters: rise/fall late = max, rise/fall early = min of the per-master
    SPICE_CLOCK_CAL_CELL factors (SS uses TT).  A master without a factor -> ClockMasterUncalibrated (fail closed)."""
    ms = sorted(set(masters))
    if not ms:
        raise ClockMasterUncalibrated("spice_cell: empty clock master set -> FAIL closed")
    miss = [m for m in ms if m not in SPICE_CLOCK_CAL_CELL]
    if miss:
        raise ClockMasterUncalibrated(f"spice_cell: no spice factor for clock master(s) {miss} (MODEL-REFIT-2 table "
                                      f"SPICE_CLOCK_CAL_CELL has {sorted(SPICE_CLOCK_CAL_CELL)}) -> FAIL closed")
    t = [SPICE_CLOCK_CAL_CELL[m].get(corner, SPICE_CLOCK_CAL_CELL[m]["TT"]) for m in ms]
    return dict(rise_late=max(x["rise_late"] for x in t), fall_late=max(x["fall_late"] for x in t),
                rise_early=min(x["rise_early"] for x in t), fall_early=min(x["fall_early"] for x in t))


def clock_masters_of(meta, tap, clock_cell):
    """masters on the clock path of one tap: tap 'clock_masters', else meta 'clock_masters', else the clock cell's."""
    m = (tap or {}).get("clock_masters") or (meta or {}).get("clock_masters")
    return tuple(m) if m else CLOCK_CELL_MASTERS["inv" if clock_cell == "inv2" else clock_cell]


_INST_RE = re.compile(r"^\s*(\w+)\s+(\\?\S+)\s*\((.*?)\)\s*;", re.M | re.S)
_PIN_RE = re.compile(r"\.(\w+)\s*\(\s*(\\?[^\s()]+)\s*\)")


def netlist_tap_masters(proof, meta=None):
    """MODEL-REFIT-2: {tap port: sorted masters} from the first clock netlist _clock_netlists finds (ctree.v: cells
    with an A input and a Y output), each tap traced through continuous assigns and drivers back to the root; None when
    no netlist is found.  The KV tap-pad BUFx24 chains on PHY taps of an inverter tree are the case this resolves."""
    for f in _clock_netlists(proof, meta):
        if not f.is_file():
            continue
        txt = f.read_text()
        drv = {}
        for m in _INST_RE.finditer(txt):
            master = m.group(1)
            if master in ("module", "input", "output", "wire", "assign"):
                continue
            pins = dict(_PIN_RE.findall(m.group(3)))
            if "Y" in pins and "A" in pins:
                drv[pins["Y"]] = (master, pins["A"])
        if not drv:
            continue
        aliases = dict(re.findall(r"\bassign\s+(\\?[^\s;=]+)\s*=\s*(\\?[^\s;]+)\s*;", txt))
        inputs = {x.strip() for y in re.findall(r"^\s*input\s+([^;]+);", txt, re.M) for x in y.split(",")}
        out, memo = {}, {}

        def up(net):
            path, seen = [], set()
            while net not in memo:
                if net in seen:
                    raise ClockMasterUncalibrated(f"spice_cell: loop in clock path at {net} -> FAIL closed")
                seen.add(net)
                if net in aliases:
                    net = aliases[net]
                    continue
                if net not in drv:
                    if net not in inputs:
                        raise ClockMasterUncalibrated(f"spice_cell: undriven clock net {net} -> FAIL closed")
                    break
                path.append(net)
                net = drv[net][1]
            acc = set(memo.get(net, ()))
            for n in reversed(path):
                acc = acc | {drv[n][0]}
                memo[n] = frozenset(acc)
            return acc
        ports = {x.strip() for y in re.findall(r"^\s*output\s+([^;]+);", txt, re.M) for x in y.split(",")}
        for p in ports:
            ms = up(p)
            if ms:
                out[p] = sorted(ms)
        return out
    return None


def annotate_clock_masters(proof, meta, taps):
    """spice_cell input: taps without 'clock_masters' get the masters traced in the proof's clock netlist (by port);
    a tap the netlist does not reach keeps the meta / clock-cell default.  Returns new taps (input unchanged)."""
    nm = netlist_tap_masters(proof, meta) if proof is not None else None
    if not nm:
        return taps
    return {k: (v if v.get("clock_masters") or k not in nm else dict(v, clock_masters=nm[k])) for k, v in taps.items()}


def _scale_clock_cell(meta, taps, corner, clock_cell):
    """--clock-cal spice_cell: each tap scaled by the bound of its own masters (cell_cal_factors), keys as
    _scale_clock_buf_edge; tree NODE arrivals by the bound of the meta / die master set; CPPR node range re-derived from
    the scaled node arrivals, else scaled by the smaller rise factor (less credit = the pessimistic side)."""
    t = {}
    for k, v in taps.items():
        _, tk = _scale_clock_buf_edge({}, {k: v}, cell_cal_factors(corner, clock_masters_of(meta, v, clock_cell)))
        t[k] = tk[k]
    dm = set(clock_masters_of(meta, None, clock_cell))
    for v in taps.values():
        dm |= set(clock_masters_of(meta, v, clock_cell))
    f4 = cell_cal_factors(corner, dm)
    m, _ = _scale_clock_buf_edge(meta, {}, f4)
    m["clock_cal_masters"] = sorted(dm)
    return m, t


def apply_clock_cal(meta, taps, corner, clock_cell, clock_cal, proof=None):
    """the ONE clock calibration step of planner and gate: none / spice (one factor, 12.15b) / spice_edge (inverter:
    late x SPICE_CLOCK_CAL_INV, early x SPICE_CLOCK_CAL_INV_EARLY; buf: == spice) / spice_buf_edge (buf: per-edge
    SPICE_CLOCK_CAL_BUF_EDGE, MODEL-REFIT-BUF; inverter: == spice_edge)."""
    if clock_cal not in CLOCK_CALS:
        raise SystemExit(f"--clock-cal {clock_cal!r}: one of {CLOCK_CALS}")
    if clock_cal == "none":
        return meta, taps
    if meta.get("clock_components_basis") and clock_cal in ("spice_edge", "spice_cell"):
        from clock_components import apply
        return apply(meta, taps, corner, clock_cal)
    f = spice_cal_factor(corner, clock_cell)
    fe = None
    if clock_cal in ("spice_edge", "spice_buf_edge") and clock_cell == "inv":
        fe = SPICE_CLOCK_CAL_INV_EARLY.get(corner, SPICE_CLOCK_CAL_INV_EARLY["TT"])
    if clock_cal == "spice_buf_edge" and clock_cell != "inv":
        return _scale_clock_buf_edge(meta, taps, buf_edge_factors(corner))
    if clock_cal == "spice_cell":
        return _scale_clock_cell(meta, annotate_clock_masters(proof, meta, taps), corner, clock_cell)
    return scale_clock(meta, taps, f) if fe is None else scale_clock(meta, taps, f, fe)


def clock_cppr_ranges(meta):
    """Common-path ranges after calibration, including measured opposite-edge arrivals.

    Preserve calibration output and old proof records; derive fall ranges in the
    consumer from the calibrated node arrays.  A partial ``__source__@fall`` map
    never implies zero common-path range for other tree nodes.
    """
    ranges = meta.get("cppr_node_range_ps")
    late, early = meta.get("node_fall_late_ps") or {}, meta.get("node_fall_early_ps") or {}
    measured = {k + "@fall": round(max(0.0, float(v) - float(early[k])), 4)
                for k, v in late.items() if v is not None and early.get(k) is not None}
    return dict(ranges or {}, **measured) if measured else ranges


def _clock_netlists(proof, meta):
    """candidate die clock netlists of a proof: PROOF/{,clk/,clock/}ctree.v, then the same names beside / above the
    arrival file the proof's tap_arrivals 'source' names (die_trial run dir: run/out_<C>/arr_<C>.txt + run/clk/ctree.v)."""
    proof = Path(proof)
    c = [proof / "ctree.v", proof / "clk" / "ctree.v", proof / "clock" / "ctree.v"]
    src = str((meta or {}).get("source") or "").split(" ")[0]
    if src:
        p = Path(src).parent
        for q in (p, p.parent, p.parent.parent):
            c += [q / "ctree.v", q / "clk" / "ctree.v", q / "clock" / "ctree.v"]
    return c


class ClockCellUndeclared(SystemExit):
    pass


def netlist_clock_cell(proof, meta=None):
    """(cell, basis) from the majority clock master of the first clock netlist _clock_netlists finds, else None."""
    for f in _clock_netlists(proof, meta):
        if f.is_file():
            txt = f.read_text()
            n = {k: sum(len(re.findall(r"^\s*" + re.escape(m) + r"\s", txt, re.M)) for m in v)
                 for k, v in CLOCK_CELL_MASTERS.items()}
            if n["inv"] or n["buf"]:
                return ("inv" if n["inv"] > n["buf"] else "buf"), f"{f}: {n['inv']} CKINVDCx16 / {n['buf']} BUFx24"
    return None


def _declared(cell, basis, proof, meta):
    if cell not in ("buf", "inv", "inv2"):
        raise ClockCellUndeclared(f"clock cell {cell!r} ({basis}) is not one of buf / inv / inv2: the die clock model "
                                  "(spice factor + AOCV class) is undefined -> FAIL closed (COORD ruling ba28d3143)")
    c = "inv" if cell == "inv2" else cell
    nl = netlist_clock_cell(proof, meta)
    if nl is not None and nl[0] != c:
        raise ClockCellUndeclared(f"declared clock_cell {cell} ({basis}) contradicts the clock netlist ({nl[1]}) -> FAIL "
                                  "closed")
    return c, basis + (f"; netlist agrees ({nl[1]})" if nl else "")


def detect_clock_cell(proof, meta=None):
    """CLK-INV-CAL-1 + COORD ruling ba28d3143 (no silent fallback): (cell, basis) of the die clock from the proof's
    DECLARATION, meta 'clock_cell' in tap_arrivals_<C>.json (trial_tap_arrivals writes it from die_trial's tree.json /
    the built netlist).  Missing or not buf/inv/inv2 -> ClockCellUndeclared (SystemExit, planner and gate alike); a
    declaration that contradicts a clock netlist found beside the proof also fails closed."""
    mc = (meta or {}).get("clock_cell")
    if mc is None:
        raise ClockCellUndeclared(f"{proof}: the proof declares no clock_cell (tap_arrivals meta) -> FAIL closed (COORD "
                                  "ruling ba28d3143: no silent BUFx24 fallback).  Re-export with trial_tap_arrivals, "
                                  "or declare it with --clock-cell buf|inv|inv2")
    return _declared(mc, f"tap_arrivals meta clock_cell={mc}", proof, meta)


def resolve_clock_cell(choice, proof, meta=None):
    """--clock-cell: 'auto' = the proof's declaration (detect_clock_cell, fail closed if missing); buf / inv / inv2 =
    the operator's declaration (inv2 = inv model), checked against the netlist the same way."""
    if choice in (None, "auto"):
        return detect_clock_cell(proof, meta)
    return _declared(choice, f"--clock-cell {choice}", proof, meta)


def credit(rng, node, la, ea, lc, ec):
    c = node
    while c not in rng and len(c) > 1:
        c = c[:-1]
    return min(max(0.0, rng.get(c, 0.0)), max(0.0, la - ea), max(0.0, lc - ec))


class FallArrivalMissing(ValueError):
    """FLOW-ONEMODEL-1: a falling-edge sample needs the MEASURED fall arrival of its capture clock pin (tap
    fall_late_ps / fall_early_ps, tap_fall_merge.py); fall = rise + T/2 is never assumed (duty distortion on BUF
    trees is 148-1149 ps, QC-11 / S81-12 / HEAD-11 / KV-11)."""


def _capture_arr(B, node, edge):
    """capture late/early of tap B for a rise- or fall-sampling flop.  fall: the measured fall arrival (relative to
    the source's falling edge, so the sampling instant is T/2 + fall arrival); raises FallArrivalMissing without it"""
    if edge == "rise":
        return None
    if edge != "fall":
        raise ValueError(f"edge {edge!r}: rise or fall")
    if node == "m" or "fall_late_ps" not in B or "fall_early_ps" not in B:
        raise FallArrivalMissing(f"tap {B.get('port')}: no measured fall arrival (fall_late_ps/fall_early_ps)")
    return float(B.get("abs_fall_late_ps", B["fall_late_ps"])), float(B.get("abs_fall_early_ps", B["fall_early_ps"]))


def ca_pair_interval(A, B, a, b, cppr_range=None, ocv=None, edge="rise", ring=None):
    """THE count-aligned phase interval of ONE launch -> capture tap pair (FLOW-ONEMODEL-1: the single function the
    planner, the binder and the gate all call).  d = capture clock - launch clock at the pair's last common node,
    lo = capture early - launch late (+ CPPR credit), hi = capture late - launch early (- credit), then exactly one
    clock variation term (ocv setup on lo, hold on hi).  The launch is a rising-edge register; edge = the capture
    flop's sampling edge: 'fall' takes the capture tap's MEASURED fall arrival (FallArrivalMissing if absent).
    CPPR on BOTH edges (one model, COORD 10-28 DIE-KV-13): the common path's late-early pessimism is removed for a
    rise-launch / fall-capture pair as for rise/rise, with the industry opposite-edge rule (PrimeTime CRPR: the smaller
    of the rise and fall common-pin ranges): credit = min(rise range at the last common node, its fall range if the
    proof has one (meta-free: cppr_range key '<node>@fall'), launch late-early, capture FALL late-early).  Without a
    measured node fall range the rise range stands for it (the late/early spread is the liberty pin-cap range,
    transition-independent in the exports, CLOCK-MESH-2; UNCHECKED on spice).  Returns (lo, hi, ocv_setup, ocv_hold).
    ring (DIE-HEAD-18, opt-in --ca-ring): callable (A, B) -> (shift_lo, shift_hi) | None, the BUILT ring clocks of the
    pair (ca_ring_fn); the shift is added before the variation term.  None = the declared common latency on both sides
    (cancels, unchanged)."""
    node = pair_node(A, B)
    la, ea, lc, ec = arr4(A, B, node)
    f = _capture_arr(B, node, edge)
    if f is not None:
        lc, ec = f
    cr = credit(cppr_range, node, la, ea, lc, ec) if cppr_range else 0.0
    if f is not None and cppr_range:
        fk = node + "@fall"
        if fk in cppr_range:
            cr = min(cr, credit({node: cppr_range[fk]}, node, la, ea, lc, ec))
    lo, hi = ec - la + cr, lc - ea - cr
    if ring is not None:
        sh = ring(A, B)
        if sh is not None:
            lo, hi = lo + sh[0], hi + sh[1]
    os_ = oh = 0.0
    if ocv is not None:
        os_, oh = float(ocv(a, b, "setup")), float(ocv(a, b, "hold"))
        lo, hi = lo - os_, hi + oh
    return lo, hi, os_, oh


def ca_pair_unshared(A, B, node_late):
    """CLK-INV-CAL-1 / COORD 10-28 wander rule: the unshared clock of ONE launch -> capture tap pair = max(launch late,
    capture late) - the late arrival of their last common node (pair_node, the node ca_pair_interval uses).  A crossing's
    post-start wander is bounded by wander_frac x the worst of this over the crossing's OWN tap pairs (planner and gate
    both call this; never a global max over all crossings).  A node without a late arrival counts from 0 (the whole
    insertion: fail-safe large)."""
    node = pair_node(A, B)
    la, _, lc, _ = arr4(A, B, node)
    n = (node_late or {}).get(node)
    n = 0.0 if n is None else float(n)
    return max(la - n, lc - n)


def ca_ring_fn(spec, plan, corner):
    """DIE-HEAD-18 (opt-in --ca-ring SPEC.json; COORD 10-28 NUMBER-CHECK-HEAD-1 finding): the BUILT clocks of a
    count-aligned ring instead of the declared common latency on both sides.  The ring in the capture partition writes
    on the FORWARDED clock and reads on its own clock, so for a launch tap A (partition type ts) -> capture tap B (td):
        writer clock = A + fwd_out(ts) [clk port -> fclk_out_o] + fwd_wire + fclk_in(td) [fclk_in_i -> ring writer CK]
        reader clock = B + reader(td)                       [clk port -> ring reader CK (slot select / guards / rp)]
    and d = reader - writer shifts the tap-level interval by (reader_early - writer_late, reader_late - writer_early).
    SPEC = {"types": {TYPE: {CORNER: {"fwd_out_ps": [early, late], "fclk_in_ps": [early, late],
                                      "reader_ps": [early, late]}}},
            "fwd_wire_ps": {CORNER: [early, late]}  (die-level fclk_out_o -> fclk_in_i wire, default [0, 0]),
            "source": "..."}  (each [early, late] = min early / max late arrival over the routed flops/pins).
    A pair whose launch type has no fwd_out or whose capture type has no fclk_in/reader keeps the declared common
    latency on both sides (returns None = unchanged) and is counted 'declared' in the record.  Returns the callable
    (A, B) -> (shift_lo, shift_hi) | None; plan = the die plan (partition name -> type)."""
    spec = spec if isinstance(spec, dict) else json.loads(Path(spec).read_text())
    plan = plan if isinstance(plan, dict) else json.loads(Path(plan).read_text())
    ptype = {p["name"]: p["type"] for p in plan.get("partitions", [])}
    T = spec.get("types", {})
    w = [float(x) for x in (spec.get("fwd_wire_ps") or {}).get(corner, (0.0, 0.0))]

    def fn(A, B):
        s = T.get(ptype.get(A["part"]), {}).get(corner) or {}
        d = T.get(ptype.get(B["part"]), {}).get(corner) or {}
        if "fwd_out_ps" not in s or "fclk_in_ps" not in d or "reader_ps" not in d:
            return None
        we = float(s["fwd_out_ps"][0]) + w[0] + float(d["fclk_in_ps"][0])
        wl = float(s["fwd_out_ps"][1]) + w[1] + float(d["fclk_in_ps"][1])
        return float(d["reader_ps"][0]) - wl, float(d["reader_ps"][1]) - we
    fn.spec = spec
    return fn


def count_align_d_intervals(landed, taps, cppr_range=None, part_region=None, ocv=None, stats=None, edge="rise", ring=None):
    """THE count-aligned crossing phase interval (DIE-HEAD-5, COORD 00:22 follow-up: ONE interval model for planner and
    STA): {'srcpart->dstpart': (d_lo, d_hi)} over EVERY landed tap pair of the partition pair, d = capture clock - launch
    clock, d_lo = min(capture early - launch late), d_hi = max(capture late - launch early) (arr4 at the pair's last
    common node).  CPPR (12.4b, as every related-pair class): with cppr_range (meta cppr_node_range_ps) the common-path
    credit min(range at the last common node, launch late-early, capture late-early) narrows both ends; without
    --cppr-lca + tap tree_path that node is the die root 'h' (credit ~0).  count_align_landed gates on it;
    count_align_plan --sta-proof plans on it (sta_d_intervals).
    part_region (DIE-QC-5, opt-in --count-align-key region): {partition: clock region}; the interval is then keyed
    'srcregion->dstregion' over every landed tap pair of the REGION pair, as the bind keys its crossings when a region
    holds several partitions (QC grp maps).  A partition missing from it raises (fail closed).
    ocv (CA-OCV-1, METHODOLOGY 12.14a "crossing margin counted after OCV + droop", ONE SHARED DIE TIMING MODEL): the
    SAME per-pair clock variation callable (a, b, check) -> ps the intra/seam classes get (clock_ocv_fn table/flat incl.
    the shared-droop rule, + signed-mesh U, or --pair-unc).  It widens the interval by exactly one variation term:
    d_lo -= ocv(a, b, 'setup') (launch late, capture early), d_hi += ocv(a, b, 'hold') (capture late, launch early).
    The OpenSTA late/early tap arrivals carry no derate/AOCV (no set_timing_derate in the exports; the late-early spread
    is the liberty pin-capacitance range, CLOCK-MESH-2), so this is not a double count.  None = no variation term
    (pre-CA-OCV-1 interval; the record labels it).  stats: optional dict, filled {tag: [max ocv setup, max ocv hold]}.
    edge (FLOW-ONEMODEL-1): the capture flop's sampling edge, see ca_pair_interval (fall: measured fall arrival)."""
    dsta = {}
    for a, b, tag in landed:
        A, B = taps[a], taps[b]
        if part_region is not None:
            tag = f"{part_region[A['part']]}->{part_region[B['part']]}"
        lo, hi, os_, oh = (ca_pair_interval(A, B, a, b, cppr_range, ocv, edge) if ring is None else
                             ca_pair_interval(A, B, a, b, cppr_range, ocv, edge, ring))
        if ocv is not None and stats is not None:
            m = stats.setdefault(tag, [0.0, 0.0])
            m[0], m[1] = max(m[0], os_), max(m[1], oh)
        o = dsta.get(tag)
        dsta[tag] = (lo, hi) if o is None else (min(o[0], lo), max(o[1], hi))
    return dsta


def _port_owners(ports, part_region):
    reg = (lambda p: p) if part_region is None else (lambda p: part_region[p])
    named, byreg = defaultdict(list), defaultdict(list)
    for pid, c in ports.items():
        if c.get("src_part") is not None and c.get("dst_part") is not None:
            named[(c["src_part"], c["dst_part"])].append(pid)
        byreg[(c["src"], c["dst"])].append(pid)

    def owners(A, B):
        sp, dp = A["part"], B["part"]
        rk = (reg(sp), reg(dp))
        return named.get((sp, dp)) or byreg.get(rk), f"{rk[0]}->{rk[1]}"
    return owners


def count_align_port_intervals(ports, landed, taps, cppr_range=None, part_region=None, ocv=None, stats=None,
                               edge="rise", ring=None):
    """FLOW-ONEMODEL-1: THE per-crossing interval the planner (count_align_plan --sta-proof) and the gate
    (die_sta_related --count-align) both use.  ports = {port: {src, dst[, src_part, dst_part]}}; part_region =
    {partition: region} (None: src/dst are partitions, the default 'part' key).
    Each landed tap pair belongs to the crossing(s) that carry it:
      * the ports that NAME its partition pair (src_part -> dst_part), else
      * every port of its REGION pair (a region-level crossing carries all partition pairs nobody names).
    A port's interval is the union over its tap pairs (ca_pair_interval), so a crossing is timed on its own
    clock pins and never on another crossing's (DIE-KV-11: a region-key union put the 12 pc_WN_3->pc_WN_2 ports'
    early bound on the phy_WN_3->phy_WN_2 ring, 61.8 ps below the plan).  Landed pairs of a region pair with no port
    are returned as unbound (fail closed by the caller).  Returns ({port: (lo, hi)}, unbound_tags, {port: n_pairs});
    stats (optional) gets {port: [max ocv setup, max ocv hold]}.
    edge 'fall' (FLOW-ONEMODEL-1): capture on the MEASURED fall arrival (ca_pair_interval); a port with any capture
    tap lacking it maps to None (the caller fails it closed / never plans a fall sample on it)."""
    own = _port_owners(ports, part_region)
    iv, npairs, unbound, nofall = {}, defaultdict(int), set(), set()
    for a, b, _ in landed:
        A, B = taps[a], taps[b]
        owners, rt = own(A, B)
        if not owners:
            unbound.add(rt)
            continue
        try:
            lo, hi, os_, oh = (ca_pair_interval(A, B, a, b, cppr_range, ocv, edge) if ring is None else
                             ca_pair_interval(A, B, a, b, cppr_range, ocv, edge, ring))
        except FallArrivalMissing:
            nofall.update(owners)
            continue
        for pid in owners:
            o = iv.get(pid)
            iv[pid] = (lo, hi) if o is None else (min(o[0], lo), max(o[1], hi))
            npairs[pid] += 1
            if ocv is not None and stats is not None:
                m = stats.setdefault(pid, [0.0, 0.0])
                m[0], m[1] = max(m[0], os_), max(m[1], oh)
    for pid in nofall:
        iv[pid] = None
    return iv, sorted(unbound), dict(npairs)


def count_align_port_unshared(ports, landed, taps, part_region=None, node_late=None):
    """CLK-INV-CAL-1 wander rule: {port: max ca_pair_unshared over the tap pairs the port carries} with the same
    ownership as count_align_port_intervals (named partition pair, else its region pair); planner
    (sta_port_intervals) and gate (count_align_landed) both use it."""
    own = _port_owners(ports, part_region)
    out = {}
    for a, b, _ in landed:
        A, B = taps[a], taps[b]
        owners, _ = own(A, B)
        if not owners:
            continue
        u = ca_pair_unshared(A, B, node_late)
        for pid in owners:
            out[pid] = max(out.get(pid, u), u)
    return out


def ca_ocv(proof, meta, taps, corner, lat, clock_ocv="none", clock_droop=None, droop_region="mesh",
           droop_regions_file=None, aocv_table=None, cell_share=None, clock_cell="buf"):
    """CA-OCV-1: the clock variation callable main() hands the related-pair classes and the count-aligned row
    (--clock-ocv flat/table with the --clock-droop rule and --droop-region regions); None for --clock-ocv none.
    clock_cell (CLK-INV-CAL-1): 'inv' = AOCV class Ainv for the die stages."""
    if clock_ocv == "none":
        return None
    droop = clock_droop or ("shared" if clock_ocv == "table" else "stated")
    dreg = droop_regions(proof, taps, droop_region, droop_regions_file) if droop == "shared" else None
    return clock_ocv_fn(clock_ocv, droop, dict(meta, corner=corner), taps, lat, aocv_table, cell_share=cell_share,
                        region=dreg, **({"clock_cell": clock_cell} if clock_cell != "buf" else {}))


def sta_d_intervals(proof, plan, corners=("TT", "FF"), clock_cal="none", cppr_lca=False, clock_ocv="none",
                    clock_droop=None, droop_regions_file=None, core_latency_ff=None, aocv_table=None, clock_cell="auto",
                    ca_ring=None):
    """{corner: count_align_d_intervals} exactly as main() feeds count_align_landed: tap_arrivals_<C>.json of PROOF,
    --clock-cal spice scaling (spice_cal_factor of the die clock cell), build_pairs on the plan (dict or path),
    --cppr-lca node choice.  clock_cell (CLK-INV-CAL-1, as main --clock-cell): 'auto' detects it from the proof.
    clock_ocv != 'none' (CA-OCV-1): the same clock variation term main() adds with --clock-ocv / --clock-droop /
    --droop-regions / --core-latency-ff (core latency TT = plan clock.common_latency_ps, FF = core_latency_ff or TT),
    so the planner hull and the gate share one interval model; 'none' = unchanged."""
    global CPPR_LCA
    plan = plan if isinstance(plan, dict) else json.loads(Path(plan).read_text())
    old, CPPR_LCA = CPPR_LCA, bool(cppr_lca)
    try:
        out = {}
        for c in corners:
            meta, taps = load_taps(Path(proof), c)
            cc, _ = resolve_clock_cell(clock_cell, proof, meta)
            meta, taps = apply_clock_cal(meta, taps, c, cc, clock_cal, proof=Path(proof))
            pairs, _ = build_pairs(plan, taps)
            lt = float(plan.get("clock", {}).get("common_latency_ps", 250.0))
            lat = core_latency_ff if (c == "FF" and core_latency_ff is not None) else lt
            ocv = ca_ocv(Path(proof), meta, taps, c, lat, clock_ocv, clock_droop, "mesh", droop_regions_file, aocv_table,
                         clock_cell=cc)
            ring = ca_ring_fn(ca_ring, plan, c) if ca_ring else None
            out[c] = count_align_d_intervals(pairs["landed"], taps, clock_cppr_ranges(meta), ocv=ocv,
                                             **({"ring": ring} if ring is not None else {}))
        return out
    finally:
        CPPR_LCA = old


def sta_port_intervals(proof, plan, corners, ports, part_region=None, clock_cal="none", cppr_lca=False,
                       clock_ocv="none", clock_droop=None, droop_regions_file=None, core_latency_ff=None, aocv_table=None,
                       fall=False, clock_cell="auto", ca_ring=None):
    """FLOW-ONEMODEL-1: {corner: dict(rise={port: (lo, hi)}, fall={port: (lo, hi) | None} (fall=True), unbound=[...])}
    = count_align_port_intervals on the proof exactly as main() feeds count_align_landed (same tap arrivals, spice
    scale, build_pairs, CPPR node, clock variation term).  The planner hulls on THIS; the gate times on THIS.
    clock_cell (CLK-INV-CAL-1, as main --clock-cell): 'auto' detects it from the proof (spice factor + AOCV class)."""
    global CPPR_LCA
    plan = plan if isinstance(plan, dict) else json.loads(Path(plan).read_text())
    old, CPPR_LCA = CPPR_LCA, bool(cppr_lca)
    try:
        out = {}
        for c in corners:
            meta, taps = load_taps(Path(proof), c)
            cc, _ = resolve_clock_cell(clock_cell, proof, meta)
            meta, taps = apply_clock_cal(meta, taps, c, cc, clock_cal, proof=Path(proof))
            pairs, _ = build_pairs(plan, taps)
            lt = float(plan.get("clock", {}).get("common_latency_ps", 250.0))
            lat = core_latency_ff if (c == "FF" and core_latency_ff is not None) else lt
            ocv = ca_ocv(Path(proof), meta, taps, c, lat, clock_ocv, clock_droop, "mesh", droop_regions_file, aocv_table,
                         clock_cell=cc)
            rng = clock_cppr_ranges(meta)
            ring = ca_ring_fn(ca_ring, plan, c) if ca_ring else None
            rk = {"ring": ring} if ring is not None else {}
            iv, unb, _ = count_align_port_intervals(ports, pairs["landed"], taps, rng, part_region, ocv, **rk)
            ush = count_align_port_unshared(ports, pairs["landed"], taps, part_region, meta.get("node_late_ps"))
            out[c] = dict(rise=iv, unbound=unb, unshared=ush)
            if fall:
                out[c]["fall"] = count_align_port_intervals(ports, pairs["landed"], taps, rng, part_region, ocv,
                                                            edge="fall", **rk)[0]
        return out
    finally:
        CPPR_LCA = old


def tap_leg(meta, taps):
    """START-TREE-1: median (late, early, stages) of the leg from a tap's driving tree node (tree_path minus its last
    level) to the tap pin, over the proof's taps: the clock leg of a retime flop placed on a tree node"""
    lt = [t for t in taps.values() if len(t.get("tree_path", "")) > 1 and t.get("part") is not None]
    ls = sorted(float(t["late_ps"]) - float(meta["node_late_ps"][t["tree_path"][:-1]]) for t in lt)
    es = sorted(float(t["early_ps"]) - float(meta["node_early_ps"][t["tree_path"][:-1]]) for t in lt)
    ss = sorted(int(t["stages_from_root"]) - int(meta["node_stages"][t["tree_path"][:-1]]) for t in lt)
    return ls[len(ls) // 2], es[len(es) // 2], ss[len(ss) // 2]


def tap_leg_fall(meta, taps):
    """FLOW-ONEMODEL-1: median (fall late, fall early) leg from the driving tree node's MEASURED fall arrival
    (meta node_fall_late_ps / node_fall_early_ps) to the tap's fall arrival; None if the proof has no node falls"""
    nfl, nfe = meta.get("node_fall_late_ps"), meta.get("node_fall_early_ps")
    if not isinstance(nfl, dict) or not isinstance(nfe, dict):
        return None
    lt = [t for t in taps.values() if len(t.get("tree_path", "")) > 1 and t.get("part") is not None
          and "fall_late_ps" in t and nfl.get(t["tree_path"][:-1]) is not None]
    if not lt:
        return None
    ls = sorted(float(t["fall_late_ps"]) - float(nfl[t["tree_path"][:-1]]) for t in lt)
    es = sorted(float(t["fall_early_ps"]) - float(nfe[t["tree_path"][:-1]]) for t in lt)
    return ls[len(ls) // 2], es[len(es) // 2]


def virtual_tap(meta, taps, path, leg, fleg=None):
    """START-TREE-1: the clock pin of a start retime flop on tree node `path` ('__st__<path>', added to taps): node
    arrival + leg, stages + leg stages, node xy; cppr_node 'h' (own droop region: the shared-droop term applies).
    FLOW-ONEMODEL-1: fall arrival = measured node fall arrival + fall leg (tap_leg_fall) when the proof has both,
    else none (a fall sample on that flop then fails closed)."""
    k = f"__st__{path}"
    path = path.split("@", 1)[0]  # source-specific retime flops share a node, not a physical clock pin
    if k not in taps:
        taps[k] = dict(port=k, part=None, cppr_node="h", tree_path=path,
                       late_ps=float(meta["node_late_ps"][path]) + leg[0],
                       early_ps=float(meta["node_early_ps"][path]) + leg[1],
                       stages_from_root=int(meta["node_stages"][path]) + leg[2], xy_um=meta["node_xy_um"][path])
        nfl, nfe = meta.get("node_fall_late_ps") or {}, meta.get("node_fall_early_ps") or {}
        if fleg is not None and nfl.get(path) is not None and nfe.get(path) is not None:
            taps[k]["fall_late_ps"] = float(nfl[path]) + fleg[0]
            taps[k]["fall_early_ps"] = float(nfe[path]) + fleg[1]
    return k


def count_align_start_ports(bind, taps, meta, period, cppr_range=None, ocv=None, sync_ap=26.5, clkq=(0.0, 0.0),
                            data_delay=None):
    """START-TREE-1 (METHODOLOGY 12.16b(iv)/(d)): reset release is a crossing.  Every dedicated start port of a
    '--start-tree clock' bind is re-timed on THIS proof's arrivals with the same interval model (count_align_d_intervals
    on its launch -> capture tap pair, CPPR at the last common node, the same ocv callable).  PASS iff the plan's
    sample edge is clean on the STA interval shifted by the start skew (clk->Q range; distance >= sync aperture) and the
    plan marked it clean (sync_values 1); a missing tap fails closed.
    data_delay (HEAD-START-4 V1, opt-in --count-align-start-data-delay, count_align_plan.load_start_data_delay doc):
    {port: [lo, hi]} MEASURED launch CLK -> capture D per start port; it REPLACES the clk->Q skew of that port (it
    contains the launch clk->Q), so the sync samples d - dd; a port with no measured row fails closed.  None (default):
    unchanged."""
    leg = fleg = None
    rows = []
    reg = bind.get("regions", {})
    added = [k for c in bind.get("start_ports", {}).values() for k in (c["launch"], c["capture"])
             if k and k.startswith("__st__") and k not in taps]
    for pid, c in sorted(bind.get("start_ports", {}).items()):
        ends = []
        for k in (c["launch"], c["capture"]):
            if k and k.startswith("__st__") and meta is not None and k[6:].split("@", 1)[0] in meta.get("node_late_ps", {}):
                if leg is None:
                    real = {q: t for q, t in taps.items() if not q.startswith("__st__")}
                    leg, fleg = tap_leg(meta, real), tap_leg_fall(meta, real)
                virtual_tap(meta, taps, k[6:], leg, fleg)
            ends.append(k if k in taps else None)
        r = reg.get(c["dst"], {})
        sk = clkq
        if data_delay is not None:
            sk = data_delay.get(pid)
        row = dict(port=pid, region=c["dst"], edge="fall" if r.get("edge_fall") else "rise",
                   sync_values=int(r.get("sync_values", 1)), skew_lo_ps=round(sk[0], 1) if sk else None,
                   skew_hi_ps=round(sk[1], 1) if sk else None,
                   limit_ps=r.get("start_skew_limit_ps"), source="start-port", launch=c["launch"], capture=c["capture"])
        if data_delay is not None:
            row["skew_source"] = "measured-data-delay"
            if sk is None:
                row.update(ok=False, reason="no measured START data delay (fail closed)")
                rows.append(row)
                continue
        if None in ends:
            row.update(ok=False, reason="no taps")
            rows.append(row)
            continue
        try:
            # FLOW-ONEMODEL-1: a fall-edge sync samples on the capture pin's MEASURED fall arrival (no T/2 assumption)
            iv = ca_pair_interval(taps[ends[0]], taps[ends[1]], ends[0], ends[1], cppr_range, ocv, row["edge"])[:2]
        except FallArrivalMissing:
            row.update(ok=False, reason="fall edge without a measured fall arrival (fail closed)")
            rows.append(row)
            continue
        off = period / 2 if row["edge"] == "fall" else 0.0
        elo, ehi = iv[0] - float(sk[1]), iv[1] - float(sk[0])
        k = math.floor((elo - off) / period)
        dist = min(elo - (off + k * period), off + (k + 1) * period - ehi) if math.floor((ehi - off) / period) == k \
            else -1.0
        row.update(d_lo_ps=round(iv[0], 1), d_hi_ps=round(iv[1], 1), plan_d_lo_ps=c["d_lo_ps"], plan_d_hi_ps=c["d_hi_ps"],
                   sta_sync_dist_ps=round(dist, 1), ok=row["sync_values"] == 1 and dist >= sync_ap)
        rows.append(row)
    for k in added:
        taps.pop(k, None)       # the virtual clock pins never leak into the other classes
    return rows


def count_align_landed(landed, taps, bind, period, reg=None, need_ps=100.0, start_wire=None, cppr_range=None,
                       key="part", ocv=None, ocv_label=None, meta=None, ring=None, start_data_delay=None):
    """MESO-INTEG-1 / MESO-RECONCILE-1 (opt-in --count-align BIND.json, count_align_bind.py v2): the count-aligned ring
    (ot_dp_clk_landing_ca) replaces the +-T/2 placement window by a write->read lag window per crossing.  Bind L_lo/L_hi
    are the plan's TRUE derated lag bounds (wander included, no aperture); d = capture-region clock - launch-region clock.
    This model re-derives d from ITS OWN derated arrivals over every landed tap pair of the partition pair
    (d_lo = min(capture early - launch late), d_hi = max(capture late - launch early)) and shifts the plan lag by the
    difference: L = (K + a_dst - a_src) T + d.  Ambiguous tree (start) crossings keep the plan sync window.
    Rows (each must PASS; a crossing without taps fails closed):
      lag      : margins to the ring guards 0.5T / (DEPTH - 0.5)T >= need_ps (COORD 20:35/20:48; the plan keeps ap = T/8)
      slot_read: slot -> dsel -> RDREG/r_v_q/r_lap_q.  The read edge samples a slot written >= L_lo earlier; the formal
                 proof (fv_ca2) treats reads < T/2 after the write as arbitrary, so the ring SDC max_delay T/2 - setup on
                 that path is sufficient iff L_lo - T/2 >= 0 (slot_read_ps)
      guard    : s_w/s_lap -> glo0/ghi0 (falling read edge).  The high guard is late by up to that path (ring SDC
                 max_delay T/8 = guard_budget_ps), so the high-side margin must cover it: margin_hi >= T/8
      start    : tree crossings.  skew = start arrival at the child's first sync flop - forwarded clock (word) timing
                 = clk->Q of the parent origin register + start wire - fclk wire; |skew| <= the plan's per-edge
                 start_skew_limit_ps (clean: sync_dist - sync aperture, e.g. HEAD 116 / KV 79 ps; ambiguous: tree
                 crossing margin - 100).  Wire mismatch from start_wire {port: [lo, hi]} (routed die), else 0 (the
                 start pin sits at the bus point, clock_landing_plan; source 'model-coroute').  A clean edge must also
                 keep its STA d interval (+ skew) >= the sync aperture from the sampling boundary (J chip-invariant).
    key (DIE-QC-5, opt-in --count-align-key): 'part' (default, unchanged) matches bind src/dst to the landed pair's
    PARTITIONS; 'region' maps each landed partition through bind['parts'][p]['region'] first (the bind's own map), so a
    bind whose crossings are region pairs is timed over every landed tap pair of the region pair, and every landed
    region pair without a bind crossing is listed in 'unbound' and fails closed (a landed crossing with no count-align
    ring is not timed by the half-period window in --count-align mode, so it must not pass silently).
    ocv / ocv_label (CA-OCV-1): the clock variation callable of count_align_d_intervals and its label; each row then
    carries ocv_lo_ps / ocv_hi_ps (max over the crossing's tap pairs); None keeps the pre-CA-OCV-1 interval and the
    record says clock_variation 'none'."""
    ap = period / 8
    sap = float(bind.get("sync_aperture_ps", 26.5))
    cq_max = float(reg["clkq_max_wire_ps"]) if reg else 0.0
    cq_min = float(reg["clkq_min_nowire_ps"]) if reg else 0.0
    pr = None
    if key == "region":
        pr = {p: v["region"] for p, v in (bind.get("parts") or {}).items() if isinstance(v, dict) and v.get("region")}
        lost = sorted({taps[x]["part"] for a_, b_, _ in landed for x in (a_, b_)} - set(pr))
        if lost:
            raise SystemExit(f"--count-align-key region: bind parts lacks a region for {len(lost)} landed partitions "
                             f"(e.g. {lost[:5]})")
    elif key != "part":
        raise SystemExit(f"--count-align-key: unknown key {key!r}")
    ost = {}
    # FLOW-ONEMODEL-1: per-port intervals (count_align_port_intervals), the SAME function count_align_plan --sta-proof
    # hulls on: a port is timed over the tap pairs it carries (its named partition pair, else its region pair)
    nl = (meta or {}).get("node_late_ps")
    ush = {} if isinstance(nl, dict) else None
    dsta, unbound, _ = count_align_port_intervals(bind["ports"], landed, taps, cppr_range, part_region=pr, ocv=ocv,
                                                  stats=ost, **({"ring": ring} if ring is not None else {}))
    rstat = None
    if ring is not None:
        # DIE-HEAD-18 --ca-ring: per port, are ALL its tap pairs on built ring clocks ('built') or not ('declared')
        own = _port_owners(bind["ports"], pr)
        rstat, shifts = {}, {}
        for a_, b_, _ in landed:
            owners, _ = own(taps[a_], taps[b_])
            sh = ring(taps[a_], taps[b_])
            for pid in owners or ():
                rstat[pid] = rstat.get(pid, True) and sh is not None
                if sh is not None:
                    o = shifts.get(pid)
                    shifts[pid] = sh if o is None else (min(o[0], sh[0]), max(o[1], sh[1]))
    if ush is not None:
        ush = count_align_port_unshared(bind["ports"], landed, taps, pr, nl)
    # CLK-INV-CAL-1 / COORD 10-28: post-start wander = wander_frac x the worst unshared clock over the crossing's OWN
    # tap pairs (ca_pair_unshared, as the planner); a bind planned with less wander is widened by the difference
    wfrac = float(bind.get("wander_frac", (bind.get("summary") or {}).get("wander_frac", 0.05)))
    tree_reg = {r["tree_port"]: (x, r) for x, r in bind.get("regions", {}).items() if r.get("tree_port")}
    dfall = None
    if any(r.get("edge_fall") for _, r in tree_reg.values()):
        dfall = count_align_port_intervals({p: bind["ports"][p] for p in tree_reg if p in bind["ports"]}, landed, taps,
                                           cppr_range, part_region=pr, ocv=ocv, edge="fall",
                                           **({"ring": ring} if ring is not None else {}))[0]
    rows, miss, srows = [], [], []
    for pid, b in sorted(bind["ports"].items()):
        tag = f"{b['src']}->{b['dst']}"
        D = int(b["depth"])
        tr = tree_reg.get(pid)
        amb_tree = bool(tr) and int(tr[1].get("sync_values", 1)) > 1
        if dsta.get(pid) is None or "d_lo_ps" not in b:
            miss.append(pid)
            continue
        dl, dh = dsta[pid]
        if amb_tree:
            lo, hi, src = b["L_lo_ps"], b["L_hi_ps"], "plan-sync"
        else:
            lo, hi, src = b["L_lo_ps"] + (dl - b["d_lo_ps"]), b["L_hi_ps"] + (dh - b["d_hi_ps"]), "sta"
        dw = 0.0
        if ush is not None and pid in ush:
            dw = max(0.0, wfrac * ush[pid] - float(b.get("wander_ps", 0.0)))
            lo, hi = lo - dw, hi + dw
        ml, mh = lo - 0.5 * period, (D - 0.5) * period - hi
        row = dict(port=pid, tag=tag, depth=D, tree=bool(tr), L_lo_ps=round(lo, 1), L_hi_ps=round(hi, 1),
                   margin_lo_ps=round(ml, 1), margin_hi_ps=round(mh, 1), source=src,
                   slot_read_ps=round(lo - 0.5 * period, 1), guard_budget_ps=round(ap, 1),
                   guard_hi_slack_ps=round(mh - ap, 1))
        if ush is not None and pid in ush:
            row["wander_ps"] = round(float(b.get("wander_ps", 0.0)) + dw, 1)
            row["wander_widen_ps"] = round(dw, 1)
        if ocv is not None and src == "sta":
            row["ocv_lo_ps"], row["ocv_hi_ps"] = (round(x, 1) for x in ost.get(pid, (0.0, 0.0)))
        if rstat is not None:
            row["ring"] = "built" if rstat.get(pid) else "declared"
            if pid in shifts:
                row["ring_shift_ps"] = [round(shifts[pid][0], 1), round(shifts[pid][1], 1)]
        row["lag_ok"] = min(ml, mh) >= need_ps
        if amb_tree and tr[1].get("edge_fall"):
            # FLOW-ONEMODEL-1: an ambiguous tree crossing's lag window is the plan sync window, which places the fall
            # sample at rise + T/2; with measured duty distortion that is not a bound -> fail closed
            row.update(lag_ok=False, reason="ambiguous fall-edge tree crossing (sync window assumes fall = rise + T/2)")
        row["slot_read_ok"] = row["slot_read_ps"] >= 0
        row["guard_ok"] = row["guard_hi_slack_ps"] >= 0
        rows.append(row)
        if tr:
            x, rg = tr
            w = (start_wire or {}).get(pid)
            wl, wh = (float(w[0]), float(w[1])) if w else (0.0, 0.0)
            sk_lo, sk_hi = cq_min + wl, cq_max + wh
            lim = rg.get("start_skew_limit_ps")
            s = dict(port=pid, region=x, edge="fall" if rg.get("edge_fall") else "rise",
                     sync_values=int(rg.get("sync_values", 1)), skew_lo_ps=round(sk_lo, 1), skew_hi_ps=round(sk_hi, 1),
                     limit_ps=lim, source="routed" if w else "model-coroute")
            ok = lim is not None and max(abs(sk_lo), abs(sk_hi)) <= lim
            if s["sync_values"] == 1:
                # J chip-invariant on the STA's own d: the effective sampled phase d - skew keeps >= sap from off + kT
                off = period / 2 if s["edge"] == "fall" else 0.0
                sl, sh = dl, dh
                if s["edge"] == "fall":
                    # FLOW-ONEMODEL-1: the fall sample is timed on the MEASURED fall arrival, never rise + T/2
                    fv = (dfall or {}).get(pid)
                    if fv is None:
                        s.update(ok=False, reason="fall edge without a measured fall arrival (fail closed)")
                        srows.append(s)
                        continue
                    sl, sh = fv
                elo, ehi = sl - sk_hi, sh - sk_lo
                k = math.floor((elo - off) / period)
                dist = min(elo - (off + k * period), off + (k + 1) * period - ehi)
                s["sta_sync_dist_ps"] = round(dist, 1)
                ok = ok and dist >= sap
            s["ok"] = ok
            srows.append(s)
    if bind.get("start_ports"):
        # START-TREE-1: dedicated start ports (--start-tree clock) are checked as crossings on this proof
        srows += count_align_start_ports(bind, taps, meta, period, cppr_range, ocv, sap, (cq_min, cq_max),
                                         **({"data_delay": start_data_delay} if start_data_delay is not None else {}))
    nfail = sum(1 for r in rows if not r["lag_ok"])
    sfail = sum(1 for s in srows if not s["ok"])
    rfail = sum(1 for r in rows if not r["slot_read_ok"])
    gfail = sum(1 for r in rows if not r["guard_ok"])
    wl = min(rows, key=lambda r: r["margin_lo_ps"]) if rows else None
    wh = min(rows, key=lambda r: r["margin_hi_ps"]) if rows else None
    ltags = {f"{(pr or {}).get(taps[a_]['part'], taps[a_]['part'])}->{(pr or {}).get(taps[b_]['part'], taps[b_]['part'])}"
             for a_, b_, _ in landed}
    unbound = unbound if key == "region" else []
    ok = rows and not (nfail or sfail or rfail or gfail or miss or unbound)
    ringrec = None
    if rstat is not None:
        nb = sum(1 for r in rows if r.get("ring") == "built")
        dcl = [r for r in rows if r.get("ring") == "declared"]
        ringrec = dict(form="built ring clocks (--ca-ring): writer = fwd_out + fwd_wire + fclk_in, reader = reader",
                       source=(getattr(ring, "spec", None) or {}).get("source"), built_ports=nb,
                       declared_ports=len(dcl), declared_examples=[r["port"] for r in dcl[:10]],
                       worst_lo_built=min((r["margin_lo_ps"] for r in rows if r.get("ring") == "built"), default=None),
                       worst_hi_built=min((r["margin_hi_ps"] for r in rows if r.get("ring") == "built"), default=None),
                       worst_lo_declared=min((r["margin_lo_ps"] for r in dcl), default=None),
                       worst_hi_declared=min((r["margin_hi_ps"] for r in dcl), default=None))
    return dict(clock_variation=(ocv_label or "callable") if ocv is not None else "none", ring=ringrec,
                ocv_max_lo_ps=round(max((v[0] for v in ost.values()), default=0.0), 1) if ocv is not None else None,
                ocv_max_hi_ps=round(max((v[1] for v in ost.values()), default=0.0), 1) if ocv is not None else None,
                below_need=sum(1 for r in rows if min(r["margin_lo_ps"], r["margin_hi_ps"]) < need_ps),
                key=key, interval="port (FLOW-ONEMODEL-1 count_align_port_intervals)", landed_tags=len(ltags),
                unbound=len(unbound), unbound_tags=unbound[:20], crossings=len(rows), sta_timed=sum(r["source"] == "sta" for r in rows),
                tree_plan=sum(r["source"] == "plan-sync" for r in rows), no_taps=len(miss), no_taps_ports=miss[:20],
                need_ps=need_ps, aperture_ps=round(ap, 3), fail=nfail, worst_lo=wl, worst_hi=wh,
                slot_read=dict(fail=rfail, worst_ps=min((r["slot_read_ps"] for r in rows), default=None),
                               sdc="ring slot->RDREG/r_v_q/r_lap_q max_delay T/2 - setup"),
                guard=dict(fail=gfail, budget_ps=round(ap, 1),
                           worst_hi_slack_ps=min((r["guard_hi_slack_ps"] for r in rows), default=None),
                           sdc="ring s_w/s_lap -> glo0/ghi0 max_delay T/8"),
                start_skew=dict(tree_ports=len(srows), fail=sfail,
                                clkq_ps=[round(cq_min, 1), round(cq_max, 1)],
                                worst=min(srows, key=lambda s: (s["limit_ps"] if s["limit_ps"] is not None else -1e9)
                                          - max(abs(s["skew_lo_ps"] or 0.0), abs(s["skew_hi_ps"] or 0.0)))
                                if srows else None,
                                **({"data_delay_ports": len(start_data_delay)} if start_data_delay is not None else {}),
                                rows=srows),
                verdict="PASS" if ok else "FAIL", rows=rows)


def build_pairs(plan, taps):
    """complete pair sets from the plan ports and the tap table (one corner's rows; ports are corner independent)."""
    by_part = defaultdict(list)
    # DIE-HEAD-13 10-28: a tap with part None is a die-level start stage (start_stage_emit '__st__<path>' / virtual_tap):
    # it belongs to no partition, so it never forms intra/seam pairs (HEAD: 193 stage taps were grouped as ONE
    # 'partition' None -> 193 x 192 = 37056 false die-wide intra pairs, setup -5350 / hold -5992 ps). Their related
    # timing is the count-align start-skew check (stage -> stage along the start tree).
    unpart = 0
    for p, r in taps.items():
        if r.get("part") is None:
            unpart += 1
            continue
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
        partitions_with_taps=len(by_part), connected_part_pairs=len(conn), uncovered_bits=dict(uncovered),
        **({"start_stage_taps_no_pairs": unpart} if unpart else {}))


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
    if not (d / "mesh.json").exists():          # e.g. a qc_clk_mesh3 sta-export proof / S81 region-tree proof (as main)
        print("nearest-tap INFO classes skipped (no mesh.json)", file=sys.stderr)
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


def seam_bits(d, plan_path, tool, taps):
    """{(src tap, dst tap): bits} from DC.seam_pairs (nearest tap under each pin register), for the HB4 cell count."""
    if tool:
        sys.path.insert(0, str(Path(tool)))
    import die_clock as DC
    import schema as S
    M = json.loads((d / "mesh.json").read_text())
    tb = defaultdict(list)
    for t in M["taps"]:
        if t["port"] in taps:
            tb[t["part"]].append(dict(port=t["port"], part=t["part"], xy=t["xy"]))
    out = defaultdict(int)
    for (a_, b_, pid), n in DC.seam_pairs(S.Plan(S.load(plan_path)), tb).items():
        out[(a_, b_)] += n
    return dict(out)


def endpoint_slacks(A, B, la, ea, lc, ec, cr, period, unc_s, unc_h, models_a, models_b, dd=None):
    """[(setup, hold, real, ma, mb)] over every launch model x capture model (REAL VIEWS).  Model: name, real,
    lat_late, lat_early (clock pin latency below the tap), clkq_max/min (launch arcs), setup/hold (capture arcs).
    dd: data droop fractions {'logic', 'wire'} (12.4a b2): setup only, never hold."""
    out = []
    for ma in models_a:
        al = la + ma["lat_late"] + ma["clkq_max"]
        ae = ea + ma["lat_early"] + ma["clkq_min"]
        for mb in models_b:
            s = (ec + mb["lat_early"] + period - mb["setup"]) - al - unc_s + cr
            if dd is not None:
                s -= DD.model_late_ps(ma, mb, dd)
            h = ae - (lc + mb["lat_late"] + mb["hold"]) - unc_h + cr
            out.append((s, h, ma["real"] or mb["real"], ma["name"], mb["name"], ma["real"] and mb["real"]))
    return out


def time_class(pairs, taps, rng, reg, lat_tol, period, unc_s, unc_h, landed=False, window=None, hold_window=None,
               ocv=None, views=None, rec=None, dd=None, kit_offset=None, missing=None):
    """ocv: optional callable (a_port, b_port, check) -> clock OCV pessimism ps on the non-common clock (CLK-AOCV,
    opt-in --clock-ocv); None = unchanged (no clock derate in this gate).
    views: optional {port: [endpoint models]} (REAL VIEWS, opt-in); None = the declared register on every tap.
    rec: optional dict, filled {(a, b, tag): (gate setup, gate hold, has real endpoint, both real)} (HB4, opt-in).
    dd: optional data droop fractions {'logic', 'wire'} (12.4a b2, data_droop.fracs): late data derate on SETUP only;
    None = unchanged (no data droop term).
    kit_offset: optional {port: ps} (FLOW-ONEMODEL-3): the kit SDC source latency of an early core tap is -early
    (gen_phys core_tap_rows), so the kit contract measures each tap's arrival + its declared earliness: a core tap
    delivered as planned is damage-free, a LATE core tap (not early enough) is charged.  None = unchanged.
    missing: optional {port: [labels]} (FLOW-HOLD-1, OWNER 12.19, missing_views): adds 'hold_measured' = hold over the
    pairs whose both endpoints carry signed real views only, + measured/unmeasured counts + the missing views."""
    ws, wh, sk, rows = None, None, 0.0, []
    sk_raw, trows = 0.0, []
    rv = dict(pairs=0, ws=None, wh=None, nneg_s=0, nneg_h=0, both=0, bs=None, bh=None, bneg_s=0, bneg_h=0,
              dmg=[]) if views is not None else None
    ocv_max = {"setup": 0.0, "hold": 0.0}
    nneg_s = nneg_h = 0
    mds = mdh = float('-inf')
    dd_reg = DD.model_late_ps(dict(clkq_max=reg["clkq_max_wire_ps"]), dict(name="budget", setup=reg["setup_ps"]), dd) \
        if dd is not None else 0.0
    dd_max = 0.0
    hm = dict(n=0, u=0, wh=None, neg=0, miss=defaultdict(int)) if missing is not None else None
    for a, b, tag in pairs:
        A, B = taps[a], taps[b]
        node = pair_node(A, B)
        la, ea, lc, ec = arr4(A, B, node)
        cr = credit(rng, node, la, ea, lc, ec)
        dmg_s, dmg_h = la - ec - cr, lc - ea - cr
        if views is None:
            s = period - unc_s - (la + reg["clkq_max_wire_ps"]) + (ec - reg["setup_ps"]) + cr - dd_reg
            h = (ea + reg["clkq_min_nowire_ps"]) - (lc + reg["hold_ps"]) - unc_h + cr
            dd_max = max(dd_max, dd_reg)
        else:
            ma, mb = views[a], views[b]
            combos = endpoint_slacks(A, B, la, ea, lc, ec, cr, period, unc_s, unc_h, ma, mb, dd=dd)
            if dd is not None:
                dd_max = max(dd_max, max(DD.model_late_ps(x, y, dd) for x in ma for y in mb))
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
        if rec is not None:
            if views is None:
                rec[(a, b, tag, "budget", "budget")] = (s, h, False, False)
            else:
                # CLOCK-KV-R19 (NUMBER-CHECK-KV-R18): one record PER ENDPOINT PATH (launch model x capture model).  HB4
                # cells sit on one capture register's data input and are sized from THAT path's hold; R18 keyed per tap
                # pair, sized k from the worst endpoint (declared budget->budget) and charged it to another endpoint's
                # (real core) setup -> 121 artefact negatives.
                po_s, po_h = (ocv(a, b, "setup"), ocv(a, b, "hold")) if ocv is not None else (0.0, 0.0)
                for c_ in combos:
                    rec[(a, b, tag, c_[3], c_[4])] = (c_[0] - po_s, c_[1] - po_h, c_[2], c_[5])
        nneg_s += s < 0
        nneg_h += h < 0
        if hm is not None:
            lab = set(missing.get(a) or ()) | set(missing.get(b) or ())
            if lab:
                hm["u"] += 1
                for x in lab:
                    hm["miss"][x] += 1
            else:
                hm["n"] += 1
                hm["neg"] += h < 0
                if hm["wh"] is None or h < hm["wh"][0]:
                    hm["wh"] = (h, a, b, tag, dmg_h, cr)
        sk_raw = max(sk_raw, dmg_s, dmg_h)
        # DIE-S81-18 (COORD 10-28 21:33 rule 2): skew = arrival minus PLANNED target.  A planned early core tap is
        # delivered kit_offset (= its declared earliness) before the plain taps on purpose; its target-relative arrival
        # is arrival + earliness, so designed earliness is not counted as skew (go15: raw 925 vs real 523.8 TT).
        # Dies without early core taps: ko = 0, identical to the raw number.
        ko = (kit_offset.get(b, 0.0) - kit_offset.get(a, 0.0)) if kit_offset else 0.0
        tdm_s, tdm_h = dmg_s - ko, dmg_h + ko
        sk = max(sk, tdm_s, tdm_h)
        trows.append((max(tdm_s, tdm_h), a, b))
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
               skew_diag_max_ps=round(sk, 2), skew_diag_over_80=sum(1 for r in trows if r[0] > 80.0),
               skew_diag_basis=("arrival minus planned target (early core tap + its declared earliness)" if kit_offset
                                else "raw tap arrival (no planned early core taps)"),
               skew_raw_max_ps=round(sk_raw, 2),
               sens_core_tol=dict(tol_ps=lat_tol, worst_setup_slack_ps=round(ws[0] - 2 * lat_tol, 2),
                                  worst_hold_slack_ps=round(wh[0] - 2 * lat_tol, 2)),
               worst_skew=[[round(v, 2), a, b] for v, a, b in sorted(trows, reverse=True)[:5]])
    if hm is not None:
        out["hold_measured"] = dict(
            rule="OWNER 12.19 (FLOW-HOLD-1): hold judged on pairs whose BOTH endpoint blocks have a signed real view; "
                 "others UNMEASURED (not tap-window failures); PASS needs 0 unmeasured and every measured >= 0",
            pairs_measured=hm["n"], pairs_unmeasured=hm["u"],
            hold_margin_ps=round(hm["wh"][0], 2) if hm["wh"] else None, neg_pairs=int(hm["neg"]),
            worst=dict(launch=hm["wh"][1], capture=hm["wh"][2], where=hm["wh"][3], clock_damage_ps=round(hm["wh"][4], 2),
                       cppr_ps=round(hm["wh"][5], 2)) if hm["wh"] else None,
            missing_views=dict(sorted(hm["miss"].items())))
        out["hold_measured"]["status"] = hold_status(out["hold_measured"])
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
    if dd is not None:
        out["data_droop_setup_max_ps"] = round(dd_max, 2)
    if hold_window is not None:
        hd = []
        for a, b, tag in pairs:
            A, B = taps[a], taps[b]
            node = pair_node(A, B)
            la, ea, lc, ec = arr4(A, B, node)
            cr = credit(rng, node, la, ea, lc, ec)
            ko = (kit_offset.get(b, 0.0) - kit_offset.get(a, 0.0)) if kit_offset else 0.0
            hd.append((lc - ea - cr + ko, a, b, tag))
        hd.sort(reverse=True)
        w = float(hold_window["ps"])
        out["kit_contract_hold"] = dict(
            window_ps=w, basis=hold_window["basis"], worst_hold_bound_ps=round(w - hd[0][0], 2),
            neg_pairs=sum(1 for v in hd if v[0] > w), window_needed_ps=round(max(0.0, hd[0][0]), 2),
            worst=dict(launch=hd[0][1], capture=hd[0][2], where=hd[0][3], damage_ps=round(hd[0][0], 2)),
            damage_pctl_ps={q: round(hd[min(len(hd) - 1, int(len(hd) * (1 - q / 100.0)))][0], 2) for q in (50, 99, 99.9)},
            verdict="PASS" if hd[0][0] <= w else "FAIL")
        if kit_offset:
            out["kit_contract_hold"]["core_tap_offset"] = dict(
                taps=len(kit_offset), basis="kit SDC set_clock_latency -source -early_ps on each early core tap "
                "(gen_phys core_tap_rows): arrival + declared earliness")
        if ocv is not None:
            # INFRA-FIRST-QC-R18 (additive, gate unchanged): the kit contract only holds if the die delivers the tap
            # pair INSIDE the window including the clock OCV (pair MC mesh skew + AOCV below the mesh) that the
            # zero-logic slack charges; the bound above uses the nominal damage only.  residual_ps = what die-level
            # data hold buffers must still cover per ordered pair (max(0, damage + ocv - W)).
            ho = sorted(((v + ocv(a, b, "hold"), a, b, tag) for v, a, b, tag in hd), reverse=True)
            res = [(round(v - w, 2), a, b) for v, a, b, _ in ho if v > w]
            out["kit_contract_hold_ocv"] = dict(
                window_ps=w, worst_hold_bound_ps=round(w - ho[0][0], 2), neg_pairs=len(res),
                window_needed_ps=round(max(0.0, ho[0][0]), 2),
                worst=dict(launch=ho[0][1], capture=ho[0][2], where=ho[0][3], damage_plus_ocv_ps=round(ho[0][0], 2)),
                damage_plus_ocv_pctl_ps={q: round(ho[min(len(ho) - 1, int(len(ho) * (1 - q / 100.0)))][0], 2)
                                         for q in (50, 90, 99)},
                residual_ps=res, verdict="PASS" if ho[0][0] <= w else "FAIL",
                note="R18 additive: kit window vs nominal damage + clock OCV (pair_unc); INFO until COORD rules")
    if landed:
        out["plan_landing"] = dict(window_ps=round(window, 2), setup_margin_ps=round(window - mds, 2),
                                   hold_margin_ps=round(window - mdh, 2),
                                   damage_max_ps=round(max(r[0] for r in rows), 2),
                                   verdict="PASS" if max(r[0] for r in rows) <= window else "FAIL",
                                   note="plan-defined landed/forwarded hop: region-to-region clock damage vs landing "
                                        "window; single-cycle slacks above are INFO for landed pairs")
    return out


def landed_gate(corners):
    """Summary gate for the landed class from {corner: {"classes": {...}}}.  A die with one clock region has 0 landed
    pairs in both TT and FF (time_class returns pairs=0, no plan_landing): an empty class -> verdict N/A, not FAIL.
    Fail closed: landed pairs in either corner with plan_landing missing (or not PASS) in either corner -> FAIL."""
    cl = {c: (corners.get(c) or {}).get("classes", {}).get("landed") or {} for c in ("TT", "FF")}
    if not any(cl[c].get("pairs") for c in cl):
        return dict(tt_setup_margin_ps=None, ff_hold_margin_ps=None, pairs=0, verdict="N/A",
                    note="no landed pairs (single clock region)")
    lt, lf = cl["TT"].get("plan_landing") or {}, cl["FF"].get("plan_landing") or {}
    return dict(tt_setup_margin_ps=lt.get("setup_margin_ps"), ff_hold_margin_ps=lf.get("hold_margin_ps"),
                verdict="PASS" if lt.get("verdict") == "PASS" and lf.get("verdict") == "PASS" else "FAIL")


def is_start_virtual_tap(r):
    """DIE-HEAD-29: a virtual START tap = a die-level start retime / start stage flop clock pin, outside every hard core:
    part None AND port '__st__<path>' (virtual_tap, start_stage_emit).  Every other tap (partition / hard-core taps, and
    any part-None tap without the '__st__' name) is not one, so its clock OCV branch is unchanged."""
    return r.get("part") is None and str(r.get("port", "")).startswith("__st__")


def clock_ocv_fn(mode, droop, meta, taps, core_lat, table_path=None, margins_path=None, cell_share=None, region=None,
                 clock_cell="buf"):
    """CLK-AOCV (METHODOLOGY 12.4a b1, DRAFT, opt-in): per pair clock OCV pessimism on the branches below the last
    common node.  Needs per-tap 'stages_from_root' + 'xy_um' and per-node meta 'node_stages' / 'node_xy_um' plus the
    node arrivals 'node_late_ps' / 'node_early_ps' in tap_arrivals_<C>.json (CLOCK-128-R7 --aocv-fold export names;
    CLOCK-128-R8); refuses when they are missing.
    Branch = tap arrival - node arrival (+ declared core latency, class-B stages), cell share from the table (class A
    die stage) unless cell_share is given.  DIE-HEAD-29 (COORD RULING 10-29 10:01): a virtual START tap
    (is_start_virtual_tap: part None, '__st__' port) carries no core latency / class-B stages; every other tap keeps them
    (per tap: a virtual -> core pair charges the core latency on the core side only).
    mode 'flat' = die_ci_margins.json cell/net derates, 'table' = clk_aocv.
    droop 'stated' = +5.1 % late on the late branch always; 'shared' = 0 when both taps share a droop region, else
    +5.1 %.  region: {port: mesh/PDN region} (CLOCK-KV-R17 default --droop-region mesh); a tap missing from it (or
    region None = --droop-region tree, the pre-R17 rule) uses its tree region (cppr_node != 'h').
    clock_cell (CLK-INV-CAL-1): the die stages use AOCV class CLOCK_CELL_AOCV_CLASS[clock_cell] ('buf' = A, unchanged;
    'inv' = Ainv, one stage per CKINVDCx16, cell share of that class); the table must carry the class (fail closed)."""
    import clk_aocv as CA
    here = Path(__file__).resolve().parent
    T = CA.load(table_path or here / APPROVED_AOCV_TABLE)
    m = json.loads(Path(margins_path or here / "die_ci_margins.json").read_text())
    need = [k for k in ("node_stages", "node_xy_um", "node_late_ps", "node_early_ps") if k not in meta]
    tneed = sum(1 for r in taps.values() if "stages_from_root" not in r or "xy_um" not in r)
    if need or tneed:
        raise SystemExit(f"--clock-ocv {mode}: tap_arrivals lacks {need} / {tneed} taps without stages_from_root+xy_um "
                         "(CLOCK-128 fold export must add them)")
    corner = meta.get("corner", "TT")
    B = T["classes"]["B"][corner]
    ka = CLOCK_CELL_AOCV_CLASS[clock_cell]
    if ka not in T["classes"]:
        raise SystemExit(f"--clock-ocv {mode}: clock cell {clock_cell} needs AOCV class {ka} in the table (CLK-INV-CAL-1)")
    fc = cell_share if cell_share is not None else T["classes"][ka][corner]["cell_share"]
    nB = max(1, round(core_lat / B["mu_stage_ps"]))

    def branch(r, node, late):
        own = (r.get("abs_late_ps", r["late_ps"]) if late else r.get("abs_early_ps", r["early_ps"])) if node in ("h", "__source__") \
            else (r["late_ps"] if late else r["early_ps"])
        arr = own - float(meta["node_late_ps" if late else "node_early_ps"][node])
        if is_start_virtual_tap(r):
            # DIE-HEAD-29 (COORD RULING 10-29 10:01): a virtual START tap is a die-level flop clock pin outside every
            # hard core: its branch is the die tree only, no hard-core class-B latency (core_lat, nB).
            return dict(cell_ps=fc * arr, net_ps=(1 - fc) * arr,
                        stages={ka: int(r["stages_from_root"]) - int(meta["node_stages"][node]), "B": 0})
        return dict(cell_ps=fc * arr + B["cell_share"] * core_lat, net_ps=(1 - fc) * arr + (1 - B["cell_share"]) * core_lat,
                    stages={ka: int(r["stages_from_root"]) - int(meta["node_stages"][node]), "B": nB})

    def fn(a, b, check):
        A_, B_ = taps[a], taps[b]
        node = pair_node(A_, B_)
        same = (A_["cppr_node"] == B_["cppr_node"]) if CPPR_LCA else node not in ("h", "__source__")   # droop shared = same region
        if node == "__source__":
            same = False
        if region is not None:
            ra = region.get(a, A_["cppr_node"] if A_["cppr_node"] not in ("h", "__source__") else None)
            rb = region.get(b, B_["cppr_node"] if B_["cppr_node"] not in ("h", "__source__") else None)
            same = ra is not None and ra == rb
        nxy = meta["node_xy_um"][node]
        pts = [A_["xy_um"], B_["xy_um"]] + ([nxy] if nxy is not None else [])
        d = ((max(p[0] for p in pts) - min(p[0] for p in pts)) ** 2 + (max(p[1] for p in pts) - min(p[1] for p in pts)) ** 2) ** 0.5
        # setup: launch a late, capture b early; hold: capture b late, launch a early
        ba = branch(A_, node, check == "setup")
        bb = branch(B_, node, check != "setup")
        if mode == "flat":
            return CA.flat_pessimism(m, ba, bb, check, same, droop == "shared")
        return CA.branch_pessimism(T, corner, ba, bb, d, same if droop == "shared" else False, check)
    return fn


# ---------------------------------------------------------------- SIGNED MESH (CLOCK-KV-R17, opt-in)
# CLOCK-KV-R18 (COORD RULING CLOCK-KV-R17, 12.4a a1 data hold buffers): planned HB4 insertion model.  Per cell: FF early
# +44.6 ps (hold repair) and TT late +83.0 ps (setup cost), area 0.1021 um2 (HOLD-REPAIR estimate basis, kv_hb_count.py).
HB4 = dict(cell="HB4xp67_ASAP7_75t_R", ff_early_ps=44.6, tt_late_ps=83.0, area_um2=0.1021,
           basis="HOLD-REPAIR estimate basis (CLOCK-KV-R6/R15 kv_hb_count.py), UNCHECKED")


# CLOCK-KV-R24 (NUMBER-CHECK-KV-R23 4b, COORD 10-27 06:0x (c)): the plan HB4 pair (44.6 FF / 83.0 TT) is not one
# physical form.  Own OpenSTA HB4xp67 chain stage (NC-KV-R23): ABUTTED (0 fF wire) FF min 37.41 / TT max 67.67.
# --hb4-delay abutted sizes k with the abutted FF minimum (hold holds for ANY placement of the chain, since wire only
# slows it) and charges the abutted TT stage (the planned island form: the k cells of a bit abut in a landing/hold
# island beside the capture pin register).  UNCHECKED here: NC-KV-R23 measured values, recheck before default.
HB4_ABUTTED = dict(HB4, ff_early_ps=37.41, tt_late_ps=67.67,
                   basis="NUMBER-CHECK-KV-R23 own OpenSTA HB4xp67 4-chain stage h2, abutted (0 fF wire): FF min / TT max")
_DATA_PIN_SKIP = re.compile(r"(^|_)(clk|ck|rst_n|rst|strap_[a-z]+)(\[|$)|__clk|__rst_n")


def _pin_names(doc):
    """pin names of a core pins file in either form: {"pins": [{name, ...}]} (core view) or the run pins.json list
    [{bus, bit, layer, x, y, face}] (FLOW-GEN-1 10-28: DIE-QC-10 K2b --hold-buffers HB4 crashed on .get of the list)."""
    rows = doc if isinstance(doc, list) else (doc.get("pins", []) if isinstance(doc, dict) else [])
    out = []
    for q in rows:
        if isinstance(q, str):
            out.append(q)
        elif isinstance(q, dict):
            n = q.get("name") or (f"{q['bus']}[{q['bit']}]" if q.get("bus") is not None and q.get("bit") is not None
                                  else q.get("bus"))
            out.append(str(n or ""))
    return out


def intra_bits(plan_path):
    """{partition: data pins of all its hard cores} (clock/reset/strap pins excluded), the INTRA HB4 cell-count basis:
    every core pin is registered (pin registers) and its other end is a register of the same partition under the
    partition glue tap or another core's tap.  Partition-internal glue-to-glue paths are not counted (no netlist)."""
    import schema as S
    raw = S.load(plan_path)
    P = S.Plan(raw)
    root = Path(plan_path).resolve().parent
    cache, out = {}, {}
    for n, p in P.parts.items():
        tot = 0
        for h in P.types[p["type"]].get("hard_cores", []) or []:
            pf = h.get("pins_file")
            if pf not in cache:
                f = root / pf if pf else None
                pins = _pin_names(json.loads(f.read_text())) if f and f.exists() else []
                cache[pf] = sum(1 for q in pins if not _DATA_PIN_SKIP.search(q))
            tot += cache[pf]
        out[n] = tot
    return out


def hold_buffer_model(tt, ff, bits=None, hb=HB4, part_bits=None):
    """per ENDPOINT PATH k = ceil(-FF hold / ff_early) HB4 cells on the capture data input (0 when hold >= 0); after
    insertion FF hold += k ff_early, TT setup -= k tt_late, both of THAT path (CLOCK-KV-R19, NUMBER-CHECK-KV-R18: keys
    (a, b, tag, launch_model, capture_model); never size k from one endpoint and charge it to another).
    tt/ff: {key: (setup, hold, real, both_real)} of ONE class at
    TT / FF (gate form: every endpoint model, clock OCV, mesh U).  bits: optional {(a, b): bit count} (nearest-tap
    seam bits, DC.seam_pairs) for the cell count; pairs absent from it count per pair-bit (k cells).  Returns the
    record for all / real-endpoint / both-real subsets plus the k histogram and the cell / area count."""
    import math as _m

    def blk(sel):
        ws = wh = None
        neg_s = neg_h = n = 0
        negs = []
        for key in sel:
            s_, _, _, _ = tt[key]
            _, h_, _, _ = ff[key]
            k = max(0, _m.ceil(-h_ / hb["ff_early_ps"] - 1e-9)) if h_ < 0 else 0
            s2, h2 = s_ - k * hb["tt_late_ps"], h_ + k * hb["ff_early_ps"]
            n += 1
            if s2 < 0:
                negs.append((round(s2, 2), key[0], key[1], key[2], k, round(s_, 2), round(h_, 2)))
            neg_s += s2 < 0
            neg_h += h2 < 0
            if ws is None or s2 < ws[0]:
                ws = (s2, key, k, s_)
            if wh is None or h2 < wh[0]:
                wh = (h2, key, k)
        if not n:
            return dict(pairs=0)
        return dict(pairs=n, tt_setup_after_ps=round(ws[0], 2), setup_neg_pairs_after=int(neg_s),
                    worst_setup_after=dict(launch=ws[1][0], capture=ws[1][1], where=ws[1][2], hb4_cells=ws[2],
                                           setup_before_ps=round(ws[3], 2),
                                           endpoint=list(ws[1][3:5]) if len(ws[1]) > 3 else None),
                    ff_hold_after_ps=round(wh[0], 2), hold_neg_pairs_after=int(neg_h),
                    setup_neg_after=[dict(zip(("tt_setup_after", "launch", "capture", "where", "hb4_cells",
                                               "tt_setup_before", "ff_hold_before"), r_)) for r_ in sorted(negs)])
    keys = [k for k in ff if k in tt]
    hist, cells, cbits, fbits, seen = defaultdict(int), 0, 0, 0, set()
    kpair = defaultdict(int)
    dpart = {}
    for key in keys:
        h_ = ff[key][1]
        k = max(0, _m.ceil(-h_ / hb["ff_early_ps"] - 1e-9)) if h_ < 0 else 0
        hist[k] += 1
        kpair[(key[0], key[1])] = max(kpair[(key[0], key[1])], k)
        if isinstance(key[2], str) and "->" in key[2]:
            dpart[(key[0], key[1])] = key[2].split("->", 1)[1]
    by_dst = defaultdict(int)
    for pk, k in kpair.items():
        if bits is not None and pk not in seen:
            seen.add(pk)       # a tap pair's bits once (INFO keys repeat it per port id / endpoint path)
            nb = bits.get(pk, 0)
            cbits += nb
            if k:              # cell-count bound: every bit of the pair at the pair's worst endpoint-path k
                fbits += nb
                cells += k * nb
                by_dst[dpart.get(pk)] += k * nb
    out = dict(model=hb, all=blk(keys), real_view=blk([k for k in keys if ff[k][2]]),
               both_real=blk([k for k in keys if ff[k][3]]), cells_per_pair_hist=dict(sorted(hist.items())),
               pairs_needing_hb=sum(1 for k in kpair.values() if k), endpoint_paths=len(keys),
               paths_needing_hb=sum(v for k, v in hist.items() if k))
    if part_bits is not None:
        # intra: per partition, every hard-core data pin at the partition's worst intra endpoint-path k (bound)
        kpart = defaultdict(int)
        for (a_, b_, part), k in ((key[:3], k_) for key, k_ in
                                   ((key, max(0, _m.ceil(-ff[key][1] / hb["ff_early_ps"] - 1e-9)) if ff[key][1] < 0 else 0)
                                    for key in keys)):
            kpart[part] = max(kpart[part], k)
        icells = sum(k * part_bits.get(pn, 0) for pn, k in kpart.items())
        ibits = sum(part_bits.get(pn, 0) for pn, k in kpart.items() if k)
        out.update(bits_counted=sum(part_bits.get(pn, 0) for pn in kpart), bits_needing_hb=ibits, hb4_cells=icells,
                   hb4_area_um2=round(icells * hb["area_um2"], 1), hb4_area_mm2=round(icells * hb["area_um2"] / 1e6, 4),
                   hb4_cells_by_part={pn: k * part_bits.get(pn, 0) for pn, k in sorted(kpart.items()) if k},
                   k_by_part={pn: k for pn, k in sorted(kpart.items()) if k},
                   count_basis="BOUND: every hard-core data pin of the partition (plan pins files, clk/rst/strap "
                               "excluded) at the partition's worst intra endpoint-path k; glue-to-glue paths not counted")
    if bits is not None:
        out.update(bits_counted=cbits, bits_needing_hb=fbits, hb4_cells=cells, hb4_cells_by_part=dict(sorted(
                       (str(k_), v_) for k_, v_ in by_dst.items())),
                   hb4_area_um2=round(cells * hb["area_um2"], 1), hb4_area_mm2=round(cells * hb["area_um2"] / 1e6, 4),
                   count_basis="nearest-tap seam bits (DC.seam_pairs: the pin register's own launch/capture taps)")
    return out


def droop_regions(proof_dir, taps, mode, regions_file=None):
    """{port: region} for --droop-region mesh; None for 'tree'."""
    if mode == "tree":
        return None
    reg = {}
    mj = Path(proof_dir) / "mesh.json"
    if mj.exists():
        for t in json.loads(mj.read_text()).get("taps", []):
            if t["port"] in taps:
                reg[t["port"]] = "mesh:0"
    if regions_file:
        reg.update(json.loads(Path(regions_file).read_text()))
    return reg


def mesh_signoff(proof_dir, taps, meta, corner, so_path, band_mode="tree"):
    """re-reference mesh-fed taps to the signed mesh (in place on taps/meta); returns U(a, b) and a record."""
    S = json.loads(Path(so_path).read_text())
    if S.get("corner") != corner:
        raise SystemExit(f"{so_path}: sign-off corner {S.get('corner')} != {corner}")
    L = S["loads"]
    idx = {k: i for i, k in enumerate(L)}
    arr = S["arr"]
    gv = S["grad_vec_ps"]
    rtj = json.loads((Path(proof_dir) / f"mesh_{corner}.json").read_text())["stubs"]
    M = json.loads((Path(proof_dir) / "mesh.json").read_text())
    import die_clock_mesh as DCM_   # fail closed (COORD PATH-S81-PD12 ruling A): a signed mesh is a common point only
    mv_ = DCM_.mesh_via_findings(M, proof_dir)   # when it is ONE connected net (VIA89 at every strap crossing)
    if mv_:
        raise SystemExit(f"--mesh-signoff refused: {proof_dir} mesh is not continuous: " + "; ".join(mv_[:4]))
    load = {}
    for t in M["taps"]:
        if t["port"] not in taps:
            continue
        if t.get("mesh_in"):
            if band_mode == "sim":
                load[t["port"]] = t["mesh_in"]
        else:
            load[t["port"]] = t["stub"]
    load = {p: l for p, l in load.items() if l in idx and l in rtj}
    # reference = median routed late of the normal mesh stubs (band mesh_in loads excluded so M0 is the same for
    # --mesh-band tree|sim; M0 is a common offset and cancels in every pair slack)
    band_in = {t["mesh_in"] for t in M["taps"] if t.get("mesh_in")}
    m0 = sorted(rtj[l]["late"] for l in set(load.values()) if l not in band_in) \
        or sorted(rtj[l]["late"] for l in set(load.values()))
    m0 = m0[len(m0) // 2]
    arr_stub = [r["stages_from_root"] for p, r in taps.items() if p in load and not p.startswith("~")
                and load[p].startswith("ckm_s_")] if all("stages_from_root" in r for r in taps.values()) else []
    # HEAD-R24 (explicit mesh, explicit_mesh_signoff.py): a tap whose load IS its own port has no stage below the mesh
    # load point, so the mesh node sits at the tap's own stage count (ckm_s_ stub taps: one stub buffer below, -1).
    # Strap-mesh proofs never name a port as its own load -> unchanged.
    arr_port = [r["stages_from_root"] for p, r in taps.items() if load.get(p) == p and "stages_from_root" in r]
    for p, l in load.items():
        r = taps[p]
        r["abs_late_ps"], r["abs_early_ps"] = r["late_ps"], r["early_ps"]
        r["late_ps"] = m0 + (r["late_ps"] - rtj[l]["late"])
        r["early_ps"] = m0 + (r["early_ps"] - rtj[l]["early"])
        r["cppr_node_tree"], r["cppr_node"], r["mesh_load"] = r["cppr_node"], "m", l
    meta.setdefault("cppr_node_range_ps", {})["m"] = 0.0
    if "node_stages" in meta:
        meta["node_stages"]["m"] = min([v - 1 for v in arr_stub] + arr_port) if (arr_stub or arr_port) else 0
        meta["node_xy_um"]["m"] = None
        meta["node_late_ps"]["m"] = m0
        meta["node_early_ps"]["m"] = m0
    ns = len(arr)
    gap = [rtj[k]["late"] - arr[0][i] if k in rtj else 0.0 for i, k in enumerate(L)]
    cache = {}

    def U(a, b):
        x, y = taps[a].get("mesh_load"), taps[b].get("mesh_load")
        if taps[a]["cppr_node"] != "m" or taps[b]["cppr_node"] != "m" or x is None or y is None or x == y:
            return 0.0
        k = (x, y) if x < y else (y, x)
        if k not in cache:
            i, j = idx[k[0]], idx[k[1]]
            g = gap[i] - gap[j]
            ds = [arr[s][i] - arr[s][j] + g for s in range(ns)]   # RC gap folded into every sample (PD11 ruling 3)
            mc = ds[1:] or ds
            mu = sum(mc) / len(mc)
            sd = (sum((v - mu) ** 2 for v in mc) / max(1, len(mc) - 1)) ** 0.5
            gd = ((gv[i][0] - gv[j][0]) ** 2 + (gv[i][1] - gv[j][1]) ** 2) ** 0.5
            cache[k] = max(max(abs(v) for v in ds), abs(mu) + 3.0 * sd) + gd
        return cache[k]

    def stats():
        """die-wide bound (max U) + per-pair percentiles over every mesh pair evaluated so far"""
        v = sorted(cache.values())
        if not v:
            return dict(pairs=0)

        def q(f):
            return round(v[min(len(v) - 1, int(f * (len(v) - 1) + 0.5))], 2)
        return dict(pairs=len(v), p50_ps=q(0.5), p90_ps=q(0.9), p99_ps=q(0.99), max_ps=round(v[-1], 2),
                    die_wide_bound_ps=round(v[-1], 2), gap="folded into each sample")
    U.stats = stats
    rec = dict(file=str(so_path), M0_ps=round(m0, 3), taps_on_mesh=len(load), taps_total=len(taps), band_mode=band_mode,
               samples=ns - 1, sim_summary=S.get("summary"), status=S.get("checked", "UNCHECKED"))
    return U, rec


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
        k = p.get("kit", {})
        meta.update(verdict=p.get("verdict"), pins_sha256=k.get("pins_sha256"), pins_file=k.get("pins_file"),
                    pins_canon_sha256=k.get("pins_canon_sha256"), outline_um=k.get("outline_um"))
    meta.update(view_dir=str(vd), module=module)
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


# GATE-PINS-2 (COORD ruling on the KV-CORES-PV ask, 10-27): the pin match hashes only physically and logically
# meaningful content -- per pin: name, direction, layer, x, y, size, clock-entry flag (when present); plus the core
# outline -- in canonical (sorted) order, coordinates on the 1-nm grid.  Free text ('source', 'frame', 'note', ...)
# never changes the hash.  A mirror image (MX/MY/R180) of the signed pin set is the same physical core when EVERY
# pin maps exactly (same names, same layers, same size); otherwise it is a different core type.
PIN_KEYS = ("direction", "dir", "layer", "w", "h", "width", "height", "size", "clock_entry", "is_clock_entry")
ORIENTS = {"MX": lambda x, y, W, H: (x, H - y), "MY": lambda x, y, W, H: (W - x, y),
           "R180": lambda x, y, W, H: (W - x, H - y)}


def _nm(v):
    return int(round(float(v) * 1000))


def _pin_outline(doc):
    """outline from a structured key, else from the generator's 'frame' text ('... outline W x H')."""
    if doc.get("outline_um"):
        return tuple(_nm(v) for v in doc["outline_um"])
    m = re.search(r"outline\s+([0-9.]+)\s*x\s*([0-9.]+)", str(doc.get("frame", "")))
    return (_nm(m.group(1)), _nm(m.group(2))) if m else None


def canon_pins(doc, outline_um=None):
    """{'outline': (W, H) nm | None, 'pins': {name: (x_nm, y_nm, (key, value)...)}} -- canonical physical content."""
    pins = {}
    if isinstance(doc, list):                            # run pins.json form: [{bus, bit, layer, x, y, face}, ...]
        doc = dict(pins=[dict(p, name=p.get("name") or ("%s[%s]" % (p["bus"], p["bit"]) if p.get("bit") is not None
                                                          else p.get("bus"))) for p in doc])
    for p in doc.get("pins", []):
        rest = tuple((k, _nm(p[k]) if isinstance(p[k], (int, float)) and not isinstance(p[k], bool) else p[k])
                     for k in PIN_KEYS if k in p)
        pins[str(p["name"])] = (_nm(p["x"]) if "x" in p else None, _nm(p["y"]) if "y" in p else None) + rest
    ol = tuple(_nm(v) for v in outline_um) if outline_um else _pin_outline(doc)
    return dict(outline=ol, pins=pins)


def canon_sha256(c):
    body = json.dumps(dict(outline=c["outline"], pins=sorted([n] + list(v) for n, v in c["pins"].items())),
                      sort_keys=True, separators=(",", ":"), default=list)
    return hashlib.sha256(body.encode()).hexdigest()


def mirror_of(signed, plan_c):
    """first orientation T in MX/MY/R180 with plan_c == T(signed) on every pin (names, layers, sizes equal), else None."""
    if signed["outline"] is None or signed["outline"] != plan_c["outline"] or set(signed["pins"]) != set(plan_c["pins"]):
        return None
    W, H = signed["outline"]
    if any(v[0] is None or v[1] is None for v in signed["pins"].values()):
        return None
    for t, f in ORIENTS.items():
        if all(plan_c["pins"][n] == f(v[0], v[1], W, H) + v[2:] for n, v in signed["pins"].items()):
            return t
    return None


def _read_json(f, _cache={}):
    f = Path(f)
    if f not in _cache:
        if f.exists():
            b = f.read_bytes()
            _cache[f] = (hashlib.sha256(b).hexdigest(), json.loads(b))
        else:
            _cache[f] = (None, None)
    return _cache[f]


def signed_pins_doc(view_meta, plan_dir, extra=()):
    """the pin file content the view was signed on, VERIFIED by whole-file sha256 == kit.pins_sha256: a copy in the
    view dir (<view>/pins.json or <module>_pins.json), kit.pins_file under plan_dir or as given, or any plan pins
    file (extra) with that sha.  None when no verified copy exists."""
    want = view_meta.get("pins_sha256")
    vd = view_meta.get("view_dir")
    cands = []
    if vd:
        cands += [Path(vd) / "pins.json"] + ([Path(vd) / f"{view_meta['module']}_pins.json"] if view_meta.get("module") else [])
    if view_meta.get("pins_file"):
        if plan_dir is not None:
            cands.append(Path(plan_dir) / view_meta["pins_file"])
        cands.append(Path(view_meta["pins_file"]))
    cands += [Path(plan_dir) / e if plan_dir is not None else Path(e) for e in extra]
    for c in cands:
        h, d = _read_json(c)
        if h is not None and h == want:
            return d
    return None


def pins_relation(view_meta, pins, plan_dir, outline_um=None, extra=(), _memo={}):
    """(how, reason): how = 'canonical' (same physical pin set), 'mirror:MX|MY|R180' (exact image of the signed
    set), or None with the mismatch reason."""
    view_meta = view_meta or {}
    key = (json.dumps(view_meta, sort_keys=True, default=str), pins, str(plan_dir),
           tuple(outline_um) if outline_um else None, tuple(extra))
    if key not in _memo:
        _memo[key] = _pins_relation(view_meta, pins, plan_dir, outline_um, extra)
    return _memo[key]


def _pins_relation(view_meta, pins, plan_dir, outline_um, extra):
    want = view_meta.get("pins_sha256")
    if not pins:
        return None, "no plan pins_file"
    if not want and not view_meta.get("pins_canon_sha256"):
        return None, "view has no pins_sha256"
    ph, pdoc = _read_json(Path(plan_dir) / pins if plan_dir is not None else Path(pins))
    if pdoc is None:
        return None, "plan pins_file missing"
    if want and ph == want:
        return "canonical", None
    vol = view_meta.get("outline_um")
    if outline_um and vol and tuple(_nm(v) for v in vol) != tuple(_nm(v) for v in outline_um):
        return None, "core outline differs"
    pc = canon_pins(pdoc, outline_um or vol)
    if view_meta.get("pins_canon_sha256") and canon_sha256(pc) == view_meta["pins_canon_sha256"]:
        return "canonical", None
    sdoc = signed_pins_doc(view_meta, plan_dir, extra) if want else None
    if sdoc is None:
        return None, "pins content differs"            # signed content not available: whole-file sha decides
    sc = canon_pins(sdoc, vol or outline_um)
    if canon_sha256(sc) == canon_sha256(pc):
        return "canonical", None
    t = mirror_of(sc, pc)
    if t:
        return f"mirror:{t}", None
    return None, "pins differ (canonical, no exact MX/MY/R180 image)"


def core_outlines(plan):
    """{(part, inst): outline_um} of every plan hard core (the outline the pin match compares)."""
    import schema as S
    P = S.Plan(plan)
    return {(n, h["inst"]): h.get("outline_um") for n, p in P.parts.items()
            for h in P.types[p["type"]].get("hard_cores", []) or []}


def pins_match(view_meta, pins, plan_dir, outline_um=None, extra=()):
    """CLOCK-KV-R24 content match, GATE-PINS-2 canonical + mirror form.  None (match) or the mismatch reason."""
    return pins_relation(view_meta, pins, plan_dir, outline_um, extra)[1]


def build_views(plan, taps, corner, reg, lat, core_views, kits, load_ff, part_delay_ps, match_pins=False, plan_dir=None,
                exclude=()):
    """{port: [models]} + coverage record.  core_views {module: dir}; kits {part_or_type: spec}.
    match_pins (CLOCK-KV-R21; gate default ON since CLOCK-KV-R22; CONTENT match since CLOCK-KV-R24): a core view
    applies only to instances whose plan pins_file (resolved under plan_dir) has the sha256 the view was signed on
    (provenance kit.pins_sha256); other pin views of the module (an orientation re-pin, an added strap pin) are a
    different physical core and stay budget (listed in pin_view_mismatch, by reason in pin_view_mismatch_reason).
    exclude: {(part, inst)} cores clocked by their own early core tap (FLOW-ONEMODEL-3, core_tap_views): never mapped
    to the nearest tap (their clock pin is not there); counted under early_core_tap_instances."""
    budget = budget_model(reg, lat)
    views = {p: [budget] for p in taps}
    cmodels = {m: core_view_model(m, d, corner, load_ff, part_delay_ps) for m, d in core_views.items()}
    cmap = map_cores_to_taps(plan, taps) if core_views else {}
    real_inst, real_taps = defaultdict(int), set()
    mism = defaultdict(int)
    why = defaultdict(int)
    how = defaultdict(int)
    olines, plan_pins = core_outlines(plan), sorted({v[3] for v in cmap.values() if v[3]})
    n_excl = 0
    for (n, inst), (mod, port, dist, pins) in cmap.items():
        if (n, inst) in exclude:
            n_excl += 1
            continue
        if match_pins and mod in cmodels:
            hw, r = pins_relation(cmodels[mod]["meta"], pins, plan_dir, olines.get((n, inst)), plan_pins)
            if hw:
                how[f"{mod}:{hw}"] += 1
            if r:
                mism[f"{mod}:{Path(pins).name if pins else None}"] += 1
                why[f"{mod}:{r}"] += 1
                continue
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
    if exclude:
        cov["early_core_tap_instances"] = n_excl
    if match_pins:
        cov["pin_view_mismatch"] = dict(mism)
        cov["pin_view_mismatch_reason"] = dict(why)
        cov["pin_view_match_how"] = dict(how)
        cov["pin_view_match"] = ("canonical content (name, direction, layer, x, y, size, clock-entry flag + core "
                                 "outline; free text ignored) or an exact MX/MY/R180 image of the signed pin set")
    return views, cov


# FLOW-ONEMODEL-3 (COORD 10-28 11:54, S81-14 + QC-15): a plan EARLY core tap (clock.core_taps 'early', port clk_c<k>)
# feeds only its core's clock pin(s), and the spine delivers it core_tap_early_ps before the plain taps on purpose
# (METHODOLOGY v5.0 insertion balancing).  The declared-budget model put the same common latency on both sides of
# every pair, so that designed earliness was charged as skew.  Each early core tap's endpoint now carries the core's
# OWN insertion: the freeze gate takes it from the signed core view (--core-view ETM: clk->out / setup / hold already
# hold the core's insertion, referenced to tap + --core-part-delay-ps) and FAILS CLOSED for a core tap whose core has
# no matching view; --core-insertion declared (PLANNING ONLY) uses the plan's declared per-tap insertion
# (tap insertion_ps / insertion_ff_ps) on the declared register, labelled 'declared', never a gate PASS.
CORE_INSERTION_MODES = ("view", "declared")


def early_core_map(plan, taps):
    """{proof port: [dict(part, inst, module, pin, ins_ps{TT,FF}, early_ps{TT,FF}, pins_file, outline_um)]} for every
    plan early core tap present in the proof (port t_<part>__clk_c<k>, gen_phys.core_tap_rows).  {} for a plan
    without early core taps (read from the raw plan types, no schema parse: minimal plans stay valid)."""
    pt = plan.get("partition_types") or {}
    if not any(((t or {}).get("clock") or {}).get("core_taps") == "early"
               for t in (pt.values() if isinstance(pt, dict) else pt)):
        return {}
    import schema as S
    import gen_phys as G
    P = S.Plan(plan)
    byname = defaultdict(dict)
    for p, r in taps.items():
        if "__" in p:
            byname[r.get("part")][p.rsplit("__", 1)[1]] = p
    out = defaultdict(list)
    for n, prt in P.parts.items():
        tn = prt["type"]
        if (P.types[tn].get("clock", {}) or {}).get("core_taps") != "early":
            continue
        hc = {h["inst"]: h for h in P.types[tn].get("hard_cores", []) or []}
        rows = {c: G.core_tap_rows(P, tn, c, pending=[]) for c in ("TT", "FF")}
        for (pn, inst, pin, e_tt, i_tt), (_, _, _, e_ff, i_ff) in zip(rows["TT"], rows["FF"]):
            port = byname.get(n, {}).get(pn)
            if port is None:
                continue
            h = hc.get(inst, {})
            out[port].append(dict(part=n, inst=inst, module=h.get("module"), pin=pin, ins_ps=dict(TT=i_tt, FF=i_ff),
                                  early_ps=dict(TT=e_tt, FF=e_ff), pins_file=h.get("pins_file"),
                                  outline_um=h.get("outline_um")))
    return dict(out)


def declared_core_model(reg, module, ins):
    """PLANNING-ONLY endpoint of an early core tap: the declared register arcs at the plan's declared core insertion."""
    return dict(name=f"declared:{module}", real=False, declared=True, lat_late=ins, lat_early=ins,
                clkq_max=reg["clkq_max_wire_ps"], clkq_min=reg["clkq_min_nowire_ps"], setup=reg["setup_ps"],
                hold=reg["hold_ps"])


def core_tap_views(views, ecm, corner, reg, cmodels, mode="view", match_pins=False, plan_dir=None, plan_pins=()):
    """replace the endpoint models of every early core tap (ecm = early_core_map) with its core's own: the signed
    view model (cmodels {module: core_view_model}, pin-matched like build_views when match_pins), else (mode
    'declared') the declared-insertion model, else the common-latency budget is KEPT and the tap is listed missing
    (fail closed).  Returns (views, record)."""
    if mode not in CORE_INSERTION_MODES:
        raise ValueError(f"--core-insertion {mode!r}: one of {CORE_INSERTION_MODES}")
    n = dict(view=0, declared=0, missing=0)
    missing, dec = [], []
    for port, mem in sorted(ecm.items()):
        ms, src = [], set()
        for m in mem:
            cm = cmodels.get(m["module"])
            if cm is not None and match_pins and pins_relation(cm["meta"], m["pins_file"], plan_dir, m["outline_um"],
                                                                plan_pins)[1]:
                cm = None
            if cm is not None:
                if cm not in ms:
                    ms.append(cm)
                src.add("view")
            elif mode == "declared" and m["ins_ps"][corner] > 0:
                dm = declared_core_model(reg, m["module"], m["ins_ps"][corner])
                if dm not in ms:
                    ms.append(dm)
                src.add("declared")
            else:
                src.add("missing")
        k = "missing" if "missing" in src else "declared" if "declared" in src else "view"
        n[k] += 1
        if k == "missing":
            missing.append(port)
        else:
            if k == "declared":
                dec.append(port)
            views[port] = ms
    rec = dict(mode=mode, early_core_taps=len(ecm), source=n, missing_taps=missing[:20], declared_taps=dec[:20],
               rule="FLOW-ONEMODEL-3: early core tap endpoint = the core's own insertion (signed view); 'declared' = "
                    "plan per-tap insertion, PLANNING ONLY, never a gate PASS; missing view -> FAIL CLOSED "
                    "(timed at the common latency, labelled)")
    return views, rec


def core_insertion_verdict(verdict, recs):
    """gate verdict after the early-core-tap insertion source: any missing view -> BLOCKED(kits) (OWNER 12.19; a
    FAIL stays FAIL, never a PASS); any declared
    insertion -> 'DECLARED' (a planning estimate, not a gate PASS); otherwise unchanged."""
    if not recs:
        return verdict
    if any(r["source"]["missing"] for r in recs):
        return "FAIL" if verdict == "FAIL" else HOLD_BLOCKED   # OWNER 12.19: a missing view is BLOCKED(kits), never PASS
    if any(r["source"]["declared"] for r in recs):
        return "DECLARED" if verdict == "PASS" else verdict
    return verdict


# FLOW-HOLD-1 (OWNER 12.19, COORD 10-29 05:52): die hold is judged on REAL SIGNED VIEWS only.  An endpoint whose
# block has no signed real view (a 'budget' declared register = the partition type has no --kit; a 'declared:' or
# kept-budget early core tap = the core has no --core-view; a core view whose provenance verdict is present and not
# SIGNED) makes every pair through it UNMEASURED (reason: missing view <block>), never a hold failure from the
# tap-window / declared-register model.  The gate is NOT loosened: hold PASS needs 0 unmeasured pairs AND every
# measured pair >= 0; with unmeasured pairs the hold status is BLOCKED(kits).  Setup reporting is unchanged.
HOLD_BLOCKED = "BLOCKED(kits)"


def _unsigned(m):
    v = (m.get("meta") or {}).get("verdict")
    return v is not None and not str(v).startswith("SIGNED")


def missing_views(views, taps, plan, ecm=None):
    """{port: sorted labels of the blocks without a signed real view} (empty list = fully measured endpoint).
    views None = the declared register on every tap (no real view at all)."""
    ptype = {x["name"]: x["type"] for x in plan.get("partitions", [])}
    out = {}
    for p, r in taps.items():
        lab = set()
        part_lab = f"type:{ptype.get(r.get('part'), r.get('part'))}"
        ms = views[p] if views is not None else [dict(name="budget", real=False)]
        if ecm and p in ecm:
            have = {m["name"] for m in ms if m.get("real") and not _unsigned(m)}
            for cm in ecm[p]:
                if f"core:{cm['module']}" not in have:
                    lab.add(f"core:{cm['module']}")
        for m in ms:
            if not m.get("real"):
                if not (ecm and p in ecm):
                    lab.add(part_lab)
            elif _unsigned(m):
                lab.add(f"{m['name']} (view not SIGNED)")
        out[p] = sorted(lab)
    return out


def hold_status(hm):
    """OWNER 12.19 hold status of one hold_measured record: FAIL (a measured pair < 0), BLOCKED(kits) (unmeasured
    pairs, none failing), PASS (all pairs measured and >= 0)."""
    if hm["neg_pairs"]:
        return "FAIL"
    return HOLD_BLOCKED if hm["pairs_unmeasured"] else "PASS"


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
    ap.add_argument("--count-align", metavar="BIND.json",
                    help="MESO-INTEG-1 opt-in: landed pairs use the count-aligned ring lag window of this count_align_bind "
                         "file (count_align_bind.py v2; rows: lag >= 100 ps to the guards, slot->read, guard T/8, "
                         "start skew per tree edge) instead of +-T/2")
    ap.add_argument("--clock-cal", choices=CLOCK_CALS, default="none",
                    help="METHODOLOGY 12.15 b: spice = scale clock arrivals x1.0485 TT / x1.0552 FF (SPICE_CLOCK_CAL; SS "
                         "uses the TT factor) before every class and the --count-align rows; spice_edge (CLK-INV-CAL-2 "
                         "opt-in) = inverter early arrivals on their own spice/STA-min factor (no pin-cap-range spread); "
                         "spice_buf_edge (MODEL-REFIT-BUF opt-in) = spice_edge + BUFx24 per-edge rise/fall late/early "
                         "factors (SPICE_CLOCK_CAL_BUF_EDGE); spice_cell (MODEL-REFIT-2 opt-in) = per clock MASTER "
                         "per-edge late/early factors (SPICE_CLOCK_CAL_CELL), a tap bounded by the masters on its path "
                         "(tap / meta 'clock_masters', else the clock cell's master; unknown master fails closed)")
    ap.add_argument("--clock-cell", choices=CLOCK_CELLS, default="auto",
                    help="CLK-INV-CAL-1: die clock cell of the ONE shared model (spice factor + AOCV die class). auto "
                         "(default) = tap_arrivals meta clock_cell, else the majority master of the proof's clock netlist "
                         "(ctree.v), else buf; inv / inv2 = CKINVDCx16 (SPICE_CLOCK_CAL_INV, class Ainv); buf = BUFx24 "
                         "(unchanged)")
    ap.add_argument("--count-align-ss-scale", type=float, default=1.27,
                    help="--count-align SS INFO row (never gates): TT taps x this SS/TT delay ratio when the proof has no "
                         "tap_arrivals_SS.json; 0 = off")
    ap.add_argument("--ca-ring", metavar="SPEC.json",
                    help="DIE-HEAD-18 opt-in (--count-align): time each count-aligned ring on its BUILT clocks (writer = "
                         "fwd_out + fwd_wire + fclk_in, reader = reader, per partition type, routed) instead of the "
                         "declared common latency on both sides (ca_ring_fn docstring); default = unchanged")
    ap.add_argument("--count-align-key", choices=("part", "region"), default="part",
                    help="DIE-QC-5 opt-in: how landed pairs meet the bind crossings. part (default, unchanged) = bind "
                         "src/dst are partitions; region = map partitions through bind parts[p].region (bind crossings "
                         "are region pairs, e.g. QC grp maps), time every landed tap pair of the region pair, and fail "
                         "closed on landed region pairs that no bind crossing covers")
    ap.add_argument("--count-align-start-wire", metavar="JSON",
                    help="routed start-wire minus fclk-wire delay per tree port {port: [lo_ps, hi_ps]} (default: "
                         "co-routed model, mismatch 0)")
    ap.add_argument("--count-align-start-data-delay", metavar="JSON",
                    help="HEAD-START-4 V1 (opt-in): MEASURED launch CLK -> capture D per dedicated start port "
                         "{ports: {port: [lo_ps, hi_ps]}} (count_align_plan --start-data-delay file); replaces the clk->Q "
                         "skew of each start port, a port without a row fails closed; default = unchanged")
    ap.add_argument("--intra-window-ps", type=float,
                    help="WHAT-IF override of the intra-partition kit window (default: the plan's clock.tap_window."
                         "window_ps, else 0 = the one-ideal-clock kit SDC)")
    ap.add_argument("--kit", action="append", default=[], help="part_or_type=kit.json partition interface model "
                    "(REAL VIEWS, opt-in; see docstring)")
    ap.add_argument("--cppr-lca", action="store_true",
                    help="opt-in (PATH-S81-PD6): CPPR/AOCV node = longest common prefix of the taps' tree_path (true last "
                         "common tree node); classes and shared droop still by cppr_node (region)")
    ap.add_argument("--core-view", action="append", default=[], help="MODULE=VIEWDIR signed hard-core view "
                    "(<MODULE>_{tt,ff}.lib ETM + core.json); REAL VIEWS, opt-in")
    ap.add_argument("--core-view-match-pins", action=argparse.BooleanOptionalAction, default=True,
                    help="apply a --core-view only to instances whose plan pins_file is the view's own (provenance "
                         "kit.pins_file); DEFAULT ON for freeze numbers (COORD RULING CLOCK-KV-R21 04:02, CLOCK-KV-R22); "
                         "--no-core-view-match-pins = the pre-R22 module-only match (diagnostic)")
    ap.add_argument("--core-part-delay-ps", type=float, default=0.0,
                    help="partition tap -> core clock pin delay (unbuilt partition = budget; default 0)")
    ap.add_argument("--core-insertion", choices=CORE_INSERTION_MODES, default="view",
                    help="FLOW-ONEMODEL-3: insertion of a plan EARLY core tap's endpoint. view (gate, default) = the "
                         "signed --core-view of its core, FAIL CLOSED where none matches; declared = the plan's per-tap "
                         "insertion_ps / insertion_ff_ps where no view matches (PLANNING ONLY: verdict 'DECLARED', "
                         "never a gate PASS)")
    ap.add_argument("--clock-ocv", choices=("none", "flat", "table"), default="none",
                    help="CLK-AOCV opt-in (12.4a b1 DRAFT, not a gate until OWNER review): clock OCV on the non-common "
                         "branches; default none = unchanged output")
    ap.add_argument("--clock-droop", choices=("stated", "shared"),
                    help="clock droop with --clock-ocv: stated +5.1 %% always, or shared (0 in one region); default "
                         "shared for table, stated for flat")
    ap.add_argument("--clock-aocv-table", help="clock_aocv block (default tools/die_plan/" + APPROVED_AOCV_TABLE + " = the approved 0.21 %%/mm gate table; "
                    "clk_aocv_table.json is the 0.42 %%/mm DRAFT, CLOCK-KV-R18)")
    ap.add_argument("--clock-ocv-cell-share", type=float, help="cell share of the die branch (default: table class A)")
    ap.add_argument("--pair-unc", help="opt-in per related pair clock uncertainty (qc_clk_mesh3 sta-export pair_unc.json: "
                    "U[corner]['partA|partB'], signed-mesh MC + approved AOCV below the mesh), subtracted from setup and "
                    "hold of every pair; replaces --clock-ocv (main e94f224396, reconciled PATH-S81-PD7: exclusive with "
                    "--clock-ocv and --mesh-signoff, which price the same non-common clock; --cppr-lca only picks the CPPR "
                    "node and is compatible)")
    ap.add_argument("--droop-region", choices=("mesh", "tree"), default="mesh",
                    help="shared-droop region (12.4a b1): mesh = mesh/PDN region (default, R17 fix); tree = pre-R17 rule")
    ap.add_argument("--droop-regions", help="JSON {port: region} override (e.g. PDNSim regions)")
    ap.add_argument("--hb4-delay", choices=("plan", "abutted"), default="plan",
                    help="CLOCK-KV-R24: HB4 stage delays for k and the setup charge: plan = 44.6 FF / 83.0 TT (default, "
                         "unchanged); abutted = 37.41 / 67.67 (NC-KV-R23 OpenSTA abutted chain, hold-safe for any placement)")
    ap.add_argument("--hold-buffers", choices=("none", "HB4"), default="none",
                    help="CLOCK-KV-R18 opt-in: model the planned HB4 data hold-buffer insertion (12.4a a1) per pair and "
                         "report the gate after it (summary.hb4); default none = output unchanged")
    ap.add_argument("--mesh-signoff", help="TT=mc.json,FF=mc.json signed-mesh variation sim (12.8e): CPPR at the mesh "
                    "+ per-pair sim uncertainty (opt-in, CLOCK-KV-R17)")
    ap.add_argument("--mesh-band", choices=("tree", "sim"), default="tree",
                    help="leaf-fed band taps: tree = strict CPPR at h (default); sim = sign-off pseudo loads (INFO)")
    ap.add_argument("--data-droop", choices=DD.MODES, default="class",
                    help="12.4a b2 data droop (setup only, never hold): class = OWNER per-class late derate (DEFAULT; "
                         "logic +10/+8 %%, wire +5/+4 %% TT/FF); flat = old stated +5.1 %% on every data cell; none = "
                         "no data term (pre-b2 output)")
    ap.add_argument("--data-droop-margins", help="margins JSON with the data_droop block (default tools/die_plan/"
                    "die_ci_margins.json)")
    a = ap.parse_args(argv)
    if a.pair_unc and (a.clock_ocv != "none" or a.mesh_signoff):   # ROOT-MERGE-29: fail fast, before any work
        raise SystemExit("--pair-unc is exclusive with --clock-ocv and --mesh-signoff (all price the non-common clock)")
    global CPPR_LCA
    CPPR_LCA = bool(a.cppr_lca)
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
    plan_bytes = Path(a.plan).read_bytes()
    plan = json.loads(plan_bytes)
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
               plan_sha256=hashlib.sha256(plan_bytes).hexdigest(),
               period_ps=period, unc_setup_ps=UNC_SETUP_PS, unc_hold_ps=UNC_HOLD_PS, gate="METHODOLOGY 12.4a v4.3: TT setup "
               ">= 0 and FF hold >= 0 on every related pair; CPPR at last common tree node (12.4b); skew = DIAGNOSTIC",
               block_model=dict(label="declared-budget", core_latency_ps=lat, cancels="same declared latency both sides",
                                core_tol_sensitivity_ps=a.core_tol_ps, register=REG_CELL,
                                seam_wire=dict(um=a.seam_wire_um, ff_per_um=a.wire_ff_per_um, applied="setup only"),
                                kits_found=len(kits), core_views_found=len(core_views)),
               corners={})
    ddm = DD.margins(a.data_droop_margins)
    if a.data_droop != "none":                      # 'none': record byte-identical to pre-b2
        res["data_droop"] = dict(mode=a.data_droop, rule="METHODOLOGY 12.4a b2 (setup only, never hold)",
                                 fractions={c: DD.fracs(ddm, a.data_droop, c) for c in corners})
    if real:
        import schema as S_
        res["block_model"]["label"] = "real-view (%d core views, %d kits) + declared-budget rest" % (len(core_views), len(kits))
        res["block_model"]["declared_latency_ps"] = {c: S_.common_latency_ps(S_.Plan(plan), c) for c in ("TT", "FF")}
        res["block_model"]["core_part_delay_ps"] = a.core_part_delay_ps
    cov = None
    hbrec, hbbits = {}, None
    ecm, ci_recs = None, []
    for c in corners:
        meta, taps = load_taps(d, c)
        ccell, cbasis = resolve_clock_cell(a.clock_cell, d, meta)
        if ccell != "buf":              # CLK-INV-CAL-1 record (BUFx24 records stay byte-identical)
            res.setdefault("clock_cell", {})[c] = dict(cell=ccell, basis=cbasis, aocv_class=CLOCK_CELL_AOCV_CLASS[ccell],
                                                       spice_factor=spice_cal_factor(c, ccell) if a.clock_cal != "none"
                                                       else None,
                                                       **({"spice_factor_early": SPICE_CLOCK_CAL_INV_EARLY.get(
                                                           c, SPICE_CLOCK_CAL_INV_EARLY["TT"])}
                                                          if a.clock_cal in ("spice_edge", "spice_buf_edge")
                                                          and ccell == "inv" else {}))
        elif a.clock_cal == "spice_buf_edge":   # MODEL-REFIT-BUF record (only in the opt-in mode)
            res.setdefault("clock_cell", {})[c] = dict(cell=ccell, basis=cbasis, aocv_class=CLOCK_CELL_AOCV_CLASS[ccell],
                                                       spice_factor_edge=buf_edge_factors(c))
        if a.clock_cal == "spice_cell":         # MODEL-REFIT-2 record (only in the opt-in mode)
            at = annotate_clock_masters(d, meta, taps)
            dm = sorted({x for v in at.values() for x in clock_masters_of(meta, v, ccell)})
            res.setdefault("clock_cell", {}).setdefault(c, dict(cell=ccell, basis=cbasis,
                                                                aocv_class=CLOCK_CELL_AOCV_CLASS[ccell]))
            res["clock_cell"][c].pop("spice_factor", None)
            res["clock_cell"][c].pop("spice_factor_early", None)
            res["clock_cell"][c].update(clock_masters=dm, spice_factor_cell=cell_cal_factors(c, dm),
                                        masters_basis="tap/netlist/meta clock_masters" if any(
                                            v.get("clock_masters") for v in at.values()) or meta.get("clock_masters")
                                        else "clock cell master (no clock_masters declared or traced)")
        meta, taps = apply_clock_cal(meta, taps, c, ccell, a.clock_cal, proof=d)
        rng = clock_cppr_ranges(meta)
        slew = max(r["slew_ps"] for r in taps.values())
        reg = characterise(out, c, slew, a.seam_wire_um * a.wire_ff_per_um)
        pairs, cov = build_pairs(plan, taps)
        views = None
        if ecm is None:
            ecm = early_core_map(plan, taps)
        kit_off = {p: m[0]["early_ps"][c] for p, m in ecm.items()} or None
        if real or ecm:
            import schema as S_
            clat = S_.common_latency_ps(S_.Plan(plan), c)
        if real:
            views, rcov = build_views(plan, taps, c, reg, clat, core_views, kits,
                                      a.seam_wire_um * a.wire_ff_per_um, a.core_part_delay_ps,
                                      match_pins=a.core_view_match_pins, plan_dir=Path(a.plan).resolve().parent,
                                      exclude={(m["part"], m["inst"]) for ms in ecm.values() for m in ms})
            cr_real = rcov
        elif ecm:
            bm = budget_model(reg, clat)
            views = {p: [bm] for p in taps}
        if ecm:
            cmods = {m: core_view_model(m, vd, c, a.seam_wire_um * a.wire_ff_per_um, a.core_part_delay_ps)
                     for m, vd in core_views.items()}
            views, ci = core_tap_views(views, ecm, c, reg, cmods, a.core_insertion, match_pins=a.core_view_match_pins,
                                       plan_dir=Path(a.plan).resolve().parent,
                                       plan_pins=sorted({m["pins_file"] for ms in ecm.values() for m in ms
                                                         if m["pins_file"]}))
            ci["common_latency_ps"] = clat
            ci_recs.append(ci)
        pairs.update(nearest_pairs(d, a.plan, a.clock_tool, taps))
        if a.hold_buffers != "none" and hbbits is None:
            hbbits = seam_bits(d, a.plan, a.clock_tool, taps)
        unc = None
        if a.mesh_signoff:
            so = dict(x.split("=", 1) for x in a.mesh_signoff.split(","))
            unc, mrec = mesh_signoff(d, taps, meta, c, so[c], a.mesh_band)
            rng = clock_cppr_ranges(meta)
        cr = dict(basis=meta.get("basis"), tap_slew_max_ps=round(slew, 2), register=reg, classes={})
        dd = DD.fracs(ddm, a.data_droop, c) if a.data_droop != "none" else None
        if real:
            cr["real_view_coverage"] = cr_real
        if ecm:
            cr["core_insertion"] = ci
        ocv = None
        if a.pair_unc:
            if a.clock_ocv != "none" or a.mesh_signoff:
                raise SystemExit("--pair-unc is exclusive with --clock-ocv and --mesh-signoff (all price the non-common clock)")
            PU = json.loads(Path(a.pair_unc).read_text())["U"][c]

            def ocv(x, y, check, PU=PU):
                k = "|".join(sorted((taps[x]["part"], taps[y]["part"])))
                if k not in PU:
                    raise SystemExit(f"--pair-unc: no uncertainty for pair {k}")
                return float(PU[k])
            cr["clock_ocv"] = dict(mode="pair-unc", file=str(Path(a.pair_unc).resolve()), status="UNCHECKED")
        elif a.clock_ocv != "none":
            droop = a.clock_droop or ("shared" if a.clock_ocv == "table" else "stated")
            dreg = droop_regions(d, taps, a.droop_region, a.droop_regions) if droop == "shared" else None
            ocv = clock_ocv_fn(a.clock_ocv, droop, dict(meta, corner=c), taps, lat[c], a.clock_aocv_table,
                               cell_share=a.clock_ocv_cell_share, region=dreg,
                               **({"clock_cell": ccell} if ccell != "buf" else {}))
            cr["clock_ocv"] = dict(mode=a.clock_ocv, droop=droop, status="DRAFT 12.4a b1, UNCHECKED, not a gate")
            if droop == "shared":
                cr["clock_ocv"]["droop_region"] = dict(mode=a.droop_region, file=a.droop_regions,
                                                       regions=sorted(set(dreg.values())) if dreg else None,
                                                       taps_in_region=len(dreg) if dreg else None)
        if unc is not None:
            base_ocv, umax = ocv, {"setup": 0.0, "hold": 0.0}

            def ocv(x, y, check, _b=base_ocv, _u=unc, _m=umax):
                u = _u(x, y)
                _m[check] = max(_m[check], u)
                return (_b(x, y, check) if _b is not None else 0.0) + u
            mrec["unc_max_ps"] = umax
            cr["mesh_signoff"] = mrec
        if a.count_align:
            # CA-OCV-1: the CA interval = STA phase + the SAME clock variation term as the related-pair classes
            # (ONE SHARED DIE TIMING MODEL); without --clock-ocv/--pair-unc/--mesh-signoff it carries none (labelled)
            ca_lab = (cr.get("clock_ocv", {}).get("mode", "callable") + ("+mesh-signoff" if unc is not None else "")) \
                if ocv is not None else None
            if ocv is None:
                print("WARNING --count-align: no clock variation model (--clock-ocv none): the CA interval carries no "
                      "AOCV/droop term (12.14a margin after OCV + droop not met by this run)")
            # HEAD-START-4 V1 (opt-in): measured START data delay per start port (None = unchanged)
            sdd = None
            if a.count_align_start_data_delay:
                from count_align_plan import load_start_data_delay, start_data_delay_for_corner
                sdd = start_data_delay_for_corner(load_start_data_delay(a.count_align_start_data_delay), c)
            ca = count_align_landed(pairs["landed"], taps, json.loads(Path(a.count_align).read_text()), period, reg,
                                    start_wire=json.loads(Path(a.count_align_start_wire).read_text())
                                    if a.count_align_start_wire else None, cppr_range=rng, key=a.count_align_key,
                                    ocv=ocv, ocv_label=ca_lab, meta=meta,
                                    ring=ca_ring_fn(a.ca_ring, plan, c) if a.ca_ring else None,
                                    **({"start_data_delay": sdd} if sdd is not None else {}))
            res.setdefault("count_aligned", {})[c] = ca
            if c == "TT" and a.count_align_ss_scale > 0 and "SS" not in corners:
                ss = count_align_ss_info(pairs["landed"], taps, json.loads(Path(a.count_align).read_text()), period, reg,
                                         a.count_align_ss_scale,
                                         start_wire=json.loads(Path(a.count_align_start_wire).read_text())
                                         if a.count_align_start_wire else None, cppr_range=rng,
                                         key=a.count_align_key, ocv=ocv, ocv_label=ca_lab,
                                         **({"start_data_delay": sdd} if sdd is not None else {}))
                res.setdefault("count_aligned_info", {})["SS"] = ss
                print(f"COUNT-ALIGN SS-INFO (TT x {a.count_align_ss_scale}) worst lo "
                      f"{ss['worst_lo'] and ss['worst_lo']['margin_lo_ps']} hi {ss['worst_hi'] and ss['worst_hi']['margin_hi_ps']} "
                      f"fail {ss['fail']} slot_read fail {ss['slot_read']['fail']} guard fail {ss['guard']['fail']} start-skew "
                      f"fail {ss['start_skew']['fail']}/{ss['start_skew']['tree_ports']} {ss['verdict']} (INFO, never gates)")
            print(f"COUNT-ALIGN {c} crossings {ca['crossings']} (sta {ca['sta_timed']}, tree {ca['tree_plan']}, no taps "
                  f"{ca['no_taps']}, key {ca['key']} unbound {ca['unbound']}) worst lo {ca['worst_lo'] and ca['worst_lo']['margin_lo_ps']} hi "
                  f"{ca['worst_hi'] and ca['worst_hi']['margin_hi_ps']} fail {ca['fail']} slot_read fail {ca['slot_read']['fail']} "
                  f"guard fail {ca['guard']['fail']} start-skew fail {ca['start_skew']['fail']}/{ca['start_skew']['tree_ports']} "
                  f"<{ca['need_ps']:g} {ca['below_need']} ocv {ca['clock_variation']} max lo/hi {ca['ocv_max_lo_ps']}/"
                  f"{ca['ocv_max_hi_ps']} {ca['verdict']}")
            if ca.get("ring"):
                rr = ca["ring"]
                print(f"COUNT-ALIGN {c} RING built {rr['built_ports']} (worst lo {rr['worst_lo_built']} hi "
                      f"{rr['worst_hi_built']}) declared {rr['declared_ports']} (worst lo {rr['worst_lo_declared']} hi "
                      f"{rr['worst_hi_declared']})")
        vmiss = missing_views(views, taps, plan, ecm)
        for k, pl in pairs.items():
            hrec = hbrec.setdefault(c, {}).setdefault(k, {}) if a.hold_buffers != "none" else None
            cr["classes"][k] = time_class(pl, taps, rng, reg, a.core_tol_ps, period, UNC_SETUP_PS, UNC_HOLD_PS,
                                          landed=k.startswith("landed"), window=window,
                                          hold_window=hwin.get(k) if c == "FF" else None, ocv=ocv, views=views,
                                          rec=hrec, dd=dd, kit_offset=kit_off, missing=vmiss)
            cr["classes"][k]["label"] = ("real-view+budget" if real else "declared-budget") + (
                f" + core-tap insertion {ci['mode']} (view {ci['source']['view']} / declared {ci['source']['declared']}"
                f" / missing {ci['source']['missing']})" if ecm else "") + (
                " / INFO subset" if k.endswith("INFO") else "")
        if unc is not None:
            # PD11 ruling 3: die-wide bound + per-pair percentiles of the signed-mesh U over the timed mesh pairs
            cr["mesh_signoff"]["pair_U"] = unc.stats()
            pu = cr["mesh_signoff"]["pair_U"]
            print(f"MESH_U {c} pairs {pu.get('pairs')} p50 {pu.get('p50_ps')} p90 {pu.get('p90_ps')} p99 {pu.get('p99_ps')} "
                  f"max {pu.get('max_ps')} (die-wide bound {pu.get('die_wide_bound_ps')} ps; RC gap folded per sample)")
        res["corners"][c] = cr
    res["coverage"] = cov
    gate = {}
    for k in ("intra", "seam"):
        s = res["corners"].get("TT", {}).get("classes", {}).get(k, {})
        h = res["corners"].get("FF", {}).get("classes", {}).get(k, {})
        # FLOW-HOLD-1 (OWNER 12.19): FF hold = measured pairs only (both endpoint blocks signed real views); unmeasured
        # pairs -> BLOCKED(kits), never PASS.  The all-pair declared/tap-window numbers stay as DIAGNOSTIC fields.
        hm = h.get("hold_measured") or {}
        hst = hm.get("status") if h.get("pairs") else ("PASS" if s.get("worst_setup_slack_ps", -1) >= 0 else "FAIL")
        setup_ok = s.get("worst_setup_slack_ps", -1) >= 0
        gate[k] = dict(tt_setup_ps=s.get("worst_setup_slack_ps"), ff_hold_margin_ps=hm.get("hold_margin_ps"),
                       hold_pairs_measured=hm.get("pairs_measured"), hold_pairs_unmeasured=hm.get("pairs_unmeasured"),
                       missing_views=sorted(hm.get("missing_views") or {}), hold_status=hst,
                       ff_hold_all_pairs_diag_ps=h.get("worst_hold_slack_ps"),
                       verdict="FAIL" if (not setup_ok or hst in (None, "FAIL")) else hst)
    for k in ("intra", "seam"):
        kc = res["corners"].get("FF", {}).get("classes", {}).get(k, {}).get("kit_contract_hold")
        if kc:
            gate[k]["ff_hold_kit_contract_ps"] = kc["worst_hold_bound_ps"]
            gate[k]["kit_contract_window_ps"] = kc["window_ps"]
            gate[k]["kit_contract_window_needed_ps"] = kc["window_needed_ps"]
            gate[k]["kit_contract_verdict"] = kc["verdict"]
            gate[k]["kit_contract_role"] = "DIAGNOSTIC only (OWNER 12.19: die hold is judged on real signed views)"
    if ci_recs:
        # FLOW-ONEMODEL-3: missing signed view -> FAIL CLOSED; declared insertion -> 'DECLARED', never a gate PASS
        for k in ("intra", "seam"):
            gate[k]["verdict"] = core_insertion_verdict(gate[k]["verdict"], ci_recs)
        gate["core_insertion"] = dict(mode=a.core_insertion, early_core_taps=ci_recs[0]["early_core_taps"],
                                      source={c: r["source"] for c, r in zip(corners, ci_recs)},
                                      verdict=core_insertion_verdict("PASS", ci_recs),
                                      note="BLOCKED(kits) = early core taps without a signed core view (OWNER 12.19, never PASS); DECLARED "
                                           "= planning estimate on plan per-tap insertion, not a gate pass")
    gate["landed"] = landed_gate(res["corners"])
    if a.count_align:
        cas = res.get("count_aligned", {})
        gate["landed"] = dict(form="count_aligned", bind=str(Path(a.count_align).resolve()),
                              worst_margin_lo_ps={c: v["worst_lo"] and v["worst_lo"]["margin_lo_ps"] for c, v in cas.items()},
                              worst_margin_hi_ps={c: v["worst_hi"] and v["worst_hi"]["margin_hi_ps"] for c, v in cas.items()},
                              half_period_INFO=gate["landed"],
                              ss_INFO={k: v["verdict"] for k, v in res.get("count_aligned_info", {}).items()},
                              clock_variation={c: v.get("clock_variation") for c, v in cas.items()},
                              verdict="PASS" if cas and all(v["verdict"] == "PASS" for v in cas.values()) else "FAIL")
    if a.hold_buffers != "none" and "TT" in hbrec and "FF" in hbrec:
        hb = {}
        HBM = HB4_ABUTTED if a.hb4_delay == "abutted" else HB4
        if a.data_droop != "none":
            # 12.4a b2: inserted hold buffers are data cells -> logic-class late droop on their TT setup charge
            HBM = dict(HBM, tt_late_ps=round(HBM["tt_late_ps"] * (1.0 + DD.fracs(ddm, a.data_droop, "TT")["logic"]), 3))
        ibits = intra_bits(a.plan)
        for k in ("intra", "seam", "seam_nearest_INFO"):
            if k in hbrec["TT"] and k in hbrec["FF"]:
                hb[k] = hold_buffer_model(hbrec["TT"][k], hbrec["FF"][k],
                                          bits=hbbits if k.startswith("seam") else None, hb=HBM,
                                          part_bits=ibits if k == "intra" else None)
        for k in ("intra", "seam"):
            if k in hb:
                gate[k]["hb4"] = dict(cells=hb[k].get("hb4_cells"), delay_model=a.hb4_delay,
                                      tt_setup_ps=hb[k]["all"].get("tt_setup_after_ps"),
                                      ff_hold_ps=hb[k]["all"].get("ff_hold_after_ps"),
                                      real_tt_setup_ps=hb[k]["real_view"].get("tt_setup_after_ps"),
                                      real_ff_hold_ps=hb[k]["real_view"].get("ff_hold_after_ps"),
                                      setup_neg_pairs=hb[k]["all"].get("setup_neg_pairs_after"),
                                      pairs_needing_hb=hb[k]["pairs_needing_hb"])
        res["hb4"] = hb
    res["summary"] = dict(gate, status="UNCHECKED (NUMBER-CHECK pending)",
                          label=res["block_model"]["label"] if real else "declared-budget (no QC kit)")
    if a.data_droop != "none":
        res["summary"]["data_droop"] = dict(
            mode=a.data_droop, tt_setup_penalty_max_ps={k: v.get("data_droop_setup_max_ps") for k, v in
                                                        res["corners"].get("TT", {}).get("classes", {}).items()})
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
                      + (f" | MEASURED-HOLD {v['hold_measured']['pairs_measured']} measured / "
                         f"{v['hold_measured']['pairs_unmeasured']} unmeasured margin "
                         f"{v['hold_measured']['hold_margin_ps']} {v['hold_measured']['status']}"
                         if c == "FF" and "hold_measured" in v else "")
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
