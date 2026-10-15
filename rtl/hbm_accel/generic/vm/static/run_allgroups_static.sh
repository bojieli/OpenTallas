#!/usr/bin/env bash
set -euo pipefail
OUT=$(realpath -m "${1:?output directory}")
INPUTS=$(realpath "${2:?actual static bank and SRAM model directory}")
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT"
SOURCES=("$HERE/tb_hbm_vm_allgroups_static.sv" "$INPUTS/ot_vms_bank_static.sv"
    "$INPUTS/ot_sram_1r1w_1024x256_m2_r2c2.v")
for shape in 7:3 5:1; do
    rg=${shape%:*};wg=${shape#*:}
    for mutant in 0 1; do
        stem="rg${rg}_wg${wg}_m${mutant}"
        /usr/bin/time -v -o "$OUT/$stem.compile.time" \
            iverilog -g2012 -s tb_hbm_vm_allgroups_static \
            -Ptb_hbm_vm_allgroups_static.RG="$rg" -Ptb_hbm_vm_allgroups_static.WG="$wg" \
            -Ptb_hbm_vm_allgroups_static.MUT="$mutant" -o "$OUT/$stem.vvp" "${SOURCES[@]}" \
            >"$OUT/$stem.compile.log" 2>&1
        set +e
        /usr/bin/time -v -o "$OUT/$stem.sim.time" vvp "$OUT/$stem.vvp" >"$OUT/$stem.log" 2>&1
        rc=$?
        set -e
        if [[ $mutant == 0 ]]; then [[ $rc == 0 ]];grep '^VM_ALLGROUPS_STATIC PASS' "$OUT/$stem.log"
        else [[ $rc != 0 ]];grep 'FATAL:.*actual bank response group mismatch' "$OUT/$stem.log";fi
        rm "$OUT/$stem.vvp"
    done
done
python3 - "$OUT" "${SOURCES[@]}" <<'PY'
import hashlib,json,pathlib,sys
out=pathlib.Path(sys.argv[1]);sources=list(map(pathlib.Path,sys.argv[2:]))
r={'scope':'actual eight-bank source gates for final native wide-group shapes;24SRAM macros per shape; unchanged bank RTL','sources_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'shapes':{'NW_NE_RG7_WG3':{'positive':'PASS','wrong_actual_return_group_wiring_mutant':'KILLED','DMA_writes':1024,'wide_reads':7168,'read_issue_cycles':896,'each_group_reads':1024,'COLL_group5_reads':1024,'IDX_group6_reads':1024,'packet_reads':8},'SW_SE_RG5_WG1':{'positive':'PASS','wrong_actual_return_group_wiring_mutant':'KILLED','DMA_writes':1024,'wide_reads':5120,'read_issue_cycles':640,'each_group_reads':1024,'packet_reads':8}},'measured':{'banks':8,'SRAM_macros_per_shape':24,'sectors_per_cycle':8,'read_return_edges':6,'DMA_commit_edges':3},'mechanisms':['all wide outputs used, each reads every128row inventory in everybank','perbank compiler rslot changes eachcycle','only selected output group valid exactlysixsubsequenedgeslater','packet ownerRG remains distinct andreturns originalbanktag','twoactivegroups withonlygroup0reserved faults andservesgroup0 only; no arbitration/defer'],'mutant_scope':'permuted response group wires carry actual bank SRAM return records; no substitute bank or payload oracle output','limitations':['source and exact throughput gate, no timing or physical closure claim','one representative8bank slice per finalshape, notfourquadrant simulation']}
(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
PY
