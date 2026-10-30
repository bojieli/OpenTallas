#!/bin/bash
# usage: hier.sh TYPE RUNDIR  -> hier/TYPE.list (flattened macro instance names + masters)
set -u
T=$1; D=$2; O=/srv/opentallas-scratch2/claude/die-s81-32/macro/hier
DEF="-DSYNTHESIS -DDSFD_PQ_STATIC_X2 -DS81CTRL_SRAM_FIFO -DS81CTRL_SRAM_P192 -DS81CTRL_NATIVE32 -DOT_COLL_NATIVE32 -DOT_COLL_NATIVE32_OFF -DOT_S81ENG_TAP_N32R2 -DOT_S81SL_KV_TRANSPORT -DOT_SVC_ALLQ -DSU_SMU_T -DOT_ATTN_HCORE -DOT_S81ENG_RR_N32 -DOT_S81C_HCORE_CTLA -DOT_S81C_HCORE_RST_TIMED -DS81_HOSTB_LAND_OBS"
FILES=$(sed -n "s/^export VERILOG_FILES = //p" $D/config.mk)
TOP=$(sed -n "s/^export DESIGN_NAME = //p" $D/config.mk)
cat > $O/$T.ys <<YS
read_verilog -defer -sv $DEF $FILES
hierarchy -top $TOP
proc
flatten
YS
rm -f $O/$T.list2
for m in $(ls $D/rtl | sed -n "s/_bb\.v$//p"); do echo "tee -q -a /out/$T.list2 log ==$m" >> $O/$T.ys; echo "tee -q -a /out/$T.list2 select -list t:$m" >> $O/$T.ys; done
docker run --rm --memory 48g -v $D:/work:ro -v $O:/out -u $(id -u):$(id -g) openroad/orfs:asap7lock bash -c "export PATH=/OpenROAD-flow-scripts/tools/install/yosys/bin:\$PATH; yosys -q -l /out/$T.log /out/$T.ys" ; echo "$T exit $?" >> $O/status
