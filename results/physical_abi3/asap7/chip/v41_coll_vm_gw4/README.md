# V4.1 collective GW4 -> VM static-bank neighborhood (W2 rung 4)

Routes of `ot_v41_coll_vm_gw4_neighborhood` (transpose OUT_PIPE=1 + four-bank
macro VM, DEPTH_GROUPS=1, 16 x ot_sram_1r1w_512x128) and of the transpose
alone, at 0.92 ns with 60 ps set_clock_uncertainty (setup and hold) and a
20 ps hold repair margin. Records are the runner's source-pinned JSON.

`transpose_fo12_idealio_cts_hold_failure.json` (historical, failed): with the
conventional ideal-clock 25% I/O delay the 23,686-sink clock tree (path depth
5-6) arrives later than the 230 ps input min delay; CTS inserted 20,638 hold
buffers on the directly registered in_data inputs, hit RSZ-0060 and stopped
at -63.3 ps hold. This is a boundary-model artifact, not an internal path:
the die balances the block's insertion, so external launch flops are clocked
late too. Later routes model that with an explicit balanced-clock allowance
L = 200 ps (lower bound of the 212-234 ps routed target latencies of the
earlier full-width transpose route): input min delay 0.25 ns (L + 50 ps
clock-to-q of an adjacent trunk flop), input max delay 0.43 ns (L + the
25% = 230 ps external budget). Outputs keep the 25% ideal-clock budget.

`transpose_fo12_balio_cts_bufcap_failure.json` (historical, failed): with the
balanced-clock input delays the input paths are no longer the limiter, but
21,235 endpoints still violate hold at CTS (initial WNS -78.8 ps): the
16,384 transpose tile cells are loaded straight from in_data_q, and each of
these direct flop-to-flop paths must absorb the 60 ps hold uncertainty plus
the 20 ps margin. repair_timing hit its default 20% buffer cap (RSZ-0060,
20,776 cells) at -45.1 ps. Later routes raise only the cap
(`physical/abi3/w2d_repair_buffer_cap.tcl`, -max_buffer_percent 60, at
PRE_CTS and PRE_GLOBAL_ROUTE); the hold-cell area is priced by the route.
