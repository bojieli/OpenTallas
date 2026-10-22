#!/usr/bin/env python3
"""XS p192 lattice successors: full channels on every macro face."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    base = json.loads((ROOT / "physical/ref_tile/smh_xs_ring_p192c_1019/spec.json").read_text())
    for label, height, rows, km in (("d", 388.8, (43.2, 172.8), 32),
                                     ("e", 432.0, (86.4, 216.0), 64)):
        s = copy.deepcopy(base)
        name = f"smh_xs_p192{label}_lattice"
        s["name"] = name
        s["outline"] = {"w": 475.2, "h": height}
        for idx, macro in enumerate(s["macros"]):
            if idx < 4:
                macro["at"][1] = rows[idx % 2]
            else:
                k = idx - 4
                macro["at"][1] = (43.2 if label == "d" else 86.4) + 86.4 * (k if k < 4 else k - 4)
            macro["at_exact"] = True
        shift = 0 if label == "d" else 43.2
        s["route"]["pin_balance"] = {"group_max": 1, "h": "M4", "v": "M5"}
        s["pin_ranges"] = {
            "o_iw": [43.2, 194.688], "o_ix": [259.2, 410.688],
            "clk": [237.06, 238.14], "rst_a": [240.3, 241.38],
            "xs_a1": [3.24, 7.56], "xs_a2": [9.72, 12.96],
            "xs_g1": [15.12, 17.28], "xs_g2": [19.44, 21.6],
            "o_iv_b": [23.76, 24.84], "o_ifirst": [25.92, 27.0],
            "o_ifp4": [28.08, 29.16], "o_ilast": [30.24, 31.32],
            "o_itag": [33.48, 40.176], "bk1": [43.2, 440.448],
            "rl1": [43.2 + shift, 345.6 + shift],
            "ohl1": [350.0 + shift, 360.0 + shift],
            "o_ifirst_e": [160.0 + shift, 161.08 + shift],
            "o_ilast_e": [163.24 + shift, 164.32 + shift],
            "o_itag_e": [166.48 + shift, 173.176 + shift],
            "o_iv_f": [175.336 + shift, 176.416 + shift],
        }
        s["orfs_vars"]["OT_CKKM_K"] = str(km)
        s["std_area_um2"] = 11255.0  # Actual mapped original p192c source, unchanged RTL.
        s["fill_reason"] = {"pin_bound": (
            "XS lattice successor: width475.2 for 2097S/1652N pins at0.192um;"
            " seven ring SRAMs use four86.4um-pitch rows (all43.2 origins),"
            " leaving46.44um N/S channels and>=34.8um W/E signal/PG channels."
            " No compact3.24um slivers. Source-mapped std11255um2, macros44903um2;"
            " low fill is the price of actual lattice/channels, not a smaller pilot."
        )}
        s["job"]["branch"] = "codex/hbm-xs-p192c-release-1020"
        s["job"]["tag"] = name
        s["job"]["purpose"] += " Full43.2 lattice and86.4 ring-row pitch, zero RTL/age changes."
        s["job"]["extra_paths"].append("results/arch/codex_xs_lattice_1020")
        s["structural_change"] = (
            "Original p192c READMEs claimed43.2 lattice, but five explicit ring"
            "origins y83.184/123.168/163.152 were stock-track aligned, off43.2."
            " All11 origins are now exact43.2 multiples; ring pitch86.4 gives"
            "full46.44um N/S channels, all W/E contacts keep>=34.8um corridors."
            f" Outline475.2x{height}, km{km}; no RTL, memory contract, or cycle changes."
        )
        kd = ROOT / "physical/ref_tile" / name
        kd.mkdir(parents=True, exist_ok=True)
        (kd / "spec.json").write_text(json.dumps(s, indent=1) + "\n")
        print(kd / "spec.json")


if __name__ == "__main__":
    main()
