#!/bin/bash
# S81-LEAF-FLOOR-2: private bind trees.  Hardlinks for read-only bulk; REAL copies for everything this lane edits.
set -eu
W=/srv/opentallas-scratch2/claude/s87bind; O=/srv/opentallas-scratch2/claude/s81-leaf-floor-2; WT=/srv/opentallas-scratch2/claude/wt/s81-leaf-floor-2
TM=$O/bsrc_main_lfcs; TR=$O/bsrc_r12ng_lfcs
test ! -e $TM && test ! -e $TR
mkdir -p $TM $TR
for d in $(ls -A $W/bsrc4_main); do
  if [ "$d" = rtl ] || [ "$d" = tools ]; then cp -a $W/bsrc4_main/$d $TM/; else cp -al $W/bsrc4_main/$d $TM/; fi
done
for d in $(ls -A $W/bsrc4_r12ng); do
  if [ "$d" = rtl ] || [ "$d" = tools ]; then cp -a $W/bsrc4_r12ng/$d $TR/; else cp -al $W/bsrc4_r12ng/$d $TR/; fi
done
cd $WT
for f in $(git diff --name-only HEAD~0 -- rtl) ; do cp --remove-destination $WT/$f $TM/$f; cp --remove-destination $WT/$f $TR/$f; done
for t in leaf_cs_depth.py stage_lfcs_netlist.py kit_istations.py; do cp --remove-destination $WT/tools/die_plan/$t $TR/tools/die_plan/$t; cp --remove-destination $WT/tools/die_plan/$t $TM/tools/die_plan/$t; done
echo TREES_DONE $(date)
