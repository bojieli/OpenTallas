#!/usr/bin/env python3
"""Export a routed, signoff-closed hardened element (ORFS keep-workdir) as a macro view for hierarchical routes:
abstract LEF + extracted timing models at SS (setup corner) and FF (hold corner), from the routed 6_final
odb/sdc/spef, in the layout --macro-view / tools/w18/corner_sta.py --macro expect (DIR/NAME.lef, DIR/NAME_ss.lib,
DIR/NAME_ff.lib). Add --tt for the actual TT setup model required by OptionB
composition; SS remains a sensitivity. Same OpenROAD commands as tools/w18/recover_abstract.py (write_timing_model, write_abstract_lef).

    python3 tools/hbm_fmax_attn_abstract.py --orfs-dir W/work/orfs --name ot_attn_hgrp_m --out physical/hbm_fmax_attn/ot_attn_hgrp_m
"""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
LIBS = {"ss": ["asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz", "asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz",
               "asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz", "asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib",
               "asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz"],
        "ff": ["asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz", "asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz",
               "asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz", "asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib",
               "asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz"]}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orfs-dir", type=Path, required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--image", default=os.environ.get("OPENTALLAS_ORFS_IMAGE", "openroad/orfs:latest"))
    ap.add_argument("--tt", action="store_true", help="also export actual TT Liberty for OptionB parent setup timing")
    ap.add_argument("--interface-sdc", type=Path,
                    help="source-pinned interface constraints without leaf IO exceptions, for parent timing views")
    ap.add_argument("--macro-view", action="append", default=[], type=Path,
                    help="a hardened sub-macro inside the element: DIR holding NAME.lef and NAME_ss.lib / NAME_ff.lib "
                         "(NAME = the directory name); repeatable")
    ap.add_argument("--tmp-dir", type=Path,
                    help="job-local host scratch to bind at /tmp; sets container TMPDIR=/tmp")
    a = ap.parse_args()
    orfs, out = a.orfs_dir.resolve(), a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    tmp_args = []
    if a.tmp_dir is not None:
        tmp_dir = a.tmp_dir.resolve()
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_args = ["-v", f"{tmp_dir}:/tmp", "-e", "TMPDIR=/tmp"]
    base = next((orfs / "results/asap7").glob("*/base"))
    rel = base.relative_to(orfs)
    rec = dict(name=a.name, orfs_dir=str(orfs), image=a.image, corners={})
    if a.interface_sdc is not None:
        interface_sdc = a.interface_sdc.resolve()
        if not interface_sdc.is_file():
            ap.error("--interface-sdc must be an existing source-pinned constraint file")
        tmp_args += ["-v", f"{interface_sdc}:/interface.sdc:ro"]
        rec["interface_sdc"] = dict(path=str(interface_sdc), sha256=sha(interface_sdc),
                                    purpose="interface timing extraction, not a new leaf signoff verdict")
    corners = ("ss", "ff", "tt") if a.tt else ("ss", "ff")
    if a.tt:
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parent / "w18"))
        from corner_sta import LIBS as SIGNOFF_LIBS
        LIBS["tt"] = SIGNOFF_LIBS["tt"]
    mv_lef, mv_lib = "", {c: "" for c in corners}
    for i, d in enumerate(a.macro_view):
        d = d.resolve()
        tmp_args += ["-v", f"{d}:/mv{i}:ro"]
        mv_lef += f"read_lef /mv{i}/{d.name}.lef\n"
        for c in corners:
            mv_lib[c] += f"read_liberty /mv{i}/{d.name}_{c}.lib\n"
    rec["macro_views"] = [str(d) for d in a.macro_view]
    # MULTI-VT: an odb with LVT/SLVT cells exports with those libraries/LEFs too (detection: tools/w18/corner_sta.py)
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent / "w18"))
    from corner_sta import extra_vts, _VT_TAG  # noqa: E402
    vts = extra_vts(base / "6_final.odb")
    if vts:
        rec["vt_flavours_added"] = vts
    vt_lefs = "".join(f"\nread_lef {PLAT}/lef/asap7sc7p5t_28_{_VT_TAG[v]}_1x_220121a.lef" for v in vts)
    for c in corners:
        libs = "\n".join(f"read_liberty {PLAT}/lib/NLDM/{x}" for x in
                         LIBS[c] + [y.replace("_RVT_", f"_{v}_") for v in vts for y in LIBS[c]]) + "\n" + mv_lib[c] + mv_lef
        lef = f"write_abstract_lef /out/{a.name}.lef\n" if c == "ss" else ""
        tcl = f"""read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef{vt_lefs}
{libs}
read_db /in/{rel}/6_final.odb
read_sdc {"/interface.sdc" if a.interface_sdc is not None else f"/in/{rel}/6_final.sdc"}
read_spef /in/{rel}/6_final.spef
set_propagated_clock [all_clocks]
puts "OT_WS [sta::worst_slack_cmd {'max' if c in ('ss', 'tt') else 'min'}]"
write_timing_model -library_name {a.name}_{c} /out/{a.name}_{c}.lib
{lef}puts "OT_EXPORT_DONE"
exit
"""
        (out / f"export_{c}.tcl").write_text(tcl)
        cmd = ["docker", "run", "--rm", "-v", f"{orfs}:/in:ro", "-v", f"{out}:/out", *tmp_args, a.image,
               "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad", "-no_init", "-exit",
               f"/out/export_{c}.tcl"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        (out / f"export_{c}.log").write_text(p.stdout + p.stderr)
        rec["corners"][c] = dict(returncode=p.returncode, done="OT_EXPORT_DONE" in p.stdout)
        if tmp_args:
            rec["corners"][c]["command"] = cmd
    # the element name is the liberty cell; the per-corner library names differ
    rec["files"] = {f.name: sha(f) for f in sorted(out.iterdir()) if f.suffix in (".lef", ".lib")}
    rec["ok"] = all(v["done"] for v in rec["corners"].values()) and len(rec["files"]) == len(corners) + 1
    (out / "abstract.json").write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps(rec))
    raise SystemExit(0 if rec["ok"] else 1)


if __name__ == "__main__":
    main()
