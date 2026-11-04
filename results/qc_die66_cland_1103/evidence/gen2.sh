#!/bin/bash
# DIE-QC-66/CLK CLAND proof: gen.py phys (wave src, wave recipe) for item T on base and fixed plans
set -u
D=/srv/opentallas-scratch2/claude/die-qc-66-cland; SRC=/srv/opentallas-scratch2/claude/wt/kw-fix-4-fl-qc
I=/srv/opentallas-scratch2/claude/codex-qc-wave-1131/kit-wave/qwen_compute/d90b109213c6949da87b330ef143d96bbe937934/items
SIDE=/srv/opentallas-scratch2/claude/wt/codex-qc-event-1131/results/qc_die57_1031/bind/sidecar.json
BASE=/srv/opentallas-scratch2/claude/wt/codex-qc-event-1131/physical/die_plan/qwen_compute/plan_of_record/plan_qc52_ucie1103.json
FIX=$D/mirror/physical/die_plan/qwen_compute/plan_of_record/plan_qc52_ucie1103_cland.json
T=$1; shift
cd $SRC
for v in "$@"; do P=$BASE; [ $v = fix ] && P=$FIX; O=$D/gen_$v/$T; rm -rf $O; mkdir -p $O
  python3 tools/die_plan/gen.py phys $P --out $O --types $T --rtl-root $SRC --kit-rtl $T=$I/$T/rtl/kit_rtl.f --hold-ff-margin 0 --clock-landing $SIDE > $O.log 2>&1
  echo "GEN $v $T rc=$? $(date)" >> $D/gen_status; done
