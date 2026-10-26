#!/bin/bash
# TOK-QK 10-25: KV token gate on a run_mu833.sh image: (A) static schedule, (B) boot ABI (MU471 + DIECFG AGES96) with the
# bind's native nc32 dispatcher, (C) default AGES0 lockstep vs the legacy dispatcher.   token_gate.sh IMG_OUT GATE_OUT
# Sources: tools + boot ABI benches at this commit; the nc32 controller face the KV binds read is not on main -> pinned by
# commit NC32 (claude/kdie5-rtl-ctl-1022 558fba7b5; the bind trees' qkd_kvs_ctl_nc32.sv / qkd_kv_ctl_nc32_face.sv are
# byte-identical to it).
set -euo pipefail
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
I=$(readlink -f "$1"); G=$(mkdir -p "$2" && readlink -f "$2")
H=$(cd "$(dirname "$0")" && pwd); R=$(cd "$H/../../.." && pwd); cd "$R"
NC32=${NC32:-558fba7b5}; A=results/rtl/native_boot_abi_1713; T=physical/die_plan/qwen_kvsys/boot_v36/kv_boot_v36.py
set -a; . "$I/compile.env"; set +a
# (A) recompile MU (dumping the frame-search inputs) + SU rows; the MU bundle must reproduce the image of record bit for bit
FS_OUT=$G/fs_in.pkl python3 "$H/fsdump.py" $T compile --ages "$I/prep/die_ages_bound_padded.json" --rs "$I/prep/relay_stages_bound.json" \
  --mu ${GATE_CONTRACT:---native-contract results/rtl/native_die_cfg_contract_1713/contract.json --capability 1} --out "$G/cmp_mu" > "$G/cmp_mu.log" 2>&1
python3 $T compile --ages "$I/prep/die_ages_bound_padded.json" --rs "$I/prep/relay_stages_bound.json" --no-mu --out "$G/cmp_su" > "$G/cmp_su.log" 2>&1
for f in "$I"/cmp_mu833/target*.hex; do cmp -s "$f" "$G/cmp_mu/$(basename "$f")" || { echo "GATE FAIL: $(basename "$f") not reproduced"; exit 2; }; done
python3 "$H/recheck.py" "$R" "$G/fs_in.pkl" "$G/cmp_mu" "$G/cmp_su" > "$G/static.json"
python3 - "$G/static.json" <<'PY'
import json,sys; d=json.load(open(sys.argv[1]))
ok=d['mu_image_equal'] and d['gaps_equal'] and d['user0_gaps_zero'] and d['checks']['collisions']==0 and d['all_launches_legal'] and d['mu_words']==471
print('STATIC_SCHEDULE', 'PASS' if ok else 'FAIL', json.dumps({k:d[k] for k in ('F','mu_words','checks','tokens_per_frame','aggregate_tok_s')}))
sys.exit(0 if ok else 3)
PY
# (B)+(C) boot ABI benches (the committed native_boot_abi_1713 benches) on THIS image
mkdir -p "$G/src" "$G/mu" "$G/ages"
git show "$NC32:rtl/qwen_sys/static_kv_die_20261017/qkd_kv_ctl_nc32_face.sv" > "$G/src/nc32_face.sv"
python3 tools/qwen_layerbench/kv_dieslice/native_boot_ages.py dispatch "$G/src/nc32_face.sv" "$G/src/dispatch.sv"
D=rtl/qwen_sys/static_kv_die_20261017
SRC=("$G/src/dispatch.sv" "$R/$D/qkd_kv_ctl_c32_boot.sv" "$R/rtl/lib/ot_s32_cells.sv")
cp "$G/cmp_su/target1.hex" "$G/mu/target1.hex"; cp "$G/cmp_mu/target1.hex" "$G/mu/target1_mu.hex"
(cd "$G/mu"; verilator --binary --timing -Wno-fatal -j 4 --top-module tb -Mdir obj -o sim "$R/$A/tb_boot_mu_abi_positive.sv" "${SRC[@]}" > build.log 2>&1; ./obj/sim > run.log 2>&1) || true
if [ -f "$G/cmp_mu/target10.hex" ]; then
  cp "$G/cmp_mu/target10.hex" "$G/ages/target10.hex"
  (cd "$G/ages"; verilator --binary --timing -Wno-fatal -j 4 --top-module tb -Mdir obj -o sim "$R/$A/tb_boot_age_miter.sv" "$R/$A/legacy_dispatch.sv" "${SRC[@]}" "$R/$D/qkd_kv_ctl_c32_dcfg.sv" "$R/$D/qkd_kv_ctl_c32_misc.sv" > build.log 2>&1; ./obj/sim > run.log 2>&1) || true
else echo "no target10 (diagnostic NO_CONTRACT image): DIECFG AGES96 + lockstep NOT RUN" > "$G/ages/run.log"; fi
verilator --version > "$G/verilator.version"
grep -h -E "PASS|FAIL|fatal|NOT RUN|fault=" "$G/mu/run.log" "$G/ages/run.log" | tee "$G/abi.txt"
grep -q ACTUAL_NATIVE_MU471_IMAGE_PASS "$G/mu/run.log" && grep -q ACTUAL_DISPATCH_DCFG_AGES96_PASS "$G/ages/run.log" && grep -q DEFAULT_AGES0_LOCKSTEP_PASS "$G/ages/run.log" \
  && echo "KV_TOKEN_GATE PASS" || { echo "KV_TOKEN_GATE FAIL/INCOMPLETE"; exit 4; }
