#!/bin/bash
# mk_fd4.sh VARIANT (mc|cc) -- on intel1: new kv3_pv_pair kit from fd3_et (same RTL/pins/outline) + fresh tools +
#   in-flow MCMM (CORNERS tc bc, FF hold repaired in CTS/GRT repair) + fanout cap 24 via PRE_RESIZE/CTS/GLOBAL_ROUTE hooks (default closing recipe m8 in-flow)
#   cc: + clock entry at the N-face centre pin s1__clk (x 195.4) instead of the corner pin s0__clk (x 7.5); s0__clk unused
set -euo pipefail
V=$1; S=/srv/opentallas-scratch2/claude/kv-cores/par/kv3_pv_pair/fd3_et; SRC=/srv/opentallas-scratch2/claude/kv-cores-1025r/src
K=/srv/opentallas-scratch2/claude/kv-cores-1025r/par/kv3_pv_pair/fd4_$V
test ! -e $K || { echo "exists $K"; exit 2; }
mkdir -p $K
rsync -a --exclude /run --exclude /views --exclude /signoff --exclude '/signoff*.log' --exclude '/run_*.log' --exclude /rc.txt \
  --exclude /__pycache__ --exclude /face_guard*.json --exclude /face_guard*.log --exclude /1_synth_odb.v --exclude /synth_odb_v.* \
  --exclude /pin_audit.json --exclude /sdc_lint.log $S/ $K/
for f in sdc_lint.py face_guard.py selrange_gate.py signoff.py; do cp $SRC/tools/die_plan/$f $K/; done
cp $SRC/physical/common_flow/clock_family.tcl $K/
H=$SRC/physical/die_plan/qwen_kvsys/cores/harden
for f in pin_audit_core.py corners.tcl run_kit_kv.sh core_preflight.py; do cp $H/$f $K/; done
cat >> $K/config.mk <<CFG
# KV-CORES/PV-PC 10-25 fd4_$V: in-flow default closing recipe (COORD 00:32 m8 in-flow; warm ECOs dead for this core:
# GRT-0013 / DRT SIGSEGV): MCMM tc+bc for floorplan..route so CTS/GRT repair_timing fixes FF hold (margin 5 above the SDC)
# and TT setup together; the fanout cap 24 hook makes repair_design split the fanout-99 control nets (c_r -> lanes).
export CORNERS = tc bc
export TC_LIB_FILES = \$(TC_NLDM_LIB_FILES) /work/macros/ot_sram_1r1w_32x128_m1_tt.lib
export BC_LIB_FILES = \$(BC_NLDM_LIB_FILES) /work/macros/ot_sram_1r1w_32x128_m1_ff.lib
override export PWR_NETS_VOLTAGES =
override export GND_NETS_VOLTAGES =
CFG
# fanout cap 24 is an in-flow hook, not golden SDC (sdc_lint forbids set_max_fanout, fail-closed)
printf "set_max_fanout 24 [current_design]\nputs \"KVCORES max_fanout 24\"\n" > $K/max_fanout.tcl
cat >> $K/config.mk <<CFG
export PRE_RESIZE_TCL = /work/max_fanout.tcl
export PRE_CTS_TCL = /work/max_fanout.tcl
export PRE_GLOBAL_ROUTE_TCL = /work/max_fanout.tcl
export SLEW_MARGIN = 20
export CAP_MARGIN = 20
CFG
if [ $V = cc ]; then
  # clock entry at the face centre: the core's clock tree root is the N-centre clock pin
  sed -i 's/\.clk(s0__clk\[0\])/.clk(s1__clk[0])/g' $K/rtl/kv3_pv_pair.sv
  sed -i 's/get_ports {s0__clk}/get_ports {s1__clk}/g' $K/constraint.sdc
  # provisional early tap: fd3_et TT pin-flop mean 356.76 minus the measured 72 ps corner->centre trunk (wire15158/15157) = ~285 -> -35
  sed -i 's/set_clock_latency -source -106.7600 \[get_ports {s1__clk}\]/set_clock_latency -source -35.0000 [get_ports {s1__clk}]/' $K/constraint.sdc
  python3 - $K <<'PY'
import json, sys, pathlib
k = pathlib.Path(sys.argv[1])
b = json.loads((k/"boundary_guard_context.json").read_text()); b["clock_ports"] = ["s1__clk"]; b["unused_clock_ports"] = ["s0__clk"]
(k/"boundary_guard_context.json").write_text(json.dumps(b, indent=1))
t = (k/"sdc_lint.json").read_text()
d = json.loads(t)
def sw(o):
    if isinstance(o, dict): return {("s1__clk" if kk == "s0__clk" else kk): sw(v) for kk, v in o.items()}
    if isinstance(o, list): return [sw(v) for v in o]
    return "s1__clk" if o == "s0__clk" else o
d = sw(d)
if "port_latency_ps" in d: d["port_latency_ps"]["s1__clk"] = -35.0
(k/"sdc_lint.json").write_text(json.dumps(d, indent=1))
c = json.loads((k/"core.json").read_text())
def swc(o):
    if isinstance(o, dict):
        r = {}
        for kk, v in o.items():
            nk = {"s0__clk": "s1__clk", "s1__clk": "s0__clk", "s0__clk[0]": "s1__clk[0]", "s1__clk[0]": "s0__clk[0]"}.get(kk, kk)
            r[nk] = swc(v)
        return r
    if isinstance(o, list): return [swc(v) for v in o]
    return {"s0__clk[0]": "s1__clk[0]"}.get(o, o) if isinstance(o, str) else o
# only roles move: the clk role goes to s1__clk, clk_unused to s0__clk (pins/positions untouched)
for key in ("pin_class", "boundary_role"):
    if key in c and isinstance(c[key], dict):
        a, b2 = c[key].get("s0__clk[0]", c[key].get("s0__clk")), c[key].get("s1__clk[0]", c[key].get("s1__clk"))
        for n0, n1 in (("s0__clk[0]", "s1__clk[0]"), ("s0__clk", "s1__clk")):
            if n0 in c[key] and n1 in c[key]: c[key][n0], c[key][n1] = c[key][n1], c[key][n0]
c["clock_entry_note"] = "KV-CORES/PV-PC 10-25 fd4_cc: clock root = N-face centre pin s1__clk (x 195.4) instead of corner s0__clk (x 7.5); parent split must feed s1__clk (READY proposal)"
(k/"core.json").write_text(json.dumps(c, indent=1))
PY
  sed -i 's/^set ff_skip_re {^(s0__clk|s0__rst_n|s1__rst_n)\$}/set ff_skip_re {^(s0__clk|s1__clk|s0__rst_n|s1__rst_n)$}/' $K/face_flops.tcl
  # sdc_lint context: s0__clk becomes a plain (unused) input, s1__clk the clock port
  python3 - $K <<'PY2'
import json, sys
k = sys.argv[1]; d = json.load(open(k + '/sdc_lint.json'))
for n, v in d.items():
    if isinstance(v, list) and n != 'clock_ports' and 's1__clk' in v: d[n] = sorted('s0__clk' if x == 's1__clk' else x for x in v)
    if isinstance(v, dict) and n != 'port_latency_ps' and 's1__clk' in v: v['s0__clk'] = v.pop('s1__clk')
json.dump(d, open(k + '/sdc_lint.json', 'w'), indent=1)
c = json.load(open(k + '/core.json')); c['report']['clk_unused'] = ['s0__clk[0]']; c['report']['clock_nets'] = {'clk': 's1__clk[0]'}
json.dump(c, open(k + '/core.json', 'w'), indent=1)
PY2
fi
echo "{\"variant\": \"fd4_$V\", \"base\": \"intel1:$S (fd3_et kit: RTL f6bd3712f fault dup, pins/outline v3.9 unchanged)\", \"changes\": \"tools refreshed from claude/kv-cores-1025r@3818de1fa; CORNERS tc bc in-flow; SDC set_max_fanout 24$( [ $V = cc ] && echo '; clock root s1__clk (N-face centre), provisional early tap -35' )\", \"by\": \"KV-CORES/PV-PC $(date '+%F %H:%M %Z')\"}" > $K/KIT_NOTE.json
grep -n "clk" $K/constraint.sdc | head -8; grep -c "s1__clk\[0\]" $K/rtl/kv3_pv_pair.sv
