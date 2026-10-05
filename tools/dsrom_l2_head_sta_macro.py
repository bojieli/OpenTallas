#!/usr/bin/env python3
"""Re-run the SS pre-layout STA of an element screen with the ROM macro's LEF and SS liberty (macro timing arcs)."""
import json, re, shutil, sys
from pathlib import Path
R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "tools"))
from chip_assembly import orfs  # noqa
work = Path(sys.argv[1]).resolve(); top = sys.argv[2]
m = R / "physical/asap7_memory_macros/ot_rom_4096x274_m8"
for f in ("ot_rom_4096x274_m8.lef", "ot_rom_4096x274_m8_ss.lib"):
    shutil.copy(m / f, work / f)
t = (work / "ss.tcl").read_text()
if "ot_rom_4096x274_m8.lef" not in t:
    t = t.replace("read_verilog", "read_lef /work/ot_rom_4096x274_m8.lef\nread_liberty /work/ot_rom_4096x274_m8_ss.lib\nread_verilog", 1)
    (work / "ss.tcl").write_text(t)
orfs.docker_openroad(work, "/work/ss.tcl", "ss.log")
wns = None
for line in (work / "ss.log").read_text(errors="replace").splitlines():
    if line.startswith("OTC wns"):
        wns = float(line.split()[2]) * 1e12
rpt = (work / "ss_worst.rpt").read_text(errors="replace")
ends = (work / "ss_ends.rpt").read_text(errors="replace")
stages = {}
for mm in re.finditer(r"^(\S+)/D \(\S+\)\s+[-0-9.]+\s+[-0-9.]+\s+([-0-9.]+)", ends, re.M):
    name = re.sub(r"\[\d+\]", "", mm.group(1)).split("$")[0]
    stages[name] = min(stages.get(name, 1e9), float(mm.group(2)))
neg = sum(1 for mm in re.finditer(r"^\S+\s+\(\S+\)\s+[-0-9.]+\s+[-0-9.]+\s+(-[0-9.]+)", ends, re.M))
out = dict(top=top, work=str(work), ss_setup_wns_ps=None if wns is None else round(wns, 1),
           worst_start=(re.search(r"Startpoint: (\S+)", rpt) or [None, None])[1],
           worst_end=(re.search(r"Endpoint: (\S+)", rpt) or [None, None])[1], negative_endpoints=neg,
           worst_slack_by_stage_ps=dict(sorted(stages.items(), key=lambda kv: kv[1])[:25]))
(work / "ss_macro.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out))
