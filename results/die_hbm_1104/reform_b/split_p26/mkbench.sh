#!/bin/bash
# mkbench.sh NAME [TILE_MUT...]: bench tree src_NAME = src_new with the group module replaced by the part 26 composition with face shells, one clock.
set -e; N=$1; shift; W=/srv/opentallas-scratch3/claude/hbm-reform-b3/wt; A=/srv/opentallas-scratch3/claude/hbm-reform-b5; B=$A/bench
rm -rf $B/src_$N; cp -al $B/src_new $B/src_$N
Q=$W/results/die_hbm_1104/reform_b/split_p26; R=$W/rtl/hbm_accel/cores_split/reform_1105b/ot_svgr_split.sv; T=$A/bench/tmp_$N; rm -rf $T; mkdir -p $T
cp $R $T/split.sv; for s in "$@"; do sed -i -f "$s" $T/split.sv; done
FW="python3 $W/physical/die_plan/hbm/over_cap_split/reform_1103/facewrap.py --no-hier --clk-re clk --rst-re rst"
$FW --top ot_svgr_top --out $T/t.fs.sv -- $T/split.sv >/dev/null
$FW --top ot_svgr_own --out $T/o.fs.sv -- $T/split.sv >/dev/null
$FW --top ot_svgr_bk --out $T/b.fs.sv -- $T/split.sv >/dev/null
G=rtl/hbm_accel/loader/service_native/ot_hbm_svc_sm_group_rel_id.sv
rm -f $B/src_$N/$G
{ sed 's/ot_hbm_svc_sm_group_rel_id__p26fs/ot_hbm_svc_sm_group_rel_id/' $Q/ot_hbm_svc_sm_group_rel_id__p26fs.sv; cat $T/split.sv $T/t.fs.sv $T/o.fs.sv $T/b.fs.sv; echo 'module ot_hbm_face_reg #(parameter integer W=1)(input wire clk, input wire [W-1:0] d, output reg [W-1:0] q); always @(posedge clk) q<=d; endmodule'; } > $B/src_$N/$G
TB=rtl/test/hbm_accel/svg_rel/tb_hbm_svg_rel_sm.sv; rm -f $B/src_$N/$TB; sed -E -e "$(cat $A/bench/tbclk.sed)" -e "s/\bsvg\./svg.u_t.u_fcore./g" $B/src_new/$TB > $B/src_$N/$TB
python3 -I $B/tb_xcface.py $B/src_$N/$TB; F=tools/hbm_layer_vehicle/smb_svc_files.txt; grep -q 'hbm_accel/service/ot_hbm_accel_cdc_fifo.sv' $B/src_$N/$F || { rm -f $B/src_$N/$F; { cat $B/src_new/$F; echo; echo rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv; } > $B/src_$N/$F; }
echo tree $N ok
