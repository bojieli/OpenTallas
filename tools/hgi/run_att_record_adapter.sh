#!/usr/bin/env bash
set -euo pipefail
src=${1:?};out=${2:?};mkdir -p "$out"
for mode in golden ring count fields completion cancel;do
 params=()
 case "$mode" in
  ring)params=(-Ptb_hgi_att_record_adapter.MUT_RING=1);;
  count)params=(-Ptb_hgi_att_record_adapter.MUT_COUNTS=1);;
  fields)params=(-Ptb_hgi_att_record_adapter.MUT_FIELDS=1);;
  completion)params=(-Ptb_hgi_att_record_adapter.MUT_EARLY_DONE=1);;
  cancel)params=(-Ptb_hgi_att_record_adapter.MUT_CANCEL_DONE=1);;
 esac
 iverilog -g2012 -s tb_hgi_att_record_adapter "${params[@]}" -o "$out/$mode.vvp" "$src/rtl/hbm_accel/generic/g12/record/ot_hgi_att_record_adapter.sv" "$src/rtl/hbm_accel/generic/g12/ot_hgi_att_row_sources.sv" "$src/rtl/hbm_accel/generic/g12/ot_hgi_att_row_sources_p.sv" "$src/rtl/test/hgi/tb_hgi_att_record_adapter.sv" >"$out/$mode.build.log" 2>&1
 set +e;vvp "$out/$mode.vvp" >"$out/$mode.log" 2>&1;rc=$?;set -e;echo "$rc" >"$out/$mode.rc"
 if [[ "$mode" == golden ]];then test "$rc" -eq 0;grep 'PASS G12_RECORD' "$out/$mode.log";else test "$rc" -ne 0;grep 'FATAL' "$out/$mode.log";fi
done
sha256sum "$src/rtl/hbm_accel/generic/g12/record/ot_hgi_att_record_adapter.sv" "$src/rtl/hbm_accel/generic/g12/ot_hgi_att_row_sources.sv" "$src/rtl/hbm_accel/generic/g12/ot_hgi_att_row_sources_p.sv" "$src/rtl/test/hgi/tb_hgi_att_record_adapter.sv" >"$out/source.sha256"
