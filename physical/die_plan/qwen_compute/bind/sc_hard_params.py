"""DIE-QC-63/SC 11-02 (QC SC event, OWNER 11-02): explicit plan hard-core parameters -> bound leaf parameters.

A plan hard core with params (partition_types[t].hard_cores[i].params, e.g. the SC leaf u_core = qfd_dv_s5_sc2_leaf
{HARD_PINREG: 1}) selects that parameter on exactly the bound leaf of every partition of type t whose type-local name
(u_<rel>, as emitted in the bound wrapper) is the hard core inst and whose module is the hard core module.  Called from coll_regen.regen (asbuilt.param_regen).
Fail closed: a parameterised hard core whose bound leaf is missing, ambiguous or of another module raises (the bind
reports PARAM_REGEN ...), so a plan event can never be silently dropped.  Types without params: nothing changes."""


def regen(ctx):
    plan = ctx.plan
    pt = plan.get("partition_types") or {}
    want = {}
    for p in plan.get("partitions") or []:
        for hc in (pt.get(p["type"]) or {}).get("hard_cores") or []:
            if hc.get("params"):
                want.setdefault(p["name"], []).append(hc)
    params, record = {}, []
    for part, hcs in sorted(want.items()):
        members = ctx.members.get(part) or []
        for hc in hcs:
            if hc.get("params_scope") == "kit_macro_rtl":
                import kit_macro_rtl
                record.append(kit_macro_rtl.obligation(ctx, part, hc))
                continue
            hit = [ci for ci in members if "u_" + ctx.rel_of(ci) == hc["inst"]]   # bound instance = u_<rel>
            if len(hit) != 1:
                raise ValueError(f"SC_HARD_PARAMS {part}: hard core {hc['inst']} binds {len(hit)} leaves (need 1)")
            c = ctx.F.cells[hit[0]]
            if c.module != hc.get("module", c.module):
                raise ValueError(f"SC_HARD_PARAMS {part}: {hc['inst']} is {c.module}, plan hard core says {hc['module']}")
            params[c.path] = {k: v for k, v in hc["params"].items()}
            record.append(dict(partition=part, inst=hc["inst"], leaf=c.path, module=c.module, params=hc["params"]))
    return params, record
