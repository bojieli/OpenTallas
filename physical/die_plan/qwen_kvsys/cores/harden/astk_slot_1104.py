#!/usr/bin/env python3
"""DIE-KV-69 11-04: kv3_astk view form into plan_c (kv3_hub_Eo/Wo), one event with the astk view.

Slot 190.08x181.44 -> 216x211.68, keeping each core's outer-face corner (grows toward the hub interior). Pin table = the
kit's routed pins.json. Plan sites the new slot covers shift out by exactly the growth, row and site grid kept. Parent
port form in native_port_adapter (kit_core_clocks.adapt_core_ports): six leaf ck and six leaf rst_n collapse onto the
core's ck and g_phys_fault_u_fault__rst_n, unused rst_n and the 4 tc buses are tied. 0 cycles, no RTL.
usage: astk_slot_1104.py PLAN PINS_OUT KIT_PINS_JSON
"""
import json, sys

W, H = 216.0, 211.68
W0, H0 = 190.08, 181.44
DX, DY = round(W - W0, 3), round(H - H0, 3)
LEAVES = ["g_phys_fault_u_fault", "u_strip_u_strip_g_zn_0_u_zn", "u_strip_u_strip_g_zn_1_u_zn",
          "u_strip_u_strip_g_zn_2_u_zn", "u_strip_u_strip_g_zn_3_u_zn", "u_strip_u_strip_u_ctl"]
ADAPTER = {"merge": {"ck": [l + "__ck" for l in LEAVES],
                     "g_phys_fault_u_fault__rst_n": [l + "__rst_n" for l in LEAVES]},
           "tie": {"rst_n": "1'b1", **{f"u_strip_u_strip_g_zn_{i}_u_zn__tc": "15'd0" for i in range(4)}},
           "cycles": 0, "note": "astk view ports vs native leaf ports (DIE-KV-69 11-04); tied inputs are unused in the core wrapper"}
# inst: (grow west?, grow south?)
CORES = {"kv3_hub_Eo": {"astk_EN": (True, True), "astk_ES": (True, False)},
         "kv3_hub_Wo": {"astk_WN": (False, True), "astk_WS": (False, False)}}


def shift_point(xy, old, new, west, south):
    """A site inside the new slot moves out across the side it sits on, by the growth."""
    x, y = xy
    if not (new[0] < x < new[2] and new[1] < y < new[3]):
        return None
    nx, ny = x, y
    if west and x < old[0]:
        nx = round(x - DX, 3)
    if not west and x > old[2]:
        nx = round(x + DX, 3)
    if south and y < old[1]:
        ny = round(y - DY, 3)
    if not south and y > old[3]:
        ny = round(y + DY, 3)
    return [nx, ny]


def walk(o, old, new, west, south, moved):
    if isinstance(o, list) and len(o) == 2 and all(isinstance(v, (int, float)) for v in o):
        n = shift_point(o, old, new, west, south)
        if n and n != o:
            moved.append((list(o), n))
            o[:] = n
    elif isinstance(o, list):
        for v in o:
            walk(v, old, new, west, south, moved)


def main():
    plan_path, pins_out, kit_pins = sys.argv[1:4]
    plan = json.load(open(plan_path))
    receipt = {}
    for tn, cores in CORES.items():
        t = plan["partition_types"][tn]
        for hc in t["hard_cores"]:
            if hc["inst"] not in cores:
                continue
            west, south = cores[hc["inst"]]
            ox, oy = hc["origin_um"]
            old = (ox, oy, round(ox + W0, 3), round(oy + H0, 3))
            nx = round(ox - DX, 3) if west else ox
            ny = round(oy - DY, 3) if south else oy
            new = (nx, ny, round(nx + W, 3), round(ny + H, 3))
            assert new[0] >= 0 and new[1] >= 0 and new[2] <= t["outline_um"][0] and new[3] <= t["outline_um"][1], new
            moved = []
            for kind in ("ft_slots", "internal_stations"):
                for s in t[kind]:
                    walk(s.get("bit_sites_um", []), old, new, west, south, moved)
                    walk(s.get("regs_um", []), old, new, west, south, moved)
            hc["origin_um"], hc["outline_um"] = [nx, ny], [W, H]
            hc["native_port_adapter"] = ADAPTER
            hc["note"] += " | DIE-KV-69 11-04: slot 216x211.68, cons view pin table + native_port_adapter"
            cx, cy = round(nx + 108.024, 3), round(ny + 105.84, 3)
            if hc["orient"] in ("MY", "R180"):
                cx = round(nx + W - 108.024, 3)
            if hc["orient"] in ("MX", "R180"):
                cy = round(ny + H - 105.84, 3)
            for tap in t["clock"]["taps"]:
                if tap["name"].startswith(hc["inst"] + ".ck"):
                    tap["xy"] = [cx, cy]
            receipt[hc["inst"]] = dict(origin=[nx, ny], ck_tap=[cx, cy], sites_moved=len(moved))
    pins = []
    for r in json.load(open(kit_pins)):
        row = dict(name=f'{r["bus"]}[{r["bit"]}]', layer=r["layer"], x=r["x"], y=r["y"])
        pins.append(row)
    old_pins = json.load(open(pins_out))
    old_pins["frame"] = f"core R0, origin (0,0), outline {W} x {H}"
    old_pins["source"] += " | DIE-KV-69 11-04: astk cons view, kit dkv64-rfe/astk/eco_cons3/i1 pins.json"
    old_pins["pins"] = pins
    json.dump(old_pins, open(pins_out, "w"), indent=1)
    open(pins_out, "a").write("\n")
    with open(plan_path, "w") as f:
        json.dump(plan, f, indent=1)
        f.write("\n")
    print(json.dumps(dict(receipt=receipt, pins=len(pins)), indent=1))


if __name__ == "__main__":
    main()
