# DIE-QC-12 (2026-10-28 09:17-10:05 PDT) QC die owner

Runs: intel2:/srv/opentallas-scratch2/claude/die-qc11-1028 (trial10, CA t10) and intel2:/srv/opentallas-scratch2/claude/die-qc12-1028/a0trunk.
Numbers are OWN / UNCHECKED-independent unless marked CHECKED.

## 1. trial10 (inv2: even inverters per leg, 2-stage root, early 1.48/1.28) collected
- Kit 08:49-09:21 (32 min: region DME join recursion in inv2 mode, not hung: py-spy showed progress). Clock-only GRT TT/FF done 09:24.
- Duty (duty_eval, NLDM both edges, CHECKED from c10_{TT,FF}): TT 48.2-51.3 %, 0 outside 45-55, MPW 0 fail.
  FF 49.9-55.75 %, 36 taps over 55 % (worst t_c_W5_tf_00__clk_t20 high 464.4 / low 368.6), MPW 0 fail.
- Spread (eval10): c_* 66.1 med / 106.2 max TT (OCV-est 140.9), 0 regions >150 (trial9: 96.2/167.6, 101 >150).
  su_c 75.0/94.2 TT, 0 >150. FF c_* 62.6/98.4.
- Render trial10_plan_die.png viewed: ladder feeds and in-region DME trees as planned; no gross detours.
- CA on built arrivals (runCA10.sh, START-TREE-1 --start-tree clock):
  - phase: 2537/2537 at D4, 0 FAIL, min lo 104.5 / hi 128.7. 483/483 start edges clean, MC 300 chips 0 violations.
  - width: crossings 2524 D4 + 13 D8, 0 crossing FAIL, min lo 104.5. START width: 60 of 871 start edges FAIL, so the release target is not met.
- Width start-fail STRUCTURAL CAUSE: all 60 are non-retimed slice-head reset-release edges:
  - by type: sl_*_ctl->st_a/st_b 24, sc->stm 11, sc->ctl 5, stm->sc 4, ctl->hc2 3, plus st_a/sc->virtual 12 and stm->coll_f4 1;
  - spread over all 12 slices.
  - The capture side has median 880 ps unshared clock (launch 428), against 296 on clean non-retimed edges. Interval width is 263-397, median 354 (clean median 154).
  - Cause: the slice-head regions stm/sc/ctl/st_a/st_b exchange the start chain, but rt2 feeds them from different feed branches. Their clock fork sits far above them, so the start chain does not follow the clock.
  - Fix (plan): feed the slice-head group of each slice from one shared node (clock follows the start data), or put the width-mode start retime nodes at the clock fork. No per-port fixes.
- Die STA (sta_clock, hold-buffers none):
  - count-align TT 2537 worst lo 110.6 PASS; FF lo 104.3 PASS. Start-skew 0/483.
  - intra FF hold -281.9 (trial9 -327.4), seam FF hold -143.3 (trial9 -188.7). Not yet structurally fixed.

## 2. A0 PARENT local trunk (owned; contract lanes/QC-A0-KITS.md 08:36), parent nk
- Flow, all plan / no ECO:
  1. dump the placed ck sinks from QC-A0-KITS-3 parent nk 3_place.odb (15,013 regs + 19 child pins);
  2. clusters.py: 57 glue clusters, <=160 um box, no macro straddle, small ones merged. Each gets a CKINVDCx16 root at its site and a TritonCTS local tree. Internal spread <=23 TT; insertion from root A 50-141 TT, re-measured with real trunk input slew (clins_nk2);
  3. trunk.py: centre entry (228.972,578.88) -> ICGx8DC (QC-PG-4 site, 3 um from the entry, A0 tile root, below the die crossing nodes; trial ties ENA=1/SE=0, RTL step separate) -> DME of CKINVDCx16 (every stage an inverter, parity even to every flop by construction: 0 odd sinks). Child sinks carry the view insertion (fixture ETM budget). Romleaf legs aim at the NEW romleaf clk pin (21.612,15.12), mirrored for MY;
  4. ins_trunk.tcl inserts and legalises (max displacement 4.3 um); meas.tcl measures TT/FF propagated, placement RC (setRC_rcx).
- Best build nkg110 (greedy, 110 um segments, 211 INV, 8.6 mm):
  - regs TT 502.9-581.1 (mean 535.0), FF 431.0-497.8 (456.6);
  - rawleaf pin+budget 518-531 TT, node 538;
  - romleaf 587-593 TT. This is +55 because the fixture LEF still has the old centre pin: the planned leg ends at the new pin, then ~100 um of unbuffered wire runs to the fixture pin. Expected ~530 with the a0k5 abstract (UNCHECKED).
  - All endpoints TT 503-593 (spread 90), FF 431-515 (84), against the target ~500/~420 with <=60.
  - Without romleaf: ~78 spread (cluster internal + DME residual).
- Model: an empirical stage table (fit2.py, 3 builds, ~850 stages) replaces the first quadratic model. Short stages were mispriced (stacked 4-um padding stages measured ~8 ps vs 13.7 modelled; trunk nkg110b dev -94..+3).
  - With the table, plan nkt110: 526-567. Measured clusters dev -45..+3 and romleaf 620-627 (same fixture-pin effect), so the spread got worse (147).
- Render a0trunk_nkg110.png viewed: trunk in the centre channel, cluster roots in the channels. PASS-COND: several last legs run unbuffered over child macros (rawleaf fixture pins at macro centres, up to ~120 um). Real views or abstract pins are needed.
- NOT done: nl variant; c_* centre-entry die change (needs a trunk that meets the contract first); A0 tap delay = trunk insertion (the measured nkg110 TT mean 535 / FF 457 is the current number to plan with).

## 3. Not done (next)
- FF duty 55.0-55.75 % on 36 taps: centre with spice-sized inverters / root driver in the plan.
- FF hold structural fix (region-tree balance); HB4 waits on FLOW-GEN-1.
- A0 trunk:
  - DME with wire elongation (die_trial merge_point snake) instead of padding-stage stacks, priced with the stage table;
  - refresh the romleaf/rawleaf abstracts (a0k5 pins);
  - then the nl variant + c_* centre entry.
