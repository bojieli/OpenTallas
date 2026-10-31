#!/bin/bash
# flat.sh KIT OUT.tsv : yosys flatten of kit RTL -> "master module cell" per SRAM macro instance
K=$(realpath $1); O=$2
T=$(mktemp -d /srv/opentallas-scratch2/claude/die-hbm-49/macros/tmp.XXXX)
TOP=$(sed -n "s/^export DESIGN_NAME = //p" $K/config.mk)
VF=$(sed -n "s/^export VERILOG_FILES = //p" $K/config.mk)
{
for l in $K/macros/*_tt.lib; do echo "read_liberty -lib /work/macros/$(basename $l)"; done
echo "read_verilog -sv -DSYNTHESIS -I/work/rtl $VF"
echo "hierarchy -top $TOP"; echo proc; echo flatten
for l in $K/macros/*_tt.lib; do m=$(basename $l _tt.lib); echo "tee -o /ys/$m.lst select -list t:$m"; done
} > $T/flat.ys
docker run --rm --memory 16g --user $(id -u) -v $K:/work:ro -v $T:/ys openroad/orfs:asap7lock bash -c "export PATH=/OpenROAD-flow-scripts/tools/install/yosys/bin:\$PATH; yosys -s /ys/flat.ys -l /ys/flat.log >/dev/null 2>&1; echo rc=\$?"
: > $O
for f in $T/*.lst; do m=$(basename $f .lst); grep / $f | sed "s#^#$m #; s#/# #" >> $O; done
wc -l $O; rm -rf $T
