# Exact address model before RTL changes

Source: selected engine e4a/e4b40562f324, AW32 HDMAX128 KVHMAX2 QKV1 APIPE0 QPIPE2 NATIVE_ROWS1 QMUT0. Frozen source and blob/SHA bindings are in source_binding.json. Existing native source is generated SHA38376238 from mapped-original SHA2b34032b; it is not a certificate for any successor. No RTL edit, new native generation or gate has occurred at this model checkpoint.

The actual report start u80525 is original graph cell80525, instance _170386_, DFFHQNx1, CLK4, D45530, QN31933. Pinned original parser SHA4adb3e6072ab0e5d93ddaa5205d5139c37971aa87175b1923beea9261dd2619b finds the cone ending at u16153.Y reaches exactly32 FFs80524..80555. Their one-state-level descriptor capture ancestry is d_data[112]..[143], respectively, plus common mode-control d_data[3:0]. Thus start80525 corresponds to architectural field a3 bit1 (descriptor113). This static provenance is not a transaction sensitization proof. Exact library-generated DFFHQN model says QN<=~D; no positive storage polarity is inferred from its name.

The complete32-bit prefix rules out calling this only a truncated low-bit row offset. It includes the full ring selection feeding s_rbase, shared by ROWS and IKEY. A decrement is used by ROWS s_local only. Existing timing alone does not select one unique mode or establish that every reported topological arc is jointly sensitizable. Preserve this distinction.

All source address operands are unsigned packed vectors. Every named address intermediate is32 bits and all results wrap modulo2^32. s_stk is3bits, pitch is5bits, row/base/stride/ring/gs are32bits. Shifts of32-bit operands discard overflow; unsigned small fields zero extend. k_q is6bits, st_sec5bits, st_ph3bits. The literal1 in the final IKEY scale offset is a32-bit unsized integer; the conditional produces32bits0/1 before32-bit addition. No power-of-two ring, legal pitch, ownership, valid descriptor or address-range assumption is admitted.

Preserved equations (each + or product is an original32-bit operation boundary):
- local = ring!=0 ? row & (ring-1) : (gs<<4)|(row&15).
- rbase = base + (ring!=0 ? 0 : stk*stride).
- raddr = rbase + local*pitch.
- blk = (rbase+(sb<<11))+(sb<<7), sb=gs>>6.
- code = ((blk+((1+zeroextend(q[5:2]))<<7))+(zeroextend(q[1:0])<<5))+((row&15)<<1).
- scal = blk+(zeroextend(q)<<1).
- RAW output = base+row; ROWS output = raddr+sec; IKEY code output=code+phase; scale output=scal+(phase==4?1:0).

All-cycle output semantics matter: st_wa defaults0, is updated under the original st_act/!st_pad/ap_go/case/payload conditions, including ROWS address generation when u_mine=0 and w_v=0. qk_wv selects qp_wa with the original4-state conditional merge. Do not compare only valid-qualified addresses. The candidate must leave these muxes, state/enable/reset assignments, clocks, macro accesses, fault/credit behavior and output cycles unchanged.

Four-state obligation: ordinary Verilog arithmetic +,-,* returns an all-X32-bit result if any operand bit is X/Z, even if a bitwise implementation could determine some result bits. A structural helper must therefore retain this exact pessimism at EACH replaced arithmetic boundary. Proposed poison p=(^operand)^(^operand) is0 for fully-known input and X otherwise; XORing {32{p}} into the structural result produces allX when required. For two operands OR their poison bits. Reductions/comparisons and ?: retain original expressions, including bitwise merge on an X condition. This is a proposed equivalence lemma, requiring actual4-state validation and binary formal proof before adoption. Never use case-equality detection as synthesized hardware or assume2-state simulation proves this obligation.

Concrete bounded candidate: replace only32-bit stream-address arithmetic with unsigned prefix-add (five parallel prefix levels) and small-width partial-product carry-save trees (3 terms for stk*stride,5 for local*pitch), with a final prefix addition and per-original-operation poison. Keep APIPE0 selection and every output mux/condition exactly. No added edge or state. Existing nonselected parameter behaviors remain required; a source-specific selected-configuration proof is explicitly scoped, not generalized. Prefix topology is a source proposal; actual mapped depth and native32 admission must be measured anew.

Next necessary qualification: binary combinational equivalence of each exact32-bit replacement over all operands, actual X/Z boundary/carry vectors using a4-state simulator, selected production-engine projection preserving raw output addresses/state/reset and causal arithmetic mutant, then new exact source mapping/native census. Existing conditional/cold proofs do not transfer to a newly mapped copy graph. No gate until these obligations and publisher coordination are satisfied.
