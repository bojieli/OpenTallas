#!/bin/bash
set -u
for seam in 1 2 3 4 5 6 7; do
  out="/srv/opentallas-scratch/dma-group-owned-0d4cfabff/mut$seam"
  bash rtl/test/hbm_accel/b2_dma/run_b2_dma_q_bench.sh "$out" "-GMUT_SEAM=$seam" -GNREC=4
  rc=$?
  if [ "$rc" -eq 1 ] && grep -q '^B2_DMA_Q FAIL' "$out/run.log"; then
    echo "FACE9RQ_MUTANT $seam observed_FAIL"
  else
    echo "FACE9RQ_MUTANT $seam BAD_RC $rc"
    exit 1
  fi
done
out="/srv/opentallas-scratch/dma-group-owned-0d4cfabff/core_pin_mut"
bash rtl/test/hbm_accel/b2_dma/run_b2_dma_q_bench.sh "$out" -GMUT_CORE_PIN=1 -GNREC=4
rc=$?
if [ "$rc" -eq 1 ] && grep -q 'core registered encoded512 disagrees' "$out/run.log"; then
 echo CORE_PIN_INVALID_MUTANT observed_FAIL
else
 echo CORE_PIN_INVALID_MUTANT BAD_RC "$rc"
 exit 1
fi

out="/srv/opentallas-scratch/dma-group-owned-0d4cfabff/core_look_mut"
bash rtl/test/hbm_accel/b2_dma/run_b2_dma_q_bench.sh "$out" -GMUT_CORE_LOOK=1 -GNREC=4
rc=$?
if [ "$rc" -eq 1 ] && grep -q '^B2_DMA_Q FAIL' "$out/run.log"; then
 echo CORE_LOOKAHEAD_MUTANT observed_FAIL
else
 echo CORE_LOOKAHEAD_MUTANT BAD_RC "$rc"
 exit 1
fi

out="/srv/opentallas-scratch/dma-group-owned-0d4cfabff/core_advance_mut"
bash rtl/test/hbm_accel/b2_dma/run_b2_dma_q_bench.sh "$out" -GMUT_CORE_ADV=1 -GNREC=4
rc=$?
if [ "$rc" -eq 1 ] && grep -q '^B2_DMA_Q FAIL' "$out/run.log"; then
 echo CORE_ADVANCE_MUTANT observed_FAIL
else
 echo CORE_ADVANCE_MUTANT BAD_RC "$rc"
 exit 1
fi

out="/srv/opentallas-scratch/dma-group-owned-0d4cfabff/group_owned_mut"
bash rtl/test/hbm_accel/b2_dma/run_b2_dma_q_bench.sh "$out" -GMUT_GROUP_OWN=1 -GNREC=4
rc=$?
if [ "$rc" -eq 1 ] && grep -q '^B2_DMA_Q FAIL' "$out/run.log"; then
 echo GROUP_OWNED_MUTANT observed_FAIL
else
 echo GROUP_OWNED_MUTANT BAD_RC "$rc"
 exit 1
fi
