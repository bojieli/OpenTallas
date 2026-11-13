# Private PC SRAM static-delay candidate

New module is an opt-in storage form, not adopted by binder or POR. Interface is `clk, strap_cnt[CW-1:0], d[W-1:0], q[W-1:0]`; there is deliberately no reset. For PCv3 hsl3.fi use W291, BASE0, DMAX24, CW5 AFTER the existing fixed2 prefix. Straps0/4/19/24 then give total delays2/6/21/26. BASE2 is also supported if the existing fixed2 is removed. Do not double-count the prefix. No added latency; sustained II1.

Static selected depth is BASE+min(strap_cnt,DMAX). Values above DMAX clamp as in the original count bank. Declared total depths0..32 are supported; impossible shape declarations fail hierarchy-check under SYNTHESIS and simulation. Count changes at runtime are outside the static-strap contract. SRAM read/capture is two stages, hence read address wp-(D-2). Reads are disabled at D<3, and active read/write addresses never collide, including D32. Every binary initial write-pointer phase is valid modulo32. No reset event elsewhere restarts it; all W bits retain exactly the same history, including bubbles/epoch/control, after the first D samples. No invalid-word masking is used.

Important startup limit: ordinary four-state simulation with an uninitialized wp keeps X forever. This candidate has no simulation-only initialization and no invented POR. Its power-up claim is arbitrary BINARY physical state, proved below. Integration must explicitly accept that contract or supply a separately qualified startup design. No physical qualification is implied.

## Smallest-vehicle evidence (2026-11-13)

E8 scratch root: `/srv/opentallas-scratch2/claude/dkv100/pc_sram`.

- `run4/result.txt`: PASS3 seeds, both mutants caught3 seeds. Primary actual SRAM RTL with OT_MEM_NO_INIT; 155648 lockstep coupon checks per4096-cycle seed. Full291 bits for actual counts0/4/19/24, fused BASE2 and preferred fixed2+BASE0. Reduced17-bit coupons cover every count0..24, plus short0/1/2, depth32 and aboveMAX clamp. Warm-reset stimulus never pauses or resets comparison. Age and count-truncation mutants both fail.
- `formal_contract5/result.txt`: production BASE2/MAX24/CW5 full-domain BMC36 AND induction PASS using explicit synchronous SRAM contract; W1 bitwise miter, all static count values0..31, every initial binary pointer/memory state and arbitrary data. Bit slices are independent and use identical shared address logic. Wider data is tested above. Optional full-depth32 induction was still running at packaging; no claim for that induction.
- `formal_actual_resume/proof.log`: binary-state BMC36 SUCCESS using unmodified PRIMARY SRAM RTL, not contract replacement; optional induction still running at packaging. The 36-step cold convergence covers the maximum26 production delay with arbitrary initial state. This is not an unconditional four-state proof. No initial DUT state fixed; only test age instrumentation starts0.
- `shape_guard/result.txt`: legal BASE0/MAX24/CW5 accepted; illegal MAX63/CW6 rejected under SYNTHESIS.
- `census/generic_cells.json`: generic unmapped synth W291 BASE0/MAX24/CW5 is5 actual macros +878 FF +878 mux +75 other gates. Existing prefix adds582 FF, total1460 standard FF bits incl5pointer bits, down from7566 full-flop stages. This is a generic count, not mapped cell area.

Actual macro SHA256: `9286563862a9cac862351ef03094fab7f53edd82c38784349d588e0958e0bde2` for `physical/asap7_memory_macros_v2/ot_sram_1r1w_32x64_m1/ot_sram_1r1w_32x64_m1.v`. Existing macro geometry31.968x17.280um,5=2762.0352um2 per instance; four replicas use20macros. Existing TT clock-to-Q243.693569ps and FF196.092368ps are macro-model numbers only. Parent slot, pin access, clock, PG and timing remain unmeasured.

Reproduce only through admitted ot-run: run.sh OUTDIR (actual macro lockstep/mutants); formal_actual.sh OUTDIR (primary macro binary BMC36); formal_contract.sh OUTDIR (contract BMC/induction); shape_guard.sh OUTDIR; census.sh OUTDIR. Existing failed harness/tool attempts are preserved in scratch run1/formal1/formal_contract1..4; they are not passing evidence. No whole-die simulation or P&R was run.
