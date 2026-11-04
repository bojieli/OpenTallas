# HBM plan event d44v = the HBM RE-FORM batch plan event, parts 1-5 (DIE-HBM-61/PLAN, 2026-11-03)

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

## Checks (epyc2 die-hbm-60-plan, same tools for every plan: main 08542fa9d7d + d44v tools)

- **G0+G0C** (`tools/die_plan/check.py --completeness`):

  | plan | ERROR | pending-view |
  |---|---|---|
  | d44t | 74 | 128 |
  | d44v part 1 | 51 | 128 |
  | d44v part 2 | 24 | 128 |
  | d44v part 3 | 24 | 128 |
  | d44v part 4 | 24 | 128 |
  | **d44v part 5** | **24** | 128 |

  - Against part 1, 27 are gone and **0 are new**.
  - Against d44t, the 3 "new" are pre-existing items under a new message:
    - u_vmb_Q6/Q7_mu1 dq core_faces: mu1s3 282 -> 281 pins.
    - L701 reach: hop index shift, still 392 um.
  - Part 3 against part 2: gone 0, **new 0**, and the warnings stay at 1148 = 1148.
  - Part 4 against part 3: errors gone 0, new 0. Warnings go from 1148 to 1146: the 2 UNKNOWN-macro clock_entry_macro WARNs are gone.
  - Part 5 against part 4: errors gone 0, new 0; warnings stay at 1146 = 1146.
  - Diffs: g0/g0_diff_d44t_d44v.txt, g0/g0_diff_d44v_p1_p2.txt, g0/g0_diff_d44v_p2_p3.txt, g0/g0_diff_d44v_p3_p4.txt and g0/g0_diff_d44v_p4_p5.txt.
- **Plan-time GEOM** (`plan_geom.py`, 74 types): **new FAIL = 0**, and the FAIL count is 225 -> 225. All of these
  are advisory, and every type already fails clock_tap_sinks or clock_reach.
  - Values worse on rules that already fail (clock_tap_sinks):
    - q_su31: 7073 -> 13386 (bays: the L5/L34/L6b stations sit on the q_su31 tap);
    - q_su11pv1: 5654 -> 6403;
    - q_su01: 8890 -> 9194;
    - q_su20: +1.
  - Part 3 against part 2, part 4 against part 3 and part 5 against part 4: identical (new 0, worse 0, better 0).
  - Diff: geom/geom_diff_d44t_d44v.txt.
- **Count**: 84 -> 84 designs, and the 6 signed cores keep their design key (SAME). See g0/count_check.txt.
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
  - (c) 21,132 crossings; plan cycles +44 over d44t; RTL/SPLIT cycles +16 (split3 4 ports x 4).
