#!/bin/bash
# TOK-FUNC3-QW stage "chain" (10-21): the REAL token (TP4 ISA golden prompt, position 8191) chained through all 36 layers
# on the KV-die attention RTL, plus the cross-layer hand-off check of the compute-die stg evidence.
#
#   stage_chain.sh KVROOT [--kv-obj DIR] [--die-netlist DIR] [--par N]
#
# Inputs (staged by run_tok_func_qw.sh "prep chain" from the stg RUNROOT; nothing generated from a model here):
#   KVROOT/chain/in/fx      the stg stage fixtures L<n>_{resid1,resid2,qk,silu,mat_qkv,mat_gu,mat_od}.npz + L<n>_fixture.json
#                           (every value the compute-die RTL produced bit-exact in stage stg)
#   KVROOT/chain/in/p8191   x_preload.hex, L<nn>_die0_x.hex (recorded layer outputs), kv_pre/L<n>_die0.npy (KV windows)
# Binary: the KV attention vehicle tb_kvattn_rel built by stage kv (release vehicle, KV-MU7 job4b 0e597ed1c, source-bound
#   receipt results/rtl/tokfunc2_qw_1021/kv: sha 5d0e1cab...).  Reused, never rebuilt (a 590 GB hierarchical build).
#   --kv-obj DIR = that build's out dir (DIR/obj/Vtb_kvattn_rel, DIR/fd.txt, sources DIR/../src_<sha>/tools).
# Runs (each the vehicle's own checker: every result word bit-exact vs gold.hex, maxima/denominators vs check.hex, STATUS,
#   all fault flags 0):
#   L<n>_u1   layer n, 1 user, ctx 8192: q = the token's 4 QR rows (stg qk RTL output), K/V = kv_pre head 0 + the P row
#             (stg qk RTL output); golden = TP8-native attention (4 q heads / 1 KV head, S128 / PV256), tools/
#             qwen_tp8_attention_native.py arithmetic (kv_real_vectors.py)
#   G<i>_u4   4 users on one KV tile = layers 4i..4i+3 of the token (real data in every user slot), ctx 8192
#   CTL_L35_goldflip  L35 with one gold.hex bit flipped: must FAIL (the checker reads THESE vectors)
# Hand-off (stage_chain.collect.py, from the fixtures): emb row -> L0 X; per layer resid1 out == resid2 in == gu x;
#   qkv out == qk in; qk out (q, k, v) == KV vector inputs; TP4 attention of them == od o_x (bit-exact, proves the od
#   input is the attention of the RTL's q/k/v); gu out == silu in; silu out == down x; resid2 out == recorded layer X ==
#   next layer's x_in (fixture json sha); L35 X -> lm.
# --die-netlist DIR: DIR/obj/Vtb_kvattn_rel = the die-netlist KV vehicle built by stage kv --die-netlist (grade die-netlist).
set -u
KVROOT=$(readlink -f "$1"); shift
KVOBJ=/srv/opentallas-scratch2/claude/kv-mu6-kvattn4-1020/out_0e597ed1c; NET=""; PAR=48
while [ $# -gt 0 ]; do case "$1" in
  --kv-obj) KVOBJ=$(readlink -f "$2"); shift 2;;
  --die-netlist) NET=$(readlink -f "$2"); KVOBJ=$NET; shift 2;;
  --par) PAR=$2; shift 2;;
  *) echo "bad arg $1"; exit 2;; esac; done
HERE=$(dirname "$(readlink -f "$0")")
C=$KVROOT/chain; IN=$C/in; V=$C/vec; O=$C/runs
B=$KVOBJ/obj/Vtb_kvattn_rel
[ -x "$B" ] || { echo "no KV binary $B"; exit 2; }
[ -d "$IN/fx" ] && [ -d "$IN/p8191/kv_pre" ] || { echo "missing $IN/{fx,p8191} (run_tok_func_qw.sh prep chain)"; exit 2; }
[ ! -e "$O" ] || { echo "runs dir exists: preserve $O"; exit 5; }
GT0=$(ls -d "$KVOBJ"/../src_*/tools 2>/dev/null | head -1); GTOOLS=""; [ -n "$GT0" ] && GTOOLS=$(readlink -f "$GT0")
[ -n "$GTOOLS" ] || GTOOLS=$(readlink -f "$KVROOT/src/tools")
mkdir -p "$V" "$O"
sha256sum "$B" > "$C/binary.sha256"
# the default vehicle is source-bound to 0e597ed1c (53/54 non-bench sources byte-identical to the c0f8097f3 assembly; the
# 54th adds default-0 RX_FREE/TX_FREE parameters left 0 by the identical instantiator: results/rtl/tokfunc2_qw_1021/kv)
KVSRC=$(grep -oE "\b[0-9a-f]{9}\b" "$KVOBJ/SOURCE_COMMIT.txt" 2>/dev/null | head -1)
GRADE="RTL-functional (source-bound KV vehicle ${KVSRC:-$KVOBJ})"
# a vehicle built by stage kv on the source assembly (KVOBJ = RUNROOT/kv/out, its stage verdict RUNROOT/kv/result.json
# PASS with grade "RTL-functional (source assembly)") carries that grade (STEWARD-TOKb-QW 10-21)
KVG=$(python3 -c "import json,sys;r=json.load(open(sys.argv[1]));print(r.get('verdict',''),'|',r.get('grade',''))" \
  "$KVOBJ/../result.json" 2>/dev/null || true)
case "$KVG" in "PASS | RTL-functional (source assembly)"*) GRADE="RTL-functional (source assembly) KV vehicle = stage kv build $KVSRC";; esac
[ -n "$NET" ] && GRADE="die-netlist"
echo "$GRADE" > "$C/GRADE"
FD=$(sed -nE 's/^FD=([0-9]+).*/\1/p' "$KVOBJ/fd.txt" 2>/dev/null); FD=${FD:-3}; echo "FD=$FD (from $KVOBJ/fd.txt)" > "$C/fd.txt"
t0=$(date +%s)
# 1. vectors (CPU golden, ~3 s per layer)
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1
seq 0 35 | xargs -P 12 -I{} sh -c "python3 -I '$HERE/kv_real_vectors.py' --fx '$IN/fx' --kv-pre '$IN/p8191/kv_pre' \
  --layer {} --out '$V/L{}' --tools '$GTOOLS' > '$V/L{}.log' 2>&1; echo rc=\$? >> '$V/L{}.log'"
for L in $(seq 0 35); do grep -q '^rc=0' "$V/L$L.log" || { echo "VECTORS FAIL L$L"; tail -3 "$V/L$L.log"; exit 3; }; done
mkdir -p "$V/CTL_L35_goldflip"; cp "$V"/L35/*.hex "$V"/L35/meta.json "$V/CTL_L35_goldflip/"
python3 - "$V/CTL_L35_goldflip/gold.hex" <<'PY'
import sys; p = sys.argv[1]; w = open(p).read().split('\n'); w[0] = f'{int(w[0], 16) ^ 1:08x}'; open(p, 'w').write('\n'.join(w))
PY
sha256sum "$V"/*/*.hex "$V"/*/meta.json > "$C/vectors.sha256"
echo "vectors $(( $(date +%s) - t0 )) s" > "$C/timing.txt"
# 2. runs (each ~510 s, ~3 GB, single thread)
{ for L in $(seq 0 35); do echo "L${L}_u1 +NU=1 +CTX=8192 +FD=$FD +VEC0=$V/L$L"; done
  for i in $(seq 0 8); do a=$((4*i)); echo "G${i}_u4 +NU=4 +CTX=8192 +FD=$FD +VEC0=$V/L$a +VEC1=$V/L$((a+1)) +VEC2=$V/L$((a+2)) +VEC3=$V/L$((a+3))"; done
  echo "CTL_L35_goldflip +NU=1 +CTX=8192 +FD=$FD +VEC0=$V/CTL_L35_goldflip"; } > "$C/runlist.txt"
run1() { local name=$1; shift; local D=$O/$name; mkdir -p "$D"
  /usr/bin/time -f "%e s %M KB" -o "$D/time" "$B" "$@" > "$D/sim.log" 2>&1; echo $? > "$D/exit"; }
export -f run1; export B O
xargs -P "$PAR" -L 1 bash -c 'run1 "$@"' _ < "$C/runlist.txt"
echo "runs $(( $(date +%s) - t0 )) s" >> "$C/timing.txt"
python3 -I "$HERE/stage_chain.collect.py" "$C" --grade "$GRADE"
