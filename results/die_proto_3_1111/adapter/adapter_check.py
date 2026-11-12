"""DIE-PROTO-3: time the adapter's die_ctree (ctree.v + ctree.spef) standalone in OpenSTA (TT) and compare every tap
port arrival with the combo GRT readout (arr_TT.txt, same RC).  usage: adapter_check.py DIE_CTREE_DIR ARR_TT OUT_JSON"""
import json, subprocess, sys, os
from pathlib import Path
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/die-proto-3/tools/die_plan")
import die_sta
d, arr, out = sys.argv[1:4]
libs = die_sta.corner_libs("TT")
tcl = Path(d) / "check_TT.tcl"
tcl.write_text("\n".join([f"read_liberty {l}" for l in libs] + [
    f"read_verilog {d}/ctree.v", "link_design die_ctree", f"read_spef {d}/ctree.spef",
    "create_clock -name vclk -period 833.333", "set_driving_cell -lib_cell BUFx24_ASAP7_75t_R -pin Y [get_ports root]",
    "set_input_delay 0 -clock vclk [get_ports root]", "set_load 3.0 [get_ports t_*]",
    "set_output_delay 0 -clock vclk [all_outputs]", "report_parasitic_annotation",
    f"set fh [open {d}/arr_check_TT.txt w]",
    "foreach p [get_ports t_*] { puts $fh \"T [get_full_name $p] [expr {833.333 - [get_property $p slack_max_rise]}]\" }",
    "close $fh", "exit"]) + "\n")
sta = os.path.expanduser("~/.local/opentallas-tools/bin/sta")
r = subprocess.run([sta, "-no_init", "-no_splash", str(tcl)], capture_output=True, text=True, timeout=3600)
ann = [l for l in r.stdout.splitlines() if "nnotat" in l or "Found" in l][:8]
ref = {l.split()[1]: float(l.split()[2]) for l in open(arr) if l.startswith("T ")}
new = {l.split()[1]: float(l.split()[2]) for l in open(f"{d}/arr_check_TT.txt") if l.startswith("T ")}
diff = sorted(((abs(new[p] - ref[p]), p, ref[p], new[p]) for p in ref if p in new), reverse=True)
res = dict(ports_ref=len(ref), ports_new=len(new), compared=len(diff), max_abs_diff_ps=diff[0][0] if diff else None,
           p99_abs_diff_ps=diff[len(diff) // 100][0] if diff else None, worst=diff[:5], annotation=ann, sta_rc=r.returncode,
           stderr_tail=r.stderr[-800:])
Path(out).write_text(json.dumps(res, indent=1))
print(json.dumps({k: res[k] for k in ("ports_ref", "ports_new", "compared", "max_abs_diff_ps", "p99_abs_diff_ps", "worst", "annotation", "sta_rc")}, indent=1))
