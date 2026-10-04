#!/usr/bin/env python3
"""hbm-fmax-su: the worst SS register-to-register paths of a routed ORFS dir, timed exactly as tools/w18/corner_sta.py
times them (same libraries, odb, sdc, spef, propagated clocks), one line per path plus the worst path in full.
    python3 tools/su_r2r_paths.py --orfs-dir W/work/orfs [-n 12]"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "w18"))
import corner_sta as C  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orfs-dir", type=Path, required=True)
    ap.add_argument("-n", type=int, default=12)
    a = ap.parse_args()
    o = a.orfs_dir.resolve()
    base = next((o / "results/asap7").glob("*/base"))
    rel = f"/work/{base.relative_to(o)}"
    s = C.script("ss", rel, []).split('puts "OT_CORNER')[0]
    s += f"""
set ps [find_timing_paths -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count {a.n} -endpoint_path_count 1 -unique_paths_to_endpoint]
foreach p $ps {{ puts "R2R [get_property $p slack] [get_full_name [get_property $p startpoint]] -> [get_full_name [get_property $p endpoint]]" }}
report_checks -path_delay max -from [all_registers -clock_pins] -to [all_registers -data_pins] -group_path_count 1 -fields {{fanout}}
exit
"""
    (o / "su_r2r.tcl").write_text(s)
    cmd = ["docker", "run", "--rm", "-v", f"{o}:/work", "openroad/orfs:latest", "bash", "-lc",
           "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/su_r2r.tcl"]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    (o / "su_r2r.log").write_text(out)
    for line in out.splitlines():
        if line.startswith("R2R") or re.search(r"[v^] \S+ \(|slack", line):
            print(line)


if __name__ == "__main__":
    main()
