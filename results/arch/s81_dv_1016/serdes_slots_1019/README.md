# Required SerDes slot diagnostic

Source plan:6e3559855 `dieplace_1019/plan.json`, SHA pinned in geometry.json.
Actual child/analog model copied unchanged from e423dde24. Eight physical replicas
exist in this MU1 plan; each required slot is518.4x3844.8um. No analog shrink.
The opt-in diagnostic translates the array and all lanes259.2um east, adds518.4um
to die width, retains25000um height and every non-link slot dimension. Existing
default `dv_plan` output is unchanged.

All sixteen real tx/rx endpoints are snapped to the new die-facing slot edge.
Legacy259.2wide post-hoc slots used endpoint x260.0 and some y outside their box.
The new pair y positions retain100um gaps and contain the full actual tx/rx data bands (not only their center points); minimum face-band clearance3.924um.
Global actual-hop census: max403.1um,0over405,3185stations,863424bit-stages,
no changed ages, no block overlaps, no relay overlaps and no lane-band crossings.
Bit-wire cost395674256->395681181bit-um (+0.00175%); worstcut0.5663 unchanged.
These are model facts, not GRT or clock qualification.

**Existing margin policy FAILS:** new die32486.9x25000um leaves256.55um W/E reticle
margin, below500um current rule. ROOT must resolve that explicit constraint before
this can become a legal floorplan. `margin_policy_pass=false` is preserved.
Actual native child/parent TT+FF clocks, reset/status and internal<=405um timed
transport remain owed by SerDes parent owner. No physical fit/native/closure claim.
MU2 extra copy-B slots deliberately refuse until a six-slot west-edge repack has
its own geometry/transport proof. Old strict-bind replay is left running.

COLL561.6square prospective storage successor is recorded as required space, with
actual std7357.695um2 and15macros; it is not placed or adopted by this diagnostic.
Compiler and die schedule must use actual admitted successors, including CAPC
pipeline edges if eventually adopted; no rate credit is taken here.

Reproduce:
`python3 tools/s81_dv/serdes_slot_candidate.py --plan results/arch/s81_dv_1016/dieplace_1019/plan.json --out results/arch/s81_dv_1016/serdes_slots_1019`
