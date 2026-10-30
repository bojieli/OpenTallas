# Global STA census from a namespaced ECO hook

Source0b900516613 is independent clock-freeze hardening, not a causal fix claimed
for the supplied PV run. Tcl info-commands relative patterns search the current
namespace only; sourcing the old helper in ot_mm can miss the existing global
STA helper. The new census explicitly uses public ::all_clocks and absolute
::sta::find_all_clk_nets, refusing enumeration errors, unmappable clock nets,
and an empty network with sequential clock pins. Clockless combinational blocks
remain allowed. The source does not move or route anything.

The focused Tcl regression reproduces the namespace miss/public-vs-private API
case and catches missing/error/empty/missing-SDC/unmapped-net paths. Actual
readonly PV5 same ODB plus proper SDC returns exactly1542 names matching the
global reference. A wrapper proves the global STA helper executes once despite
the relative info-command lookup returning0. ActualSTA reports2clocks and29778
sequential clockpins. Injected STA enumeration error and empty return both fail
closed. Native unit1542721 exits0; original input directory is read-only and no
freeze, route, write_db or physical rebuild runs.

Two initial controls expected the old namespaced helper to return0 on the
supplied PV5 post-hook5_1_grt ODB; they failed because that database already
contains1542CLOCK tags, masking the namespace miss. Failures remain preserved.
Further inspection and the PV owner confirm prototype.log actually froze1542
nets/32457instances with0ROUTED WIRES. The later all0 message counted frozen
wires, not discovered clock nets. No actual0-net PV log existed. Therefore the
PV flow problem is absence of a preexisting routed clock-wire baseline, with
old RCX preservation unproven; its fresh COMMON50 diagnostic remains separately
owned. This source change makes future census failures explicit and does not
qualify the PV clock tree or authorize any route retry.
