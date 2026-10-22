#!/bin/bash
# TOK-FUNC-QW (owner 10-21: "first run the functional token delivery on the current RTL, and rerun the proven script once the
# die is closed").  ONE command for the Qwen ROM token pass:
#     assemble RTL -> stage it on the fleet -> run every stage bench (per-layer DV families x36 layers, ROM tile matvec,
#     compute<->KV D2D 35 layers, TP8 all-reduce, 4-user OVL pair + MU context link, LM head, KV attention u1/u4,
#     chain = the real token's 36 layers through the KV attention RTL + compute-die hand-off checks (TOK-FUNC3-QW))
#     -> collect -> compose 1-user token and 4-user frame -> report vs the 4,403 / 11,751 tok/s MODEL.
#
# usage (from a checkout of this branch, local coordinator host; heavy work goes to the fleet via ot-run):
#   run_tok_func_qw.sh [--asm SHA] [--die-netlist COMPUTE_GEN_OUT[:KV_GEN_OUT]] [--stages a,b,..] [--runroot DIR]
#                      [--collect-only] [--no-wait] [--out DIR]
#   --asm          RTL assembly commit (default: asm_recipe.json "commit" = claude/tok-func-qw-asm-1021). At die closure pass
#                  the frozen main/release commit.
#   --die-netlist  die-netlist mode (TOK.FREEZE hook): every stage that has a netlist form takes the GEN out/case dirs
#                  (compute die.v/rom_bind.vh/die.v.params.json; KV die.v) instead of source RTL; grade "die-netlist".
#   --collect-only skip assembly/launch; fetch RUNROOT/<stage>/result.json from the fleet hosts and compose.
#   --no-wait      launch and exit (re-run later with --collect-only).
#   --stage-dir S=D collect stage S from RUNROOT/D (or from the absolute dir D on any staged/KV host) instead of
#                  RUNROOT/S (repeatable; e.g. stg=stg3 = the STG rerun on the
#                  LAST-K tail-fixed rebuild, stage_stg.sh --stage stg3 --overlay ...)
#   --stage-local S=DIR  take stage S from a committed local receipt dir (DIR/result.json; e.g. the terminal KV-MU7 job4b
#                  kv=results/rtl/tokfunc2_qw_1021/kv) instead of a fleet RUNROOT
#   --kvroot DIR   (TOK-FUNC3-QW) root of stage "chain" on the host that holds the KV attention vehicle binary (default
#                  /srv/opentallas-scratch2/claude/tokfunc3-qw-1021, only on ot-epyc5 -> ot-run --dir selects it by data
#                  locality).  Before launch the stg fixtures + P8191 KV windows are relayed there from the stg host.
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=${OT_REPO:-/home/ubuntu/OpenTallas}
ASM=$(python3 -c "import json;print(json.load(open('$HERE/asm_recipe.json'))['commit'])")
RUNROOT=/srv/opentallas-scratch/claude/tokfunc-qw-1021
HOSTS=${TOKFUNC_HOSTS:-"ot-gold1 ot-gold2"}     # staging targets only (ot-run picks among hosts that have RUNROOT)
KVROOT=/srv/opentallas-scratch2/claude/tokfunc3-qw-1021; KVHOSTS=${TOKFUNC_KVHOSTS:-ot-epyc5}   # stage chain
STAGES=""; DIE=""; COLLECT=0; NOWAIT=0; OUT=""; declare -A SDIR=() SLOCAL=()
while [ $# -gt 0 ]; do case $1 in
  --asm) ASM=$2; shift;; --die-netlist) DIE=$2; shift;; --stages) STAGES=$2; shift;; --runroot) RUNROOT=$2; shift;;
  --collect-only) COLLECT=1;; --no-wait) NOWAIT=1;; --out) OUT=$2; shift;;
  --stage-dir) SDIR[${2%%=*}]=${2#*=}; shift;; --kvroot) KVROOT=$2; shift;; --stage-local) SLOCAL[${2%%=*}]=${2#*=}; shift;; *) echo "unknown $1"; exit 2;; esac; shift; done
ASM=$(git -C "$REPO" rev-parse --short=9 "$ASM^{commit}") || { echo "asm commit not found"; exit 2; }
GRADE="RTL-functional (source assembly)"; [ -n "$DIE" ] && GRADE="die-netlist"
OUT=${OUT:-$HOME/scratch/tokfunc-qw-1021/run_$ASM${DIE:+_die}}
mkdir -p "$OUT/results" "$OUT/logs"
# stage table: name script mem_GB  (stage scripts take: RUNROOT [--die-netlist DIR])
TABLE=$HERE/stages.tsv
[ -z "$STAGES" ] && STAGES=$(awk '!/^#/ && NF>=3 {print $1}' "$TABLE" | paste -sd,)
echo "TOK-FUNC-QW asm=$ASM grade='$GRADE' stages=$STAGES runroot=$RUNROOT out=$OUT"

if [ $COLLECT = 0 ]; then
  # 1. assemble + stage: git archive of the assembly (RTL, tools, configs, memory macro models) + this tool dir
  T=$OUT/src_$ASM.tar
  [ -s "$T" ] || git -C "$REPO" archive -o "$T" "$ASM" rtl tools configs physical/asap7_memory_macros || exit 3
  for h in $HOSTS; do
    ssh "$h" "test -f $RUNROOT/src_$ASM/ASM_COMMIT" || {
      ssh "$h" "mkdir -p $RUNROOT/src_$ASM" && ssh "$h" "tar -x -C $RUNROOT/src_$ASM" < "$T" &&
      ssh "$h" "echo $ASM > $RUNROOT/src_$ASM/ASM_COMMIT" || { echo "staging on $h failed"; exit 3; }; }
    ssh "$h" "ln -sfn src_$ASM $RUNROOT/src && mkdir -p $RUNROOT/tokfunc_tools" &&
      tar -C "$HERE" -c . | ssh "$h" "tar -x -C $RUNROOT/tokfunc_tools" || exit 3
    [ -n "$DIE" ] && ssh "$h" "echo '$DIE' > $RUNROOT/DIE_NETLIST"
  done
  # 2. launch every stage on the fleet (unpinned; RUNROOT exists only on the staged hosts)
  for s in ${STAGES//,/ }; do
    read -r name script mem <<<"$(awk -v s="$s" '$1==s {print $1, $2, $3}' "$TABLE")"
    [ -z "${name:-}" ] && { echo "no stage $s in $TABLE"; exit 2; }
    STAGE_DIE=${DIE%%:*}
    [ "$s" = kv ] || [ "$s" = chain ] && STAGE_DIE=${DIE#*:}
    SROOT=$RUNROOT
    if [ "$s" = chain ]; then
      # inputs: the stg fixtures (values the compute-die RTL produced bit-exact) + P8191 windows, relayed from the stg host
      SROOT=$KVROOT; fxh=""
      for h in $HOSTS; do ssh "$h" "test -f $RUNROOT/stg/fx/L35_fixture.json" && { fxh=$h; break; }; done
      [ -n "$fxh" ] || { echo "chain: no host with $RUNROOT/stg/fx"; exit 3; }
      for h in $KVHOSTS; do
        ssh "$h" "test -f $KVROOT/chain/in/.complete" || {
          ssh "$h" "mkdir -p $KVROOT/chain/in/fx $KVROOT/chain/in/p8191" &&
          ssh "$fxh" "cd $RUNROOT/stg/fx && tar -ch L*_fixture.json L*.npz" | ssh "$h" "tar -x -C $KVROOT/chain/in/fx" &&
          ssh "$fxh" "cd $RUNROOT/stg/fx_in/P8191 && tar -ch x_preload.hex embedding_row.json L*_die0_x.hex kv_pre/L*_die0.npy" |
            ssh "$h" "tar -x -C $KVROOT/chain/in/p8191" && ssh "$h" "touch $KVROOT/chain/in/.complete" || { echo "chain relay to $h failed"; exit 3; }; }
        ssh "$h" "mkdir -p $KVROOT/tokfunc_tools" && tar -C "$HERE" -c . | ssh "$h" "tar -x -C $KVROOT/tokfunc_tools" || exit 3
      done
    fi
    nohup /home/ubuntu/bin/ot-run --mem "$mem" --threads 48 --dir "$SROOT" -- \
      bash "$SROOT/tokfunc_tools/$script" "$SROOT" ${STAGE_DIE:+--die-netlist "$STAGE_DIE"} > "$OUT/logs/$s.otrun.log" 2>&1 &
    echo "$s launched (pid $!, mem $mem GB) log $OUT/logs/$s.otrun.log"
  done
  [ $NOWAIT = 1 ] && { echo "launched; collect later: $0 --asm $ASM --collect-only ${DIE:+--die-netlist $DIE}"; exit 0; }
  wait
fi

# 3. collect RUNROOT/<stage>/ (result.json + logs named in it) from the host with the NEWEST result.json
install_collection() {
  local incoming=$1 stage=$2 prior
  if [ -e "$OUT/results/$stage" ]; then
    prior=$(mktemp -d "$OUT/results/.prior_${stage}.XXXXXX") || return 1
    rmdir "$prior" && mv "$OUT/results/$stage" "$prior" || return 1
  fi
  mv "$incoming" "$OUT/results/$stage"
}
for s in ${STAGES//,/ }; do
  if [ -n "${SLOCAL[$s]:-}" ]; then        # a committed terminal stage receipt (e.g. kv=results/rtl/tokfunc2_qw_1021/kv)
    incoming=$(mktemp -d "$OUT/results/.collect_${s}.XXXXXX"); cp -a "${SLOCAL[$s]}/." "$incoming/" &&
      install_collection "$incoming" "$s" && echo "$s from committed ${SLOCAL[$s]}" || exit 4
    continue
  fi
  best=""; bt=0; sd=${SDIR[$s]:-$s}; CH=$HOSTS; RR=$RUNROOT
  [ "$s" = chain ] && { CH=$KVHOSTS; RR=$KVROOT; }
  # --stage-dir S=/ABS/DIR: collect from an absolute run dir (e.g. the preserved KV-MU7 job4b out dir on the KV host)
  case $sd in /*) CH="$HOSTS $KVHOSTS"; RR=$(dirname "$sd"); sd=$(basename "$sd");; esac
  for h in $CH; do
    t=$(ssh "$h" "stat -c %Y $RR/$sd/result.json 2>/dev/null") || true
    [ -n "$t" ] && [ "$t" -gt "$bt" ] && { bt=$t; best=$h; }
  done
  if [ -n "$best" ]; then
    incoming=$(mktemp -d "$OUT/results/.collect_${s}.XXXXXX")
    files="$OUT/logs/$s.files"
    if ssh "$best" "cat '$RR/$sd/result.json'" > "$incoming/remote_result.raw.json" &&
      ssh "$best" "python3 - '$RR/$sd'" < "$HERE/collect_files.py" > "$files" &&
      ssh "$best" "cd '$RR/$sd' && tar -h --null -c -T -" < "$files" | tar -x -C "$incoming"; then
      # Never fill missing evidence from an earlier collection. Preserve the
      # previous folder and install this fetch as one fresh local snapshot.
      install_collection "$incoming" "$s" || exit 4
      echo "$s collected from $best:$RR/$sd"
      if [ "$s" = stg ]; then
        python3 "$HERE/normalize_collected_stg.py" "$OUT/results/$s" "$ASM" "$REPO" || exit 4
      fi
    else
      python3 "$HERE/normalize_collected_stg.py" --unavailable "$incoming" "$s" 'required remote evidence could not be collected' || exit 4
      install_collection "$incoming" "$s" || exit 4
      echo "$s: collection INCOMPLETE"
    fi
  else
    incoming=$(mktemp -d "$OUT/results/.collect_${s}.XXXXXX")
    python3 "$HERE/normalize_collected_stg.py" --unavailable "$incoming" "$s" 'no remote result.json available' || exit 4
    install_collection "$incoming" "$s" || exit 4
    echo "$s: no remote result; INCOMPLETE"
  fi
done
# 4. compose the token (1u) and the 4-user frame; report vs the MODEL 4,403.2 / 11,750.6 tok/s
python3 -I "$HERE/compose_tokfunc.py" --results "$OUT/results" --out "$OUT/compose" --asm "$ASM" --grade "$GRADE" --repo "$REPO"
echo "report: $OUT/compose/report.json"
