#!/bin/bash
# hbm-forks 2026-10-09: the MTP control block (hfd_mtp: dspark_ctl + argmax + accept) at TW 18 (HGI-1 18-bit tokens),
# CF-1 = the DS golden-trace benches (physical/hbm_mtp/run_bench.sh; traces from tools/dshbm_dspark_trace.py) replayed with
# TW = 18 in the hm (FAST 0) and hmf (FAST 1) configurations: PASS; ctl MUT 1 at TW 18: must FAIL.
#   run_mtp_tw18.sh <trace root> <out dir>
T=$1; O=$2; mkdir -p $O; rc=0
for tr in tr_dspark tr_forced tr_forced_w16; do
  W=$(python3 -c "import json;c=json.load(open('$T/$tr/cfg.json'));print(c.get('window_override') or 0)")
  (WR=$([ "$W" != 0 ] && echo $((W + 8)) || echo 0) bash physical/hbm_mtp/run_bench.sh $T/$tr $O/hm_$tr -DHFD_MTP -Ptb_dshbm_dspark.TW=18 > $O/hm_$tr.txt 2>&1; echo "hm_$tr rc=$?" >> $O/rc.txt) &
  (WR=$([ "$W" != 0 ] && echo $((W + 8)) || echo 0) bash physical/hbm_mtp/run_bench.sh $T/$tr $O/hmf_$tr -DHFD_MTP -DHFD_MTP_FAST -Ptb_dshbm_dspark.TW=18 > $O/hmf_$tr.txt 2>&1; echo "hmf_$tr rc=$?" >> $O/rc.txt) &
done
(MUT=1 bash physical/hbm_mtp/run_bench.sh $T/tr_dspark $O/mut1 -DHFD_MTP -DHFD_MTP_FAST -Ptb_dshbm_dspark.TW=18 > $O/mut1.txt 2>&1; echo "mut1 rc=$?" >> $O/rc.txt) &
wait
cat $O/rc.txt; head -1 $O/*.txt
for r in hm_tr_dspark hm_tr_forced hm_tr_forced_w16 hmf_tr_dspark hmf_tr_forced hmf_tr_forced_w16; do grep -q "^$r rc=0" $O/rc.txt || rc=1; done
grep -q "^mut1 rc=0" $O/rc.txt && rc=1
[ $rc -eq 0 ] && echo "MTP_TW18 PASS" || echo "MTP_TW18 FAIL"; exit $rc
