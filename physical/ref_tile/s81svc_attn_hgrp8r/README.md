# S81 attention head group 8r (registered SRAM write face)

Structural fallback for hgrp8 (owner rule 10-19: gate the safe variant in parallel). hgrp8 gate3
(ref_gate s81svc_attn_hgrp8-20261020-043206) reached GRT overflow 0 but setup repair stalled at WNS -167.9 ps /
TNS -427 ns, worst endpoint u_ot_pr_core.c508230/wd_in[25]: ring write data arrives combinationally from the
arithmetic pipeline into the SRAM write setup window.

Change (only): every one of the 17 ring SRAMs is instantiated through ot_s81svc8_sram_wreg
(rtl/hdc/v41x/ot_s81svc8_sram_wreg.v), which registers the whole write port (w_ce, w_addr, wd; the constant
mask folds) one edge before the macro, so macro write pins are flop->macro only. Source
rtl/hdc/v41x/svc8_hgrp8r_bounded.v = svc8_hgrp8_bounded.v with the top renamed ot_s81svc8_hgrp8r_s81_bounded and the
17 macro masters renamed (generator /home/ubuntu/scratch/s81-hgrp8r-1021/mk_hgrp8r.py; every other byte identical).
Macro instances are now c5082xx.u_mem; placement unchanged. RTL twin: ot_s81svc8_ring #(.WREG(1)) (-DSVC8_RING_WREG).

Cycle accounting (checklist 8): ring = write t, read address t+D-2, capture t+D-1, D>=4 in svc8 (FPL 4..24, FML 6).
The registered write lands at t+1 < t+D-2 and the macro is read-before-write only on the same edge, so every read
returns the word written for it: ring delay, group latency and the static schedule are UNCHANGED (+0 cycles to the
svc schedule; the extra edge is internal to the ring's read offset). Proof: RTL lockstep m0w vs old group and mapped
lockstep (gold flat svc8 vs hgrp8r netlist) -- logs in results/rtl/s81_dv_1016/svc_rs/svc8_hgrp8r_1021.

Checklist deltas vs hgrp8 (all other items as below): 1 pins unchanged; 3 fanout: each former wd/addr/ce driver
now drives one flop D instead of the macro pin (same load count), each new flop drives 1 macro pin -> census max
stays 32 (gate re-runs the native census); 4 depth: SRAM write setup path cut to flop->macro; 5/6 storage and
floorplan unchanged (+~700 flops, ~+250 um2 std); 7 clock: new flops are SRAM-adjacent sinks of the same domain;
8 schedule: +0 cycles (above).

---- hgrp8 README (inherited) ----

# S81 attention head group 8

Zero-cycle replacement for the original production four-head group. Arithmetic modules, rounding points and reduction order are unchanged. Long skew/fault/valid delays use 17 SRAM32x64 rings. Stationary-write predicates decode before the existing R0 edge; data/bank and actual stationary capture retain their original edges. WRITE_PREDECODE defaults off in the RTL candidate; the admitted source was mapped with SVC8_WRITE_PREDECODE enabled, then bounded and re-synthesized.

Source: rtl/hdc/v41x/svc8_hgrp8_bounded.v, SHA256 6cc7756384633bed7fc0c70e636ca605e2e19e274df720c92d2244bcc6062e43. The plain source is 65,816,476 bytes. Gzip proof copy and complete compressed census/replication ledger are in results/rtl/s81_dv_1016/svc_rs/svc8_codex_1020/retained. Plain text is required by existing lint and preflight port readers; Yosys alone can consume gzip.

Retained mandatory-flow census PASS: 515,961 roots examined, max dynamic loads32, zero violations/role errors, no constant output bits. Replication invariant PASS: 4,775 clones, 513,006 cells before explicit inversion materialization. Retained cells590,189, including84,310 HQN/4,614 ASR flops and17 SRAMs. Measured standard area63,344.24um2; SRAM area9,390.92um2. Three 20,000-cycle lockstep seeds PASS mism0, valid outputs14,983/19,942/10,036; bank/address/fault mutants all causalFAIL. Symbolic head/lane stationary-write equality SAT SUCCESS in2.89s. This focused proof excludes arithmetic and the mapped graph.

SAFE-DESIGN pre-gate review:

1. Pins PASS for functional ingress/egress: data/bank at R0, decoded stationary-write predicates at the same R0, every functional output registered. Upper512 ld_w bits are reserved in the inherited PWORDS2 interface; the original group also ignores them. No tied functional output (census constant outputs0). Source landing has two reset stages; flow landing is enabled at2 stages. Reset asserted>=4 edges, iv/ld_v withheld for6 release edges; stationary weights written before use.
2. Reach planned PASS:432um square with two central macro columns, intermediate source R0/D1 and arithmetic pipeline stages; no planned fixed-terminal stage requires an unregistered full-tile crossing. The placed reach audit remains mandatory at the gate.
3. Fanout PASS: retained native max32, including resets and raw functional inputs, no waiver.
4. Depth structurally fixed: unchanged production FPL4/FML6 pipelines and golden order; predecode uses bounded control comparisons at the existing input capture edge. Actual native depth/setup is checked by the gate; no timing mask or exception.
5. Storage PASS: long delays in17 SRAM32x64 macros. Each independently accessed stationary lane bank is5x16=80bits, below2kb. No new ECC in academic phase.
6. Floorplan PASS at prescribed432x432: macros on43.2um lattice at x172.8/259.2, y43.2k,17.28um E/W pin faces,205 total pins =>5.93pins/um per face. Centre column channels preserve continuous standard-cell space and full-width lower band. Measured fill39% generates WARN, not FAIL; outside-macro standard utilization35.74% gives additional placement headroom. Aspect1:1.
7. Clock structurally fixed: one compact432um CTS domain, clock at the inherited N face; pin-flop TT/FF spread<=80ps remains mandatory. Both hold margins0.03ns. Source cycle schedule unchanged.
8. Schedule PASS: delta0 score and stationary-write edges. Parent still names old hard-group source/view; explicit hgrp8 replacement and actual minimum parent/consumer proof are required after closure. Old SOP2/SOLP2 ST2 receipts each8/8PASS qualify the existing producer schedule, not replacement adoption. ST0 remains unqualified due compiled P.V drain faults; no compiler constant change is claimed.

Gate must pass native census, pin/reach/depth checks, CTS and TT/FF spread before submission. No source or layout adoption is claimed by this kit alone. SS setup / FF hold remain the headline signoff policy; TT is pathfinding evidence.
