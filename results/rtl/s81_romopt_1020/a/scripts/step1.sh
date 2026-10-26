#!/bin/bash
# S81-ROMOPT-A step 1: die topology, CAP emission (O1 / O1+O2) L0, field-calendar selftests (release / legacy)
set -u; D=/srv/opentallas-scratch/claude/s81-romopt-a; cd $D/root; export PYTHONDONTWRITEBYTECODE=1
O=$D/out/step1; mkdir -p $O
DR=/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref; FXR=/srv/opentallas-scratch/claude/s81-calpipe/fixtures
python3 - > $O/topo.txt 2>&1 <<PY
import sys; sys.path.insert(0,'tools/s81_dv/layer_prog'); sys.path.insert(0,'tools/s81_dv')
import xs_place as X, dv_layer_compile as C
die=C.Die(C.die_tree(None,'$DR'))
for sl in sorted(die.slices()):
    fr=die.frames_of(sl); print(sl, die.slices()[sl].get('sid'), len(fr), [(f, die.inst[f]['master']) for f in fr])
print(X.TP.describe())
PY
echo "TOPO rc=$?"
for CFG in o1o2 o1; do
  if [ $CFG = o1 ]; then export OT_XS_QPAIRS=10; else unset OT_XS_QPAIRS; fi
  for L in L0 L2 L14 L20; do
    timeout 1800 python3 tools/s81_dv/layer_prog/xs_calendar.py cap --out $O/cap_${CFG}_$L.json --fixtures $FXR/$L --layer $L --die-src $DR > $O/cap_${CFG}_$L.log 2>&1
    echo "CAP $CFG $L rc=$? $(grep -E 'XS_CAP|Error' $O/cap_${CFG}_$L.log | tail -2 | cut -c1-400)"
  done
done
unset OT_XS_QPAIRS
OT_XS_GU_MERGE=0 timeout 1800 python3 tools/s81_dv/layer_prog/xs_calendar.py cap --out $O/cap_nomerge_L0.json --fixtures $FXR/L0 --layer L0 --die-src $DR > $O/cap_nomerge_L0.log 2>&1; echo "CAP nomerge L0 rc=$? $(tail -1 $O/cap_nomerge_L0.log|cut -c1-300)"
for M in release legacy; do
  if [ $M = legacy ]; then export OT_XS_LEGACY=1; fi
  rm -rf $O/selftest_$M; timeout 1800 python3 tools/s81_dv/layer_prog/xs_field_calendar.py selftest --out $O/selftest_$M > $O/selftest_$M.log 2>&1; echo "SELFTEST $M rc=$? $(tail -1 $O/selftest_$M.log | cut -c1-300)"
done
