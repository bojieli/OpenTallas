#!/usr/bin/env python3
"""E2/AGI admitted barrier K32 retained-view extraction; named SS/FF parasitics.
No synthesis/route replay. Original IO load fixture does not qualify parent.
"""
import argparse
import hashlib
import json
import re
import subprocess
import os
from export_barrier import capacity, INPUT_SHA
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
    ap.add_argument("--image", default="openroad/orfs:latest")
    ap.add_argument("--interface-sdc", type=Path,
                    help="source-pinned interface constraints without leaf IO exceptions, for parent timing views")
    ap.add_argument("--tmp-dir", type=Path,
                    help="job-local host scratch to bind at /tmp; sets container TMPDIR=/tmp")
    a = ap.parse_args()
    if not set(subprocess.check_output(['hostname', '-I'], text=True).split())&{'5.199.165.105','155.103.253.226'}:
        raise SystemExit('E2/AGI only; call the guarded export_barrier.py launcher')
    orfs, out = a.orfs_dir.resolve(), a.out.resolve()
    if not (out / 'post_guard_capacity.json').is_file():
        raise SystemExit('missing guarded admission receipt')
    out.mkdir(parents=True, exist_ok=True)
    tmp_args = []
    if a.tmp_dir is not None:
        tmp_dir = a.tmp_dir.resolve()
        tmp_dir.mkdir(parents=True, exist_ok=True)
        tmp_args = ["-v", f"{tmp_dir}:/tmp", "-e", "TMPDIR=/tmp"]
    base = next((orfs / "results/asap7").glob("*/base"))
    rel = base.relative_to(orfs)
    for suffix, expected in INPUT_SHA.items():
        if sha(base / f'6_final.{suffix}') != expected:
            raise SystemExit('retained routed artifact hash mismatch')
    if a.name != 'ot_gpu_barrier_node':
        raise SystemExit('fixed retained K32 source only')
    rec = dict(name=a.name, orfs_dir=str(orfs), corners={}, source_signoff_reused=True,
               parent_qualified=False, interface_scope='actual K32 node only; enclosing SM arrive/release network open',
               parameters={'K':32}, source_owner='Sagan', input_sha256=INPUT_SHA,
               requested_CPU=1, input_signoff_ps={'SS_setup':330.53,'FF_hold':39.39},
               constraints={'period_ps':833,'setup_uncertainty_ps':60,'hold_uncertainty_ps':25},
               parent_receiver_loads=None, parent_clock_skew=None,
               fixture_output_load_fF=3.898, jobs_rebuilt=0, routes_replayed=0)
    if a.interface_sdc is not None:
        interface_sdc = a.interface_sdc.resolve()
        if not interface_sdc.is_file():
            ap.error("--interface-sdc must be an existing source-pinned constraint file")
        tmp_args += ["-v", f"{interface_sdc}:/interface.sdc:ro"]
        rec["interface_sdc"] = dict(path=str(interface_sdc), sha256=sha(interface_sdc),
                                    purpose="interface timing extraction, not a new leaf signoff verdict")
    for c in ("ss", "ff"):
        cap = capacity()
        (out / f'capacity_before_{c}.json').write_text(json.dumps(cap, indent=2)+'\n')
        if not cap['CPU_fit']:
            rec['status']='CPU_CAPACITY_REFUSED'
            (out / 'export.json').write_text(json.dumps(rec, indent=2)+'\n')
            raise SystemExit(66)
        libs = "\n".join(f"read_liberty -corner {c} {PLAT}/lib/NLDM/{x}" for x in LIBS[c])
        lef = f"write_abstract_lef /out/{a.name}.lef\n" if c == "ss" else ""
        tcl = f"""define_corners {c}
read_lef {PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
{libs}
read_db /in/{rel}/6_final.odb
read_sdc {"/interface.sdc" if a.interface_sdc is not None else f"/in/{rel}/6_final.sdc"}
read_spef -corner {c} /in/{rel}/6_final.spef
set_propagated_clock [all_clocks]
report_units
report_clock_properties [all_clocks]
puts "OT_WS [sta::worst_slack_cmd {'max' if c == 'ss' else 'min'}]"
write_timing_model -library_name {a.name}_{c} /out/{a.name}_{c}.lib
{lef}puts "OT_EXPORT_DONE"
exit
"""
        (out / f"export_{c}.tcl").write_text(tcl)
        cmd = ["docker", "run", "--rm", "--cpus", "1", "-e", "OMP_NUM_THREADS=1", "-v", f"{orfs}:/in:ro", "-v", f"{out}:/out", *tmp_args, a.image,
               "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad", "-no_init", "-threads", "1", "-exit",
               f"/out/export_{c}.tcl"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        (out / f"export_{c}.log").write_text(p.stdout + p.stderr)
        rec["corners"][c] = dict(returncode=p.returncode, done="OT_EXPORT_DONE" in p.stdout)
        if tmp_args:
            rec["corners"][c]["command"] = cmd
        rec["corners"][c]["parasitic_corner"] = c
    # the element name is the liberty cell; the per-corner library names differ
    rec["files"] = {f.name: sha(f) for f in sorted(out.iterdir()) if f.suffix in (".lef", ".lib")}
    rec["ok"] = all(v["done"] and v["returncode"] == 0 for v in rec["corners"].values()) and len(rec["files"]) == 3
    if rec['ok']:
        lef_text=(out/f'{a.name}.lef').read_text()
        pins=[]
        for m in re.finditer(r'^  PIN (\S+)\n(.*?)^  END \1$',lef_text,re.M|re.S):
            pins.append({'name':m[1], 'direction':re.search(r'DIRECTION\s+(\S+)',m[2])[1],
                         'geometry':[{'layer':r[1],'rect_um':[float(x) for x in r[2].split()]} for r in re.finditer(r'LAYER\s+(\S+)\s*;\s*RECT\s+([^;]+);',m[2])]})
        pinset={p['name'] for p in pins}
        size=[float(x) for x in re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lef_text).groups()]
        rec['macro_size_um']=size
        (out/'pins.json').write_text(json.dumps({'macro':a.name,'size_um':size,'pins':pins},indent=2)+'\n')
        for c in ('ss','ff'):
            lib=(out/f'{a.name}_{c}.lib').read_text()
            if set(re.findall(r'\bpin\s*\(\s*"?([^"\s)]+)"?\s*\)',lib))!=pinset:
                rec['ok']=False
            rec['corners'][c]['units']={'time':re.search(r'time_unit\s*:\s*"([^"]+)"',lib)[1], 'capacitance':re.search(r'capacitive_load_unit\s*\(([^)]+)\)',lib)[1]}
            rec['corners'][c]['rising_output_arcs']=len(re.findall(r'timing_type\s*:\s*rising_edge',lib))
            rec['corners'][c]['internal_CTS_included']=True
    rec['status']='EXPORTED_REAL_RETAINED_LEAF'  if rec['ok'] else 'EXTRACTION_FAILED'
    (out / "export.json").write_text(json.dumps(rec, indent=2) + "\n")
    (out / "abstract.json").write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps(rec))
    raise SystemExit(0 if rec["ok"] else 1)


if __name__ == "__main__":
    main()
