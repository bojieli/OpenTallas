# coll_q2n2_split: NE hub NLINK2 collective body re-split (PATH-HBM/NE2, 2026-10-25)

Master: `ot_hfd_coll_q2_hard_v8g_s #(NLINK 2, TP 192, AR_ITER 1, ROWS 256, VM_RT 81)` with `-DOT_COLL_ISSUER256_NATIVE32`
(the NE `u_hb_coll_Q` body). The body splits into four hard cores, like the q3 split:

| core | module | ASAP7 cells (ORFS synth) |
|---|---|---|
| body_n2 (remainder) | `ot_hfd_coll_q2n2_body_core` | 231,533 (19 SRAM macros), synth_check 0 |
| vm (u_writer + u_vmasm) | `ot_hfd_coll_q2n2_vm_core` | 69,222 |
| ring | `ot_hfd_coll_q2_ring_ag_core` (reused) | as built |
| reduce | `ot_hfd_coll_q2_reduce_core` (reused) | as built |

Unsplit hierarchical synth: 581,881 cells, consistent with the sum of the pieces.

- `rest_n2.sh`: runs yosys remainder extraction (`rest_extract.sh`), then `rest_wrap.py` prunes the master input bits that nothing reads (`use/`).
  This leaves 5,241 inputs and 6,890 outputs.
- `ot_hfd_coll_q2n2_vm_core` is the q3 vm core with the tk_w write port folded. The q2 master drives tk_w with 0,
  so there are no tied pins at the parent. `clk_tkw` is driven from `writer_clk_meta`.
- `conn/`: `body_n2_conn.json` lists the partners of each wrapper bit in the master parent view.
  It covers 12,131 bits, none unpartnered. The plan step reads it.
- `ls/regclass_body_n2.txt` checks that every partition pin is registered. Cut ports not registered: 0.
  Five const bits per link are the off-die tx_pin_flit format bits, which are master ports.
- `ls/`: the lockstep of the split assembly against the unsplit master. It runs under Verilator 5.050 with 4 positive seeds
  and 5 single-bit mutants on the cut wires. The result is in `ls/lockstep_n2.log`.
