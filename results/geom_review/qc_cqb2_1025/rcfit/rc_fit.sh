#!/bin/bash
# rc_fit.sh MODE CORNER KLIST  (diagnostic probe, docker --memory, per owner 10-23 checks rule)
cd /srv/opentallas-scratch2/claude/qc-cqb/vmr_s5 && mkdir -p rcfit
docker run --rm --name qccqb-s5-rcfit-$1-$2 --memory=8g --memory-swap=8g --cpus=2 -v $PWD:/work \
 -v /srv/opentallas-scratch2/claude/codex-qc-cores/vmr_cqb/run/results/asap7/kq_qfd_dv_s8x_vmr_rw60/base:/orig:ro \
 -e OT_BASE=/orig -e MODE=$1 -e OT_CORNER=$2 -e KLIST="$3" openroad/orfs:asap7lock \
 /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/rc_fit.tcl > rcfit/log_$1_$2_$(echo $3|md5sum|cut -c1-6).log 2>&1
echo rc $?
