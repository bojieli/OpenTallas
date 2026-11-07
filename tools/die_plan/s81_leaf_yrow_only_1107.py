#!/usr/bin/env python3
"""t27: keep each bit of exact three-row yrow shift on one PRE_CTS tap.
Opt-in existing tap grouping only; no RTL, source-window, cap, or plan changes.
Apply only to a fresh private copy with the reviewed 41.016um macro channel.
"""
import argparse, hashlib, json, re
from pathlib import Path
GROUP_RE = r"^u_bound[.]g_u_lf0_u_vp_yrow_d[.].*native_memory[^0-9]*[0-2][^0-9]+([0-9]+)[^0-9]"
p=argparse.ArgumentParser();p.add_argument("kit",type=Path);p.add_argument("--apply",action="store_true");a=p.parse_args()
f=a.kit/"config.mk";s=f.read_text();macro=(a.kit/"macro_place.tcl").read_text()
assert re.search(r"^export OT_TAP_MAX_SINKS = 3000$",s,re.M),"keep original cap3000"
assert not re.search(r"^export OT_TAP_GROUP_RE\s*=",s,re.M),"fresh ungrouped copy required"
assert "set ct_gre [expr {[info exists ::env(OT_TAP_GROUP_RE)] ? $::env(OT_TAP_GROUP_RE) : {}}]" in (a.kit/"clock_taps.tcl").read_text(),"baseline group default must be disabled; do not replace additive groups"
assert "export PRE_CTS_TCL = /work/pre_cts.tcl" in s
assert "source /work/clock_taps.tcl" in (a.kit/"pre_cts.tcl").read_text()
for n in ("a","b"):
 assert re.search(r"u_bound.u_u_lf0_u_vn_u_"+n+r"\} -location \{509[.]8920 ",macro),"retain41.016um channel"
assert "-180.0000" in (a.kit/"pre_cts.tcl").read_text(),"keep180ps source window"
assert not re.search(r"^export OT_TAP_FOLLOW_RE\s*=",s,re.M),"baseline follower env must be unset"
out=s+"\nexport OT_TAP_FOLLOW_RE =\n# Exact native three-row shift, bitwise clock affinity; PRE_CTS only.\nexport OT_TAP_GROUP_RE = "+GROUP_RE+"\n"
r={"profile":"s81_leaf_yrow_only_1107","phase":"PRE_CTS after loading 3_place.odb; before repair_clock_inverters and CTS","group_re":GROUP_RE,"prior_group_default":"disabled (deployed empty ct_gre)","follow_re":"","expected_followers":0,"expected_groups":128,"expected_sinks":384,"sinks_per_group":3,"scope":"u_bound.g_u_lf0_u_vp_yrow_d.native_memory rows0..2 only","cap":3000,"source_window_ps":180,"macro_channel_um":41.016,"pin_cycles_added":0,"rtl_changed":False,"plan_changed":False,"source_config_sha256":hashlib.sha256(s.encode()).hexdigest(),"config_sha256":hashlib.sha256(out.encode()).hexdigest(),"next_goal":"one CTS-only pilot from preserved reviewed 3_place; coordinator review before launch"}
print(json.dumps(r,indent=2))
if a.apply:f.write_text(out);(a.kit/"CLOCK_AFFINITY_PROFILE.json").write_text(json.dumps(r,indent=2)+"\n")
