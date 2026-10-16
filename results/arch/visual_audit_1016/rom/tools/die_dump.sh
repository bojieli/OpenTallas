#!/bin/bash
# die_dump.sh HOST ODB TAG OUTDIR : layout_dump.tcl with OT_LAYOUT_LINKS=1 on a die odb (read-only), json back
H=$1; ODB=$2; T=$3; O=$4; mkdir -p $O
SSH="ssh -o ConnectTimeout=15 -o ControlPath=none"
W=/srv/opentallas-scratch/claude/visrom/$T
$SSH $H "mkdir -p $W" && scp -q -o ControlPath=none /home/ubuntu/wt/vis-rom-1016/tools/ref_tile/layout_dump.tcl $H:$W/
$SSH $H bash -s "$ODB" "$W" "$T" <<'EOS'
ODB=$1; W=$2; T=$3; D=$(dirname $ODB); B=$(basename $ODB)
printf 'read_db /work/%s\nsource /ld/layout_dump.tcl\nexit\n' "$B" > $W/ld.tcl
docker run --rm --name visrom_$T -e OT_LAYOUT_LINKS=1 -e OT_LAYOUT_BINS=128 -e OT_LAYOUT_OUT=/ld/dump.json -e OT_LAYOUT_TOP=$T -v $D:/work:ro -v $W:/ld openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /ld/ld.tcl > $W/ld.log 2>&1
tail -2 $W/ld.log; gzip -f $W/dump.json
EOS
scp -q -o ControlPath=none $H:$W/dump.json.gz $O/ && gunzip -f $O/dump.json.gz && $SSH $H "rm -rf $W"
ls -la $O
