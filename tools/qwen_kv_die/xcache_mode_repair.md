Request-bound normalization and resident context repair (default off)
====================================================================

The original immutable split parent1ac31de60 has one live j_repeat input for
both cache read and fill normalization. The actual production op5 in this
fixture has xjs=ABCDE7, and exports old pending epoch{k0,j6}. An incoming
candidate PC1 descriptor has xjs0; its GO is held externally while its latest
mode is offered to the loader. Flipping j_repeat0→1 makes the original cache
normalize that OLD j6 request to j0. The old resident j0 entry then passes the
old21-bit tag check and supplies the wrong operand. Original parent arithmetic
fails at op5/core-edge1394 (base time18.076us). The exact original source and
failure are preserved in results/rtl/qwen_xcache_mode_1014. This counterexample
proves a missing external mode-stability contract; it does NOT claim the core
accepted a new GO at that same j6 edge. Old fixture draining between completed
instructions does not protect against offering/preparing a next descriptor.

New rtl/physical/ot_qwen_xcache_context32.sv is a separate default-off helper:
read_j_repeat travels with the old request; load_j_repeat comes from the fill's
resolved descriptor. Full21 epoch, normalization mode, context16, VMversion32
and full96 address quartet must ALL match the resident entry. A newer context
or version written to the same slot is a miss for the old request. The loader
then restores the exact old descriptor/version while all core clocks pause.
The helper itself neither creates context IDs nor commits VM versions, and
cannot guarantee the old snapshot remains available for that reload. Actual
version allocation, wrap/reset drain and source/resident retention remain open.

The repaired fixture uses the actual immutable production core/RPS0 hierarchy
from1ac31de60. Read mode is registered from reference production pre-update
xjs_r in the SAME request-generation edge as x_addr/x_epoch; the independent
reference address oracle still checks every actual candidate request. This is
source-bound simulation mode provenance, not an adopted physical export port.
Context/version are explicit harness descriptor fields; full producer provenance
and a production registered mode/context/version export remain missing. No
production source path or old parent master was edited by this repair.

The production six-profile arithmetic repair passes680 words/684 nonzero read
edges; raw split0..15 diagnostic passes936/876. Both report143 reactive misses
plus the explicitly injected resident-guard scenario. Restoring shared live
mode normalization loses the old pending request. Ignoring the resident
mode/context/version/address guard accepts a newer resident version and fails.
Original live-mode arithmetic failure and both mutants are required negatives.
EPYC4 unit oth-ubuntu-845109-1791963243 completed allfive cases with exit0.
The finite hash operands are not checkpoint/Qwen token data. Mid-operation
reset, clear and manual stalls remain in the actual production fixture.

Physical and cycle implications, not a qualified field cut
---------------------------------------------------------

Store32 entries each retain128data+21epoch+1mode+16context+32version+96address
+1valid=295 bits, total9440. Response128+stickyfault1 gives9569 storage bits:
4640 additional store bits versus the old4929-bit cache. Only valid32 resets
in the store; response129 resets. No added response edge is present in this
RTL. Comparators now check166 tag/key bits rather than just21; actual mux,
status-face setup/hold/CTS and pin fanout are UNMEASURED. Logical <15k storage
alone is not a physical signoff receipt.

Read interface4re+21epoch+1mode+16context+32version+96addr=170 bits,49 more
than the existing121-bit exported read request. Fill128data+21epoch+1mode+
16context+32version+96addr+valid1=295 bits,145 more than the old150-bit local
fill seam. A token dictionary can resolve some fields locally only after actual
source/context lookup and fanout proofs; the physical149-bit root lower bound
is not qualified here. In-core instruction context/version storage and separate
request registers could require48+48+1=97 additional flops, conditional on
where the accepted descriptor fields actually reside. The currently requested
production read-mode export itself is one register on the existing request
edge; no source or clock-path latency is silently added.

The simulated falling-edge combinational hit gate is not an approved registered
physical admission round trip. Guard misses pause the full core pipeline while
the live loader restores old-context data. Actual reload latency, registered
lookahead/credits, snapshot/version retention, parallel source delivery and native
whole-layer cycle cost must be measured; no <=5% loss or149 ABI claim follows.

Reproduce: xcache_mode_prepare.py --workdir DIRECTORY, copy xcache_mode_gate.py
as DIRECTORY/run.py, transfer the prepared source directory to EPYC scratch,
then run python3 run.py only through ot-run --mem 48 --threads 15.

Immutable production port binding followups
------------------------------------------

06cf43243 actual core_ctx now supplies read mode/context/version directly from
its registered production ports, rather than harness metadata. Independent
reference pre-update state checks >=600 actual query exports; actual op_accept
and accepted context/version are checked. Native680/684 and raw936/876 arithmetic
pass; original/live-mode/resident-guard negatives fail. Unit
oth-ubuntu-1102524-1791964837 exit0; results/rtl/qwen_xcache_production_mode_1014.

a778c2ba6 separately snapshots acceptedIB379 on the actual post-IREG go&&ready
edge. The fixture checks that snapshot against independently observed reference
acceptance, and checks its lifetime through an incoming next descriptor while
old j6 remains pending. Query metadata still comes directly from production
ports. Both arithmetic positives pass, and replacing acceptedIB with live ib_i
fails the lifetime assertion. Unit oth-ubuntu-1168503-1791965533 exit0; artifacts
results/rtl/qwen_xcache_accepted_ib_1014. This preserves each source-specific
receipt; no source is relabeled as a newer admission/event master.

Prepare using xcache_production_prepare.py --parent-commit 06cf43243 --workdir
DIRECTORY, or --parent-commit a778c2ba6 --accepted-ib. Copy the matching
xcache_production_mode_gate.py or xcache_accepted_ib_gate.py into DIRECTORY as
run.py, transfer prepared sources, and run only through ot-run. The five-case
port gate uses --mem48/--threads15 and six-case acceptedIB gate --mem48/--threads18
(with separate argument values). These are local arithmetic/acceptance/query
bindings, not full VM version/source reservation, all-consumer ACK, physical
CDC/admission or native cycle qualification.
