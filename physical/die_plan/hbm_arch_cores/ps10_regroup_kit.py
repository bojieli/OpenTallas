#!/usr/bin/env python3
"""ps10_regroup_kit.py (DIE-HBM-97-PS10, DIE-HBM-100 ruling 11-12): ot_hgi_sfu_programme_store_r10 structural form
"regroup": the leaf-grouped, face-paired macro table (ps10_cf1: every leaf = one 2x2 block or a 1x4 column, 0 foreign
macros inside any leaf bbox, vs 37 in the REBAL-6 table) on a deeper routing deck, no density cap.
Resume kit: copy of the ps10_cf1 kit (proved synth kept, cf1 macro_placement.tcl kept), stages 2_1 onward removed,
config.mk MAX_ROUTING_LAYER = LAYER and PLACE_DENSITY = 0.4 (same two keys as ps10_m6d), mtime kept (RESYNTH-GUARD).
usage: ps10_regroup_kit.py SRC_KIT DST_KIT LAYER(M6|M7)
"""
import json, os, re, shutil, subprocess, sys
from pathlib import Path

def main():
    src, dst, layer = Path(sys.argv[1]).resolve(), Path(sys.argv[2]), sys.argv[3]
    assert layer in ("M6", "M7")
    if dst.exists(): raise SystemExit(f"{dst} exists")
    subprocess.check_call(["cp", "-a", str(src), str(dst)])
    res = next(dst.glob("run/results/asap7/*/base"))
    for f in res.iterdir():
        if not f.name.startswith(("1_", "clock_period", "mem.json", "ot_face", "ot_unreg")): f.unlink()
    for sub in ("logs", "reports", "objects"):
        for d in dst.glob(f"run/{sub}/asap7/*/base"):
            for f in d.iterdir():
                if f.name.startswith(("1_", "synth")): continue
                shutil.rmtree(f) if f.is_dir() else f.unlink()
    shutil.rmtree(dst / "run/layout_review", ignore_errors=True)
    cm = dst / "config.mk"; st = cm.stat(); t = cm.read_text()
    t, n1 = re.subn(r"^export MAX_ROUTING_LAYER = .*$", f"export MAX_ROUTING_LAYER = {layer}", t, flags=re.M)
    t, n2 = re.subn(r"^export PLACE_DENSITY = .*$", "export PLACE_DENSITY = 0.4", t, flags=re.M)
    assert (n1, n2) == (1, 1)
    cm.write_text(t); os.utime(cm, ns=(st.st_atime_ns, st.st_mtime_ns))
    if layer == "M7":  # same PDN change as HBM-RXBM3 M7T (12.1a): own M7 straps on the tile lattice, PG pins on M7
        pp = dst / "pdn.tcl"; u = pp.read_text()
        u = u.replace("-pins {M5}", "-pins {M7}")
        u = u.replace("add_pdn_connect -grid {top} -layers {M2 M5}\n", "add_pdn_connect -grid {top} -layers {M2 M5}\nadd_pdn_stripe -grid {top} -layer {M7} -width {0.288} -spacing {0.096} -pitch {8.64} -offset {4.128}\nadd_pdn_connect -grid {top} -layers {M5 M7}\n")
        pp.write_text("# ps10 regroup M7: M7 stripes = tile geometry (pitch 8.64, offset 4.128), PG pins on M7 (parent die M8 lands them, 12.1a); M5-M7 stacked via\n" + u)
    (dst / "ps10_regroup.json").write_text(json.dumps(dict(form="ps10_regroup_" + layer, src=str(src), table="ps10_cf1 leaf-grouped", max_routing_layer=layer, place_density=0.4), indent=1))
    (dst / "DO_NOT_COUNT").write_text(f"ps10 regroup {layer} diagnostic form, DO_NOT_COUNT until signed off\n")
    print("ok", dst, layer)
if __name__ == "__main__": main()
