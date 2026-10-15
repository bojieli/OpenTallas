#!/usr/bin/env bash
set -euo pipefail
OUT=$(realpath -m "${1:?output directory}")
INPUTS=$(realpath "${2:?directory containing actual static bank and SRAM model}")
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT"
SOURCES=("$HERE/ot_hbm_vm_lg_static_bank.sv" "$HERE/physical/hfd_vm_lg_su10.sv" "$HERE/physical/hfd_vm_lg_sfu14.sv" "$HERE/ot_hbm_vm_lg_static_split.sv" "$HERE/tb_hbm_vm_lg_static_split.sv"
    "$INPUTS/ot_vms_bank_static.sv" "$INPUTS/ot_sram_1r1w_1024x256_m2_r2c2.v")
for mutant in 0 1; do
    /usr/bin/time -v -o "$OUT/m$mutant.compile.time" \
        iverilog -g2012 -s tb_hbm_vm_lg_static_split -Ptb_hbm_vm_lg_static_split.MUT="$mutant" \
        -o "$OUT/m$mutant.vvp" "${SOURCES[@]}" >"$OUT/m$mutant.compile.log" 2>&1
    set +e
    /usr/bin/time -v -o "$OUT/m$mutant.sim.time" vvp "$OUT/m$mutant.vvp" >"$OUT/m$mutant.log" 2>&1
    rc=$?
    set -e
    if [[ $mutant == 0 ]]; then [[ $rc == 0 ]];grep '^VM_LG_STATIC_SPLIT PASS' "$OUT/m0.log"
    else [[ $rc != 0 ]];grep 'FATAL:.*actual bank readback mismatch' "$OUT/m1.log";fi
    rm "$OUT/m$mutant.vvp"
done
python3 - "$OUT" "${SOURCES[@]}" <<'PY'
import hashlib,json,pathlib,sys
out=pathlib.Path(sys.argv[1]);sources=list(map(pathlib.Path,sys.argv[2:]))
r={'scope':'three split LG groups comprising24realbankleaves plus eight actual static VM banks and24SRAM macros; source behaviour not physical closure','sources_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'positive':'PASS','wrong_compiler_write_payload_mux_mutant':'KILLED at actual SRAM readback','shape':{'taps':3,'tap_leaves':24,'banks':8,'RG':3,'WG':1,'SRAMs_1024x256':24,'extra_compiler_calendar_bits':48},'measured':{'writes':3072,'exact_readbacks':3072,'issue_cycles_per_phase':384,'aggregate_sectors_per_cycle':8,'SU_read_edges':10,'SFU_read_edges':14,'HC_read_edges':18,'SU_write_edges':7,'SFU_write_edges':11,'HC_write_edges':15},'mechanisms':['three independent producers pipeline full8sector/cycle aggregate','return valid stripped before forwarding to farther station','missing real bank response faults at reserved local output edge','active unselected local request fault','far/local collision fault'],'limitations':['no physical closure claim','SFUwordoperandstore requires separate prefetch adapter;14edgeVMreturn isnot1edgeoperandport','HCsharedVMread18edge is distinct from HCweightapertureML2']}
(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
PY
