# Actual-bound S81 c7 internal timing pilot

This gate supplements boundary die STA. It does not release the die. Census is
from the immutable running c7 kit on EPYC1, source main4f79ec65e. It includes
17 CLOSED relay masters (23,680 instances), q-element and the four real hard-IP /
ROM macro masters; placeholders and partitioned slabs remain explicitly listed.
Historical hquad_r6/ep_r4/ep_r6 are absent from this kit's bound libs, so their
negative SS730 sensitivity is not evidence of failure in these bound leaves.

`tools/s81/bound_leaf_internal_gate.py gate c7_review_manifest.json reviewed_receipts.json c7_gate.json`
returns nonzero: only dsfd_rly_15_EN has an admitted, fully reviewed pilot receipt.
The other16 relay masters and5 macro masters still need internal timing or their
own exact source-bound hard-IP/combinational coverage evidence. No exemptions
are inferred from master names or zero ETM minimum-period fields.

Pilot actual retained CLOSED route s81_rly_15_en-v3-faf093855 resides on AGIdock.
Replay admitted by ot-run4GB/1thread, unit oth-ubuntu-3300994-1791949219, exit0.
The SS and FF replay commands and hashes are in pilot/receipt.json. The original
export mounting sequence and routed ODB/SPEF/SDC hashes were verified before
load. No routing or timing constraints were changed. Original physical clock
833.333ps, setup uncertainty60ps, hold25ps remain; original boundary virtual
clock770ps remains. Hashes of source files and params{} match the actual c7 source.

SS all45 register D endpoints: max+378.925629ps, min+32.676571ps, no unconstrained.
FF all45 register D endpoints: max+447.452545ps, min+9.727920ps, no unconstrained.
An independent all-arcs structural fanin census finds zero register-output to
register-data pairs: this is a one-stage relay. Thus internal reg-to-reg timing
and feedback minimum period are inapplicable for this exact master; this is not
inferred from an ETM. Flat actual route min-period report is zero and period /
pulse violation report is empty. This basis is source/log-bound in the reviewed
receipt. Multi-stage leaves require actual nonnegative SS reg-to-reg setup and
FF hold, constrained coverage, and independently reviewed min-period/pulse.

Raw execution receipt remains passed:false because execution alone is not
qualification. The reviewed_receipts.json record binds the explicit review to
the actual lib/source/clock hashes. Gate requires that exact matching evidence;
missing, negative, unconstrained, unrelated old source, alias-corner hash or
wrong clock periods fail. Tests exercise these distinct rejection conditions.

No CLOSED route was rerun. No main push or producer RTL change occurred.
