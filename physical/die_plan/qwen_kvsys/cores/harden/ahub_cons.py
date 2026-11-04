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


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--from", dest="src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--zh-view", required=True)
    ap.add_argument("--recip-view", required=True)
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[5]))
    a = ap.parse_args()
    kd, moved = build(a.src, a.out, a.zh_view, a.recip_view, a.repo)
    print(kd)
    print(json.dumps(moved))
