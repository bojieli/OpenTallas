# DIE-QC-37 / A0 (sub-agent of DIE-QC-37), 2026-10-29 — deeper planned tile tree (T21), 2 variants vs TritonCTS

COORD ruling 14:18 item 4. Branch `claude/die-qc-37-a0-1029` (origin/main da21832de + merge of Codex WIP
`codex/qc-a0-1355@33418c63c8d`). core_infra opt-in (main 452603b6fbb) **stays OFF for production A0**: neither variant
beats TritonCTS. No pads / trims / delay cells, no RTL / pin / period / uncertainty change, no new check kinds.

## 1. Generator `gen_a0_tree21.py` (new; T11 `results/qc_die36_1029/a0/gen_a0_tree.py` untouched)
- Macro hop ICGs keep their GEOM-PASS placed xy. After each gate: r register-free BUF repeaters along a shortest
  macro-free corridor (3-um grid, macro + halo boxes from `freeze.json` + LEF) to the **actual clk PIN** (LEF pin +
  placement orient, not the macro centre the census/Codex used); r = ceil(corridor / leg); last repeater = macro leaf at
  the legal point nearest the pin. Gate depth = T - k - r (k = signed Liberty view / plan stage model: romleaf 8, LSL 7,
  NK node 7).
- Root registers: ceil(N/21) equal-count leaves (20/21 sinks) at depth T.
- One bounded spread from R (at the port): fanout <= 4; a node splits only when a load attaches, fan-out depth needs it,
  or the load spread exceeds one more leg; else it walks one leg toward the centroid.
- **V1** (`--leg 150 --reg-domains open`): register hop ICGs at T-3, CTS-open (TritonCTS, cts_stages 3) = the ruling design.
- **V2** (`--leg 100 --reg-domains planned`): register hop ICGs become planned domains: every gated register domain is split
  into the same 20/21-sink leaves and built through the same bounded spread (leaf-complete, no TritonCTS). Chosen because
  the DIE-QC-36 run-4 log shows TritonCTS realises 3..14 buffers per gated net (`ck_g` 14, `rn` 3) with
  `-no_insertion_delay`, i.e. the cts_stages-3 accounting of V1 cannot hold.

## 2. Estimate (analytic; formed from the plan reports before launch, written up while CTS ran 14:4x)
| item (UNCHECKED model) | value |
|---|---|
| T | 21 (register insertion 21 x 27.55 = 579 FF / 759 TT vs NL frame 601.9 / 692.6) |
| NL / NK planned cells | V1 278 / 564, V2 1447 / 1751; max fanout 4 (CHECKED in report) |
| macro corridor (gate -> pin) | NL rp0 631.7 um -> r 5 (V1) / 7 (V2); legs <= 150 / 100 + legalisation; leaf -> pin <= 74.8 um (LSL pin at macro centre) |
| max node leg | V1 157.1 NL / 170.9 NK; V2 193.2 / 199.2 (spread tree, not macro chains; 20 legs > 100 in V2) |
| max leaf -> sink | register 178.7 (NL V1) .. 303.9 um (NL V2) — scattered face/edge flops in a 20/21 group |
| IO hold | NL: registers ~= frame -> class gone; NK frame 202.5 -> about -(insertion - 202.5) ~ -250..-375 (still fails) |
| V1 internal | TritonCTS 3..14 levels under register ICGs vs 3 declared -> domain-to-domain skew >> 80 ps (expected FAIL) |
| V2 internal | equal stages, residuals: ICG stage slower than BUF (~+18 FF on gated vs root leaves), leg-length spread, macro view residual |

Renders `plan/{nl,nk}_{v1,v2}.png` viewed before CTS: macro chains follow the centre column (x ~200-268) and the row gaps;
no node inside a macro halo; leaf -> macro-pin legs cross only the target macro.

## 3. CTS on fresh copies of the PASS-COND places (NO re-place; `make -n` = do-4_1_cts + do-4_cts; harness `cts_a0.sh`/`prep_cts.py` of DIE-QC-36)
Copies `intel2:/srv/opentallas-scratch2/claude/dqc37-a0/{v1,v2}/<kit>` from `die-qc34-a0/kits` (NL rr2, NK rr1).
Diag hook = DIE-QC-35 `diag_append.tcl` (hold_fail.tsv + cts_prehold.odb, copy only). ot-run units (intel2), all exit 2:
NL V1 1744596, NK V1 1744597, NL V2 1744613, NK V2 1744614. Late DPL max disp: 1.9 / 8.2 / 3.8 / 9.9 um (bound 60).

Gate numbers CHECKED (cts.log `OT_HOLD_STRUCTURAL`, `OT_HOLD_MM`; class split from diag hold_fail.tsv, IO = port startpoint):

| tile / tree | FF hold ws | fail eps | IO class (n, worst) | internal (n, < -100, worst) | TT setup pre / post repair |
|---|---|---|---|---|---|
| NL TritonCTS (DIE-QC-35) | **-172.53** | 2370 | 528, -172.53 | 1842, 2, -102.96 | — / -223.55 |
| NL plan T11 (DIE-QC-36) | -654.46 | 5718 | | | -699.01 / -616.34 |
| NL **V1** T21 | -429.29 | 3782 | 0 | 3782, 1596, -429.29 | -316.74 / -238.89 |
| NL **V2** T21 | -281.18 | 5080 | 0 | 5080, 1406, -281.18 | -188.18 / **-155.88** |
| NK TritonCTS (DIE-QC-35) | -571.84 | 3082 | 1556, -571.84 | 1526, 37, -129.31 | — / -181.77 |
| NK plan T11 (DIE-QC-36) | -1105.87 | 7766 | | | -1351.35 / -1319.11 |
| NK **V1** T21 | -404.41 | 7040 | 1556, -259.77 | 5484, 1987, -404.41 | -679.25 / -627.88 |
| NK **V2** T21 | **-289.88** | 6434 | 1556, -251.51 | 4878, 1938, -289.88 | -407.70 / **-172.35** |

Verdict: **FAIL (kept), neither variant beats TritonCTS** on the gate (NL ws and counts worse; NK ws better but 2x the
endpoints). V2 beats V1 on hold ws and setup on both tiles; NL V2 has more failing endpoints than NL V1 (5080 vs 3782). What T21 fixed: IO hold (NL 0 failing, NK -572 -> -252 = the kit frame 202.5 vs
realised insertion, a root/die-event item, not the tree) and setup (V2 TT setup better than TritonCTS on NL).
What it did not: internal register skew. Worst paths (`cts/*_hold_worst200.tsv`):
- V1: LSL macro output -> register (NL sl7 t_out -> t_out, -429) and `tap_q -> xl_q` across sibling TritonCTS domains:
  the 3..14-level TritonCTS imbalance, as estimated.
- V2 NL: `ot_fconst_*` -> `tie_lo/tie_hi` output ports (-281; reading UNCHECKED: root leaves early vs the 601.9 output frame) and
  sl5 `tx di -> u_tx/q` zero-logic pairs (-224) split across different leaves of the planned tx domain.
- V2 NK: register -> LSL macro input (`sl6 u_tx/q -> u_native_rawleaf/w_d`, -290): macro view insertion later than the
  register leaves (reading UNCHECKED: stage-count k = 7 vs a realised stage below 27.55 FF on short legs).

## 4. Next step (proposal; not built)
1. Measure per-stage realised delay on `cts_prehold.odb` (V2 copies kept) and re-derive k / T from the measured stage
   instead of the 27.55 FF model; the macro-vs-register residual is the NK -290 class.
2. Zero-logic pairs (tx di -> q, tap_q -> xl_q): `same_leaf_pairs` in the slice (core_infra already enforces it) so both
   ends share a leaf; leaf grouping by netlist pairs, not by pure geometry.
3. Leaf grouping that bounds leaf -> sink span (<= ~60 um) instead of pure equal-count bisection (304 um now).
4. NK IO class needs the root / die IO event (frame 202.5 vs ~450+ realised), outside this tree.
Until one variant beats TritonCTS, production A0 stays on TritonCTS with core_infra OFF.
