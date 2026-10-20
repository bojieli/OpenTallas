#!/bin/bash
# TOKSIM-S81/FIELD 10-19: wq_b fullsix (sid6, 6 frames, 512 rows, 15 epochs) epoch-period sweep on the TOK2 L16/E24 exe.
# Only change vs TOK2 fullsix_l16e24: the bench calendar epoch shift 1100+600*i -> 1100+P*i (TOKSIM_PERIOD). Same exe/RTL.
set -uo pipefail
P=$1; D=/srv/opentallas-scratch/claude/toksim-s81-field; T=$D; S=$D/fs
O=$D/p$P; rm -rf $O; mkdir -p $O; cd $T/root; Q=tools/s81_dv/layer_prog/qf_producer
TOKSIM_PERIOD=$P python3 $D/tools/retained_xs_program_period.py --fixture sid6_fixture --contract retained_sid6_fixture_contract.json --raw-program qnorm_program_model_v2/program.json --out $O/model --placements s_16_24.json --shifts "{\"L01\":0,\"L02\":0,\"L03\":0,\"R01\":16,\"R02\":24,\"R03\":24}" > $O/gen.log 2>&1 || { echo GEN_FAIL; tail -5 $O/gen.log; exit 2; }
python3 $Q/serialize_selected_vehicle.py --fixture sid6_fixture --model $O/model --out $O/ser > $O/ser.log 2>&1 || { echo SER_FAIL; tail -5 $O/ser.log; exit 2; }
cd $O; cp $S/expected_xq.mem $S/expected_reads.mem $S/classify_diagnostic.py $S/diagnostic_expected_identity.json .
cp $O/model/source_ctl.txt .; mkdir -p images; cp $S/images/*.viamap.hex images/ 2>/dev/null; cp $O/ser/images/* images/
cmp -s $O/model/source_ctl.txt $D/root/model_l16e24/source_ctl.txt && echo "CTL_SAME_AS_600" || echo "CTL_DIFF_FROM_600"
/usr/bin/time -v -o run_time.log $D/tools/Vtb_fullsix_trace +DIR=. +OT_ROM_DIR=images > diagnostic.log 2>&1; echo "sim rc=$?"
python3 classify_diagnostic.py; echo "classify rc=$?"
python3 - <<PY
import json,collections,re
d=json.load(open("diagnostic_classification.json"));w=d["frame_return_words"];c=d["actual_tag_captures"]
ep=collections.defaultdict(list)
for x in w: ep[x["epoch"]].append(x["t"])
cg=collections.defaultdict(list)
s=open("diagnostic.log").read()
gos=[int(t) for t,e in re.findall(r"ACTUAL_GO t=(-?\d+) epoch=(\d+)",s)]
base=json.load(open("$S/diagnostic_classification.json"))
bv={(x["semantic_row"],x["row16"],x["word"]) for x in base["frame_return_words"]}
nv={(x["semantic_row"],x["row16"],x["word"]) for x in w}
print("TOKSIM_FIELD_P$P", "returns",len(w),"missing",len(d["missing_semantic_rows"]),"unknown",len(d["unknown_row_identities"]),
 "srcerr",d["raw_source_check_errors"],"CAPcause",d["CAP_sticky_causes"],"capt_mism",len(d["captured_sample_mismatches"]),
 "first_capture",min(x["t"] for x in c),"last_capture",max(x["t"] for x in c),"first_ret",min(x["t"] for x in w),"last_ret",max(x["t"] for x in w),
 "words_equal_600",nv==bv,"only_new",len(nv-bv),"only_600",len(bv-nv))
for e in sorted(ep): print(" epoch",e,len(ep[e]),min(ep[e]),max(ep[e]))
PY
grep -m2 -E "FULLSIX_SOURCE_CHECK|FULLSIX_PREPARATORY_TRACE_END" diagnostic.log
gzip -kf diagnostic.log; rm -f diagnostic.log
echo TOKSIM_FIELD_DONE P=$P
