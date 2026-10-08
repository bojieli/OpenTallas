#!/bin/bash
# WINDOW stage MARGIN unit bench: original tb (MARGIN default 0), derived tb MARGIN 0/1 x SPLIT 0/1, three mutants.
set -u
B=/srv/opentallas-scratch/claude/takeover-ds/window-stage/bench; S=$B/src; R=$B/out; mkdir -p $R
ROWS=/srv/opentallas-scratch/claude/dsrom-s81-window-bind/vec/L0.rows
STG=$S/rtl/dsrom_sys/s81_window_la/pipeline/ot_dsrom_window_stage_pipeline.sv
TO=$S/rtl/test/dsrom_sys/s81_window_la/tb_window_stage_read_qualification.sv
TM=$S/rtl/test/dsrom_sys/s81_window_la/tb_window_stage_margin.sv
mk() { # name tb top stage params...
  local n=$1 tb=$2 top=$3 stg=$4; shift 4
  ( iverilog -g2012 -s $top "$@" -o $R/$n.vvp $tb $stg > $R/$n.compile.log 2>&1 && \
    /usr/bin/time -v vvp $R/$n.vvp +rows=$ROWS > $R/$n.sim.log 2> $R/$n.time ; echo $? > $R/$n.rc ) &
}
sed 's/wire \[ROWB-1:0\] row_l = MARGIN ? bq1\[bank\] : bank_q\[bank\];/wire [ROWB-1:0] row_l = bank_q[bank];/' $STG > $R/mut_rsp_unstaged.sv
sed 's/assign chosen = chosen_q;/assign chosen = chosen_c;/' $STG > $R/mut_chosen_unaligned.sv
sed "s/occ <= occ_n; rdy_q <= occ_n < 2'd2;/occ <= occ_n; rdy_q <= 1'b1;/" $STG > $R/mut_fifo_overrun.sv
for m in mut_rsp_unstaged mut_chosen_unaligned mut_fifo_overrun; do cmp -s $STG $R/$m.sv && echo "MUTANT $m NOT APPLIED" > $R/$m.notapplied; done
mk orig_tb_m0 $TO tb_window_stage_read_qualification $STG
mk orig_tb_m0_split $TO tb_window_stage_read_qualification $STG -Ptb_window_stage_read_qualification.SPLIT_COLUMNS=1
mk m0 $TM tb_window_stage_margin $STG -Ptb_window_stage_margin.MARGIN=0
mk m1 $TM tb_window_stage_margin $STG -Ptb_window_stage_margin.MARGIN=1
mk m1_split $TM tb_window_stage_margin $STG -Ptb_window_stage_margin.MARGIN=1 -Ptb_window_stage_margin.SPLIT_COLUMNS=1
mk neg_rsp_unstaged $TM tb_window_stage_margin $R/mut_rsp_unstaged.sv -Ptb_window_stage_margin.MARGIN=1
mk neg_chosen_unaligned $TM tb_window_stage_margin $R/mut_chosen_unaligned.sv -Ptb_window_stage_margin.MARGIN=1
mk neg_fifo_overrun $TM tb_window_stage_margin $R/mut_fifo_overrun.sv -Ptb_window_stage_margin.MARGIN=1
wait
for f in $R/*.rc; do n=$(basename $f .rc); echo "$n rc=$(cat $f) $(grep -h -E 'PASS|FATAL|fatal|Error|error' $R/$n.sim.log $R/$n.compile.log 2>/dev/null | head -2 | tr '\n' ' ')"; done > $R/summary.txt
echo done > $R/terminal
