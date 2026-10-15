# Qwen sequencer fixed native row transport

Production body uses STATIC=1, VARIABLE=0 and measured native row memory latency13. With output/input pin stations1 and two relay stages each direction, the actual response expectation is19 edges. Request issue and collective sends have no runtime ready or credit dependency. The new die completion pin svq_v accompanies vrq; it checks exact scheduled response visibility. Early, missing and late completions fault rather than become a successful adaptive schedule.

The AR bench uses TP8/N8 and the real legacy CRED128 setting, which STATIC deliberately removes from scheduling. All256 native rows issue consecutively at cycles8..263 and respond at27..282. Full segment lifecycle including looped-back writes completes in544 cycles. Changing legacy collective readiness from always ready to random produces a byte-identical full timeline. Every response is exactly19 cycles after its matching issue. Data and write address order are checked bit-exactly. Four mutants fail: early response, missing response, one-cycle-wrong response expectation, wrong response row.

The exceptional variable memory/admission test uses the actual standalone controller-owned request station and the embedded sequencer with VARIABLE=1. It passes ready stalls and13..23-cycle memory stalls in6846 cycles. This diagnostic station is absent from the production wrapper hierarchy.

Production state belongs to seq_su clk and the existing reset regions; the new svq_v input station follows vm_rq with the same IS delay and rsv[5]. The expected response pipeline grows from7 to19 bits. STATIC removes runtime credit-counter dependencies and uses a four-word output queue, eliminating the old latency-sized FIFO rather than creating8192 more flops. Production pins must be assigned by die tooling; no old CLOSED view can qualify this RTL.

The embedded production controller and newly generated controller both pass the transport bench. The native qfd_seq_su production top elaborates with PSRAM1, HQ2, TP8/D8, real dependencies and OT_QFD_SEQ_SU_NOWROM. Address regressions remain six positive cases and three observed failing mutants. Test scripts: rtl/test/qwen_seq_addr/run_transport.sh and run.sh.

Remaining integration: die wiring of svq_v and the real physical row13 response route, statically reserved collective receive/send windows, native pin/reset/clock and TT/FF/DRC qualification, and end-to-end cost versus immutable token price. The local fixed memory model is a protocol bench, not a native memory or die timing signoff.
