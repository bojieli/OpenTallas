#!/bin/bash
# PATH-QC-RP1-F59 miter runner (Verilator 5.032 docker image, as PATH-QC-SRAMIF): 3 seeds x 20k cycles + 3 mutants.
#   mut_rb: per-bank r_ce decoded for the other bank (wrong-bank read)            -> must mismatch
#   mut_rs: c1/c1_off fed from the undelayed pcr_addr (bank/offset select not +1)  -> must mismatch
#   mut_wb: per-bank w_ce decoded for the other half (wrong-bank half write)       -> must mismatch
set -u; D=$(cd "$(dirname "$0")" && pwd); IMG=verilator/verilator:v5.032
run() { # name newfile seeds
  rm -rf $D/obj_$1; docker run --rm -u $(id -u):$(id -g) -e CCACHE_DISABLE=1 -e HOME=/tmp -v $D:/m -w /m $IMG --binary --timing -Wno-fatal -Wno-lint -Wno-style \
    --top-module tb -Mdir obj_$1 -o sim tb_rp1.sv orig_rp1.sv $2 kff.sv sram_1024x256.v > $D/build_$1.log 2>&1 || { echo "BUILD FAIL $1"; tail -20 $D/build_$1.log; return 1; }
  for s in $3; do $D/obj_$1/sim +seed=$s | grep -E "MITER|MISMATCH"; done; }
echo "== MIF=1 vs ORIG (and MIF=0 vs ORIG)"; run base new_rp1.sv "1 7 1234"
sed 's/u_rce (.ck(ck), .d(pcr_re\[0\] \&\& pcr_addr\[3\] == bk\[0\])/u_rce (.ck(ck), .d(pcr_re[0] \&\& pcr_addr[3] != bk[0])/' new_rp1.sv > $D/mut_rb.sv
sed 's/assign rsel_n\[0\] = pcr_addr\[3\];/assign rsel_n[0] = pcr_addr[3];  wire [24:0] mut_x = rsel_n;/; s/(.ck(ck), .d(rsel_n), .q(rsel))/(.ck(ck), .d(rsel_n), .q())/; s/wire \[24:0\] rsel;/wire [24:0] rsel = MIF == 0 ? rsel_n : rsel_n;/' new_rp1.sv > $D/mut_rs.sv
sed 's/u_we (.ck(ck), .d(twc_crw \&\& (!twc_half\[1\] || twc_half\[0\] == bk\[0\]))/u_we (.ck(ck), .d(twc_crw \&\& (!twc_half[1] || twc_half[0] != bk[0]))/' new_rp1.sv > $D/mut_wb.sv
for m in mut_rb mut_rs mut_wb; do
  if cmp -s new_rp1.sv $D/$m.sv; then echo "MUTANT $m NOT APPLIED"; continue; fi
  echo "MUTANT $m"; run $m $m.sv 3; done
rm -rf $D/obj_*
