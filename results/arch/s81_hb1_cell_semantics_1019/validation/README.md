# HB1 cell functional semantics validation

The 107974d0d Liberty-driven procedural projection is REJECTED for general
four-state use. Its binary tuple-transition test also fails. The replacement
`udp_functional_projection.v` passes the bounded cell-semantic checks below;
coordinator review remains necessary before the full mapped-graph miter.
No production RTL, synthesis, placement, routing, timing or hardware reset
contract changes are included.

The replacement copies the exact 39 used combinational module implementations
from the frozen official Verilog, including their primitive buffers (which map
Z input to X, unlike a continuous assignment). The two sequential wrappers use
the exact official Function inverters, error UDPs and state UDP tables. Actual
pins replace delayed_* timing-check output wires. The original uninitialized
`reg notifier` is retained; no timing checks drive it. Original combinational
zero-delay specify blocks remain. No SDF, timing-violation/notifier-event
or timing-check-output equivalence is claimed.

Default `INIT=-1` leaves storage uninitialized. Bench-only INIT=0/1 selects a
copied state UDP whose sole table-independent addition is `initial q=0/1`.
Error UDPs remain unchanged and uninitialized. Initialization occurs at time
zero, before asynchronous controls and gates settle, and is never reapplied.
Consequently, a seed need not survive initial unknown input/gate events:
32 of the tested deasserted-reset startup combinations become X in both the
replacement and independently copied seeded official UDP. Asserted clear or
preset takes precedence over the seed. The mapped implementation graph has no
new initialization, reset or validity mechanism.

Fleet run06 (ot-agidock128, unit oth-ubuntu-1998904-1792447482) completed exit0:

- 506 exhaustive binary combinational tuples across 39 used masters.
- 2,566 sequential checkpoints, including every pair of the 16 binary
  CLK/D/RESETN/SETN tuples from both seeded binary states and explicit SETN
  release under asserted RESETN at both clock levels.
- 262,144 sequential checkpoints spanning all pairs of 256 four-state input
  tuples from both binary seed states, including uncertain clocks, X/Z data,
  unknown/forbidden async combinations, hold, assertion and release.
- 15,234 exhaustive four-state combinational tuples, zero differences.
- Causal data-polarity, asynchronous-priority and AND-to-NAND mutants each
  failed with committed mismatch witnesses.

The binary bench prints `seq_checks=2564`; that historical display literal is
an off-by-two reporting typo. Its measured total is 3072, comprising 506
combinational and 2566 sequential checks. Source and raw output are retained.

Fleet run07 (same host, unit oth-ubuntu-1999556-1792447545) adds INIT coverage:
512 ASR and 32 HQ startup cases compare against separately copied original
seeded UDPs, covering all four-state controls/data/clock and both initial
states. Checks occur at 0.3 ns after initialization, before a clock sequence.
All comparisons and explicit asserted-async override checks pass, exit0.
The added copyright/comment header changes no simulated logic; immutable
run06/07 bundles preserve the exact executed pre-header source bytes.

All work ran through unpinned ot-run, with 4 GB RAM, two threads and 2 GB disk
capacity reservation, not a process address-space or runtime limit. Host
memory/disk admission, actual tools and SHA256s are in fleet logs. Icarus 12.0
executes these UDP semantics probes; this is not the closure-daemon Verilator
behavioral qualification. The final INIT probe used 14,008 KiB peak vvp RSS
and 0.08 seconds. No heavy local execution occurred.

## Immutable failure history and reproduction

`run01` preserves the first missed-capture startup witness. `run02` also
preserves a four-state bench name-collision compile failure. `run03` preserves
the procedural model's 193,486 mismatches / 262,144 checkpoints and the first
seeded UDP syntax failure (initial statement before input declarations).
`run04` preserves the initial seed-survival expectation failure. `run05`
preserves the same failure after retaining notifier and seven combinational
buffer-Z differences; this showed that attributing seed loss solely to a
constant notifier event was incomplete. Initial gate/input delta events also
matter. No failed verdict was replaced with a PASS.

Every numbered immutable tar contains that run's exact input source, runner,
compile logs and simulation logs. Generated vvp executables are omitted.
To reproduce, extract a selected bundle into a NEW empty fleet directory and
run its `validation/runNN.sh` through unpinned ot-run. Each runner refuses an
existing run output directory. Run06 is the final complete semantic suite;
run07 adds HQ/ASR arbitrary-initial-state coverage. Expected-failure cases in
run06 remain explicit. The original 107974 source remains byte-identical.
`check_projection.py` records the original bench-generation step;
`make_udp_projection.py` emits the replacement from the frozen official files.
The committed final bench snapshots and immutable bundles are authoritative.
