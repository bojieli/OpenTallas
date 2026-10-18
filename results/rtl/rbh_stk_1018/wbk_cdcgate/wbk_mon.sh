#!/usr/bin/env bash
# HBM-WBK 10-18: reachability witness. OLD (pre-gate) cutthrough + a sim-only monitor of the exact state the gate
# changes: req_valid[pc] && fifo_empty[req_lane[pc]] (k_v differs between old and new only there; pick_v already
# implies !fifo_empty[pick_lane]). Runs every wbq + GEN0 wb_default bench; expects hits=0 with checks>0 in each run.
R=/home/ubuntu/scratch/hbm-wbk-1018; T=$R/mon; rm -rf $T; cp -a $R/old $T
f=$T/rtl/hbm_accel/loader/service_native/ot_hbm_svc_wb_cutthrough_cdc.sv
python3 - "$f" <<'PY'
import sys;p=sys.argv[1];t=open(p).read()
mon='''`ifndef SYNTHESIS
 integer mon_checks=0,mon_hits=0,mon_live=0,mm;
 always @(posedge hbm_clk) if(hrst) for(mm=0;mm<NPC;mm=mm+1) begin
  mon_checks=mon_checks+1;
  if(req_valid[mm])mon_live=mon_live+1;
  if(req_valid[mm]&&fifo_empty[req_lane[mm]])begin mon_hits=mon_hits+1;
   $display("WBK_EMPTY_HEAD_READ pc=%0d lane=%0d meta_active=%0d t=%0t",mm,req_lane[mm],meta_active,$time);end
 end
 final $display("WBK_EMPTY_MONITOR %m checks=%0d req_valid_cycles=%0d hits=%0d",mon_checks,mon_live,mon_hits);
`endif
 integer h;'''
assert t.count(' integer h;')==1; open(p,'w').write(t.replace(' integer h;',mon,1))
PY
mkdir -p $R/out/mon
for c in wbq_e wbq_w wbq_e_wopen wb_default; do (cd $T && JOBS=8 bash rtl/hbm_accel/loader/service_native/run_stk_quadrant_bench.sh $R/out/mon/$c $c > $R/out/mon/$c.stdout 2>&1; echo rc=$? >> $R/out/mon/$c.stdout) & done; wait
grep -rh 'WBK_EMPTY_MONITOR\|WBK_EMPTY_HEAD_READ' $R/out/mon --include=*.log | sort | uniq -c | sort -rn | head -40
grep -h 'STK_\|rc=' $R/out/mon/*.stdout
