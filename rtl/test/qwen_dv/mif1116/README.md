# Current native QC MIF calibration

The pinned capsule contains the current H/J SUVM, eight heads, native relays and SFUs. It compares MIF0/CROM3 with coupled MIF1/CROM3 and a mismatched MIF1/reply0 negative control. The test-only adapter drives landed `su_cmd`, bypassing command delivery and collective transport. Exact source hashes and boundary receipts are in `results/rtl/qc_mif_native_1116`.

Use `single`, `two_row`, or `silu_sigm` fixtures. `three_row_timing_only` preserves an oversized scalar-scoreboard experiment: its timing/counts are valid, but the third scalar row is not payload-qualified. Use `two_row` for bounded payload evidence. Outputs named scalar are streamed head values before the reducer, not completed partial sums. No absolute full-slice compiler profile is claimed by this bench alone.

Admit the runner with `ot-run`; provide a fresh scratch path. The same executable can replay any fixture by replacing `programme.hex` in a new runtime directory. The source capsule retains the exact behavioral memory models used by the native component, including collision assertions.
