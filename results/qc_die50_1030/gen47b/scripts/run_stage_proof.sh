#!/bin/bash
# DIE-QC-50/gen47b: measured stage proof. usage: run_stage_proof.sh NAME ARR_TT ARR_FF RAW_TT RAW_FF
# (1) stage T/F rows from the measured readout (mk_stage_arr.py), (2) main start_stage_emit proof on proofP (the gen47
# physical-path proof the stages were emitted from), (3) main die_sta_related (DIE-QC-45/49 args) with --count-align = the
# gen47 START bind (startplanP/bind.json): every start port re-timed on the MEASURED stage clock pins (count_align_start_ports).
set -u
Q=/srv/opentallas-scratch2/claude; R=$Q/die-qc-50/gen47b; G=$Q/die-qc-50/gen47; S=$Q/wt/die-qc-50-gen47b/results/qc_die50_1030/gen47b/scripts
N=$1; ATT=$2; AFF=$3; RTT=$4; RFF=$5; O=$R/$N; rm -rf $O; mkdir -p $O
python3 $S/mk_stage_arr.py $ATT $G/emitP/emitted/start_stages.json $R/bound/bindings.json $O/arr_TT.txt $O/arr_TT.json $RTT || exit 1
python3 $S/mk_stage_arr.py $AFF $G/emitP/emitted/start_stages.json $R/bound/bindings.json $O/arr_FF.txt $O/arr_FF.json $RFF || exit 1
python3 $R/tools_main/tools/die_plan/start_stage_emit.py proof $G/proofP --stages $G/emitP/emitted/start_stages.json --arr TT=$O/arr_TT.txt --arr FF=$O/arr_FF.txt --clock-netlist $G/emitP/emitted/ctree.v --out $O/proof > $O/st_proof.log 2>&1; echo "STPROOF rc=$?"; tail -2 $O/st_proof.log
T=$R/tools_main/tools/die_plan
systemd-run --user --scope -q -p MemoryMax=64G env PYTHONPATH=$T python3 -I $T/die_sta_related.py $O/proof --plan $R/inputs/plan_qc49.json --out $O/sta --corner TT --corner FF --cppr-lca --clock-ocv table --clock-droop shared --droop-regions $O/proof/droop_regions.json --clock-cal spice_edge --count-align $G/startplanP/bind.json > $O/sta.log 2>&1; echo "STA rc=$? $(date)" | tee $O/status
grep -E -i "START|COUNT-ALIGN|intra |seam " $O/sta.log | cut -c1-400 | head -30
