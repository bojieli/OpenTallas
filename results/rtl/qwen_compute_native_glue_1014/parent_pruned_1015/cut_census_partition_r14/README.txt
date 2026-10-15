Q-COMPUTE-ELEM r14 2026-10-15: partition screen of the NK banked parent residual logic (input = Codex read-only
snapshot85 ODB dump, commit 9c2614c65 cut_census/{connections,instances}.tsv.gz, 3_2_place_iop.odb sha e3082225...).
Union-find over std cells joined by signal nets, excluding clock nets and nets with fanout > T (broadcast controls).
T=64: one giant component 8,139 cells / 952 FF / 33 hard / 3,040 hard pins + 5,089 single-gate per-bit components.
T=8 (control broadcasts cut): control core 5,942 cells / 886 FF / 26 hard / only 340 hard pins (face_tap 139, strap 16,
5 rpair x 14, 8 lsl x 9); datapath = 1,024 mq_wrom->s2_word per-bit comps (2 hard), 2,048 3-hard and 1,024 4-hard
per-bit gates (ROM return OR into rqr), 4 x ~165-cell TX x-path comps (s2_x_full + 8 tx_r0_lo).
=> S1 partition: one compact control leaf (886 FF local root) + per-bit glue folded into consumer bank/relay leaves
(selects from the control leaf) + TX x-path into the RNE TX stages. No residual parent std-cell root remains.
Screen only: no RTL partition, timing or area claim yet.
