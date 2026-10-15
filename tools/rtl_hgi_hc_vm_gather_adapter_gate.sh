#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=$(realpath -m "${1:?output directory}")
mkdir -p "$OUT"
cd "$ROOT"
SOURCES=(rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_vm_gather_adapter_static.sv
 rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_gathered_mix_reader_static.sv
 rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_tap.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 rtl/test/tb_hgi_hc_vm_gather_adapter_static.sv)
/usr/bin/time -v -o "$OUT/compile.time" iverilog -g2012 -s tb_hgi_hc_vm_gather_adapter_static -o "$OUT/gate.vvp" "${SOURCES[@]}" >"$OUT/compile.log" 2>&1
/usr/bin/time -v -o "$OUT/positive.time" vvp "$OUT/gate.vvp" >"$OUT/positive.log" 2>&1
grep 'HC_VM_GATHER_ADAPTER PASS' "$OUT/positive.log"
for case in MUTANT COLLISION; do
 set +e
 /usr/bin/time -v -o "$OUT/$case.time" vvp "$OUT/gate.vvp" +"$case" >"$OUT/$case.log" 2>&1
 rc=$?
 set -e
 [[ $rc != 0 ]]
 if [[ $case == MUTANT ]]; then grep 'FATAL:.*residual mux readback mismatch' "$OUT/$case.log"
 else grep 'FATAL:.*native/reader fault' "$OUT/$case.log";fi
done
rm "$OUT/gate.vvp"
python3 - "$OUT" "${SOURCES[@]}" <<'PY'
import hashlib,json,pathlib,sys
out=pathlib.Path(sys.argv[1]);paths=sys.argv[2:]+['tools/rtl_hgi_hc_vm_gather_adapter_gate.sh']
r={'scope':'opt-in native-wrapper shared VM port adapter only, actual8banks24SRAM+3LG; no arithmetic/whole-native/physical qualification','source_sha256':{p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in paths},'positive':'PASS','actual_SRAM_payload_mutant':'KILLED at real residual readback','actual_compiler_phase_collision_mutant':'KILLED stickyfault','enabled':{'canonical_P1_stride0':24,'component_P6_P8_stride3_5':672,'shared_residual_readback':1,'neighbor_readbacks':4,'same_VM_ports':True,'additional_pipeline_edges':0},'disabled':'every residual rq/read/rr and external gathered payload bit passes with no added edge','timing':{'gather_request_sample':1,'registered_word0':20,'engine_capture':21},'logs_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.log')},'full_native_qualified':False,'physical_qualified':False}
(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
PY
