#!/usr/bin/env python3
"""Report detailed SS setup / FF hold paths of a routed ORFS result for given -through/-to patterns (diagnostics only).
usage: path_probe.py ORFS_DIR SIGNOFF_SDC REPO_ROOT corner(ss|ff) 'from_glob|to_glob' ... [--macro m]...
Runs in the orfs docker image; prints report_checks -fields {fanout cap slew} for the worst path of each pair."""
import subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "w18"))
import corner_sta as C
args = sys.argv[1:]
macros = []
while "--macro" in args:
    i = args.index("--macro"); macros.append(args[i + 1]); del args[i:i + 2]
orfs, sdc, root, corner = Path(args[0]).resolve(), Path(args[1]).resolve(), Path(args[2]).resolve(), args[3]
pairs = args[4:]
base = next((orfs / "results/asap7").glob("*/base"))
rel = f"/work/{base.relative_to(orfs)}"
s = C.script(corner, rel, macros)
(orfs / "probe_extra.sdc").write_text(sdc.read_text())
s = s.replace("set_propagated_clock [all_clocks]\n", "set_propagated_clock [all_clocks]\nread_sdc /work/probe_extra.sdc\n", 1)
s = s.split('puts "OT_CORNER')[0]
chk = "max" if corner == "ss" else "min"
for p in pairs:
    f, t = p.split("|")
    fr = f"-from [get_pins -hierarchical {{{f}}}]" if f else ""
    if f.startswith("port:"): fr = f"-from [get_ports {{{f[5:]}}}]"
    to = f"-to [get_pins -hierarchical {{{t}}}]" if t else ""
    if t.startswith("port:"): to = f"-to [get_ports {{{t[5:]}}}]"
    s += f'puts "=== PAIR {p}"\nreport_checks -path_delay {chk} {fr} {to} -fields {{fanout cap slew}} -digits 1\n'
s += "exit\n"
(orfs / f"probe_{corner}.tcl").write_text(s)
cmd = ["docker", "run", "--rm", "-v", f"{orfs}:/work", "-v", f"{root}:/src:ro", "openroad/orfs:asap7lock", "bash", "-lc",
       f"/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/probe_{corner}.tcl"]
print(subprocess.run(cmd, capture_output=True, text=True).stdout)
