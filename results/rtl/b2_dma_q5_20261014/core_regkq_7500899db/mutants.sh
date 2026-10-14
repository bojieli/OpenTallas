#!/bin/bash
set -u
for seam in 1 2 3 4 5 6 7; do
  out="/srv/opentallas-scratch/dma-core-regkq-7500899db/mut$seam"
  bash rtl/test/hbm_accel/b2_dma/run_b2_dma_q_bench.sh "$out" "-GMUT_SEAM=$seam" -GNREC=4
  rc=$?
  if [ "$rc" -eq 1 ] && grep -q '^B2_DMA_Q FAIL' "$out/run.log"; then
    echo "FACE9RQ_MUTANT $seam observed_FAIL"
  else
    echo "FACE9RQ_MUTANT $seam BAD_RC $rc"
    exit 1
  fi
done
out="/srv/opentallas-scratch/dma-core-regkq-7500899db/core_pin_mut"
bash rtl/test/hbm_accel/b2_dma/run_b2_dma_q_bench.sh "$out" -GMUT_CORE_PIN=1 -GNREC=4
rc=$?
if [ "$rc" -eq 1 ] && grep -q 'core registered encoded512 disagrees' "$out/run.log"; then
 echo CORE_PIN_INVALID_MUTANT observed_FAIL
else
 echo CORE_PIN_INVALID_MUTANT BAD_RC "$rc"
 exit 1
fi
