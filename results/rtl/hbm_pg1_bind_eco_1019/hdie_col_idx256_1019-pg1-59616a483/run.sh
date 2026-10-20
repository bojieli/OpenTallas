#!/bin/bash
set -euo pipefail
out=/srv/opentallas-scratch/claude/codex-hbm-pg1-eco-1019/hdie_col_idx256_1019-pg1-59616a483/pg_bind_eco_native
odb=/srv/opentallas-scratch/claude/closure-loop/hdie_col_idx256_1019-pg1-59616a483/routes/hdie_col_idx256_1019_pg1_59616a483/work/orfs/results/asap7/opentallas_ot_hbm_static_cfg_collar_idx256_asap7_ref_hdie_col_idx256_1019_pg1_59616a483/base/6_final.odb
mkdir -p "$out"
test ! -e "$out/post_audit.json"
sha256sum "$odb" > "$out/input.before.sha256"
docker run --rm --network none -v "${odb%/*}:/input:ro" -v "$out:/out" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit /out/pg_bind_eco.tcl > "$out/run.log" 2>&1
cmp "$out/pre_signal.txt" "$out/post_signal.txt"
echo SIGNAL_IDENTICAL >> "$out/run.log"
sha256sum "$odb" > "$out/input.after.sha256"
cmp "$out/input.before.sha256" "$out/input.after.sha256"
cd "$out"
sha256sum 6_final_pgbound.odb pre_signal.txt post_signal.txt >> run.log
echo RC=0 >> run.log
tail -12 run.log
