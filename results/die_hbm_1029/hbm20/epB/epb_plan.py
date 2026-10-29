#!/usr/bin/env python3
"""DIE-HBM-20-EPB plan delta (opt-in candidate, not the plan of record): hfd_ep_static WIDER SLOT.
    epb_plan.py SRC_PLANDIR OUT_PLANDIR KIT_PLAN_PINS_JSON W H TAG
OUT_PLANDIR must be a hard-link copy (cp -al) of SRC_PLANDIR; every file this script changes is rewritten via
os.replace (breaks the link, never edits the source).  Changes, for the 6 hfd_ep_static instances in 5 types:
outline_um (+ contents outline), origin x (NW_io / NE_io u_ep_N* -> x 108 so the 432-um core stays inside the 648-um
partition; others keep origin), pins_file (new per-type pin table = the probe kit's plan pins), core_macros.json entry,
clock_entries.json (centre entry = the probe kit's island 0) and clock taps xy, internal_stations of the u_lk <-> u_ep
links (EP end moved to the new S-face pin centroid; regs re-spaced on a Z route, hops <= 360 um)."""
import json, math, os, sys
from pathlib import Path

SRC, OUT, KPINS, W, H, TAG = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), sys.argv[6]
HOP = 360.0
ENTRY = json.loads(sys.argv[7]) if len(sys.argv) > 7 else None   # [x, y] island-0 centre in the core frame
MOVE_X = {"u_ep_N0": float(os.environ.get("EPB_NX", 112.32)), "u_ep_N2": float(os.environ.get("EPB_NX", 112.32))}   # 8.64-um core lattice (G0C hard_cores)


def wr(p, obj, indent=None):
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=indent))
    os.replace(tmp, p)


def main():
    plan = json.loads((OUT / "die_plan.json").read_text())
    kp = json.loads(KPINS.read_text())["pins"]
    pf = f"cores/hfd_ep_static__{W:.2f}x{H:.2f}__{TAG}.json"
    tab = [dict(name=p["name"], layer=p["layer"], x=p["x"], y=p["y"]) for p in kp]
    tmp = OUT / (pf + ".tmp"); tmp.write_text(json.dumps(tab)); os.replace(tmp, OUT / pf)
    cen = {}
    for p in tab:
        b = p["name"].split("[")[0]
        cen.setdefault(b, []).append((p["x"], p["y"]))
    cen = {b: (sum(x for x, _ in v) / len(v), sum(y for _, y in v) / len(v)) for b, v in cen.items()}
    clk = [p for p in tab if p["name"] == "clk"][0]
    entry = ENTRY or [round(clk["x"] - 0.024, 3), clk["y"]]
    moved = {}
    for tn, T in plan["partition_types"].items():
        for hc in T.get("hard_cores", []):
            if hc.get("module") != "hfd_ep_static":
                continue
            o_old = list(hc["origin_um"]); w_old = list(hc["outline_um"])
            ox = MOVE_X.get(hc["inst"], hc["origin_um"][0]); oy = hc["origin_um"][1]
            hc["origin_um"] = [ox, oy]; hc["outline_um"] = [W, H]; hc["pins_file"] = pf
            hc["note"] = hc.get("note", "") + f" | DIE-HBM-20-EPB {TAG}: WIDER SLOT {W:.2f}x{H:.2f} 2x2 SRAM (logic band S, heavy SRAM pin sides into the mid channel), SerDes pins S, tx_frame W, rx_pin_flit E (probe kit epyc2 die-hbm-20/epB)"
            moved[(tn, hc["inst"])] = (o_old, w_old, [ox, oy])
            for c in T.get("contents", []):
                if c.get("inst") == hc["inst"]:
                    c["origin_um"] = [ox, oy]; c["outline_um"] = [W, H]
            for tp in (T.get("clock") or {}).get("taps", []) or []:
                if tp.get("name") in (hc["inst"], hc["inst"] + ".clk"):
                    tp["xy"] = [round(ox + entry[0], 3), round(oy + entry[1], 3)]
            # internal stations of the u_lk <-> u_ep links
            bx = (o_old[0], o_old[1], o_old[0] + w_old[0], o_old[1] + w_old[1])
            for s in T.get("internal_stations", []):
                conn = s.get("conn", "")
                if hc["inst"] not in conn.split("|")[0].split(".")[0] + "|" + conn.split("|")[-1]:
                    continue
                port = "sd_rx" if (".rx|" in conn or ".sd_rx|" in conn) else "sd_tx" if (".tx|" in conn or ".sd_tx|" in conn) else "sd_st"
                new = (round(ox + cen[port][0], 3), round(oy + cen[port][1], 3))
                def inside(p):
                    return bx[0] - 1 <= p[0] <= bx[2] + 1 and bx[1] - 1 <= p[1] <= bx[3] + 1
                if inside(s["to_um"]):
                    s["to_um"] = list(new)
                elif inside(s["from_um"]):
                    s["from_um"] = list(new)
                else:
                    continue
                a, b = s["from_um"], s["to_um"]
                ym = round((a[1] + b[1]) / 2, 3)
                pts = [tuple(a), (a[0], ym), (b[0], ym), tuple(b)]
                L = sum(abs(pts[i + 1][0] - pts[i][0]) + abs(pts[i + 1][1] - pts[i][1]) for i in range(3))
                n = max(1, math.ceil(L / HOP) - 1)
                regs = []
                for k in range(1, n + 1):
                    d = L * k / (n + 1)
                    for i in range(3):
                        seg = abs(pts[i + 1][0] - pts[i][0]) + abs(pts[i + 1][1] - pts[i][1])
                        if d <= seg or i == 2:
                            f = d / seg if seg else 0
                            regs.append([round(pts[i][0] + f * (pts[i + 1][0] - pts[i][0]), 3), round(pts[i][1] + f * (pts[i + 1][1] - pts[i][1]), 3)])
                            break
                        d -= seg
                s["regs_um"] = regs
                s["note"] = s.get("note", "") + f" | DIE-HBM-20-EPB {TAG}: EP end -> S-face {port} centroid, {n} station(s) on a Z route ({L:.0f} um)"
    wr(OUT / "die_plan.json", plan)
    cm = json.loads((OUT / "core_macros.json").read_text())
    e = cm["cores"]["hfd_ep_static"]
    e["outline_um"] = [W, H]
    e["basis"] = f"DIE-HBM-20-EPB {TAG} wider slot probe"
    e["r15_note"] = f"4 SRAM 2x2 (A col MY, B col R0, heavy pin edges into the mid channel), logic band S; probe kit epyc2 /srv/opentallas-scratch2/claude/die-hbm-20/epB"
    wr(OUT / "core_macros.json", cm)
    ce = json.loads((OUT / "clock_entries.json").read_text())
    n = 0
    for tn, d in ce.items():
        if not isinstance(d, dict):
            continue
        for inst, v in d.items():
            if isinstance(v, dict) and v.get("module") == "hfd_ep_static":
                v["xy_um"] = list(entry); v["island_um"] = [entry[0] - 4.32, entry[1] - 4.32, entry[0] + 4.32, entry[1] + 4.32]
                v["source"] = v.get("source", "") + f" | DIE-HBM-20-EPB {TAG}: S-band centre entry"
                n += 1
    wr(OUT / "clock_entries.json", ce)
    print("EPB plan", TAG, "moved", len(moved), "clock entries", n, "pins file", pf)
    for k, v in moved.items():
        print(" ", k, "origin", v[0], "->", v[2])


if __name__ == "__main__":
    main()
