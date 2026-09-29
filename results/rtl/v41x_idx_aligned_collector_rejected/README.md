# Rejected aligned-beat quarter collector (historical)

Codex commits 5b6e7042, 69e61bbf, 268e7e59, 5481bc49 and d0e6e8e7 (branch
`codex/v41-quarter-collector-aligned-fast`) tried bypassing aligned quarter
beats into the vacated output register. The full exact four-stack Verilator
gate passed but took 9,516 cycles against 9,278 for the adopted two-cycle
collector (2.57% slower), so root rejected it (TASKS.md).

The records beside the production ones
(`hdc_v41x_idx_four_stack_aligned_short.json`,
`hdc_v41x_idx_four_stack_aligned_q64_short.json`,
`hdc_v41x_idx_four_stack_verilator_collector_aligned.json`) are historical:
their source pins name the variant RTL, which is NOT applied to production.
`aligned_collector_variant.patch` reproduces the variant against the Codex
branch base for replay.
