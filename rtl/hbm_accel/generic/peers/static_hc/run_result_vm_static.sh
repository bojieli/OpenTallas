#!/usr/bin/env bash
set -euo pipefail
OUT=$(realpath -m "${1:?output directory}")
ROOT=$(cd "$(dirname "$0")/../../../../.." && pwd)
mkdir -p "$OUT"
SOURCES=(rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_result_vm_static.sv
 rtl/hbm_accel/generic/peers/static_hc/tb_hgi_hc_result_vm_static.sv
 rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_tap.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v)
cd "$ROOT"
for mutant in 0 1 2 3; do
 /usr/bin/time -v -o "$OUT/m$mutant.compile.time" iverilog -g2012 -s tb_hgi_hc_result_vm_static -Ptb_hgi_hc_result_vm_static.MUT="$mutant" -o "$OUT/m$mutant.vvp" "${SOURCES[@]}" >"$OUT/m$mutant.compile.log" 2>&1
 set +e
 /usr/bin/time -v -o "$OUT/m$mutant.sim.time" vvp "$OUT/m$mutant.vvp" >"$OUT/m$mutant.log" 2>&1
 rc=$?
 set -e
 if [[ $mutant == 0 ]]; then [[ $rc == 0 ]];grep '^HC_RESULT_VM_STATIC PASS' "$OUT/m0.log"
 elif [[ $mutant == 3 ]]; then [[ $rc != 0 ]];grep 'FATAL:.*actual SRAM result readback mismatch' "$OUT/m3.log"
 else [[ $rc != 0 ]];grep 'FATAL:.*source identity/calendar fault' "$OUT/m$mutant.log";fi
 rm "$OUT/m$mutant.vvp"
done
python3 - "$OUT" "${SOURCES[@]}" <<'PY'
import hashlib,json,pathlib,sys
out=pathlib.Path(sys.argv[1])
r={'scope':'actual static HC result producer -> three actual LG taps -> eight native static VM banks and24 real SRAM macro models; component only', 'sources_sha256':{p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in sys.argv[2:]}, 'positive':'PASS','source_identity_mutant':'KILLED','missing_store_slot_mutant':'KILLED','result_payload_mutant':'KILLED at actual SRAM readback','shape':{'HC_positions':8,'FP32_result_words':192,'full_sectors':24,'banks':8,'real_SRAMs':24,'untouched_neighbors':2},'timing':{'HC_tap_write_commit':15,'HC_tap_read_output':18,'HC_consumer_capture':19,'producer_registered_output':1},'limitations':['No arithmetic claim: independent192-word producer fixture exercises exact transport only','Result stores have mask ff: every sector word overwritten; adjacent sectors checked unchanged','No physical timing or throughput qualification; no wholeHC native claim']}
(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
PY
