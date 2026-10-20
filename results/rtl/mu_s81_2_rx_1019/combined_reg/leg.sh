#!/usr/bin/env bash
# REFILL-0730/MUS81REG leg driver (cwd = staged repo root). leg.sh LEG
set -u; L=$1; O=$PWD/out/$L; rm -rf $O; mkdir -p $O
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH; export J=8 OT_THREADS=8
verilator --version > $O/verilator_version.txt; echo "host $(hostname) src 7613ee7f4" >> $O/verilator_version.txt
B=rtl/dsrom_sys/s81_dv/slice/test/run_lep_mu_bench.sh
case $L in
  lep_base) bash $B $O base ;;
  lep_mut3) bash $B $O mut ;;
  lep_mut2) sed 's/for m in OT_S81SL_LEP_MUT_TAGDROP OT_S81SL_LEP_MUT_WRONGCOPY OT_DSDV_MU_LAND_MUT_OVR/for m in OT_S81SL_LEP_MUT_LANDCUT OT_S81SL_LEP_MUT_STALEHD/' $B > $O/bench_mut2.sh; bash $O/bench_mut2.sh $O mut ;;
  lep_regr) bash $B $O regr ;;
  lep_nh)   sed -e 's/tb_s81sl_lep_mu\.sv -GSEED=\$s/tb_s81sl_lep_nh.sv -GSEED=$s/' -e 's/TOP=tb_s81sl_lep_mu$/TOP=tb_s81sl_lep_nh/' \
              -e "s/build mu_s\$s \$TOP/build nhp_s\$s \$TOP/; s/run mu_s\$s PASS '\^PASS lep_mu'/run nhp_s\$s PASS '^PASS lep_nh'/; s/for s in 1 5; do/for s in 5; do/" $B > $O/bench_nh.sh
            sed -e 's/tb_s81sl_lep_mu\.sv -GSEED=\$s/tb_s81sl_lep.sv -GSEED=$s +define+TB_LEP_NH/' -e 's/TOP=tb_s81sl_lep_mu$/TOP=tb_s81sl_lep/' \
              -e "s/build mu_s\$s \$TOP/build nhr_s\$s \$TOP/; s/run mu_s\$s PASS '\^PASS lep_mu'/run nhr_s\$s PASS '^PASS lep'/; s/for s in 1 5; do/for s in 7; do/" $B > $O/bench_nhr7.sh
            bash $O/bench_nh.sh $O base; r1=$?; bash $O/bench_nhr7.sh $O base; r2=$?; [ $r1 = 0 ] && [ $r2 = 0 ] ;;
  hwin)     bash rtl/dsrom_sys/s81_dv/unit/test/run_mu_hwin_bench.sh $O ;;
  host)     bash rtl/dsrom_sys/s81_dv/unit/test/run_mu_host_bench.sh $O ;;
  prog)     bash tools/s81_dv/layer_prog/run_mu.sh . $O results/rtl/s81_layer_tput_1018/compiler/prog_L0_s0S results/rtl/s81_mu_1018/prog_L0_mu results/rtl/s81_mu_1018/prog_L2_mu ;;
esac
rc=$?; echo "LEG $L rc=$rc" | tee $O/LEG.rc; exit $rc
