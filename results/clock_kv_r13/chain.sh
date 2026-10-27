#!/bin/bash
# CLOCK-KV-R13 chain: headmirror kit from hm_r12 (die_trial kit) -> r13 clock (upstream L6-L9 + split drops) combo GRT
# --merge-shields TT -> ndr016 RCX -> tree STA TT/FF -> per-level spreads.  Same steps for the up4 control (no split drops).
set -e
R=/srv/opentallas-scratch2/claude/clock-kv-r13-1026; T=/srv/opentallas-scratch2/claude/wt/clock-kv-r13/tools/die_plan
export PYTHONPATH=/srv/opentallas-scratch2/claude/codex-kv-mesh-1026/pylib:$T
cd $R; echo "start $(date -Is) host $(hostname)"
if [ ! -f kit/grt/route.v ]; then python3 $T/die_trial.py kit /srv/opentallas-scratch2/claude/clock-kv-r12-1026/pd/hm_r12.json --out kit > kit.log 2>&1; fi
ls kit/abstracts | wc -l; ls -la kit/grt
for O in ${BUILDS:-r13 up4}; do
  python3 $T/die_clock_mesh.py combo $R/$O --kit $R/kit --plan /srv/opentallas-scratch2/claude/clock-kv-r12-1026/pd/hm_r12.json --merge-shields > $O/combo_gen.log 2>&1
  tail -2 $O/combo_gen.log
  ( CORNERS=TT MEM=40 bash $R/$O/run_combo.sh; grep -H EXIT $R/$O/combo_TT.log; grep -H -E "OT_SHIELD_MERGE|overflow|Total" $R/$O/combo_TT.log | tail -8 ) &
done; wait
for O in ${BUILDS:-r13 up4}; do
  X=$R/$O/rcx; mkdir -p $X; python3 $T/rcx_kv.py $R/$O $X $T > $X/gen.log 2>&1 || { tail $X/gen.log; exit 1; }
  docker run --rm --name r13-kv-rcx-$O-$$ --cpus 16 --memory 64g --memory-swap 64g -v "$R/$O:/b:ro" -v "$X:/out" openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 16 -exit /out/rcx.tcl > /out/rcx.log 2>&1; rc=\$?; chown -R $(id -u):$(id -g) /out; exit \$rc"
  python3 /srv/opentallas-scratch2/claude/codex-kv-clock-2001/tools/spef_connectivity.py $X/rcx.spef $X/connectivity.json | tail -1
  for C in TT FF; do
   docker run --rm --name r13-kv-sta-$O-$C-$$ --cpus 4 --memory 24g -e CORNER=$C -e BASIS=rcx -e LIBDIR=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM -v "$X:/out" openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -threads 4 -exit /out/sta.tcl > /out/sta_\$CORNER.log 2>&1; rc=\$?; chown -R $(id -u):$(id -g) /out; exit \$rc" &
  done; wait
  python3 /srv/opentallas-scratch2/claude/clock-kv-r11-1026/lvl.py $X/tree_TT_rcx.txt $X/tree_FF_rcx.txt
done
echo "CHAIN_DONE $(date -Is)"
