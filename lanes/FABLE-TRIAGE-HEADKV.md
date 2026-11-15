# FABLE-TRIAGE-HEADKV 2026-11-15 00:5x PST: HEAD (s81_head) and KV (qwen_kvsys) failures, and checks of tonight's claims

Scope: technical PD only. Read-only on every lane directory. One small run of my own (epyc2
`/srv/opentallas-scratch3/claude/fable-triage-headkv/sta_ca_proofca3`, 3 min, 0.8 GB). No kit, plan or job was touched.
Not redone: FABLE-PD-HEAD-CLK, FABLE-ROUTE, FABLE-KVOVF, FABLE-CLOSURE-STRATEGY.

Status words: MEASURED = read from a log, DB record, lib, RTL or my run. INFERENCE = fits the numbers, not proven.
State of the running jobs is as of 00:45 PST.

## 0. Short answer

1. HEAD count-aligned clock passes on both edges: 427 of 427 crossings, depth 4 on all of them, start tree 1,556 of 1,556
   clean. The "start-skew 1,556 FAIL" was the chain script timing against the wrong proof (section 2a4).
2. HEAD-99's partial re-bind (rp21z20NC) mixes two count frames. Of the 262 ports adopted from the rise-only plan, 248
   have a different K and 35 a different latency in the both-edge plan. Do not bind it. Re-bind all 427 once (2c).
3. The HEAD die route has not passed yet. Four earlier attempts ended in errors; two runs are in detail route now (2a1).
4. KV: three follow-up jobs (route rerun, count-aligned STA, seam check) failed because ot-run sent them to a host
   without the run directory. None of them has a result (2b).
5. Six "CRASH/flow-error exit 1" kit failures tonight are not crashes. They are placement geometry checks that failed
   after a clean place stage (mechanism M1).
6. kp4_dchn: the 73 ps audit row does not move with clock depth. One fix for HEAD and S81: an input face register inside
   the core (M6).

## 1. Failures since 11-14 21:00, by mechanism

Counts from `tools/failure_breakdown.py` at 00:25: HEAD cores 3/5 signed, types 19/26; KV cores 34/34, types 5/56
(47 running).

| # | mechanism | kits (MEASURED) | root cause, numbers | fix | owner |
|---|---|---|---|---|---|
| M1 | place geometry check reported as crash | kv3_hgi_v3 a7, hgi_v4 a5, hgi_v1 cl141 a10, hgi_v1 cl42 a10, kv3_io_cor a2, hd_spn_end a8 | place ends rc 0 (physical_completion goal place), then `geom/auto_geom.json` verdict FAIL; the wave prints "exit 1". hgi: channel_h 1.47-2.24 (hard 1.0), pin_reg_p90 313-385 um (limit 30), r2r up to 2,425 um, relay_collapse 16-182. io_cor: col_v 1.20, clock_reach 223 vs 220. hd_spn_end: pin_reg_p90 32.75 vs 30, r2r 711 um x2, empty 0.96 | (a) label these GEOM-FAIL with the reason list, not CRASH; (b) only channel_h / col_v above 1.0 stops a kit (it predicts GRT overflow); the rest is advisory (owner academic profile); (c) hgi is the FABLE-KVOVF bank merge, no relaunch before r_hgi2 / r_hg report | KIT-OPS-6 (label, gate); KV-102 + TYPE-KVHGI2 (hgi); TYPE-KVIOCOR (io_cor) |
| M2 | DRT-0255, maze route finds no path | hd_ctl a6 (net f2d[390], box 94.6,158.5), kv3_io_cor_v1 a4 (u_cland_ft19_i, box 964.4,54.7) | both attempts run on an old plan (head_rp21z4_1113, kvgeom4) without the PG pin-band keepout: cells under M5 x M6 PG crossings have no pin access | no relaunch on the old plans; relaunch on rp21z20 / kvgeom6 with PG-PINBAND-1's keepout (its proof: band cells 2,183 -> 0 on hd_spn) | PG-PINBAND-1 (merge), KIT-OPS-5 (relaunch) |
| M3 | client lost, logs idle 3 h | kv3_hg_v3 a14, pv_v8 a5, hgi_v5 a6, hgi_v1 cl141 a8, hgi_v2 a7, kv3_hgi a8 (all epyc2, 21:44-22:22) | one host event on epyc2, not six design failures. All are kvgeom4 or kv102sem attempts, i.e. plans already replaced | do not re-queue: kvgeom6 relaunches cover them | KIT-OPS-5 |
| M4 | GRT congestion | kv3_hgi_v1 cl42 a9 (kvgeom4) | hg/hgi front-core bank merge | FABLE-KVOVF | TYPE-KVHGI2 |
| M5 | post-route repair over the 6 h cap | kv3_sys_c | hold -281.6 ps, 679 endpoints left, worst u_ucie_rom/tx_flit[258]: the tap cap pass moved the ROM clock pin (clock_taps.tcl line 236) | KV-102 guard branch claude/kv-102-macropin-guard-1114 @426728e16ed; then one CTS-only proof from the placed DB | KV-102, ROOT-MERGE-63 |
| M6 | boundary arc inside a hard core | hd_serdes / ot_s81_kp4_dchn (audit FAIL 73 ps), 11 S81 rows | inputs are not registered at the pin: k_v selects 620 flops, k_lo runs a constant multiplier; about 600 ps pin to flop. clk->q + setup = 760 ps for any insertion (lib e240e3b28304: insertion 285-341, setup k_v 310 / k_lo 240, hold k_lo 177) | face register on all 320 input bits inside dchn, DD 55 -> 56 in the decoder, +1 cycle on the rx lanes, standard early tap. HEAD interim without RTL: tap u_chn/clk 200 ps early (window -263..-127) | S81-RESIGN-DEEP (RTL + re-sign); HEAD-REMAP-1 (tap); HEAD-BIND-1, DIE-S81-92 (pricing) |
| M7 | stopped from outside | hd_host_e a13 (exit 143) | STOPLIST-2120, intended | none; hd_host_e continues as form B (2d) | HEAD-EPC-RTL-1 |
| M8 | synchronous seam hold, real views | mesh0S -> mesh0S_estrip m_rx_ft_i 65 bits -31.7 TT / -52.7 FF; mesh7N -14.0 FF; ctl -> ctl_estrip n_tx_ft_i -11.4 FF; ctl -> ctl_nstrip unit_ft_i -1.7 FF | strip partitions sit in the same clock region as their parent but their taps arrive 27-80 ps later; zero-logic ft seam | move the strip tap to the sender's tap group or add receiver hold padding in the strip type (65-bit bus, about 55 ps) | HEAD-99 (plan tap), type owner of hd_mesh_e / hd_ctl_e |

The two cores without a wave row (s81hd_elemA_cv, elemB_cv, owner S81-HEAD) have had no job for more than 6 h. They
block hd_tile re-timing (HEAD-99 waits for their libs). They need a live lane today.

## 2. Verdicts on the claims

### (a) DIE-HEAD-ROUTE-1 (epyc2 die-head-route-1, plan rp21z16)

**a1. "The die route passes": NOT SHOWN.** MEASURED:

| run | PG | result |
|---|---|---|
| p16/drt_TT (22:38) | none | DRT-0073, no access point for nst4/arst_n |
| p16/drt_clk_TT (22:43) | none | openroad exit 1 after guides |
| p16g/drt3_clk_TT (23:01) | hand-built die-wide M8/M9 stripes | DRT-0155 |
| p16g/drt3_clk_TT rerun (00:14) | hand-built stripes | past guides and track assignment; detail route iteration 0 for 30 min, 20 threads, 155 GB; no violation count yet |
| p16g/drt4_pdn2_TT (00:24) | pdn2 region grids | pdngen 498 s, 358 of 358 macros in a grid; GRT same as drt3 (4,972 nets, 2.467 m, overflow 0); entering detail route |

- What is routed is the clock tree (4,971 nets) and rst_n. The 48,400 ft slot nets are set special and skipped, which
  is right (FABLE-ROUTE). Say "die clock route", not "die route".
- GRT is clean in every run: 0 overflow, clock usage M8 0.02 %, M9 0.03 %.
- Hazard: `drt3_clk_TT/die_top_routed.odb` and `.def` are from the failed 23:01 run (written after the caught error).
  The same holds for KV `runs/p1/die_top_routed.odb` (identical size to die_grt.odb, DRT-0509). Neither is a routed
  DB. Delete or rename before anything reads them.
- The hand-built stripes run on top of `obs.tcl` (38,134 M8 obstruction strips that already model the PG), so PG is
  counted twice on M8. Harmless at 0.02 % use, but it is not the comparison to keep. Keep pdn2; drop the hand-built form.

**a2. "M1-M9 clock guide fix": CORRECT so far, unproven by DRC.** GRT runs with `-signal M4-M7 -clock M8-M9` on
coarse 0.72 um M1-M3 tracks. Before detail route the script rebuilds the real M1-M3 tracks and sets M1-M9. The rerun
got past the point where 23:01 failed. Two limits: more than 1,000 DRT-0422 warnings (tap pins `t_*__clk_t*` have no
track through their centre, off-track access), and 155 GB RSS for 4,972 nets. KV's `shared/tail.tcl` does not have
this block: KV will hit DRT-0155 or DRT-0073 on its 32,281 clock nets. Port the block to the shared script first.

**a3. "15-view real STA (TT setup -524, hold -1,850) is landed-dominated": CONFIRMED.** MEASURED from
`p16v/real_sta_15/run/die_sta.json`, 1,182 seam groups, by launch-to-capture tap offset:

| offset | groups | paths | setup neg / worst | hold neg / worst (TT) |
|---|---|---|---|---|
| <= 100 ps | 144 | 22,763 | 0 / +412 | 65 / -31.7 |
| 100-416 ps | 401 | 81,280 | 0 / +172 | 54,733 / -399 |
| > 416 ps | 565 | 95,438 | 6,102 / -524 | 40,189 / -1,850 |

All 6,102 setup failures and the worst hold sit where the two taps are more than half a period apart. `die_sta.py`
in ilm mode times every crossing as one synchronous cycle; it has no count-aligned class. So:
- The 19-view rerun (running, TT at 00:45) will print the same headline. Read it by class, not by the worst number.
- The worst hold rows are `start_i` and `arst_n` (357 groups each, 183 with offset above 416 ps). arst_n ends in a
  reset synchroniser (false path by design). start_i is judged by the start tree of the count-aligned plan (clean,
  a4), not by this run.
- The real content is the synchronous class: setup at least +412 ps, hold -31.7 TT / -52.7 FF on four ft seams (M8).
- Tool gap: `die_sta.py` needs the plan's landing edges as a class (exclude from the single-cycle gate, report
  separately). Until then its verdict line "FAIL" on HEAD means nothing. Owner KIT-OPS-6.
- 11 of 26 types are still stand-in views (hd_ctl, host_e, host_w, lep0N, mesh, serdes, spn; 4 more get real views
  in the 19-view run).

**a4. "Both-edge CA chain": the physics PASSES; the chain has two wiring defects.** MEASURED:
- Readout: 13,090 fall taps and 44,917 fall nodes, both corners.
- Plan (`p16r/ca3/out/plan.json`): 427 crossings, depth 4 on 427, depth 8 on 0, fail 0, worst margin 113.3 ps
  (sp_x5__0), below 100 ps: 0; start tree 1,556 edges clean (1,222 on the fall edge), 2,000 chips 0 violations.
- Defect 1: `count_align_bind` stops in strap_ties on coll_WN3_d__0 (hd_ctl_n.w3d_i): the ring's write register adds
  a cycle that the sidecar does not declare. bind.json is written before that check, so the strap part is unchecked.
  HEAD-99 is fixing the sidecar (sched_lat +1, freg 1).
- Defect 2: the last step times the bind against `p16r/proof` (rise-only, nodes named h4, h40...). The bind's start
  ports name nodes of `ca3/out/proof`. Found: 1 of 1,435 start nodes, so all 1,556 start ports fail closed with
  reason "no taps". My rerun with only the proof changed: TT PASS, FF PASS, crossings 427, slot-read 0, guard 0,
  start-skew fail 0 of 1,556, worst lo 211.9 / 151.2 ps, smallest start sync distance 157.4 / 149.4 ps (aperture 26.5).
- Fix: both_ca.sh uses `$D/ca3/out/proof`; KIT-OPS-6's die_chain_ca.sh must pass the proof the plan step wrote.
- Limit: declared core insertion (450 / 380), no built ring clocks. SS-INFO (TT x 1.27) keeps 8 lag and 2 slot-read
  fails, information only.

### (b) DIE-KV-ROUTE-1 (epyc7 die-kv-route-1, kvgeom5 plan_c)

**b1. "pdn2 per-region macro grids": CORRECT.** pdngen 335 s, no PDN-0233, 160 of 160 partition instances in a grid
(ot_pg_0 153, others 1-2, ot_pg_10 0), 5 ring strips under 40 um dropped. The same script built HEAD (358 of 358).

**b2. "Net classification": CORRECT, with one consequence.** MEASURED: 202,491 signal nets = 32,281 clock tree
+ 170,209 ft slot nets (both pins on one instance) + 1 port net; two-pin abutted 0, gap 0, multi-pin 0. GRT: 32,282
nets, overflow 0, 9 min, 11 GB. The 3,915 inter-partition ports (602,002 bits) are not in route.v, so nothing in the
routed DB checks them. That is by design, and it makes the seam check the only physical evidence for those bits.

**b3. "New seamchk": the check is right; it has not run, and on this kit it would prove nothing new.**
- Not run: the standalone job went to epyc9, which has no `asm/` (STA-0340, SEAMCHK 1). The route rerun went there
  too (FAIL_NOASM 08:24 UTC), and so did the count-aligned STA (LPO, CA, CABIND all FileNotFound). The run directory
  exists only on epyc7. The post "route + DRT rerunning, count-aligned STA running" is wrong: nothing is running.
  Fix: run the three steps on the host that holds runs/p1 (this is run state, not a kit), or rsync runs/p1 first.
- p1 uses plan-shape abstracts. Their pins are generated from the same plan tables that abutted_pin_check reads, so
  seamchk on p1 repeats the arithmetic. It only tests something on signed LEFs: 5 of 56 types have one
  (kv3_phy, phy_v1, sys_SD, sys_SD_v1, io_ft; epyc8 `views/`). Run it on the kv5_signed kit and report coverage as
  "bits with both ends signed".
- Script gaps: a missing instance makes `$A findITerm` abort the run (guard NULL); bit i is paired with bit i, so the
  ft enable bit must be in `port_pins_count` (HEAD: plan width 565, pin bus 566; check the bit count against the LEF
  bus width); "touching" accepts any overlap, so add a count of pins that also touch a second neighbour pin.
- The earlier KV landed FAIL (-312 / -162 ps) is the same wrong check as HEAD's. `ca_p1.sh` is the right chain; the KV
  kit already has fall taps (10,572 fall taps, 32,408 fall nodes), so no depth inflation is expected.

### (c) HEAD-99 CA re-bind: HOLD of the 165 depth-8 rings CORRECT; ADOPTION of the 262 now WRONG

MEASURED, rise-only plan (fable-pd-head-clk/ca2) against both-edge plan (p16r/ca3), per port:

| group | ports | same K and latency | K differs | latency differs |
|---|---|---|---|---|
| depth 4 in both (adopted in rp21z20NC) | 262 | 13 | 248 | 35 (33 x -1, 2 x -2) |
| depth 8 rise-only, depth 4 both-edge (held) | 165 | 0 | 165 | 139 |

- Holding the 165 was right: on both edges none needs depth 8, so hd_tile keeps DEPTH 4 and its RTL.
- Adopting the 262 from the rise-only plan was not safe. K comes from the start tree, and 1,222 of 1,556 start edges
  move to the fall edge. rp21z20NC carries new K on 262 ports and old K on 165: two count frames in one plan.
- Do: discard the CA part of rp21z20NC; after the freg fix re-bind all 427 ports from `ca3/out/plan.json`, then
  `gen.py latency --inplace`, G0, LATCHECK. Latency improves: histogram 1:15, 2:216, 3:186, 4:10 (rise-only had 144
  ports at 4-5 cycles). If HEAD-REMAP-1 moves any partition origin, the clock and this plan must be rebuilt first.

### (d) HEAD-EPC-RTL-1 form B: SOUND; one open side

MEASURED: 2-entry slice between the u_ski read data and the endpoint in_data (define OT_HE_EPC_ISLICE); ir_g now
comes from registered state. Simulation gold against slice, with and without impairments: err 0, same delivered
stream. Lane coll_HOST1_d: table 6, delivered 4, fixed in core 2, PASS. The 34 LATCHECK failures in bindrun/B1 are
the station lanes that rp21z16 never priced (chE/chW/sp, +1..+6); they are not form B's. Build dpkit-hd_host_e is
running on epyc7.
- "+0-2 cycles, priced +1": correct. The slice adds exactly 1 cycle when it is empty; 0-2 is its occupancy under
  back-pressure, which the credit loop absorbs.
- INFERENCE, timing: before, SRAM launch 442 + clk->q 250 + 580 of data = 1,271 against 1,097 required (-173). With
  one slice the two stages have 1,097 + 833 = 1,930 ps for about 1,610: about +160 ps per stage if the slice flops
  sit midway on the 552 um run. If the placer keeps them at the SRAM, the second stage is about -85. Check the
  placed position of isl_d0 / isl_d1 before route.
- Open: the u_epc OUTPUT side (-85 ps, 19 endpoints with the signed lib) is not touched by form B. WITHDRAWN: my
  first text proposed a u_epc tap 45-60 ps earlier. That is not buildable (the pin is already 20 ps after its die
  tap) and not needed; see section 8.
- Base: the kit is built on rp21z16e. Rebase on rp21z20 before it counts.

### (e) KV canary 2 CTS warnings: REAL, but the 1,200 cap is the wrong lever

MEASURED (epyc2 kv-102/ctscan2, kv3_pc cl254f2e73, CTS still running at 00:45):
- Four taps are over the cap, not three: clk_t1 2,007, clk_t10 3,225, clk_t4 11,302, clk_t7 10,061.
- The cap cannot hold by count: 47,154 sinks on 27 taps is 1,746 per tap; 27 x 1,200 = 32,400.
- First balance pass, target 250 ps: the over-cap taps are fine: clk_t4 241 (223-262), clk_t7 279 (266-313), clk_t1
  176, clk_t10 185; spread inside each at most 47 ps. The outliers are taps filled to exactly 1,200 by sinks pushed
  from up to 200 um away: clk_t24 378 (367-489), clk_t25 314, clk_t11 304.
- So the cap pass (5,274 sinks re-assigned) creates the long local trees it was meant to prevent. One 11k-sink tap
  builds a 240-280 ps tree with 40-47 ps spread.
- The four big taps are one column (x 517.9, y 190 / 570 / 950 / 1,330, 380 um pitch).
- Fix, in order: (1) set OT_TAP_MAX_SINKS back to 3,000 for kv3_pc (clk_t1 and clk_t10 are then legal, far fewer
  sinks are pushed out); (2) add taps in the x 518 column at half pitch (190 um) between y 380 and 1,140, which
  splits clk_t4 and clk_t7 into about 4 taps of 5k each; do not make the pitch finer over the whole type.
- Core taps: clk_c0..c3 read 250 (pin 62-68 ps early + internal 312-318), on target. clk_c4..c7 (pcf cores) read
  193-196, 54-57 ps early with early_ps 0: they need 55 ps of delay on their tap, or they fail the 20 ps window.
- The eight "WARN core tap clk_cN: no clock pin ... on clk" lines are harmless here (the pins are already on their
  tap nets; each tap shows 1 sink). The message should say so.
- Owner KV-102. Verdict on the canary itself only after its final OT_TAP_CORE lines.

## 3. Stop list

1. rp21z20NC: no G0, prepare or bind (two count frames). HEAD-99.
2. Old-plan attempts still in the wave: HEAD head_rp21z4_1113 (hd_ctl a6, hd_spn_end a8 / a9 / a11; hd_spn_end is
   already signed and fails only advisory geometry numbers); KV kvgeom4 and kv102sem items. KIT-OPS-5.
3. kv3_hgi* relaunches before FABLE-KVOVF's r_hgi2 / r_hg report (4 place-geometry fails tonight, channel_h up to 2.24).
4. S81-RESIGN-DEEP shallow-CTS forms of kp4_dchn (already stopped): they cannot change the arc.
5. The hand-built-stripe die route form after the running drt3 ends: keep pdn2 only.
6. Any reader of `die_top_routed.odb` in p16g/drt3_clk_TT (23:01 copy) and KV runs/p1: not routed DBs.
7. Quoting `die_sta.py` ilm "FAIL" or the T/2 "landed FAIL" for HEAD or KV as a clock result.
8. KV seamchk on the plan-shape kit as evidence for abutment.
9. Lowering tap caps or tap pitch across whole KV types on the strength of the canary warnings.

## 4. Next steps, by lane

- DIE-HEAD-ROUTE-1: fix the proof path in both_ca.sh; report DRC for drt4_pdn2 by layer and location; remove the stale
  routed DBs; rerun on rp21z20 once it is bound.
- HEAD-99 + HEAD-REMAP-1: one re-bind of 427 ports in the partition-origin form (section 11), 18 freg ports;
  u_chn early branch (-200 ps, section 8), no u_epc tap; re-sign hd_mesh_e and hd_ctl_e for the strip seams (section 9).
- KIT-OPS-6: die_chain_ca.sh proof path; landed class in die_sta.py; GEOM-FAIL label and advisory rule (M1).
- DIE-KV-ROUTE-1: run route, CA and seamchk where runs/p1 lives; port the M1-M3 track block; seamchk on signed views.
- KV-102: tap cap 3,000 and the x 518 half-pitch taps; 55 ps on the pcf core taps; sys_c guard merge.
- S81-RESIGN-DEEP: kp4_dchn face register + DD 56, one re-sign.
- HEAD-EPC-RTL-1: check slice flop placement, read the output side on the signed lib, rebase on rp21z20.

## 5. HEAD cores elemA / elemB (questions opened in this file by CORES-NOROW-1, 00:55 PST)

This file was first created by CORES-NOROW-1 (commit aeeb1d6633a). Its two items are kept in section 6 and answered here.
Kits: `/srv/opentallas-scratch2/claude/type-hdcore-elemab/runs2/` (A2, B2 read on epyc9).

### 5.1 elemA A2 pin_audit, 10 pins wrong_place: the PINS ARE RIGHT, the kit's pins.json is wrong

MEASURED: the 10 pins (ft_ck0_i/o, ft_ck1_i/o, ft_mesh_i/o, ft_mstrap_i, ft_rst_i/o, rst_n) are M5 0.192 um squares
at the core centre. All 10 rectangles in the routed A2 DB are identical, to the nanometre, to the rectangles in the
macro LEF that the parent uses (epyc7 head-99/kits21z16/g_hd_tile/hd_tile/macros/ot_s81hd_elemA_cv.lef; for example
ft_ck0_i 157.584 163.344 157.776 163.536 in both). They also equal the kit's own io.tcl. Only pins.json disagrees:
it lists them on the N / S / E face (ft_ck0_i at y 319.68). face_guard.json already skips exactly these 10 names.
- Verdict: do not move the pins. A face position would break the bind to hd_tile, which is built on the interior LEF.
- Do not add a blanket ft exemption either. `pin_audit_core.py` already checks interior pins at their exact (x, y)
  when the row's face is not N/E/S/W. Fix the generator so pins.json writes these rows as face "island" with the
  io.tcl centre; the audit then checks them strictly and passes. Its INTERIOR name pattern covers ft_ck / ft_rst but
  not ft_mesh_*, ft_mstrap_i or rst_n: the generated rows are the place to fix that, not the pattern.
- Tonight: the audit result is 456 of 466 on the face rows plus 10 of 10 equal to the parent LEF. That is a pass on
  substance; run signoff GOAL=post on A2 / A1 with pin_audit advisory for these 10 names. Same for elemB.
- Owner: CORES-NOROW-1 (signoff now); KIT-OPS-6 (pins.json generator for hard cores with centre ft squares).

### 5.2 elemB B1/B2 "KEEP FAIL" and elemA A2 "NOT EQUIVALENT": two different things

**(i) The 8 kept bits (B only): keep-list artefact.** MEASURED: 8 of 150 declared kept bits are missing, all
`g_t[6]` and `g_t[7]` `.g_pad.u_a.g_cy_copy.cyq[0..3]`. `cyq` is `(* keep = 1 *)` in ot_v41_fadd.sv line 197, so every
adder instance declares it. g_t[6] and g_t[7] are pad adders; the other 142 bits are present. The keep list is per
module, the folding is per instance. Fix: drop keep rows for g_pad instances from the declared list (or mark them
"may fold"). No RTL or synthesis change.

**(ii) The 107 (A2) / 168 (B2) differing points: most likely a LEC window limit, not a design difference.** MEASURED:
- Same points in both cores: `u_a.y[*]`, `u_a.err[*]`, `g_s9.man_q[*]` in four adder instances
  (g_ch[0].g_s[0], g_ch[1].g_s[0], g_t[*].g_pair, u_pair / g_join). Every failing cone is unmatched on the gold side
  only: `g_s9.byp_q`, `g_s9.exo_q[*]`, `g_s9.er_q[*]`, `u_c8.g_r.r[*]`. In the netlist exo_q and byp_q occur 0 times.
- g_s9 is the SPLIT9 pipeline stage of the adder: plain registers without reset, the ninth stage after u_c0..u_c8.
- The LEC accepts no-reset registers that settle to a constant, but only for OT_LEC_RELEASE_EDGES = 8 edges
  (lec.py line 4923). Its release list for these same four instances stops exactly there: u_c5 at edge 5, u_c6 at 6,
  u_c7 at 7, u_c8 at 8. g_s9 settles at edge 9 and y at edge 10: one and two edges past the window.
- INFERENCE: synthesis folded the constant bits of the ninth stage (correct for these constant-operand instances),
  the LEC cannot see them as constant, calls them "removed although not constant", and y differs through them.
  This also explains why the earlier signed elemA / elemB passed (no SPLIT9 stage).
- Deciding test (about 1.7 h, 48 GB, no build): rerun lec.py on A2 and B2 with OT_LEC_RELEASE_EDGES=12. Expected:
  A2 EQUIVALENT; B2 down to the 8 keep rows of (i). If points still differ, it is real and the adder goes to an RTL
  lane with the first differing y cone.
- Until the test is back: letting B1r / B2r route with LEC advisory is acceptable (the checkpoint is reusable), but
  neither core counts as signed on an open LEC. LEC is not one of the advisory gates when points differ.
- Owner: CORES-NOROW-1 (rerun); KIT-OPS-6 (default window = longest no-reset pipeline depth + 2, taken from the kit).

## 6. Original items from CORES-NOROW-1 (commit aeeb1d6633a, restored)

- 2026-11-15 00:55 PST HDCORE elemA_cv pin_audit: 10 interior ft/rst_n pins read as wrong_place. Evidence: epyc9
  runs2/A2/kit/pin_audit.json (routed 6_final.odb exists, 06:33 UTC): PIN_AUDIT FAIL 456/466 missing 0 wrong_layer 0
  wrong_place 10 extra 0. The audit expects them on the die face; the kit places the M5 0.192 squares inside the core
  (y 156-163, x 157-160). Question: exempt interior ft squares as face_guard does, or must they sit on the face?
  Not done by CORES-NOROW-1: no audit / kit edit. -> answered in 5.1.
- 2026-11-15 00:55 PST HDCORE pre-route LEC stops the flow. A2 NOT EQUIVALENT 107/58130 (u_core.u_m.g_ch[0].g_s[0].
  u_a.y[*]); B1/B2 KEEP FAIL 172/52669 (8 of 150 declared kept regs merged / folded). lec_async stops the flow
  container on exit 1. Action taken: B1r / B2r copies with LEC advisory, route resumed from 5_1_grt. Question: real
  RTL / synth difference or keypoint matching? Inputs runs2/{A2,B1,B2}/kit/lec/lec.json. -> answered in 5.2.

## 7. KV count-aligned bind and start-skew (kvgeom5 plan_c, epyc7 die-kv-route-1/runs/p1/gate), 01:1x PST

Two different sets fail, with one cause: KV still uses the data-port start tree.

**7.1 Bind simulation, 32 of 500 samples, minimum -208.9 ps: REAL, 14 ambiguous start edges.** MEASURED (ca.json,
bind.json): 159 start-tree edges, 145 clean, 14 `tree_ambiguous` (sync_values 2: the reset-release sample can land in
either of two cycles). The worst simulated port, L1102_3 (pc_WS_5 -> pc_WS_4), is one of the 14.
- 10 edges have a root-to-root phase of 500-660 ps: pc and phy `_5 -> _4` and `_1 -> _0` in the N/S/E/W quadrants
  (L1099_3/_7, L1101_3/_7, L1102_3, L668_3, L678_7, L689_3, L699_3) and hub_Wo -> hroot_WN (L1133_0). The TT-to-FF
  hull of that phase is 480-490 ps wide (L1102_3: sample window 341.1 to 832.0 ps), wider than half a period, so
  neither the rise nor the fall edge can sample it cleanly. Cause: feed delay between the two region roots.
- 4 edges pc_* -> phy_* (L1145_0, L1275_0, L1283_0, L1308_0) have phase near 0 (window -117 to +111 ps). The fall
  edge would be clean, but these crossings are among the 320 with no STA tap pair and no measured fall arrival, so
  the planner cannot use it.
- The planner absorbs the ambiguity downstream (458 ports carry 1 ambiguous cycle, 32 carry 2, 12 carry 3; 14 ports
  go to depth 8) but gives the 14 tree ports themselves 0 ambiguous cycles at depth 4. The simulation, which
  resolves the metastable sample both ways, breaks exactly there. Not K, not OCV spread on the rings: the plan's
  own Monte Carlo (0 of 300) does not model the two-way resolution.

**7.2 Start-skew 34 of 155 in TT (0 in FF): mostly the model, not these 14 pairs.** MEASURED (sta_fixed): every
failing row is a clean edge (sync_values 1) with source "model-coroute": skew is taken as the TT clk->q range
78.2-109.6 ps and fails when 109.6 exceeds the per-edge limit (79.0-108.8). The same rows pass the direct test on
the STA interval in 33 of 34 cases (sync distance 51.6-361 ps against the 26.5 ps aperture); one is really thin
(L2085_1 hgi_EN_6, 25.8 ps), two more are under 60 (L689_4 51.6, L133_0 54.7). The 10 ambiguous rows that STA can
see are reported ok, because the direct test is skipped for sync_values 2. So the 34 and the 32 are different
sets: the STA flags a conservative margin on clean edges and is blind to the edges that actually break.

**7.3 Fix: give KV the clock-form start tree that HEAD uses.** MEASURED, my run on the same inputs with
`count_align_plan --start-tree clock` (epyc7 /srv/opentallas-scratch2/claude/fable-triage-headkv/ca_clk.json,
bind_clk.json): 193 start edges, 193 clean, 0 ambiguous cycles anywhere, 3,915 of 3,915 crossings at depth 4 (0 at
depth 8), worst margin +109.4 / +765.1 ps, bind simulation 0 of 500 violations (minimum +109.4). It needs 32 retime
flops on clock-tree nodes and one start port per clock-tree edge.
- Count-aligned STA on that bind (same directory, sta_clk; MEASURED): start-skew fail 0 of 193 in TT and in FF,
  crossings fail 0, slot-read 0, guard 0, worst lo 190.0 / 203.7 ps. The verdict line still says FAIL for one
  remaining reason: 320 crossings have no STA tap pair ("no taps 320", the phy-side ports; they fail closed).
  That is a proof coverage gap in the clock kit, not a timing result: the die clock kit must emit taps for those
  partitions (owner DIE-KV-ROUTE-1).
- Owner: KV-102 (plan event: start form clock, start ports and retime stages via start_stage_emit; the plan
  already carries start_i / start_o ports); DIE-KV-ROUTE-1 switches ca_p1.sh to `--start-tree clock` and reruns.
- Not recommended: shortening the 10 feeds or padding per edge; it treats 14 rows and leaves the form.
- Tool items (KIT-OPS-6): die_sta_related must fail sync_values 2 start rows instead of passing them, and
  count_align_plan must count the ambiguity of a tree port on that port.

## 8. HEAD: early taps for u_epc and kp4_dchn (HEAD-99 question, 03:45 post)

Signed numbers (rtx-pro signed-export-1114 signoff.json and DEF):

| core | insertion TT min / mean / max | FF min / mean / max | clk pin (core frame) | in the type (z18 placement) |
|---|---|---|---|---|
| ot_s81hd_he_epc (u_epc) | 351 / 428 / 488 | 269 / 338 / 387 | M4, W face, (0.096, 223.992) | hd_host_e (423.456, 284.472) |
| ot_s81_kp4_dchn (u_chn) | 273 / 287 / 315 | 214 / 228 / 255 | M5, core centre, (138.36, 69.12) | hd_serdes (1106.04, 75.07); after the MY move x = origin + 138.12 |

- **u_epc: no tap, and I withdraw my "45-60 ps earlier" line in 2(d).** The pin already hangs on one buffer 20 ps
  after clk_t6 (TYPE-HDEPC), and 20 + 428 = 448 against registers at 442: the core is already aligned to within
  6 ps. An earlier pin would have to arrive before the die tap, which no in-type form can do. The -85 ps output
  side was measured on a DB placed against the stale lib. With the signed lib in the kit (form B build) the placer
  sees it. If it is still under -42 after that build, register the 19 output endpoints at the u_epc face
  (same slice form as B), not a tap.
- **kp4_dchn: no core_taps = early, no new kit port, no renumber.** u_chn is on pma_rck (kit sdc: its own clock
  port), not on the density taps. Use the form hd_host_e already has for u_epc: the core pin on its own buffer
  branch straight from the clock entry, and the registers on the tree. Target: pin 200 ps before the pma_rck
  registers (window 127-263). With the pin about 30 ps after the entry, the island's register latency must be
  160-290 ps; above that, add the difference as buffers on the u_chn branch. FABLE-SERDES-STRUCT item 2 is the
  same construction. If the kit generator can only make that branch through core_taps, the missing piece is a
  generator option "core branch from a named clock port", owner KIT-OPS-6; do not accept the renumber.
- After the face-register re-sign (M6) the target becomes "pin earlier by the new core insertion".

## 9. HEAD: the seven seam holds (15-view STA, FF)

| seam | FF hold | what it is | form |
|---|---|---|---|
| mesh0S -> mesh0S_estrip m_rx_ft_i (65 bits) | -52.7 | synchronous ft seam, tap offset 79.6 ps | receiver padding in the type, below |
| mesh7N -> mesh7N_estrip m_rx_ft_i | -14.0 | same type, same seam | same re-sign |
| ctl -> ctl_estrip n_tx_ft_i | -11.4 | synchronous ft seam, offset 27 ps | receiver padding in hd_ctl_e |
| tE3b3 -> tE3b4 arst_n / start_i | -61.3 | region crossing (offset 148.5 ps) | none |
| tE5o7 -> tE4b8, tE4o0 -> tE3b1, tW3o10 -> turnW3a (arst_n / start_i) | -27.4, -26.4, -3.4 | region crossings | none |

- The four reset / start rows need no hold form and no hd_tile re-sign. arst_n ends in the reset synchroniser
  (reset is held at least 64 cycles: false path). start_i between two tiles is a start-tree crossing; it is judged
  by the count-aligned start check, which passes on both edges (0 of 1,556, minimum sync distance 149 ps). In the
  15-view run hd_tile was also still a stand-in view. Exclude `*/arst_n` and `*/start_i` from the ilm seam gate.
- The three ft seams are inside the plan's own 90 ps seam window (offsets 27-80 ps), so the die-wide seam_hold is
  not too small; the receiving types do not deliver the padding it promises. Fix in the type, no plan key: re-sign
  hd_mesh_e (covers both mesh strips) and hd_ctl_e with the input-min constraint on the `*_ft_i` ports set for the
  full 90 ps window plus 10 ps, so the kit's hold repair inserts the delay cells (+0 cycles, no RTL). Both types are
  small (2-4k cells) and signed, so this is two short re-signs. Owner HEAD-99.
- Not ft_hop_lockup (a latch for 53 ps costs setup on a +680 ps seam for nothing), not core_input_lockup (no core),
  not a wider seam_hold (it would hit every seam).
- HOLD_SLACK_MARGIN 10 in the hd_host_e kits does not touch any of the seven; none is a host_e seam.
- Limit: the sender side of the two mesh seams (hd_mesh) is a stand-in view. Re-read after hd_mesh has a real view.

## 10. HEAD: 18 or 12 freg ports

18 is right, and both lanes now agree. `p16r/ca3/out/bind_fz.json` ends with 18 marked ports after 19 bind
iterations: chE0..5_t__0 and chW0..5_t__0 (hd_turn_a.t_i), coll_WN1_d__0, coll_WN1_u__1, coll_WN2_d__0,
coll_WN2_u__3 (hd_st_n4), coll_WN3_d__0, coll_WN3_u__0 (hd_ctl_n). The "12" was read from `regions_ca_fz.json`,
which carries no freg key at all (the bind's table writer drops it; DIE-HEAD-ROUTE-1's local patch covers only
bind_fz.json). HEAD-99's plan rule gives the same 18. Tool fix: count_align_bind must write freg into the table
output. Note `freg_fix.sh` line 32 still times against the old proof; its "start-skew 1556/1556" line is the same
artefact as 2(a4), use the sta_ca_fz2 result.

## 11. HEAD: rp21z20NC does not prep, TYPE_SPLIT on hd_spn and hd_spn_wshim_rx

- Trigger (MEASURED): the start ORIGIN FORM of the ca3 sidecar. The plan of record has one count origin per
  partition (1,609 origins, 0 relays, with frame_clock_regions and start_pins). The ca3 sidecar has one origin per
  clock region (1,557 origins + 31 relays, neither key), because `head_current_ca.py` calls the planner without
  `--start-native-clocks --start-partition-origins`. In the spine the planner chose the origin unevenly: sp1 and
  sp2 are origins themselves; in sp0, sp3, sp4, sp5 the origin is spN_bw_i_shim and hd_spn is a relay. In strap form
  the type signature is (count-aligned input buses, is-relay, is-origin-with-relays), so the copies differ exactly
  as reported. K and latency are not involved.
- Decision: do not split the two types, do not change the ring form, do not force origin_part by hand (a uniform
  region origin puts relay pins on hd_spn and the four shim types, three of them signed, and moves K again).
  Re-plan in the plan-of-record form.
- My run with the two flags (epyc2 fable-triage-headkv/po): 427 crossings at depth 4, fail 0, worst margin
  113.3 ps, 2,000 chips 0 violations, 1,564 start edges all clean by width, 358 partition origins, 0 relays.
  Two mechanical items remain: (1) 12 start hops exceed the 405 um reach bound (sp -> its east shims
  spN_be_i_shim / spN_xe_o_shim, and mesh7N -> mesh7N_estrip): pass the plan of record's launch-tap selection
  (its start_pins) or allow these 12 after GEOM; (2) the bind needs the partition-keyed table, not ca3's region
  table. Owners: DIE-HEAD-ROUTE-1 (chain), HEAD-99 (re-bind of all 427 and the 18 freg ports from that output).

### 11.1 How the plan of record closes the 12 long start hops: leaf origins, not launch taps

MEASURED in the plan-of-record sidecar (epyc7 head-99/prep21z16e/prep/source_sidecar.json, count_aligned):
- No partition starts another partition. Every one of the 358 partitions is a LEAF of the virtual clock-node start
  tree: region sp0_be_i_shim has parent `st:h...` (a clock-tree node, path depth 73), sp0 has its own node (depth 68),
  mesh7N_estrip its own (depth 109). There is no edge sp0 -> sp0_be_i_shim at all.
- start_ports: 1,608 = 1,250 node -> node + 358 node -> partition (capture_part set, launch_part null, no retime
  flag). start_pins: 358 die_outputs (one die-level start stage output per partition), 26 type_pins (one START input
  pin per type), 1,126 reset_inputs. frame_clock_regions maps the 358 partitions onto their clock regions.
- So the long hop is never built: the start rides the clock tree to the node next to each partition's own taps and
  enters through that partition's START pin. This is the planner option `--start-leaf-origins` ("each data START
  origin is a leaf of the virtual clock-node tree"), used together with `--start-native-clocks
  --start-partition-origins`. Explicit `--start-launch-taps` / `--start-capture-taps` are a different mechanism;
  they conflict with the native clock frame and are not what the plan of record used. I withdraw that suggestion
  from my 01:0x post.
- Proof on the current clock (my run, epyc2 fable-triage-headkv/po2/plan.json; ca3 inputs, hop bound kept at 405 um,
  the three flags): plan rc 0, reach_fail 0, 1,787 start edges all clean (1,430 virtual nodes, 1,039 retime nodes,
  358 partition leaves), minimum start sync distance 130.5 ps, 427 crossings at depth 4, fail 0, worst margin
  113.3 ps, 2,000 chips 0 violations.
- Do: DIE-HEAD-ROUTE-1 drops the 1400 um bound and the tap JSONs, adds `--start-leaf-origins` (hop bound 405),
  runs bind with the partition-keyed table, the 18 freg ports, start_stage_emit and the count-aligned STA. HEAD-99
  takes count_aligned whole from that output (it then carries start_ports, start_pins, parts, frame_clock_regions).

## 12. KV die PG: grid ot_pg_9 fails pdngen (question from GENBUG-IMPL, 01:3x PST)

GENBUG-IMPL's item (its commit 241397267d4 to this file, restored here; my later commits had replaced it): G3
works (die_pg_parts touched 160 of 160, 160 macro grids), but die pdngen on kvgeom6 plan_c fails PDN-0232 / PDN-0233
on `ot_pg_9`, a 6.48 x 972 um region (x 11173.68-11180.16, y 26064.72-27036.72), M8 only, 0 partitions. With that
grid removed from a copy, pdngen exits 0 in 351 s. Question: plan item, or should pg_regions skip such regions?

Answer: it is an emit-rule defect in `pg_regions.pdn_tcl`, not a region-split bug and not a plan item.
- MEASURED (epyc9 genbug-impl/g3/kit/psm/pdn.tcl): 12 regions. Six carry the die default spec and hold 0
  partitions: ot_pg_1, 3, 11 (6.48 um high bands), ot_pg_4 and ot_pg_9 (6.48 um wide columns), ot_pg_10
  (7,469 x 183.6). The 6.48 um pieces are the die margin around the top-row domains (partitions end at x 11173.68,
  die at 11180.16; the same frame exists on the west and the top). The split is consistent.
- The generator already knows that no M9 stripe (pitch 39.96) fits in a 6.48 um wide column: it emits ot_pg_4 and
  ot_pg_9 with M8 only, yet still emits the grid and `add_pdn_connect -layers {M8 M9}`. A one-layer grid has no
  via, pdngen removes the floating M8 stubs, the grid is empty, PDN-0233. ot_pg_4 is the same class and passes only
  by position; treat it the same.
- EXACT RULE, per region, from the stripe spec and the region box (no fixed width threshold):
  for each stripe layer L with width w, pitch p, offset o: stripes inside = 0 if span < o + w, else
  floor((span - o - w) / p) + 1, where span is the region size across the stripe direction (M8 horizontal: height;
  M9 vertical: width).
  1. If the region has at least one horizontal-layer stripe AND at least one vertical-layer stripe: emit the grid.
  2. Otherwise, if it holds 0 partition instances (the die_pg_parts centre-in-box test) and no bump: do not emit a
     region, domain or grid for it; print `OT_PG_REGION_SKIP <name> <w> <h> no_crossing`.
  3. Otherwise (it holds a partition but cannot form a crossing): fail closed at generation, plan error.
  On kvgeom6 this skips exactly ot_pg_4 and ot_pg_9 and keeps ot_pg_1, 3, 10, 11 (each has M8 and M9 stripes and
  builds today). Do not skip on "0 partitions" alone: ot_pg_10 and the bands carry the die grid between domains and
  the die-top clock cells.
- DIE-KV-ROUTE-1's interim filter (drop regions under 40 um, 5 dropped) is wider than needed; replace it with
  this rule in the shared script so both lanes build the same PG.
- HEAD: its die pdngen already passes with 358 of 358 macro grids (2a1); run the same rule there, it should skip
  nothing. QC and S81: run the rule in report mode once before installing G3.
- Owner: GENBUG-IMPL (rule in pg_regions + one test with a 6.48 um column); then install G3 after the KV die
  pdngen passes unmodified.

## 13. elemA A2p after the pins.json fix (question from CORES-NOROW-1, 02:5x PST)

CORES-NOROW-1's item (its commit ddf6a081fd4 to this file, restored here): pin_audit now passes with island rows.
Signoff GOAL=post on A2p: TT setup +207.83, FF hold -6.51 ps on 58 endpoints, DRC 0, antenna 0, drv FAIL (TT slew
4, FF slew 1). Question: hold ECO on the routed DB or margin change and re-route; are the slew violations real?

Answer (rule-based; I did not open the A2p reports):
- Hold: ECO on the routed DB. Hold >= 0 is a blocking gate, the miss is 6.5 ps on 58 endpoints against +208 ps of
  setup, so one delay cell per endpoint closes it; this is the small local case the owner allows as an ECO, and the
  old signed elemA used the same head_post_route_eco flow. Re-check setup, DRC and antenna after it. Do not change
  the margin and re-route for 6.5 ps.
- Slew: advisory under the academic profile (blocking gates are DRC 0, setup, hold, bind and lane latency), with
  one exception to check: if any of the 5 violating nets is a clock or an ft clock pass-through (ft_ck0/1,
  ft_mesh), fix it in the same ECO by sizing the driver, because the die clock STA propagates through those arcs.
- The core does not count as signed until the LEC rerun (5.2) is back.

## 14. Die PG form for the route gate and for sign-off (COORD question, 01:3x PST)

MEASURED state:
- HEAD pass 3 (p16g/drt3_clk_TT) draws M8 and M9 stripes by hand as special wires (4,064 + 4,063 M8, 512 + 512 M9).
  It has NO vias at all: no M8-M9 vias and no vias to the partitions' M7 PG pins. Its M9 spec (12.96 wide, pitch
  34.56) is typed in the script. It is a routing obstacle set, not a power grid.
- HEAD pdn2 run (p16g/drt4_pdn2_TT, region grids + 358 partition macro grids with M7-M8 connect): pdngen itself is
  cheap (498 s, about 7 GB resident during pdngen). The run was killed (signal 9, exit 137) at 209 GB after
  39 min, while DRT was reading the M8 shapes into its region query. The via mesh is what does not fit in DRT.
- The stripes-only form is not cheap either on HEAD: pass 3 sits at 155-175 GB and has been in detail-route
  iteration 0 for over 70 min (20 threads busy, no iteration line). So "stripes only" removes the kill, but the
  HEAD detail route is still unproven.
- KV with macro grids: pdngen 335-367 s, whole process 11 GB through GRT; its DRT never ran. KV relaunch now uses
  PG_MACRO=0 (region grids with M8-M9 connect, no partition vias), 10 regions kept, 2 skipped.
- Tech (asap7 tech LEF): M8 spacing 0.04, V8 cut spacing 0.057, V7 cut spacing 0.046, M7 spacing 0.032. Cut
  spacing is larger than metal spacing, so metal-clean does not by itself prove cut-clean.
- Size of the mesh on HEAD: 8,127 M8 stripes x 1,024 M9 stripes give about 4.2 million same-net M8-M9 crossings
  (computed from the stripe counts); the M7-M8 partition vias are several times more (INFERENCE, not counted).

Form:
1. Route database (what DRT loads): pdngen REGION grids only, PG_MACRO=0, i.e. the final M8/M9 stripes with their
   M8-M9 vias and nothing below M8. CORRECTED in section 15: the M8-M9 connect must be capped (2 x 4 cuts); the
   uncapped arrays are 2.3 billion cuts on KV and are what filled the memory. Both dies use this one form from the shared script. HEAD drops the hand-drawn
   stripes: they are not the sign-off shapes and they carry no V8, so their DRC count proves less than KV's.
2. Partition connection, separate pass after DRT, on the routed DB, with no router loaded: pdngen with the
   per-partition macro grids (pdn2 / G3 form, `add_pdn_connect {M7 M8}`), then write_db. Cost as measured: 6-9 min
   and about 7-11 GB. This pass adds only V7 cuts and enclosures that lie inside metal already present (the
   partition's M7 PG pin and the M8 stripe).
3. Check after pass 2, no rip-up: (a) every partition PG pin has at least one via to its stripe net (count per
   instance; 358 of 358 on HEAD, 160 of 160 on KV); (b) V7 cut spacing 0.046 between each die-net V7 cut (clock
   landings on the M7 tap pins) and the nearest PG V7 cut, by a small odb script over the die-net vias (a few
   tens of thousands of vias, minutes, under 10 GB). A hit is fixed by deleting that one PG via, not by re-routing.

Is the stripes-only DRC count valid as the die gate? Yes, as the ROUTE gate, on two conditions: the stripes in the
route database are the pdngen region grids of the final PG (not hand-drawn ones), and check 3(b) reports 0. The
die gate is then "DRT DRC 0 with region grids" plus "3(a) complete, 3(b) 0". A count from HEAD pass 3 as it stands
does not qualify (no V8, different M9 spec); use it only to learn whether the clock route converges.

Not needed for the academic profile: IR / EM analysis of the grid (advisory). Do not load the macro vias into DRT
to get there; that is the 209 GB path.

Open: if KV's PG_MACRO=0 detail route also grows past about 150 GB, the cost is DRT on a die-wide database (real
M1-M3 tracks, die-long stripes in every worker box), not the PG, and the next lever is on the route side (route
the clock tree per region window, or restrict the real M1-M3 tracks to the clock-cell sites). Post the DRT peak
and the first iteration line of both dies before changing anything else.

Owners: DIE-KV-ROUTE-1 (shared script: region-grid route form, macro pass, check 3); DIE-HEAD-ROUTE-1 (switch
HEAD to it, retire pass 3 after it reports).

## 15. Die DRT memory in the region-grid form: the V8 cut arrays (01:5x PST). Corrects section 14, item 1

Cause of the climb during "M8 shape load" (MEASURED, KV runs/p1/die_pg.odb, counted with a 1 GB odb script,
epyc7 fable-triage-headkv/cnt.py):
- The region grids hold 3,558,699 M8-M9 vias. Each is the array `via8_9_12960_480_5_134`: 5 x 134 = 670 cuts,
  because the M9 stripe is 12.96 um wide over a 0.48 um M8 stripe. Total 2,309,843,155 V8 cuts.
- ODB keeps a via as one parametric object (the whole DB is 0.3-1 GB). DRT expands every cut into its own shape
  when it loads layer V8. Both logs stop right there: last line "Complete M8", then the climb (KV 76 -> 107 GB
  at cap 150; HEAD pdn2 killed at 209 GB; HEAD gate form at 111 GB). HEAD has about 4.2 million crossings of the
  same kind, so about 2.8 billion cuts (computed from stripe counts).
- This is the form I gave in section 14 item 1 ("region grids with their M8-M9 vias"). It was wrong as written:
  the vias must be capped. Partition abstraction, gcell size and thread count do not touch this.

Exact form:
- In the route database keep the region grids, but cap the connect:
  `add_pdn_connect -grid <g> -layers {M8 M9} -max_rows 2 -max_columns 4` (8 cuts per crossing instead of 670).
  KV: 28 million cuts, HEAD about 33 million: a factor 84 less. Apply it in pdn_f.tcl generation for every
  region grid whose M9 width is above 1 um; the narrow 8.64-pitch regions keep their 5 x 5 arrays.
- Keep that capped array as the FINAL die PG. The grid is then connected at every crossing and the DRT DRC count
  is the die gate without any later step on V8. (IR is advisory; if fuller arrays are wanted later they sit
  inside the same M8 x M9 overlap and need only the cut-spacing script of section 14 item 3(b), on V8.)
- Macro grids (M7-M8 partition vias) stay out of the route database, as in section 14 items 2 and 3. When that
  pass runs, cap it the same way (`-max_rows 1 -max_columns 2` on the `{M7 M8}` connect).
- Stop both running DRTs now; they cannot finish the V8 load inside their caps, or will finish it with no room
  left to route.

Expected peak: shape load and track assignment in the single GB range for HEAD (pass 3, which has no vias at
all, measured 4.7 GB after load and 7.0 GB after track assignment), KV somewhat more (larger DB). Not known: the
routing phase itself. HEAD pass 3 jumped from 7 GB to about 155 GB within 11 minutes of "Start 0th optimization
iteration" and has crept to 185 GB since, with no vias in the database. So there is a second cost, in DRT's
iteration set-up on a 17.7 mm die (INFERENCE: it instantiates its route workers die-wide, about 55 thousand at the
default 7-gcell size, whether or not they hold a clock net; the growth does not follow the thread count: 158 GB
at 15 busy threads, 185 GB at 23).

Measure on the capped relaunch, three numbers per die: RSS after "Complete Pad", after track assignment
(DRT-0267 line), and 10 minutes into iteration 0. Decision:
- third number under about 60 GB: done, this form is the die-route form;
- third number above it while the second is small: the cost is the worker set-up. Then, and only then, use a
  windowed route: split the die into fixed windows along clock-region boundaries, route the clock nets of one
  window per run with everything outside the window (partitions, PG, already routed clock) left in place as
  fixed shapes, overlap the windows by one region, and count DRC from each window's own region only. The count
  stays a valid die gate because every routed shape is checked against the full fixed context of its window and
  every boundary region is checked in both neighbours. I have not built or measured this; it is the fallback,
  not the recommendation.
Not recommended: turning partitions into pure obstructions (they are already LEF abstracts; their pin shapes are
needed for the tap landings), or tuning threads / gcells (neither bounds the cut count).

Owners: DIE-KV-ROUTE-1 (cap in the shared pdn_f.tcl step, relaunch KV); DIE-HEAD-ROUTE-1 (same script on HEAD,
retire pass 3 and the gate-form run, post the three numbers).

## 16. The iteration-0 cost of the die DRT: worker size, set by the 10.8 um gcell (02:0x PST)

Diagnosis (MEASURED unless marked):
- DRT's own lines on the capped HEAD gate run (p16g/drt6_gate_TT/drt_TT.log): after pin access 7.4 GB
  (84,333 pins), 164,794 guides, after track assignment 10.2 GB (peak 31.8 GB; 8.5 min, 45 CPU-min). Nothing
  die-wide is large: guides, pins, shapes and the capped vias all fit in 10 GB.
- Then "Start 0th optimization iteration" and 144 GB, flat since (143.9 -> 144.3 GiB over 12 min, 15-16 threads
  busy). Pass 3 (no vias): 158 GB at 15 busy threads, 185 GB at 23. That is 8.0-10.5 GB per busy thread on top of
  a 10 GB base, in three readings on two databases. The cost is per route worker, not per die.
- Why a worker is that big: the route's gcell grid is `GCELLGRID ... STEP 10800`, i.e. 10.8 um (1,640 x 1,625
  gcells on the 17.7 mm die; chosen for die GRT). DRT's iteration 0 works in boxes of 7 x 7 gcells = 75.6 um.
  The real ASAP7 tracks are 0.036 um on M1-M4 (make_tracks.tcl in the flow image), so one box is 2,100 M1 tracks
  per side; with the M5-M9 track offsets about 4,500 distinct coordinates per axis, times 10 layers: about 200
  million grid nodes per worker (INFERENCE from the pitches; at 9.6 GB that is about 48 bytes per node). A normal
  ASAP7 block uses 0.54 um gcells: its worker is 3.8 um, 105 tracks per side, 400 times fewer nodes.
- Time follows the same number: pass 3 has run iteration 0 for 110 min on 24 threads without reaching the first
  "10 %" line, so iteration 0 alone is at least 18 h there.
- So: not guides, not M1 pin access data, not the die-wide database, not the PG. And NOT fixable by windows:
  a clock-region window still routes in 75.6 um workers, 9.6 GB each. I withdraw the windowed fallback of
  section 15.

Decision:
- Do not switch to the windowed form.
- Stop pass 3 now (no vias, wrong PG; it holds 185 GB and cannot become the gate).
- Let drt6_gate_TT run on only as the baseline (it is the valid PG form, 144 GB flat under a 240 cap), and stop
  it as soon as the small-worker run below prints its first progress line. Never raise its thread count: about
  9.6 GB per thread, 24 threads is the cap.
- Build the small-worker form now, in parallel, on both dies.

Exact form (same database, same PG, same guides; only DRT's worker size changes):
1. `detailed_route ... -single_step_dr` in place of the plain call (the flag exists in this image; it runs pin
   access, guide processing and track assignment, then stops before the first iteration).
2. Drive the iterations with `drt::step_dr`, nine positional arguments = FlexDR's SearchRepairArgs
   (size, offset, mazeEndIter, workerDRCCost, workerMarkerCost, workerFixedShapeCost, workerMarkerDecay,
   ripupMode, followGuide). Use the stock iteration table of this OpenROAD version unchanged, except the first
   two numbers: size 2 instead of 7, and every stock offset scaled as round(offset x 2 / 7), kept non-zero where
   the stock one is non-zero. A 2 x 2 gcell box is 21.6 um = 600 M1 tracks per side, still 5.7 times a normal
   ASAP7 worker, so route quality is not reduced.
3. `drt::step_end`, then write_db and the DRC report as today.
4. First run it on one cut-out to check the argument table: 5 iterations on a 2 x 2 mm corner; compare its
   violation count with the stock call on the same cut-out.
Expected peak: about 16 million nodes per worker, 0.8 GB per thread; 15 threads plus the 10 GB base and the
32 GB track-assignment peak = under 40 GB (INFERENCE from the per-node figure; to be measured). Worker count per
iteration rises from 55 thousand to 666 thousand; each is 12 times smaller.

Why the DRC count stays the die gate: nothing is hidden or abstracted. It is the same full-die database, the
same fixed shapes, and DRT's own end-of-iteration DRC over the whole die; only the box in which the maze router
works is smaller, with DRT's normal overlap between boxes. No per-window counting is involved.

KV: same gcell (the shared kit), same cost; apply the same form in shared/tail.tcl.
Structural note for the kit owner: a die-level kit that will be detail-routed should carry a DRT worker size
with its gcell size (size = round(75 um / gcell / 20), at least 1); 10.8 um gcells and stock size 7 never fit.

Not verified by me: the exact stock numbers of the iteration table in this build (take them from the FlexDR
source of the image's OpenROAD commit), and the small-worker run itself.
Owners: DIE-HEAD-ROUTE-1 (cut-out check, then HEAD), DIE-KV-ROUTE-1 (shared script, KV).

## 17. rp21z20NC: cohort 10 of 26 and LATCHECK host_rx (02:4x PST)

**(a) Cohort FAIL is a prep defect, not the sidecar.** MEASURED (epyc7 head-99/prep21z20NC/prep/published,
head-bind-1/run/z20nc/cohort.json):
- The 16 DIFF types are exactly the 16 whose published wrapper is dated 11-11 13:40. The 10 EQUAL types are exactly
  the 10 that this prep republished (11-15 10:03-10:16: hd_tile, lep0N, mesh, host_e, host_w, spn_end,
  spn_eshim_tx, st_n3_transit, st_str, turn_a). prep21z20NC.sh republishes only its TYPES list.
- The differences are generator age, not the new bind. Example ctl_estrip: the 11-11 file has `ot_dp_landing_relay`
  and `rst_start_raw_0/1` ports; today's generator writes `ot_dp_landing_relay_rep #(.N(5))` and no such ports.
  The rp21z18d_c run, which passed 26 of 26 on the old sidecar, generated the same text as z20nc for that module.
  hd_ctl differs because its 11-11 file is from before the tap moves (clk_t1 at (124, 17) against (146, 17)).
- Fix: republish all 26 types in prep21z20NC, then rerun cohort. Check before the run that no file in
  prep/published is older than the prep start. Expected 26 of 26.

**Sidecar composition.** The bind table of ca4 is sound: bind passes, count-aligned STA PASS in TT and FF, 427
crossings at depth 4, 18 freg ports, start-skew 0 of 1,787, 1,788 origins and 0 relays. Compose it like this:

| key | take from | why |
|---|---|---|
| top level regions, ports, granularity, collector, codex_serdes_geometry | plan of record | physical 327-region map; identical in both |
| count_aligned.ports, regions, parts, start_ports (+ schema, root, pad, strap_form, start_tree, relay_stages) | ca4 regions_ca.json | one consistent bind |
| count_aligned.frame_clock_regions | plan of record | 358 partitions to clock regions; partitions unchanged |
| count_aligned.start_pins | NEITHER: delete it and let compose rebuild it | it is derived from start_ports (clock_landings.start_pins) |
| count_aligned.root_settle_cycles | 88 (plan of record) until recomputed | ca4 carries the default 64 |

- start_pins as spliced is stale (MEASURED): 1,608 ports against 1,787 start_ports, and 357 of its 358
  die_outputs name start stages that do not exist in the new tree. After the rebuild check: ports 1,787,
  die_outputs 358, type_pins 26, and reset_inputs still 1,126. If reset_inputs come back empty, the START reset
  wiring has to be regenerated on the ca4 stages by the head_start_sources path (as DIE-HEAD-36 did on 10-29).
- root_settle_cycles: 88 is 64 plus the 24-cycle reset guard that head_start_local_reset computed on the old
  stage sites. Dropping to 64 removes that guard silently. Keep 88 now; recompute it on ca4's start_stages.json
  when that step is rerun. INFERENCE: the guard is of the same size on the new stages; not recomputed by me.
- ca4 does not need to be regenerated for the sidecar. The emit failure ("no free legal row segment (4 flops)
  within 40 rows of (6724.08, 8429.94)") is in the physical placement of the start stages; the bind table does
  not read it. The wide rerun placed 1,430 stages / 5,493 flops / 358 die outputs with at most 18.4 um from
  cell to stage. Rerun only the emit with KIT-OPS-6's start_stage_emit (@6140b34a0b5) once it is merged, for the
  die kit, and confirm the same three counts.

**(b) LATCHECK host_rx is a checker accounting gap; nothing is missing in hd_ctl.** MEASURED
(head-bind-1/run/z20nc/latcheck.json, plans):
- Delivered 58 = source face 1 + ft 38 + landing 17 + receiver face 1 + receiver kit station 1. The hd_ctl
  REGS station IS observed (kit_ist 1). Table 59 = 57 natural + fixed_cycles 2, where the 2 are one in-core cycle
  (there since rp21z16, where the row passed with delta -1) and the REGS station priced as +1.
- So the real latency is 58 observed + 1 in-core = 59 = table. The landing sum went 18 -> 17 with the new bind
  (host_rx__1 4 -> 3, __2 3 -> 4, __4 2 -> 1) and the table followed.
- `gen_lane_latcheck.reclassify` passes a fixed-in-core lane only when delta == -fixed_cycles. Here one of the
  two fixed cycles is now an observable kit station, so delta is -1, not -2, and the row falls to FAIL / OTHER.
- Fix in the checker, no plan or RTL change: with --fixed-in-core, PASS when
  delta == -(fixed_cycles - min(fixed_cycles, observed stations)), observed stations = source and receiver
  kit_ist + bound_ist. It gives -1 here, 0 on the 34 priced station lanes, -2 on coll_HOST1_d (no station).
  Add one test with this row. Owner HEAD-BIND-1.

Order: HEAD-99 deletes start_pins, sets root_settle_cycles 88, republishes all 26, reruns prep, cohort and
LATCHECK with the patched checker. DIE-HEAD-ROUTE-1 keeps ca4 as is.

## 18. HEAD clock feed hk6 (rp21z20NF), the NC intra skew, root move and the 1.15 scale (03:1x PST)

Data: lanes/handoff/HEAD-CLKFEED-1.md; epyc2 head-clkfeed-1/head/{nc,p16g}; my p16r rerun (section 2a4).

**18.1 Adopt hk6. Decision: yes, as rp21z20NF, after 18.2 is fixed.**
- What it buys (MEASURED): deepest tap 8,992 -> 7,001 ps TT (7,987 -> 6,214 FF), median tap 4,723 -> 3,825,
  feed wire -28 %, non-tree landing edges 144 -> 12. Every term the nominal gate does not carry scales with these:
  supply-noise jitter with insertion depth (-22 % on the far regions), and the late/early spread with the unshared
  path (415 of 427 crossings are now parent-child, so their unshared path is one hop, not up to 1,735 ps).
- The slow-corner information line agrees: SS-INFO worst lo +21.6 ps with hk6 against -45.5 ps with the old feed,
  slot-read fails 0 against 2 (lag fails 11 against 8; information only).
- The 19 ps FF loss is not a cost of the feed. The four worst ports are one spine crossing group
  (host_rx__3, m0S_rx__6, m7S_rx__5, sp_b3__0, all 132.3 ps), on the spine, which hk6 does not re-parent; the old
  worst was the neighbouring spine group (sp_x5__0 and three more, 151.2). Their window is lopsided (lo 132 / hi
  1,086): the planner takes the smallest latency that keeps 100 ps. One more cycle on that group would give about
  965 / 253. Not needed at the 100 ps floor; available if wanted. Ports under 150 ps: 4 with hk6, 0 before.
- Cost: one more bind (K changes per port, total latency 1,061 against 1,063), no type change.
- Flag for the route lane: the die detail-route runs so far (die-head-route-1 p16g, 4,972 clock nets) use the
  generic single-tree kit, not the regional tree with a feed (about 45 thousand clock cells). The die route gate
  has to be run on the adopted clock kit, i.e. hk6.

**18.2 NC intra skew 271.6 ps: one partition, lep0N; not the feed, not ca4, not the origins.** MEASURED
(tap arrivals FF, nc against p16g):
- 357 of 358 partitions have the same tap spread on NC as on rp21z16 to the decimal (tW4o0 98.8, tE5o6 97.2, ...).
  Only lep0N differs: 271.6 ps over 195 taps on NC, 86.7 ps over 223 taps on rp21z16. Because every other local
  tree is identical, the cause is isolated without an old-feed NC run.
- Inside lep0N the taps fall in two groups: 98 taps at x 6,982-8,179 arrive within 0-110 ps, 97 taps at
  x 8,222-8,838 arrive 160-272 ps later. The east half of the region's local tree is late as a block.
  The handoff says the lep0N and mesh region roots were kept from p16r while NC moved the lep0N taps (z19 delta:
  223 -> 195 taps). INFERENCE: the local tree was built from the old root for a tap set that moved.
- Is it a gate? Not by name: the blocking gate is routed hold >= 0 on real views. But it is real: hd_lep0N is
  built for a 92 ps tap window, and a 200 ps step between its halves will show up as hold and setup failures at
  the die once lep0N has a view (the kit-contract line already counts 53,550). Fix it before either NC or NF
  is adopted; it is the same fix for both.
- Fix: rebuild the lep0N region local tree on the NC taps (region root at the NC tap centroid; delay-balanced
  form). Accept when lep0N FF tap spread is at most 92 ps and the other 357 spreads are unchanged. Check the
  mesh regions the same way (their roots were kept too; their spread is unchanged today).
  Owner HEAD-CLKFEED-1 (cfg), DIE-HEAD-ROUTE-1 (rerun).

**18.3 Root move: no. Drop the 6.0 ns target.** The root sp3 is at the die centre; the Manhattan floor from it
is 16.7 mm = 5.8 ns, and no root position on a 17.7 x 17.6 mm die can do better than about (W + H) / 2 = 17.6 mm to
a corner region. The 7.0 ns is the floor plus about 0.4 ns of local tree and a 1.14 detour. A root move changes
every region's phase (a full re-bind) for no gain. Accept 7.0 ns.

**18.4 The 1.15 late/early factor: keep it out of the stage-model registry and out of the gate.** The model is
right in the mean (measured / model 1.005 TT, 0.981 FF on feed legs). 1.15 is the late-to-early ratio inside one
corner. The count-aligned gate already uses routed late and early arrivals, so it needs no factor. Use 1.15 only
in estimates made before a clock is built: unshared path late = 1.15 x unshared path early. Owner HEAD-CLKFEED-1
(one line in its estimate script).

## 19. HEAD NC + hk6 gate kit: seam hold on sp5_bw_i_shim -> sp5 (03:3x PST)

Data: epyc2 die-head-route-1/head/p20nc_gate/sta_dump/die_sta_related.json and proof/tap_arrivals_FF.json.

**(1) The counts are a declared-budget artefact; the seam itself is tight but inside the contract.** MEASURED:
- The "hold below 0" numbers (5,161 TT, 8,095 FF, worst -80.6 / -83.4) come from the declared-budget form: no real
  views, zero data delay, no credit for the receiver's hold padding. In that form hold slack is simply minus the
  clock damage, so every pair whose capture tap is later than its launch tap counts as negative.
- The same record's contract line passes: FF window needed 80.92 ps against the plan's seam window of 90 ps
  (clock.seam_hold.seam_ps), bound +9.08 ps, 0 negative pairs. The real-view hold gate is UNMEASURED on all 13,152
  seam pairs (missing views: hd_spn 6,300 pairs, hd_spn_wshim_rx 4,726, hd_ctl 2,340, ...).
- What is real: the damage on this one seam is 81 ps FF / 91 ps TT, 9 ps under the window in FF and 1.2 ps over it
  in TT (TT is not the hold corner). Cause: in region sp5 the spine partition's 68 taps arrive on average 28 ps
  after the west shim's 17 taps (2,282.6 against 2,254.2 ps), and spread 59.8 ps. In the other five spine rows
  the two means differ by 3 to 12 ps. sp5 is the larger hd_spn_end type, with a deeper local tree. The ctl ->
  ctl_estrip / ctl_nstrip rows are the same class (ctl spread 66.1 ps).

**(2) Fix: two small things, no lockup, no HB4, no plan window change.**
- Clock side (owner HEAD-CLKFEED-1): bring region sp5's two partitions to one target. Shift the sp5 partition's
  local tree about 20 ps earlier (or the shim's later) in the region build, so the worst damage is 70 ps or less
  in both corners. Check sp2 at the same time (spread 82.7 ps, the largest of the spine rows).
- Receiver side (owner HEAD-99 with the hd_spn_end type lane): sp5 is hd_spn_end, which is not signed. Build it
  with the input-min constraint on `bw_i` set for the full 90 ps window plus 10 ps, the same rule as section 9, so
  its kit hold repair delivers what the plan promises. For ctl -> strips the receivers are the signed hd_ctl_e and
  hd_ctl_n: the re-sign of section 9 covers hd_ctl_e; add hd_ctl_n to it (its real-view miss was -1.7 ps).
- A latch or HB4 cell on a seam with +656 ps of setup and a 9 ps contract margin is the wrong size of tool.

**(3) It does not block adopting NC or NF.** It is a follow-up delta: the clock trim goes with the lep0N local-tree
rebuild (18.2), which is needed anyway before adoption; the receiver constraint goes into the hd_spn_end build
that is still open. The seam becomes a gate only when hd_spn, hd_spn_end and the shims have real views; until
then report it as "contract PASS, margin 9 ps, UNMEASURED on views", not as 8,095 violations.

## 20. Region-parallel die DRT: the exact rule (04:0x PST)

Why now: memory is fixed by the small worker (28-37 GiB), but one full-die iteration 0 is at least 4 h on 13-29
shared threads for the generic kit's 4,972 clock nets (section 16). That is about 2.5 thread-seconds per worker
that holds a net (INFERENCE from 2.47 m of wire in 21.6 um boxes). The adopted regional clock has about 45
thousand nets, nine times more. One process cannot use more than one host, so the work has to be split by net.

Principle: never cut a net and never put a pin on a crop edge. A unit is a set of whole nets; everything else is
fixed context. Then every DRC that a unit reports is a true die DRC, and nothing can hide at a boundary.

**Rule**
1. Unit = one clock region (HEAD 327, KV 128). Its nets are the die-top nets whose DRIVER pin lies in the region
   box. Every routable net is in exactly one unit (check: the unit net counts add up to the routable total).
2. Reach R = the kit's leg bound (actual_max 405 um) plus two worker boxes (43.2 um) = 448.2 um, rounded up to
   gcells: 453.6 um (42 gcells). No net of a unit leaves its region box bloated by R. Check per unit from the
   guides; a unit that fails the check is merged with the neighbour it reaches into.
3. Passes. Two units may run at the same time only if their region boxes are at least 2 R = 907.2 um apart.
   Colour the "closer than 2 R" graph greedily. On the tile lattice (717 x 1,037 um) that is 3 colours in x times
   2 in y = 6 passes; the spine regions fit into the same six. Passes run one after another; units inside a pass
   run in parallel on any hosts.
4. Context of one unit run:
   - own nets: normal nets, routed by DRT (small worker, section 16 table);
   - nets routed in earlier passes: present with their routed shapes (wires and vias, metal and cut layers) as
     fixed special wires of the same net;
   - all other nets (later passes, other units of this pass): marked special, no shapes;
   - everything else as in the die database: all partitions as LEF abstracts, PG region grids with the capped
     vias, obstructions, tracks, the die guides.
   Two builds of this context are allowed, and they give the same count:
   (a) full-die database with the net marking above. Nothing is cropped; the halo is the whole die. Cost per run:
       the die load (about 8-13 GB; pin access 14 s; track assignment is 11 min for all nets and drops with the
       net count). This is the reference form.
   (b) geometric crop, to cut the load time: crop box = region box bloated by R, snapped out to gcells; keep
       every instance and every fixed shape that intersects the crop (macros whole, stripes clipped at the crop
       edge); guides of own nets only. No boundary pins: by item 2 no own net reaches the crop edge.
       The first three units built this way must be run in form (a) as well and give the same violation list.
5. A unit is done when its DRT count is 0. Its result is the routed wires of its own nets only.
6. Merge. After each pass add the units' own-net routes to the master as fixed special shapes (item 4, second
   bullet) for the next pass. After the last pass build the final database from the die GRT database plus every
   unit's own-net wires as normal routed nets: write_def per unit, take the own nets' NETS statements, put them
   into one DEF, read it into a fresh database. Checks: every routable net has exactly one wire; no net appears
   in two units; wire count per net equals the unit's.
7. Die gate = one whole-die DRC on that final database, all nets normal: `drt::check_drc` (present in this image;
   take its arguments from `info args drt::check_drc_cmd`) over the die in tiles of about 2.2 mm that overlap by
   43.2 um, markers de-duplicated by layer, box and rule. Gate: 0. The separate "seam-strip DRC" is not needed:
   the tiled whole-die check covers every strip, and by item 3 two units of one pass cannot have shapes within
   reach of each other. If the whole-die check finds a marker, re-run the owning unit of the later pass with the
   final context.

**Expected runtime (INFERENCE, to be replaced by the first three units)**
- A tile region has about 137 nets (45 thousand over 327) of about 68 um each (3.08 m of clock wire), so roughly
  550 to 1,500 worker boxes with a net. At 2.5 thread-seconds each, one rip-up-all iteration is 0.4 to 1.0
  thread-hours; three of them plus the DRC-driven ones: about 3.5 thread-hours per unit.
- Per unit at 8 threads: 30-40 min in form (a), less in form (b); 10-13 GB in form (a).
- Per pass: about 55 units x 8 threads = 440 threads: about 40 min when the fleet gives them; 6 passes: 4-6 h
  wall, about 1,150 thread-hours in total. The same work in one process is about 9 x 4 h per iteration.
- Spine regions (1,382 x 2,074 um, more nets) take about 4 times a tile unit.

**Order**
1. Build the unit list, reach check and colouring on the ADOPTED clock kit (regional tree with the hk6 feed), not
   on p16g's generic tree.
2. Run three units of pass 1 in both forms; post nets, workers with nets, minutes, peak RSS, violations.
3. Then volume. KV uses the same script with its own region map.

Not verified by me: the special-wire conversion of routed nets, `drt::check_drc`'s argument list and its memory
on a 2.2 mm tile, and all runtimes.
Owners: DIE-HEAD-ROUTE-1 (script and HEAD), DIE-KV-ROUTE-1 (KV).
