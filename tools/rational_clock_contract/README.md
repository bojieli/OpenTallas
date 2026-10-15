# QCOLL rational clock prototype v1

This directory is isolated from `ref_tile`, `pre_route_gate`, clock-entry
constraints and the running daemon. It changes no production clock support.
The model pins three actual RTL sources from main a7faf16ba. Any source change
invalidates its contract. The existing 108-root production boundary contains
five gearbox roots: one core, one FDI, and three separately delivered RX roots.

## Source calendar and costs

Use C(n)=n*2500/3 ps and F(n)=delta+n*1000 ps. `delta` is the difference between
first active edges after the common reset release, conservatively within
[-2500/3,+2500/3] ps. This is a REQUIRED ASSUMPTION, not physical PLL evidence.

For block b and word j=0..5, core writes TX bank b%2 at C(6b+j).
FDI consumes beats k=0..3 at F(5+5b+k); beat 4 is reserved idle.
The selected external four-FDI-edge PHY model produces RX bank b%3 captures
at F(10+5b+k). Core outputs at C(24+6b+j). The actual codec producer adds one
edge, giving PU25. Six 598-bit words are packed into 3588 bits, split across
three 1043-bit beats and a final 459-bit beat with 584 zero padding bits.
Bank addresses and enable calendars advance unconditionally, including invalid
frames; validity and padding faults cannot reschedule execution.

The exact per-bit affine model gives conservative minimum stable guards:

| Boundary | Write to read | Read to next overwrite |
|---|---:|---:|
| TX bank / FDI output register | 2000 ps | 4000 ps |
| RX bank / core output register | 9000 ps | 2000 ps |

These are LOGICAL ENABLED WINDOWS before CQ, setup/hold, data RC, uncertainty,
and root phase/insertion errors. They are NOT timing exceptions. The analytic
mutant that moves consumption three core edges early fails the window proof.
It is a model mutant; actual RTL mutants remain in QCOLL's separate source proof.

Storage is 2*3588 TX + 3*3588 RX = 17940 explicit payload DFF bits, before output,
phase-counter and fault registers. No new SRAM/FIFO/credit logic is proposed.
Declared-register inventory (before synthesis optimization): core root 7789 bits,
FDI root 1058 bits, each RX root 3588 bits, total 19611. Actual mapped census,
clock buffers, clock wiring, data muxes and tile shape remain to be measured.
Payload is 3588 bits/5 ns=717.6 Gbps. Physical 1043-bit FDI capacity is
1043 Gbps; four active beats per five give 834.4 Gbps available active-beat
capacity. Capacity is not a claim of measured physical signal integrity.

## Real STA probe and its limits

`python3 tools/rational_clock_contract/test_model.py` checks source hash,
ratio, phase, no-exception policy and enabled-window mutants.
`python3 tools/rational_clock_contract/probe.py OUTPUT_DIRECTORY` runs actual
ASAP7 TT and FF Liberty in OpenROAD, eleven first-edge offsets from -833.333 to
+833.333 ps at 166.667 ps increments. It uses a synthetic common 200 MHz source,
1.2 GHz / 1 GHz generated clocks, and ordinary max AND min paths in both rational
crossing directions and FDI-to-RX control. There are no false paths, asynchronous
clock groups or multicycle exceptions. Artificial buffer branches represent the
clock source only in this fixture, not a realizable frequency multiplier.
The fixture does not implement the actual full gearbox mux/control datapath.
It establishes engine edge visibility, not physical timing closure.

Clock enable behavior is implemented as data muxes in ordinary synthesis; STA
cannot infer the several-ns enabled-bank windows from this source automatically.
Thus ordinary rational crossings can still be limited by a 166.667 ps nearest
edge pair (or less for a different phase), and coincident-edge hold must close.
A positive model window cannot justify suppressing the actual timing checks.
The physical phase interval must be narrowed to actual PLL/reset delivery;
continuous phase uncertainty approaching a relative edge coincidence cannot be
qualified by eleven sampled STA phases.

## Required production API / integration contract

Use a NEW explicit versioned profile; never silently extend the existing
same-frequency `multiple_cts_roots` meaning. Each root needs its own frequency,
phase, clock sink census, actual min/max insertion and spread, launch/capture
pin budgets and station/root identity. The scheduler needs the reset-edge
calendar and actual fixed latency. Die delivery must compensate the measured
root insertion (phi minus R) using that root's own clock period and station phase.
Shared input ownership must be a LIST of capture roots, not one root per input:
`shared_rx` feeds all three RX data banks plus FDI-domain padding fault checks.
Each root gets a separate real wire/launch/capture budget; `shared_rx_valid`
feeds the FDI-domain fault checker. fdi_ck controls feed fdi_rx_ck bank enables
and indices and require real ordinary same-phase setup and hold proof.

Required before production support: actual common-PLL and reset/phase source;
actual source-pin-to-clock ownership; mapped roots; every related crossing max
and min timing; shared-input multi-root constraints without overwrite; formal
CTS and routed TT setup/FF hold/DRC; physical phi-R/station binding; actual
full-calendar token/collective proof. No physical leaf pin file/home currently
exists. No PLL licence or physical phase guarantee is assumed. All release
qualification remains UNQUALIFIED.

The prototype uses this OpenROAD build's `-scenes TC` / `-scenes BC` option on
both `find_timing_paths` and `report_checks`. Merely calling `set_scene` still
queries both scenes in this build. Generated-clock periods are lazy: report
clock properties (or otherwise update generated clocks) before checking their
periods; the direct clock object's period is converted with `sta::time_sta_ui`.
A pre-update generated period can be zero and is not valid frequency evidence.
The first diagnostic attempts and their errors are retained under
`/home/ubuntu/artifacts/rational-clock-contract-1015/`; the final committed
probe output is the explicit-scene, period-validated, shared-input variant.
