#!/usr/bin/env python3
"""DIE-HBM-28-K: opstore_a static macro grid + core_macros KNOWN entry (plan DELTA only, not applied).

    python3 opstore_a_static.py WT PLANDIR KIT ELAB_LIST OUTDIR

WT        sparse worktree with tools/die_plan/kit_contract.py + physical/die_plan/hbm/core_macros_fix.py (read only)
PLANDIR   plan dir with die_plan.json + core_macros.json (read only)
KIT       HBM-CORES-KITS-24 opstore_a kit (read only; copied into OUTDIR/stage for the kit_contract checks)
ELAB_LIST yosys flatten list (select -list t:ot_sram*) of the kit RTL

Same method as DIE-HBM-26 mk_static.py opstore_b: 4 columns of ot_sram_1r1w_256x256_m2_r2c2 (172.824 x 41.064)
at col channel 12.096 centred on x = 380.16 (identical column x to opstore_b), bands of 4 rows, equal horizontal
logic channels, y snapped to 0.012 mod 0.048.  opstore_a has 2 bands (g_operand[0], g_operand[1]); bank b -> column
b // 4, row b % 4 (opstore_b: bank 4c+r).
"""
import json
import os
import re
import shutil
import sys

WT, PLAN, KIT, ELAB, OUT = sys.argv[1:6]
sys.path.insert(0, os.path.join(WT, "tools/die_plan"))
sys.path.insert(0, os.path.join(WT, "physical/die_plan/hbm"))
import kit_contract as K          # noqa: E402
import core_macros_fix as F       # noqa: E402

CORE = "ot_hgi_sfu_core_split3__opstore_a"
MASTER, W, H = "ot_sram_1r1w_256x256_m2_r2c2", 172.824, 41.064
OUTLINE = [760.32, 483.84]        # 88 x 56 on the 8.64 lattice


def snap_y(y):
    return round(0.012 + round((y - 0.012) / 0.048) * 0.048, 3)


def snap_x(x):
    return round(round(x / 0.108) * 0.108, 3)


def spec():
    span = 4 * W + 3 * 12.096
    x0 = snap_x(380.16 - span / 2)
    xs = [round(x0 + i * (W + 12.096), 3) for i in range(4)]
    band = 4 * H + 3 * 0.024
    hc = OUTLINE[1] - 2 * 4.32
    ch = (hc - 2 * band) / 3
    rows = []
    for g in range(2):
        yb = 4.32 + ch + g * (band + ch)
        for b in range(16):
            c, r = b // 4, b % 4
            rows.append(dict(name=f"u_fcore.u_core.u_x.u_core.u_engine.u_memory.g_operand[{g}].u_group.g_bank[{b}]"
                                  ".u_b.genblk1.genblk1.g_m11.u_m",
                             master=MASTER, origin_um=[xs[c], snap_y(yb + r * (H + 0.024))], orient="R0"))
    basis = (f"DIE-HBM-28-K static grid (DIE-HBM-26 opstore_b method): 4 col x 8 row (2 bands g_operand[0]/"
             f"g_operand[1] of 4 rows; bank b -> col b//4 row b%4), col channel 12.096 (opstore_b column x), "
             f"{ch:.3f}-um logic channels, centred on x=380.16; 32 x {MASTER} from yosys flatten of the "
             f"HBM-CORES-KITS-24 kit RTL")
    return dict(outline_um=OUTLINE, macros=rows, basis=basis), ch


def main():
    os.makedirs(OUT, exist_ok=True)
    sp, ch = spec()
    names = {l.strip().split("/", 1)[1] for l in open(ELAB) if l.strip()}
    got = {m["name"] for m in sp["macros"]}
    assert got == names, (sorted(names - got)[:3], sorted(got - names)[:3])
    sizes = F.lef_sizes(os.path.join(KIT, "macros"))
    assert tuple(sizes[MASTER]) == (W, H), sizes[MASTER]
    rows = [dict(name=m["name"], master=m["master"], orient="R0",
                 rect_um=[round(m["origin_um"][0], 4), round(m["origin_um"][1], 4),
                          round(m["origin_um"][0] + W, 4), round(m["origin_um"][1] + H, 4)]) for m in sp["macros"]]
    err, ncols = F.channel_errors(rows, OUTLINE)
    assert not err, err
    cm = json.load(open(os.path.join(PLAN, "core_macros.json")))
    old = cm["cores"][CORE]
    entry = dict(status="KNOWN", outline_um=OUTLINE, basis=sp["basis"], macros=rows, channel_rule_um=F.CH,
                 previous=dict(status=old.get("status"), why=old.get("why"), outline_um=old.get("outline_um")))
    json.dump({CORE: sp}, open(os.path.join(OUT, "opstore_a_static_sites.json"), "w"), indent=1)

    # fit arithmetic
    marea = 32 * W * H
    fit = dict(macros=32, master=MASTER, macro_area_um2=round(marea, 1),
               core_macros_outline=[388.8, 345.6], core_macros_outline_area=round(388.8 * 345.6, 1),
               die_plan_outline=[390.528, 436.32], die_plan_outline_area=round(390.528 * 436.32, 1),
               die_plan_core_area=round((390.528 - 8.64) * (436.32 - 8.64), 1),
               proposed_outline=OUTLINE, proposed_area=round(OUTLINE[0] * OUTLINE[1], 1),
               proposed_macro_pct=round(100 * marea / (OUTLINE[0] * OUTLINE[1]), 2), band_channel_um=round(ch, 3),
               floor_10p8_outline=[760.32, 371.52])

    # kit_contract checks on a staged kit copy at the proposed outline (clock entry = outline centre, as opstore_b)
    kd = os.path.join(OUT, "stage", os.path.basename(KIT.rstrip("/")))
    if os.path.exists(kd):
        shutil.rmtree(kd)
    shutil.copytree(KIT, kd, symlinks=True)
    lines = ["foreach {inst master x y orient} {"]
    for m in sp["macros"]:
        inst = m["name"].replace("[", "\\[").replace("]", "\\]")
        lines.append(f"  {{{inst}}} {m['master']} {m['origin_um'][0]} {m['origin_um'][1]} {m['orient']}")
    lines.append("} { place_macro -macro_name $inst -location [list $x $y] -orientation $orient }")
    open(os.path.join(kd, "macro_placement.tcl"), "w").write("\n".join(lines) + "\n")
    cfg = open(os.path.join(kd, "config.mk")).read()
    cfg = re.sub(r"export DIE_AREA = .*", f"export DIE_AREA = 0 0 {OUTLINE[0]} {OUTLINE[1]}", cfg)
    cfg = re.sub(r"export CORE_AREA = .*", f"export CORE_AREA = 4.32 4.32 {OUTLINE[0] - 4.32:.3f} "
                 f"{OUTLINE[1] - 4.32:.3f}", cfg)
    cfg += "\nexport MACRO_PLACEMENT_TCL = /work/macro_placement.tcl\n"
    open(os.path.join(kd, "config.mk"), "w").write(cfg)
    entries = [("plan-centre", "clk", OUTLINE[0] / 2, OUTLINE[1] / 2)]
    chk = {}
    e, i = K.macro_channels(kd, PLAN); chk["macro_channels"] = dict(verdict="FAIL" if e else "PASS", err=e[:3], info={k: v for k, v in i.items() if k != "min_channel_note"})
    e, i = K.clock_entry_clear(kd, PLAN, entries=entries); chk["clock_entry_clear(centre)"] = dict(verdict="FAIL" if e else "PASS", err=e[:3], info=i)
    e, i = K.clock_entry_clear(kd, PLAN); chk["clock_entry_clear(kit io, stale outline)"] = dict(verdict="FAIL" if e else "PASS", err=e[:3], info=i)
    e, i = K.macro_pin_grid(kd, PLAN); chk["macro_pin_grid"] = dict(verdict="FAIL" if e else "PASS", err=e[:3], info=i)
    e, i = K.island_macro_clear(kd); chk["island_macro_clear"] = dict(verdict="FAIL" if e else "PASS", err=e[:2], info=i)

    delta = dict(schema="opentallas.hbm.plan_delta.v1", lane="DIE-HBM-28-K", item="opstore_a core_macros KNOWN",
                 status="PROPOSED, NOT APPLIED; needs the q_b113 / q_b113__physical_v1 hard_core outline change "
                        "(no slot at current packing, see fit.q_b113)",
                 core_macros={CORE: entry},
                 die_plan_hard_cores=[dict(type=t, inst="u_sfucore_Q_opstore_a", outline_um_old=[390.528, 436.32],
                                           outline_um_new=OUTLINE) for t in ("q_b113", "q_b113__physical_v1")],
                 fit=fit, kit_contract_checks=chk)
    json.dump(delta, open(os.path.join(OUT, "opstore_a_delta.json"), "w"), indent=1)
    print(json.dumps(dict(fit=fit, checks={k: (v["verdict"], v["err"][:1]) for k, v in chk.items()}), indent=1))

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig, ax = plt.subplots(figsize=(10, 6.6))
    ax.add_patch(Rectangle((0, 0), *OUTLINE, fill=False, lw=2))
    ax.add_patch(Rectangle((4.32, 4.32), OUTLINE[0] - 8.64, OUTLINE[1] - 8.64, fill=False, ls="--", lw=.8))
    ax.add_patch(Rectangle((0, 0), 390.528, 436.32, fill=False, ec="red", lw=1.5, ls=":"))
    ax.text(5, 425, "current plan outline 390.528x436.32", color="red", fontsize=8)
    for r in rows:
        x0, y0, x1, y1 = r["rect_um"]
        g = 0 if "g_operand[0]" in r["name"] else 1
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=("#9ecae1" if g == 0 else "#fdae6b"), ec="k", lw=.5))
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, re.search(r"g_bank\[(\d+)\]", r["name"]).group(1) + f"/op{g}",
                ha="center", va="center", fontsize=6)
    ax.plot([OUTLINE[0] / 2], [OUTLINE[1] / 2], "r*", ms=12)
    ax.set_xlim(-10, OUTLINE[0] + 10); ax.set_ylim(-10, OUTLINE[1] + 10); ax.set_aspect("equal")
    ax.set_title(f"opstore_a proposed {OUTLINE[0]}x{OUTLINE[1]}: 32 x {MASTER}, clk entry * at centre")
    fig.savefig(os.path.join(OUT, "opstore_a_static.png"), dpi=110, bbox_inches="tight")


if __name__ == "__main__":
    main()
