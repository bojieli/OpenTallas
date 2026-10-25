#!/bin/bash
# TOK-QK 10-25: ONE reproducible KV boot-image compile: bind dir in -> boot bundle + vehicle inputs out, every input hashed.
#
#   kv_boot_image.sh BIND_DIR OUT_DIR PV_ENTRY_TABLE.json         (run from anywhere; repository = this script's tree)
#
# Env (all optional; the defaults reproduce image_kv41 bit-exact on BIND=binder4 kv41):
#   AS         rtl6 GEN as-built case dir (relay_stages / static_model / boot_ages / kv_flags.env / health_successor /
#              rst_regional).  Default: the committed copy boot_v36/asbuilt_rtl6 (gz, e33504a6f GEN, sha256 in manifest).
#   LINK_IMAGE pair image (repo-relative or absolute .svh) the KV dcal tile of the bound top carries; the script compiles
#              the pair image itself and fails unless it equals LINK_IMAGE bit for bit.  Unset = no comparison (kv41).
#              kv44+ (KV-R4): results/rtl/qwen_rom_pair_candidate_1024/d2d_cal_image.svh (MU+RoPE emb1627 R16, HEAD_PREP 12):
#              LINK_EMB_WIN=1627 LINK_ROPE=1 LINK_HEAD_PREP=12.
#   LINK_EMB_WIN  token-run embedding window of the pair image (default 595; the pair1024 image is 1627)
#   LINK_ROPE     1 = RoPE pair profile (D2D_ROPE=1; OT_KV_ROPE_OVL=1 in the target-11 link-calendar rebuild)
#   LINK_HEAD_PREP N = recurring C->K HEAD_PREP slot edges (D2D_HEAD_PREPARE_EDGES; OT_KV_HEAD_PREP_EDGES)
#   KST        KV seam stages override (default: kst.py on the bind's bus_groups)
#   DQ_TABLE   the bind's vport request-lane table (kv44: bind/kv44/tables/vport_dq_pads_kv44.json) -> dq_check.txt
# Outputs in OUT_DIR: prep/ img_bnd/ cmp_asbuilt/ cmp_bound/ (boot_bundle.json, target*.hex), pv_check.txt,
#   vehicle/{boot_bundle.json.gz,frames.hex,expect.txt,epoch.txt} (tb_kvslice inputs), manifest.json (sha256 in + out).
# Fails closed on: compiled pair image != LINK_IMAGE; compile errors; link_image_check (target 11 != pair image).
set -euo pipefail
B=$(readlink -f "$1"); O=$(mkdir -p "$2" && readlink -f "$2"); PV=$(readlink -f "$3")
H=$(cd "$(dirname "$0")" && pwd); R=$(cd "$H/../../../.." && pwd)
T=physical/die_plan/qwen_kvsys/boot_v36/kv_boot_v36.py
cd "$R"
# ---- inputs
if [ -z "${AS:-}" ]; then
  AS=$O/asbuilt_rtl6; mkdir -p "$AS"
  for f in "$H"/asbuilt_rtl6/*; do b=$(basename "$f"); case $b in *.gz) gunzip -c "$f" > "$AS/${b%.gz}";; *) cp "$f" "$AS/$b";; esac; done
fi
AS=$(readlink -f "$AS")
BG=$B/bus_groups.json; [ -f "$BG" ] || { gunzip -c "$B/bus_groups.json.gz" > "$O/bus_groups.json"; BG=$O/bus_groups.json; }
KST=${KST:-$(python3 "$H/kst.py" "$BG")}; echo "KST $KST"
EMB=${LINK_EMB_WIN:-595}
# ---- GEN flags (rtl6 profile) + prep (bound depths from the bind's bus_groups)
set -a; . "$AS/kv_flags.env"; set +a
export OT_KV_RETIRE_SUCCESSOR=$AS/health_successor.json OT_KV_RETIRE_LOGICAL=1
python3 $T prep --rs "$AS/relay_stages.json" --model "$AS/static_model.json" --groups "$BG" --out "$O/prep" > "$O/prep.log"
# ---- pair (link) image: always compiled here on the bind's KV seam (MU, r16 TX shift 1 / STATUS 213, EMB window, RoPE,
#      HEAD_PREP); a given LINK_IMAGE must equal it bit for bit (proves the dcal tile's image is this compile's calendar)
[ "${LINK_ROPE:-0}" = 1 ] && export D2D_ROPE=1
[ -n "${LINK_HEAD_PREP:-}" ] && export D2D_HEAD_PREPARE_EDGES=$LINK_HEAD_PREP
D2D_K_STAGES=$KST D2D_DIE_STAGES=2,2,2,3,2,2/$KST D2D_MU=1 D2D_EMB_WINDOW=$EMB D2D_ATTN_TX_SHIFT=1 D2D_STATUS_DELAY=213 \
  bash tools/qwen_split/d2d_cal_image_production.sh "$O/img_bnd"
if [ -n "${LINK_IMAGE:-}" ]; then
  case $LINK_IMAGE in /*) LI=$LINK_IMAGE;; *) LI=$R/$LINK_IMAGE;; esac
  cmp -s "$LI" "$O/img_bnd/d2d_cal_image.svh" || { echo "PAIR IMAGE MISMATCH: $LI != compiled $O/img_bnd/d2d_cal_image.svh" >&2; exit 3; }
  echo "pair image == $LINK_IMAGE (bit-exact)"
fi
# ---- compile (as-built reference, then bound)
python3 $T compile --ages "$O/prep/die_ages_asbuilt.json" --rs "$O/prep/relay_stages_asbuilt.json" --out "$O/cmp_asbuilt" | tee "$O/cmp_asbuilt.log"
# the bound compile binds the pair image of the bound dcal tile (its emb window / RoPE profile); the as-built reference keeps
# the rtl6 GEN profile (kv_flags.env)
OT_KV_EMB_WIN=$EMB OT_KV_ROPE_OVL=${LINK_ROPE:-0} OT_KV_HEAD_PREP_EDGES=${LINK_HEAD_PREP:-} OT_KV_LINK_IMAGE=$O/img_bnd/d2d_cal_image.svh python3 $T compile --ages "$O/prep/die_ages_bound_padded.json" \
  --rs "$O/prep/relay_stages_bound.json" --out "$O/cmp_bound" | tee "$O/cmp_bound.log"
# ---- checks + vehicle inputs
python3 "$H/pv_check.py" "$O" "$PV" > "$O/pv_check.txt" || true; tail -1 "$O/pv_check.txt"
# the bind's own PV request-lane derivation (kv44+: kv_wreq_dq44.py vport_dq_pads_kvNN.json, RL / RT / DQ after its W pads)
if [ -n "${DQ_TABLE:-}" ]; then
  python3 - "$O" "$DQ_TABLE" > "$O/dq_check.txt" <<'EOF' || true
import json, sys
from pathlib import Path
O, T = Path(sys.argv[1]), json.load(open(sys.argv[2]))
ag = json.loads((O / 'prep/die_ages_bound_padded.json').read_text()); dq = json.loads((O / 'prep/vport_dq_pads.json').read_text())
rl = [k for k in T if k.startswith('RL') and k != 'RL41'] or ['RL']; rt = [k for k in T if k.startswith('RT_') and k != 'RT_kv41']
bad = 0
def chk(n, g, w):
    global bad; bad += g != w; print(f"{'OK ' if g == w else 'BAD'} {n}: boot {g} bind {w}")
chk('PV RL', ag['pv']['RL'], T[rl[-1]])
for v, w in sorted(T[rt[-1]].items()):
    chk(f'{v} RT', ag['vport'][v]['RT'], w)
    chk(f'{v} DQ (after bind W pad)', ag['vport'][v]['DQ'], T['dq_unpadded_kv44' if 'dq_unpadded_kv44' in T else 'dq'][v] - T['pad_stages'][v])
    chk(f'{v} extra W pad needed by boot', dq['pad_stages'][v], 0)
print('DQ_CHECK', 'PASS' if not bad else f'FAIL {bad}')
EOF
  tail -1 "$O/dq_check.txt"
fi
# owner decision 14: per-PC column / command duty of the compiled controller calendars (targets 6..9)
OT_KV_EMB_WIN=$EMB OT_KV_ROPE_OVL=${LINK_ROPE:-0} OT_KV_HEAD_PREP_EDGES=${LINK_HEAD_PREP:-} OT_KV_LINK_IMAGE=$O/img_bnd/d2d_cal_image.svh \
  python3 "$H/hbm_duty.py" --ages "$O/prep/die_ages_bound_padded.json" --rs "$O/prep/relay_stages_bound.json" --out "$O/hbm_duty.json" \
  | python3 -c "import json,sys; d=json.loads(sys.stdin.read()); print('HBM_DUTY per 833-ps cycle', {k: round(v['max'], 3) for k, v in d['per_833ps_cycle'].items()}, d['verdict']['shape_per_833ps'])"
mkdir -p "$O/vehicle"; gzip -9nc "$O/cmp_bound/boot_bundle.json" > "$O/vehicle/boot_bundle.json.gz"
python3 tools/qwen_layerbench/kv_dieslice/boot_frames.py "$O/cmp_bound/boot_bundle.json" "$O/vehicle"
( cd "$O/cmp_bound" && sha256sum $(ls target*.hex | sort -V) boot_bundle.json ../img_bnd/d2d_cal_image.svh > "$O/targets.sha256" )
# ---- manifest
python3 - "$O" "$R" "$B" "$BG" "$PV" "$AS" "$KST" "$EMB" "${LINK_IMAGE:-generated}" "${LINK_ROPE:-0}" "${LINK_HEAD_PREP:-}" <<'EOF'
import hashlib, json, subprocess, sys
from pathlib import Path
O, R, B, BG, PV, AS, KST, EMB, LI, ROPE, HP = sys.argv[1:]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
git = lambda *a: subprocess.run(['git', '-C', R] + list(a), capture_output=True, text=True).stdout.strip()
dirty = git('status', '--porcelain', '--', 'tools', 'physical/die_plan/qwen_kvsys/boot_v36', 'results/rtl', 'rtl')
b = json.load(open(Path(O) / 'cmp_bound/boot_bundle.json'))
m = dict(tool='physical/die_plan/qwen_kvsys/boot_v36/kv_boot_image.sh', git_head=git('rev-parse', 'HEAD'),
         git_dirty_paths=dirty.splitlines(), bind_dir=B, kst=KST, link_emb_window=int(EMB), link_image=LI, link_rope=ROPE == '1', link_head_prep=int(HP) if HP else None,
         inputs={'bus_groups': sha(BG), 'pv_entry_table': sha(PV), 'pair_image': sha(Path(O) / 'img_bnd/d2d_cal_image.svh'),
                 **{f'asbuilt/{p.name}': sha(p) for p in sorted(Path(AS).iterdir()) if p.is_file()}},
         outputs={'boot_bundle.json': sha(Path(O) / 'cmp_bound/boot_bundle.json'),
                  **{f'vehicle/{n}': sha(Path(O) / 'vehicle' / n) for n in ('frames.hex', 'expect.txt', 'epoch.txt')},
                  **{p.name: sha(p) for p in sorted(Path(O, 'cmp_bound').glob('target*.hex'))}},
         epoch=b['epoch'], images=[(im['target'], im['program_words'], im['digest']) for im in b['images']],
         pv_check=open(Path(O) / 'pv_check.txt').read().splitlines()[-1],
         dq_check=open(Path(O) / 'dq_check.txt').read().splitlines()[-1] if Path(O, 'dq_check.txt').is_file() else None,
         hbm_duty={k: v for k, v in json.load(open(Path(O) / 'hbm_duty.json')).items() if k in ('hbm_ps_compiled', 'per_compiled_edge', 'per_833ps_cycle', 'verdict')})
Path(O, 'manifest.json').write_text(json.dumps(m, indent=1) + '\n')
print('MANIFEST', Path(O, 'manifest.json'), 'bundle', m['outputs']['boot_bundle.json'][:16])
EOF
