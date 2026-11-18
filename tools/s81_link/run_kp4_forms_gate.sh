#!/usr/bin/env bash
# FABLE-FIX-HEAD-SD9F 11-18: link-level gate (tb_s81_pdie_link -GSERDES=1: ot_pdie_serdes = KP4 FEC + rate matching over a
# behavioural PMA with pad bit errors, two plesiochronous dies) of every hd_serdes window form, through the ot_pdie_serdes /
# ot_s81_kp4_dec define plumbing: defines off, (a) OT_S81_KP4_ENC_PPCYC, (b) OT_S81_RCK_RX_SPCYC, (c) both, (d) the zero-cycle
# partial splits OT_S81_KP4_ENC_PW16 + OT_S81_KP4_SYN_PW8 (with OT_S81_KP4_ENC_LA), all must PASS; DMUT 2 on (c) and (d) and the
# split mutant RCKRF_MUT_SPW8 on (d) must FAIL.  usage: run_kp4_forms_gate.sh <repo> <workdir>.  Last line KP4_FORMS_GATE PASS|FAIL.
set -u
SRC=$1; OUT=$2; mkdir -p "$OUT"
F=$(sed -n 's/^F="\(.*\)"$/\1/p' "$SRC/rtl/dsrom_sys/s81_link/run_pdie_link_gate.sh" | head -1 | sed "s#\$SRC#$SRC#g")
[ -n "$F" ] || { echo "file list not found"; exit 2; }
v=PASS
run() { local l=$1 want=$2; shift 2
  verilator --binary --timing -j 16 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT +incdir+$SRC/rtl/dsrom_sys/s81_link \
    --top-module tb_s81_pdie_link -GSERDES=1 "$@" --Mdir "$OUT/$l" -o tb $F > "$OUT/build_$l.log" 2>&1 || { echo "BUILD FAIL $l"; tail -6 "$OUT/build_$l.log"; v=FAIL; return; }
  "$OUT/$l/tb" +verilator+seed+3 > "$OUT/run_$l.log" 2>&1
  local r; r=$(grep TB_S81_PDIE "$OUT/run_$l.log" | tail -1)
  echo "[$l] ${r:-NO RESULT LINE}" | cut -c1-300
  case "$r" in *" $want") ;; *) echo "  UNEXPECTED (want $want)"; v=FAIL;; esac
}
LA=-DOT_S81_KP4_ENC_LA
run off PASS
run la PASS $LA
run a_ppcyc PASS $LA -DOT_S81_KP4_ENC_PPCYC
run b_spcyc PASS $LA -DOT_S81_RCK_RX_SPCYC
run c_both PASS $LA -DOT_S81_KP4_ENC_PPCYC -DOT_S81_RCK_RX_SPCYC
run d_pw PASS $LA -DOT_S81_KP4_ENC_PW16 -DOT_S81_KP4_SYN_PW8
run c_dmut FAIL $LA -DOT_S81_KP4_ENC_PPCYC -DOT_S81_RCK_RX_SPCYC -GDMUT=2
run d_dmut FAIL $LA -DOT_S81_KP4_ENC_PW16 -DOT_S81_KP4_SYN_PW8 -GDMUT=2
run d_mspw8 FAIL $LA -DOT_S81_KP4_ENC_PW16 -DOT_S81_KP4_SYN_PW8 -DRCKRF_MUT_SPW8
echo "KP4_FORMS_GATE $v"
[ $v = PASS ]
