# DS-ROM 1M: field nodes on the element the S81 die contains (2026-10-05)

The 1M composition's ROM-field nodes (`results/rtl/dsrom_1m_allmeasured_20261004/field.json`) were measured with the
pinned W10 element `ot_v41_rom_elem_w10` (segtree2, bterm2) on every pair.  The S81 die's FP8/FP4 pairs are the DS
q-element (`ot_v41_rom_elem_q_qp_w10` routed; closure successor `ot_v41_rom_elem_q_qx_w10`).  Differences:
`element_difference.json`.

Vehicle option (default off): `ot_v41_fieldtop_w17w10` / `ot_v41_field_w17w10` / `ot_v41_pair_w17w10` parameter
`QELEM` (+ `QXV`), `tools/dsrom_1m_field.py build --qelem N`.  QELEM=1 puts the q-element at its routed parameters
(NB 2, MTP 1, EARLY 1, FAST 1, PP 1, QTIMING_FIX 1, QPIPE 1, QP_XS 1, QP_CAP 0, QP_P1 1, QP_CSAM 10, QZ 1, QZ_NS 8,
QZ_NE 4, QY 1, QX N) on the non-BF16 pairs; BF16 pairs keep the W10 element.  The spine is unchanged: it waits for
every row (rows_left) before the next configuration, which is the contract the q-element's delayed output tables need.

Measurement: same S81 plan (167 phases x regions, 20,160 region runs per variant, ot-epyc1tb), every row bit-exact
vs the golden (249,920 rows, ISA cross-check 34,880 rows, 0 mismatches) for base, QX 9 and QX 8.  Base re-measured on
current main RTL reproduces the committed field.json on all 59 nodes.

| | AR us | AR tok/s | MTP tok/s (tau 4.159) |
|---|---|---|---|
| base (W10, as composed on main) | 577.175 | 1,732.6 | 5,053.3 |
| q-element QX 8 | 577.915 | 1,730.4 (-0.13%) | 5,047.9 (-0.11%) |
| q-element QX 9 | 579.572 | 1,725.4 (-0.42%) | 5,036.0 (-0.34%) |

43 of 59 field nodes change (+2..+12 cycles QX 8, +3..+42 cycles QX 9); 16 BF16-only nodes (wo_a, router,
cmp.wk) are unchanged.  168 of the 248 critical-path nodes that take their time from field.json are affected
(`affected_nodes.json`).  Per-node cycles: `composition_delta.json`.  Main's headline is not changed; the q-element
is not yet closed.  Tool: `tools/dsrom_field_qelem_delta.py`.
