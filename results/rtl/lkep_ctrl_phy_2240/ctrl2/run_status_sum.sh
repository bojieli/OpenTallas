#!/bin/bash
set -euo pipefail
$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator --binary --timing -O2 -j 4 -Wno-fatal -Wno-lint -Wno-style --top-module tb_lkep_status_sum_2240 --Mdir /srv/opentallas-scratch/lkep-ctrl2-2240/sumobj -o sim tb_lkep_status_sum_2240.sv rtl/hbm_accel/tu/lk_ep_20261010/ot_lkep_ctrl_phy.sv rtl/hbm_accel/tu/lk_ep_20261010/ot_hbm_lk_ep.sv rtl/hbm_accel/tu/lk_ep_20261010/ot_crc_par.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv > /srv/opentallas-scratch/lkep-ctrl2-2240/sum_build.log 2>&1
/srv/opentallas-scratch/lkep-ctrl2-2240/sumobj/sim
