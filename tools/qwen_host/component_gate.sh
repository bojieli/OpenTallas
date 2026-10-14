#!/usr/bin/env bash
# Run only through ot-run. Builds intentionally small component benches.
set -euo pipefail
cd "$(dirname "$0")/../.."
out=${1:?output dir};mkdir -p "$out";out=$(cd "$out"&&pwd)
export TMPDIR="$out"
for component in axi_packet ctrl_packet static_pc ingest_map ingest_station visibility_fence;do
 src="rtl/qwen_sys/host_20261013/qkd_host_${component}.sv"
 tb="rtl/test/qwen_host/tb_qkd_host_${component}.sv"
 deps=()
 if [[ "$component" == static_pc ]];then deps=(rtl/lib/ot_async_fifo.sv rtl/lib/ot_reset_sync.sv);fi
 iverilog -g2012 -s "tb_qkd_host_${component}" -o "$out/${component}-pos" "$src" "$tb" "${deps[@]}"
 vvp "$out/${component}-pos" | tee "$out/${component}-pos.log"
 iverilog -g2012 -s "tb_qkd_host_${component}" -P"tb_qkd_host_${component}.MUT=1" -o "$out/${component}-mut" "$src" "$tb" "${deps[@]}"
 if vvp "$out/${component}-mut" > "$out/${component}-mut.log" 2>&1;then echo "FAIL undetected $component mutant";exit 1;fi
 cat "$out/${component}-mut.log"
done
