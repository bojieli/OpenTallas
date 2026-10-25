#!/bin/bash
# S81-KITS-RTLC synth-only kits (RTLB recipe): generated kit without run outputs, changed RTL from the branch worktree,
# no POST_SYNTH_TCL, main face_guard.py, no pair lines; pins.json through const_pins_dropped.json (kitpins.py, RTLA)
set -eu
R=/srv/opentallas-scratch/claude/elem-s81-cores; W=/srv/opentallas-scratch/claude/wt/s81-kits-1024r-nodes
D=/srv/opentallas-scratch/claude/s81-kits/rtlc_stage
CH="rtl/dsrom_sys/s81_fill2/gen19b/dsfd_qbank_N.sv rtl/dsrom_sys/s81_fill2/gen19b/dsfd_qbank_S.sv rtl/dsrom_sys/s81_static_net/gen/dsfd_rstg.sv rtl/dsrom_sys/s81_static_net/ot_s81_sstn_payload536.sv rtl/dsrom_sys/s81_static_net/ot_s81_sstn_base566.sv rtl/dsrom_sys/s81_ph/ot_s81ph_sel_tile.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l0.sv rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l1.sv rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l1c.sv rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l2.sv rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l3.sv rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l4.sv rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_l5.sv rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv"
mk() {  # src_kit new_name
  local src=$R/$1 dst=$D/$2
  [ -e $dst ] && { echo "EXISTS $dst"; return 1; }
  mkdir -p $dst
  rsync -a --exclude run --exclude __pycache__ --exclude face_guard.json --exclude image.txt --exclude "*.log" \
        --exclude placed.csv --exclude "review*" --exclude signoff $src/ $dst/
  n=0; for f in $CH; do b=$(basename $f); [ -e $dst/rtl/$b ] && { cp $W/$f $dst/rtl/$b; n=$((n+1)); }; done
  sed -i "/^export POST_SYNTH_TCL/d" $dst/config.mk
  git -C $W show origin/main:tools/die_plan/face_guard.py > $dst/face_guard.py
  sed -i "/^pair /d" $dst/ft_stations.txt
  python3 $D/kitpins.py $dst $W/physical/die_plan/s81/inputs/const_pins_dropped.json
  echo "made $dst ($n rtl files refreshed)"
}
mk r4/dsfd_qbank_N_c dsfd_qbank_N; mk r4/dsfd_qbank_S_c dsfd_qbank_S; mk r4/dsfd_rstg_c dsfd_rstg
mk r4/ot_s81_sstn_payload536_c ot_s81_sstn_payload536; mk r2/ot_s81_sstn_base566_c ot_s81_sstn_base566
mk r2/dsdv_bksel_c_c dsdv_bksel_c
for l in l0 l1c l2 l4; do mk r2/dsdv_gunit_${l}_c dsdv_gunit_$l; done
mk r2/dsdv_gunit_l5_n32 dsdv_gunit_l5_n32
for l in l1 l3; do mk r5/dsdv_gunit_${l}_c dsdv_gunit_$l; done
for x in xrt1 xrt3; do mk r5/ot_s81sl_${x}_c ot_s81sl_${x}; done
