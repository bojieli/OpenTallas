#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=$(realpath -m "${1:?output directory}")
mkdir -p "$OUT"
cd "$ROOT"
SOURCES=(rtl/hbm_accel/generic/peers/static_hc/ot_hgi_hc_gathered_mix_reader_static.sv
 rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_tap.sv
 rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
 rtl/test/tb_hgi_hc_gathered_mix_reader_static.sv)
/usr/bin/time -v -o "$OUT/compile.time" iverilog -g2012 -s tb_hgi_hc_gathered_mix_reader_static -o "$OUT/gate.vvp" "${SOURCES[@]}" >"$OUT/compile.log" 2>&1
/usr/bin/time -v -o "$OUT/positive.time" vvp "$OUT/gate.vvp" >"$OUT/positive.log" 2>&1
grep 'HC_GATHERED_MIX PASS' "$OUT/positive.log"
set +e
/usr/bin/time -v -o "$OUT/mutant.time" vvp "$OUT/gate.vvp" +MUTANT >"$OUT/mutant.log" 2>&1
rc=$?
set -e
[[ $rc != 0 ]];grep 'FATAL:.*actual SRAM gathered_mix mismatch' "$OUT/mutant.log"
rm "$OUT/gate.vvp"
python3 - "$OUT" "${SOURCES[@]}" <<'PY'
import hashlib,json,pathlib,sys
out=pathlib.Path(sys.argv[1]);paths=sys.argv[2:]+['tools/hbm_hc_gathered_mix_reader_model.py','tools/rtl_hgi_hc_gathered_mix_reader_gate.sh']
r={'scope':'actual fixed-slot768b register landing/serializer→3LG→8SID2nativebanks/24realSRAM; component only','source_sha256':{p:hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest() for p in paths},'positive':'PASS','actual_SRAM_payload_mutant':'KILLED','shape':{'npos':[6,8,6,8],'strides':[3,3,5,5],'exact_words':672,'canonical_base_sector':18136,'SID':2,'banks':8,'actual_SRAMs':24,'neighbor_readbacks':4},'timing':{'request_sample':1,'registered_output_word0':20,'engine_capture_word0':21,'request_period':24,'words_per_cycle':1},'faults_proved':['overlap','npos0','SIDbounds','unsolicited','missingresponse_withoutstall'],'logs_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.glob('*.log')},'physical_qualified':False,'full_native_qualified':False}
(out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n')
PY
