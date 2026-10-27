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
# TOK-DS-9: <tree> = tools/s81_dv/tokfunc/mk_vehicle_current.sh output (tree_b178 = main die_b178.v), not tree_fc31.
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
    if f.endswith('_bb.v'):
        continue          # macro black boxes are not RTL; dv_rtl_kit resolves the real macro + cell models
    # TOK-DS-9: s81_asb_models.sv is NOT a stub: it holds the as-built frame band compositions (col_h*_l4_lp_asb_{x,nx}
    # = r0/r1/r2 plan kits + s81b_fint seams) and s81b_ckrst that the current die top (die_b178.v) instantiates
    a += ['--rtl-file', f]
for f in d['prefer']:
    a += ['--prefer', f]
for x in d['defines']:
    a += ['--define', x]
print(' '.join(a))
PY
)
if [ ! -f $O/bind/port_bind.json ]; then
  # TOK-DS-10 (10-27): the manifest's own files/prefer decide every module, exactly as the compiler and bind.py select
  # (layer_prog/slice_source.manifest_selection).  The fc30-era --prefer-list frame_bench.f / rs_files.sh +
  # --ref-tile-prefer were appended AFTER the manifest files, i.e. ranked above them, so main rtl/ copies beat the
  # selected portfix178 sources: dsdv_bk_sel_vmtx (idx/dsdv_idx_l20s.sv, no tpn_i/tpn_o/tps_o) and dsdv_idx_rg3(+_nq)
  # (no fault) -> TOK-DS-9's 5 port_not_in_rtl + 560 undriven bits (idxn_tp__bk_sel__s_7{N,S}_LP 552, f_irg_* 8).
  python3 tools/die_port_bind.py $O/die.v --top dv_die --rtl-root rtl $ARGS \
    --allow-model ot_s81_pma_bm --allow-model ot_s81_hbm3e_dev_bm --out $O/bind/port_bind.json > $O/bind/port_bind.log 2>&1
  echo "PORT_BIND rc $? $(tail -n 1 $O/bind/port_bind.log | cut -c1-300)"
fi
[ -f $O/bind/port_bind.json ] || exit 2
bash tools/s81_dv/tokfunc/prep_cuts.sh HEAD $O/die.v $O/bind/port_bind.json $LP $O "$@"
echo PREP_DONE
