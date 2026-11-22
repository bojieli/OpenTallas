# FAM-QC-FEFW handoff (Sonnet 5.5, 2026-11-21 ~02:00 PST). Family: QC sle_fe*/slw_fe*/sle_fw*/slw_fw*. STOOD DOWN after census; successor needed.
NOTHING IS BUILT: no private bind, kit, GRT, sign-off or export exists for this family from this lane.

## Census (ROUTE-REACH-0020 + OWNERS-SWEEP 00:50): 13 unsigned current-plan types, all owner QC-PLAN-R8 (family), all furthest=place on current plan
sle_fe_v1__cl8210183c (192 att., sweep: running route), sle_fw_v1__cl9d029624 / clf58b4dfb (running route), sle_fw_v2__cl6740750e (running route),
sle_fw_v2__cl69f5e854 (cancelled superseded), slw_fe_v1__cl95cd1d0c (134 att., routed once, running route), slw_fe_v1__clfe325744__cldb4efe33 (place),
slw_fe_v2__clf110fab2 (running route), slw_fw_v1__clf51c11d8__cl592e3d37 (333 att., place), slw_fw_v2__cl8537f156, slw_fw_v2__cl8f84514c, slw_fw_v3 (running route).
## Findings (static, MEASURED on epyc9 with tools of fable-fix-qc-sle/clone; outputs epyc9 /srv/opentallas-scratch2/claude/fam-qc-fefw/{sc_v1.out,sc_v2b.out,pp_v1/place_precheck.tsv})
1. The sle_ctl core-slit station class (lever 3) does NOT show on fe/fw statically: station_core on V1 (qc103 s4q9n46r4 final preview) and V2b (v2b/c4/p_final.json)
   = 0 rows with station sites in / routes over a hard macro for (sle|slw)_f[ew]. So per-bit relay_sites (FABLE-FIX-QC-SLE-R3) has nothing to move on fe/fw. Do not copy it.
2. V1 KNEE (place_precheck, plan-decidable, matches PLACE-PRECHECK-2330): +1 station needed on
   sle_fe_v1__cl1cbb7497 arv_wi 584.9 um, arm_wi 506.5 um (1 -> 2 stations); sle_fe_v1__cl8210183c arv_wi 578.7, arm_wi 501.9 (1 -> 2);
   slw_fe_v2__cle312294d arv_ei 559.3 (1 -> 2); sle_fe_v2 x_fw_p2_i NEAR 399.4 (kit pins +-2 um). V2b has none of these. Rows for V1 relaunch go to QC-PLAN-R8.
3. Closest-to-signing fe kit: slw_fe_v1__clfe325744__cldb4efe33 (kw43 s29q103S4Q9N46C, epyc10, review 26c6b7661321): ROUTED, TT +51.9 ps, DRC 0, late ECO 1 it exhausted,
   FF hold core -60.89 -> -3.63 ps / 1 endpoint (3819 raw hold viol at sdc_min), "NOT SIGNED hold_ff". Hold paths: input port -> u_bin_x_stm_i flop (vclk ideal 199.9 vs clock 223 + 12.5 unc).
   Next lever: second ECO pass / shared-tap hold fix on those u_bin_* input flops, not a plan change. Sibling attempts of same type died FAIL_POSTCTS ft hop 2.06 / 2.17 mm
   (u_ft_x_su_l0_ctl_o / x_fw_ctl_p2_o, infra-oom) - a 2 mm pin-to-pin ft crossing.
4. slw_fe_v1 GRT overflow 50-56k, 99.5% vertical (FABLE-FIX-QC strategy lever 3) is NOT explained by station-in-core; diagnose from 5_1_grt congestion reports of the kit (ft channels / ft_spread).

## Next steps for successor
a. Pick representative slw_fe_v1__clfe325744__cldb4efe33 (routed, hold -3.6 ps): copy kit (git-archive tree), rerun hold ECO / tap balance; read CTS post-hook only.
b. Hand knee rows (item 2) to QC-PLAN-R8 if V1 relaunch is wanted; V2b is clean.
c. Check the 3 cancelled/infra-oom FAIL_POSTCTS ft-hop 2 km? (2.06-2.17 mm) rows for ft_spread cause.

## UPDATE 02:3x PST (lane RESUMED per COORD; stood-down row removed)
- slw_fe_v1__clfe325744__cldb4efe33 (C plan kit, epyc10): ECO i1 left ONE internal reg endpoint, FF -3.63 ps: u_bound.u_pd2_dd_ei_32.r[0]/D from u_bound.u_lpad_dd_ei.q[32]/QN.
  The other 3817 FF hold ends are input-port starts (LOCAL_PASS_NEEDS_PARENT class, advisory). Remaining fails: hold_ff (that 1 endpoint) + drv (advisory).
  RUNNING: eco_loop.py residual (pad pass, hold margin 10) on epyc10, client log /srv/opentallas-scratch2/claude/fam-qc-fefw/residual.client.log, out ECO_ROOT/residual/i2r. Then sign-off + LEC + export if signed.
- Knee rows posted to QC-PLAN-R8 (f8d70b09).
- slw_fe_v1__cl95cd1d0c (C plan, key-cardinal kw43 .../S4Q9N46C): 5_1_grt final overflow 0/0/0, usage 10.9 pct: the 50-56k vertical overflow in the brief is NOT this plan; stale/other plan.
- 2.06/2.17 mm FAIL_POSTPLACE (R6V1 plan siblings, PLACE-SETUP-STOP, not post-CTS): start u_bound.u_rrl_229/q (reset relay stage, rst_n_t74 gate at (142,1163.7)), end u_ft_x_fw_ctl_p2_o_3/eq flop;
  wns -187714 ps, tns -2.04e9 = reset-net recovery over a free net, not a data hop. Kit ft_bit_sites.tcl is EMPTY (no FIRM ft sites), so the ft eq flops are free-placed while their reset is repointed to a tap reset
  net (rst_n_t74); planned ft station site (140.8,1025) is 138 um from the relay, placed distance 2061 um. HYPOTHESIS, not yet verified in the place ODB (positions of the eq flop).
  Check: why ft_bit_sites is empty on R6V1 vs routed C kit; compare reset_taps.tcl repoint.

## FT-BIT-SITES-EMPTY finding 11-21 (COORD request) - NOT a generator bug
Count (kw43 kits, plans S4Q9N46R6V1 + S4Q9N46C, kits with ft_stations.txt: 82): ft_bit_sites.tcl empty (118 B) on 41. 15 of them have explicit station sites in ft_stations.txt
(relay_bay form: relay_bay.py rewrites ft_stations.txt with FIRM bay sites and deliberately drops ft_bit_sites rows of regenerated slots - SAFE-STATION-1; fe/fw/stm wire-only kits). 26 have no
station sites at all; of those, 13 C-plan kits have slots with stations>=2 and NO regs_um in the plan (sle_hc0 x3, sle_hc1 cl7d360508, sle_st_b_v1 x2, sle_st_b_v2 x3, slw_hc0, slw_hc1 x2, slw_st_b_v1):
gen ft_spread.spread_type only spreads slots with regs_um >= stations (todo filter), plan has none, so those stations are GPL-free by plan design. Other 13 = single-station slots (nothing to site).
slw_fe_v1__clfe325744__cldb4efe33 itself is relay_bay form: MEASURED in 3_place.odb ft eq flops sit AT their bays (o_2 (153,792), o_3 (162,1054), o_4 (173,1315); rrl_229 (139,1164)): 133 um, not 2 km.
The 2061 um in FAIL_POSTPLACE is the longest hop between consecutive instances ON THE WORST PATH (tt_setup_repair.tcl OT_POSTPLACE_WORST), not rrl->eq: the path runs through reset-net buffers
far away; WNS -187714 ps / TNS -2.0e9 on a reset net whose sinks (repointed ft/face flops of tap 74) span the die. Cause is the reset repoint/fanout of rst_n_t74 (RTL has 0 sinks on it, sinks are attached at place), not ft sites.
No generator change pushed (nothing to fix; spreading no-regs_um slots would be a feature, owner QC-PLAN-R8 could add regs_um rows).

## 2026-11-21 02:29 PST Codex notes
- Last candidate remains epyc10 `oth-ubuntu-325482-1795255542`, `residual/i2r`. Hold ECO selected the one internal failing capture at -3.63 ps and inserted one delay cell, leaving 3,817 parent-only endpoints advisory. DRT/STA/LEC results pending.
- The 02:12 rc127/1 were diagnostic tool calls; the subsequent placed geometry dump succeeded (`epyc9:/srv/opentallas-scratch2/claude/fam-qc-fefw/pos.out`, eq flop sites establish the 133 µm geometric leg). The failed 2 mm path is reset-buffer fanout; pursue partitioned reset distribution with actual sink partitions. No same-input reroute.


## 2026-11-21 02:37 PST Codex notes
- Corrected diagnosis of `5a19718fad1d` / `PLACE-SETUP-STOP`: exact saved epyc9 R6V1 `3_place.odb` has a local reset driver `u_rrl_229/_2_` at (139.968,1163.7) and only three sinks on `rst_n_t74`; target at (162.0,1053.81) is direct. The stock pre-CTS TT probe propagated unbuilt clocks (-187,714.01 ps). Same DB, TT libraries, SDC, and placement RC without pre-CTS propagation gives +21.56 ps WNS / TNS 0. Recovery in shared main `eda19506a55`, runtime synced. Epyc9 `fam-qc-fefw/trace_reset.log`, `fe_place_ideal.log`, `fe_place_propagated.log`. Actual post-CTS and sign-off retain propagated clocks.
- Rendered and viewed epyc9 `fam-qc-fefw/fe_pre_sta.png`: 622 × 1,832 µm soft partition with dense face pin bands and distributed taps. Read-only TT diagnostic approved. Current V1 attempt 3 already routes on epyc7 (wave `9af791d4cf50`, placed kit epyc8). It was generated before the tool fix. Keep running, then use a fresh runtime-pinned recovery if the obsolete pre-CTS probe stops it. Preserve that historical verdict. The independent C-plan residual is still in the private route pass.


## 11-21 03:4x PST after COORD RESUME (Codex takeover read)
- PLACE-SETUP-STOP on reset nets: 32 kit rows in kw43 (R6V1 31 + R4A4 1) stop at wns -35k..-401k ps with START = a reset relay / reset-sync flop (u_rrl_N, u_rl.rst_n, g_leaf u_l) and END an eq/reset-pin flop;
  QC types: slw_fe_v1 x3, slw_fe_v2 x2, sle_sc_v2/v3, sle_st_a x8, sle_su_c, sle_su_l1, slw_su_c cl19bb38ef, slw_su_l0, slw_st_a x4, sle_hc0/hc2, slw_hc1, slw_fw_v1 clf51c11d8, cbx_q10.
  Codex already found + fixed this class: pre-CTS ideal measurement eda19506a55 (false pre-CTS setup stops, unbuffered reset net / ideal clocks) + post-place path fix 24af28ef7d3; Codex reports the latest FE sibling
  went -189759.90 -> -1.98 with ideal clocks (geometry FAIL separate). So no separate flow fix from FEFW: these are false stops; relaunch/retry those kits on tools >= eda19506a55 (QC-PLAN-R8 wave owns relaunch).
- ECO residual on slw_fe_v1 cldb4efe33 (unit oth-ubuntu-325482-1795255542, epyc10) still running; waiter armed (task b9h6dyune); then sign-off + LEC + export.

## RULING d442c09bb6e noted (11-21): any private proof kit of this family must be generated with the exact effective env + gen args of the same type wave kit (OT_PGCAP + grt_pre hook, OT_PLACE_MAX_FANOUT, OT_CLAND_STRIP_DENS, OT_IO_HOLD, OT_SIGNED_VIEW_SHA, OT_GPL_SPARSE_UTIL, flow_tag) and config.mk must be diffed vs the wave kit before launch. FEFW has generated NO private kit so far: the residual hold ECO runs on the wave kit own ECO root (eco_20261120_185639_3224747/residual), same config.mk by construction.

## 11-21 ~08:1x PST SIGNED: slw_fe_v1__clfe325744__cldb4efe33 (C plan kit, epyc10), residual hold ECO PASS
eco_loop residual: internal FF hold -3.63/1 -> 0/0; sign-off verdict SIGNED (minimal profile: DRC 0, TT +51.92, internal hold 0, face_guard/sdc_lint PASS). legacy/local flags: legacy NOT SIGNED
(boundary hold -119.2 = input-port seam, advisory NEEDS_PARENT: parent_qualification NEEDS_PARENT, release_qualified False, provisional views allowed). signoff.json:
.../eco_20261120_185639_3224747/residual/i2r/signoff/signoff.json, record 5d5a4e3878dd25fe. AUTO_EXPORT queued (spool 5d5a4e3878dd25fe.json); AGIdock+rtx-pro export to be confirmed by the exporter, LEC = the exporter/signoff_chain routed LEC (not run by me).
Carry to siblings: same final hold ECO (eco_loop.py residual) for routed builds with <=5 internal ends; setup hop rows (x_sc_i chains) are with QC-PLAN-R9.

## FAM-QC-FEFW-R2 handoff 11-21 ~15:30 PST (stood down at ~285k; successor FAM-QC-FEFW-R3)
DONE (signed + routed LEC EQUIVALENT + exported to AGIdock and rtx-pro):
- slw_fe_v1__clfe325744__cldb4efe33 (residual hold ECO; LEC lec_kit/lec_out on epyc10; unit ax_ae011c12e0)
- slw_fw_v2__cl8f84514c (R-MINIMAL SIGNED TT -12.58; LEC fam-qc-fefw/lec_kit_fw2/lec_out on epyc2; unit ax_0897f930cd)
LEC lesson: run LEC from a COPY of the kit (no run/eco_*/signoff*) - the autopilot WATCHDOG stops any job whose cwd/path is a kit whose wave row is CANCELLED SUPERSEDED (4 kills, exit 143); copy script fam-qc-fefw/lec_kit*/ pattern, ot-run --priority proof.
CHAIN WAITERS (armed 11-21 ~10:5x; the wrapper-pid waiters for slw_fe_v2 epyc9 1944888 / sle_fe_v1 epyc7 3163263 / slw_fw_v3 epyc10 1319765 produced NO output notification before the limit; their results were not recorded by me): R3 must re-read the sign-off of each from the kits.
STATE now (kit_wave status): R6V2 ENQUEUED rows exist for sle_fe_v1 cl8210183c (epyc7), sle_fw_v2 cl6740750e (epyc2 b87cda6910e26 + epyc7 bef90cf9809e6), slw_fe_v2 clf110fab2 (epyc9 b8ee415c0c1bb), slw_fw_v1 cl592e3d37 (epyc2 b07775b5b53d9 + epyc7 bb8ae10e74de2); slw_fw_v3: ENQUEUED R6V1 b0877997cee7d (epyc8) and R6V2 place fail b20e0a78d2bd9 now RETRY-INFRA (disk-ETA hold, auto requeue). The relaunch check ended 23:03Z: all three types DO have live rows. The slw_fw_v1 E2BIG fail bc2005d26a581 is CANCELLED SUPERSEDED (case sent to FLOW-OPS-1000).
OPEN ROWS (QC-PLAN-R10/R11): x_sc_i +1 station (slw_fw_v1, sle_fw_v2, slw_fw_v3, slw_fe_v1) and slw_fw_v3 u_core.ch_dn_o[] (-84.28, x_fe_p1_i -> core, +1 station): confirm R11 carries them.
NEXT for R3: (1) read CODEX-LOG from line 14146 for fe/fw work done 14:23-18:1x; (2) check sign-off of slw_fe_v2 / sle_fe_v1 / slw_fw_v3 R6V1 chains; if R-MINIMAL SIGNED run kit-copy LEC + confirm AGIdock/rtx-pro INDEX; (3) sle_fe_v1 had 174 internal hold ends (-25.93) - not a residual-ECO candidate; (4) re-arm waiters with ot-wait --kit KITDIR --stage finish.

## FAM-QC-FEFW-R3 11-21 ~19:0x PST
- sle_fe_v1__cl8210183c R4A4 attempt_6 (epyc7): SIGNED by autopilot ECO i1 (R-MINIMAL, TT +68.28, internal hold -1.15 -> 0, DRC 0; signoff_eco_1795314113417494525). Spool a11a10ac4c7940fe queued for AGIdock+rtx-pro auto-export. Routed LEC (kit copy epyc7 fam-qc-fefw/lec_kit_sefe, out lec_out) RUNNING, log scratchpad lec_sefe.log.
- slw_fe_v2 cle312294d R6V1: NOT SIGNED (hold_ff -36.39, ECO exhausted). slw_fe_v2 clf110fab2 and slw_fw_v3: no sign-off yet (R4A4 / R6V1 rows ENQUEUED). slw_fw_v1 cl592e3d37 epyc2 attempt_3 RUNNER_FAIL.
- V3 rows delivered: lanes/handoff/FAM-QC-FEFW-R3-V3-rows.json (x_sc_i reconciled; ch_dn_o needs sites).
- LEC EQUIVALENT sle_fe_v1__cl8210183c cp=103598 proved=103598 differs=0 (kit-copy epyc7 fam-qc-fefw/lec_kit_sefe/lec_out, unit oth-ubuntu-1218730-1795315360).

### CODEX 11-22 13:27 PST

West FW `slw_fw_v2__cl8537f156` E10 inherited route completed detailed routing at zero violations and wrote its final RCX. The stage-6 reader hit the STA-1652 warning cap twice. All 1,000 distinct sample records name forwarded clock numeric internal nodes across 15 outputs, including 260 positive RES and 524 positive CAP records. The exact Verilog net and BUFx24 instance use the same identifier. Frozen full replay E10 `oth-ubuntu-1981410-1795382043` rc0 in `fam-qc-fefw/nov22_fw_fwd_alias` uses 15 ODB net renames and the exact corresponding SPEF map IDs, removing every STA-1652. Exploratory TT −74.82 is outside qualified signoff.

The generator fix preserves driver and external port names and names each output net `cland_fwd_net_<port>`. Exact old pre-CTS buffer reuse accepts and migrates legacy names after preserving connectivity checks. Branch `claude/fwd-spef-repair-1122@09a2ba041e4be941d0822159b5c4eea20e25c104` passed 30 focused tests and is admitted to canonical E10 `ot-gate-remote --merge` unit `2406832` after the mirror received the ref. The original central merge attempt stopped at unrelated unstaged KV/S81 changes. Those bytes remain untouched. Exact routed visual review is `results/geom_review/qc-fw-forward-alias-1122.md`. The normal TT/FF signoff on an alias-normalized copy is queued in the same E10 directory, client log `~/fam-qc-fefw.fwd_alias_signoff.log`.

Forwarded clock naming fix merged through MERGE-QUEUE at 13:30 PST, main `499dd5a2e11`. Canonical E10 gate on `4721325949b` passed 23/23 test files. The legacy alias readout remains exploratory. The normalized-copy normal signoff is still queued. West FE `cldb4efe33` reached 90% of DRT opt iteration 1 with 23,651 raw violations, down from 111,085 at the initial iteration boundary. East FE `cl1cbb7497` is live in auxiliary TT/FF GRT policy work even though its main route log is quiet. `postcts_gate_FF.log` and `stage_odb_cap.log` advanced at 13:26 and 13:30 and its OpenROAD process remains active.

West FW also has a separate physical setup successor. The exact TT −74.82 in both the inherited finish report and the alias-only measurement comes from the intra-clk `u_bin_x_sc_i/q[16]` to `u_ist_sc_wo_0/q[15]` class. On retained measured placement the 47 affected incoming legs measure up to 852.228 µm. The proposed move uses actual cut DEF rows for 47 data FFs and one epoch FF. Incoming max 372.168 µm, next-stage max 262.062 and epoch reset 394.848. Boundary and exceptional FLT registers keep their original placements. Witness `epyc10:/srv/opentallas-scratch2/claude/fam-qc-fefw/nov22_fw_sc/fw_sc_station_review.png` was viewed. Typed source `p7c5rt_fw_sc_station.json` in that directory SHA `bbae670d775b7413` adds zero cycles and needs exact fresh placement/CTS before route.
