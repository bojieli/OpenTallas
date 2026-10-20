#!/bin/bash
# L2H-PAD fleet run: Verilator 5.050 72-shape golden bench, ASSERT_MUTANT=1..4 witnesses, Yosys 0.68 synth + all-Q audit.
# usage: run_pad_l2h.sh <dir holding hbfd_pad.sv tb.sv delay.sv macro.sv macro_bb.v audit.py> [bench|mutants|synth|all]
set -u
D=$1; MODE=${2:-all}; cd "$D" || exit 2
for _d in "$HOME/.local/opentallas-tools/verilator-5.050/bin" "$HOME/.local/opentallas-tools/yosys-0.68/bin"; do [ -d "$_d" ] && PATH="$_d:$PATH"; done
export PATH
rc=0
if [ "$MODE" = all ] || [ "$MODE" = bench ] || [ "$MODE" = mutants ]; then
  verilator --version
  verilator --binary --timing -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -j 8 --top-module tb_hbfd_pad_storage \
    tb.sv hbfd_pad.sv delay.sv macro.sv -o vpad > build.log 2>&1 || { echo BUILD_FAIL; tail -30 build.log; exit 3; }
fi
if [ "$MODE" = all ] || [ "$MODE" = bench ]; then
  ./obj_dir/vpad > bench.log 2>&1; b=$?; cat bench.log; echo "BENCH_RC=$b"; [ $b -ne 0 ] && rc=1
  grep -q PAD_STORAGE_PASS bench.log || rc=1
fi
if [ "$MODE" = all ] || [ "$MODE" = mutants ]; then
  for m in 1 2 3 4; do
    ./obj_dir/vpad +ASSERT_MUTANT=$m ${PAD_ASSERT_SHAPE:-} > w_mutant$m.log 2>&1; r=$?
    echo "MUTANT $m rc=$r $(grep -o 'PAD_MUTANT_WITNESS[^\r]*' w_mutant$m.log | head -1)"
    { [ $r -ne 0 ] && grep -q "PAD_MUTANT_WITNESS mutant=$m" w_mutant$m.log; } || { echo "MUTANT $m NOT WITNESSED"; rc=1; }
  done
fi
if [ "$MODE" = all ] || [ "$MODE" = synth ]; then
  for s in 17_115 1_3 34_73 274_14 136_28 17_4 274_3 1_115; do
    W=${s%_*}; N=${s#*_}
    if [ $s = 17_115 ]; then TOP=hbfd_pad_r17x115; WR=""; else TOP=pad_top_$s; WR=wrap_$s.sv
      printf 'module %s(input wire ck, rs, input wire [%d:0] i, output wire [%d:0] o);\n hbfd_pad #(.W(%d),.N(%d),.SAFE_STORAGE(1)) u_pad(.ck(ck),.rs(rs),.i(i),.o(o));\nendmodule\n' $TOP $((W-1)) $((W-1)) $W $N > $WR; fi
    yosys -q -l synth_$s.log -p "read_verilog -sv -lib macro_bb.v; read_verilog -sv -DSYNTHESIS hbfd_pad.sv delay.sv $WR; hierarchy -top $TOP; synth -flatten -top $TOP; write_json synth_$s.json; stat" \
      && echo "SYNTH_COMPLETE W=$W N=$N top=$TOP" || { echo "SYNTH_FAIL $s"; rc=1; }
  done
  python3 audit.py . > audit.json && python3 -c "
import json;d=json.load(open('audit.json'))
bad=0
for k,v in d['shapes'].items():
  print('AUDIT',k,'ff_q',v['ff_outputs'],'kept_cells',v['kept_cells'],'macros',v['macro_counts'],'max_q_loads',v['max_q_loads'],'over32',v['over32_count'],'max_pi_loads',v['max_input_port_loads'])
  bad+=v['over32_count']
print('AUDIT_RESULT', 'PASS' if bad==0 else 'FAIL', 'over32_total', bad)
" || rc=1
  grep -q "AUDIT_RESULT PASS" <(python3 -c "
import json;d=json.load(open('audit.json'));print('AUDIT_RESULT PASS' if all(v['over32_count']==0 for v in d['shapes'].values()) else 'X')") || rc=1
fi
echo "RUN_PAD_L2H rc=$rc"; exit $rc
