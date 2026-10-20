#!/usr/bin/env python3
"""S81-TILES-B (10-20) COLL v8 lane kits dscoll_lane_{w,e}_s6c: structural successor of s5/s5c.

Root cause (s5c W/E post-CTS, ep9 *-20261020-030127): macro->reg TT -511 ps (W, u_sko.l_data <- RX FIFO q) and -626 ps
(E, u_ep.b_pay <- replay q).  The s5 macro map put the 18 RX-FIFO banks in the 6 columns FARTHEST from the core face
(x 43..475 for W: the read data crossed up to ~680 um to the lo_d face registers in one cycle, reach > 405) and the
replay buffer on the core side, far from the gearbox it feeds.  Same RTL, same outline / band / face columns / lattice;
only the macro map changes, ordered along the data flow (W lane, link face W -> core face E):
  col 43.2        gearbox slot store (10 x 32x64, 5 under + 5 over the band)   <- rx / tx link pins on the W face
  col 129.6..302.4 replay buffer (18 x 256x64, 3 cols x 6 rows)               b_pay -> TX -> gearbox (<= 300 um)
  col 388.8       credit-rx landing head (9 x 32x64)                          <- li_d (E face, <= 340 um)
  col 475.2..648  RX FIFO (18 x 256x64, 3 cols x 6 rows)                       q -> u_sko l_data at the E face (<= 250 um)
E lane = column mirror (x' = 691.2 - x, orientation as s5c's mirror).  Rows: big macros y 43.2/129.6/216 (MX) under the
band and 345.6/432/518.4 (R0) over it; small macros at 43.2 pitch.  Pins face the band as in s5c.
"""
import copy, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
BIG_B, BIG_T = [43.2, 129.6, 216.0], [345.6, 432.0, 518.4]
SM_B, SM_T = [43.2, 86.4, 129.6, 172.8, 216.0], [345.6, 388.8, 432.0, 475.2, 518.4]
MIRROR = 691.2
ORI_E = {"MX": "R180", "R0": "MY"}


def slots_big(cols):
    return [(x, y, "MX") for x in cols for y in BIG_B] + [(x, y, "R0") for x in cols for y in BIG_T]


def slots_small(col, n):
    s = [(col, y, "MX") for y in SM_B] + [(col, y, "R0") for y in SM_T]
    return s[:n]


def place(side):
    s = json.loads((ROOT / f"physical/ref_tile/dscoll_lane_{side}_s5c/spec.json").read_text())
    groups = {"gb": [], "rb": [], "ski": [], "fifo": []}
    for m in s["macros"]:
        i = m["inst"]
        k = "gb" if "u_gb." in i else "rb" if "g_rb" in i else "ski" if "u_ski." in i else "fifo" if "fifo" in i else None
        assert k, i
        groups[k].append(m)
    assert [len(groups[k]) for k in ("gb", "rb", "ski", "fifo")] == [10, 18, 9, 18]
    plan = {"gb": slots_small(43.2, 10), "rb": slots_big([129.6, 216.0, 302.4]),
            "ski": slots_small(388.8, 9), "fifo": slots_big([475.2, 561.6, 648.0])}
    for k, ms in groups.items():
        for m, (x, y, o) in zip(ms, plan[k]):
            if side == "e":
                x, o = round(MIRROR - x, 4), ORI_E[o]
            m["at"], m["orient"] = [x, y], o
    name = f"dscoll_lane_{side}_s6c"
    s["name"] = name
    s["structural_change"] = (__doc__.strip() + " " + s.get("structural_change", ""))[:6000]
    j = s["job"]
    j.update(owner="Claude:S81-TILES-B", branch="claude/s81-coll5-1020", tag="s6c",
             views_to=f"physical/ref_tile/{name}/views", record_to=f"results/rtl/ref_tile/{name}",
             purpose="S81-COLL v8 s6c: s5c with the macro map ordered along the data flow (RX FIFO at the core face, "
                     "replay at the gearbox): s5c macro->reg -511/-626 ps reach fix. SAFE checklist in kit README.")
    return name, s


if __name__ == "__main__":
    for side in ("w", "e"):
        name, s = place(side)
        d = ROOT / "physical/ref_tile" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
        print("wrote", d / "spec.json")
