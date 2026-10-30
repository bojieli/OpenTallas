"""DIE-QC-49/collft: what the plan_qc50 tap change moves in derived plan infra (tap pins of every type, reset wavefront
per partition, coll_ft reset out pins, die clock tap list).  Usage: diff_infra.py OLD NEW OUT.json"""
import json, sys
sys.path.insert(0, "tools/die_plan")
import schema as S, gen_phys as G, reset_tree as RT
T = "coll_ft__cla4a25d77"
def snap(pp):
    P = S.Plan(S.load(pp), pp)
    d = dict(pins={}, wf=None, outs=None)
    for tn in P.types:
        try: d["pins"][tn] = [list(map(lambda v: round(v, 4) if isinstance(v, float) else v, x)) for x in G.tap_pins(P, tn)]
        except Exception as e: d["pins"][tn] = "ERR " + str(e)[:200]
    try:
        W = RT.wf_solve(P)
        d["wf"] = json.loads(json.dumps(W, default=str))
    except Exception as e: d["wf"] = "ERR " + str(e)[:300]
    try: d["outs"] = RT.out_pins(P, T)
    except Exception as e: d["outs"] = "ERR " + str(e)[:300]
    try: d["rt"] = {k: (v if isinstance(v,(int,float,str)) else str(v)[:300]) for k, v in RT.for_type(P, T).items()} if isinstance(RT.for_type(P, T), dict) else str(RT.for_type(P, T))[:500]
    except Exception as e: d["rt"] = "ERR " + str(e)[:300]
    return d
a, b = snap(sys.argv[1]), snap(sys.argv[2])
rep = dict(pin_types_changed=sorted(tn for tn in a["pins"] if a["pins"][tn] != b["pins"].get(tn)))
rep["coll_ft_pins_old"] = a["pins"][T]; rep["coll_ft_pins_new"] = b["pins"][T]
rep["coll_ft_reset_outs_old"] = a["outs"]; rep["coll_ft_reset_outs_new"] = b["outs"]
def flat(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items(): yield from flat(v, p + "/" + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from flat(v, p + f"[{i}]")
    else: yield p, o
fa, fb = dict(flat(a["wf"])), dict(flat(b["wf"]))
diff = sorted(k for k in set(fa) | set(fb) if fa.get(k) != fb.get(k))
rep["wf_keys_changed"] = len(diff); rep["wf_changed_sample"] = [(k, fa.get(k), fb.get(k)) for k in diff[:60]]
rep["wf_changed_roots"] = sorted({"/".join(k.split("/")[:3]) for k in diff})[:80]
rep["rt_old"] = a["rt"]; rep["rt_new"] = b["rt"]
json.dump(rep, open(sys.argv[3], "w"), indent=1, default=str)
print("pin types changed", rep["pin_types_changed"]); print("wf keys changed", len(diff)); print("roots", rep["wf_changed_roots"][:40])
