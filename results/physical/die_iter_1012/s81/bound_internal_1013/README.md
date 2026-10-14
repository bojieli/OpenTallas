# Actual-bound S81 c7 internal timing pilot

This gate supplements boundary die STA. It does not release the die. Census is
from the immutable running c7 kit on EPYC1, source main4f79ec65e. It includes
17 CLOSED relay masters (23,680 instances), q-element and the four real hard-IP /
ROM macro masters; placeholders and partitioned slabs remain explicitly listed.
Historical hquad_r6/ep_r4/ep_r6 are absent from this kit's bound libs, so their
negative SS730 sensitivity is not evidence of failure in these bound leaves.

`tools/s81/bound_leaf_internal_gate.py gate c7_review_manifest.json reviewed_receipts.json c7_gate.json`
returns nonzero: the17 relays have admitted reviewed receipts; q-element and
4 hard-IP/ROM macros remain open. See relay_batch_summary.json and raw receipts/.
All17 relay masters now have fresh source/route/domain-matched SS/FF receipts.
The5 macro masters still need internal timing or their
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
The initial get_fanin API diagnostic returns zero, but a fresh q-element run
proved that diagnostic is incomplete and MUST NOT provide an absence proof.
The corrected gate always rejects a returned negative internal path regardless
of that diagnostic. An explicit source/spec/hash-bound review instead proves
these relays have one r<=i register vector, o=r, no feedback, and no returned
internal STA paths. Missing-path exemptions require that review separately. Flat actual route min-period report is zero and period /
pulse violation report is empty. This basis is source/log-bound in the reviewed
receipt. Multi-stage leaves require actual nonnegative SS reg-to-reg setup and
FF hold, constrained coverage, and independently reviewed min-period/pulse.

Raw execution receipt remains passed:false because execution alone is not
qualification. The reviewed_receipts.json record binds the explicit review to
the actual lib/source/clock hashes. Gate requires that exact matching evidence;
missing, negative, unconstrained, unrelated old source, alias-corner hash or
wrong clock periods fail. Tests exercise these distinct rejection conditions.

No CLOSED route was rerun. No main push or producer RTL change occurred.

Fresh four-host batch admitted4GB/1thread each: EPYC1unit338044, EPYC4unit74501,
PVE1unit565444, AGIdockunit3307554, all exit0. Remaining16 variants SS setup
+192.506454..+401.049652ps, FF hold+9.359937..+18.235060ps, every D endpoint
finite max/min. Source/spec/params/lib/route hashes match exact current c7.
The aggregate gate now covers17/17 CLOSED relay masters and fails the5 macros.
No v18 consumed kit exists yet; these results never claim a v18 binding.

Q-element internal timing is now disproven at its current actual caller period.
`qelem_source_binding.json` freezes all32 routed sources at7fb23b7ff and20
parameters (PQ1/QM5/QS5), with original archive job/driver-receipt hashes.
`qelem_caller_binding.json` matches ALL1280 consumed Q clk nets to128 explicit
column clock roots at833.333ps (10Q/column). Only proven wire[0:0] aliases are
normalized. This is a direct netlist/root binding proof, not clock RC closure.

The CLOSED archive ODB6504260a436b... and SPEF3f5ac826e0b8... plus all original
post-SDC hashes were restored and checked. Original833.000ps replay remains in
qelem_original/. Separate actual833.333ps replay in qelem_actual/ changes ONLY
the physical core_clk period literal from833.000 to833.333; the original default
50% duty/zero phase, uncertainty60/25ps, exceptions and virtual clock833.000ps
remain. actual_context.json records the precise original and translated SDC
hashes. Both admitted16GB/1thread runs exit0 (EPYC1units349061 and386332).

Actual833.333 Q SS internal max−187.246658ps, FF internal min+12.042617ps;
53,738 returned internal-path endpoints and55,561 finite register D endpoints.
SS minimum period1020.58ps exceeds833.333; FF minimum595.22ps fits. Full paths,
clock reports and snapshots are retained. The source-bound runtime gate fails
Q by internal setup and minimum period; faulty get_fanin zero cannot override
a returned negative path. Root assigned s81_qelem_internal_repair to the
structural source repair; historical CLOSED route is preserved.

Macro literal audit identifies existing HBM declared SS900ps and ROM634.964ps
period contracts; these are not internal implementation/provider proof. D2D
serdes and UCIe omit minimum-period characterization. A read-only admitted
actual c7 floorplan/unchanged-kit clock probe also finds PHYclk and ALL8D2Dclk
pins unclocked. Die lead identified the generator causes: PHY clk is packed
into its data bundle; D2D forwarded fo is a sequential cq arc rather than actual
clock transfer. Independent ideal clocks on these pins would conceal the
source defects and are not used. Their receipts remain missing/unqualified.
