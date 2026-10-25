#!/bin/bash
# S81-KITS-RTLC ruling (b): synth-only kits dsdv_bksel_c / dsdv_bk_g (RTLC recipe, new dirs on scratch2)
set -eu
R=/srv/opentallas-scratch/claude/elem-s81-cores/r2; W=/srv/opentallas-scratch/claude/wt/s81-kits-1024r-nodes
D=/srv/opentallas-scratch2/claude/rtlc2/kits; ST=/srv/opentallas-scratch/claude/s81-kits/rtlc_stage
CH="rtl/dsrom_sys/s81_ph/ot_s81ph_sel_tile.sv rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bksel_c.sv rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bk_g.sv rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bk_v.sv rtl/dsrom_sys/s81_dv/unit/ot_dsdv_vstop.sv"
mk() {
  local src=$R/$1 dst=$D/$2
  [ -e $dst ] && { echo "EXISTS $dst"; return 1; }
  mkdir -p $dst
  rsync -a --exclude run --exclude __pycache__ --exclude face_guard.json --exclude image.txt --exclude "*.log" \
        --exclude placed.csv --exclude "review*" --exclude signoff $src/ $dst/
  n=0; for f in $CH; do b=$(basename $f); [ -e $dst/rtl/$b ] && { cmp -s $W/$f $dst/rtl/$b || n=$((n+1)); cp $W/$f $dst/rtl/$b; }; done
  sed -i "/^export POST_SYNTH_TCL/d" $dst/config.mk
  git -C $W show origin/main:tools/die_plan/face_guard.py > $dst/face_guard.py
  sed -i "/^pair /d" $dst/ft_stations.txt
  python3 $ST/kitpins.py $dst $W/physical/die_plan/s81/inputs/const_pins_dropped.json
  echo "made $dst ($n rtl files changed)"
}
mk dsdv_bksel_c_c dsdv_bksel_c; mk dsdv_bk_g_c dsdv_bk_g
