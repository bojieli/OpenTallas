# QBS nodes — independent pre-placement review

Verdict: PASS-COND for one normal PLACE after actual synthesis and equivalence. This is a plan/outline review; actual cell placement, clock tree, density and timing are not qualified.

Image personally viewed: `/srv/opentallas-scratch/claude/codex-s81-qbsnode-2038/node_outlines.png`.
Source receipt: `codex/s81-die-2032@91eca6889`, `results/geom_review/s81_qbsnode_2038`.

The three macro-free 43.2 by 77.76 um outlines have no macro walls or narrow channels. LLfu and LLfd collect their two input banks on the east face and put the output band on the north/south face respectively. NNfu has opposite north/south data bands. The outline maximum Manhattan span is 120.96 um, below the 405 um per-cycle budget. The east clock entry is near mid-height and has a short geometric path into this compact outline; no clock balance or PDN claim follows from a plan image.

Conditions: actual PLACE must demonstrate legal rows, usable fill/empty-bin metrics, boundary-flop locality and no collapsed relays; CTS must retain real clock connectivity and measured leaf/pair timing. Check parent face alignment in the actual composition before parent route.
