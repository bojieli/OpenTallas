#!/bin/bash
set -euo pipefail
ROOT=${WBK1340_GEN_ROOT:?fresh immutable GEN-only root}
cd "$ROOT/src"
test "$(cat HELPER_COMMIT)" = b5f983efec3f397e21d998efd23bfa55e40d0c3d
test "$(cat SOURCE_COMMIT)" = 0441f9958
sha256sum -c "$ROOT/input.sha256" > "$ROOT/gen_input_verification.log"
export OT_THREADS=8
set +e
python3 tools/ref_tile/ref_tile.py gen tools/hbm_static/wbk_native_1340/spec.json --commit "$(cat SOURCE_COMMIT)" > "$ROOT/gen.log" 2>&1
rc=$?
set -e
printf '%s\n' "$rc" > "$ROOT/gen.rc"
if [ "$rc" -eq 0 ]; then echo WBK_FINAL_GEN_ONLY_DONE_NO_SYNTH_NATIVE_LAYOUT; fi
exit "$rc"
