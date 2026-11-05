#!/usr/bin/env python3
"""S81 half event (DIE-S81-56/PLAN 11-04, COORD 13:40 + die owner 19:3x): one ot_v41_bf_col -> one ot_v41_bf_col3_c + two ot_v41_bf16_half in the
unchanged 450.168x198.72 slot, same 26 col types, by the coordinates of results/rfh_1103/bf_col3/mkplan_rfh3.py on the current plan.  Half view:
signed half5.  C view: col3c5 i2 routed but NOT signed off (COORD: C need not be signed off for this event); pins are the same table.  Clock: the
one bf_col tap becomes one tap per core at its signed clk pin with its measured insertion.  Reset tree republished.
    python3 delta_bf_col3_1104.py PLAN_IN PLAN_OUT SIDE_IN SIDE_OUT      (cwd = repo root)
"""
import hashlib, json, sys
from pathlib import Path
sys.path[:0] = ["physical/die_plan/s81", "tools/die_plan"]
import check as CK, schema as S, reset_tree as RT
from plan_event_1104 import plan_text, publish_tree

D = Path("physical/die_plan/s81")
VIEW = "physical/die_plan/s81/cores/views/bf_col3_1104"
W, H, XS, HH, YB, LAT = 450.168, 198.72, 241.92, 95.04, 103.68, 8.64
WC = round(W - XS, 3)
R = lambda v: round(v, 3)
OBS = {"ot_v41_bf_col3_c": "M6", "ot_v41_bf16_half": "M5"}
OLD_LIST = "rtl/dsrom_sys/s81_dv/frame_lp/kit/dsfd_bf_col_kit.sv"
NEW_LIST = ["rtl/v41rom/ot_v41_bf_col3_hw.sv", "rtl/dsrom_sys/s81_dv/frame_lp/kit/dsfd_bf_col3_kit.sv"]


def pin_doc(m):
    """the rfh3 pin table with this event's LEF; asserted equal to the kit's pins.json"""
    src = json.loads((D / f"inputs/core_pins/{m}_rfh3.json").read_text())
    kit = {q["bus"] + (f"[{q['bit']}]" if q.get("bit") is not None else ""): q for q in json.loads(Path(f"{VIEW}/{m}/pins.json").read_text())}
    moved = [q["name"] for q in src["pins"] if q["name"] not in kit or (kit[q["name"]]["layer"], kit[q["name"]]["x"], kit[q["name"]]["y"]) != (q["layer"], q["x"], q["y"])]
    assert len(kit) == len(src["pins"]) and not moved, (m, len(kit), len(src["pins"]), moved[:5])
    pf = f"inputs/core_pins/{m}_1104.json"
    doc = dict(src, lef=f"{VIEW}/{m}/{m}.lef", source="DIE-S81-56/PLAN 11-04: rfh3 pin table, equal to the kit pins.json",
               pinhash=hashlib.sha256(json.dumps(sorted((q["name"], q["layer"], q["x"], q["y"]) for q in src["pins"])).encode()).hexdigest()[:12])
    (D / pf).write_text(json.dumps(doc, indent=0))
    return pf, {q["name"]: q for q in src["pins"]}


def main():
    src, out, side_src, side_out = sys.argv[1:]
    P = json.loads(Path(src).read_text())
    T = json.loads(Path(side_src).read_text())
    Ps = S.Plan(S.load(src), src)
    tbl = {m: pin_doc(m) for m in OBS}
    ins = {m: json.loads(Path(f"{VIEW}/{m}/insertion.json").read_text()) for m in OBS}
    report, n = {}, 0
    for tn, t in P["partition_types"].items():
        hcs, new = t.get("hard_cores") or [], []
        for hc in hcs:
            if hc["module"] != "ot_v41_bf_col":
                new.append(hc)
                continue
            n += 1
            o, (dx, dy), ori = hc["origin_um"], hc.get("track_offset_um", [0.0, 0.0]), hc["orient"]
            assert hc["outline_um"] == [W, H] and ori in ("R0", "MY"), hc
            base = {k: v for k, v in hc.items() if k not in ("module", "lef", "lib", "pins_file", "origin_um", "outline_um", "track_offset_um", "inst", "obs_max")}
            old_tap = next(x for x in t["clock"]["taps"] if x["name"] == f"{hc['inst']}.ck")
            t["clock"]["taps"].remove(old_tap)
            keep = {k: v for k, v in old_tap.items() if k not in ("name", "xy", "insertion_ps", "insertion_ff_ps", "budget_owner")}

            def core(sfx, m, x, y, w, h):
                lx = x if ori == "R0" else W - x - w
                gx = o[0] + dx + lx
                ox = LAT * int((gx + 1e-6) // LAT)
                while gx - ox < 0 or gx - ox >= 2.16 - 1e-9:
                    ox -= LAT if gx - ox < 0 else -LAT
                row = dict(inst=f"{hc['inst']}.{sfx}", module=m, lef=f"{VIEW}/{m}/{m}.lef", lib=f"{VIEW}/{m}/{m}_tt.lib", origin_um=[R(ox), R(o[1] + y)],
                           outline_um=[w, h], orient=ori, track_offset_um=[R(gx - ox), dy], pins_file=tbl[m][0], obs_max=OBS[m])
                row.update({k: v for k, v in base.items() if k != "orient"})
                c = tbl[m][1]["clk"]
                a = CK._orient_pt(ori, w, h, c["x"], c["y"])
                t["clock"]["taps"].append(dict(keep, name=f"{row['inst']}.clk", xy=[R(row["origin_um"][0] + row["track_offset_um"][0] + a[0]), R(row["origin_um"][1] + dy + a[1])],
                                               insertion_ps=ins[m]["tt"]["boundary"]["mean"], insertion_ff_ps=ins[m]["ff"]["boundary"]["mean"],
                                               budget_owner=f"parent_budget pin_register_mean {VIEW}/{m}/insertion.json"))
                return row
            new += [core("u_c", "ot_v41_bf_col3_c", XS, 0.0, WC, H), core("u_ha", "ot_v41_bf16_half", 0.0, 0.0, XS, HH), core("u_hb", "ot_v41_bf16_half", 0.0, YB, XS, HH)]
            report.setdefault(tn, []).append(hc["inst"])
        if len(new) != len(hcs):
            t["hard_cores"] = new
            s = t.get("sources")
            if s and OLD_LIST in s:
                i = s.index(OLD_LIST)
                s[i:i + 1] = NEW_LIST
    assert n == 56 and len(report) == 26, (n, len(report))
    Path(out).write_text(plan_text(P))
    Pn = S.Plan(S.load(out), out)
    rep = {}
    for tn in report:
        t = P["partition_types"][tn]
        lc = t["clock"].get("landing_contract") or {}
        st = T["collector"]["types"].get(tn) or {}
        tree = json.loads(json.dumps(RT.for_type(Pn, tn)))
        old = lc.get("collector_tree") or st.get("tree")
        if not old:      # a col type with no published collector tree: nothing to republish
            rep[tn] = dict(cores=report[tn], reset_depth=None, relays=None, tree=len(tree["relays"]))
            continue
        rep[tn] = dict(cores=report[tn], reset_depth=[old["depth"], tree["depth"]], relays=[len(old["relays"]), len(tree["relays"])])
        publish_tree(lc, st, tree, rep[tn])
    Path(side_out).write_text(json.dumps(T, separators=(",", ":")))
    Path(out).write_text(plan_text(P))
    Pz = S.Plan(S.load(out), out)
    a, b = RT.wf_solve(Ps)["outs"], RT.wf_solve(Pz)["outs"]
    moved = [k for k in Pz.types if k in a and a[k] != b[k]]
    print(json.dumps(dict(cores=n, types=rep, wave_moved=moved), indent=0))


if __name__ == "__main__":
    main()
