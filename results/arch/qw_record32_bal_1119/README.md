# Record port n32, depth-balanced regeneration (FABLE-FIX-S81-GLUE 2026-11-19)

Why: QC glue (qfd_qc_glue_part, u_sys_face.u_ot_pr_core.u_record = qfd_sys_face_record_port_n32) failed TT setup at -130.39 ps
on 648 ends at the GRT gate. The netlist keeps every 2-input gate as its own cell, and its registers sat behind up to 25
gate levels: wide record zero checks (370 / 446 / 495 bits) and 64 / 80-bit digest and epoch compares in front of the
fault / accept priority chains of the five sub-blocks.

What the logic computes (unchanged): BEGIN / AUTH record decode; two write ledgers whose digest round is
rotl(digest,7) ^ data ^ {desc,addr} per observed full-word write (1024 PW then 8 DW) with the final digest compared against
the authorized digest; the two-sink commit join; HOST context decode against the installed image; witness transmit.

Change: rtl/qwen_split/qfd_sys_face_record_port_bal.sv is a readable rewrite with the SAME registers and the SAME next-state
function for every state and input (0 added cycles, no interface or latency change): flat sums of products over shared
terms instead of nested priority muxes. tools/qwen_split/record32/depth_opt.py re-associates every single-user AND / OR / XOR
cone by leaf arrival (NAND / NOR levels). bound_record_graph.py --port-shape keeps the 36 source copies and 54 reset leaves
the parents bind. Result: 5891 cells (was 6590), 1193 flops (was 1244), register depth 13 levels at most, 11 or fewer on all
but 12 registers (was up to 25); the port list is identical.

Command:  (seconds).

Proof (all in this directory):
- rewrite_source: one-edge transition + output SAT, readable rewrite against the original source, 1975 comparisons over 1976
  free state / input bits: no model.
- rewrite_emitted: the same miter on the EMITTED graph (fanout copies, input copies and reset leaves bound as the parent binds
  them), 2018 comparisons: no model (74,542 variables, 193,306 clauses). Three single-gate mutants of the graph are each
  refuted by the same command (negative control, not kept).
- bench/run0.log: Verilator 5.050 lockstep of the emitted file against the original source on every edge: the production
  1024 PW + 8 DW program, 800 random edges and 48 protocol episodes (12 deviation kinds x 4), 53,803 checks, PASS;
  run1..3.log: source-copy, reset-polarity and Boolean mutants all FAIL.
Not covered here: mapped timing (the private glue kit to GRT TT) and the die-level bind (ports unchanged, so no bind edit).
