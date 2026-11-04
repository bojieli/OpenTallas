"""DIE-KV-64/RF-E 11-03 AHUB-CONS (OWNER 18:57 conservative form): qkd_ahub re-composed around the conservative ZH.

qkd_ahub's own logic already meets timing (dkv63-ahub/ahub_preview: TT +22.51, FF +3.88, slew 0); it is NOT SIGNED
only because its hard children are unsigned ref_tile views (UNEXPANDED_CHILD_ETM).  The form keeps the AHUB kit
(RTL, pins, outline 604.8 x 440.64, PDN, anchors) and changes only the children:
  * ot_nhb_zh -> the RF-CONS ZH 162 x 162 (zh_rf1.py --cons-side 162).  Each instance origin moves by -10.8 um along
    every mirrored axis (R180: x,y; MX: y; MY: x; R0: none) so the 268 S-face input pins keep their parent position;
    the 68 output pins move 10.8 um outward with the grown edge.  No anchor falls in the grown footprint + halo.
  * ot_qkh_recip_leaf -> its SIGNED routed view (same LEF size / 71 pins).
The ZH view is staged from a given dir (provisional abstract until ZH-CONS signs; then re-sign the routed AHUB).
"""
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

D = 10.8
SHIFT = {"R180": (-D, -D), "MX": (0.0, -D), "MY": (-D, 0.0), "R0": (0.0, 0.0)}


def build(src, out, zh_view, recip_view, repo):
    src, out, zh_view, recip_view, repo = map(Path, (src, out, zh_view, recip_view, repo))
    kd = out / src.name
    if kd.exists():
        raise SystemExit(f"ahub_cons: {kd} exists")
    shutil.copytree(src, kd, ignore=shutil.ignore_patterns("run", "lec", "lec_async.*", "physical_completion",
                                                           "__pycache__", "*.log", "face_guard*.json", "1_synth_odb.v"))
    for m, v in (("ot_nhb_zh", zh_view), ("ot_qkh_recip_leaf", recip_view)):
        for suf in (".lef", "_tt.lib", "_ff.lib"):
            shutil.copyfile(v / f"{m}{suf}", kd / "macros" / f"{m}{suf}")
        if (v / "provenance.json").is_file():
            shutil.copyfile(v / "provenance.json", kd / "macros" / f"{m}.provenance.json")
    if "SIZE 162 BY 162" not in (kd / "macros/ot_nhb_zh.lef").read_text():
        raise SystemExit("ahub_cons: ZH view is not the 162 x 162 RF-CONS outline")
    mp = (kd / "macro_place.tcl").read_text()
    moved = []
    pat = re.compile(r"\$i setOrient (R180|MX|MY|R0)\n(.*?)round\(([\d.]+) \* \$dbu\)(.*?)round\(([\d.]+) \* \$dbu\)(.*?)\n"
                     r"(\$i setPlacementStatus FIRM\nputs \"hard child (g_zh\[\d\]\.u_zh) -> \[\$i getName\] \1 at )([\d.]+) ([\d.]+)\"",
                     re.S)

    def sub(m):
        o, x, y = m.group(1), float(m.group(3)), float(m.group(5))
        dx, dy = SHIFT[o]
        nx, ny = round(x + dx, 3), round(y + dy, 3)
        moved.append(dict(inst=m.group(8), orient=o, old=[x, y], new=[nx, ny]))
        return (f"$i setOrient {o}\n{m.group(2)}round({nx:g} * $dbu){m.group(4)}round({ny:g} * $dbu){m.group(6)}\n"
                f"{m.group(7)}{nx:g} {ny:g}\"")
    mp = pat.sub(sub, mp)
    if len(moved) != 4:
        raise SystemExit(f"ahub_cons: macro_place.tcl ZH sites not in the expected form ({len(moved)})")
    (kd / "macro_place.tcl").write_text("# AHUB-CONS (ahub_cons.py): ZH origins shifted for the 162 x 162 RF-CONS ZH\n" + mp)
    sys.path.insert(0, str(repo / "tools/die_plan"))
    import lec as LEC
    import gen_core_kit_kv as GEN
    prov = LEC._repo_provenance(repo)
    fz = json.loads((kd / "freeze.json").read_text())
    fz.update(source_commit=prov.get("commit"),
              ahub_cons=dict(derived_from=str(src), derived_from_kit_hash=fz.get("kit_hash"), zh_sites=moved,
                             zh_view=str(zh_view), recip_view=str(recip_view),
                             zh_lef_sha256=hashlib.sha256((kd / "macros/ot_nhb_zh.lef").read_bytes()).hexdigest()))
    fz["kit_hash"] = GEN.kit_hash(kd)
    (kd / "freeze.json").write_text(json.dumps(fz, indent=1) + "\n")
    LEC.write_kit_provenance(kd, repo, provenance=prov)
    return kd, moved


def swap_lef(kd, master, lef, repo):
    """replace one child LEF in an existing kit and refresh its stamp.  Needed for the recip: the signed view's bloated
    abstract (full M5/M6 OBS, top PG M6) leaves the AHUB M5-M6 macro grid no via site (PDN-0232/0233).  The stand-in is
    write_abstract_lef of the same signed routed DB without bloat: same 69 signal pins and PG pins, real M5/M6 shapes."""
    kd, lef, repo = Path(kd), Path(lef), Path(repo)
    sys.path.insert(0, str(repo / "tools/die_plan"))
    import lec as LEC
    import gen_core_kit_kv as GEN
    shutil.copyfile(lef, kd / "macros" / f"{master}.lef")
    prov = LEC._repo_provenance(repo)
    fz = json.loads((kd / "freeze.json").read_text())
    fz["source_commit"] = prov.get("commit")
    fz["ahub_cons"][f"{master}_lef"] = dict(source=str(lef), sha256=hashlib.sha256(lef.read_bytes()).hexdigest())
    fz["kit_hash"] = GEN.kit_hash(kd)
    (kd / "freeze.json").write_text(json.dumps(fz, indent=1) + "\n")
    LEC.write_kit_provenance(kd, repo, provenance=prov)
    return fz["kit_hash"]


# ZH footprints: old and RF-CONS (x0, y0), with the axis direction each one grows in.
ZH_OLD = {"g_zh0": (25.908, 69.108), "g_zh1": (198.732, 69.108), "g_zh2": (25.908, 263.532), "g_zh3": (198.732, 263.532)}
ZH_DIR = {"g_zh0": (-1, -1), "g_zh1": (1, -1), "g_zh2": (-1, 1), "g_zh3": (1, 1)}
OLD_SIDE, HALO, FF_W = 151.2, 4.32, 1.5


def anchor_move(x, y):
    """an anchor in an old ZH's halo on a grown side moves out with that edge (10.8 = 200 sites = 40 rows: same row
    orientation).  Returns (x, y) or None when it is clear of the grown footprint."""
    for k, (x0, y0) in ZH_OLD.items():
        sx, sy = ZH_DIR[k]
        xa, xb, ya, yb = x0 - HALO, x0 + OLD_SIDE + HALO, y0 - HALO, y0 + OLD_SIDE + HALO
        if not (xa - FF_W <= x <= xb and ya - 0.27 <= y <= yb):
            continue
        beyond_x = x + FF_W > x0 + OLD_SIDE if sx > 0 else x < x0
        beyond_y = y + 0.27 > y0 + OLD_SIDE if sy > 0 else y < y0
        if beyond_x or beyond_y:
            return (round(x + (sx * D if beyond_x else 0), 3), round(y + (sy * D if beyond_y else 0), 3))
    return None


def fix_anchors(kd, repo, release=()):
    """move the planned stages next to a grown ZH face and let DPL legalize those (PLACED, not FIRM): they may land on a
    tap or the new macro padding.  `release` names further anchors to hand to DPL (DPL-0033 tap overlaps)."""
    kd, repo = Path(kd), Path(repo)
    pat = re.compile(r"set c \[\$b findInst \{(\S+)\}\]\n(.*?)set ay \[expr \{round\(([\d.]+) \* \$u\)\}\]\n(.*?)"
                     r"\$c setLocation \[expr \{round\(([\d.]+) \* \$u\)\}\] \$ay\n\$c setPlacementStatus FIRM\n", re.S)
    moved = []

    def sub(m):
        name, x, y = m.group(1), float(m.group(5)), float(m.group(3))
        n = anchor_move(x, y)
        if n is None and name not in release:
            return m.group(0)
        nx, ny = n or (x, y)
        moved.append(dict(name=name, old=[x, y], new=[nx, ny]))
        return (f"set c [$b findInst {{{name}}}]\n{m.group(2)}set ay [expr {{round({ny:.6f} * $u)}}]\n{m.group(4)}"
                f"$c setLocation [expr {{round({nx:.6f} * $u)}}] $ay\n$c setPlacementStatus PLACED\n")
    tcl = kd / "ahub_pre_dpl.tcl"
    tcl.write_text(pat.sub(sub, tcl.read_text()))
    sys.path.insert(0, str(repo / "tools/die_plan"))
    import lec as LEC
    import gen_core_kit_kv as GEN
    prov = LEC._repo_provenance(repo)
    fz = json.loads((kd / "freeze.json").read_text())
    fz["source_commit"] = prov.get("commit")
    fz["ahub_cons"]["anchors_moved"] = moved
    fz["kit_hash"] = GEN.kit_hash(kd)
    (kd / "freeze.json").write_text(json.dumps(fz, indent=1) + "\n")
    LEC.write_kit_provenance(kd, repo, provenance=prov)
    return moved


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--from", dest="src")
    ap.add_argument("--out")
    ap.add_argument("--zh-view")
    ap.add_argument("--recip-view")
    ap.add_argument("--swap-lef", nargs=3, metavar=("KIT", "MASTER", "LEF"), help="replace one child LEF in a built kit")
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[5]))
    ap.add_argument("--fix-anchors", metavar="KIT", help="move the planned stages off the grown ZH faces")
    ap.add_argument("--release", nargs="*", default=[], help="anchors handed to DPL without a move")
    a = ap.parse_args()
    if a.fix_anchors:
        print(json.dumps(fix_anchors(a.fix_anchors, a.repo, set(a.release))))
        raise SystemExit(0)
    if a.swap_lef:
        print(swap_lef(a.swap_lef[0], a.swap_lef[1], a.swap_lef[2], a.repo))
        raise SystemExit(0)
    kd, moved = build(a.src, a.out, a.zh_view, a.recip_view, a.repo)
    print(kd)
    print(json.dumps(moved))
