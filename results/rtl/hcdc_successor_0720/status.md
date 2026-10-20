# 07:20 resumed collection and successor model

Gate-Rule: evidence and kit geometry only; no shared helper relaxation or admission change.

R8 sr9 private audit terminal exit143, terminated during C++ compilation. No initial-state audit result; R7 positive pcpo failures retained. Normal PC6 synthesis now supersedes that private route.

HOST7 six CDC variants all terminal FAIL before clock/route qualification, with max32 mapped dynamic fanout and actual pin geometry PASS. PC1j raw detailed placement log: 3943 site alignment,3271 overlaps,3654 unresolved negotiation cells. Independent readback OpenROAD check_placement on frozen failed ODB reports360 region-placement failures. Python full row/site audit finds no grid or same-row overlap in serialized failed ODB; this does not erase the original fail. Region has crossing overlapping horizontal and vertical rectangles;345 cells fit both rectangles in failed ODB. A naive in-memory boundary replacement without rebuilding the placement/group state fails all13636 region members, so it is NOT proof of a fix. No gate launched.

Actual row grid: origin2.16um, x pitch0.054um, rowheight0.27um, DBU1000. Pre-DPL grouped13636 cells; ungrouped11662 centres in old full-width band,6227 in proposed27um edge corridors. Ownership collision remains a hypothesis, not a demonstrated sole cause.

Proposed model before gate:475.2x540 unchanged macro columns and orientations. Reserve W/E27um pin corridors; interior central rectangle x27..448.2,y216..334.8, capacity50038.56um2 before exclusions. Pin range160..390=230um gives PC counts1187/1151 ->5.161/5.004 pins per um; host679/706 ->2.952/3.070. Individual data-bus subranges and clock gaps must separately pass literal placement density and projected flop checks. Macro/halo intersection with pin corridors must be checked. Variant1 single interior band; variant2 disjoint centre-channel extensions. Initial legal anchors, actual region capacity, all macro terminal faces, full graph405 and TT/FF clock measurements remain required, no closure/adoption claim.
