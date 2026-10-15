#!/usr/bin/env bash
# Prepare by default. Build/run only under ot-run after the previous full-SU
# job is terminal and its logs/cache collected. Never mutate its frozen tree.
set -euo pipefail
ulimit -c 0
cd "$(dirname "$0")/../.."
out=$(realpath -m "$1"); mode=${2:-prepare}
mkdir -p "$out"
mlat=${SU_TOP_MLAT:-4};alat=${SU_TOP_ALAT:-3};leaf=${SU_TOP_LEAF:-1};relay=${SU_TOP_RF_RELAY:-8}
[ -f "$out/vec/prog.mem" ] || python3 tools/hbm_static/su_top_compile.py "$out/vec" --rf-relay "$relay" --mlat "$mlat" --alat "$alat" --leaf "$leaf" > "$out/vec.log"
python3 tools/hbm_static/su_multirate_compile.py "$out/vec/prog.mem" "$out/vec/phase" --expected-writes "$out/vec/expw.mem" > "$out/phase.log"
python3 tools/hbm_static/su_programme_compile.py "$out/vec/phase/serial_prog.mem" "$out/vec/serial" --param-prefix SERIAL > "$out/serial.log"
python3 tools/hbm_static/su_programme_compile.py "$out/vec/phase/stream_cal.mem" "$out/vec/stream" --line-bits 64 --param-prefix STREAM > "$out/stream.log"
read -r NE NW NS PE < <(python3 - "$out/vec" <<'PY'
import json,sys
from pathlib import Path
v=Path(sys.argv[1]);s=json.loads((v/'programme.json').read_text());p=json.loads((v/'phase/manifest.json').read_text())
assert s['edges']==p['serial_edges'];assert s['expected_vm_writes']==p['write_slots']
print(s['edges'],s['expected_vm_writes'],s['expected_scalars'],p['stream_edges'])
PY
)
if [ "$mode" = prepare ]; then echo "SU_MULTIRATE_PREPARED serial=$NE stream=$PE";exit 0;fi
if [ "$mode" != build ] && [ "$mode" != run ];then echo 'mode must be prepare, build or run' >&2;exit 2;fi
S=rtl/hbm_accel/generic/adapters/static_su
sources=(
 "$S/arithmetic/ot_hbm_su_static_ins.sv" "$S/arithmetic/ot_hbm_su_static_lane.sv" "$S/arithmetic/ot_hbm_su_static_side.sv"
 "$S/data_store/ot_hbm_su_static_data_store.sv" "$S/data_store/ot_hbm_su_static_pinned_bank.sv"
 "$S/register_file/ot_hbm_su_static_rf.sv" "$S/reduction/ot_hbm_su_reduce_static.sv" "$S/ot_hbm_su_static_vm_ports.sv"
 "$S/top/ot_hbm_su_static_pgslice.sv" "$S/top/ot_hbm_su_static_qcore.sv" "$S/top/ot_hbm_su_static_quarter.sv" "$S/top/ot_hbm_su_static_top.sv"
 "$S/native_vm/ot_hbm_su_native_vm.sv" "$S/programme/ot_hbm_su_programme.sv" "$S/programme/multirate_bridge.sv" "$S/programme/tb_hbm_su_native_multirate_top.sv"
 rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_split.sv rtl/hbm_accel/generic/vm/static/ot_hbm_vm_lg_static_bank.sv rtl/hbm_accel/generic/vm/static/ot_vms_bank_static.sv
 rtl/hbm_accel/generic/peers/ot_hgi_su_unit.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv
 rtl/proto/ot_fp32_add_rne_pipe.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fastfp_lat.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv
 rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_softplus.sv
 physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v
)
# Reject an absent integration instead of silently elaborating the old top.
python3 - <<'PY'
from pathlib import Path
p=Path('rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_top.sv').read_text()
assert 'MULTIRATE' in p and 'bridge_rst_n' in p, 'multirate top integration is absent'
PY
sha256sum "${sources[@]}" tools/hbm_static/su_programme_compile.py tools/hbm_static/su_multirate_compile.py "$0" > "$out/sources.new.sha256"
printf '%s\n' "NE=$NE PE=$PE NW=$NW NS=$NS MLAT=$mlat ALAT=$alat LEAF=$leaf RELAY=$relay" >> "$out/sources.new.sha256"
if [ -x "$out/obj/Vtb_hbm_su_native_multirate_top" ] && ! cmp -s "$out/sources.sha256" "$out/sources.new.sha256"; then
 echo 'Cached binary source/configuration mismatch; use a fresh output directory.' >&2;exit 1
fi
mv "$out/sources.new.sha256" "$out/sources.sha256"
vl=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
obj="$out/obj"
if [ ! -x "$obj/Vtb_hbm_su_native_multirate_top" ]; then
 "$vl" --binary --timing --hierarchical -O1 -j "${SU_TOP_JOBS:-4}" -CFLAGS -O0 -Wno-fatal -Wno-lint -Wno-style \
 --top-module tb_hbm_su_native_multirate_top -I"$out/vec" -GNE="$NE" -GPE="$PE" -GNW="$NW" -GNS="$NS" \
 -GRF_RELAY="$relay" -GMLAT="$mlat" -GALAT="$alat" -GLEAF="$leaf" --Mdir "$obj" "${sources[@]}" > "$out/build.log" 2>&1
fi
if [ "$mode" = build ];then echo SU_MULTIRATE_BUILD_COMPLETE;exit 0;fi
bin="$obj/Vtb_hbm_su_native_multirate_top"
"$bin" +DIR="$out/vec" > "$out/positive.log" 2>&1
grep -q 'SU_NATIVE_MULTIRATE_TOP PASS' "$out/positive.log"
python3 - "$out/positive.log" "$out/endpoints.json" <<'PY'
import json,sys
from pathlib import Path
line=next(x for x in Path(sys.argv[1]).read_text().splitlines() if x.startswith('SU_NATIVE_MULTIRATE_ENDPOINTS '))
d=json.loads(line.split(' ',1)[1]);d['max_observed_completion_tick']=max(3*d['last_lg_ack_stream'],3*d['last_read_return_stream'],4*d['last_bridge_read_serial'],4*d['last_bridge_ack_serial'],4*d['last_lane_write_serial'],4*d['last_scalar_serial'])
d['quantum_ps']='2500/9';d['physical_clock_epoch_qualified']=False;d['throughput_qualified']=False
Path(sys.argv[2]).write_text(json.dumps(d,indent=2)+'\n')
PY
for mut in DATA ADDR RF RED CAL EPOCH;do
 set +e
 "$bin" +DIR="$out/vec" +MUT_$mut > "$out/mut_$mut.log" 2>&1
 rc=$?
 set -e
 if [ "$rc" = 0 ] || ! grep -q 'SU_NATIVE_MULTIRATE_TOP FAIL' "$out/mut_$mut.log";then exit 1;fi
done
echo SU_NATIVE_MULTIRATE_TOP_GATE_PASS
