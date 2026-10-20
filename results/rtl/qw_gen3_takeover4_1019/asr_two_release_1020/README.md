# Typed two-release-chain functional witnesses

Evidence only; no helper or release RTL edits. Canonical model source is ROOT's verified3905a5c7d coupon, already on main bf429e404. ASR normalized SHA ee63e9a38cab2a9fa507f6fdc0480b04f047088a2f76464a5fca6182a9ba26d5; plain HQN cbba1c176afe1a03e677d21ee4e095c7b3d326689d8ec5ec46640d3e43a26254. Staging rechecks both hashes before simulation. The imported buggy ASR model is not used. The upstream canonical coupon independently checked544ASR and128plain-DFF binary cases against pinned PDK UDP/Liberty truth; this chain experiment does not extend qualification to other cells.

Canonical ASR QN is inverted: with SETN=RESETN=1, QN<=!D on rising CLK. SETN0 asynchronously clears QN; RESETN0 with SETN1 asynchronously presets QN; both-low clears. Thus a logical release-to-one stage uses native D0, RESETN1, SETN=its active-low clear and positive logical output QN. “D1 release” in RTL/helper language must not be confused with native pin D1 on this inverted-output cell.

The positive typed chain is:

- stage0: own CLK, native D0, RESETN1, SETN=raw_n, output s0;
- stage1: same own CLK, native D0, RESETN1, SETN=s0, output s1;
- reference: actual qfd_land8 two-release pattern, q<=1 with asynchronous clear by the previous stage;
- validity stage: same-clock canonical ASR, asynchronous clear by s1; offered validity admitted on the next own edge;
- payload: four canonical plain HQN cells, with input inversion to represent positive data, left unreset; only admitted validity permits payload comparison.

Assertions are phase independent in the fault-free digital model. Deassertion propagates stage0 on the first own rising edge, stage1 on the second, and first admitted validity on the third. Four restart sequences exercise cold off-phase release, a50psdigital assertion wholly between clock edges, assertion while the clock is high with in-flight valid/tag state, held reset, and deassertion while the own clock is stopped and a foreign clock keeps running. Payload tags change on falling edges so first valid use must contain the current sampled tag, not retained data. Timing/pulse-width/metastability/recovery-removal behavior is outside this coupon.

Actual source qfd_land8 W1/ICG0 is instantiated alongside the typed cells. en_s0/en_icg and rs0/rs1 must match the two canonical stages on every own/foreign edge and off-phase event. With same source/receiver clock, L3/K2, the actual D8 first word is checked at R0+5 own edges, with zero output before the warm sample edges and no epoch fault. This is a minimum functional source-pattern witness, not a die K/origin or mixed-clock production proof.

Seven concrete native-body negatives are compiled separately, not selected by changing expected results: stage1 bypasses stage0 clear; stage1 wrong clock; stage1 wrong native D; stage1 wrong clear/preset polarity; then stage0 wrong clock/D/polarity. A negative must produce an actual chain/first-valid/asynchronous-clear/held-release mismatch. A nonzero exit from compilation or a generic end-of-run coverage guard alone does not count as a witness. Golden runs use seeds1and37; all actual simulation logs and model identities are retained.

Attempt1 is intentionally preserved: it incorrectly demanded that actual native_o clear asynchronously. Actual ot_qfd_land8_region.o is an UNRESET payload flop and can retain its value between edges; its rs1/warm validity clears asynchronously. Only three erroneous immediate payload-zero checks failed; chain release and first-valid checks matched. The corrected coupon checks asynchronous chain/valid/warm quiescence, then payload at the sampling edge and when valid. This is a corrected bench assumption; no source/helper behavior was changed and no functional data path is masked.

These witnesses establish the functional semantics of the exact chain body and its causal mutations under the stated models. They do not prove a mapped helper's role classification, clock ownership, physical fanout, route reach, global release origin, SRAM contents, or production PLL/reset correlation. ROOT owns those static/helper obligations separately.
