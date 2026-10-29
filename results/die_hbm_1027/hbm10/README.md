# DIE-HBM-10 (HBM die owner, successor of DIE-HBM-9), 2026-10-28

Everything here is an ESTIMATE (12.14b). Tool runs are CHECKED. Model numbers are UNCHECKED, and CA numbers on inverter
trees stay UNCHECKED-model until CLK-INV-CAL-1 lands.

## (1) Collect: C21 G0/G0C, C20j baseline, trial1 clock-only GRT (CHECKED tool runs)
The runs are on intel2 under `/srv/opentallas-scratch2/claude/die-hbm-9/`. All three use the same tools snapshot
(`mainsnap`), and each took about 48 min.

| plan | G0 | G0C ERROR count | G0C by check |
|---|---|---|---|
| C20j baseline | -- | 16 | core_faces 12, street_reach 4 |
| C21 | FAIL 19 (all geometry) | 80 | street_die_leg 41, geometry 19, core_faces 12, complete 4, street_reach 4 |

- The diff is 64 new errors and 0 gone. All 64 come from C21's own changes:
  - **street_die_leg 41 + geometry 19:** the 66 idx 2nd-quarter pieces (u_hb_idx__s_Q2_*) were homed in q_b010 / q_b001
    on top of ft lane stations. The C21 home search ignored the bit sites and station regs. Render `c21_idx_homes.png`
    (viewed) shows the pieces sitting on the dense L14 / L28 / L36 ... corridors.
  - **complete/internal_station 4:** the planned VM link u_vmb_Q1 <-> u_vmb_Q5 (3.98 mm) has 3 registers, so its hops
    are over the 405 um reach.
- **Fix = C22** (`apply_c22.py`; plan at intel2 `/srv/opentallas-scratch2/claude/die-hbm-10/c22`).
  - (a) Every piece is re-homed on a corridor-free slot. Blocked = other cores and contents, every actual ft bit cell,
    every station reg, with an 8.64-um halo to cores.
    - Fill order goes outward from the hub W face (locality): q_b000 7, q_b010 23, q_b001 27, q_b011 7, q_b002 2.
    - Same views and inst names; 0 new types. Stations, windows and pins are unchanged.
    - Corridor-free capacity per type is from `idx_cap.py`: b010 22, b001 28, b000 7, b011 7, b002 7, b003 18, b012 16,
      b013 23.
    - Render `c22_idx_homes.png` (viewed): the pieces sit in the empty top band and in the gaps, clear of the lanes.
  - (b) The VM link registers are placed by a greedy walk along the nearest free channel row, because the straight row
    crosses u_hb_vms_Q__q0, which is 778 um wide.
    - NW: dy +513 um, path 5.01 mm, 14 regs, Lx 15, max hop 401.8 um, 0 regs in a core.
    - NE: 13 regs, Lx 14.
    - The RTL LX parameter (vmx branch, bench at LX 4) must take 15 for both hubs, so that there is one static-schedule
      constant.
  - G0 + G0C on C22 are RUNNING (started 10:00; collect `c22/gates_g0{,c}.{log,exit}`). The expected result is the C20j
    16 errors plus whatever the moves expose.
- **trial1** (DIE-HBM-9 private pre-READY tool copy, `--clock-cell inv` on C21): the kit step is still running at 54 min
  (pid 3309279) and has written no tree yet. It is not killed. Collect `trial1/chain.status` and `duty_trial1.json`.
  Its numbers are informational only, because the tool copy is not on main.
- **trial2** (started 10:02): MAIN die_trial (RM150 DIE-QC-11) with `--clock-cell inv2` on C22, using the same feed and
  region trees as trial1.
  - Chain: kit -> bays -> overlay -> clock GRT TT/FF (docker, 48 g cap each) -> duty_eval.
  - Path: intel2 `/srv/opentallas-scratch2/claude/die-hbm-10/trial2/` (status in `chain.status`, readout in
    `duty_trial2.json`; script copy in `c22/trial2_chain.sh`).
  - QC trial10 with inv2 measured duty TT 48.2-51.3 / FF 49.9-55.75. HBM's deepest taps (~220 stages) are the
    open question.

## (2) PHY_N W/C/E split: plan-time CA bound (COORD 09:30)
Script: `ca/ca_bound.py`. It uses the ONE shared model and nothing else:
- `tools/die_plan/locality.margins` = `landed_phase_ocv.analyse` with clk_aocv g021, i.e. clock_variation=table, 0.21 %/mm;
- one-sided droop between regions;
- class-B core latency 250 TT / 202.5 FF;
- `locality.cap_reading` = `count_align_plan` unchanged (K, DEPTH 4/8, start tree, path ambiguity, T/8 aperture, 5 % wander);
- spice x1.05 on every unshared delay (12.15b plan tools).

Branch geometry comes from the DIE-HBM-9 `die_retree.py` model:
- a tree edge whose crossing exists takes its CHECKED unshared value;
- otherwise Manhattan(feed taps) x 365.9 ps/mm;
- NEW: an unmeasured last edge into an endpoint region also pays that region's insertion (die_retree.py left it out).

Both directions of every link are planned. Start-tree crossings are directed, so planning one direction leaves regions
unreached.

| feed (92 region links) | FAIL | <100 ps | D4 / D8 (directions) | worst m_lo / m_hi | max unshared |
|---|---|---|---|---|---|
| **split** (PHY_N W/C/E + centre column from root, `hbm9/retree/hbm_feed_split.tsv`) | **0** | **0** | 130 / 54 | **109.6 / 122.5 ps** | 9.37 ns |
| V1: PHY_N whole, fed from centre column T057 | 2 | 1 | 128 / 54 | T059~T060 FAIL (m_hi -718) | 14.83 ns |
| V2: V1 + NW_mcb/NE_mcb fed from PHY_N leaves | 4 | 2 | 125 / 55 | T055~T059 FAIL (m_hi -1287) | 14.86 ns |

- **Worst link of the split (the "8.9 ns" one) is T047~T052, 173 b, 3 tree hops, LCA T029.** In this model it is 9.37 ns
  unshared (x1.05 included). Result: p_tt 418 / p_ff 344 ps, DEPTH 8, margin lo 219.0 / hi 1462.5 ps, ambiguity 3, so
  **PASS >= 100 ps at D8.**
  - Plausibility check (not an independent NUMBER-CHECK): CLK-LOCAL-EST-1's own row for the same port, L78m_0 at
    8.04 ns, gives D8 679 / 1442 ps. This model is the more pessimistic of the two.
- The thinnest links are not the long ones:
  - T010~T014 (4732 b, D4): m_lo 109.6;
  - T011~T019 and T018~T038 (1246 b each, **12 tree hops**, D4): m_hi 122.5.
- The PHY_N links in the split: T059~T060W and T060E~T061 are tree edges, 3.69 ns, D4, 205.7 / 1038.7 ps.
  T057~T060C is 2.09 ns, 285.5 / 1118.5 ps.
- 12.16b(i) says a direct crossing must be a tree edge or close a SHORT loop. Rerun with "more than 2 tree hops becomes a
  hop chain" (`ca_split_h2.json`):
  - 17 links (10.25k b) become chains of neighbour crossings;
  - 0 FAIL; worst hop margin 109.6 / 192.9 ps;
  - the worst chains are the 12-hop T011~T019 / T018~T038 (about 22 root-frame cycles against 5 direct) and T019~T039 /
    T038~T049 (27 b, 22-25).
  - tok/s cost NOT estimated. The ds rerun with these latencies is owed.
- Without the split (V1/V2), the loop T010-T028-T042-T055-T059-T060-T057-T054 is closed by a 6.5-7.1 kb link. Its hop
  chain is a 7-hop detour down through the die centre. **The split is the structural fix.** It moves the tree cut inside
  the PHY, where (if the cut lies between independent channel groups) no data crosses it.

### BLOCKER found while building it: PHY_N is ONE hard macro with ONE clock pin
- `ot_hbm3e_phy_rc_e8p5` is 8500 x 1177 um, an ASSUMED licensed-PHY abstract. Its notes say "clk, rst_n in window 16",
  and gen_arch.py says "hard macro: one clock pin, own tree".
- It spans all three thirds of PHY_N (io rect 9797.76..18299.52). A 3-partition split would cut a hard macro, so the
  C22 split is NOT built.
- What the split needs:
  - (a) a PHY abstract with per-group clock pins: 3 slice macros by pseudo-channel group, or one footprint with 3
    clk/rst_n pairs. This is an opt-in `tools/mem_compiler/hbm_phy_gen.py` variant, i.e. a shared tool, so ROOT-MERGE.
  - (b) a PC -> link map showing that no data crosses a group cut. Today L8 (W, via NW_mcb) and L9 (centre, via vsN6)
    are BOTH NW-hub -> PHY data, and their PC windows are not yet mapped.
- The ASK goes to COORD-REVIEW-QUEUE with a default.

## (3) VM crossing-read port + dead-by-schedule ties (die-local RTL)
Branch `claude/die-hbm-10-vmx-1028@3acc793e88`, kept separate from this results branch because it contains RTL. Files
are under `results/die_hbm_1027/hbm10/vmx/` on that branch.
- **RTL:** `rtl/hbm_accel/generic/vm/static/xread/hfd_vms_xread_link.sv`. It is a new module, so no existing instance
  changes.
  - The owner half issues the read with the record. The bank response (257 b) goes over a fixed LX-register relay chain
    to the far half.
  - Width: 16 lanes x 257 b = 4112 b per direction.
- **Ties:** the far client's request pins toward the owner bank group are tied to 0 at the parent, and its response
  pins are left unconnected. The master is unchanged. Declared in `vmx/xread_ties.json`.
- **Bench (CHECKED):**
  - iverilog with real q0_faces banks: 1755 crossing reads, each at exactly n+6+PIN+LX, while the far half does 256
    local reads in the same cycles.
  - 4 mutants are all FATAL: one stage short, lanes swapped, a data bit flipped, a live tied request.
- **LEC (CHECKED):** lec.py on a mini kit (LANES 16, LX 4, 32,961 cells) is EQUIVALENT, 20,560 of 20,560 points.
  Per-variant LEC of the tied bank is UNCHECKED; the argument is that the master is unchanged and the tie sits at the
  parent.
- **Token check: NOT RUN.** It needs the link in the die contract, plus half-local VM allocation and owner-issued reads
  in the compiler. **The cross-half relief is still NOT counted.**
- C22 needs LX = 15 (see (1)). The bench should be re-run at LX 15 before READY.

## (4) Quarter cuts: constructive hub placement (ESTIMATE; `hubplace/`, tool runs CHECKED, model UNCHECKED)
- **Method:** `hub_place_est.py` = hbm9 `hub_replica_est_q.py` with the model unchanged, plus:
  - `--placer cons`: grow outward from the fixed face windows and put each core in its best cell under the same net
    cost, then greedy move and swap passes. Deterministic.
  - `--snap`: hard cores sit fully inside their cell, off every cut line plus the halo.
  - `--pack`: a MaxRects legal pack per cell, so 0 overlaps and 0 cores outside the outline. The two oversize VMS cores
    stay fixed at their plan rects.
- **hbm9 model bugs** (they make the earlier SA and cut-clear numbers unreliable):
  - `--cut-clear` moved hard rects before station pins were resolved;
  - SA moved the oversize VMS cores out of the hub (1-3 cells per hub could not pack).

| Hub | Variant | Worst face | Cuts v0 / v2 | v1 | Cell hard util |
|---|---|---|---|---|---|
| NW | conn order, util 0.80 | **0.699** (0 faces over 1.0) | 0.57 / 0.57 | 0.46 | 0.80 |
| NE | area order, util 0.80 | 1.026 (1 face, h30) | 0.49 / 0.64 | 0.45 | 0.76 |
| NE | conn order, util 0.85 | 1.004 (1 face) | 0.71 / 0.61 | -- | 0.85 |

- Render `hubplace/cons_fa_snap_pack.png` (viewed): cores sit off the cut lines. Only the plan-fixed VMS cores straddle
  h1.
- **Verdict:** every quarter cut is closed (<= 0.64 in the best variant per hub). One NE face (the lower SM/VM corner
  row) is still at 1.00-1.03.
- **Next:** take the constructive placement into the plan event (hub repack) and close the NE corner face with the
  face-window re-site there.

## Next steps
1. Collect C22 G0/G0C (diff against C20j: 0 new errors expected from (a)/(b)).
2. Collect trial2 (duty both edges TT/FF at the deepest taps, MPW, overflow, a viewed render). Then collect trial1.
3. PHY_N: once the ASK is ruled, generate the per-group PHY abstract + map PCs to links, then build the split (C23).
4. The 17 far links (> 2 tree hops) as hop chains: ds tok/s estimate with the chain latencies.
5. vmx: LX 15 bench, then wire it into the hub glue / die contract; token pass once the compiler does half-local
   allocation.
6. Hub repack from the constructive placement in the plan event.

## (5) 2026-10-28 11:00-11:50: C22b gates, the one tok/s rerun, compiler half-local slice, C23 PHY map, reset contract
- C22b (lattice-fixed C22) G0/G0C, same mainsnap tools as C20j/C21 (CHECKED): **G0 PASS** (0 errors, 565 warnings);
  **G0C 16 errors = the C20j baseline exactly** (12 core_faces + 4 street_reach), 0 new, 0 gone. Logs `c22b/`.
- One tok/s rerun (`tok_rerun_c22.py`, `tok/`; ds S2, ESTIMATE, model UNCHECKED): hop chains (17 links, per-unit worst
  added latency, every record of the unit serial) + half-local far reads (LX 15, Wx 4096, f 0.5).
  - Estimate of record (data-path hop latency SM +2 / SU +7 / IDX,DMA +17; SM matvec far reads stream under the op):
    **+2.98 % -> 1,851 tok/s** from 1,906. Serial far reads: +5.01 %.
  - Bounds: hop latency incl. the 27-b io<->SFU ctl links on every SU record (+24): +4.72 % alone, +6.0/+6.96 % with
    far reads; blanket (all VM inputs of every record half far): +10.6 % / +15.1 %.
- Compiler half-local VM (claude/die-hbm-10-vmhalf-1028@f5558f45be, opt-in): Placement half mode keeps k%8; far-half
  groups are owner-issued crossing reads at fill_commit + NativeTiming.xread_lx; calendar assert refuses a late or
  unpriced (tied-pin) far read. Default output byte-identical (DS L2, 366 files). 5 new + 9 existing tests PASS.
  DS L2 fixture run (`vmhalf/ds_l2_runs.jsonl`): 9 emitted records, 0 mismatched words in both halves; 866 / 881
  crossing reads, 0 late, 0 unpriced; replay end 15,406 -> 15,406 / 15,416 cycles. RTL slice replay: NOT RUN.
- C23 PHY map + rc_slice generator (claude/die-hbm-10-physlice-1028@c99b18e969): see `phy_split/`.
- Reset contract per kit: `write_kit_reset_contract.py`, 65 HBM kits, all gate-checked used = 64.

## (6) 2026-10-28 11:40-12:10: C23 face census -> re-balanced split C23q (ESTIMATE, plan time, no build)

- Scoping the C23 build found a capacity problem. No cut crossing means every PC's in and out bits (585 b/PC) take one path.
  - 8/16/8: the centre column vsN4..6 must carry PCs 8-23 = 9360 b, because L22/L22m rdata now leave PHY_NC through it.
  - That is 1674 um of the 1684.8-um face at the plan's achieved 5.59 b/um (fill 0.994). It is NOT buildable safely.
- 2-way variants:
  - `ca_c23b`: everything goes on the W/E mcb paths. The spu0 and spt0 faces reach 1.17 of face_pins_per_um. FAIL.
  - `ca_c23h`: the column feeds the W half. T057~T060W fails direct. Hop chains cost 6/10 cycles. Rejected.
- **C23q = W PC 0-9 / C PC 10-21 / E PC 22-31** (whole channels; `c23q.py`, `feed_c23q.tsv`, `ca_c23q.json`, `feed_c23q_census.json`).
  - Face fills, worst / column / column window: C22b 0.89 / 0.56 / 0.60, C23 0.70 / 0.93 / 0.99, **C23q 0.82 / 0.69 / 0.75**.
  - CA: 0 fail, 0 below 100.
    - Die worst is still T047~T052 at 109.6 ps.
    - PHY links: T059~T060W and T060E~T061 are D4 at 206.9 / 1039.9 ps. T057~T060C is D4 at 283.1 / 1116.1 ps.
  - Grade: UNCHECKED model until the build re-plans on the merged CLK-INV-CAL-1 model.
  - Slices: rc_slice `--pcs 0-9 / 10-21 / 22-31` = 308 / 369 / 308 x 8.64 = 2661.12 / 3188.16 / 2661.12 um (sum 8510.4 <= PHY_N 8804.16).
  - Cost: the hub PHY buses regroup by PC (W path 10 PCs, column 6 PCs per hub). This is a hub face re-pin inside the C23 plan event.

## (7) 2026-10-28 18:15 PDT: plan event C24 = C23q + hnx_lane_x view + REBAL-6 arrays + bank3 write_v pin (plan time, no build)
Plan intel2:/srv/opentallas-scratch2/claude/die-hbm-10/c24/die_plan.json sha256 3ab76af4 (base C23q 403d45a4). The script is
`apply_c24.py`; its inputs are the committed REBAL files (claude/hbm-cores-rebal-6-1028@bd8c7c1b54, rebal-10@5a0f726f94). The
event report, side data, pins file, render, probe and gate logs are in `c24/`.
- **hnx_lane_x view** (`c24/hnx_lane_x__285.12x302.4__c24.json`, plan cores/ format):
  - Outline 285.12 x 302.4 (33 x 35 units of 8.64). The estimate of 289 x 320 does not fit the S half: 2 x 320 lanes
    plus the SRAM top at 373.68 and the channels exceed 1036.8.
  - 1670 pins (the RTL port list: 1669 signal + clk; the REBAL-5 figure of ~1672 was an estimate).
  - Faces:
    - N (M5): shared operands, 552.
    - S (M5): ixb_p, 532.
    - W (M4): side store, 531 (the parent W face, or the E face for lane 2).
    - E (M4): gather out + 4 resets, 54, on the centre channel.
    - clk: centre M5 interior pin.
  - Density is at most 1.94 pins/um, 20 per 10-um window (budget 60).
- **Children per half** (c24_side.json core_views; core frame, inside CORE_AREA):
  - u_lane0 R0 (8.64, H-311.04); u_lane1 R0 (8.64, H-648); u_lane2 MY (336.96, H-311.04).
  - The centre channel is 43.2 wide, and lane 1's operand face has a 34.56 gap.
  - Child-to-SRAM body gap: S 15.12, N 131.76, against a rule of >= 10.8.
  - The parent clock entry (315.36, 604.8 N / 518.4 S) is in the channel.
  - 12 of the 33 REBAL-4 islands per half fall inside the children. The parent infra plan must be regenerated with the hard children (REBAL-11).
  - Render `c24/hnx_c24.png` VIEWED.
- **REBAL-6 arrays** (core_arrays):
  - lanes_plain: 24 SRAM, 9 driver_rects, detour <= 19.1.
  - programme_store: 44 SRAM, 16 driver_rects, detour <= 87.4.
  - core_macros.json now marks the hnx halves, lanes_plain and programme_store KNOWN (plan-fixed).
  - Existing G0C clock_entry_macro: 179 -> 319 cores checked, 0 entries over a macro.
- **bank3 write_v** (COORD relay of REBAL-10): the lanes__canon pin g_bank_k3_u_bank_write_v moves on its S face (M5, free track) from x 13.656 to x 569.976, under bank3.
  - The model is REBAL-10's own relay_reg_guide_spec on the m5w1gr guides, with the other 11 relay boxes kept.
  - Hop: pin->relay 574.9 -> 299.9 um, longer hop 579.3 -> 299.9 um (`c24_wv3_probe.py`).
  - Timing: UNCHECKED estimate, about +280 um of reach.
- **Gates** (same mainsnap check.py):
  - G0 PASS: 0 errors, 564 warnings (568 on C23q).
  - G0C: 16 errors, identical to the C23q baseline (12 core_faces q_hub_nw/ne + 4 street_reach); 0 new; 85 pending-view.
- Unchanged: the C23q PHY split, the xq_pegress view drop, section 12, all checks.
