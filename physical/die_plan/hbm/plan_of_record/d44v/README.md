# HBM plan event d44v = the HBM RE-FORM batch plan event, parts 1-9 (DIE-HBM-61/PLAN + /SPLIT, DIE-HBM-62/BIG, 2026-11-03)

OWNER 11-03: TWO-STRIKES -> RE-FORM, ONE batch per die. Rules are design targets: plan GEOM, fill, aspect and channels
are ADVISORY. Only sign-off blocks.
DIE-HBM-61 ruling 06:5x: the >150k-cell cores go to DIE-HBM-61/SPLIT. The pin-bound and macro-channel cores go to
DIE-HBM-61/MEM. Their slots in this event are PLACEHOLDERS (unchanged), and their outlines and pins fold in when those
lanes post READY.

Base: DIE-HBM-60/PLAN v4. That is d44t + d44w (4fe0c55a9b5, on main) + d44u mu1-3sram, re-applied, + the FT S0 re-site
and nudge moves (ft_s0_resite --jog-sweep, ft_nudge clock halo; tools on this branch, f252174de86).
Sidecars are the d44t plan dir. Files that differ are in this dir; files over 200 kB are stored as .gz.
Builder: `results/die_hbm_1103/reform/build_d44v.sh WORK OUT`, steps in order:

1. **Templates (d)** `mk_tmpl.py`: the 10 per-hub `__sp_*__fx` vms_bank repins of v4 go back to their shared tables.
   That keeps the design count at 84 (DIE-HBM-61 ruling).
2. **RE-FORM slots (class 2)** `mk_reform.py`. This is a centre-kept resize via MASTER-PLAN-R6 hub_repack.run, using
   even 8.64 steps so origins stay on the 8.64 lattice. Each resize is accepted only when every one of these holds:
   - est fill <= 0.45 (target 0.40);
   - aspect <= 2;
   - each face >= pins/5 per um;
   - (W+H)/2 <= 220;
   - macro channels >= 10.8 um AND >= the pin count x 0.048/2;
   - the centre entry is not over a macro;
   - no parent station gains a register.

   Result: ot_hgi_qw_dec goes from 260x260 (fill 0.27) to 260x173.6 (fill 0.40, aspect 1.5). No station is regenerated.
   Left unchanged:
   - q2_hard_reduce: +1 register on 13 crossings;
   - subtree32: +1 on L43_o;
   - pc_ctrl_leaf_cfg_h9b: +1 on kr_data, and the odd-k form put origins off the lattice.
3. **Slot infra (a)** `mk_infra.py`: core_pg_connect: true (PG-CORECONN-2) on q_hub_ne, q_hub_nw and root, which carry
   35 + 35 + 3 placed hard-core macros.
4. **Centre clock-entry pins, LAST plan change**: tools/die_plan/clock_entry_pins.py (claude/die-hbm-60-centry-1103,
   on main). It covers 84 tables: 52 moved, 6 kept (the signed records).
5. Sidecars:
   - `reform_census.json`: per RE-FORM core, the class, the owner lane and the plan numbers.
   - `core_clock_regions.json` (OWNER: one clock entry per <= 5k sinks): 33 modules over 5k sinks get 239 regional
     entries over 576 slots. Kit/gen support for these entries is DIE-HBM-61/CLOCK. 35 modules have no sink data.
   - `ext/`: the (a)-(d) census and the ONE die crossing latency table, `crossing_latency.json`.

Proof: see the "Checks" section, appended by the builder run.

## Part 2 (builder steps between 3 and 4; the centre clock-entry pins stay LAST)

All numbers are advisory (OWNER 11-03). Each step writes an event file into this dir.

- **2b. Part-2 lane outlines** (`mk_reform.py` + `p2_outlines.json`), from DIE-HBM-61/MEM 55c4a61894a `channel_fit.json`:
  - ot_hbm_host_cp_rxs: 434.808x480 -> **400.248x151.68**. Fill goes 0.035 -> 0.107 and aspect 1.10 -> 2.64. The
    station count is unchanged.
  - hfd_ep_static: the slot is **kept** at 427.68x246.24. channel_fit's 250.56x146.88 fits, but every shrink tried
    (H 159.84-211) adds 1 register on the vsN0 u_lk_S1->u_ep_S1 and NW_io u_ep_N0->u_lk_N0 stations.
  - Both get core_macros status UNKNOWN (old entry under `macros_r2c2_old`) until the RE-FORM kit runs.
  - The MEM recipe (OT_HBM_RW_MACROS define + instance renames) is in `mem_recipe_delta.json`, copied verbatim.
- **2c. Pin moves** (`mk_repin.py`, `repin_event.json`, new tables `cores/*__p2pin.json`):
  - keybuf_slice: key_out goes W -> E, giving W 1132 / E 1099. That is 5.2 pins/um at a 0.192 pitch.
  - vm_wr_q_t_lanes4: the outline is kept (a 259-um-tall slot breaks 22 q_hub stations). The faces go from
    N 839 / E 1116 / W 562 / S 1156 to **N 746 / E 1122 / W 1059 / S 746**, at a 0.168 mean pitch (5.95 pins/um).
    - The move is bit-level and minimal. It uses the check.py core_faces score per instance, so no port mean drops
      below -0.09. Result: 0 new core_faces FAIL.
- **2d. keybuf macro sites** (`mk_kbmac.py`, written into `core_macros.json`): 4x ot_sram_1r1w_256x256_m2_r0c0_g256
  (169.368x28.392) + 1x ot_sram_1r1w_256x64_m2_r0c0_g64.
  - One column at x 31.32-200.688, orient **MY**: the write port (wd_in) faces W = key_in, and the read port (rd_out)
    faces E = key_out.
  - Channels:
    - W logic channel **31.32 um**. Need: 1132 pins x 0.048 / 2 vertical layers = 27.2 um.
    - E channel **41.23 um**. It holds the clock island [203.04,142.56,211.68,151.2].
    - 6 row gaps of 25.0-25.4 um carry the key_in -> key_out bypass mux wires (1099 bits on M4/M6, about 31 um of the
      151 um available).
  - No route crosses a SRAM.
- **2e. Clock entry over a macro** (`mk_cefix.py`, `cefix_event.json`): q_su00 lanes_plain__canon_663526. The entry
  moves to the nearest free same-phase lattice point, [168.456, 228.96]. All 16 entries of that table are updated,
  and so are the type clock taps.
- **2f. Hard-core reset trees for q_sm0-3** (`mk_smrst.py`, `hard_reset_trees.json`). These are the 128 rp3lp3h core
  resets that had no tree.
  - The tree is the generator's reset topology (relay reach, blockages, walls), sized as below. `reset.depth` is set
    to the tree depth.

    | type | depth | relays |
    |---|---|---|
    | q_sm0 | 20 | 376 |
    | q_sm1 | 19 | 307 |
    | q_sm2 | 20 | 340 |
    | q_sm3 | 19 | 325 |

  - Open: on q_sm1 and q_sm3, the u_sm_t00_s last mile is 439 um (the pin is behind its core). That one is for the
    kit's in-core relay.
- **2g. Relay bays on first FT hops over 405 um** (`mk_bays.py`, `bays_event.json`). Each bay sits on the in-face
  strip and then the free L path, or the free 4.32-grid point nearest S1, clear of hard cores and of the check.py
  geometry macros. The station counts change as follows:

  | slot (type and __physical_v1) | stations |
  |---|---|
  | q_su31 L5r0_1 | 7 -> 9 |
  | q_su31 L34r0_1 | 6 -> 8 |
  | q_su31 L6br0_1 | 4 -> 5 |
  | q_su00 L730x1 | 7 -> 9 |
  | q_su01 L730x4 | 7 -> 9 |

  - All first hops are now <= 357 um.
  - `gen.py latency --inplace` regenerates latency.lanes, and `latency_changes_d44v.json` holds the part-1 and
    part-2 changes. Part-2 cycle changes:

    | lanes | cycles |
    |---|---|
    | L5, L5m, L34, L34m | +2 |
    | L6b, L6bm, L6, L6m, L6c, L6cm | +1 (latency group) |
    | L730, L730m | 44 -> 51 |

    - L730's +7 is +4 from bays. The other +3 is a stale part-1 latency record, now regenerated (sum of stations 49).
- **Sidecars**:
  - `split_slots.json` (`mk_split_slots.py`, `split_spec.json`): the SPLIT READY sub-block slots inside the parent
    slot (8.64 street, 8.64 lattice, per-sub centre clock entry).

    | parent | SPLIT ref | sub-block slots |
    |---|---|---|
    | hcol_h0 | c4237519789 | ra 103.68 + rb 106.272 x 187.488 |
    | split3_lane | 273120b2730 | fr 120.96 / ex 95.04 / bk 155.52 x 345.6 |
    | lanes8_11 | 8dd205e8bcc | 3x 181.44 + 190.08 x 311.04 |

    - The hard_cores swap waits until the composition RTL lands.
    - q3_edge (WIP d764970683d), rp3lp3h_n/s (WIP), q3_body, tkm and fused_lane stay placeholders.
  - `core_clock_regions.json`: the one unsited hnx_rp3lp3h_n region now has a site (nearest free lattice point).
  - `corelat/*.tsv`: the SPLIT and MEM latency tables, folded into ext/crossing_latency.json.
- **Crossing latency** (`ext/crossing_latency.json`, CLOCK ruling 11-03):
  - Every core-face crossing without a count-aligned station gets face reg + negedge lockup + 1 parent-face relay
    register, which is **+1 declared cycle**. There are 4 such crossings in this plan.
  - Crossings that have stations get no lockup.
  - Core-internal rows: 32.
    - split3_lane: +4 on write/reducer/status.
    - hcol_h0: the ra->rb seam is +2, internal and compensated (0 at the ports).
    - MEM: +0.

## Part 3 (one-block plan fix after freeze: hcol_h1 mesh-island ft pins; builder step after 2d)

- **Why**: SS24 10:06. The signed ot_hbm_idx_score_hcol_h1 (hcol_h1_w90 routed DB, re-signed in ss23/hcol_w90_r_hbm,
  flow-20261102-r-hbm) has 1228 pins. The plan table (d35a `__canon__codex_g21`) has 1216. The 12 extra pins are
  the 12.2a1 pushdown island ft ports `mp_isl{0,1,2}_{ck,rst}_{i,o}` that the kit adds from core_infra_plan.json
  (the d35a master-plan form). So the record matched no plan design.
- **Event** (`mk_mpisl.py`, `mpisl_event.json`): the new table `cores/ot_hbm_idx_score_hcol_h1__218.592x187.488__canon__codex_g21__mpisl.json`
  is the 1216 rows + the 12 pins. Each pin is M5, at the signed-DEF centre with its w/h (DEF sha256 8ce38d2e9978acd4).
  All 128 hcol_h1 `pins_file` refs point to it. No other row moves.

  | island (role) | ck_i | ck_o | rst_i | rst_o |
  |---|---|---|---|---|
  | isl0 (clock entry) | 106.92, 97.2 | 109.08, 97.2 | 106.92, 92.88 | 109.08, 92.88 |
  | isl1 (tree leaf) | 55.08, 97.2 | 57.24, 97.2 | 55.08, 92.88 | 57.24, 92.88 |
  | isl2 (tree leaf) | 163.08, 97.2 | 165.24, 97.2 | 163.08, 92.88 | 165.24, 92.88 |

- **Parent connection** (`cores/ot_hbm_idx_score_hcol_h1__d44v_mpisl_parent.json`, d35a / 12.2a1 form). Island rects are
  the plan `clock.mesh.core_islands` ones.
  - `_ck_i` connects to the die clock tap: the M9->M5 stack at the island centre.
  - `_ck_o` connects to the die mesh/tree feed-through net, independent of the core clock pin clk_pair[0].
  - `_rst_i` connects to the die regional reset stack (M9->M5).
  - `_rst_o` connects to the die reset feed-through net.
  - Arcs: ck via the fixed BUFx8 `mp_islK_ck0`, rst via the fixed BUFx4 `mp_islK_rst0`. There is no core logic on
    these arcs (LEC-exempt).
  - Signed ft_interface delays: TT ck 23.2-26.4 ps, rst 25.0-28.2 ps.
- **Result**: the signed record now gives DESIGN-MATCH: 1228/1228 pins match, 0 by convention. With d44v part 2 it
  gave "12/1228 pins: extra pin (record only)".

## Part 4 (fix-only after freeze: KNOWN right-width macro sites for hfd_ep_static and ot_hbm_host_cp_rxs)

- **Why**: KW-FIX-4 11:58 SWITCH held both cores. Part 2 swapped them to the DIE-HBM-61/MEM right-width masters
  (55c4a61894a, `OT_HBM_RW_MACROS`). Their core_macros entries were left UNKNOWN, with the r2c2 rects kept under
  `macros_r2c2_old`.
- **Event** (`mk_rwmac.py`, written into `core_macros.json`; builder step after `mk_mpisl`). Status is now KNOWN, in
  the keybuf 2d form:
  - W column MY, E column R0, so the read pins (master W edge) face the centre logic channel.
  - Channels are >= 10.8, row gaps 8.64, and the clock entry sits in the centre channel.
  - Outlines, pins and die_plan.json are unchanged; the die_plan sha stays the same.
  - The macro names are the recipe inst renames.

  | core (outline) | macros | form |
  |---|---|---|
  | hfd_ep_static (427.68 x 246.24) | 4x ot_sram_1r1w_64x306_m1_r0c0_g306 `u_fcore.u_rxb.g_block[b].u_block.g_mem[m].u_mem.g_rw.u_sram` | the old 2x2 grid, each macro on the centre-facing edge of its old rect: x 82.512 / 239.112, y 70.416 / 169.776; centre channel 50.5 holds the entry (216.0, 120.96); W/E logic fields 82.5 um, S field 70 um |
  | ot_hbm_host_cp_rxs (400.248 x 151.68) | 2x ot_sram_1r1w_256x256_m2_r0c0_g256 `u_fcore.u_land.g_bank[b].u_mem` + 4x ot_sram_1r1w_64x141_m1_r0c0_g141 `u_fcore.u_link.g_bank[k].u_store.u_native.g_rw141.u_sram` | S-edge block (the S face has no pins), 2 columns x 3 rows: 256 banks at y 15.12, 141 leaves at y 52.164 / 81.648 on the centre side; x 15.12 / 215.676; centre channel 31.2 holds the entry (198.72, 77.76); N std-cell band 49 um |

- **Result**: both "macro positions UNKNOWN" clock_entry_macro WARNs are gone. Nothing else changes.

## Part 5 (one-block fix after freeze: bank128_pair macro stack; DIE-HBM-61/B128, COORD 15:3x GEOM)

- **Why**: kit-wave d44v AUTO-GEOM of ot_hbm_hc_bank128_pair_core__v7d149b37532c: GRT overflow 7646 (50 it), channel_h
  FAIL 0.93 in the N band, channel_v / col_v FAIL 0.67 in the W column at y ~207. g_w[0] sat at y 179.28-249.77 and
  left an 18 um N band (9.5 um of rows) under the 563 N face pins. Their face flops routed out sideways around the
  macro corners; the macros block M1-M4 and only M5 crosses them. Both 1024 macros sat at x 21.6, so the W column was
  17 um of rows for the 512 W pins plus the macro W-edge pins.
- **Macro pins**: the SRAM signal pins are M4 on the master W and E edges (415 + 415 per 1024x256, 410 + 411 per
  128x256), in the lower 40.5 um in R0. MY/R0 keep them low; R180/MX put them high. The channels that carry the macro
  pins are therefore the W/E columns, sized from pin count (macro side pins + slot side pins) x 0.048 / 2.
- **Event** (`mk_b128.py`, written into `core_macros.json`; builder step after `mk_rwmac`). It is an S-edge stack
  with a wide N band and centred 1024 columns. Outline 250.56 x 267.84, pins and die_plan.json are unchanged (sha
  a396208a7ec4). The modules are ot_hbm_hc_bank128_pair_core (both kit variants) and
  ot_hbm_hc_bank128_pair_first_core, the only d44v cores with this stack.

  | macro | orient | rect (um) |
  |---|---|---|
  | g_w[1] 1024x256 | R180 (pins high, into band A) | 38.88, 4.32 - 213.624, 74.808 |
  | g_x[0] 128x256 | MY | 21.6, 108.0 - 116.424, 149.064 (x kept: entry (125.3, 133.9) 8.9 um E) |
  | g_w[0] 1024x256 | MY (pins low) | 38.88, 158.76 - 213.624, 229.248 |

  The N band is now 38.6 um (was 18.1) and band A is 33.2 um. The W column is 38.88 (was 21.6) and the E column is
  36.94 (was 54.2) beside the 1024 macros. The core_clock_regions.json regional entries of the first_core move with the
  macros (sidecar regenerated by `mk_clkreg`).
- **Pre-build probe** (epyc2 scratch-root/claude/b128probe): kit d44v synth + 2_1 floorplan, 2_2 macros -> 3_place,
  then AUTO-GEOM `geom_check.sh` (GRT M2-M5, 50 it):

  | form | GRT overflow | usage | channel_h | r2r > 405 |
  |---|---|---|---|---|
  | d44v part 4 (kit item) | 7646 | 37.6% | FAIL 0.93 | 0 |
  | **part 5 (g_w[0] MY)** | **0** | 39.6% | WARN 0.999 | 1 (422 um) |
  | alt g_w[0] R180 (pins up) | 0 | 41.3% | 1.03 | 2 (434 um) |

  The r2r hits are one lane -> `lf` fan-in (advisory).

## Part 9 (one-block events: one plan clock pin for 3 cores, xcal central macros, q2r table; DIE-HBM-65, COORD 07:34 (2), 08:40 (4))

Builder: `results/die_hbm_1104/reform/mk_p9.py PLAN TABLES results/die_hbm_1104/reform/part9/core_macros_delta.json`, after the build_d44v.sh steps; tables gunzipped from part9/tables. Replay on base = this plan [CHECKED].

- **Oneclk** (DIE-HBM-63 02c23e9262c5, class PORT-TREE-SKEW): lane1, lane_exp canon and split3 ctl get one pin `clk` at the middle clock pin. 78 pins_file refs in q_su*. 0 added cycles. Approve basis COORD 07:34 (2): bench mutants, source LEC on logic (lane1oc 17121, lane1b 17125, ctl_oc 56984), wrapper diff `oneclk_wrapper_diff.txt` (tool oneclk_wrapper_diff.py): lane_exp 13 changed lines, ctl 9, lane1 69 connections with 4 clock lines; off-rule 0. Kit LEC is clock-blind, so it is not part of the basis. No oneclk kit has a sign-off yet. Canon lane_exp ~188k and ctl ~187k cells are over the 150k conservative target (target only).
- **ctl recipe pin**: the oneclk ctl wrapper was only ever passed by hand; recipes_split.json now selects it by table sha 5e0b96ed.
- **xcal_rel_t + lane1 macros**: the 2 core_macros rows that differ (part9/core_macros_delta.json), central form and the `u_core` names under one clock.
- **q2r table**: `...__oneclk__codex_g21__centry__in512.json` drops u_reduce_in_flit[544:512] (33 bits, 1143 -> 1110). The RTL reads 16 x 32 bits and the face shell already dropped these, so the signed record had 1110 pins and counted as core, not design. Wrapper `oneclk/ot_hfd_coll_q2_hard_v8g__reduce__in512.sv` ties the 33 bits to 0 at the RTL input. Parent side [CHECKED, results/hbm_query_native_event_0135/selected, q_hub_nw and q_hub_ne]: the 33 bits are the two top slices of the 545-bit concat at this pin (qout_17 bit 0, qout_16 31:0); each wire has one driver (the body output) and this pin as its only sink, so the body outputs end unloaded and nothing else changes. The parent RTL still passes 545 bits to a 512-bit port, so elaboration drops the 33 MSBs, the same bits; not elaborated or LEC-checked at parent level here. core_conns.json has no entry for this port. No re-sign.
- **Checks**: G0+G0C 24 -> 24, errors gone 0, **new 0**; warnings new 0, gone 1 (`g0/g0_diff_d44v_p7_p9.txt`). Plan-time GEOM advisory FAIL 225 -> 225, new 0, worse 0 (`geom/geom_diff_d44v_p7_p9.txt`). Gen trial of all 4 views rc 0 on this plan (no build). Count: q2r record MATCH 1110/1110, `g0/count_check.txt`. Designs stay 91.
- **Open**: the live oneclk kits were built on plan copy d44v13oc, older than main in 3 places, so this event carries the delta and not that copy. Whether each of those kits counts on this plan is read from its pins at the sign-off record; not checked here.

## Part 7 (conservative form, OWNER 18:57: the huge rp3lp3h n/s and fused_lane cores become plan sub-core designs; DIE-HBM-62/BIG)

Builder step `mk_split.py p/b3 split_p7/split_p7.json split_p7`, right after the part 6 step (build_d44v.sh). Inputs are in
results/die_hbm_1103/reform/split_p7/. `gen_p7.py` writes the composition with flat instances (u_ln<p>_tl0/tl1/lc, u_p<q>)
and the glue. `p7_check.py` proves its wiring identical to the EQ-proven reform_1103 composition: DIFF 0 on 25473 (n),
23504 (s) and 5610 (fused) bits. The RTL and EQ proofs are on main: rtl/hbm_accel/cores_split/reform_1103 and
physical/die_plan/hbm/over_cap_split/reform_1103.

| core (EQ sha) | inst | slot | sub-core designs (tile, pins, instances in the die) |
|---|---|---|---|
| hnx_rp3lp3h_n (c37ffbb6c4) | 64 | 630.72 x 1209.6 | gn 630.72 x 345.6 (9573, 64); xs 630.72 x 216 (7785); 3 x lc 198.72 x 216 (1671); 6 x tl 95.04 x 155.52 (517) |
| hnx_rp3lp3h_s | 64 | 630.72 x 1036.8 | gs 630.72 x 345.6 (7604, 64); the same xs, lc, tl masters, MX in the s slot |
| hnx_fused_lane | 32 | 345.6 x 518.4 | c 345.6 x 103.68 (2995, 32); 4 x elp 172.8 x 198.72 (653, 128) |

The shared masters place xs 128, lc 384 and tl 768 times. Designs: 87 -> **91** (-3, +7).

- **Layout.** Explicit tiles in the spec (`layout`), every edge on the 8.64 lattice. rp3 stack away from the n/s seam:
  glue -> xs -> lc -> tl. Fused: c at the south, 2 x 2 elp above it, all elp pins on the S face (the upper pair's wires
  pass over the lower pair).
- **Pins.** Seam pins are per-peer blocks in natural order on the N/S faces. A shared master has one pin table across
  cores (asserted: outline, ports, clock entry). Bus-level station refs and partner connections go to `boundary_sub`.
- **mk_split fixes.** The swap loop finds hard_cores by instance name (earlier swaps shift indices). split_event.json
  keeps the core_faces moves of earlier parts.
- **Fill targets.** ORFS synth area / tile area: tl 41%, lc 37%, gn/gs below 40%; xs below 40% with macros; fused c 46%
  and elp 47%, a little over the 0.45 target because the slot is fixed. Fused kits use util 0.5. These are targets only.
- **Added cycles (TOK-VERIFY batch).** rp3: leaf result +7 edges, xs->glue act mask +2/+3 pure delay. Fused: up chunk sum
  +4, wq/fin HC_POST +4, HC_PRE_NORM +8, flt +4; rq, scalar up and inputs 0. Tables: over_cap_split/reform_1103 latency/.
- **Reset.** The kit face shell adds a face flop + lockup on rst_lf/rst_ln outputs; xs/lc/tl reset inputs pass through;
  gn/gs/c/elp rst_n get relay 2. Only release timing differs from the bench model (rst_n is held >= 64 clk, owner rule).
- **Clock regions.** mk_clkreg `--extra split_p7/sinks.json` (ORFS FF counts): xs 8, lc 5, tl 2, gn 6, gs 4, c 3, elp 4
  entries. The part 6 subs still have no sink data.
- **Checks.**
  - G0+G0C: errors gone 0, **new 0**, by check core_faces 8, hops 2, reach 9, stations 3, street_die_leg 2 (same as part 6).
  - Plan-time GEOM: FAIL 225 -> 225, **new 0, worse 0**.
  - Count: all signed records still in the record set MATCH. The query_static table is byte-identical to part 6a; its
    q7b2 record is not in the 8-record input this time, so the count has no line for it.
  - Diffs: g0/g0_diff_d44v_p6_p7.txt, geom/geom_diff_d44v_p6_p7.txt, g0/count_check.txt.

## Part 6a (one-block plan pin event: query_static q7b2 mesh-island ft pins; builder step after mk_cefix)

SS24 re-signed ot_hbm_idx_query_static q7b2 at 20:16 (ss24/q7b2_w_hbm, flow-20261103-w-hbm): SIGNED TT +0.35 /
FF +6.54, LEC EQ. It did not count because design_unmatched showed 4 extra pins against the d44v table. This is the
same class as hcol_h1 in part 3.

- `mk_mpisl_q.py` adds mp_isl0_{ck,rst}_{i,o} to the query_static table (1633 -> 1637 pins). The pins are placed at
  the signed DEF layer, centre and rect (DEF sha256 88f7ef6a00a78f36).
- It repoints the 4 pins_file refs and writes the parent-connection sidecar
  cores/ot_hbm_idx_query_static__d44v_mpisl_parent.json. That sidecar holds the 12.2a1 ft arcs from signoff
  ft_interface.json: BUFx12f clock and BUFx4 reset.
- Count: the q7b2 record (signed-DEF pins) gives **MATCH** against the plan design, 1637/1637 pins.

## Part 6 (conservative form, OWNER 18:57: the DIE-HBM-61/SPLIT cores become plan sub-core designs)

Builder step `mk_split.py p/b3 split_p6/split_p6.json split_p6`. It runs after mk_cefix / mk_mpisl_q and before
mk_smrst. The centre clock-entry pins stay LAST. Inputs, all in results/die_hbm_1103/reform/split_p6/:

- the spec;
- `<core>__p6glue.sv`, the thin parent glue;
- `<sub>.conn.json`, which split_conn.py derives from a yosys netlist of glue + composition with the subs blackboxed.

The glue is the kit pass-through wrapper `<core>__fcore` with its u_core swapped to the SPLIT composition, plus the
plan module as a wires-only shell. It has no face registers: every sub-core carries its own kit face shell. The
physical sub-core path is `<inst>.u_fcore.u_core.<u_sub>`.

| core (SPLIT EQ sha) | inst | slot | sub-core designs (tile, pins) | added cycles |
|---|---|---|---|---|
| ot_hbm_idx_score_hcol_h0 (c4237519789) | 128 | 218.592 x 187.488 | ra 106.272 x 187.488 (1165), rb 106.272 x 187.488 (1198); street 6.048 | 0 on every port |
| ot_hgi_sfu_split3_lane_core__idpin (273120b2730) | 32 | 388.8 x 345.6 | bk 155.52 (385), fr 120.96 (1557), ex 95.04 (68), full height; streets 8.64 | +4 on sfu_vm/kv/ro/fault/coll outputs |
| ot_hbm_su_static_pgslice_lg__lanes8_11 (8dd205e8bcc) | 4 | 760.32 x 311.04 | 4 x ot_hbm_su_pg_lane1_core 190.08 x 311.04 (2035), abutted, one table | 0 on every port |

- **Tiles.**
  - Tiles run along the long axis. Every tile edge is on the 8.64 lattice in both R0 and mirrored instances, so
    track_offset is 0.
  - The sub order is the permutation with the least pin displacement: bk | fr | ex. The 35 bk<->ex bits cross fr.
- **Pins.**
  - Parent-pin bits keep the parent face and position, clamped into the tile.
  - Seam bits sit on facing faces in the same order on both ends.
  - Clock bits sit at the sub's own centre entry: M5, every 2nd track, the same placement as clock_entry_pins.
  - The lane1 entry is at (164.16, 155.52) in the macro-free E strip.
  - Unconnected bits go on the replicas' common outer faces.
  - core_faces pass (check.py model, as mk_repin): hcol rb cf_out / cs_out / prdy move E -> N.
- **Sidecars**, re-pointed from the core inst to its subs:
  - clock_entries.json and clock.taps: one entry/tap per sub.
  - core_conns.json: sub ports, parent targets, seam peers, and the partners' core:<sub>.
  - internal_stations: 11,696 re-pointed; <inst>.<port> goes to the owning sub port, a bare inst to the nearest
    tile. The 132 hcol cs_in/cf_in refs are dead ports, tied 0 in the uncut shell.
  - parent_id_straps (split3 map_lane_j) move to fr.
  - core_macros.json: lane1 is KNOWN with 6 x 128x256 as one column (pairs abutted, 24.024 channel as the uncut
    rows), x 41.148.
- **Part 7** (next event): fused_lane, rp3lp3h n/s, q3_edge, tkm idpin/terminal, q3_body. Their EQ verdicts are on
  claude/die-hbm-61-split-1103.

## Checks (epyc2 die-hbm-60-plan, same tools for every plan: main 08542fa9d7d + d44v tools)

- **G0+G0C** (`tools/die_plan/check.py --completeness`):

  | plan | ERROR | pending-view |
  |---|---|---|
  | d44t | 74 | 128 |
  | d44v part 1 | 51 | 128 |
  | d44v part 2 | 24 | 128 |
  | d44v part 3 | 24 | 128 |
  | d44v part 4 | 24 | 128 |
  | d44v part 5 | 24 | 128 |
  | **d44v part 6 + 6a** | **24** | 64 |

  - Against part 1, 27 are gone and **0 are new**.
  - Against d44t, the 3 "new" are pre-existing items under a new message:
    - u_vmb_Q6/Q7_mu1 dq core_faces: mu1s3 282 -> 281 pins.
    - L701 reach: hop index shift, still 392 um.
  - Part 3 against part 2: gone 0, **new 0**, and the warnings stay at 1148 = 1148.
  - Part 4 against part 3: errors gone 0, new 0. Warnings go from 1148 to 1146: the 2 UNKNOWN-macro clock_entry_macro WARNs are gone.
  - Part 5 against part 4: errors gone 0, new 0; warnings stay at 1146 = 1146.
  - Part 6 + 6a against part 5: errors gone 0, **new 0**; warnings 1146 -> 1085; pending-view 128 -> 64 (the 128 hcol_h0 merged clk_pair taps become single-clock sub taps). Diff: g0/g0_diff_d44v_p5_p6.txt.
  - Diffs: g0/g0_diff_d44t_d44v.txt, g0/g0_diff_d44v_p1_p2.txt, g0/g0_diff_d44v_p2_p3.txt, g0/g0_diff_d44v_p3_p4.txt and g0/g0_diff_d44v_p4_p5.txt.
- **Plan-time GEOM** (`plan_geom.py`, 74 types): **new FAIL = 0**, and the FAIL count is 225 -> 225. All of these
  are advisory, and every type already fails clock_tap_sinks or clock_reach.
  - Values worse on rules that already fail (clock_tap_sinks):
    - q_su31: 7073 -> 13386 (bays: the L5/L34/L6b stations sit on the q_su31 tap);
    - q_su11pv1: 5654 -> 6403;
    - q_su01: 8890 -> 9194;
    - q_su20: +1.
  - Part 3 against part 2, part 4 against part 3 and part 5 against part 4: identical (new 0, worse 0, better 0).
  - Part 6 + 6a against part 5: new FAIL 0, 225 -> 225. One value is worse on a rule that already fails (q_b112__physical_v1 clock_tap_sinks 9577 -> 9580). Better: q_b110 clock_reach 289 -> 238, plus 6 clock_tap_sinks. Diff: geom/geom_diff_d44v_p5_p6.txt.
  - Diff: geom/geom_diff_d44t_d44v.txt.
- **Count** (part 6): 84 -> **87** designs: -3 split cores, +6 sub-core designs (ra, rb, fr, ex, bk, lane1). All 9 signed records are **MATCH**: the 8 of part 4 plus q7b2 query_static (part 6a). hcol_h0 had an unchanged key, so 26 of 84 keys are unchanged. Earlier parts: 84 -> 84 designs, and the 6 signed cores keep their design key (SAME). See g0/count_check.txt.
  - The signed hcol_h1 record (signed-DEF pins) gives **MATCH** against the plan design: 1228/1228 pins.
  - Part 4: all 8 signed records (routed-DEF pins) give MATCH: pretree, hcol_h1, qctl, tail_native x2, collar,
    ring_ag, tnode. Part 5: the same, count output identical to part 4.
    count_check.py uses the release counter's `design_pin_cmp` / `pins_equiv`.
  - hcol_h1 now has a new design key (the 12 pins), so 27 of 84 design keys are unchanged against d44c (was 28).
- **Census** (ext/census_summary.json):
  - (a) 81/81 types carry PG + clock tap + reset relays.
    - 379/1028 core slots are complete.
    - The 133 reset gaps include the 128 q_sm rp3lp3h. Those are now covered by hard_reset_trees.json, which the
      census does not read.
  - (b) 203/203 die lanes over 400 um are hop-compliant (part 1: 195/203). FT slots: 520, 0 over.
  - (c) 21,184 crossings; plan cycles +44 over d44t; RTL/SPLIT core port cycles: see the 11-04 fold below.
- **Core cycle fold + calendar LEF, 11-04 (DIE-HBM-63; SS25-TOK 23:23, SS26-TOK 04:05 exactness gap):**
  - `corelat/` now holds every declared core cycle table whose form is in this plan, built by
    results/die_hbm_1103/reform/mk_corelat_fold.py: over_cap_split latency tables + reform_1103/cycles tables.
    `ext/crossing_latency.json` was regenerated with ext_census.py --core-lat on this plan (it was last written on part 7a, d44v7).
    Lanes and type_internal rows unchanged: die lane cycles 4035, type internal 91793, plan cycles +44.
    Core port maxima new here: hnx_fused_lane 8, hnx_rp3lp3h_n/s 7, tailx_rest 70, subtree32 17, vms_glue_nw_t 1.
  - Not folded (split form not in this plan): q3_body_core, the two tkm tile straps (+448 TKM op), listed in the delta.
  - `compiler_core_delta.json`: no compiler code reads core cycle tables (LAT ABI = latency.lanes only), so this is the
    schedule delta for the S2 model of record: HC_PRE_NORM +8, HC_POST +4 per record, SM +7 per record.
  - hfd_hgi_vm_calendar_f20 plan LEF: 10-16 ref_tile copy -> cores/hfd_hgi_vm_calendar_f20__241.92x116.64.lef (sibling
    routed view cal_sg 11-03). 558/558 table pins inside the LEF pin rects, 0 layer differences. No pin table,
    outline or lane changed; plan GEOM unchanged by construction.

## Part 10 (fused host program conservative outline; DIE-HBM-66, COORD 09:16 (2))

- **u_mu_fused_program** (`ot_hnx_fused_host_program`): 207.36 x 129.6 -> 276.48 x 129.6 (35832 um2), fill 0.65 -> 0.43 (1273 std + 14194 macro) for the owner-rule conservative form (fhp7 failed on the old outline). All growth on E, 69.12 um, origin (734.4, 5339.52) kept. Pin table `__p10`: same 562 pins, N and S faces only, same core and die position; both SRAMs and the clock island unchanged; no parent wire moves.
- **Why E only**: the first trial grew 34.56 W and E; G0 flagged L9x1 stage 10 bit sites (x up to 747.36) against W (428 cells), new error. E is free: `part10_event.json` slot_hits [] including actual bit sites, hard cores, contents, channels, internal stations.
- **Checks**: G0+G0C 24 -> 24, new 0, gone 0 (`g0/g0_diff_d44v_p9_p10.txt`). Plan-time GEOM advisory FAIL 225 -> 225, new 0, worse 0 (`geom/geom_diff_d44v_p9_p10.txt`). Gen trial of the core rc 0, DIE 276.48 x 129.6. Designs stay 91. Stacks on part 9.

## Part 12 (qw_dec clk pin to the signed location; DIE-HBM-66, COORD 15:56)

- **ot_hgi_qw_dec** `clk` M5 (129.624, 86.4) -> (129.624, 0.24), S face, table `__p12`; the other 1669 pins unmoved. Signed DB kept (re-signed on flow-20261104-k-hbm); the table now equals the signed kit's 1670 pins. Two `q_hub_nw` rows take it.
- **Parent clock taps**: `u_hb_quant_Q__u_dec__q0` (164.16, 1650.24) -> (164.16, 1564.08), `__q1` (4121.28, 2592.0) -> (4121.28, 2505.84); same x. The two clock entry rows follow (xy 129.6, 0.24; island kept 8.64 um square, clipped to the S edge).
- **Checks**: G0 compare new 0, gone 0. Plan-time GEOM advisory FAIL 225 -> 225, new 0, worse 0. 0 cycles, no RTL. The plan has no `asbuilt` key, so bind.py does not apply; pin names are unchanged.

## Part 13 (outlines for measured GRT overflow; DIE-HBM-66, COORD 19:1x and 19:34)

- **ot_hfd_coll_q3_edge_core** +60.48 um on W, 216 -> 276.48 x 1054.08, origin x 95.04 -> 34.56 (on the 8.64 lattice). Reason: M3 126.8%, macros 70% of area. E face, clock pin and tap keep die position; W pins stay on the W face; other pins +60.48 local, 12 macros +30.24.
- **ot_hgi_dma_back_static_vp4_banks_cp** +60.48 um on local E, 239.976 -> 300.456 x 275.4. Reason: M2 114%, M3 116%, macros 59%. Second macro column +30.24; `__q0` copies keep origin and pins; `__q1` (mirrored) copies keep their die W edge, so pins and tap move +60.48 um in die x.
- **ot_hcol h0_rb** out: 0.68 stdcell utilization, room only +7.56 x +1.08 um; next form follows h0_ra.
- **Checks**: G0 compare errors new 0, gone 0; warnings 1950 -> 1940, new 0 (the 10 gone were missing-pins warnings on these rows). Plan-time GEOM advisory FAIL 225 -> 225, new 0, worse 0 at +64.8; not rerun at +60.48, plan_geom reads non-hard types only, so these two outlines are not in it. Slot hits 0. 0 cycles, no RTL.

## Part 8 (pslice_c5 per-column sub-cores; DIE-HBM-63/CUTS, replayed by DIE-HBM-66 on part 13, COORD 20:2x)

ot_hbm_su_programme_pslice_c5 (4 inst, q_hub_nw/ne.u_pgp_Q__q0/q1) becomes ot_hbm_su_pcol_s x7 (118.8x336.96, 7 macros), _l x3 (257.04x423.36, 17 macros) and head _h (136.08x216, no macro). Registered faces, per-column start/length relay with no shared flop, registered command funnel.
Slice latency against the kit base form, end to end: start/length/cfg to command/busy/valid/done/edge_index +2, to fault +4, physical/die_plan/hbm/reform_1103/cycles/pcol.tsv. Bench: split_p8/run_eq.sh (lockstep, 8 mutants killed).
Built by `mk_split.py` at 3ea69acee2a on the older chain; here its plan delta is a 3-way JSON merge onto this tree (0 conflicts, q_hub_nw/ne only). **Checks** against part 13: G0 errors new 0, gone 0; warnings 1940 -> 1972 (the part's core_faces rows, as in its own p7-p8 diff). GEOM advisory 225 -> 225, new 0, worse 0, clock_reach better on q_hub_ne/nw. su_pcol_h signed off and routed LEC EQUIVALENT; _s and _l forms still running.

## Part 14 (fused host program clk pin to the signed location; DIE-HBM-66, COORD 20:4x)

- **ot_hnx_fused_host_program** `clk` M5 (103.704, 64.8) -> (103.704, 129.36), N face, table `__p14`; the other 561 pins unmoved. Signed DB kept (re-signed on flow-20261105-i-hbm). The kit was generated without `--clock-pin-entry on`, so the centre entry went to the N face; the plan now follows it. Gen on a stage with the flag: rc 0, all 562 pins equal the signed kit.
- **Parent clock tap**: `u_mu_fused_program.clk` (838.08, 5404.32) -> (838.08, 5468.88), same x. The `root` clock entry row follows (xy 103.68, 129.36; island kept 8.64 um square, clipped to the N edge).
- **Checks**: plan diff 3 fields on `root` plus 4 on its clock entry. G0 compare new 0, gone 0. Plan-time GEOM advisory FAIL 225 -> 225, new 0, worse 0. 0 cycles, no RTL. No `asbuilt` key, so bind.py does not apply.

## Part 20 (ot_pdie_serdes conservative form; HBM-REFORM-B/B2, OWNER 11-03 two strikes)

- **ot_pdie_serdes** (276k + kept kp4_inv 128.8k) becomes three plan designs inside its slot: `ot_pdie_serdes_tx` 285.12x155.52 (72.2k cells), `ot_pdie_serdes_rx` 302.4x345.6 (145.2k, 2 SRAM), and the signed `ot_s81_kp4_dchn` 276.48x138.24, pins = the signed table. Outline 600.048x600.48 -> 596.16x596.16, origin kept (8.64 lattice). Rows: `u_lk_*` in NW_io, NE_io, q_spb0 and siblings, 5 slots.
- **Cycles**: `reform_1103/cycles/pdie.tsv`: pma_rx -> rx +2 (ddly DD 55 -> 57), uncorrectable and e_flt -> st[0] +2, pma_tx, tx, st[1] 0.
- **Clock (COORD ruling 11-04 23:2x)**: the recovered clock enters rx on `rck_clk`; one SDC clock on `clk` and `rck_clk`, so the rate matcher is timed as synchronous. The real CDC is proved in simulation only (plesiochronous bench modes). The die-level PMA clock note stays open.
- **Bench**: `results/die_hbm_1104/reform_b/split_p20/run_eq.sh`, kit face shells modelled by `ot_hbm_face_reg`.

## Part 21 (ot_hbm_idx_selector_static_sel conservative form; HBM-REFORM-B3, OWNER 11-03 two strikes)

- **ot_hbm_idx_selector_static_sel** (322.7k, STRUCT=0, ws -46931) becomes the proven s3 cluster, wires-only: `ot_hidx_s3_ctl` 43.2x34.56 + 4 x `ot_hidx_s3_q` 259.2x216 (3 SRAMs each, macros 12 as before), in a 596.16x449.28 slot (was 600.048x450.36, origin kept; mk_split needs the 8.64 lattice). The landed parent of claude/hbm-idx-sel-c14-1021 is not used: the kit face shells are the registered crossings.
- **Clocks**: u_ctl on `clk_ctl`, u_q<q> on `clk_q[q]`. `clk_mem[11:0]` stays a master port with no load; each SRAM runs on its quadrant clock.
- **Cycles**: `reform_1103/cycles/selector.tsv`; schedule table sel_in 7, sel_in_line 3, sel_out 2, sel_core_out 2, sel_scan_drain 2, sel_choose_rt 6. The compiler on main has none of the s3 keys; the TOK lane adds the table.
- **Bench**: `results/die_hbm_1104/reform_b/split_p21/run_eq.sh`: tb_selector_s3 full-shape checks on the composition with kit face shells modelled by `ot_hbm_face_reg`.

## Part 24 (ot_hgi_sfu_core_split3__ctl smaller tile; HBM-REFORM-B3)

- **ot_hgi_sfu_core_split3__ctl** (74.5k logic, 32k FF, no macros, 8.5% util, TT -148 from spread) goes from 669.6x626.4 to 427.68x453.6 by mk_reform.py (centre kept, pins repacked, pin pitch 0.096, W edge 3819 pins). RTL unchanged, 0 cycles.
- **Wrapper**: recipes_b2 entry ot_hgi_sfu_core_split3__ctl pins physical/die_plan/hbm_arch_cores/wrappers/oneclk for this pin table only.
- **Scripts**: results/die_hbm_1104/reform_b/split_p24/ (ov_p24.json, mk_p24.py).



## Part 17 (lanes canon and lanes_plain -> 4 x lane; HBM-REFORM-A, HBM-REFORM-A2)

- **lanes canon**, 14 rows, 760.32x725.76 slot: 4 x existing ot_hbm_su_pg_lane1_core, 190.08x311.04 strip, 0 cycles. Same cut as part 6 on lanes8_11.
- **lanes_plain**, 8 rows, 440.64x457.92 slot: 4 x new ot_hbm_su_pg_lane1p_core, 216x224.64, 2 x 2, 0 cycles. Same RTL text as lane1; the plain slot cannot hold 2 x 2 lane1. Macros 2 x 3; one clock pin.
- **Bench**: results/die_hbm_1104/reform_a/part17, lockstep on both rows, mutant 0 PASS, 3 mutants FAIL. Straps: parent_id_straps lane0_lane_id = {lane_lane_id, k}.
- **Checks** against part 14: G0 compare new 0, gone 0. Plan-time GEOM advisory FAIL 225 -> 225, new 0. Clock_tap_sinks and clock_reach move both ways (9 worse, 13 better), see geom/geom_diff_d44v_p14_p17.txt.

- **Part 17 rework (HBM-REFORM-A3, 11-05):** lanes_plain tile 216x224.64 (2x2, W/E macro bands 3.5, mid 10.8) stopped at GRT-0116 on the first form: 40141 overflow, M3 33006, CTS 72% with macros. Macro pins are W/E on M4 and need a band per column edge. New tile 440.64x112.32, 4 stacked in the 440.64x457.92 slot; 3 x 2 macros, bands 24.6/49.2/49.2/24.4, top cell strip 20.4. W/E faces M4 only, so ld_c[840:255] moved E to W: W 1136, E 880. 0 added cycles, same RTL and lockstep. G0 new 0, gone 0. GEOM advisory 225 -> 225, new 0.

- **Part 18 (HBM-REFORM-A2/A3, 11-05):** lane_exp canon (60) -> lane_exp_x + sfu_s, lane_exp0_id (4) -> lane_full_x + sfu_s, row grows 414.72 -> 440.64 on local E. S chain moved to a shared SFU core, seam 101 bits with face flops. SFU_EXP, SFU_SIGM, SFU_SILU +4 edges, S-chain fault +4, others 0. Macros 2 x 3, W/E bands 30.2, 60.7, 30.4. Bench eq_x: PASS and 5 mutants FAIL on both rows. G0 new 0, gone 0. GEOM advisory 225 -> 225, new 0.

- **Part 19 (HBM-REFORM-A3, 11-05):** tkm tile (both id forms) -> 2 x ot_hgi_coll_tkm_tp192_htile_core stacked Y (319.68x172.8 each), chain PTILE 32, NT 64. TKM op +448 edges, down +5, clr_o +3, conv_o +2, up_out +2. Root re-extracted on PTILE 32 with the same _x ports (recipe file replaced). Corridor clock buffers now drive __ha + __hb. G0: 15 new clock lines, advisory: direct leg 410-462 um > reach 405 (repeater segments pass), geometry of the split, not of the logic. GEOM 225 -> 225, new 0. EQ: reduced chain KMAX 128 bench, positive PASS, 3 mutants FAIL; full chain not run.


## Part 25 (ot_hbm_svc_wb_kport_q split, 4 instances; HBM-REFORM-B4)

- **ot_hbm_svc_wb_kport_q** (flat 374k), slot 475.2x475.2 grows to 527.04x544.32, u_wbk_Q__q1 origin y -8.64 (gaps at q1: E 17.28, N 8.64, S 21.6). It becomes one switch tile **ot_wbq_sw** 86.4x544.32 (160k cells at kit synth, over the 150k target) and four root tiles **ot_wbq_root** 432x129.6 (57k cells, 2 lane groups each, 8 128x256 payload macros), all with registered faces, one clock.
- **Form**: root pushes sectors with a credit of 4 per group; sw queues per group and switches onto 16 K ports at most 8 per edge (flat 16). Order on K changes; each PC still gets its sectors in stream order per group.
- **Cycles**: physical/die_plan/hbm/reform_1103/cycles/wb_kport.tsv. Scripts results/die_hbm_1104/reform_b/split_p25/ (mk_p25.py pre, then mk_split.py).

Parts 27, 29 (HBM-FORM-SPLIT, 11-05): ot_hgi_sfu_core_split3__opstore_b -> 2 x opsb_group + opsb_output; opstore_a -> opsa_group0 + opsa_group1 + opsa_rest, slot 760.32 x 552.96 (origin kept, grows die north); ot_hgi_coll_gq_issue -> gqi_issue + 2 x gq_aq_tile, slot 328.32 x 233.28 (origin kept, grows die east). Util 0.45, registered faces. Added cycles: opstore_a engine fault +2 from operand groups 0,1 only; everything else 0. Benches and replay: results/die_hbm_1105/form_split.


Part 26 (HBM-REFORM-B5): ot_hbm_svc_sm_group_rel_id -> ot_svgr_top + ot_svgr_own + 2 x ot_svgr_bk inside the old slot, registered faces. SM command, packet and GO slots unchanged (bench: 29/29 exact, results bit-equal). Seam edges in results/die_hbm_1104/reform_b/split_p26/cycles/rel_id_split.tsv. 298 station ends moved to the tile pins, register counts unchanged. ot_wbq_root macros moved 15.12 um off the W seam (DPL-0033 on the k3 build).

Part 33 (HBM-REFORM-B5): ot_hfd_coll_q2n2_body_core -> ot_q2nf_rest + ot_q2nf_qout, 0 added data cycles, select/unavailable faults +2. results/die_hbm_1104/reform_b/split_p33/.

Part 28 (HBM-FORM-SPLIT-2, 11-05): ot_hfd_coll_q3_body_core -> ot_hfd_coll_q3_body_ctl + 4 x ot_hfd_coll_q3_qcol4, same slot, util 0.45, registered faces, 0 added cycles. Replay results/die_hbm_1105/form_split/replay_p28.sh.

- **Part 16 (DIE-HBM-69, from DIE-HBM-66/68, 11-05):** tailx_sk_step0 + tailx_sk_steady -> ot_hbm_hc_root_static__tailx_sk_fsr; tailx_rest -> tailx_rest_fsr, forms v6bc7f2 and v4f4566. Row Sinkhorn with a free-running stage shift, no enable fan-out. Tail launch -> result_v 592 -> 1054 edges [MEASURED, lockstep bench results/die_hbm_1105/sk_fsr, value FSR_EQ 60/60]; every pin in reform_1103/cycles/tailx_rest_fsr.tsv. Reset contract 64 cycles for both fsr tops. **Checks** against main's plan with parts 17-19: 43 stations dropped; G0 compare new 0, gone 0; plan-time GEOM advisory FAIL 225 -> 225, new 0 (geom/geom_diff_d44v_p24_p16.txt). Replay: results/die_hbm_1105/sk_fsr/mk_p16.py. Token calendars: +462 on these pins, next token lane.

Event gqmx (HBM-GAPS-2, COORD 11-05 12:00 ruling B): q_hub_nw u_hcollgl_Q__q1 (ot_hgi_coll_gq_land) takes the o_MX pin table placed MX, as q_hub_ne q1 already does; the o_R0 table (view bfcd846691ef, its DRT stuck in the NW corner) leaves the plan. Signed view ac72b8c34f86 (gqac2) now serves both q1 rows. Same module, origin, outline and 3880 pin names; clock entry at the core centre is unchanged under MX. In core frame W/E pins are identical in both tables, so under MX the q_hub_nw W/E pin order flips in y (as in q_hub_ne). G0 new 0 gone 0; plan-time GEOM advisory 225 -> 225, new 0 (geom/geom_diff_d44v_gqmx.txt). Replay: results/die_hbm_1105/gq_land_mx/run_gqmx.sh.

Event ev74 (DIE-HBM-74/75, COORD 11-05 12:38/12:40/12:42/12:51): idx score hcol_h0 ra/rb split pieces +102.816 um tall (106.272x290.304), moved as rigid ra|rb row units on the 8.64 lattice (142 hard cores pushed by collision, 10 units grow down; q_b000/001/010/011 bank128 pair gaps compacted); opsb_output 760.32x280.8 (macro rows with 21.6-um y gaps; q_b113 opsb_group g1 -56.16); topk_link_static 650.16x535.68 (+35.64, rows 3 x 11.88 gaps; root rootctl + argmax +34.56); q_sm0 L29_i +69.168 on the S face and q_su01 L29x1 out window with it; xcal_rel_t rst_n -> M5 (121.032, 224.544) = signed 6_final.def (all 507 pins = signed kit). Station cells under moved cores re-sited by tools/die_plan/ft_nudge.py, then tools/die_plan/ft_reach_fix.py re-sites the S1 bits nudged past 405 um (1122 bits). Replay results/die_hbm_1105/ev74/run_ev74.sh. G0 vs base: new 5 = q_b011 L15x1 S0->S1 473 um (167 bits the band has no free site for; 2 hops + 2 stations rows, NW/NE) + NW_b101 horizontal cut 5750 ratio 0.84 (taller cores now span the old row gap), advisory; GEOM FAIL 225 -> 225, new 0 (g0/g0_diff_d44v_ev74.txt, geom/geom_diff_d44v_ev74.txt). 26 types change. topk_store has no slot in d44v (part-30 split piece), its +35.64 stays kit-local.

Event ev74f (DIE-HBM-75, follow-on to ev74; COORD 11-05 14:01, 15:0x, 14:52, 16:0x): HBM-BIND-10 C-form plan delta (results/hbm_bind_10_1105/delta_714_k13f.json.gz: C row form + B0/b0l/pair leaf + hub<->sm endpoint reuse + spb0->root) applied on the ev74 d44v; 36 base-differs, all benign (34 ev74 bit-site edits on slots C deletes, q_sm0 L29_i same +69.168, q_su01(+pv1) L29x1 deleted by C; ev74f_apply.log). q_b011 L15x1 (both type copies) +1 station by tools/die_plan/ft_add_station.py (new S1 per bit on free legal sites, worst hop 319.7 um, 0 failed) = +1 pin cycle: LAT_L15 / LAT_L15M 6 -> 7 (TOK-LEDGER HBM-27, 0.000%). C-form stations that ev74-moved cores now cover are re-sited by tools/die_plan/ft_nudge.py, whose explicit-regs_um mode (new, default-on) keeps a threaded chain's route and moves only station centres inside a core (147 slots; 18 slots still have a stage-0 bit band over a core, see the ev74f READY). l1r5: ot_hbm_su_pg_lane1_core MLAT 4 -> 5 (RTL commit 308663537a8, recipes_b2 files_at pinned to it). Replay results/die_hbm_1105/ev74/run_ev74f.sh. G0 vs ev74: new 23 = the C form's known "slot in_face == out_face" schema rows (HBM-BIND-10 README), gone 26 (incl. the ev74 L15x1 reach rows, NW_b101 cut 0.84, L700/L701 reach, 15 root tkm clock legs). GEOM FAIL 225 -> 233 (C alone 229; ft_nudge adds 4 r2r: q_b000 415, q_b010__physical_v1 411, q_b103 429, q_hub_nw 491 um), advisory. The part-28 EMIT bind fix is an as-built manifest (asbuilt_t13: sub_core_leaf keyed by the plan parent); it lives with the HBM-BIND as-built lineage outside the repo (its inputs/ are not in git), see the ev74f READY.

Event ev75 (DIE-HBM-75, COORD 17:3x x2: merged pin cycles into the latency keys; on ev74f + main 97a021f9a9d): no plan geometry or lane change. corelat/cycles_pincycles_1105.tsv (new) declares the merged core pin cycles: HBM-31 ot_hidx_s3_q selected_v_o/selected_line_o +1 (I166), HBM-33 ot_hgi_sfu_opsb_output sr_d/sr_rv/flt +2 (I166), HBM-28 Part 27 ot_hgi_sfu_opsa_group0/1 rd_q and ot_hgi_sfu_opsb_group rd/flt +2 (I158 B10 form), HBM-29 ot_pdie_serdes_tx pma_tx +1 (I154 txla), HBM-26 ot_hbm_su_pg_lane1_core multiply +1 (l1r5 MLAT 5, ev74f). ext/crossing_latency.json.gz regenerated with results/die_hbm_1103/reform/ext_census.py --core-lat corelat/*.tsv --latency-changes latency_changes_d44v.json (now also ev74f L15/L15m 6->7) on the ev74f plan: 21262 crossings (422 die lanes, 20744 type internal, 96 core internal), die lane cycles 6627, added RTL cycles 963 (the previous table was from the d44v7-era plan: 357 die lanes, lane ids before the C form). compiler_core_delta.json S2 extra: SFU +4 (HBM-28 + HBM-33 in series), IDX +2 (HBM-31 + HBM-34 op6 -> op2/op7 spacing 7 -> 8), SU +4 (HBM-26 FO rule), COLL_XING +1 (HBM-29); SM +7 and HC opx unchanged. HBM-30 (q3 writer_kq +1) is listed as pending: it folds after its form RTL merges.

Event ev76 (DIE-HBM-75, COORD 11-05 17:20 (4) / 17:4x / 17:5x): (1) dma_m6c conservative form: ot_hgi_dma_back_static_vp4_banks_cp 300.456x275.4 -> 372.6x275.4 (+72.144 um local E, util <= 0.45; HBM-FORM-TIMING-6 17:29 ESTIMATE), 4 instances (u_hb_dbk_Q__q0 R0 / q1 MY in q_hub_nw and q_hub_ne), origins kept. The pin table has no E-face pin, so the new pins file (..._372.6x275.4__ev76_cons.json) is the old table byte for byte; q1 (MY) pins and its centre clock tap move +72.144 parent-E (clock.taps x 7342.032 -> 7414.176). core_macros: outline only, same 10 macros. (2) 123 internal-station registers in the four new strips re-sited (contiguous strip runs between kept neighbours, tools/die_plan/ft_nudge.nudge_explicit, wider search / neighbour moves only when a hop would pass 405 um): worst touched hop 403.9 um, no hop newly over 405; ft slot stations by ft_nudge.py (22 slots, 18 as before). (3) q_hub_nw C25c boot packet bank u_host_boot_hop12 channel moved S of q1: 7490.88,682.56-7508.16,699.84. (4) pcol_l pin event: ot_hbm_su_pcol_l (12 instances) -> cores/ot_hbm_su_pcol_l__257.04x423.36__p26_signed.json = the signed i3 kit's plan_pins.json (part-26 lane-only table, 545/565 pins +101.52 um core-x, same outline; re-signed on tag i, routed LEC EQ). Replay results/die_hbm_1105/ev76/run_ev76.sh (ledgers there). Plan-time G0 vs base: 23 = 23 (the known C-form schema rows), new 0 / gone 0; GEOM FAIL 234 -> 234, NEW 0 / WORSE 0 (advisory).

Event part 37 (DIE-HBM-81, COORD 11-06 11:00 (2)): ot_pdie_serdes_rx (5 instances) -> HBM-GAPS-7 RX BM3 vB form in the same slot: residual ot_pdie_serdes_rx_bm3_rest 197.856x345.6 (E) + 3 x ot_pdie_serdes_rx_bm_native 95.904x106.56 (W column); Model-A tables; PIN CYCLES rx/st[0] +5 (corelat/cycles_rxbm3_1106.tsv); part37_event.json; replay results/die_hbm_1106/rx_bm3_p37.

Event part 39 (DIE-HBM-81 11-06, G0C class C): q_hub_nw/q_hub_ne u_svg_Q0/Q1 split cores (MX) track_offset y -0.024 -> 0.0 so their M4 pins sit on the type M4 track; clock tap points follow (+0.024); part39_event.json.
- part 41 (HBM-FORM-SPLIT-13-OPSB 11-06): ot_hgi_sfu_opsb_output banks -> 16 x ot_sram_1r1w_2048x32_m8_r0c0_g32 4x4 (core_macros + recipe OT_OPSB_N32; old form recipe __row256); die_plan/pins/conns/clock/reset unchanged; G0 new 0 gone 0, GEOM 234 -> 234 NEW 0 WORSE 0; results/die_hbm_1106/opsb_n32 (replay_p41.sh, BENCH.txt, p41_opsb_output.png).

Event part 40 (DIE-HBM-82 11-06, COORD 13:37 RULINGS (1) / DIE-HBM-81 13:37): ot_hfd_coll_q3_edge_arg (q_hub_nw u_hb_coll_Q_edge__q0__arg) takes the HBM-GAPS-8 same-slot re-pin table (cores/ot_hfd_coll_q3_edge_arg__276.48x43.2__d44v_repin_hg8.json, sha 9ae65807400d, byte for byte): S-face M5 pins spread in x only; outline, origin, E pins and clock entry unchanged; no sidecar change. PIN CYCLES fault +1 for the HBM-GAPS-9 __fpipe2 form (corelat/cycles_q3arg_fpipe_1106.tsv); part40_event.json; replay results/die_hbm_1106/q3arg_repin_p40.

Event part 42 (DIE-HBM-81 11-06 12:06 (b), HBM-FORM-SPLIT-13-FULLX): ot_hbm_su_pg_lane_full_x_core 319.68x207.36 -> 354.24x207.36 (+34.56 um local E; conservative form, stdcell util 0.52 -> ~0.44), 4 instances u_su_Q{0,1}_lane_exp0__l (q_su00/q_su00__physical_v1 R0, q_su10/q_su10__physical_v1 MX), origins kept; no E-face pin, so the new pins file (..._354.24x207.36__d44v_p42.json) is the oneclk table byte for byte; partner u_su_Q{0,1}_lane_exp0__s (ot_hbm_su_pg_sfu_s_core) x +34.56 (pure shift, seam pins stay aligned; q_su10 street to exp2__l 8.64) with its clock tap; core_macros outline; internal station regs in the new strips re-sited (ft_nudge.nudge_explicit, ev76 method) + ft_nudge/ft_reach_fix. PIN CYCLES: none in the plan event. G0 base vs new gone 0 new 0; plan-time GEOM NEW 0 WORSE 0; part42_event.json; replay results/die_hbm_1106/fullx_grow_p42.

Event part 43 (DIE-HBM-82-G0C 11-06, G0C class F street_die_leg): lane stations off the hard cores with the least move: bit-site slots get a real bit site of the stage (smallest worst hop) as regs_um (no cell moves), q_b102 N-edge keep-out stations nudged (ft_nudge.nudge_explicit); station counts unchanged, 0 pin cycles; normal-slot S0 under an abutting core left for a window re-pin; part43_event.json.
Event part 44 (DIE-HBM-82-B128 11-06, plan-owner approved DIE-HBM-82): ot_hgi_sfu_split3_lane_core_fr (32 instances) pin tables __d44v_split.json and __d44v_split__vi24.json restored byte for byte to their pre-p35 state (510f347b9f^): sfu_clk M5 (60.888, 172.8) -> (60.6, 172.8), map_clk unchanged at 60.504. p35 moved only the tables; clock_entries.json still spreads the merged map_clk/sfu_clk entry to 60.504/60.6 (no clock_pin_sites_um), so no --clock-pin-entry kit could match the p35 table. 60.6 is the signed fr DB geometry (DRC 0, routed LEC EQUIVALENT). Pin-only, PIN CYCLES 0; part44_fr_clkpin_event.json.

Event part 45 (DIE-HBM-82 11-06, p35 clock-site class): clock_entries.json gets clock_pin_sites_um = the current pin-table clock pin positions for kshare v8e478a / v700685, xload ctlx, svgr_bk, wbq_root, wbq_sw (part 35 moved one clock pin per table but not the entries, so --clock-pin-entry kits missed their tables); entry xy, tables and die_plan unchanged; no pin cycles; part45_event.json; replay results/die_hbm_1106/clkpin_sites_p45.

Event part 46 (DIE-HBM-82 11-06, plan-owner approved): ot_hgi_sm_xload_cl2_ctlx pin table back to pre-p35 (clk_cal 194.808 -> 194.52, the signed DB's site, as part 44 did for fr); its part-45 clock_pin_sites_um follow (clk 194.424, clk_cal 194.52); no pin cycles; part46_event.json; replay results/die_hbm_1106/ctlx_clkpin_p46.

Event part 47 (DIE-HBM-82-G0C 11-06, G0C class A ft reach): one ft_s0_resite.py pass over the 57 types with a 'stations' row: 429 slots re-sited, 129 with added stations (+166 station cycles), 99 lanes' latency.lanes changed (PIN CYCLES, ledger_p47.json), 182 slots kept (no chain fits); part47_event.json.

Event part 49 (DIE-HBM-82-EP6 11-06, plan-owner approved DIE-HBM-82): ot_wbq_sw (4 instances) 86.4 -> 155.52 x 544.32, grown west (W face moves 69.12 west, other pins keep their absolute site; table cores/ot_wbq_sw__155.52x544.32__d44v_split.json), aq_tree13 u_xl_Q_aqhi 51.84 west in q_hub_nw/ne, station chains touched by the move re-planned by station_resite.py (same counts) + ft_nudge.py; plan-time G0/G0C NEW 0; part49_event.json; replay results/die_hbm_1106/wbq_swmv/run_p49.sh.

Part 38 (HBM-FORM-TIMING-11, numbered 38 after DIE-HBM-81 BM3 took part 37 (COORD 12:4x), regenerated on main d306f1c305 (after parts 39-46) by HBM-FORM-TIMING-13; COORD 11-06 10:2x approval + 11:21 (2) "TIMING-11 WRITES IT NOW", one event): split3__ctl rest + pipe. u_sfucore_Q_ctl (ot_hgi_sfu_core_split3__ctl, 427.68x453.6 MY) becomes two hard cores in q_b113 and q_b113__physical_v1: u_sfucore_Q_ctl__rest = ot_hgi_sfu_split3_ctl_rest_1c in the SAME slot (origin, orient, track offset, all 11,813 pin sites kept) + 560 seam pins on its local E (die W) face; u_sfucore_Q_ctl__pipe = ot_hgi_sfu_split3_ctl_pipe_1c in a NEW 172.8x151.2 R0 slot W of it (die x 328.32-501.12, y 1019.52-1170.72, 8.544 street), seam pins at the same die y (straight hops), resets above, centre clock entry. The cut is HBM-FORM-TIMING-10 I205 (21,816 delay-line flops into the pipe, seam = 280 FF->FF bits each way, 0 cycles); the pipe keeps its own copy of the ctl 2-flop reset sync + relay, so no reset crosses the seam. Same related clock: rest keeps the ctl tap (renamed), pipe gets its own centre tap at the same insertion target. core_conns: every core:u_sfucore_Q_ctl -> __rest (24 refs per type), seam rows rest<->pipe; 48 station refs per type repointed to __rest; no station register in the new slot. RTL rtl/hbm_accel/cores_split/ot_hgi_sfu_core_split3/ot_hgi_sfu_split3_ctl_{rest_1c,pipe_1c,split}.sv (generated by results/die_hbm_1106/ctlsplit_p37/gen_p37.py); recipes_b2 + reset_contract entries for both. Proof: iverilog lock-step old plan module vs part-38 plan module, 800 cycles with reset pulses, 0 errors; mutants seam-swap and pipe-reset-off FAIL (BENCH.txt). Replay results/die_hbm_1106/ctlsplit_p37/replay_p37.sh; render p37_q_b113.png viewed. Plan-time G0 vs base: findings 1045 = 1045 on this base, new 0 / gone 0; GEOM FAIL 234 -> 234, NEW 0 / WORSE 0 (advisory). Views ot_hgi_sfu_split3_ctl_rest_1c@f057777f78e4, ot_hgi_sfu_split3_ctl_pipe_1c@3fff874b48c2.

Event part 50 (DIE-HBM-82 11-06, clock-site scan): clock_entries.json gets clock_pin_sites_um = the plan clock pin points for static_cfg_collar_idx256r and pdie_serdes_rx_bm3_rest (table points) and idx_qctl_static (centre entry; new table cores/ot_hbm_idx_qctl_static__194.832x82.08__d44v_centry_p50.json with the two clock pins at the entry, 4 instances repointed, lands the COORD 11-03 centre-entry pin event); --clock-pin-entry kits of these cores matched neither; no pin cycles; part50_event.json; replay results/die_hbm_1106/clkpin_sites_p50.

Event part 51 (DIE-HBM-82-EP6, plan-owner approved DIE-HBM-82 11-06): ot_wbq_root (16 instances, wiring-bound at GRT) -> its two lane groups in the same 432x129.6 slot: ot_wbq_root_g0 / ot_wbq_root_g1 216x129.6 (4 x 128x256 one-mask-pin macros each, own group pick + credit, fill/copy control replicated; no seam, 0 pin cycles, corelat/cycles_wbq_g2_1106.tsv); glue ot_wbq_root_g2; yosys induction EQ + lock-step in results/die_hbm_1106/wbq_g2; part51_event.json.

Event part 52 (DIE-HBM-82-SPB 11-06, plan-owner approved DIE-HBM-82): q_spb2 N->N turnaround ft slots L1278x3 / L1280x6 re-sited from the N-edge strip above u_xc_Q2 to nested U corridors below the xcal row with explicit per-bit station sites (bands y 1065-1175 / 995-1055, track use 0.49 / 0.46, hops <= 363 um); station counts unchanged, 0 pin cycles; plan-time G0/G0C NEW 0; GRT probe 0 overflow; part52_event.json, part52_ft_uturn_ledger.json; replay results/die_hbm_1106/spb2_uturn/run_p52.sh.

Event part 54 (DIE-HBM-82-SPB 11-06, plan-owner approved DIE-HBM-82): lane L3012 (27 b, su21 -> x1..x7 -> hub) pin windows widened to max(old, 3.5) um about the same centre on both faces of all 8 abutted ports (16 windows); fix-only, 0 pin cycles; plan-time G0/G0C 971 = 971 errors, no new error; part54_event.json, part54_l3012_window_ledger.json; replay results/die_hbm_1106/spb2_uturn/run_p54.sh.

Event part 53 (DIE-HBM-82-SVGR 11-06, plan-owner approved DIE-HBM-82 (A)): ot_svgr_bk (16 instances) 259.2 -> 302.4 x 207.36, +43.2 on the core-local E (FIFO) face (E-face pins +43.2, other pins and macros keep their core-frame site; table cores/ot_svgr_bk__302.4x207.36__d44v_p53.json), streets to ot_svgr_top / ot_svgr_own 17.28, no neighbour moves; station chains touched re-planned (station_resite.py + ft_nudge.py); plan-time G0/G0C NEW 0; part53_event.json; replay results/die_hbm_1106/svgr_bk_grow_p53/run_p53.sh.

Event part 60 (DIE-HBM-86 11-07, COORD 08:41 (1) injector (B)): ot_hgi_coll_inj_idx_join_rg (4 instances) table drops 31 read-nothing pins, inj_rd_r1[1] and idx_tx_h_r1[131:102] (4761 -> 4730; new table ...__centry__r1drop.json), matching inj_e2 as built. Region 1 reads the header only through gs[a*3+:3]; tx_h and rq_rd feed g_chk, generated only for r==0. Read bits kept. The parent passes the same wires to idx_tx_h and inj_rd, which keep all bits, so only the r1 branch goes: no station, ft slot or bus width changes. idx_tx_h_r1 3..32, 36..65, 69..98 and inj_rd_r1[0] are also unread and stay, the built kit has them. 0 pin cycles, sites unmoved. part60_event.json; replay results/die_hbm_1106/rf86_p60/mk_p60.py.

Event part 61 (DIE-HBM-86 11-07, COORD 09:20 svgr_bk (A)): ot_svgr_bk (16 instances) back to 259.2 x 207.36, the outline of signed DB svgrbk_e2. Part 53 undone for this core: origins, outlines, taps return to pre-part-53 values, core_macros.json to its pre-part-53 bytes; part 53 station chain sites stay, since they clear the larger outline and undoing them brings back L40_i hops > 405 um. Table cores/ot_svgr_bk__259.2x207.36__d44v_p61.json = pre-p35 bytes, sha 8ba152814ecb, the table the kit was generated from: stream_clk M5 21.72 (p35 had 22.008), clock_pin_sites_um follows on 16 rows. Pin cycles: corelat/cycles_svgr_bk_vB_1107.tsv records +1 on complete, complete_bank, bfault, carried by the signed VARIANT 1 RTL. svgr_own RF3 (recipe, ifdef, corelat row) stays: not in the die_plan diff. Replay results/die_hbm_1106/rf86_p61/mk_p61.py; part61_event.json.

Event istadrop_1107 (DIE-HBM-90-ISTA 11-07, under DIE-HBM-90; class fix for the DIE-HBM-89-HBMBIND READY class (a)): 1255 type internal_stations entries on 164 buses the types no longer have are dropped in 25 types (NE_io 8, NW_io 72, q_b110(+pv1) 53+53, q_b113(+pv1) 12+12, q_hub_ne 311, q_hub_nw 254, q_su00..q_su31 (+pv1) all of theirs, root 70). The die_hbm_1029 lane re-route events (hbm22/23/28 replan_event*.py) removed the lanes, ports and endpoint buses and kept these stations by name; kit_istations.py stopped the kits on them ("internal station on unknown bus"). Every dropped bus is absent from the type's buses and ft slot ports, from every die port on a partition of the type, and from the bound RTL of record (bind14, strict bind 0 errors); tools/die_plan/drop_dead_istations.py fails closed otherwise. Not remapped: the current lanes are priced without them (e.g. L5032 cycles 2, stations 0) and the bound RTL has no pad stage for them. Live entries, lanes, latency, pins, outlines, clock, reset and core_conns.json unchanged; PIN CYCLES 0. istadrop_1107_event.json (bound RTL sha256 per type), istadrop_1107_ledger.json.

Event phypgfit_1107 (DIE-HBM-90-TSTRAP 11-07, under DIE-HBM-90; class fix (j) of the DIE-HBM-90-ISTA READY, on top of istadrop_1107): the 5 die.pg.domains rects are fitted to their SerDes partition. Each rect was its IO window / bump field grown by one diagonal bump pitch (45*sqrt(2) = 63.64 um); where the window sits on the partition edge that halo covered core-VDD neighbours without a PHY macro (phy_NW_io_u_lk_N0 over NW_su21 + NW_b013, phy_NE_io_u_lk_N2 over NE_su21 + NE_b013, phy_vsN0_u_lk_S1 over NW_sm3), so gen_phys stopped q_su21(+pv1) 'PG domain ... holds no macro'; inside its own type it cut the endpoint core u_ep_* placed 38.64 um above the window (NW_io/NE_io/q_spb0(+pv1)/vsN0 'macro u_ep_* straddles PG domain'). tools/die_plan/fit_phy_pg_domains.py clips each rect to the partition of its IO window and cuts it at the edge of a placed block it cuts, keeping every bump rect, window, exclude and esd box and the PHY sub-cores inside (fails closed otherwise); die_io.check_pg_domains already states this rule but only runs it with phy_macro_um. New rects: NW_io [0, 6065.28, 648, 7153.92], NE_io [27751.68, 6065.28, 28399.68, 7153.92], vsN0 [13357.44, 0, 14055.688, 1088.64], NW_spb0 / NE_spb0 top 1113.64 -> 1088.64. Only die.pg.domains[].rect_um and the note change; bumps, windows, grids, nets, partitions, types, lanes, latency unchanged; PIN CYCLES 0. phypgfit_1107_event.json, phypgfit_1107_ledger.json.

Event tname_1107 (DIE-HBM-90-TNAME 11-07, under DIE-HBM-90; naming class (i) of the DIE-HBM-90-ISTA READY): root hard core u_mu_fused_program (ot_hnx_fused_host_program) declares physical_inst u_mu_fused_programme, physical_master ot_hnx_fused_host_program. bind.py kit-rtl stopped root with core clock clk_c12: expected one bound leaf u_mu_fused_program, got 0: the as-built RTL of record (bind inputs t11_top.sv) and the bind map (t5_map.json) name the instance u_mu_fused_programme, so the bound leaf is u_u_mu_fused_programme; the C25b plan rows had the short name. physical_inst is the plan's field for this (DIE-QC-69): kit-rtl, core_tap_rows and kit placement read it, while the logical inst, contents[], the clock tap u_mu_fused_program.clk and core_conns.json stay, so the native bind receipt of every type still matches bind14 (a tap rename would change kit_topology's die-wide reset digest and force a new die bind). tools/die_plan/declare_physical_inst.py fails closed unless the bound RTL has exactly one leaf of the new name with the row's module and none of the old. PIN CYCLES 0, no logic change. tname_1107_event.json (bound RTL sha256), tname_1107_ledger.json.
