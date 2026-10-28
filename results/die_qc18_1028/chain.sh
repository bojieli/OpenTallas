#!/bin/bash
# chain.sh D damp tag0 tag1 tag2 ...: successive stepi corr steps
R=/srv/opentallas-scratch2/claude/die-qc18-1028; D=$1; dm=$2; shift 2; p=$1; shift
for g in "$@"; do $R/stepi.sh $D $p $g --damp $dm || exit 1; p=$g; done
