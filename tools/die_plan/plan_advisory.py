#!/usr/bin/env python3
"""plan_advisory.py -- PRECHECK-R2 (COORD 11-22): static ADVISORY checks of a composed die plan + its bind inputs.

Owner rule 11-19: the precheck is an ESTIMATOR, never a gate.  Every line this module returns starts with "WARN ADV-<CHECK>";
plan_gate_pre.check() appends them (class ADVISORY, --skip ADVISORY or OT_PLAN_ADVISORY=off to leave out) and they never
change its verdict or exit code.  Each check found, on 11-22, a problem one build (about a day) late that the plan showed:

  CORE-PARAM       hard-core parameters the bind derives (e.g. KV ectl QK_ISSUE_AGE / RESPONSE_LAT from landed station depths)
                   differ from the parameters the signed core view was built with (KV D27d3+ ectl 42/31 vs signed qkd_ectlk 37/26)
  GHOST-MACRO      a placed macro / hard-core row of the plan with no instance in the bound RTL (S81 svc pvq_capture rows)
  SITE-COLLIDE     station / relay / START / reset sites crowding each other or a macro keep-out (HEAD w10 reader START ~(487,1370))
  PORT-WINDOW-PAIR the two ends of a die-level port pair no longer carry matching windows after a split / nudge (S81 J8 svc
                   rt_W0_out_1__6, rt_E0_out_0__5)
  DEPTH-VS-RTL     plan stage counts beyond what the RTL parameters allow (S81 istation_respace vs LF_CS_DEPTH: 102 bind errors)
  CELLCAP          flat standard-cell count above the native CELL-CAP reference using a retained kit count or an estimate
  CELL-BUDGET      projected synth cells of a soft type = measured content + the slot overhead the plan places in it (ft stations,
                   clock landings, internal stations, relays; 2 cells per stage bit for ASAP7 QN flops) > 350k (place ~x1.28 vs the
                   400k cap): S81 kv_leaf t2 658k as handed, ~340k of it feed-through landings + stations (adv_cell_budget.py)
  DENSITY          std-cell utilisation of a piece from the synth cell count > ~0.6 (S81 strip_S 0.91)
  TAP-BUDGET       estimated clock insertion of a pin-register cluster from its tap distance > 450 ps (S81 t5 / col 478-538 ps)
  TAP-LOAD         planned max tap load > 1.3x below the netlist flop estimate; placed tap load > 1,500 (S81 t5 1,099 vs 8,000)
  PORT-PIN         a wrapper port of the strict bind output with no planned pin (KV pv_v3e ri_pv_u_g1_j_rst_n: split piece without
                   its reset pin, died at place)
  MERGE-RESET-DEPTH core reset pins merged into one port whose delay rows carry different depths (OPUS-FIX-KV-HUB-R6)
  PATH-SEAT        a short pin-to-seat span whose path detours behind a macro (S81 leaf t15: 5 um span, 1,885 um path), and
                   planned paths over ~20 logic stages at 833 ps (lepw_mus_C 28)
  PHANTOM-STATION  a plan station row priced +N cycles on a lane with no stage register in the bound RTL (HEAD hd_lep0N e1/e2)
  BANK-OFFAREA     exact / bank flop sites (internal_stations bit_sites_um / face_bit_sites_um, soft_reg_banks) outside CORE_AREA,
                   the outline minus the core inset: place refuses them not on row/site (KV kv3_pv_v3 / v3e D28 R5: 749 sites)
  STATION-DENSITY / SITE-ON-ROW / PLACE-REGION / BAND-BLOCKAGE / BAND-GAP  static placement geometry (adv_geom_static.py, COORD
                   flow review 11-22): exact sites over a bin's capacity, internal exact sites off the row/site grid, place
                   regions that cannot hold movable cells, soft landing bands under hard cores, bands too small for their flops
  LANE-STATIONS    lanes whose planned kit stations (both end buses, kit_depth) exceed fixed_cycles + pad, so the strict bind
                   would deliver late (LANE_ASBUILT UNPRICED_KIT_STATIONS; QC V4 l1a sl_W4_fw arm/arv 12 vs 8)
  ROUTE-DEMAND     static RUDY of planned station / ft legs vs M2-M8 track supply above hard-core obstructions: gcells at est.
                   routing util >= 0.8 and the core channel there (S81 leaf: vn->lane bank fan-in through 4-17 um channels,
                   t44 50k GRT overflow at 2.6 % fill); calibrated as a where-to-look map, not a ranking (adv_route_demand.py)

  EDGE-STRIP       >= 256-bit die windows with a hard core < 69.12 um behind the window span (VIS-DIE-S81 EDGESTRIP-1; S81 J8:
                   241 types, 0/47 signed, 40/51 failing); fix = edgestrip_row.py interior shift or re-shape (adv_edge_strip.py)

  HOP-GAP          internal one-cycle reg-to-reg / reg-to-core-pin hop > 405 um with no station (FABLE-RC-S81: gunit -2168 ps)
  TAPOFF-SITE      tap_offset / tap_window rows whose tap moved > 9 um vs a baseline plan (rows are keyed by tap NAME; QC st_a r9 had 5-22 of 225-408 on their own tap); needs --baseline
  ROW-APPLIED      rows accepted by reference whose ops (value at path, by CONTENT) are not in this plan: FULL / PARTIAL / NONE per ops file (OT_ADV_ROWS)
  UNSEATED-CHAIN   multi-stage ot_dp_dly delay pipes in the BOUND RTL (no plan seat) whose bits x stages need more area than their pin window x 17 um (QC cbf_q11 n_y: 514 bits x 10 stages, 89 um window); needs bind_out
  SEATLINE         station seats whose cells (bits x 2) cannot fit the seat window (sqrt(cells x 0.25 / 0.6)) or whose 100 um bin is 2x the median / 30% seat area (QC sle_ctl hc1_o 1,574 bits at one point)
  COLSYNC          plan landing_contract collector nodes vs the landed sidecar's (strict reads the sidecar, landing_place / kit gen the plan): differ / not in tree / > 405 um from the row (QC su_c)
  CTLM-AGES        compiled tt_ctlm program lane ages (ctlm_metadata_source relay.R_*) and core XPF_TRANSPORT_EDGES vs the bound lane cycles and xpf = 1 + R_HR (QC C1g 19/19 vs 14/10, XPF 21 vs 20)
  BITSITE-SEAT     exact bit sites (ft bit_sites_um, in-core rows) farther than 40 um from their station / wrong stage count (KV A5t2 RREACH 659 um; --baseline: only stages seated before)
  LAT-DEFINE       latency-changing verilog_defines (RIP, SRAMREG, CFX, kv_seam) on a type that the die-wide as-built profile does not list, MIXED within a family
  G0-HOPS          G0's check_hops alone (~30 s): every lane's mandatory-slot-pin / ft-station hop vs its reach (S81 c8: 98 lanes found only at G0)
  STALE-KEEPOUT    clock.keepouts_um that are old copies of landing bands (KV pv_v2ne/v5ne), and sink_bins_file counts >10% off the latest placed DB
  RAW-RESET-TO-PORT a writer START stage raw reset that drives an output port in the type's bound RTL (QC C1b sle_su_c rr_t85, EMIT refusal after 3628 s)
  IST-PRICE        a lane's stored latency row (cycles / ft stations / landing) short of the live ft + landing + source stations (KV A3c
                   'native stations exceed priced lane depth', A2g L415): every lane, not only native-source ones
  STN-CONFLICT     >= 2 station rows of differing geometry on one native bus, or a valid bit stationed apart (S81 iqf idx_o0)
  LAND-CAP         a clock-landing band filled >= 90 % or crossed by a foreign halo (S81 c1x_C t9, QC st_a x_st_b_i)
  LAND-REACH       a hard landing core parked farther from its port than the cland data allowance (QC sle_ctl 300 um / 192 ps vs 45 ps)
  TREE-DRIFT       a view LEF / porous map / flow script / tool fix on main the bound tree lacks (u_cf view 31c7ccbd1b on J7/J8)
  OFF-GRID         exact station / bank sites off the placement grid (KV sys_c row C)
  RESET-NAME       a generated reset relay (rst_rl_<k>) / density tap (clk_t<i>) name the clock section references that the
                   type's reset tree / tap table no longer emits (tap rows renumbered the tree: S81 J8, HEAD Row B, KV D29 14
                   EMIT); fix = landing_remap --resets anchor from the TREE's tools (adv_reset_names.py, TAP-GRID-R5)

    python3 -I tools/die_plan/plan_advisory.py --plan PLAN.json [--tree TREE] [--checks A,B] [--json OUT]   (exit 0 always, 2 = bad input)
"""
import argparse
import importlib
import json
import os
import signal
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
# (check name, module in this directory); a module absent from an older tree is skipped quietly
CHECKS = (("CORE-PARAM", "adv_core_param"), ("GHOST-MACRO", "adv_ghost_macro"), ("SITE-COLLIDE", "adv_site_collide"),
          ("PORT-WINDOW-PAIR", "adv_port_window_pair"), ("DEPTH-VS-RTL", "adv_depth_vs_rtl"), ("DENSITY", "adv_density"),
          ("CELLCAP", "adv_cellcap"), ("CELL-BUDGET", "adv_cell_budget"),
          ("TAP-BUDGET", "adv_tap_budget"), ("TAP-LOAD", "adv_tap_load"),
          ("PORT-PIN", "adv_port_pin"), ("MERGE-RESET-DEPTH", "adv_merge_reset_depth"), ("PATH-SEAT", "adv_path_seat"),
          ("PHANTOM-STATION", "adv_phantom_station"), ("BANK-OFFAREA", "adv_bank_offarea"),
          ("STATION-DENSITY", "adv_station_density"), ("SITE-ON-ROW", "adv_site_on_row"), ("PLACE-REGION", "adv_place_region"),
          ("BAND-BLOCKAGE", "adv_band_blockage"), ("BAND-GAP", "adv_band_gap"), ("LANE-STATIONS", "adv_lane_stations"),
          ("ROUTE-DEMAND", "adv_route_demand"), ("EDGE-STRIP", "adv_edge_strip"), ("RESET-NAME", "adv_reset_names"),
          ("REF-SITE", "adv_ref_site"), ("HOP-GAP", "adv_hop_gap"), ("OFF-GRID", "adv_off_grid"), ("TREE-DRIFT", "adv_tree_drift"), ("LAND-CAP", "adv_land_cap"), ("LAND-REACH", "adv_land_reach"), ("STN-CONFLICT", "adv_stn_conflict"), ("IST-PRICE", "adv_ist_price"), ("RAW-RESET-TO-PORT", "adv_raw_reset_port"), ("STALE-KEEPOUT", "adv_stale_keepout"), ("G0-HOPS", "adv_g0_hops"), ("TAPOFF-SITE", "adv_tapoff_site"), ("LAT-DEFINE", "adv_latdefine"), ("BITSITE-SEAT", "adv_bitsite_seat"), ("CTLM-AGES", "adv_ctlm_ages"), ("COLSYNC", "adv_colsync"), ("SEATLINE", "adv_seatline"), ("UNSEATED-CHAIN", "adv_unseated_chain"), ("ROW-APPLIED", "adv_row_applied"), ("PAD-LAUNCH", "adv_pad_launch"))
CHECK_TIMEOUT_S = int(os.environ.get("OT_PLAN_ADVISORY_TIMEOUT_S", "120"))
MAX_LINES = 25          # per check, plus its own summary line


class _Timeout(Exception):
    pass


def _alarm(_sig, _frm):
    raise _Timeout()


def _norm(name, lines):
    out = []
    for x in lines or []:
        x = str(x)
        if not x.strip() or x.startswith("#"):          # module debug / coverage lines
            continue
        if not x.startswith("WARN "):
            x = f"WARN ADV-{name} {x}"
        out.append(x)
    if len(out) > MAX_LINES + 1:
        out = out[:MAX_LINES] + [f"WARN ADV-{name} ... {len(out) - MAX_LINES} more line(s) (plan_advisory.py --checks {name} for all)"]
    return out


def run(raw, plan_path, tree=None, checks=None, skip=(), timing=None, cap=True, **kw):
    """WARN ADV-* lines of every check (never raises)."""
    if os.environ.get("OT_PLAN_ADVISORY", "").lower() == "off":
        return []
    skip = {s.upper() for s in skip or ()}
    want = {c.upper() for c in checks} if checks else None
    out = []
    sys.path.insert(0, str(HERE))
    try:
        for name, mod in CHECKS:
            if name in skip or (want is not None and name not in want):
                continue
            t0 = time.time()
            try:
                m = importlib.import_module(mod)
            except ImportError:
                continue
            main_thread = threading.current_thread() is threading.main_thread()
            old = None
            try:
                if main_thread and CHECK_TIMEOUT_S > 0:
                    old = signal.signal(signal.SIGALRM, _alarm)
                    signal.alarm(CHECK_TIMEOUT_S)
                lines = m.findings(raw, plan_path, tree=tree, **{k: v for k, v in kw.items() if v})
            except _Timeout:
                lines = [f"WARN ADV-{name} not checked: over {CHECK_TIMEOUT_S} s"]
            except Exception as e:  # noqa: BLE001 an estimator never breaks the gate
                lines = [f"WARN ADV-{name} not checked: {type(e).__name__}: {str(e)[:200]}"]
            finally:
                if old is not None:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old)
            out += _norm(name, lines) if cap else [str(x) for x in lines or []]
            if timing is not None:
                timing[name] = round(time.time() - t0, 2)
    finally:
        try:
            sys.path.remove(str(HERE))
        except ValueError:
            pass
    return out


def summary(lines):
    """'ADV-X n, ADV-Y m' over finding lines (not-checked / summary lines excluded)"""
    n = {}
    for x in lines:
        f = x.split()
        if len(f) > 2 and f[1].startswith("ADV-") and f[2] not in ("not", "...") and not f[2].startswith("summary"):
            n[f[1]] = n.get(f[1], 0) + 1
    return ", ".join(f"{k} {v}" for k, v in n.items())


def main(argv=None):
    ap = argparse.ArgumentParser(prog="plan_advisory", description=__doc__.split("\n\n")[0])
    ap.add_argument("--plan", required=True)
    ap.add_argument("--tree")
    ap.add_argument("--checks", default="")
    ap.add_argument("--asbuilt")
    ap.add_argument("--bind-out")
    ap.add_argument("--baseline", help="base plan (changed-lane scope, e.g. PHANTOM-STATION)")
    ap.add_argument("--json")
    ap.add_argument("--all", action="store_true", help="no per-check line cap")
    a = ap.parse_args(argv)
    try:
        raw = json.loads(Path(a.plan).read_text())
    except (OSError, ValueError) as e:
        print(f"plan_advisory: cannot read {a.plan}: {e}", file=sys.stderr)
        return 2
    tm = {}
    lines = run(raw, a.plan, a.tree, [c for c in a.checks.split(",") if c] or None, timing=tm, cap=not a.all,
                asbuilt=a.asbuilt, bind_out=a.bind_out, baseline=a.baseline)
    for x in lines:
        print(x)
    print(f"PLAN-ADVISORY plan={a.plan} lines={len(lines)} ({summary(lines) or 'no findings'}) seconds={tm}")
    if a.json:
        Path(a.json).write_text(json.dumps({"plan": a.plan, "tree": a.tree, "advisories": lines, "seconds": tm}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
