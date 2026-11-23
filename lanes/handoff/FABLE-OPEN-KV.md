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

## fork hroot (11-23, stood down 10:5x PST on COORD order; rows held by Codex K3 compose f75a71af72eb / gate k3c)
- x15 (slg o_ctl dch[2] y[16] -76.46): ADOPTED KV-D29 B-HROOT GEOM block (3) (slg band 320 -> 152 um). Cause from placed DB kv3_hroot_1123035126: bit 144 storage/y at band E end x1245, its g_srep.sr[2] select flops packed at band W corner x944 (cland_ffkey: select key bit 148 >= bus width 145 keeps raw-name key), mux at x1011 -> 468 um round trip in the half cycle. Class fix (FLOW-OPS-R3, not D29): clamp g_srep/u_wen keys to nbits-1.
- h1/h2/h3: ROWS_FABLE-OPEN-KV-HROOT-RINGFORM.py sha12 97083c85fd86 (epyc8 kv-plan-r6/d29/rows_in/B + intel1 fable-open-kv/hroot): budgets.cland_strip_rows_types.kv3_hroot=5 (pinslot-dense body-to-body packing = cause of E wall + ft2_i blob), o_next band 642 -> 300 um.
- Gated stack B4 plan 468788f372eb (intel1 fam-kv-hroot-r1/fork_d29g = R1+BAND+RING+RES+EFS+GEOM+RINGFORM+tapoff fill): PRE 0, G0 0, strict bind 0 errors, LATCHECK 2434/2434, BPC 0 (d29geom g0gate_r3, bindgate_r4). Probe: Codex place kit d29geom/b4_place (unit oth-ubuntu-3847728-1795457470), not mine.
- Nothing launched after 10:45. My superseded fork_rf/launch_rf being removed via ot-delete on intel1.
## parent state 10:55 PST (after the 06:4x-10:40 limit; COORD: review K3 rows, build no parallel rows)
- K3 compose f75a71af72eb (Codex/KV-D29) holds rc118 PCGUT 823a4142c484 (mine) + PCSLIT 32447daeb2e6 (pcf cores out 25.92, slits 34.56, gutter 35), rc119 PCONEXT/PCTAPEGRESS, rc121 PCST + PCKEEP (IOPC arm B, keep_types tool), x15 hroot rows. Gate = k3c.
- Probes: epyc9 fable-open-kv/p1 (kit A 4_cts + permanent slit blockage + DPL): 5-it GRT 11,671 -> 3,284, kvpc*_f interiors 6,813 -> 110. p2 (4.32 ring on 8 cores): 3,220. Residual = four inner pcc faces (seam).
- Real kit epyc8 KV-D28/private/FABLE-OPEN-KV/kv3_pc_v3_1123063652 (D28 + OT_GUTTER_BLOCK_UM=12, goal geom, place done 08:47, AUTO-GEOM grt NA = 600 s wall): gutter is GPL-ONLY (released before DPL); slits still hold 865/1316/1194/48 cells at 3_place. 5-it GRT of that 3_place: epyc8 fable-open-kv/g3 (running 10:5x).
- REVIEW-GAPS posted 10:54 to KV-D29: G1 gutter released before DPL (needs keep+carve flow key or k3c probe proof), G2 seam not covered by K3 (row PCGROW or REASONED on k3c full-iteration GRT), G3 no pc__po_d3 station.
- Next: read g3; read the k3c pc_v3 probe when KV-D29 names it; post GATED/REASONED per item to PRECHECK-LEDGER-R3; REPORT to COORD.
- ROWS_FABLE-OPEN-KV-PCSLIT.py (halo_um form, epyc8 fable-open-kv/rows) is NOT delivered: refuses on 55 bit sites per pc_v1 clone inside the ring.
- 11:15 g3 read: GPL-only gutter kit 3_place 5-it GRT 16,161 (kvpc1_f 2,748, kvpc3_f 2,134, kvpc0_f 952 interior): gutter as run today does not fix rc118. RESULT+STATUS posted 11:15 with per-item ledger status; rc118 stays OPEN pending a keep-through-DPL flow key + pc_v3 probe. Nothing of mine is running.
