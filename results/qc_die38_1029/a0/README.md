# DIE-QC-38 / A0 (sub-agent of DIE-QC-38), 2026-10-29: per-stage clock delay of the kept T21-V2 trees, hold-class split, A/B estimate

COORD ruling: "A0: measured per-stage delay on kept V2 ODBs (intel2 dqc37-a0/v2), same_leaf_pairs, leaf groups <=60 um;
2 variants in parallel (12.17-3); core_infra opt-in stays OFF until one beats TritonCTS on both NL and NK."

**Outcome: NO BUILD. The estimate predicts neither variant beats TritonCTS on NL (both stay at -281.18), so per 12.x
estimate-before-build nothing was launched. core_infra opt-in stays OFF for A0.** The same per-stage mispricing causes
all three dominant classes, and A/B do not touch it. Diagnostics only: no pads, trims, ECOs, rule changes or new check kinds.

Inputs: the kept `intel2:/srv/opentallas-scratch2/claude/dqc37-a0/v2/{qfd_tile_nl_a0c_a0nl14icg2rr2,qfd_tile_nk_a0c_a0nk14icg2rr1}/diag/cts_prehold.odb`
(DIE-QC-37 V2, branch `claude/die-qc-37-a0-1029@c539563e1f4`) and its `diag/hold_fail.tsv`.
Probe: `ck_stage_dump.tcl` (docker `openroad/orfs:asap7lock` on intel2, 2 CPU, 12 GB cap, read-only kit mount). It loads the kit
NLDM + macro libs per corner, `3_place.sdc` (+ `vclk_ff.sdc` at FF, as the flow's FF hold scene does), and `setRC_rcx.tcl` + `estimate_parasitics -placement`
with propagated clocks. It walks the clock net from port `ck` and records every buffer/ICG input and output arrival and every sink pin arrival.
Data: `data/{nl,nk}_tree_{tt,ff}.tsv.gz`.

## 0. Reproduction (CHECKED)
Fresh FF hold WS on the ODB: **NL -281.18 / NK -289.88**. Both equal DIE-QC-37's `OT_HOLD_STRUCTURAL` (`data/probe_ws.txt`).
TT setup WS in the same session (placement RC, before repair, information only): NL -149.43 / NK -199.10.

## 1. Per-stage delay vs the plan model (CHECKED from the dump, `stage_an.py` -> `data/stage_summary.json`)
The plan (`gen_a0_tree21.py` STAGE) prices **every** stage at FF 27.549 / TT 36.154 ps (AOCV class B mean).
Measured stage = (child input arrival - parent input arrival), max-rise, split into cell + wire:

| class (FF) | n NL/NK | cell | wire | stage mean (min..max) NL | stage mean (min..max) NK | leg mean/max um | vs plan 27.55 |
|---|---|---|---|---|---|---|---|
| spread walk node `s` (fanout ~1.3, short legs) | 201/465 | 12.6 | 1.7-2.0 | **14.2** (10.5..39.7) | **14.6** (10.5..49.8) | 12-15 / 122-145 | **-13** |
| domain spread node `d` (below a hop ICG) | 462/449 | 19.0-19.7 | 14.4-17.2 | 33.4 (12.3..130.2) | 36.9 (14.0..166.9) | 58-62 / 190-200 | +6..+9 |
| hop ICG | 34/36 | 13.9 | 3.6-5.3 | 17.4 | 19.2 | 20-27 | -8..-10 |
| root register leaf `lr` (20/21 sinks) | 29/78 | 24-31 | 4.5-15.5 | 46.6 (21.4..70.0) | 28.6 | 45-88 / 158 | +1..+19 |
| domain register leaf `ld` (20/21 sinks) | 663/664 | 26.1-26.9 | 6.1-7.2 | 34.1 (19.2..88.4) | 32.3 | 51-55 / 193-199 | +5..+7 |
| macro chain repeater `m` (fanout 1, ~80 um legs) | 91/94 | 18.1 | 9.8-10.0 | 28.2 | 27.9 | 80-82 / 91-95 | ~0 |
| leaf -> register pin wire | 14330/15360 | | 2.5-3.0 mean, max 142-153 | | | 10-11 / **288-304** | |

TT has the same pattern (walk node 18.3-18.7 vs plan 36.15; `d` 39.7-43.5; leaves 36-56).
Fitted FF models (pooled NL+NK, rms 4-5 ps/stage): node cell = 14.22 + 0.015·Lsum + 0.62·fanout; leaf cell = 31.49 + 0.0035·Lsum - 0.28·nsink;
node wire = -3.49 + 0.092·leg + 0.059·Lsum; sink wire = -1.28 + 0.282·leg (ps, um).

**Mispriced stages:** the planner uses one constant, but realised stages are bimodal. The fanout-1 walk nodes that fill the
equal-count levels above the gates cost 14 ps at FF, about half the model. Domain-spread and leaf stages on 50-200 um legs
cost 33-47 ps, up to 130-167 ps. Macro chain stages cost 28 ps, which matches the model; the register stages are what is mispriced. Consequences (CHECKED):
- Register insertion is realised at **FF median 358.3 (NL) / 346.7 (NK)**, i.e. 16.3 / 15.8 ps per stage over 22 cells.
  The plan put it at 21 x 27.55 = 579 (TT 453.3 / 438.1 vs 759 planned). Spread is min..max 274..540 NL and 281..531 NK at FF, sd 40 / 49.
- Early vs late registers differ by path mix, not by depth (all registers sit at depth 22). The earliest 5 % carry about 15.7 `s` and 2.5 `d` nodes
  (NL, 301 FF); the latest 5 % carry 11.8 `s` and 6.2 `d` (460 FF).
- Domain medians (`data/domain_ff.tsv`) spread **313..442 FF NL (129 ps), 288..455 NK (167 ps)**. Domains whose gate sits shallow
  (depth 14-15, more `d` levels) are late (tx2 442, tx5 393, fa2/fa3 389-455). Domains whose gate sits deep (17) are early (tx3 313, de 316).
- Macro taps (`data/macro_tap.tsv`): each macro clock pin is measured against the hold-neutral tap (register median - macro FF max insertion,
  LSL 210.6, romleaf 243.3). **LSL pins are late by 86..230 ps (NL) and 86..316 ps (NK).** Example: NK sl6, chain r 9, pin 452.5 FF vs ideal 136.1.
  Cause: the macro k = 7 stages is priced at 27.55 per stage, but the register stages it must match realise 16 ps each, so k should be about 12.
  On top of that, chain stages cost 28 ps against 16 ps register-equivalents, i.e. about 0.165 ps/um of corridor in excess. Several gates
  already arrive later than the ideal pin (NK sl3 gate 248.7 vs 136.1), so the T21 structure cannot place these taps at all.

## 2. FF hold classes of the V2 failures (CHECKED: `hold_class.py`, leaf/driver from the dump + `zl_pairs.tcl` netlist walk)
Zero-logic = the capture D pin is driven by the launch register through BUF/INV only.

| tile | class | fail eps | worst | < -100 |
|---|---|---|---|---|
| NL | reg -> output port (`t_out` 514, `tie_lo/hi`), launch 314..406 FF vs frame 601.9 | 516 | **-281.18** | 516 |
| NL | reg -> LSL/romleaf macro | 2762 | -177.15 | 872 |
| NL | zero-logic, different leaf: **cross-domain** 696 / same domain 594 | 1290 | -224.63 (cross) / -94.27 (same) | 16 |
| NL | logic, different leaf | 509 | -105.15 | 2 |
| NL | reg -> async RESETN | 3 | -19.28 | 0 |
| NK | reg -> LSL/romleaf/node macro | 3519 | **-289.88** | 1916 |
| NK | input port -> * (frame 202.5) | 1556 | -251.51 | 1554 |
| NK | logic, different leaf | 238 | -172.09 | 5 |
| NK | zero-logic, different leaf: cross-domain 704 / same domain 407 | 1111 | -125.24 / -115.94 | 17 |
| NK | reg -> async | 10 | -42.83 | 0 |

**No failing pair shares a leaf** (same_leaf class = 0 on both tiles). Leaf distance of the failing reg-reg pairs: median 17-22 um
between leaves, registers 9 um apart. The worst zero-logic pairs, e.g. NL sl5 `tx di[219]` (dw domain, 359 FF) -> `u_tx/q[219]` (tx5 domain, 564 FF),
cross two different hop ICGs, so no leaf grouping can put them on one leaf.

## 3. Estimate (analytic on the measured pairs, `estimate_ab.py` -> `data/estimate_ab.json`; UNCHECKED predictions)
- **A same_leaf_pairs.** Each zero-logic diff-leaf pair gets the capture clock = its launch clock (optimistic: perfect co-location).
  Result: NL zero-logic class -224.63 -> -27.81 (fails 1290 -> 659), but **WNS stays NL -281.18 / NK -289.88**. Fails go 5078 -> 4447 (NL) and 6433 -> 5880 (NK).
  In practice it is weaker. The generator implementation (`gen_a0_tree38.py --pairs`, count-preserving swaps, 60 um reach, equal counts kept for the
  core_infra check) co-leafs 2696 of 4641 in-domain pairs on NL T30. Only **303 of 1293** failing zero-logic pairs land on one leaf, because the
  worst ones are cross-domain (`plan/nl_t30_report.json`, plan only).
- **B leaf span <= 60 um.** Every register sink leg is capped at 60 um with the measured sink-wire fit. Result: NL zero-logic -224.63 -> -190.46,
  NK logic -172.09 -> -125.28, **WNS unchanged at NL -281.18 / NK -289.88**. B also needs unequal leaf counts, and core_infra refuses those without
  `load_balance: joint_nldm_plan`.
- **C (checked whether it should replace A/B): measured stage price for k (FF 16.0 / TT 20.25 -> k LSL 12-13, romleaf 13-14) + T raised to 30-33.**
  NL output class -281 -> about -150 / -107 and LSL taps relatively about 70 ps earlier (sl4 -177 -> about -105). NK input-port class -252 -> about -382 / -426
  (still above -571.84). But the cross-domain zero-logic class (-224.63, domain-median skew 129 ps) is untouched: raising T adds the same walk levels above every gate.
  **NL is predicted at about -224 (FAIL vs -172.53).**

| variant | NL FF hold WNS (pred.) | NK FF hold WNS (pred.) | vs TritonCTS NL -172.53 / NK -571.84 |
|---|---|---|---|
| V2 measured (CHECKED) | -281.18 | -289.88 | NL FAIL / NK PASS |
| A same_leaf_pairs | -281.18 | -289.88 | NL FAIL / NK PASS |
| B leaf span <= 60 um | -281.18 | -289.88 | NL FAIL / NK PASS |
| C measured k + T30..33 (+A) | about -224 (cross-domain zero-logic) | about -382..-426 | NL FAIL / NK PASS |

Estimate FAILS for every variant, so **nothing was built** (4.: no runs launched, no live jobs).

## 4. What would fix it (proposal for COORD; not built)
All three dominant classes share one root cause: the plan stage has no fixed delay.
NL frame vs insertion, LSL taps late by 86-316 ps, and the 129-167 ps domain-median skew all follow from walk nodes at 14 ps vs domain/leaf
stages at 33-47 ps under an equal stage count.
Within the count-aligned rule (12.16 "standard depth"), the next generator must make **every stage a standard stage**:
fixed fanout (e.g. 2) and a leg window (e.g. 40-60 um) on every level. Walk nodes then move a full standard leg, not (centroid - parent) / remaining levels;
domain spreads no longer take 190 um legs; macro chains use the same leg. The early-tap k is priced with the measured standard stage.
Model check from the fits: a fanout-2, 50 um stage costs about 24 FF ± 3 ps from leg variation, vs today's 14..47 mix. Path sigma over 22 stages is about 14 ps, vs today's
domain skew of 129-167 ps. The alternative, delay-priced balancing without equal counts (as TritonCTS does), changes the core_infra equal-stage invariant
and is an owner / COORD call. The NK input-port class is the kit frame (202.5 vs realised ~347 FF), a die IO item outside the tree.
Until then production A0 stays on TritonCTS with core_infra OFF.

## Files
- `ck_stage_dump.tcl`, `run_dump.sh`: per-stage/sink clock dump + hold-endpoint driver walk (docker on intel2, memory-capped).
- `zl_pairs.tcl`, `run_pairs.sh`: all zero-logic register pairs (netlist walk). `data/{nl,nk}_zl_pairs.tsv.gz` (NL 6003, NK 6519).
- `stage_an.py`, `hold_class.py`, `estimate_ab.py`, `macro_tap.py`, `domain_arr.py`: analyses (`python3 -I <script> <datadir>`).
- `gen_a0_tree38.py`: gen_a0_tree21 + `--stage-ff/--stage-tt` (measured early-tap stage) + `--pairs` (same-leaf swaps). **Plan-only**, not built;
  `plan/{nl,nk}_t30_report.json` are its T30 dry runs. They show the same-leaf coverage and k 13 for LSL at the FF 16.0 price
  (the k TT/FF agreement in core_infra was not exercised).
- `data/`: dumps (tt/ff), holdpairs, stage_summary.json, hold_class.json, estimate_ab.json, macro_tap.tsv, domain_ff.tsv, probe_ws.txt.
Probe scratch: `intel2:/srv/opentallas-scratch2/claude/dqc38-a0/` (dumps, logs, T30 slices). No ODBs were written.
