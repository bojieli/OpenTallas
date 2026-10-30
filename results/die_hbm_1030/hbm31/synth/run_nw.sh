#!/bin/bash
# DIE-HBM-31: rerun of DIE-HBM-30-S hub_nw synth with the 4 SRAM macro models read -lib (blackbox); the 30-S run read
# them as behavioural RTL (memory -> registers), ~2 h in elaboration at 38 GB. Diagnostic probe (docker, 48 GB cap).
docker run --rm --name dhbm31s_hubnw -m 48g -v /srv/opentallas-scratch2:/srv/opentallas-scratch2 -v /srv/opentallas-scratch:/srv/opentallas-scratch openroad/orfs:asap7lock bash -c "/usr/bin/time -v yosys -q -l /srv/opentallas-scratch2/claude/wt/die-hbm-27/results/die_hbm_1030/hbm31/synth/nw/yosys.log -s /srv/opentallas-scratch2/claude/wt/die-hbm-27/results/die_hbm_1030/hbm31/synth/nw/hub_synth.ys" > /srv/opentallas-scratch2/claude/wt/die-hbm-27/results/die_hbm_1030/hbm31/synth/nw/run.out 2>&1
echo $? > /srv/opentallas-scratch2/claude/wt/die-hbm-27/results/die_hbm_1030/hbm31/synth/nw/rc
