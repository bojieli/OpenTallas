#!/bin/bash
# S81-KITS-RTLC: place-only kits (full recipe: POST_SYNTH_TCL kept) for l5_n32 and xfin from the current branch RTL
set -eu
R=/srv/opentallas-scratch/claude/elem-s81-cores/r2; W=/srv/opentallas-scratch/claude/wt/s81-kits-1024r-nodes
D=/srv/opentallas-scratch2/claude/rtlc2/place; S=/srv/opentallas-scratch2/claude/rtlc2/kits; mkdir -p $D
mk() {  # src new synthkit
  local src=$R/$1 dst=$D/$2
  [ -e $dst ] && { echo "EXISTS $dst"; return 1; }
  mkdir -p $dst
  rsync -a --exclude run --exclude __pycache__ --exclude face_guard.json --exclude image.txt --exclude "*.log" \
        --exclude placed.csv --exclude "review*" --exclude signoff $src/ $dst/
  cp $S/$3/rtl/* $dst/rtl/            # the synth kit's refreshed RTL (same file list)
  cp $S/$3/pins.json $dst/pins.json
  cmp -s $S/$3/io.tcl $dst/io.tcl || cp $S/$3/io.tcl $dst/io.tcl
  git -C $W show origin/main:tools/die_plan/face_guard.py > $dst/face_guard.py
  sed -i "/^pair /d" $dst/ft_stations.txt
  echo "made $dst"
}
mk dsdv_gunit_l5_n32 dsdv_gunit_l5_n32 dsdv_gunit_l5_n32
mk ot_s81dv_xfin_c ot_s81dv_xfin ot_s81dv_xfin
for k in dsdv_gunit_l5_n32:48:8 ot_s81dv_xfin:32:8; do n=${k%%:*}; r=${k#*:}; m=${r%%:*}; c=${r#*:}
  nohup bash -c "cd $D/$n && ~/.local/bin/ot-run --mem $m --threads $c --dir $D/$n -- bash run_kit.sh $D/$n place $m $c; echo rc=\$?" > $D/$n.otrun.log 2>&1 < /dev/null &
done
echo launched
