#!/usr/bin/env bash
# MU-S81/KIT (2026-10-19): one bench per call for the multi-user S81 closure kits (cwd = repo root, Verilator 5.050).
#   mu_kit_bench.sh OUTDIR lepmu  MUT SEED   tb_s81sl_lep_mu: die P = ot_s81sl_lep_mu_ab (kit s81sl_lepmu, AB_EN 1),
#                                            dies A / B = ot_s81sl_lep_mu + dsdv_mu_land NB 80 NS 1 SRAM 1 (kit
#                                            dsdv_mu_land), RP -> RA single-user reference (ot_s81sl_lep_nh).
#                                            MUT none | TAGDROP | WRONGCOPY | LANDCUT (ot_s81sl_lep_core) | LANDOVR (dsdv_mu_land)
#                                            (dies A / B = ot_s81sl_lep_mu_a, kit s81sl_lepmua)
#   mu_kit_bench.sh OUTDIR lepmuh MUT SEED   tb_s81sl_lep_muh (kit s81sl_lepmuh, MU-S81-2/HOSTEP): host-plane MU endpoint
#                                            ot_s81sl_lep_mu_h + dsdv_mu_land vs the single-user ot_s81sl_lep.
#                                            MUT none | HSTAMP | TAGDROP | LANDCUT | KSOFF (ot_s81sl_lep_core)
#   mu_kit_bench.sh OUTDIR hslot  MUT NS [COLLIDE]   tb_dsdv_mu_hslot (kit dsdv_mu_hslot): NS users / slots, MUT 0|1|2,
#                                            COLLIDE 1 = a start into an occupied slot (must fault)
# Prints the testbench verdict lines and a last line BENCH_PASS / BENCH_FAIL <what>; exit 0 only on BENCH_PASS.
set -u
O=$(realpath -m "${1:?outdir}"); B=${2:?bench}; M=${3:-none}; mkdir -p "$O"
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
$V --version
case $B in
lepmu|lepmuh)
  S=${4:-1}; L=rtl/dsrom_sys/s81_link; SL=rtl/dsrom_sys/s81_dv/slice
  SRCS="rtl/lib/ot_rst_relay_tree3.sv rtl/lib/ot_sram_oldread_wreg.sv rtl/lib/ot_sram_showahead_1r1w.sv physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1/ot_sram_1r1w_32x128_m1.v rtl/link/ot_link_crc32.sv rtl/common/ot_link_credit.sv rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv
   rtl/dsrom_sys/s81_ph/ot_s81ph_link_ep.sv rtl/dsrom_sys/s81_ph/ot_s81ph_link_gbx.sv rtl/dsrom_sys/s81_ph/ot_s81ph_rfifo.sv
   rtl/dsrom_sys/s81_ph/coll/ot_s81ph_skid2.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_ckbuf.sv rtl/dsrom_sys/s81_ph/coll/ot_s81ph_coll_lane.sv
   $L/ot_s81_kp4_common.sv $L/ot_s81_kp4_enc.sv $L/ot_s81_kp4_bm.sv $L/ot_s81_kp4_dsyn.sv $L/ot_s81_kp4_ddly.sv $L/ot_s81_kp4_dchn.sv
   $L/ot_s81_kp4_dout.sv $L/ot_s81_kp4_dec.sv $L/ot_pdie_serdes.sv
   physical/asap7_memory_macros/ot_sram_1r1w2c_64x546_m1/ot_sram_1r1w2c_64x546_m1.v
   physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1/ot_sram_1r1w_32x546_m1.v
   physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v
   physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
   $SL/ot_s81sl_slice_lep.sv $SL/dsdv_mu_land.sv"
  TB=tb_s81sl_lep_mu; VR=lep_mu; [ $B = lepmuh ] && { TB=tb_s81sl_lep_muh; VR=lep_muh; }
  SRCS="$SRCS $SL/test/$TB.sv"
  D="+define+OT_S81SL_TX_GROUP_ASSERT +define+OT_S81PH_GBX_FMT1 +define+OT_S81PH_EP_PIPE2"
  case $M in none) ;; LANDOVR) D="$D +define+OT_DSDV_MU_LAND_MUT_OVR" ;; *) D="$D +define+OT_S81SL_LEP_MUT_$M" ;; esac
  R=${B}_${M}_$S
  $V --binary --timing -O1 -Wno-fatal -Wno-WIDTH -Wno-TIMESCALEMOD -Wno-MULTIDRIVEN -Wno-lint -Wno-style +incdir+$L $D -GSEED=$S -GRXSRAM=${MU_RX_SRAM:-0} -GINPIPE=${MU_IN_PIPE:-0} \
    --top-module $TB -Mdir $O/obj_$R $SRCS --build-jobs ${J:-8} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" \
    > $O/build_$R.log 2>&1 || { grep -m10 %Error $O/build_$R.log; echo "BUILD_FAILED $R"; exit 3; }
  $O/obj_$R/V$TB > $O/run_$R.log 2>&1
  grep -E "^(LEP_MU_STATS|LEPMUH_STATS|MISMATCH|PASS|FAIL|ERR)|%Fatal" $O/run_$R.log | head -12
  grep -q "^PASS $VR:" $O/run_$R.log && { echo "BENCH_PASS $B MUT=$M seed $S"; exit 0; }
  echo "BENCH_FAIL $B MUT=$M seed $S"; exit 1 ;;
hslot)
  NS=${4:-47}; C=${5:-0}; U=rtl/dsrom_sys/s81_dv/unit
  D="+define+NS=$NS +define+NP=$NS"; [ "$M" != none ] && [ "$M" != 0 ] && D="$D +define+MUT=$M"; [ "$C" = 1 ] && D="$D +define+COLLIDE=1"
  R=hslot_${M}_${NS}_$C
  $V --binary --timing -j ${J:-8} -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style --top-module tb_dsdv_mu_hslot $D \
    rtl/lib/ot_rst_relay.sv rtl/dsrom_sys/s81_ph/ot_s81ph_mem1r1w.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v $U/dsdv_mu_hslot.sv $U/test/tb_dsdv_mu_hslot.sv --Mdir $O/obj_$R -o tb > $O/build_$R.log 2>&1 \
    || { grep -m10 %Error $O/build_$R.log; echo "BUILD_FAILED $R"; exit 3; }
  $O/obj_$R/tb > $O/run_$R.log 2>&1
  grep -E "^(MUHSLOT|ERR)" $O/run_$R.log | head -12
  if [ "$C" = 1 ]; then ok='^MUHSLOT COLLIDE NS [0-9]+ PASS \(fault raised\)'; else ok='^MUHSLOT PASS$'; fi
  grep -q -E "$ok" $O/run_$R.log && { echo "BENCH_PASS hslot MUT=$M NS $NS COLLIDE $C"; exit 0; }
  echo "BENCH_FAIL hslot MUT=$M NS $NS COLLIDE $C"; exit 1 ;;
*) echo "unknown bench $B"; exit 2 ;;
esac
