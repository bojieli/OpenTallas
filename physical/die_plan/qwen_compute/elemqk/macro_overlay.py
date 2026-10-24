"""ELEM-QK 10-24: macro placements for Qwen compute plan types whose bound RTL reaches SRAM / ROM macros
(bind.py kit-rtl hard_macros) but whose plan type places none (gen_phys.type_macros needs contents[] with
lef/lib/origin_um, else the G3 kit floats them).  Proposal for the plan owner; G3 kits use a COPY of the plan.

    python3 macro_overlay.py overlay PLAN.json --out overlay.json            # placements -> contents[] entries
    python3 macro_overlay.py apply PLAN.json overlay.json --out plan_copy.json
    python3 macro_overlay.py render PLAN.json overlay.json --pins KIT/<t>/pins.json --type T --png out.png

Origins: x on the 0.054 site grid, y shifted (< one M4 pitch) so every M4 macro pin centre lands on a plan M4 track
(y = 0.024 + k 0.048, symmetric offsets: the same in every R0/MX/MY/R180 instance of the 8.64 lattice).
"""
import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
MAC = {
    "ot_sram_1r1w_32x512_m1": "physical/asap7_memory_macros/ot_sram_1r1w_32x512_m1",
    "ot_sram_1r1w_32x128_m1": "physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1",
    "ot_sram_1r1w_64x512_m1_r2c2": "physical/asap7_memory_macros_v2/ot_sram_1r1w_64x512_m1_r2c2",
    "ot_rom_4096x72_m8": "physical/asap7_memory_macros_v2/ot_rom_4096x72_m8",
    "ot_rom_4096x266_m8": "physical/asap7_memory_macros_v2/ot_rom_4096x266_m8",
    "d2d_sram_1r1w_64x137_m1_r2c2_p192": "physical/asap7_memory_macros_v2/d2d_sram_1r1w_64x137_m1_r2c2_p192",
    "ot_sram_1r1w2c_64x546_m1": "physical/asap7_memory_macros_v2/ot_sram_1r1w2c_64x546_m1",
}

# type -> [(inst (kit netlist path), module, x, y, orient)] before snapping (type frame, um)
B = "u_bound.u_core."
S64 = "ot_sram_1r1w_64x512_m1_r2c2"
PLACE = {
    # tt_ctlm: the closed-kit floorplan of its content qfd_hp13_cpub39_rp_alt (claude/qtile-r-1023 floorplan.json,
    # two SRAM stacks + ROM/small-SRAM tops, no macro at a pin face), moved against the W die edge (no pins) so the
    # plan clock/reset tap (388.8, 259.2) sits 17 um clear of the second stack (at the tile coordinates it fell ON an
    # SRAM, review 10-24); 20.9 um channel; S pins (x <= 308) stay below y 54; E face pins 400 um away.
    "tt_ctlm": [(B + "u_gi.u_cal.g_fifo[0].u_fifo", S64, 8.64, 54.0, "R0"),
                (B + "u_gi.u_cal.g_fifo[1].u_fifo", S64, 8.64, 131.9, "R0"),
                (B + "u_gi.u_cal.g_fifo[2].u_fifo", S64, 8.64, 209.8, "R0"),
                (B + "u_gi.u_cal.g_fifo[3].u_fifo", S64, 8.64, 287.7, "R0"),
                (B + "u_gi.u_cal.g_calrom.u_rom.m0", "ot_rom_4096x266_m8", 8.64, 365.6, "R0"),
                (B + "u_gi.u_cal.g_calrom.u_rom.m1", "ot_rom_4096x266_m8", 8.64, 428.7, "R0"),
                (B + "u_gi.u_cal.g_m[0].u_pm", S64, 200.88, 54.0, "R0"),
                (B + "u_gi.u_cal.g_m[1].u_pm", S64, 200.88, 131.9, "R0"),
                (B + "u_hr.u_24525", S64, 200.88, 209.8, "R0"),
                (B + "u_hr.u_24526", S64, 200.88, 287.7, "R0")] +
               [(B + f"u_hr.u_{24527 + i}", "ot_sram_1r1w_32x128_m1", 200.88, 365.6 + 20.9 * i, "R0")
                for i in range(6)] +
               [(B + "u_gi.g_op.u_leaf.g_op.g_banked.u_rom1", "ot_rom_4096x72_m8", 274.32, 365.6, "R0"),
                (B + "u_gi.g_op.u_leaf.g_op.g_banked.u_rom2", "ot_rom_4096x72_m8", 274.32, 428.7, "R0"),
                (B + "u_gi.g_op.u_leaf.g_op.u_rom", "ot_rom_4096x72_m8", 334.8, 365.6, "R0")],
    # native59: 8 qseat writer SRAMs as two abutted 4-stacks against the W die edge (no pins there), 22.7 um channel,
    # 22 um clear of the clock/reset tap (388.8, 259.2), 86 um above the S face pins.
    "native59": [(B + f"u_qb.u_qseat.g_writer[{4 * c + r}].u_mem", "ot_sram_1r1w_32x512_m1",
                  8.64 + 190.08 * c, 86.4 + 76.3 * r, "R0") for c in range(2) for r in range(4)],
    # glue: d2d replay store (4 x 64x137) stack + sys_face ROMs (3 x 4096x72) stack + embedding code SRAM, on the W die
    # edge between the two clock taps' rows (y 302 / 907), clear of the N/S pin faces.
    "glue": [("u_bound.u_d2d_rom.u_core.u_end.u_link.g_bank[%d].u_store.u_sram.u_m" % i,
              "d2d_sram_1r1w_64x137_m1_r2c2_p192", 8.64, 432.0 + 45.8 * i, "R0") for i in range(4)] +
            [("u_bound.u_sys_face.u_ot_pr_core.u_rom", "ot_rom_4096x72_m8", 86.4, 432.0, "R0"),
             ("u_bound.u_sys_face.u_ot_pr_core.u_cseq.u_tx_rom", "ot_rom_4096x72_m8", 86.4, 495.1, "R0"),
             ("u_bound.u_sys_face.u_ot_pr_core.u_cseq.u_rx_rom", "ot_rom_4096x72_m8", 86.4, 558.2, "R0"),
             ("u_bound.u_embed_prov.store.codes", S64, 8.64, 648.0, "R0")],
}


def lef_info(mod):
    d = MAC[mod]
    t = (REPO / d / f"{mod}.lef").read_text()
    w, h = map(float, re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", t).groups())
    cys = []
    for pin in re.finditer(r"PIN\s+(\S+)(.*?)END\s+\1", t, re.S):
        if pin.group(1) in ("VDD", "VSS"):
            continue
        for m in re.finditer(r"LAYER\s+M4\s*;\s*RECT\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)\s+([\d.\-]+)", pin.group(2)):
            y1, y2 = float(m.group(2)), float(m.group(4))
            cys.append((y1 + y2) / 2)
    return dict(w=w, h=h, lef=f"{d}/{mod}.lef", lib=f"{d}/{mod}_tt.lib", m4=cys)


def snap(x, y, info, pitch=0.048, off=0.024):
    x = round(round(x / 0.054) * 0.054, 4)
    best = None
    for k in range(48):
        dy = k * 0.001
        yy = round(y + dy, 3)
        bad = sum(1 for c in info["m4"] if abs(((yy + c - off) / pitch) - round((yy + c - off) / pitch)) > 1e-3)
        if best is None or bad < best[1]:
            best = (yy, bad)
        if bad == 0:
            break
    return x, best[0], best[1]


def overlay(plan):
    raw = json.loads(Path(plan).read_text())
    out = {}
    for tn, rows in PLACE.items():
        w, h = raw["partition_types"][tn]["outline_um"]
        ents, boxes = [], []
        for inst, mod, x, y, o in rows:
            info = lef_info(mod)
            X, Y, bad = snap(x, y, info)
            if bad:
                raise SystemExit(f"{tn} {inst}: {bad} M4 pins off track at any shift")
            if X < 0 or Y < 0 or X + info["w"] > w or Y + info["h"] > h:
                raise SystemExit(f"{tn} {inst}: outside the outline")
            for (a, b, c, d) in boxes:
                if X < c - 1e-6 and a < X + info["w"] - 1e-6 and Y < d - 1e-6 and b < Y + info["h"] - 1e-6:
                    raise SystemExit(f"{tn} {inst}: overlaps another macro")
            boxes.append((X, Y, X + info["w"], Y + info["h"]))
            ents.append(dict(inst=inst, module=mod, status="reuse", lef=info["lef"], lib=info["lib"],
                             origin_um=[X, Y], outline_um=[info["w"], info["h"]], orient=o,
                             note="ELEM-QK 10-24 macro site (macro_overlay.py; M4 pins on plan tracks)"))
        out[tn] = ents
    return out


def apply(plan, ov):
    raw = json.loads(Path(plan).read_text())
    for tn, ents in ov.items():
        raw["partition_types"][tn]["contents"] = list(raw["partition_types"][tn]["contents"]) + ents
    return raw


def render(plan, ov, tn, pins, png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    raw = json.loads(Path(plan).read_text())
    t = raw["partition_types"][tn]
    w, h = t["outline_um"]
    fig, ax = plt.subplots(figsize=(10, 10 * h / w + 0.5))
    ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=1.5))
    P = json.loads(Path(pins).read_text())
    col = {"M4": "tab:blue", "M5": "tab:green", "M6": "tab:orange", "M7": "tab:red"}
    for p in P:
        ax.plot([p["x"]], [p["y"]], ".", ms=1, color=col.get(p["layer"], "k"))
    for e in ov.get(tn, []):
        (x, y), (mw, mh) = e["origin_um"], e["outline_um"]
        ax.add_patch(Rectangle((x, y), mw, mh, fc="lightgrey", ec="k", lw=0.6))
        ax.text(x + 2, y + mh / 2, e["module"].replace("ot_", "")[:18], fontsize=5)
    for tp in t["clock"].get("taps", []) or [dict(name="tap", xy=t["clock"]["tap_um"])]:
        ax.plot([tp["xy"][0]], [tp["xy"][1]], "r*", ms=10)
    if "reset" in t:
        ax.plot([t["reset"]["tap_um"][0]], [t["reset"]["tap_um"][1]], "mx", ms=8)
    ax.set_xlim(-20, w + 20)
    ax.set_ylim(-20, h + 20)
    ax.set_aspect("equal")
    ax.set_title(f"{tn} {w}x{h} um: {len(P)} pins (M4 blue/M5 green/M6 orange/M7 red), macros grey, clock taps *")
    fig.savefig(png, dpi=150, bbox_inches="tight")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("overlay", "apply", "render"))
    ap.add_argument("plan")
    ap.add_argument("ov", nargs="?")
    ap.add_argument("--out")
    ap.add_argument("--type")
    ap.add_argument("--pins")
    ap.add_argument("--png")
    a = ap.parse_args(argv)
    if a.cmd == "overlay":
        Path(a.out).write_text(json.dumps(overlay(a.plan), indent=1) + "\n")
    elif a.cmd == "apply":
        Path(a.out).write_text(json.dumps(apply(a.plan, json.loads(Path(a.ov).read_text())), indent=1) + "\n")
    else:
        render(a.plan, json.loads(Path(a.ov).read_text()), a.type, a.pins, a.png)


if __name__ == "__main__":
    sys.exit(main())
