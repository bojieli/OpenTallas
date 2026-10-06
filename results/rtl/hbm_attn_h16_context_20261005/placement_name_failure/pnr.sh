#!/bin/bash
set -u
cd /srv/opentallas-scratch2/codex/hbm-suattn-context-20261005/src || exit 1
export TMPDIR=/srv/opentallas-scratch2/codex/hbm-suattn-context-20261005/context_h16_pnr/tmp
export OPENTALLAS_ORFS_IMAGE=openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
export OT_ORFS_NUM_CORES=16
date -u +%FT%TZ > /srv/opentallas-scratch2/codex/hbm-suattn-context-20261005/context_h16_pnr/pnr.started
python3 tools/run_abi3_physical.py --view asap7 --top ot_attn_tile_m6h1 --source physical/hbm_fmax_attn_context/ot_attn_tile_m6h1.sv --macro-view ot_attn_hgrp_m6h1=physical/hbm_fmax_attn_context/ot_attn_hgrp_m6h1 --macro-place-halo 5 5 --clock-period-ns 0.8333333333333334 --clock-uncertainty-ns 0.06 --clock-uncertainty-hold-ns 0.025 --orfs-corner WC --hold-corners WC,BC --io-delay-fraction 0.2 --sdc-append physical/hbm_fmax_attn_context/parent.sdc --stages pnr --die-area 0 0 1349.112 1349.976 --core-area 0 0 1349.112 1349.976 --place-density 0.50 --routing-layers M2 M9 --pin-region '^(ld_.*|iv|ibank.*|ib.*)$=left' --pin-region '^(ov|oy.*|oflt.*)$=right' --pin-region '^(clk|rst_n)$=top' --orfs-var MACRO_PLACEMENT_TCL=/src/physical/hbm_fmax_attn_context/macro_placement.tcl --orfs-var IO_PLACER_H=M8 --orfs-var IO_PLACER_V=M9 --orfs-var ADDER_MAP_FILE= --slew-margin-percent 30 --hold-margin-ns 0.01 --purpose signoff_target --nickname-tag codex_h16_nb5_context_r1 --synth-timeout-seconds unlimited --flow-timeout-seconds unlimited --keep-workdir /srv/opentallas-scratch2/codex/hbm-suattn-context-20261005/context_h16_pnr/work --output /srv/opentallas-scratch2/codex/hbm-suattn-context-20261005/context_h16_pnr/physical.json > /srv/opentallas-scratch2/codex/hbm-suattn-context-20261005/context_h16_pnr/run.log 2>&1
rc=$?
printf "rc=%s\n" "$rc" > /srv/opentallas-scratch2/codex/hbm-suattn-context-20261005/context_h16_pnr/exit
if test -f /srv/opentallas-scratch2/codex/hbm-suattn-context-20261005/context_h16_pnr/physical.json; then
 python3 tools/w18/corner_sta.py --orfs-dir /srv/opentallas-scratch2/codex/hbm-suattn-context-20261005/context_h16_pnr/work/orfs --macro physical/hbm_fmax_attn_context/ot_attn_hgrp_m6h1 --output /srv/opentallas-scratch2/codex/hbm-suattn-context-20261005/context_h16_pnr/corner_sta.json > /srv/opentallas-scratch2/codex/hbm-suattn-context-20261005/context_h16_pnr/corner.log 2>&1
 printf "corner_rc=%s\n" "$?" >> /srv/opentallas-scratch2/codex/hbm-suattn-context-20261005/context_h16_pnr/exit
fi
date -u +%FT%TZ > /srv/opentallas-scratch2/codex/hbm-suattn-context-20261005/context_h16_pnr/end
