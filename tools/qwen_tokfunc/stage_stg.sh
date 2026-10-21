#!/bin/bash
# TOK-FUNC-QW stage "stg" (10-21): the compute-die DV layer families PER LAYER on the RTL-only SOURCE ASSEMBLY
# (RUNROOT/src), Verilator 5.050, 12-slice tb_qfd_dv2 chain (qfd_dv_slice2 + redstn2 + scalar2 + vm + stream + amax_mu).
#
#   stage_stg.sh RUNROOT [--die-netlist DIR] [--layers "0 1 ... 35"] [--par N]
#
# Bench = the existing TOKSIM-QW/STG bench (results/token_pass/measured_qwen_1019/stg/run.sh + run_mat.sh):
#   rtl/test/qwen_dv/dv_lower_bench.py (build + slice calibrate), dv_lower_vec_bench.py (resid / qk / silu),
#   dv_lower_mat_bench.py (qkv / gu / od / lm / emb), real operands from QW-REALSTG tools/qwen_layerbench/dv_layer_fixture.py.
# Fixtures: generated HERE for every layer from the TP4 36-layer ISA golden (RUNROOT/stg/fx_in/P8191 = tokpass-qwen-1018
#   fx/gold/tp4/P8191, stage images RUNROOT/stg/fx_in/img_p1/L<n>-d<die>); each layer is re-executed on all 4 TP4 dies and
#   must reproduce the recorded layer X and K/V rows bit-exact (fail-closed) before its operands are cut (TP8 die 0).
# Builds (one each, Verilator 5.050, ~50-70 GB):
#   rel : -GMU_NU=4 -GSU_LT=1                       release slice kit parameters
#   pos : -GMU_NU=4 -GSU_LT=1 -GARF=1 -GRP=1        + QW-LAYERGAP slice2 AR framer + RoPE row (the next slice kit)
#   mut : -GMU_NU=4 -GSU_LT=1 -GARF=2 -GRP=2        layergap RTL mutants (must FAIL)
# Runs:
#   rel : per layer L resid1 resid2 qk silu qkv gu od (real operands, ISA-gold cross-check); lm, emb; 8 mutants (L0);
#         layergap "off" set (ARF/RP absent: od/lm --arf and qk --rope rx must FAIL, od plain PASS)
#   pos : per layer L resid1 resid2 silu qkv gu, qk --rope rx, od --arf; lm --arf, emb; layergap "pos" set
#         (od/lm --arf PASS, qk --rope rx PASS, qk --rope rx --mutant rope_late FAIL, qk stream PASS)
#   mut : layergap "mut" set (od --arf FAIL, qk --rope rx FAIL)
# Ends with RUNROOT/stg/result.json (stage_stg.collect.py): per-family span_cycles per layer per cfg; vec_ages / stn_ages.
#
# --die-netlist DIR (closure hook): DIR/qfd_dv_slice2_w.v + DIR/qfd_dv_slice2_e.v = the GEN die carve of the slice row
#   tiles (gate-level, with DIR/cells.v the ASAP7 cell models).  tb_qfd_dv2 FACE=1/2 instantiates the face wrappers; the
#   hook adds those files to the Verilator build in place of rtl/qwen_dv/qfd_dv_slice2*.sv (DV2_EXTRA_SRCS) and grades
#   die-netlist.  NOT wired yet (no carve exists at c0f8097f3): with --die-netlist the script refuses (exit 4).
set -u
RUNROOT=$(readlink -f "$1"); shift
NET=""; LAYERS=$(seq -s ' ' 0 35); PAR=24
while [ $# -gt 0 ]; do case "$1" in
  --die-netlist) NET=$(readlink -f "$2"); shift 2;;
  --layers) LAYERS=$2; shift 2;;
  --par) PAR=$2; shift 2;;
  *) echo "bad arg $1"; exit 2;; esac; done
[ -n "$NET" ] && { echo "--die-netlist: not wired yet (see header); RTL-functional run only"; exit 4; }
SRC=$RUNROOT/src; S=$RUNROOT/stg; FXIN=$S/fx_in; FX=$S/fx; T=$S/tree; HERE=$(dirname "$(readlink -f "$0")")
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version | grep -q '5.050' || { echo "need Verilator 5.050"; exit 2; }
# fixture inputs: $FXIN/.complete marks a finished staging copy (the builds start meanwhile; fixtures wait <= 3 h for it)
[ -d "$FXIN" ] || { echo "missing $FXIN (P8191 TP4 gold + img_p1)"; exit 2; }
[ -d "$S/fx_res/results" ] || { echo "missing $S/fx_res/results (bench data files from c0f8097f3)"; exit 2; }
# tree = REAL copy of src rtl/tools/configs (the benches resolve ROOT = Path(__file__).resolve().parents[2], so a symlink
# overlay would point back into src) + physical symlinked + the committed bench data files they read (ROOT/results/*)
rm -rf "$T"; mkdir -p "$T" "$FX"
for d in rtl tools configs; do [ -e "$SRC/$d" ] && cp -r "$SRC/$d" "$T/"; done
[ -e "$SRC/physical" ] && cp -as "$SRC/physical" "$T/"
cp -r "$S/fx_res/results" "$T/"
cd "$T" || exit 3
t0=$(date +%s)

# ---------------------------------------------------------------- 1. fixtures (background) + 3 builds (background)
fixtures() {
  local L=$1
  [ -s "$FX/L${L}_fixture.json" ] && { echo "L$L cached"; return 0; }
  local i=0; while [ ! -e "$FXIN/.complete" ] && [ $i -lt 180 ]; do sleep 60; i=$((i+1)); done
  env QWEN_O4_TP=4 QWEN_O4_GROUPS=6144 HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8 OT_GOLD_ROOT=$T \
    python3 $T/tools/qwen_layerbench/dv_layer_fixture.py tp4 --img "$FXIN/img_p1/L{layer}-d{die}" \
    --realmem $FXIN/P8191 --layer $L --out $FX > $FX/L$L.log 2>&1
  echo "rc=$?" >> $FX/L$L.log; echo "L$L $(tail -2 $FX/L$L.log | head -1 | cut -c1-120)"
}
export -f fixtures; export FX FXIN T
( for L in $LAYERS; do echo $L; done | xargs -P 9 -I{} bash -c 'fixtures {}' > $S/fixtures.log 2>&1 ) &
FXPID=$!

declare -A VF=( [rel]='-GMU_NU=4 -GSU_LT=1' [pos]='-GMU_NU=4 -GSU_LT=1 -GARF=1 -GRP=1' [mut]='-GMU_NU=4 -GSU_LT=1 -GARF=2 -GRP=2' )
VB=$T/rtl/test/qwen_dv/dv_lower_vec_bench.py; MB=$T/rtl/test/qwen_dv/dv_lower_mat_bench.py
build_cfg() {   # build + slice / vec / stn calibrate on this build
  local c=$1 W=$S/$1; export DV_LOWER_VFLAGS="${VF[$1]}"
  rm -rf $W; mkdir -p $W/build $W/cal_mat $W/runs; echo "$DV_LOWER_VFLAGS" > $W/vflags.txt
  local b0=$(date +%s)
  python3 $T/rtl/test/qwen_dv/dv_lower_bench.py --work $W/build --calibrate > $W/build/slice_calibrate.out 2>&1; echo "rc=$?" >> $W/build/slice_calibrate.out
  echo "build+slice_calibrate $(( $(date +%s) - b0 )) s" > $W/timing.txt
  [ -x $W/build/obj_n12/Vtb ] || { echo "$c BUILD FAILED"; tail -30 $W/build/build.log; return 2; }
  python3 $VB --work $W/build --mode calibrate > $W/build/calibrate.out 2>&1; echo "rc=$?" >> $W/build/calibrate.out
  ln -sfn $W/build/obj_n12 $W/cal_mat/obj_n12
  python3 $MB --work $W/cal_mat --calibrate > $W/cal_mat/calibrate.out 2>&1; echo "rc=$?" >> $W/cal_mat/calibrate.out
  echo "calibrate done $(( $(date +%s) - b0 )) s" >> $W/timing.txt; echo "$c built"
}
declare -A BP
for c in rel pos mut; do build_cfg $c > $S/build_$c.log 2>&1 & BP[$c]=$!; done
for c in rel pos mut; do wait ${BP[$c]}; echo "build $c rc=$?"; done
wait $FXPID; echo "fixtures done"; cat $S/fixtures.log
echo "fixtures+builds $(( $(date +%s) - t0 )) s" > $S/timing.txt

# ---------------------------------------------------------------- 2. runs (one list, all cfgs, -P PAR)
job() {   # cfg name bench-args...
  local c=$1 name=$2; shift 2; local W=$S/$c d=$S/$c/runs/$name; mkdir -p $d; ln -sfn $W/build/obj_n12 $d/obj_n12
  DV_LOWER_VFLAGS="$(cat $W/vflags.txt)" python3 "$@" --work $d > $d/bench.out 2>&1; echo "rc=$?" >> $d/bench.out
  echo "$c $name $(head -1 $d/bench.out | cut -c1-160)"
}
export -f job; export S
ok_fx() { [ -s "$FX/L${1}_fixture.json" ]; }
{
for c in rel pos; do
  W=$S/$c; [ -x $W/build/obj_n12/Vtb ] || continue
  VA=$W/build/vec_ages.json; SA=$W/cal_mat/stn_ages.json
  if [ $c = rel ]; then QK=""; OD=""; LM=""; else QK="--rope rx"; OD="--arf"; LM="--arf"; fi
  for L in $LAYERS; do ok_fx $L || continue
    for m in resid1:resid resid2:resid silu:silu; do n=${m%%:*}; md=${m##*:}
      echo "$c L${L}_$n $VB --mode $md --ages $VA --fixture $FX/L${L}_$n.npz"; done
    echo "$c L${L}_qk $VB --mode qk $QK --ages $VA --fixture $FX/L${L}_qk.npz"
    for r in qkv gu; do echo "$c L${L}_$r $MB --run $r --ages $SA --fixture $FX/L${L}_mat_$r.npz"; done
    echo "$c L${L}_od $MB --run od $OD --ages $SA --fixture $FX/L${L}_mat_od.npz"
  done
  echo "$c lm $MB --run lm $LM --ages $SA"
  echo "$c emb $MB --run emb --ages $SA"
  if [ $c = rel ]; then
    echo "rel MUT_L0_resid1_arwin $VB --mode resid --mutant arwin --ages $VA --fixture $FX/L0_resid1.npz"
    echo "rel MUT_L0_qk_ropesign $VB --mode qk --mutant ropesign --ages $VA --fixture $FX/L0_qk.npz"
    echo "rel MUT_L0_silu_nor $VB --mode silu --mutant nor --ages $VA --fixture $FX/L0_silu.npz"
    echo "rel MUT_L0_qkv_sbase1 $MB --run qkv --mutant sbase1 --ages $SA --fixture $FX/L0_mat_qkv.npz"
    echo "rel MUT_L0_gu_sbase1 $MB --run gu --mutant sbase1 --ages $SA --fixture $FX/L0_mat_gu.npz"
    echo "rel MUT_L0_od_nostagger $MB --run od --mutant nostagger --ages $SA --fixture $FX/L0_mat_od.npz"
    echo "rel MUT_lm_amax_local $MB --run lm --mutant amax_local --ages $SA"
    echo "rel MUT_emb_emb_late $MB --run emb --mutant emb_late --ages $SA"
    echo "rel LGOFF_od_arf $MB --run od --arf --ages $SA"
    echo "rel LGOFF_lm_arf $MB --run lm --arf --ages $SA"
    echo "rel LGOFF_qk_roperx $VB --mode qk --rope rx --ages $VA"
    echo "rel LGOFF_od $MB --run od --ages $SA"
  else
    echo "pos LGPOS_od_arf $MB --run od --arf --ages $SA"
    echo "pos LGPOS_lm_arf $MB --run lm --arf --ages $SA"
    echo "pos LGPOS_qk_roperx $VB --mode qk --rope rx --ages $VA"
    echo "pos LGPOS_qk_roperx_ropelate $VB --mode qk --rope rx --mutant rope_late --ages $VA"
    echo "pos LGPOS_qk_stream $VB --mode qk --ages $VA"
  fi
done
W=$S/mut
if [ -x $W/build/obj_n12/Vtb ]; then
  echo "mut LGMUT_od_arf $MB --run od --arf --ages $W/cal_mat/stn_ages.json"
  echo "mut LGMUT_qk_roperx $VB --mode qk --rope rx --ages $W/build/vec_ages.json"
fi
} > $S/runlist.txt
xargs -P $PAR -L 1 bash -c 'job "$@"' _ < $S/runlist.txt > $S/runs.log 2>&1
echo "total $(( $(date +%s) - t0 )) s" >> $S/timing.txt
# Preserve completed objects for incremental recovery and collection.
for c in rel pos mut; do sha256sum $S/$c/build/obj_n12/Vtb 2>/dev/null > $S/$c/vtb.sha256; done
python3 $HERE/stage_stg.collect.py $RUNROOT
