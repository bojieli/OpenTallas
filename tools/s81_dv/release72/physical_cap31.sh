#!/bin/bash
# remote (STW-S81d-GEN): cap31 VARIANT physical from its staged GEN receipt, probe-first, in three phases:
#   PHASE=pre   : receipt -> rep600 (max_wire 600 + ctrl_corner 600 fix 0b6f74584 + s81_cc_segment_um 100) -> place + die clock (MEMG 64)
#   PHASE=probe : repeaters + initial GRT (congestion_iterations 0, read-only probe map out/grt_congestion.rpt) in the same run dir (MEMG 160)
#   PHASE=full  : run.tcl -> congestion_iterations 30; repeaters + full GRT + hold ECO + STA TT/FF + IR (run_all_post_clock.sh)
set -uo pipefail
V=${1:?variant}; PHASE=${PHASE:?pre|probe|full}
I=/home/ubuntu/ot-scratch/claude/stw-s81d-cap31
MW=${MW:-600}; R=${OT_SCRATCH:-/srv/opentallas-scratch}/claude/stw-s81d-cap31-$V-rep$MW-physical
if [ "$PHASE" = pre ]; then
  mkdir -p "$(dirname "$R")"; mkdir "$R" || exit 2
  tar -xzf "$I/cap31_${V}_receipt.tar.gz" -C "$R" || exit 3
  sed -i "s/max_wire_um 160 /max_wire_um $MW /" "$R/case/die_repeaters_step.tcl"; grep -q "max_wire_um $MW " "$R/case/die_repeaters_step.tcl" || exit 3
  if [ "$MW" != 160 ]; then test -s "$I/ctrl_corner_fix.tcl" || exit 3; cp "$I/ctrl_corner_fix.tcl" "$R/case/ctrl_corner.tcl"; fi
  grep -q "congestion_iterations 0 " "$R/case/run.tcl" || exit 3
  sha256sum "$R/case/die_repeaters_step.tcl" "$R/case/ctrl_corner.tcl" "$R/case/run.tcl" > "$R/rep.sha256"
  printf 'cap31 %s (STW-S81d-GEN, cap30 chain + g9f_cap31_plan.py) host %s %s DIECLK_ITERS=%s MW=%s\n' "$V" "$(hostname)" "$(date -Is)" "${DIECLK_ITERS:-6}" "$MW" > "$R/physical.identity"
  echo "$(hostname):$R" > "$I/cap31_${V}_rundir"
  python3 - "$R/case" <<'PHASE_PY' || exit 3
from pathlib import Path
import sys
p=Path(sys.argv[1]);s=(p/'run_inner.sh').read_text(); marker='/usr/bin/time -v openroad -threads $N -no_init -exit /work/run.tcl'
assert s.count(marker)==1
pre,grt=s.split(marker)
(p/'run_pre_grt.sh').write_text(pre+'echo OT_PRE_GRT_DONE\n')
(p/'run_grt_inner.sh').write_text('#!/bin/bash\nsource /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1\nN=${CPUS:-16}\n'+marker+grt)
s=(p/'run.sh').read_text(); assert s.count('/work/run_inner.sh')==1
(p/'run_placeclock.sh').write_text(s.replace('/work/run_inner.sh','/work/run_pre_grt.sh'))
(p/'run_grt.sh').write_text(s.replace('/work/run_inner.sh','/work/run_grt_inner.sh'))
s=(p/'run_all.sh').read_text();assert s.count('bash $D/run.sh')==1
(p/'run_all_post_clock.sh').write_text(s.replace('bash $D/run.sh','bash $D/run_grt.sh'))
PHASE_PY
  DIECLK_ITERS=${DIECLK_ITERS:-6} CPUS=16 MEMG=64 bash "$R/case/run_placeclock.sh" > "$R/phase_pre.log" 2>&1
  rc=$?; grep -q DIE_CLOCK_BUILD_DONE "$R/case/out/dieclk.log" 2>/dev/null || rc=${rc/#0/9}
  echo "PHASE_PRE_RC $rc $(date -Is)" > "$R/phase_pre.exit"; exit "$rc"
fi
test -s "$R/case/out/dieclk/clock.odb" || exit 4
if [ "$PHASE" = probe ]; then
  CPUS=16 MEMG=160 bash "$R/case/run_grt.sh" > "$R/phase_probe.log" 2>&1
  rc=$?; mkdir -p "$R/probe0"; cp "$R/case/out/run.log" "$R/probe0/probe.log"; cp "$R/case/out/grt_congestion.rpt" "$R/probe0/grt_congestion_probe.rpt"
  echo "PHASE_PROBE_RC $rc $(date -Is)" > "$R/phase_probe.exit"; exit "$rc"
fi
if [ "$PHASE" = full ]; then
  sed -i "s/-congestion_iterations 0 /-congestion_iterations 30 /" "$R/case/run.tcl"; grep -q -- "-congestion_iterations 30 " "$R/case/run.tcl" || exit 3
  rm -f "$R/case/out/grt.odb" "$R/case/run_all.done"
  CPUS=16 MEMG_GRT=160 MEMG_HOLD=96 MEMG_STA=64 bash "$R/case/run_all_post_clock.sh" > "$R/chain.log" 2>&1
  rc=$?; echo "PHYSICAL_RC $rc $(date -Is)" > "$R/physical.exit"; exit "$rc"
fi
exit 5
