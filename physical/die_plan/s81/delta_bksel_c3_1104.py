#!/usr/bin/env python3
"""S81 plan event, bksel_c step (DIE-S81-56/PLAN 11-04, COORD 16:23): after delta_xrt_rfj_1104.py.  The signed dsdv_bksel_c (ECO bksel_c3,
re-signed flow-20261104-y-s81, odb 11f32154) is 388.8x129.6, the plan row 388.8x172.8.  Keep the signed DB, move the plan: outline, lef, lib,
pins_file, obs_max, origin unchanged, the ck[0] core tap at the signed pin (N M5) with the signed insertion.  bk_sel__t2 only.
    python3 delta_bksel_c3_1104.py PLAN_IN PLAN_OUT SIDE_IN SIDE_OUT      (cwd = repo root)
"""
import json, sys
from pathlib import Path
sys.path[:0] = ["physical/die_plan/s81", "tools/die_plan"]
import check as CK, schema as S, reset_tree as RT
from plan_event_1104 import plan_text, publish_tree
from delta_xrt_rfj_1104 import offset, R

M, TN, INST = "dsdv_bksel_c", "bk_sel__t2", "u_bk_sel.u_sel.u_c"
VIEW = f"physical/die_plan/s81/cores/views/bksel_c3_1104/{M}"
PF = "inputs/core_pins/dsdv_bksel_c_c3_1104.json"
W, H = 388.8, 129.6


def main():
    src, out, side_src, side_out = sys.argv[1:]
    P = json.loads(Path(src).read_text())
    T = json.loads(Path(side_src).read_text())
    Pa = S.Plan(S.load(src), src)
    t = P["partition_types"][TN]
    c = next(c for c in t["hard_cores"] if c["inst"] == INST)
    assert c["module"] == M and c["outline_um"] == [W, 172.8] and c["orient"] == "R0"
    assert [n for n, ty in P["partition_types"].items() for q in ty.get("hard_cores") or [] if q.get("module") == M] == [TN]
    ins = json.loads(Path(f"{VIEW}/insertion.json").read_text())
    doc = json.loads(Path("physical/die_plan/s81", PF).read_text())
    pins = [(q["name"], q["layer"], q["x"], q["y"]) for q in doc["pins"]]
    by = {q["name"]: q for q in doc["pins"]}
    old = dict(outline=list(c["outline_um"]), off=list(c["track_offset_um"]), obs_max=c.get("obs_max"), lib=c.get("lib"))
    c.update(outline_um=[W, H], lef=f"{VIEW}/{M}.lef", lib=f"{VIEW}/{M}_tt.lib", pins_file=PF, obs_max="M6")
    dx, dy = offset(Pa, TN, c, pins)
    assert dx is not None and dy is not None, (dx, dy)
    c["track_offset_um"] = [dx, dy]
    X0, Y0 = c["origin_um"][0] + dx, c["origin_um"][1] + dy
    tap = next(x for x in t["clock"]["taps"] if x["name"] == INST + ".ck[0]")
    oldtap = dict(xy=tap["xy"], tt=tap["insertion_ps"], ff=tap["insertion_ff_ps"])
    tap.update(xy=[R(X0 + by["ck[0]"]["x"]), R(Y0 + by["ck[0]"]["y"])], insertion_ps=ins["tt"]["boundary"]["mean"],
               insertion_ff_ps=ins["ff"]["boundary"]["mean"], budget_owner=f"parent_budget pin_register_mean {VIEW}/insertion.json")
    rep = dict(old=old, off=[dx, dy], origin=c["origin_um"], top=R(c["origin_um"][1] + H), old_tap=oldtap, tap=tap["xy"],
               insertion=[tap["insertion_ps"], tap["insertion_ff_ps"]], rst=[R(X0 + by["rst[0]"]["x"]), R(Y0 + by["rst[0]"]["y"])])
    Path(out).write_text(plan_text(P))
    Pn = S.Plan(S.load(out), out)
    lc = t["clock"].get("landing_contract") or {}
    st = T["collector"]["types"].get(TN) or {}
    prev = lc.get("collector_tree") or st.get("tree")
    tree = json.loads(json.dumps(RT.for_type(Pn, TN)))
    rep.update(published=bool(prev), reset_depth=[prev and prev["depth"], tree["depth"]],
               relays=[prev and len(prev["relays"]), len(tree["relays"])], tree_changed=(prev or {}).get("relays") != tree["relays"])
    if prev and rep["tree_changed"]:
        publish_tree(lc, st, tree, rep)
    Path(side_out).write_text(json.dumps(T, separators=(",", ":")))
    Path(out).write_text(plan_text(P))
    Pz = S.Plan(S.load(out), out)
    wa, wz = RT.wf_solve(Pa), RT.wf_solve(Pz)
    rep["outs_changed"] = sorted(k for k in wa["outs"] if wa["outs"][k] != wz["outs"].get(k))
    rep["parents_changed"] = sorted(k for k in wa["parent"] if wa["parent"][k] != wz["parent"].get(k))
    print(json.dumps(rep, indent=0))


if __name__ == "__main__":
    main()
