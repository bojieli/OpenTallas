#!/bin/bash
# PORTFIX-DEAD D-SVCARITY proof: per face variant, elaborate dsdv_svc_rs_c #(FM, ENTRY) (flattened, generic, the heavy
# non-face leaves att / SM share / SO target / svc_pc as black boxes) and list every reader of the masked input bits.
set -e
W=/srv/opentallas-scratch2/claude/wt/s81-portfix-dead; O=/srv/opentallas-scratch2/claude/s81-portfix/dead/svcproof
mkdir -p $O; cd $W
D=rtl/dsrom_sys/s81_dv/svc_rs
TAG=$1; FM=$2; ENTRY=$3; TOP=${4:-dsdv_svc_rs_c}
DEF="-DSYNTHESIS -DOT_SVC_ALLQ -DSVCQ_ENG_FG3 -DSU_SMU_T -I$D"
FULL="rtl/hdc/v41x/ot_hdc_v41x_attn_tile_s.sv rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv rtl/hdc/v41x/ot_hdc_v41x_kreg.sv
 rtl/hdc/v41x/ot_hdc_v41x_attn_tile_lat.sv rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv rtl/hdc/v41x/ot_hdc_v41x_attn.sv
 rtl/hdc/v41x/ot_hdc_v41x_attn_staging.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv
 rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/ot_hdc_delay.sv rtl/dsrom_sys/s81_ctrl/ot_s81_svc_job.sv
 rtl/dsrom_sys/s81_glue/ot_s81_rly.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv rtl/dsrom_sys/s81_dv/sm_target/dsdv_sm_wire.sv
 $D/dsdv_svc_sx_hrow.sv $D/dsdv_svc_sx.sv $D/dsdv_svc_rs.sv"
rm -f $O/att_stub_$TAG.sv; python3 $O/mkstub.py $D/dsdv_svc_att.sv dsdv_svc_att $O/att_stub_$TAG.sv
LIB="$O/att_stub_$TAG.sv rtl/dsrom_sys/s81_dv/su_sm/ot_s81_su_sms.sv rtl/dsrom_sys/s81_dv/sm_target/dsdv_sm_so_target.sv rtl/dsrom_sys/s81_ph/svc/dsfd_svc_pc.sv"
{ if [ "$TOP" = dsdv_svc_rs_c ]; then
    for f in $FULL; do echo "read_verilog -sv $DEF $f"; done
    for f in $LIB; do echo "read_verilog -sv -lib $DEF $f"; done
    echo "hierarchy -check -top dsdv_svc_rs_c -chparam FM 40'h$FM -chparam ENTRY $ENTRY -chparam PV_IDENTITY 1"
  else
    echo "read_verilog -sv $DEF rtl/dsrom_sys/s81_dv/pv_so/dsdv_pv_so_program.sv"
    echo "hierarchy -check -top $TOP -chparam ENABLE 1 -chparam TF 0"
  fi
  echo "proc"; echo "flatten"; echo "opt_clean -purge"; echo "opt"; echo "opt_clean -purge"
  echo "stat"
  echo "write_json $O/$TAG.json"; } > $O/$TAG.ys
docker run --rm --name otdead-svcproof-$TAG -m 40g -u $(id -u):$(id -g) -v $W:$W -v $O:$O -w $W openroad/orfs:asap7lock \
  /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -l $O/$TAG.log -s $O/$TAG.ys
python3 $O/check.py $O/$TAG.json $FM $ENTRY $TOP > $O/$TAG.check.txt
cat $O/$TAG.check.txt | tail -25
#keep json
