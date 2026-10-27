# svc_13 last storage-band candidate

GEOM-REVIEW: PASS-COND for this local planning delta; NOT route approval.
Personally viewed corridor.png on 2026-10-27. The existing macro array and three FT banks move left 25.92um. The fourth FT bank is compacted, preserving bit/stage order. All72 macros stay inside the unchanged1442.88x2453.76 outline with minimum8.64um left margin. Exact actual cell boxes have zero macro-body intersections. The east landing band reserves20160 flops for4017payload+control bits, with max pin-to-band corner hop386.64um; nearest FT bank-to-band gap0.594um. Exact gen_phys pin-to-cell-centre and interbank hops max404.383um (405um bound). No RTL or cycle change.

This new candidate removes the sole storage-band placement failure from a COPY of the prepared G2 sidecar. The original failed plan/sidecar remain intact. Run prepare.py against the original prepared plan and sidecar with --tools pointing at tools/die_plan; the input plan SHA is guarded. The large candidate is reproducible rather than duplicated in Git.

Outstanding: COORD same-event adoption, regenerate clock/reset local geometry to follow shifted macro terminals, include this in the single assembled S81 plan event and strict binding, real mapped anchoring/channel/pin/clock/PG checks. Physical qualification remains false. Actual PHY/source boundary stages, real mesh clock, ROWX placement/topology and QXPQ GB source/view integration remain open. No P&R launched.
