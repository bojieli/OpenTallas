# FABLE-TRIAGE-QC: QC die (qwen_compute) failure triage, pass 1

2026-11-15 00:50 PST, FABLE-TRIAGE-QC. Scope: technical PD only. Read: `failure_breakdown.py` (00:25), `autopilot/kit_wave_stages.tsv` (00:31), the QC queue lines since 11-14 21:00, handoffs QC-HOLDGRT-1, DIE-QC-103, QC-CORES-HEAD, TYPE-QCCB-GEN, the kit and proof logs named below. Not redone: the cb head-hop / anchor finding (FABLE-QC-CB, FABLE-CLOSURE-STRATEGY lever 4, FABLE-GENBUG).

MEASURED = read from a log, database or file by me tonight. INFERENCE is marked.

## 0. State and summary

QC cores 65/65 signed. QC types 4/127 signed. Event s29q103S3R, latest row per item (122 items): 109 RUNNING, 9 RETRY-INFRA, 3 FAIL, 1 CANCELLED. So almost nothing is in a failed state right now; the failures of tonight are the ones below, and most of them were not design failures.

1. The largest failure group tonight (about 25 QC rows, also S81 and HEAD) was an infra fault in the job wrapper, shown as "FLOW" or "PLAN" failures at place. No design caused it.
2. The 8 "hold-stall" types are one structural cause that the accept-rule patch does not remove: the relay input ports carry a setup contract and a hold contract that cannot both be met. I measured it on stm_v1.
3. The S4f tap values are from SIGNED runs, not unsigned ones; the FF values in S4f should be the measured ones, not scaled.
4. Claims (a) to (e): (a) correct but incomplete, (b) correct, pending the rebind, (c) correct, (d) consistent, proof pending, (e) correct, proof pending.

## 1. Mechanisms

### M1. Job wrapper import failure, 23:08 to 00:18 (infra, fleet-wide)

- Symptom: `FAIL FLOW (tool / Tcl error @place: ModuleNotFoundError: No module named 'ot_store')`; 20 queue lines, QC, S81 and HEAD. QC autopilot rows 23:12 to 00:23: 25 "CRASH/flow-error exit 1" (not each traced to this text).
- MEASURED: `~/.local/bin/ot-job` was replaced on all 7 hosts at 22:55-22:56 PST (WAVE-BALANCE-1 `best_job_root`, backup `ot-job.bak-wb1-*`). It does `import ot_store` from its own directory. `~/.local/bin/ot_store.py` has mtime 00:24 PST on all 7 hosts, one sha (07316aff7a76). `ot-job --help` imports cleanly now on intel1, epyc2, epyc7, epyc8, epyc9, epyc10.
- INFERENCE: the module was missing or unreadable between the two times. I did not find who removed or restored it, and no lane posted it.
- Same window, wrong class: `sle_fw_v1__cl9d029624` a2 and `sle_fe_v2` a3 are recorded as `FAIL PLAN (plan geometry / site @place: GRTM mode edge_outline image ...)`. MEASURED on epyc2: both wrote `3_5_place_dp.odb` (23:37, placement converged, no error line). The "reason" is the runner's banner line. `sle_fw_v1__clf58b4dfb` a2 (epyc9) "route flow-error exit 1" at 23:55 has a good placed database too.
- Fix (KIT-OPS-5): retry keys with stage resume for every row that failed between 22:56 and 00:24 with this text or with a banner-only reason; they are not design failures and must not count toward the 3-retry rule. Classifier: `ModuleNotFoundError` and a reason equal to the banner line go to INFRA.
- Fix (WAVE-BALANCE-1): install `ot-job` and `ot_store.py` as a pair, then run `ot-job --help` on each host as the smoke test before leaving.

### M2. Child views missing (infra)

- `INFRA-VIEW-MISSING` on sle_ctl x6 and slw_su_c x2 (btab, prog; also vmr, nk_a0c, nl_a0c and 3 more view dirs). KIT-OPS-6 rebuilt btab and prog from the signed rtx-pro export (23:5x) and the protect sync is live.
- Still open at 00:31: `slw_su_c__cl19bb38ef` FAIL prov_views (22:04), `slw_su_c__cl92142dac` RETRY-INFRA (21:55). Owner KIT-OPS-6: re-key both now that the views exist.

### M3. Port-seam hold: the relay input contract cannot be met (structural, 8+ types)

Types: sle_fw_v1, sle_stm_v1 x2, slw_stm_v1 x2, slw_stm_v2, slw_fe_v1, slw_fe_v2, slw_hc3, sle_st_b_v1, and the sc_v1 / fe_v3 / hc0 rows of FABLE-TYPES-QC-EAST cause A.

MEASURED, read-only STA on the stm_v1 proof copy (`slw_stm_v1__cl05fc43f7__cl389df4e9`, `4_cts.odb`, same timing context as `hold_gate.tcl`; epyc7 `/srv/opentallas-scratch2/claude/fable-triage-qc/stm_v1/whatif.log`):

| endpoint `u_bound.u_ft_x_fw_fe_p1_o_0/q[..]/D` | q[208], tap clk_t28 | q[174], tap clk_t23 |
|---|---|---|
| FF hold: input min -85 on vclk 202.5, data arrives | 131.4 ps | 131.3 ps |
| FF hold: clock at the flop + 12.5 uncertainty + hold | 229.6 ps | 245.1 ps |
| FF hold slack | -98.27 | -113.74 |
| TT setup: input max 676.36 on vclk 250, data arrives | 945.1 ps | 945.0 ps |
| TT setup: tap early latency (tap window) | -51 | -17 |
| TT setup slack | +72.4 | +128.6 |

- The path is port -> one BUFx2 -> flop. To close hold, q[208] needs about 98 ps more data delay at FF, which is about 125 ps at TT (INFERENCE on the corner ratio, about 1.3). The setup contract leaves 72 ps. `repair_timing -hold` does not break setup, so it stops. q[174] has 128 ps of setup room and was repaired.
- This is why the stm_v1 proof ends at -98.27 after two passes with 3,260 endpoints left, every one of them class `port_in` (MEASURED, final line: same_tap 0, cross_tap 0, port_out 0, cross-tap WNS +45.0, 31,951 hold cells). More passes cannot change it. The in-flow GRT hold repair meets the same limit.
- Cause: the relay input ports (`set_input_delay -max 676.36`, one port list in `constraint.sdc`; every other input has -max 76.6) also carry `-min -85`. A signal cannot be both 676 ps late and 85 ps early. The window left for the capture clock is 833 - 676.4 - 85 = 72 ps, and the tap window (4 to 90 ps early latency per tap in this kit) is taken out of it. A tap with a window above about 20 ps cannot meet both.
- Port hold is the parent's under R-MINIMAL, and die STA on real views is the judge. So the kit should not fail, stall or spend cells on this class beyond what setup allows.

Fix, in order:
1. (QC-HOLDGRT-1, flow) Finish the accept rule as FABLE-TYPES-QC-EAST section 1 wrote it: the hold arm judges the classes the repair can move (same_tap, cross_tap, port_out and port_in endpoints with setup room), not the kit WNS. Today's patch leaves the hold arm as it was (`w1 < w0 + 1` on WNS), so a kit whose worst endpoint is setup-locked still ends "no hold gain" and loses the whole repair (stm_v1 cl27746664 -110.69 -> -110.69, sc_v1 cl7479a5ec, fe_v3, fe_v2 clf110fab2 in the EAST table). The stm_v1 proof passed only because its worst endpoint (q[174]) happened to have setup room.
2. (QC-HOLDGRT-1, flow) `hold_guard_grt.tcl` and `failfast_rules.py`: count the stall and HOLD_STRUCTURAL on the non-port classes only; print the port_in residue as PORT_SEAM (advisory, for die STA). Otherwise the 3,260 endpoints stall GRT again for hours.
3. (DIE-QC-103, plan, only if die STA shows real misses) Relay input ports: make the pair consistent. Either a tighter `-max` on these ports (about 600 leaves room for the pad) or the relay capture flops on taps with a window of 20 ps or less. No change before the die STA result.

Not real yet: `sle_fw_v1` TT setup -305 at CTS. It is a placement estimate before any repeater pass (same note as FABLE-QC-CB 1.3); judge it after GRT.

### M4. cb family GRT / setup / lock-up hold (16 types)

Cause and fix are in FABLE-QC-CB. Status tonight (MEASURED): TYPE-QCCB-GEN branch `claude/type-qccb-gen-1114` @348d28d3ff1 patches `core_input_chain.tcl` (head hop, xstn siting with a guard for stations that also drive the outside) and `core_input_anchor.tcl`. Proofs q00, q11 (epyc2) and q01 (epyc8) started 00:23 and are in global placement. No patched-hook result exists yet. See verdict (d).

### M5. slw_su_c cl19bb38ef: clock taps starved of sink data

MEASURED (QC-CORES-HEAD, files read by me): the type had no `sink_bins_file`, so the plan placed 30 taps; its sibling cl92142dac has one (58,374 registers) and 110 taps and passes the hold gate. Result on cl19bb38ef: 11 taps over the 1,200 cap, tree depth 8-9, capture 602 ps against 123 ps, FF hold -397 on 3,667 endpoints. Fix = delta D1, see verdict (e). Class guard still missing: G0 should warn when a `tap_mode density` type has no sink inventory (coll_core has none; coll_ftc is 1 tap over the cap).

### M6. qfd_dv_s8x_vmr pin access (DRT-0073) blocks every su_c route

Fix = view v2, see verdict (c). su_c proof run 4 (KIT-OPS-6, receipt placed beside the LEF) is the first run that can pass gen; no result yet.

### M7. Plan timing audit: 32 FAIL rows

22 tile rows were a rule artefact (verdict (c)); fixed in `plan_timing_audit.py` @dea1a73bb3. MEASURED on `audit3_QC`: FAIL 0, PASS 80, UNMEASURED 247 rows in 50 types (14 would fail on the library fallback). The 247 are the next work list, not the old 32.

### M8. Single rows, not diagnosed in this pass (owner named, no verdict)

- `cbn_q00__cldbcda913` gen `KeyError: 'src'`, repeated 22:57 and 00:31 (a3 epyc7, a4 intel1): the item cannot start. KIT-OPS-5.
- `sle_st_a_v2__pv30dda31f` kit_rtl bind `param_wrap u_r0 ... station_tail1_nb0 #(.ADD_LAT(7)`; `sle_st_a_v1__cl67389ecd` KIT_NOT_SELF_CONTAINED (path under tl-qcstav2). TL-QCSTAV2.
- `sle_su_l0__cl086d85ba` late ECO route DRT-1231 (no access point on `_13403_/A`, 1,903 violations). NEARMISS-FIX-1 / PG-AWARE-1.

## 2. Verdicts on the posted claims

### (a) QC-HOLDGRT-1 accept rule: CORRECT, INCOMPLETE

- fw_v1 cl9d029624: MEASURED -109.60 ps / 11,536 endpoints -> +4.04 / 0, 22,934 hold cells (+6.1 %), TT estimate -305.49 -> -306.61. The old rule threw this away for 1.1 ps. The setup arm (reject only below -42 and more than 5 ps under the floor) is right.
- hc3: MEASURED pass 2 reached +5.0 ps, 0 endpoints (setup before +106.2; final line not written yet).
- stm_v1: -98.27 after pass 2 is not a repair failure and not a regression. It is M3: 3,260 setup-locked port_in endpoints.
- Gap: the hold arm is unchanged, see M3 fix 1 and 2. Without them the other FALLBACK kits stay FALLBACK and GRT stalls on the port residue.
- Cost to watch: 22.9 k to 32 k hold cells per kit, most of them padding ports to a -85 ps contract. Report the port_in share of hold cells per kit; if die STA shows the real seam needs less, the contract moves, not the kits.

### (b) DIE-QC-103 S4c, R8 re-derive, S4f taps: CORRECT, two corrections

- S4c adoption: fine. Bind 0 errors, LAND_R8 changed 0, LATCHECK 1921/1921, G0 = the 2 baseline face-density errors. Its only delta over S3R3b is (e).
- R8_STALE on the S4 family is expected, and the pinned re-derive is the right form. MEASURED by me, table `r8_s29q103S4E.derived.json` against seed S3D2, compared by member id: 1,380 of 9,050 members changed, 0 added, 0 removed, max depth 49 unchanged, pad flops 1,266,161 -> 1,337,969 (+5.7 %). Changed members by sink <- source partition: su_c <- ctl 492, st_a / st_b <- ctl 576, fw <- ctl 60, st_a / ctl <- stm 96, fw <-> fe 73, fw <- stm 18, coll_core <- fw 17, cb `n_b` 48 (+2, y_o23). Sum 1,380. Deltas are +1 on the E side and +2 on the W side of the ctl and su_c lanes, which fits rep4v (+1) plus the W su_c / fw stations (INFERENCE on the attribution). No lane outside the S4 delta moved.
- Still to show before READY: the rebinds S4EQ / S4CEQ / S4FQ (started 00:16 PST, still running at 00:42) must end with R8 check "changed 0", 0 errors, LATCHECK PASS. One derive is enough only if that check is clean.
- Correction 1: the sc2 and coll depths are NOT from unsigned runs. MEASURED `qcviews_1111/views/<core>/insertion.json`: source = `signoff.json corners.{tt,ff}.insertion_pinflops` of the SIGNED run. sc2_leaf TT 406.39 (spread 25.9), FF 332.54; ot_coll_fold_slice TT 208.25, FF 170.77. The audit row field `signed: false` is a harvest flag bug (DIE-QC-103 / PLAN-READERS-1 to fix).
- Correction 2: S4f scales FF by the TT ratio: sc2 `insertion_ff_ps` 348.2 against measured 332.5 (16 ps high); coll 168.6 against 170.8. Put the measured FF values in before S4f is bound for adoption. 10 types change.

### (c) QC-CORES-HEAD tile arc and vmr receipt: CORRECT

- Tile: MEASURED `insertion.json` of qfd_tile_nk_a0c: pin-register insertion TT mean 733.25 (min 351.5, max 781.1). The library arc is from the ck pin, so clk->q 923 = insertion + about 190 ps. With the early tap (733 - 250 = 483) the output leaves at about 440 ps after the die edge (nl: 414). The 22 rows are an audit artefact. No library or core change.
- Limits of that statement: the insertion spread is 430 ps, and the shallow flops are on the input side (setup arcs -212 to -732). The audit floors negative setup at 0, so it does not judge the input side or hold. That is the lock-up pair class of FABLE-QC-CB (CB-LOCKUP) and the die STA with the real view. Also the tile view is `LOCAL_PASS_NEEDS_PARENT` with FF -41.25: the parent owes that hold.
- vmr v2: MEASURED LEF diff base -> v2: only OBS on M5 (3 windows, x 122.40-122.90, 123.35-126.55, 127.70-128.20, y 105.40-110.60) and M6 (x 122.0-128.6, y 105-111); pins byte-equal; the M5 PG straps at x 123.024 / 123.216 / 127.344 / 127.536 stay under OBS; the five pins sit inside the windows. `detail_view()` passes. The v1 window held real core metal and v2 removed it (QC-CORES-HEAD 20:57, `winchk.py` against the signed DEF; not re-run by me).
- One weakness: the receipt was written by hand (`mkrcpt.py`, `check_ok: true` typed in). Add the `winchk.py` output sha to the receipt so the claim "0 foreign shapes" is tied to a file.

### (d) TYPE-QCCB-GEN head-hop patch and xstn: CONSISTENT, proof pending

- 635 -> 459 on cbn_q01 matches the FABLE-QC-CB split: 635 = 164 head-hop nets over t12 + 441 xstn tap nets over t13 + about 30. Removing the head hop leaves about 459. The patched hook itself has no result yet.
- xstn: MEASURED RTL `qfd_c_xstn_safe`: one register bank `b_q` (516 flops) drives both `a_d` (to the out-boundary register) and `tap_p` (380 bits to the tile tap). One bank cannot sit within 405 um of both when they are 460-970 um apart. So siting alone cannot fix the upper range: correct. Both parts are needed: the xstn at the tap face (generator, in the patch) and the stations on bc_o (plan, S4g).
- S4g must take the whole family in one event: cbf_q01 and cbf_q01_s2 carry u_t13 / u_t03 too and are left out today.
- Alternative with 0 cycles (not recommended now): a second copy of `b_q` in the RTL. It changes all 16 cb types; S4g changes 3 to 5.

### (e) su_c tap 960 -> 900 with sink bins: CORRECT, proof pending

- MEASURED plan delta `zz_s29_qc103_s4a_tapd2.json`: cl19bb38ef gets `sink_bins_file` (64,597 registers, 8.64-um bins) and `tap_target_sinks` 900, the same form as the passing sibling. 30 -> 135 taps, max planned sinks 955, 0 empty; 12 forwarded-clock outputs re-fit to a tap 21-58 um away. G0 adds no error.
- The 960 -> 900 number is not the fix; the sink inventory is. Proof = one cl19bb38ef kit: CTS depth 7 or less, hold gate pass. It waits on M6.

## 3. Stop list

1. Do not count or relaunch as design failures the rows that failed 22:56-00:24 with `ot_store` or a banner-only reason. Re-key them with stage resume.
2. Do not send stm_v1 / fw_v1 / sc_v1 / fe / hc3 / st_b to RTL or to a split for "HOLD_STRUCTURAL" or "hold stall". The residue is port_in and setup-locked (M3).
3. Do not add hold passes, a larger guard or `-allow_setup_violations` to close the port_in residue in the kit.
4. Do not relaunch the 8 hold-stall types before M3 fix 1 and 2 are in the QC source; the installed patch alone leaves the "no hold gain" veto and the GRT stall.
5. Do not bind S4f for adoption with ratio-scaled FF taps; use the measured FF values.
6. Do not act on the old 32-row audit list or on a budget of 450 ps; the list is 0 FAIL after the audit fix.
7. Do not re-sign or re-export the nk / nl tiles for the 923 / 938 ps arcs.
8. Do not capture a new qualified-FT proof for vmr; the detail receipt path is the sanctioned one.
9. Do not relaunch cb routes unchanged, mirror tiles, or change the tile tap 483 -> 568 (as FABLE-QC-CB and the strategy review said).
10. Do not launch S4g for cbn_q01 alone; add cbf_q01 and cbf_q01_s2.

## 4. Owners

| item | owner lane |
|---|---|
| M1 re-key + classifier | KIT-OPS-5 |
| M1 paired install + smoke test | WAVE-BALANCE-1 |
| M2 su_c re-key | KIT-OPS-6 |
| M3 fix 1 + 2 (hold arm, stall count) | QC-HOLDGRT-1 |
| M3 fix 3, S4f FF taps, S4g family, R8 rebind check | DIE-QC-103 |
| M4 patch proofs q00 / q11 / q01 | TYPE-QCCB-GEN |
| M5 / M6 su_c proof, receipt sha | KIT-OPS-6, QC-CORES-HEAD |
| M7 `signed` flag, 247 UNMEASURED rows | PLAN-READERS-1 |
| M8 rows | KIT-OPS-5, TL-QCSTAV2, NEARMISS-FIX-1 |

## 5. What I ran

One read-only STA (ot-run, epyc7, 8 threads, about 3 min) on a copy of the stm_v1 proof kit: `/srv/opentallas-scratch2/claude/fable-triage-qc/stm_v1/` (`whatif.tcl`, `whatif.log`). Two table diffs on epyc9 (`/srv/opentallas-scratch2/claude/fable-triage-qc/r8diff*.py`). No kit, plan or owner checkout was changed.
