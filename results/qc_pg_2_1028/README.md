# QC-PG-2 (2026-10-28): QC IR at 150-um bumps on PRODUCTION su8 activity

Deck/method = QC-PG-MAP (claude/qc-pg-map-1027@91e2ffb77a) upper deck (M9 .672, 150-um bumps / 70-um pads, R35 plan),
exact linear class superposition (S signed cores, U8 su8 alone, A = A0 tiles, F = flattened partition logic), as
Codex su8_superpose.py (codex/qc-activity-0359-1028@4fc469ac5c); tools/pg_activity/qc/su8_superpose2.py only splits the
background into A and F densities and adds an "all non-su8 nodes" window. 35 mV = VDD drop + VSS bounce co-located,
upper + below-M7; su8 below-M7 6.602 mV kept (own-vectorless 30.2 mW in-core solve, conservative at 12.6 mW).
Reproduces Codex: 50.426 (vectorless 33.7 mW), 40.690 (stress 22.4 mW), 31.984 (clock floor) at bg 0.5823 (CHECKED).

## 1. Production su8 activity (Codex run, collected; CHECKED as run outputs)
QCLM production replay (epyc2 codex-qc-activity-0359/qclm, source tok-qk-qclm-r2, 8 cases, trace_identical PASS),
402 su8 signals / 6809 bits of g_s[0].g_w5.u_suvm.u_su8; power on the SIGNED su8 rst3_k0/hold_b 6_final odb + SPEF,
propagated clock (intel1 codex-qc-activity-0359/su8_production_activity, copy su8_production_power_summary.json).
| case | su8 W (unmatched 18 FF at 0.5 / 1.0) |
|---|---|
| L0_gu / od / qk / qkv / silu / lm | 12.396-12.420 / 12.529-12.553 mW |
| L0_resid2, L0_resid1 (qualified window) | 12.429 / 12.562 mW (max) |
| clock floor (zero data) | 12.262 mW |
| random stress (old basis) / vectorless | 22.38 / 30.25 mW |
Matched 4637/4655 FFs, 487/488 inputs; L0_resid2 rpt: clock 6.374 + sequential 5.926 (clock-pin internal) + comb 0.262 mW.
su8 power is clock-floor bound: data adds only 0.30 mW. Duty: in L0_resid2 su8 handles 72 valid items in 6222 cycles
(v[0] 0.0231 toggles/cycle); boot+idle <= 2830 cycles (shortest case), so the steady-state op share is >= 55 % of the window
-> data x <=1.8 -> su8 <= 12.8 mW (UNCHECKED bound). It fails 35 mV only if data were x11.7, i.e. never at production duty.

## 2. Composed QC IR, 150 um (mV; superpose.jsonl)
| window / basis | su8 W | bg A0 / F W/mm2 | upper (VDD+VSS) | below-M7 | total | verdict |
|---|---|---|---|---|---|---|
| su8 window, production max | 12.562 | 0.5823 / 0.5823 (canonical cap) | 25.64 (14.29+11.35) u_b39_33 | 6.602 | 32.24 | PASS |
| su8 window, duty-bounded | 12.8 | 0.5823 / 0.5823 | 25.85 | 6.602 | 32.45 | PASS |
| su8 window, old stress | 22.38 | 0.5823 / 0.5823 | 34.09 | 6.602 | 40.69 | (retired: not production) |
| su8 window threshold | 12.562 | F <= 0.69 | 28.36 | 6.602 | 34.96 | PASS iff F <= 0.69 |
| A0 window (u_b50_12) | - | 0.60 / 0.27 | 29.07 | 4.6 (QC-PG-MAP) | 33.7 | PASS iff A0 <= ~0.62 |
| A0 window, measured floor | - | 0.417 / 0.27 | 20.40 | 4.6 | 25.0 | PASS (floor only) |
| F-only window (u_b53_51) | - | 0.5823 / 0.5823 | 29.36 | 4.6 | 33.96 | PASS (QC-PG-MAP HC window) |
The su8 window has zero A0 sensitivity (A unit response 0.002 mV); its background is the su_c partition's flattened logic
(F, 25.26 mV per W/mm2). So the QC failure that triggered the 75-um question is gone at measured su8 activity, even with
the unmeasured F background at the canonical 0.5823 cap. 75-um field NOT solved (owner rule: only if still failing).

## 3. Background (non-su8) activity: what is and is not measured
* F (flattened logic, su_c strip): QCLM has the logic but no power netlist exists for slw_su_c (only STA register skeletons:
  10,573 FFs clbb0c543d / 14,693 FFs qfd_qc_slw_su_c over the 1.0787 mm2 F area). Per-FF power from the signed su8
  (floor 2.63 uW/FF, data 21.3 uW/FF per toggle/cycle) gives F 0.03-0.04 W/mm2 at zero data and <= ~0.18 W/mm2 at a
  flat 0.5 toggle rate on every FF (ESTIMATE, UNCHECKED: census from STA skeleton, comb/FF ratio of su8). Well under 0.69.
* A0 (qfd_tile_n[kl]_a0c, 768 tiles): NOT in the QCLM production model (no ot_qwen_tile / rom_tile modules), so production A0
  activity cannot be measured from it. Measured (Codex qc-a0-activity-0359, child CTS dbs): activity-independent floor
  clock 0.248 + assumed ROM macro 0.169 = 0.417 W/mm2 (NK); correctness-stress child total 1.284 W/mm2 (no parent glue).
  A0 window passes iff A0 total (floor + child data + parent glue/clock) <= ~0.62 W/mm2, i.e. data+glue <= ~0.20 W/mm2
  (~107 mW per 0.530-mm2 NK tile, ~23 % of the stress child data 0.460 W). This needs the production A0 calendar duty
  (Codex root owns the measurement). This is the only open QC PG term; it is an A0-window question, not su8.

## 4. Side runs
* KV tile glue IR (ir_tile.tcl, PG-CORECONN-3 method) LIVE: intel2 docker qcpg2-ir-kv_hroot (48 GB cap), kit
  codex-kv-physical-prep-1027/gen1/kv3_hroot 3_place (15,044 std cells / 6,592 FF over 1.59 mm2, 0 landable macros),
  OT_ACT 0.263 (HEAD measured, UNCHECKED for KV), out intel2:/srv/opentallas-scratch2/claude/qc-pg-2/ir/kv_hroot.out,
  volt_kv_hroot_{VDD,VSS}.rpt, done.txt; collect with ir_summ.py DIR kv_hroot. KV dp tiles are sparse (8-15k cells per
  1.3-2.1 mm2 vs S81's 166k per 1.77 mm2), so a S81-like 13 mV cluster is unlikely (UNCHECKED until the run ends).
* HBM hub activity: ot-run unit oth-ubuntu-1837203-1793193526 still compiling at 07:48 (intel2 pg-coreconn-3/hbm_hub);
  not collected. See lane file for the collect list.
