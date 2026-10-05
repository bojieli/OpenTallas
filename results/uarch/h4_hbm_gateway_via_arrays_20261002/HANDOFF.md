Constructive HBM PG arrays and real clock contact sites

Authoritative selected_spacing_contacts_r4.json.gz is an additive successor to
constructor_r10 on reviewed main760a. Both models retain32SM and the existing
full-die service context. No RTL, P&R or numerical job was launched; live1950286
was not touched. Historical sources/failures are unchanged.

The source VIARULEs select21 contacts (7x3 M6-M7) and49 (7x7 M7-M8), satisfying
source cut spacing/enclosures inside the already reserved0.544um envelope.
Actual clock via45/56/67 stacks use min-area-safe M4/5/6/7 pads, centre snapped
on the source1nm grid in each macro's real left4um halo. All4160 Qwen/4416 DS
clock sites avoid every selected SM macro body and each other. The passive path
includes the pin escape; its maximum206.000818um stays below the existing215um
SS source ceiling. No reduced RC/slew bound or extra clock buffer credit follows.

The full tech source uncovered an inherited PG failure: M8 width0.544um with
long parallel runs requires0.5um spacing, whereas source recipe stripes and
rings use0.096um. Selected_optin_pdn.tcl changes both M8 stripe and top-ring
spacing to0.5. The model unions new masks with ALL old exclusions, keeping the
50percent reserve, and charges shifted clock contacts too. No tracks are gained.
Selected L2 capacities become Qwen12679/12725/12679/12725 and DS12679 each;
minimum local margins are1538/881. These replace capacity assumptions only;
transaction costs, ownership waits and token latency are not changed.

Local array/contact/distributed-cut gates PASS. Complete physical G0 remains
FAIL: the enlarged ring has2.088um edge extent (+0.404um) and needs a real parent
core-boundary/guard join. Exact array-size enforcement is not installed. IR/EM,
actual route DRC, installed CTS, contextual SS/FF and finite owner/consumer/reverse
waits remain unknown. General L2 reservations are still NOT installed/excluded.
No automatic timing delta or hardware rate is claimed.

Dewey/Sagan contracts are in handoff.json. Owner_hazard_handoff.json coordinates
the existing exact HBM single-owner logic with the parent/Russell tagged-return
proposal. It explicitly states that concurrent remaining_PC and many live-tag
allocation are not provided by the HBM FSM; no pipeline capability is inferred.
The parent's Qwen source finding and exact HBM owner are archived for this join.

Replay:
 python3 -m unittest discover -s tests -p test_h4_hbm_gateway_via_arrays.py
 python3 tools/h4_hbm_gateway_via_arrays.py --out results/uarch/h4_hbm_gateway_via_arrays_20261002/selected_spacing_contacts_r4.json.gz --verify

All inputs are portable hard-pinned archives. Earlier exploratory array-only and
spacing-only records are retained; only the named authoritative record is current.
