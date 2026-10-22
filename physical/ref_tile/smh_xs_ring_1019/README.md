# HBM-SMHXS-RING rg1 safe-design packet

Sizing: `results/rtl/smhxs_ring_1019/sizing.json` written before RTL build.
External data latency and throughput unchanged (1 word / edge). Reset assert/release gains two registered face edges, as already required by hxh.

1. FIXED: all data/control input/output pins retain the existing RTL landing/launch registers. Raw reset now lands in two plain RTL registers before either relay. No flow pin-reg latency.
2. PASS pending gate: outline432x345.6, stages local to pins/macros; no data timing exceptions. Gate wire reach must confirm <=405um.
3. PASS pending synthesis: operand ring address fans out only to four 2-bit lockup copies; each macro receives local negedge input registers. Existing kept strap-tree copies retained. Lint will confirm no merged high-fanout critical driver.
4. PASS pending gate: no new data mux. SRAM rd_out -> existing output flop; fixed two-bit slot add/subtract and half-cycle launch. Existing rotation stages unchanged.
5. FIXED: 788b x3 flop delay replaced by four-slot SRAM ring. No flop arrays or wide runtime output mux. Four macros allocated128x256, four active slots. Remaining wide r0w and macro negedge stages are separated by SRAM from the output stage. SRAM is fault-free per academic validation policy; no new ECC.
6. FIXED: all eight macros on43.2um origins, x pitch129.6 and y pitch86.4. Outline432x345.6 (aspect1.25), full-width cell space above macro rows, no power islands. Full-face pins: N1639/432=3.80; S2069/432=4.79; W831/345.6=2.40; E19/345.6=0.06 per um. Horizontal macro channels34.776um with16.2um pin-face halo. Pre-gate hard+old-std fill26.8%; gate synthesis must report actual utilization; pin-bound sizing explains the excess space. Coordinator accepted low-fill waiver08:00: lattice plus >=20um macro-face channels require the safe geometry; final actual synthesis utilization still reported at gate. New hard macro area+15,566.3um2; outline area+101,616.5um2 vs302.4x157.68; no data latency change.
7. PASS pending CTS: one geometric tree from the stem beside clk, equal buffer levels; tile <1mm. Pin-flop TT/FF spread must be<=80ps. IO/core hold margins0.03ns. Macro inputs launch at negedge for hold safety.
8. PASS: fixed four-slot counter, no credits/backpressure. Same data edge/II; two reset landing cycles already handed off by hxh. New outline goes to SM parent/die owner before binding.

Do not create REVIEW.json or submit until coordinator has inspected gate PNGs/checklist. Prior hxh failure remains immutable evidence in its original tree.
