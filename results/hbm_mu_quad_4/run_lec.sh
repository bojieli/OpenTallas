#!/bin/bash
# run_lec.sh WT CANON_DIR : wiring-map LEC of every pgslice member wrapper vs canonical strap wrapper (docker orfs yosys)
WT=$1; C=$2; WD=$WT/physical/die_plan/hbm_arch_cores/wrappers; RT=$WT/rtl/hbm_accel/cores_split/ot_hbm_su_static_pgslice_lg
cd $C; mkdir -p lec; : > lec/summary.txt
python3 - "$C" > lec/jobs.txt <<'PY'
import json,sys
m=json.load(open(sys.argv[1]+"/canon_manifest.json"))
for cn,v in m.items():
    if cn.endswith("#top"): continue
    for e in v: print(cn, e["member"], m[cn+"#top"])
PY
while read cn mem top; do
  cat > lec/$mem.gold.ys <<Y
read_verilog -sv -lib $RT/$top.sv
read_verilog -sv $WD/$mem.sv
hierarchy -top $mem
proc; flatten; opt_clean -purge
write_json lec/$mem.gold.json
Y
  cat > lec/$mem.gate.ys <<Y
read_verilog -sv -lib $RT/$top.sv
read_verilog -sv $C/$cn.sv $C/shim_$mem.sv
hierarchy -top $mem
proc; flatten; opt_clean -purge
write_json lec/$mem.gate.json
Y
done < lec/jobs.txt
docker run --rm --memory=8g --cpus=4 -v $WT:$WT -w $C openroad/orfs:asap7lock bash -c '
Y=$(ls /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys 2>/dev/null || which yosys)
while read cn mem top; do $Y -q -l lec/$mem.gold.log lec/$mem.gold.ys >/dev/null 2>&1; echo "gold $mem rc=$?"; $Y -q -l lec/$mem.gate.log lec/$mem.gate.ys >/dev/null 2>&1; echo "gate $mem rc=$?"; done < lec/jobs.txt' > lec/yosys_rc.txt 2>&1
while read cn mem top; do echo "$mem -> $cn: $(python3 $C/../../../../results/hbm_mu_quad_4/wiremap_lec.py lec/$mem.gold.json lec/$mem.gate.json 2>&1 | tail -1)" >> lec/summary.txt; done < lec/jobs.txt
cat lec/summary.txt; grep -c "rc=0" lec/yosys_rc.txt
