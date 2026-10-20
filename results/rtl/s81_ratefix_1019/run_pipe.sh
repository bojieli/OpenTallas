#!/bin/bash
# S81-RATEFIX 10-19: wq_b fullsix (sid6, 6 frames, 512 rows, 15 epochs) with the PIPELINED phase calendar
# (xs_calendar.compile_pipeline) on the unchanged TOK2 L16/E24 fullsix exe (same exe / RTL as TOKSIM-S81/FIELD).
# args: TAG MODE(pipe|serial) PERIOD CFG_LEAD
set -uo pipefail
TAG=$1; MODE=$2; P=$3; C=${4:-48}
F=/srv/opentallas-scratch/claude/toksim-s81-field; D=/srv/opentallas-scratch/claude/s81-ratefix; S=$F/fs
O=$D/$TAG; rm -rf $O; mkdir -p $O; cd $F/root; Q=tools/s81_dv/layer_prog/qf_producer
if [ $MODE = pipe ]; then X="--pipeline-period $P --cfg-lead $C"; else X="--epoch-period $P"; fi
python3 $D/tools/gen_wrap.py $F/root $D/tools --fixture sid6_fixture --contract retained_sid6_fixture_contract.json --raw-program qnorm_program_model_v2/program.json --out $O/model --placements s_16_24.json --shifts "{\"L01\":0,\"L02\":0,\"L03\":0,\"R01\":16,\"R02\":24,\"R03\":24}" $X > $O/gen.log 2>&1 || { echo GEN_FAIL; tail -8 $O/gen.log; exit 2; }
python3 $Q/serialize_selected_vehicle.py --fixture sid6_fixture --model $O/model --out $O/ser > $O/ser.log 2>&1 || { echo SER_FAIL; tail -5 $O/ser.log; exit 2; }
cd $O; cp $S/expected_xq.mem $S/expected_reads.mem $S/classify_diagnostic.py $S/diagnostic_expected_identity.json .
cp $O/model/source_ctl.txt .; mkdir -p images; cp $S/images/*.viamap.hex images/ 2>/dev/null; cp $O/ser/images/* images/
# the xs ROM images (calendar action/time, phase, stream) are the MODEL's: $S/images holds the serial-calendar copy
for f in pq_calendar_action pq_calendar_time pq_phase0 pq_stream0 pq_stream1 pq_stream2 pq_stream3; do cp $O/model/$f.viamap.hex images/; done
for f in source_ctl.txt; do cmp -s $O/model/$f $F/p224/model/$f && echo "SAME_AS_P224 $f" || echo "DIFF_FROM_P224 $f"; done
/usr/bin/time -v -o run_time.log $F/tools/Vtb_fullsix_trace +DIR=. +OT_ROM_DIR=images > diagnostic.log 2>&1; echo "sim rc=$?"
python3 classify_diagnostic.py; echo "classify rc=$?"
python3 $D/tools/ana_pipe.py . $S/diagnostic_classification.json
gzip -kf diagnostic.log; rm -f diagnostic.log
echo RATEFIX_DONE $TAG
