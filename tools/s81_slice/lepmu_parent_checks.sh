#!/bin/bash
# lepmu_parent_checks.sh <outdir> <side: e|w> bind   (cwd = repo root; FLEET only via ot-run)
# DRIVE-S81-SLICEP 10-20: strict port bind of the landed MU end-slice parents ot_s81sl_slice_lep{e,w}_mu_x_lp and their
# flat expansions (as lepenh_parent_checks.sh bind): no tied / open / undriven / unread child pin.
# DRIVE-S81-LEPENHMU 10-20: side e_nh = ot_s81sl_slice_lepe_nh_mu_x(_lp) (dsdv_slice_lepe_nh_mus) on the REAL MU lane tops
# dsfd_coll_lane_e_safe8_ntf (kit dscoll_lane_e_s8n sources added as --rtl-file).
set -u; O=$1; S=$2; W=${3:-bind}; mkdir -p $O
L=rtl/dsrom_sys/s81_dv/slice/landed/lep${S}_mu
XR=""
if [ "$S" = e_nh ]; then
  for f in rtl/lib/ot_rst_relay_tree3.sv rtl/lib/ot_sram_oldread_b64.sv rtl/lib/ot_sram_showahead_b64.sv rtl/common/ot_link_credit_rx_b64.sv rtl/common/ot_link_credit_tx_rc.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep_safe4.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx_safe3.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane_safe4.sv; do XR="$XR --rtl-file $f"; done
  XR="$XR --define OT_COLL_NATIVE32 --define OT_COLL_NATIVE32_OFF"
fi
case $W in
bind)
  rc=0
  for top in ot_s81sl_slice_lep${S}_mu_x_lp ot_s81sl_slice_lep${S}_mu_x; do
    f=$O/$top.v; python3 tools/s81_slice/bind_form.py $L/$top.sv $top $f || exit 3
    python3 tools/die_port_bind.py $f --top $top --define DSFD_PQ_STATIC_X2 --define OT_S81PH_LANE_CR \
      --rtl-file rtl/common/landed_parent/ot_pl_land.sv --rtl-file rtl/common/landed_parent/ot_pl_land_field_copies.sv --rtl-file rtl/common/landed_parent/ot_pl_land_reset_forest.sv --rtl-file rtl/common/landed_parent/ot_pl_land_kept_enable.sv \
      --rtl-file rtl/dsrom_sys/s81_dv/slice/dsdv_mu_land.sv $XR \
      --prefer rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane.sv --prefer rtl/hdc/v41/ot_hdc_fsqrt.sv --prefer rtl/hdc/ot_hdc_fp32_mul_lat.sv \
      --prefer-list tools/s81_slice/slice_lep_bench.sh --out $O/bind_$top.json > $O/bind_$top.log 2>&1
    r=$?; echo "BIND $top exit $r"; tail -5 $O/bind_$top.log; [ $r -eq 0 ] || rc=1
  done
  echo "BIND_EXIT $rc"; exit $rc;;
*) echo "unknown $W"; exit 2;;
esac
