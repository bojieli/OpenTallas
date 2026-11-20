#!/bin/bash
# SONNET-FIX-QC 11-20 (COORD): place the signed su-lane clock contracts into the N46T tree AT APPLY, never into a pinned older snapshot.
# usage: enable_contracts.sh TREE_ROOT_ON_EACH_HOST      e.g. /srv/opentallas-scratch2/claude/kw45/snap_qwen_compute/qwen_compute_n46t_s0
# Source = the files next to this script (clock_contract_l0..l7.json, from the signed records); each is verified against the lib sha256
# of the target view before it is written (new file, then mv). Hosts: intel1 epyc2 epyc7 epyc8 epyc9 epyc10.
T=$1; HERE=$(cd "$(dirname "$0")" && pwd)
case "$T" in *n46_s0*|"") echo "REFUSE: pinned tree or empty (give the N46T tree root)"; exit 2;; esac
for h in intel1 epyc2 epyc7 epyc8 epyc9 epyc10; do
 for l in 0 1 2 3 4 5 6 7; do
  d=$T/physical/die_plan/qwen_compute/qcviews_1111/views/qfd_qc_su_lane_w_l$l
  scp -q -o ControlPath=none $HERE/clock_contract_l$l.json $h:$d/clock_contract.json.new 2>/dev/null || { ssh -n -o ControlPath=none $h "chmod u+w $d" && scp -q -o ControlPath=none $HERE/clock_contract_l$l.json $h:$d/clock_contract.json.new; }
  ssh -n -o ControlPath=none $h "python3 -I -c \"import json,hashlib,sys;c=json.load(open(\\\"$d/clock_contract.json.new\\\"));h=hashlib.sha256(open(\\\"$d/qfd_qc_su_lane_w_l${l}_tt.lib\\\",\\\"rb\\\").read()).hexdigest();sys.exit(0 if c[\\\"view_lib_sha256\\\"]==h else 3)\" && mv -f $d/clock_contract.json.new $d/clock_contract.json && chmod 444 $d/clock_contract.json && echo \"$h l$l ok\" || { echo \"$h l$l BAD lib sha\"; mv -f $d/clock_contract.json.new /tmp/clock_contract_l$l.BAD 2>/dev/null; }; chmod a-w $d"
 done
done
