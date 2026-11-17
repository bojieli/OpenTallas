# FABLE-CLOSURE-STRATEGY 2026-11-17 03:30 PST (0320): delta on 01:30

Reviewer: FABLE-CLOSURE-STRATEGY-0320 (Fable). Read-only on builds. Technical PD only. HBM parked.
Blocking gates (R-MINIMAL): DRC 0 route, routed TT setup >= -42 ps, internal reg-to-reg FF hold >= 0, die bind + LATCHECK.

Marking: **V** = I opened the file / DB / log myself this round. **R** = reported by the named lane, not opened.

## 0. What changed versus 01:30

1. **QC cb has a second class and it is not placement (V, own STA probe).** The head-hop re-site works: post-CTS TT TNS
   -10,898 -> -436. The 4 `u_lk_nk_*_tap -> u_t*/tap` ends stay at -108.4 / -95.2 / -89.2 / -87.0 with the latch 3 um
   from the core pin. They are a half-cycle lockup latch launching into an early core tap. No re-site step fixes them.
2. **S81 reset: relay_um 180 re-plans every hop, but only 42.5 % of the relays had a hop over 180 um (V, table).**
   The cost is small in cells. The form question has a different answer for strip and for col (lever 2).
3. **S81 col relay path form is confirmed at GRT (V):** pg3 GRT TT -34.0 against pg1 routed -138.10 on the same type.
4. **QC M3: 60 HARD_CORE_PARAM_WRAP opened (V).** M4 with 5 masters is the right answer for this event (lever 4).
5. **HEAD hd_tile land1 is signed off (V); hd_ctl routed with DRT 0, sign-off running (V).**
6. S81 gunit define pairing is a functional lane error the bind cannot see; 45 more shared pipeline-class defines exist (V scan).

## 1. Evidence I opened

| item | host, path | result |
|---|---|---|
| QC cb pilot attempt_hh (r534 1c07ed14) | epyc8 fable-fix-qc-dieclk/pilot2/items/cbn_q01__clab6e67f2/attempt_hh/gen/cbn_q01__clab6e67f2: tt_setup_measure.log, tt_setup_keep.log, tt_setup_repair.log; same files of attempt_1 | Post-CTS TT, placement RC: attempt_1 -300.40 / TNS -10,897.89; attempt_hh -108.42 / TNS -938.30 before repair, 29 violating ends; after repair (1,441 cells) -108.42 / TNS -436.44. WNS did not move in 48 repair iterations; worst end `u_bound.u_t03/tap[0]` every iteration. Stage now in pre-GRT FF hold. No routed read yet |
| QC cb tap ends, own probe | epyc8 /srv/opentallas-scratch2/claude/fable-closure-strategy-0320/cb/run.log, run2.log (ot-run units 2067604 and one more, 4_1_cts.odb read-only, TT, placement RC) | u_t03 -108.4, u_t13 -95.2, u_t02 -89.2, u_t12 -87.0 (sum -380 of the -436 TNS). Path u_t03: DLLx1 latch at (83.4, 1865.8), core pin at (86.4, 1865.7), wire 0.1 ps. Launch = fall edge 416.5 + clk_t108 insertion 278.1 + latch 51.0 = 745.7. Required = 833 - 412.7 (clk_c2 early source latency) - 216.8 (core pin library setup) = 637.3. Hold on the same pin +436.5 (library hold 641.8). The feeding flop `u_pc_nk_u_t_0_3_tap` data reaches the latch D at 324.2 |
| S81 C4R reset table | intel2 lanes/handoff/S81-C4R-RESET-RELAYS-1117.tsv (74 rows, summed) | relays 20,567 -> 41,001 (x1.994, +20,434, mean +276 per type); hops over 180 um before: 8,736 = 42.5 % of relays; depth 6-8 -> 13-19 |
| S81 relay cells | intel2 ~/OpenTallas tools/die_plan/gen_rtl.py (LOCKUP_CELLS), reset_tree.py (RLK-1108, relay_cell) | `ot_dp_rrelay_nl` = 2 flops (posedge state + negedge q), 1 cycle. Latch form = plain posedge relay + one `ot_dp_lk` FIRM at the hop midpoint, clocked from the launch tap, 0 cycles. Lockup is per type, not per hop |
| S81 C4R1 bind | intel2 ~/s81-die-r/c4r1_bind.log | BIND_RC 0, LATCHECK_RC 0, lanes 873 / 873 PASS. FSTART_RC 1: `ot_s81sl_leaf__t37: no cland_start_raw in the bound RTL` (fstart_reset_delta.py:105) |
| S81 t47 ladder path, 01:30 probe | intel1 fable-closure-strategy-0155/t47/run.log | u_rrl_151 (1427, 954) -> u_rrl_159 (1048, 954): 379 um Manhattan, 8 buffers, route dips to y 823 (about 260 um of detour) on buffers shared at fanout 2-3 |
| S81 col ir1 (h9_r1) | epyc8 fable-fix-s81-col/ir1/.../grt_policy.json, 5_2_route.tmp.log | Second policy read TT -31.7, 86 violators, TNS -597.85; FF hold -41.2 on 476, port-start only (frame_int_i0 / i1). DRT first pass at 70 % |
| S81 col pg3 (h9_r2) | epyc8 .../pg3/.../grt_policy.json, postcts_gate_tt.json | GRT TT -34.0, 216 violators, TNS -1,690.06; FF hold -11.18 on 128 (sdc -22.38). DRT in the first optimization iteration |
| S81 col h10a (h10_r2) | epyc8 .../h10a/.../grt_policy.json | GRT TT -9.55, 9 violators; FF hold -60.57 on 345 (sdc -85.41). GRT repair running |
| QC M3BR | epyc2 fable-fix-qc-knee-hc/bind/bind_s29q103S4Q9M3BR/bind_report.json; gates/m4_prebind_1117 | 90 errors = HARD_CORE_PARAM_WRAP 60 (HI_PAD 32, SKEW_N 16, SKEW_S 16) + R8_STALE 30. M4 prebind replay: pass 1 running, no verdict yet |
| QC M4 masters | intel2 lanes/handoff/QC-M4-STA-MASTERS-1117.json | 5 new masters / 36 instances; 5 masters signed off on 11-16 become unused; 7 st_a param sets in use after M4 on 2 bases |
| HEAD hd_tile land1 | epyc7 head-die-r/tp2/land1/signoff_land.log, kit_hd_tile/signoff_land/signoff.json | Signed off (minimal profile): DRC 0, TT setup +11.6, internal FF hold 0.0 with 0 violators; sdc FF hold -95.02 on 590 ends is the port side |
| HEAD hd_ctl MCHK_LOCAL1 | epyc7 head-types-r2/mchk_local/kit_hd_ctl/run_route.log | DRT ends at 0 violations, pin audit 4,467 / 4,467; sign-off started 03:18, no record yet |
| S81 shared defines | epyc10 kw45/src_s81_pin_3c913dbdfb23_f2s4_cohort_d5c/rtl/dsrom_sys (ifdef scan, test benches left out) | 726 OT_ defines read; 88 are read by 2 or more source files and are not mutation / assert / bench switches; 45 of those are pipeline, split, hard or reset-ack class (list in lever 5) |

Not opened: H5 / H6 / H7 / H8 DBs, rm3, KV D14 / HG5, HEAD NF15e, hd_serdes a4, the S81 view define sets, C4R plan itself.

## 2. Levers, ranked by types / dies unblocked

| # | die | lever | unblocks | owner |
|---|---|---|---|---|
| 1 | S81 | col: pg3 form is the default; volume on its routed read | 203 col types | FABLE-FIX-S81-COL, S81-TYPES-R2 |
| 2 | S81 | reset relays: keep relay_um 180 on strip; col / dsdv go plain posedge, not 180 | 74 strip + 260 col / dsdv types | S81-DIE-R2, S81-TYPES-R2 |
| 3 | QC | cb: remove the lockup latch on the 4 nk tap pins per partition | 18 cb types / 192 partitions | QC-TYPES-R, QC-PLAN-R |
| 4 | QC | M4 with 5 st_a masters now; st_a arrivals pinned from N on | QC die bind, CB16 | QC-PLAN-R, QC-TYPES-R |
| 5 | S81 | gunit FWPIPE pairing + define-set check seeded with the scan list | S81 die function | S81-CORES-R, S81-DIE-R2 |
| 6 | S81 | SerDes: H5 (0.30) to route; rxf_q -> face_am is the one class to watch | 11 serdes types | FABLE-FIX-S81-SERDES |
| 7 | HEAD | swap land1 and hd_ctl into die STA; NF15e relay rows; clock nets priced with clock RC in the GRT gate | HEAD die gate | HEAD-DIE-R, FABLE-FIX-HEAD-CTL, HEAD-TYPES-R2 |
| 8 | KV | HG5 bind on D14, cross-tap read at the first post-CTS | 50 unsigned KV types | KV-R, KV-CLK-R2 |

### Lever 1. S81 col (203 types)

Evidence (V): same type h9_r2, pg1 routed TT -138.10 / 318 violators; pg3 with `OT_RELAY_POLY=1` GRT TT -34.0 / 216 violators,
FF hold -11.18. The macro-crossing relay hop was the -100 ps. ir1 holds -31.7 on a second GRT read. h10a -9.55.
Root cause: unchanged from 01:30 (rows, PG cap, wall-avoiding relay path). rm3 died in DRT-0255 on M8 without `OT_PGCAP` (R).
Fix.
1. FABLE-FIX-S81-COL: pg3 has 216 violators inside the gate. If the routed read is below -42, class the ends before any ECO;
   216 near-critical ends on one type means the relay rows are at their reach limit, and the fix is one more relay stage on the
   worst group, not repair.
2. S81-TYPES-R2: the three defaults (rows, `OT_PGCAP`, `OT_RELAY_POLY=1`) go in the next S81 tree now. Do not wait for the
   routed read to stage them; wait for it to launch volume.
3. h10a FF hold -60.57 on 345 ends at GRT: confirm they are port-start like ir1 before the route. If internal, they are relay
   hops (lever 2 applies to this type first).

### Lever 2. S81 reset relays (74 strip + 260 col / dsdv)

Evidence (V): 8,736 of 20,567 strip relays had a falling-edge hop over 180 um. relay_um 180 doubled all of them. An nl relay
is 2 flops, so the strip goes from 41,134 to 82,002 relay flops: +552 flops per type on average. The t47 kit numbers cells
past 158,000, so this is about 0.35 % of the type (inferred from instance names, not a cell census). C4R1 is bound: LATCHECK 873 / 873.
Cost of the three forms on the strip, same 74 types:

| form | relay flops | latches | depth | boot | hold by construction | setup on the hop |
|---|---|---|---|---|---|---|
| relay_um 180, negedge (C4R) | 82,002 | 0 | 13-19 | 208 | yes, T/2 | 155 um on 416 ps |
| latch RLK-1108 at 380 um | 20,567 | up to 20,567 (one per internal hop) | 6-8 | 154 | yes, T/2 | two half hops of 190 um, about 250 ps of 416 (estimate) |
| plain posedge (SerDes H3p form) | 20,567 | 0 | 6-8 | 154 | no: wire delay against cross-tap skew | 380 um on 833 ps |

Answer.
1. **Strip: keep C4R (relay_um 180).** Area and congestion are not the discriminator at 0.35 %. It is bound, 0 cycles on lanes,
   and it is the only form of the three already proven through bind on these types. The latch form is cheaper in cells but puts
   a new FIRM midpoint cell class into 74 types that has one HBM pilot behind it. Not worth a rebind.
2. **Col / dsdv (260 types): do not apply relay_um 180. Take them out of `reset.relay_lockup.types` (plain posedge).**
   In col the scarce resource is legal relay sites between paired macros (R: h10_r0_p1 18 of 95 groups NOFIT, h9_r0_p2 16
   unfitted). relay_um 180 needs a site every 155 um and the latch form needs a FIRM midpoint site; both reopen the fit.
   Plain posedge keeps the 383 um sites as they are and gives the hop a full cycle. Hold on a 380 um hop is covered by wire
   delay (about 340 ps at this kit's 0.9 ps/um); only short cross-tap hops need pads, and S81-DIE-R2 already reads those in
   the die STA for the 11 SerDes types.
3. One real risk in the plain form, measured on SerDes H5 (R): `rt_e (clk_t10, 117 ps) -> u_enc.u_rst (clk_t42, 448 ps)`
   FF -290.83 before repair. That is 331 ps of tap insertion skew on a reset hop. Before col leaves the lockup list,
   S81-TYPES-R2 prints, per col type, the tap insertion spread across reset relay hops from one CTS DB. Under about 150 ps:
   plain. Over: that type keeps negedge with 180.
4. S81-DIE-R2: FSTART step fails on t37 (`no cland_start_raw in the bound RTL`, V). t37 has no START landing, so the delta
   tool must skip types without it instead of raising; C4R2 is blocked on this, not on design.
5. Tool note for S81-TYPES-R2: lockup is chosen per type. A per-hop choice (nl only when every child hop is <= 180 um) would
   have fixed the strip with 0 new relays. Worth having for the next die; not for C4R.

### Lever 3. QC cb (18 types / 192 partitions)

Evidence (V): section 1, rows 1 and 2.
Root cause. `u_lk_nk_*_tap` is a transparent-low lockup latch between the glue flop `u_pc_nk_*_tap` (tap clk_t108, insertion
278 ps) and the nk core pin `tap[0]`. The core tap is delivered 413 ps early and the pin needs 217 ps of setup, so the pin
window at TT is 274.5 to 637.3 ps after the edge. The latch re-launches at the falling edge and lands at 745.7: 108 ps late with
zero wire. The flop output alone would land at 324: setup +313, hold about +50 at TT. The early core tap already gives the
hold protection the latch was added for.
Fix.
1. QC-TYPES-R / QC-PLAN-R: drop the lockup latch on the nk `tap` hops (0 cycles either way, so no lane or LATCHECK change),
   keep `u_pc_nk_*_tap` at the pin, and let the FF hold repair pad the 4 nets into the window. Target arrival about 450 ps TT
   (3 HB4 on a single-sink net). Check the FF window from the core library before the build: I read TT only.
2. Do not wait for the routed read of attempt_hh to decide this: placement RC has 0.1 ps of wire on the path, so route cannot
   change it. The routed read is still needed for the b_d -> a_d class.
3. The gate for the pilot stays as 01:30: no head-hop end below -42 and the 4 tap ends at or above -42.
4. Same check on every die: any lockup latch or negedge stage whose capture is an early core tap or a landing with a
   library setup above 150 ps. One grep of kit netlists for `u_lk_*` driving a hard-core pin.

### Lever 4. QC M4 (die bind, CB16)

Evidence: 60 PARAM_WRAP = 32 HI_PAD + 16 SKEW_N + 16 SKEW_S (V). Cause is the M count re-frame clock_landing only; a 0-cycle
restore needs +1 / +2 far-path cycles and a c16 re-shape on about 240 lanes, and voids CB16 e2f94854 (R).
Answer: **M4 with 5 masters is right for this event.** Five builds of a recipe that signed off yesterday cost less than
reopening the clock frame and the CB16 table. But 5 masters signed off on 11-16 are now unused (V), so the structure is wrong
for the next event: die arrivals are baked into hard-core parameters.
Fix.
1. QC-PLAN-R: from M4 on, st_a QFT values (SKEW_N, SKEW_S, HI_PAD per site) are an equality constraint of any later frame
   change, like bus pads. N (NB slot, SC reset rows) must show 0 st_a param diffs in the prebind replay or it is not composed.
2. QC-TYPES-R: build the 5 in parallel now. Size, on the first one, a strap-selected span for the same pads (HI_PAD 15-18 and
   28-30, SKEW_N 7-9, SKEW_S 8-11), the form the ctl types already use for R8 strap pads. If it fits timing, the next st_a
   rebuild is 2 masters (tail1, nb0) and a frame move inside the span needs 0 builds. This is a proposal, not measured.
3. The st_b split the M4 check found (W1 RD_PAD 2, W3 3) is the same class: put st_b under the same constraint.

### Lever 5. S81 gunit pairing and the define-set check

Evidence (R, S81-CORES-R): signed bf has FWPIPE (s_bias_fwp), signed ba0 / ba1 have 0 s_bias_fwp; bias leads SV by 1 cycle.
COORD has ruled: ba0 / ba1 FWPIPE builds, D5d with 4 defines, a die check.
Other pairings like it (V scan, candidates only; I did not compare view define sets):
- host: `OT_HOSTNATIVE_PIPE`, `_PIPE2`, `_PIPE7` to `_PIPE10` (dsfd_host_native and _n32); `OT_S81_SH_APIPE9 / 10`
  (dsdv_seq_host and dsdv_sh_sd).
- pq: `OT_PQ_QB_PIPE`, `OT_PQ_IX_BANK_SPLIT`, `OT_PQ_AQ / IX / QB_PHYS_SPLIT` (die-bind wrappers dsfd_sp_pq_n / _produced and
  the pq core). These span the black-box boundary exactly like gunit.
- collective: `OT_S81PH_EP_PIPE2` (coll_lane, coll_lane_safe2, coll_core), `OT_S81PH_COLL_QPIPE` (coll_core, coll_split),
  `OT_COLL_NATIVE32` (S81 coll_lane_safe4 / link_ep_safe4 and HEAD he_epc / mesh_ep_core: crosses two dies).
- vm: `OT_VMFE_FCC_PIPE`, `OT_VMFE_FCN_SUM_PIPE` (dsfd_sp_vm, dsfd_vm_fe_h); `OT_SPVM_RESET_ACK` (5 files incl. the mtp side).
- svc: `OT_SVC_H8`, `OT_SVC_HV`, `OT_SVC_ALLQ`, `OT_SVC_MERGE_H4`, `OT_SVC_H8_REUSE_RT2`.
- serdes: `OT_S81_RCK_RELAY4`, `OT_S81_KP4_SYN_LOCAL`, `OT_S81_KP4_AM_FACE3`, `OT_S81_DCHN_FACE`, `OT_S81_RM_STAGED`.
- engram: `OT_S81ENG_RR_N32` (lookup cores and dsdv_eng_rr).
Fix. S81-DIE-R2's check compares, for every define a hard core's source closure reads, the view's build set against the die
set, and also against every other view whose closure reads the same define. Run it first on the pq, host and collective
groups: they have a wrapper on one side of the black box. HEAD-DIE-R runs the same check for `OT_COLL_NATIVE32`.
A view without a recorded define list fails the check (the bf view listed 1 of its 4).

### Lever 6. S81 SerDes (11 types)

Evidence (R): H5 at 0.30 post-CTS TT -87.88 on 9 ends, all `rxf_q(fall) -> u_dec.u_face_am.parts`; H6 at 0.20 -532 on 402.
The density window is real: 0.50 fails DRT-0255, 0.20 costs 500 ps of wire on the syndrome / BM cone.
Fix. H5 is the lead form; route it. The 9 ends launch on a falling edge, so they are a half-cycle class like lever 2 and
lever 3: if GRT repair does not clear them (it did on H3p), move the face_am parts beside rxf, not more repair. H7 / H8 stay as
brackets only until H5 has a DRT verdict. FF -290.83 on `rt_e -> u_enc.u_rst` is tap insertion skew of 331 ps on a plain reset
hop: place that relay on the encoder tap (clk_t42) instead of padding 290 ps.

### Lever 7. HEAD

- hd_tile land1 signed off (V): swap into die STA now; the tile ring leg of 01:30 is closed. NF15e still re-derives
  `OT_FWD_RING_MIN` from the pair read, or the next tile build repeats it.
- hd_ctl (V DRT 0; R: 54 % of the 20k hold ends were the port contract in_min -90, 40 % cross-tap at 97 ps tap skew, 3 %
  local; all closed with 27,572 HB4 at 28 % util). No tap rows for this type. If sign-off shows internal FF a few ends
  short, one final-mile pass; nothing else.
- NF15e reset / START (R): 508 negative seams all have setup + hold >= 0, so the last relay moves into the receiver region;
  no cycle. Apply the lever 2 rule there too: region skew p90 896 ps means plain hops are not hold-safe by wire delay on HEAD.
- GRT gate frame (R, FABLE-FIX-HEAD-SERDES): the GRT TT gate prices clock nets with the signal C; about 75 ps of hd_serdes
  inter-tap skew at GRT is the frame. HEAD-DIE-R: clock nets take the clock-fit RC in the GRT gate on every die, or GRT TT
  repair spends cells on a skew that RCX does not have (829 cells on hd_ctl, 720+ iterations on sd9d).

### Lever 8. KV

No new physical data since 01:30 (R: D14 is on one host). HG5 binds as packed; first pilot stops at post-CTS FF and prints
cross-tap ends (projection 163 on hgi). The 58 forwarded-clock ports stay out of the die-tap window until HG6 derives their
offset from the sender fclk; do not invent rows for them.

## 3. Stop list (changes only; 01:30 list otherwise stands)

1. QC cb: more setup repair or any re-site step for the `u_lk_nk_*_tap` ends; waiting for a routed read to decide them.
2. QC plan: a 0-cycle restore of the L2 st_a arrivals inside M; a further frame change that moves st_a params; M4 bind before
   the prebind replay is clean.
3. S81 reset: relay_um 180 or the latch form on col / dsdv types; a strip rebind to change the relay form; taking col types
   out of lockup without the tap-spread print.
4. S81 col: ECO on rm3 or any col kit without `OT_PGCAP`; volume before a pg3 or ir1 routed read.
5. S81 SerDes: densities below 0.30; hold pads on `rt_e -> u_enc.u_rst`.
6. S81 gunit: counting any gunit core before ba0 / ba1 FWPIPE views are signed off; a die check that only compares views to
   the die define list and not to each other.
7. HEAD: tap rows for hd_ctl; GRT TT repair on clock-skew-limited ends priced with signal RC.

## 4. Not checked

- FF corner of the cb core-pin window (TT only), and the cb routed setup: the build is in pre-GRT hold repair.
- Strip leaf cell counts (0.35 % rests on instance numbering) and any strip or col tap insertion spread on reset hops.
- Latch form on an S81 route: no S81 kit has run it; the 250 ps half-hop figure is arithmetic from 0.9 ps/um.
- View define sets of the 45 candidate defines; whether any pair is actually mismatched.
- The strap-span st_a master: no timing or area number exists.
- h10a hold class, pg3 / ir1 routed timing, H5 route, hd_ctl sign-off record, KV D14 pilot, NF15e.
- Whether the C4R plan pins `reset.part_depth`: if not, the die contract K follows the deepest type (now 19).
