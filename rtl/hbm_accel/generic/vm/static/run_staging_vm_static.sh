#!/usr/bin/env bash
set -euo pipefail
OUT=$(realpath -m "${1:?output directory}")
INPUTS=$(realpath "${2:?frozen directory containing actual source and SRAM models}")
TB=$(realpath "$(dirname "$0")/tb_hbm_staging_vm_static.sv")
mkdir -p "$OUT"
SOURCES=("$INPUTS/ot_hbm_svc_static_vm_delivery.sv" "$INPUTS/ot_hbm_svc_static_landing.sv"
    "$INPUTS/ot_vms_bank_static.sv" "$INPUTS/ot_sram_1r1w_128x256_m1_r2c2.v"
    "$INPUTS/ot_sram_1r1w_1024x256_m2_r2c2.v" "$TB")
for mutant in 0 1; do
    /usr/bin/time -v -o "$OUT/m$mutant.compile.time" \
        iverilog -g2012 -s tb_hbm_staging_vm_static -Ptb_hbm_staging_vm_static.MUT="$mutant" \
        -o "$OUT/m$mutant.vvp" "${SOURCES[@]}" >"$OUT/m$mutant.compile.log" 2>&1
    set +e
    /usr/bin/time -v -o "$OUT/m$mutant.sim.time" vvp "$OUT/m$mutant.vvp" >"$OUT/m$mutant.log" 2>&1
    rc=$?
    set -e
    if [[ $mutant == 0 ]]; then
        [[ $rc == 0 ]]
        grep '^HBM_STAGING_VM_STATIC PASS' "$OUT/m0.log"
    else
        [[ $rc != 0 ]]
        grep 'FATAL:.*actual VM memory mismatch' "$OUT/m1.log"
    fi
    rm "$OUT/m$mutant.vvp"
done
python3 - "$OUT" "${SOURCES[@]}" <<'PY'
import hashlib,json,pathlib,sys
out=pathlib.Path(sys.argv[1]);sources=map(pathlib.Path,sys.argv[2:])
receipt={'scope':'actual SRAM staging to actual VM SECDED banks; behavioural macro models; no physical timing claim','sources_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'positive':'PASS','mutant_row_address_bit3':'KILLED at actual VM readback, not by source-port checking','shape':{'landing_SRAMs_128x256':32,'VM_SRAMs_1024x256':24,'VM_banks':8,'RG':3,'WG':1,'DMA_wslot':5},'measured':{'write_sectors':2048,'readback_sectors':2048,'delivery_slots':256,'sectors_per_cycle':8,'VM_sample_to_commit_edges':3,'VM_read_sample_to_response_edges':6},'landing_fill':{'epoch':77,'base_sector':'0x2800','sid':1,'pattern':'{8{0x17624611 ^ (pseudochannel << 12) ^ slot}}'}}
(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
PY
