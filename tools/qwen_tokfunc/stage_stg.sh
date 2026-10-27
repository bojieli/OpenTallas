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
# TOK-FUNC2-QW 10-21 options (all optional; defaults = the original run):
#   --stage NAME      work dir RUNROOT/NAME (default stg); RUNROOT/stg/{fx_in,fx_res} stay the shared inputs
#   --fx DIR          reuse finished per-layer fixtures (DIR/L<n>_*.npz + L<n>_fixture.json) instead of regenerating
#   --reuse-objs DIR  no Verilator build: DIR/{rel,pos,mut} are finished obj_n12 dirs of the SAME source (+ overlay);
#                     calibrations and every run are redone on them (current per-K LAST-K bench protocol)
#   --overlay DIR     copy DIR/<repo path> over the tree before the builds (RTL fix branches not yet in the assembly)
set -u
# Internal pure provenance operations. They never compile or run a simulator.
# A manifest is made prospectively, then bound to the finished binary; an old
# executable cannot acquire a source identity merely by being copied beside RTL.
if [ "${1:-}" = --object-manifest ]; then
  shift
  python3 - "$@" <<'PY'
import hashlib, importlib, json, os, re, shlex, sys
from pathlib import Path

mode, root_arg, snapshot_arg, overlay_arg, *rest = sys.argv[1:]
root, snapshot = Path(root_arg).resolve(), Path(snapshot_arg)
def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''): h.update(part)
    return h.hexdigest()
def fail(why): raise SystemExit('STG OBJECT IDENTITY REFUSED: ' + why)
def current():
    sys.path.insert(0, str(root / 'rtl/test/qwen_dv'))
    b2 = importlib.import_module('dv_bench2')
    flags = shlex.split(os.environ.get('DV_LOWER_VFLAGS', ''))
    names = list(b2.SRCS2)
    if '-GSU_LT=1' in flags: names += list(b2.XSRCS)
    names += ['rtl/test/qwen_dv/main2.cpp', 'rtl/test/qwen_dv/dv_lower_bench.py',
              'tools/qwen_layerbench/dv_lower.py',
              'rtl/test/qwen_dv/dv_bench2.py', 'rtl/test/qwen_dv/dv_bench.py']
    pending, inputs = [Path(n) if Path(n).is_absolute() else root / n for n in names], {}
    while pending:
        path = pending.pop().resolve()
        key = str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        if key in inputs: continue
        if not path.is_file(): fail('missing build input ' + key)
        inputs[key] = sha(path)
        if path.suffix in ('.sv', '.v', '.svh', '.vh'):
            for inc in re.findall(r'`include\s+"([^"\n]+)"', path.read_text()):
                choices = [path.parent / inc, root / inc]
                target = next((p for p in choices if p.is_file()), None)
                if target is None: fail('unresolved include ' + inc + ' from ' + key)
                pending.append(target)
    overlay = Path(overlay_arg) if overlay_arg else None
    return dict(schema='opentallas.stg_build_source.v1', inputs=inputs, flags=flags,
                environment={k: v for k, v in sorted(os.environ.items())
                             if k.startswith('DV2_') or k in ('CXX', 'CXXFLAGS', 'CPPFLAGS', 'LDFLAGS')},
                overlay_sha256=sha(overlay) if overlay and overlay.is_file() else None)
def read_snapshot():
    if not snapshot.is_file(): fail('prospective build-source snapshot unavailable')
    saved = json.loads(snapshot.read_text())
    if saved != current(): fail('current build source/flags/overlay differ from prospective snapshot')
    return saved
if mode == 'snapshot':
    if snapshot.exists(): fail('prospective snapshot already exists; preserve it')
    snapshot.write_text(json.dumps(current(), sort_keys=True, indent=1) + '\n')
elif mode in ('bind', 'verify'):
    obj = Path(rest[0]); exe = obj / 'Vtb'; manifest = obj / 'build_identity.json'
    saved = read_snapshot()
    if not exe.is_file() or not os.access(exe, os.X_OK): fail('finished Vtb unavailable')
    identity = dict(schema='opentallas.stg_object_identity.v1', binary_sha256=sha(exe), source=saved)
    if mode == 'bind':
        if manifest.exists(): fail('binary identity already exists; preserve it')
        manifest.write_text(json.dumps(identity, sort_keys=True, indent=1) + '\n')
    elif not manifest.is_file(): fail('binary build_identity.json unavailable; executable presence is insufficient')
    elif json.loads(manifest.read_text()) != identity: fail('binary/source/flags/overlay identity mismatch')
else: fail('unknown provenance operation ' + mode)
print('STG OBJECT IDENTITY ' + mode.upper() + ' OK')
PY
  exit $?
fi
RUNROOT=$(readlink -f "$1"); shift
NET=""; LAYERS=$(seq -s ' ' 0 35); PAR=24; STAGE=stg; FXRE=""; REUSE=""; OVL=""
while [ $# -gt 0 ]; do case "$1" in
  --stage) STAGE=$2; shift 2;;
  --fx) FXRE=$(readlink -f "$2"); shift 2;;
  --reuse-objs) REUSE=$(readlink -f "$2"); shift 2;;
  --overlay) OVL=$(readlink -f "$2"); shift 2;;
  --die-netlist) NET=$(readlink -f "$2"); shift 2;;
  --layers) LAYERS=$2; shift 2;;
  --par) PAR=$2; shift 2;;
  *) echo "bad arg $1"; exit 2;; esac; done
[ -n "$NET" ] && { echo "--die-netlist: not wired yet (see header); RTL-functional run only"; exit 4; }
SRC=$RUNROOT/src; S=$RUNROOT/$STAGE; FXIN=$RUNROOT/stg/fx_in; FX=$S/fx; T=$S/tree; HERE=$(dirname "$(readlink -f "$0")")
[ ! -e "$T" ] || { echo "stage tree already exists: preserve $T and select a fresh --stage"; exit 5; }
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
verilator --version | grep -q '5.050' || { echo "need Verilator 5.050"; exit 2; }
# fixture inputs: $FXIN/.complete marks a finished staging copy (the builds start meanwhile; fixtures wait <= 3 h for it)
[ -d "$FXIN" ] || { echo "missing $FXIN (P8191 TP4 gold + img_p1)"; exit 2; }
[ -d "$RUNROOT/stg/fx_res/results" ] || { echo "missing $RUNROOT/stg/fx_res/results (bench data files from c0f8097f3)"; exit 2; }
# tree = REAL copy of src rtl/tools/configs (the benches resolve ROOT = Path(__file__).resolve().parents[2], so a symlink
# overlay would point back into src) + physical symlinked + the committed bench data files they read (ROOT/results/*)
rm -rf "$T"; mkdir -p "$T" "$FX"
for d in rtl tools configs; do [ -e "$SRC/$d" ] && cp -r "$SRC/$d" "$T/"; done
[ -e "$SRC/physical" ] && cp -as "$SRC/physical" "$T/"
cp -r "$RUNROOT/stg/fx_res/results" "$T/"
if [ -n "$OVL" ]; then (cd "$OVL" && find . -type f | sort | xargs sha256sum) > "$S/overlay.sha256"; cp -r "$OVL/." "$T/"; fi
if [ -n "$FXRE" ]; then for f in "$FXRE"/L*_fixture.json "$FXRE"/L*.npz "$FXRE"/L*.log; do ln -sfn "$f" "$FX/"; done; fi
cd "$T" || exit 3
# Current LAST-K station consumes all running k blocks. Repair the benchmark cut
# contract/lifecycle without changing RTL; preserve this overlay in the receipt.
if ! grep -q 'producer_words_per_cluster_per_round' rtl/test/qwen_dv/dv_lower_mat_bench.py; then
  patch -p1 < "$HERE/stg_mat_running.patch" > "$S/mat_contract_patch.log" 2>&1 || exit 3
fi
sha256sum tools/qwen_layerbench/dv_lower_mat.py rtl/test/qwen_dv/dv_lower_mat_bench.py > "$S/mat_contract_sources.sha256"
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
export -f fixtures; export FX FXIN T REUSE

declare -A VF=( [rel]='-GMU_NU=4 -GSU_LT=1' [pos]='-GMU_NU=4 -GSU_LT=1 -GARF=1 -GRP=1' [mut]='-GMU_NU=4 -GSU_LT=1 -GARF=2 -GRP=2' )
VB=$T/rtl/test/qwen_dv/dv_lower_vec_bench.py; MB=$T/rtl/test/qwen_dv/dv_lower_mat_bench.py
# Validate every requested object before any fixture calculation or simulation.
# Do not backfill a manifest for historical objects whose build inputs were not
# recorded prospectively. Existing admitted runs and their evidence stay intact.
for c in rel pos mut; do
  DV_LOWER_VFLAGS="${VF[$c]}" bash "$HERE/stage_stg.sh" --object-manifest snapshot "$T" "$S/$c.build_source.json" "$S/overlay.sha256" > "$S/$c.identity.log" 2>&1 || { cat "$S/$c.identity.log"; exit 5; }
  if [ -n "$REUSE" ]; then
    DV_LOWER_VFLAGS="${VF[$c]}" bash "$HERE/stage_stg.sh" --object-manifest verify "$T" "$S/$c.build_source.json" "$S/overlay.sha256" "$REUSE/$c" >> "$S/$c.identity.log" 2>&1 || { cat "$S/$c.identity.log"; exit 5; }
  fi
done
( for L in $LAYERS; do echo $L; done | xargs -P 9 -I{} bash -c 'fixtures {}' > $S/fixtures.log 2>&1 ) &
FXPID=$!
build_cfg() {   # build + slice / vec / stn calibrate on this build
  local c=$1 W=$S/$1; export DV_LOWER_VFLAGS="${VF[$1]}"
  rm -rf $W; mkdir -p $W/build $W/cal_mat $W/runs; echo "$DV_LOWER_VFLAGS" > $W/vflags.txt
  local b0=$(date +%s)
  if [ -n "$REUSE" ]; then [ -x "$REUSE/$c/Vtb" ] || { echo "$c: no $REUSE/$c/Vtb"; return 2; }
    ln -sfn "$REUSE/$c" $W/build/obj_n12; sha256sum "$REUSE/$c/Vtb" > $W/reused_vtb.sha256; fi
  python3 $T/rtl/test/qwen_dv/dv_lower_bench.py --work $W/build --calibrate > $W/build/slice_calibrate.out 2>&1
  local slice_rc=$?; echo "rc=$slice_rc" >> $W/build/slice_calibrate.out
  echo "build+slice_calibrate $(( $(date +%s) - b0 )) s" > $W/timing.txt
  [ -x $W/build/obj_n12/Vtb ] || { echo "$c BUILD FAILED"; tail -30 $W/build/build.log; return 2; }
  if [ -z "$REUSE" ]; then
    bash "$HERE/stage_stg.sh" --object-manifest bind "$T" "$S/$c.build_source.json" "$S/overlay.sha256" "$W/build/obj_n12" >> "$S/$c.identity.log" 2>&1 || { cat "$S/$c.identity.log"; return 5; }
  else
    bash "$HERE/stage_stg.sh" --object-manifest verify "$T" "$S/$c.build_source.json" "$S/overlay.sha256" "$W/build/obj_n12" >> "$S/$c.identity.log" 2>&1 || { cat "$S/$c.identity.log"; return 5; }
  fi
  python3 $VB --work $W/build --mode calibrate > $W/build/calibrate.out 2>&1
  local vec_rc=$?; echo "rc=$vec_rc" >> $W/build/calibrate.out
  ln -sfn $W/build/obj_n12 $W/cal_mat/obj_n12
  python3 $MB --work $W/cal_mat --calibrate > $W/cal_mat/calibrate.out 2>&1
  local mat_rc=$?; echo "rc=$mat_rc" >> $W/cal_mat/calibrate.out
  # Mutant calibration is retained as diagnostic, not credited as a causal
  # negative. Required nominal calibration failure must block all stage cases.
  if [ "$c" != mut ] && { [ "$slice_rc" != 0 ] || [ "$vec_rc" != 0 ] || [ "$mat_rc" != 0 ]; }; then
    echo "$c REQUIRED CALIBRATION FAILED slice=$slice_rc vec=$vec_rc mat=$mat_rc"
    return 6
  fi
  echo "calibrate done $(( $(date +%s) - b0 )) s" >> $W/timing.txt; echo "$c built"
}
declare -A BP
for c in rel pos mut; do build_cfg $c > $S/build_$c.log 2>&1 & BP[$c]=$!; done
BUILD_FAILED=0
for c in rel pos mut; do wait ${BP[$c]}; rc=$?; echo "build $c rc=$rc"; [ "$rc" = 0 ] || BUILD_FAILED=1; done
wait $FXPID; echo "fixtures done"; cat $S/fixtures.log
[ "$BUILD_FAILED" = 0 ] || { echo 'STG refused: build/object identity failed; no stage cases run'; exit 5; }
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
python3 $HERE/stage_stg.collect.py $RUNROOT $STAGE
