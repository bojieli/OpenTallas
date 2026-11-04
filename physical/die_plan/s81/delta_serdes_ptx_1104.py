#!/usr/bin/env python3
"""S81 plan event, serdes step (DIE-S81-56/PLAN 11-04, COORD 13:1x): every serdes type has u_ptx above the core area: top 1225.8 or
1226.88 against core top 1222.56 (outline 1226.88 - 4.32 kit inset), so macro placement stops on MPL-0034 once a row passes the
cell cap.  delta_pma_views_1031 / delta_serdes_lots_1031 laid the PMA pair flush to the shore without the inset.  u_ptx and u_prx
move down together by the smallest 1.08-um step that clears it (their tx/rx channel stays 10.8).  A reset tree is republished only if the
solver gives another one (the macro boxes are reset obstacles).  The PG domains bound to the PMA pair (phy_lk_ES0, ES1) restate phy_macro_um
from the moved body; the domain rect, bumps and IO windows stay.
    python3 delta_serdes_ptx_1104.py PLAN_IN PLAN_OUT SIDE_IN SIDE_OUT      (cwd = repo root)
"""
import json, math, sys
from pathlib import Path
sys.path[:0] = ["physical/die_plan/s81", "tools/die_plan"]
import schema as S, reset_tree as RT, die_io
from plan_event_1104 import plan_text, publish_tree

INSET, STEP = 4.32, 1.08


def main():
    src, out, side_src, side_out = sys.argv[1:]
    P = json.loads(Path(src).read_text())
    T = json.loads(Path(side_src).read_text())
    Pa = S.Plan(S.load(src), src)
    report = {}
    for tn, t in P["partition_types"].items():
        if not tn.startswith("serdes"):
            continue
        core_top = t["outline_um"][1] - INSET
        parts = [q for c in t["contents"] if c.get("inst") == "u_phy" for q in c.get("physical_parts") or []]
        tx = next(q for q in parts if q["physical_inst"].endswith("u_ptx"))
        rx = next(q for q in parts if q["physical_inst"].endswith("u_prx"))
        over = tx["origin_um"][1] + tx["outline_um"][1] - core_top
        assert over > 0, (tn, over)
        d = round(math.ceil(over / STEP - 1e-9) * STEP, 3)
        for q in (tx, rx):
            q["origin_um"][1] = round(q["origin_um"][1] - d, 3)
        report[tn] = dict(move_down_um=d, ptx=tx["origin_um"], prx=rx["origin_um"],
                          ptx_top=round(tx["origin_um"][1] + tx["outline_um"][1], 3), core_top=core_top)
    Path(out).write_text(plan_text(P))
    Pn = S.Plan(S.load(out), out)
    for tn in report:
        lc = P["partition_types"][tn]["clock"].get("landing_contract") or {}
        st = T["collector"]["types"].get(tn) or {}
        a, b = RT.for_type(Pa, tn), json.loads(json.dumps(RT.for_type(Pn, tn)))
        changed = json.loads(json.dumps(a["relays"])) != b["relays"]
        report[tn].update(tree_changed=changed, relays=[len(a["relays"]), len(b["relays"])])
        if changed:
            publish_tree(lc, st, b, report[tn])
    Path(side_out).write_text(json.dumps(T, separators=(",", ":")))
    Path(out).write_text(plan_text(P))
    Pz = S.Plan(S.load(out), out)
    pg = {}
    for d in P["die"]["pg"]["domains"]:
        if d.get("phy_macro_binding"):
            new = [round(v, 4) for v in die_io.bound_phy_macro(Pz, d)["rect_um"]]
            if new != d.get("phy_macro_um"):
                pg[d["name"]] = dict(old=d.get("phy_macro_um"), new=new)
                d["phy_macro_um"] = new
    Path(out).write_text(plan_text(P))
    Pz = S.Plan(S.load(out), out)
    wa, wz = RT.wf_solve(Pa), RT.wf_solve(Pz)
    wave = dict(parents_changed=sorted(p for p in wa["parent"] if wa["parent"][p] != wz["parent"][p]),
                choice_changed=sorted(k for k in wa["choice"] if wa["choice"][k] != wz["choice"][k]),
                outs_changed=sorted(k for k in wa["outs"] if wa["outs"][k] != wz["outs"][k]), unreachable=wz["unreachable"])
    print(json.dumps(dict(wave=wave, pg_domains=pg, types=report), indent=0))


if __name__ == "__main__":
    main()
