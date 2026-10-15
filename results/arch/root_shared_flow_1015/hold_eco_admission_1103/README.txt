Hold ECO resource admission (2026-10-15)

The retained metadata leaf is READY at verdict after completed route, TT
+356.68ps/FF -6.28ps/DRC0. It requests4GB for route; no recorded class peak.
The universal32GB ECO request selected a200GB disk floor and waited on AGI
with81GB free. No ECO has been started or job state changed by this proof.

Compute hold ECO request from the effective completed route admission and
largest recorded block-class actual peak (same25%/+4GB margin used for
route sizing), with minimum8GB. Any resulting request above8GB keeps at
least32GB; larger actual requests remain larger. Measurement opt-out keeps
the raw route request. A known large class prevents a low declared request
from being treated as small. Unknown default route retains32GB. Fixed8
threads unchanged. Admission, launch reservation and launch_stage use one
value, also recorded under eco.resources.

Existing Fleet logic provides30GB light-stage disk floor for <=8GB,
200GB host-specific heavy floor otherwise, unchanged16GB RAM safety,
per-job limits, launch reservations and all other disk roots. No timing,
DRC, acceptance, source-binding, or ECO ownership behavior changed.

5 focused tests PASS: actual81GB disk/8GB positive;32GB still blocked;
<30GBdisk and <24GBmemory negatives; small/large/class/optout/unknown
resource cases; reservation+launch consistency; blocked job stays unchanged.
Existing5 acceptance and7 reference tests PASS. Some existing reference
tests emit unclosed-file ResourceWarning; all assertions pass.

Root owns exact daemon deployment. Existing verdict tick can start the
single ECO normally after deployment; no manual state edit or reroute.
