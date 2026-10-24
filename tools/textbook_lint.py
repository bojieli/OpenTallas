#!/usr/bin/env python3
"""Textbook physical-design lint (owner request 2026-10-11, stream textbook-lint): refuse a route whose post-synthesis
netlist + floorplan has a classic, known-unclosable structure, before placement, instead of discovering it after a
4-12 h route and dozens of ECO / LVT / density retries.

Runs in the closure loop's floorplan-lint hook (tools/fp_margin_lint.tcl ot_fp_lint_flow, ORFS PRE GLOBAL_PLACE on
3_2_place_iop.odb, on the fleet host: no extra synthesis) on the ORFS synthesis netlist (results/.../1_2_yosys.v, or a
write_verilog of the floorplan db) and the floorplan geometry dump fp_margin_lint.tcl already writes (die / core, placed
IO pins, placed macros with pin positions + directions).  Offline:

    textbook_lint.py check --netlist 1_2_yosys.v --dump fp_margin_lint_dump.json [--out R.json] [--mode warn|refuse]
                     [--set key=value ...] [--waive check ...]
    exit 0 PASS / WARN (prints "textbook_lint: WARN ..."), 3 REFUSE (prints "TEXTBOOK_LINT: ..."), 2 tool error

Checks (each names the offending nets / registers; thresholds in THRESHOLDS, calibrated on the validation set of
2026-10-11, see tools/closure_loop/README.md "Textbook lint"):
  clock_domain   flops per clock root: > clk_sinks_max sinks on ONE root, or a root with > clk_span_sinks sinks on an
                 outline whose longer side is > clk_span_um, without hierarchical sub-blocks (VM8 halves 33-60k sinks
                 over 350 x 1000 um; smh_tile_eg 130k)
  high_fanout    a non-clock net (fanout counted through BUF / INV trees) with > hf_max loads; a PORT-driven net with
                 > hf_port_max loads; reset-named nets reported as such (norm engine reset 39,240 flops, su64 780k reset
                 pins, tkm reset 20,061; wfc_crp kit pin -> ~1,000 enables; coll_ce decision -> 2,200 regs; qfd_tile rom_ce)
  boundary       combinational input->output paths; > bnd_levels logic levels between an input port and its first flop
                 or between the last flop and an output port; a clock-gate (ICG) enable driven combinationally from an
                 input port (tt_ctlm me_mem_ok -> ICG)
  logic_depth    estimated reg->reg stage delay (ASAP7 cell weights, ps) > depth_ps_max (~700 ps fits 1.2 GHz at SS with
                 60 ps uncertainty)
  wire_reach     a register whose combinational fan-in and fan-out reach FIXED terminals (placed IO pins, macro pins) that
                 no single point lies within reach_um (Manhattan) of, or a fixed-to-fixed combinational path longer than
                 reach_um: such a stage needs relay flops (504 um per stage at SS)
  util_channel   (std + macro) / core above util_max (enlarge the outline), and macro-to-macro channels narrower than
                 channel_um that are not fully blocked for placement.  Below util_min is informational only (metric
                 util_note "outline roomy; acceptable"): OWNER 10-19/10-21, target fill 40-60%, never shrink for area
Mode: WARN (findings are logged to the job and the daemon log; the flow continues) until the validation set shows zero
false positives, then REFUSE (the flow stops with "TEXTBOOK_LINT: ..." and the loop finishes the job FLOORPLAN_MARGIN).
Per-check modes: REFUSE applies to the checks in refuse_checks only; the others stay WARN.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
import warnings
warnings.filterwarnings("ignore", category=SyntaxWarning)
from collections import defaultdict

# Two tiers per check.  WARN: the owner's textbook lines (2026-10-11).  REFUSE (*_refuse keys): calibrated on the
# validation set (README "Textbook lint"): each sits above every CLOSED block's value and below the failing lines', so
# the refuse tier rejects no closed block.  The textbook WARN lines are NOT refuse lines: closed blocks exceed them
# (one clock root: P4 qkvd_rom_end 94,498 flops, P9 norm_grp8 56,805; a 33,346-load flop net in P4; util 6-21% on
# seven closed blocks; 17 um macro channels in el1011 wfc_crp; 6-7 level skid-buffer input paths).
THRESHOLDS = {
    # clock_domain: flops on one clock root
    "clk_sinks_max": 15000,        # WARN (flops only; the hard line is CLK_ROOT_SINKS_MAX / clock_rule below)
    "clk_span_um": 600.0,          # WARN: outline side ...
    "clk_span_sinks": 8000,        # ... with this many flops on the root
    "clk_sinks_refuse": 110000,    # REFUSE (closed max 94,498; failing 124,633-147,062)
    # high_fanout (loads after collapsing BUF / INV trees; constants excluded)
    "hf_report": 256,              # WARN for port-driven and reset nets
    "hf_max": 3000,                # WARN other nets
    "hf_port_refuse": 2048,        # REFUSE: a non-reset port drives > N loads (closed max 813; smh_tile_eg xs_a1 4,107)
    "hf_reset_refuse": 8000,       # REFUSE: reset-named net (closed max 4,964: mtp_p2_prefix_path rst_n port)
    "hf_refuse": 50000,            # REFUSE: any other net (closed max 33,346)
    # reset_landing (ROOT-RST 2026-10-19): a reset INPUT port must land in a pin register stage (2 registered stages at
    # the face, then equal-depth fan-out); its own net (through BUF / INV) may reach at most this many sinks: 1 = the
    # landing flop's D, 2 = an async-assert synchroniser's two reset pins.  Over it the port is an unregistered reset tree.
    "rst_land_max": 2,             # WARN + REFUSE tier (the pre_route_gate enforces it; the route-time lint only WARNs)
    # boundary (logic levels: non-BUF/INV cells)
    "bnd_levels": 3,               # WARN
    "bnd_in_levels_refuse": 9,     # REFUSE input->register (closed max 7; failing 10-17)
    "bnd_out_levels_refuse": 3,    # REFUSE register->output (closed max 2; tt_ctlm 5)
    "bnd_in_to_out_refuse": 1,     # REFUSE any combinational input->output bit (closed: none)
    "bnd_icg_port_refuse": 1,      # REFUSE an ICG enable combinational from a port (closed: none)
    # OWNER 10-20 ~09:05 PIN REGISTERS: required only at region crossings (landing rings) and on wires over the 405 um
    # reach; touching same-region tiles may connect directly when the combined path meets timing (die / parent STA
    # judges it).  So input->register / register->output LEVELS are a WARN (reported), never a boundary REFUSE, unless
    # the strict 10-15 "every pin registered" form is asked for (--set bnd_strict_pin_regs=1).  A combinational
    # input->output bit and an ICG enable from a port stay REFUSE; a stage beyond reach_um stays a wire_reach REFUSE.
    "bnd_strict_pin_regs": 0,
    # logic_depth: raw ASAP7 weight sum x depth_scale = ps.  depth_scale calibrated so the closed set's worst stage
    # (P6 tu_retry_phy_port, 15 levels) estimates <= ~610 ps against the 700 ps budget at 1.2 GHz
    "depth_scale": 1.667,
    "depth_ps_warn": 600.0,
    "depth_ps_max": 700.0,         # REFUSE (closed max 608; failing 775-1,020)
    # wire_reach
    "reach_um": 500.0,             # REFUSE (504 um per stage at SS)
    "reach_min_count": 1,
    # util / channels: WARN only (closed blocks at 6-58% util and 0.07 / 17 um channels)
    "util_min": 0.40,              # below: informational "outline roomy; acceptable" (OWNER 10-21: never shrink for area)
    "util_max": 0.60,              # above: WARN, enlarge the outline; std-cell density over the placeable area (core -
                                   # macros - halos) when macros exist
    "fill_max": 0.90,              # total (std + macro) / core sanity bound, macros only
    "macro_halo_um": 2.16,
    "channel_um": 20.0,
}
# CLOCK RULE (OWNER DECISION 2026-10-23, supersedes the 10-17 0dq spread FAIL; memory clock-rule-boundary-match-1017).
# One place for the numbers; pre_route_gate.py, the in-flow hook and the closure loop all read them from here.
#   FAIL only on the measured related launch/capture flop-pair skew WITH CPPR credit > CLK_PAIR_SKEW_MAX_PS at TT OR FF
#   (evidence "tt_pair_skew_ps" / "ff_pair_skew_ps" = worst |skew| over the reg->reg setup + hold path ends:
#   tools/die_plan/pair_skew.tcl, measured by ck_insertion.py on the CTS odb).  Sign-off = propagated-clock STA (setup
#   TT, hold FF).  The pin-flop / leaf spread (max-min) is REPORTED only, never a FAIL; a measured clock record
#   without pair skew is a WARN ("pair skew not measured").
#   > CLK_ROOT_SINKS_MAX sinks on one root, or TT insertion > CLK_INSERTION_MAX_PS: WARN (guidance).
# Sinks of a root = flops + hard-child / macro clock pins (a hard child with its own clock pin is ONE sink, never its
# internal flops); ICGs are tree cells, the flops behind them count on the ICG's root.
CLK_ROOT_SINKS_MAX = 15000
CLK_INSERTION_MAX_PS = 300.0
CLK_SPREAD_MAX_PS = 80.0          # 10-17 0dq spread number: REPORT reference only since 10-23 (closed_stands kinds)
CLK_PAIR_SKEW_MAX_PS = 80.0       # owner 10-23: related flop-pair skew with CPPR, TT and FF
CLOCK_RULE_FIX = ("related flop-pair skew (CPPR credited) > 80 ps at TT or FF (owner 10-23): re-balance the tree so "
                  "related launch / capture flops share their clock path (common branch, clock entry beside the "
                  "register mass, pin flops grouped by face) or split into hardened leaves with their own roots; "
                  "spread, insertion and sink count alone never fail a tile")
HARD_CHECKS = ("clock_sinks",)     # refused in every mode, never waivable by spec

# CLOSED STANDS (owner decision 2026-10-12 19:00 "M5 cap narrowed", made a submit gate 2026-10-13; logic in
# tools/closure_loop/closed_stands.py, enforced by the closure loop at submit).  A block (same top module, same parameter
# set) with a CLOSED job whose view is published is NOT routed again: the closed tile stands.  A new route is admitted
# only with spec "reroute_reason": {"kind": <one of CLOSED_STANDS_KINDS>, ...}:
#   die_window    the tile sits under a die window that needs the tracks: "slot" (contract slot), "cut" (measured fine
#                 cut, must be > DIE_WINDOW_CUT_MIN in the direction the freed layer serves) or "grt_overflow" (measured
#                 die-GRT overflow over the tile, > 0), and "source" (the file the figure was read from; must exist)
#   slot_change   outline / pin faces differ from the closed view: "contract" (name + version) or "slot_change_request"
#   param_change  elaborated parameters differ: "params" lists them
#   rtl_change    the block's RTL differs from the closed job's commit (the gate compares the source blobs itself)
#   evidence_gap  the closed job lacks a behavioural bench + mutant or a routed verdict: "why_route" says why a route
#                 (and not a bench bind / re-export) is needed
#   pin_register  (owner 2026-10-13, die timing by construction: a tile with an unregistered face pin or a long
#                 pin-to-flop wire is a defect to fix, not to waive) the closed view is a ranked violation of the
#                 insertion-compensated pin-register audit (tools/hier_contract/pinreg_audit.py v2): "source" (the
#                 audit JSON, must exist), "cell", and the measured "pair_cost_ps" (o + s of the view, must be >
#                 PIN_REGISTER_PAIR_MAX_PS: no hop of any length closes against it) -- the die needs the tile re-placed
#                 with its pin flops at the pins; "fix" says what the new kit changes (recipe 2 / RTL pin flops)
# M5 is the default for NEW tiles only.  Loop successors (auto-react, near-miss finishing, -hs / -ls re-runs) of a job
# that is not CLOSED are unaffected.
#   native_launch (el1014-root-macro-edge 2026-10-14) a CLOSED view fails the native launch budget (TT launch >
#                 PIN_LAUNCH_MAX_PS at phi - R) only because its kit predates the recipe-2 output stage (main 36de4b87f):
#                 the same RTL and outline / pin faces re-kitted with that stage ("source" audit JSON, "cell",
#                 "launch_ps"); written by tools/ref_tile/rekit_native_launch.py
#   native_capture (coordinator 2026-10-16, S81 ctrnown_e; widened 22:30) a CLOSED view FAILS its native audit (TT capture at
#                 the pin + R > PIN_CAPTURE_MAX_PS, launch at phi - R > PIN_LAUNCH_MAX_PS, or boundary clock spread >
#                 CLK_SPREAD_MAX_PS) with unchanged RTL / outline / pin faces (pin positions may move along the same
#                 faces): "source" (a COMMITTED native audit receipt that the gate reads: a record of "cell"), "cell",
#                 and "fix" (what the new kit changes: input pin flops / clock entry / insertion / boundary registers)
#   native_spread (ROOT-0745 2026-10-18) as native_capture, for a view whose committed receipt FAILS on the TT / FF
#                 pin-flop spread (> CLK_SPREAD_MAX_PS).  For native_launch / native_capture / native_spread an RTL
#                 difference from the closed commit no longer refuses when "source" is a COMMITTED receipt (a path on the
#                 job's commit / origin/main, not an absolute local file) that records the closed view's FAIL: such a
#                 view cannot bind into the die, so the re-route is not a repeat (Gate-Rule: relaxing, submit lint only).
#   native_reach  exact-job committed native-path receipt >405 um, unchanged RTL/parameters, and source-pinned
#                 changed pin coordinate ranges on the same outline/faces; fresh native/gate qualification required.
#   flow_failure  (ROOT-0945 2026-10-18) a re-route of the same or a fixed source after a harness / OOM / flow failure of
#                 an ADMITTED re-route: "failed_job" (the failed job's id, in the loop's history: same block, not CLOSED,
#                 not active, and its own spec carried a valid "reroute_reason" -- the retry inherits that admission;
#                 a failed job that was never admitted gives none), optional "failure" (what failed).  The daemon's
#                 earlyoom retry (main a1f06d7f2) and lanes resubmitting after an OOM / harness crash use it
#                 (Gate-Rule: relaxing, submit-time CLOSED-STANDS only).
#   pin_order     (REFILL-0400/PO-LINK 2026-10-19, pin_order rule c81a8f458) the closed view's own bus bit order is
#                 chunk-scrambled on an abutted joint: "source" (the COMMITTED abutted-joint audit hand-off / JSON naming
#                 the block), "fix"; same RTL, outline and pin faces; the new kit.env carries an ordered layout
#                 (OT_PIN_BALANCE_H from route.pin_balance, or PINEX=0 from an exact io_tcl) and the closed kit did not
#                 (Gate-Rule: relaxing, submit-time CLOSED-STANDS only).
CLOSED_STANDS_KINDS = ("die_window", "slot_change", "param_change", "rtl_change", "evidence_gap", "pin_register",
                       "native_launch", "native_capture", "native_spread", "flow_failure", "pin_order",
                       "pg_binding", "native_reach")
DIE_WINDOW_CUT_MIN = 0.6
PIN_LAUNCH_MAX_PS = 220.0             # tile defect: first-load launch beyond phi - R (header 10-13 die clock rule)
PIN_CAPTURE_MAX_PS = 190.0            # tile defect: setup at the pin plus R
PIN_REGISTER_PAIR_MAX_PS = 683.3      # 833.3 - 60 - SKEW 90 (same clock level): o + s of one view above it leaves no wire
CLOSED_STANDS_INSTEAD = ("a CLOSED tile stands (owner 10-12): do not route it again. Instead: bind the missing bench + "
                         "mutant to the closed job (job \"benches_from\" / tools/ref_tile/composition_gates.json "
                         "\"benched_by\"), re-export its view from the closed run (tools/ref_tile/ref_tile.py export), "
                         "or wrap the closed view under the contract slot name. M5 is the default for NEW tiles only. "
                         "A route that IS needed states it in the spec: \"reroute_reason\": {\"kind\": "
                         "\"die_window\" (+ \"slot\", \"cut\" > 0.6 or \"grt_overflow\" > 0, \"source\" file) | "
                         "\"slot_change\" (+ \"contract\" or \"slot_change_request\") | \"param_change\" (+ "
                         "\"params\") | \"rtl_change\" (verified against the closed commit) | \"evidence_gap\" (+ "
                         "\"why_route\") | \"pin_register\" (+ \"source\" audit JSON, \"cell\", \"pair_cost_ps\" > "
                         "683.3, \"fix\") | \"native_launch\" (+ \"source\" audit JSON, \"cell\", \"launch_ps\" > 220; "
                         "tools/ref_tile/rekit_native_launch.py) | \"native_capture\" / \"native_spread\" (+ "
                         "\"source\" COMMITTED native audit receipt recording the closed view's FAIL, \"cell\", "
                         "\"fix\") | \"flow_failure\" (+ \"failed_job\": the id of the failed, ADMITTED re-route "
                         "being retried) | native_reach (+ committed exact all-path audit and changed pin coordinates; same RTL/slot) | \"pg_binding\" (+ \"source\" COMMITTED native PG-binding audit summary that "
                         "records the closed view's unbound VDD/VSS terminals, \"fix\"; same RTL and outline)}")


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def clock_spreads(ev):
    """{corner: (spread_ps, basis)} for TT and FF from a clock record: the pin-flop (boundary register) spread
    "<c>_pin_spread_ps" when measured, else the all-register leaf spread "<c>_spread_ps" (older records, conservative)."""
    out = {}
    for c in ("tt", "ff"):
        if _num(ev.get(f"{c}_pin_spread_ps")):
            out[c] = (float(ev[f"{c}_pin_spread_ps"]), "pin-flop")
        elif _num(ev.get(f"{c}_spread_ps")):
            out[c] = (float(ev[f"{c}_spread_ps"]), "leaf")
    return out


def clock_pair_skews(ev):
    """{corner: worst |related flop-pair skew| ps (CPPR credited)} for TT and FF from a clock record
    ("<c>_pair_skew_ps"; owner 10-23)."""
    return {c: float(ev[f"{c}_pair_skew_ps"]) for c in ("tt", "ff") if _num(ev.get(f"{c}_pair_skew_ps"))}


def clock_rule_eval(max_sinks, evidence=None):
    """The clock rule (OWNER DECISION 2026-10-23, supersedes the 10-17 0dq spread FAIL): FAIL only on a measured
    related launch/capture flop-pair skew with CPPR credit > CLK_PAIR_SKEW_MAX_PS at TT or FF.  The pin-flop / leaf
    spread is reported, never a FAIL; a measured clock record without pair skew WARNs ("pair skew not measured").
    Insertion > CLK_INSERTION_MAX_PS and > CLK_ROOT_SINKS_MAX sinks on one root are guidance: WARN.  evidence: the kit
    gate result's "clock" record ({"max_root_sinks", "tt_insertion_ps", "tt_spread_ps", "tt_pin_spread_ps",
    "tt_pair_skew_ps", "ff_..."}) or None.  Returns (level, text), level PASS / WARN / FAIL; text always carries the
    measured numbers when they exist."""
    ev = evidence if isinstance(evidence, dict) else {}
    ins, evn = ev.get("tt_insertion_ps"), ev.get("max_root_sinks")
    sp = clock_spreads(ev)
    pk = clock_pair_skews(ev)
    parts = []
    if _num(ins):
        parts.append(f"measured TT insertion {ins:.1f} ps")
    if _num(ev.get("ff_insertion_ps")):
        parts.append(f"FF insertion {ev['ff_insertion_ps']:.1f} ps")
    for c, v in pk.items():
        parts.append(f"{c.upper()} pair skew {v:.1f} ps")
    for c, (v, basis) in sp.items():
        parts.append(f"{c.upper()} {basis} spread {v:.1f} ps (info)")
    if "tt" in sp and "ff" not in sp:
        parts.append("FF spread not measured")
    measured = bool(sp or pk or _num(ins) or _num(ev.get("ff_insertion_ps")))
    meas = ", ".join(parts) if parts else "no measured clock tree (no --cts gate evidence)"
    fail = [f"{c.upper()} pair skew {v:.1f} ps > {CLK_PAIR_SKEW_MAX_PS:.0f}" for c, v in pk.items()
            if v > CLK_PAIR_SKEW_MAX_PS]
    warn = []
    if measured and not pk:
        warn.append("pair skew not measured (owner 10-23 gate: related flop-pair skew with CPPR <= "
                    f"{CLK_PAIR_SKEW_MAX_PS:.0f} ps at TT and FF; spread is information only)")
    elif pk and len(pk) < 2:
        warn.append(f"{'FF' if 'tt' in pk else 'TT'} pair skew not measured")
    if max_sinks is not None and max_sinks > CLK_ROOT_SINKS_MAX:
        warn.append(f"{max_sinks:,} sinks on one clock root > {CLK_ROOT_SINKS_MAX:,} (guidance)")
        if not measured:
            warn.append("no measured clock tree: run the --cts gate")
        elif _num(evn) and evn < 0.9 * max_sinks:
            warn.append(f"the gate evidence was measured on a root of {evn:,} sinks, not this netlist: re-run --cts")
    if _num(ins) and ins > CLK_INSERTION_MAX_PS:
        warn.append(f"insertion {ins:.1f} ps > {CLK_INSERTION_MAX_PS:.0f} (guidance; boundary matched by parent "
                    "compensation / landing)")
    head = ("clock sinks unknown" if max_sinks is None else
            f"{max_sinks:,} sinks on the largest root") + f"; {meas}"
    if fail:
        return "FAIL", f"{head}; " + " and ".join(fail)
    if warn:
        return "WARN", f"{head}; WARN: " + "; ".join(warn)
    return "PASS", head + (f" (pair skew <= {CLK_PAIR_SKEW_MAX_PS:.0f} ps)" if pk else "")


CLOCK_WAIVER_MAX_PS = 2.0     # HANDOFF 0ga 2026-10-18: largest recorded per-pair excess (over CLK_PAIR_SKEW_MAX_PS since 10-23)
# COORD 10-20 19:25 (rule freeze; spread accepted for route, route timing decides, fail -> regional root split):
# SCOPED caps above limit + CLOCK_WAIVER_MAX_PS, one tile each.  A waiver uses one only when it names the tile in
# "scope" and its recorded tt_ps/ff_ps stay within the cap.  Never a general relaxation.
SCOPED_CLOCK_WAIVER_CAPS = {
    "qkd_pv_fin_s32": {"tt": 88.4, "ff": 84.6},     # KV PVFIN R15c, 38k-sink single root, COORD 10-20 19:25
    "qfd_native59_svc": {"tt": 84.6},               # Qwen N59 svc4 (TT 84.6 / FF 77.5), 21,950-sink root, COORD 10-20 17:33
}


def clock_waiver_eval(evidence, waiver, tile=None):
    """HANDOFF 0ga 2026-10-18 (s81lk_kp4_dec syn-dly 80.5 FF vs 80): a coordinator-recorded per-pair excess, the job
    spec's "clock_rule_waiver" {"pair": "a-b", "ff_ps"|"tt_ps": measured, "limit_ps", "by"}.  Since the owner's 10-23
    gate it applies to the measured PAIR SKEW numbers ("<c>_pair_skew_ps") the same way it applied to spreads: every
    over-limit corner pair skew must be <= limit + CLOCK_WAIVER_MAX_PS (or the tile's scoped cap), <= the recorded
    value, and, when the evidence names its worst pair ("<c>_pair_skew_pair": [launch, capture]), come from the
    named child pair.  Spread values are never judged (they no longer FAIL).  One rule for pre_route_gate and the
    in-flow textbook_lint.  Returns (applied, note, why): note is the printable waiver, why the reasons it was not
    applied."""
    if not isinstance(waiver, dict):
        return False, "", ["no clock_rule_waiver"]
    ev = evidence if isinstance(evidence, dict) else {}
    lim = CLK_PAIR_SKEW_MAX_PS
    pair = {x.strip().removeprefix("u_") for x in str(waiver.get("pair", "")).split("-") if x.strip()}
    why = []
    if not str(waiver.get("by", "")).strip():
        why.append("no 'by'")
    if not _num(waiver.get("limit_ps")) or float(waiver["limit_ps"]) != lim:
        why.append(f"limit_ps must be {lim:.0f}")

    def named(inst):  # waiver tokens name the child instance (u_dly / dly) or its block suffix (s81lk_kp4_ddly / ddly)
        inst = [str(x).split("/", 1)[0].split(".", 1)[0].removeprefix("u_") for x in inst]
        return len(pair) == 2 and all(any(t.endswith(x) for t in pair) for x in inst) \
            and all(any(t.endswith(x) for x in inst) for t in pair)
    over = 0
    for c, v in clock_pair_skews(ev).items():
        if v <= lim:
            continue
        over += 1
        rec_ps = waiver.get(f"{c}_ps")
        if not _num(rec_ps) or v > float(rec_ps) + 1e-6:
            why.append(f"{c.upper()} {v:.1f} ps not recorded in the waiver ({c}_ps={rec_ps})")
        scope = str(waiver.get("scope", ""))
        cap = SCOPED_CLOCK_WAIVER_CAPS.get(scope, {}).get(c)
        if cap is not None and tile is not None and str(tile) != scope:
            why.append(f"scoped waiver {scope} does not apply to tile {tile}")
        if cap is not None:
            if v > cap + 1e-6:
                why.append(f"{c.upper()} {v:.1f} ps exceeds the scoped cap {cap} of {waiver.get('scope')}")
        elif v > lim + CLOCK_WAIVER_MAX_PS:
            why.append(f"{c.upper()} {v:.1f} ps exceeds limit + {CLOCK_WAIVER_MAX_PS:.0f}")
        wp = ev.get(f"{c}_pair_skew_pair")
        if isinstance(wp, (list, tuple)) and len(wp) == 2 and not named(wp):
            why.append(f"{c.upper()} worst pair {wp[0]} -> {wp[1]} is not the named pair {waiver.get('pair')}")
    if not over:
        why.append("no over-limit pair skew in the evidence")
    if why:
        return False, "", why
    note = (f"clock_rule_waiver by {waiver['by']}: pair {waiver.get('pair')} "
            + ", ".join(f"{c}_ps {waiver[c + '_ps']}" for c in ("tt", "ff") if f"{c}_ps" in waiver)
            + f" vs limit {lim:.0f}")
    return True, note, []


def clock_rule(max_sinks, evidence=None):
    """(ok, text): ok is False only on the FAIL of clock_rule_eval (pair skew > 80 ps at TT or FF); WARN is ok."""
    level, text = clock_rule_eval(max_sinks, evidence)
    return level != "FAIL", text


# checks whose refuse tier REFUSES in refuse mode; util_channel stays WARN (false positives on closed blocks)
REFUSE_CHECKS = ("clock_domain", "high_fanout", "boundary", "logic_depth", "wire_reach")

OUT_PINS = {"Y", "QN", "Q", "CON", "SN", "GCLK", "H", "L"}
FLOP_RE = re.compile(r"^(ASYNC_)?(S?DFF|SDF[HL]|DHL|DLL)", re.I)
ICG_RE = re.compile(r"^ICG", re.I)
BUFINV_RE = re.compile(r"^(BUF|INV|CKINV|HB\d)", re.I)
TIE_RE = re.compile(r"^TIE(HI|LO)", re.I)
PHYS_RE = re.compile(r"TAPCELL|FILL|DECAP|ENDCAP|WELLTAP|ANTENNA", re.I)
CLKPIN_RE = re.compile(r"^(clk|ck|clock|CLK|CK)(_?[a-z0-9]*)?$", re.I)
RST_RE = re.compile(r"(^|[\s_.\\/])(p?a?rst|reset|rsv?)(_?n|_ni|_i|_[a-z0-9]+)?($|[\s_\[.$/])", re.I)


def declared_resets(T):
    """GATE-FRICTION 2026-10-18 (KV core_peer por_n, 5,344 async loads, refused as a DATA port > 2,048): the kit spec's
    reset_ports (passed as --set reset_ports=a,b or cfg set) are resets whatever their name; plus power-on-reset names
    (por, por_n, poweron_rst ...)."""
    v = (T or {}).get("reset_ports") or ()
    names = [x.strip() for x in (v.split(",") if isinstance(v, str) else v) if str(x).strip()]
    return {re.sub(r"\[.*$", "", str(n)) for n in names}


POR_RE = re.compile(r"(^|[\s_.\\/])(por|poweron|power_on)(_?n|_ni|_i|_[a-z0-9]+)?($|[\s_\[.$/])", re.I)


def is_reset_net(label, net, T=None, port=True):
    """reset-named (RST_RE) nets as before; a power-on-reset name or a declared reset_ports entry counts only for a
    PORT-driven net (so the change only ever relaxes: a data-port limit 2,048 -> the reset limit 8,000)."""
    if RST_RE.search(label) or RST_RE.search(net):
        return True
    if not port:
        return False
    if POR_RE.search(label) or POR_RE.search(net):
        return True
    decl = declared_resets(T)
    if not decl:
        return False
    base = re.sub(r"\[.*$", "", re.sub(r"^port\s+", "", str(label)).strip())
    return base in decl or re.sub(r"\[.*$", "", str(net)) in decl
SEQ_CLK_PINS = {"CLK"}
ASYNC_PINS = {"RESET", "SET", "RESETN", "SETN"}
# reset_landing port names: the rst_port_fanout PORT_RE spelling (rst / arst / prst / reset [_n|_ni|_i|_b]) plus por;
# stricter than RST_RE (no 'rsv' / '_x' suffixes: S81 rsv_* reservation-station data ports are not resets)
RST_LAND_RE = re.compile(r"(^|_)(p?a?rst|reset|por)(_?n|_ni|_i|_b)?$", re.I)

# ASAP7 75t cell delay weights (ps, TT, typical fan-out; calibrated so that the closed validation blocks' worst stage
# sits at <= ~700 ps). The exact numbers matter less than the ratio failing / closed.
WEIGHTS = (
    (re.compile(r"^(INV|CKINV)"), 7.0),
    (re.compile(r"^(BUF|HB\d)"), 12.0),
    (re.compile(r"^(NAND|NOR)2"), 12.0),
    (re.compile(r"^(NAND|NOR)[34]"), 17.0),
    (re.compile(r"^(NAND|NOR)5"), 22.0),
    (re.compile(r"^(AND|OR)[2]"), 17.0),
    (re.compile(r"^(AND|OR)[345]"), 22.0),
    (re.compile(r"^(A|O)(O|A)I?\d"), 18.0),
    (re.compile(r"^(XOR|XNOR)"), 22.0),
    (re.compile(r"^MAJ"), 20.0),
    (re.compile(r"^(FA|HA)"), 28.0),
)
DEFAULT_W = 18.0


def cell_w(t: str) -> float:
    for rx, w in WEIGHTS:
        if rx.match(t):
            return w
    return DEFAULT_W


# --------------------------------------------------------------------------------------------- netlist reading
TOK = re.compile(r"\\(\S+)|([A-Za-z_][A-Za-z0-9_$]*)|(\d*'[sS]?[bBhHdDoO][0-9a-fA-FxXzZ_?]+|\d+)|(\S)")


def _consts(tok: str) -> list[str]:
    m = re.match(r"(\d*)'[sS]?([bBhHdDoO])([0-9a-fA-FxXzZ_?]+)", tok)
    if not m:
        n = int(tok)
        return ["1'" + c for c in format(n, "032b")]
    w = int(m.group(1) or 32)
    base = {"b": 2, "h": 16, "d": 10, "o": 8}[m.group(2).lower()]
    v = m.group(3).replace("_", "")
    if base == 10:
        bits = format(int(v), "b")
    else:
        per = {2: 1, 8: 3, 16: 4}[base]
        bits = "".join("x" * per if c in "xXzZ?" else format(int(c, base), f"0{per}b") for c in v)
    bits = bits[-w:].rjust(w, bits[0] if bits and bits[0] in "xz" else "0")
    return ["1'" + c for c in bits]


class Module:
    __slots__ = ("name", "ports", "dirs", "widths", "assigns", "insts")

    def __init__(self, name):
        self.name, self.ports, self.dirs, self.widths, self.assigns, self.insts = name, [], {}, {}, [], []


def _tok(s: str):
    return [(m.group(1), m.group(2), m.group(3), m.group(4)) for m in TOK.finditer(s)]


PIN_RE = re.compile(r"\.\s*(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)\s*\(((?:\\\S+\s|[^()\\])*)\)")
HEAD_RE = re.compile(r"^\s*(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)\s+(?:#\s*\((?:[^()]|\([^()]*\))*\)\s*)?"
                     r"(\\\S+|[A-Za-z_][A-Za-z0-9_$]*)\s*\(", re.S)
DECL_KW = ("input", "output", "inout", "wire", "reg", "tri", "supply0", "supply1")


def parse_verilog(text: str) -> dict:
    """structural Verilog (yosys / OpenROAD write_verilog) -> {module name: Module}.  Statement-streaming (a 600 MB
    netlist is read without a whole-file token list).  Bits are names: 'w' (scalar) or 'w[i]'; constants '1'0' etc.
    Instance pins keep their token lists (expanded to bits MSB first by expr_bits at flatten time)."""
    text = re.sub(r"\(\*.*?\*\)", " ", text, flags=re.S)
    if "/*" in text:
        text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    if "//" in text:
        text = re.sub(r"(?m)(^|\s)//[^\n]*", " ", text)
    mods = {}
    mod = None
    for raw in text.split(";"):
        st = raw.strip()
        if not st:
            continue
        if mod is None or st.startswith("module") or "endmodule" in st:
            while "endmodule" in st:
                pre, st = st.split("endmodule", 1)
                if mod is not None:
                    mods[mod.name] = mod
                    mod = None
                st = st.strip()
            if not st:
                continue
            if st.startswith("module"):
                toks = _tok(st)
                mod = Module(toks[1][0] if toks[1][0] is not None else toks[1][1])
                for t in toks[2:]:
                    nm = t[0] if t[0] is not None else t[1]
                    if nm and nm not in ("input", "output", "inout", "wire", "reg", "signed", "logic"):
                        mod.ports.append(nm)
                continue
            if mod is None:
                continue
        first = st.split(None, 1)[0]
        if first in DECL_KW:
            toks = _tok(st)
            kw = toks[0][1]
            k, msb, lsb = 1, None, None
            while k < len(toks) and toks[k][1] in ("signed", "wire", "reg", "logic"):
                k += 1
            if k < len(toks) and toks[k][3] == "[":
                msb, lsb = int(toks[k + 1][2]), int(toks[k + 3][2])
                k += 5
            for t in toks[k:]:
                nm = t[0] if t[0] is not None else t[1]
                if nm:
                    if msb is not None:
                        mod.widths[nm] = (msb, lsb)
                    if kw in ("input", "output", "inout"):
                        mod.dirs[nm] = kw
                        if nm not in mod.ports:
                            mod.ports.append(nm)
            continue
        if first == "assign":
            lhs, rhs = st[6:].split("=", 1)
            mod.assigns.append((_tok(lhs), _tok(rhs)))
            continue
        if first in ("parameter", "localparam", "defparam", "`timescale"):
            continue
        m = HEAD_RE.match(st)
        if not m:
            continue
        typ, iname = m.group(1), m.group(2)
        typ = typ[1:] if typ.startswith("\\") else typ
        iname = iname[1:] if iname.startswith("\\") else iname
        pins = {}
        for pm in PIN_RE.finditer(st, m.end()):
            pn = pm.group(1)
            pins[pn[1:] if pn.startswith("\\") else pn] = pm.group(2)
        mod.insts.append((typ, iname, pins))
    if mod is not None:
        mods[mod.name] = mod
    return mods


SIMPLE_RE = re.compile(r"^\s*(?:\\(\S+)|([A-Za-z_][A-Za-z0-9_$]*)(?:\s*\[\s*(\d+)\s*\])?)\s*$")


def expr_bits(toks, widths) -> list[str]:
    """expression (string or token list) -> bit names, MSB first"""
    if isinstance(toks, str):
        m = SIMPLE_RE.match(toks)
        if m:
            if m.group(1) is not None:
                nm = m.group(1)
                if nm in widths:
                    msb, lsb = widths[nm]
                    rng = range(msb, lsb - 1, -1) if msb >= lsb else range(msb, lsb + 1)
                    return [f"{nm}[{x}]" for x in rng]
                return [nm]
            nm = m.group(2)
            if m.group(3) is not None:
                return [f"{nm}[{m.group(3)}]"]
            if nm in widths:
                msb, lsb = widths[nm]
                rng = range(msb, lsb - 1, -1) if msb >= lsb else range(msb, lsb + 1)
                return [f"{nm}[{x}]" for x in rng]
            return [nm]
        if not toks.strip():
            return []
        toks = _tok(toks)
    out = []
    k = 0
    n = len(toks)

    def ident(t):
        return t[0] if t[0] is not None else t[1]

    def primary(k):
        t = toks[k]
        if t[3] == "{":
            bits, k = [], k + 1
            while k < n and toks[k][3] != "}":
                if toks[k][3] == ",":
                    k += 1
                    continue
                b, k = primary(k)
                bits += b
            return bits, k + 1
        if t[2] is not None:
            # replication {N{x}} is rare in netlists: plain constant
            return _consts(t[2]), k + 1
        nm = ident(t)
        if nm is None:
            return [], k + 1
        k += 1
        if k < n and toks[k][3] == "[":
            a = int(toks[k + 1][2])
            if toks[k + 2][3] == ":":
                b = int(toks[k + 3][2])
                k += 5
                rng = range(a, b - 1, -1) if a >= b else range(a, b + 1)
                return [f"{nm}[{x}]" for x in rng], k
            return [f"{nm}[{a}]"], k + 3
        if nm in widths:
            msb, lsb = widths[nm]
            rng = range(msb, lsb - 1, -1) if msb >= lsb else range(msb, lsb + 1)
            return [f"{nm}[{x}]" for x in rng], k
        return [nm], k

    while k < n:
        if toks[k][3] == ",":
            k += 1
            continue
        b, k = primary(k)
        out += b
    return out


# --------------------------------------------------------------------------------------------- flat graph
class Graph:
    """flat bit-level netlist: nets are ints; cells are (type, name, {pin: [net, ...] MSB first})"""

    def __init__(self):
        self.net_id, self.net_name = {}, []
        self.parent = []
        self.cells = []            # (type, name, pins)
        self.ports = {}            # bit name -> (dir, net)

    def net(self, name):
        i = self.net_id.get(name)
        if i is None:
            i = self.net_id[name] = len(self.net_name)
            self.net_name.append(name)
            self.parent.append(i)
        return i

    def find(self, i):
        p = self.parent
        while p[i] != i:
            p[i] = p[p[i]]
            i = p[i]
        return i

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            # keep a port / readable name as representative: prefer the lower id (declared first)
            if ra < rb:
                self.parent[rb] = ra
            else:
                self.parent[ra] = rb


def flatten(mods: dict, top: str | None) -> tuple[Graph, str]:
    if top is None or top not in mods:
        users = {t for m in mods.values() for t, _, _ in m.insts}
        cands = [m for m in mods if m not in users]
        top = cands[0] if cands else next(iter(mods))
    g = Graph()
    for c in ("1'0", "1'1", "1'x", "1'z"):
        g.net(c)
    sys.setrecursionlimit(10000)

    def bits_of(mod, nm):
        if nm in mod.widths:
            msb, lsb = mod.widths[nm]
            rng = range(msb, lsb - 1, -1) if msb >= lsb else range(msb, lsb + 1)
            return [f"{nm}[{x}]" for x in rng]
        return [nm]

    def local(prefix, bit):
        return bit if bit.startswith("1'") else prefix + bit

    def emit(mod, prefix, bind):
        def nid(bit):
            if bit in bind:
                return bind[bit]
            return g.net(local(prefix, bit))
        for lhs, rhs in mod.assigns:
            lb, rb = expr_bits(lhs, mod.widths), expr_bits(rhs, mod.widths)
            for a, b in zip(reversed(lb), reversed(rb)):
                g.union(nid(a), nid(b))
        for typ, iname, pins in mod.insts:
            if typ in mods:
                sub = mods[typ]
                sb = {}
                for pn, toks in pins.items():
                    pb = bits_of(sub, pn)
                    cb = expr_bits(toks, mod.widths)
                    for a, b in zip(reversed(pb), reversed(cb)):
                        sb[a] = nid(b)
                emit(sub, f"{prefix}{iname}.", sb)
            else:
                g.cells.append((typ, prefix + iname, {pn: [nid(b) for b in expr_bits(toks, mod.widths)]
                                                      for pn, toks in pins.items()}))
    tm = mods[top]
    bind = {}
    for p in tm.ports:
        for b in bits_of(tm, p):
            bind[b] = g.net(b)
            g.ports[b] = (tm.dirs.get(p, "input"), bind[b])
    emit(tm, "", bind)
    # canonicalise nets after assign unions
    g.cells = [(t, nm, {pn: [g.find(x) for x in bs] for pn, bs in pins.items()}) for t, nm, pins in g.cells]
    g.ports = {b: (d, g.find(x)) for b, (d, x) in g.ports.items()}
    return g, top


# --------------------------------------------------------------------------------------------- analysis
def _base(pin):
    return re.sub(r"\[\d+\]$", "", pin)


def build(g: Graph, dump: dict | None):
    """classify cells, assign pin directions, build driver / load tables"""
    macro_dirs, macro_pos, macro_inst = defaultdict(dict), {}, {}
    if dump:
        for m in dump.get("macros", []):
            nm = m["name"].replace("\\", "")
            macro_inst[nm] = m
            for p in m.get("pins", []):
                pn, x, y, d = p[0], p[1], p[2], p[3]
                macro_dirs[m["master"]][_base(pn)] = d
                macro_pos[(nm, pn)] = (x, y)
    ncell = len(g.cells)
    kind = [""] * ncell            # 'ff' 'icg' 'buf' 'tie' 'comb' 'macro' 'phys'
    pin_dir = []                   # per cell: {pin: 'in'|'out'}
    driver = {}                    # net -> (cell or -1 port, pin)
    loads = defaultdict(list)      # net -> [(cell, pin, bitidx)]
    unknown_cells = []
    for ci, (t, nm, pins) in enumerate(g.cells):
        if PHYS_RE.search(t):
            kind[ci] = "phys"
        elif FLOP_RE.match(t):
            kind[ci] = "ff"
        elif ICG_RE.match(t):
            kind[ci] = "icg"
        elif TIE_RE.match(t):
            kind[ci] = "tie"
        elif BUFINV_RE.match(t):
            kind[ci] = "buf"
        elif "ASAP7" in t:
            kind[ci] = "comb"
        else:
            kind[ci] = "macro"
        pd = {}
        if kind[ci] == "macro":
            md = macro_dirs.get(t, {})
            for pn in pins:
                d = md.get(pn) or md.get(_base(pn))
                if d is None and md:
                    d = next((v for k, v in md.items() if _base(k) == pn), None)
                pd[pn] = "out" if d == "OUTPUT" else ("in" if d else None)
            if any(v is None for v in pd.values()):
                unknown_cells.append(ci)
        else:
            for pn in pins:
                pd[pn] = "out" if pn in OUT_PINS else "in"
        pin_dir.append(pd)
    for b, (d, x) in g.ports.items():
        if d == "input":
            driver[x] = (-1, b)
    for ci in range(ncell):
        for pn, bs in g.cells[ci][2].items():
            if pin_dir[ci].get(pn) == "out":
                for k, x in enumerate(bs):
                    driver.setdefault(x, (ci, pn))
    for ci in unknown_cells:          # black box without directions: an undriven net on its pin is its output
        for pn, bs in g.cells[ci][2].items():
            if pin_dir[ci].get(pn) is None:
                pin_dir[ci][pn] = "out" if all(x not in driver and x > 3 for x in bs) else "in"
                if pin_dir[ci][pn] == "out":
                    for x in bs:
                        driver.setdefault(x, (ci, pn))
    for ci in range(ncell):
        for pn, bs in g.cells[ci][2].items():
            if pin_dir[ci].get(pn) == "in":
                w = len(bs)
                for k, x in enumerate(bs):
                    loads[x].append((ci, pn, w - 1 - k))
    out_ports = defaultdict(list)
    for b, (d, x) in g.ports.items():
        if d == "output":
            out_ports[x].append(b)
    return dict(kind=kind, pin_dir=pin_dir, driver=driver, loads=loads, out_ports=out_ports,
                macro_pos=macro_pos, macro_inst=macro_inst)


def _in_nets(g, A, ci, skip_clk=True):
    pd = A["pin_dir"][ci]
    for pn, bs in g.cells[ci][2].items():
        if pd.get(pn) == "in" and not (skip_clk and pn in SEQ_CLK_PINS):
            for x in bs:
                yield x


def _out_nets(g, A, ci):
    pd = A["pin_dir"][ci]
    for pn, bs in g.cells[ci][2].items():
        if pd.get(pn) == "out":
            for x in bs:
                yield x


def net_label(g, A, x):
    d = A["driver"].get(x)
    if d is None:
        return g.net_name[x]
    ci, pn = d
    if ci < 0:
        return f"port {pn}"
    t, nm, _ = g.cells[ci]
    if A["kind"][ci] in ("ff", "macro"):
        return f"{nm}/{pn} ({t})"
    nn = g.net_name[x]
    return nn if not nn.startswith("_") else f"{nm}/{pn} ({t})"


def clock_nets(g, A):
    """nets that feed a flop / ICG / macro clock pin through BUF / INV / ICG only, and each sink's root"""
    kind, driver = A["kind"], A["driver"]
    clk = set()
    root_of = {}

    def root(x, depth=0):
        if x in root_of:
            return root_of[x]
        clk.add(x)
        d = driver.get(x)
        r = None
        if d is None:
            r = ("undriven", g.net_name[x])
        elif d[0] < 0:
            r = ("port", d[1])
        else:
            ci = d[0]
            k = kind[ci]
            if depth < 64 and (k == "buf" or k == "icg"):
                pins = g.cells[ci][2]
                src = pins.get("A") or pins.get("CLK") or next(iter(_in_nets(g, A, ci, False)), None)
                if isinstance(src, list):
                    src = src[0] if src else None
                r = root(src, depth + 1) if src is not None else ("cell", g.cells[ci][1])
            elif k == "ff":
                r = ("divided", g.cells[ci][1])
            else:
                r = ("logic", g.cells[ci][1] + "/" + d[1])
        root_of[x] = r
        return r
    sinks = defaultdict(lambda: {"ff": 0, "icg": 0, "macro_pins": 0, "example": None})
    for ci, (t, nm, pins) in enumerate(g.cells):
        k = kind[ci]
        if k in ("ff", "icg"):
            for x in pins.get("CLK", []):
                r = root(x)
                s = sinks[r]
                s["ff" if k == "ff" else "icg"] += 1
                s["example"] = s["example"] or nm
        elif k == "macro":
            for pn, bs in pins.items():
                if A["pin_dir"][ci].get(pn) == "in" and CLKPIN_RE.match(_base(pn)):
                    for x in bs:
                        sinks[root(x)]["macro_pins"] += 1
    return clk, sinks


def bufinv_fanout(g, A, x, clk, limit=10_000_000):
    """sinks of net x counting through BUF / INV trees: (total non-buffer load pins, flop loads, port loads, example)"""
    kind, loads = A["kind"], A["loads"]
    tot = ff = 0
    stack, seen = [x], {x}
    ex = None
    while stack:
        y = stack.pop()
        for ci, pn, _ in loads.get(y, ()):
            if kind[ci] == "buf":
                for z in _out_nets(g, A, ci):
                    if z not in seen:
                        seen.add(z)
                        stack.append(z)
                continue
            tot += 1
            if kind[ci] == "ff":
                ff += 1
                ex = ex or g.cells[ci][1]
        if tot > limit:
            break
    ports = sum(len(A["out_ports"].get(y, ())) for y in seen)
    return tot + ports, ff, ex


def reset_sinks(g, A, x):
    """sinks of reset net x through BUF / INV trees: (total load pins incl. output ports, flops, macros, example)"""
    kind, loads = A["kind"], A["loads"]
    tot = ff = mac = 0
    stack, seen, ex = [x], {x}, None
    while stack:
        y = stack.pop()
        for ci, pn, _ in loads.get(y, ()):
            if kind[ci] == "buf":
                for z in _out_nets(g, A, ci):
                    if z not in seen:
                        seen.add(z)
                        stack.append(z)
                continue
            tot += 1
            ff += kind[ci] == "ff"
            mac += kind[ci] == "macro"
            ex = ex or f"{g.cells[ci][1]}/{pn}"
    tot += sum(len(A["out_ports"].get(y, ())) for y in seen)
    return tot, ff, mac, ex


def async_two_stage_reset_proof(g, A, port, net):
    """Recognise the exact ASAP7 async-assert/two-edge release landing shape.

    Raw reset is permitted only on RESETN of these landing flops. First D
    is tied high; every final D is the positive first-stage value. This is
    structural classification, not a sink-count exemption or an RTL waiver.
    The supported master has QN=!state, active-low RESETN/SETN, reset priority;
    SETN stays inactive. Other masters/control roles retain the legacy rule.
    """
    def fail(reason):
        return {'pass': False, 'reason': reason}

    def unary_origin(q):
        seen = set(); parity = 0
        while True:
            if q in seen:
                return None, parity
            seen.add(q)
            drv = A['driver'].get(q)
            if drv is None or drv[0] < 0 or A['kind'][drv[0]] != 'buf':
                return q, parity
            ci, _ = drv[:2]
            typ, _, pins = g.cells[ci]
            ins = [v for pn, bs in pins.items() if A['pin_dir'][ci].get(pn) == 'in' for v in bs]
            outs = list(_out_nets(g, A, ci))
            if len(ins) != 1 or outs != [q] or not re.match(r'^(INV|BUF|CKINV|CKBUF)', typ):
                return None, parity
            parity ^= bool(re.match(r'^(INV|CKINV)', typ))
            q = ins[0]

    def high(q):
        q, parity = unary_origin(q)
        if q is None or parity:
            return False
        if q == 1 and g.net_name[q] == "1'1":
            return True
        drv = A['driver'].get(q)
        if drv is None or drv[0] < 0:
            return False
        typ, _, pins = g.cells[drv[0]]
        return typ == 'TIEHIx1_ASAP7_75t_R' and pins == {'H': [q]}

    def terminals(q):
        todo = [(q, 0)]; seen = set(); ends = []; ports = 0
        while todo:
            x, parity = todo.pop()
            if (x, parity) in seen:
                continue
            seen.add((x, parity)); ports += len(A['out_ports'].get(x, ()))
            for ci, pn, _ in A['loads'].get(x, ()):
                if A['kind'][ci] == 'buf':
                    typ, _, pins = g.cells[ci]
                    ins = [v for k, bs in pins.items() if A['pin_dir'][ci].get(k) == 'in' for v in bs]
                    outs = list(_out_nets(g, A, ci))
                    if ins != [x] or len(outs) != 1 or not re.match(r'^(INV|BUF|CKINV|CKBUF)', typ):
                        return None, ports
                    neg = bool(re.match(r'^(INV|CKINV)', typ))
                    todo.append((outs[0], parity ^ neg))
                else:
                    ends.append((ci, pn, parity))
        return ends, ports

    roots = A['loads'].get(net, ())
    if A['out_ports'].get(net) or not 2 <= len(roots) <= 32:
        return fail('raw reset exported or root count outside bounded shape')
    cells = set(); clock = None
    for ci, pn, _ in roots:
        typ, _, pins = g.cells[ci]
        if (typ != 'DFFASRHQNx1_ASAP7_75t_R' or pn != 'RESETN'
                or set(pins) != {'CLK', 'D', 'QN', 'RESETN', 'SETN'}
                or any(len(v) != 1 for v in pins.values())
                or pins['RESETN'] != [net] or not high(pins['SETN'][0])):
            return fail('raw reset reaches a foreign cell/control/data role')
        if clock is None:
            clock = pins['CLK'][0]
        if pins['CLK'] != [clock]:
            return fail('landing clocks differ')
        cells.add(ci)
    clock_ports = [n for n, (direction, q) in g.ports.items() if direction == 'input' and q == clock]
    if len(clock_ports) != 1 or clock == net or len(cells) != len(roots):
        return fail('clock is not one literal input or root roles repeat')
    first = {ci for ci in cells if high(g.cells[ci][2]['D'][0])}
    final = cells - first
    if not first or not final:
        return fail('missing first or final landing stage')
    qfirst = {g.cells[ci][2]['QN'][0]: ci for ci in first}
    used = set()
    for ci in final:
        q, parity = unary_origin(g.cells[ci][2]['D'][0])
        if q not in qfirst or parity != 1:
            return fail('final D is not positive first-stage Q')
        used.add(qfirst[q])
    if used != first:
        return fail('orphan first-stage copy')
    first_max = final_max = 0
    for ci in first:
        ends, ports = terminals(g.cells[ci][2]['QN'][0])
        if ends is None or ports or not ends or len(ends) > 32:
            return fail('first stage exported, empty, or exceeds32')
        if any(cj not in final or pn != 'D' or parity != 1 for cj, pn, parity in ends):
            return fail('first stage reaches another role, stage, or polarity')
        first_max = max(first_max, len(ends))
    for ci in final:
        ends, ports = terminals(g.cells[ci][2]['QN'][0])
        if ends is None or ports or not ends or len(ends) > 32:
            return fail('final stage exported, empty, or exceeds32')
        if any(cj in cells for cj, _, _ in ends):
            return fail('landing feedback or extra landing stage')
        # RESETN publications must retain positive active-low reset polarity.
        # Ordinary downstream control/data logic is outside this two-stage
        # landing; it is still subject to the ordinary timing/native checks.
        if any(pn in ASYNC_PINS and (pn != 'RESETN' or parity != 1) for _, pn, parity in ends):
            return fail('wrong asynchronous publication role or polarity')
        final_max = max(final_max, len(ends))
    return dict({'pass': True}, first=len(first), final=len(final), edges=2,
                root_loads=len(roots), clock=clock_ports[0], first_max_loads=first_max,
                final_max_loads=final_max, master='DFFASRHQNx1_ASAP7_75t_R',
                first_cells=sorted(g.cells[ci][1] for ci in first),
                final_cells=sorted(g.cells[ci][1] for ci in final))


def balanced_reset_proof(g, A, port, net, profile):
    """Opt-in mapped proof, never a threshold waiver: exactly two plain-FF levels.

    The source-pinned profile supplies exact counts; the actual netlist proves
    data, clock, polarity, depth and all fanouts. Unprofiled designs retain the
    existing <=2 root-sink rule. BUF/INV paths are counted with exact polarity on both publication edges.
    """
    def fail(why):
        return {"pass": False, "reason": why}
    if not isinstance(profile, dict) or profile.get('schema') != 'opentallas.ref_tile.reset_landing.v1':
        return fail('missing/foreign profile')
    if profile.get('enable') is not True or profile.get('stages') != 2:
        return fail('profile must enable exactly two edges')
    f = (profile.get('first_copies') or {}).get(port)
    l = (profile.get('copies') or {}).get(port)
    if (not isinstance(f,int) or isinstance(f,bool) or not 1<=f<=32 or
            not isinstance(l,int) or isinstance(l,bool) or not 1<=l<=32*f):
        return fail('invalid exact first/final counts')
    cp=profile.get('clock');clock=[x for n,(d,x) in g.ports.items() if n==cp and d=='input']
    if len(clock)!=1:return fail('missing literal clock port')
    first=set();last=set();qfirst=set();qlast=set();master=None
    def terminals(q):
        stack=[(q,0)];seen=set();ends=[];ports=0
        while stack:
            y,inv=stack.pop()
            if (y,inv) in seen:continue
            seen.add((y,inv));ports+=len(A['out_ports'].get(y,()))
            for ci,pn,_ in A['loads'].get(y,()):
                if A['kind'][ci]=='buf':
                    neg=bool(re.match(r'^(INV|CKINV)',g.cells[ci][0]))
                    for z in _out_nets(g,A,ci):stack.append((z,inv^neg))
                else:ends.append((ci,pn,y,inv))
        return ends,ports
    def plain(ci,pn,d):
        nonlocal master
        typ,_,pins=g.cells[ci]
        if (A['kind'][ci]!='ff' or not re.fullmatch(r'DFFHQNx[0-9]+_ASAP7_75t_[RSL]',typ)
                or pn!='D' or pins.get('D')!=[d] or pins.get('CLK')!=clock):
            return False
        if any(k in pins for k in ASYNC_PINS) or set(pins)-{'CLK','D','QN','Q'}:
            return False
        if master is None:master=typ
        return typ==master and len(list(_out_nets(g,A,ci)))==1
    if A['out_ports'].get(net):return fail('reset input also exported')
    for ci,pn,_ in A['loads'].get(net,()):
        if not plain(ci,pn,net):return fail('root reaches non-identical/plain first D')
        first.add(ci);qfirst.update(_out_nets(g,A,ci))
    if len(first)!=f:return fail('stale first count')
    first_max=0
    for q in qfirst:
        if A['out_ports'].get(q):return fail('first stage also exported')
        children,ports=terminals(q);first_max=max(first_max,len(children))
        if ports:return fail('first stage also exported through buffers')
        if len(children)>32:return fail('first output exceeds32')
        for ci,pn,d,inv in children:
            # ASAP7 DFFHQN exposes inverted Q; exactly one net inversion restores
            # the logical first-stage value at every final-stage D.
            if ci in first or inv!=1 or not plain(ci,pn,d):return fail('first reaches non-identical/plain final D or wrong polarity')
            last.add(ci);qlast.update(_out_nets(g,A,ci))
    if len(last)!=l:return fail('stale final count')
    final_max=0
    for q in qlast:
        ends,ports=terminals(q);n=len(ends)+ports;final_max=max(final_max,n)
        if n>32:return fail('final output exceeds32')
        if ports:return fail('final stage exported outside declared core')
        if any(ci in first|last for ci,_,_,_ in ends):return fail('extra landing stage/feedback')
        if any(inv!=1 for _,_,_,inv in ends):return fail('wrong final reset publication polarity')
    return {"pass":True,"first":f,"final":l,"root_loads":f,
            "first_max_loads":first_max,"final_max_loads":final_max,"edges":2}


def analyse(g: Graph, dump: dict | None, th: dict) -> dict:
    T = th
    A = build(g, dump)
    kind, driver, loads = A["kind"], A["driver"], A["loads"]
    res = {"cells": len(g.cells), "flops": kind.count("ff"), "icgs": kind.count("icg"), "macros": kind.count("macro"),
           "findings": {}, "refuse": {}, "metrics": {}}
    F = res["findings"]
    RF = res["refuse"]
    M = res["metrics"]
    die = (dump or {}).get("core") or (dump or {}).get("die")
    W = H = None
    if die:
        W, H = die[2] - die[0], die[3] - die[1]
        M["core_um"] = [round(W, 1), round(H, 1)]

    # ---- 1. clock domains
    clk, sinks = clock_nets(g, A)
    doms = sorted(sinks.items(), key=lambda kv: -kv[1]["ff"])
    M["clock_roots"] = [{"root": f"{r[0]}:{r[1]}", **s} for r, s in doms[:6]]
    hier = sum(1 for ci, k in enumerate(kind) if k == "macro" and not re.search(r"sram|rom|regfile|rf_", g.cells[ci][0], re.I))
    M["hier_subblocks"] = hier
    big = max(doms, key=lambda kv: kv[1]["ff"] + kv[1]["macro_pins"], default=None)
    M["clock_max_root_sinks"] = (big[1]["ff"] + big[1]["macro_pins"]) if big else 0
    M["clock_max_root"] = f"{big[0][0]}:{big[0][1]}" if big else None
    bad = []
    for r, s in doms:
        n = s["ff"]
        why = None
        if n > T["clk_sinks_refuse"]:
            RF.setdefault("clock_domain", []).append(f"clock root {r[0]} {r[1]}: {n:,} flops > {T['clk_sinks_refuse']:,}")
        if n > T["clk_sinks_max"]:
            why = f"{n:,} flops > {T['clk_sinks_max']:,} on one root"
        elif W is not None and max(W, H) > T["clk_span_um"] and n > T["clk_span_sinks"]:
            why = (f"{n:,} flops > {T['clk_span_sinks']:,} spread over a {W:.0f} x {H:.0f} um outline "
                   f"(> {T['clk_span_um']:.0f} um)")
        if why:
            bad.append(f"clock root {r[0]} {r[1]}: {why} (+{s['icg']} ICGs, {s['macro_pins']} macro clock pins; "
                       f"e.g. {s['example']}): split into hierarchical sub-blocks (hardened elements with their own "
                       f"CTS) or a clock mesh / H-tree spine")
    if bad:
        F["clock_domain"] = bad

    # ---- 2. high fanout (roots only: drivers that are not BUF / INV)
    hf = []
    for x, d in driver.items():
        if x in clk or x <= 3:
            continue
        ci = d[0]
        if ci >= 0 and kind[ci] in ("buf", "tie"):
            continue
        nl = len(loads.get(x, ()))
        if nl < 8 and not any(kind[c] == "buf" for c, _, _ in loads.get(x, ())):
            continue
        tot, ff, ex = bufinv_fanout(g, A, x, clk)
        if tot > T["hf_report"]:
            hf.append((tot, ff, x, ex))
    hf.sort(reverse=True)
    M["high_fanout_top"] = [{"net": net_label(g, A, x), "loads": t, "flops": f} for t, f, x, _ in hf[:8]]
    bad = []
    M["hf_max_port"] = M["hf_max_reset"] = M["hf_max_net"] = 0
    for tot, ff, x, ex in hf:
        d = driver[x]
        lab = net_label(g, A, x)
        is_port = d[0] < 0
        is_rst = is_reset_net(lab, g.net_name[x], T, port=is_port)
        cat = "hf_max_reset" if is_rst else ("hf_max_port" if is_port else "hf_max_net")
        M[cat] = max(M[cat], tot)
        lim = T["hf_report"] if (is_port or is_rst) else T["hf_max"]
        rl = T["hf_reset_refuse"] if is_rst else (T["hf_port_refuse"] if is_port else T["hf_refuse"])
        if tot > rl:
            RF.setdefault("high_fanout", []).append(f"{'reset ' if is_rst else ('' if is_port else 'net ')}{lab}: "
                                                    f"{tot:,} loads > {rl:,}")
        if tot > lim:
            what = "reset" if is_rst else ("port-driven" if is_port else "net")
            bad.append(f"{what + ' ' if what != 'port-driven' else ''}{lab}: {tot:,} loads ({ff:,} flops, e.g. {ex}) > {lim:,}: "
                       + ("register it and replicate per region (rtl/lib/ot_rst_relay.sv: one relay copy per region)"
                          if is_rst else "replicate the driver register per consumer region (one copy per <= ~256 "
                                         "loads / ~100 um) or pipeline the broadcast"))
    if bad:
        F["high_fanout"] = bad[:12] + ([f"... {len(bad) - 12} more"] if len(bad) > 12 else [])

    # ---- 2b. reset landing (ROOT-RST 2026-10-19): the worst capture / setup path of qkd_hr_core_order (host_rst_n 386.9),
    # qkd_kvs_attn (rst_n 383.3), qkd_astk_rly_296 (277.4) and ot_s81_kp4_dec (rst_n 648 ps through 11 buffers, TT -70)
    # started at a reset INPUT that reached its flops / hard children through a buffer tree.  The standard: the port
    # lands in a register at the face (ref_tile "reset_landing": 2 registered stages, ot_pin_regs.tcl OT_RST_LAND), then
    # fans out at equal depth; reset release latency is a scheduled constant.
    decl = declared_resets(T)
    land, bad = [], []
    for b, (dd, x) in sorted(g.ports.items()):
        if dd != "input" or x in clk or x <= 3:
            continue
        base = re.sub(r"\[.*$", "", b)
        if base not in decl and not RST_LAND_RE.search(base):
            continue
        tot, ff, mac, ex = reset_sinks(g, A, x)
        land.append({"port": b, "sinks": tot, "flops": ff, "macros": mac})
        if tot > T['rst_land_max']:
            async_proof = async_two_stage_reset_proof(g, A, base, x)
            land[-1]['async_two_stage_proof'] = async_proof
            if async_proof['pass']:
                continue
        profile = T.get('_balanced_reset_profile')
        if profile and base in (profile.get('first_copies') or {}):
            proof=balanced_reset_proof(g,A,base,x,profile)
            land[-1]['balanced_proof']=proof
            if proof['pass']:
                continue
            bad.append(f"reset port {b}: balanced landing refused: {proof['reason']}")
        if tot > T["rst_land_max"]:
            bad.append(f"reset port {b}: {tot:,} sinks ({ff:,} flops, {mac} hard-child / macro pins, e.g. {ex}) reached "
                       f"without a landing register (> {T['rst_land_max']}): land it at the face in 2 registered stages "
                       f"(ref_tile \"reset_landing\": {{\"enable\": true}}, or RTL rst_l0 -> rst_l1 per region), then "
                       f"fan out at equal depth")
    M["reset_landing"] = land
    if bad:
        F["reset_landing"] = bad[:12]
        RF["reset_landing"] = list(bad[:12])

    # ---- levels / weights for 3 and 4
    ncell = len(g.cells)
    order = topo(g, A, clk)
    wt = [0.0] * ncell
    lv = [0] * ncell
    for ci in range(ncell):
        k = kind[ci]
        if k in ("comb", "buf"):
            wt[ci] = cell_w(g.cells[ci][0])
            lv[ci] = 0 if k == "buf" else 1

    # ---- 3. boundary: forward from input ports (levels), stop at sequential / macro
    data_in = {x for b, (dd, x) in g.ports.items() if dd == "input" and x not in clk}
    rst_in = {x for b, (dd, x) in g.ports.items() if dd == "input" and is_reset_net(b, b, T)}
    in_lv = {x: (0, A["driver"][x][1]) for x in data_in}       # net -> (levels from a data input port, port)
    q_ps = {}                                                   # net -> (ps from a flop / macro output, start)
    for ci in range(ncell):
        if kind[ci] in ("ff", "macro"):
            for x in _out_nets(g, A, ci):
                q_ps[x] = (0.0, g.cells[ci][1])
    q_lv = {x: 0 for x in q_ps}
    for ci in order:
        if kind[ci] not in ("comb", "buf"):
            continue
        best_in, best_q, best_ql = None, None, None
        for x in _in_nets(g, A, ci, False):
            v = in_lv.get(x)
            if v is not None and (best_in is None or v[0] > best_in[0]):
                best_in = v
            q = q_ps.get(x)
            if q is not None and (best_q is None or q[0] > best_q[0]):
                best_q = q
            ql = q_lv.get(x)
            if ql is not None and (best_ql is None or ql > best_ql):
                best_ql = ql
        for y in _out_nets(g, A, ci):
            if best_in is not None:
                in_lv[y] = (best_in[0] + lv[ci], best_in[1])
            if best_q is not None:
                q_ps[y] = (best_q[0] + wt[ci], best_q[1])
                q_lv[y] = best_ql + lv[ci]
    # endpoints
    in2out, in2reg, icg_en = [], [], []
    for b, (dd, x) in g.ports.items():
        if dd == "output" and x in in_lv and x not in rst_in:
            in2out.append((in_lv[x][0], in_lv[x][1], b))
    for ci in range(ncell):
        k = kind[ci]
        if k not in ("ff", "macro", "icg"):
            continue
        for pn, bs in g.cells[ci][2].items():
            if A["pin_dir"][ci].get(pn) != "in" or pn in SEQ_CLK_PINS or pn in ASYNC_PINS:
                continue
            for x in bs:
                v = in_lv.get(x)
                if v is None or x in rst_in or (v[1] and RST_RE.search(v[1])):
                    continue
                if k == "icg" and pn in ("ENA", "SE"):
                    icg_en.append((v[0], v[1], g.cells[ci][1]))
                else:
                    in2reg.append((v[0], v[1], f"{g.cells[ci][1]}/{pn}"))
    r2o = []
    for b, (dd, x) in g.ports.items():
        if dd == "output" and x in q_lv:
            r2o.append((q_lv[x], q_ps[x][1], b))
    in2out.sort(reverse=True)
    in2reg.sort(reverse=True)
    r2o.sort(reverse=True)
    M["in_to_out_bits"] = len(in2out)
    M["in_to_reg_levels"] = in2reg[0][0] if in2reg else 0
    M["reg_to_out_levels"] = r2o[0][0] if r2o else 0
    M["icg_enable_from_port"] = len(icg_en)
    if T["bnd_in_to_out_refuse"] and len(in2out) >= T["bnd_in_to_out_refuse"]:
        RF.setdefault("boundary", []).append(f"{len(in2out)} combinational input->output bit(s)")
    strict_pins = bool(T.get("bnd_strict_pin_regs"))
    if strict_pins and in2reg and in2reg[0][0] > T["bnd_in_levels_refuse"]:
        RF.setdefault("boundary", []).append(f"input->register {in2reg[0][0]} levels > {T['bnd_in_levels_refuse']} "
                                             f"({in2reg[0][1]} -> {in2reg[0][2]})")
    if strict_pins and r2o and r2o[0][0] > T["bnd_out_levels_refuse"]:
        RF.setdefault("boundary", []).append(f"register->output {r2o[0][0]} levels > {T['bnd_out_levels_refuse']} "
                                             f"({r2o[0][1]} -> {r2o[0][2]})")
    if T["bnd_icg_port_refuse"] and len(icg_en) >= T["bnd_icg_port_refuse"]:
        RF.setdefault("boundary", []).append(f"{len(icg_en)} ICG enable(s) combinational from ports")
    bad = []
    if in2out:
        bad.append(f"{len(in2out)} output bit(s) combinational from input ports (e.g. "
                   + ", ".join(f"{p}->{o} {l} lv" for l, p, o in in2out[:3]) + ")")
    deep_in = [e for e in in2reg if e[0] > T["bnd_levels"]]
    if deep_in:
        bad.append(f"{len(deep_in)} input->register endpoint(s) > {T['bnd_levels']} levels (worst "
                   + ", ".join(f"{p}->{r} {l} lv" for l, p, r in deep_in[:3]) + ")")
    deep_out = [e for e in r2o if e[0] > T["bnd_levels"]]
    if deep_out:
        bad.append(f"{len(deep_out)} register->output bit(s) > {T['bnd_levels']} levels (worst "
                   + ", ".join(f"{s}->{o} {l} lv" for l, s, o in deep_out[:3]) + ")")
    if icg_en:
        bad.append(f"{len(icg_en)} clock-gate enable(s) combinational from input ports (e.g. "
                   + ", ".join(f"{p}->{c} {l} lv" for l, p, c in icg_en[:3]) + "): register the enable first")
    if bad:
        F["boundary"] = [b + (": register the boundary (pin flops / registered outputs)" if strict_pins else
                              ": allowed as a same-region direct connection when the die / parent path meets timing "
                              "(owner 10-20); register it if the pin is a region crossing or its wire exceeds 405 um")
                         for b in bad]

    # ---- 4. logic depth reg -> reg
    worst = (0.0, None, None)
    for ci in range(ncell):
        k = kind[ci]
        if k not in ("ff", "macro", "icg"):
            continue
        for pn, bs in g.cells[ci][2].items():
            if A["pin_dir"][ci].get(pn) != "in" or pn in SEQ_CLK_PINS:
                continue
            for x in bs:
                q = q_ps.get(x)
                if q and q[0] > worst[0]:
                    worst = (q[0], q[1], f"{g.cells[ci][1]}/{pn}", q_lv.get(x))
    worst = (worst[0] * T["depth_scale"],) + tuple(worst[1:])
    M["depth_ps"] = round(worst[0], 1)
    M["depth_path"] = [worst[1], worst[2]] if worst[1] else None
    M["depth_levels"] = worst[3] if len(worst) > 3 else None
    if worst[0] > T["depth_ps_warn"]:
        F["logic_depth"] = [f"reg->reg stage {worst[1]} -> {worst[2]}: ~{worst[0]:.0f} ps estimated "
                            f"({worst[3]} logic levels) > {T['depth_ps_warn']:.0f} ps: pipeline / restructure the stage"]
    if worst[0] > T["depth_ps_max"]:
        RF["logic_depth"] = [f"~{worst[0]:.0f} ps > {T['depth_ps_max']:.0f} ps ({worst[1]} -> {worst[2]})"]

    # ---- 5. wire reach (fixed terminals: placed IO pins, macro pins)
    if dump:
        reach_findings(g, A, dump, clk, rst_in, order, T, F, M)
        if "wire_reach" in F:
            RF["wire_reach"] = F["wire_reach"][:2]

    # ---- 6. util / channels
    if dump:
        util_findings(dump, T, F, M)
    return res


def topo(g, A, clk):
    """combinational cells (comb / buf) in topological order (Kahn on cell -> cell edges); loops broken arbitrarily"""
    kind, loads = A["kind"], A["loads"]
    ncell = len(g.cells)
    comb = [ci for ci in range(ncell) if kind[ci] in ("comb", "buf")]
    indeg = [0] * ncell
    for ci in comb:
        for x in _in_nets(g, A, ci, False):
            d = A["driver"].get(x)
            if d and d[0] >= 0 and kind[d[0]] in ("comb", "buf"):
                indeg[ci] += 1
    ready = [ci for ci in comb if indeg[ci] == 0]
    out = []
    seen = bytearray(ncell)
    while ready:
        ci = ready.pop()
        if seen[ci]:
            continue
        seen[ci] = 1
        out.append(ci)
        for y in _out_nets(g, A, ci):
            for cj, _, _ in loads.get(y, ()):
                if kind[cj] in ("comb", "buf") and not seen[cj]:
                    indeg[cj] -= 1
                    if indeg[cj] <= 0:
                        ready.append(cj)
    if len(out) < len(comb):           # combinational loop: append the rest
        out += [ci for ci in comb if not seen[ci]]
    return out


def _pin_xy(boxes):
    if not boxes:
        return None
    _, r = boxes[0]
    return ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)


def reach_findings(g, A, dump, clk, rst_in, order, T, F, M):
    """forward / backward bounding boxes of fixed terminals in (u, v) = (x + y, x - y) through combinational logic"""
    R = T["reach_um"]
    kind = A["kind"]
    pos = {}
    for name, net, sig, io, boxes in dump.get("bterms", []):
        p = _pin_xy(boxes)
        if p:
            pos[name.replace("\\", "")] = p
    INF = float("inf")

    def box(p, lab):
        u, v = p[0] + p[1], p[0] - p[1]
        return [u, lab, u, lab, v, lab, v, lab]       # umin, umax, vmin, vmax with labels

    def merge(a, b):
        if a is None:
            return list(b)
        if b[0] < a[0]:
            a[0], a[1] = b[0], b[1]
        if b[2] > a[2]:
            a[2], a[3] = b[2], b[3]
        if b[4] < a[4]:
            a[4], a[5] = b[4], b[5]
        if b[6] > a[6]:
            a[6], a[7] = b[6], b[7]
        return a
    skip = set(clk) | set(rst_in) | {0, 1, 2, 3}
    # high-fanout nets are judged by high_fanout (relayed broadcast), not here
    hfn = {x for x, d in A["driver"].items() if len(A["loads"].get(x, ())) > T["hf_report"]}
    skip |= hfn
    src = {}         # net -> box of fixed sources reaching it combinationally
    snk = {}         # net -> box of fixed sinks it reaches combinationally
    mpos = A["macro_pos"]
    for b, (d, x) in g.ports.items():
        if x in skip:
            continue
        p = pos.get(b)
        if p is None:
            continue
        if d == "input":
            src[x] = merge(src.get(x), box(p, f"pin {b}"))
        else:
            snk[x] = merge(snk.get(x), box(p, f"pin {b}"))
    for ci, (t, nm, pins) in enumerate(g.cells):
        if kind[ci] != "macro":
            continue
        for pn, bs in pins.items():
            w = len(bs)
            for k, x in enumerate(bs):
                if x in skip:
                    continue
                pname = pn if w == 1 and (nm, pn) in mpos else f"{pn}[{w - 1 - k}]"
                p = mpos.get((nm, pname)) or mpos.get((nm, pn))
                if p is None:
                    continue
                if A["pin_dir"][ci].get(pn) == "out":
                    src[x] = merge(src.get(x), box(p, f"{nm}/{pname}"))
                else:
                    snk[x] = merge(snk.get(x), box(p, f"{nm}/{pname}"))
    if not src and not snk:
        M["reach"] = "no fixed terminals"
        return
    for ci in order:                         # forward
        acc = None
        for x in _in_nets(g, A, ci, False):
            if x in src and x not in skip:
                acc = merge(acc, src[x])
        if acc is not None:
            for y in _out_nets(g, A, ci):
                if y not in skip:
                    src[y] = merge(src.get(y), acc)
    for ci in reversed(order):               # backward
        acc = None
        for y in _out_nets(g, A, ci):
            if y in snk and y not in skip:
                acc = merge(acc, snk[y])
        if acc is not None:
            for x in _in_nets(g, A, ci, False):
                if x not in skip:
                    snk[x] = merge(snk.get(x), acc)

    def spread(b):
        return max(b[2] - b[0], b[6] - b[4])

    bad = []
    worst = 0.0
    for ci, (t, nm, pins) in enumerate(g.cells):
        if kind[ci] != "ff":
            continue
        acc = None
        for pn, bs in pins.items():
            if pn in SEQ_CLK_PINS or pn in ASYNC_PINS:
                continue
            for x in bs:
                if A["pin_dir"][ci].get(pn) == "in" and x in src:
                    acc = merge(acc, src[x])
                elif A["pin_dir"][ci].get(pn) == "out" and x in snk:
                    acc = merge(acc, snk[x])
        if acc is None:
            continue
        s = spread(acc) / 2.0
        worst = max(worst, s)
        if s > R:
            ends = (acc[1], acc[3]) if acc[2] - acc[0] >= acc[6] - acc[4] else (acc[5], acc[7])
            bad.append((s, f"register {nm}: its fixed terminals {ends[0]} and {ends[1]} put it >= {s:.0f} um from one "
                           f"of them (> {R:.0f} um per stage)"))
    # fixed -> fixed combinational paths
    for x, sb in snk.items():
        if x not in src:
            continue
        a = src[x]
        # max distance between any source and any sink within the boxes (conservative upper bound: box diameter)
        u = max(abs(sb[2] - a[0]), abs(a[2] - sb[0]))
        v = max(abs(sb[6] - a[4]), abs(a[6] - sb[4]))
        dist = max(u, v)
        if dist > R:
            bad.append((dist, f"combinational path {a[1] if abs(sb[2] - a[0]) >= abs(a[2] - sb[0]) else a[3]} -> "
                              f"{sb[3] if abs(sb[2] - a[0]) >= abs(a[2] - sb[0]) else sb[1]}: up to {dist:.0f} um "
                              f"with no register (> {R:.0f} um)"))
    bad.sort(key=lambda z: -z[0])
    M["reach_worst_um"] = round(max([worst] + [b[0] for b in bad]), 1)
    M["reach_violations"] = len(bad)
    if len(bad) >= T["reach_min_count"]:
        F["wire_reach"] = [f"{len(bad)} stage(s) beyond {R:.0f} um reach: insert relay flops"] + [b for _, b in bad[:6]]


def util_findings(dump, T, F, M):
    core = dump["core"]
    core_area = (core[2] - core[0]) * (core[3] - core[1])
    std = 0.0
    for name, m in dump.get("masters", {}).items():
        if m.get("block") or PHYS_RE.search(name) or str(m.get("type", "")).startswith(("ENDCAP", "CORE_WELLTAP",
                                                                                         "CORE_SPACER")):
            continue
        std += m["n"] * m["w"] * m["h"]
    mac = 0.0
    for m in dump.get("macros", []):
        b = m["bbox"]
        ox = max(0.0, min(b[2], core[2]) - max(b[0], core[0]))
        oy = max(0.0, min(b[3], core[3]) - max(b[1], core[1]))
        mac += ox * oy
    util = (std + mac) / core_area if core_area else 0.0
    M["util"] = round(util, 4)
    bad = []
    if mac > 0:
        # macro-dominated tile: gate the std-cell density over the placeable area, bound the total fill
        halo = float(dump.get("macro_halo_um", T["macro_halo_um"]))
        keep = 0.0
        for m in dump.get("macros", []):
            b = m["bbox"]
            ox = max(0.0, min(b[2] + halo, core[2]) - max(b[0] - halo, core[0]))
            oy = max(0.0, min(b[3] + halo, core[3]) - max(b[1] - halo, core[1]))
            keep += ox * oy
        placeable = max(core_area - min(keep, core_area), 1e-9)
        dens = std / placeable
        M["std_density"] = round(dens, 4)
        M["total_fill"] = round(util, 4)
        if dens > T["util_max"]:
            bad.append(f"std-cell density {dens:.1%} > {T['util_max']:.0%} (std {std:.0f} um2 in placeable {placeable:.0f} um2 = "
                       f"core {core_area:.0f} - macros/halos; total fill {util:.1%}): grow the outline")
        if util > T["fill_max"]:
            bad.append(f"total fill {util:.1%} > {T['fill_max']:.0%} (std {std:.0f} + macro {mac:.0f} um2 in {core_area:.0f} um2): "
                       "grow the outline")
    elif util > T["util_max"]:
        bad.append(f"utilisation {util:.1%} > {T['util_max']:.0%} (std {std:.0f} + macro {mac:.0f} um2 in "
                   f"{core_area:.0f} um2; target {T['util_min']:.0%}-{T['util_max']:.0%}): enlarge the outline")
    elif util < T["util_min"]:
        # OWNER 10-19/10-21: never squeeze a tile for area; a roomy outline is acceptable (informational, no finding)
        M["util_note"] = (f"utilisation {util:.1%} < {T['util_min']:.0%}: outline roomy; acceptable (do not shrink)")
    macros = dump.get("macros", [])
    if len(macros) > 1:
        try:
            sys.path.insert(0, __file__.rsplit("/", 1)[0])
            from fp_margin_lint import sliver_gaps
        except Exception:  # noqa: BLE001
            sliver_gaps = None
        if sliver_gaps:
            hard = [b["bbox"] for b in dump.get("blockages", []) if not b.get("soft") and float(b.get("max_density", 0)) == 0]
            gaps = sliver_gaps([(m["name"], m["bbox"]) for m in macros], T["channel_um"])
            open_ = []
            for a, b, r, w in gaps:
                ga = max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])
                cov = sum(max(0.0, min(r[2], h[2]) - max(r[0], h[0])) * max(0.0, min(r[3], h[3]) - max(r[1], h[1]))
                          for h in hard)
                if ga > 0 and cov < 0.9 * ga:
                    open_.append((w, a, b))
            M["narrow_channels"] = len(open_)
            M["narrow_channel_min_um"] = round(min(w for w, _, _ in open_), 2) if open_ else None
            if open_:
                open_.sort()
                bad.append(f"{len(open_)} macro channel(s) narrower than {T['channel_um']:.0f} um with placement rows "
                           f"(e.g. " + ", ".join(f"{a}|{b} {w:.1f} um" for w, a, b in open_[:3]) + "): widen to >= "
                           f"{T['channel_um']:.0f} um or block the channel")
    if bad:
        F["util_channel"] = bad


# --------------------------------------------------------------------------------------------- verdict / CLI
def verdict(res, mode="warn", waive=(), refuse_checks=REFUSE_CHECKS, clock=None):
    """WARN: any finding (textbook tier).  REFUSE: mode refuse and a refuse-tier finding of a check in refuse_checks.
    res["would_refuse"] lists the refuse-tier checks whatever the mode (the WARN-phase evidence for the switch)."""
    # measured clock rule (HARD_CHECKS): clock = {"enforce": bool, "evidence": {...}, "closed_stands": bool}.  Not in
    # `waive`, not mode-dependent: enforce refuses, otherwise the finding is a WARN (the gate judges it after its CTS).
    clock = clock or {}
    n = res.get("metrics", {}).get("clock_max_root_sinks")
    ok, text = clock_rule(n, clock.get("evidence"))
    if not ok and clock.get("waiver"):
        # the pre_route_gate's recorded per-pair waiver (HANDOFF 0ga), judged on the same evidence by the same rule
        applied, note, why = clock_waiver_eval(clock.get("evidence"), clock.get("waiver"))
        if applied:
            ok, text = True, f"{text}; WARN: WAIVED: {note}"
        else:
            text += f" (clock_rule_waiver NOT applied: {'; '.join(why)})"
    res["clock_rule"] = dict(max_root_sinks=n, root=res.get("metrics", {}).get("clock_max_root"), ok=ok, text=text,
                             enforce=bool(clock.get("enforce")), closed_stands=bool(clock.get("closed_stands")),
                             limits=dict(sinks=CLK_ROOT_SINKS_MAX, insertion_ps=CLK_INSERTION_MAX_PS,
                                         spread_ps=CLK_SPREAD_MAX_PS, pair_skew_ps=CLK_PAIR_SKEW_MAX_PS))
    hard = []
    if ok and "WARN:" in text and not clock.get("closed_stands"):
        res["findings"]["clock_guidance"] = [f"clock root {res['clock_rule']['root']}: {text}"]
    if not ok and not clock.get("closed_stands"):
        res["findings"]["clock_sinks"] = [f"clock root {res['clock_rule']['root']}: {text}: {CLOCK_RULE_FIX}"]
        if clock.get("enforce"):
            hard = ["clock_sinks"]
            res.setdefault("refuse", {})["clock_sinks"] = list(res["findings"]["clock_sinks"])
    waive = [w for w in waive if w not in HARD_CHECKS]
    F = {k: v for k, v in res["findings"].items() if k not in waive}
    RFt = {k: v for k, v in res.get("refuse", {}).items() if k not in waive and k in refuse_checks and k not in hard}
    for k, v in RFt.items():                     # a refuse-tier item is always reported
        F.setdefault(k, list(v))
        res["findings"].setdefault(k, list(v))
    res["would_refuse"] = sorted(RFt)
    refuse = (sorted(RFt) if mode == "refuse" else []) + hard
    res["waived"] = sorted(set(res["findings"]) & set(waive))
    res["verdict"] = "REFUSE" if refuse else ("WARN" if F else "PASS")
    res["refusing_checks"] = refuse
    res["summary"] = " | ".join(f"{k}: {v[0]}" for k, v in F.items())[:1500]
    return res


def run(netlist_path, dump_path, th=None, top=None, mode="warn", waive=(), refuse_checks=REFUSE_CHECKS, clock=None):
    T = dict(THRESHOLDS, **(th or {}))
    t0 = time.time()
    with open(netlist_path, errors="replace") as f:
        text = f.read()
    mods = parse_verilog(text)
    del text
    dump = None
    if dump_path:
        with open(dump_path) as f:
            dump = json.load(f)
    g, top = flatten(mods, top)
    del mods
    profile=T.get('_balanced_reset_profile')
    if profile and profile.get('top')!=top:
        raise ValueError('balanced reset profile top does not match actual netlist')
    res = analyse(g, dump, T)
    res["top"] = top
    res["netlist"] = netlist_path
    res["seconds"] = round(time.time() - t0, 1)
    res["thresholds"] = T
    return verdict(res, mode, waive, refuse_checks, clock)


def parse_set(items):
    out = {}
    for it in items or []:
        k, v = it.split("=", 1)
        try:
            out[k] = float(v) if "." in v else int(v)
        except ValueError:
            out[k] = v
    return out



# --------------------------------------------------------------------------------------------- RTL lint (ref-flow-1011)
# RTL-level pitfalls of 2026-10-11 that the netlist checks cannot see because synthesis never finishes / renames them:
#   runtime_partselect  a part-select whose base is a runtime signal (x[f(sig) +: W] / x[f(sig) -: W]) becomes a wide
#                       $shift/$shiftx cell; many of them stall yosys' SHARE (SAT) pass for hours (s81 su_tile 9eff3d007:
#                       16 x 512-b bb[512*(r-A0)+:512] writes, 3.5 h; hc ctile 5db4c7ec6 ~200 computed-offset slices, 4 h+;
#                       hgi_hc_unit 6 h+).  Fix: decoded constant-index slices (one-hot compare + AND-OR per destination).
#   hard_child_params   a hard child instantiated with #(...) overrides in the hard-build path: yosys "does not have a
#                       parameter named ..." (q-coll, hbm-no3).  Fix: no overrides under the hard define (defaults = the
#                       hardened configuration), parameterised path for simulation only.
#   onebit_vector_port  a [0:0] port is a scalar after synthesis: a pin plan naming x[0] fails PPL-0061 (ds-mtp P2, s81).
RTL_T = {"ps_warn_bits": 64, "ps_refuse_bits": 4096}   # bits x loop trips (su_tile 16,384 refused)
_DECL = re.compile(r"\b(input|output|inout|wire|reg|logic|bit|integer|int|var)\b")
_KW = {"input", "output", "inout", "wire", "reg", "logic", "bit", "signed", "unsigned", "integer", "int", "var", "tri",
       "parameter", "localparam", "genvar", "begin", "end", "if", "else", "for", "case", "default", "assign"}


def _strip_comments(s: str) -> str:
    s = re.sub(r"/\*.*?\*/", " ", s, flags=re.S)
    return re.sub(r"//[^\n]*", "", s)


def _eval_int(expr: str, params: dict):
    e = expr
    for _ in range(4):
        e2 = re.sub(r"\b([A-Za-z_]\w*)\b", lambda m: str(params[m.group(1)]) if m.group(1) in params else m.group(1), e)
        if e2 == e:
            break
        e = e2
    e = re.sub(r"(\d+)'[sS]?[dD](\d+)", r"\2", e)
    if re.search(r"[A-Za-z_$'?]", e):
        return None
    try:
        return int(eval(e.replace("/", "//"), {"__builtins__": {}}))  # noqa: S307 (arith only, identifiers rejected)
    except Exception:  # noqa: BLE001
        return None


def _loop_mult(body: str, pos: int, params: dict, ids=()) -> int:
    """product of the constant trip counts of the for-loops (in the same always / generate scope) enclosing pos whose
    variable the index uses, directly or through a variable assigned inside the loop (a loop-invariant index is one
    shifter that synthesis shares, not one per trip)"""
    start = max(body.rfind("always", 0, pos), body.rfind("assign", 0, pos), body.rfind("endgenerate", 0, pos), 0)
    mult = 1
    for h in re.finditer(r"\bfor\s*\(\s*(?:int(?:eger)?\s+|genvar\s+)?(\w+)\s*=\s*([^;]+);\s*\1\s*(<=?)\s*([^;]+);[^)]*\)",
                         body[start:pos]):
        seg = body[start + h.end():pos]
        depth, alive = 0, True
        for tok in re.finditer(r"\bbegin\b|\bend\b|;", seg):
            k = tok.group(0)
            if k == "begin":
                depth += 1
            elif k == "end":
                depth -= 1
                if depth <= 0:
                    alive = depth == 0 and False if depth < 0 else alive
                    if depth == 0:
                        alive = False
                        break
            elif depth == 0:
                alive = False
                break
        if not alive:
            continue
        if ids and h.group(1) not in ids and not any(re.search(r"\b" + re.escape(i) + r"\s*<?=(?!=)", seg) for i in ids):
            continue
        lo, hi = _eval_int(h.group(2), params), _eval_int(h.group(4), params)
        if lo is not None and hi is not None:
            mult *= max(1, hi - lo + (1 if h.group(3) == "<=" else 0))
    return min(mult, 1 << 16)


def rtl_modules(texts: list) -> dict:
    mods = {}
    for txt in texts:
        txt = _strip_comments(txt)
        for m in re.finditer(r"\bmodule\s+(\w+)(.*?)\bendmodule\b", txt, re.S):
            mods[m.group(1)] = m.group(2)
    return mods


def module_ports(body: str) -> dict:
    """{port: width or None} of a module body (ANSI header or non-ANSI declarations)"""
    body = re.sub(r"\(\*.*?\*\)", " ", body, flags=re.S)        # attributes (* keep = "true" *) name no ports
    hdr = body[:body.find(";")] if ";" in body else body
    params = module_params(body)
    out = {}
    for blob in (hdr, body):
        for m in re.finditer(r"\b(input|output|inout)\b([^;]*?)(?=;|\)\s*$|\binput\b|\boutput\b|\binout\b)", blob, re.S):
            seg = m.group(2)
            rng = re.search(r"\[([^\]:]+):([^\]]+)\]", seg)
            w = None
            if rng:
                a, b = _eval_int(rng.group(1), params), _eval_int(rng.group(2), params)
                w = abs(a - b) + 1 if a is not None and b is not None else None
            else:
                w = 1
            names = re.sub(r"\[[^\]]*\]", " ", seg)
            for n in re.findall(r"\b([A-Za-z_]\w*)\b", names):
                if n not in _KW and n not in out:
                    out[n] = (w, bool(rng))
        if out:
            break
    return out


def module_port_dirs(body: str) -> dict:
    """{port: 'input'|'output'|'inout'}"""
    body = re.sub(r"\(\*.*?\*\)", " ", body, flags=re.S)        # attributes (* keep = "true" *) name no ports
    hdr = body[:body.find(";")] if ";" in body else body
    out = {}
    for blob in (hdr, body):
        for m in re.finditer(r"\b(input|output|inout)\b([^;]*?)(?=;|\)\s*$|\binput\b|\boutput\b|\binout\b)", blob, re.S):
            names = re.sub(r"\[[^\]]*\]", " ", m.group(2))
            for n in re.findall(r"\b([A-Za-z_]\w*)\b", names):
                if n not in _KW and n not in out:
                    out[n] = m.group(1)
        if out:
            break
    return out


def module_params(body: str) -> dict:
    params = {}
    for m in re.finditer(r"\b(?:parameter|localparam)\b(?:\s+(?:integer|int|logic|bit)\b)?(?:\s*\[[^\]]*\])?\s*([^;]*)", body):
        for a in re.finditer(r"([A-Za-z_]\w*)\s*=\s*([^,;)]+)", m.group(1)):
            v = _eval_int(a.group(2), params)
            if v is not None:
                params[a.group(1)] = v
    return params


def rtl_lint(files: list, hard_cells=(), hard_define=None, T=None, top=None) -> dict:
    T = dict(RTL_T, **(T or {}))
    texts = []
    for f in files:
        try:
            with open(f, errors="replace") as fh:
                texts.append(fh.read())
        except OSError:
            continue
    mods = rtl_modules(texts)
    if top and top in mods:          # only the elaborated hierarchy under the top (other modules in the files never synthesise)
        keep, todo = set(), [top]
        while todo:
            mn = todo.pop()
            if mn in keep:
                continue
            keep.add(mn)
            for im in re.finditer(r"(?m)^\s*([A-Za-z_]\w*)\s*(?:#\s*\(.*?\)\s*)?[A-Za-z_][\w\[\]: ]*\(", mods[mn], re.S):
                if im.group(1) in mods and im.group(1) not in keep and im.group(1) not in hard_cells:
                    todo.append(im.group(1))
        mods = {k: v for k, v in mods.items() if k in keep}
    F, R = defaultdict(list), defaultdict(list)
    ps_sites = []
    for mn, body in mods.items():
        params = module_params(body)
        consts = set(params) | set(re.findall(r"\bgenvar\s+(\w+)", body))
        consts |= set(re.findall(r"\bfor\s*\(\s*(?:int(?:eger)?\s+|genvar\s+)?(\w+)\s*=", body))
        sigs = set()
        for dm in re.finditer(r"(?:^|;|\bbegin\b(?:\s*:\s*\w+)?|\(|,)\s*(?:input|output|inout|wire|reg|logic|bit|"
                              r"integer|int|var)\b([^;]*)", body):
            names = re.sub(r"\[[^\]]*\]", " ", dm.group(1).split("=")[0])
            sigs |= {n for n in re.findall(r"\b([A-Za-z_]\w*)\b", names) if n not in _KW}
        for n, _w in module_ports(body).items():
            sigs.add(n)
        rt = sigs - consts
        for m in re.finditer(r"(\w+|\])\s*\[([^\[\]]*?)([+-]):\s*([^\[\]]+?)\]", body):
            base, width = m.group(2), m.group(4)
            ids = set(re.findall(r"\b([A-Za-z_]\w*)\b", base))
            if not ids & rt:
                continue
            w = _eval_int(width, params)
            mult = _loop_mult(body, m.start(), params, ids)
            w = w * mult if w is not None else None
            after = body[m.end():m.end() + 4]
            write = bool(re.match(r"\s*<?=(?!=)", after))
            ps_sites.append((mn, m.group(0)[:80], w, write))
    wide = [s for s in ps_sites if (s[2] or 0) >= T["ps_warn_bits"]]
    tot = sum(s[2] or 0 for s in ps_sites)
    if wide:
        ex = ", ".join(f"{s[0]}: {s[1]} ({s[2]} b{' write' if s[3] else ''})" for s in wide[:3])
        msg = (f"{len(ps_sites)} runtime-indexed part-select(s), {tot:,} bits ({len(wide)} >= {T['ps_warn_bits']} b; e.g. "
               f"{ex}): each is a wide $shift/$shiftx; yosys SHARE pairs them (hours). Fix: decoded constant-index slices "
               f"(one-hot compare + AND-OR per destination), or a real memory")
        F["runtime_partselect"].append(msg)
        if tot >= T["ps_refuse_bits"]:
            R["runtime_partselect"].append(msg)
    for cell in hard_cells:
        for mn, body in mods.items():
            if mn == cell:
                continue
            for m in re.finditer(r"\b" + re.escape(cell) + r"\s*#\s*\(", body):
                pre = body[:m.start()]
                stack = []
                for d in re.finditer(r"`(ifdef|ifndef|else|endif)\b\s*(\w*)", pre):
                    k, nm = d.group(1), d.group(2)
                    if k in ("ifdef", "ifndef"):
                        stack.append([k, nm])
                    elif k == "else" and stack:
                        stack[-1][0] = "ifndef" if stack[-1][0] == "ifdef" else "ifdef"
                    elif k == "endif" and stack:
                        stack.pop()
                hard_path = True
                if hard_define:
                    hard_path = not any(nm == hard_define and k == "ifndef" for k, nm in stack)
                if hard_path:
                    msg = (f"{mn} instantiates hard child {cell} with #(...) overrides"
                           + (f" outside `ifndef {hard_define}" if hard_define else "")
                           + ": a hard view has no parameters (yosys 'does not have a parameter named'); under the hard "
                             "define instantiate it with NO overrides (defaults = hardened config)")
                    F["hard_child_params"].append(msg)
                    R["hard_child_params"].append(msg)
    return {"findings": dict(F), "refuse": dict(R), "modules": len(mods),
            "runtime_partselects": len(ps_sites), "runtime_partselect_bits": tot}


def rtl_main(a) -> int:
    hc = [x for x in (a.hard_cells or "").split(",") if x]
    res = rtl_lint(a.files, hc, a.hard_define, top=a.top)
    res["verdict"] = "REFUSE" if (res["refuse"] and a.mode == "refuse") else ("WARN" if res["findings"] else "PASS")
    res["would_refuse"] = sorted(res["refuse"])
    if a.out:
        with open(a.out, "w") as f:
            json.dump(res, f, indent=1)
    print(f"textbook_lint rtl: {res['verdict']} modules {res['modules']} runtime part-selects "
          f"{res['runtime_partselects']} ({res['runtime_partselect_bits']:,} b)")
    for k, v in res["findings"].items():
        tag = "REFUSE" if (k in res["refuse"] and a.mode == "refuse") else (
            "WARN(refuse-tier)" if k in res["refuse"] else "WARN")
        for line in v[:4]:
            print(f"textbook_lint rtl: {tag} {k}: {line}"[:700])
    return 3 if res["verdict"] == "REFUSE" else 0

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--netlist", required=True)
    c.add_argument("--dump")
    c.add_argument("--balanced-reset-profile", help="source-bound reset_landing.json; exact mapped two-edge/count/clock/load proof")
    c.add_argument("--top")
    c.add_argument("--out")
    c.add_argument("--mode", choices=("warn", "refuse"), default="warn")
    c.add_argument("--set", nargs="*", default=[])
    c.add_argument("--waive", nargs="*", default=[])
    c.add_argument("--refuse-checks", default=",".join(REFUSE_CHECKS))
    c.add_argument("--cfg", help="JSON {mode, set, waive, refuse_checks} (the loop's /ot_fplint/textbook_cfg.json)")
    r = sub.add_parser("rtl", help="RTL-level pitfalls: runtime part-selects (SHARE stalls), hard-child parameters")
    r.add_argument("files", nargs="+")
    r.add_argument("--hard-cells", default="", help="comma list of hard-child module names (cluster)")
    r.add_argument("--hard-define", help="the define selecting the hard-build path")
    r.add_argument("--top", help="lint only the hierarchy under this module")
    r.add_argument("--mode", choices=("warn", "refuse"), default="warn")
    r.add_argument("--out")
    a = ap.parse_args(argv)
    if a.cmd == "rtl":
        return rtl_main(a)
    mode, th, waive, rc = a.mode, parse_set(a.set), list(a.waive), tuple(x for x in a.refuse_checks.split(",") if x)
    clock = None
    if a.balanced_reset_profile:
        try:
            with open(a.balanced_reset_profile) as f:th['_balanced_reset_profile']=json.load(f)
        except (OSError,ValueError) as ex:
            print(f'textbook_lint: invalid balanced reset profile: {ex}');return 2
    if a.cfg:
        try:
            with open(a.cfg) as f:
                cfg = json.load(f)
            mode = cfg.get("mode", mode)
            th.update(cfg.get("set") or {})
            waive += list(cfg.get("waive") or [])
            rc = tuple(cfg.get("refuse_checks") or rc)
            clock = cfg.get("clock") if isinstance(cfg.get("clock"), dict) else None
        except (OSError, ValueError) as ex:
            print(f"textbook_lint: cfg {a.cfg} unreadable ({ex}); defaults")
    quiet = False
    if mode not in ("warn", "refuse"):
        if not (clock or {}).get("enforce"):
            print("textbook_lint: disabled by cfg")
            return 0
        mode, quiet = "warn", True      # lint off by spec: the measured clock rule (owner 2026-10-13) still applies
    try:
        res = run(a.netlist, a.dump, th, a.top, mode, waive, rc, clock)
    except Exception as ex:  # noqa: BLE001
        print(f"textbook_lint: tool error {type(ex).__name__}: {ex}")
        return 2
    if a.out:
        with open(a.out, "w") as f:
            json.dump(res, f, indent=1)
    M = res["metrics"]
    print(f"textbook_lint: {res['verdict']} {res['top']} cells {res['cells']:,} flops {res['flops']:,} "
          f"depth {M.get('depth_ps')} ps util {M.get('util')} reach {M.get('reach_worst_um')} um ({res['seconds']} s)")
    if "reset_landing" in M:
        print("textbook_lint: INFO reset_landing " + json.dumps({"max": res["thresholds"]["rst_land_max"],
                                                                "ports": M["reset_landing"][:64]}, separators=(",", ":")))
    cr = res["clock_rule"]
    print(f"textbook_lint: INFO clock_roots max_root_sinks={cr['max_root_sinks']} root={cr['root']} "
          f"rule={'PASS' if cr['ok'] else ('CLOSED_STANDS' if cr['closed_stands'] else 'FAIL')}: {cr['text']}"[:600])
    for k, v in res["findings"].items():
        if quiet and k not in HARD_CHECKS:
            continue
        tag = "REFUSE" if k in res["refusing_checks"] else ("WAIVED" if k in res["waived"] else
                                                            ("WARN(refuse-tier)" if k in res["would_refuse"] else "WARN"))
        for line in v[:4]:
            print(f"textbook_lint: {tag} {k}: {line}"[:600])
    if res["verdict"] == "REFUSE":
        print("TEXTBOOK_LINT: " + " | ".join(f"{k}: {'; '.join(res['refuse'][k][:2])}" for k in res["refusing_checks"])[:1200])
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
