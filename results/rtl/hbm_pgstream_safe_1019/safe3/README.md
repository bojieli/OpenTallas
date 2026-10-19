# PGSTREAM SAFE3 (L2H-PGVM 10-19, branch claude/l2h-pgs3-1019)

Source `rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_pg_stream_safe3.sv`, top
`ot_hbm_su_static_pg_stream_split_safe3` (same ports as SAFE2 / b_1019). Fixes the SAFE2 native audit 78b77c1ff
(codex/pgsafe-native-1019, gate 121732 placed graph): 596 inputs first reaching logic (562 su_wq + 34 vmr_cmd),
42 outputs driven by logic (36 ij_row, 4 ij_v, ij_bad, lg_fault), 3 inject_q roots `g_ij[*].sq` with 42 loads.

| change | edge cost |
|---|---|
| su_wq / vmr_cmd captured at the face on clk_ctl (no reset; bridge regions are in reset >= 3 serial edges after the face) | +1 serial edge on the SU VM request path (LH-REPRICE3 input note) |
| ij_v / ij_row / ij_bad taken bit-wise from the owning inject_q region flop (the OR across kept regions was output logic) | 0 |
| inject_q region: flops only for its own bits M; registered one-hot select from the next slot (oh == onehot(ib(sq)) every edge) | 0 |
| stream-side inject bank bits taken bit-wise from the owning region (bit 40 = OR of the 4 registered group flags as SAFE2) | 0 |
| lg_fault published by an output flop on pg_clk (reset with tap-0 control) | +1 stream edge, sticky fault only |

Cause of the 42-load sq / 42 output logic: the regions are keep_hierarchy, so they could not see the parent's `& M`
masks and kept all 41 qr flops (and the parent OR could not see the zero bits).

## Evidence (fleet, ot-epyc7)
- `bench_s3/` (Verilator 5.050, tb_hbm_su_pg_stream_safe3 = SAFE2 bench with the reference su_wq/vmr_cmd through one
  clk_ctl register and lg_fault compared one stream edge later; gen_safe3_tb.py): rr18 / rr10 / qid0 PASS (checks 7194,
  windows 9228: request 4q/2q, return 2q/4q, inject 3q/7q as declared); m1 m2 m3 m6 m8 m12 m13 m14 FAIL.
- `map_c4751/` (yosys 0.68 TT native map, flattened all-driver BUF/INV-transparent census): 30,323 cells, 10,098 FF,
  4,351 um2, 0 roots > 32 (max 32); `boundary.json` (tools/hbm_static/pgstream_safe/boundary.py): 0 inputs reaching
  logic, 0 outputs from logic. The same checker on the SAFE2 r7 map reproduces the audit (596 / 42).
- Source c475a1871 == 3731b613e for RTL (3731b only fixes the bench history of lg_fault).
