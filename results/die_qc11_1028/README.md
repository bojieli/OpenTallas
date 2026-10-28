# DIE-QC-11 (QC die owner): plan event K2b-L on the rt2 local form — duty-cycle fix (inverter tree), feed-end fix, START-TREE-1 start ports

Runs: intel2:/srv/opentallas-scratch2/claude/die-qc11-1028. Plan inputs as DIE-QC-10 (codex-die-qc-0359-1028/build_inputs, K2b event,
part_region, rt2 feed `plan/feed_rt2.json`). START-TREE-1 tools: claude/start-tree-1-1028@91c2e9fec3, exported read-only (`st_tools/`),
not forked. Labels: CHECKED = my own run on the named files; UNCHECKED = model or not independently rechecked.

## 1. MEASURED FAILURE: duty-cycle distortion on the BUF-only forwarded clock (trial8)
- Probe: the trial8 clock-only GRT rerun with both edges reported per tap (`duty/c8d_{TT,FF}/arr_*.txt`, `F port fall rise slew`).
- die_trial emitted only BUFx24 (29,112 cells, 10-170 stages root->tap). The fall-minus-rise delay grows ~3.8 ps per stage TT.
- `duty_eval.py` (high pulse = T/2 + spice x (fall - rise); lib MPW of DFFHQNx1 on both phases; target 45-55 %), CHECKED:

| trial | corner | duty min / med / max | taps outside 45-55 % | MPW fail |
|---|---|---|---|---|
| trial8 (BUF) | TT | 0.536 / 0.959 / 1.321 | 7105 / 7121 | 3878 (low phase gone) |
| trial8 (BUF) | FF | 0.526 / 0.867 / 1.161 | 7105 | 2014 |
| **trial9 (inverter tree)** | TT | **0.473 / 0.502 / 0.524** | **0** | **0** |
| **trial9 (inverter tree)** | FF | **0.438 / 0.479 / 0.512** | **51** | **0** |

- Every die STA so far propagated only the rising edge, so no gate saw this. Any die built on BUF-only die_trial trees has it.

## 2. Tool changes (shared, opt-in, defaults byte-identical; 66 die_trial tests PASS incl. 7 new)
- `--clock-cell inv`: every node driver / repeater is CKINVDCx16 (BUFx24 footprint 1.62 x 0.27, same legal sites); a tap with odd
  inverter parity gets one plan-placed inverter at the tap. (trial9)
- `--clock-cell inv2`: every leg gets an EVEN inverter-stage count, priced in `leg_ps` and in the DME snake chains, plus a 2-stage
  root: true polarity at every node and tap by construction, no tap parity inverters (removes the trial9 parity skew). (trial10)
- `--tree-opt dme_feed_centroid=1`: a DME region's feed ends at its tap centroid, not its partition bbox centre.
- Clock-only GRT report (`scripts/mk_clkfirst.py`): F lines (fall/rise per tap), node readout on the true-rise edge for odd-parity
  nodes, `report_check_types -min_pulse_width`. Note: the clock-only netlist has no sequential sinks, so the OpenSTA MPW report is
  empty by construction; the MPW check is applied per tap by `duty_eval.py` from the lib table.

## 3. trial9 = rt2 feed + inverter tree + feed-end centroid (BUILT, CHECKED)
- 33,105 CKINVDCx16 (3,875 tap parity inverters), 0 BUF. Clock-only GRT 2W2S TT/FF EXIT 0, overflow 0, wire 5.724 m.
- c_W5_bf_01 detour FIXED: the feed now runs straight down x = 2133 to the region (trial8: west to x = 1400 and back,
  ~0.7 mm). Render `trial9_plan_W5coll.png` viewed; die render viewed, same form as trial8.
- Insertion: ~313 ps faster median than trial8 (max 8981 vs 9509 TT).
- In-region spread REGRESSED (eval9, TT med/max, regions >150 incl OCV-est): c_* 96.2/167.6, 101 (trial8 73.5/180.7, 34);
  su_c 71.2/151.7, 2 (trial8 56.5/92.4, 0). Cause (CHECKED): tap parity inverters, +19.3 ps median odd-vs-even arrival in
  207 mixed-parity regions (-50..+74), plus the early-hang ratio (1.548/1.293) calibrated on BUFs. -> trial10 (inv2).
- CA on BUILT arrivals with START-TREE-1 `--start-tree clock`:
  - `--start-clean phase`: 2537 crossings D4, 0 FAIL, 0 path ambiguity, worst lo 105.9 / hi 205.9, 513/513 start ports clean
    (201 virtual + 103 retime stages), MC 300 0 violations.
  - `--start-clean width` (release target): 0 FAIL on data crossings, but 17 start ports cannot be made width-clean within 8
    retimes (1104 ports, 792 virtual / 684 retime stages). NOT met on trial9.
  - Bind + die STA (die_sta_related, table, shared droop, spice, cppr-lca, key region, --hold-buffers none): count-align TT
    PASS lo 105.7 / FF PASS lo 121.2, start-skew 0/513 FAIL. Intra-region FF hold -327.4 (skew 295), seam FF hold -188.7:
    FAIL with no hold buffers (HB4 crash is with FLOW-GEN-1); the intra skew is the c_* in-region spread (A0 trunk, section 5).
- Same START-TREE-1 run on trial8 arrivals (INFO; BUF clock is not releasable): phase 0 FAIL, min 105.0, 413/413 clean;
  width 917/917 clean but 605 virtual / 497 retime stages; die STA count-align PASS TT 109.4 / FF 104.8, 0/413 start fail.

## 4. trial10 = inv2 + early ratios 1.48 / 1.28 (re-scaled from trial9 measured in-region delay: TT c_ 0.938, su_c 0.970) — RUNNING
- Kit started 08:49; >25 min CPU (trial9: 9 min). The even-stage filter in the snake search is the likely cost. `after10.sh`
  then runs duty_eval, eval10, render10 and `ca/runCA10.sh` (START-TREE-1 phase + width, bind, die STA). COLLECT: after10.status.

## 5. A0 parent local trunk — NOT built in this slice
- Contract posted to QC-A0-KITS-5 (lanes/QC-A0-KITS.md 08:3x): centre entry M5 (228.972, 578.88), DME trunk to 18/19 child pins
  + ~16 glue clusters, target ~500 TT / ~420 FF, spread <= 60 (DIE-QC-10 estimate, UNCHECKED); die tap early = trunk insertion
  - 250 BY PLAN (--region-dme-early). Trunk uses the inverter cell class.

## 6. Next (DIE-QC-12)
1. Collect trial10 (after10.status): duty 45-55 % TT and FF, in-region spread back to <= trial8, CA width-clean count.
2. If FF duty stays below 45 % on some taps: choose the inverter size / root driver from a spice pair check (FF median 47.9 %).
3. A0 parent trunk build; c_* centre-entry delta; then hold with HB4 when FLOW-GEN-1 merges.
4. NUMBER-CHECK (requested 08:2x) on the release arrivals once trial10 is chosen.
