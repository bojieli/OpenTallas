#!/bin/bash
# DIE-HBM-5 (runs on localhost, light): wait for the kit's GRT inputs on HOST, stop only this probe's adopted chain, launch GRT via the intel2 ot-run head pinned to HOST.
# usage: grt_now_local.sh SSHHOST OTHOST PROBE_DIR PGREP_REGEX
S=$1; H=$2; D=$3; PAT=$4; X="ssh -o ControlPath=none $S"
until $X "[ -s $D/kit/run_grt.sh ] && [ -s $D/kit/grt/grt.tcl ] && [ -s $D/kit/grt/obs.tcl ] && [ -s $D/kit/psm/psm.tcl ]"; do sleep 30; done
sleep 20; echo "inputs ready $(date)"
$X "for p in \$(pgrep -f '$PAT'); do echo kill script \$p; kill \$p; done; for p in \$(pgrep -f 'die_trial.py kit .* --out $D/kit'); do echo kill kit \$p; kill \$p; done"
sleep 5
ssh -o ControlPath=none intel2 ~/.local/bin/ot-run --mem 100 --threads 16 --hosts $H --dir $D/kit --priority die -- env MEM=96 CPUS=16 bash $D/kit/run_grt.sh
echo "GRT rc=$? $(date)"; $X "grep -E '^Total|EXIT' $D/kit/grt/grt.log | tail -4"; echo ALL_DONE
