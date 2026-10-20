#!/usr/bin/env bash
# REFILL-1725/S81REG leg driver (cwd = staged repo root). leg.sh LEG
# Source 10dab88ec (claude/refill1725-s81reg-1019) = S81 MU release die GEN mu4c 19bf4121e + MU die master hwinmerge 233a1b448
#   + LEPCAP bb66563eb RTL/benches (ot_s81sl_slice_lep.sv 3-way merged clean with mu4c bo[512:0]).  Verilator 5.050.
set -u; L=$1; O=$PWD/out/$L; rm -rf $O; mkdir -p $O
export PATH=$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH; export J=8 OT_THREADS=8
verilator --version > $O/verilator_version.txt; echo "host $(hostname) src 10dab88ec (mu4c+hwinmerge+lepcap)" >> $O/verilator_version.txt
B=rtl/dsrom_sys/s81_dv/slice/test/run_lep_mu_bench.sh; K=tools/s81_dv/mu_kit_bench.sh
case $L in
  kit_lepmu_s1|kit_lepmu_s5|kit_lepmuh_s1|kit_lepmuh_s5) b=${L#kit_}; MU_RX_SRAM=1 MU_IN_PIPE=1 bash $K $O ${b%_s*} none ${b##*_s} ;;
  kit_lepmu_ip0|kit_lepmuh_ip0) b=${L#kit_}; MU_RX_SRAM=1 MU_IN_PIPE=0 bash $K $O ${b%_ip0} none 1 ;;
  kmut_lepmu_*|kmut_lepmuh_*) r=${L#kmut_}; b=${r%%_*}; m=${r#*_}; MU_RX_SRAM=1 MU_IN_PIPE=1 bash $K $O $b $m 1 ;;
  lep_base) bash $B $O base ;;
  lep_mut)  bash $B $O mut ;;
  lep_regr) bash $B $O regr ;;
  muh_all)  bash rtl/dsrom_sys/s81_dv/slice/test/run_lep_muh_bench.sh $O all ;;
  lint_die) bash rtl/dsrom_sys/s81_dv/slice/test/lint_lep_mu_die.sh $O ;;
  hwin)     bash rtl/dsrom_sys/s81_dv/unit/test/run_mu_hwin_bench.sh $O ;;
  host)     bash rtl/dsrom_sys/s81_dv/unit/test/run_mu_host_bench.sh $O ;;
  seqhost)  bash rtl/dsrom_sys/s81_dv/unit/test/run_seq_host_mu_bench.sh $O ;;
  shmut1)   bash rtl/dsrom_sys/s81_dv/unit/test/run_seq_host_mu_mut.sh $O 1 ar ;;
  shmut2)   bash rtl/dsrom_sys/s81_dv/unit/test/run_seq_host_mu_mut.sh $O 2 f_collide ;;
  shmut5)   bash rtl/dsrom_sys/s81_dv/unit/test/run_seq_host_mu_mut.sh $O 5 ar ;;
  hslot_m0) bash $K $O hslot 0 47 ;;
  hslot_m1) bash $K $O hslot 1 47 ;;
  hslot_m2) bash $K $O hslot 2 47 ;;
  hslot_col) bash $K $O hslot 0 47 1 ;;
  prog)     bash tools/s81_dv/layer_prog/run_mu.sh . $O results/rtl/s81_layer_tput_1018/compiler/prog_L0_s0S results/rtl/s81_mu_1018/prog_L0_mu results/rtl/s81_mu_1018/prog_L2_mu ;;
  *) echo "unknown leg $L"; false ;;
esac
rc=$?; echo "LEG $L rc=$rc" | tee $O/LEG.rc; exit $rc
