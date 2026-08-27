# Clock, reset, and power-intent specification

**Document:** SPEC-CRP 1.0

This is logical power intent suitable for RTL, assertions, CDC/RDC inventory, and
an eventual UPF implementation. It is not a target-node voltage, IR-drop, PLL, or
power-switch signoff record.

## CRP-1 Principles

Clock, reset, isolation, retention, and service admission are controlled
independently. Clock gating is not reset. Reset is not error recovery. Power-state
transition is not complete until interfaces, credits, macro readiness, and
architectural state satisfy the target state's invariant.

The public reference contains no silent power gating or retention inference. It
models domain power-good and isolation and verifies their sequencing; target power
switches, level shifters, retention cells, PLLs, and sensors are external macros.

## CRP-2 Clock domains and crossings

### CRP-2.1 Domain inventory

| Domain | Nominal/product hypothesis | Ownership | Reset |
|---|---:|---|---|
| `aon_cfg_clk` | 250 MHz | CSRs, boot, RAS log, telemetry, power FSM, JTAG bridge | `aon_rst_n` |
| `core_clk` | 1.0 GHz; legal 0.8–1.2 GHz operating hypotheses | stage controller, tiles, static NoC, service counters | `core_rst_n` |
| `hbm_clk[i]` | macro defined | one logical HBM controller/channel wrapper | `hbm_rst_n[i]` |
| `stage_link_clk[i]` | PHY defined | one neighbor stage-link wrapper | `link_rst_n[i]` |
| `test_clk` | test-flow defined | scan shift/capture and BIST override | `test_rst_n` |

Clock frequency numbers are assumed budgets. Functional behavior is cycle based
and remains valid across legal ratios and phase drift. `aon_cfg_clk` is the only
clock required in STANDBY/SAFE diagnostics. Core, HBM, and link clocks may stop only
after their local stop acknowledgements and isolation conditions are satisfied.

### CRP-2.2 Crossing inventory

`clock_reset_crossings.json` is the machine-readable instance and stage-top-port
inventory. Its 12 public stage crossings are normative for the checked RTL and
must remain one-to-one with the table below; adding a clock, reset, top-level port,
or crossing without updating that record fails the static campaign.

| Source → destination | Data | Mechanism | Reset/recovery rule |
|---|---|---|---|
| AON → core | accepted host commands | dual-clock asynchronous FIFO | either reset flushes both pointer domains; interfaces remain closed until a two-domain reset rendezvous |
| core → AON | command responses | dual-clock asynchronous FIFO | response reservation prevents loss; either reset flushes both pointer domains and fatal reset cause is logged in AON |
| AON → core | schedule shadow write or commit, including schedule ID | `schedule_cdc`, closed-loop four-phase mailbox with stable payload and typed response | source holds payload through returned acknowledgement; destination reset replays only into schedule state sharing that reset |
| core → AON | coherent status/counter/first-error snapshot | `status_snapshot_cdc`, 512-bit request/acknowledge snapshot mailbox | one complete core image is latched and held through acknowledgement; a changed live image schedules a follow-up transfer |
| AON → core | ERROR_STATUS RW1C first-error clear | `ras_clear_cdc`, closed-loop one-bit mailbox | requests may coalesce because clear is idempotent; no asynchronous pulse is sampled in core |
| core → AON | telemetry/fatal events | asynchronous FIFO, depth at least 16 | exhaustion blocks admission; AON survives core reset |
| AON → core | service-enable and power-safe levels | independent `ot_sync_bits` instances | destination defaults to admission disabled/reset-interlocked state |
| core → AON | RAS SAFE request | `ot_sync_bits` sticky-level synchronizer | source holds the request until reset/requalification |
| core → AON | stage idle and schedule valid | `ot_sync_level` with three-cycle destination qualification | destination reset values are explicitly idle and invalid, respectively |
| AON/external → core | qualified core reset | `ot_reset_sync` | assertion is asynchronous; release takes at least two qualified `core_clk` edges |
| core → HBM[i] | `IF-HBM-REQ` | asynchronous FIFO | reset withdraws tags/credits and requires channel resync |
| HBM[i] → core | `IF-HBM-RSP` | asynchronous FIFO | late pre-reset generations are discarded and counted |
| core → link[i] | stage packets/control | asynchronous packet FIFO | reset withdraws packet credit and forces link handshake |
| link[i] → core | received packets/acknowledgements | asynchronous packet FIFO | generation/epoch prevents duplicate commit |
| AON/sensor → core | power-good, throttle, fatal alarm | filtered level plus two-flop synchronizer | assertion is fail-safe; deassertion requires AON acknowledgement |
| core → AON | quiescent, clock-stop acknowledgement | two-flop synchronized levels with stable-state qualification | must be stable three destination cycles |

No multi-bit bus is sampled through independent bit synchronizers. Gray pointers
are used only inside reviewed asynchronous FIFOs. A synchronized status that fans
into reconvergent logic is latched once in the destination domain before use.

The public-reference asynchronous FIFO couples assertion of the two interface
resets inside the wrapper: assertion of either reset asynchronously flushes both
pointer domains, while release is synchronized independently to each local clock.
Each side then advertises an online generation and keeps `ready`/`valid` closed
until the remote online indication has traversed two synchronizer stages. This is
the executable public-tool realization of "either reset flushes"; a target macro
may instead exchange explicit monotonically protected reset generations if it
preserves the same externally visible flush and rendezvous behavior.

The public-reference mailbox uses request/acknowledge levels rather than an
open-loop pulse. Request payload and response payload are each held stable while
their associated level crosses two synchronizer stages. Source and destination
online levels prevent a reset value from being mistaken for a transaction. A
destination reset while a request is outstanding may replay that request after
the rendezvous, so the mailbox may drive only destination state that shares the
destination reset or an explicitly idempotent operation. A source reset cancels
its local completion obligation; warm reset therefore quiesces mailbox traffic
before reset, as required by CRP-3.3.

The 512-bit diagnostic snapshot is the only path by which changing core-domain
counters, completion metadata, schedule identity, session generation/poison,
credit summary, or first-error state reach AON CSRs. AON never samples those
multi-bit buses directly. ERROR_STATUS clearing travels in the reverse direction
through its own acknowledged mailbox. CSR schedule/repair window outputs and
upper boot-control requests remain AON-domain platform integration boundaries;
they do not create a crossing until the platform owner consumes them.

## CRP-3 Reset architecture

### CRP-3.1 Reset domains

External `por_n` asserts all resets asynchronously. Each domain has a reset
synchronizer that deasserts only on its local free-running qualified clock after
power-good/clock-stable. Reset synchronizers are excluded from ordinary scan only
with dedicated structural review and test controls.

Architectural reset values include:

- every output valid and interrupt low;
- service/admission disabled and all credits zero until discovered;
- active schedule bank zero, epoch zero, slot zero, schedule invalid;
- session/transaction valid bits zero;
- error mask zero, sticky errors and first-error empty except retained reset cause;
- power FSM STANDBY when AON power is good;
- repair and capacity invalid until loaded/checked;
- test mode follows sampled straps and cannot be entered from an untrusted glitch.

Payload flops on invalid interfaces need not reset unless required for security or
X-propagation containment; verification must not depend on their value.

### CRP-3.2 Power-on sequence

1. `por_n` low holds all domains reset and interface isolation asserted.
2. AON power-good and clock-stable permit synchronous `aon_rst_n` deassertion.
3. AON samples stable straps/device identity, records reset cause, and remains
   STANDBY with service disabled.
4. Requested core/HBM/link clocks and power-good qualify independently; each local
   reset deasserts synchronously.
5. CDC wrappers flush or exchange reset generations and complete their two-domain
   online rendezvous; no interface advertises ready/valid and no credit exists
   before both sides agree.
6. Boot firmware loads repair/schedule shadow data and runs mandatory BIST.
7. Hardware publishes degraded capacities and identities, commits a checked epoch,
   enters IDLE, then accepts an explicit service-enable transition to ACTIVE.

A failed step enters diagnostic SAFE. Firmware cannot bypass identity, repair,
schedule, or mandatory BIST qualification with an ordinary CSR write.

### CRP-3.3 Warm reset and local reset

Warm reset is a transaction, not an asynchronous pulse. AON requests quiesce,
core stops admission and drains, links/HBM acknowledge idle, and all accepted host
commands retire. On bounded timeout, core poison-aborts remaining work and logs the
affected sessions. AON then asserts core/HBM/link resets, preserves AON error/reset
cause and immutable identity, and repeats boot qualification.

A local HBM/link reset does not reset the entire stage immediately. It withdraws
the affected resource's credits, poisons dependent transactions, runs local
resynchronization/BIST, and publishes reduced or restored capability. Escalation to
SAFE occurs when required image capacity/connectivity cannot be retained.

Asynchronous fatal reset assertion is reserved for electrical safety outside the
digital protocol. When asserted, state consistency is not promised; retained AON
logic reports a catastrophic reset cause after recovery.

## CRP-4 Power states and gating

### CRP-4.1 State invariants

| State | AON | Core | HBM/link | Admission | Isolation |
|---|---|---|---|---|---|
| OFF | off except physical POR | off | off | no | all asserted |
| STANDBY | on | reset/off | reset/off | no | core/HBM/link asserted |
| IDLE | on | qualified, mostly clock-gated | ready as required | no | service paths released after checks |
| ACTIVE | on | running/on-demand gated | active | yes | released |
| THROTTLED | on | running at lower enable/frequency | active or bandwidth-limited | yes if credits permit | released |
| SAFE | on | quiesced/reset or diagnostic clock only | isolated except diagnostics | no | service outputs asserted |

OFF is a system/package state. The synthesizable FSM represents its entry/exit
requests and begins observable operation in STANDBY after AON reset.

### CRP-4.2 Legal transitions

```text
OFF → STANDBY → IDLE ↔ ACTIVE ↔ THROTTLED
                  ↘      ↓          ↓
                    SAFE ←───────────┘
SAFE → STANDBY only through acknowledged reset/requalification
IDLE → STANDBY only after HBM/link/core stop acknowledgements
STANDBY → OFF only after external power-controller acknowledgement
```

ACTIVE to IDLE requires quiesce. ACTIVE to THROTTLED may occur at a certified slot
boundary and preserves all in-flight state. Any state enters SAFE on uncontained
fatal integrity, clock, power, sensor, thermal, repair, or watchdog error. Transition
guards are duplicated/parity protected and formally checked for illegal outputs.

### CRP-4.3 Clock gating

Clock gates use integrated-clock-gate semantics: enable is captured while source
clock is low; test enable forces clocks in scan/capture. Local gating conditions are
registered in the source domain. A pipeline group gates valid, tag, data, poison,
CRC/ECC state, and associated counters together. No combinational data value drives
a clock pin.

The core clock may be gated when no admitted transaction, schedule commit, BIST,
counter snapshot, or CDC work is pending. Static NoC slot state gates only when the
whole service fabric is quiescent; a partially active schedule epoch never pauses
one switch independently.

The public proxy emits explicit clock-enable logic by default and can map it to
technology gates during synthesis. This avoids relying on simulator behavior of a
generated clock.

## CRP-5 Throttle, thermal, and safe shutdown

### CRP-5.1 Throttle protocol

Thermal/power management requests one of discrete service ratios expressed as a
core clock-frequency state or globally coherent cycle enable. The request crosses
into core, waits for a static-NoC slot boundary, captures the new state, and
acknowledges. HBM/link credits naturally reflect any changed service rate.

No local tile may throttle independently during deterministic service. If a local
sensor requires urgent action, the whole stage transitions to THROTTLED or SAFE.
Performance counters distinguish commanded throttle, credit stall, clock-off,
and thermal emergency.

### CRP-5.2 Limits and SAFE

The product hypothesis budgets 15 kW operating and 20 kW cooling limit per stage;
these are assumed, not sensor trip settings. Target trip points and hysteresis come
from qualified package/silicon data. Until then, the public reference uses normalized
warning and fatal threshold inputs with programmable test values.

Warning requests THROTTLED. Fatal, invalid/stuck sensor, lost power-good, clock
monitor failure, or inability to throttle within the watchdog bound stops admission,
poison-aborts if time permits, asserts service isolation, records first error, and
enters SAFE. SAFE diagnostics run only on AON and explicitly qualified local test
clocks. Recovery requires reset and full requalification.

## CRP-6 CDC/RDC and power-intent closure

### CRP-6.1 Required checks

Before RTL verification closure:

- every clock and reset appears in a machine-readable inventory and generated-clock
  relationship is constrained;
- every crossing maps to one row of CRP-2.2 or an approved change;
- async FIFO pointer, reset-generation, overflow, underflow, and ordering assertions
  pass across randomized independent clocks/resets;
- handshake payload stability and acknowledgement progress are formally checked;
- synchronizer attributes and reconvergence points pass structural review;
- reset assertion/deassertion and reset-domain crossings are exercised at every
  pipeline and protocol phase;
- isolation is asserted before modeled power loss and released only after reset/
  readiness;
- clock-gate enables are glitch-free and forced open in test;
- public-tool CDC/RDC findings are zero or individually owned and documented.

Commercial target-qualified CDC/RDC and UPF checks remain mandatory after PDK/IP
integration. Public structural checks are methodology evidence, not signoff.
