# DIE-KV-40 W243 (mk_sd36 rule, DIE-KV-36): the q1/q2 widen-east re-routes the partition reset relay chain of kv3_hg_v1p5 /
# kv3_hg_v1p6 around the wider cores (reset_tree.for_type on event28w; taps, depth, max hop unchanged).  Collector tree :=
# current reset tree for exactly those types; local sources / children / root node must already sit on unchanged taps
# (fail closed otherwise).  usage: mk_coll_w243.py SIDECAR_IN SIDECAR_OUT PLAN_IN PLAN_OUT
import json, sys, hashlib
sys.path.insert(0, "tools/die_plan")
import schema as S, reset_tree as RT
sin, sout, pin, pout = sys.argv[1:5]
raw = json.load(open(pin)); P = S.Plan(json.load(open(pin)), pin)
side = json.load(open(sin)); rep = {}
keep = ("root", "depth", "own_depth", "relays", "max_hop_um", "reach_um", "taps", "n_tree", "n_pad")
for tn, ct in side["collector"]["types"].items():
    try:
        T = RT.for_type(P, tn)
    except RT.ResetError:
        continue
    new = {k: (list(T[k]) if k == "root" else T[k]) for k in ct["tree"] if k in T}
    assert set(new) == set(ct["tree"]), (tn, set(ct["tree"]) - set(new))
    norm = lambda t: {r["q"]: (r["d"], tuple(round(v, 3) for v in r["xy"])) for r in t["relays"]}
    if norm(new) == norm(ct["tree"]):
        continue
    old = ct["tree"]
    tp = lambda t: {r["q"]: [round(v, 3) for v in r["xy"]] for r in t["relays"] if r["q"].startswith("rst_n_t")}
    assert tp(old) == tp(new) and old["depth"] == new["depth"], tn
    nodes = {r["q"] for r in new["relays"]} | {"rst_root_n"}
    used = {f"rst_n_t{s['tap']}" for s in ct["local_sources"]} | {c["node"] for c in ct.get("children", [])} | {ct.get("collector_root_node")}
    assert used <= nodes, (tn, used - nodes)
    rep[tn] = dict(old_relays=len(old["relays"]), new_relays=len(new["relays"]), depth=new["depth"], max_hop_um=new.get("max_hop_um"),
                   used_nodes=sorted(used))
    ct["tree"] = new
    lc = raw["partition_types"][tn].get("clock", {}).get("landing_contract")
    if lc and "collector_tree" in lc:
        lc["collector_tree"] = new; rep[tn]["plan_patched"] = True
assert set(rep) == {"kv3_hg_v1p5", "kv3_hg_v1p6"}, sorted(rep)
raw["note"] = raw.get("note", "") + " | DIE-KV-40 W243: kv3_hg_v1p5/_v1p6 landing collector tree = current reset tree (relay chain re-routed around the wider q1/q2, taps/depth unchanged)"
json.dump(side, open(sout, "w"), indent=1); json.dump(raw, open(pout, "w"), indent=1)
rep["sidecar_sha256"] = hashlib.sha256(open(sout, "rb").read()).hexdigest(); rep["plan_sha256"] = hashlib.sha256(open(pout, "rb").read()).hexdigest()
print(json.dumps(rep, indent=1))
