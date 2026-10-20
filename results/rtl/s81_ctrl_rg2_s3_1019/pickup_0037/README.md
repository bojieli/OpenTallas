# CTRL/COLL pickup 2026-10-20 00:37 PT

No candidate qualifies for submit under the binding native <=32 rule.

Mapped-native fanout census uses unmodified textbook_lint parse/build/clock/fanout functions, with all clock nets excluded and BUF/INV collapsed. CTRL actual mapped gate K8 netlist; COLL safe4 synthesis 1_2_yosys.v. JSON includes SHA256. Macro directions use textbook inference (not independently LEF verified); physical reach, tie audit, all pin registration and storage scope remain unqualified. These failures suffice to block adoption.

- CTRL23 nonclock roots >32: reset u_hrs159 and u_srs116; kept per32-bit load-enable combinational roots64. Structural successor must reduce group width (12 bits -> expected24 mapped enable loads) and distribute reset with native-verified kept <=32 leaves. Clock split must cover both clk/ckh, since current km hook covers clk only.
- COLL8 nonclock roots >32: local reset45; nxt/una sequence bits33..38 and OR3 decode37. Must replicate sequence/decode consumers and bound reset before new layout gate. Existing runners preserved.
- CTRL K2 boundary TT/FF spread core120.2/105.9, HBM99.7/92.8 FAIL. K8 core18.9/14.9 PASS, HBM99.8/92.9 FAIL. Source per-clock GATE_CK_DOMAIN in pve1 ref_gate/s81ctrl_rg2_s3k{2,8}-20261019-225611/execution.log. No largest-root waiver.
- COLL W_s4 and E_s4b terminal FAIL GPL-0305 placement divergence. E_s4 and W_s4b still live at00:34. Archived JSON/PNG do not claim completed CTS/GRT. ROOT lattice/channel fill approval remains pending.
- Correct PACK terminal TB_DSFD_CTRL FAIL5910, witness2/rg2_mut_pack.log. Nominal PASS already committed. Original RD/KRDY still running at00:34, unmodified watchdog20k. Reused exact/RD/KRDY binaries in separate runs/codex_watch512 with explicit +stall=512 (> nominal measured max143.25), fleet session23529. No rebuild/new RTL and no overwritten failure logs.

SAFE checklist: pins existing implementation claimed registered (independent native audit owed); reach not measured; fanout FAIL; depth CTRL375ps/COLL659ps estimate (COLL FAIL); storage existing SRAM; floorplan COLL failed placement; clocks FAIL HBM; schedule unchanged. No new gate, submit or REVIEW.json.

Failed COLL W_s4/E_s4b floorplan PNGs personally inspected:55 macros in separated strips; center horizontal band clear of macros, pins on both full vertical faces, ck at center height. Portrait540x712.8 and landscape706.32x540, total fill18.6/18.8%. Static full-height row guides do not prove placed cell-band density; placement failed before density/congestion output. No acceptance.

## Native32 successor (opt-in, unfinished)

Source `S81CTRL_NATIVE32` uses G12 instead of G32 and kept reset leafbanks with asynchronous assertion. Native mapped synthesis has2956 FF vs2740 (+216/tile,16 tiles ->3456), same4 SRAMs; max nonclock loads31 and0 roots>32, including reset through BUF/INV. Confirmed production SRAM directions and output constants audited in next census artifact. Actual reach/pin audit remains owed. Macro capacity, interface bits, throughput and steady data edge count unchanged. Reset release adds1 PCR +1 FIFO local edge; initialization/live contract must pass32PC nominal/warm-reset bench before adoption. `native32_model.json` records this candidate budget.

A second K8 clock hook for ckh is prepared with distinct names. It has not run; no physical claim. No layout gate until census/checklist/region-reach proof complete. Four production nominal/RD/KRDY/PACK benches active on ep5 under codex-s81-native32-bench-1020, sessions55030/42579/8753/52043. Mutant runs use explicit +stall512; nominal uses20000.
