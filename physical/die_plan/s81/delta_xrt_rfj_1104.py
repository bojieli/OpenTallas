#!/usr/bin/env python3
"""S81 plan event, xrt step (DIE-S81-56/PLAN 11-04, COORD ruling 12:05 PST): after delta_svc_band_1104.py.  The RF-J cores are
signed at 207.36x164.16, so the plan slot takes the signed form, no kit rebuild.  xrt1: outline 311.04x395.28 -> 207.36x164.16,
lef/lib/pins_file -> signed view, obs_max M6 (the signed LEF has M6 OBS).  xrt3: outline already right, lef/lib/pins_file -> signed
view (only when its tagged LEC ends EQUIVALENT: pass xrt3 on the command line then).
Anchor: R0 keeps the SW corner.  MX keeps the mirrored S face up to the 8.64-um origin lattice: y 794.88 -> 1019.52, the origin
xrt3 already uses (top edge 1183.68, old 1190.16; old + 395.28 - 164.16 = 1026.0 is off the lattice).  Track offset: searched against
the plan tracks in the type and instance frames (check_taps_cores rule).  Clock tap and reset tree follow the signed pins (clk N M5).
    python3 delta_xrt_rfj_1104.py PLAN_IN PLAN_OUT SIDE_IN SIDE_OUT xrt1 [xrt3]      (cwd = repo root)
"""
import json, sys
from pathlib import Path
sys.path[:0] = ["physical/die_plan/s81", "tools/die_plan"]
import check as CK, schema as S, reset_tree as RT
from delta_svc_band_1104 import plan_text, publish_tree

VIEW = "physical/die_plan/s81/cores/views/xrt_rfj_1104"
W, H = 207.36, 164.16
R = lambda v: round(v, 3)


def offset(P, tn, row, pins):
    """first (dx, dy) that puts every pin on its plan track in the type frame and the instance frames"""
    cw, ch = row["outline_um"]
    o, (ox, oy) = row["orient"], row["origin_um"]
    frames = [pi for pi, p in P.parts.items() if p["type"] == tn]
    def fits(axis, d):
        for name, ln, x, y in pins:
            L = P.layers.get(ln)
            if L is None or ln == "M1" or (L["dir"] == "V") != (axis == 0):
                continue
            tx, ty = CK._orient_pt(o, cw, ch, x, y)
            pt = (ox + d + tx, oy + ty) if axis == 0 else (ox + tx, oy + d + ty)
            for fx, fy in [pt] + [P.to_die(pi, pt) for pi in frames if ln not in CK.MIRROR_SKIP or P.parts[pi].get("orient", "R0") == "R0"]:
                if not CK.on_track(fx if axis == 0 else fy, L):
                    return False
        return True
    dx = next((R(k * 0.002) for k in range(0, 500) if fits(0, k * 0.002)), None)
    dy = next((R(k * 0.002) for k in range(0, 500) if fits(1, k * 0.002)), None)
    return dx, dy


def main():
    src, out, side_src, side_out, *mods = sys.argv[1:]
    mods = {"ot_s81sl_" + m for m in mods}
    assert mods and mods <= {"ot_s81sl_xrt1", "ot_s81sl_xrt3"}, mods
    P = json.loads(Path(src).read_text())
    plan_dir = Path(src).parent if False else Path("physical/die_plan/s81")
    Ps = S.Plan(S.load(src), src)
    T = json.loads(Path(side_src).read_text())
    report = {}
    for tn, t in P["partition_types"].items():
        for c in t.get("hard_cores") or []:
            m = c.get("module")
            if m not in mods:
                continue
            ins = json.loads(Path(f"{VIEW}/{m}/insertion.json").read_text())
            pf = f"inputs/core_pins/{m}_rfj.json"
            doc = json.loads((plan_dir / pf).read_text())
            pins = [(q["name"], q["layer"], q["x"], q["y"]) for q in doc["pins"]]
            by = {q["name"]: q for q in doc["pins"]}
            old = dict(origin=list(c["origin_um"]), outline=list(c["outline_um"]), off=list(c["track_offset_um"]))
            y = c["origin_um"][1]
            if c["orient"] == "MX" and c["outline_um"][1] != H:
                y = R(y + c["outline_um"][1] - H)
                y = R(int(y / 8.64) * 8.64)
            c.update(origin_um=[c["origin_um"][0], y], outline_um=[W, H], lef=f"{VIEW}/{m}/{m}.lef", lib=f"{VIEW}/{m}/{m}_tt.lib",
                     pins_file=pf, obs_max="M6")
            dx, dy = offset(Ps, tn, c, pins)
            assert dx is not None and dy is not None, (tn, dx, dy)
            c["track_offset_um"] = [dx, dy]
            X0, Y0 = c["origin_um"][0] + dx, c["origin_um"][1] + dy
            at = lambda q: (lambda a: [R(X0 + a[0]), R(Y0 + a[1])])(CK._orient_pt(c["orient"], W, H, q["x"], q["y"]))
            tap = next(x for x in t["clock"]["taps"] if x["name"] == "u_c.u_xr.clk")
            tap.update(xy=at(by["clk"]), insertion_ps=ins["tt"]["boundary"]["mean"], insertion_ff_ps=ins["ff"]["boundary"]["mean"],
                       budget_owner=f"parent_budget pin_register_mean {VIEW}/{m}/insertion.json")
            report[tn] = dict(module=m, orient=c["orient"], old=old, origin=c["origin_um"], off=[dx, dy], clk=tap["xy"], rst_pin=at(by["rst_n"]))
    Path(out).write_text(plan_text(P))
    Pn = S.Plan(S.load(out), out)
    for tn in report:
        t = P["partition_types"][tn]
        lc = t["clock"].get("landing_contract") or {}
        st = T["collector"]["types"].get(tn) or {}
        tree = json.loads(json.dumps(RT.for_type(Pn, tn)))
        old = lc.get("collector_tree") or st.get("tree")
        report[tn].update(reset_depth=[old["depth"], tree["depth"]], relays=[len(old["relays"]), len(tree["relays"])],
                          core_reset=[r for r in tree["core_resets"] if r["inst"] == "u_c.u_xr"])
        publish_tree(lc, st, tree, report[tn])
    Path(side_out).write_text(json.dumps(T, separators=(",", ":")))
    Path(out).write_text(plan_text(P))
    Pz = S.Plan(S.load(out), out)
    assert all(RT.wf_solve(Pz)["outs"][k] == RT.wf_solve(Ps)["outs"][k] for k in Pz.types if k in RT.wf_solve(Ps)["outs"]), "wave moved"
    print(json.dumps(dict(modules=sorted(mods), types=report), indent=0))


if __name__ == "__main__":
    main()
