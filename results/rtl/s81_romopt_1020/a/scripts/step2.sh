#!/bin/bash
# S81-ROMOPT-A step 2: release default (compact tails on): single-phase frame bench, CAP L0..L20, frame images
set -u; D=/srv/opentallas-scratch/claude/s81-romopt-a; cd $D/root; export PYTHONDONTWRITEBYTECODE=1
DR=/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref; FXR=/srv/opentallas-scratch/claude/s81-calpipe/fixtures; O=$D/out/step2; mkdir -p $O
python3 -c "import sys; sys.path.insert(0,'tools/s81_dv/layer_prog'); import xs_flags as X; print('ENV', X.describe())"
( rm -rf $D/out/bench_o1o2c; timeout 5400 python3 $D/bencha.py $D/out/bench_o1o2c > $D/out/bench_o1o2c.log 2>&1; echo "BENCHA o1o2c rc=$? $(grep -E 'VERDICT|Error' $D/out/bench_o1o2c.log|tail -2)" ) &
for L in L0 L2 L14 L20; do ( timeout 1800 python3 tools/s81_dv/layer_prog/xs_calendar.py cap --out $O/cap_default_$L.json --fixtures $FXR/$L --layer $L --die-src $DR > $O/cap_default_$L.log 2>&1
  echo "CAP default $L rc=$? $(grep -E 'XS_CAP|Error' $O/cap_default_$L.log | tail -2 | cut -c1-300 | tr '\n' '|')" ) & done
wait
bash $D/imagesa.sh o1o2c
