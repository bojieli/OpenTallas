# S81 G8 binding repair (2026-10-21)

This is diagnostic die integration, not physical closure. The qualified 241-stage
map remains a capacity/inventory binding. Calendar 6f8bbf5c4 is held invalid after
a same-user xL0/partialL0 overlap finding; this packet claims no old calendar rates.

## Terminal G7 evidence

`g7_port_bind.json` is the original immutable ep5 report from
`claude-s81-die72-g7-1021/die72-g7/bind/bind/port_bind.json` (run46e46e17b).
G7 terminated BIND_RC1 at09:09 PT. All unresolved child, width, unbound, input,
multi-driver and undriven counts were zero. Open xo/xok ports were aggregated by
frame master; the master's total instance count is not the count of open instances.
Unread bits were16 unbuilt slice xc fanout words (17664bits) and14 reset leaves.

## Changes

The three non-mab MU72 top instances now use RX_SRAM/IN_PIPE/NATIVE32=1, matching
closure kits. Specs and the assembly generator record the same parameters; their
views stay explicitly UNBOUND. IN_PIPE adds one face stage on ro/mu_c, rather than
a constant offset on every queued ri beat. The mab top already used1/1/1.

The G8 overlay verifies the actual frame source's four u_xo relays forward each
X bit and corresponding clock unchanged. It traces all four incoming lanes of
every frame through an acyclic chain back to a slice XC root. Only unlinked
output ranges at actual chain ends are declared spare. Intermediate frame
outputs and active forwarded clock taps remain strict. Slice xc is checked as
four identical registered copies of xw4; only unbuilt fanout branches are spare.
The reset pass physically removes generated station outputs with no consumers,
including now-unused ancestor twigs, retaining all surviving release depths.
There is no global unread-net waiver, dummy sink, or functional input tie.

## Validation and retained attempts

The exact actual-plan source/chain check passes on the fleet. A deliberate
frame-X cycle is rejected (`frame_cycle_mutant.log`). Attempts04597 andefbe
stopped before binding when guards caught an incorrect topology assumption and
a logical-versus-physical port-name mismatch; both original directories remain.
Attemptbace completed the source guard but stopped at a missing regex import in
the reset-pruning pass, before a physical build. Correctedd74894719 includes the
import and active-forwarded-clock exemption guard. Its run is
`ot-gold1:/srv/opentallas-scratch/claude/codex-s81-g8-bindfix-1021/die72-g8r4`.
Full strict binding, GEN/GRT, TT/FF/SS and clock results are pending. Do not
interpret this source packet as a passing die or as ready for merge.

The pre-existing G3/G4/G5 strict binds and original G8 Yosys parse were preserved.

`available_descendants.json` records exact GUNIT leaf and XR3 closure inputs.
Both are NOT_BINDABLE onto current R4 source: new leaf parameters/source and
XR3 source/FOREG1 plus its C3 entry age must first enter the parent successor.
A later emitter optimization counts reset-net occurrences once per pruning
pass, preserving the same tested decisions; R4 remains pinned and untouched.
