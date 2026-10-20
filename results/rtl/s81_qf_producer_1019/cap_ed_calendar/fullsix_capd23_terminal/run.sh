#!/bin/bash
# TOK2 (LEAD2-S81) 10-19: fullsix coupled QF diagnostic with the CAP-ED calendar fix
#  = frontend_02 inputs (757a340ff recipe) + ot_s81sl_cap #(.EDLY(23)) + ot_s81sl_cap_ed + packD_23 12-pair images.
set -uo pipefail
S=/srv/opentallas-scratch/claude/s81-qf-producer-source-1019/fullsix_frontend_02
T=/srv/opentallas-scratch/claude/tok2-capd
O=$T/fullsix_capd23; cd $O
if [ ! -e staged ]; then
  cp -a $S/src $S/cells_used.v $S/selected_fullsix_cone.sv $S/source_files.f $S/expected_xq.mem $S/expected_reads.mem \
        $S/source_ctl.txt $S/classify_diagnostic.py $S/diagnostic_expected_identity.json .
  mkdir images; cp $S/images/*.viamap.hex images/ 2>/dev/null
  cp $T/root/images_capd23/images/* images/
  cp $T/new/ot_s81sl_cap.sv $T/new/ot_s81sl_cap_ed.sv src/rtl/dsrom_sys/s81_dv/slice/
  grep -q ot_s81sl_cap_ed.sv source_files.f || sed -i 's|^src/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap.sv$|&\nsrc/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap_ed.sv|' source_files.f
  sed 's|^ot_s81sl_cap cap(|ot_s81sl_cap #(.EDLY(23)) cap(|' $S/tb_fullsix_trace.sv > tb_fullsix_trace.sv
  grep -c 'EDLY(23)' tb_fullsix_trace.sv; grep -c cap_ed source_files.f; ls images | wc -l
  sha256sum tb_fullsix_trace.sv source_files.f src/rtl/dsrom_sys/s81_dv/slice/ot_s81sl_cap*.sv images/* > inputs.sha256
  touch staged
fi
v="$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator"; "$v" --version > verilator.version
if [ ! -x obj/Vtb_fullsix_trace ]; then
  /usr/bin/time -v -o build_time.log "$v" --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD +define+DSFD_PQ_STATIC_X2 \
   --top-module tb_fullsix_trace --Mdir obj -f source_files.f cells_used.v selected_fullsix_cone.sv tb_fullsix_trace.sv \
   --build-jobs 32 -MAKEFLAGS 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0' > build.log 2>&1 || { echo BUILD_FAILED; grep -m10 %Error build.log; exit 3; }
fi
/usr/bin/time -v -o run_time.log obj/Vtb_fullsix_trace +DIR=. +OT_ROM_DIR=images > diagnostic.log 2>&1; echo "sim rc=$?"
python3 classify_diagnostic.py; echo "classify rc=$?"
python3 - <<'PY'
import re,json
s=open('diagnostic.log').read()
c=[(int(t),v) for t,v in re.findall(r'^\S*\s*t=(-?\d+)\S*.* causes=([0-9a-f]+)',s,re.M)]
first={}
for t,v in c:
  if v not in first:first[v]=t
d=json.load(open('diagnostic_classification.json'))
print('TOK2_CAPD_RESULT causes_first_seen',first,'sticky',d['CAP_sticky_causes'],'missing_rows',len(d['missing_semantic_rows']),
      'dups',len(d['duplicate_counts']),'unknown',len(d['unknown_row_identities']),'returns',len(d['frame_return_words']),'srcerr',d['raw_source_check_errors'])
PY
grep -m3 -E "FULLSIX_SOURCE_CHECK|FULLSIX_PREPARATORY_TRACE_END" diagnostic.log
echo TOK2_FULLSIX_DONE
