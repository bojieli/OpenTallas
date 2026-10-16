#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../../../.."
out=$(realpath -m "${1:-/tmp/wb-kshare-drain}")
mkdir -p "$out"
n=rtl/hbm_accel/loader/service_native
src=("$n/tb_hbm_svc_wb_kshare_drain.sv" "$n/ot_hbm_svc_async_fifo.sv" "$n/ot_hbm_svc_pc_ctrl_leaf.sv" rtl/lib/ot_reset_sync.sv)
sha256sum "${src[@]}" "$n/ot_hbm_svc_vm_kshare.sv" > "$out/source.sha256"
iverilog -g2012 -s tb_hbm_svc_wb_kshare_drain -o "$out/sim" "${src[@]}" "$n/ot_hbm_svc_vm_kshare.sv"
vvp "$out/sim" > "$out/baseline.log"
grep -q '^PASS tb_hbm_svc_wb_kshare_drain' "$out/baseline.log"
# Restore the historical four-bit outstanding counter: the 32 queued writes wrap to zero.
python3 - "$n/ot_hbm_svc_vm_kshare.sv" "$out/counter_mutant.sv" <<'PY'
import pathlib,sys
s=pathlib.Path(sys.argv[1]).read_text()
assert s.count('reg[5:0]g_wr_out')==1
pathlib.Path(sys.argv[2]).write_text(s.replace('reg[5:0]g_wr_out','reg[3:0]g_wr_out'))
PY
iverilog -g2012 -s tb_hbm_svc_wb_kshare_drain -o "$out/mutant" "${src[@]}" "$out/counter_mutant.sv"
rc=0
vvp "$out/mutant" > "$out/mutant.log" 2>&1 || rc=$?
test "$rc" != 0 && grep -q 'PREMATURE_WB accepted=32 returned=0' "$out/mutant.log"
echo 'PASS WB drain: 32 group writes completed before WB; historical four-bit counter mutant rejected'
rm "$out/sim" "$out/mutant" "$out/counter_mutant.sv"
