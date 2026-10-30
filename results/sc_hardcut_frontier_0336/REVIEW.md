# Independent SC hardcut frontier review

Scope: f8b9aa53b same-outline bay and 07759fbf5b9 exact-source 572-pin child.
Personally viewed both bay_model.png and pin_plan.png. CONDITIONAL source/GEN/
SYNTH characterization only; normal physical readiness BLOCKED. No source
activation, new cycle, parent P&R or STA is authorized by this review.

The bay is [345.6,656.64,598.8,1162.08], child253.2x505.44um. Existing mapped
u_core281884std/36859.275um2 and wrapper260481std are individually under400k.
Child usable density30.34% is deliberate reserved physical space. Exact affine
output pins preserve track/PG phases and bit-correlated N401.76/E403.44/W345.6um
proxies. These are port-to-public-face proxies, not actual bout-FF reach or
child timing. The E proxy has only1.56um margin. Four reset reservations and
six FT stage groups intersect the body and remain parent physical blockers.

## Existing source frontier

The exact k79 structural source contains43058 existing state helpers. Every
355data input bits immediately feeds FF D, with no combinational sinks or
input-to-output bypass. There are757 distinct immediate input FFs. Every215
output bits is a direct unique FF Q with NO internal loads; output FFs are
disjoint from input FFs. This establishes sequential connectivity but does not
satisfy all normal face rules.

Normal tools/die_plan/face_guard.py explicitly requires exactly ONE input load
leading to dedicated FF D. Source input fanout histogram is248bits x1,97bits x5,
9bits x2,1bit x6. Thus107bits have a shared-input frontier and cannot receive a
normal face qualification merely because each load is sequential:

- sc_cfg[100]
- dn_i[0:34] and dn_i[47]
- up_i[0:34] and up_i[47]
- red_addr[2]
- red_data[31:0]
- am_v

Of these,103bits have duplicate FFs with matching clock/reset-type/net signature.
Four control bits have distinct reset nets: sc_cfg100 (three signatures),
dn_i47/up_i47/am_v (two each). No duplicate-state deletion or reset equivalence
is assumed. These are source predictions; actual native SYNTH/face_guard must
still report mapped survival and sharing. Preserve every failure; no skip or
pathfinding continuation may be reported as normal qualification.

## Frontier ownership options and geometry blocker

Moving an EXISTING preceding parent register stage into child ownership could
retain overall state/cycles and make the raw replicated capture FFs internal.
It changes private input phase/meaning and requires a concrete parent/child
source rewrite plus whole-parent equivalence and complete clock/reset ownership.
Mixed migration of only107bits creates mixed private port phases. Neither form
has been activated or approved here.

Moving ALL355 preceding stages into this bay cannot preserve direct public
input faces: parent u_bin_x_fe_i.D reads public x_fe_i[46:0] directly and
u_bin_flt_fe_i.D reads public flt_fe_i[0] directly. Exact public-pin distance to
ANY point in the child body is378.960..388.152um for x_fe_i and443.792um for
flt_fe_i0. These exceed the150um maximum before inset or row placement. Those
public input registers must remain outside this child. N/W final bins are fed
by CA landing logic, so their movement requires identifying and preserving the
actual earlier public face FFs rather than assuming the final bin is the face.
All parent public output pins are also >=345.6um from the body: parent bout FFs
must remain at public faces. Raw child output FFs are already dedicated.

A viable next source event therefore needs a different private frontier/cut or
bay, or an explicitly reviewed same-cycle source transformation. No added data
cycle or broad face-guard exception is a solution in this packet. The exact
107bit/757FF lists are in frontier.json; frontier.py reads only the supplied
structural source and is not a timing estimator.

## Layer and timing interface demand

Recipe and source spec request MAX_ROUTING_LAYER=M7. The child must conservatively
obstruct M1 through M7 across its body until actual routed abstraction proves a
more precise shape. Parent adoption must explicitly publish obs_max=M7; a default
M5 abstraction must not silently free M6/M7. Parent FT partition logic also uses
<=M7, so intersecting FT cannot pass through this child unless pushed into its
netlist with exact existing stages/footprints and proof, or rerouted around it.
M8/M9 are die PG/clock/reset-first resources, not free parent-FT overflight.

M4/M6 E/W and M5/M7 N/S child pins comply with direction/phase rules in the pin
model. W clock/reset pins and all757+215 existing candidate face FF homes still need
actual row/FIRM capacity and internal reach/cut checks. No input-face homes or
TT/FF interface timing exist yet. Nominal833ps period,250/202.5ps common frames,
tol40 and60/25ps uncertainties are generation inputs only; they are not actual
clock insertion or a child timing result. Parent CA/R8/pd6/pd8 delivery budgets,
actual per-bit reach, clock sink tree and synchronous reset contract remain.

GEN and native SYNTH-only characterization are useful next steps if ROOT elects
to inspect this exact-source candidate: keep parent inactive, retain expected
shared-input face failures, and stop before floorplan/place/STA. Physical
qualification requires resolving the dedicated frontier and parent delivery/
reset/FT/layer conflicts first. No A0 source or physical milestone was changed.
