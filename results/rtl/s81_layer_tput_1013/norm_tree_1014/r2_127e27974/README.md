# S81 HC NORM tree r2 (source 127e27974, branch claude/s81-norm-tree-1014) -- measured 2026-10-14

Structural changes vs the r1 tree (4e4a241f1):
- bottom collector `ot_s81_hc_cnclt` (19,155 / 16,082 sinks, TT R 407 / 365 ps: clock rule REFUSE) split by bank half into
  `ot_s81_hc_cncla` (banks 0/1 + rvt/pi + fault) and `ot_s81_hc_cnclb` (banks 2/3), own clock roots; every chain-owned
  tree node lies in one bank, so the two halves run the golden tree's own nodes (same qadd, same pairing, same NT_K);
  decoded leaf write, per-octet one-hot read select.
- scale-lane relay moved from `ctrn_nt` into `ctfs_nt`: the CLOSED `ot_s81_hc_ctrn` is reused unchanged; `ctfx_nt` 12.96 -> 25.92 tall
  (DPL-0033 at 12.96).

| check (hc_gate NG 256 hier3 DPI, g4.sh, ot-epyc4) | result |
|---|---|
| probe exact (all variant tiles at kit tuples) | PASS 0/1940 x3 (golden_L0_L2, stress_0, stress_1), 5,540 cycles |
| loop bench exact / m3 | PASS / FAIL |
| NT_K 66 | FAIL (fault) |
| tile mutants cncla / cnclb / ctfs_nt / ctfx_nt | all FAIL |
| NORM trace (norm_trace.json, 4 jobs identical) | 514 = accept->sum 225 + sum->rsqrt 72 + rsqrt->first row 141 + rows 39 + writer 22 + done 15 (serial: 727) |

Production layer (tb_s81_die_layer NG 256 HCH 1 nom --coef-split --h-stream, g2c.sh): base L0 8,660 / L2 17,566; NTREE L0 8,228 / L2 17,146,
both bit-exact; mut_hc FAIL.  -216 / -210 a NORM -> layer-local NORM 713 -> 497 (1.507x of 329.9).
Ledger (tools/throughput/accepted_cost.py compute s81 --match 'hc_pre$', same method for both): node delta 383.1 -> 167.1,
AR 3.609 -> 1.607 % (MTP 3.059 -> 1.358 %): about -2.0 pp vs the accepted 3.566 % row.  NOT written to the ledger: the swap is posted
only when every variant tile closes (owner 10-14).

CTS pre-route gates (kit gate_result.json): cncla0/1/2 9,819 / 8,273 / 9,819 sinks R 245.4 / 220.2 / 241.9 spread 16.1 / 25.3 / 12.7;
cnclb0/1/2 9,811 / 8,265 / 9,811 R 246.5 / 227.2 / 245.0 spread 15.3 / 27.4 / 16.0; ctfx_nt 1,718 R 339.0 / 76.0; ctfs_nt 6,163 R 328.7 / 30.4;
cnrsq 8,575 R 212.9 / 22.6.  All PASS/WARN (util only).
