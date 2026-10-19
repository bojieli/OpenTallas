# Private native owner join core source

Source only; no compile, simulation, root binding, synthesis or timing verdict.
Base f6e4d6cac. The frozen allocation is exactly 162 bits: pending66,
active95 and sticky fault1. `join_core_state_census.json` derives packed
field widths from the emitted declarations. The only clocked assignments
are p_q, a_q and fault_q. Default ENABLE_NATIVE_OWNER_JOIN=0.

Every input is in the explicitly common component clock. Reset is raw POR;
there are no clock-crossing, landing or transport registers in this file.
The actual production crossings, reset phase, latency, H and SRAM remain HOLD.
This is an isolated private component and changes no public source/default.

Issue reserves the descriptor owner/input token/position. Actual accepted
package and HC tuples supply token18/position18/generation2 only. The active
record inherits client/slot/descriptor generation from pending, never an
invented native transport field. The combinational current request tuple
must match before admission. Allocation consumes actual pre-edge TAG59/gen2;
its epoch may be zero. Same-edge HC/allocation is refused, as frozen.

TAG layout is {epoch16,stage6,input18,pos13,segment6}. Request requires stage0,
segment0 and zero position high bits. Terminal and POST require exact stage37
TAG and generation; POST carries no synthetic descriptor fields. Certificate,
event-copy and CQ-B keys are87 bits {client16,slot8,descgen2,terminalTAG59,gen2}
from the genuine immutable saved lineage. Returned next token is never
compared against the input token in the native key.

Raw completion matches the actual descriptor tuple to the already-bound
active record. It does not invent an epoch on raw completion. A real unready
raw completion matching pending is typed NO_NATIVE and clears pending without
constructing an active/native key. Cleanup allowance is always1 and cannot be
masked by faults or certification. A genuine matching prompt-retirement hook
drains non-CQ reports after raw completion (or on its actual edge); generated reports require matching real event-copy/CQ-B.
A matching POST and real report drain are both required before freeing active.
A pending next issue may coexist with active; no same-edge slot reuse is added.

Duplicate, missing-phase and wrong-owner/key events latch fault until raw POR.
Fault blocks new admission and certification success, while independently
matching raw cleanup and accepted report/POST drain remain available. No timeout,
health waiter, anonymous settling interval or synthetic healthy vector exists.
Parent must connect certificate_health_bound only at a genuine bound cutoff.

The parent bench must exercise actual source reachability, all phase/cause
controls and first authoritative edges. Source declaration census is not an
HDL correctness or physical closure claim.
