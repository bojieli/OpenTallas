# Hub status input stage — candidate, not adopted

The hub B2 GRT setup repair retains roughly 84 ps of debt at status pair_sum and reset recovery. The current u_status placement guide gathers status logic centrally, while bank_status arrives through face registers at the boundary. This form registers the complete input status frame inside u_status before its arithmetic; the existing guide also covers these new registers. Long face-to-centre reach and the pair_sum adder now occupy separate cycles.

The numeric input, hub flags, ring fault, and late ring fault all advance together. The sum-valid warmup guard gains one edge. Only vmstat gains one pin cycle; other hub data paths are unchanged. Relative to the active B2 form, the reset relay remains two boot edges and the status warmup gains one edge. Compiler/latency adoption is pending physical results and the die owner; no live plan has changed.

The test uses the exact released ak status module as reference, with only its module name changed. Both DMUT0 and DMUT2 compare the new module to that reference delayed exactly one cycle over 200 asynchronous reset episodes. Mutants bypass one bank input stage, bypass the late-fault stage, and shorten warmup. The source change requires fresh synthesis and canonical routed LEC before qualification.

Run from a matching own checkout through ot-run: bash results/hub_status_stage_1106/run.sh. Verilator must be available at ~/.local/opentallas-tools/bin. No P&R pass or closure is claimed by these functional checks.

Measured checks: 26,000, zero differences; data-stage mutant 10,399 differences, late-fault mutant 6,403 differences, early-warmup mutant 200 differences. Both ordinary and DMUT2 late-fault paths are compared.
