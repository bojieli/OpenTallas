# HBM-NEXT-ATT4 step 4: landed decode inputs of the shared PV merge (2026-10-19)

## Why
The step-3 `hnx_rp4a4_spvm` --cts gate (250.56 um, ot-epyc7 `ref_gate/hnx_rp4a4_spvm-20261019-020708`) ended CTS setup
repair at SS **-167 ps** @770 (TNS -69.9k, 569 endpoints; detailed place -198 / -87.5k), worst endpoints
`u_sm.g_madd[*].ka_hw/kb_hw` (the decode stage). The worst path did NOT run through the 8:1 descriptor residue mux: it
started at the wrapper's N-face pin register `ev_q` (`ot_hnx_att4_spvm`), crossed the tile in ~250 ps of buffered wire,
then ev -> d_md -> cand -> sel priority -> one-hot compare -> ka_hw (~500 ps of logic). The decode read the pin registers
directly.

## RTL change (`rtl/hbm_next/att/ot_hnx_att4_smerge.sv`)
- Every merge input passes one more register: stage 1 = LANDING (`ev_q`, `tag_q`, `sum_l`, `ps_l/pl_l/pslot_l`), stage 2
  = the step-3 input register (`sum_q`, `ps_q`, ...). The decode reads only `ev_q` / `tag_q`, whose D is the pin register
  across the outline (a wire-only cycle), so the placer lands them beside the decode.
- Uniform delay of all inputs = pure retiming: it only rotates which residue a slot owns (like the pin registers). Nodes,
  tags and faults are bit-identical; `pv_*` / `pub_*` one more edge later (pin -> head turn +3 edges in the tile; the
  compiler counts it). Cost: +2,048 + 64 + ~10 flops (~+3% of 67k).
- Descriptor shift rings (the other planned fix) NOT done: the 8:1 residue mux was not on the worst path.

## Benches (Verilator 5.050, fleet ot-epyc4, `tools/hbm_next/att4_a1_matrix.sh`; `bench/`, witnesses `witness/`)
| run | step 4 | PV span max (step 4 / step 3) |
|---|---|---:|
| sh_s00 / s03 / s10 / sdj | PASS 200 / 200 / 40 / 200 | 387/386, 531/530, 747/746, 1,091/1,090 |
| sh_k500 / k490 / k486 (flush paths) | PASS | 539/538, 539/538, 387/386 |
| sh_smut1 / 2 / 3, sh_smut4k | FAIL (witnessed) | |
| sh_smut4 (top-k 512) | PASS (unexercised, as steps 2-3; smut4k covers it) | |
| pub_m0 (768 nodes) / pub_s2 (1,152) | PASS, 0 mismatches | |
| pub_m1 / m2 / m3 / m4 / m5 | FAIL 421 / 768 / 636 / 125 / 768 nodes (witnessed) | |

Kit spec fail witnesses now point at `s4/witness/` (sh_smut1, pub_m5).

## Gate
Regate `pre_route_gate.py physical/ref_tile/hnx_rp4a4_spvm --remote auto --cts --mem 32` (pending_results, HBM-NEXT-ATT4).
If it still misses on the decode stage: descriptor shift rings (entry ph+1 at stage 1, drops the 8:1 residue mux).
