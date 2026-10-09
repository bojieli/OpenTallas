#!/usr/bin/env python3
"""Export a re-hardened embedding ingress child (ot_qwen_embedding_ingress_numeric, routed by route_master.sh) as the
parent's macro view qfd_embed_ingress_<kind>: abstract LEF + timing models at SS, TT and FF (option B: setup at TT,
hold at FF; SS kept as sensitivity), the top identifier renamed to the parent's cell name (MACRO / END / cell lines
only), and clock_reference.tcl with the measured internal valid_q clock insertion (TT max for the setup reference,
FF min for the hold reference) that physical/qwen_embedding_parent/io_ref_macro*.sdc adds to the macro clk pin.

    export_ingress_view.py --orfs-dir W/work/orfs --kind code --out physical/qwen_embedding_parent/m4c/code
(--out is resolved inside the job's source snapshot; the view lands in OUT/qfd_embed_ingress_<kind>/)."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

PLAT = "/OpenROAD-flow-scripts/flow/platforms/asap7"
SRC_TOP = "ot_qwen_embedding_ingress_numeric"
LIBS = {c: [f"asap7sc7p5t_AO_RVT_{C}_nldm_211120.lib.gz", f"asap7sc7p5t_INVBUF_RVT_{C}_nldm_220122.lib.gz",
            f"asap7sc7p5t_OA_RVT_{C}_nldm_211120.lib.gz", f"asap7sc7p5t_SEQ_RVT_{C}_nldm_220123.lib",
            f"asap7sc7p5t_SIMPLE_RVT_{C}_nldm_211120.lib.gz"] for c, C in (("ss", "SS"), ("tt", "TT"), ("ff", "FF"))}


def tcl(corner, base, name, lef):
    libs = "\n".join(f"read_liberty {PLAT}/lib/NLDM/{l}" for l in LIBS[corner])
    return f"""read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
{libs}
read_db {base}/6_final.odb
read_sdc /iface.sdc
read_spef {base}/6_final.spef
set_propagated_clock [all_clocks]
set ws [sta::worst_slack_cmd max]
set ref {{}}
foreach c [get_cells -quiet -hierarchical *valid_q*] {{
  set p [get_pins -quiet "[get_full_name $c]/CLK"]
  if {{[llength $p]}} {{ set ref $p; break }}
}}
if {{[llength $ref] != 1}} {{ error "no valid_q register clock pin" }}
puts "QREF [get_full_name $ref] [get_property $ref arrival_max_rise] [get_property $ref arrival_min_rise]"
puts "OT_WS_MAX $ws OT_WS_MIN [sta::worst_slack_cmd min]"
write_timing_model -library_name {name}_{corner} /out/{name}_{corner}.lib
{lef}
puts OT_EXPORT_DONE
exit
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orfs-dir", type=Path, required=True)
    ap.add_argument("--kind", choices=["code", "scale"], required=True)
    ap.add_argument("--iface-sdc", type=Path, default=Path("physical/qwen_embedding_parent/island_interface.sdc"))
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--image", default="openroad/orfs:asap7lock")
    a = ap.parse_args()
    name = f"qfd_embed_ingress_{a.kind}"
    o = a.orfs_dir.resolve()
    view = (a.out / name).resolve()
    orig = view / "export_original"
    orig.mkdir(parents=True, exist_ok=True)
    base = next((o / "results/asap7").glob("*/base"))
    rel = f"/work/{base.relative_to(o)}"
    rec = dict(schema="opentallas.qwen_missing.ingress_view.v1", name=name, source_top=SRC_TOP, orfs_dir=str(o),
               corners={})
    for corner in ("ss", "tt", "ff"):
        lef = f"write_abstract_lef /out/{name}.lef" if corner == "tt" else ""
        (o / f"qm_export_{corner}.tcl").write_text(tcl(corner, rel, name, lef))
        cmd = ["docker", "run", "--rm", "-v", f"{o}:/work", "-v", f"{orig}:/out",
               "-v", f"{a.iface_sdc.resolve()}:/iface.sdc:ro", a.image,
               "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad", "-no_init", "-exit",
               f"/work/qm_export_{corner}.tcl"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        log = p.stdout + p.stderr
        (view / f"export_{corner}.log").write_text(log)
        q = re.search(r"^QREF (\S+) (\S+) (\S+)$", log, re.M)
        w = re.search(r"OT_WS_MAX (\S+) OT_WS_MIN (\S+)", log)
        rec["corners"][corner] = dict(done="OT_EXPORT_DONE" in log, ref_pin=q and q.group(1),
                                      clk_max_ps=q and float(q.group(2)), clk_min_ps=q and float(q.group(3)),
                                      ws_max=w and w.group(1), ws_min=w and w.group(2))
        if "OT_EXPORT_DONE" not in log or not q:
            (view / "export.json").write_text(json.dumps(rec, indent=1) + "\n")
            sys.exit(f"export {corner} failed; see {view}/export_{corner}.log")
    # top identifier alias: the parent instantiates the cell as qfd_embed_ingress_<kind>
    for f in sorted(orig.iterdir()):
        t = f.read_text()
        if f.suffix == ".lef":
            t, n = re.subn(rf"(?m)^(MACRO|END)([ \t]+){SRC_TOP}([ \t]*)$", rf"\1\2{name}\3", t)
            ok = n == 2
        else:
            t, n = re.subn(rf'(\bcell\s*\(\s*"?){SRC_TOP}("?\s*\))', rf"\1{name}\2", t)
            ok = n == 1
        if not ok:
            sys.exit(f"alias: unexpected top declarations in {f.name}")
        (view / f.name).write_text(t)
    c = rec["corners"]
    (a.out / "clock_reference.tcl").write_text(
        f"# measured by tools/qwen_missing/export_ingress_view.py on {o}: {c['tt']['ref_pin']} clock arrival\n"
        f"# setup reference = TT max (option B setup corner; SS max {c['ss']['clk_max_ps']}), hold = FF min\n"
        f"set embedding_ref_internal_setup_ps {c['tt']['clk_max_ps']:.6f}\n"
        f"set embedding_ref_internal_hold_ps {c['ff']['clk_min_ps']:.6f}\n")
    rec["files"] = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(view.iterdir()) if f.is_file()}
    (view / "export.json").write_text(json.dumps(rec, indent=1) + "\n")
    print(json.dumps(rec["corners"], indent=1))


if __name__ == "__main__":
    main()
