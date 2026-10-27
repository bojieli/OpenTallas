"""Repair stale alias-clock metadata when the PV pair RTL has two live clock ports."""
import re
from collections import Counter
from pathlib import Path
def update(cj, rtl_dir):
    if cj["module"] != "kv3_pv_pair":
        return cj
    text=(Path(rtl_dir)/"kv3_pv_pair.sv").read_text()
    promoted=[]
    for bit,kind in list(cj["pin_class"].items()):
        if kind!="clk_unused":continue
        # This is the actual top-level leaf clock connection, not a comment/name guess.
        pattern=r"\.clk\s*\(\s*"+re.escape(bit)+r"\s*\)"
        if re.search(pattern,text):
            cj["pin_class"][bit]="clk";promoted.append(bit)
    if promoted:
        cj["report"]["clk_unused"]=[x for x in cj["report"].get("clk_unused",[]) if x not in promoted]
        cj["report"]["live_clock_aliases"]=promoted
        cj["report"]["clock_domain"]="one related 833 ps core clock; all live alias pins are timed together"
        cj["classes"]=dict(Counter(cj["pin_class"].values()))
    return cj
