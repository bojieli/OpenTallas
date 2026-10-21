# Address factoring option plan: zero additional edges

PLAN ONLY, authorized bounded source/report analysis. Frozen e4a gate remains source40562f324; its full SS CTS report, real SDC and active job are immutable. No RTL edit, helper edit, synthesis, proof campaign, variant, gate or source adoption is performed. ROOT/Disk owns the ep9 incident; all admitted jobs are preserved and no ep9 launch/deletion is made.

## Actual expression and observed cone

The selected engine wrapper's behavioural reference is AW32/HD128/KVHMAX2/QKV1/APIPE0/QPIPE2/NATIVE_ROWS1/QMUT0, all engine data clocks ck_ingest. Production source is copied verbatim and SHA-bound here. At APIPE0 the stream output address uses the following unsigned32-bit math:

- s_local = ring_nonzero ? (st_row & (s_ring-1)) : ((s_gs<<4) | (st_row&15));
- s_rbase = descriptor_base + (ring_nonzero ? 0 : s_stk*descriptor_stride), with s_stk3 bits;
- s_raddr = s_rbase + s_local*s_pitch, with pitch5 bits;
- k_blk = s_rbase + (k_sb<<11) + (k_sb<<7);
- k_code adds block, shifted4-bit group+1, shifted2-bit sub-group and shifted4-bit row terms; k_scal adds k_blk+(k_q<<1);
- st_wa selects RAW base+row, ROWS s_raddr+st_sec, or IKEY k_code+st_ph/k_scal+scale-bit;
- w_addr = qk_wv ? qp_wa : st_wa, since QPIPE2 already registers the QKV branch.

This description preserves the actual source mux/control boundaries and explicit widths. No power-of-two ring, one-hot pitch, alignment, narrow address range or constant descriptor assumption is granted.

Existing mapped worst address path has48 output arcs/1737.71ps cell delay plus wiring, from physical FF80525 through serial AND5/NAND5/NOR5 and address logic to eng_waddr[29]. Its first six mapped gates combine progressively larger sets of preceding bit signals: u16130->u16134->u16137->u16140->u16143->u16147. This is direct evidence of an unbalanced prefix/reduction chain. Its exact RTL-register identity and whether that first chain is specifically the ring-decrement prefix are not established by existing metadata. Do not claim that a localized source rewrite fixes this path before exact mapping/qualification.

## Option A: localized balanced decrement/reduction, same combinational boundary

Express the exact32-bit s_ring-1 borrow as parallel prefixes: z_i = NOT(OR of ring bits0..i-1), z_0=1, and result_i = ring_i XOR z_i. A balanced prefix OR tree computes all required z_i, while ring_nonzero is the ordinary OR of all32 bits; reuse is allowed without changing its logic. This is an exact modulo2^32 identity for every binary ring value, including0. Preserve s_local's original ring_nonzero mux and every st_wa selection. No state, valid, ready, reset, QPIPE/producer/consumer edge or port changes.

Analytical topology: a full32-bit parallel-prefix network needs at most5 combine levels; a straightforward Kogge-Stone-style complete prefix has129 OR-combine nodes plus32 XOR/inversion endpoints before mapping (a smaller prefix topology is also possible). This is a topology/area estimate, not a measured speedup. Native fanout, routing cost and actual post-map preservation remain obligations. The present AND5 chain is six serial wide reductions before later arithmetic; Option A addresses the observed shape only if source mapping confirms the decrement/reduction correspondence. This is the smallest prospective change, so it is the preferred first source option once exact mapping is available.

## Option B: address carry-save factoring and one final explicit carry prefix

If the dominant path spans successive address arithmetic rather than only the first reduction, keep all current mode/control mux boundaries and compute the selected address's32-bit addends in parallel. For arbitrary5-bit pitch use five masked shifted partial products of s_local; for the3-bit stack index use three masked shifted descriptor-stride partial products. Compress simultaneous addends with3:2 carry-save cells until two rows remain, then use one explicit balanced32-bit carry merge. For IKEY, present the existing shifted k_sb, group, row and phase terms as separate width32 addends instead of serial '+' stages. All carries above bit31 are discarded exactly where the existing width32 assignments discard them; source expression signedness, shift widths, the32-bit intermediate (1+group) and small-field zero extensions must be retained explicitly.

Analytical model: five pitch partial products require three3:2 compression row-reduction levels before a two-row final merge; integrating additional base/sector operands increases compression levels and gate count, which must be priced for the exact selected expression. A32-bit generic carry merge has at most5 prefix-combine levels (129 pair nodes for a complete prefix topology), plus propagate/generate and sum XOR logic. This can remove serial carry propagation between multiple additions; it gives no MHz, area or final-fanout claim. It adds combinational gates/wires, zero FFs, zero SRAMs and zero calendar edges. Keep valid/data/identity/generation/fault outputs and the exact existing ready/credit behavior unchanged; do not move the QKV/stream arbitration or introduce speculative output transactions.

## Required exact model before any source adoption

Both options are unsigned fixed-width address Boolean identities, not floating-point reassociation. Their eventual model must establish exact modulo32 results for arbitrary legal descriptor/ring/pitch values and preserve every source branch, constant/read port, valid-qualified output and cold/reset obligation. No current primitive-copy record, source certificate, native census or physical view may be aliased onto a rewritten engine. A future source would need its own exact native generation/correspondence and ordinary source-bound physical qualification under the unchanged real1666.667ps relationship. Existing qualified benches are the reuse path after authorization; none was run here. Four-state simulation propagation and arbitrary initialization are not promoted to equivalence by these binary identities.

Existing TT signoff pc.log is reg->output-810.5ps at eng_waddr29, reg->reg+126.8ps. Full SS CTS detail is1540ps, source80525->address29-931.98ps; these contexts remain distinct. Clock periods/PLL relationship are consistent with the intended1666.667ps signoff contract, so no timing/IO-budget relaxation is part of either option. The current gate and all routes keep progressing; no new variant/gate before parent authorization, published support where needed and disk clearance.
