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
  RECT-OUTLINE     clock-band rects, tap windows, tap_reserved_um and landing-contract rects outside the type outline
                   (S81 R9 svc_ytrade_row.py moved only points; svc_lo t7 attn_i0 band + tap windows left outside)
  BITSITE-AREA     ft / internal-station / landing CS bank bit sites off CORE_AREA or the outline, and colliding footprints
                   (S81 c8: 47 types, 42 leaf + 5 svc)
  PG-EDGE-PIN      hard-core edge pins on a parent PG stripe column (M5/M7) or row (M6) of a core without pg_halo_um
                   (QC st_a DRC 72, all M5; fix hard_cores[].pg_halo_um)
  LANE-STATIONS    lanes whose planned kit stations (both end buses, kit_depth) exceed fixed_cycles + pad, so the strict bind
                   would deliver late (LANE_ASBUILT UNPRICED_KIT_STATIONS; QC V4 l1a sl_W4_fw arm/arv 12 vs 8)
  BUS-CHANNEL-FIT  per E/W face side: per-bit bus stations need disjoint vertical bands max(4, 0.1*bits) um (y-overlapping buses) inside
                   the pin..leaf strip; WARN when the packer rule cannot place them, with the strip width needed (QC sle_fe_v2 E
                   side: 311 um has, ~388-429 needed; adv_bus_channel.py)
  DRT-M2M3         INVENTORY, uncalibrated, no threshold: plan cells / free area and route-demand hot gcells at or above the M2/M3
                   load of the known DRT-heavy QC types (41 kits 10-29 h DRT; adv_drt_m2m3.py)
  ROUTE-DEMAND     static RUDY of planned station / ft legs vs M2-M8 track supply above hard-core obstructions: gcells at est.
                   routing util >= 0.8 and the core channel there (S81 leaf: vn->lane bank fan-in through 4-17 um channels,
                   t44 50k GRT overflow at 2.6 % fill); calibrated as a where-to-look map, not a ranking (adv_route_demand.py)

  LEG-DELAY        station-free bus->core / core->core legs: estimated setup slack from Manhattan length x 1.2 ps/um (C4 kv3_pc phy->kvpc -773 ps, C6 kv3_hgi -870 ps; HOP-GAP / G0-HOPS were silent)
  FP-FLOORPLAN     street lane demand > 1.0, plan cells > 400k, hard-core overlap / outside the outline (FP-CONVERGE-KV 11-25; OT_FP_BLOCK=1 -> FAIL lines)
  GEN-PARSE        gen-step parse of every type in scope: reg_leaf_split.config and the bound R8 count declarations (bound_r8_straps.project)
                   with the TREE tools, no synthesis (KV R6: kv3_hg_v1p4/v1p6 ">= 2 copies needed", kv3_pc_v1 r8ef700d7c strap_r8pad_lane_*, all
                   found only at gen); report only, OT_GEN_PARSE_BLOCK=1 -> FAIL lines (adv_gen_parse.py)
  BOUNDARY-REG-50  ft out pins with no planned register within 50 um (precheck BOUNDARY-REG reading, exact bit sites); boundary_reg.py plan seats an out-face station (COORD 19:25 FABLE-RC-KV item 3; OT_BREG_BLOCK=1 -> FAIL lines)
  RSTSPREAD        reset nets (FIRM seats on their nearest consumer tap) over 3,000 loads, 405 um of seat-to-tap, or 900 um HPWL; report only,
                   adv_rst_spread.py, fix = rst_reach_construct.py spread (one relay stage per sink region, opt-in) (C-RST-RELAY-REACH r3)
  EDGE-STRIP       >= 256-bit die windows with a hard core < 69.12 um behind the window span (VIS-DIE-S81 EDGESTRIP-1; S81 J8:
                   241 types, 0/47 signed, 40/51 failing); fix = edgestrip_row.py interior shift or re-shape (adv_edge_strip.py)

  HOP-GAP          internal one-cycle reg-to-reg / reg-to-core-pin hop > 405 um with no station (FABLE-RC-S81: gunit -2168 ps)
  TAPOFF-SITE      tap_offset / tap_window rows whose tap moved > 9 um vs a baseline plan (rows are keyed by tap NAME; QC st_a r9 had 5-22 of 225-408 on their own tap); needs --baseline
  ROW-APPLIED      rows accepted by reference whose ops (value at path, by CONTENT) are not in this plan: FULL / PARTIAL / NONE per ops file (OT_ADV_ROWS)
  UNSEATED-CHAIN   multi-stage ot_dp_dly delay pipes in the BOUND RTL (no plan seat) whose bits x stages need more area than their pin window x 17 um (QC cbf_q11 n_y: 514 bits x 10 stages, 89 um window); needs bind_out
  SEATLINE         station seats whose cells (bits x 2) cannot fit the seat window (sqrt(cells x 0.25 / 0.6)) or whose 100 um bin is 2x the median / 30% seat area (QC sle_ctl hc1_o 1,574 bits at one point)
  COLSYNC          plan landing_contract collector nodes vs the landed sidecar's (strict reads the sidecar, landing_place / kit gen the plan): differ / not in tree / > 405 um from the row (QC su_c)
  RST-SIDECAR      sidecar collector source/child tap index measured against the PLAN collector tree: raw reset copy > 300 um from its RTL raw parent, collector > 405 um from its status pins, node not in tree (QC-SLECTL-RRL)
  PG-HALO-APPLIED  pg_halo_um that never reaches the PDN: type core_pg_connect false, halo < 0.3 or > 8.64 um, bad value, same-inst clash, or dropped on a core whose module has it elsewhere (QC st_a DRC 72)
  GCELL-SLIVER     clock tap site rect edges that leave a GRT gcell strip under 0.20 um (obs_gcell_cap class; hd_host_w GRT 139)
  MACRO-CHANNEL    facing hard cores of a type with a channel under 14.88 um (HEAD colfix 8.16 um needed 14.88 before GRT could route)
  INSERTION-BAND   per-region clock insertion: leg > 405 um, arrival not balanceable under tap_slowest_max_ps, or spread > 40 ps (QC st_a/stm C2; report only, fires on no v13 type)
  CHANNEL-PILE     through-wires / (channel width x supply) > 0.6 per strip, central channel tap grid (sinks/900 taps, gap <= 400 um) (QC cbn_q00/q11 C5)
  ISTA-LEAF        a non-core internal_stations chain whose leaf_um (kit route start) sits > 403 um from its real launch / capture register (QC sle_fw_v1 / slw_fw_v1 sc_eo/sc_wo leaf at the SE corner, 1390 um first hop, TT -150..-195)
  C2-REACH         rstart / flt_o / btab-read single-cycle hops > 800 um (or > CBC 405 um, cbc tier) or btab macros without a planned g_read site (QC C2 GRT kits, TT -153..-178)
  TREE-LINKS       launch tree dir/file symlinks resolving outside the tree (QC C1o v13 rtl/ and bind/ into an older private tree, 2.5 h lost) and tool/RTL files differing from the declared rt / main sha
  PHY-FACE-ROWS    hard-macro type whose free cell rows on a bus (port) face are < the port-buffer need, rows only on the far side (QC phy_serdes: 7 rows in the S strip, ports on N, ~20k wire buffers, DPL-0033)
  SITE-IN-MACRO    any plan site (regs_um, bit_sites_um, face_bit_sites_um, relay_sites, soft banks, CLAND seats) inside a hard core
                   + its halo_um, or off the outline, per type and key (KV A5t3-A5t6: 22 i_ectl_Q_N_kf bit sites on u_kvpc1_f in 8
                   kv3_pc_v1 types, all 19 pc_v1 failed place; a CORE-PLACE row moved the core, not its dependent sites)
  STATION-STACK    station points (internal_stations / ft_slots regs_um) shared by >= 2 buses: points, bits per point, reset tap / START within 10 um (KV kv3_pv_v1n V1NSITE)
  SINKBIN-STALE    density sink bins written for an older form: split/other type, > 5 % of bin sinks in hard cores/children or off the outline, kit tap > 1,000 sinks
  BANK-SPAN        SRAM bank groups (<parent>.g_bank[k].u_m) whose centre-to-centre span exceeds the 405 um reach (FAIL-SPAN) or 250 um
                   (WIDE): one write-data slice feeds every bank, so a far bank is an unregistered leg over reach (HEAD W4b
                   hd_lep0N_w u_rg2 g_bank[3]: 480 um leg, TT -151 ps; W6 rg1 437, East rg0/rg3 583) (adv_bank_span.py)
  TAP-STEP         per-port tap_offset tables with neighbouring kit taps > 42 ps apart, hard cores whose surrounding taps spread
                   > 42 ps, taps without a row; types with taps and no table listed as UNPRICED (HEAD W6 hd_lep0N 16 pairs, max
                   125.4 ps on the 11-20 r13 die clock) (adv_tap_step.py)
  CTLM-AGES        compiled tt_ctlm program lane ages (ctlm_metadata_source relay.R_*) and core XPF_TRANSPORT_EDGES vs the bound lane cycles and xpf = 1 + R_HR (QC C1g 19/19 vs 14/10, XPF 21 vs 20)
  BITSITE-SEAT     exact bit sites (ft bit_sites_um, in-core rows) farther than 40 um from their station / wrong stage count (KV A5t2 RREACH 659 um; --baseline: only stages seated before)
  LAT-DEFINE       latency-changing verilog_defines (RIP, SRAMREG, CFX, kv_seam) on a type that the die-wide as-built profile does not list, MIXED within a family
  STALE-EXPORT-TAP forwarded-clock export pins whose source_clock_port tap is > 300 um from the pin (re-grown / renumbered taps; class C-FWDCLK-WRONG-TAP; stale / dangling / no-nearer, per type + die counts; needs the plan tree for sink_bins)
  G0-HOPS          G0's check_hops alone (~30 s): every lane's mandatory-slot-pin / ft-station hop vs its reach (S81 c8: 98 lanes found only at G0)
  STALE-KEEPOUT    clock.keepouts_um that are old copies of landing bands (KV pv_v2ne/v5ne), and sink_bins_file counts >10% off the latest placed DB
  RAW-RESET-TO-PORT a writer START stage raw reset that drives an output port in the type's bound RTL (QC C1b sle_su_c rr_t85, EMIT refusal after 3628 s)
  STN-DEADLANE     internal-station rows on lanes the bind leaves with 0 bits (native_istations 'expected one outgoing lane', KV A5t8 x54);
                   needs the elab netlist (OT_STN_DEADLANE_ELAB/_ASBUILT) or a stn_deadlane.py report (OT_STN_DEADLANE_REPORT), else not checked
  IST-PRICE        a lane's stored latency row (cycles / ft stations / landing) short of the live ft + landing + source stations (KV A3c
                   'native stations exceed priced lane depth', A2g L415): every lane, not only native-source ones
  STN-CONFLICT     >= 2 station rows of differing geometry on one native bus, or a valid bit stationed apart (S81 iqf idx_o0)
  LAND-CAP         a clock-landing band filled >= 90 % or crossed by a foreign halo (S81 c1x_C t9, QC st_a x_st_b_i)
  LAND-REACH       a hard landing core parked farther from its port than the cland data allowance (QC sle_ctl 300 um / 192 ps vs 45 ps)
  TIED-BITS        UNBOUND-tied bits: observed in the bind of record + predicted unlisted parameterized blackbox leaves (S81 svc c8)
  DEFINE-NOOP      plan-set OT_* verilog define no tree rtl file tests (NOOP) or tests only in an older copy (LAG); QC C9 pre-366319e2e3b xhead3 (P-TREE-RTL-STALE, adv_define_noop.py)
  TREE-DRIFT       a view LEF / porous map / flow script / tool fix on main the bound tree lacks (u_cf view 31c7ccbd1b on J7/J8)
  CONE-DEPTH       (C-CONE-DEPTH) a register/port logic cone in the elab json deeper than period - 130 ps at 22 ps per level (adv_cone_depth.py;
                   needs the bind's asbuilt.json next to the as-built or $OT_CONE_YOSYS_JSON; silent without it)
  OFF-GRID         exact station / bank sites off the placement grid (KV sys_c row C)
  RESET-NAME       a generated reset relay (rst_rl_<k>) / density tap (clk_t<i>) name the clock section references that the
                   type's reset tree / tap table no longer emits (tap rows renumbered the tree: S81 J8, HEAD Row B, KV D29 14
                   EMIT); fix = landing_remap --resets anchor from the TREE's tools (adv_reset_names.py, TAP-GRID-R5)

  FIRM-FIXED-SEAT  (C-FIXEDSITE-FIRM-OVERLAP, R3-FIRMSEAT 11-27, report only) a FIRM cell (reset-tree relay rrl:*, landing reader / writer START,
                   status, local reset, collector, raw export, relay_sites) whose 2.16 x 0.27 um footprint overlaps a fixed seat
                   (place_regions kind fixed reserve_rect_um) that place_fixed_sites.tcl seeds AFTER those cells are FIRM: QC TT r3c 11 of the 12
                   placed pairs, all 10 seats (adv_firm_fixed_seat.py; core / station overlaps are context counts only)

  PUB-STALE        (P-RESET-PUB-STALE, C-RST-RELAY-REACH 11-26) the published clock.landing_contract.collector_tree vs the tree the bind re-solves
                   (reset_tree.for_type): relay-set / tap-count / depth mismatch and any collector ref > 405 um on the solved tree (S81 v3: 126 types,
                   col_h10_r2 rst_n_t30 950 um); budgeted solve, never reports unchecked types as clean (adv_pub_stale.py)
  FENCE-GEOM       (C-FENCE-GEOM-ILLEGAL 11-27) zero-area / sub-row / sub-site / singleton / off-grid fence + region shapes in plan logic_cluster_rects_um,
                   rck_island and the kit tree logic_cluster.tcl / region_guide.tsv (adv_fence_geom.py; report-only)
  PARAM-NOT-IN-RTL (P-PLAN-AHEAD-OF-RTL 11-27) a partition_types[T].leaf_params parameter the bound leaf RTL / as-built netlist / param_regen.declare does not
                   declare (S81 WREG row d44304a8a2c5: 6 types PARAM_REGEN in a 35 min whole bind); adv_param_not_in_rtl.py
  PHASE-BIND       (DIECLOCK-PHASE-BIND-CHECK, C-DIECLOCK-PHASE-BIND 11-26) plan reset_entry_phase / strap_rst_ph / START edge_fall
                   vs the choices phase_bind.py derived from a die STA on the ROUTED die clock (<plan dir>/phase_bind.json or
                   $OT_PHASE_BIND); NO-BIND when a phase-using plan has none (HEAD W10: 33/358 entry phases below 60 ps)

    python3 -I tools/die_plan/plan_advisory.py --plan PLAN.json [--tree TREE] [--checks A,B] [--json OUT]   (exit 0 always, 2 = bad input)
"""
import argparse
import importlib
import json
import os
import signal
import sys
import threading
import types
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
# (check name, module in this directory); a module absent from an older tree is skipped quietly
CHECKS = (("CORE-PARAM", "adv_core_param"), ("GHOST-MACRO", "adv_ghost_macro"), ("SITE-COLLIDE", "adv_site_collide"),
          ("PORT-WINDOW-PAIR", "adv_port_window_pair"), ("DEPTH-VS-RTL", "adv_depth_vs_rtl"), ("CONE-DEPTH", "adv_cone_depth"), ("DENSITY", "adv_density"),
          ("CELLCAP", "adv_cellcap"), ("CELL-BUDGET", "adv_cell_budget"), ("HOLDCELL-BUDGET", "adv_holdcell_budget"),
          ("TAP-BUDGET", "adv_tap_budget"), ("TAP-LOAD", "adv_tap_load"), ("XTAP-PAIR", "adv_xtap_pair"), ("TAP-REACH", "tap_reach_fix"), ("STALE-BINS", "adv_stale_bins"),
          ("PORT-PIN", "adv_port_pin"), ("MERGE-RESET-DEPTH", "adv_merge_reset_depth"), ("PATH-SEAT", "adv_path_seat"),
          ("PHANTOM-STATION", "adv_phantom_station"), ("BANK-OFFAREA", "adv_bank_offarea"),
          ("STATION-DENSITY", "adv_station_density"), ("SITE-ON-ROW", "adv_site_on_row"), ("PLACE-REGION", "adv_place_region"),
          ("BAND-BLOCKAGE", "adv_band_blockage"), ("BAND-GAP", "adv_band_gap"), ("LANE-STATIONS", "adv_lane_stations"),
          ("ROUTE-DEMAND", "adv_route_demand"), ("EDGE-STRIP", "adv_edge_strip"), ("RESET-NAME", "adv_reset_names"),
          ("REF-SITE", "adv_ref_site"), ("HOP-GAP", "adv_hop_gap"), ("OFF-GRID", "adv_off_grid"), ("TREE-DRIFT", "adv_tree_drift"), ("DEFINE-NOOP", "adv_define_noop"), ("LAND-CAP", "adv_land_cap"), ("LAND-REACH", "adv_land_reach"), ("STN-CONFLICT", "adv_stn_conflict"), ("IST-PRICE", "adv_ist_price"), ("STN-DEADLANE", "adv_stn_deadlane"), ("RAW-RESET-TO-PORT", "adv_raw_reset_port"), ("STALE-KEEPOUT", "adv_stale_keepout"), ("G0-HOPS", "adv_g0_hops"), ("TAPOFF-SITE", "adv_tapoff_site"), ("LAT-DEFINE", "adv_latdefine"), ("BITSITE-SEAT", "adv_bitsite_seat"), ("CTLM-AGES", "adv_ctlm_ages"), ("COLSYNC", "adv_colsync"), ("SEATLINE", "adv_seatline"), ("UNSEATED-CHAIN", "adv_unseated_chain"), ("ROW-APPLIED", "adv_row_applied"), ("PAD-LAUNCH", "adv_pad_launch"), ("UNSET-DEFINE", "adv_unset_define"), ("TREE-SWITCH", "adv_tree_switch"), ("TIED-BITS", "adv_tied_bits"), ("RECT-OUTLINE", "adv_rect_outline"), ("BITSITE-AREA", "adv_bitsite_area"), ("PG-EDGE-PIN", "adv_pg_edge_pin"), ("PIN-TRACK-PG", "pin_track_pg"), ("RST-SIDECAR", "adv_rst_sidecar"), ("STATION-STACK", "adv_station_stack"), ("SINKBIN-STALE", "adv_sinkbin_stale"), ("BANK-SPAN", "adv_bank_span"), ("TAP-STEP", "adv_tap_step"), ("SITE-IN-MACRO", "adv_site_in_macro"), ("CLK-LAND-OBS", "adv_clk_land_obs"), ("PHY-FACE-ROWS", "adv_phy_face_rows"), ("TREE-LINKS", "adv_tree_links"), ("ISTA-LEAF", "adv_ista_leaf"), ("C2-REACH", "adv_c2_reach"), ("INSERTION-BAND", "adv_insertion_band"), ("CHANNEL-PILE", "adv_channel_pile"), ("PG-HALO-APPLIED", "adv_pg_halo_applied"), ("MACRO-CHANNEL", "adv_macro_channel"), ("GCELL-SLIVER", "adv_gcell_sliver"), ("FP-FLOORPLAN", "adv_fp_floorplan"), ("LEG-DELAY", "adv_leg_delay"), ("SLOT-GAP", "adv_slot_gap"), ("CHANNEL-WIDTH", "adv_channel_width"), ("FT-OUTSIDE", "adv_ft_outside"), ("BUS-CHANNEL-FIT", "adv_bus_channel"), ("DRT-M2M3", "adv_drt_m2m3"), ("BOUNDARY-REG-50", "boundary_reg"), ("IN-OUTLINE", "adv_fpconv:IN-OUTLINE"), ("LEG405-ZERO", "adv_fpconv:LEG405-ZERO"), ("LEG405-STAGED", "adv_fpconv:LEG405-STAGED"), ("RELAY-SEAT", "adv_fpconv:RELAY-SEAT"), ("SEAT-DENSITY", "adv_fpconv:SEAT-DENSITY"), ("PIN-FACE-CLEAR", "adv_fpconv:PIN-FACE-CLEAR"), ("HUB-BOX", "adv_fpconv:HUB-BOX"), ("FT-CLEAR", "adv_fpconv:FT-CLEAR"), ("TAP-STEP-DUP", "adv_fpconv:TAP-STEP-DUP"), ("BAND-AT-PIN", "adv_fpconv:BAND-AT-PIN"), ("SEAT-UNIQUE", "adv_fpconv:SEAT-UNIQUE"), ("RANK-PILE-PINFACE", "adv_fpconv2:RANK-PILE-PINFACE"), ("FT-SITE-LEGAL", "adv_fpconv2:FT-SITE-LEGAL"), ("STALE-EXPORT-TAP", "adv_stale_export_tap"), ("SINKBIN-AGE", "adv_sinkbin_age"),
          ("STATUS-UP-REACH", "adv_rcs81:STATUS-UP-REACH"), ("CORE-LEG-OVERMACRO", "adv_rcs81:CORE-LEG-OVERMACRO"), ("RELAY-COHORT-SPAN", "adv_rcs81:RELAY-COHORT-SPAN"),
          ("TAP-SPAN-EST", "adv_placed_est:TAP-SPAN-EST"), ("ASPECT-EST", "adv_placed_est:ASPECT-EST"), ("LEG405-EST", "adv_placed_est:LEG405-EST"),
          ("SEAT-ORIENT", "adv_seatgap:SEAT-ORIENT"), ("MACRO-GAP", "adv_seatgap:MACRO-GAP"),
          ("BITS-OVER-CYCLE", "adv_bitscycle:BITS-OVER-CYCLE"), ("PIN-FACE-KVLEAF", "adv_bitscycle:PIN-FACE-KVLEAF"),
          ("PLACED-HOP-RATIO", "adv_placed_hop_ratio"), ("GEN-PARSE", "adv_gen_parse"),
          ("XTAP-SEAM", "kit_xtap_seam"), ("RSTSPREAD", "adv_rst_spread"), ("RESERVED-POCKET", "reserved_pocket"), ("PHASE-BIND", "adv_phase_bind"), ("PUB-STALE", "adv_pub_stale"), ("FENCE-GEOM", "adv_fence_geom"), ("PARAM-NOT-IN-RTL", "adv_param_not_in_rtl"),
          ("LEG405-POLY", "adv_leg405_chain:LEG405-POLY"), ("LEG405-RRL", "adv_leg405_chain:LEG405-RRL"), ("LEG405-TAIL", "adv_leg405_chain:LEG405-TAIL"),
          ("FIRM-FIXED-SEAT", "adv_firm_fixed_seat"))
CHECK_TIMEOUT_S = int(os.environ.get("OT_PLAN_ADVISORY_TIMEOUT_S", "120"))
MAX_LINES = 25          # per check, plus its own summary line


class _Timeout(Exception):
    pass


def _alarm(_sig, _frm):
    raise _Timeout()


FAIL_KEEP = ("FAIL ADV-RESET-NAME ", "FAIL ADV-TREE-DRIFT rtl ")   # TREE-DRIFT: OT_TREE_RTL_BLOCK=1 (P-TREE-RTL-STALE)


def _norm(name, lines):
    out = []
    for x in lines or []:
        x = str(x)
        if not x.strip() or x.startswith("#"):          # module debug / coverage lines
            continue
        if x.startswith(FAIL_KEEP):                     # P-FALSE-GREEN: a crashed estimator is an ERROR, kept as a FAIL line
            out.append(x)
            continue
        if not x.startswith("WARN "):
            x = f"WARN ADV-{name} {x}"
        out.append(x)
    if len(out) > MAX_LINES + 1:
        out = out[:MAX_LINES] + [f"WARN ADV-{name} ... {len(out) - MAX_LINES} more line(s) (plan_advisory.py --checks {name} for all)"]
    return out


PARENT_CHECKS = ("REF-SITE",)   # REF-SITE-SPEED-1125: they fork their own per-type pool, which a daemonic pool worker cannot


def _run_one(name, mod, raw, plan_path, tree, kw, cap, alarm=True):
    """-> (name, lines, seconds) of one check (never raises); the per-check alarm needs the main thread of the process"""
    t0 = time.time()
    try:
        if ":" in mod:            # "module:KEY": a module that serves several checks (adv_fpconv.findings_by_check[KEY])
            mn, key = mod.split(":", 1)
            m = types.SimpleNamespace(findings=importlib.import_module(mn).findings_by_check[key])
        else:
            m = importlib.import_module(mod)
    except (ImportError, KeyError, AttributeError):
        return name, None, 0.0
    main_thread = threading.current_thread() is threading.main_thread()
    old = None
    try:
        if alarm and main_thread and CHECK_TIMEOUT_S > 0:
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
    return name, (_norm(name, lines) if cap else [str(x) for x in lines or []]), round(time.time() - t0, 2)


_JOB = {}


def _job(i):
    name, mod = _JOB["todo"][i]
    return _run_one(name, mod, *_JOB["args"])


def default_jobs():
    try:
        return max(1, int(os.environ.get("OT_PLAN_ADVISORY_JOBS", "8")))
    except ValueError:
        return 1


def run(raw, plan_path, tree=None, checks=None, skip=(), timing=None, cap=True, jobs=None, **kw):
    """WARN ADV-* lines of every check (never raises), in CHECKS order.  jobs > 1 (default 8, OT_PLAN_ADVISORY_JOBS) runs the
    independent checks in a fork pool (a PRE took > 1 h serially: ~60 whole-plan checks); a pool that cannot start runs serial."""
    if os.environ.get("OT_PLAN_ADVISORY", "").lower() == "off":
        return []
    skip = {s.upper() for s in skip or ()}
    want = {c.upper() for c in checks} if checks else None
    todo = [(n, m) for n, m in CHECKS if n not in skip and (want is None or n in want)]
    jobs = default_jobs() if jobs is None else jobs
    out = []
    sys.path.insert(0, str(HERE))
    try:
        res = None
        if jobs > 1 and len(todo) > 1:
            try:
                import multiprocessing
                par = [(n, m) for n, m in todo if n in PARENT_CHECKS]
                rest = [(n, m) for n, m in todo if n not in PARENT_CHECKS]
                _JOB["todo"], _JOB["args"] = rest, (raw, plan_path, tree, kw, cap)
                with multiprocessing.get_context("fork").Pool(max(1, min(jobs, len(rest)))) as pool:
                    it = pool.imap(_job, range(len(rest)), chunksize=1)
                    mine = {n: _run_one(n, m, raw, plan_path, tree, kw, cap, alarm=False) for n, m in par}
                    got = {r[0]: r for r in it}
                got.update(mine)
                res = [got[n] for n, _m in todo]
            except Exception:  # noqa: BLE001 e.g. a daemonic parent cannot fork a pool
                res = None
        if res is None:
            res = [_run_one(n, m, raw, plan_path, tree, kw, cap) for n, m in todo]
        for name, lines, secs in res:
            if lines is None:
                continue
            out += lines
            if timing is not None:
                timing[name] = secs
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
    ap.add_argument("--jobs", type=int, default=None, help="worker processes over checks (default 8, OT_PLAN_ADVISORY_JOBS; 1 = serial)")
    ap.add_argument("--all", action="store_true", help="no per-check line cap")
    a = ap.parse_args(argv)
    try:
        raw = json.loads(Path(a.plan).read_text())
    except (OSError, ValueError) as e:
        print(f"plan_advisory: cannot read {a.plan}: {e}", file=sys.stderr)
        return 2
    tm = {}
    lines = run(raw, a.plan, a.tree, [c for c in a.checks.split(",") if c] or None, timing=tm, cap=not a.all, jobs=a.jobs,
                asbuilt=a.asbuilt, bind_out=a.bind_out, baseline=a.baseline)
    for x in lines:
        print(x)
    print(f"PLAN-ADVISORY plan={a.plan} lines={len(lines)} ({summary(lines) or 'no findings'}) seconds={tm}")
    if a.json:
        Path(a.json).write_text(json.dumps({"plan": a.plan, "tree": a.tree, "advisories": lines, "seconds": tm}, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
