# Native HBM SU producer recovery

DS L0 record 23 (`attend.bf16_p`, 128 FP32 words) first fails its original VM commit at serial edge2727. The unchanged-input diagnostic confirms sector/input row33 is nonzero both at edge1 and edge2670; output row35 remains zero at3300. Contrary to an initial coordinator summary, the raw programme probes show **busy=valid=1 at2680–2710**, with fault0. The producer ran.

The first programme contains44 command lines and56 configuration writes. `lower_columns` historically allocated one index SRAM bank from those44 lines, so its dictionary begins at localbank1. The actual instantiated `ot_hbm_su_programme_pgcol_m55` has `EDGES=7111`, requiring four index banks, and reads its dictionary at localbank4. The configuration therefore populated unused index storage, leaving the actual dictionary zero. This is an image/physical-capacity ABI error.

`lower_columns(..., resident_edges=7111)` now preserves the hardware's bank numbering while retaining the existing short-programme default. `layer_images.column_image` supplies the actual capacity. No RTL or macro count changes. Native pslice_c5 also presents line0 to a consumer nine edges after start; the old five-edge reference assumption is wrong. The vehicle compiler now uses9. A correctly scheduled source issues start/config four edges earlier; this consumes four more idle preload edges rather than moving numerical acceptance.

Verilator5.050 native component, job `oth-ubuntu-2212937-1792425920` on auto-selected epyc8:

- Compiler-generated configuration exactly matches the native corrected-bank image; legacy default remains byte-identical and an undersized capacity is refused.
- All44 native command words, indices and fault state PASS; consumer startup=9.
- Original bank numbering fails at command0, returning allzero despite valid.
- Original startup=5 assertion fails with measured9.

The captured flattened production master, source hashes, original/fixed configuration, expected command words, testbench, compiler check and raw positive/mutant logs are in `producer/`. The unchanged-input/late-output diagnostic is in `vm_path/`.

A first-record integration replay uses the preserved production slice binary. It changes only the first programme's dictionary bank IDs and advances its source configuration/start/length events four serial edges. Every numerical check, preload word and other drive is unchanged. Its outcome must be collected before a numerical recovery claim. Later programmes, actual release source binding, per-column physical dictionary capacities, full layers, token/head and SU/MU qualification remain open.
