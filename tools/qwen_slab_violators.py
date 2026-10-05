#!/usr/bin/env python3
"""Group failing endpoints of an ORFS stage ODB by class (SS setup / FF hold, io_ref die-context boundary).

    python3 tools/qwen_slab_violators.py --orfs-dir <work/orfs> --stage 4_1_cts|6_final --output V.json
Endpoint classes are the instance path with bus indices and generate indices stripped (g_mul[3] -> g_mul[*])."""
import argparse, json, re, subprocess
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent / "w18"))
import corner_sta as cs  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MACRO = "physical/asap7_memory_macros/ot_rom_4096x266_m8"


def tcl(corner, base, stage):
    libs = "\n".join(f"read_liberty {cs.PLAT}/lib/NLDM/{l}" for l in cs.LIBS[corner])
    chk = "max" if corner == "ss" else "min"
    sdc = "6_final.sdc" if stage == "6_final" else "4_cts.sdc"
    par = f"read_spef {base}/6_final.spef" if stage == "6_final" else "estimate_parasitics -placement"
    return f"""
read_lef {cs.PLAT}/lef/asap7_tech_1x_201209.lef
read_lef {cs.PLAT}/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /src/{MACRO}/ot_rom_4096x266_m8.lef
{libs}
read_liberty /src/{MACRO}/ot_rom_4096x266_m8_{corner}.lib
read_db {base}/{stage}.odb
read_sdc {base}/{sdc}
source {cs.PLAT}/setRC.tcl
{par}
set_propagated_clock [all_clocks]
read_sdc /src/physical/qwen_slab_structural/io_lat.sdc
foreach p [concat [get_pins -hierarchical */D] [all_outputs]] {{
  set s [get_property $p slack_{chk}]
  if {{$s ne "INF" && $s < 0}} {{ puts "OT_V [get_full_name $p] $s" }}
}}
foreach pa [find_timing_paths -path_delay {chk} -group_path_count 5000 -endpoint_path_count 1 -slack_max 0] {{
  puts "OT_P [get_full_name [get_property $pa startpoint]] -> [get_full_name [get_property $pa endpoint]] [get_property $pa slack]"
}}
exit
"""


def cls(n):
    return re.sub(r"_\d+_", "_*_", re.sub(r"\[\d+\]", "[*]", n.replace("\\", "")))


def pairs(out):
    """worst path per (start class -> end class)"""
    best = {}
    for m in re.finditer(r"^OT_P (\S+) -> (\S+) (\S+)$", out, re.M):
        k = (cls(m[1]), cls(m[2])); s = float(m[3])
        if k not in best or s < best[k][0]:
            best[k] = (s, m[1], m[2], 0)
        best[k] = (best[k][0], best[k][1], best[k][2], best[k][3] + 1)
    return [dict(start=k[0], end=k[1], n=v[3], worst_ps=round(v[0], 1), example=f"{v[1]} -> {v[2]}")
            for k, v in sorted(best.items(), key=lambda kv: kv[1][0])][:40]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--orfs-dir", type=Path, required=True)
    ap.add_argument("--stage", default="6_final"); ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args(); o = a.orfs_dir.resolve()
    base = next((o / "results/asap7").glob("*/base")); rel = f"/work/{base.relative_to(o)}"
    rec = {}
    for corner in ("ss", "ff"):
        (o / f"viol_{corner}.tcl").write_text(tcl(corner, rel, a.stage))
        out = subprocess.run(["docker", "run", "--rm", "-v", f"{o}:/work", "-v", f"{ROOT}:/src:ro", "openroad/orfs:latest",
                              "bash", "-lc", f"/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/viol_{corner}.tcl"],
                             capture_output=True, text=True).stdout
        (o / f"viol_{corner}.log").write_text(out)
        groups = {}
        for m in re.finditer(r"^OT_V (\S+) (\S+)$", out, re.M):
            k = re.sub(r"\[\d+\]", "[*]", re.sub(r"\\", "", m[1]))
            k = re.sub(r"_\d+_", "_*_", k)
            g = groups.setdefault(k, [0, 0.0]); g[0] += 1; g[1] = min(g[1], float(m[2]))
        rec[corner] = dict(endpoints=sum(v[0] for v in groups.values()),
                           groups=[dict(cls=k, n=v[0], worst_ps=round(v[1], 1)) for k, v in sorted(groups.items(), key=lambda kv: kv[1][1])][:60],
                           paths=pairs(out))
    a.output.write_text(json.dumps(rec, indent=1) + "\n")
    for c in rec: print(c, rec[c]["endpoints"], rec[c]["groups"][:12])


if __name__ == "__main__":
    main()
