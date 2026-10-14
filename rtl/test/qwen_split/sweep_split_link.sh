#!/bin/bash
# Qwen TP8 split die-link measurement sweep (tb_qwen_split_link.sv): every configuration in the list below, J at a time.
# usage: sweep_split_link.sh <outdir> [J]      -> <outdir>/results.txt (one PASS/FAIL line per case, case name first)
set -u
OUT=$(readlink -f $1); J=${2:-16}
H=$(cd "$(dirname "$0")" && pwd)
mkdir -p $OUT
P=tb_qwen_split_link
cases() {
  # merged-die reference (on-die relays ROM_ST each way between the SU / VM / ROM-sequencer faces and the sequencer)
  for e in 200 849; do for r in 0 24; do echo "m_r${r}_e${e} -P$P.SPLIT=0 -P$P.ROM_ST=$r -P$P.ENG=$e"; done; done
  # split: compute-die stages C_ST, KV/system-die stages K_ST, UCIe FDI-to-FDI latency PHY, KV end flat (0) / thin cluster (1)
  for e in 200 849; do for spl in 0 1; do for c in 0 8 16 26; do
    echo "s_c${c}_k16_p5_spl${spl}_e${e} -P$P.SPLIT=1 -P$P.C_ST=$c -P$P.K_ST=16 -P$P.PHY_LAT=5 -P$P.KVE_SPL=$spl -P$P.ENG=$e"
  done; done; done
  for p in 3 9; do echo "s_c8_k16_p${p}_spl1_e849 -P$P.SPLIT=1 -P$P.C_ST=8 -P$P.K_ST=16 -P$P.PHY_LAT=$p -P$P.KVE_SPL=1 -P$P.ENG=849"; done
  for k in 0 8 24; do echo "s_c8_k${k}_p5_spl1_e849 -P$P.SPLIT=1 -P$P.C_ST=8 -P$P.K_ST=$k -P$P.PHY_LAT=5 -P$P.KVE_SPL=1 -P$P.ENG=849"; done
  # mutants (must FAIL): 1 flit dropped in the PHY, 2 Q beats 0/1 swapped (sequencer MUT 2), 3 KVN v-tag dropped in the bridge
  for mu in 1 2 3; do echo "mut${mu} -P$P.SPLIT=1 -P$P.C_ST=8 -P$P.K_ST=16 -P$P.KVE_SPL=1 -P$P.MUT=$mu"; done
}
cases_llr() {
  # v1b (owner 08:05 no-stubs): the link-level retry + CRC layer at both ends (ot_qkvd_d2d_llr), KV end thin cluster
  for e in 200 849; do echo "m_r0_e${e} -P$P.SPLIT=0 -P$P.ROM_ST=0 -P$P.ENG=$e"; done
  for c in 0 8 26; do for k in 1 16; do
    echo "l_c${c}_k${k}_e849 -P$P.SPLIT=1 -P$P.LLR=1 -P$P.C_ST=$c -P$P.K_ST=$k -P$P.KVE_SPL=1 -P$P.ENG=849"
  done; done
  echo "l_c8_k1_e200 -P$P.SPLIT=1 -P$P.LLR=1 -P$P.C_ST=8 -P$P.K_ST=1 -P$P.KVE_SPL=1 -P$P.ENG=200"
  for p in 3 9; do echo "l_c8_k1_p${p}_e849 -P$P.SPLIT=1 -P$P.LLR=1 -P$P.C_ST=8 -P$P.K_ST=1 -P$P.PHY_LAT=$p -P$P.KVE_SPL=1 -P$P.ENG=849"; done
  for er in 5001 501; do echo "l_c8_k1_err${er}_e849 -P$P.SPLIT=1 -P$P.LLR=1 -P$P.C_ST=8 -P$P.K_ST=1 -P$P.KVE_SPL=1 -P$P.ENG=849 -P$P.ERRP=$er"; done
  echo "l_mut1_drop_recovers -P$P.SPLIT=1 -P$P.LLR=1 -P$P.C_ST=8 -P$P.K_ST=1 -P$P.KVE_SPL=1 -P$P.MUT=1"
  for mu in 2 3; do echo "l_mut${mu} -P$P.SPLIT=1 -P$P.LLR=1 -P$P.C_ST=8 -P$P.K_ST=1 -P$P.KVE_SPL=1 -P$P.MUT=$mu"; done
  for mu in 4 5; do echo "l_mut${mu}_err501 -P$P.SPLIT=1 -P$P.LLR=1 -P$P.C_ST=8 -P$P.K_ST=1 -P$P.KVE_SPL=1 -P$P.ERRP=501 -P$P.MUT=$mu"; done
}
if [ "${SWEEP:-v1}" = llr ]; then cases_llr > $OUT/cases.txt; else cases > $OUT/cases.txt; fi
run1() { n=$1; shift; r=$($H/run_split_link.sh $OUT/$n "$@" 2>&1 | tail -1); echo "$n $r"; }
export -f run1; export OUT H
cat $OUT/cases.txt | xargs -P $J -L 1 bash -c 'run1 "$@"' _ > $OUT/results.txt
sort $OUT/results.txt -o $OUT/results.txt
cat $OUT/results.txt
