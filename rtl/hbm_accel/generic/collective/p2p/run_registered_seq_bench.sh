#!/usr/bin/env bash
# Invoke through ot-run. All output and failed evidence retained in OUT.
set -euo pipefail
root=${HCOLL_ROOT:-$(cd "$(dirname "$0")/../../../../.." && pwd)}
out=$(realpath -m "$1");mkdir -p "$out";cd "$root"
p=rtl/hbm_accel/generic/collective/p2p
native=(rtl/qwen_sys/split_20261014/ot_qwen_crc_parallel.sv rtl/qwen_sys/split_20261014/ot_qkvd_d2d_llr.sv
 physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v)
src=("${native[@]}" "$p/ot_hgi_coll_static_seq_ctl.sv" "$p/ot_hgi_coll_static_link_seq.sv")
for mutant in 0 1 2 3 4 5 6 7 8 9 10 11;do
 iverilog -g2012 -s tb_hgi_coll_static_link_seq -Ptb_hgi_coll_static_link_seq.MUT="$mutant" -o "$out/sim$mutant" \
  "${src[@]}" "$p/tb_hgi_coll_static_link_seq.sv" > "$out/build$mutant.log" 2>&1
 vvp "$out/sim$mutant" > "$out/m$mutant.log" 2>&1
 cat "$out/m$mutant.log"
 if grep -Eq 'FATAL|ERROR' "$out/m$mutant.log";then exit 1;fi
 if [[ "$mutant" == 0 ]];then
  grep -q 'HBM_STATIC_LINK_SEQ_PASS FW545 CW32 checks2048 TX3 RX1 PHY96 wire612 sameepoch' "$out/m$mutant.log"
 elif [[ "$mutant" == 3 ]];then
  grep -Eq 'HBM_STATIC_LINK_SEQ_FAIL.*errors[1-9]' "$out/m$mutant.log"
 else
  grep -Eq 'HBM_STATIC_LINK_SEQ_FAIL.*abort_cycles[1-9]' "$out/m$mutant.log"
 fi
done
iverilog -g2012 -s tb_hgi_coll_static_link_seq_overflow -o "$out/overflow" "${src[@]}" "$p/tb_hgi_coll_static_link_seq_overflow.sv" > "$out/overflow-build.log" 2>&1
vvp "$out/overflow" > "$out/overflow.log" 2>&1
cat "$out/overflow.log"
grep -q '^HBM_STATIC_LINK_SEQ_OVERFLOW_PASS ' "$out/overflow.log"
# Physical macro is an opaque native cell for mapping. Extract its exact port
# declaration, not its functional array internals; simulation above uses full
# actual catalog functional model. The controller and CRC are REAL RTL here.
python3 - "$out/macro_ports.v" <<'PY'
import pathlib,sys
p=pathlib.Path('physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.v')
s=p.read_text();s=s[s.index('module '):];s=s[:s.index(');')+2]
pathlib.Path(sys.argv[1]).write_text('(* blackbox *) '+s+'\nendmodule\n')
PY
yosys -Q -T -p "read_verilog -lib -sv $out/macro_ports.v; read_verilog -sv ${native[0]} ${native[1]} $p/ot_hgi_coll_static_seq_ctl.sv $p/ot_hgi_coll_static_link_seq.sv; synth -top ot_hgi_coll_static_link_seq -flatten; write_json $out/mapped.json" > "$out/synth.log" 2>&1
python3 tools/hbm_coll_static/check_registered_seq.py "$out/mapped.json" "$out/registered_outputs.json"
echo 'REGISTERED_SEQ_SUITE PASS'
