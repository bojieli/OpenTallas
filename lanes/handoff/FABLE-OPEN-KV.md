# FABLE-OPEN-KV handoff (Fable 5.2, started 11-23 05:56 PST). OPEN KV ledger items rc118, rc119, rc121, x10, x15 (+ hroot h1-h3 per COORD 06:3x).
Deadlines PST: rows (sha+PRE) into epyc8 kv-plan-r6/d29/rows_in/ by 11:00 (KV-D29 composes), REASONED to FABLE-RC-ALL by 12:30, gate 13:00.
Split: parent = rc118 + rc121 (pc rows); fork hroot = x15 + h1/h2/h3; fork taps = rc119 + x10. Local work: rtx-pro scratchpad fok_*.py.
## rc118 cause (own read, kit A epyc9 .../KV-D28/private/FAM-KV-IOPC-R4/kv3_pc_v3_1122200331 4_cts, reviewer cong.rpt)
- 99% of 11,671 = H overflow at capacity 0 inside macro footprints (kvpc3_f 3891, kvpc1_f 2922, kvpc1 1622, kvpc3 985, kvpc2 751).
- 8.64 um pcc|pcf slits are placeable dead-end pockets: slit3 1872 cells, slit1 1611 (clean slits 63 / 799). Bus centroid lies on the macro pair
  (kvpc3 po pins N face y1274 vs po_d3 die pins W y878-927; o_dn/hsl S pins x956-1015 under kvpc1_f).
- Row PCGUT: budgets.gutter_block_um 12 + gutter_block_types (6 pc types). Seam capacity (COORD): measuring; PCGROW (IOPC, +112.32) or W-pair shift.
## log
- 06:00 TAKING; 06:35 ACK+CAUSE post; forks spawned 06:40.

## fork taps (Opus 5.5, stood down 11-23 ~11:00 PST per COORD; K3 f75a71af72eb holds PCONEXT)
- Work dir epyc8 /srv/opentallas-scratch2/claude/fable-open-kv/taps: dumps/kv3_pc_v3.reg (kit A 4_cts placed regs), split3.sh (tap_split, placed sinks), pre.sh, row/ROWS_FABLE-OPEN-KV-PCTAPS.py eae0e44c976c (unused, superseded), row/ROWS_FABLE-OPEN-KV-PCONEXT.py 9c58e1d1c17c (in K3), tmp/rows_k3c1500.json (+33 taps that would bring K3 pc_v3 max load 2321 -> 1496 at cap 1500, advisory).
- x10: chain9 TAPOFF census 56/56 ok on k1, and K3 reports 56/56. Nothing is running.
