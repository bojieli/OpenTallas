"""Per-port boundary characterisation of a synthesised block.

For every port bus of a mapped netlist, OpenSTA reports (ideal clock, zero
wire load, the corner's liberty):

* input  -- ``in2reg_ps``: the latest arrival at a register D pin (setup
  included) from the port, with the port arriving at time 0;
* output -- ``reg2out_ps``: the latest arrival at the port from a clock edge
  (clock-to-q included);
* ``feedthrough_ps`` when a combinational input-to-output path exists.

These are the numbers a budget divides the cycle with: a registered input
needs only its setup, a registered output only its clock-to-q, and a port
behind logic needs its logic depth.  Pre-layout numbers exclude wire and
repair buffering; the budget adds a growth allowance for that.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

STA = Path.home() / ".local/opentallas-tools/opensta-be771a0/bin/sta"
ASAP7_NLDM = Path.home() / ".local/opentallas-pdk-asap7/lib/NLDM"
STD_LIBS = sorted(ASAP7_NLDM.glob("asap7sc7p5t_*_RVT_TT_*.lib"))

TCL = r"""
foreach f {%(libs)s} { read_liberty $f }
foreach f {%(netlists)s} { read_verilog $f }
link_design %(top)s
create_clock -name clk -period %(period_ps)s [get_ports %(clock)s]
set ins [list]
foreach p [all_inputs] { if {[get_name $p] ne "%(clock)s"} { lappend ins $p } }
set_input_delay 0 -clock clk $ins
set_output_delay 0 -clock clk [all_outputs]
foreach p [get_ports *] {
  set n [get_name $p]
  if {$n eq "%(clock)s"} continue
  set net [get_nets -quiet $n]
  set used 0
  if {[llength $net] > 0} { set used [llength [get_pins -quiet -of_objects $net]] }
  puts "OTP [get_property $p direction] $n $used [get_property $p slack_max]"
}
# every input bus separately, so a through-path is found from each start bus,
# not only from the worst one per output
set fbuses [dict create]
foreach p $ins { regsub {\[[0-9]+\]$} [get_name $p] "" b; dict lappend fbuses $b $p }
foreach b [dict keys $fbuses] {
  set ft [find_timing_paths -from [dict get $fbuses $b] -to [all_outputs] -path_delay max -group_path_count 100000 -endpoint_path_count 1]
  foreach e $ft {
    puts "OTF [get_full_name [get_property $e startpoint]] [get_full_name [get_property $e endpoint]] [expr %(period_ps)s - [get_property $e slack]]"
  }
}
exit
"""


def _num(text: str) -> float | None:
    return None if text == "none" else round(float(text), 2)


def characterise(netlists: list[Path], top: str, work: Path, *, clock: str = "clk",
                 period_ps: float = 1000.0, extra_libs: list[Path] | None = None,
                 timeout: int = 7200) -> dict[str, Any]:
    work.mkdir(parents=True, exist_ok=True)
    libs = [*STD_LIBS, *(extra_libs or [])]
    script = work / f"boundary_{top}.tcl"
    script.write_text(TCL % {
        "libs": " ".join(str(p) for p in libs),
        "netlists": " ".join(str(p) for p in netlists),
        "top": top, "clock": clock, "period_ps": period_ps,
    }, encoding="utf-8")
    proc = subprocess.run([str(STA), "-no_init", "-exit", str(script)], capture_output=True,
                          text=True, timeout=timeout, check=False)
    (work / f"boundary_{top}.log").write_text(proc.stdout + proc.stderr, encoding="utf-8")
    ports: dict[str, Any] = {}
    for line in proc.stdout.splitlines():
        if not line.startswith("OTP "):
            continue
        _, direction, name, used, slack = line.split()
        bus = re.sub(r"\[\d+\]$", "", name)
        entry = ports.setdefault(bus, {"direction": direction, "width": 0, "unused_bits": 0,
                                       "worst_slack_ps": None})
        entry["width"] += 1
        if int(used) == 0:
            entry["unused_bits"] += 1
            continue
        sl = float(slack)
        if sl > 1e20:
            continue
        if entry["worst_slack_ps"] is None or sl < entry["worst_slack_ps"]:
            entry["worst_slack_ps"] = sl
    for entry in ports.values():
        sl = entry.pop("worst_slack_ps")
        key = "in2reg_ps" if entry["direction"] == "input" else "reg2out_ps"
        entry[key] = None if sl is None else round(period_ps - sl, 2)
    for line in proc.stdout.splitlines():
        if line.startswith("OTF "):
            _, start, end, delay = line.split()
            for name in (start, end):
                bus = re.sub(r"\[\d+\]$", "", name)
                if bus in ports:
                    prev = ports[bus].get("feedthrough_ps") or 0.0
                    ports[bus]["feedthrough_ps"] = round(max(prev, float(delay)), 2)
    if not ports:
        raise RuntimeError(f"boundary characterisation of {top} produced nothing; see {work}")
    return {
        "top": top,
        "period_ps": period_ps,
        "netlists": [str(p) for p in netlists],
        "basis": ("OpenSTA, ideal clock, zero wire load, ASAP7 RVT TT liberty; inputs arrive at 0 "
                  "and outputs are required at the period, so a port's worst slack gives "
                  "in2reg = period - slack (setup included) for an input and reg2out = period - "
                  "slack (clock-to-q included) for an output; a combinational input-to-output "
                  "path, when present, is feedthrough_ps on both ends; unused_bits are ports "
                  "with no connection inside the block"),
        "ports": ports,
    }


def write(result: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
