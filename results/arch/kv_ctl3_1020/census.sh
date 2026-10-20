#!/bin/bash
# usage: census.sh G   (G = remote ref_gate dir of a synth gate)  -> G/census/native_census.json
G=$1; mkdir -p $G/census; cd $G/census || exit 2
N=$(ls $G/routes/gate/work/orfs/results/asap7/*/base/1_2_yosys.v | head -1); echo "NETLIST $N"
docker run --rm --network none -v $G/census:/c openroad/orfs:asap7lock bash -c 'B=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM; for t in AO INVBUF OA SEQ SIMPLE; do f=$(ls $B/asap7sc7p5t_${t}_RVT_TT_nldm_*lib* | head -1); case $f in *.gz) zcat $f > /c/$t.lib;; *) cp $f /c/$t.lib;; esac; done'
L=""; for f in $G/census/*.lib $G/src/physical/asap7_memory_macros_v2/ctl_sram_*/*_tt.lib; do L="$L --liberty $f"; done
python3 $G/src/tools/ref_tile/native_census.py --netlist $N --top qkd_kvs_ctl_s32 $L --out $G/census/native_census.json; rc=$?
python3 - $G/census/native_census.json <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
print("CENSUS",d["status"],"max",d.get("max_dynamic_loads"),"roots",d.get("roots_examined"),"viol",len(d.get("violations",[])),d.get("role_errors",[])[:3])
for v in d.get("violations",[])[:40]: print(" V",str(v)[:300])
PY
exit $rc
