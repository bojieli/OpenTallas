"""SU2 (slw_su_l1 x2) south-channel form, DIE-QC-85 2026-11-06.

Cause (GRT-0116, 274 M6 ov at x150-250 y0-150): the 515-bit rsn landing child sle_cland_w515_s_201 sat at x 184.9-413.9
under lane4 with a 4.32 um gap to lane4 (y 34.56), while its rsn_i pins are at x 13.5-101 and its ft station 1 at
x 10.8-101.5 y 311: 515 inputs ran east and 515 outputs ran back west through two 4.3-um strips.
Form (placement only; no RTL, no netlist, 0 cycles):
  * lane4 origin y 34.56 -> 60.48 (+25.92); lane4/lane5 gap 51.84 -> 25.92 um.
  * rsn landing child origin (184.896, 4.32) -> (4.32, 25.92): directly above its rsn_i pins with a 21.6-um fan-in
    channel below it and an 8.64-um via channel above it (outputs climb to M7 over lane4).
  * items in the old lane4/lane5 gap that the taller lane4 now covers move +30.24 into the new gap middle:
    ft rsn station 1 (regs_um[1] + bit sites stage 1), collector relays u_rrl_30, u_rrl_68.
  * strip items the moved landing covers move east of it: monitor_0 band -> x 250.56.., relay u_rrl_73 -> east edge.
  * core taps follow their core: u_lane4.clk +25.92 in y; cl_rsn_i.clk with the landing.
Hash-guarded on each selected base type; refuses a changed base.
"""
import argparse, copy, hashlib, json
from pathlib import Path

TYPES = ("slw_su_l1__cla2a78701", "slw_su_l1__clcc9d0155")
DY_LANE = 25.92
DY_GAP = 30.24
LAND_OLD = (184.896, 4.32)
LAND_NEW = (4.32, 25.92)
MON0_NEW_X0 = 250.56


def digest(v):
    return hashlib.sha256(json.dumps(v, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def r6(v):
    return round(v, 6)


def patch_type(t):
    t = copy.deepcopy(t)
    hc = {h["inst"]: h for h in t["hard_cores"]}
    l4 = hc["u_lane4"]
    assert l4["origin_um"] == [17.28, 34.56], l4["origin_um"]
    l4["origin_um"] = [17.28, r6(34.56 + DY_LANE)]
    rs = hc["cl_rsn_i"]
    assert [r6(v) for v in rs["origin_um"]] == list(LAND_OLD), rs["origin_um"]
    w, h = rs["outline_um"]
    rs["origin_um"] = list(LAND_NEW)
    dx, dy = LAND_NEW[0] - LAND_OLD[0], LAND_NEW[1] - LAND_OLD[1]
    clk = t["clock"]
    for tp in clk.get("taps", []):
        if tp["name"] == "u_lane4.clk":
            tp["xy"] = [tp["xy"][0], r6(tp["xy"][1] + DY_LANE)]
        elif tp["name"] == "cl_rsn_i.clk":
            tp["xy"] = [r6(tp["xy"][0] + dx), r6(tp["xy"][1] + dy)]
    lc = clk["landing_contract"]
    b = lc["bands"]["rsn_i"]
    b["rect_um"] = [LAND_NEW[0], LAND_NEW[1], r6(LAND_NEW[0] + w), r6(LAND_NEW[1] + h)]
    b["rects_um"] = [list(b["rect_um"])]
    b["placement"] = "DIE-QC-85 11-06 south-channel form: hard child over its rsn_i pins"
    m0 = lc["bands"]["monitor_0"]
    x0, y0, x1, y1 = m0["rect_um"]
    m0["rect_um"] = [MON0_NEW_X0, y0, r6(MON0_NEW_X0 + (x1 - x0)), y1]
    if m0.get("rects_um"):
        m0["rects_um"] = [list(m0["rect_um"])]
    moved = []
    for r in lc["collector_tree"]["relays"]:
        n = r.get("name")
        if n in ("u_rrl_30", "u_rrl_68"):
            r["xy"] = [r["xy"][0], r6(r["xy"][1] + DY_GAP)]; moved.append(n)
        elif n == "u_rrl_73":
            r["xy"] = [r6(LAND_NEW[0] + w + 2.16), r["xy"][1]]; moved.append(n)
    assert sorted(moved) == ["u_rrl_30", "u_rrl_68", "u_rrl_73"], moved
    for s in t["ft_slots"]:
        if s["name"] == "rsn":
            s["regs_um"][1] = [s["regs_um"][1][0], r6(s["regs_um"][1][1] + DY_GAP)]
            if s.get("bit_sites_um"):
                s["bit_sites_um"][0] = [[x, r6(y + DY_GAP)] for x, y in s["bit_sites_um"][0]]
    t["note"] = (t.get("note") or "") + " | DIE-QC-85 11-06 su2 south-channel form (lane4 +25.92, rsn landing over its pins)"
    return t


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--plan", required=True, type=Path)
    ap.add_argument("--out-plan", required=True, type=Path)
    ap.add_argument("--write-guards", type=Path)
    a = ap.parse_args()
    plan = json.loads(a.plan.read_text())
    gpath = Path(__file__).resolve().parent / "base_guards.json"
    if a.write_guards:
        a.write_guards.write_text(json.dumps({n: digest(plan["partition_types"][n]) for n in TYPES}, indent=1) + "\n")
    guards = json.loads(gpath.read_text())
    for n in TYPES:
        if digest(plan["partition_types"][n]) != guards[n]:
            raise SystemExit(n + ": base type changed; review composition")
        plan["partition_types"][n] = patch_type(plan["partition_types"][n])
    a.out_plan.write_text(json.dumps(plan, indent=1) + "\n")
    print(json.dumps({"types": list(TYPES), "data_cycles": 0, "boot_cycles": 0}))


if __name__ == "__main__":
    main()
