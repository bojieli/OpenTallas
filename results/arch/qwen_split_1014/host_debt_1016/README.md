Actual exceptional HOST debt and native admission candidates, 2026-10-16.

The static-port proof instantiates the real four-entry landing/host queues,
64-entry physical-WDONE owner FIFO, and real credit arbitration. Six accepted
requests emit six actual controller-face descriptors; five write ACKs and one
read payload retire independently. Removing owner debt fails with one write
outstanding; removing read debt fails after read WDONE but before payload.

The admission proof instantiates the real packet-class receiver and actual
4 HOST / 16 ING deferred queues. During reservation all twenty data words stay
stored, CTRL traffic remains live, and release emits exact ordered data against
the original capacity promises. Invalid ownership remains locked. A real
reservation-bypass mutant leaks a word and fails the independent scoreboard.

Separately named source variants preserve old closed module bodies. The actual
root_admission -> rank -> control packet -> packet bundle -> RX admission chain
is wired, not an interface suggestion. The old misleading host_drained_local
name is host_interface_idle in this variant and cannot stand in for debt.

Each per-PC station/queue/boot quiet export costs one source clock observation
edge. qkd_host_native_quiet uses two capture flops, one PC reduction edge, one
8-PC group reduction edge and one root edge: five ownership-clock edges from
the quiet source pins. The ownership calendar then adds its actual captured-pin
edge before the fixed check. Physical relays/skew and admission-to-last-launch
latency remain compiler inputs. These are observations only; failed fixed-cycle
entry faults instead of waiting. No native scheduling uses queue credits.

Six upstream source pins are ingress16 queue quiet (queue clock), QM host quiet,
QM ingest quiet, QM core quiet, dispatch quiet, and commit-order quiet. They
observe actual queues, engine busy, Gray FIFO status and credit/owner debt.
Deferred RX words have not entered those paths and intentionally do not prevent
native reservation. Admission launch quiet is an additional separate input.

Scope: component tests and full-source lint only. No full native ownership
composition, all-clock CDC debt proof, new physical kits, clock insertion or
pin-placement grants are claimed. Boot/station/reduction and upstream debt
integration still require a source-pinned composition bench and mutants.
