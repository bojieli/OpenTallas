"""HBM-CORE-WBQ-1 (2026-11-12): stage the clock-pin landing guard into an HBM core kit.

Root cause (ot_wbq_root_g0, OBS-SYNC-1): an interior M5 clock entry has every M6 track over its span taken by the core's own
signal routing, so the parent router has no M6 landing for VIA56 (DRT-0073 with any view).  The guard keeps those M6
tracks free during GRT/DRT (physical/common_flow/clock_pin_landing_guard.tcl; added pre-GRT, removed post-DRT).

    python3 clock_pin_landing.py KITDIR PORT [PORT ...]     stage into an existing kit (idempotent)
    gen_core_kit_hbm.py --clock-pin-landing on               the generator calls stage() with the kit's clock ports
"""
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
GUARD = REPO / "physical/common_flow/clock_pin_landing_guard.tcl"
PRE = "core_grt_pre.tcl"
POST = "core_drt_post.tcl"
HOOK = "export POST_DETAIL_ROUTE_TCL = /work/core_drt_post.tcl"


def end_guards(box_um, clear_um=0.06, pad_um=0.064, x_um=0.1):
    """the two M4 end-guard rects (um) over the ends of one M5 clock pin box (x0, y0, x1, y1), as the tcl computes them"""
    x0, y0, x1, y1 = box_um
    return [(x0 - x_um, y1 - clear_um, x1 + x_um, y1 + pad_um), (x0 - x_um, y0 - pad_um, x1 + x_um, y0 + clear_um)]


def stage(kit, ports, pad_x_um=1.0, pad_y_um=0.064, end_clear_um=0.06, end_pad_um=0.064, end_x_um=0.1):
    kit = Path(kit)
    ports = sorted(set(ports))
    if not ports:
        raise ValueError("clock pin landing guard: no clock ports")
    shutil.copyfile(GUARD, kit / "clock_pin_landing_guard.tcl")
    env = (f"set ::env(OT_CPL_PORTS) {{{' '.join(ports)}}}\nset ::env(OT_CPL_PAD_X_UM) {pad_x_um:g}\n"
           f"set ::env(OT_CPL_PAD_Y_UM) {pad_y_um:g}\n"
           f"set ::env(OT_CPL_END_CLEAR_UM) {end_clear_um:g}\nset ::env(OT_CPL_END_PAD_UM) {end_pad_um:g}\n"
           f"set ::env(OT_CPL_END_X_UM) {end_x_um:g}\n")
    pre = kit / PRE
    t = pre.read_text() if pre.exists() else ""
    t = re.sub(r"# OT_CPL_BEGIN.*?# OT_CPL_END\n", "", t, flags=re.S)
    pre.write_text(t + "# OT_CPL_BEGIN\n" + env + "set ::env(OT_CPL_MODE) add\nsource /work/clock_pin_landing_guard.tcl\n# OT_CPL_END\n")
    (kit / POST).write_text("# OT_CPL_BEGIN\n" + env + "set ::env(OT_CPL_MODE) remove\nsource /work/clock_pin_landing_guard.tcl\n# OT_CPL_END\n")
    cfg = kit / "config.mk"
    c = cfg.read_text()
    if "POST_DETAIL_ROUTE_TCL" in c and HOOK not in c:
        raise ValueError("config.mk already has another POST_DETAIL_ROUTE_TCL hook")
    if HOOK not in c:
        cfg.write_text(c.rstrip("\n") + "\n# HBM-CORE-WBQ-1: clock-pin landing guard (M6 route exclusion over interior clock pins, GRT+DRT only)\n" + HOOK + "\n")
    return dict(ports=ports, pad_x_um=pad_x_um, pad_y_um=pad_y_um, end_clear_um=end_clear_um)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    print(stage(sys.argv[1], sys.argv[2:]))
