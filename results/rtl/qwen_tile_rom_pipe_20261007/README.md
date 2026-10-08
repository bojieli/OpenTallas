# Qwen tile ROM read pipeline: exactness gate (qwen-blocks, 2026-10-07)

tools/rtl_qwen_me_partition_gate_w12.py at the committed gate shape (GT 16, W 4, SMIN 3, SMAX 4, TCUT 3, BD 2, NWS 1,
ORD 1, TWS 2, MEM_EXTRA 1, ACC_LAT 7, TREE_LAT 7, MUL_LAT 8, FAST_ISSUE 1, KV_PREP 4) with ROM_PIPE 1 / LRST 1:
the array's tiles (ot_qwen_rom_tile_logic_w12) against the original ot_hdc_matvec (0e8df511), 300 random ops, result
writes / maxima / argmax / scale reads as event sequences, first result exactly XD later.

| file | params | verdict |
|---|---|---|
| gate_a1.json | ROM_ARELAY 1 | PASS (latency +10 = XD) |
| gate_a2.json | ROM_ARELAY 2 | PASS (+11) |
| gate_h.json | ROM_ARELAY 2, BAW 11 | PASS |
| gate_e10.json | ROM_ARELAY 2, BAW 10 | PASS |
| gate_m11.json / gate_m10.json | ROM_MUT 1 (capture bank select one edge early), BAW 11 / 10 | FAIL (event 262) -- required |
| gate_m.json | ROM_MUT 1 at BAW 12 | passes: the bench's addresses rarely cross a 4,096-word bank, so the select mutant needs BAW <= 11 |

Every run's built-in negative control (tile ROM slices swapped) FAILs as required.
