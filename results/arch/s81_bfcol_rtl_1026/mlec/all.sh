export PATH=/OpenROAD-flow-scripts/tools/install/yosys/bin:$PATH
M=/srv/opentallas-scratch2/claude/s81-bfcol-rtl/mlec; G=/srv/opentallas-scratch2/claude/s81-bfcol-rtl/gold; N=/srv/opentallas-scratch2/claude/wt/s81-bfcol-rtl
$M/mlec.sh $G $N $M/bt_p1s0 ot_v41_bterm4_w10 -set TW 8 &
$M/mlec.sh $G $N $M/bt_p1s1 ot_v41_bterm4_w10 -set TW 8 -set P1S 1 -set CSAM 10 -set P2S 1 -set NS 1 &
$M/mlec.sh $G $N $M/bt_p1s1wd ot_v41_bterm4_w10 -set TW 8 -set P1S 1 -set CSAM 10 -set P2S 1 -set NS 1 -set WD 1 &
$M/mlec.sh $G $N $M/st5_def ot_v41_segtree5 &
$M/mlec.sh $G $N $M/st5_bf ot_v41_segtree5 -set NT 16 -set LV 5 -set EARLY 1 -set QD 8 &
wait
