#!/bin/bash
# regclass.sh TAG TOP files... : port_regclass of every port of a split piece (PATH-HBM/Q3 10-25)
TAG=$1; TOP=$2; shift 2
D=/srv/opentallas-scratch2/claude/path-hbm/ne2/ls; WT=/srv/opentallas-scratch2/claude/path-hbm/ne2/src
cd $D; export YOSYS=$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys; export PORTCLASS_DEFINES="SYNTHESIS OT_COLL_ISSUER256_NATIVE32"
/usr/bin/time -v python3 $WT/tools/hbm_split/port_regclass.py rc_$TAG.json $TOP "" "*" "$@" > rc_$TAG.log 2>&1
echo "regclass $TAG rc=$?"
