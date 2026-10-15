Default-off opaque-token/context and GO protocol candidate
=========================================================

rtl/physical/ot_qwen_xcontext_protocol.sv is a protocol miter candidate only.
No physical root ABI or global producer/consumer controller is adopted.
Every request transaction denotes ONE phase, not a whole4/16-phase burst.
The record retains a full96-bit address quartet for EACH of32 root destinations,
IB379, VM version32, full k18/j3, phase4 and readmask4. Its opaque token16 is
unique among live records, including across the complete16-bit counter wrap.
All32 unique returns and all32 downstream acknowledgments must finish before
release. A duplicate/unknown return or invalid/duplicate ACK raises sticky fault.
A cache acknowledgment must certify every consumer behind that root and all
required return/replay quiescence; one tile's write pulse is not an aggregate ACK.

Reset/flush blocks allocation and returns until transport_flushed certifies the
old source, transport, cache and replay state has drained. No local helper can
prove that external distributed certificate. A late old return after a falsely
asserted certificate can alias a reset token; reset-generation fields or actual
flush proof remain mandatory. VM version32 is an exact retained comparison
context, not a independently proven production version allocator; its wrap and
writer commit semantics remain external obligations.

Source event contract: q_valid alone is not an event. q_output_step must be
sampled on EVERY live base edge and describe the edge that produced the visible
q/tag; disabled source steps clear output_step without changing q/tag. Then
return_event=q_valid&&q_output_step. An accepted return_event&&return_ready
causes one cache fill. If a produced event cannot be accepted, an explicit
ready/replay queue must retain it. Dictionary, source and gather load_step stay
live while core_step is paused. The helper rejects duplicate(token,root), but
an actual producer/gather event implementation is still required.

A separate one-entry IB379/GO mailbox captures an offer on base_clk and holds
it until core_step&&core_ready. A pending instruction cannot be overwritten;
a simultaneous consume/new offer is supported. core_go stays asserted while
core clocks are paused and becomes deasserted after the single acceptance.
The caller must bind core_step to an actual coherent core edge and core_ready
to valid production instruction readiness. The helper does not gate clocks or
prove ready=!active&&!pend safe to overwrite outstanding operand context.

Correctness receipts
--------------------

The dictionary miter uses actual pinned candidate IB words from PCs1/16/19/23
of14065c8c7 (program SHA120b42a583db68fb9faaa32d2076f1515d5c07e41787bf47533a1d230b4d1903),
and synthetic independent32-root full96-bit keys. It checks640 unique fills,
23 contexts, all32 roots, all16 phases, overlapping descriptors with repeated
full21-bit coordinates but different addresses/IB/version, reverse return order,
ACK retirement, reset/flush drain, and an instruction held for11 paused edges.
A separate full16-bit wrap test executes65537 allocations while token0 stays
live across65535 other transactions. Token0 cannot be reused until its ACK.
Stale-context substitution, duplicate-fire, GO passthrough and token-reuse
mutants all fail. EPYC4 unit oth-ubuntu-561523-1791959259 completed exit0.
The multi-root key miter does NOT generate keys from the production VM selector.

State and cycle receipt
-----------------------

Default DEPTH8/ROOTS32 entry:
3072 address +379 IB +32 VMversion +21 epoch +4 phase +4 mask +16 token
+32 returned +32 acknowledged +1 live =3593 storage bits.
Eight entries=28744; token counter16 plus mailbox380 plus flushing1/fault1
=398 control bits, total29142. Mutation-only latest-context registers3483
are eliminated when default MUT_CONTEXT=0. These are RTL storage counts;
there is no synthesis/PG/CTS/placed-pin receipt. At least two4-entry banks
would each contain14372 bits BEFORE bank control. A separate central control
root and actual clock/pin/mux/fanout lowering still require measurement.

This helper has ONE return-root port and ONE ACK-root port. Even when returning
one root and acknowledging an earlier root on the same base edge, allocation
at edge0 permits first return at1, first ACK at2, last return at32, final ACK
at33 and next same-slot allocation at34. Without overlap the bound is larger.
This serial test interface cannot represent the accepted native32-parallel
source. No native layer issue cost, 149-bit wire qualification, <=5% accepted
loss or physical fabric closure follows from this receipt. The mailbox adds
at least one base edge from offer capture to a possible core acceptance;
paused core edges and queue fullness add explicit waiting. The test's11-edge
pause is an exercised scenario, not measured production scheduling overhead.

Reproduce via xcontext_prepare.py --workdir DIRECTORY, copy xcontext_gate.py
as DIRECTORY/run.py, transfer the prepared directory to EPYC scratch and run
python3 run.py only through ot-run --mem 6 --threads 6. Actual-parent mailbox
binding uses xcache_parent_prepare.py --parent-commit 7cbe00c33 --context-mailbox
and xcontext_parent_gate.py. The parent fixture drains between instructions;
back-to-back production arithmetic context overlap remains unproven.
