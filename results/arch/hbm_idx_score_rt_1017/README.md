# IDX-SCORE retimed leaf core (ot_hbm_idx_chunk_rt), 2026-10-17

Cycle-exact equivalence vs ot_hbm_idx_chunk_owned_native (tb_idx_chunk_rt_equiv.sv, run_chunk_rt_equiv.sh @3d3f3c256, E4):
6 frames x 32-head query loads + 200 keys, every output on every edge.

| mode | expect | result |
|---|---|---|
| pos (first key 2 edges after the last query beat = hardware boundary) | PASS | PASS 2,337 checks, 1,063 outputs, 0 errors |
| gap4 (engine settle rule) | PASS | PASS 2,349 checks, 0 errors |
| qlate1 (query broadcast one edge late) | FAIL | FAIL 2 mismatches (the broadcast keeps the old load latency exactly: 0 slack lost) |
| seam (region seam head1->head2 one edge late) | FAIL | FAIL 965 mismatches |
| swap (leaf computes its neighbour's heads) | FAIL | FAIL 1,063 mismatches |

Root/seam map (16 regions per leaf, H-DIE 10-17): region r = column r/4, heads 2(r%4), 2(r%4)+1 on clk_pair[r]; glue on clk.
Every inter-root hop is register-to-register: glue rkey/rq -> region pin regs; region cs_out -> next region csi_p;
last region cs_out -> glue c_sum; region online -> glue rdy1. Term delay lines live in their head's region.
Protocol note for the compiler: a query reload must not follow a key by fewer than LAT_T+FPL*2 (~46) edges (unchanged
frame drain); keys follow query beats by >= 2 edges in hardware (engine settle rule enforces >= 4).
