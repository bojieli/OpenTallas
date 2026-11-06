Captured native reset identity — shared flow READY, no physical signoff claim.

Source authority is clean bind commit49eec7e0a6bd7cc38588c1bc162966e980e5cecc,
physical/die_plan/s81/plan_h2_2249.json and its declared negedge policy.
The source RTL and original failed physical plans remain unchanged.

Actual t13: captured306 logical relays /307 physical relay instances (one output
tap copy) plus entry =308 exact native paths. u_rrl_176 remains depth1,
d=rst_root_n, at1388.88/922.32. Current recomputed308 logical tree is rejected.
Captured tree SHA c005b8f21d87ca57197126e9cefc6d313ca46f603accf2675fd835bdfd054751.
Actual maximum native relay hop380um. Wrong u176 site86.4/17.28 is rejected:
2549.248um actual driver edge exceeds405um. Staged kit metadata/Tcl reimport PASS.
Native core reset ports remain exactly connected as in the bound RTL; no generated
private core tap is substituted. Core reset hop coverage is not claimed.

Actual t25clone: captured237 logical/physical relays verified, maxhop380um,
positive+negedge cell bodies checked. T30 owner's original actual source212 and
placement212 match; it has NO serialized collector tree in captured plan. A NEW
t30 export is intentionally refused until an emitted authoritative tree receipt
exists. Existing t30 baseline remains intact; no current-plan solver substitutes
for missing historical authority.

Minimal focused tests after current-main merge:20 passed,1 optional fixture skip.
This includes changed source/hash/Tcl, recomputed tree, wrong wrapper reset,
out/tap-copy, wrong negedge cell, invalid review/ID/hash and long-edge mutants.
Actual scripts ran via ot-run4GB on dedicated intel2 scratch2 (source-only parsing).
No P&R, timing relaxation, RTL regeneration or route was launched.

Export: bind emission writes <bound>.reset_tree.json and Tcl; kit-rtl recovers
only captured exact tree authority and stages bound_reset.json/reset_tree.tcl.
Physical GEN validates actual native hierarchy/ports/cell behavior, stages both
metadata and exact Tcl beside exported RTL, and uses exact physical instances.

Resite only via clock.landing_contract.bound_reset_placement:
 schema opentallas.bound_reset_placement.v1
 source_tree_sha256 exact captured hash
 sites map actual native IDs (u_rrl_N/u_rst_in) to [x,y]
 review {verdict:PASS,image:actual reviewed image path,findings:reason}
The collector_tree itself stays captured, with identical IDs/edges/depths.
Unknown IDs, changed graph, missing image review and overlong actual edges fail.
A reviewed overlay is retained across kit export, with absolute review image path.
The separate t13 shared inband compute-reset compact-pose feasibility failure
is not repaired by this source-identity guard; S81 types owns that geometry.
