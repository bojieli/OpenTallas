# Rootctl FACEQ successor

Structural fix for g2ef TT -416.9ps setup: vm_rq and index_rr now leave literal kept face registers. ARGMAX raw request is captured by vm_rq face registers, keeping ARGMAX VMX77; INDEX RTT +2 requires die pad -2, TOPK +1/row. FACEQ default0 unchanged.

SAFE review before first gate (10-21 09:47):
1 PASS fixed: literal face outputs, automatic io_flop_at_pins anchors direct registers.
2 PASS planning: one local region; datapath hop S/N <=259.2um, E/W <=432um with pin-output retiming; fallback reach measured at gate, no claimed waiver.
3 pending mapped native census: predecessor max32; FACEQ removes arq flop and adds direct flops; no high-fanout control added.
4 fixed: output OR/AND moved before face flops; 833ps same timing contract.
5 PASS inherited: programme SRAM macro, no new storage arrays.
6 PASS inherited pin-bounded outline with lattice SRAM at43.2,86.4, halo5.4, continuous std-cell area; utilization reported by gate.
7 PASS planning: single region spine (predecessor TT/FF pin spread46.3/48.0); no regional crossings introduced.
8 PASS inherited: only new valid/control reset, datapath unreset; two-stage landed reset and max32 replicated leaves.

Existing TOPK and ARGMAX latency benches run at FACEQ1, with VM_RT64/VMX76 mutants; source-bound witnesses required before submit. G2e live route remains untouched.
