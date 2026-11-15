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
- Open: the u_epc OUTPUT side (-85 ps, 19 endpoints with the signed lib) is not touched by form B. With the input
  side at +160, a u_epc tap 45-60 ps earlier closes it (outputs to about -25..-40, inside the -42 gate; FF output
  hold stays at or above +5). Put that tap in the same build.
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
- HEAD-99 + HEAD-REMAP-1: freg sidecar fix; one re-bind of 427 ports from ca3; u_chn early tap (-200 ps) and u_epc
  tap (-45..-60 ps) in the next event; strip-tap fix for M8.
- KIT-OPS-6: die_chain_ca.sh proof path; landed class in die_sta.py; GEOM-FAIL label and advisory rule (M1).
- DIE-KV-ROUTE-1: run route, CA and seamchk where runs/p1 lives; port the M1-M3 track block; seamchk on signed views.
- KV-102: tap cap 3,000 and the x 518 half-pitch taps; 55 ps on the pcf core taps; sys_c guard merge.
- S81-RESIGN-DEEP: kp4_dchn face register + DD 56, one re-sign.
- HEAD-EPC-RTL-1: check slice flop placement, add the u_epc tap, rebase on rp21z20.

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
