#!/usr/bin/env bash
# hgi-1010/vm: VM.PORTS production-shape throughput bench.  usage: run_vm_ports_tput.sh <out>   (env VMMUT=n, JOBS)
# 1) trace of the DS AR 1M token's VM traffic on the S2 schedule; 2) verilator tb_hgi_vm_ports_tput; 3) ratio report.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../../../.." && pwd); O=$(realpath -m "$1"); mkdir -p "$O"; cd "$ROOT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}; T=m${VMMUT:-0}
[ -f "$O/trace/manifest.json" ] || python3 tools/hgi_vm_ports_trace.py --out "$O/trace" > "$O/trace.log"
$V --binary --timing -O2 -j ${JOBS:-8} -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-LATCH \
  -Wno-WIDTHCONCAT --top-module tb_hgi_vm_ports_tput -DVMMUT=${VMMUT:-0} "-DTRACE=\"$O/trace\"" "+incdir+$O/trace" --Mdir "$O/obj_$T" \
  rtl/hbm_accel/generic/vm/ot_hgi_vm_core.sv rtl/hbm_accel/generic/vm/ot_hgi_vm_unit.sv \
  physical/asap7_memory_macros/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v \
  rtl/hbm_accel/generic/vm/tb_hgi_vm_ports_tput.sv > "$O/build_$T.log" 2>&1 || { tail -20 "$O/build_$T.log"; exit 2; }
"$O/obj_$T/Vtb_hgi_vm_ports_tput" > "$O/run_$T.log" 2>&1 || true
tail -4 "$O/run_$T.log"
python3 tools/hgi_vm_ports_trace.py --report "$O/trace" "$O/run_$T.log" --json "$O/report_$T.json" | python3 -c "import json,sys; r=json.load(sys.stdin); print('VM.PORTS ratio', r['ratio'], r.get('verdict'))"
grep -q '^HGI_VM_PORTS PASS' "$O/run_$T.log"
