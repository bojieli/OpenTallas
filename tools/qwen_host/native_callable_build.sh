#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
out=${1:?output directory};io=${2:?immutable IO0d401fc0b tree};top=${3:-qkd_host_control_packet_capture_token_service}
mkdir -p "$out";out=$(cd "$out"&&pwd)
case "$top" in
 qkd_host_control_packet_capture_token_service) params=(-GENABLE_SERVICE=1 -GENABLE_TOKEN=1);;
 qkd_host_token_service) params=(-GENABLE_SERVICE=1 -GENABLE_TOKEN=1 -GENABLE_NATIVE=1);;
 qkd_host_native_token_endpoint) params=(-GENABLE_NATIVE=1);;
 qkd_host_service_guard|qkd_host_board_port_fixture) params=();;
 *) echo "unsupported HOST callable top: $top" >&2;exit 2;;
esac
python3 - "$io" <<'PYSOURCE'
import hashlib,json,pathlib,sys
j=json.loads(pathlib.Path('physical/qkd_host_integration/native_callable_manifest.json').read_text())
for prefix,group in [(pathlib.Path('.'),'sources'),(pathlib.Path(sys.argv[1]),'io_sources')]:
 for name,want in j[group].items():
  path=prefix/name
  if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=want:
   raise SystemExit('HOST callable source hash mismatch: '+str(path))
print('PASS HOST_CALLABLE_SOURCE_HASHES')
PYSOURCE
vlt=${VERILATOR:-verilator}
"$vlt" --cc --build -O1 --output-split 10000 --output-split-cfuncs 100 -CFLAGS -O0 -j "${HOST_BUILD_JOBS:-8}" --top-module "$top" --Mdir "$out/obj" -Wno-fatal "${params[@]}" \
 rtl/test/qwen_host/qkd_host_board_port_fixture.sv rtl/qwen_sys/host_20261013/*.sv rtl/physical/ot_qkd_host_prompt_capture_pins.sv rtl/physical/ot_qfd_prompt_sram_capture.sv rtl/physical/ot_qwen_host_ctl.sv rtl/physical/ot_qwen_die_cdc_ch.sv rtl/physical/ot_qwen_async_fifo_w.sv \
 rtl/qwen_sys/system_20261008/ot_host_if_pb2.sv rtl/qwen_sys/system_20261008/ot_qfd_prompt_sram.sv rtl/qwen_sys/system_20261008/ot_qfd_pkgctl.sv rtl/qwen_sys/ot_qwen_sys_rst_seq.sv rtl/lib/ot_reset_sync.sv rtl/lib/ot_async_fifo.sv rtl/link/ot_link_afifo.sv rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv \
 "$io/rtl/physical/ot_qfd_link_adp512_split.sv" "$io/rtl/qwen_sys/missing_masters_20261007/ot_qfd_link_adapter.sv" "$io/rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv" \
 "$io/physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v" \
 physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
 physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v > "$out/build.log" 2>&1 || { tail -n 100 "$out/build.log";exit 1; }
python3 - "$out" "$top" <<'PYMAN'
import hashlib,json,pathlib,sys
out=pathlib.Path(sys.argv[1]);top=sys.argv[2]
files=[out/'obj'/('V'+top+'.h'),out/'obj'/('V'+top+'__ALL.a')]
manifest={'top':top,'kind':'callable Verilator component, functional only','artifacts':[]}
for p in files:
 if not p.is_file():raise SystemExit('missing callable artifact '+str(p))
 manifest['artifacts'].append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(out/'callable.json').write_text(json.dumps(manifest,indent=2)+'\n')
PYMAN
printf 'PASS HOST_CALLABLE top=%s manifest=%s/callable.json\n' "$top" "$out"
