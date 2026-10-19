#!/usr/bin/env bash
# HBM-BW (10-19): fleet driver of the controller-only HBM boundary bench (hbm_bw_unit.py, tb_hbm_bw_pc4.sv).
#   run_hbm_bw_unit.sh OUTROOT "PATTERN[:flags] ..."     flags: mr, mrkey0, gaps, L<n> (layers), S<n> (seed)
# Syncs the working tree's bench files to OUTROOT/src on $HOST (ot-epyc5) and runs every case in ONE ot-run job.
set -uo pipefail
OUT=$1; CASES=$2; HOST=${HOST:-ot-epyc5}
WT=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
cd "$WT" && tar -c tools/hbm_layer_vehicle/hbm_bw_unit.py $(python3 -c "import sys;sys.path.insert(0,'tools/hbm_layer_vehicle');import hbm_bw_unit as h;print(' '.join(h.FILES))") \
  | ssh "$HOST" "mkdir -p $OUT/src $OUT/work && tar -x -C $OUT/src" || exit 2
J="cd $OUT/src && export VERILATOR=\$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator; "
for c in $CASES; do
  p=${c%%:*}; fl=""; [ "$c" != "$p" ] && fl=${c#*:}
  args="--pattern $p"
  for f in ${fl//,/ }; do case $f in mr) args+=" --mr";; mrkey0) args+=" --mrkey0";; gaps) args+=" --gaps";; L*) args+=" --layers ${f#L}";; S*) args+=" --seed ${f#S}";; esac; done
  J+="python3 tools/hbm_layer_vehicle/hbm_bw_unit.py run --work $OUT/work $args; "
done
/home/ubuntu/bin/ot-run --mem ${MEM:-16} --threads 8 --dir "$OUT" -- bash -c "$J"
