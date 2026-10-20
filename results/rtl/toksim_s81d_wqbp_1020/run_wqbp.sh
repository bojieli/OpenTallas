#!/bin/bash
# TOKSIM-S81D/WQBP 10-20: attn.wq_b fullsix vehicle (TOK2 L16/E24 exe, sid6 placement: head 6, 6 frames, 512 rows,
# 15 phases) on the COMPILER-EMITTED retained-XS programme: retained_xs_program.py now takes its calendar from the die
# compiler's xs_wqb_die.wqb_calendar (DEFAULT pipeline P126 / cfg 52, static checks).  x source (qnorm raw programme),
# XQ gold and per-epoch read counts are regenerated from the given layer fixture, so a sparse layer runs its own x.
# args: TAG FIXTURE_DIR [extra retained_xs_program args, e.g. --pipeline-period 124 --cfg-lead 50 --allow-below-floor]
set -uo pipefail
TAG=$1; FIX=$2; shift 2; X="$*"
D=/srv/opentallas-scratch/claude/toksim-s81d-wqbp; F=/srv/opentallas-scratch/claude/toksim-s81-field; S=$F/fs; R=$D/root
O=$D/runs/$TAG; rm -rf $O; mkdir -p $O; cd $R; Q=tools/s81_dv/layer_prog/qf_producer
echo "WQBP_ARGS tag=$TAG fixture=$FIX extra=[$X] host=$(hostname)"
python3 $Q/qnorm_program_model.py --fixture $FIX --out $O/qn > $O/qn.log 2>&1 || { echo QN_FAIL; tail -5 $O/qn.log; exit 2; }
cmp -s $O/qn/program.json $R/qnorm_program_model_v2/program.json && echo "QN_PROGRAM_SAME_AS_SID6_V2" || echo "QN_PROGRAM_DIFF_FROM_SID6_V2"
python3 $Q/retained_xs_program.py --fixture $FIX --contract retained_sid6_fixture_contract.json --raw-program $O/qn/program.json --out $O/model --placements s_16_24.json --shifts '{"L01":0,"L02":0,"L03":0,"R01":16,"R02":24,"R03":24}' $X > $O/gen.log 2>&1 || { echo GEN_FAIL; tail -8 $O/gen.log; exit 2; }
tail -1 $O/gen.log
python3 $Q/serialize_selected_vehicle.py --fixture $FIX --model $O/model --out $O/ser > $O/ser.log 2>&1 || { echo SER_FAIL; tail -5 $O/ser.log; exit 2; }
cd $O; cp $S/classify_diagnostic.py $S/diagnostic_expected_identity.json .
python3 - <<PY
import json
q=json.load(open('qn/quantized_scoreboard.json'));open('expected_xq.mem','w').write(''.join(x['payload532']+'\n' for x in q))
c=json.load(open('model/contract.json'));open('expected_reads.mem','w').write(''.join(f"{e['data_reads']:08x}\n" for e in c['epochs']))
cc=c['compiler_calendar'];print('WQBP_COMPILER_CALENDAR',cc['mode'],cc['period'],cc['cfg_lead'],'nphases',cc['nphases'],'static_PASS',cc['static']['PASS'],'negctl',cc['static']['below_floor_negative_control'],'predicted_span',cc['predicted_span'])
PY
for f in expected_xq.mem expected_reads.mem; do cmp -s $f $S/$f && echo "SAME_AS_SID6 $f" || echo "DIFF_FROM_SID6 $f"; done
cp $O/model/source_ctl.txt .; mkdir -p images; cp $S/images/*.viamap.hex images/ 2>/dev/null; cp $O/ser/images/* images/
for f in pq_calendar_action pq_calendar_time pq_phase0 pq_stream0 pq_stream1 pq_stream2 pq_stream3; do cp $O/model/$f.viamap.hex images/; done
for f in source_ctl.txt pq_calendar_action.viamap.hex pq_calendar_time.viamap.hex pq_phase0.viamap.hex pq_stream0.viamap.hex; do cmp -s $O/model/$f /srv/opentallas-scratch/claude/s81-ratefix/p126c52/model/$f && echo "SAME_AS_RATEFIX_P126 $f" || echo "DIFF_FROM_RATEFIX_P126 $f"; done
(cd images && sha256sum *.viamap.hex) > images.sha256
echo "EXE $(sha256sum $F/tools/Vtb_fullsix_trace | cut -c1-16) verilator: $(strings $F/tools/Vtb_fullsix_trace | grep -m1 -oE 'Verilator 5\.[0-9]+')"
/usr/bin/time -v -o run_time.log $F/tools/Vtb_fullsix_trace +DIR=. +OT_ROM_DIR=images > diagnostic.log 2>&1; echo "sim rc=$?"
grep -m2 -E "FULLSIX_SOURCE_CHECK|FULLSIX_PREPARATORY_TRACE_END" diagnostic.log
python3 classify_diagnostic.py; echo "classify rc=$?"
python3 /srv/opentallas-scratch/claude/s81-ratefix/tools/ana_pipe.py . $S/diagnostic_classification.json
python3 $D/wqbp_golden_check.py $R $O/golden.json $FIX $TAG=$O
gzip -kf diagnostic.log; rm -f diagnostic.log
echo WQBP_DONE $TAG
