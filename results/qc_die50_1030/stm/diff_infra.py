"""DIE-QC-50/stm: what the plan_qc51 stm tap split moves in derived plan infra (tap pins of every type, die reset
wavefront, stm reset out pins + own reset tree).  Adapted from DIE-QC-49 collft diff_infra.py.
Usage: diff_infra.py OLD NEW OUT.json"""
import json, sys
sys.path.insert(0, "tools/die_plan")
import schema as S, gen_phys as G, reset_tree as RT
STM = ['slw_stm_v3', 'sle_stm_v3', 'slw_stm_v1__cle34a73c3', 'slw_stm_v1__cl05fc43f7__cl2086fa2c',
       'slw_stm_v1__cl05fc43f7__cl389df4e9', 'slw_stm_v2__cl1ca9c415', 'slw_stm_v2__cl9beb65e6',
       'sle_stm_v1__cl27746664', 'sle_stm_v1__clbe630b9c', 'sle_stm_v2__cl7b3062fa', 'sle_stm_v2__cl55be2264']
def snap(pp):
    P = S.Plan(S.load(pp), pp)
    d = dict(pins={}, wf=None, outs={}, rt={})
    for tn in P.types:
        try: d["pins"][tn] = [list(map(lambda v: round(v, 4) if isinstance(v, float) else v, x)) for x in G.tap_pins(P, tn)]
        except Exception as e: d["pins"][tn] = "ERR " + str(e)[:200]
    try: d["wf"] = json.loads(json.dumps(RT.wf_solve(P), default=str))
    except Exception as e: d["wf"] = "ERR " + str(e)[:300]
    for T in STM:
        try: d["outs"][T] = RT.out_pins(P, T)
        except Exception as e: d["outs"][T] = "ERR " + str(e)[:300]
        try:
            r = RT.for_type(P, T)
            d["rt"][T] = {k: r[k] for k in ("depth", "own_depth", "max_hop_um", "n_tree", "n_pad", "entry", "start_in") if k in r}
        except Exception as e: d["rt"][T] = "ERR " + str(e)[:300]
    return d
a, b = snap(sys.argv[1]), snap(sys.argv[2])
rep = dict(pin_types_changed=sorted(tn for tn in a["pins"] if a["pins"][tn] != b["pins"].get(tn)))
rep["non_stm_pin_types_changed"] = sorted(set(rep["pin_types_changed"]) - set(STM))
rep["stm_reset_outs_same"] = {T: a["outs"][T] == b["outs"][T] for T in STM}
rep["stm_rt"] = {T: dict(old=a["rt"][T], new=b["rt"][T]) for T in STM}
rep["stm_tap_pins"] = {T: dict(old=sum(1 for p in a["pins"][T] if str(p[0]).startswith("clk")),
                              new=sum(1 for p in b["pins"][T] if str(p[0]).startswith("clk"))) for T in STM}
def flat(o, p=""):
    if isinstance(o, dict):
        for k, v in o.items(): yield from flat(v, p + "/" + str(k))
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from flat(v, p + f"[{i}]")
    else: yield p, o
fa, fb = dict(flat(a["wf"])), dict(flat(b["wf"]))
diff = sorted(k for k in set(fa) | set(fb) if fa.get(k) != fb.get(k))
rep["wf_keys_changed"] = len(diff); rep["wf_changed_sample"] = [(k, fa.get(k), fb.get(k)) for k in diff[:60]]
rep["wf_changed_roots"] = sorted({"/".join(k.split("/")[:3]) for k in diff})[:120]
json.dump(rep, open(sys.argv[3], "w"), indent=1, default=str)
print("pin types changed", len(rep["pin_types_changed"]), "non-stm", rep["non_stm_pin_types_changed"])
print("reset outs same", rep["stm_reset_outs_same"]); print("wf keys changed", len(diff)); print("roots", rep["wf_changed_roots"][:40])
for T in STM: print(T, rep["stm_rt"][T], rep["stm_tap_pins"][T])
