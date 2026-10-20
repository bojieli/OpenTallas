# Native32 v5 replay address source experiment (not qualified)

Immutable source88e0e5958 replaces the three full-width predicates
`d_ack > ((sender_after_launch - una_skip) mod 2^SEQW)` with kept independent
parallel carry/compare modules. No constrained protocol range is assumed.

The subtract uses p=a XOR NOT(b), g=a AND NOT(b), c0=1. Each carry ci is the
OR of its complete group-propagate term and every lower bit's generate term
propagated to i. Difference bits are p XOR carry. Each unsigned greater term
requires limit[i] AND NOT(difference[i]) AND equality at every higher bit;
gt is the OR of those terms. This exposes bounded parallel logic to native
mapping instead of a serial increment/mux/subtract/compare chain.

There are no new flops, SRAMs, protocol edges, reset stages or output ages in
source. Mapped area, native <=32 loads including reset and actual depth remain
measured qualification conditions, with no claim from this source count.
The native scout preserves ORFS canonical keep-reg hook and adds the new kept
module to SYNTH_KEEP_MODULES, TT same library, CH_BOARD700, period770ps.

`prefix_equiv.sv` proves the exact modulo unsigned truth relation for ALL 30
input bits (arbitrary a,b,limit), no initial state or protocol assumptions.
Yosys0.68+post SAT SUCCESS is in prefix_equiv.log. This is a combinational RTL
proof, not a native ASR model or production lane qualification.

Fresh native source scout and full 5.050 boundary nominal are pending at ep6
codex-s81-coll-native32v5-1020 and codex-s81-coll-native32v5-bench-1020/runs_v5/m0.
Prior v3 max32/621.8ps and v4 rejected35/686.8ps sources/evidence remain intact.
No physical gate; one-band packing/reach/native/clock/PG qualification owed.

TERMINAL REJECTED: fullproduction79994 PASS and16306FF/55SRAM native max32/0>32, but mappeddepth733.5ps/20levels from pace_ok to replay rp_r. No gate. failed_source.sv+exactcensus/depth/nominal committed; current source restored immutable v3 before any successor. Original staging127 and permission126 failed before design execution, preserved remote/local sessions; corrected reruns terminal.
