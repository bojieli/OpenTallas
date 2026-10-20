# PVM distributed-input successor

The SAFE2 source leaves captured ev and tag_first single-source. Existing real native ev reaches 1,587 logical terminal loads. Buffers do not resolve the owner max32 rule. This source model adds one real input edge, aligning every payload, tag and command field and the core barrel reset epoch. It keeps the internal eight-edge barrel recurrence and SRAM collision semantics unchanged.

Four first-stage event registers drive 97 second-stage event copies in cohorts 25/24/24/24; 32 copies control 16-bit operand muxes,64 control 8-bit SRAM write muxes,one controls scheduler/faults. Thirty-two second-stage first-tag copies drive the corresponding operand cohorts. Raw event reaches four FF D pins; each first-stage event reaches at most25 second-stage D pins. Native per-cohort reconvergence remains to be measured.

This is sized before implementation: 1,212 input capture bits versus540 before, delta672 FF (48.9888um2 before reset/distribution logic). No extra SRAM and no new indexed storage. Per invocation latency grows one edge; full rate and energy remain unqualified. Model state counts will be reconciled against actual mapped state. The old physical s4a sizing is provisional; actual placement reach, density and all-role census govern the successor.

Default public source and existing receipts remain unchanged. The next source must compare original one-input-edge reference versus two-edge successor at exact translated ages, with cold reset/reassertion, first-use and command identity controls. An arbitrary bp phase, zero initialization, valid-low payload exemption or delayed fault mask is not a proof.
