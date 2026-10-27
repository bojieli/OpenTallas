"""Use the PV pair staged leaf connections as the physical clock contract."""
import re
from collections import Counter
from pathlib import Path
def update(cj, rtl_dir):
    if cj["module"]!="kv3_pv_pair":return cj
    text=(Path(rtl_dir)/"kv3_pv_pair.sv").read_text()
    text=re.sub(r"//[^\n]*|/\*.*?\*/","",text,flags=re.S)
    clock_bits=[b for b,c in cj["pin_class"].items() if c in ("clk","clk_unused")]
    live=[b for b in clock_bits if re.search(r"\.clk\s*\(\s*"+re.escape(b)+r"\s*\)",text)]
    if not live:raise ValueError("PVpair has no declared physical clock connected to a leaf")
    for b in clock_bits:cj["pin_class"][b]="clk" if b in live else "clk_unused"
    cj["report"]["clk_unused"]=[b for b in clock_bits if b not in live]
    cj["report"]["clock_nets"]={"clk":live[0]}
    cj["report"]["live_clock_ports"]=live
    cj["report"]["clock_domain"]="one related833ps core clock; staged leaf connections are authoritative"
    cj["classes"]=dict(Counter(cj["pin_class"].values()))
    return cj
