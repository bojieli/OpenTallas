# DIE-S81-6 (10-28): kit F collected, ASK-1 trunk estimate, fanout slew legs

Data: intel2:/srv/opentallas-scratch2/claude/die-s81-5 (kit/clk/out/proof/sta/lpo/ca _F) and
intel2:/srv/opentallas-scratch2/claude/die-s81-6 (est/, sta_F_inreg/).  CHECKED = read from the run logs myself;
UNCHECKED = estimate or inference.

## 1 Kit F = kit E + DIE-QC-3 2de66bb213 --clock-rc 1x --region-dme delay, GRT with clock 2W2S NDR (chain_F, done 02:47)
* Clock: 24,524 cells (7,252 repeaters), CTS wire 3.985 m (CHECKED kit_F/clock/tree.json).
* GRT0 incl clock, TT+FF, 50 it, crit 0: EXIT 0, overflow 0 on every layer; M4 3.04 / M5 4.38 / M6 4.91 / M7 8.58 /
  M8 0.86 / M9 0.99 % (CHECKED logs/grt_F.log).
* ASK-2 condition (scripts/guide_clk.py on route_{TT,FF}.guide): routed clock guide wire 3.958 m vs CTS 3.985 m = -0.7 %
  (limit 5 %); clock guide segments on M4-M7 longer than one GCell = 0 (only the pin via stacks) -> the in-pass NDR counts
  as clock-first; no separate frozen pass needed (CHECKED).  Kit E same check: -2.4 %, 0.
* Slew: 0 violators TT and FF (report_check_types empty; max cell input slew 214.7 TT / 213.1 FF ps) (CHECKED).  The 6
  fanout legs of kit E (feed branch nodes b64/b104/b144/b212/b314 driving 4 legs of 180-247 um) are gone -> step 3 moot,
  no node split built.
* Die STA, main die_sta_related --cppr-lca x1.00: intra TT setup +458.49 / FF hold -198.60, skew 163.5 TT / 136.4 FF.
  Gate form --clock-cal spice: intra TT setup +422.93 / FF hold -210.09 (kit-contract -143.96), skew 171.4 TT /
  144.0 FF -> intra spread FAILS <=150 at TT by 21 ps (CHECKED logs/sta_F_*.log).
* In-region spread per region (scripts/inregion_F.py = the same shared spice run with its pair damages captured,
  inregion_F.json): 397 regions with intra pairs, p50 64 ps TT, ONE region over 150: fE3_p2_b0
  (col_h9_r0_p2__t1, 76 hard cores, dsfd bank macros up to 113,100 um2 -> SRAM/macro partition) 171.4 TT / 144.0 FF.
  Every other region <= 150 TT and FF (CHECKED).  Kit E had 394 TT / 338 FF.
* Count-aligned crossings (landed_phase_ocv main -> MESO-RECONCILE count_align_plan, MC 500): x1.00 0 FAIL, x1.0485
  0 FAIL (D4 2248 / D8 58, lo 105.4 / hi 298.7, max path ambiguity 2), x1.0552 0 FAIL (lo 109.2) (CHECKED logs/ca_F_*).
  Kit E was 28 / 17 / 17.  Max unshared 11.53 ns (E 15.90); off-feed ports > 3.4 ns 69 in 20 pairs (E 146 / 38);
  on-feed max 1.75 ns.  Measured feed rate p50 286 ps/mm (E 368).

## 2 ASK-1 trunk estimate (12.14b; method CHECKED, form numbers UNCHECKED estimates)
scripts/est_trunk.py: cut the measured spine feed bottom-up into segments of height <= H (measured arrivals), feed each
segment root from one balanced zero-skew Manhattan trunk (die clock root 15975,12372; repeaters per 450 um; v_t ps/mm),
keep measured arrivals inside each segment, then price ALL crossings with the unchanged shared tools
(landed_phase_ocv -> count_align_plan, scripts/est_ca.sh).  Control (H = inf, no cut) reproduces the measured kit
exactly: E 17/17 FAIL, F 0/0 FAIL (CHECKED).
| base | H ps | v_t ps/mm | segments | trunk I TT ns | trunk wire mm / reps | CA FAIL x1.0485 / x1.0552 |
|---|---|---|---|---|---|---|
| E | 6000 | 200 / 300 | 16 | 3.5 / 5.3 | 100 / 208 | 41/41 , 88/88 |
| E | 4000 | 200 / 300 | 31 | 6.5 / 9.7 | 206 / 426 | 33/16 , 69/71 |
| E | 3000 | 200 / 300 | 53 | 6.7 / 10.0 | 313 / 632 | 9/9 , 34/34 |
| E | 2000 | 200 / 300 | 124 | 6.5 / 9.8 | 518 / 1031 | 12/25 , 78/100 |
| F | 4000 | 340 | 19 | 9.3 | 141 / 295 | 51/51 |
| F | 3000 | 340 | 31 | 10.6 | 203 / 426 | 67/67 |
Floor (arithmetic, CHECKED): die 31.95 x 24.74 mm, centre-to-corner Manhattan 28.4 mm; any single balanced trunk has
insertion >= v_t x the farthest segment-root distance (~25 mm) = 5.0 ns at 0.2, 8.5 ns at 0.34 ns/mm (COORD 03:1x routed
rate), and every pair straddling the trunk's top split carries that whole insertion unshared.  So "<= 3.4 ns unshared
on every crossing" cannot be met by a trunk; it raises the CA FAIL count at every H.  VERDICT: trunk NOT built.
Not needed either: kit F already has 0 CA FAIL at both spice scales.
Also tried (estimate, kit E): targeted feed re-parent of the 4 failing pairs (scripts/est_swap.py) 17 -> 14 FAIL (moved
subtrees break new pairs); greedy (scripts/greedy.py) round 1 best s_4S_C -> s_3S_C 12/6; stopped when F landed at 0.

## Open
1. fE3_p2_b0 171.4 TT (SRAM/macro partition, gate 150) is the only in-region failure: local tree fix in that region
   (region-dme on the bank-macro legal sites) or one more equal level; builder = DIE-QC-3 code (not forked here).
2. Intra FF hold -210 spice / kit-contract -144 = HB4 per endpoint (as other dies), not clock.
3. lk_ES1 orient = PATH-S81 (unchanged).
