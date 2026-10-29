#!/bin/bash
# TOK-QC-3: strict bind (+verify +portbind) of the ONE-QC RTL. usage: bind.sh OUT RECIPE PLAN [nover]
# elaboration reused from TOK-QC-2 bind2 (symlinks), same as TOK-QC-2 bind5
set -u; O=$1; A=$2; P=$3; mkdir -p $O
S=/srv/opentallas-scratch2/claude/tok-qc-2-1028/bind2
for f in asbuilt.json asbuilt.ys asbuilt_lib_stubs.sv asbuilt_sources.json bind_elab_keep.sv die_r56.v provenance_elab.json shim_qfd_dv_slice2.sv; do
  [ -e $O/$f ] || ln -s $S/$f $O/$f; done
python3 tools/die_plan/bind.py bind $P --asbuilt $A --out $O --strict > $O/bind.log 2>&1; echo "bind rc $? $(date)" >> $O/status
[ "${4:-}" = nover ] && exit 0
python3 tools/die_plan/bind.py verify $P --asbuilt $A --out $O --mem 64 > $O/verify.log 2>&1; echo "verify rc $? $(date)" >> $O/status
python3 tools/die_plan/bind.py portbind $P --asbuilt $A --out $O > $O/portbind.log 2>&1; echo "portbind rc $? $(date)" >> $O/status
