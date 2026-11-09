#!/bin/bash
# QC-TYPES-11: final START event: strict bind at the staged wave path, bench + structural census, G0C vs v4n, advisory dry kit-rtl..gen.
set -u
W=/srv/opentallas-scratch2/claude/qct11/wave; S=$W/src; Q=/srv/opentallas-scratch3/claude/qct11/start; R=/srv/opentallas-scratch3/claude/codex-qc-compose-1113
P=$W/plan/plan_qc53v4nS.json; B=$W/bind_v4nS; L=$W/bind_logs; A=$S/physical/die_plan/qwen_compute/qc_start_1106/runtime/asbuilt_hc3.json
mkdir -p $L $B; cd $S
python3 -I -B -c "import sys,runpy;sys.path.insert(0,'$S/tools/die_plan');sys.argv=['schema.py','validate','$P'];runpy.run_path('$S/tools/die_plan/schema.py',run_name='__main__')" > $L/validate.log 2>&1; echo "VALIDATE rc $?"
python3 -I -B tools/die_plan/bind.py elab $P --out $B --asbuilt $A > $L/elab.log 2>&1; echo "ELAB rc $?"
python3 -I -B tools/die_plan/bind.py bind $P --out $B --strict --all-gaps --asbuilt $A > $L/bind.log 2>&1; echo "BIND rc $?"
python3 -I -c "import json;r=json.load(open('$B/bind_report.json'));print('n_errors',r['n_errors'])"
python3 -I /tmp/qct11_st2.py 2>&1 | cut -c1-900
cd $Q; rm -rf bench_out; python3 -B bench_start.py $B/rtl bench_out > bench.log 2>&1; echo "BENCH rc $?"; tail -14 bench.log | cut -c1-180
cd $S; mkdir -p $Q/dry
python3 -B tools/die_plan/check.py $P --completeness --out $Q/dry/g0c_S > $Q/dry/check_S.txt 2>&1; echo "G0C_S rc $?"; grep -E "^G0C FAIL|^G0C PASS" $Q/dry/check_S.txt | cut -c1-200
SC=$S/physical/die_plan/qwen_compute/qc_start_1106/runtime/sidecar.json
for T in "$@"; do
  D=$W/dry/$T; mkdir -p $D/logs
  python3 -B tools/die_plan/bind.py kit-rtl $P --out $B --asbuilt $A --type $T --kit $D/rtl > $D/logs/kit_rtl.log 2>&1; echo "$T KIT_RTL rc $?"
  python3 -B tools/die_plan/gen.py phys $P --out $D/gen --types $T --rtl-root $S --kit-rtl $T=$D/rtl/kit_rtl.f --hold-ff-margin 0 --max-wire-um 120 --clock-landing $SC > $D/logs/gen.log 2>&1; echo "$T GEN rc $?"
  ls $D/gen/$T/config.mk 2>&1; tail -2 $D/logs/gen.log | cut -c1-220
done
echo CHAIN_END
