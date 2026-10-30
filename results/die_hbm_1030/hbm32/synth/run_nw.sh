#!/bin/bash
# DIE-HBM-32: hub_nw synth count with PORT-ONLY (* blackbox *) SRAM stubs (sram_stubs.sv). The 31 run read the SRAM models
# with read_verilog -lib, but yosys still expanded arr (mem2reg) on the 1024x256 model: >35 min in parse, stopped.
docker run --rm --name dhbm32s_hubnw -m 48g -v /srv/opentallas-scratch2:/srv/opentallas-scratch2 -v /srv/opentallas-scratch:/srv/opentallas-scratch openroad/orfs:asap7lock bash -c "/usr/bin/time -v yosys -q -l /srv/opentallas-scratch2/claude/wt/die-hbm-27/results/die_hbm_1030/hbm32/synth/nw/yosys.log -s /srv/opentallas-scratch2/claude/wt/die-hbm-27/results/die_hbm_1030/hbm32/synth/nw/hub_synth.ys" > /srv/opentallas-scratch2/claude/wt/die-hbm-27/results/die_hbm_1030/hbm32/synth/nw/run.out 2>&1
echo $? > /srv/opentallas-scratch2/claude/wt/die-hbm-27/results/die_hbm_1030/hbm32/synth/nw/rc
