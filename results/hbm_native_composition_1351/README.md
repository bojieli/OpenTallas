# Current native source composition candidate

This emits a reviewable source top where the selected released quad IDX client
and four actual VMS roles replace the historical two-stop IDX/VMS composition.
It is FAIL_CLOSED_NATIVE_PROVIDERS_MISSING, not a current physical or boot pass.

The 356-instance top retains all four original qctl/operand/query/scorer paths,
selector/rootctl/topk/link and XQ collection tree. It imports the original
hb_argmax graph too: the historical B1 argmax read NW.cr, which is not the
selected four-role NC0 NW interface. Actual SW retains its two scalar clients.
The four scorer instances use ot_hnx_idxn_quarter_with_keybuf TP192,
DELIVERED_RESET1, packed NP4/RS0, 17 soft SRAMs per quarter. Ordinals and half
straps remain SW0/0, SE1/0, NW0/342, NE1/342.

The additive real central root and two N4 tnodes use delivered-reset mode1.
The four identity links are NW.uo271 -> root.up_nw and root.down_nw173 -> NW.dn,
with the analogous NE pair (888 bits total). No old HC graph is deleted for this
addition. Local source interfaces follow main's merged reset source 837c608795.

187 explicit boundary ports include 48 new obligations: 28 replay/calendar
controls, five central job/load/pad controls, eight N4 lower-tree/pad inputs,
and seven delivered-reset inputs. Original POR expressions are recorded as
provenance, not accepted as delivered wavefront endpoints. Remaining boundaries
include original external inputs and missing original SW/SE calendar, VMS bank,
and SVG providers. Missing inputs are never tied to zero or silently renamed.
Native unconsumed outputs are exposed to the top, never dropped silently.

Non-IDX/VMS existing B1 leaves remain explicitly historical scaffold. Current
full-native binding, actual host bootstrap, calendar, target allocation, reset
wavefront, lower FUSED tree, mapped per-bit aliases, PG/clock and physical plan
adoption remain open. This source candidate cannot clear the old 142 failures.
The old source's 94 empty intersections all have actual parent-bus partners;
that diagnosis is not authorization to reuse them in the selected vehicle.

Reproduce with tools/hbm_b2/current_native_top.py ORIGINAL BASE ASBUILT OUT.
ORIGINAL is the released die_r18h5.v.gz and BASE is retained logical_b1
out/top/die_b2.v. Exact content hashes are in composition.json. Snapshot inputs
and full manifest/source path records are at intel2:
/srv/opentallas-scratch2/claude/codex-hbm-native-bays-1351/compose4.

Validation: three narrow tests pass, including wrong VMS-role and distinct-clock
mutants. Actual emitted source round-trips to 356 instances / 8886 ports; all
referenced net ranges are declared. These checks do not establish RTL equivalence
or source-module ABI elaboration.

LEC bounded identity review: all 658 retained ports across the 28 imported
instances match original resolved bit origins and directions, zero mismatches.
352 input ports carry removed original transport history (maximum 129 edges).
The receipt now records each history obligation and an empty current-plan
station binding ledger. Original parameter dates remain provenance. This is
BITGRAPH_PARTIAL_ONLY; executable dates and current calendar equivalence are
not established by collapsing that history. The separate current-main strict
RTL port/child bind uses immutable ee405a63ca8 (merged delivered reset and HCOL
clock adapter) and is collecting diagnostics before any source qualification.
