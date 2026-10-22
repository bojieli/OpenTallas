#!/bin/bash
# S81-WQBP 10-20: attn.wq_b P126 row-batch pipeline -- compiler emission + consumer retirement / deadline bench.
#  1. EMIT: the vehicle programme from the die compiler of this branch (main-based tools/s81_dv overlaid on the TOK2 sid6
#     root): qnorm_program_model -> retained_xs_program (calendar = xs_wqb_die.wqb_calendar default pipeline P126/52, static
#     checks); image SHA equality with the simulated P126 + 15-CAP-descriptor run (codex-cap-contract-1020/source_compiled,
#     same exe 63eccd91 Verilator 5.050) => that RTL run executed exactly this compiler emission.
#  2. DIE: xs_wqb_die.py die (L0 L2 L14 L20, 8 frames / 11 phases per slice, + idx.q on sparse layers), pipeline + serial,
#     and the P124 refusal; dv_layer_compile.py --fixtures L0 (lower_placed emits prog/xs/<id>.calendar.json + ROM images).
#  3. CONSUMER: check_wqbp_consumer.py on the real RTL traces (R1 element per-tag retire, R2 CAP per-domain retire,
#     R3 consumer read of all 512 golden dims at the compiled deadline + retention, R4 static == runtime); nominal L0/L2/L14
#     must PASS; deadline mutants, wrong row base, late CFG, P124 calendar must FAIL.
set -u
D=/srv/opentallas-scratch/claude/s81-wqbp; R=$D/root; B=/srv/opentallas-scratch/claude/toksim-s81d-wqbp
CX=/srv/opentallas-scratch/claude/codex-cap-contract-1020; Q=$R/tools/s81_dv/layer_prog; O=$D/out; G=$B/wqbp_golden_check.py
[ -e $O ] && { echo REFUSE_EXISTING_OUT; exit 2; }; mkdir -p $O/emit $O/consumer
echo "HOST $(hostname) python $(python3 --version 2>&1)"
cd $R
# ---------------------------------------------------------------- 1 EMIT
python3 $Q/qf_producer/qnorm_program_model.py --fixture $R/sid6_fixture --out $O/emit/qn > $O/emit/qn.log 2>&1 || { echo QN_FAIL; tail -5 $O/emit/qn.log; }
python3 $Q/qf_producer/retained_xs_program.py --fixture $R/sid6_fixture --contract retained_sid6_fixture_contract.json \
  --raw-program $O/emit/qn/program.json --out $O/emit/model --placements s_16_24.json \
  --shifts '{"L01":0,"L02":0,"L03":0,"R01":16,"R02":24,"R03":24}' > $O/emit/gen.log 2>&1 || { echo GEN_FAIL; tail -8 $O/emit/gen.log; }
tail -1 $O/emit/gen.log
python3 -c "import json;c=json.load(open('$O/emit/model/contract.json'))['compiler_calendar'];json.dump(c,open('$O/emit/compiler_calendar.json','w'),indent=1);print('EMIT_CALENDAR',c['mode'],c['period'],c['cfg_lead'],c['nphases'],'static',c['static']['PASS'],'span',c['predicted_span'])"
neq=0
for f in pq_calendar_action pq_calendar_time pq_phase0 pq_stream0 pq_stream1 pq_stream2 pq_stream3; do
  for r in source_compiled capture_l2 capture_l14 wrong_rbase late_cfg; do
    cmp -s $O/emit/model/$f.viamap.hex $CX/$r/images/$f.viamap.hex && echo "EMIT_SAME_AS_RUN $r $f" || { echo "EMIT_DIFF_FROM_RUN $r $f"; neq=$((neq+1)); }
  done
done
(cd $O/emit/model && sha256sum *.viamap.hex) > $O/emit/images.sha256
echo "EMIT_IMAGE_MISMATCHES $neq"
# ---------------------------------------------------------------- 2 DIE
python3 $Q/xs_wqb_die.py die --fixtures-root $B/fixtures --contract $R/retained_sid6_fixture_contract.json --out $O/die_p126 > $O/die_p126.log 2>&1; echo "DIE_P126 rc=$?"; grep XS_WQB_DIE $O/die_p126.log
python3 $Q/xs_wqb_die.py die --fixtures-root $B/fixtures --contract $R/retained_sid6_fixture_contract.json --out $O/die_serial --calendar serial > $O/die_serial.log 2>&1; echo "DIE_SERIAL rc=$?"; grep XS_WQB_DIE_DONE $O/die_serial.log
python3 $Q/xs_wqb_die.py die --fixtures-root $B/fixtures --contract $R/retained_sid6_fixture_contract.json --out $O/die_p124 --period 124 --cfg-lead 50 --layers L0 > $O/die_p124.log 2>&1; rc=$?
echo "DIE_P124_REFUSE rc=$rc $(grep -m1 -o 'CalendarFault.*' $O/die_p124.log)"
timeout 3600 python3 tools/s81_dv/dv_layer_compile.py --layer L0 --out $O/dvc_L0 --die-src /srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref --fixtures $B/fixtures/L0 > $O/dvc_L0.log 2>&1
echo "DVC_L0 rc=$? $(ls $O/dvc_L0/prog/xs/ 2>/dev/null | grep -c calendar) calendar records"; tail -3 $O/dvc_L0.log
for c in $O/dvc_L0/prog/xs/*.calendar.json; do [ -f $c ] && python3 -c "import json;c=json.load(open('$c'));print('DVC_CAL',c['layer'],c['slice'],c['mode'],c['period'],c['nphases'],'static',c['static']['PASS'],'span',c['predicted_span'])"; done
# ---------------------------------------------------------------- 3 CONSUMER
CAL=$O/emit/compiler_calendar.json; K="python3 $Q/check_wqbp_consumer.py --root $R --golden-checker $G"
nbad=0
run() { local name=$1 run=$2 fix=$3 cal=$4 exp=$5; shift 5
  $K --fixture $fix --run $run --calendar $cal --out $O/consumer/$name.json --expect $exp "$@" > $O/consumer/$name.stdout 2>&1; local rc=$?
  echo "CONSUMER $name rc=$rc $(tail -1 $O/consumer/$name.stdout)"; [ $rc = 0 ] || nbad=$((nbad+1)); }
run l0_nominal       $CX/source_compiled $R/sid6_fixture $CAL pass
run l2_nominal       $CX/capture_l2      $B/fixtures/L2  $CAL pass
run l14_nominal      $CX/capture_l14     $B/fixtures/L14 $CAL pass
run l0_deadline_m118 $CX/source_compiled $R/sid6_fixture $CAL pass --deadline-shift -118
run l0_deadline_m119 $CX/source_compiled $R/sid6_fixture $CAL fail --deadline-shift -119
run l0_no_tail       $CX/source_compiled $R/sid6_fixture $CAL fail --tail 0
run neg_wrong_rbase  $CX/wrong_rbase     $R/sid6_fixture $CAL fail
run neg_late_cfg     $CX/late_cfg        $R/sid6_fixture $CAL fail
run neg_p124         $B/runs/l0_p124neg  $R/sid6_fixture $B/runs/l0_p124neg/model/contract.json fail
echo "WQBP_CONSUMER_MATRIX not_as_expected=$nbad"
echo WQBP_CONSUMER_DONE
