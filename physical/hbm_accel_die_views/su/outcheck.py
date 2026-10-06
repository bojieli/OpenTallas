#!/usr/bin/env python3
"""CLAUDE HBM-ABSTRACTS (hub) lane recipe post-check.  Register-direct output check on a routed ORFS dir: for every output port, the worst max path's startpoint must be a
register and every cell on it a buffer / inverter (ASAP7 BUF*/INV*/HB*).  Prints one line per offending port and a
summary; exit 1 if any output is not register-direct."""
import re, subprocess, sys
from pathlib import Path
sys.path.insert(0, "tools/w18")
import corner_sta as C
o = Path(sys.argv[1]).resolve()
base = next((o / "results/asap7").glob("*/base")); rel = f"/work/{base.relative_to(o)}"
s = C.script("ss", rel, []).split('puts "OT_CORNER')[0]
# the routed SDC without the output false path (so the output paths can be listed)
sdc = next(base.glob("6_final.sdc"))
logical = sdc.read_text().replace("\\\n", " ").splitlines()
(o / "outcheck.sdc").write_text("\n".join(l for l in logical if not l.lstrip().startswith("set_false_path")) + "\n")
s = s.replace(f"{rel}/6_final.sdc", "/work/outcheck.sdc")
assert "/work/outcheck.sdc" in s, "sdc path not found in corner script"
s += """
report_checks -path_delay max -to [all_outputs] -group_path_count 100000 -endpoint_path_count 1 -unique_paths_to_endpoint
puts "=== INPUTS ==="
report_checks -path_delay max -from [all_inputs -no_clocks] -group_path_count 1000000 -endpoint_path_count 1 -unique_paths_to_endpoint
exit
"""
(o / "outcheck.tcl").write_text(s)
out = subprocess.run(["docker", "run", "--rm", "-v", f"{o}:/work", "openroad/orfs:latest", "bash", "-lc",
                      "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/outcheck.tcl"],
                     capture_output=True, text=True).stdout
(o / "outcheck.log").write_text(out)
bad = n = 0
outs, ins = out.split("=== INPUTS ===") if "=== INPUTS ===" in out else (out, "")
def check(text, kind):
    global bad, n
    for blk in text.split("Startpoint: ")[1:]:
        sp = blk.split()[0]
        m = re.search(r"Endpoint: (\S+)", blk)
        if not m:
            continue
        ep = m.group(1)
        if kind == "in" and sp in ("rst_n",):
            continue                     # the asynchronous reset: a reset tree in the parent (recovery/removal)
        n += 1
        cells = re.findall(r"\(([A-Za-z0-9_]+_ASAP7_75t_[RLS])\)", blk)
        seq = [c for c in cells if re.match(r"(DFF|SDF|DHL|DLL|ASYNC|ICG)", c)]
        comb = [c for c in cells if c not in seq and not re.match(r"(BUF|INV|HB)", c)]
        if not seq or comb:
            bad += 1
            print("NOT_REGISTER_DIRECT", kind, sp, "->", ep, sorted(set(comb)))
check(outs, "out")
n_out = n
check(ins, "in")
print(f"outputs {n_out} input_paths {n - n_out} not_register_direct {bad}")
sys.exit(1 if bad or n == 0 else 0)
