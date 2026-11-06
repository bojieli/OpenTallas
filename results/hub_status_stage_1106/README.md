# Optional hub status input stage — default off

STATUS_INPUT_STAGE is appended after DMUT, preserving existing positional calls. Default0 selects the original direct input frame and two-bit sum-valid guard: no data latency or warmup change. Enabled1 selects the exact d818 registered-frame mechanism and three-bit guard: vmstat gains one pin cycle and actual status warmup gains one edge. All numeric and flag inputs, including the late-fault path, advance together. The input registers remain unreset only in enabled mode; the guard masks warmup exactly as in d818.

Source-only adoption does not enable any consumer, change a recipe/plan, or price latency. Enabling a consumer still requires physical pass and parent latency/compiler adoption. The current private vC2 physical pilot remains pinned to unconditional candidate d818, unchanged. Its existing external reset relay2 is specific to that physical form, not added by this source option.

Existing d818 enabled proof is retained: 26,000 checks, zero differences against the released status module delayed exactly one cycle, both DMUT0/2,200 asynchronous reset episodes. Data-stage/late-flag/early-warmup mutants caught10,399/6,403/200 differences. No broad rerun was performed for the option wrapper. Minimal relation check compares default0 directly to the released reference and enabled1 directly to the exact d818 snapshot (both DMUT0/2), checking two-bit/three-bit guard widths:272 checks,0 differences. See default_result.log and run_default.sh.

The enabled physical intent is unchanged: register the complete status frame inside the existing central u_status guide before arithmetic, separating long face-to-centre reach from the pair_sum adder. Other hub data paths do not change. No physical closure or routed-equivalence claim is made by these component checks.

Run functional evidence through ot-run: run_default.sh is the small branch-relation check; run.sh retains the original enabled+1 miter/mutants and now selects STATUS_INPUT_STAGE=1 explicitly. Both use Verilator at ~/.local/opentallas-tools/bin.
