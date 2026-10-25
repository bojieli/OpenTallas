#!/bin/bash
C=/srv/opentallas-scratch2/claude/s81-cores3-lb/kits/ot_s81_cfg7_seq_bfp_c2; P=/srv/opentallas-scratch2/claude/kits-spare/lb/cfg7probe
docker run --rm --name lbprobe-cfg7-$$ --cpus=4 --memory=8g -v $C:/work:ro -v $P:/out -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; M=\"make DESIGN_CONFIG=/work/config.mk WORK_HOME=/tmp/w FLOW_VARIANT=base\"; \
 BC=\"\$(\$M print-BC_LIB_FILES 2>/dev/null | sed -n \"s/^BC_LIB_FILES *[:=] *//p\")\"; TC=\"\$(\$M print-TC_LIB_FILES 2>/dev/null | sed -n \"s/^TC_LIB_FILES *[:=] *//p\")\"; O=\$(ls /work/run/results/asap7/*/base/4_cts.odb); \
 PC=ff VC=161.6 PLIBS=\"\$BC\" ODB=\$O openroad -exit /out/probe.tcl > /out/probe_ff.log 2>&1; PC=tt VC=256 PLIBS=\"\$TC\" ODB=\$O openroad -exit /out/probe.tcl > /out/probe_tt.log 2>&1; chown -R $(id -u):$(id -g) /out"
