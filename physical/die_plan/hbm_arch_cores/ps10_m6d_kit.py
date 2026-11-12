#!/usr/bin/env python3
"""ps10_m6d_kit.py (DIE-HBM-97-PS10, RULING DIE-HBM-100 11-11 22:xx): ot_hgi_sfu_programme_store_r10 form "m6d" =
the hbm-cons-2 form (REBAL-6 macro table WITHOUT the macro-gap row cuts, MAX_ROUTING_LAYER M6, PLACE_DENSITY 0.4)
PLUS a soft std-cell density cap (dcap_hot_boxes.py) in the channels around the cons-2 hot region.

Resume form: copies a kit that already holds the proved synth + floorplan (ps10_cf1), drops 2_1 onward (the flow restarts at floorplan, as ps10_cf1 did), restores the
a12/REBAL-6 table minus the ot_mgb_cut block, edits config.mk (3 keys, none touches synthesis), chains the dcap hook
into PRE_GLOBAL_PLACE_TCL (same mechanism as gen_core_kit_hbm.py --pre-gpl-extra) and keeps config.mk's old mtime so the
RESYNTH-GUARD / make chain keep the proved netlist.  Equivalent fresh-kit flags: --sigmax M6 --util 0.4
--macro-gap-block off --pre-gpl-extra <hook> (+ POST_GLOBAL_PLACE_TCL = the release hook).
usage: ps10_m6d_kit.py SRC_KIT DST_KIT HOOK.tcl RELEASE.tcl   (both from dcap_hot_boxes.py --tcl / --release-tcl)
"""
import hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path

def main():
    src, dst, hook, rel = Path(sys.argv[1]).resolve(), Path(sys.argv[2]), Path(sys.argv[3]).resolve(), Path(sys.argv[4]).resolve()
    if dst.exists(): raise SystemExit(f"{dst} exists")
    subprocess.check_call(["cp", "-a", str(src), str(dst)])
    res = next(dst.glob("run/results/asap7/*/base"))
    keep = ("1_", "clock_period", "mem.json", "ot_face", "ot_unreg")
    for f in res.iterdir():
        if not f.name.startswith(keep): f.unlink()
    for sub in ("logs", "reports", "objects"):
        for d in dst.glob(f"run/{sub}/asap7/*/base"):
            for f in d.iterdir():
                if f.name.startswith(("1_", "synth")): continue
                shutil.rmtree(f) if f.is_dir() else f.unlink()
    for d in ("run/layout_review",):
        shutil.rmtree(dst / d, ignore_errors=True)
    # REBAL-6 table minus the macro-gap row cuts (= the hbm-cons-2 macro_placement.tcl)
    old = (dst / "macro_placement.tcl.a12").read_text()
    cut = old.index("# DIE-HBM-82-EP6 class fix")
    (dst / "macro_placement.tcl.cf1").write_text((dst / "macro_placement.tcl").read_text())
    (dst / "macro_placement.tcl").write_text(old[:cut])
    # config: deck M6, density 0.4 (cons-2 values); nothing else
    cm = dst / "config.mk"; st = cm.stat(); t = cm.read_text()
    t, n1 = re.subn(r"^export MAX_ROUTING_LAYER = .*$", "export MAX_ROUTING_LAYER = M6", t, flags=re.M)
    t, n2 = re.subn(r"^export PLACE_DENSITY = .*$", "export PLACE_DENSITY = 0.4", t, flags=re.M)
    t, n3 = re.subn(r"^export PRE_GLOBAL_PLACE_TCL = .*$", "export PRE_GLOBAL_PLACE_TCL = /work/pre_gpl_chain.tcl", t, flags=re.M)
    assert (n1, n2, n3) == (1, 1, 1), (n1, n2, n3)
    t = t.rstrip('\n') + '\n# ps10_m6d: density-cap blockages removed after global placement\nexport POST_GLOBAL_PLACE_TCL = /work/dcap_release.tcl\n'
    cm.write_text(t); os.utime(cm, ns=(st.st_atime_ns, st.st_mtime_ns))
    body = hook.read_bytes()
    (dst / "dcap_release.tcl").write_bytes(rel.read_bytes())
    (dst / "pre_gpl_extra.tcl").write_bytes(body)
    (dst / "pre_gpl_chain.tcl").write_text("# ps10_m6d_kit.py: the kit face-register placement, then the dcap hook\n"
                                           "source /work/face_flops.tcl\nsource /work/pre_gpl_extra.tcl\n")
    rec = dict(form="ps10_m6d", src=str(src), hook_sha256=hashlib.sha256(body).hexdigest(), release_sha256=hashlib.sha256(rel.read_bytes()).hexdigest(), table="a12 minus ot_mgb_cut",
               max_routing_layer="M6", place_density=0.4)
    (dst / "ps10_m6d.json").write_text(json.dumps(rec, indent=1))
    (dst / "DO_NOT_COUNT").write_text("ps10_m6d diagnostic form, DO_NOT_COUNT until signed off\n")
    print(json.dumps(rec))
if __name__ == "__main__": main()
