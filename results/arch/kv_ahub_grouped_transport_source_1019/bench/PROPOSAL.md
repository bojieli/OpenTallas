Bench draft only; NOT COMPILED/RUN. Parent emitted-source review remains mandatory.

Files: tb_grouped_transport.sv, old_q_injection.svh, tb_grouped_default.sv,
run_fleet_reviewed.sh. bash -n PASS; no RTL compile/run has occurred. Frozen predecessor source must be passed separately.

The scoreboard samples true accept before each rising edge and expects that full
268/68-bit word exactly four edges later. Receiver reset discards outstanding
receiver ownership; transmitter reset must drain exactly four preexisting words.
Every edge compares out_valid (including idle/startup), so extra output fails.
Changing owned return fault nibble independently of payload catches wrong-owner
mutation. No invented public owner bits or arithmetic qualification.

Independent explicit raw root two-stage and leaf four-stage recurrences predict
admission. A separate actual enabled frozen predecessor is checked against its independent
leaf-only recurrence, then its actual first acceptance requires successor admission
exactly two edges later in the selected release schedule. This is a private test
of the approved delta, not production calendar modification.

At time .5ns (before first edge, raw already LOW), static hierarchy assignments
write every root/leaf/phase/slotvalid/ringvalid/landingvalid/group ingressvalid,
and all data arrays, to all-one, partial group/bank, or all-zero histories; INIT_CASE3 adds actual X old Q in four-state Icarus.
Assignments are released immediately (procedural deposit; no force). Public
accept/out_valid must be zero at 1ns. Then actual reset/clock recurrences converge;
no fixed quiet-window mask, equal-state premise, or data validity assumption.
Three Verilator random seeds additionally sample unspecified state. The identical
bench runs in Icarus for all four old-Q patterns and both widths; the default
bypass also runs in Icarus.

Cases: rawLOW preedge, staggered initial release, healthy line-rate/wrap, TX-only
reset drain, RX-only reset discard, repeat staggered reset/release, sparse traffic,
idle fault-bearing words, and final continuous/idle drain. Default ENABLE0 compares
all340 output bits against both frozen predecessor and direct interface equations
for256 input/reset patterns.

Dynamic mutants1(remove rawauthority),2(rootearly),3(leafearly),4(stalegroupvalid),
5(readslot),6(returnfaultowner,returnonly). Every expected mutant failure requires
a nonzero application status plus causal failure regex; logs, .rc and measured
/usr/bin/time resource output are preserved. Structural merged/overloaded groups
are source-expanded census failures, not manufactured runtime failures; parent
owns that check separately.

Proposed measured admission: previous standalone component builds were small;
request16GB/2threads/4GBdisk, unpinned ot-run, no timeout. Runner measures every
build/run with time -v. Parent chooses frozen remote directory, synchronizes exact
reviewed inputs, then launches via /home/ubuntu/bin/ot-run --mem 16 --threads 2
--disk 4 --dir REMOTE -- bash run_fleet_reviewed.sh --reviewed-source with explicit
GROUPED_SOURCE/PREDECESSOR_SOURCE/REVIEWED_SHA256 environment. Do not execute this
proposal until source graph review authorizes compile.

Limits: two-state sampled initial histories, common clock, conditional reset
contract; no native fanout/storage/PG/timing/reset recovery, arithmetic health,
actual child/calendar, whole-parent SU/MU, or physical qualification claim.
