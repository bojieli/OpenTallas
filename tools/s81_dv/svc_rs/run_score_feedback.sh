#!/usr/bin/env bash
set -euo pipefail
O=$(realpath -m "${1:?outdir}")
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
D=rtl/dsrom_sys/s81_dv/svc_rs
mkdir -p "$O"
python3 - "$O" <<'PY'
import re,json,pathlib,hashlib,sys
src=pathlib.Path('results/svc_attcut_1113/native_programme');out=pathlib.Path(sys.argv[1])
assert json.loads((src/'oracle.json').read_text())['status']=='PASS'
lines=[];dates=[]
for s in (src/'run.log').read_text().splitlines():
 m=re.fullmatch(r'SCORE case0 relative(\d+) row(\d+) payload([a-f0-9]+) flags([a-f0-9]+)',s)
 if m:
  cy,row,data,flags=m.groups();word=(int(row)<<1060)|(15<<1056)|(int(data,16)<<32)|int(flags,16)
  lines.append(f'{word:0269x}');dates.append(int(cy))
assert len(lines)==8 and dates==list(range(77,85))
(out/'score.hex').write_text('\n'.join(lines)+'\n');(out/'dates.hex').write_text('\n'.join(f'{d:08x}' for d in dates)+'\n')
(out/'source_trace.json').write_text(json.dumps({'source_commit':'4b3430fb52','native_scope':'actual outer/native H8 band2m1PAIR5 selectedcalendar programme, fixedT32','source_go_phase':1,'score_relative_cycles':dates,'source_trace_sha256':hashlib.sha256((src/'run.log').read_bytes()).hexdigest(),'replay_virtual_go':128,'p_source_test_pio':800,'active_sm_head':0,'active_sid':10,'active_tile':0,'global_pio_adoption':False},indent=2)+'\n')
PY
SX=(rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/dsrom_sys/s81_glue/ot_s81_rly.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv)
COMMON=(-DOT_SVC_H8 -DOT_SVC_NATIVE_RT2_CALENDAR -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -I"$D" --output-split 20000 --output-split-cfuncs 2000 -fno-inline --unroll-count 16 --unroll-limit 131072 -MAKEFLAGS OPT_SLOW=-O0 -CFLAGS -O0)
if [[ ! -f $O/pl/libdsdv_svc_sx_pl.a ]];then
 "$VL" --cc --build -j 4 --protect-lib dsdv_svc_sx_pl --top-module dsdv_svc_sx -GH=8 -Mdir "$O/pl" "${COMMON[@]}" "${SX[@]}" "$D/dsdv_svc_sx_hrow.sv" "$D/dsdv_svc_sx.sv" >"$O/build_lib.log" 2>&1
fi
source tools/s81_dv/svc_rs/rs_files.sh
"$VL" --binary --timing --top-module tb_svc_score_feedback -Mdir "$O/obj" -j 4 "${COMMON[@]}" -DSU_SMU_T "${RS_SRC[@]}" "${RS_LIB[@]}" "$O/pl/dsdv_svc_sx_pl.sv" "$O/pl/libdsdv_svc_sx_pl.a" "$D/dsdv_svc_mem_ar.sv" physical/asap7_memory_macros_v2/ot_sram_1r1w_160x256_m1_r0c0/ot_sram_1r1w_160x256_m1_r0c0.v physical/asap7_memory_macros_v2/ot_sram_1r1w_32x128_m1_r0c0/ot_sram_1r1w_32x128_m1_r0c0.v "$D/test/tb_svc_score_feedback.sv" >"$O/build_top.log" 2>&1
for drop in 0 1;do
 "$O/obj/Vtb_svc_score_feedback" +scores="$O/score.hex" +dates="$O/dates.hex" +drop=$drop >"$O/run_drop$drop.log" 2>&1
 grep -E '^FEEDBACK_|^SCORE_FEEDBACK' "$O/run_drop$drop.log"
 if [[ $drop == 0 ]];then grep -q '^SCORE_FEEDBACK PASS' "$O/run_drop$drop.log";else grep -q '^SCORE_FEEDBACK NEGATIVE_CAUGHT' "$O/run_drop$drop.log";fi
done
