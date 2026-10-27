M6 pin-only grants
==================

A die lead may put `m6_pin_grant` in a leaf's physical spec or contract slot.
This is separate from the legacy whole-layer `layer_cap_grant`. Keep
`layer_cap: M5`, PG M5, and routing M2–M5. A pin-only grant never changes
`view_cap` to M6 or authorizes M6 routing, OBS, power, or M7 geometry.
The default behavior without `m6_pin_grant` is unchanged.

Use `m6_pin_grant.schema.json`. The grant names the exact master, die lead,
reason, immutable source commit, and physical-spec digest. Each entry in
`ports` names one scalar or bus bit, its face, span along that face, maximum
edge depth, and maximum contact area. Wildcards and duplicate names fail.
Depth and area are bounded to at most 1 um and 1 um²; use actual contact
bounds from the native pin plan, usually much smaller. Any unlisted M6 pin,
interior shape, enlarged contact, or unknown port fails.

The physical-spec digest is SHA256 of canonical JSON (sorted keys, compact
separators) excluding only `m6_pin_grant`, computed by
`m6_pin_grant.spec_digest`. Generation checks this digest. For granted kits,
the original source spec is preserved so regenerating the kit/gate checks
that same source. Changes to routing, outline, sources, ports, or other spec
fields require a renewed grant. Generation also verifies that RTL sources, exact IO Tcl, post-synthesis Tcl,
and referenced Tcl/SDC flow variables match that source commit byte for byte.
The immutable source commit and physical-spec digest complement each other.

A grant is written before submission, after the die lead reviews the physical
spec and exact access plan. It is permission to attempt the route, not a
closure claim. Use exact IO placement to place only the named bits on M6.
`route.pin_h: "M4 M6"` becomes legal with the grant, but the exported geometry
still must use only listed M6 contacts. Keepout above an M6 face pin is M7;
the parent must also exclude its M6 power straps from the actual M6 contact
footprints. Die-region access and power checks remain the die lead's proof.

Export checks the untouched LEF plus a raw final detailed-route DEF
(`6_final.def`, or `5_route.def`) and stores its copy, the grant, and audit
hashes beside the exported view. LEF M6 PORT rectangles must match actual
DEF PINS rectangles in both directions. Every M6 OBS, M7 route, or above-M5 PG shape fails, even when an abstract omitted it.
M6 signal wire is accepted only when its complete rectangle (tech width and
DEF endpoint extensions included) lies inside one actual granted terminal PORT
on the same net. Unknown width or unsupported route geometry fails closed. A signal via may have an M6
landing only completely inside that net's authorized M6 PORT; its remaining
metal is M5 or below. Named technology vias use the exact read-tech LEF snapshot emitted by
view_export; its hash is in the audit. DEF-defined vias use explicit RECTs.
Generated-rule vias whose declared routing layers both stop at M5 are safe
without a high-layer footprint. High generated-rule vias require expanded
RECT geometry; unresolved vias fail closed. POLYGON/PATH and unparsed geometry are not
accepted by this conservative audit. Do not replace real OBS with strips
or move above-cap route stubs into PORTs to make the audit pass.

The closure daemon ships the auditor, reads the raw routed DEF, and repeats
the check. A `hier_lint` skip does not override grant checks. Structural PG
spread and face-access checks remain in force.

Validation currently includes a constrained fixture with a real historical
M6 rectangle (`vm_cp_rb2`, `ei[1001]`) and synthetic legal M5 PG/routing. The
historical master itself uses M7 PG and does not qualify for this permission.
No actual closed M5-routing/PG master with M6 contacts existed when this
implementation was written. Full closure requires the new native candidate's
real routed DEF/LEF, timings, DRC, benches, and parent access proof.
