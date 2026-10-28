import sys, json, collections, traceback
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/die-s81-10/tools/die_plan")
import schema, gen_phys as G, sdc_lint
P = schema.Plan(json.load(open(sys.argv[1])), path=sys.argv[1]) if "path" in schema.Plan.__init__.__code__.co_varnames else schema.Plan(json.load(open(sys.argv[1])))
used = {x["type"] for x in P.raw["partitions"]} if hasattr(P, "raw") else set(P.types)
res = collections.Counter(); errs = {}
for tn in sorted(P.types):
    try:
        s = G.sdc(P, tn, G.type_pins(P, tn)); ctx = sdc_lint.kit_context(P, tn); e = sdc_lint.lint(s, **ctx)
        G.core_tap_ff_sdc(P, tn); G.clock_phase_tcl(P, tn); G.clock_phase_tcl(P, tn, before_cts=True)
        core = bool(G.core_tap_rows(P, tn))
        res[("core" if core else "grid") + (" LINT_ERR" if e else " OK")] += 1
        if e: errs[tn] = e[:3]
    except Exception as ex:
        res["EXC " + type(ex).__name__] += 1; errs[tn] = [repr(ex)[:300]]
print(dict(res)); print(json.dumps(dict(list(errs.items())[:8]), indent=0)[:3000])
