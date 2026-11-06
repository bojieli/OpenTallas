#!/bin/bash
# HBM-REFORM-B6: stalled K bench. The landing pop is held off 256 of every 1024 edges (slow stream side), so the bank FIFO fills,
# credit reaches 0, the arbiter drops kr_rdy and the K read response back-pressures. Only the bench copy of split.sv changes.
B=/srv/opentallas-scratch3/claude/hbm-reform-b5/bench; cd $B; export B VL_JOBS=8
OUT=/srv/opentallas-scratch3/claude/hbm-reform-b6/stall; mkdir -p $OUT
cat > $OUT/s1.sed <<'S'
s/^ assign packet_v=!empty;assign freed=rf\[1:0\];/ reg [15:0] tb_st=0;always @(posedge stream_clk)tb_st<=tb_st+1'b1;always @(posedge stream_clk)if(tb_st==0)$display("STALLBENCH on");assign packet_v=!empty\&\&!(tb_st[9:8]==2'd3);assign freed=rf[1:0];/
S
run(){ n=$1; shift; bash mkbench.sh $n $OUT/s1.sed "$@" > out/$n.mk 2>&1; grep -c tb_st tmp_$n/split.sv > $OUT/$n.chk; bash one.sh $n L00:0 smoke > out/$n.run 2>&1
 echo "$n sedhits=$(cat $OUT/$n.chk) $(grep -cE 'MUT=[1-4]\)\(' src_$n/rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_group_rel_id.sv) $(grep -m1 -E 'SMB_UNIT|FAULT|Error' out/$n.smoke.log | cut -c1-200) | $(tail -1 out/$n.mk | cut -c1-40)" >> $OUT/res.txt; rm -rf work_$n/obj_*; }
run sb0 & run sb1 $B/m_ow1.sed & run sb4 $B/m_ow4.sed & wait
echo ALLDONE >> $OUT/res.txt
