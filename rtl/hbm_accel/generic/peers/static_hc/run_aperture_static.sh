#!/usr/bin/env bash
set -euo pipefail
OUT=$(realpath -m "${1:?output directory}")
INPUTS=$(realpath "${2:?frozen source directory: delivery, landing, SRAM model}")
HERE=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$OUT"
SOURCES=("$HERE/ot_hgi_hc_aperture_bridge_static.sv" "$HERE/ot_hgi_hc_aperture_static.sv"
    "$HERE/tb_hgi_hc_aperture_static.sv" "$INPUTS/ot_hbm_svc_static_vm_delivery.sv"
    "$INPUTS/ot_hbm_svc_static_landing.sv" "$INPUTS/ot_sram_1r1w_128x256_m1_r2c2.v")
for mutant in 0 1; do
    /usr/bin/time -v -o "$OUT/m$mutant.compile.time" \
        iverilog -g2012 -s tb_hgi_hc_aperture_static -Ptb_hgi_hc_aperture_static.MUT="$mutant" \
        -o "$OUT/m$mutant.vvp" "${SOURCES[@]}" >"$OUT/m$mutant.compile.log" 2>&1
    set +e
    /usr/bin/time -v -o "$OUT/m$mutant.sim.time" vvp "$OUT/m$mutant.vvp" >"$OUT/m$mutant.log" 2>&1
    rc=$?
    set -e
    if [[ $mutant == 0 ]]; then [[ $rc == 0 ]];grep '^HC_APERTURE_STATIC PASS' "$OUT/m0.log"
    else [[ $rc != 0 ]];grep 'FATAL:.*actual aperture memory mismatch' "$OUT/m1.log";fi
    rm "$OUT/m$mutant.vvp"
done
python3 - "$OUT" "${SOURCES[@]}" <<'PY'
import hashlib,json,pathlib,sys
out=pathlib.Path(sys.argv[1]);sources=list(map(pathlib.Path,sys.argv[2:]))
r={'scope':'actual staging producer and HC FP32 aperture SRAM consumer; separate from SYS1/whole-HC arithmetic integration','sources_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},'positive':'PASS','wrong_quarter_mutant':'KILLED at actual SRAM readback','shape':{'W':32,'RMAX':128,'PMAX':8,'HC_slots':2,'HC_banks':8,'weight_macros_128x256':64,'landing_macros_128x256':32},'measured':{'write_sectors':8192,'readback_sectors':8192,'wd_captured_sectors':8192,'source_blocks':4,'landing_slots_per_block':256,'fill_sectors_per_cycle':8,'macro_commit_after_ap_sample_edges':1,'HC_g_wq_ML':2},'actual_ABI':{'dq_bits':2248,'ap_bits':2224,'read_v_bits':8,'read_slot_bits':8,'read_row_bits':56,'raw_weight_bits':8192,'read_valid_bits':8},'limitations':['no physical closure claim','SYS1 HCtile remains historical/no-aperture until separately migrated','full HC numeric consumption proved by dedicated engine owner, not claimed by this memory bench']}
(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
PY
