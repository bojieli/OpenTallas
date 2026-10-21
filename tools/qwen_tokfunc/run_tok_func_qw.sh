#!/bin/bash
# TOK-FUNC-QW (owner 10-21: "first run the functional token delivery on the current RTL, and rerun the proven script once the
# die is closed").  ONE command for the Qwen ROM token pass:
#     assemble RTL -> stage it on the fleet -> run every stage bench (per-layer DV families x36 layers, ROM tile matvec,
#     compute<->KV D2D 35 layers, TP8 all-reduce, 4-user OVL pair + MU context link, LM head, KV attention u1/u4)
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
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=${OT_REPO:-/home/ubuntu/OpenTallas}
ASM=$(python3 -c "import json;print(json.load(open('$HERE/asm_recipe.json'))['commit'])")
RUNROOT=/srv/opentallas-scratch/claude/tokfunc-qw-1021
HOSTS=${TOKFUNC_HOSTS:-"ot-gold1 ot-gold2"}     # staging targets only (ot-run picks among hosts that have RUNROOT)
STAGES=""; DIE=""; COLLECT=0; NOWAIT=0; OUT=""
while [ $# -gt 0 ]; do case $1 in
  --asm) ASM=$2; shift;; --die-netlist) DIE=$2; shift;; --stages) STAGES=$2; shift;; --runroot) RUNROOT=$2; shift;;
  --collect-only) COLLECT=1;; --no-wait) NOWAIT=1;; --out) OUT=$2; shift;; *) echo "unknown $1"; exit 2;; esac; shift; done
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
    nohup /home/ubuntu/bin/ot-run --mem "$mem" --dir "$RUNROOT" -- \
      bash "$RUNROOT/tokfunc_tools/$script" "$RUNROOT" ${DIE:+--die-netlist "$DIE"} > "$OUT/logs/$s.otrun.log" 2>&1 &
    echo "$s launched (pid $!, mem $mem GB) log $OUT/logs/$s.otrun.log"
  done
  [ $NOWAIT = 1 ] && { echo "launched; collect later: $0 --asm $ASM --collect-only ${DIE:+--die-netlist $DIE}"; exit 0; }
  wait
fi

# 3. collect RUNROOT/<stage>/ (result.json + logs named in it) from the host with the NEWEST result.json
for s in ${STAGES//,/ }; do
  best=""; bt=0
  for h in $HOSTS; do
    t=$(ssh "$h" "stat -c %Y $RUNROOT/$s/result.json 2>/dev/null") || true
    [ -n "$t" ] && [ "$t" -gt "$bt" ] && { bt=$t; best=$h; }
  done
  if [ -n "$best" ]; then
    rm -rf "$OUT/results/$s"; mkdir -p "$OUT/results/$s"
    ssh "$best" "cd $RUNROOT/$s && tar -c result.json \$(python3 -c \"import json;r=json.load(open('result.json'));print(' '.join(p for p in r.get('logs',[])+list((r.get('ages') or {}).values())))\") 2>/dev/null" |
      tar -x -C "$OUT/results/$s"; echo "$s collected from $best"
  else echo "$s: NO result.json yet"; fi
done
# 4. compose the token (1u) and the 4-user frame; report vs the MODEL 4,403.2 / 11,750.6 tok/s
python3 -I "$HERE/compose_tokfunc.py" --results "$OUT/results" --out "$OUT/compose" --asm "$ASM" --grade "$GRADE" --repo "$REPO"
echo "report: $OUT/compose/report.json"
