#!/bin/bash
# TOK-DS-8 (10-27): slice-cut kits for the per-layer replays rebuilt from the CURRENT source tree by script (RULING TOK-DS-7:
# fc30-era kits are not the current die).  Die topology = the compile vehicle's die tree (the same die.v the layer
# programmes are compiled against, so the replay schedule and the cut agree); RTL = the worktree HEAD with the 877
# selected-source manifest (physical/die_plan/s81/bind/asbuilt_b178_coll.json: files + prefer + defines), i.e. the same
# selected source set compile.sh hands the compiler (OT_S81_SELECTED_*).  Steps:
#   1. die.v from <tree>/results/arch/s81_dv_1016/bind9/die.v.gz
#   2. strict tools/die_port_bind.py on that die.v over <wt>/rtl + manifest files/prefer + defines -> port_bind.json
#   3. tools/s81_dv/tokfunc/prep_cuts.sh HEAD die.v port_bind.json <tree land_plan> <out> (cut + tb + dv_rtl_kit at HEAD)
# Usage: prep_cuts_current.sh <worktree> <tree> <out> [cut ...]
set -u
W=$(realpath $1); T=$(realpath $2); O=$(realpath -m $3); shift 3
M=physical/die_plan/s81/bind/asbuilt_b178_coll.json
mkdir -p $O/bind
cd $W
git rev-parse HEAD > $O/source_sha.txt; git status --short -- tools rtl physical/die_plan/s81 > $O/source_dirty.txt
[ -f $O/die.v ] || gunzip -c $T/results/arch/s81_dv_1016/bind9/die.v.gz > $O/die.v
LP=$T/results/arch/s81_dv_1016/landing/p4l/land_plan.json
sha256sum $O/die.v $LP $W/$M > $O/inputs.sha256
ARGS=$(python3 - "$W/$M" <<'PY'
import json, sys, os
d = json.load(open(sys.argv[1]))
a = []
for f in d['files']:
    if f.endswith('_bb.v') or f.endswith('s81_asb_models.sv'):
        continue          # black boxes / as-built lib stubs are not RTL; dv_rtl_kit resolves real macros + cell models
    a += ['--rtl-file', f]
for f in d['prefer']:
    a += ['--prefer', f]
for x in d['defines']:
    a += ['--define', x]
print(' '.join(a))
PY
)
if [ ! -f $O/bind/port_bind.json ]; then
  python3 tools/die_port_bind.py $O/die.v --top dv_die --rtl-root rtl $ARGS \
    --prefer-list tools/s81_dv/frame_bench.f --prefer-list tools/s81_dv/svc_rs/rs_files.sh --ref-tile-prefer \
    --allow-model ot_s81_pma_bm --allow-model ot_s81_hbm3e_dev_bm --out $O/bind/port_bind.json > $O/bind/port_bind.log 2>&1
  echo "PORT_BIND rc $? $(tail -n 1 $O/bind/port_bind.log | cut -c1-300)"
fi
[ -f $O/bind/port_bind.json ] || exit 2
bash tools/s81_dv/tokfunc/prep_cuts.sh HEAD $O/die.v $O/bind/port_bind.json $LP $O "$@"
echo PREP_DONE
