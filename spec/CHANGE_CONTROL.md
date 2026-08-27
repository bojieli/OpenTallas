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
