# Boot-age attention structural successor b3

B1 routed TT setup -105.22ps. B2 reset copies fixed reset fanout, but gate TT reg-to-reg -40ps remains in the same landed-codec payload -> root enables class. B2 is retained as evidence, not resubmitted.

B3 computes CMD and STATUS zero-check flags in 32-bit groups at the existing RX landing edge. The next stage reduces 16 flags rather than 493/507 data bits. Fault, valid, Q and RESULT edges are unchanged. Eight reset copies remain; no schedule cycle is added. Original closed and boot-age RTL files remain byte-identical. The new modules are bound only by this opt-in kit.

SAFE checklist before gate:
1. PASS: existing native pin landing/launch preserved; rst_n lands2 stages plus3-edge wrapper release. D2D raw data lands in codec flops; new zero flags have <=32-input combinational reductions before flops.
2. PASS: 302.4um square is below405um span; no long-die wire in this tile.
3. FIXED: eight KEPT reset copies, b2 synth1871 pre-opt loads split234x7/233 (<=256). Each new zero flag consumes<=32 data bits and fans into two legality expressions; route fanout rechecked by gate.
4. FIXED: split500-bit zero-reduction/control chain at existing landing. New pre-landing reductions are<=32bits; next stage16 flags. Codec lockstep8800 checks and controller/root/face pair16 modes33305 checks PASS; fault-delay mutant598 mismatches. Depth is measured in gate before route.
5. PASS: no new indexed storage/delay arrays. Existing payload registers are capture/launch registers;32 new predicate bits replace wide combinational reduction, no queue.
6. WAIVER REQUEST: 302.4 square is pin-bound (S1546pins at4tracks*.048um=296.8um), logic-only util~3%; no macros/power islands, one contiguous standard-cell core. Same die slot; four-track min pitch<=5.21pins/um replaces b2 three-track7pins/um. Lattice N/A(no macros).
7. PASS/design: clock entry S center beside control mass; b2 measured pin-flop spread49.6TT/46.7FF. B3 measured spread pending gate. io_hold_margin0.03.
8. PASS: static schedule; no added cycle, no credits/backpressure, no timing masks.

Critical-prefix list checked: no match for qkd_kvs_attn_ba3 or top qkd_kvs_attn_fl_ba3. B1 failure still requires coordinator packet/review as directed by parent.

Pin packing local check: grouped PPL at four tracks stranded slots on the S face. Replaced groups with per-bus disjoint pin_ranges and balanced literal placement over the full face; raw pin count/slot and die outline unchanged. Original local refusal preserved in attn_b2_recovery/gate_pinfit_fail.log.
