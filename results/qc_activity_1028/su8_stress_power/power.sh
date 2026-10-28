#!/bin/bash
set -eu
K=/srv/opentallas-scratch2/claude/qccores1-1027/rst3_k0/hold_b
O=/srv/opentallas-scratch2/claude/codex-qc-activity-0359/su8_power_v2
mkdir -p "$O"
B=run/results/asap7/kq_qfd_dv_s5_su8_rst3_c/base
docker run --rm --name codex_qc_activity_su8_$$ -m 32g --cpus 4 -u $(id -u):$(id -g) -v "$K:/kit:ro" -v "$O:/work/out" -v "$O/act_su8.txt:/work/act.txt:ro" -v "$O/power_spef.tcl:/work/meas.tcl:ro" -e OT_ODB=/kit/$B/6_final.odb -e OT_SDC=/kit/$B/6_final.sdc -e OT_SPEF=/kit/$B/6_final.spef -e OT_TAG=su8_stress -e OT_PREFIX= -e OT_PLACED=0 openroad/orfs:asap7lock bash -c "/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/meas.tcl" > "$O/power.log" 2>&1
