#!/bin/bash
# usage: whatif.sh KIT_GEN_DIR ODBNAME SDCNAME OUTDIR   (kit mounted read-only)
set -uo pipefail
G=$1; ODB=$2; SDC=$3; OUT=$4; mkdir -p "$OUT"
RS=${5:-$(ls -d $G/run/results/*/*/base | head -1)}
DK=docker; docker ps >/dev/null 2>&1 || DK="sudo docker"
cp "$(dirname "$0")/whatif.tcl" "$OUT/"
$DK run --rm --name "fableunc-wi-$$" --cpus 4 --memory 32g --memory-swap 32g -v "$G":/work:ro -v "$RS":/odb:ro -v "$OUT":/out -e ODB=$ODB -e SDC=$SDC -e HUID=$(id -u) -e HGID=$(id -g) -w /out openroad/orfs:asap7lock bash -lc \
 "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 4 -exit /out/whatif.tcl > /out/whatif.log 2>&1; rc=\$?; chown -R \$HUID:\$HGID /out; exit \$rc"
rc=$?; echo "rc $rc"; grep WHATIF "$OUT/whatif.log"; grep -n "ERROR" "$OUT/whatif.log" | head -5; grep -q "WHATIF done" "$OUT/whatif.log"
