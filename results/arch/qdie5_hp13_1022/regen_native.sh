#!/bin/bash
# QDIE5-HP13: frozen HP13 frontend (yosys 0.68) + construct_hp13_2 in tree $1
set -u; T=$(readlink -f "$1"); cd $T || exit 2
Y=$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys
mkdir -p work/generic work/constructed2
sed "s#/work/#$T/work/#g" full_generic_hp13.ys > run_generic.ys
sed "s#/work/#$T/work/#g" construct_hp13_2.py > run_construct.py
$Y -l work/frontend.log -s run_generic.ys > /dev/null 2>&1; echo "FRONTEND_RC $?"
python3 run_construct.py > work/construct.log 2>&1; echo "CONSTRUCT_RC $?"; tail -1 work/construct.log
sha256sum work/generic/parent.json work/constructed2/*.sv
