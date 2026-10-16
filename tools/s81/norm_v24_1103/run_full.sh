#!/bin/bash
set -euo pipefail
tar xf source.tar.gz
printf '%s\n' 28dd8dbda > SOURCE_COMMIT
sha256sum source.tar.gz rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ntree.sv > source.sha256
export S81_SU_CASES=/srv/opentallas-scratch/claude/s81-suhc/su_cases_v2_ildr.pkl
mkdir -p output
bash tools/s81_suhc/hc_owned_bench.sh "$PWD/output/exact" 1 > output/exact.log 2>&1
grep -q '^RUN ng256_dpi_m0_a0_hier3tail_cp1_cs6_ls1_pipe40_nt67 pass$' output/exact.log
printf 'FULL_EXACT_PASS\n'
for tile in ot_s81_hc_ctfxs_nt ot_s81_hc_ctfl_nt ot_s81_hc_ctfn ot_s81_hc_ctfs_nt; do
 set +e
 bash tools/s81_suhc/hc_owned_bench.sh "$PWD/output/$tile" 1 "$tile" > "output/$tile.log" 2>&1
 rc=$?
 set -e
 grep -q "^RUN ng256_dpi_m0_a0_hier3tail_cp1_cs6_ls1_pipe40_nt67_tm-$tile fail$" "output/$tile.log"
 printf 'EXPECTED_MUTANT_FAIL %s rc=%s\n' "$tile" "$rc"
done
printf 'NORM_V24_FULL_PROOF_COMPLETE\n'
