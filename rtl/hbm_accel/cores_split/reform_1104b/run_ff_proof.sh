#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p build logs
common=(-g2012 -Irtl -Icanonical)
src=(rtl/ot_s81_kp4_enc_la.sv canonical/ot_s81_kp4_common.sv)
for la in 1 2; do
  iverilog "${common[@]}" -s tb_kp4_enc_la -Ptb_kp4_enc_la.LA="$la" -o build/native_la"$la" rtl/tb_kp4_enc_la.sv canonical/ot_s81_kp4_enc.sv "${src[@]}" >logs/build_native_la"$la".log 2>&1
  vvp build/native_la"$la" +NCYC=4000 +STALL=729 +SEED=23 >logs/native_la"$la".log
  grep 'TB_KP4_ENC_LA PASS' logs/native_la"$la".log
 done
for mut in 0 1 2 3; do
  iverilog "${common[@]}" -s tb_kp4_enc_ff -Ptb_kp4_enc_ff.MUT="$mut" -o build/ff_mut"$mut" rtl/tb_kp4_enc_ff.sv "${src[@]}" >logs/build_ff_mut"$mut".log 2>&1
  if [[ "$mut" == 0 ]]; then
    for test in continuous stall_reset; do
      args=(+NCYC=5000 +SEED=41)
      [[ "$test" == continuous ]] || args=(+NCYC=5000 +SEED=709 +STALL=839 +RESET_AT=2300)
      vvp build/ff_mut0 "${args[@]}" >logs/ff_"$test".log
      grep 'TB_KP4_ENC_FF PASS' logs/ff_"$test".log
    done
  else
    if vvp build/ff_mut"$mut" +NCYC=1200 +SEED=97 >logs/ff_mut"$mut".log 2>&1; then
       echo "MUTANT $mut SURVIVED"; exit 1
    fi
    grep 'TB_KP4_ENC_FF FAIL' logs/ff_mut"$mut".log
    echo "MUTANT $mut CAUGHT"
  fi
 done
iverilog "${common[@]}" -s tb_pdie_tx_ff -o build/pdie_ff rtl/tb_pdie_tx_ff.sv rtl/ot_pdie_serdes_split.sv canonical/ot_s81_kp4_enc.sv canonical/ot_pdie_serdes.sv "${src[@]}" >logs/build_pdie_ff.log 2>&1
vvp build/pdie_ff >logs/pdie_ff.log
grep 'TB_PDIE_TX_FF PASS' logs/pdie_ff.log
printf 'ALL_NATIVE_FF_PROOFS_PASS\n' 
