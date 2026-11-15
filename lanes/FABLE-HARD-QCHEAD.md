# FABLE-HARD-QCHEAD 2026-11-14: root causes for the QC and HEAD types that did not close

Scope: QC coll_n, qfd_dv_s5_ctl_repair4_leaf, slw/sle_su_l0; HEAD hd_ctl_n, hd_host_e, hd_spn, hd_spn_end. Read-and-diagnose: kit logs, sign-off records, one read-only database probe, a perf sample of the stuck yosys, three fleet scans (630 kits) and two small ot-run experiments in my own directory. Nothing shared was changed, no job was touched.

Status words: MEASURED = read from a log, record, database or experiment; HYPOTHESIS = fits the numbers, not proven.

## 0. Verdict in one table

| type | what the lanes chase | root cause | status |
|---|---|---|---|
| QC repair4_leaf | yosys "stuck" in OPT_DFF; SHARE pass; unregistered inputs | the slang frontend turns each of the 21,246 gate instances into its own kept module; every yosys pass is quadratic in modules, then ABC runs 21,246 times | MEASURED, fix PROVEN (synth 9 h+ -> 25 s) |
| QC slw/sle_su_l0 | DRC-only route pass, late ECO, "bad site" | interior M7 landing pin lies wholly over an M6 PG pair: no legal via down, the router leaves along M7, a 0.032 wire on a 0.080 pin is not a rectangle | MEASURED; the rule predicts every known case |
| HEAD hd_spn_end | pin moved one 8.64-um step | same pin class; 8.64 um is two PG pitches, so the moved pin sits on the next PG pair in the same phase | MEASURED: the adopted move cannot work |
| HEAD hd_host_e | DRT-0255 forms (density, south blockage, flow margins) | two blockers hidden behind DRT-0255: (a) setup -395 ps on 564 endpoints because the hard core u_epc gets its clock 400 ps early; (b) 64 DRC because one in twelve M6 pins of u_epc lies on a parent M6 PG stripe | MEASURED on the one form that routed |
| HEAD hd_ctl_n | flow margins | already signed off under the academic profile (private pre-GRT hold kit); the wave failure is the DRT-0255 class below | MEASURED |
| HEAD hd_spn | flow margins | no open design cause: the one failing path was fixed in the plan (pin move raw_42); every build since died of host memory | MEASURED |
| QC coll_n | PG hook, edge blockage, density | DRT-0255 class below, made dense by an SRAM whose 793-pin west face looks at a 13-um strip | class MEASURED, mechanism HYPOTHESIS |

## 1. QC qfd_dv_s5_ctl_repair4_leaf: synthesis is quadratic, not stuck

MEASURED
- The core is a generated gate netlist: 21,246 instances of nine one-gate helper modules (`qfd_bmath_mux` 5,796, `dff_p` 4,531, `and` 2,769, `dff_pn0` 2,676, `not` 2,314, `xor` 1,562, `ao21` 1,260, `or` 225, `oa21` 113), each marked keep_hierarchy.
- The kit sets `SYNTH_HDL_FRONTEND = slang`. The slang frontend names every kept instance as its own module: the canonical RTLIL holds 21,247 modules (`\qfd_bmath_mux$qfd_dv_s5_ctl_repair4_leaf.u_r.u_ctl.u_NNN` ...).
- perf sample of the running yosys of form d (epyc2, pid 148069): time is in `OptDffWorker::run_constbits -> ModWalker::ModWalker -> NewCellTypes::setup_module`. opt_dff builds a table of all design modules once per module: 21,247 x 21,247.
- Form d is not hung: pass 5.6 at 17:05, pass 13.6 at 18:32. Form a (same netlist) started 05:16 and was in ABC module 1,431 of 21,246 at 14:06 when it was cancelled: over 9 h and not half way.
- Experiment: form d kit copied, the one line `export SYNTH_HDL_FRONTEND = slang` removed. The Verilog frontend makes nine modules. Synthesis took 24.6 s. The structure is kept exactly: 21,246 submodule instances, 48,386 cells. The build went on to placement at once.
  Kit: epyc2 `/srv/opentallas-scratch2/claude/fable-hard-qchead/rep4v/kits/qfd_dv_s5_ctl_repair4_leaf_synth0`, log intel2 `~/fable-hard-qchead/rep4v.log`, goal finish.

Dead ends
- Form dn (-noshare twin): SHARE is not where the time goes.
- Waiting on form d: it will finish synthesis in about 15 h and then route the same netlist as my copy.
- Forms a, b, c: same cause; c also failed face_guard, which form d's pin registers answer.

Fix
1. Now: take over the rep4v build (it is form d plus the frontend line) or relaunch form d without the slang line. Note for LEC: the kit proves the netlist against the other frontend, so the gold side now reads slang and will be slow in the same way; run LEC with the gold side on the Verilog frontend too for this core, or give it the nine-module canonical RTLIL.
2. Generator (`mk_rep4d.py` and the helper file): do not emit one kept module per gate. Keep the flops by a keep attribute on the cell and let the gates flatten, or emit the ASAP7 cells directly. Then either frontend works.
3. Flow guard: stop a kit at canonicalize when the design holds more than about 2,000 modules, with this message. The S81 `svc` kit that got the same -noshare recipe should be checked for the same cause.

## 2. Interior landing pins over an M6 PG pair (QC su_l0, HEAD hd_spn_end, hd_host_e)

MEASURED
- QC su_l0: `cland_tstart_in` is an M7 pin 0.080 x 0.432 at (158.176, 174.9516), inside the core. The M6 PG pair there is VSS 174.624-174.912 and VDD 175.008-175.296 (width 0.288, gap 0.096, pitch 4.32, first centre at core + 1.968). The pin spans y 174.736-175.168: all of it lies over the pair or its gap. No M6 track under the pin is legal, so no via can go down. The router leaves the pin along M7 with a 0.032 wire; a 0.032 wire joined to a 0.080 pin is an L shape, which ASAP7 M7 forbids (Rect Only). That is the 3 DRC, on every build, before and after any ECO.
- The pin placer does not know PG: `landing_contract._site_clear` checks only pin-to-pin distance.
- Scan of 630 wave kits on three hosts (about 940 interior M7 pins) with one rule, "an interior M7 pin must contain a legal M6 track": it flags exactly QC `cland_tstart_in` of sle/slw_su_l0 (the four known Rect Only items), HEAD hd_spn_end `rst_start_raw_5`, HEAD hd_host_e `rst_start_raw_0` and `rst_start_raw_2`, and S81 serdes `io_pma_rck[0]` (a 0.192 square pin). HEAD-99 had already measured 3 Rect Only on `rst_start_raw_5`. Nothing else is flagged and no clean type is flagged.
- HEAD hd_spn_end: plan rp21z10 moved `rst_start_raw_5` from y 887.784 to 896.424. That is 8.64 um = two PG pitches: the pin again spans 896.208-896.640 over the pair 896.064-896.736. The current wave kit (attempt_6, epyc10) carries this site. It will end with the same 3 DRC.
- QC S3R2 moves `cland_tstart_in` to y 167.392 or 228.949: both are clear (1.26 and 2.34 um from a pair centre). That move is right.

Dead ends
- A DRC-only route pass or a late ECO on the existing su_l0 databases (KIT-OPS-4, two in the loop): hold and slew can close, the 3 DRC cannot.
- Any pin move by a multiple of 4.32 um in y.

Fix
1. Rule in `landing_contract` (site check and `separate_pins`): an interior M7 pin is legal only if its extent holds an M6 track at least 0.072 um from every M6 PG stripe, or a free M8 type track for the way up. Same rule with x and M5/M7 for a horizontal-layer pin. Add the scan as a plan test; it is 40 lines (`pinscan.py`, section 6).
2. HEAD: move `rst_start_raw_5` by 2.16 um (y 889.944), not 8.64. Check hd_host_e `rst_start_raw_0` (170.528, 554.880) and `rst_start_raw_2` (289.952, 19.200) with the rule; move them in the same event. Stop the hd_spn_end attempt_6 build or accept that it ends DRC 3.
3. Sign-off of the routed su_l0 databases now, without waiting for the plan event (HYPOTHESIS, cheap to try): give that one net an M7 rule of width 0.080 (the pin width), delete its wire and detail-route it again. A 0.080 wire on a 0.080 pin is a rectangle. The pin does not change, so the parent view stays valid.

## 3. HEAD hd_host_e: DRT-0255 hides two blockers

Only one hd_host_e form reached sign-off: `g_hd_host_e_ws` (epyc2, hook with wide spacing, 16:56). It is the picture of what every other form will meet after detail route.

MEASURED, timing
- TT setup -395.27 ps, 564 endpoints, total -120,289 ps. FF hold -10.24 on 179.
- Worst path: SRAM `u_ski.u_head.g_bank[6].u_m` to `u_epc/in_data[441]`. Launch clock at the SRAM 441.8 ps after the tap. Capture clock at `u_epc/clk` 42 ps after the same tap (one buffer). Skew against setup 400 ps = the violation.
- Why: `OT_TAP_CORE u_epc/clk pin 42 + internal 421 = effective 464 (target 450) OK`. The tap tool aligns the core by the largest internal clock delay of the model (421 ps). The model itself says the inputs are captured much earlier: setup arcs of the 1,209 inputs have median -81 ps, hold arcs median +117 ps, so the input registers sit about 100 ps behind the clock pin, not 421. Outputs leave 426-468 ps after the pin. The core has about 320 ps of skew between its input and output registers, and the parent pays all of it on the input side.
- Budget with tap latency L at the core pin (parent flops at 442): input data may take 421 + L, output data 787 - L. Today L = 42. The failing SRAM path needs L of at least 395 for -42 ps; outputs then keep 392 ps.

MEASURED, DRC
- 64 violations, flat for 25 iterations: 22 shorts, 12 spacing, 30 end-of-line, all at x 423.2-423.5, the west pin face of `u_epc` (macro origin 423.36). Shorts are `ft[60]`, `ft[72]`, `ft[84]`, `ft[96]`, `ft[108]`, `ft[238]`, `ft[250]`, `ft[262]` against VSS on M6: every twelfth bit. The core's M6 pins have 0.36 um pitch; every twelfth lies inside a parent M6 VSS stripe (pin y 325.92, stripe 325.824-326.112), and the stripe runs to 48 nm from the pin.

Dead ends
- Forms B (density 0.4, south blockage), C/nr (flow margins off), the wave retries: they change where DRT-0255 hits. None touches -395 ps or the 64 DRC.

Fix
1. Clock: set the `u_epc` tap from the pin-referenced arcs, not from the largest internal delay: L about 330-400 ps (plan core latency of ot_s81hd_he_epc, or `OT_CORE_LAT` in the kit). Tool rule for every hard core: align on the median setup/hold arc of the inputs and the clock-to-output arc, report both budgets, and flag a core whose two sides differ by more than 150 ps. Proof without a build: on the routed `ws` database, set the latency of `u_epc/clk` in STA and read the two budgets (minutes).
   If the output side then fails, the structural fix is in the core: clock the HE-EPC input registers at the same depth as its output registers and re-sign it (owner allows re-sign).
2. PG at a hard-core pin face: stop the parent M6 stripes 1-2 um before a macro face that carries M6 pins (same for M5/M7 faces), or place core pins off the parent PG phase when the core is exported. The first is a generator change in `pdn.tcl` and needs no core re-sign. Proof: the `ws` kit rerouted from the floorplan with the cut: DRC 64 -> 0.
3. Pins `rst_start_raw_0/2`: section 2.

## 4. HEAD hd_ctl_n and hd_spn

- hd_ctl_n is signed off under the academic profile: TYPE-HDCTLN's pre-GRT hold kit (epyc8 `type-hdctln/pregrt`) has DRC 0, TT -25.82, internal hold pass, archived on both sides. Form f1 (wave kit without the flow margins) finished detail route with DRC 0 at 18:5x (12,920 -> 1,528 -> 961 -> 23 -> 0); sign-off numbers pending.
- The flow-margin theory is half right. MEASURED: with `SLEW_MARGIN 50` the place stage inserts 7,698 buffers against 31 without; the kit ends with 139,183 cells against 130,851. The buffers land on port nets (the failing `w3u_i[427]` runs 54 um from its M7 pin to a buffer), so 250 times more nets are exposed to the trap of section 5. The margins are not the mechanism; removing them lowers the odds. Do remove them from the HEAD type_args (they are R-FLOW leftovers, no gate needs them), but do not expect that alone to end DRT-0255.
- hd_spn: the only design failure on record is one path (-108 ps, the `rst_start_raw_42` export, 1,261 um reach), fixed in the plan by the pin move. Every build since was killed by host memory (Error 241). Its current kit has no pin over a PG pair (44 interior pins checked). It needs one build that is not killed, nothing else.
- hd_spn_end "late-fix DRT 112 h": I found no such job; the oldest live container of these types is 5 h old.

## 5. DRT-0255 is one class: routes pushed into the row of an M6 PG pair

MEASURED
- All DRT-0255 failures still on disk on six hosts: 83 in 36 kits (QC 26, S81 34, HEAD 20, KV 3). For each I took the access point DRT prints and its distance to the nearest M6 PG pair.
  - Access point on a horizontal layer (55): 49 lie inside the pair or within 0.2 um of it. By chance it would be 25 %.
  - With the PG hook on (32 failures): 19 of 19 horizontal ones, 31 of 32 overall, are at a PG pair.
  - Typical values: M8 24 nm above the pair (hd_ctl_n `w3u_i[427]`, hd_host_e, coll_n), M6 on the first track above or below it (0.128, 0.096).
- The guide of each probed net runs along the gcell row under the pair: coll_n `net35749` M6 in row y 550.62-551.19, pair 550.464-551.136; hd_ctl_n `w3u_i[427]` M6 in row 654.36-654.93, pair 654.144-654.816.
- The hook does not close the row. It blocks M6 tracks by min spacing 0.032; the technology asks 0.072 next to a 0.288 stripe (read from the database), so one track per stripe edge is still counted free. And the row keeps capacity from M8 (and M2/M4 away from macros), so the 2D router still uses it.
- coll_n: `net35749` is not a pin problem. Its two ends are a repair buffer at (14.4, 551.1) in the west strip of SRAM bank 0 and a flop at (52, 499); the route returns east over the macro. Bank 0 sits at x 17.28: its west face has 793 connected M4 pins and 12.96 um of rows to the core edge; 526 of those nets go to logic above or below the macro, not west. The same build (attempt_8) also failed at the west edges of the rx memory and bank 2. Over a macro M1-M4 are closed, so a pair row has only M8.

- coll_n form b (hook off, density 0.4; COORD 19:0x): seven more failures, on `net29144` (66.69, 767.16 M8 and 74.67, 767.264 M6), `net21342` (74.67, 430.304 M6), `net28865`, `net30081`, `rf[38]`, `net29823`. Same picture: `net29144` has its M6 guide in row y 766.65-767.22 under the pair 766.464-767.136, and its access points are 24 nm (M8) and 128 nm (M6) above that pair; `net21342` has its guide in row 429.78-430.35 under the pair 429.504-430.176, access point 128 nm above. These two are NOT over a macro and not in the edge strip: y 767 is 67 um above bank 2, y 430 is below the rx memory, x 62-75 is 45-58 um from the edge.
- So the x 62-75 band is not macro pin access and not the macro-to-edge channel. It is where the nets of the west bay (cells at x 55-59, M7 trunks at x 55-59) turn east along a pair row. Hook on, hook off, density 0.5 and 0.4 all fail in pair rows.

HYPOTHESIS (mechanism): in a pair row a net can run only on M8, or on the one M6 track at the pair edge; the stack down to M5 has no legal M6 landing inside the row. DRT's first pass leaves such nets on edge or off-track positions; in the next pass the box holds a fixed end that no legal path reaches. I could not show the geometry: my experiment (detail route pass 0 on the saved coll_n database, wires kept, epyc10) was killed inside pass 0 on a host at load 380 and I did not rerun it. The mechanism stays a hypothesis; the class (pair row) is measured on 90 failures.

Dead ends
- coll_n form a (hook alone): failed, as did 31 other hooked builds.
- coll_n form d (edge blockage): moves one buffer; the 793 west-face nets still turn in the strip and the pair rows stay open.
- Density 0.4 (form b): failed in pair rows at seven places. Seeds: the same trap.
- The fw and cbn twins on epyc2: all six ended 18:42-18:45 with make Error 241 (host memory), not with a design result. epyc2 had 29 GB free of 1,007.

Fix
1. Hook, two lines of intent: use the width-dependent spacing (the opt-in `OT_PG_TRACK_TRUTH_WIDE_SPACING` should be the default: the `ws` hd_host_e form is the only hd_host_e build that passed detail route) and close the whole gcell row of an M6 pair on M6, and on M8 where M1-M4 are closed by a macro. Proof: rerun GRT and DRT from `4_cts.odb` for coll_n form a, hd_ctl_n attempt_7 and hd_host_e d4; all three are deterministic today.
2. coll_n plan (layout improvement, not the DRT-0255 fix): move SRAM bank 0 from x 17.28 to 60.48 (the column of bank 2 and the rx memory; 44.7 um remain to bank 1), so its west face gets a 56-um bay like the others. No outline change. Form b shows the failure also occurs away from macros, so this alone does not close coll_n.
3. Scan before detail route (extends fleet fix 6): count nets whose guide runs along a pair row over a macro or ends on a cell in a pair row with the guide in that row; reroute those in GRT. The 83 failures give the test set.

## 6. Evidence and tools

- intel2 `~/fable-hard-qchead/` (ot-run logs); epyc10 and epyc2 `/srv/opentallas-scratch2/claude/fable-hard-qchead/` (probe_colln.tcl and log, drt0 scripts, rep4v kit).
- Scans (my scratchpad on rtx-pro, copy on request): `pinscan.py` (interior pin over a PG pair), `ap_scan.py` (DRT-0255 access point against PG pairs).
- Not done: the DRT pass-0 geometry dump (killed, see section 5); the STA what-if for the `u_epc` tap; the NDR reroute of the su_l0 net; sign-off of rep4v (running).
