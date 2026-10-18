#!/bin/bash
# TOKEN-PASS-QWEN 2026-10-18: Qwen3-8B ROM per-layer RTL steps on the fleet (one step per ot-run call).
#   run_1018.sh D STEP      D = the run root on the host (src/ = pinned source export, fx/ = fixtures)
# Steps
#   restore   W12 TP4 stage images L0..L35 + head (x4 dies) from the pinned prep npz into fx/img_p1 (sha-checked vs the
#             prep's recorded image pins; the EPYC1 /home/ubuntu/w12 + qwen-dspark-system/img_p1 trees are gone)
#   hist_l3   KV history for the L3 chain: L0..L2 from the realmem P8191 gold kv_pre (L0 die0 checked against the
#             committed pin); L3..L35 ZERO placeholders of the same size (never read before the L3 chain stops after L2;
#             they only feed the early-go prefetch of L3, whose outputs are not checked) -> fx/history_l3
#   gold      CPU TP4 36-layer + head golden (venv torch CPU; the local GPU is in ERR state, owner 10-09: CPU goldens
#             on the fleet) -> fx/gold/tp4, verified vs the committed digests, full 144-file KV history -> fx/history
#   d2d       compute<->KV static D2D link programme bench on the CURRENT link-end RTL (qfd_d2d_static /
#             qkd_d2d_static, all 36 layer calendars, Verilator) + mutants 1..7 (must FAIL)
#   kvprog    KV die layer-programme control root (qkd_static_kv_layer_programme = kvs14c u_lprg) + mutants
#   build     partition_token.py build --variant part (pos: --comp 1, neg: --comp 0), the 10-13 vehicle configuration
#   runL3 / runL3neg / runhead   the per-layer runs (L0 cold, L1/L2 chained; head = L35 gold X preload)
set -u -o pipefail
D=$1; STEP=$2
SRC=$D/src; FX=$D/fx; LOG=$D/STATUS.log
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH
ENVTP="QWEN_O4_TP=4 QWEN_O4_GROUPS=6144 HDC_SU_WIDTH=1024 HDC_KV_FMT=fp8"
PYV=$D/py   # python3 + PYTHONPATH=$D/pylib (torch CPU + safetensors via pip --target: no python3-venv on the fleet)
mkvenv() { [ -x "$PYV" ] && "$PYV" -c "import torch, safetensors" 2>/dev/null && return 0
  { python3 -m pip install -q --target "$D/pylib" torch --index-url https://download.pytorch.org/whl/cpu && \
    python3 -m pip install -q --target "$D/pylib" safetensors && \
    printf '#!/bin/sh\nPYTHONPATH=%s/pylib${PYTHONPATH:+:$PYTHONPATH} exec python3 "$@"\n' "$D" > "$PYV" && chmod +x "$PYV" && \
    "$PYV" -c "import torch, safetensors; print(torch.__version__)"; } >> "$D/venv.log" 2>&1; }
now() { TZ=America/Los_Angeles date '+%F %H:%M:%S'; }
log() { echo "$(now) $*" >> "$LOG"; }
T0=$(date +%s)
done_() { local rc=$1; log "$STEP rc=$rc wall_s=$(( $(date +%s) - T0 ))"; exit "$rc"; }
cd "$SRC" || exit 2
log "$STEP start src $(cat SOURCE_COMMIT) host $(hostname)"
case $STEP in
restore)
  mkvenv || done_ 3
  mkdir -p "$FX/img_p1" "$D/restore"
  : > "$D/restore/fails.txt"
  one() { local o=$FX/img_p1/L$1-d$2 f=$D/restore/L$1-d$2.log
    env $ENVTP "$PYV" tools/exactness/w12_layer_restore.py "$FX/prep/tp4" $1 $2 "$o" > "$f" 2>&1 || \
    env $ENVTP "$PYV" tools/exactness/w12_layer_restore.py "$FX/prep/tp4" $1 $2 "$o" --compact >> "$f" 2>&1 || \
    echo "FAIL L$1-d$2" >> "$D/restore/fails.txt"; }
  for l in $(seq 0 35); do for d in 0 1 2 3; do
    while [ "$(jobs -rp | wc -l)" -ge 48 ]; do wait -n; done
    one $l $d &
  done; done; wait
  for d in 0 1 2 3; do
    o=$FX/img_p1/head-d$d
    { env $ENVTP "$PYV" tools/qwen_tokpass/w12_head_restore.py "$FX/prep/tp4" $d "$o" && \
      env $ENVTP "$PYV" tools/exactness/w12_head_stage.py "$FX/prep/tp4" $d "$o"; } > "$D/restore/head-d$d.log" 2>&1 || echo "FAIL head-d$d" >> "$D/restore/fails.txt"
  done
  n=$(wc -l < "$D/restore/fails.txt"); log "restore fails=$n ($(head -c 300 "$D/restore/fails.txt" | tr '\n' ' '))"
  [ "$n" = 0 ]; done_ $? ;;
hist_l3)
  H=$FX/history_l3; mkdir -p "$H"
  python3 - "$FX/realmem/P8191/kv_pre" "$H" <<'EOF' >> "$LOG" 2>&1
import hashlib, json, sys
from pathlib import Path
import numpy as np
src, out = Path(sys.argv[1]), Path(sys.argv[2])
pin = "190fcd6d3cd94bba849b4082990090cbedba5ddd9a756f82624d225f5c721876"
man = {}
for p in sorted(src.glob("L*_die*.npy")):
    b = out / (p.stem + ".bin"); np.load(p).astype("<u4").tofile(b)
    man[p.stem] = hashlib.sha256(b.read_bytes()).hexdigest()
n = (out / "L0_die0.bin").stat().st_size
zero = []
for l in range(3, 36):
    for d in range(4):
        b = out / f"L{l}_die{d}.bin"; b.write_bytes(b"\0" * n); zero.append(b.stem)
ok = man.get("L0_die0") == pin
(out / "MANIFEST.json").write_text(json.dumps({"real": man, "zero_placeholders": zero, "pin_L0_die0_match": ok,
  "rule": "L3 chain only: L3..L35 are zero placeholders (the run stops after L2; L3+ never checked)"}, indent=1))
print("hist_l3 real", len(man), "zero", len(zero), "pin", ok)
sys.exit(0 if ok and len(man) == 12 else 1)
EOF
  done_ $? ;;
gold)
  mkvenv || done_ 3
  L=$FX/gold/tp4; mkdir -p "$L"
  env $ENVTP OMP_NUM_THREADS=${THREADS:-64} "$PYV" tools/qwen_hbmacc_position_oracle_gpu.py --run --device cpu \
    --prep-dir "$FX/prep/tp4" --layers 36 --head --tokens "$FX/inputs/prompt_tokens_8192.txt" --positions 8191 \
    --embedding-npz "$FX/inputs/prompt_embedding.npz" --out "$L" > "$D/gold_tp4.log" 2>&1 || done_ 4
  python3 tools/exactness/fixtures.py verify --gold "$L" --ref results/rtl/qwen_hbmacc_p8191_20261004/gold_tp4/oracle.json \
    --out "$L/verify.json" >> "$LOG" 2>&1 || done_ 5
  python3 tools/exactness/fixtures.py history --gold "$L/P8191" --out "$FX/history" >> "$LOG" 2>&1
  done_ $? ;;
d2d)
  rc=0
  for m in 0 1 2 3 4 5 6 7; do
    BACKEND=verilator JOBS=8 bash rtl/test/qwen_split/run_d2d_program.sh "$D/d2d/m$m" $m > "$D/d2d/m$m.out" 2>&1; r=$?
    log "d2d mutant $m rc=$r $(tail -1 "$D/d2d/m$m.out" | head -c 160)"
    if [ $m = 0 ]; then [ $r = 0 ] || rc=1; else [ $r != 0 ] || rc=1; fi
  done
  done_ $rc ;;
kvprog)
  python3 tools/qwen_static_kv/run_layer_programme.py --out "$D/kvprog" > "$D/kvprog.out" 2>&1; done_ $? ;;
build)
  # 10-15 fleet NBA guard (verilator_guarded.py) refuses this die: 3 in-place NBA loops (u_hbm t_rd_sectors, kvw_ce,
  # st_rsp_stall) -> unroll them (the guard's own remedy); the 10-13 builds predate the guard
  export QROM_VFLAGS_EXTRA="${QROM_VFLAGS_EXTRA:---unroll-count 4096}"
  python3 tools/qwen_missing/partition_token.py build --variant part --build "$D/bld_pos" --jobs ${JOBS:-32} --dcu 2 --duc 2 --su-ml 7 --comp 1 > "$D/build_pos.log" 2>&1; r1=$?
  log "build pos rc=$r1"
  python3 tools/qwen_missing/partition_token.py build --variant part --build "$D/bld_neg" --jobs ${JOBS:-32} --dcu 2 --duc 2 --su-ml 7 --comp 0 > "$D/build_neg.log" 2>&1; r2=$?
  log "build neg rc=$r2"
  [ $r1 = 0 ] && [ $r2 = 0 ]; done_ $? ;;
runL3|runL3neg|runhead)
  b=bld_pos; st=L3; hist=$FX/history_l3; gold=$FX/realmem/P8191
  [ $STEP = runL3neg ] && b=bld_neg
  if [ $STEP = runhead ]; then st=head; hist=$FX/history; gold=$FX/gold/tp4/P8191; fi
  QWEN_FX_IMG=$FX/img_p1 QWEN_FX_GOLD=$gold QWEN_FX_XPRE=$gold/x_preload.hex QWEN_FX_HISTORY=$hist \
    python3 tools/qwen_missing/partition_token.py run --build "$D/$b" --work "$D/$STEP" --stages $st --threads ${THREADS:-16} \
    > "$D/$STEP.log" 2>&1; r=$?
  log "$STEP $(tail -2 "$D/$STEP.log" | tr '\n' ' ' | head -c 300)"
  done_ $r ;;
*) echo "unknown step $STEP"; exit 2 ;;
esac
