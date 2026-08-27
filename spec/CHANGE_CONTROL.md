# Specification change control

**Document:** SPEC-CC 1.0  
**Status:** frozen governance contract

## CC-1 Baseline ownership

The versioned specification package, machine-readable records, generated
traceability, analytical inputs, and RTL verification manifests are one controlled
baseline. A clean-tree check, reviewer identity, and commit hash accompany every
gate. The public reference has no tapeout authority.

## CC-2 Change classes and review

### CC-2.1 Requirement-first implementation

No implementation block is added or behaviorally changed without a requirement
allocation, interface/numeric contract, reference-model impact assessment,
verification entry, and owner. A change that affects observable records, ordering,
numeric bits, capacity, timing class, reset, error, or security boundary requires
specification review before RTL merge.

### CC-2.2 Traceability and compatibility

Every change updates requirement/architecture/implementation/verification links and
regenerates `TRACEABILITY.md` deterministically. A minor release may add previously
reserved fields/opcodes or capabilities without changing old meanings. A major
release is required for width, field meaning, ordering, numeric, reset, error,
security, or commit-semantics changes. The compatibility matrix names affected
firmware, compiler, manifests, tests, and model images.

### CC-2.3 Synthesis and release gate

The synthesis baseline is immutable after DV closure. Any RTL/spec change after
that point reopens affected static, formal, simulation, coverage, CDC/RDC, fault,
and equivalence checks; a PPA result is invalidated until rerun. Waivers never
silently carry across a major baseline.

## CC-3 Waivers, evidence, and release

### CC-3.1 Waiver record

Each waiver records ID, exact finding, scope, owner, risk, rationale, compensating
check, expiration/review date, affected requirements, and re-entry criterion. An
unowned or expired waiver fails the gate. External gaps (PDK, PHY, package, model
quality, commercial data) are tracked as blocked evidence, not waived into a pass.

### CC-3.2 Commit and push policy

Analytical, specification, RTL, verification, and synthesis gates are committed and
pushed separately at significant progress points. The release note names the
commit, generated artifacts, tests, open external gates, and next authorized phase.

### CC-3.3 Reproducible release

Two independent clean builds must agree on canonical generated outputs. Timestamps,
hostnames, absolute paths, credentials, and nondeterministic seeds are excluded
from image identity. Source artifacts and their hashes are retained even when a
large payload or licensed macro cannot be redistributed.

## CC-4 Public-reference implementation deltas

### CC-4.1 CDC/reset protocol clarification

The first CDC-closure implementation refines the abstract "acknowledged toggle"
wording into a closed-loop four-phase mailbox and defines the async-FIFO coupled
flush/online rendezvous. This does not change any architectural record encoding or
host ABI. It does make the local stage integration contract explicit by adding
write ready/ack/error and commit ready/error indications. Firmware and compiler
records are unaffected because they use the protected CSR/boot transaction layer;
stage RTL, reset/static checks, formal harnesses, and asynchronous-clock tests must
be regenerated together. Owner: digital control/CDC. Review gate: DV-RESET-001 and
DV-STATIC-001; re-entry is required after any reset or handshake change.

### CC-4.2 Static-closure interface refinement

The static-closure baseline consumes the existing host `schedule_id` field end to
end, rejects partial inactive schedule banks, carries session allocation generation
and complete command/service metadata to the abstract service boundary, and makes
session lookup/retire/abort ownership checks functional. Changing core diagnostic
state reaches AON only through a coherent 512-bit mailbox; RW1C clear uses a
separate lossless mailbox. Accepted CSR window/control requests that belong to the
platform boot/repair/DFT owner are explicit AON top-level sidebands rather than
unconnected internal pins. These changes do not alter frozen record bit positions,
but they do strengthen previously specified legality, ownership, and CDC behavior.
Owner: digital control/RAS/DV. Review gates: DV-CMD-001/002, DV-SESSION-001,
DV-NOC-001, DV-RAS-001, DV-RESET-001, and DV-STATIC-001. Any later edit to these
paths reopens strict lint, static CDC/RDC, formal, both simulators, fault injection,
and source-hash consistency.

### CC-4.3 Directed fault-containment baseline

The first source-controlled fault baseline adds 87 deterministic logical sites for
route/ROM/HBM, stage links, RAS/BIST/DFT, power/schedule/session control, and common
stage abort cleanup. The HBM implementation now decodes the frozen 16-bit minus-one
burst field into a 17-bit count and composes concurrent admit/complete reservation
updates; this corrects implementation behavior without changing the ICD field width
or meaning. ROM injection distinguishes corrected single-bit data from poisoned
multi-bit data, framing faults poison the current HBM completion, stage-link CRC/
sequence state recovers packet-locally, RAS counters saturate, and all post-lookup
stage failures use abort cleanup. Owner: digital control/RAS/DV. Review gates:
DV-HBM-001, DV-LINK-001, DV-RAS-001/002, DV-REPAIR-001, DV-DFT-001,
DV-POWER-001, DV-SESSION-001, DV-STAGE-001, and DV-STATIC-001. Any affected edit
reopens both timed simulators, strict warnings, formal/static checks, and the exact
site/source manifest.

### CC-4.4 Source-coverage closure and arithmetic integrity baseline

The first canonical source-coverage baseline adds a machine-readable plan, an exact
waiver ledger, five coverage-focused benches, and four directed-fault supplements.
Nine cases must agree under Icarus/vvp and pinned Verilator 5.050; native source
points are hierarchy/instance deduplicated and unexpected warnings are fatal. The
closed baseline records 96.512 percent line, 94.662 percent branch, 85.210 percent
toggle, 89/89 mandatory bins, 28/28 FSM-state bins, and zero exclusions.

Coverage-driven checking corrected implementation defects without changing a frozen
record encoding or host ABI: CRC32C retains unfinalized state between beats; signed
decode/dot/reduction widths are explicit; reduction accumulation and overflow are
widened; a completed reduction is emitted once; group allocation captures its first
source atomically instead of racing whole-vector and bit-select updates; a zero ROM
injection mask is a no-op; and non-default layer bounds use typed widths. Owner:
digital datapath/control/DV. Review gates: DV-NUM-001/002, DV-TILE-003/004,
DV-RAS-001, DV-STAGE-001, DV-COVERAGE-001, and DV-STATIC-001. Any affected edit
reopens both simulators, strict static checks, formal properties, fault injection,
and the complete source-coverage merge before synthesis evidence remains valid.
