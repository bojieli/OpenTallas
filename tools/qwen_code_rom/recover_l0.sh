#!/bin/bash
# Restore actual L0/rank0 TP8 native code masks from the released pinned source.
# Run via ot-run; worktree and output directory must reside on scratch disks.
set -euo pipefail
WT=${1:?own clean worktree}
OUT=${2:?new recovery output directory}
mkdir -p "$OUT"
printf 'RECOVERY_START %s\n' "$(date -Is)" >> "$OUT/status"
cd "$WT"
python3 tools/qwen_code_rom/recover_checkpoint.py --out "$OUT/checkpoint" > "$OUT/download.log" 2>&1
python3 -m venv "$OUT/venv"
"$OUT/venv/bin/pip" install --index-url https://download.pytorch.org/whl/cpu torch > "$OUT/deps_torch.log" 2>&1
"$OUT/venv/bin/pip" install numpy safetensors > "$OUT/deps.log" 2>&1
export QWEN_O4_TP=8 QWEN_O4_GROUPS=3072 OMP_NUM_THREADS=${OT_J:-4} MKL_NUM_THREADS=${OT_J:-4}
SNAP="$OUT/checkpoint/b968826d9c46dd6066d109eabc6255188de91218"
"$OUT/venv/bin/python" tools/hdc_qwen_layer0_rom_w12.py --snapshot "$SNAP" --die 0 --layer 0 --compact-banks --out "$OUT/banks/images/layer0/die0" > "$OUT/l0_emit.log" 2>&1
"$OUT/venv/bin/python" tools/qwen_code_rom/build.py --banks "$OUT/banks" --out "$OUT/code_masks_l0" --layers 0 --ranks 0 --jobs 1 > "$OUT/code_masks.log" 2>&1
printf 'RECOVERY_COMPLETE %s\n' "$(date -Is)" >> "$OUT/status"
