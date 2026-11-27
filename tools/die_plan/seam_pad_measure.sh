#!/bin/bash
# usage: [SEAM_OUT=dir] seam_pad_measure.sh KIT_DIR BASE_REL(odb dir rel. to kit) ODB_NAME SPEF_NAME|none NAME LABEL [PAD_SPEC_TSV]
# results: $SEAM_OUT (default ./seam_out)/<NAME>_<LABEL>_{TT,FF}.tsv + .log + .identity   (read-only on the kit; the ODB is never written)
set -euo pipefail
W=$(cd "$(dirname "$0")" && pwd)   # tool dir: seam_pad_measure.tcl, seam_pad_port.tcl (never written)
O=${SEAM_OUT:-$PWD/seam_out}
K=$1; BASE=$2; ODB=$3; SPEF=$4; P=$5; L=$6; PAD=${7:-}
mkdir -p "$O"
if [ "$SPEF" = none ]; then sha256sum "$K/$BASE/$ODB" | tee "$O/${P}_${L}.identity"
else sha256sum "$K/$BASE/$ODB" "$K/$BASE/$SPEF" | tee "$O/${P}_${L}.identity"; fi
for C in TT FF; do
  env=(-e OT_CORNER=$C -e ODB=/work/$BASE/$ODB -e OUT=/out/${P}_${L}_$C.tsv)
  [ "$SPEF" = none ] || env+=(-e SPEF=/work/$BASE/$SPEF)
  mnt=(-v "$K:/work:ro" -v "$O:/out" -v "$W/seam_pad_measure.tcl:/tmp/seam.tcl:ro" -v "$W/seam_pad_port.tcl:/sp/seam_pad_port.tcl:ro")
  if [ -n "$PAD" ]; then env+=(-e PAD_SPEC=/pad.tsv); mnt+=(-v "$PAD:/pad.tsv:ro"); fi
  docker run --rm --cpus 2 --memory 12g "${mnt[@]}" "${env[@]}" openroad/orfs:asap7lock \
    bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; exec openroad -exit /tmp/seam.tcl' > "$O/${P}_${L}_$C.log" 2>&1 || { grep -v STA-1212 "$O/${P}_${L}_$C.log" | tail -20; exit 1; }
  grep -E '^SEAM_' "$O/${P}_${L}_$C.log"
done
