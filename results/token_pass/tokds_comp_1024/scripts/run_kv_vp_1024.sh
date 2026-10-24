#!/bin/bash
# TOK-DS/COMP 10-24: real VP + KV512 consumer component (tools/s81_dv/kv_vp_1021/gate.py, unchanged) on main RTL.
# run_kv_vp_1024.sh WT OUT JOBS
# The new fleet lacks the installed NBA guard (share/ot_nba_guard) that gate.py imports from $HOME; a private HOME with
# the real verilator bin dir symlinked and the repo's tools/verilator_nba_guard.py (same sha as the 10-21 run) is used.
set -uo pipefail
WT=$1; O=$2; J=${3:-8}; mkdir -p $O
cd $WT; git rev-parse HEAD > $O/main_sha.txt
python3 $(dirname $(realpath $0))/mk_kv_baseline_1024.py $WT $O/baseline > $O/baseline.log 2>&1 || { echo "BASELINE FAIL"; exit 2; }
H=$O/home; R=$HOME/.local/opentallas-tools/verilator-5.050
mkdir -p $H/.local/opentallas-tools/verilator-5.050/share/ot_nba_guard
ln -sfn $R/bin $H/.local/opentallas-tools/verilator-5.050/bin
ln -sfn $R/share/verilator $H/.local/opentallas-tools/verilator-5.050/share/verilator
cp $WT/tools/verilator_nba_guard.py $H/.local/opentallas-tools/verilator-5.050/share/ot_nba_guard/
HOME=$H python3 $WT/tools/s81_dv/kv_vp_1021/gate.py --baseline $O/baseline --out $O/run --jobs $J > $O/gate.log 2>&1
echo "rc $?" >> $O/gate.log
echo DONE
