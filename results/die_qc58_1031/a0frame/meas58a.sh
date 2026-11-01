#!/bin/bash
# DIE-QC-58A: measure face-register clock arrivals (TT, FF) on the DIE-QC-57d V3 CTS ODBs (read-only mounts)
M=/srv/opentallas-scratch2/claude/die-qc-58a/meas
for t in nk:e6_nk:kq_qfd_tile_nk_a0c_a0nk14icg2rr1 nl:e3_nl:kq_qfd_tile_nl_a0c_a0nl14icg2rr2; do
  IFS=: read n d top <<< "$t"; K=/srv/opentallas-scratch2/claude/die-qc-57d/$d
  for c in TT FF; do
    sudo docker run --rm --name dqc58a-meas-$n-$c --cpus=2 --memory=12g --memory-swap=12g -v "$K":/work:ro -v $M:/out \
      -e CORNER=$c -e ODB=/work/run/results/asap7/$top/base/diag57_cts.odb -e SDC=/work/run/results/asap7/$top/base/3_place.sdc \
      -e FACE=/work/run/results/asap7/$top/base/ot_face_flops.txt -e OUT=/out/${n}_$c.tsv \
      openroad/orfs:asap7lock bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /out/meas58a.tcl" > $M/${n}_$c.log 2>&1 &
  done
done
wait; sudo chown -R $(id -u):$(id -g) $M; echo done
