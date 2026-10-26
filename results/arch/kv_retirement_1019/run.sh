#!/bin/bash
set -eu
cd "$(dirname "$0")"
python3 -m unittest discover -s tools/qwen_kv_die -p test_kv_retirement.py -v > planner.log 2>&1
V=/opt/verilator-5.050/bin/verilator
if [ ! -x "$V" ]; then V=$(command -v verilator); fi
"$V" --version > verilator.version
case "$(cat verilator.version)" in *5.050*) ;; *) exit 91;; esac
S=rtl/qwen_sys/split_20261014
FILES="rtl/test/qwen_split/kv_retirement_collector.sv rtl/test/qwen_split/tb_kv_retirement.sv $S/qkd_native_attention_programme.sv $S/qkd_native_attention_static_ctl.sv $S/qkd_native59_descriptor_producer.sv $S/qkd_native59_command_guard.sv $S/qkd_native_attention_record.sv $S/qkd_astk_phys.sv rtl/qwen_sys/static_kv_die_20261017/qkd_attn_fault_root.sv"
for mut in 0 1 2; do
 "$V" --binary --timing -Wno-fatal -j 4 --top-module tb_kv_retirement -GRET_MUT=$mut --Mdir obj$mut $FILES > build$mut.log 2>&1
 if [ "$mut" = 0 ]; then
  for mode in 0 1 2 3 4; do ./obj0/Vtb_kv_retirement +MODE=$mode > mode$mode.log 2>&1; done
  mkdir -p sources
  for source in $(seq 0 355); do ./obj0/Vtb_kv_retirement +MODE=2 +SOURCE=$source > sources/source$source.log 2>&1; done
 else
  set +e
  ./obj$mut/Vtb_kv_retirement +MODE=2 > mutant$mut.log 2>&1
  rc=$?
  set -e
  [ $rc -ne 0 ]
  python3 -c "import pathlib; s=pathlib.Path('mutant$mut.log').read_text(); assert 'healthy STATUS escaped' in s or 'fault path lost' in s"
 fi
done
printf 'PASS planner, 5 causal modes, 2 mutant witnesses\n'
for bad in 0 1; do
 "$V" --binary --timing -Wno-fatal -j 4 --top-module tb_kv_retirement_reset -GBAD_RELEASE=$bad --Mdir reset$bad rtl/test/qwen_split/tb_kv_retirement_reset.sv $S/qkd_astk_phys.sv > reset_build$bad.log 2>&1
 set +e
 ./reset$bad/Vtb_kv_retirement_reset > reset$bad.log 2>&1
 rc=$?
 set -e
 if [ "$bad" = 0 ]; then [ $rc = 0 ]; else [ $rc -ne 0 ]; python3 -c "assert 'reset resurrection' in open('reset1.log').read()"; fi
done
"$V" --binary --timing -Wno-fatal -j 4 --top-module tb_kv_retirement_cal --Mdir cal rtl/test/qwen_split/tb_kv_retirement_cal.sv rtl/qwen_sys/kv_bootage_20261019/qkd_attn_cal_gen_b.sv > cal_build.log 2>&1
./cal/Vtb_kv_retirement_cal > cal.log 2>&1
"$V" --binary --timing -Wno-fatal -j 4 --top-module tb_native_attention_static_ctl --Mdir default rtl/test/qwen_split/tb_native_attention_static_ctl.sv $S/qkd_native_attention_programme.sv $S/qkd_native_attention_static_ctl.sv $S/qkd_native59_descriptor_producer.sv $S/qkd_native59_command_guard.sv $S/qkd_native_attention_record.sv > default_build.log 2>&1
for mode in $(seq 0 8); do ./default/Vtb_native_attention_static_ctl +MODE=$mode > default$mode.log 2>&1; done
printf 'PASS 356 sources, early/cutoff/late/missing, reset, 8192 calendars, 9 legacy modes\n'
