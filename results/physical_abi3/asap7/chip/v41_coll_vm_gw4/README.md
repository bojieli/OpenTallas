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
