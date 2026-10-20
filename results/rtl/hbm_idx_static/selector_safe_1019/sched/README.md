# IDX full-shape calendar proof, SAFE selector (L2H-IDXSEL 10-19), src claude/l2h-idxsel-1019 @2eb3176f1, Verilator 5.050 (ot-epyc5)
run_scheduled.sh (calendar sel_in 3 / sel_out 2, frame 1411): pos_gap100 PASS (TX 1286 = prediction), pos_gap4 PASS (TX 1190);
mut1_query, mut2_key, mut_flush, mut_pins0 rejected. mut_drain SURVIVED -> script exit 1 (no IDX_SCHEDULED_GATE_PASS line).
drain_probe/: op5 block moved 1, 2, 3, 4 edges earlier into the 4 drain slots before it (pass 1 op5 at 817, pass 2 at 1026,
last op4 at 812 / 1021): all PASS with identical scores/records/flits/timeline. So on these vectors the last scan line's
histogram never changes op5's choice: the mutant is undetectable by the vector set (coverage gap, already open for the
pipelined core 98f4b19a7, lanes/HBM-C.md), not a calendar fault on the positive runs. NEXT (bench owner): a vector whose last
scan line decides the threshold (or an RTL mutant that drops the last line's histogram add), then re-time sel_scan_drain.
