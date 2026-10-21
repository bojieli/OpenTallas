#!/bin/bash
# QW-GEN3 phase 3: ship this die's netlist relay table + recompiled schedule, launch the physical chain.  usage: phase3.sh TAG
set -u
T=${1:?tag}; R=/srv/opentallas-scratch/claude/mu-die-qw/$T; P=/home/ubuntu/scratch/qw-gen3/$T/p2
[ -s $P/relay_stages_netlist.json ] && [ -s $P/compiled_L1/manifest.json ] || { echo "phase2 outputs missing"; exit 2; }
SCH=$(ls $P/compiled_L1/relay_schedule/compute_compiled.json* | head -1)
ssh -o ControlPath=none ot-epyc6 "set -e; cd $R; mkdir -p compiled_L1" || exit 3
scp -q -o ControlPath=none $P/relay_stages_netlist.json ot-epyc6:$R/out/case/relay_stages.json || exit 4
tar -C $P/compiled_L1 -cf - . | ssh -o ControlPath=none ot-epyc6 "tar -C $R/compiled_L1 -xf -" || exit 5
cat > /tmp/qwgen3_run_$T.sh <<EOS
#!/bin/bash
S=$R; echo "\$(date '+%F %T %Z') chain start (phase 3: netlist relay table + schedule recompiled on THIS die)" >> \$S/PILOT.log
OT_RELAY_SCHEDULE=\$S/compiled_L1/relay_schedule/$(basename $SCH) bash \$S/chain.sh; rc=\$?
echo "\$(date '+%F %T %Z') chain rc=\$rc" >> \$S/PILOT.log; exit \$rc
EOS
scp -q -o ControlPath=none /tmp/qwgen3_run_$T.sh ot-epyc6:$R/phase3_run.sh
exec /home/ubuntu/bin/ot-run --priority die --mem 200 --dir /srv/opentallas-scratch/claude/mu-die-qw -- bash $R/phase3_run.sh
