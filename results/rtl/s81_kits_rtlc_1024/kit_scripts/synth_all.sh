#!/bin/bash
E=/srv/opentallas-scratch2/claude/s81-kits/rtlc; L=/srv/opentallas-scratch/claude/s81-kits/rtlc_stage/logs
for k in dsfd_qbank_N dsfd_qbank_S dsfd_rstg ot_s81_sstn_payload536 ot_s81_sstn_base566 dsdv_bksel_c dsdv_gunit_l0 dsdv_gunit_l1c dsdv_gunit_l2 dsdv_gunit_l4 dsdv_gunit_l5_n32 dsdv_gunit_l1 dsdv_gunit_l3 ot_s81sl_xrt1 ot_s81sl_xrt3; do
  case $k in dsdv_gunit_l1|dsdv_gunit_l4|dsdv_gunit_l5_n32|dsdv_bksel_c|ot_s81sl_xrt3|ot_s81sl_xrt1|dsdv_gunit_l3) M=48;; *) M=16;; esac
  ( ~/.local/bin/ot-run --mem $M --threads 8 --dir $E/$k -- bash run_kit.sh $E/$k synth $M 8 > $L/$k.synth.otrun.log 2>&1; echo "rc=$?" >> $L/$k.synth.otrun.log ) &
done
wait
