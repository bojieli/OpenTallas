# RAS, repair, diagnostics, and DFT specification

**Document:** SPEC-RAS 1.0

## RAS-1 Fault model and policy

OpenTallas assumes that an immutable image, wafer-scale service fabric, large ROM
population, HBM interfaces, and repaired resources will experience manufacturing
defects and run-time faults. Detection without containment is insufficient. Every
planned fault maps to correction, retry, transaction poison/abort, resource
quarantine/degradation, SAFE shutdown, or an explicit external signoff gap.

Fault classes are:

| Class | Examples | Required disposition |
|---|---|---|
| transient data | SRAM bit upset, link/flit corruption, synchronized control upset | correct or detect; retry/abort; no silent commit |
| permanent data | ROM row/column defect, stuck SRAM bit, HBM lane failure | repair/quarantine, BIST, reduced capability or unavailable |
| control/protocol | illegal state, lost credit, duplicate response, schedule mismatch | detect, contain transaction, watchdog, SAFE if conservation lost |
| timing/clock/reset | missing clock, unsafe reset, CDC corruption, throttle incoherence | fail-safe alarm, isolation, SAFE, requalification |
| power/thermal | over-limit, sensor invalid, power-good loss | throttle or SAFE; product trip values require characterization |
| configuration/identity | wrong image, bad schedule/repair CRC, stale epoch | reject before service or abort affected work |
| latent design defect | unverified corner, coverage hole, waiver escape | bug process; never reclassified as random hardware failure |

## RAS-2 Data integrity

### RAS-2.1 End-to-end CRC

Host commands/responses, CSR records, NoC flits, tile route/activation/results, HBM
wrapper responses, and telemetry use CRC16-CCITT-FALSE exactly as ICD-1.3. Stage
packets additionally use CRC32C over retained packet bytes. CRC state is tagged and
cannot cross records.

CRC failure is detected before a state commit. A link packet may retry; on-chip
static service traffic does not slip/retry in a later slot because that would break
schedule determinism, so it poisons and drains. Error injection must flip every
covered field class, CRC bit, burst position, and terminal marker.

### RAS-2.2 SRAM/FIFO ECC and control protection

Architectural SRAM/FIFO data uses SECDED per 64 data bits, with eight check bits or
a macro code no weaker under the declared fault model. Single-bit correction returns
corrected data, increments a saturating location/class counter, and schedules scrub.
Double-bit detection returns no data and poisons all records sharing the protected
word. Syndrome, address, ownership, epoch, and transaction are logged.

Small reconstructible datapaths may use parity and replay/abort. Commit pointers,
credit state, power-state guards, schedule bank/epoch, repair generation, and
identity-critical control use ECC, duplication-plus-compare, or fail-safe parity.
The implementation inventory records the selected protection for every state array
and high-consequence control register.

### RAS-2.3 ROM integrity

ROM logical content is divided into 512-byte data blocks. Each block has immutable
CRC32C stored in a separately addressed protected region; data and scale blocks are
covered. The streaming datapath checks a block before its partial result can commit.
A CRC mismatch, macro uncorrectable syndrome, address/region violation, or scale
mismatch poisons the transaction and increments a per-macro counter.

Boot ROM-BIST reads every logical address after repair, checks every block CRC, and
accumulates a 64-bit MISR plus complete image SHA-256 comparison performed by the
boot/host validation flow. Runtime background signature scans are allowed only in
quiescent reserved slots and may not contend invisibly with service counters.

CRC protects against random corruption and address faults within its diagnostic
coverage; it is not a substitute for characterized sense margin, retention,
coupling, aging, or manufacturing test.

## RAS-3 HBM and external macro errors

The HBM wrapper translates vendor status into none, corrected, uncorrectable,
poison, timeout, or protocol. Corrected data is accepted only when end-to-end CRC
also passes and policy permits. Uncorrectable data poisons the transaction. Channel
loss withdraws credit, drains tags, reruns calibration/BIST, and republishes local
capacity before service resumes.

PLL, link PHY, sensor, eFuse/OTP, and other macro wrappers expose `ready`, `corrected`,
`uncorrectable`, `fatal`, `BIST_done/pass`, and diagnostic syndrome classes as
applicable. Unknown/reserved macro status is fatal. Tying an error pin inactive in
a synthesis configuration requires an explicit waiver proving the macro lacks that
failure mode.

## RAS-4 Error reporting and containment

### RAS-4.1 Severity and capture

Severity is informational, correctable, uncorrectable, or fatal:

- informational changes no result and requires no recovery;
- correctable produces the specified result after correction/retry and remains
  visible in counters/logs;
- uncorrectable invalidates at least one transaction/session but may leave unrelated
  service available;
- fatal means architectural conservation, identity, power/clock safety, or required
  capacity/connectivity cannot be trusted and forces SAFE.

First-error capture is sticky and atomic. It stores severity, stable source ID,
epoch, transaction, 48-bit AON timestamp, syndrome class, and a pointer to extended
diagnostics. Later errors update counters and recent-error FIFO but never overwrite
first error. AON retains first/reset cause across core warm reset.

### RAS-4.2 Transaction containment

Poison is monotonic. Before COMMIT, any uncorrectable component marks the whole
homogeneous command batch poisoned. Already launched NoC/HBM/link/tile work drains
under its original tags; results are discarded; prepared state is invalidated;
credits return exactly once; and one ordered terminal response is emitted.

An error discovered after a layer commit attaches to the next protected boundary.
If data that contributed to the committed state could be corrupt, the session is
marked poisoned and cannot continue until released/rebuilt. Unrelated sessions may
continue only when all shared credit, schedule, clock/power, and identity state
remain trustworthy. Otherwise escalation is fatal.

### RAS-4.3 Watchdogs and progress

Separate programmable watchdog classes cover command validation/reservation, HBM
tag completion, NoC epoch/collective completion, tile result, stage packet retry,
quiesce, BIST, schedule commit, and repair commit. Defaults come from certified
worst-case cycles plus margin; zero disables only diagnostic non-safety watchdogs.

First expiration records timeout and starts poison drain. Drain has an independent
watchdog. Failure to recover credits, reach quiescence, or resynchronize external
resources enters SAFE. Watchdog counters use a clock source appropriate to the
resource so ordinary service clock gating cannot suppress detection.

## RAS-5 Identity, authenticity boundary, and debug

### RAS-5.1 Image identity

The image manifest SHA-256 covers pinned source revisions and inventory hashes,
canonical tensor/scale layout, numeric profile, partitions, expected ROM block
CRCs/MISR, schedule certificate hashes, ABI, compiler version, and repair-compatibility
policy. The mask-programmed stage exposes all 256 identity bits. Every stage in a
pipeline must match the deployment manifest and its declared stage index/partition.

SHA-256 provides collision-resistant identity/integrity binding in this public
flow. Authenticity, secure boot, key storage, anti-rollback, and manufacturing
chain of trust require a product security root and signed manifest outside this
baseline.

### RAS-5.2 Immutable weight boundary

No functional, repair, BIST, scan, JTAG, diagnostic, or macro wrapper interface can
write logical ROM data. Row/column repair changes address translation to preexisting
spare content personalized with the same logical bits. Test modes can select,
sense, compare, and signature data but not program it.

Behavioral models load initialization only at simulation elaboration. A synthesis
build fails if it sees a weight write enable, writable inferred memory in the ROM
hierarchy, or a configuration bus connected to ROM data storage.

### RAS-5.3 Debug data boundary

Service CSRs expose identities, status, counters, errors, BIST signatures, repair
metadata, schedule metadata, and loopback results. They do not expose arbitrary
activation, partial-sum, or KV payload. Intrusive scan/test observation requires
test mode, quiesced service, and the product test/security authorization boundary.
The public reference models the interlock but makes no anti-tamper claim.

## RAS-6 Repair and degradation

### RAS-6.1 ROM row/column repair

Each ROM macro wrapper exposes logical-to-physical row and column repair tables,
valid bits, CRC, and generation. Logical addresses remain stable. Entries must be
in range, injective within a repair class, target characterized spares, and never
map two live logical locations to one physical location. Active maps are immutable
until quiescent shadow commit.

The stage raw-capacity budget is 184 GB for 160 GB usable. This 13.04% reserve is
shared by row/column spares, fragmentation, integrity metadata, disabled tiles,
and service margin; it is not permission to consume each component's worst case
independently. Target macro spare counts and defect distributions require foundry
characterization. Compiler capacity uses the actual qualified map, not the nominal
reserve alone.

### RAS-6.2 Repair-map record

A repair-map record binds physical device identity, image identity, monotonic map
generation, macro row/column entries, disabled tile/link/lane set, expected
post-repair capacities/bandwidth, schedule compatibility hash, creator/tool version,
and CRC32C. Optional signatures belong to the later security architecture.

Hardware range/CRC checks every entry. Firmware independently checks injection,
capacity, schedule, and identity. A map cannot activate while service or BIST owns
the affected resource. Failed commit leaves the previous active map untouched.

### RAS-6.3 Tile and link quarantine

A permanent tile or link failure is removed from the service resource graph.
Interleaved logical shards are reassigned only when personalized spare copies and
remaining bandwidth/capacity support the manifest. A new schedule certificate
excludes quarantined resources. Dynamic adaptive routing is not a repair mechanism
for deterministic service.

Link lane sparing/retraining may remain inside a qualified PHY if it preserves the
logical packet interface and reports degraded rate. Otherwise the logical link is
withdrawn. A stage unable to reach all required endpoints or hold all image/state
regions is unavailable rather than silently incomplete.

### RAS-6.4 Capability publication

After repair/BIST, hardware publishes enabled tiles/links/HBM channels, usable ROM
and HBM bytes, schedule set, service bandwidth class, maximum resident sessions,
and fatal/degraded state. Admission uses these values. A nominal capability bit is
never retained merely for software compatibility after a resource loss.

Performance results label repaired configuration and map generation. Degradation
tests cover zero faults, each single fault class, clustered faults, reserve edge,
and repair exhaustion.

## RAS-7 Diagnostics and BIST

### RAS-7.1 Diagnostic functions

Non-destructive service diagnostics include heartbeat, clock/power/sensor monitors,
counter snapshots, first/recent error logs, CRC/ECC counters, active identity/epoch,
repair/capability map, and link state. Intrusive quiescent diagnostics include
NoC/tile loopback, selected known-answer numeric operations, memory march, ROM full
signature, and fault-injection hooks in DV/test hardware.

Every BIST has start, busy, done, pass/fail, timeout, signature, failing resource,
and clear semantics. Starting while an incompatible owner is active returns BUSY.
Aborting BIST leaves the resource unqualified until a complete pass.

### RAS-7.2 Boot and periodic BIST

Mandatory boot sequence:

1. control-register/parity self-check;
2. SRAM/FIFO March C- plus ECC syndrome injection where supported;
3. schedule/repair memory integrity and range check;
4. NoC local/mesh walking-one, walking-zero, CRC, lane, and static-loopback tests;
5. HBM calibration, vendor BIST/ECC, address aperture test, and wrapper loopback;
6. stage-link PRBS/loopback, packet CRC, retry, and credit test;
7. ROM address/wordline/mask/repair test, every block CRC32C, and full MISR;
8. representative numeric known-answer tests and end-to-end diagnostic transaction.

Periodic background tests are compiler-scheduled in reserved quiescent slots. ROM
signature and SRAM scrub intervals are product reliability inputs; public tests
exercise mechanisms without claiming a qualified interval.

## RAS-8 Design for test

### RAS-8.1 Scan domains

Scan partitions follow AON, core control, tile groups, NoC reticles, HBM wrappers,
stage-link wrappers, and DFT control. Functional CDC synchronizers are not chained
across unrelated scan clocks. Each partition has declared shift clock, capture
clock, reset/test override, isolation state, compression boundary, maximum chain
length, and power budget.

All synthesizable sequential state is scannable unless it is a synchronizer first
stage, analog/macro state, security-sensitive product state, or individually
waived. Exclusions have alternate structural/functional tests.

### RAS-8.2 At-speed and clock/reset test

The product design reserves on-chip clock-control hooks for launch/capture pulses
per functional domain, safe PLL bypass, clock-gate test enable, and reset override.
At-speed domains do not launch uncontrolled paths across asynchronous boundaries.
Reset trees, isolation controls, and clock-stop acknowledgements have dedicated
test observations and stuck-at checks.

The public proxy verifies logical controls and scan-friendly structure. It cannot
establish target clock-controller, compression, transition-fault, or power-aware
ATPG closure.

### RAS-8.3 Memory/ROM and link test access

SRAM wrappers expose MBIST ports separate from functional traffic. ROM wrappers
expose address, mask, sense/compare, repair select, expected CRC/signature, and
failing-block localization. HBM and link wrappers expose vendor BIST/loopback status
through stable instrument registers. BIST muxing is fail-safe: test mode blocks
functional issue and functional mode cannot select test write data.

### RAS-8.4 JTAG and instrument network

The product boundary reserves IEEE 1149.1-compatible IDCODE, BYPASS, SAMPLE/PRELOAD,
EXTEST where IO permits, and an IEEE 1687-compatible access path for BIST, repair,
monitors, and diagnostics. Unsupported or security-restricted instructions return
defined bypass behavior. JTAG reset cannot release functional service resets.

The public model implements IDCODE/BYPASS and instrument-register semantics; target
boundary cells, TAP timing, IJTAG retargeting, and secure test authorization remain
external integration work.

### RAS-8.5 Fault-coverage targets

Target-node goals are at least 99% stuck-at and 95% transition fault coverage after
reviewed untestable/excluded faults, plus macro-qualified memory/ROM/link coverage.
Coverage reports separate detected, possibly detected, untestable, tied, blocked,
and excluded. No public tool result is relabeled as target ATPG coverage when it
does not model target cells/macros.

### RAS-8.6 Wafer probe and production sequence

The product plan reserves per-reticle power isolation, scan/BIST access, identity,
repair load, clock/sensor monitors, and known-good-reticle results at wafer probe.
Probe sequence qualifies AON/control first, then local power/clock, ROM/SRAM, tile
numeric paths, local NoC, cross-reticle links, global fabric, and repair/degraded
capability. Package test repeats integrity/link/HBM/thermal paths and correlates
probe signatures.

Burn-in, voltage/temperature corners, defect screening, repair limits, known-good
reticle assembly, and final test time require foundry/OSAT data. The public
architecture reserves controls and data records but cannot qualify the flow.

## RAS-9 Verification and closure

### RAS-9.1 Fault campaign

The DV campaign injects, at minimum:

- every single-bit and representative double-/multi-bit protected-memory syndrome;
- CRC corruption in every record field class, data position, CRC bit, first/middle/
  last beat, and retransmission;
- ROM data, scale, address, mask, repair, block CRC, and macro syndrome faults;
- dropped, duplicate, late, reordered, wrong-tag, wrong-epoch, wrong-sequence, and
  early/late-terminal records;
- credit underflow/overflow attempts and schedule expected-valid violations;
- tile/link/HBM channel quarantine, clustered defects, reserve edge, and exhaustion;
- clock stop, reset at every protocol phase, sensor warning/fatal/invalid, and
  watchdog expiration;
- BIST pass, each fail class, timeout, abort, and ownership conflict.

For each planned site the campaign records activation, observation, classification,
latency, containment, recovery, final session state, credits, and expected telemetry.
Closure requires 100% activation and specified detection/containment for planned
sites, no silent state commit, and reviewed exclusions. Statistical random injection
supplements but does not replace deterministic site coverage.

The source-controlled public subset is enumerated in `fault_campaign.json`. Its 87
sites are required to appear exactly once in their declared timed benches and to pass
under both Icarus/vvp and the pinned public Verilator 5.050 source build. The campaign
records expected observation, containment, recovery, commands, tool/executable
hashes, source hashes, logs, and explicit external gates. This closes deterministic
logical behavior only for those sites. It does not qualify foundry macro ECC/BIST,
HBM or link PHYs, scan insertion/compression, ATPG, delay/bridging/open faults,
physical layout, manufacturing/yield, or target-node signoff.
