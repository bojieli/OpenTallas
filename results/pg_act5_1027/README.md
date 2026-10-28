# PG-ACTIVITY-5 (2026-10-27): QC .672 below-M7 verdict, HBM measured-SM canonical deck, upper-deck STA double-count check

Deck: canonical (150-um bumps, 70-um pads, VDD drop + VSS bounce co-located, <= 35 mV). Below-M7 = every M7 node ideal
(-source_type FULL, PG pins on M7), so M7 lateral spreading stays in the above-M7 deck only. Exact load-only numbers use
superposition (set_pdnsim_inst_power ADDS to PSM's STA instance power, PG-ACTIVITY-4): drop(A) - drop(B) per terminal.
All PDNSim numbers below are this lane's run outputs (PG_CHECK OK, EXIT 0) = CHECKED as solves; the power BASIS of each is
labelled. No QC measured-activity (RTL toggle) map exists; none was built here (see section 1.4).

## 1. QC .672 (upper 30.403 mV CHECKED, flat canonical 0.5823 W/mm2 "region model, owner cap"; below-M7 budget 4.597)
### 1.1 coll_ftm (Codex vehicle), collected runs (not re-run): intel2 pg-act-3-1027/qc_orig_full (A) + pg-act4-1027/qc_sta_only (B)
| load | below-M7 colo max | worst cell | total | verdict |
|---|---|---|---|---|
| flat canonical 0.672 W by cell area (A-B, exact) | 20.429 (VDD 10.651 + VSS 9.778, p99 16.45) | u_ft_out_data_rd_wi_s0/q[186] (441.18, 4.59) | 50.83 | FAIL |
| own vectorless STA power 0.0342 W (B alone) | 3.349 (p99 1.78) | clkbuf_leaf_4_clk_t14 | 33.75 | PASS |
INFRA-FIRST-QC-R35's 20.429 reproduced exactly (same two runs; this lane did not duplicate them).
Why 20.4: coll_ftm is a 786.24 x 1468.8 um feed-through block with 80,260 cells = 11,721 um2 of cell area = 1.01 %
utilisation; normalising 0.5823 W/mm2 x block area by cell area puts 0.672 W (20x its own STA power) into 1 % of the area
(20-um bins up to 6.3 W/mm2, 10.8x canonical). This vehicle over-concentrates the flat load; it is not a physical QC load.

### 1.2 Dense signed QC cores (autopilot closed + qc/closed, read-only 6_final odb/sdc/spef), QC partition straps added
Straps = coll_ftm signed partition PDN (M6 0.288@4.32, M7 0.288@8.64, checked on the odb; tools/pg_activity/qc/).
| core (area mm2, util) | own vectorless W (W/mm2) | below-M7 own power | worst (own) | below-M7 flat canonical (A-B) |
|---|---|---|---|---|
| qfd_dv_s8x_vmr f4kfinal (0.0541, 5.3 %) | 0.0119 (0.22) | 4.390 PASS | ot_ms_Q2B0L2_tap (mesh tap) | 5.372 FAIL |
| qfd_dv_s8_crh_rp1 f62 (0.0717, 2.5 %) | 0.0098 (0.14) | 4.282 PASS | clkbuf_2_1_0_ot_ctap_W0_n | 10.876 FAIL |
| qfd_dv_s8x_prog s8b (0.0918, 3.2 %) | 0.0169 (0.18) | 5.989 FAIL | clkbuf_2_2_0_ot_ms_Whi_clk | 6.927 FAIL |
| qfd_dv_s5_su8_rst3 (0.0224, 17.9 %) | 0.0337 (1.51) | 6.602 FAIL | clkbuf_5_30_0_ck (p99 5.15) | 1.590 PASS |
(own W = OpenSTA report_power vectorless, spef; PSM's internal charge is 0.0096/0.0085/0.0132/0.0292 W.)
QC totals: flat canonical basis worst 30.403 + 10.876 = 41.3 FAIL (coll_ftm 50.8); own-vectorless basis worst
30.403 + 6.602 = 37.0 FAIL (su8), prog 36.4 FAIL, VMR 34.79 / crh 34.69 / coll_ftm 33.75 PASS.
VERDICT: QC .672 does NOT pass on either basis available today. It is NOT a measured-activity result.
Mixed basis caveat: the upper 30.403 uses the flat 0.5823 cap while su8 alone draws 1.51 W/mm2 vectorless (2.6x the cap):
the flat cap is not a bound near SU cores, and is ~3-4x above the large cores (0.14-0.22 W/mm2).

### 1.3 Structural options (CHECKED where a solve exists, else ESTIMATE)
| option | below-M7 effect | QC total | status |
|---|---|---|---|
| M6+M7 partition straps 2x width (0.576@4.32 / 0.576@8.64) | VMR 4.39->4.17, prog 5.99->5.69, su8 6.60->5.50 (own); VMR canon 5.37->4.44 | 35.9-36.1 still FAIL (prog/su8) | CHECKED solves; M6/M7 PG 13->27 % tracks |
| M7 2x pitch (0.288@4.32) | VMR 4.39->4.24 own, 5.37->4.62 canon | ~-0.2..-0.8 | CHECKED (VMR only) |
| M6 2x pitch (0.288@2.16) | VMR 4.39->3.91 own, 5.37->4.72 canon | ~-0.5 | CHECKED (VMR only) |
| QC upper deck on a per-core power map (own vectorless now, measured later) instead of the flat 0.5823 cap | upper scales ~linearly with local W/mm2: large cores 0.14-0.22 -> est. 8-12 mV upper in core fields; SU fields need their real 1.5 W/mm2 | est. 15-25 mV | ESTIMATE (UNCHECKED); biggest lever |
| QC measured RTL activity (KV method) | data part x ~0.55 (KV ratio); clock-buffer hotspots (all 4 worst cells) unchanged | su8 est ~4.5, prog ~5.5 below | ESTIMATE |
| core-local: clock-buffer hotspots (prog ot_ms_Whi clkbuf, su8 clkbuf_5_30_0) placed on M5/M6 strap crossings or split | below-M7 floor is the signed core PDN (M1/M2 rails + M5 0.12@4.32): 3.9-4.2 mV even with 2x straps | - | needs core re-sign |
| 75-um bumps | above-M7 only; OWNER: only if 150 still fails after the measured map | est. upper ~0.5x | ESTIMATE, not proposed now |
Recommended order: (1) QC per-core power map for the upper deck (own vectorless, then measured) -- removes the cap/cell
mismatch on both sides; (2) re-judge; (3) only then straps 2x width or 75-um bumps.

### 1.4 QC measured-activity map: not built
No QC RTL toggle-rate map exists (searched lanes + branches). Building one = full QC slice workload VCD -> per-core
register activity -> report_power per core type (KV method, tools/pg_activity) -- a lane of its own (~2-3 h incl. sim).
The worst below-M7 cells on own power are clock buffers/taps (activity-independent), so measured activity alone will not
close prog/su8; the upper-map change (1.3 row 4) is the lever.

## 2. HBM measured SM activity (replaces the UNCHECKED 30.4 mV x1.202)
Activity: 14 cases (ot-run unit oth-ubuntu-473444-1793147036, intel2 pg-act4-1027/hbm/case*), act_merge.py ->
peak = case1 (3072 x words, 2351 cycles, summed rate 271,752), cycle-weighted mean over 32,057 cycles. Register names mapped by
longest hierarchical suffix (tools/pg_activity/sm_match.py, Codex PG-ACTIVITY-2): S 130,929/145,605, N 135,169/149,992,
BDC 10,658/10,670 (unmatched = matched mean). Power: core_power_meas.tcl on intel1 (placed halves 3_place, BDC 3_place+4_cts).
| | S half W | N half W | BDC cts/place | SM slot W/mm2 |
|---|---|---|---|---|
| flat 0.5 (old upper bound) | 0.7906 | 0.8364 | 1.202 | 1.3656 |
| vectorless | 0.4446 | 0.4548 | 1.189 | 0.7550 |
| measured mean | 0.2184 | 0.2253 | 1.932 | 0.6051 |
| measured PEAK (used) | 0.2244 | 0.2318 | 1.920 | 0.6182 |
(additive clock-per-register alternative 0.5925; max taken.) Codex's c0/c1 estimate 0.610/0.614 agrees.
Map: bump-survey hbm_loads.json, 8 SM rects 2.1787 -> 0.6182, 80 others kept (10-24 estimate). Deck = KVHBM hbm_flat05_E
kits byte-identical except loads (B2r2 plan, G12E M8 0.48@4.32 / M9 12.96@34.56, edge-fill lattice margin 60, pad 70).
| window (PDNSim, intel2 units oth-ubuntu-2550274/2550276-1793158934) | W | above-M7 colo (canonical interior / die-edge strip) | flat-0.5 same kit |
|---|---|---|---|
| G12E_p70_int (all SM) | 5.461 | 11.315 (VDD 6.239 + VSS 5.076, u_b53_24) | 24.99 |
| G12E_p70_edgeW (die edge + inner, open edges keep-off 450) | 3.810 | 11.200 (u_b24_56) | 24.74 |
Linearity check: 24.994 x 5.461/12.0633 = 11.31 vs solved 11.315 (int window is all SM). Collector results/pg_act5_1027/coloc.py (= pg_act3 coloc.py)
reproduces the flat-0.5 kit numbers (24.994 / 24.742). HBM total = 11.315 (CHECKED, measured SM activity; non-SM blocks still
10-24 estimate) + 5.13 below-M7 (UNCHECKED-ESTIMATE) = 16.4 mV PASS (old 30.4 x1.202 retired).
Below-M7 HBM 5.13 stays UNCHECKED-ESTIMATE (HEAD-5 slice; no SM final odb exists).

## 3. Upper-deck placeholder loads: no STA double count (CHECKED)
infra_pg.window_kit loads are `irblk` LEF-only macros (no liberty cell). Probe on the KV ef39_LR deck (same generator as
KV/QC/HEAD/HBM upper decks): report_power total 0, sta::instance_power nonzero on 0 of 4830 instances,
get_lib_cells */irblk empty (tools/pg_activity/upper_sta_probe.tcl). PSM "Total power" equals the explicit load sum on all 8
KV edge decks (4.7024/4.7294/3.5838/3.6018 W). So the ADDITIVE set_pdnsim_inst_power issue does NOT affect any upper-deck
number: KV/QC/HEAD/HBM upper parts are exact for their loads; no re-solve needed.
