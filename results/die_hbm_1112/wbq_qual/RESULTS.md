# HBM-WBQ-QUAL-1: parent-in-the-loop qualification of the WBQ root S7 form (11-12)

Bench: `tb_qual.sv` + `qual_comp.sv` + `qual_s7_g2.sv`, driver `run_qual.py REPO OUT` (Verilator 5.050, nice, J=4). Two compositions of the REAL
parent (`ot_wbq_sw` HREG=2 from reform_1105b, 16 K pin skids, 4 root slots, CDC FIFOs, SRAM models) run on identical random stimulus on two free-running
clocks: A = old root (`ot_wbq_root_g2` of reform_1105b), B = ROOT S7 (CBREG, SSTOPREG, GREG as parameters). g1 RR candidate: `-DQUAL_G1RR`.
`run_rrfifo.sh REPO OUT`: unit bench of the g1 record pipeline. Logs: `logs/`. S7+GREG source: branch claude/hbm-cores-c-wbq-greg-1112@7cfa7d1160a3.

Checks: golden K-write map (no dup, no missing, no corrupt), stream pins and wa sequence equal A vs B, K outstanding drained, no fault in clean runs;
fault sweep (stream sticky by bad reserve, stream sticky by corrupted wd sector, hbm sticky by spurious K write-done) at a random fifo_clk: fault raised and held,
root activity after s_stop, seam valids and K writes after h_stop, reset and clean recovery block.
Clock ratios fifo:hbm (ps): 1000:1000 (two phases), 1000:3000, 3000:1000, 1000:1370, 1370:1000, 833:1024, 1024:833. Real parent signals: copy_bank, s_stop, h_stop,
copy_on, start_copy, ack, done, g_credit, g_v/g_d. Back-to-back copy starts (<=3 fifo_clk after copy_on fell) occur 120 to 2000 times per run.

## Results (out_full2: 142 jobs; out_t3: target rerun, 43 jobs, after the F3 rule fix; logs/results_*.tsv)
| build | what | jobs | verdict |
|---|---|---|---|
| tgt (CBREG=1, SSTOPREG=1, GREG=1) | clean + fault + K always ready, 8 ratios, SLOW 0/1/2, QUAD 0/1 | 36 + 43 rerun | PASS (the 7 REGRESSION rows in out_full2 were the F3 absorb rule; all 43 rerun jobs PASS) |
| s7a, cb, st, gr, base (all off) | 4 ratios | 11, 8, 8, 8, 8 | PASS; base equals old root cycle exact (done-lag 0, write delta 0) |
| tgt_gin (parent GIN=1), tgt_h0 (parent HREG=0) | 4 ratios | 8, 8 | PASS |
| rr (g1 RPIPE), tgt_rr (g1 RPIPE + target) | 4 ratios, fault + clean (2 K modes) | 15, 15 | PASS |
| negative: late copy_bank, inverted copy_bank | mcb1, mcb2 | 2 + 2 | FAIL as required |
| negative: dropped s_stop, s_stop 3 late, g1 stop dropped | mst1, mst2, mst3 | 2 + 2 + 2 | FAIL as required |
| g1 record pipeline unit bench | rr_fifo vs cdc_fifo, 5 ratios, 50k words, producer on !full, random stalls | 5 + 5 negative | PASS, no loss/dup/reorder; MUT=1 FAIL 5/5; max occupancy 5 (old 4) |

Measured on the target config:
- After parent s_stop the new root works at most 1 more fifo_clk (old: 0), up to 12 lane events per group in that cycle; integrity 0.
- Seam valids after h_stop: at most 1 (old 0). K writes after h_stop: up to 32 in both forms (K outstanding, same as old).
- Fault raised and held in every injected F1/F2 case in both forms; recovery after reset clean.
- F3 (spurious write-done): in K-slow/quadrant mode one form can absorb the injected done when a write is in flight on that PC (GREG shifts in-flight timing by one cycle); a spurious done is indistinguishable from a real one there. Accepted only with no corrupt/dup K write; counted in the log.
- Done lag new minus old: mean +1 to +3 fifo_clk; copy duration +0.4 percent with K always ready; same set of K writes. CRED=4 does not throttle with GREG.
- CRED must be 4 (parent group queues use 2-bit pointers); CRED=3/5 are invalid for this parent and were dropped.

## g1 naming and sha
- Main `ot_wbq_root_s7.sv` (sha 94a79a2d...) defines `ot_wbq_root_s7_grp`, `ot_wbq_root_g0__fcore`, `ot_wbq_root_s7_g1`. The g0 recipe top `ot_wbq_root_g0` is the face shell around `ot_wbq_root_g0__fcore`: consistent. The g1 recipe top `ot_wbq_root_g1` needs `ot_wbq_root_g1__fcore`, which main S7 does NOT define (it defines `ot_wbq_root_s7_g1`).
- The Codex kit renames exactly that one line (make_s7_rr_kit.py): source sha 24d03128... (branch codex/hbm-root-s7-rr-1107@54e55794f394) vs kit file 5699133294ea... Otherwise identical. `ot_wbq_root_s7_rr_fifo.sv` (0040ce07...) is byte identical, enabled by define OT_WBQ_ROOT_S7_RPIPE.
- Proposed (NOT built through the recipe path) `ot_wbq_root_g1` entry in recipes_b2.json, files under rtl/hbm_accel/counted_1109/ot_wbq_root_g1/, defines [OT_WBQ_ROOT_S7_RPIPE]. HBM-CORES-C owns the edit and must check gen_core_kit_hbm.py with the fshell wrapper. The parent bench builds the S7 g1 with a local GREG patch (bench derivative, not a kit source).

## Remains unqualified
- g0 reset4/rbin1 and g1 rbin3 setup classes, SW pin clump, clock entry under the stack: physical, not covered by RTL simulation.
- CDC FIFO first-stage hold (rgray to rg_w1, -0.39 ps) and metastability: zero-delay RTL does not model them.
- Real die clock skew; ratios beyond the 8 tested.
- Only three fault classes injected (bad reserve, wd corruption, spurious done). Not injected: faults inside K ports, SRAM errors, reset during a copy.
- GREG under long K back-pressure: run with K always ready and random ready only.
- Token-level adoption of the g1 extra in-flight capacity (5 vs 4) and the perf cost: not done here.
- LEC of S7+GREG: not done here (Codex did g0 S7 LEC without GREG).
