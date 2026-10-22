#!/bin/bash
set -eu
out=$(realpath -m "${1:?out}");mut=${2:-0};mkdir -p "$out"
VL=${VL:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mapfile -t src < <(python3 - <<'PY'
import re,pathlib
s=pathlib.Path('tools/s81_dv/topk_control_local_1021/run_production.sh').read_text()
f=re.search(r'SRC="(.*?)"',s,re.S).group(1).split()
f.remove('tools/s81_dv/topk_control_local_1021/tb_bk_layer_n32.sv')
print('\n'.join(f+['tools/s81_dv/control_export_1021/tb_control_miter.sv']))
PY
)
sha256sum "${src[@]}" > "$out/sources.sha256"
"$VL" --version > "$out/verilator.version"
if [ "$mut" = 1 ];then
 python3 - "$out" <<'PY'
import pathlib,sys
s=pathlib.Path('rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/ot_s81pa_ctl.sv').read_text()
a='assign vd = vd_q;';b='assign vd = {o_d, o_v & rst_n, rst_n}; // missing actual output register'
assert s.count(a)==1
pathlib.Path(sys.argv[1]+'/ot_s81pa_ctl_mut.sv').write_text(s.replace(a,b))
PY
 for i in "${!src[@]}";do
  [ "${src[$i]}" != rtl/dsrom_sys/s81_dv/unit/bk/plana/n32/ot_s81pa_ctl.sv ] || src[$i]="$out/ot_s81pa_ctl_mut.sv"
 done
 sha256sum "$out/ot_s81pa_ctl_mut.sv" > "$out/mutated_source.sha256"
fi
"$VL" --binary --timing --output-split 10000 --output-split-cfuncs 1000 -j "${J:-4}" -CFLAGS -O1 \
 -DOT_S81PH_SEL_INDEXED13 -DOT_S81PH_FIFO_SRAM -DOT_SRAM_P192 -DOT_S81PH_SEL_SUCC -DOT_S81PH_SEL_FAN32 -DOT_S81PH_SEL_ACC32 -DOT_S81PH_SEL_HQ -DOT_HARD_CHILDREN -DOT_S81PH_HQ_INPUT_RAW -DOT_S81PH_SEL_ILD -DOT_S81PH_SEL_FRPR \
 -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN -Wno-UNOPTFLAT -Wno-PINMISSING -Wno-IMPLICIT -Wno-SELRANGE \
 --top-module tb_control_miter "${src[@]}" --Mdir "$out/obj" -o sim > "$out/build.log" 2>&1 || { tail -25 "$out/build.log"; echo CONTROL_BUILD_FAIL;exit 2; }
set +e
"$out/obj/sim" > "$out/run.log" 2>&1
rc=$?
set -e
cat "$out/run.log"
if [ "$rc" = 0 ] && grep -q '^CONTROL_MITER_PASS$' "$out/run.log";then exit 0;fi
if [ "$rc" != 0 ] && grep -q '^CONTROL_MISMATCH ' "$out/run.log";then echo CONTROL_CAUSAL_FAIL;exit 1;fi
echo CONTROL_UNCLASSIFIED_FAIL;exit 2
