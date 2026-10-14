#!/bin/bash
set -u
for seam in 1 2 3 4 5 6 7; do
  out="/srv/opentallas-scratch/dma-face9rq-9000f754c/mut$seam"
  bash rtl/test/hbm_accel/b2_dma/run_b2_dma_q_bench.sh "$out" "-GMUT_SEAM=$seam" -GNREC=4
  rc=$?
  if [ "$rc" -eq 1 ] && grep -q '^B2_DMA_Q FAIL' "$out/run.log"; then
    echo "FACE9RQ_MUTANT $seam observed_FAIL"
  else
    echo "FACE9RQ_MUTANT $seam BAD_RC $rc"
    exit 1
  fi
done
