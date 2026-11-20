# FABLE-PD-S81-SVC-0245: S81 svc family, what is still open for the J6 cut (11-21 14:00 PST)

Revision 2, 2026-11-20 03:5x PST. Read-only review. Revision 1 (commit before this one) covered the width class and the
split; COORD's 02:5x update says both are settled by S81-SVC-SPLIT-1119 on main 6ad4914428, so this revision keeps only
a short confirmation of those and spends the rest on the four open items: lo t7 margin, H8 placement and outline fit,
registered-read timing, and seams.

Sources: lanes/posts of S81-DIE-R3, S81-SVC-SPLIT-1119, FLOW-FIX-2045, FABLE-FIX-S81-SVC2, S81-TYPES-R3,
FABLE-FIX-S81-LEAF; origin/main 150d614de88 (my local ref; I did not read 6ad4914428); plan_j3b (the H8 rows) and
asbuilt_run.svc_h8.json in intel1 `/srv/opentallas-scratch2/claude/s81-die-r3-e8/d8j`; shell synth stats in intel1
`/srv/opentallas-scratch2/claude/s81-svc-split-1119`; provider kits in epyc8 `.../s81-svc-split-1119/s81svc_*`; live
flat kits on epyc2; SRAM views `physical/asap7_memory_macros_v2`.

## Verdict

1. **lo t7 is over the limit in practice, not at it.** 495k is a synth-only cell count before the 300-um stations,
   tie cells and timing repair. Decide the extra cut now; do not wait for the bind census.
2. **The H8 rows fit** (0 overlaps, 0 out of bounds on the three types I checked, parent cells use about 8 % of the
   free area). The risk is not area. It is where the N / S bus stations go: on svc_lo the cores form a wall with only
   8.64-um channels, and the gather bus arrives at 8.5 bits per um.
3. **Registered reads are a siting problem first.** All svc memories sit in one band at the top of the type, 1.2 to
   2.6 mm from their readers, with a 270 to 401 ps clk-to-q. A +1 flop does not close that unless the flop is at the
   macro and the macro is near its reader. One of the five sites (sw) already has a registered form on main that the
   H8 plan does not switch on.
4. **Seams:** five of the seven provider masters have pin registers, hslice is source-registered, and the TRX box is
   not registered on either side. That is the one open provider seam.

Ranked actions for J6:

| # | Action | Owner | Cost |
|---|---|---|---|
| 1 | Add `OT_SVC_ATT_RDPIPE` to the 16 svc rows and the as-built defines | S81-DIE-R3 (rows), S81-SVC-SPLIT-1119 (confirm cycles) | define only |
| 2 | Re-site the 31 form-A macros (wq 18, sw 8, qmem 4, pbuf 1) next to their readers | S81-DIE-R3 (`svc_formA_sites.py`) | plan rows |
| 3 | Explicit station bank sites for the N / S buses, one bank per band channel, spread wider than the pin window | S81-DIE-R3 | plan rows |
| 4 | t7 cut prepared now: `dsdv_idx_rg3` child; check whether `dsfd_ctrl_rg3_native32` has a usable view | S81-SVC-SPLIT-1119 | 1 core kit |
| 5 | TRX seam: trace `col` and the control pins on the first H8 bound; parent-side register beside the box if a leg is over 300 um | S81-SVC-SPLIT-1119 | +1 on the q.k / p.v calendar |
| 6 | RDREG on pbuf, wq, qmem with per-site bench | S81-SVC-SPLIT-1119 | J7 unless green by 11-21 08:00 |

## 0. Width class and split: confirmed, three leftovers

I found the same root cause independently before the lane's post: the as-built lists only
`portfix178/dsdv_svc_rs_fv.sv` and `portfix178/dsdv_svc_rs_pvso_entry.sv` for the port variants, both were 10-25 H16
copies (`wire [8527:0] c_gi_d`), and the column-frame `2132` hits are net names and reset-leaf indices. Leftovers:

- `tools/s81_dv/svc_rs/rs_fv_lint.sh` runs Verilator with `-Wno-WIDTH -Wno-fatal` and `|| true`. `svc_width_gate` now
  covers the bind; the lint should still fail on WIDTH, or be deleted.
- The H8 plan rows in plan_j3b still have the gather buses `attnh_i0 / attnh_o0` at 2133 bits and `dead_inputs` rows
  with `"H": "16"` (ranges such as `gi_d [[2132, 8527]]`). `svc_h_netlist.py --h 8` now narrows the die netlist to
  1,077. The plan bus width, pin sites, ft slots and the `attnh` landing-band reserve (9,634 um2 on t7) must follow in
  the same event, or the gate will stop on the type port. I did not check the post-fix rows.
- Nothing checks that a file under `bind/source_modules` is the current output of its generator. That check would have
  caught this bug at the source; the width gate catches it one step later.

## 1. lo t7 margin

Measured (split lane synth, plain yosys + abc, cores black-boxed):

| Shell | Cells | Area um2 |
|---|---|---|
| lo t7 H16, hcores + hrows + providers boxed (A) | 698,776 | 95,133 |
| lo t7 H16, landing rings also boxed (AF) | about 495k | 71,403 |
| lo rs_w t1 H16 (A) / rings boxed (AF) | 597,137 / 476,923 | 81,967 / 67,974 |
| hi rs t2 H16 (A), H8 measured 11-09 | 432,791, 228,760 | 60,092 |

In the t7 shell 217,580 cells are flops or latches and 172,440 are buffers or inverters.

The H8 estimate of 495k is 698,776 minus the 204k H16-to-H8 delta measured on hi rs. Three things are not in it:

- **300-um stations (R1, default on S81 from J5).** svc_lo carries about 8,400 bus bits on its N face and they travel
  about 1,700 um to the hrow band. At one station per 276.48-um band (section 2) that is about 5 more stations than
  today on each bus: roughly 40k to 60k more flops. Estimate, not measured.
- **Kit additions.** On the flat lo7 run of 11-17 the kit added 121,915 tie cells to 5.69M and the timing-driven
  repair added 13.9 % instances by global place.
- **Count basis.** The 517k "largest closed" is a kit instance count; 495k is a generic abc count. On hi t4 today the
  same kit reports 4.37M yosys cells and 3.39M instances at floorplan, so the two bases differ by about 20 %, and I
  cannot say in which direction the split lane's number is off.

So plan for t7 at 500k to 600k placed instances and make the cut now. Options, by saving:

| Cut | Saving | Cost | Comment |
|---|---|---|---|
| Landing rings as boxes | about 204k (measured, A vs AF) | up to 10 distinct ring masters, forwarded-clock cores, 17 ring bands on t7 | largest lever, too many new masters for J6; J7 |
| `dsfd_ctrl_rg3_native32` x 2 | 164k (split lane measure of bind_native) | none if the "reuse" status in the plan contents means a signed view exists | **check first**: I did not verify the view |
| `dsdv_idx_rg3` child (the lane's plan) | 57.5k to 79.9k (plan note) + 13 SRAM | 1 master a lo type; seam is to the 32 hslices, which are source-registered | good seam, small saving: t7 lands near 420k to 435k before stations |

Recommendation: build the `dsdv_idx_rg3` child now, in parallel with the bind (it is useful either way), and check the
ctrl view today. With both, t7 is about 260k to 280k before stations. With only the idx child t7 stays above 450k once
stations are in, so it would be the first svc type I expect to fail. pvso_entry t1 (about 420k, no idx) has the same
problem with less margin to cut: it needs the ctrl view or the rings.

## 2. H8 placement and outline fit

Measured on plan_j3b:

| Type | Outline um | Hard cores | Core area um2 | SRAM (count, area) | Overlaps | Out of bounds |
|---|---|---|---|---|---|---|
| svc_lo rs t7 | 1442.88 x 2980.8 | 98 | 2,779,802 | 97, 305,079 | 0 | 0 |
| svc_hi rs t4 | 1442.88 x 2747.52 | 66 | 2,091,831 | 76, 145,950 | 0 | 0 |
| svc_hi pvso_entry t1 | 1442.88 x 2877.12 | 66 | 2,091,831 | 212, 221,077 | 0 | 0 |

- Area: t7 has 1.216M um2 free and the parent is about 95k um2 at most. Area is not a constraint on any type.
- Band structure: rows at a 276.48-um pitch. hcore rows (8 x 157.68 x 259.2) alternate with provider rows; the hrow
  row (8 x 138.24 x 164.16) is at y 1140; all memories are in one band above y 2420.
- svc_hi: a provider row uses 544 um (691 on the smc / smr row) of 1,443 um, so each provider band has about 750 to
  900 um of free width. Channels are 10.8 um or more.
- svc_lo: the 32 hslices (77.76 x 276.48, taller than the band) stand at x 371 to 1054 in each provider band with
  8.64-um gaps in x (54 gaps) and 8.64 um to the hcore rows above and below (56 gaps). From y 35 to y 2420 the
  x range 371 to 1054 is hard core except for 8.64-um channels.

Consequences:

1. **N / S buses on svc_lo cross that wall.** `attnh_i0` (2,133 b) enters in the N window x 879 to 1130: 8.5 bits
   per um, straight above the hslice wall, and has to reach the hrow band about 1,700 um below. Every core is
   `obs_max M5`, so only M7 carries it vertically over the cores. The leaf lane measured about 10 usable tracks per um
   over hard cores on 11-19. A bus that stays in its pin window would use about 85 % of that; with `attn_o0` and
   `attnh_o0` beside it the column is over. Estimate from the leaf number, not an svc measurement.
2. **Stations need explicit sites.** The band pitch (276.48 um) is just under the 300-um hop, so the natural form is
   one station bank per band channel. A 2,133-bit bank is about 620 um2: in an 8.64-um channel that is about 72 um of
   channel length at full use, so give each bank at least 150 um of channel and spread the bus to about twice its pin
   window before the first core row. Without sites the tool places a bank at the centroid of its ends, which on the
   leaf types landed inside a core for 5 of 8 banks (FABLE-FIX-S81-LEAF 11-19 20:27). Use the same site form as
   `s81_hi_corridor.py sites`.
3. **Cycles.** With a bank per band the gather path inside svc_lo is about 7 to 8 legs from the N pin to the sx
   centre and about 4 to 5 on svc_hi from its S pin, against 2 to 3 today (`NR = 1`: 5 cycles a hop in total). The
   lo-to-hi score hop goes from 5 to about 12 to 14 cycles plus the landing ring. E / W hops on svc_hi (1,443 um
   pitch) go from 5 to about 7. The role-ROM GO delay (`svc_rs_tree.py`) has to be regenerated from the plan depth in
   the same event. Cycles are pre-approved; the numbers are geometry estimates.
4. Fence the parent logic by instance prefix to its band (`u_att.u_eng.g_t[i]` to band i, `u_sx` to the hrow band,
   `u_cland_*` to their `band_fixed_um` rectangles). At 2 % density over 3 mm the placer has no other reason to keep a
   500k-cell parent local.

## 3. Registered reads

Measured:

- SRAM views (TT): clk to `rd_out` 270 to 290 ps for `32x128`, 380 to 401 ps for `160x256`; address setup 28 to 32 ps.
  At 833 ps that leaves about 430 to 530 ps for the bypass mux, the wire and the reader's logic.
- Sites and macro positions in plan_j3b (svc_hi rs t4; svc_lo is the same band, 190 um higher):

| Site | Wrapper | Macros | Where | Reader | Distance |
|---|---|---|---|---|---|
| sw | `mem_la`, or `mem_lr` under `OT_SVC_ATT_RDPIPE` | 8 x 32x128 | x 168 to 655, y 2610 to 2630 | scanner (`g_own / f_full -> sw_step`) | not traced |
| wq | `mem_ar` x 6 (3 queues x 2 PC, 341 b) | 18 x 32x128 | x 146 to 1255, y 2559 to 2580 | HBM request `rq`, out on `hbm_o0` | svc_hi: S face, about 2,560 um |
| qmem | `mem_ar` SYNC 1 (512 b) | 4 x 32x128 | x 43 to 1380: one word spread over 1,340 um | engine q operand `eq_w` | fans to all hcore rows |
| pbuf | `mem_ar` MACRO 1 (256 b) | 1 x 160x256 | x 43 to 135, top-left corner | P-beat inject into the sx leaf | hrow band, about 1,250 um or more |

- In `mem_ar` and `mem_la` the macro output goes through the write-bypass mux to the reader with no flop, and the read
  address is the D-input cone of the pointer. `mem_lr` holds the word in a flop; the RTL comment records why: the `ar`
  form of sw was -107 ps TT pre-route and the 32:1 count mux was -173 ps.
- **`OT_SVC_ATT_RDPIPE` is not in the H8 as-built defines** (`OT_SVC_ALLQ, OT_SVC_ATT_MEM_MACRO, OT_SVC_H8,
  OT_SVC_H8_REUSE_RT2, OT_SVC_MERGE_H4, OT_IDX_*`), and not in the plan rows. The five provider kits signed on 11-19
  (sml, smd, merge_h4, smc, smr) do list it in their spec defines. The define is only read in `dsdv_svc_att.sv`, so the
  provider netlists should not depend on it, but the parent and its providers are then built under different define
  sets, and the parent uses the slower sw form.

What follows:

1. **sw: switch on the existing form.** Add `OT_SVC_ATT_RDPIPE` to the 16 rows. It has a bench (`tb_svc_mem_ar` LR,
   two negative controls). S81-SVC-SPLIT-1119 should confirm it is cycle-exact against the `la` form before the rows
   go in; I read the comment, not the bench result.
2. **Siting before retiming.** A capture flop only helps if it sits at the macro, and then the word still has 1.2 to
   2.6 mm to travel: 4 to 9 stations at 300 um, each of which the static calendar has to absorb. Moving the macro is
   cheaper. The provider bands of svc_hi have 750 to 900 um of free width and a `32x128` macro is about 52 x 21 um.
   Proposed sites (S81-DIE-R3, `svc_formA_sites.py`):
   - qmem: the 4 macros of the one word adjacent, in the provider band nearest the engine's q distribution.
   - wq: each queue's 3 macros adjacent, in the band next to the HBM face (svc_hi: the lowest provider band, y 311 to
     570, under the `hbm_o0` window x 401 to 569; svc_lo: stay in the top band, its HBM face is N).
   - pbuf: in the free 300 um of the hrow row (y 1140 to 1305), next to `u_sx`.
   - sw: next to the scanner; with RDPIPE the word flop goes beside the macros.
   On svc_lo the provider bands are full of hslices; the free width there is about 200 to 280 um a band, enough for
   these macros but check the channel to the hslice row.
3. **RDREG as the lane scoped it** (reader re-timed by +1, or a two-ahead address, bench per site) is then a +1 with
   the capture flop and the address flop both at the macro. Order by need: pbuf (401 ps, worst), wq, qmem.
   `mem_ar` already carries a registered address for qmem (`SYNC 1`). Do not add the define without the bench: the
   lane is right that it would break the slice.
4. The `mem_ar` 256-bit blackbox bug the lane found sits on the same three sites (wq 341 to 256, qmem 512 to 256). Any
   timing or cell count taken from a bound before that fix under-counts these read paths.

There is no placed or CTS timing report of any svc type left on epyc8 or epyc9 to confirm this with a path; the
argument is view timing plus plan geometry.

## 4. Seams

| Master | Count lo / hi | Pin registers | Source |
|---|---|---|---|
| ot_s81_su_sml_fold2 | 8 / 8 | recipe stage on, 1 in + 1 out | kit `pin_regs.json` |
| ot_s81_svc_merge_h4 | 8 / 8 | on, 1 + 1 | same |
| ot_s81_su_smd_fold2 | 4 / 4 | on, 1 + 1 | same |
| ot_s81_su_smc, ot_s81_su_smr | 1 / 1 each | on, 1 + 1 | same |
| ot_s81_svc_idx_hslice_fp | 32 / 0 | source-registered: every input a pin flop, every output from a flop | same |
| ot_hdc_v41x_attn_tr_x (4 XOFF masters) | 4 / 4 | **off**: inputs land on storage flops, controls pass one decode level before a flop, `col` is a one-hot read mux of stored flops | same |
| ot_s81c_attn_hcore, dsdv_svc_sx_hrow | 32 + 8 | on the flat hi t2 netlist every core input ends at logic, a constant, a port or a landing ring; 0 core-to-core links | FABLE-FIX-S81-LEAF 11-19 13:59 |

- The TRX box is the open seam. `col` leaves a mux inside the box and its controls enter a decode. In svc_lo the box
  is at x 1253 to 1313 at the east end of each provider band, up to about 1,220 um from the far end of the hcore row;
  in svc_hi it is at x 553. I did not trace which cells read `col`. On the first fixed H8 bound: trace the TRX pins to
  their first flop; if any leg is over 300 um, put a parent-side register bank beside the box (the row is free east
  of x 1313 on svc_lo) and move the q.k / p.v calendar by one, or move the box to mid-row.
- Parent-side partner of the registered providers: the provider side is registered, the parent side is whatever the
  placer does with the driving flop. The band fences of section 2 are what keeps that under 300 um.
- Between partitions the seam is unchanged from J4f: out pin flop, plan stations, 4-slot landing ring on the
  forwarded clock. The dn (805 b), up (16 b), P.V return (514 b) and scatter (1,076 b) lanes do not depend on H.
- The hcore / hrow trace above was "blind" on hi t4 / t5 / t6 (cores looked up by plan name, no receipt), so it stands
  for t2 only.

## 5. Evidence by lever

| Lever | Evidence | Where |
|---|---|---|
| t7 cut | shell 698,776 / 495k with rings boxed; 204k H8 delta from hi rs; kit adds ties and +13.9 % repair | split lane stats (intel1); S81-TYPES-R3 11-17 13:15 |
| Station sites | 8.64-um channels x 110 on lo; attnh 2,133 b in a 251-um window; leaf banks inside cores 5 of 8; about 10 tracks per um over cores | plan_j3b; FABLE-FIX-S81-LEAF 11-19 19:30, 20:27 |
| Macro re-site | clk to q 270 to 401 ps; macros 1.2 to 2.6 mm from readers; qmem word over 1,340 um | SRAM `_tt.lib`; plan_j3b contents |
| RDPIPE | define missing in as-built and rows; -107 / -173 ps recorded for the unregistered forms | asbuilt_run.svc_h8.json; `dsdv_svc_att.sv` 726 to 746 |
| TRX seam | `pin_regs.enable false` with the stated reason | epyc8 `s81svc_h8_trx_xoff0/pin_regs.json` |
| Fit | 0 overlaps, 0 out of bounds, free 1.216M um2 on t7 | plan_j3b |
| Flat form | 3.39M to 4.99M instances; floorplan repair 50,584 / 55,780 endpoints all violating; t7 repair 6 h 05 | epyc2 kits t4 / t6 a14; FLOW-FIX-2045 |

No svc type kit has been placed in the H8 form on the current RTL. Everything above about the type level is plan
geometry, view timing and synth counts.

## 6. Stop list

- Do not launch the lo t7 or pvso_entry t1 H8 kit as a single 495k / 420k parent and wait for the result; make the cut
  first.
- Do not add an RDREG define without the per-site bench, and do not add read flops while the macros stay in the top
  band: it buys one cycle of a path that needs four to nine.
- Do not leave the N / S station banks to centroid placement on svc_lo, and do not set `NR` or the role-ROM hop delay
  by hand.
- Do not box the landing rings for J6 (too many masters); do not pursue the H16 provider split or any growth (die
  spare is 103.7 um; H16 needs 1.196M um2 against 1.138M um2 free).
- Do not take cell counts or timing from a bound made before the `mem_ar` blackbox fix as final.
- Do not spend lane time on the flat C6 / H16 svc kits. Whether the live rows are stopped is COORD's call; I stopped
  nothing.

## Not checked

- main 6ad4914428 itself (the fix, `svc_width_gate`, the bench) and the post-fix plan rows.
- Whether `dsfd_ctrl_rg3_native32` has a signed view; the per-type variation of `dsdv_idx_rg3`.
- Which cells read TRX `col`, the sw scanner distance, and the qmem distribution path (`ot_hdc_v41x_kreg` may already
  pipeline it).
- Over-core routing capacity on svc (taken from the leaf measurement) and every cycle estimate in section 2.
- Whether `OT_SVC_ATT_RDPIPE` is cycle-exact against the `la` form, and whether the 11-09 parent counts were taken
  with it.
- The other 13 svc types' rows for overlaps (three checked), and svc_lo macro sites after an H8 re-site.
