#!/bin/bash
# [link] 2026-10-10 combined coll RTL bench: ot_hgi_coll_ep (NPT 9, SWCRED 32) <-> 9 hfd_lk_ep pairs <-> switch stub,
# the DS-V4.1 layer's COLL.ALL_GATHER sequence (tb_hgi_coll_lk, from tb_hgi_coll_pipe).  run in the source root:
#   run_coll_lk.sh <out> [plusargs...]   env DEFS="-DPIPE ..."
set -u; O=$1; shift; mkdir -p $O; D=rtl/hbm_accel/tu; C=rtl/hbm_accel/generic/collective
S="rtl/common/ot_secded.sv rtl/common/ot_secded_dec_dp.sv physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
   $D/link_retry_sram_20261008/ot_hbm_replay_sram_dp.sv $D/link_retry_pipeline_20261009/ot_hbm_link_retry_pipeline_cl.sv
   rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv $D/lk_ep_20261010/ot_crc_par.sv $D/lk_ep_20261010/ot_hbm_lk_ep.sv $D/lk_ep_20261010/ot_lkep_sub.sv
   $C/ot_hgi_coll_ep.sv $C/ot_hgi_coll_amerge.sv $C/ot_hgi_coll_record.sv $C/ot_hgi_coll_decode.sv
   $D/ot_hbm_accel_tu_endpoint_psg.sv $D/ot_hcoll_sram_prims.sv rtl/hbm_accel/ha2_ar/ot_ha2_prims.sv $D/ot_hcoll_port.sv
   rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_fastfp.sv rtl/link/ot_link_afifo.sv
   rtl/hbm_accel/generic/ot_hgi_cfg.sv $C/ot_hfd_coll_r25gq.sv $D/lk_ep_20261010/tb_hgi_coll_lk.sv"
for f in $C/rgx/*.sv rtl/hbm_accel/generic/peers/ot_hgi_hbm_lane.sv rtl/hbm_accel/generic/ot_hgi_vm_lanearb.sv; do case $f in *tb_*) continue;; esac; [ -f $f ] && S="$S $f"; done
verilator --binary --timing -O2 -j ${JOBS:-8} -Wno-fatal -Wno-WIDTH -Wno-UNUSED -Wno-BLKSEQ -Wno-UNOPTFLAT -Wno-MULTIDRIVEN -Wno-lint -Wno-style \
  -Irtl/common -Irtl/hbm_accel/generic --top-module tb_hgi_coll_lk --Mdir $O/obj ${DEFS:-} $S > $O/build.log 2>&1 || { grep -m8 "%Error" $O/build.log; echo "HGI_COLL_PIPE FAIL (build)"; exit 2; }
$O/obj/Vtb_hgi_coll_lk "$@" > $O/run.log 2>&1
grep -h "HGI_COLL_PIPE\|Fatal\|ERR" $O/run.log | head -5; tail -4 $O/run.log | grep -v "^- "
grep -q "HGI_COLL_PIPE PASS" $O/run.log
