#!/usr/bin/env bash
# Smallest HOST mechanism gate: independent mux miter+mutants, real HBC RX tests,
# and complete provider elaboration. Run through ot-run against a pinned source.
set -euo pipefail
ROOT=${OT_SOURCE_ROOT:-$(git -C "$(dirname "$(readlink -f "$0")")" rev-parse --show-toplevel)}
O=$(realpath -m "${1:?fresh output dir}")
if [ -e "$O" ];then echo "refusing existing output $O" >&2;exit 2;fi
mkdir -p "$O"
cd "$ROOT"
V=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$V" --version >"$O/verilator_version.txt"
for mut in 0 1 2;do
 "$V" --binary --timing -O1 -Wno-fatal -Wno-TIMESCALEMOD --top-module tb_s81hd_host_mux -GMUT="$mut" -Mdir "$O/mux$mut" \
  rtl/dsrom_sys/s81_head/ot_s81hd_host_ep_core.sv rtl/dsrom_sys/s81_head/test/tb_s81hd_host_mux.sv --build-jobs "${J:-2}" >"$O/mux_build$mut.log" 2>&1
 set +e
 "$O/mux$mut/Vtb_s81hd_host_mux" >"$O/mux_run$mut.log" 2>&1
 rc=$?
 set -e
 if [ "$mut" = 0 ];then test "$rc" = 0;grep 'HEAD_HOST_MUX PASS' "$O/mux_run$mut.log"
 else test "$rc" != 0;grep 'miter' "$O/mux_run$mut.log";fi
done
python3 tools/s81_dv/hostctx_1021/gen_vectors.py "$O/vec" >"$O/gen.log"
python3 - "$O" <<'PY'
import sys
from pathlib import Path
out=Path(sys.argv[1]);p=Path('tools/s81_dv/hostctx_1021/tb_hostb_stage_hbc.sv')
s=p.read_text().replace('module tb_hostb_stage_hbc;', 'module tb_hostb_stage_hbc #(parameter integer RX_ONLY=0);').replace('#(.ENABLE(1),.LOCAL_STAGE','#(.ENABLE(1),.RX_ONLY(RX_ONLY),.LOCAL_STAGE')
(out/'tb_hbc.sv').write_text(s)
sys.path.insert(0,'tools/s81_head');from head_host_plan_delta import SOURCES
(out/'provider_sources.f').write_text('\n'.join(SOURCES)+'\n')
PY
H=rtl/dsrom_sys/s81_dv/hostb
for rx in 0 1;do
 "$V" --binary --timing -O1 -Wno-fatal -Wno-TIMESCALEMOD --top-module tb_hostb_stage_hbc -GRX_ONLY="$rx" -Mdir "$O/hbc$rx" \
 rtl/lib/ot_reset_sync.sv "$H"/dsdv_hostb_hold.sv "$H"/dsdv_hostb_crc512.sv "$H"/dsdv_hostb_rx.sv "$H"/dsdv_hostb_tx.sv \
 "$H"/dsdv_hostb_stage.sv "$H"/dsdv_hbc1_loader.sv "$H"/dsdv_hbc1_affine_book.sv "$H"/dsdv_hostb_stage_hbc.sv "$O/tb_hbc.sv" \
 --build-jobs "${J:-2}" >"$O/hbc_build$rx.log" 2>&1
 for mode in 0 1 2 3 4 5;do
  "$O/hbc$rx/Vtb_hostb_stage_hbc" +VEC="$O/vec" +MODE="$mode" >"$O/hbc_${rx}_${mode}.log" 2>&1
  grep 'PASS mode=' "$O/hbc_${rx}_${mode}.log"
 done
done
"$V" --lint-only -Wall -Wno-fatal --top-module ot_s81hd_host_ep_core +define+OT_COLL_NATIVE32 +define+OT_COLL_NATIVE32_OFF \
 -f "$O/provider_sources.f" >"$O/provider_lint.log" 2>&1
# Inherited safe8 and HBC primitives carry width warnings; changed HOST/HBC
# composition code must add no WIDTH or SELRANGE warning and no lint errors.
if grep -E '^%Warning-(WIDTH[A-Z]*|SELRANGE): rtl/(dsrom_sys/s81_head/ot_s81hd_host_ep_core|dsrom_sys/s81_dv/hostb/dsdv_hostb_stage_hbc)\.sv' "$O/provider_lint.log";then exit 3;fi
if grep '^%Error' "$O/provider_lint.log";then exit 4;fi
echo HOST_GATE_PASS
