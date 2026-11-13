CBF R8 corridor source candidate (2026-11-13)

Source: tools/die_plan/core_input_chain.tcl (opt-in OT_NK_R8_COUNT_CHAIN=1;
OT_NK_R8_COUNT_SITE_REGEX=u_t_0_2_n_b_in_f$ for the measured bank).
It discovers fixed r/q aliases, kept count bank, actual PC and mux data cone.
Verified source output anchor and PC face-file identity are mandatory. Static count
logic stays in place. All eligible bits preflight before any new pass locations.
It rejects macro crossings, diagonal fallbacks and minimum-count hops over405um.
It never changes gate topology, counts or latency.

Coherent plan event: tools/die_plan/cbf_inner_event.py
  python3 tools/die_plan/cbf_inner_event.py PLAN CLEAN_BIND R8_TABLE CB16_TABLE NEW_EXTRA --report REPORT
It raises common fixed depth to4 for cbf_q01/cbf_q01_s2 u_t02 n_b, keeps optional
span1, aligns n_a and affected downstream reduction branches via existing INNER
metadata, preserving IDs/original asbuilt values. Existing Binder._apply_inner and
inner_strap_sites must regenerate RTL and runtime cb16_pads.json. It refuses an
unclean strict seed; no generated/pinned RTL is patched. No event adopted yet.

Focused source tests:7 PASS (unit E7 oth-ubuntu-1828523-1794612329). Includes
actual Binder/inner_strap_sites, released delay RTL 514-bit count0/1 lockstep and
wrong-depth/count/source-bit mutants, Tcl aliases/layout, coherent branch alignment,
and dirty-seed refusal. Final real-ODB probes and visual in this directory are
candidate-only: no ODB written, no production PLACE/GRT result claimed.

Generic anchor dependency is RULES-REACH core_input_anchor.tcl source follow-up:
unique bounded BUF/INV fanin and forward macro endpoint. Actual E4 ODB census:
6148latches =5888surviving PC chains +256constant TIELO tap bits +4reset paths.
Complete in-memory anchor run has6148latches/5888PC/unresolved0. Keep bound6;
constants and resets do not become fictitious pipeline cells.

Actual frozen ODB vehicle:
E4 /srv/opentallas-scratch2/claude/qc-proof-1/runs/qp1s28/cbf_q01/gen/cbf_q01
run/results/asap7/dp_cbf_q01/base/3_4_place_resized.odb
Intel2 logs ~/hqf-codexlog/cbf_{anchor_census3,anchor_layout_final,atomic_final}.log

Required next: clean strict bind seed from parent QC; generate coherent new EXTRA,
rerun strict bind/asbuilt/model event pricing, manifest kit generation, source-faithful
RTL lockstep and review refreshed plan render, then a private PLACE-only pilot.
Do not enable the placer on old fixed3 or route an unpriced/new latency event.

Bank-area refinement after independent geometry review:
The original route skeleton used collinear bit targets. The placer now allocates
three whole fixed-FF bank rectangles and one combined count/data-mux rectangle.
Actual master demand: DFF1.08–1.188um x0.27um. The measured candidate's three
514-FF banks each reserve36.18x11.8125um /20rows /35.07% occupancy. The combined
514count+1542data-mux/buffer bank reserves36.18x46.44um /77rows /16.06% occupancy.
All rectangles are macro/9um-halo-clear, inside core, and mutually disjoint.
Actual per-bit minimum/count1 paths max387.2675um; all rectangle-corner paths
max393.0286um (<405). This bound includes uncorrelated endpoint movement within
each bank. The source fails atomically if any rectangle or exact/corner hop fails.
It still needs real synthesized common-floor4 masters and PLACE legalization proof.
Static count decode remains in its existing tree; it is not moved into this bank.
Evidence: cbf_bank_area_review.png (viewed), bank_sites.tsv, bank_rects.tsv.
Intel2 ~/hqf-codexlog/cbf_bank_layout_corners.log, E4unit2281269-1794612927 exit0.
This probe uses exact real ODB masters/data cones plus a virtual proposed fourth FF;
no database placement or ODB write occurred. Eight focused tests PASS including
full-bank row demand, macro-clear fit and unfittable-bank refusal (E7unit1948094).
The earlier327.43um skeleton estimate excludes bank area and is superseded by the
387.27um exact/393.03um rectangle-envelope bounds above.

Singleton correction: actual E9 bind_fsuc3 RTL confirms cbf_q01_s2 has ordinary
u_d3_u_t_1_2_t_out D3 -> u_pc_nk_u_t_0_2_n_b D1, no INNER/count bank. The original
hardcoded span1 candidate was wrong for that type. The adapter now derives span
from real rows, allows singleton span0, and applies fixed3->4 with companion/tree
propagation while preserving its ordinary chain. It reports actual optional_span
per type. No generated event used the earlier assumption.
The placer supports this explicit source/PC fixed chain under BOTH
OT_NK_R8_COUNT_CHAIN=1 and OT_NK_CBF_FIXED_CHAIN=1; same area/hop preflight, span0
creates no count FF/site. Replicated cbf_q01 span1 remains unchanged. The ordinary
singleton branch is source-tested, not an actual s2 physical claim; measure its
new synthesized kit and legalized hops in the next pilot. Nine focused tests PASS
(E7unit2044346-1794613279), including actual Binder singleton ordinary chain and
no invented optional count, plus old replicated count/RTL/row-area tests.
