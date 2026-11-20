# FABLE-PD-KV-0945 (2026-11-20 09:50 PST): structural review of KV plan event D26 R3

Reviewer: FABLE-PD-KV-0945 (Fable). Read-only: nothing launched, cancelled or patched; no STA run. Owner of every fix: KV-PLAN-R1.
Gate: DRC 0, TT >= -42 ps at 833 ps, internal FF hold >= 0, LEC, bind + LATCHECK.
Marking: **V** = I opened the file / ran the read this round. **R** = reported by the named lane. **I** = inferred. **P** = proposal.
R3 state at 09:46 (V): composed, schema VALID; gate queued on epyc8 behind memory (`intel2 ~/tmp/kvplanr1/d26_r3_gate.log`, admits 0 GB), not started. Runtime `rt/current` 1caf584c654 carries b699b5b678, 8899ba10e9, c6ab8bd7be (V).

## 0. Verdict

D26 R3 is sound for what it contains and should bind. It does not make any hg / hgi / pv type signable by itself. Four things found in real data:

1. **Proposal 3 clears the reserved-row wall on hgi. It does not clear pv.** hgi_v1: 94% of the classic overflow sits inside the M3-M7 reserved rects, and the split form removes it. pv_v8: 24% is in reserved rects; 67% is inside the pv_pair core boxes (over-the-core routing), which proposal 3 does not touch. pc is not measured.
2. **The lockups cover 5,083 of the 5,105 head-core hold ends. 22 core `rst_n` pin ends per type (to -250.8 ps FF) are not in the port list.**
3. **The hg types with the astk strip have a second hold class the lockups do not touch:** 1,862 cross-tap ends to -195 ps FF inside the strip, caused by the 1,200 sinks/tap spill onto taps 565 to 588 um wide.
4. **krsp h1 against h2 is not decided by krsp.** In both kits the worst setup paths are astk strip data paths of 25 to 30 cells (-577 / -548 ps), not reset recovery and not krsp. h2 has no gain and twice the TNS. D26 = h1 is right.

## 1. Proposal 3 (reserved rows M1-M2 + via column) against the zero-capacity walls

Method (V): every marker of `congestion-N.rpt` classified by gcell centre against (a) the kit's own `reserved_sites.tcl` M3-M7 obstructions, (b) content-macro boxes from `macro_place.tcl` + LEF size, (c) rest. Script `scratchpad/cls.py`, `pv8.py` (this session).

| Kit (intel2) | Form | Iter | Overflow | Zero-cap | In reserved M3-M7 rects | In core boxes | Open |
|---|---|---|---|---|---|---|---|
| k13ci `kv3_hgi_v1__cl141fc26e` | classic | 15 | 10,201 | 99% | 9,643 (94%) | 553 | 1 |
| k13i same type | split (proposal 3) | 5 | 3,499 | 91% | 39 | 3,248 | 204 |
| k13i | split | 20 | 185 | 98% | 0 | 185 | 0 |
| k13i | split | final | 4 | 100% | 0 | 4 | 0 |
| `kv3_pv_v8` D23H wave kit (dpkit-376552) | classic | 15 | 18,806 | 66% | 4,448 (24%) | 12,558 (67%) | 1,800 |

- hgi (V): the classic wall is two tiles, (100-200, 1200) 5,108 + 1,977 and (100, 600) 1,260, all inside reserved rects. Split form: kit M3-M7 obstruction area 5,340 -> 740 um2; the wall is gone by iteration 5. What is left (4 markers) is inside `u_head2_e0` at (185, 125) on `clk_c8` and one `rst_n` relay net: core-interior pin access, a DRT question, not a GRT wall.
- hg (R, FABLE-FIX-KV-HG 03:22): kR with M1-M3 reserve ended 195 at iteration 20, 191 inside head-core boxes. Same picture as k13i.
- pv (V): the reserved part is all vertical (4,422 V against 26 H): rows 1.35 um tall and 21 to 97 um long cut M3/M5/M7. R3 rows for `kv3_pv_v8`: 605 rects, stack area 2,629 um2 against 14,610 um2 of M3-M7 obstruction in the classic kit (-82%). So proposal 3 removes that quarter. The other two thirds are inside pair boxes: `u_pvg2_p0` 3,199, `u_pvg1_p3` 2,747, `u_pvg3_p2` 2,407, `u_pvg3_p0` 2,088 (4 of 16 pairs = 10,441); 75% horizontal; 3,729 zero-capacity markers are more than 20 um inside the box. Nets on those markers: `u_cland_ft*_i/u_ring.dch[].u_dsel` 4,433, `u_ft_ft*_o_*` 2,545, `u_cland_ft*_i` 1,623, pad `u_pd*_i_vport_*` registers about 1,600. This is ft feed-through and pad traffic crossing the pair cores on the layers the core leaves, not a reserved-site effect.
- pc (not measured): the cancelled pc_v1 / hg_v1p6 / hgi_v2 containers and their reports are gone (V: no `congestion-*.rpt` left under the epyc7 / epyc10 wave attempts). R3 pc rows: 2,657 die-clock rects on 6 types, stack area 10,196 of 30,086 um2 = 34% stays M3-M7 blocked, the highest share of any family (pv 25%, hg 19%, hgi 14%). The 102 `channel_keepout` rects (110,244 um2) are GPL-only placement blockages (gen_phys line 4652), not routing walls.
- R3 row report (V, `p3_rows.report.json`): 56 types, 28,628 -> 17,031 rects, walls 0. "walls 0" is the row tool's own geometric test; it says nothing about core boxes.

Family-wide answer: yes for hg / hgi (19 types), partly for pv (16 types, about a quarter of the overflow), unknown for pc (6) and hub / io / sys (no GRT data on either form).

## 2. krsp h1 against h2 (kv3_hg_v1p6, D25e GEN kit + rls rows, intel2 opus-kv-hg)

| | h1 (krsp unmoved) | h2 (krsp south) |
|---|---|---|
| Post-CTS TT setup wns / tns (V) | -577.21 / -102,622 | -548.25 / -193,145 |
| After TT repair (V) | -537.7 (still running, endpoint `u_ep.u_sc0/w_ce_in`) | -546.69 / -183,859 (958 cells added) |
| Post-CTS hold ws (V) | -209.26 | -213.66 |
| Pre-GRT FF hold (V) | not reached | -194.86, 2,617 ends: cross_tap 1,862, port_in 651 (-116.6), same_tap 104 (-21.5) |
| GRT iteration 5 | not reached | not reached |

Worst setup paths (V, `4_cts_post_hook.rpt`):
- h1 -577.21: `u_astk_u_strip..u_ep.sc_v` -> macro `u_ep.u_sc0` (w_ce_in), 30 cells, launch 281 ps, arrival 1,637 ps: 1,356 ps of buffered wire from one control flop to a memory pin.
- h2 -548.25: `u_ep.eo_q[1]` -> `u_er..u_owner.fault`, 26 cells, 1,349 ps; -414 on `u_owner.response_data[235/252]`. h2 second: the same `sc_v -> u_sc0` at -523.9.
- h1 next class -371 / -366 / -354: `u_cland_i_head_Q_N_N__u_fts_s_b/u_ring.dch[0].u_dsel/y[]` -> `u_bin_i_head..q[]` and the `hst_Q` twin, 27 to 28 cells: the bin rank is not at the landing output.
- The reset recovery path I opened (`rn_q -> u_exp..u_cc.q[52]/RESETN`) is in the asynchronous group at 956 ps arrival against 1,078 required; the first recovery check is MET +115. KV-PLAN-R1 09:30 named reset recovery as the worst path; the report says data paths.

Reading: the 29 ps wns difference is two different astk paths, not the krsp site. h2 doubles TNS and needs the die clock tree re-run. Neither form can sign: both are below -300 after repair. They are proofs for GRT congestion only; keep them to GRT iteration 5 for the 8.64 um gap question, then stop reading them for timing. D26 = h1.

## 3. Hold at 833 ps after the lockups

**Head-core fronts (hgi, kR retained GRT ODB 477b6b4aaede, epyc9 `fable-kv-hg0/kR_readback/FF.endpoints.tsv`, V).** 5,293 negative FF ends. 5,105 reg -> macro on `u_head3_e0/e2/e4/e6`, `u_head2_e2/e6`; `u_head3_e4` is master `kv3_head_eighth_e6`, so the three masters in `apply_cil.py` cover all six instances. Port coverage of the R3 list: 5,083 ends covered (q_data_in 3,054, row_in 1,347, kp_in 421, the rest 261). **Not covered: 22 ends on 16 `rst_n` pins** (`g_front_N_u_front__rst_n`, `g_t_N_u_stk__rst_n`, `g_t_N_u_stin__rst_n`, `u_kt__rst_n`), worst -250.80 ps on e2, -128.3 on e0, -56.9 on e6, launched from `u_rs_ri_head*_u_score_rst_n_r*`.

Margin of the latch form (I, from the worst end): launch/capture skew 247.55 + library hold 118.96 = 366.5 ps; half period 416.5 ps. A transparent-low latch on the launch clock gives at least +50 ps before its own delay and the wire to the pin. That holds only while skew + hold stays under 416 ps; the die-level ETM insertion of the head core (167 ps pin arc) is inside that sum. Not measured on a built kit: R3 has no kit yet.

Remaining 188 non-macro ends (V): port -> `u_cland_i_ectl_Q_N_eN/u_ring.s_d` 131 (-29.0), `rls_b` reg -> reg 23 (-10.4), port -> `u_rst_in` / `u_run_in` (-56), `u_kst.kp_o` 4 (-25.9). All inside the in_min -75 contract or small enough for the 3 ECO passes.

**hg with astk strip (h1 / h2, V).** Post-CTS hold -209 / -214 is reg -> reg, one cell, inside `u_astk_u_strip..u_ep` (`line[] -> line[]`, `zq[] -> row_in[]`, `u_cd.q -> s2_code`): launch clock 223 to 229 ps, capture clock 454 to 469 ps. Cause (V, `4_1_cts.log`): `OT_CLOCK_TAPS cap 1200 sinks/tap: 8,666 sinks re-assigned` (h2 8,885). clk_t27 goes 47 -> 888 sinks, clk_t28 1,020 -> 1,200; their sink boxes are 361 / 565 um (h1) and 588 / 582 um (h2) against the 300 um limit, and their trees arrive at 468 (h1 t28) and 516 / 414 ps (h2 t27 / t28) against the 250 target. clk_t33 still holds 9,046 sinks and clk_t29 7,570 after the cap. 35 of 51 taps are over the 300 um span. The lockups do nothing here; hold buffers on 1,862 ends at about 200 ps each will repeat the kR result (hold repair eats setup).

Answer: after R3 the head-core class closes by structure with about +50 ps (inferred), minus the 22 reset-pin ends. Hold at 833 ps is not closed on the astk types until the tap rows change.

## 4. Other R3 contents

- N3 (hgi_v1 x2 section N, V `n3_check.log`): 27 hops, max 299.0 um, 4 hops at 295 to 299; 1,936 plan stations checked, 0 close sites. Correct. Margin to the 300 cap is 1 um on `hst3_ftg -> rls3_a`; legalisation can push it over. Advisory only.
- pack_fault D=1 (V, TT readback): the one real TT end, -149.77, `u_head3_e6/pack_fault -> u_head3_u_score.u_rof`. The row is on the right leaf. The other 50 TT ends are `ft2_i` port -> `u_cland_ft2_i/d` to -54.3 on missing-route nets.
- pv station 300 and trunk anchor c6ab8bd7be: not verifiable on a kit yet (v8k on epyc7 is in floorplan). `pv_station300.py` names c77d5b890f in its comment; that sha is not in `rt/current`, c6ab8bd7be is. Comment only; the gate checks the right three.

## 5. Residual fixes for D27, ranked (owner KV-PLAN-R1)

| # | Fix | Evidence | Types | Form |
|---|---|---|---|---|
| 1 | astk strip setup: register the `sc_v -> u_sc0` memory control at the macro pin; one stage on `u_ep.eo_q -> u_owner.fault / response_data`; seat the `u_bin_i_head_Q / hst_Q` rank at the landing output, then re-scan | section 2: -577 / -548 / -371, 25 to 30 cells | hg family with astk (v1p6 measured; check the other 7) | registered memory + pipeline rows, +cycles pre-approved; seat first, stage second |
| 2 | astk tap rows: taps so that the 1,200 cap holds without re-assigning across 300 um; `u_ep` flops on one tap or neighbour taps of equal depth; split clk_t33 (9,046) and clk_t29 (7,570) | section 3: 1,862 ends -195 FF, t27 / t28 span 565 to 588 um | same | DIE-CORETAP / clock rows; no hold-buffer ECO |
| 3 | add the 16 head-core `rst_n` ports to `clock.core_input_lockup` (or launch the last reset relay on the core tap) | section 3: 22 ends to -250.8 | 19 hg / hgi | amend R3 before the gate admits if it costs no cut time; else D27 |
| 4 | pv over-core traffic: ft ring / `ft_o` feed-through and vport pad registers routed in the channels, stations sited so no hop crosses a pair box; first check the D26 tree (pvsnake3) on v8k at GRT iteration 5 with the section 1 classifier | section 1: 67% in pair boxes, 4 pairs 10,441 | 16 pv | station / region rows; no core re-shape |
| 5 | pc: classify the first D26 pc GRT iteration 5 (reserved stack / core box / open) before any pc row; stack share 34% | section 1 | 6 pc | estimator |
| 6 | hgi residual: `clk_c8` and one `rst_n` relay net inside `u_head2_e0` at (185, 125): check the clock tap pin stack at DRT on the first R3 kit | k13i final 4 markers | hg / hgi | check, then tap-pin row if DRT fails |
| 7 | hg / hgi superset pinout (union links) | R, FABLE-SUPERSET 01:59 | 19 -> fewer masters | after 1 to 3 |
| 8 | krsp south site | section 2: no gain | - | only if GRT iteration 5 shows the 8.64 um gap as a wall |

## 6. Stop list

- No hg type with the astk strip to route before fixes 1 and 2 are in a plan: both forms sit at -537 / -547 after repair and -195 FF hold on 1,862 ends.
- No h2 (krsp south) row in D26 or D27 on timing grounds; no die-clock re-run for it.
- No reading of proposal 3 as the pv or pc congestion fix; no pv wave on the expectation that the split rows clear GRT.
- No hold-buffer ECO on the astk cross-tap class or on the head-core fronts; no late-repair retry of kR / k13i (-310 / -416).
- No "walls 0" from the row tool quoted as a congestion result.
- No claim that hold is closed on hgi before a built R3 kit reports the FF pin class; the +50 ps is arithmetic.
- No more GRT iterations on a classic-form hg / hgi / pv kit (k13ci is flat at 10.2k, 99% zero-capacity).
- No N3 hop re-site below 299 um unless the built kit measures a hop over 300.

## 7. Not checked

- pc, hub, io, sys congestion on either form; hg_v1p6 and hgi_v2 wave reports (deleted with the containers).
- The other 7 hg types for the astk paths. kR (hgi_v1) has no astk end in its FF list; not confirmed for every hgi type.
- Which clock the bind gives the `ot_dp_lk` latch; the margin above assumes the launch tap.
- R3 strict / G0 / LATCHECK (gate not started). The +2 cycles of N3 and +1 status cycle of pack_fault against token latency.
- pv station 300 and the trunk anchor on a built kit; the pv_v8 read is the D23H tree, not pvsnake3.
- h1 / h2 at GRT; the 8.64 um gap.
