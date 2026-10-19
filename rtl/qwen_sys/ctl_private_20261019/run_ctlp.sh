#!/usr/bin/env bash
# Fleet only. Run from an immutable checkout containing the private source pair.
# Dependencies: git, python3, Icarus (four-state); optional Verilator exactly 5.050.
set -euo pipefail
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
repo=$(git -C "$here" rev-parse --show-toplevel)
out=${CTLP_OUT:-"$PWD/ctlp-results"}
engine=${CTLP_ENGINE:-iverilog}
mkdir -p "$out"
out=$(cd "$out" && pwd)
# Pin original references and primitive, never a handwritten macro substitute.
git -C "$repo" show c5fbbded9:rtl/qwen_sys/static_kv_20261014/qkd_kv_native_programme.sv > "$out/writer_original.sv"
git -C "$repo" show c5fbbded9:rtl/qwen_sys/mu_qwen_20261018/qkd_static_kv_layer_programme_mus.sv > "$out/programme_original.sv"
git -C "$repo" show c5fbbded9:physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v > "$out/sram_original.v"
sha256sum "$out/"*original* "$here/qkd_kv_native_programme_ctlp.sv" "$here/qkd_static_kv_layer_programme_ctlp.sv" "$here/tb_ctlp.sv" > "$out/sources.sha256"
if [[ $engine == verilator ]]; then
 verilator --version | tee "$out/tool.txt"
 verilator --version | grep -q 'Verilator 5.050' || { echo 'Requires Verilator 5.050'; exit 2; }
else
 iverilog -V > "$out/tool.txt" 2>&1
fi
for mode in base late_read wrong_row mask_word invalid_start; do
 cp "$here/qkd_kv_native_programme_ctlp.sv" "$out/writer_$mode.sv"
 python3 - "$out/writer_$mode.sv" "$mode" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=p.read_text();mode=sys.argv[2]
changes={
 'late_read':('ENABLE!=0?ctlp_accept_start:start_p','ENABLE!=0?ld:start_p'),
 'wrong_row':(".r_addr_in({1'b0,selected_stage-6'd1})",".r_addr_in({1'b0,selected_stage-(ENABLE!=0?6'd0:6'd1)})"),
 'mask_word':('{32{wq_word[0]}}','{32{wq_word[0]&&(ENABLE==0)}}'),
 'invalid_start':('if(!configured||active||fault||cfg_we_p||stage_p<1||stage_p>36)fault<=1;', 'if((!configured&&ENABLE==0)||active||fault||cfg_we_p||stage_p<1||stage_p>36)fault<=1;')}
if mode in changes:
 a,b=changes[mode]
 assert s.count(a)==1,(mode,s.count(a))
 s=s.replace(a,b)
p.write_text(s)
PY
 variants=1
 [[ $mode == base ]] && variants='0 1'
 for ws in $variants; do
  stem="$out/${mode}_sram${ws}"
  sources=("$out/sram_original.v" "$out/writer_original.sv" "$out/programme_original.sv" "$out/writer_$mode.sv" "$here/qkd_static_kv_layer_programme_ctlp.sv" "$here/tb_ctlp.sv")
  if [[ $engine == verilator ]]; then
   verilator --binary --timing --top-module tb_ctlp -Wno-fatal -DOT_MEM_NO_INIT -GWS="$ws" --Mdir "${stem}_obj" -j "${CTLP_JOBS:-2}" "${sources[@]}" > "${stem}.compile.log" 2>&1
   command=("${stem}_obj/Vtb_ctlp")
  else
   iverilog -g2012 -DOT_MEM_NO_INIT -s tb_ctlp -Ptb_ctlp.WS="$ws" -o "${stem}.vvp" "${sources[@]}" > "${stem}.compile.log" 2>&1
   command=(vvp "${stem}.vvp")
  fi
  set +e
  "${command[@]}" > "${stem}.log" 2>&1
  rc=$?
  set -e
  printf '%s\n' "$rc" > "${stem}.rc"
  if [[ $mode == base ]]; then
   [[ $rc == 0 ]] && grep -q 'CTLP_PASS' "${stem}.log" || { cat "${stem}.log"; exit 1; }
  else
   [[ $rc != 0 ]] && grep -q 'CTLP_MISMATCH family=w enable=1' "${stem}.log" || { cat "${stem}.log"; echo "MUTANT_NOT_CAUGHT $mode"; exit 1; }
  fi
 done
done
printf 'CTLP_SUITE_PASS engine=%s original=c5fbbded9\n' "$engine" | tee "$out/verdict.txt"
