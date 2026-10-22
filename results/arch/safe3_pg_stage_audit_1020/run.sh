#!/bin/bash
set -eu
D=/srv/opentallas-scratch/claude/codex-safe3-pg-class-1020
R=/srv/opentallas-scratch/claude/ref_gate/hbm_su_pg_stream_b_safe3_1019-20261020-004612/routes/gate/work/orfs/results/asap7/opentallas_ot_hbm_su_static_pg_stream_split_safe3_asap7_ref_gate/base
for stage in 4_1_cts 5_1_grt;do
 sha256sum "$R/$stage.odb" > "$D/$stage.before.sha256"
 docker run --rm -v /srv:/srv:ro -v "$D:/audit:ro" openroad/orfs:asap7lock /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /audit/$stage.tcl > "$D/$stage.log" 2>&1
 sha256sum -c "$D/$stage.before.sha256" > "$D/$stage.unchanged"
done
