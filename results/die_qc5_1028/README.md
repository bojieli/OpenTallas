# DIE-QC-5 (2026-10-28): NUMBER-CHECK of K2, HB4 hold structure, die_sta_related fixes, 3-pair region merge (K3)

Runs are on epyc2:/srv/opentallas-scratch2/claude/die-qc5-1028. K2 data is from DIE-QC-4 (die-qc4-1028/K2).
The K2 plan is the event plan 40b05f16d753. Die STA is die_sta_related --cppr-lca --clock-ocv table --clock-droop shared.

## NUMBER-CHECK (K2)
- In-region skew 135.39 TT / 117.43 FF: CHECKED. The independent spread (scripts/indep_skew.py) has max 121.9 / 105.6, and 0 of 313 regions are over 150.
- GRT including clock, overflow 0: CHECKED from the logs.
  - Stage 1 (clock alone): 0.32 %.
  - Stage 2 (signal with the frozen clock): 2.89 %.
- TT setup +475.43 and FF hold -162.18 on the pre-scaled proof: CHECKED.
- With --clock-cal spice, main gave +457.35 / -180.36. Cause: scale_clock did not scale the tree node arrivals, which inflated the clock OCV. Fixed on this branch; the two forms are now equal.

## HB4 7.91M
- The number is main's intra BOUND: 2.07M hard-core data pins x each partition's worst k (4). Counted per capture tap it is 5.59M.
- The die is about 160M cells, so this is 3.5-5 %.
- The cause is not skew. It is the clock OCV plus the zero-delay budget data model.
- Breakdown (scripts/hold_decomp.py), c_* median: damage 11.6, OCV 45.4, hold -53.8.
- 72,846 failing paths have damage <20 ps.

## Count-align key
- The bind keys crossings by region pair, but the STA keyed landed pairs by partition pair.
  - Result: 631 bind ports had no taps, and 231 landed partition pairs were untimed.
  - Fix: new opt-in --count-align-key region.
- K2 with --count-align-key region:
  - All 2531/2531 crossings are timed. lag lo is 121.7 / 116.8.
  - 3 region pairs are unbound; they are the 3 CA FAILs.
  - start-skew FAILs 34/312 TT and 21/312 FF.

## K3 = K2 with the 3 FAIL region pairs merged (COORD 04:0x)
- Merges: c_E4_tf_11->c_E4_tf_01, c_W0_bf_11->c_W0_bf_01, c_W0_tf_11->c_W0_tf_01. That leaves 310 regions.
- G0C PASS: 0 errors, 164 warnings. The render g0c_grpPm.png was viewed.
- GRT overflow 0.
- Intra skew 151.50 TT / 132.17 FF: FAIL (over 150).
  - The c_W0_bf_01 region nominal spread is 153.8 TT.
  - Seam skew is 178.06 / 156.19 (9,356 seam pairs, was 7,004).
- TT setup +438.12. FF hold -195.83.
- The CA plan has 5 FAILs.
  - Unbound pairs: c_E4_tf_00->c_E4_tf_10, c_W0_bf_00->c_W0_bf_10, c_W0_tf_00->c_W0_tf_10 and c_W0_bn_11->c_W0_bn_01.
  - The ambiguous start edge moves one hop down the tree.
- start-skew FAILs 34/309 TT and 20/309 FF.
- Verdict: the merge does NOT close. Keep K2.
