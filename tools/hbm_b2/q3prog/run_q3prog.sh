#!/bin/bash
# usage (inside ot-run, from the repo worktree root): tools/hbm_b2/q3prog/run_q3prog.sh <OUT> <legacy|sync>
# Stage A q3 programme bench in TRACE FORM on the actual five-core q3 producer assembly (one engine per model).
# Rule 3: refuses a dirty tracked tree; every input repo-relative at HEAD; __q3sync copies + the adopted assembly are
# regenerated at HEAD into <OUT>/<mode>/ (never read from older scratch).
set -u
OUT=$1; MODE=$2; P=${P:-6}; WARMAT=${WARMAT:-150}; HOLD=${HOLD:-64}
WT=$(git rev-parse --show-toplevel) || exit 2
cd "$WT"
[ -n "$(git status --porcelain --untracked-files=no)" ] && { echo "DIRTY tracked tree: refuse"; exit 2; }
V=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
ASM=rtl/hbm_accel/cores_split/ot_hfd_coll_q3_hard_v8x/ot_hbm_q3_producer_native.sv
CEN=results/token_pass/path_hbm_1713/q3sync/census.json
D=$OUT/$MODE; rm -rf "$D"; mkdir -p "$D"
git rev-parse HEAD > "$D/source_commit.txt"
sha256sum -c tools/hbm_b2/q3sync/q3_producer_native.sha256 > "$D/asm_sha.log" 2>&1 || { echo "ASM SHA FAIL"; exit 2; }
# programme: actual argmax_rows compiler, q3 profile VM_RT81 ROWS256 NPT3, argmax_m_tp192_pr contract
python3 -I tools/hbm_coll_static/argmax_rows.py "$D/prog" --P $P --vm-rt 81 --rows 256 --npt 3 --start-reg --arg-pr-source \
  > "$D/compile.log" 2>&1 || { cat "$D/compile.log"; echo "Q3PROG compile FAIL"; exit 2; }
NR=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['parents']['d0q0']['rows'])" "$D/prog/manifest.json")
mac=$(python3 -c "
import json;c=json.load(open('$CEN'));s=[]
[s.append(m) for k in c['core_filelists'] for m in c['core_filelists'][k]['macros'] if m not in s]
print(' '.join(s))")
if [ $MODE = sync ]; then
  python3 -I tools/hbm_b2/q3sync/q3_sync_profile.py --root . --files tools/hbm_b2/q3sync/q3b.files --out "$D/gen" \
     --census "$D/census_regen.json" > "$D/gen.log" 2>&1 || { echo "GEN FAIL"; exit 2; }
  python3 -I tools/hbm_b2/q3sync/q3_assembly_sync.py --asm $ASM --census $CEN --gen "$D/gen" \
     --out "$D/ot_hbm_q3_producer_native__q3sync.sv" --report "$D/asm_sync.json" > "$D/asm_sync.log" 2>&1 \
     || { cat "$D/asm_sync.log"; exit 2; }
  files=$(python3 -c "
import json;c=json.load(open('$CEN'));s=[]
[s.append(f) for k in c['core_filelists'] for f in c['core_filelists'][k]['files'] if f not in s]
print(' '.join('$D/gen/'+f for f in s))")
  files="$D/ot_hbm_q3_producer_native__q3sync.sv $files"; DEF=+define+DUT=ot_hbm_q3_producer_native__q3sync
else
  files=$(python3 -c "
import json;c=json.load(open('$CEN'));fl=set(f for k in c['core_filelists'] for f in c['core_filelists'][k]['files'])
s=[]
[s.append(e['source']) for e in c['emitted'] if e['emitted'] in fl and e['source'] not in s]
print(' '.join(s))")
  files="$ASM $files"; DEF=+define+DUT=ot_hbm_q3_producer_native
fi
log=$D/sim.log
echo "# $(date) host=$(hostname) commit=$(git rev-parse HEAD) mode=$MODE P=$P NR=$NR WARMAT=$WARMAT HOLD=$HOLD" > $log
echo "# files: $(echo $files $mac | wc -w)" >> $log
/usr/bin/time -v $V --binary --timing -O1 -j ${JOBS:-8} -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-MULTIDRIVEN \
 -Wno-TIMESCALEMOD -Wno-INITIALDLY -Wno-MULTITOP -Wno-BLKSEQ -Wno-WIDTHCONCAT $DEF --top-module tb_q3prog_trace \
 --Mdir $D/obj -o tb tools/hbm_b2/q3prog/tb_q3prog_trace.sv $files $mac > $D/build.log 2>&1
brc=$?; echo "# build rc=$brc $(grep 'Maximum resident' $D/build.log)" >> $log
[ $brc = 0 ] || { tail -30 $D/build.log; echo "Q3PROG build FAIL"; exit 2; }
/usr/bin/time -v $D/obj/tb +DIR=$D/prog +P=$P +NR=$NR +WARMAT=$WARMAT +HOLD=$HOLD +TRACE=$D/trace.txt >> $log 2>&1
echo "# sim rc=$? $(date)" >> $log
[ -n "${KEEP_OBJ:-}" ] || rm -rf $D/obj
grep -E "^Q3PROG|^FAULT|^ARG_|^ADDR_|Maximum resident" $log
