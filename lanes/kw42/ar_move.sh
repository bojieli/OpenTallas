#!/bin/bash
# KW-FIX-42 COORD 02:3x: move S81 re-sign inputs to epyc7 (same paths), sha-check the routed DB, resubmit pinned to epyc7
set -u
U=$1; SRC=$2; KIT=$3; DB=$4; TOOLS=$5; SHA=$6
L=~/coord/lanes/kw42/$U.copy.log; exec >>$L 2>&1; echo "START $(date)"
ssh -n -o ControlPath=none $SRC "rsync -aHR $KIT $TOOLS epyc7:/" ; echo "rsync rc $?"
S=$(ssh -n -o ControlPath=none epyc7 "sha256sum $DB | cut -d\" \" -f1")
O=$(ssh -n -o ControlPath=none $SRC "sha256sum $DB | cut -d\" \" -f1")
echo "sha epyc7 $S src $O want $SHA"
[ "$S" = "$SHA" ] && [ "$O" = "$SHA" ] || { echo "SHA MISMATCH, not submitted"; exit 2; }
echo "SHA OK $(date)"
