#!/bin/bash
# XDIE-S81-2: stage the co-sim sources pinned by commit (no checkout needed): stage.sh <repo> <stage dir> <worktree>
#   G8R2 = 0e6b9b710 (claude/tok-s81-g8r2-1019, the newest S81 die bind p4m): every die RTL file of the endpoint path
#   HF3  = ed9d570ad (claude/hf3-coll-lane-1018, current lane tile contract: lt RTL, tile-top CH_BOARD 700)
#   MU   = $MU_COMMIT (default origin/main): ot_s81sl_slice_lep.sv with ot_s81sl_lep_core / ot_s81sl_lep_mu_ab (MU-S81 kit)
# Writes <stage>/SOURCES.txt (path, commit, blob) and copies the bench + tools from <worktree>.
set -eu
R=$1; S=$2; W=$3
# XDIE-S81-MU (10-19): default = the MU RELEASE DIE source, mu3 ceaed19c4 (the RTL of the mu4 strict bind, lanes/
# LEAD2-S81-DIECHAIN): every endpoint-path file, the lane tile (it binds the HF-3 file, blob 0acb62cec41f) and the MU lep
# (ot_s81sl_lep_mu_a / lep_mu_ab / lep_mu with the MU-S81-2/RX show-ahead head) come from that one commit.
# The 10-19 00:30 G8R2 staging = G8=0e6b9b710 HF3=ed9d570ad MU_COMMIT=c6ed36963.
DIE=${DIE:-ceaed19c4}
G8=${G8:-$DIE}; HF3=${HF3:-$DIE}; MU=${MU_COMMIT:-$DIE}
mkdir -p $S; : > $S/SOURCES.txt
put() { # put <commit> <path> [<dest path>]
  local c=$1 p=$2 d=${3:-$2}
  mkdir -p $S/$(dirname $d)
  git -C $R show $c:$p > $S/$d
  echo "$d $(git -C $R rev-parse --short=12 $c) $p $(git -C $R rev-parse --short=12 $c:$p)" >> $S/SOURCES.txt
}
L=rtl/dsrom_sys/s81_link
for p in rtl/link/ot_link_crc32.sv rtl/common/ot_link_credit.sv rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv \
  rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv rtl/dsrom_sys/s81_ph/ot_s81ph_rfifo.sv \
  rtl/dsrom_sys/s81_ph/coll/ot_s81ph_skid2.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv \
  $L/ot_s81_kp4_common.sv $L/ot_s81_kp4_enc.sv $L/ot_s81_kp4_bm.sv $L/ot_s81_kp4_dsyn.sv $L/ot_s81_kp4_ddly.sv $L/ot_s81_kp4_dchn.sv \
  $L/ot_s81_kp4_dout.sv $L/ot_s81_kp4_dec.sv $L/ot_pdie_serdes.sv \
  physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v \
  physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v \
  physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v \
  rtl/dsrom_sys/s81_dv/slice/ot_s81sl_rstop.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv \
  rtl/dsrom_sys/s81_glue/ot_s81_rly.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dv276.sv rtl/dsrom_sys/s81_glue/dsfd_rly_masters_dvh.sv \
  rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv rtl/dsrom_sys/s81_dv/land/dsfd_dvland.sv; do
  put $G8 $p
done
for p in $(git -C $R ls-tree --name-only $G8 $L/ | grep '\.svh$'); do put $G8 $p; done
put $G8 rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane.g8r2.sv
put $HF3 rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane.sv
put $MU rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.mu.sv
for p in rtl/test/xdie_s81_2/xdie_s81_2.vlt rtl/test/xdie_s81_2/xdie_s81_2_ep.sv rtl/test/xdie_s81_2/tb_xdie_s81_2.sv \
  tools/xdie_s81_2/xdie2.sh tools/xdie_s81_2/gate.sh tools/xdie_s81_2/gate_mu.sh tools/xdie_s81_2/gen_golden.py \
  tools/xdie_s81_2/mu_check.py; do
  mkdir -p $S/$(dirname $p); cp $W/$p $S/$p
done
echo "STAGED $(wc -l < $S/SOURCES.txt) pinned files"
