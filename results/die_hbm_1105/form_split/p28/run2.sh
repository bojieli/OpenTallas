#!/bin/bash
cd /srv/opentallas-scratch3/claude/hfs2/q3/eq
V=$HOME/.local/opentallas-tools/bin/verilator
until [ -s /srv/opentallas-scratch3/claude/hfs2/q3/est/ctl__fs.sv ] && [ -s /srv/opentallas-scratch3/claude/hfs2/q3/est/qcol4__fs.sv ]; do sleep 20; done
date
$V --binary -j 8 --output-split 30000 --output-split-cfuncs 3000 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN --top-module tb -O1 -Mdir obj2 -o sim tb2.sv   /srv/opentallas-scratch2/claude/hfs/v0/k/ot_hfd_coll_q3_body_core_4cf02115fd4a/rtl/ot_hbm_face_reg.sv /srv/opentallas-scratch2/claude/hfs/v0/k/ot_hfd_coll_q3_body_core_4cf02115fd4a/rtl/ot_hfd_coll_q3_body_core__fshell.sv /srv/opentallas-scratch2/claude/hfs/v0/k/ot_hfd_coll_q3_body_core_4cf02115fd4a/rtl/ot_hfd_coll_q3_body_core__wrap.sv /srv/opentallas-scratch2/claude/hfs/v0/k/ot_hfd_coll_q3_body_core_4cf02115fd4a/rtl/ot_hfd_coll_q3_body_core.sv   /srv/opentallas-scratch3/claude/hfs2/q3/sr/ot_sram_1r1w_256x256_m2_r2c2.v /srv/opentallas-scratch3/claude/hfs2/q3/sr/ot_sram_1rw_256x64_m4_r2c2.v   /srv/opentallas-scratch3/claude/hfs2/q3/gen/ot_hfd_coll_q3_body_ctl.sv /srv/opentallas-scratch3/claude/hfs2/q3/gen/ot_hfd_coll_q3_body_core__split.sv qcol4_mutrt.sv /srv/opentallas-scratch3/claude/hfs2/q3/est/ctl__fs.sv /srv/opentallas-scratch3/claude/hfs2/q3/est/qcol4__fs.sv > build2.log 2>&1
echo BUILD_RC $?; date
for R in 0 1; do for M in 0 1 2 3; do obj2/sim +MUT=$M +ROWRND=$R > sim2_r${R}_m$M.log 2>&1; echo "ROWRND $R MUT $M: $(grep -E 'DIRECTED|LOCKSTEP' sim2_r${R}_m$M.log | tr '\n' ' ')"; done; done
sha256sum /srv/opentallas-scratch2/claude/hfs/v0/k/ot_hfd_coll_q3_body_core_4cf02115fd4a/rtl/*.sv /srv/opentallas-scratch3/claude/hfs2/q3/gen/*.sv qcol4_mutrt.sv /srv/opentallas-scratch3/claude/hfs2/q3/est/*__fs.sv tb2.sv > sources2.sha256
echo EQ_DONE
