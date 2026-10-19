#!/bin/bash
set -eu
cd src
export MU_RX_SRAM=1 J=4
b=$1
if [ "$b" = lepmu ]; then ms='TAGDROP WRONGCOPY LANDCUT LANDOVR'; else ms='HSTAMP TAGDROP LANDCUT KSOFF'; fi
bash tools/s81_dv/mu_kit_bench.sh ../qual_sram_$b $b none 5
for m in $ms; do
 set +e
 bash tools/s81_dv/mu_kit_bench.sh ../qual_sram_$b $b "$m" 1
 rc=$?
 set -e
 [ "$rc" = 1 ] || { echo "MUTANT_BAD_STATUS $b $m rc=$rc"; exit 1; }
 grep -q "^FAIL lep_mu" ../qual_sram_$b/run_${b}_${m}_1.log || exit 1
 echo "MUTANT_DETECTED $b $m"
done
echo "SRAM_QUAL_PASS $b"
