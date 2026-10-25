#!/bin/bash
# postcts.sh KIT : read-only post-CTS dumps (docker, 12 GB cap) -> KIT/review/
K=$1; L=/srv/opentallas-scratch2/claude/kits-spare/lb; O=/srv/opentallas-scratch2/claude/kits-spare-lbrev/$(basename $K); mkdir -p $O
docker run --rm --name lbpost-$(basename $K)-$$ --cpus=8 --memory 12g -v $K:/work -v $L:$L -v $O:/rev -w /OpenROAD-flow-scripts/flow openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; M=\"make DESIGN_CONFIG=/work/config.mk WORK_HOME=/tmp/w FLOW_VARIANT=base\"; \
 BC=\"\$(\$M print-BC_LIB_FILES 2>/dev/null | sed -n \"s/^BC_LIB_FILES *[:=] *//p\")\"; TC=\"\$(\$M print-TC_LIB_FILES 2>/dev/null | sed -n \"s/^TC_LIB_FILES *[:=] *//p\")\"; O=\$(ls /work/run/results/asap7/*/base/4_cts.odb); \
 VT=\$(sed -n \"s/^export OT_VCLK_TT = //p\" /work/config.mk); VF=\$(sed -n \"s/^export OT_VCLK_FF = //p\" /work/config.mk); \
 ODB=\$O OUT=/rev/placed.csv openroad -python -exit $L/dump_placed.py > /rev/dump.log 2>&1; \
 PC=ff VC=\$VF PLIBS=\"\$BC\" ODB=\$O KIT=/work OUT=/rev/ck_ff.csv openroad -exit $L/ck_dump.tcl > /rev/ck_ff.log 2>&1; \
 PC=tt VC=\$VT PLIBS=\"\$TC\" ODB=\$O KIT=/work OUT=/rev/ck_tt.csv openroad -exit $L/ck_dump.tcl > /rev/ck_tt.log 2>&1; chown -R $(id -u):$(id -g) /rev"
