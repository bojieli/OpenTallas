#!/usr/bin/env python3
"""Macro view export at SS / FF / TT (OWNER OPTION B 2026-10-07: setup signs off at TT, hold at FF, SS = sensitivity).

Same OpenROAD commands as tools/hbm_fmax_attn_abstract.py (write_timing_model from the routed 6_final odb + spef, with
the routed 6_final.sdc or an --interface-sdc read INSTEAD of it; write_abstract_lef in the SS pass), plus a TT pass
with the ASAP7 TT NLDM libraries and each sub-macro's <name>_tt.lib.  Self-contained (no repo imports) so it can be
copied to any host and run next to the route:

    python3 view_export.py --orfs-dir W/work/orfs --name NAME --out DIR [--interface-sdc F] [--macro-view D ...]
                           [--corners ss,ff,tt] [--image openroad/orfs:latest] [--tmp-dir T]

--corners tt alone adds <name>_tt.lib to a view whose LEF / SS / FF were already written from the SAME route by
hbm_fmax_attn_abstract.py (pass the same --interface-sdc / --macro-view it used).  Exit 0 iff every corner finished.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
CELLS = ["asap7sc7p5t_AO_RVT_{C}_nldm_211120.lib.gz", "asap7sc7p5t_INVBUF_RVT_{C}_nldm_220122.lib.gz",
         "asap7sc7p5t_OA_RVT_{C}_nldm_211120.lib.gz", "asap7sc7p5t_SEQ_RVT_{C}_nldm_220123.lib",
         "asap7sc7p5t_SIMPLE_RVT_{C}_nldm_211120.lib.gz"]
VT = {"L": ("LVT", "L"), "SL": ("SLVT", "SL")}   # odb cell suffix -> (lib tag, lef tag)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def extra_vts(odb):
    data = Path(odb).read_bytes()
    out = []
    for t in ("L", "SL"):
        import re
        if re.search(rb"_ASAP7_75t_" + t.encode() + rb"(?![A-Za-z0-9_])", data):
            out.append(t)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--orfs-dir", type=Path, required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--interface-sdc", type=Path)
    ap.add_argument("--macro-view", action="append", default=[], type=Path)
    ap.add_argument("--corners", default="ss,ff,tt")
    ap.add_argument("--image", default="openroad/orfs:latest")
    ap.add_argument("--tmp-dir", type=Path)
    a = ap.parse_args()
    orfs, out = a.orfs_dir.resolve(), a.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    base = next((orfs / "results/asap7").glob("*/base"))
    rel = base.relative_to(orfs)
    mounts = []
    if a.tmp_dir is not None:
        a.tmp_dir.mkdir(parents=True, exist_ok=True)
        mounts += ["-v", f"{a.tmp_dir.resolve()}:/tmp", "-e", "TMPDIR=/tmp"]
    recp = out / "abstract.json"
    rec = json.loads(recp.read_text()) if recp.exists() else dict(name=a.name, orfs_dir=str(orfs), corners={})
    rec.setdefault("corners", {})
    if a.interface_sdc is not None:
        isdc = a.interface_sdc.resolve()
        mounts += ["-v", f"{isdc}:/interface.sdc:ro"]
        rec["interface_sdc"] = dict(path=str(isdc), sha256=sha(isdc),
                                    purpose="interface timing extraction, not a new leaf signoff verdict")
    mv = []
    for i, d in enumerate(a.macro_view):
        d = d.resolve()
        mounts += ["-v", f"{d}:/mv{i}:ro"]
        mv.append((i, d.name))
    rec["macro_views"] = [str(d) for d in a.macro_view]
    vts = extra_vts(base / "6_final.odb")
    if vts:
        rec["vt_flavours_added"] = vts
    for c in a.corners.split(","):
        C = c.upper()
        libs = [f"read_liberty {PLAT}/lib/NLDM/{x.format(C=C)}" for x in CELLS]
        libs += [f"read_liberty {PLAT}/lib/NLDM/{x.format(C=C).replace('_RVT_', '_' + VT[v][0] + '_')}"
                 for v in vts for x in CELLS]
        libs += [f"read_liberty /mv{i}/{n}_{c}.lib" for i, n in mv]
        lefs = [f"read_lef {PLAT}/lef/asap7sc7p5t_28_{VT[v][1]}_1x_220121a.lef" for v in vts]
        lefs += [f"read_lef /mv{i}/{n}.lef" for i, n in mv]
        sdc = "/interface.sdc" if a.interface_sdc is not None else f"/in/{rel}/6_final.sdc"
        tcl = "\n".join([f"read_lef {PLAT}/lef/asap7_tech_1x_201209.lef",
                         f"read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef", *lefs, *libs,
                         f"read_db /in/{rel}/6_final.odb", f"read_sdc {sdc}", f"read_spef /in/{rel}/6_final.spef",
                         "set_propagated_clock [all_clocks]",
                         "puts \"OT_WS max [sta::worst_slack_cmd max] min [sta::worst_slack_cmd min]\"",
                         f"write_timing_model -library_name {a.name}_{c} /out/{a.name}_{c}.lib",
                         f"write_abstract_lef /out/{a.name}.lef" if c == "ss" else "",
                         "puts \"OT_EXPORT_DONE\"", "exit", ""])
        (out / f"export_{c}.tcl").write_text(tcl)
        cmd = ["docker", "run", "--rm", "-v", f"{orfs}:/in:ro", "-v", f"{out}:/out", *mounts, a.image,
               "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad", "-no_init", "-exit", f"/out/export_{c}.tcl"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        log = p.stdout + p.stderr
        (out / f"export_{c}.log").write_text(log)
        ws = [l for l in log.splitlines() if l.startswith("OT_WS")]
        rec["corners"][c] = dict(returncode=p.returncode, done="OT_EXPORT_DONE" in log, ws=ws[-1] if ws else None,
                                 image=a.image, command=cmd)
    rec["files"] = {f.name: sha(f) for f in sorted(out.iterdir()) if f.suffix in (".lef", ".lib")}
    want = [f"{a.name}.lef"] + [f"{a.name}_{c}.lib" for c in ("ss", "ff", "tt")]
    rec["ok"] = all(v.get("done") for v in rec["corners"].values()) and all(w in rec["files"] for w in want)
    recp.write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps({k: rec[k] for k in ("name", "ok", "files")}))
    raise SystemExit(0 if all(rec["corners"][c]["done"] for c in a.corners.split(",")) else 1)


if __name__ == "__main__":
    main()
