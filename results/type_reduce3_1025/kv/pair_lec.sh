#!/bin/bash
# TR3-KV-LEC 2026-10-25: kit-level LEC of one odd head strap master (netlist, strap_bsel tied) against one old constant
# variant kit (gold = that kit's RTL).  Run on epyc1 from the branch worktree:
#   pair_lec.sh SCRATCH MASTER VARIANT BSEL
# SCRATCH/kits/m_e<M>/*/run/results/asap7/*/base/1_2_yosys.v = master netlist; SCRATCH/kits/old_e<N>/* = old kit.
set -euo pipefail
S=$1; M=$2; N=$3; B=$4
HERE=$(cd "$(dirname "$0")" && pwd); REPO=$(cd "$HERE/../../.." && pwd)
MK=$(ls -d $S/kits/m_e$M/kv3_head_eighth_e${M}__*); OK=$(ls -d $S/kits/old_e$N/kv3_head_eighth_e${N}__*)
NET=$(ls $MK/run/results/asap7/*/base/1_2_yosys.v)
P=$S/lec/m${M}_vs_e${N}; rm -rf $P; mkdir -p $P
# gold kit = copy of the old variant kit (no run data); gate netlist inside it (lec.py --image mounts the kit)
rsync -a --exclude run --exclude lec $OK/ $P/kit/
mkdir -p $P/kit/gate
python3 $HERE/tie_strap.py $NET $P/kit/gate/master_e${M}_tied_${B}.v --variant $N --bsel $B
sha256sum $NET $P/kit/gate/master_e${M}_tied_${B}.v $OK/rtl/kv3_head_eighth_e$N.sv > $P/inputs.sha256
nohup ~/.local/bin/ot-run --mem 24 --threads 2 --dir $P --stage $P -- \
  python3 -I $REPO/tools/die_plan/lec.py $P/kit --netlist $P/kit/gate/master_e${M}_tied_${B}.v --out $P/out --mem 24 \
  > $P/lec_run.log 2>&1 &
sleep 15; grep -h "admitted" $P/lec_run.log || tail -3 $P/lec_run.log
